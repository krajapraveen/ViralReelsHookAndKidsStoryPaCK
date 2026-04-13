"""
Story Engine Pipeline — Stage Orchestrator.

Replaces monolithic run_pipeline() with independently retryable stages.
Each stage: load → heartbeat → budget check → execute → persist → advance.
Recovery daemon can resume any stage independently.
"""
import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict

from .schemas import JobState, ErrorCode, TERMINAL_STATES, SUCCESS_STATES, PER_STAGE_FAILURE_STATES
from .state_machine import (
    transition_job, update_heartbeat, increment_stage_retry,
    get_stage_retry_count, get_next_stage, get_failure_state, get_progress, get_label,
    STAGE_ORDER, STAGE_MAX_RETRIES, FAILURE_TO_RETRY,
)
from .cost_guard import pre_flight_check, enforce_runtime_budget, BudgetExceededError
from .continuity import validate_pipeline_outputs, should_mark_ready
from .safety import check_content_safety, check_rate_limits, detect_abuse, rewrite_content_safely, should_queue_job

from .adapters import planning_llm, video_gen, tts, ffmpeg_assembly

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db

logger = logging.getLogger("story_engine.pipeline")


# ═══════════════════════════════════════════════════════════════
# JOB CREATION — Step 1-2: Credit check + Create job
# ═══════════════════════════════════════════════════════════════

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
    now = datetime.now(timezone.utc).isoformat()

    # Safety: rewrite risky terms instead of blocking
    story_text, was_rewritten, user_note = rewrite_content_safely(story_text)

    if title:
        title, _, _ = rewrite_content_safely(title)

    if not skip_credits:
        rate_error = await check_rate_limits(db, user_id)
        if rate_error:
            return {"success": False, "error": rate_error}

        abuse_error = await detect_abuse(db, user_id)
        if abuse_error:
            return {"success": False, "error": abuse_error}

    # Credit check
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
        cost = pre_flight_check(999, scene_count=5)

    # Create job document
    job_id = str(uuid.uuid4())
    chain_id = story_chain_id or job_id

    episode_number = 1
    parent_chain_depth = 0
    if parent_job_id:
        parent = await db.story_engine_jobs.find_one(
            {"job_id": parent_job_id},
            {"_id": 0, "episode_number": 1, "chain_depth": 1, "root_story_id": 1, "story_chain_id": 1}
        )
        if parent:
            episode_number = parent.get("episode_number", 0) + 1
            parent_chain_depth = (parent.get("chain_depth") or 0) + 1
            # Inherit root_story_id from parent if not provided via story_chain_id
            if not story_chain_id:
                chain_id = parent.get("root_story_id") or parent.get("story_chain_id") or parent_job_id

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
        "visibility": "public",  # public | unlisted | private
        "slug": None,
        "hooks": [],
        "hook_text": None,
        "winning_hook": None,
        "hook_locked": False,
        # Reliability fields
        "retry_count": 0,
        "max_retries": 3,
        "last_heartbeat_at": now,
        "last_error_code": None,
        "last_error_message": None,
        "last_error_stage": None,
        "stage_retry_counts": {},
        # Worker priority + recovery
        "worker_class": "critical_story_video",
        "recovery_state": "NONE",
        "fallback_in_use": False,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "error_message": None,
        # Story Multiplayer Engine graph fields
        "root_story_id": chain_id,
        "chain_depth": parent_chain_depth,
        "continuation_type": "original" if not parent_job_id else "episode",
        "total_children": 0,
        "total_views": 0,
        "total_shares": 0,
        "battle_score": 0.0,
        # Attribution
        "derivative_label": None,  # "continued_from" | "remixed_from" | "styled_from" | "converted_from"
        "source_story_id": parent_job_id,
        "source_story_title": None,
        "source_creator_id": None,
        "source_creator_name": None,
    }

    await db.story_engine_jobs.insert_one({k: v for k, v in job_doc.items() if k != "_id"})

    # Atomic credit deduction
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
                {"$set": {"state": JobState.FAILED.value, "error_message": str(e), "last_error_code": ErrorCode.INSUFFICIENT_CREDITS.value}},
            )
            return {"success": False, "error": str(e)}

    logger.info(f"[PIPELINE] Job {job_id[:8]} created for user {user_id[:12]}, deducted {credits_deducted} credits (guest={skip_credits})")

    # Check if job should be queued (slots busy) or run immediately
    queued = False
    if not skip_credits:
        queued = await should_queue_job(db, user_id)
        if queued:
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"state": "QUEUED", "queued_at": datetime.now(timezone.utc).isoformat()}}
            )
            logger.info(f"[PIPELINE] Job {job_id[:8]} QUEUED — render slots busy for user {user_id[:12]}")

    return {
        "success": True,
        "job_id": job_id,
        "state": "QUEUED" if queued else JobState.INIT.value,
        "queued": queued,
        "credits_deducted": credits_deducted,
        "cost_estimate": cost.model_dump(),
    }


# ═══════════════════════════════════════════════════════════════
# REUSE MODE — Continue/Remix Checkpoint Optimization
# ═══════════════════════════════════════════════════════════════

# Dependency graph: which fields each stage produces
STAGE_OUTPUTS = {
    "PLANNING": ["episode_plan"],
    "BUILDING_CHARACTER_CONTEXT": ["character_continuity"],
    "PLANNING_SCENE_MOTION": ["scene_motion_plans"],
    "GENERATING_KEYFRAMES": ["keyframe_urls", "keyframe_local_paths"],
    "GENERATING_SCENE_CLIPS": ["scene_clip_urls", "scene_clip_local_paths", "used_ken_burns_fallback", "sora_clips_count", "fallback_clips_count"],
    "GENERATING_AUDIO": ["narration_url", "narration_local_path", "narration_segments", "tts_failed"],
    "ASSEMBLING_VIDEO": ["output_url", "preview_url", "thumbnail_url", "thumbnail_small_url"],
}

