"""
Panel Orchestrator — The heart of the smart repair pipeline.
Generate → Validate → Diagnose → Repair → Fallback → Persist outcome.

Hard caps:
  - 1 primary attempt
  - 1 repair attempt
  - 1 fallback attempt
  - Max 3 total attempts per panel

NO blind retries. Every retry has:
  - explicit failure classification
  - explicit repair mode
  - explicit model tier reason
"""
import time
import base64
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from enums.pipeline_enums import (
    FailureType, ModelTier, RepairMode, PanelStatus, FailureClass,
    ValidationResult, PanelScores, RiskBucket,
    MAX_PRIMARY_ATTEMPTS, MAX_REPAIR_ATTEMPTS, MAX_FALLBACK_ATTEMPTS,
    MAX_TOTAL_ATTEMPTS_PER_PANEL, MODEL_TIER_MAPPING,
    PIPELINE_STATE_MESSAGES,
)
from services.comic_pipeline.validator_stack import ValidatorStack
from services.comic_pipeline.prompt_composer import PromptComposer
from services.comic_pipeline.model_router import ModelRouter
from services.comic_pipeline.attempt_logger import AttemptLogger
from services.comic_pipeline.character_lock_service import CharacterLockService, CharacterLock

logger = logging.getLogger("creatorstudio.comic_pipeline.panel_orchestrator")


