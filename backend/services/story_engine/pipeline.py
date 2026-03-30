"""
Story Engine Pipeline — Main orchestrator that runs the 11-step pipeline.
Coordinates planning, generation, assembly, and validation stages.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from .schemas import JobState, PipelineJob, StageResult
from .state_machine import transition_job, get_progress, get_label
from .cost_guard import pre_flight_check, check_stage_budget, estimate_cost
from .continuity import validate_pipeline_outputs, validate_character_continuity, should_mark_ready
from .safety import check_content_safety, check_rate_limits, detect_abuse
from .negative_prompt import get_negative_prompt

from .adapters import planning_llm, video_gen, tts, ffmpeg_assembly

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db

logger = logging.getLogger("story_engine.pipeline")


async def create_job(
    user_id: str,
    story_text: str,
    title: str = "Untitled",
    style_id: str = "cartoon_2d",
    language: str = "en",
    age_group: str = "teens",
    parent_job_id: Optional[str] = None,
    story_chain_id: Optional[str] = None,
    skip_credits: bool = False,
) -> Dict:
    """
    Step 1-2: Credit check + Create job.
    When skip_credits=True (guest mode), bypasses credit check/deduction.
    """
    now = datetime.now(timezone.utc).isoformat()

    # ── Safety checks ──
    violation = check_content_safety(story_text)
    if violation:
        return {"success": False, "error": violation}

    if title:
        title_violation = check_content_safety(title)
        if title_violation:
            return {"success": False, "error": title_violation}

    if not skip_credits:
        rate_error = await check_rate_limits(db, user_id)
        if rate_error:
            return {"success": False, "error": rate_error}

        abuse_error = await detect_abuse(db, user_id)
        if abuse_error:
            return {"success": False, "error": abuse_error}

    # ── Credit check (skip for guests) ──
    cost = None
    if not skip_credits:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
        if not user:
            return {"success": False, "error": "User not found"}

        user_credits = user.get("credits", 0)
        cost = pre_flight_check(user_credits, scene_count=5)

        if not cost.sufficient:
            return {
                "success": False,
                "error": "insufficient_credits",
                "credit_check": {
                    "required": cost.total_credits_required,
                    "current": cost.user_current_credits,
                    "shortfall": cost.shortfall,
                    "breakdown": cost.breakdown,
                },
            }
    else:
        # Guest mode: create a dummy cost for the job doc
        cost = pre_flight_check(999, scene_count=5)  # Passes check with fake high credits

    # ── Create job ──
    job_id = str(uuid.uuid4())
    chain_id = story_chain_id or job_id

    # Determine episode number
    episode_number = 1
    if parent_job_id:
        parent = await db.story_engine_jobs.find_one({"job_id": parent_job_id}, {"_id": 0, "episode_number": 1})
        if parent:
            episode_number = parent.get("episode_number", 0) + 1

    job_doc = {
        "job_id": job_id,
        "user_id": user_id,
        "state": JobState.INIT.value,
        "story_text": story_text,
        "title": title or "Untitled",
        "style_id": style_id,
        "language": language,
        "age_group": age_group,
        "story_chain_id": chain_id,
        "parent_job_id": parent_job_id,
        "episode_number": episode_number,
        "episode_plan": None,
        "character_continuity": None,
        "scene_motion_plans": None,
        "keyframe_urls": [],
        "scene_clip_urls": [],
        "narration_url": None,
        "output_url": None,
        "preview_url": None,
        "thumbnail_url": None,
        "cost_estimate": cost.model_dump(),
        "total_credits_consumed": 0,
        "credits_refunded": 0,
        "stage_results": [],
        "is_seed_content": False,
        "public": False,
        "slug": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "error_message": None,
        "retry_count": 0,
        "max_retries": 2,
    }

    await db.story_engine_jobs.insert_one({k: v for k, v in job_doc.items() if k != "_id"})

    # ── Atomic credit deduction via Credits Service (skip for guests) ──
    credits_deducted = 0
    if not skip_credits:
        from services.credits_service import get_credits_service, InsufficientCreditsError
        svc = get_credits_service(db)
        try:
            deduction = await svc.deduct_credits(
                user_id, cost.total_credits_required,
                reason=f"Story Engine job {job_id[:8]}",
                reference_id=job_id,
            )
            credits_deducted = deduction["amount"]
        except InsufficientCreditsError as e:
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"state": JobState.FAILED.value, "error_message": str(e)}},
            )
            return {"success": False, "error": str(e)}

    logger.info(f"[PIPELINE] Job {job_id[:8]} created for user {user_id[:12]}, deducted {credits_deducted} credits (guest={skip_credits})")

    return {
        "success": True,
        "job_id": job_id,
        "state": JobState.INIT.value,
        "credits_deducted": credits_deducted,
        "cost_estimate": cost.model_dump(),
    }


async def run_pipeline(job_id: str) -> Dict:
    """
    Execute the full 11-step pipeline for a job.
    Steps 3-11: Plan → Character → Motion → Keyframes → Clips → Audio → Assembly → Validate → Ready
    """
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return {"success": False, "error": "Job not found"}

    stage_results = []

    try:
        # ── Step 3: Generate episode plan (with 1 retry for transient LLM failures) ──
        job = await transition_job(db, job_id, JobState.PLANNING)
        plan_result = await _run_stage(job_id, "planning", _stage_planning, job)
        if plan_result["status"] != "success":
            logger.warning(f"[PIPELINE] Planning failed for {job_id[:8]}, retrying once...")
            import asyncio as _aio
            await _aio.sleep(2)
            plan_result = await _run_stage(job_id, "planning_retry", _stage_planning, job)
        stage_results.append(plan_result)
        if plan_result["status"] != "success":
            await _fail_job(job_id, "Episode planning failed", stage_results)
            return {"success": False, "error": "Planning failed", "stage_results": stage_results}

        # ── Step 4: Build character continuity ──
        job = await transition_job(db, job_id, JobState.BUILDING_CHARACTER_CONTEXT)
        char_result = await _run_stage(job_id, "character_context", _stage_character_context, job)
        stage_results.append(char_result)
        if char_result["status"] != "success":
            await _fail_job(job_id, "Character continuity failed", stage_results)
            return {"success": False, "error": "Character context failed", "stage_results": stage_results}

        # ── Step 5: Scene motion planning ──
        job = await transition_job(db, job_id, JobState.PLANNING_SCENE_MOTION)
        motion_result = await _run_stage(job_id, "scene_motion_planning", _stage_scene_motion, job)
        stage_results.append(motion_result)
        if motion_result["status"] != "success":
            await _fail_job(job_id, "Scene motion planning failed", stage_results)
            return {"success": False, "error": "Motion planning failed", "stage_results": stage_results}

        # ── Step 6: Generate keyframes ──
        job = await transition_job(db, job_id, JobState.GENERATING_KEYFRAMES)
        kf_result = await _run_stage(job_id, "keyframes", _stage_keyframes, job)
        stage_results.append(kf_result)
        # Keyframes can partially fail — continue

        # ── Step 7: Generate moving scene clips ──
        job = await transition_job(db, job_id, JobState.GENERATING_SCENE_CLIPS)
        clip_result = await _run_stage(job_id, "scene_clips", _stage_scene_clips, job)
        stage_results.append(clip_result)

        # ── Step 8: Generate narration ──
        job = await transition_job(db, job_id, JobState.GENERATING_AUDIO)
        audio_result = await _run_stage(job_id, "audio", _stage_audio, job)
        stage_results.append(audio_result)

        # ── Step 9: FFmpeg assembly ──
        job = await transition_job(db, job_id, JobState.ASSEMBLING_VIDEO)
        assembly_result = await _run_stage(job_id, "assembly", _stage_assembly, job)
        stage_results.append(assembly_result)

        # ── Step 10-11: Validate and mark READY ──
        job = await transition_job(db, job_id, JobState.VALIDATING)
        job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})

        validation = validate_pipeline_outputs(job)
        final_state = should_mark_ready(validation)

        target = JobState(final_state)
        job = await transition_job(db, job_id, target)

        # Save final stage results
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "stage_results": [r for r in stage_results if r],
                "validation_result": validation.to_dict(),
            }},
        )

        logger.info(f"[PIPELINE] Job {job_id[:8]} completed: {final_state}")
        return {
            "success": final_state in ("READY", "PARTIAL_READY"),
            "job_id": job_id,
            "state": final_state,
            "stage_results": stage_results,
            "validation": validation.to_dict(),
        }

    except Exception as e:
        logger.error(f"[PIPELINE] Job {job_id[:8]} pipeline error: {e}")
        await _fail_job(job_id, str(e), stage_results)
        return {"success": False, "error": str(e), "stage_results": stage_results}


# ═══════════════════════════════════════════════════════════════
# STAGE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════

async def _stage_planning(job: dict) -> Dict:
    """Generate structured episode plan."""
    # Get previous plan if this is a continuation
    previous_plan = None
    if job.get("parent_job_id"):
        parent = await db.story_engine_jobs.find_one(
            {"job_id": job["parent_job_id"]},
            {"_id": 0, "episode_plan": 1},
        )
        if parent:
            previous_plan = parent.get("episode_plan")

    plan = await planning_llm.generate_episode_plan(
        story_text=job["story_text"],
        style_id=job.get("style_id", "cartoon_2d"),
        episode_number=job.get("episode_number", 1),
        previous_plan=previous_plan,
    )

    if not plan:
        return {"status": "failed", "error": "LLM failed to generate episode plan"}

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"episode_plan": plan, "title": plan.get("title", job.get("title", "Untitled"))}},
    )

    return {"status": "success", "output": {"title": plan.get("title"), "scenes": len(plan.get("scene_breakdown", []))}}


async def _stage_character_context(job: dict) -> Dict:
    """Build character continuity package."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    if not job.get("episode_plan"):
        return {"status": "failed", "error": "No episode plan"}

    # Get existing continuity from chain
    existing = None
    if job.get("parent_job_id"):
        parent = await db.story_engine_jobs.find_one(
            {"job_id": job["parent_job_id"]},
            {"_id": 0, "character_continuity": 1},
        )
        if parent:
            existing = parent.get("character_continuity")

    continuity = await planning_llm.generate_character_continuity(
        episode_plan=job["episode_plan"],
        existing_package=existing,
        style_id=job.get("style_id", "cartoon_2d"),
    )

    if not continuity:
        return {"status": "failed", "error": "Failed to generate character continuity"}

    # Add metadata
    continuity["universe_id"] = job.get("story_chain_id", job["job_id"])
    continuity["story_chain_id"] = job.get("story_chain_id", job["job_id"])
    continuity["locked_at"] = datetime.now(timezone.utc).isoformat()

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"character_continuity": continuity}},
    )

    char_count = len(continuity.get("characters", []))
    return {"status": "success", "output": {"characters": char_count, "style_lock": continuity.get("style_lock")}}