# Which inputs invalidate which stages
# If any of these fields differ from parent, all listed stages must rerun
INVALIDATION_MAP = {
    "story_text": ["PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                    "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS", "GENERATING_AUDIO", "ASSEMBLING_VIDEO"],
    "style_id": ["GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS", "ASSEMBLING_VIDEO"],
    "voice_preset": ["GENERATING_AUDIO", "ASSEMBLING_VIDEO"],
    "age_group": ["PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                   "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS", "GENERATING_AUDIO", "ASSEMBLING_VIDEO"],
}


def analyze_reuse(parent_job: dict, new_params: dict) -> dict:
    """
    Analyze what can be reused from a parent job based on what changed.
    Returns {reuse_mode, reusable_stages, invalidated_stages, start_from, reusable_data}.
    """
    invalidated = set()

    # Check each parameter for changes
    for field, stages in INVALIDATION_MAP.items():
        parent_val = parent_job.get(field)
        new_val = new_params.get(field)
        if new_val is not None and parent_val != new_val:
            invalidated.update(stages)

    # Pipeline order for determining start point
    stage_order = [
        "PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
        "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS",
        "GENERATING_AUDIO", "ASSEMBLING_VIDEO",
    ]

    reusable = [s for s in stage_order if s not in invalidated]
    invalidated_ordered = [s for s in stage_order if s in invalidated]

    # Determine reuse mode
    if not invalidated_ordered:
        reuse_mode = "full_reuse"  # Nothing changed — shouldn't happen normally
    elif invalidated_ordered[0] == "PLANNING":
        reuse_mode = "continue"  # Story changed — rerun from planning
    elif invalidated_ordered[0] == "GENERATING_KEYFRAMES":
        reuse_mode = "style_remix"  # Only style changed
    elif invalidated_ordered[0] == "GENERATING_AUDIO":
        reuse_mode = "voice_remix"  # Only voice changed
    else:
        reuse_mode = "partial_remix"

    # Determine the first stage that needs to run
    start_from = invalidated_ordered[0] if invalidated_ordered else "ASSEMBLING_VIDEO"

    # Collect reusable data from parent
    reusable_data = {}
    for stage_name in reusable:
        for field_name in STAGE_OUTPUTS.get(stage_name, []):
            val = parent_job.get(field_name)
            if val is not None:
                reusable_data[field_name] = val

    # For continue mode, always carry forward character_continuity as base
    if reuse_mode == "continue" and parent_job.get("character_continuity"):
        reusable_data["_parent_character_continuity"] = parent_job["character_continuity"]

    return {
        "reuse_mode": reuse_mode,
        "reusable_stages": reusable,
        "invalidated_stages": invalidated_ordered,
        "start_from": start_from,
        "reusable_data": reusable_data,
    }


# State name → JobState enum mapping
_STATE_NAME_TO_ENUM = {
    "PLANNING": JobState.PLANNING,
    "BUILDING_CHARACTER_CONTEXT": JobState.BUILDING_CHARACTER_CONTEXT,
    "PLANNING_SCENE_MOTION": JobState.PLANNING_SCENE_MOTION,
    "GENERATING_KEYFRAMES": JobState.GENERATING_KEYFRAMES,
    "GENERATING_SCENE_CLIPS": JobState.GENERATING_SCENE_CLIPS,
    "GENERATING_AUDIO": JobState.GENERATING_AUDIO,
    "ASSEMBLING_VIDEO": JobState.ASSEMBLING_VIDEO,
}


async def apply_reuse_checkpoints(job_id: str, parent_job_id: str, new_params: dict) -> dict:
    """
    Analyze parent job, copy valid checkpoints, and advance job state to skip completed stages.
    Returns reuse analysis result.
    """
    parent_job = await db.story_engine_jobs.find_one({"job_id": parent_job_id}, {"_id": 0})
    if not parent_job:
        return {"reuse_mode": "fresh", "reusable_stages": [], "invalidated_stages": [], "start_from": "PLANNING"}

    # Only reuse from completed parent jobs
    if parent_job.get("state") not in ("READY", "PARTIAL_READY"):
        return {"reuse_mode": "fresh", "reusable_stages": [], "invalidated_stages": [], "start_from": "PLANNING"}

    analysis = analyze_reuse(parent_job, new_params)

    if analysis["reuse_mode"] == "fresh" or not analysis["reusable_data"]:
        return analysis

    # Copy reusable data to new job
    update_fields = {}
    for field, value in analysis["reusable_data"].items():
        if not field.startswith("_"):  # Skip internal markers
            update_fields[field] = value

    # Mark reuse metadata
    update_fields["reuse_info"] = {
        "parent_job_id": parent_job_id,
        "reuse_mode": analysis["reuse_mode"],
        "reused_stages": analysis["reusable_stages"],
        "invalidated_stages": analysis["invalidated_stages"],
        "start_from": analysis["start_from"],
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }

    # Also create synthetic stage_results for reused stages (for UI display)
    reused_stage_results = []
    for stage_name in analysis["reusable_stages"]:
        # Find the parent's result for this stage
        parent_result = None
        for sr in parent_job.get("stage_results", []):
            if sr.get("stage") == stage_name:
                parent_result = sr
                break

        reused_stage_results.append({
            "stage": stage_name,
            "status": "reused",
            "reused_from": parent_job_id,
            "original_duration_seconds": parent_result.get("duration_seconds") if parent_result else None,
            "duration_seconds": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    update_fields["stage_results"] = reused_stage_results

    # Advance job state to skip reused stages
    start_state = _STATE_NAME_TO_ENUM.get(analysis["start_from"], JobState.PLANNING)
    update_fields["state"] = start_state.value

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": update_fields},
    )

    logger.info(
        f"[REUSE] Job {job_id[:8]} reusing {len(analysis['reusable_stages'])} stages from "
        f"{parent_job_id[:8]}, starting from {analysis['start_from']} (mode={analysis['reuse_mode']})"
    )

    return analysis


# ═══════════════════════════════════════════════════════════════
# STAGE ORCHESTRATOR — Replaces monolithic run_pipeline()
# ═══════════════════════════════════════════════════════════════

# Map states to their stage execution functions
STAGE_FUNCTIONS = {}  # Populated after function definitions below


async def execute_pipeline(job_id: str) -> Dict:
    """
    Stage orchestrator loop. Processes stages one at a time until terminal.
    Each iteration is independently recoverable.
    """
    max_iterations = 20  # Safety cap against infinite loops

    for iteration in range(max_iterations):
        result = await process_next_stage(job_id)

        if result.get("terminal"):
            logger.info(f"[PIPELINE] Job {job_id[:8]} reached terminal state: {result.get('state')}")
            return result

        if not result.get("success"):
            logger.warning(f"[PIPELINE] Job {job_id[:8]} stage failed: {result.get('error')}")
            return result

        # Small pause between stages to prevent CPU monopolization
        await asyncio.sleep(0.1)

    # Safety: max iterations exceeded
    await _fail_job_terminal(job_id, ErrorCode.UNKNOWN_STAGE_FAILURE, "Max pipeline iterations exceeded")
    return {"success": False, "terminal": True, "error": "Max iterations exceeded"}


async def process_next_stage(job_id: str) -> Dict:
    """
    Process exactly ONE stage. Independently callable by orchestrator or recovery daemon.
    1. Loads persisted job state
    2. Determines which stage to execute
    3. Runs it with retry/heartbeat/budget
    4. Persists output
    5. Advances to next stage or handles failure
    """
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return {"success": False, "terminal": True, "error": "Job not found"}

    state = JobState(job["state"])

    # Already terminal — exit
    if state in TERMINAL_STATES:
        return {"success": state in SUCCESS_STATES, "terminal": True, "state": state.value}

    # INIT → advance to PLANNING
    if state == JobState.INIT:
        try:
            await transition_job(db, job_id, JobState.PLANNING)
        except ValueError as e:
            logger.error(f"[PIPELINE] Failed to transition {job_id[:8]} from INIT: {e}")
            return {"success": False, "terminal": True, "error": str(e)}
        state = JobState.PLANNING
        job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})

    # Validate state is an active stage
    if state not in STAGE_FUNCTIONS:
        await _fail_job_terminal(job_id, ErrorCode.UNKNOWN_STAGE_FAILURE, f"Unknown active state: {state.value}")
        return {"success": False, "terminal": True, "error": f"Unknown state: {state.value}"}

    # Update heartbeat at start of stage
    await update_heartbeat(db, job_id, f"Starting {state.value}")

    # ═══ REUSE CHECK — skip stages whose outputs already exist from checkpoint copy ═══
    reuse_info = job.get("reuse_info")
    if reuse_info and state.value in (reuse_info.get("reused_stages") or []):
        logger.info(f"[REUSE] Skipping {state.value} for {job_id[:8]} — outputs reused from {reuse_info['parent_job_id'][:8]}")
        # Advance to next stage without executing
        if state == JobState.VALIDATING:
            return await _finalize_job(job_id)
        next_state = get_next_stage(state)
        if next_state:
            try:
                await transition_job(db, job_id, next_state)
            except ValueError as e:
                logger.error(f"[PIPELINE] Failed to skip-advance {job_id[:8]}: {e}")
                return {"success": False, "terminal": True, "error": str(e)}
        return {"success": True, "terminal": False, "state": (next_state or state).value}

    # Budget guard — enforce before every external call
    try:
        enforce_runtime_budget(job, state.value)
    except BudgetExceededError as e:
        failure_state = get_failure_state(state)
        await transition_job(db, job_id, failure_state, error=str(e), error_code=ErrorCode.BUDGET_EXCEEDED_RUNTIME.value)
        await _refund_credits(job_id)
        return {"success": False, "terminal": True, "state": failure_state.value, "error": str(e)}

    # Execute the stage with retry logic
    stage_fn = STAGE_FUNCTIONS[state]
    result = await _execute_stage_with_retry(job_id, state, stage_fn, job)

    if result["success"]:
        # Stage succeeded — advance
        if state == JobState.VALIDATING:
            # Final stage — determine READY or PARTIAL_READY
            return await _finalize_job(job_id)

        next_state = get_next_stage(state)
        if next_state:
            try:
                await transition_job(db, job_id, next_state)
            except ValueError as e:
                logger.error(f"[PIPELINE] Failed to advance {job_id[:8]}: {e}")
                return {"success": False, "terminal": True, "error": str(e)}
        return {"success": True, "terminal": False, "state": (next_state or state).value}
    else:
        # Stage failed after retries — already transitioned to failure state
        return result


async def _execute_stage_with_retry(job_id: str, stage: JobState, stage_fn, job: dict) -> Dict:
    """
    Execute a stage with retry logic. On exhaustion, transitions to per-stage failure.
    For PLANNING, uses the multi-level fallback chain.
    """
    max_retries = STAGE_MAX_RETRIES.get(stage, 2)
    current_retry = get_stage_retry_count(job, stage.value)
    last_error = None

    # For planning stage, we have a 4-level fallback chain handled inside planning_llm
    attempts_remaining = max(1, max_retries - current_retry)

    for attempt in range(attempts_remaining):
        attempt_num = current_retry + attempt + 1

        # Update heartbeat with attempt info
        detail = f"Executing {stage.value} (attempt {attempt_num}/{max_retries})"
        await update_heartbeat(db, job_id, detail)

        # Update UI-visible retry info
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "current_attempt": attempt_num,
                "max_stage_attempts": max_retries,
                "heartbeat_detail": detail,
            }},
        )

        started = datetime.now(timezone.utc)
        try:
            result = await stage_fn(job)

            if result.get("status") == "success":
                # Record stage result
                completed = datetime.now(timezone.utc)
                stage_result = {
                    "stage": stage.value,
                    "status": "success",
                    "started_at": started.isoformat(),
                    "completed_at": completed.isoformat(),
                    "duration_seconds": round((completed - started).total_seconds(), 2),
                    "attempt_number": attempt_num,
                    "model_used": result.get("model_used"),
                    "output": result.get("output", {}),
                }
                await db.story_engine_jobs.update_one(
                    {"job_id": job_id},
                    {
                        "$push": {"stage_results": stage_result},
                        "$set": {"updated_at": completed.isoformat()},
                    },
                )
                return {"success": True}
            else:
                last_error = result.get("error", "Stage returned non-success")
                error_code = result.get("error_code", ErrorCode.UNKNOWN_STAGE_FAILURE.value)
                logger.warning(f"[PIPELINE] Stage {stage.value} attempt {attempt_num} failed: {last_error}")

        except BudgetExceededError as e:
            last_error = str(e)
            error_code = ErrorCode.BUDGET_EXCEEDED_RUNTIME.value
            break  # No point retrying budget errors

        except Exception as e:
            last_error = str(e)
            error_code = ErrorCode.WORKER_CRASH.value
            logger.error(f"[PIPELINE] Stage {stage.value} attempt {attempt_num} crashed: {e}")

        # Record failed attempt
        await increment_stage_retry(db, job_id, stage.value)

        # Backoff before retry
        if attempt < attempts_remaining - 1:
            backoff = min(2 ** attempt * 2, 30)
            logger.info(f"[PIPELINE] Backing off {backoff}s before retry...")
            await asyncio.sleep(backoff)

            # Re-load job for latest state
            job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
            if not job or JobState(job["state"]) in TERMINAL_STATES:
                return {"success": False, "terminal": True, "error": "Job cancelled during retry"}

    # All retries exhausted — transition to per-stage failure
    failure_state = get_failure_state(stage)
    error_msg = f"{stage.value} failed after {max_retries} attempts: {last_error}"

    try:
        await transition_job(db, job_id, failure_state, error=error_msg, error_code=error_code)
    except ValueError:
        # Fallback: force-set failure state
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "state": failure_state.value,
                "error_message": error_msg,
                "last_error_code": error_code,
                "last_error_stage": stage.value,
            }},
        )

    # Refund credits on terminal failure
    await _refund_credits(job_id)

    return {
        "success": False,
        "terminal": True,
        "state": failure_state.value,
        "error": error_msg,
        "error_code": error_code,
    }


