"""
Pipeline Worker Pool with Auto-Scaling
Dedicated heavy-job workers for Story -> Video pipeline.
Dynamically scales workers based on queue depth.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from shared import db

logger = logging.getLogger("pipeline_worker")

# Worker pool configuration
MIN_WORKERS = 1
MAX_WORKERS = 3
SCALE_UP_THRESHOLD = 2    # scale up when queue > this
SCALE_DOWN_INTERVAL = 60  # seconds idle before scaling down

# Global worker state
_worker_queue: asyncio.Queue = None
_workers_started = False
_worker_tasks = []
_active_worker_count = 0
_scale_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
_worker_stats = {
    "jobs_processed": 0,
    "jobs_failed": 0,
    "total_processing_ms": 0,
    "active_jobs": 0,
    "queue_size": 0,
    "current_workers": 0,
    "scale_events": 0,
}


async def get_queue() -> asyncio.Queue:
    global _worker_queue
    if _worker_queue is None:
        _worker_queue = asyncio.Queue(maxsize=50)
    return _worker_queue


async def enqueue_job(job_id: str):
    """Add a job to the worker queue and trigger scaling if needed."""
    queue = await get_queue()
    await queue.put(job_id)
    _worker_stats["queue_size"] = queue.qsize()
    logger.info(f"[WORKER] Job {job_id[:8]} enqueued (queue size: {queue.qsize()})")

    # Check if we need more workers
    await _maybe_scale_up()


async def _maybe_scale_up():
    """Scale up workers if queue depth exceeds threshold."""
    global _active_worker_count, _scale_lock
    if _scale_lock is None:
        _scale_lock = asyncio.Lock()

    async with _scale_lock:
        queue = await get_queue()
        if queue.qsize() > SCALE_UP_THRESHOLD and _active_worker_count < MAX_WORKERS:
            new_id = _active_worker_count
            _active_worker_count += 1
            _worker_stats["current_workers"] = _active_worker_count
            _worker_stats["scale_events"] += 1
            task = asyncio.create_task(worker_loop(new_id, auto_scaled=True))
            _worker_tasks.append(task)
            logger.info(f"[AUTOSCALE] Scaled UP to {_active_worker_count} workers (queue: {queue.qsize()})")


async def worker_loop(worker_id: int, auto_scaled: bool = False):
    """Single worker loop — picks jobs from queue and executes pipeline."""
    global _active_worker_count
    from services.pipeline_engine import execute_pipeline

    logger.info(f"[WORKER-{worker_id}] Started {'(auto-scaled)' if auto_scaled else ''}")
    queue = await get_queue()

    while True:
        try:
            # For auto-scaled workers, use timeout to allow scale-down
            timeout = SCALE_DOWN_INTERVAL if auto_scaled else None

            try:
                if timeout:
                    job_id = await asyncio.wait_for(queue.get(), timeout=timeout)
                else:
                    job_id = await queue.get()
            except asyncio.TimeoutError:
                # Auto-scaled worker idle too long — scale down
                if auto_scaled and _active_worker_count > MIN_WORKERS:
                    async with _scale_lock:
                        _active_worker_count -= 1
                        _worker_stats["current_workers"] = _active_worker_count
                        _worker_stats["scale_events"] += 1
                    logger.info(f"[AUTOSCALE] Worker-{worker_id} idle, scaled DOWN to {_active_worker_count} workers")
                    return
                continue

            _worker_stats["active_jobs"] += 1
            _worker_stats["queue_size"] = queue.qsize()

            logger.info(f"[WORKER-{worker_id}] Processing job {job_id[:8]}")
            start = time.time()

            try:
                await execute_pipeline(job_id)
                _worker_stats["jobs_processed"] += 1
            except Exception as e:
                _worker_stats["jobs_failed"] += 1
                logger.error(f"[WORKER-{worker_id}] Job {job_id[:8]} crashed: {e}")
                try:
                    await db.pipeline_jobs.update_one(
                        {"job_id": job_id},
                        {"$set": {
                            "status": "FAILED",
                            "error": f"Worker crash: {str(e)}",
                            "completed_at": datetime.now(timezone.utc),
                        }}
                    )
                except Exception:
                    pass

            elapsed = int((time.time() - start) * 1000)
            _worker_stats["total_processing_ms"] += elapsed
            _worker_stats["active_jobs"] -= 1

            logger.info(f"[WORKER-{worker_id}] Job {job_id[:8]} finished in {elapsed}ms")
            queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"[WORKER-{worker_id}] Shutting down")
            break
        except Exception as e:
            logger.error(f"[WORKER-{worker_id}] Unexpected error: {e}")
            await asyncio.sleep(1)


async def start_workers():
    """Start the dedicated worker pool with auto-scaling and stuck job recovery."""
    global _workers_started, _worker_tasks, _active_worker_count, _scale_lock

    if _workers_started:
        return

    _workers_started = True
    _scale_lock = asyncio.Lock()

    # Start minimum workers
    for i in range(MIN_WORKERS):
        task = asyncio.create_task(worker_loop(i))
        _worker_tasks.append(task)
        _active_worker_count += 1

    _worker_stats["current_workers"] = _active_worker_count
    logger.info(f"[WORKER] Started {MIN_WORKERS} pipeline workers (auto-scale to {MAX_WORKERS})")

    # Start stuck job recovery loop
    asyncio.create_task(_stuck_job_recovery_loop())

    # Clean up stale jobs from previous server lifecycle
    try:
        stale_jobs = await db.pipeline_jobs.find(
            {"status": {"$in": ["PROCESSING", "QUEUED"]}},
            {"job_id": 1, "user_id": 1, "credits_charged": 1, "created_at": 1, "title": 1, "_id": 0}
        ).to_list(length=50)

        for job_doc in stale_jobs:
            jid = job_doc.get("job_id", "")
            uid = job_doc.get("user_id")
            credits = job_doc.get("credits_charged", 0)
            logger.info(f"[WORKER] Cleaning stale job {jid[:8]} (was stuck)")

            await db.pipeline_jobs.update_one(
                {"job_id": jid},
                {"$set": {
                    "status": "FAILED",
                    "error": "Job interrupted by server restart. Credits refunded.",
                    "current_step": "Failed: server restarted during processing. Please try again.",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            if uid and credits:
                from bson import ObjectId
                # Try both ID formats for robustness
                result = await db.users.update_one(
                    {"id": uid},
                    {"$inc": {"credits": credits}}
                )
                if result.modified_count == 0:
                    try:
                        await db.users.update_one(
                            {"_id": ObjectId(uid)},
                            {"$inc": {"credits": credits}}
                        )
                    except Exception:
                        pass
                logger.info(f"[WORKER] Refunded {credits} credits for stale job {jid[:8]}")

        if stale_jobs:
            logger.info(f"[WORKER] Cleaned up {len(stale_jobs)} stale jobs")
    except Exception as e:
        logger.warning(f"[WORKER] Could not clean stale jobs: {e}")


STUCK_JOB_TIMEOUT_MINUTES = 10

async def _stuck_job_recovery_loop():
    """Periodically check for stuck jobs and recover them."""
    logger.info("[STUCK-RECOVERY] Started stuck job recovery loop (checks every 2 min)")
    while True:
        try:
            await asyncio.sleep(120)  # Check every 2 minutes

            cutoff = datetime.now(timezone.utc)
            from datetime import timedelta
            cutoff = cutoff - timedelta(minutes=STUCK_JOB_TIMEOUT_MINUTES)

            # Find jobs stuck in PROCESSING for too long
            stuck_jobs = await db.pipeline_jobs.find({
                "status": "PROCESSING",
                "started_at": {"$lt": cutoff},
            }, {"job_id": 1, "user_id": 1, "credits_charged": 1, "current_stage": 1, "title": 1, "progress": 1, "_id": 0}).to_list(length=20)

            for job_doc in stuck_jobs:
                jid = job_doc.get("job_id", "")
                stage = job_doc.get("current_stage", "unknown")
                progress = job_doc.get("progress", 0)
                credits = job_doc.get("credits_charged", 0)
                uid = job_doc.get("user_id")

                logger.warning(f"[STUCK-RECOVERY] Job {jid[:8]} stuck at {stage} ({progress}%) for >{STUCK_JOB_TIMEOUT_MINUTES}min. Marking FAILED.")

                await db.pipeline_jobs.update_one(
                    {"job_id": jid},
                    {"$set": {
                        "status": "FAILED",
                        "error": f"Job timed out at {stage} stage ({progress}%). Auto-recovered. Credits refunded. Please retry.",
                        "current_step": f"Failed: timed out at {stage}. Credits refunded. Please retry.",
                        "completed_at": datetime.now(timezone.utc),
                    }}
                )

                # Refund credits
                if uid and credits:
                    from bson import ObjectId
                    result = await db.users.update_one(
                        {"id": uid},
                        {"$inc": {"credits": credits}}
                    )
                    if result.modified_count == 0:
                        try:
                            await db.users.update_one(
                                {"_id": ObjectId(uid)},
                                {"$inc": {"credits": credits}}
                            )
                        except Exception:
                            pass
                    logger.info(f"[STUCK-RECOVERY] Refunded {credits} credits for stuck job {jid[:8]}")

            if stuck_jobs:
                logger.info(f"[STUCK-RECOVERY] Recovered {len(stuck_jobs)} stuck jobs")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[STUCK-RECOVERY] Error: {e}")
            await asyncio.sleep(30)


async def stop_workers():
    """Gracefully stop workers."""
    global _workers_started, _worker_tasks, _active_worker_count
    for task in _worker_tasks:
        task.cancel()
    _worker_tasks = []
    _workers_started = False
    _active_worker_count = 0


def get_worker_stats() -> dict:
    """Return current worker pool statistics."""
    return {
        **_worker_stats,
        "min_workers": MIN_WORKERS,
        "max_workers": MAX_WORKERS,
        "num_workers": _active_worker_count,
        "max_concurrent": MAX_WORKERS,
        "workers_running": _workers_started,
        "scale_up_threshold": SCALE_UP_THRESHOLD,
    }
