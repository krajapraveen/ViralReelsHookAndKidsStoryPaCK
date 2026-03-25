"""
Story Engine Pipeline — Main orchestrator that runs the 11-step pipeline.
Coordinates planning, generation, assembly, and validation stages.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db

from .schemas import JobState, PipelineJob, StageResult
from .state_machine import transition_job, get_progress, get_label
from .cost_guard import pre_flight_check, check_stage_budget, estimate_cost
from .continuity import validate_pipeline_outputs, validate_character_continuity, should_mark_ready
from .safety import check_content_safety, check_rate_limits, detect_abuse
from .negative_prompt import get_negative_prompt

from .adapters import planning_llm, video_gen, tts, ffmpeg_assembly

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
) -> Dict:
    """
    Step 1-2: Credit check + Create job.
    Returns the job document or raises on failure.
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

    rate_error = await check_rate_limits(db, user_id)
    if rate_error:
        return {"success": False, "error": rate_error}

    abuse_error = await detect_abuse(db, user_id)
    if abuse_error:
        return {"success": False, "error": abuse_error}

    # ── Credit check ──
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

    # ── Atomic credit deduction ──
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": cost.total_credits_required}},
        {
            "$inc": {"credits": -cost.total_credits_required},
            "$push": {
                "credit_history": {
                    "type": "deduction",
                    "amount": -cost.total_credits_required,
                    "reason": f"Story Engine job {job_id[:8]}",
                    "timestamp": now,
                }
            },
        },
    )

    if result.modified_count == 0:
        # Race condition — credits insufficient between check and deduction
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"state": JobState.FAILED.value, "error_message": "Credit deduction failed — insufficient credits"}},
        )
        return {"success": False, "error": "Credit deduction failed — try again"}

    # Log credit transaction
    await db.credit_transactions.insert_one({
        "user_id": user_id,
        "amount": -cost.total_credits_required,
        "type": "story_engine_deduction",
        "job_id": job_id,
        "timestamp": now,
    })

    logger.info(f"[PIPELINE] Job {job_id[:8]} created for user {user_id[:8]}, deducted {cost.total_credits_required} credits")

    return {
        "success": True,
        "job_id": job_id,
        "state": JobState.INIT.value,
        "credits_deducted": cost.total_credits_required,
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
        # ── Step 3: Generate episode plan ──
        job = await transition_job(db, job_id, JobState.PLANNING)
        plan_result = await _run_stage(job_id, "planning", _stage_planning, job)
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
    """Generate keyframes for all scenes."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    plans = job.get("scene_motion_plans", [])
    continuity = job.get("character_continuity", {})

    keyframe_urls = []
    for plan in plans:
        result = await video_gen.generate_keyframe(
            scene_plan=plan,
            continuity=continuity,
            style_id=job.get("style_id", "cartoon_2d"),
        )
        keyframe_urls.append(result.get("url"))

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"keyframe_urls": keyframe_urls}},
    )

    generated = sum(1 for u in keyframe_urls if u)
    return {"status": "success", "output": {"keyframes_generated": generated, "total": len(plans)}}


async def _stage_scene_clips(job: dict) -> Dict:
    """Generate moving scene clips."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    plans = job.get("scene_motion_plans", [])
    keyframes = job.get("keyframe_urls", [])
    continuity = job.get("character_continuity", {})

    clip_urls = []
    for i, plan in enumerate(plans):
        kf_url = keyframes[i] if i < len(keyframes) else None
        result = await video_gen.generate_scene_clip(
            scene_plan=plan,
            keyframe_url=kf_url,
            continuity=continuity,
            style_id=job.get("style_id", "cartoon_2d"),
        )
        clip_urls.append(result.get("url"))

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"scene_clip_urls": clip_urls}},
    )

    generated = sum(1 for u in clip_urls if u)
    return {"status": "success", "output": {"clips_generated": generated, "total": len(plans)}}


async def _stage_audio(job: dict) -> Dict:
    """Generate narration audio."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})

    result = await tts.generate_narration(
        episode_plan=job.get("episode_plan", {}),
        scene_motion_plans=job.get("scene_motion_plans", []),
    )

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"narration_url": result.get("url"), "narration_segments": result.get("segments", [])}},
    )

    return {"status": "success" if result.get("status") != "failed" else "failed", "output": result}


async def _stage_assembly(job: dict) -> Dict:
    """FFmpeg assembly — stitch clips, mix audio, generate preview/thumbnail."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    clips = [u for u in job.get("scene_clip_urls", []) if u]

    if not clips:
        # No GPU-generated clips available yet — record assembly plan
        plans = job.get("scene_motion_plans", [])
        transitions = [p.get("transition_type", "crossfade") for p in plans[1:]] if plans else []
        assembly_plan = ffmpeg_assembly.build_assembly_plan(
            scene_clips=[f"scene_{i+1}.mp4" for i in range(len(plans))],
            narration_path=job.get("narration_url"),
            transitions=transitions,
        )
        await db.story_engine_jobs.update_one(
            {"job_id": job["job_id"]},
            {"$set": {"assembly_plan": assembly_plan}},
        )
        return {
            "status": "success",
            "output": {
                "note": "Assembly plan created. Clips will be stitched when GPU workers produce scene clips.",
                "assembly_plan": assembly_plan,
            },
        }

    # Real clips available — assemble
    # (In production, clips are local files downloaded from R2/S3)
    return {"status": "success", "output": {"note": "Assembly ready for execution when clips are local files"}}


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

    # Refund credits
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if job and job.get("cost_estimate"):
        refund_amount = job["cost_estimate"].get("total_credits_required", 0)
        if refund_amount > 0:
            now = datetime.now(timezone.utc).isoformat()
            await db.users.update_one(
                {"id": job["user_id"]},
                {"$inc": {"credits": refund_amount}},
            )
            await db.credit_transactions.insert_one({
                "user_id": job["user_id"],
                "amount": refund_amount,
                "type": "story_engine_refund",
                "job_id": job_id,
                "reason": f"Pipeline failure: {error[:100]}",
                "timestamp": now,
            })
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"credits_refunded": refund_amount}},
            )
            logger.info(f"[PIPELINE] Refunded {refund_amount} credits for failed job {job_id[:8]}")


async def get_job_status(job_id: str) -> Optional[Dict]:
    """Get current job status with progress."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return None

    state = JobState(job["state"])
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
    }