async def _finalize_job(job_id: str) -> Dict:
    """Final validation — determine READY or PARTIAL_READY. Create notification."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return {"success": False, "terminal": True, "error": "Job not found"}

    validation = validate_pipeline_outputs(job)
    final_state = should_mark_ready(validation)
    target = JobState(final_state)

    try:
        await transition_job(db, job_id, target)
    except ValueError:
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"state": target.value}},
        )

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"validation_result": validation.to_dict()}},
    )

    # Clear recovery state on completion
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"recovery_state": "NONE", "fallback_in_use": False}},
    )

    # Register completed episode into story_episodes if this is a series-linked job
    if target in SUCCESS_STATES and job.get("series_id"):
        await _register_series_episode(job)

    # Create notification if user opted in
    await _send_completion_notification(job_id, target)

    logger.info(f"[PIPELINE] Job {job_id[:8]} finalized: {final_state}")

    # ═══ PREVIEW GENERATION: Generate poster + 2s preview for feed cards ═══
    if target in SUCCESS_STATES and job.get("output_url"):
        try:
            from services.media_preview_pipeline import generate_preview_derivatives
            asyncio.create_task(generate_preview_derivatives(job_id, job["output_url"], db))
            logger.info(f"[PIPELINE] Preview generation queued for {job_id[:8]}")
        except Exception as prev_err:
            logger.warning(f"[PIPELINE] Preview generation failed to queue: {prev_err}")

    # ═══ RANK NOTIFICATIONS: Check rank changes when a new entry completes ═══
    if target in SUCCESS_STATES and job.get("continuation_type") == "branch" and job.get("parent_job_id"):
        try:
            from routes.story_multiplayer import check_and_send_rank_notifications, refresh_battle_score
            await refresh_battle_score(job_id)
            await check_and_send_rank_notifications(job_id, job["parent_job_id"])
        except Exception as rank_err:
            logger.warning(f"[PIPELINE] Rank notification check failed: {rank_err}")

    # ═══ QUEUE DRAIN: If this user has queued jobs, start the next one ═══
    try:
        user_id = job.get("user_id")
        if user_id:
            await _drain_queue_for_user(user_id)
    except Exception as e:
        logger.warning(f"[PIPELINE] Queue drain failed: {e}")

    return {"success": target in SUCCESS_STATES, "terminal": True, "state": final_state}


async def _register_series_episode(job: dict):
    """
    Register or update a story_episodes record when a series-linked job completes.

    - Upserts on (series_id, episode_number) to avoid duplicates.
    - Only called for successful jobs (READY / PARTIAL_READY).
    - Persists enough metadata for SeriesTimeline to recover episode state
      without relying on temporary navigation state.
    """
    series_id = job.get("series_id")
    episode_number = job.get("episode_number")
    job_id = job.get("job_id")

    if not series_id or episode_number is None:
        return

    now = datetime.now(timezone.utc).isoformat()

    # Build the episode record from the completed job
    episode_data = {
        "job_id": job_id,
        "status": "ready",
        "title": job.get("title", f"Episode {episode_number}"),
        "output_asset_url": job.get("output_url"),
        "thumbnail_url": job.get("thumbnail_url"),
        "output_type": "video",
        "tool_used": "story_video",
        "scene_count": len(job.get("keyframe_urls", [])),
        "user_id": job.get("user_id"),
        "character_ids": job.get("character_ids", []),
        "cliffhanger": job.get("cliffhanger", ""),
        "cliffhanger_text": job.get("cliffhanger", ""),
        "summary": job.get("story_text", "")[:500] if job.get("story_text") else "",
        "updated_at": now,
    }

    # Try to find existing episode for this series + episode number
    existing = await db.story_episodes.find_one(
        {"series_id": series_id, "episode_number": episode_number},
        {"_id": 0, "episode_id": 1},
    )

    if existing:
        # Update the existing record (e.g., re-generation of same episode)
        await db.story_episodes.update_one(
            {"series_id": series_id, "episode_number": episode_number},
            {"$set": episode_data},
        )
        logger.info(
            f"[SERIES] Updated episode {episode_number} for series {series_id[:8]} "
            f"with job {job_id[:8]}"
        )
    else:
        # Create a new episode record
        episode_id = str(uuid.uuid4())
        new_episode = {
            "episode_id": episode_id,
            "series_id": series_id,
            "parent_episode_id": None,
            "branch_type": "mainline",
            "episode_number": episode_number,
            "story_prompt": job.get("story_text", ""),
            "episode_goal": "",
            "plan": {},
            "view_count": 0,
            "remix_count": 0,
            "share_count": 0,
            "created_at": now,
            **episode_data,
        }
        await db.story_episodes.insert_one(new_episode)
        logger.info(
            f"[SERIES] Registered new episode {episode_number} (id={episode_id[:8]}) "
            f"for series {series_id[:8]} with job {job_id[:8]}"
        )

    # Update the series episode_count
    total = await db.story_episodes.count_documents({"series_id": series_id})
    await db.story_series.update_one(
        {"series_id": series_id},
        {"$set": {"episode_count": total, "updated_at": now}},
    )


# ═══════════════════════════════════════════════════════════════
# INDIVIDUAL STAGE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def _stage_planning(job: dict) -> Dict:
    """Generate structured episode plan with multi-level fallback."""
    previous_plan = None
    if job.get("parent_job_id"):
        parent = await db.story_engine_jobs.find_one(
            {"job_id": job["parent_job_id"]},
            {"_id": 0, "episode_plan": 1},
        )
        if parent:
            previous_plan = parent.get("episode_plan")

    job_id = job["job_id"]
    retry_count = get_stage_retry_count(job, "PLANNING")

    # Multi-level fallback: attempt level increases with retries
    quality_config = job.get("quality_config") or {}
    max_scenes = quality_config.get("max_scenes", 5)

    plan, model_used = await planning_llm.generate_episode_plan_with_fallback(
        story_text=job["story_text"],
        style_id=job.get("style_id", "cartoon_2d"),
        episode_number=job.get("episode_number", 1),
        previous_plan=previous_plan,
        attempt_level=retry_count,
        max_scenes=max_scenes,
    )

    if not plan:
        return {
            "status": "failed",
            "error": "All scene generation strategies failed",
            "error_code": ErrorCode.SCENE_GENERATION_FAILED.value,
        }

    # Validate scene count
    scenes = plan.get("scene_breakdown", [])
    if not scenes:
        return {
            "status": "failed",
            "error": "Plan has zero scenes",
            "error_code": ErrorCode.MODEL_INVALID_RESPONSE.value,
        }

    if len(scenes) > 8:
        plan["scene_breakdown"] = scenes[:8]

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "episode_plan": plan,
            "title": plan.get("title", job.get("title", "Untitled")),
        }},
    )

    # Non-blocking hook generation
    await _stage_hooks_safe(job)

    return {
        "status": "success",
        "model_used": model_used,
        "output": {"title": plan.get("title"), "scenes": len(plan.get("scene_breakdown", []))},
    }


async def _stage_hooks_safe(job: dict) -> None:
    """Generate hooks — non-blocking, non-fatal."""
    try:
        from services.hook_service import generate_hook_variants
        job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
        story_text = job.get("story_text", "")
        title = job.get("episode_plan", {}).get("title") or job.get("title", "Untitled")

        hooks = await generate_hook_variants(
            story_prompt=story_text, title=title,
            style_id=job.get("style_id", "default"),
            age_group=job.get("age_group", ""), n=3,
        )
        hook_text = hooks[0]["text"] if hooks else None
        await db.story_engine_jobs.update_one(
            {"job_id": job["job_id"]},
            {"$set": {"hooks": hooks, "hook_text": hook_text, "winning_hook": None, "hook_locked": False}},
        )
    except Exception as e:
        logger.warning(f"[PIPELINE] Hook generation failed (non-blocking): {e}")


async def _stage_character_context(job: dict) -> Dict:
    """Build character continuity package.
    
    RESILIENCE: Character continuity is best-effort, NOT a hard dependency.
    If the LLM call fails, we build a basic fallback from the episode plan
    and continue the pipeline. Videos still generate — just with simpler
    per-scene character descriptions instead of cross-scene consistency.
    """
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    if not job.get("episode_plan"):
        return {"status": "failed", "error": "No episode plan", "error_code": ErrorCode.SCENE_GENERATION_FAILED.value}

    existing = None
    if job.get("parent_job_id"):
        parent = await db.story_engine_jobs.find_one(
            {"job_id": job["parent_job_id"]}, {"_id": 0, "character_continuity": 1},
        )
        if parent:
            existing = parent.get("character_continuity")

    await update_heartbeat(db, job["job_id"], "Generating character continuity")

    continuity = await planning_llm.generate_character_continuity(
        episode_plan=job["episode_plan"],
        existing_package=existing,
        style_id=job.get("style_id", "cartoon_2d"),
    )

    used_fallback = False
    if not continuity:
        # ── FALLBACK: Build basic continuity from episode plan ──
        # Instead of failing the entire pipeline, extract character names
        # from the episode plan and create minimal descriptions.
        logger.warning(f"[PIPELINE] Character continuity LLM failed for {job['job_id'][:8]} — using best-effort fallback")
        continuity = _build_fallback_continuity(job["episode_plan"])
        used_fallback = True

    continuity["universe_id"] = job.get("story_chain_id", job["job_id"])
    continuity["story_chain_id"] = job.get("story_chain_id", job["job_id"])
    continuity["locked_at"] = datetime.now(timezone.utc).isoformat()
    if used_fallback:
        continuity["_fallback"] = True

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"character_continuity": continuity}},
    )

    return {
        "status": "success",
        "output": {
            "characters": len(continuity.get("characters", [])),
            "used_fallback": used_fallback,
        },
    }


def _build_fallback_continuity(episode_plan: dict) -> dict:
    """Build a minimal character continuity package from the episode plan.
    
    Extracts character names from scenes and creates generic descriptions
    so downstream stages (keyframes, scene clips) can still reference them.
    This produces less consistent visuals but the video still generates.
    """
    characters = []
    seen_names = set()

    # Try to extract characters from scenes in the episode plan
    scenes = episode_plan.get("scenes", [])
    for scene in scenes:
        for char_name in scene.get("characters", []):
            name = char_name.strip() if isinstance(char_name, str) else str(char_name)
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                characters.append({
                    "name": name,
                    "description": f"A character named {name}",
                    "visual_tags": [],
                    "color_palette": [],
                })

    # If no characters found in scenes, check top-level plan
    if not characters:
        for key in ("characters", "cast", "main_characters"):
            raw = episode_plan.get(key, [])
            if isinstance(raw, list):
                for item in raw:
                    name = item if isinstance(item, str) else (item.get("name", "") if isinstance(item, dict) else "")
                    name = name.strip()
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        desc = item.get("description", f"A character named {name}") if isinstance(item, dict) else f"A character named {name}"
                        characters.append({
                            "name": name,
                            "description": desc,
                            "visual_tags": [],
                            "color_palette": [],
                        })

    return {
        "characters": characters,
        "style_notes": "",
        "consistency_level": "basic",
    }


async def _stage_scene_motion(job: dict) -> Dict:
    """Generate per-scene motion plans."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})

    await update_heartbeat(db, job["job_id"], "Planning scene motion")

    plans = await planning_llm.generate_scene_motion_plans(
        episode_plan=job["episode_plan"],
        continuity=job.get("character_continuity", {}),
        style_id=job.get("style_id", "cartoon_2d"),
    )

    if not plans:
        return {"status": "failed", "error": "Failed to generate scene motion plans", "error_code": ErrorCode.MODEL_INVALID_RESPONSE.value}

    await db.story_engine_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$set": {"scene_motion_plans": plans}},
    )

    return {"status": "success", "output": {"scenes_planned": len(plans)}}