class PanelOrchestrator:
    """
    Processes a single panel through the smart repair pipeline.
    Clean reliability engine — no credits, no UI text, no metrics aggregation.
    """

    def __init__(self, db, llm_key: str):
        self.db = db
        self.llm_key = llm_key
        self.validator = ValidatorStack()
        self.prompt_composer = PromptComposer()
        self.model_router = ModelRouter()
        self.attempt_logger = AttemptLogger(db)

    async def process_panel(
        self,
        job_id: str,
        panel_index: int,
        scene: dict,
        style_name: str,
        style_prompt: str,
        genre: str,
        photo_b64: str,
        negative_prompt: str,
        panel_count: int,
        risk_bucket: RiskBucket,
        character_lock: Optional[CharacterLock] = None,
        source_image_bytes: Optional[bytes] = None,
        approved_panel_bytes: Optional[List[bytes]] = None,
        user_id: str = "",
        force_fail: bool = False,
    ) -> dict:
        """
        Process a single panel through: Primary → Validate → Smart Repair → Fallback.

        Returns panel_data dict compatible with the existing pipeline.
        """
        panel_start = time.time()
        total_attempts = 0
        worker_telemetry = {
            "job_id": job_id,
            "panel_index": panel_index,
            "style": style_name,
            "risk_bucket": risk_bucket.value if risk_bucket else "UNKNOWN",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "stages": [],
        }

        panel_data = {
            "panelNumber": panel_index + 1,
            "scene": scene.get("scene", f"Panel {panel_index + 1}"),
            "dialogue": scene.get("dialogue"),
            "style": style_name,
        }

        # Character lock context for prompts
        char_context = None
        if character_lock:
            char_lock_svc = CharacterLockService(self.db)
            char_context = char_lock_svc.get_continuity_context(character_lock)

        # Build base prompt
        base_prompt = self.prompt_composer.build_base_prompt(
            panel_index=panel_index,
            total_panels=panel_count,
            scene=scene.get("scene", ""),
            style_prompt=style_prompt,
            genre=genre,
            character_lock=char_context,
            negative_prompt=negative_prompt,
        )

        # Forced failure for validation testing
        if force_fail:
            logger.info(f"[ORCHESTRATOR] Forced failure for panel {panel_index + 1}, job {job_id}")
            panel_data.update({
                "imageUrl": None,
                "status": PanelStatus.FAILED.value,
                "fail_reason": "validation_forced_failure",
                "pipeline_status": PanelStatus.FAILED.value,
                "timing_ms": round((time.time() - panel_start) * 1000),
                "attempts": 0,
                "model_tier_used": "none",
                "routing_explanation": "Forced failure for validation testing",
            })
            return panel_data

        # ══════════════════════════════════════════════════════════════
        # STAGE 1: PRIMARY GENERATION
        # ══════════════════════════════════════════════════════════════
        initial_tier = self.model_router.choose_initial_tier(risk_bucket)
        primary_result = await self._generate_panel(
            job_id=job_id,
            panel_index=panel_index,
            prompt=base_prompt,
            model_tier=initial_tier,
            photo_b64=photo_b64,
            user_id=user_id,
            attempt_number=1,
            stage="PRIMARY",
            attempt_type="primary",
            approved_panel_bytes=approved_panel_bytes,
        )
        total_attempts += 1

        # ── WORKER TELEMETRY: PRIMARY ──
        worker_telemetry["stages"].append({
            "stage": "PRIMARY",
            "model_tier": initial_tier.value,
            "model": MODEL_TIER_MAPPING[initial_tier]["model"],
            "latency_ms": primary_result["latency_ms"],
            "success": primary_result["success"],
            "error_type": primary_result.get("error_type"),
        })

        if primary_result["success"]:
            # Validate the output
            validation = self.validator.validate(
                image_bytes=primary_result.get("image_bytes"),
                panel_plan={"panel_index": panel_index},
                panel_data=panel_data,
                source_image_bytes=source_image_bytes,
                approved_panel_bytes=approved_panel_bytes,
            )

            # Log the attempt
            await self.attempt_logger.log_attempt(
                job_id=job_id,
                panel_index=panel_index,
                attempt_number=1,
                stage="PRIMARY",
                attempt_type="primary",
                model_tier=initial_tier.value,
                provider_model=MODEL_TIER_MAPPING[initial_tier]["model"],
                prompt_text=base_prompt,
                latency_ms=primary_result["latency_ms"],
                accepted=validation.pass_status,
                scores=validation.scores.model_dump() if validation.scores else None,
                failure_types_out=[ft.value for ft in validation.failure_types],
                severity_out=validation.severity,
                asset_url=primary_result.get("cdn_url"),
                validator_summary=validation.validator_summary,
            )

            if validation.pass_status:
                panel_data.update({
                    "imageUrl": primary_result.get("cdn_url") or primary_result.get("data_url"),
                    "status": "READY",
                    "pipeline_status": PanelStatus.PASSED.value,
                    "retries": 0,
                    "timing_ms": round((time.time() - panel_start) * 1000),
                    "attempts": total_attempts,
                    "model_tier_used": initial_tier.value,
                    "validation_scores": validation.scores.model_dump(),
                    "_image_bytes": primary_result.get("image_bytes"),
                    "routing_explanation": self.model_router.explain_routing_decision(
                        initial_tier, "Primary pass", risk_bucket=risk_bucket
                    ),
                })
                await self._persist_worker_telemetry(worker_telemetry, total_attempts, round((time.time() - panel_start) * 1000), panel_data)
                return panel_data

            # ══════════════════════════════════════════════════════════
            # STAGE 2: SMART REPAIR (not blind retry)
            # ══════════════════════════════════════════════════════════
            if total_attempts < MAX_TOTAL_ATTEMPTS_PER_PANEL:
                repair_strategy = self.model_router.choose_repair_strategy(validation, risk_bucket)

                repair_prompt = self.prompt_composer.build_repair_prompt(
                    base_prompt=base_prompt,
                    failure_types=validation.failure_types,
                    repair_mode=repair_strategy.repair_mode,
                    panel_index=panel_index,
                    scene=scene.get("scene", ""),
                )

                repair_result = await self._generate_panel(
                    job_id=job_id,
                    panel_index=panel_index,
                    prompt=repair_prompt,
                    model_tier=repair_strategy.model_tier,
                    photo_b64=photo_b64,
                    user_id=user_id,
                    attempt_number=2,
                    stage=f"REPAIR_{repair_strategy.repair_mode.value}",
                    attempt_type="repair",
                    approved_panel_bytes=approved_panel_bytes,
                )
                total_attempts += 1

                # ── WORKER TELEMETRY: REPAIR ──
                worker_telemetry["stages"].append({
                    "stage": f"REPAIR_{repair_strategy.repair_mode.value}",
                    "model_tier": repair_strategy.model_tier.value,
                    "model": MODEL_TIER_MAPPING[repair_strategy.model_tier]["model"],
                    "latency_ms": repair_result["latency_ms"],
                    "success": repair_result["success"],
                    "error_type": repair_result.get("error_type"),
                    "repair_mode": repair_strategy.repair_mode.value,
                })

                if repair_result["success"]:
                    repair_validation = self.validator.validate(
                        image_bytes=repair_result.get("image_bytes"),
                        panel_plan={"panel_index": panel_index},
                        panel_data=panel_data,
                        source_image_bytes=source_image_bytes,
                        approved_panel_bytes=approved_panel_bytes,
                    )

                    await self.attempt_logger.log_attempt(
                        job_id=job_id,
                        panel_index=panel_index,
                        attempt_number=2,
                        stage=f"REPAIR_{repair_strategy.repair_mode.value}",
                        attempt_type="repair",
                        model_tier=repair_strategy.model_tier.value,
                        provider_model=MODEL_TIER_MAPPING[repair_strategy.model_tier]["model"],
                        prompt_text=repair_prompt,
                        latency_ms=repair_result["latency_ms"],
                        accepted=repair_validation.pass_status,
                        trigger_reason=[ft.value for ft in validation.failure_types],
                        repair_mode=repair_strategy.repair_mode.value,
                        scores=repair_validation.scores.model_dump(),
                        failure_types_in=[ft.value for ft in validation.failure_types],
                        failure_types_out=[ft.value for ft in repair_validation.failure_types],
                        severity_in=validation.severity,
                        severity_out=repair_validation.severity,
                        asset_url=repair_result.get("cdn_url"),
                        validator_summary=repair_validation.validator_summary,
                    )

                    if repair_validation.pass_status:
                        panel_data.update({
                            "imageUrl": repair_result.get("cdn_url") or repair_result.get("data_url"),
                            "status": "READY",
                            "pipeline_status": PanelStatus.PASSED_REPAIRED.value,
                            "retries": 1,
                            "timing_ms": round((time.time() - panel_start) * 1000),
                            "attempts": total_attempts,
                            "model_tier_used": repair_strategy.model_tier.value,
                            "repair_mode": repair_strategy.repair_mode.value,
                            "validation_scores": repair_validation.scores.model_dump(),
                            "_image_bytes": repair_result.get("image_bytes"),
                            "routing_explanation": self.model_router.explain_routing_decision(
                                repair_strategy.model_tier,
                                f"Repair after {[ft.value for ft in validation.failure_types]}",
                                validation.failure_types, risk_bucket,
                            ),
                        })
                        await self._persist_worker_telemetry(worker_telemetry, total_attempts, round((time.time() - panel_start) * 1000), panel_data)
                        return panel_data

                    # Update validation for fallback decision
                    validation = repair_validation
                else:
                    await self.attempt_logger.log_attempt(
                        job_id=job_id,
                        panel_index=panel_index,
                        attempt_number=2,
                        stage=f"REPAIR_{repair_strategy.repair_mode.value}",
                        attempt_type="repair",
                        model_tier=repair_strategy.model_tier.value,
                        provider_model=MODEL_TIER_MAPPING[repair_strategy.model_tier]["model"],
                        prompt_text=repair_prompt,
                        latency_ms=repair_result["latency_ms"],
                        accepted=False,
                        trigger_reason=[ft.value for ft in validation.failure_types],
                        repair_mode=repair_strategy.repair_mode.value,
                        error_type=repair_result.get("error_type"),
                        error_message=repair_result.get("error_message"),
                    )
        else:
            # Primary generation failed entirely
            await self.attempt_logger.log_attempt(
                job_id=job_id,
                panel_index=panel_index,
                attempt_number=1,
                stage="PRIMARY",
                attempt_type="primary",
                model_tier=initial_tier.value,
                provider_model=MODEL_TIER_MAPPING[initial_tier]["model"],
                prompt_text=base_prompt,
                latency_ms=primary_result["latency_ms"],
                accepted=False,
                error_type=primary_result.get("error_type"),
                error_message=primary_result.get("error_message"),
            )
            validation = ValidationResult(
                pass_status=False,
                failure_types=[FailureType.HARD_FAIL],
                failure_class=FailureClass.HARD,
                severity=1.0,
            )

        # ══════════════════════════════════════════════════════════════
        # STAGE 3: DEGRADED FALLBACK (last resort)
        # ══════════════════════════════════════════════════════════════
        if total_attempts < MAX_TOTAL_ATTEMPTS_PER_PANEL:
            fallback_prompt = self.prompt_composer.build_degraded_prompt(
                panel_index=panel_index,
                total_panels=panel_count,
                scene=scene.get("scene", ""),
                style_prompt=style_prompt,
                genre=genre,
                negative_prompt=negative_prompt,
            )

            fallback_result = await self._generate_panel(
                job_id=job_id,
                panel_index=panel_index,
                prompt=fallback_prompt,
                model_tier=ModelTier.TIER4_SAFE_DEGRADED,
                photo_b64=photo_b64,
                user_id=user_id,
                attempt_number=3,
                stage="FALLBACK",
                attempt_type="fallback",
                approved_panel_bytes=approved_panel_bytes,
            )
            total_attempts += 1

            # ── WORKER TELEMETRY: FALLBACK ──
            worker_telemetry["stages"].append({
                "stage": "FALLBACK",
                "model_tier": ModelTier.TIER4_SAFE_DEGRADED.value,
                "model": MODEL_TIER_MAPPING[ModelTier.TIER4_SAFE_DEGRADED]["model"],
                "latency_ms": fallback_result["latency_ms"],
                "success": fallback_result["success"],
                "error_type": fallback_result.get("error_type"),
                "fallback": True,
            })

            if fallback_result["success"]:
                fb_validation = self.validator.validate(
                    image_bytes=fallback_result.get("image_bytes"),
                    panel_plan={"panel_index": panel_index},
                    panel_data=panel_data,
                    source_image_bytes=source_image_bytes,
                    approved_panel_bytes=approved_panel_bytes,
                    is_fallback=True,
                )

                await self.attempt_logger.log_attempt(
                    job_id=job_id,
                    panel_index=panel_index,
                    attempt_number=3,
                    stage="FALLBACK",
                    attempt_type="fallback",
                    model_tier=ModelTier.TIER4_SAFE_DEGRADED.value,
                    provider_model=MODEL_TIER_MAPPING[ModelTier.TIER4_SAFE_DEGRADED]["model"],
                    prompt_text=fallback_prompt,
                    latency_ms=fallback_result["latency_ms"],
                    accepted=fb_validation.pass_status or fb_validation.fallback_acceptable,
                    trigger_reason=[ft.value for ft in validation.failure_types],
                    scores=fb_validation.scores.model_dump(),
                    failure_types_in=[ft.value for ft in validation.failure_types],
                    failure_types_out=[ft.value for ft in fb_validation.failure_types],
                    severity_in=validation.severity,
                    severity_out=fb_validation.severity,
                    asset_url=fallback_result.get("cdn_url"),
                    validator_summary=fb_validation.validator_summary,
                )

                if fb_validation.pass_status or fb_validation.fallback_acceptable:
                    panel_data.update({
                        "imageUrl": fallback_result.get("cdn_url") or fallback_result.get("data_url"),
                        "status": "READY",
                        "pipeline_status": PanelStatus.PASSED_DEGRADED.value,
                        "retries": 2,
                        "fallback": True,
                        "timing_ms": round((time.time() - panel_start) * 1000),
                        "attempts": total_attempts,
                        "model_tier_used": ModelTier.TIER4_SAFE_DEGRADED.value,
                        "validation_scores": fb_validation.scores.model_dump(),
                        "_image_bytes": fallback_result.get("image_bytes"),
                        "routing_explanation": self.model_router.explain_routing_decision(
                            ModelTier.TIER4_SAFE_DEGRADED,
                            f"Degraded fallback after {total_attempts - 1} failed attempts",
                            validation.failure_types, risk_bucket,
                        ),
                    })
                    await self._persist_worker_telemetry(worker_telemetry, total_attempts, round((time.time() - panel_start) * 1000), panel_data)
                    return panel_data
            else:
                await self.attempt_logger.log_attempt(
                    job_id=job_id,
                    panel_index=panel_index,
                    attempt_number=3,
                    stage="FALLBACK",
                    attempt_type="fallback",
                    model_tier=ModelTier.TIER4_SAFE_DEGRADED.value,
                    provider_model=MODEL_TIER_MAPPING[ModelTier.TIER4_SAFE_DEGRADED]["model"],
                    prompt_text=fallback_prompt,
                    latency_ms=fallback_result["latency_ms"],
                    accepted=False,
                    error_type=fallback_result.get("error_type"),
                    error_message=fallback_result.get("error_message"),
                )

        # ══════════════════════════════════════════════════════════════
        # PANEL FAILED — all attempts exhausted
        # ══════════════════════════════════════════════════════════════
        total_duration_ms = round((time.time() - panel_start) * 1000)
        panel_data.update({
            "imageUrl": None,
            "status": "FAILED",
            "pipeline_status": PanelStatus.FAILED.value,
            "fail_reason": "all_attempts_exhausted",
            "timing_ms": total_duration_ms,
            "attempts": total_attempts,
            "model_tier_used": "exhausted",
            "routing_explanation": f"All {total_attempts} attempts exhausted. "
                                   f"Failures: {[ft.value for ft in validation.failure_types]}",
        })

        # ── WORKER TELEMETRY: PERSIST ──
        await self._persist_worker_telemetry(worker_telemetry, total_attempts, total_duration_ms, panel_data)

        return panel_data

    async def _persist_worker_telemetry(self, telemetry: dict, total_attempts: int, total_duration_ms: int, panel_data: dict):
        """Persist worker performance telemetry to DB and log structured metrics."""
        telemetry["end_time"] = datetime.now(timezone.utc).isoformat()
        telemetry["total_duration_ms"] = total_duration_ms
        telemetry["total_attempts"] = total_attempts
        telemetry["final_status"] = panel_data.get("status", "UNKNOWN")
        telemetry["pipeline_status"] = panel_data.get("pipeline_status", "UNKNOWN")
        telemetry["model_tier_used"] = panel_data.get("model_tier_used", "UNKNOWN")
        telemetry["fallback_used"] = panel_data.get("fallback", False)
        telemetry["fail_reason"] = panel_data.get("fail_reason")

        # Compute model time vs queue/overhead time
        model_time_ms = sum(s.get("latency_ms", 0) for s in telemetry["stages"])
        telemetry["model_time_ms"] = model_time_ms
        telemetry["overhead_ms"] = max(0, total_duration_ms - model_time_ms)

        # Structured log for monitoring
        logger.info(
            f"[WORKER_TELEMETRY] job={telemetry['job_id']} panel={telemetry['panel_index']+1} "
            f"status={telemetry['final_status']} pipeline={telemetry['pipeline_status']} "
            f"attempts={total_attempts} total_ms={total_duration_ms} "
            f"model_ms={model_time_ms} overhead_ms={telemetry['overhead_ms']} "
            f"tier={telemetry['model_tier_used']} style={telemetry['style']} "
            f"risk={telemetry['risk_bucket']} fallback={telemetry['fallback_used']} "
            f"fail_reason={telemetry['fail_reason']}"
        )

        # Per-stage breakdown
        for s in telemetry["stages"]:
            logger.info(
                f"[WORKER_STAGE] job={telemetry['job_id']} panel={telemetry['panel_index']+1} "
                f"stage={s['stage']} model={s.get('model')} latency_ms={s.get('latency_ms')} "
                f"success={s.get('success')} error={s.get('error_type')}"
            )

        # Persist to DB
        try:
            await self.db.worker_telemetry.insert_one(telemetry)
        except Exception as e:
            logger.warning(f"[WORKER_TELEMETRY] DB persist failed: {e}")

    async def _generate_panel(
        self,
        job_id: str,
        panel_index: int,
        prompt: str,
        model_tier: ModelTier,
        photo_b64: str,
        user_id: str,
        attempt_number: int,
        stage: str,
        attempt_type: str,
        approved_panel_bytes: Optional[List[bytes]] = None,
    ) -> dict:
        """
        Execute a single generation call. Returns result dict with:
        - success: bool
        - image_bytes: bytes or None
        - cdn_url: str or None
        - data_url: str or None
        - latency_ms: int
        - error_type, error_message: on failure
        """
        gen_start = time.time()
        provider_config = self.model_router.get_provider_config(model_tier)

        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

            # Build system message — enhanced when reference panels exist
            has_refs = approved_panel_bytes and any(b for b in approved_panel_bytes if b)
            system_msg = (
                "You are a comic artist. Create original characters. Maintain character consistency across panels."
                if not has_refs else
                "You are a comic artist. Create original characters. "
                "CRITICAL: Reference images of previously approved panels are provided alongside the source photo. "
                "You MUST match the exact character appearance, art style, line quality, color palette, "
                "and rendering technique shown in those reference panels. The source photo (first image) "
                "defines the character's real face. The reference panels define the established comic style."
            )

            img_chat = LlmChat(
                api_key=self.llm_key,
                session_id=f"smart-comic-{job_id}-p{panel_index}-a{attempt_number}",
                system_message=system_msg,
            )
            img_chat.with_model(
                provider_config["provider"],
                provider_config["model"]
            ).with_params(modalities=["image", "text"])

            # Build image list: source photo first, then approved panel references
            image_contents = [ImageContent(photo_b64)]
            if has_refs:
                for ref_bytes in approved_panel_bytes:
                    if ref_bytes and len(ref_bytes) > 100:
                        ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
                        image_contents.append(ImageContent(ref_b64))

            msg = UserMessage(
                text=prompt,
                file_contents=image_contents
            )

            text_response, images = await asyncio.wait_for(
                img_chat.send_message_multimodal_response(msg),
                timeout=120,
            )

            if images and len(images) > 0:
                img_data = images[0]
                if isinstance(img_data, dict):
                    raw_data = img_data.get('data') or img_data.get('b64_json') or img_data.get('image') or ''
                    image_bytes = base64.b64decode(raw_data) if raw_data else b''
                elif isinstance(img_data, str):
                    image_bytes = base64.b64decode(img_data)
                else:
                    image_bytes = img_data if isinstance(img_data, bytes) else b''

                if not image_bytes:
                    return {
                        "success": False,
                        "latency_ms": round((time.time() - gen_start) * 1000),
                        "error_type": "empty_output",
                        "error_message": "Model returned empty image data",
                    }

                # Watermark
                try:
                    from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config
                    from shared import db as shared_db
                    user_data = await shared_db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
                    user_plan = user_data.get("plan", "free") if user_data and isinstance(user_data, dict) else "free"
                    if should_apply_watermark({"plan": user_plan}):
                        config = get_watermark_config("COMIC")
                        image_bytes = add_diagonal_watermark(
                            image_bytes,
                            text=config["text"],
                            opacity=config["opacity"],
                            font_size=config["font_size"],
                            spacing=config["spacing"],
                        )
                except Exception:
                    pass  # Watermark failure should never block generation

                # Upload to R2
                cdn_url = None
                data_url = None
                try:
                    from services.cloudflare_r2_storage import upload_image_bytes
                    fname = f"comic_smart_{job_id[:8]}_p{panel_index + 1}_a{attempt_number}.png"
                    success, url = await upload_image_bytes(image_bytes, fname, f"comic/{user_id[:8]}")
                    if success and url:
                        cdn_url = url
                except Exception:
                    pass

                if not cdn_url:
                    b64_str = base64.b64encode(image_bytes).decode('utf-8')
                    data_url = f"data:image/png;base64,{b64_str}"

                latency = round((time.time() - gen_start) * 1000)
                logger.info(
                    f"[GEN] job={job_id} panel={panel_index + 1} attempt={attempt_number} "
                    f"stage={stage} tier={model_tier.value} latency={latency}ms"
                )

                return {
                    "success": True,
                    "image_bytes": image_bytes,
                    "cdn_url": cdn_url,
                    "data_url": data_url,
                    "latency_ms": latency,
                }

            return {
                "success": False,
                "latency_ms": round((time.time() - gen_start) * 1000),
                "error_type": "no_images_returned",
                "error_message": "Model did not return any images",
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "latency_ms": round((time.time() - gen_start) * 1000),
                "error_type": "timeout",
                "error_message": "Generation timed out after 120s",
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": round((time.time() - gen_start) * 1000),
                "error_type": type(e).__name__,
                "error_message": str(e)[:200],
            }