async def _stage_scene_motion(job: dict) -> Dict:
    """Generate per-scene motion plans."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})

    plans = await planning_llm.generate_scene_motion_plans(
        episode_plan=job["episode_plan"],
        continuity=job.get("character_continuity", {}),
        style_id=job.get("style_id", "cartoon_2d"),
    )

    if not plans:
        return {"status": "failed", "error": "Failed to generate scene motion plans"}

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"scene_motion_plans": plans}},
    )

    return {"status": "success", "output": {"scenes_planned": len(plans)}}


async def _stage_keyframes(job: dict) -> Dict:
    """Generate REAL keyframes using GPT Image 1."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    plans = job.get("scene_motion_plans", [])
    continuity = job.get("character_continuity", {})
    job_id = job["job_id"]

    keyframe_urls = []
    keyframe_local_paths = []
    for plan in plans:
        result = await video_gen.generate_keyframe(
            scene_plan=plan,
            continuity=continuity,
            style_id=job.get("style_id", "cartoon_2d"),
            job_id=job_id,
        )
        keyframe_urls.append(result.get("url"))
        keyframe_local_paths.append(result.get("local_path"))

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"keyframe_urls": keyframe_urls, "keyframe_local_paths": keyframe_local_paths}},
    )

    generated = sum(1 for u in keyframe_urls if u)
    return {"status": "success", "output": {"keyframes_generated": generated, "total": len(plans)}}