async def _stage_keyframes(job: dict) -> Dict:
    """Generate keyframes using GPT Image 1."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    plans = job.get("scene_motion_plans", [])
    continuity = job.get("character_continuity", {})
    job_id = job["job_id"]

    keyframe_urls = []
    keyframe_local_paths = []
    for i, plan in enumerate(plans):
        await update_heartbeat(db, job_id, f"Generating keyframe {i+1}/{len(plans)}")

        result = await video_gen.generate_keyframe(
            scene_plan=plan, continuity=continuity,
            style_id=job.get("style_id", "cartoon_2d"), job_id=job_id,
        )
        keyframe_urls.append(result.get("url"))
        keyframe_local_paths.append(result.get("local_path"))

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"keyframe_urls": keyframe_urls, "keyframe_local_paths": keyframe_local_paths}},
    )

    generated = sum(1 for u in keyframe_urls if u)
    if generated == 0:
        return {"status": "failed", "error": "No keyframes generated", "error_code": ErrorCode.IMAGE_GENERATION_FAILED.value}

    return {"status": "success", "output": {"keyframes_generated": generated, "total": len(plans)}}


async def _stage_scene_clips(job: dict) -> Dict:
    """Generate scene clips using Sora 2 with Ken Burns fallback."""
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
        await update_heartbeat(db, job_id, f"Generating clip {i+1}/{len(plans)}")

        kf_url = keyframes[i] if i < len(keyframes) else None
        kf_path = keyframe_paths[i] if i < len(keyframe_paths) else None

        result = await video_gen.generate_scene_clip(
            scene_plan=plan, keyframe_url=kf_url, keyframe_local_path=kf_path,
            continuity=continuity, style_id=job.get("style_id", "cartoon_2d"), job_id=job_id,
        )

        if result.get("status") == "ready" and result.get("local_path"):
            clip_urls.append(result.get("url"))
            clip_local_paths.append(result.get("local_path"))
            sora_count += 1
        elif kf_path and os.path.exists(kf_path):
            logger.warning(f"[PIPELINE] Sora failed for scene {i+1}, falling back to Ken Burns")
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

    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "scene_clip_urls": clip_urls,
            "scene_clip_local_paths": clip_local_paths,
            "used_ken_burns_fallback": fallback_count > 0,
            "sora_clips_count": sora_count,
            "fallback_clips_count": fallback_count,
        }},
    )

    generated = sum(1 for u in clip_urls if u)
    return {
        "status": "success",
        "output": {"clips_generated": generated, "sora_clips": sora_count, "fallback_clips": fallback_count, "total": len(plans)},
    }


async def _stage_audio(job: dict) -> Dict:
    """Generate narration audio. Non-fatal — proceeds without narration on failure."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})

    await update_heartbeat(db, job["job_id"], "Generating narration audio")

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

    # Audio failure is non-fatal
    if tts_failed:
        logger.warning("[PIPELINE] TTS failed, proceeding without narration")
    return {"status": "success", "output": result}


