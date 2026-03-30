"""
Recovery Daemon — Watchdog for stuck jobs.

Runs every 2 minutes. Detects stale heartbeats and either:
- Requeues the current stage for retry
- Marks terminal failure + refund if max retries exceeded
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta

from .schemas import JobState, ErrorCode, ACTIVE_STATES
from .state_machine import (
    HEARTBEAT_THRESHOLDS, STAGE_MAX_RETRIES, STAGE_TO_FAILURE,
    get_stage_retry_count, increment_stage_retry,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared import db

logger = logging.getLogger("story_engine.recovery")

DAEMON_INTERVAL_SECONDS = 120  # 2 minutes
_daemon_running = False


async def start_recovery_daemon():
    """Start the background recovery daemon. Safe to call multiple times."""
    global _daemon_running
    if _daemon_running:
        logger.info("[RECOVERY] Daemon already running, skipping")
        return
    _daemon_running = True
    logger.info("[RECOVERY] Starting recovery daemon (interval=%ds)", DAEMON_INTERVAL_SECONDS)
    asyncio.create_task(_daemon_loop())


async def _daemon_loop():
    """Main daemon loop — runs every DAEMON_INTERVAL_SECONDS."""
    global _daemon_running
    while _daemon_running:
        try:
            await _recover_stale_jobs()
        except Exception as e:
            logger.error(f"[RECOVERY] Daemon error: {e}")
        await asyncio.sleep(DAEMON_INTERVAL_SECONDS)


async def _recover_stale_jobs():
    """Find and recover jobs with stale heartbeats."""
    now = datetime.now(timezone.utc)
    recovered = 0
    failed = 0

    # Find all jobs in active states
    active_state_values = [s.value for s in ACTIVE_STATES]
    cursor = db.story_engine_jobs.find(
        {"state": {"$in": active_state_values}},
        {"_id": 0, "job_id": 1, "state": 1, "last_heartbeat_at": 1,
         "stage_retry_counts": 1, "retry_count": 1, "user_id": 1,
         "cost_estimate": 1, "credits_refunded": 1, "created_at": 1},
    )

    async for job in cursor:
        job_id = job["job_id"]
        state = job["state"]
        heartbeat_str = job.get("last_heartbeat_at")

        if not heartbeat_str:
            # No heartbeat ever set — use created_at
            heartbeat_str = job.get("created_at")

        if not heartbeat_str:
            continue

        try:
            heartbeat_time = datetime.fromisoformat(heartbeat_str.replace("Z", "+00:00"))
            if heartbeat_time.tzinfo is None:
                heartbeat_time = heartbeat_time.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue

        # Get threshold for this stage
        threshold_seconds = HEARTBEAT_THRESHOLDS.get(state, 300)
        stale_threshold = now - timedelta(seconds=threshold_seconds)

        if heartbeat_time > stale_threshold:
            continue  # Not stale

        # Job is stale
        seconds_stale = (now - heartbeat_time).total_seconds()
        logger.warning(
            f"[RECOVERY] Stale job detected: {job_id[:8]} in state {state}, "
            f"heartbeat {seconds_stale:.0f}s ago (threshold: {threshold_seconds}s)"
        )

        # Check retry count for this stage
        stage_retries = get_stage_retry_count(job, state)
        max_retries = STAGE_MAX_RETRIES.get(JobState(state), 2)

        if stage_retries >= max_retries:
            # Max retries exceeded — terminal failure
            logger.error(f"[RECOVERY] Job {job_id[:8]} max retries exceeded for {state}, marking failed")
            failure_state = STAGE_TO_FAILURE.get(JobState(state), JobState.FAILED)
            error_msg = f"Job stuck at {state} — heartbeat expired after {max_retries} retries"

            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "state": failure_state.value,
                    "error_message": error_msg,
                    "last_error_code": ErrorCode.JOB_HEARTBEAT_EXPIRED.value,
                    "last_error_stage": state,
                    "updated_at": now.isoformat(),
                }},
            )

            # Refund credits
            from .pipeline import _refund_credits
            await _refund_credits(job_id)
            failed += 1
        else:
            # Requeue — increment retry and reset heartbeat so the job can be picked up
            logger.info(f"[RECOVERY] Requeuing job {job_id[:8]} at stage {state} (retry {stage_retries + 1}/{max_retries})")

            await increment_stage_retry(db, job_id, state)
            await db.story_engine_jobs.update_one(
                {"job_id": job_id},
                {"$set": {
                    "last_heartbeat_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "heartbeat_detail": f"Recovered by daemon — retrying {state} (attempt {stage_retries + 2}/{max_retries})",
                }},
            )

            # Re-run the pipeline from current stage in background
            from .pipeline import process_next_stage
            asyncio.create_task(_safe_retry(job_id))
            recovered += 1

    if recovered > 0 or failed > 0:
        logger.info(f"[RECOVERY] Cycle complete: {recovered} requeued, {failed} marked failed")


async def _safe_retry(job_id: str):
    """Safely retry a job stage, catching all errors."""
    try:
        from .pipeline import execute_pipeline
        await execute_pipeline(job_id)
    except Exception as e:
        logger.error(f"[RECOVERY] Retry failed for {job_id[:8]}: {e}")


def stop_recovery_daemon():
    """Stop the daemon gracefully."""
    global _daemon_running
    _daemon_running = False
    logger.info("[RECOVERY] Daemon stopped")