async def _stage_scene_clips(job: dict) -> Dict:
    """Generate REAL moving scene clips using Sora 2. Falls back to Ken Burns on keyframes if Sora fails."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    plans = job.get("scene_motion_plans", [])
    keyframes = job.get("keyframe_urls", [])
    keyframe_paths = job.get("keyframe_local_paths", [])
    continuity = job.get("character_continuity", {})
    job_id = job["job_id"]

    clip_urls = []
    clip_local_paths = []
    sora_count = 0
    fallback_count = 0

    for i, plan in enumerate(plans):
        kf_url = keyframes[i] if i < len(keyframes) else None
        kf_path = keyframe_paths[i] if i < len(keyframe_paths) else None

        # Try Sora 2 first
        result = await video_gen.generate_scene_clip(
            scene_plan=plan,
            keyframe_url=kf_url,
            keyframe_local_path=kf_path,
            continuity=continuity,
            style_id=job.get("style_id", "cartoon_2d"),
            job_id=job_id,
        )

        if result.get("status") == "ready" and result.get("local_path"):
            clip_urls.append(result.get("url"))
            clip_local_paths.append(result.get("local_path"))
            sora_count += 1
        elif kf_path and os.path.exists(kf_path):
            # Graceful degradation: Ken Burns fallback on keyframe
            logger.warning(f"[PIPELINE] Sora failed for scene {i+1}, falling back to Ken Burns on keyframe")
            scene_num = plan.get("scene_number", i + 1)
            duration = plan.get("clip_duration_seconds", 5.0)
            fallback_path = str(Path("/app/backend/static/generated") / f"se_{job_id[:8]}_fallback_{scene_num}.mp4")
            ok = await ffmpeg_assembly.create_ken_burns_fallback(kf_path, fallback_path, duration)
            if ok and os.path.exists(fallback_path):
                fallback_url = f"/api/generated/se_{job_id[:8]}_fallback_{scene_num}.mp4"
                clip_urls.append(fallback_url)
                clip_local_paths.append(fallback_path)
                fallback_count += 1
            else:
                clip_urls.append(None)
                clip_local_paths.append(None)
        else:
            clip_urls.append(None)
            clip_local_paths.append(None)

    # Track whether Ken Burns fallback was used
    used_fallback = fallback_count > 0

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "scene_clip_urls": clip_urls,
            "scene_clip_local_paths": clip_local_paths,
            "used_ken_burns_fallback": used_fallback,
            "sora_clips_count": sora_count,
            "fallback_clips_count": fallback_count,
        }},
    )

    generated = sum(1 for u in clip_urls if u)
    return {
        "status": "success",
        "output": {
            "clips_generated": generated,
            "sora_clips": sora_count,
            "fallback_clips": fallback_count,
            "total": len(plans),
        },
    }


async def _stage_audio(job: dict) -> Dict:
    """Generate REAL narration audio. Gracefully degrades if TTS fails."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})

    result = await tts.generate_narration(
        episode_plan=job.get("episode_plan", {}),
        scene_motion_plans=job.get("scene_motion_plans", []),
        job_id=job["job_id"],
    )

    tts_failed = result.get("status") == "failed"
    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {
            "narration_url": result.get("url"),
            "narration_local_path": result.get("local_path"),
            "narration_segments": result.get("segments", []),
            "tts_failed": tts_failed,
        }},
    )

    # Audio failure is non-fatal — video can still be assembled without narration
    if result.get("status") == "failed":
        logger.warning(f"[PIPELINE] TTS failed for job {job['job_id'][:8]}, proceeding without narration")
        return {"status": "success", "output": {"note": "TTS failed, proceeding without narration", "error": result.get("error")}}

    return {"status": "success", "output": result}


