"""
Pipeline Worker Pool
Dedicated heavy-job workers for Story → Video pipeline.
Isolated from lightweight API request handling.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from shared import db

logger = logging.getLogger("pipeline_worker")

# Worker pool configuration — use 1 worker for production stability
NUM_WORKERS = 1
MAX_CONCURRENT_JOBS = 1

# Global worker state
_worker_queue: asyncio.Queue = None
_workers_started = False
_worker_tasks = []
_worker_stats = {
    "jobs_processed": 0,
    "jobs_failed": 0,
    "total_processing_ms": 0,
    "active_jobs": 0,
    "queue_size": 0,
}


async def get_queue() -> asyncio.Queue:
    global _worker_queue
    if _worker_queue is None:
        _worker_queue = asyncio.Queue(maxsize=50)
    return _worker_queue


async def enqueue_job(job_id: str):
    """Add a job to the worker queue."""
    queue = await get_queue()
    await queue.put(job_id)
    _worker_stats["queue_size"] = queue.qsize()
    logger.info(f"[WORKER] Job {job_id[:8]} enqueued (queue size: {queue.qsize()})")


async def worker_loop(worker_id: int):
    """Single worker loop — picks jobs from queue and executes pipeline."""
    from services.pipeline_engine import execute_pipeline

    logger.info(f"[WORKER-{worker_id}] Started")
    queue = await get_queue()

    while True:
        try:
            job_id = await queue.get()
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
                # Mark job failed in DB
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
    """Start the dedicated worker pool."""
    global _workers_started, _worker_tasks

    if _workers_started:
        return

    _workers_started = True
    for i in range(NUM_WORKERS):
        task = asyncio.create_task(worker_loop(i))
        _worker_tasks.append(task)

    logger.info(f"[WORKER] Started {NUM_WORKERS} dedicated pipeline workers")

    # Clean up stale jobs from previous server lifecycle (mark as FAILED, refund credits)
    # DO NOT re-process — they would likely fail again and could crash the server
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stale_jobs = await db.pipeline_jobs.find(
            {"status": {"$in": ["PROCESSING", "QUEUED"]}},
            {"job_id": 1, "user_id": 1, "credits_charged": 1, "created_at": 1, "_id": 0}
        ).to_list(length=50)

        for job_doc in stale_jobs:
            jid = job_doc.get("job_id", "")
            uid = job_doc.get("user_id")
            credits = job_doc.get("credits_charged", 0)
            logger.info(f"[WORKER] Cleaning stale job {jid[:8]} (was stuck)")
            
            # Mark as FAILED
            await db.pipeline_jobs.update_one(
                {"job_id": jid},
                {"$set": {
                    "status": "FAILED",
                    "error": "Job interrupted by server restart. Credits refunded.",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            # Refund credits
            if uid and credits:
                await db.users.update_one(
                    {"id": uid},
                    {"$inc": {"credits": credits}}
                )
                logger.info(f"[WORKER] Refunded {credits} credits for stale job {jid[:8]}")

        if stale_jobs:
            logger.info(f"[WORKER] Cleaned up {len(stale_jobs)} stale jobs")
    except Exception as e:
        logger.warning(f"[WORKER] Could not clean stale jobs: {e}")


async def stop_workers():
    """Gracefully stop workers."""
    global _workers_started, _worker_tasks
    for task in _worker_tasks:
        task.cancel()
    _worker_tasks = []
    _workers_started = False


def get_worker_stats() -> dict:
    """Return current worker pool statistics."""
    return {
        **_worker_stats,
        "num_workers": NUM_WORKERS,
        "max_concurrent": MAX_CONCURRENT_JOBS,
        "workers_running": _workers_started,
    }