async def _stage_assembly(job: dict) -> Dict:
    """FFmpeg assembly — stitch clips, mix audio, generate preview/thumbnail.
    Includes fallback rendering for resilience."""
    job = await db.story_engine_jobs.find_one({"job_id": job["job_id"]}, {"_id": 0})
    job_id = job["job_id"]
    clip_paths = [p for p in job.get("scene_clip_local_paths", []) if p and os.path.exists(p)]
    narration_path = job.get("narration_local_path")

    if not clip_paths:
        return {"status": "success", "output": {"note": "No local clips available for assembly yet"}}

    # Mark recovery state for UI truthfulness
    is_retry = job.get("retry_count", 0) > 0
    if is_retry:
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"recovery_state": "AUTO_RECOVERING"}}
        )

    await update_heartbeat(db, job_id, "Stitching video clips")

    output_dir = Path("/app/backend/static/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stitch clips — with fallback to simple concat if transitions fail
    stitched_path = str(output_dir / f"se_{job_id[:8]}_stitched.mp4")
    plans = job.get("scene_motion_plans", [])
    transitions = [p.get("transition_type", "crossfade") for p in plans[1:]] if plans else []

    stitch_ok = await ffmpeg_assembly.stitch_clips(clip_paths, stitched_path, transitions=transitions)
    if not stitch_ok:
        # FALLBACK: Try simple concatenation without transitions
        logger.warning(f"[ASSEMBLY FALLBACK] Fancy stitch failed for {job_id[:8]}, trying simple concat")
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"fallback_in_use": True, "recovery_state": "AUTO_RECOVERING"}}
        )
        await update_heartbeat(db, job_id, "Using fallback rendering")
        stitch_ok = await ffmpeg_assembly.stitch_clips(clip_paths, stitched_path, transitions=[])
        if not stitch_ok:
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"recovery_state": "NONE"}}
            )
            return {"status": "failed", "error": "FFmpeg stitch failed", "error_code": ErrorCode.RENDER_FAILED.value}

    await update_heartbeat(db, job_id, "Mixing audio")

    # Mix audio
    final_path = stitched_path
    if narration_path and os.path.exists(narration_path):
        mixed_path = str(output_dir / f"se_{job_id[:8]}_mixed.mp4")
        mix_ok = await ffmpeg_assembly.mix_audio(stitched_path, narration_path, None, mixed_path)
        if mix_ok:
            final_path = mixed_path

    # Addiction triggers
    episode_plan = job.get("episode_plan", {})
    trigger_text = episode_plan.get("trigger_text")
    cliffhanger_text = episode_plan.get("cliffhanger")
    triggered_path = str(output_dir / f"se_{job_id[:8]}_triggered.mp4")
    trigger_ok = await ffmpeg_assembly.apply_addiction_triggers(
        final_path, triggered_path,
        trigger_text=trigger_text, cliffhanger_text=cliffhanger_text,
    )
    if trigger_ok and os.path.exists(triggered_path):
        final_path = triggered_path

    # Watermark end screen
    await update_heartbeat(db, job_id, "Adding brand watermark")
    watermarked_path = str(output_dir / f"se_{job_id[:8]}_watermarked.mp4")
    wm_ok = await ffmpeg_assembly.add_watermark_endscreen(final_path, watermarked_path)
    if wm_ok and os.path.exists(watermarked_path):
        final_path = watermarked_path

    await update_heartbeat(db, job_id, "Generating preview and thumbnails")

    # Preview
    preview_path = str(output_dir / f"se_{job_id[:8]}_preview.mp4")
    await ffmpeg_assembly.generate_preview(final_path, preview_path)

    # Media assets
    from services.story_engine.adapters.media_gen import generate_media_assets
    fallback_kf = None
    for kp in job.get("keyframe_local_paths", []):
        if kp and os.path.exists(kp):
            fallback_kf = kp
            break

    thumb_url, poster_url, thumb_blur = await generate_media_assets(
        video_path=final_path, job_id=job_id, fallback_image_path=fallback_kf,
    )

    await update_heartbeat(db, job_id, "Uploading to storage")

    # Upload to R2
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

    update_fields = {
        "output_url": output_url,
        "preview_url": preview_url,
        "thumbnail_url": poster_url,
        "thumbnail_small_url": thumb_url,
    }
    if thumb_url:
        update_fields["media.thumbnail_small.url"] = thumb_url
        update_fields["media.thumbnail_small.type"] = "image/jpeg"
    if poster_url:
        update_fields["media.poster_large.url"] = poster_url
        update_fields["media.poster_large.type"] = "image/jpeg"
    if thumb_blur:
        update_fields["media.thumb_blur"] = thumb_blur

    await db.story_engine_jobs.update_one({"job_id": job_id}, {"$set": update_fields})

    return {
        "status": "success",
        "output": {
            "output_url": output_url, "preview_url": preview_url,
            "clips_stitched": len(clip_paths), "has_narration": bool(narration_path),
        },
    }


