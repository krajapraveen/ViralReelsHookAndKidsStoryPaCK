"""
Repair Worker — detects partial failure jobs and retries failed tasks.
Only repairs missing/failed assets. Does NOT re-run entire job.
Max 3 attempts per task. Structured failure reasons logged.
"""
import logging
from shared import db
from services.viral import viral_job_service as jobs
from services.viral.task_dispatch import dispatch_task, Q_TEXT_FAST, Q_IMAGE_FAST, Q_AUDIO_FAST, Q_VIDEO_FAST

logger = logging.getLogger("viral.worker.repair")

MAX_REPAIR_ATTEMPTS = 3

TASK_QUEUE_MAP = {
    "hooks": Q_TEXT_FAST,
    "script": Q_TEXT_FAST,
    "captions": Q_TEXT_FAST,
    "thumbnail": Q_IMAGE_FAST,
    "audio": Q_AUDIO_FAST,
    "video": Q_VIDEO_FAST,
}


async def handle_repair_task(payload: dict):
    job_id = payload["job_id"]
    target_task_type = payload.get("target_task_type")  # None = repair all failed

    logger.info(f"[REPAIR] Starting repair for job {job_id}, target={target_task_type or 'all'}")

    job = await jobs.get_job(db, job_id)
    if not job:
        logger.error(f"[REPAIR] Job {job_id} not found")
        return

    tasks = await jobs.get_tasks_for_job(db, job_id)
    repaired_count = 0

    for task in tasks:
        task_type = task["task_type"]
        if task_type == "packaging":
            continue
        if target_task_type and task_type != target_task_type:
            continue

        # Repair tasks that failed or have no corresponding asset
        needs_repair = False
        failure_reason = None

        if task["status"] == "failed":
            needs_repair = True
            failure_reason = "task_status_failed"
        elif task.get("fallback_used") and task.get("attempts", 0) < MAX_REPAIR_ATTEMPTS:
            # Check if asset exists
            asset = await db.viral_assets.find_one({"job_id": job_id, "task_id": task["task_id"]})
            if not asset or (not asset.get("content") and not asset.get("file_url")):
                needs_repair = True
                failure_reason = "missing_asset"

        if not needs_repair:
            continue

        if task.get("attempts", 0) >= MAX_REPAIR_ATTEMPTS:
            logger.warning(f"[REPAIR] Task {task_type} hit max attempts ({MAX_REPAIR_ATTEMPTS}), skipping")
            await jobs.log_event(db, job_id, "repair_skipped",
                                 f"Task {task_type} exceeded max attempts. Reason: {failure_reason}")
            continue

        # Reset task status for retry
        await db.viral_job_tasks.update_one(
            {"task_id": task["task_id"]},
            {"$set": {"status": "pending", "fallback_used": False}}
        )

        # Remove old failed asset if exists
        await db.viral_assets.delete_many({"job_id": job_id, "task_id": task["task_id"]})

        # Re-dispatch to appropriate queue
        queue = TASK_QUEUE_MAP.get(task_type)
        if queue:
            await dispatch_task(queue, {
                "task_id": task["task_id"],
                "job_id": job_id,
                "task_type": task_type,
                "idea": job["idea"],
                "niche": job["niche"],
            })
            repaired_count += 1
            await jobs.log_event(db, job_id, "repair_dispatched",
                                 f"Retrying {task_type} (attempt {task.get('attempts', 0) + 1}). Reason: {failure_reason}")
            logger.info(f"[REPAIR] Redispatched {task_type} for job {job_id} (reason: {failure_reason})")

    if repaired_count > 0:
        # Reset packaging to pending so it re-triggers when repairs finish
        await db.viral_job_tasks.update_one(
            {"job_id": job_id, "task_type": "packaging"},
            {"$set": {"status": "pending"}}
        )
        # Update job status
        await db.viral_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "repairing", "progress.message": "Optimizing your output...", "completed_at": None}}
        )
        await jobs.log_event(db, job_id, "repair_started", f"Repairing {repaired_count} task(s)")
    else:
        await jobs.log_event(db, job_id, "repair_noop", "No tasks needed repair")
        logger.info(f"[REPAIR] No repairs needed for job {job_id}")