async def _stage_assembly(job: dict) -> Dict:
    """FFmpeg assembly — stitch REAL clips, mix REAL audio, generate preview/thumbnail."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    job_id = job["job_id"]
    clip_paths = [p for p in job.get("scene_clip_local_paths", []) if p and os.path.exists(p)]
    narration_path = job.get("narration_local_path")

    if not clip_paths:
        return {"status": "success", "output": {"note": "No local clips available for assembly yet"}}

    import hashlib
    from pathlib import Path
    output_dir = Path("/app/backend/static/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Stitch clips
    stitched_path = str(output_dir / f"se_{job_id[:8]}_stitched.mp4")
    plans = job.get("scene_motion_plans", [])
    transitions = [p.get("transition_type", "crossfade") for p in plans[1:]] if plans else []

    stitch_ok = await ffmpeg_assembly.stitch_clips(clip_paths, stitched_path, transitions=transitions)
    if not stitch_ok:
        return {"status": "failed", "error": "FFmpeg stitch failed"}

    # Step 2: Mix audio
    final_path = stitched_path
    if narration_path and os.path.exists(narration_path):
        mixed_path = str(output_dir / f"se_{job_id[:8]}_mixed.mp4")
        mix_ok = await ffmpeg_assembly.mix_audio(stitched_path, narration_path, None, mixed_path)
        if mix_ok:
            final_path = mixed_path

    # Step 2.5: Apply addiction triggers (zoom + darken + text in last 2s)
    episode_plan = job.get("episode_plan", {})
    trigger_text = episode_plan.get("trigger_text")
    cliffhanger_text = episode_plan.get("cliffhanger")
    triggered_path = str(output_dir / f"se_{job_id[:8]}_triggered.mp4")
    trigger_ok = await ffmpeg_assembly.apply_addiction_triggers(
        final_path, triggered_path,
        trigger_text=trigger_text,
        cliffhanger_text=cliffhanger_text,
    )
    if trigger_ok and os.path.exists(triggered_path):
        final_path = triggered_path
        logger.info(f"[PIPELINE] Addiction triggers applied for job {job_id[:8]}")
    else:
        logger.warning(f"[PIPELINE] Addiction triggers skipped for job {job_id[:8]} — using original video")

    # Step 3: Generate preview
    preview_path = str(output_dir / f"se_{job_id[:8]}_preview.mp4")
    await ffmpeg_assembly.generate_preview(final_path, preview_path)

    # ── Step 4: Generate deterministic media assets (Pillow + FFmpeg) ──
    # This is the ONLY place thumbnails and posters are ever created.
    from services.story_engine.adapters.media_gen import generate_media_assets

    # Find first available keyframe as fallback image source
    fallback_kf = None
    for kp in job.get("keyframe_local_paths", []):
        if kp and os.path.exists(kp):
            fallback_kf = kp
            break

    thumb_url, poster_url = await generate_media_assets(
        video_path=final_path,
        job_id=job_id,
        fallback_image_path=fallback_kf,
    )

    # Upload video + preview to R2
    from services.story_engine.adapters.video_gen import _upload_to_r2

    output_url = None
    preview_url = None

    if os.path.exists(final_path):
        with open(final_path, "rb") as f:
            output_url = await _upload_to_r2(f.read(), f"se_{job_id[:8]}_final.mp4", job_id, "video")
        if not output_url:
            output_url = f"/api/generated/se_{job_id[:8]}_final.mp4"

    if os.path.exists(preview_path):
        with open(preview_path, "rb") as f:
            preview_url = await _upload_to_r2(f.read(), f"se_{job_id[:8]}_preview.mp4", job_id, "video")
        if not preview_url:
            preview_url = f"/api/generated/se_{job_id[:8]}_preview.mp4"

    # ── Store in STRICT media schema + legacy flat fields for backcompat ──
    update_fields = {
        "output_url": output_url,
        "preview_url": preview_url,
        # Legacy flat fields (kept for backcompat during migration)
        "thumbnail_url": poster_url,
        "thumbnail_small_url": thumb_url,
    }
    # Nested media object — the single source of truth going forward
    if thumb_url:
        update_fields["media.thumbnail_small.url"] = thumb_url
        update_fields["media.thumbnail_small.type"] = "image/jpeg"
    if poster_url:
        update_fields["media.poster_large.url"] = poster_url
        update_fields["media.poster_large.type"] = "image/jpeg"

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": update_fields},
    )

    return {
        "status": "success",
        "output": {
            "output_url": output_url,
            "preview_url": preview_url,
            "media": {
                "thumbnail_small": thumb_url,
                "poster_large": poster_url,
            },
            "clips_stitched": len(clip_paths),
            "has_narration": bool(narration_path),
        },
    }


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

async def _run_stage(job_id: str, stage_name: str, stage_fn, job: dict) -> Dict:
    """Run a pipeline stage with timing and error handling."""
    started = datetime.now(timezone.utc)
    try:
        result = await stage_fn(job)
        completed = datetime.now(timezone.utc)
        duration = (completed - started).total_seconds()

        stage_result = {
            "stage": stage_name,
            "status": result.get("status", "success"),
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": round(duration, 2),
            "output": result.get("output", {}),
            "error": result.get("error"),
        }

        # Update job with stage result
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$push": {"stage_results": stage_result}, "$set": {"updated_at": completed.isoformat()}},
        )

        return stage_result

    except Exception as e:
        logger.error(f"[PIPELINE] Stage {stage_name} failed for job {job_id[:8]}: {e}")
        return {"stage": stage_name, "status": "failed", "error": str(e)}


async def _fail_job(job_id: str, error: str, stage_results: list):
    """Fail a job and trigger credit refund."""
    try:
        await transition_job(db, job_id, JobState.FAILED, error=error)
    except ValueError:
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"state": JobState.FAILED.value, "error_message": error}},
        )

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"stage_results": stage_results}},
    )

    # Refund credits via Credits Service
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if job and job.get("cost_estimate"):
        refund_amount = job["cost_estimate"].get("total_credits_required", 0)
        if refund_amount > 0:
            from services.credits_service import get_credits_service
            svc = get_credits_service(db)
            await svc.refund_credits(
                job["user_id"], refund_amount,
                reason=f"Pipeline failure: {error[:100]}",
                reference_id=job_id,
            )
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"credits_refunded": refund_amount}},
            )


async def get_job_status(job_id: str) -> Optional[Dict]:
    """Get current job status with progress."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return None

    state = JobState(job["state"])
    episode_plan = job.get("episode_plan", {})
    return {
        "job_id": job["job_id"],
        "state": state.value,
        "progress_percent": get_progress(state),
        "current_stage": get_label(state),
        "title": job.get("title"),
        "episode_number": job.get("episode_number"),
        "stage_results": job.get("stage_results", []),
        "output_url": job.get("output_url"),
        "preview_url": job.get("preview_url"),
        "thumbnail_url": job.get("thumbnail_url"),
        "error_message": job.get("error_message"),
        "credits_consumed": job.get("cost_estimate", {}).get("total_credits_required", 0),
        "credits_refunded": job.get("credits_refunded", 0),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
        "used_ken_burns_fallback": job.get("used_ken_burns_fallback", False),
        "sora_clips_count": job.get("sora_clips_count", 0),
        "fallback_clips_count": job.get("fallback_clips_count", 0),
        "cliffhanger": episode_plan.get("cliffhanger"),
        "trigger_text": episode_plan.get("trigger_text"),
        "tension_peak": episode_plan.get("tension_peak"),
        "cut_mood": episode_plan.get("cut_mood"),
    }