async def _stage_validation(job: dict) -> Dict:
    """Validate outputs — determines READY vs PARTIAL_READY."""
    # Validation is handled in _finalize_job, this just passes through
    return {"status": "success", "output": {"note": "Validation delegated to finalize"}}


# Register stage functions
STAGE_FUNCTIONS = {
    JobState.PLANNING: _stage_planning,
    JobState.BUILDING_CHARACTER_CONTEXT: _stage_character_context,
    JobState.PLANNING_SCENE_MOTION: _stage_scene_motion,
    JobState.GENERATING_KEYFRAMES: _stage_keyframes,
    JobState.GENERATING_SCENE_CLIPS: _stage_scene_clips,
    JobState.GENERATING_AUDIO: _stage_audio,
    JobState.ASSEMBLING_VIDEO: _stage_assembly,
    JobState.VALIDATING: _stage_validation,
}


# ═══════════════════════════════════════════════════════════════
# CREDIT REFUND — Centralized, idempotent
# ═══════════════════════════════════════════════════════════════

async def _refund_credits(job_id: str) -> None:
    """
    Idempotent credit refund. Checks if already refunded before processing.
    Called on any terminal failure.
    """
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return

    # Skip if already refunded or no cost estimate
    if job.get("credits_refunded", 0) > 0:
        logger.info(f"[REFUND] Job {job_id[:8]} already refunded, skipping")
        return

    cost_estimate = job.get("cost_estimate", {})
    refund_amount = cost_estimate.get("total_credits_required", 0)
    if refund_amount <= 0:
        return

    # Skip guest jobs
    if job.get("is_guest") or job.get("user_id", "").startswith("guest_"):
        return

    try:
        from services.credits_service import get_credits_service
        svc = get_credits_service(db)

        # Atomic: set credits_refunded BEFORE actually refunding to prevent double-refund
        result = await db.story_engine_jobs.update_one(
            {"job_id": job_id, "credits_refunded": 0},  # Only if not yet refunded
            {"$set": {"credits_refunded": refund_amount}},
        )
        if result.modified_count == 0:
            logger.info(f"[REFUND] Job {job_id[:8]} concurrent refund prevented")
            return

        await svc.refund_credits(
            job["user_id"], refund_amount,
            reason=f"Pipeline failure: {job.get('error_message', 'Unknown')[:100]}",
            reference_id=job_id,
        )
        logger.info(f"[REFUND] Refunded {refund_amount} credits for job {job_id[:8]}")

    except Exception as e:
        logger.error(f"[REFUND] Failed to refund job {job_id[:8]}: {e}")
        # Rollback the flag so retry can attempt again
        await db.story_engine_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"credits_refunded": 0}},
        )


async def _fail_job_terminal(job_id: str, error_code: ErrorCode, error_msg: str) -> None:
    """Force a job into terminal FAILED state, refund, notify, and drain queue."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0, "user_id": 1})
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "state": JobState.FAILED.value,
            "error_message": error_msg,
            "last_error_code": error_code.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    await _refund_credits(job_id)
    await _send_completion_notification(job_id, JobState.FAILED)

    # ═══ QUEUE DRAIN on failure — slot freed, promote next queued job ═══
    try:
        user_id = job.get("user_id") if job else None
        if user_id:
            await _drain_queue_for_user(user_id)
    except Exception as e:
        logger.warning(f"[PIPELINE] Queue drain after failure failed: {e}")


async def _drain_queue_for_user(user_id: str):
    """Promote the oldest QUEUED job for this user if a slot is now free."""
    needs_queue = await should_queue_job(db, user_id)
    if needs_queue:
        return  # Still no free slots

    queued_job = await db.story_engine_jobs.find_one(
        {"user_id": user_id, "state": "QUEUED"},
        {"_id": 0, "job_id": 1},
        sort=[("created_at", 1)],  # FIFO
    )
    if queued_job:
        qjid = queued_job["job_id"]
        result = await db.story_engine_jobs.update_one(
            {"job_id": qjid, "state": "QUEUED"},
            {"$set": {
                "state": JobState.INIT.value,
                "promoted_from_queue_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
        if result.modified_count > 0:
            import asyncio
            asyncio.create_task(run_pipeline(qjid))
            logger.info(f"[PIPELINE] Promoted queued job {qjid[:8]} for user {user_id[:12]}")


async def _send_completion_notification(job_id: str, final_state: JobState) -> None:
    """Send in-app notification on job terminal state."""
    try:
        job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            return

        user_id = job.get("user_id", "")
        is_failure = final_state in (JobState.FAILED, JobState.FAILED_PLANNING, JobState.FAILED_IMAGES, JobState.FAILED_TTS, JobState.FAILED_RENDER)
        opted_in = job.get("notification_opt_in", False)

        # Always notify on failure, otherwise only if opted in
        if not opted_in and not is_failure:
            return

        from services.notification_service import get_notification_service
        svc = get_notification_service(db)

        if is_failure:
            await svc.notify_generation_failed(
                user_id=user_id,
                job_id=job_id,
                title=job.get("title", "Untitled"),
                error=job.get("error_message", "Generation failed"),
            )
        else:
            await svc.notify_generation_complete(
                user_id=user_id,
                job_id=job_id,
                title=job.get("title", "Untitled"),
            )
    except Exception as e:
        logger.warning(f"[NOTIFY] Failed to send notification for job {job_id[:8]}: {e}")


# ═══════════════════════════════════════════════════════════════
# JOB STATUS — For frontend polling
# ═══════════════════════════════════════════════════════════════

async def get_job_status(job_id: str) -> Optional[Dict]:
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        return None

    state = JobState(job["state"])
    episode_plan = job.get("episode_plan", {})

    # Build honest status label
    label = get_label(state)
    attempt = job.get("current_attempt", 0)
    max_attempts = job.get("max_stage_attempts", 0)
    heartbeat_detail = job.get("heartbeat_detail", "")

    # Honest retry info for UI
    retry_info = None
    if attempt > 1 and state in {JobState.PLANNING, JobState.BUILDING_CHARACTER_CONTEXT,
                                   JobState.PLANNING_SCENE_MOTION, JobState.GENERATING_KEYFRAMES,
                                   JobState.GENERATING_SCENE_CLIPS, JobState.GENERATING_AUDIO,
                                   JobState.ASSEMBLING_VIDEO}:
        retry_info = f"Retrying ({attempt}/{max_attempts})"

    # Can this job be retried?
    can_retry = state in PER_STAGE_FAILURE_STATES

    # Queue position (if queued)
    queue_position = None
    if state.value == "QUEUED":
        user_id = job.get("user_id")
        if user_id:
            # Count how many QUEUED jobs are ahead (older created_at)
            ahead = await db.story_engine_jobs.count_documents({
                "user_id": user_id,
                "state": "QUEUED",
                "created_at": {"$lt": job.get("created_at", "")},
            })
            queue_position = ahead + 1  # 1-indexed

    return {
        "job_id": job["job_id"],
        "state": state.value,
        "progress_percent": get_progress(state),
        "current_stage": "Queued for rendering" if state.value == "QUEUED" else label,
        "heartbeat_detail": heartbeat_detail,
        "retry_info": retry_info,
        "can_retry": can_retry,
        "queue_position": queue_position,
        "title": job.get("title"),
        "episode_number": job.get("episode_number"),
        "stage_results": job.get("stage_results", []),
        "output_url": job.get("output_url"),
        "preview_url": job.get("preview_url"),
        "thumbnail_url": job.get("thumbnail_url"),
        "error_message": job.get("error_message"),
        "error_code": job.get("last_error_code"),
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


# Keep backward compat alias
async def run_pipeline(job_id: str) -> Dict:
    """Backward-compatible entry point. Delegates to execute_pipeline."""
    return await execute_pipeline(job_id)
