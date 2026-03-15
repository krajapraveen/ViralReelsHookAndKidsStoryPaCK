"""
Pipeline Worker Pool with Priority Queue & Auto-Scaling
Dedicated heavy-job workers for Story -> Video pipeline.
Dynamically scales workers based on queue depth.

Priority Levels:
  0 = Admin / Demo / UAT (highest)
  1 = Paid (Creator, Pro, Premium, Enterprise)
  10 = Free (standard)

Anti-starvation: Free jobs waiting > MAX_FREE_WAIT_SECONDS get boosted to priority 2.
FIFO within each priority tier via monotonic sequence counter.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field

from shared import db

logger = logging.getLogger("pipeline_worker")

# Worker pool configuration
MIN_WORKERS = 1
MAX_WORKERS = 3
SCALE_UP_THRESHOLD = 2
SCALE_DOWN_INTERVAL = 60

# Priority configuration
PRIORITY_ADMIN = 0
PRIORITY_PAID = 1
PRIORITY_FREE = 10
MAX_FREE_WAIT_SECONDS = 120  # Boost free jobs after 2 min to prevent starvation

PAID_PLANS = frozenset([
    "weekly", "monthly", "quarterly", "yearly",
    "starter", "creator", "pro", "premium", "enterprise",
    "admin", "demo"
])

# Monotonic counter for FIFO within same priority
_seq_counter = 0

def _next_seq():
    global _seq_counter
    _seq_counter += 1
    return _seq_counter


@dataclass(order=True)
class PriorityJob:
    """Comparable job entry for PriorityQueue. Sorts by (priority, sequence)."""
    priority: int
    sequence: int = field(compare=True)
    job_id: str = field(compare=False)
    user_id: str = field(compare=False, default="")
    user_plan: str = field(compare=False, default="free")
    enqueued_at: float = field(compare=False, default_factory=time.time)


# Global worker state
_worker_queue: asyncio.PriorityQueue = None
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
    # Priority analytics
    "priority_jobs_processed": 0,
    "free_jobs_processed": 0,
    "admin_jobs_processed": 0,
    "total_wait_ms_free": 0,
    "total_wait_ms_paid": 0,
    "total_wait_ms_admin": 0,
    "free_starvation_boosts": 0,
}

# Track pending free jobs for anti-starvation
_pending_free_jobs: list = []


async def get_queue() -> asyncio.PriorityQueue:
    global _worker_queue
    if _worker_queue is None:
        _worker_queue = asyncio.PriorityQueue(maxsize=50)
    return _worker_queue


def compute_priority(user_plan: str) -> int:
    """Determine queue priority from user plan."""
    plan = str(user_plan).lower().strip()
    if plan in ("admin", "demo"):
        return PRIORITY_ADMIN
    if plan in PAID_PLANS:
        return PRIORITY_PAID
    return PRIORITY_FREE


async def enqueue_job(job_id: str, user_id: str = "", user_plan: str = "free"):
    """Add a job to the priority worker queue and trigger scaling if needed."""
    queue = await get_queue()
    priority = compute_priority(user_plan)
    seq = _next_seq()

    entry = PriorityJob(
        priority=priority, sequence=seq,
        job_id=job_id, user_id=user_id, user_plan=user_plan,
        enqueued_at=time.time(),
    )
    await queue.put(entry)

    # Track free jobs for starvation detection
    if priority == PRIORITY_FREE:
        _pending_free_jobs.append(entry)

    _worker_stats["queue_size"] = queue.qsize()
    tier_name = "ADMIN" if priority == PRIORITY_ADMIN else "PAID" if priority == PRIORITY_PAID else "FREE"
    logger.info(f"[QUEUE] Job {job_id[:8]} enqueued as {tier_name} (priority={priority}, seq={seq}, queue={queue.qsize()})")

    # Store priority + queued_at in DB for analytics
    try:
        await db.pipeline_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "queue_priority": priority,
                "queue_tier": tier_name,
                "queued_at": datetime.now(timezone.utc),
            }}
        )
    except Exception:
        pass

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


async def _anti_starvation_loop():
    """Periodically boost starving free-tier jobs to prevent indefinite wait."""
    logger.info("[ANTI-STARVATION] Started (boosts free jobs waiting >2min)")
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            now = time.time()
            boosted = 0
            remaining = []
            for entry in _pending_free_jobs:
                wait = now - entry.enqueued_at
                if wait > MAX_FREE_WAIT_SECONDS and entry.priority == PRIORITY_FREE:
                    # Re-enqueue with boosted priority (2 = between paid and free)
                    queue = await get_queue()
                    boosted_entry = PriorityJob(
                        priority=2, sequence=entry.sequence,
                        job_id=entry.job_id, user_id=entry.user_id,
                        user_plan=entry.user_plan, enqueued_at=entry.enqueued_at,
                    )
                    try:
                        await queue.put(boosted_entry)
                        _worker_stats["free_starvation_boosts"] += 1
                        boosted += 1
                        logger.info(f"[ANTI-STARVATION] Boosted free job {entry.job_id[:8]} (waited {int(wait)}s)")
                    except asyncio.QueueFull:
                        remaining.append(entry)
                else:
                    remaining.append(entry)
            _pending_free_jobs.clear()
            _pending_free_jobs.extend(remaining)
            if boosted:
                logger.info(f"[ANTI-STARVATION] Boosted {boosted} free jobs")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[ANTI-STARVATION] Error: {e}")
            await asyncio.sleep(10)


async def worker_loop(worker_id: int, auto_scaled: bool = False):
    """Single worker loop — picks highest-priority job from queue and executes pipeline."""
    global _active_worker_count
    from services.pipeline_engine import execute_pipeline

    logger.info(f"[WORKER-{worker_id}] Started {'(auto-scaled)' if auto_scaled else ''}")
    queue = await get_queue()

    while True:
        try:
            timeout = SCALE_DOWN_INTERVAL if auto_scaled else None

            try:
                if timeout:
                    entry: PriorityJob = await asyncio.wait_for(queue.get(), timeout=timeout)
                else:
                    entry: PriorityJob = await queue.get()
            except asyncio.TimeoutError:
                if auto_scaled and _active_worker_count > MIN_WORKERS:
                    async with _scale_lock:
                        _active_worker_count -= 1
                        _worker_stats["current_workers"] = _active_worker_count
                        _worker_stats["scale_events"] += 1
                    logger.info(f"[AUTOSCALE] Worker-{worker_id} idle, scaled DOWN to {_active_worker_count} workers")
                    return
                continue

            job_id = entry.job_id
            wait_ms = int((time.time() - entry.enqueued_at) * 1000)

            # Remove from pending free list
            try:
                _pending_free_jobs[:] = [j for j in _pending_free_jobs if j.job_id != job_id]
            except Exception:
                pass

            # Check if job was already processed (e.g., from starvation re-queue)
            try:
                job_check = await db.pipeline_jobs.find_one(
                    {"job_id": job_id}, {"status": 1, "_id": 0}
                )
                if job_check and job_check.get("status") not in ("QUEUED", None):
                    queue.task_done()
                    continue
            except Exception:
                pass

            # Track wait time analytics by tier
            if entry.priority == PRIORITY_ADMIN:
                _worker_stats["admin_jobs_processed"] += 1
                _worker_stats["total_wait_ms_admin"] += wait_ms
            elif entry.priority <= PRIORITY_PAID:
                _worker_stats["priority_jobs_processed"] += 1
                _worker_stats["total_wait_ms_paid"] += wait_ms
            else:
                _worker_stats["free_jobs_processed"] += 1
                _worker_stats["total_wait_ms_free"] += wait_ms

            _worker_stats["active_jobs"] += 1
            _worker_stats["queue_size"] = queue.qsize()

            tier_name = "ADMIN" if entry.priority == PRIORITY_ADMIN else "PAID" if entry.priority <= PRIORITY_PAID else "FREE"
            logger.info(f"[WORKER-{worker_id}] Processing {tier_name} job {job_id[:8]} (waited {wait_ms}ms, priority={entry.priority})")

            # Record pickup time in DB
            try:
                await db.pipeline_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "queue_wait_ms": wait_ms,
                        "picked_up_at": datetime.now(timezone.utc),
                    }}
                )
            except Exception:
                pass

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

            logger.info(f"[WORKER-{worker_id}] {tier_name} job {job_id[:8]} finished in {elapsed}ms (waited {wait_ms}ms)")
            queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"[WORKER-{worker_id}] Shutting down")
            break
        except Exception as e:
            logger.error(f"[WORKER-{worker_id}] Unexpected error: {e}")
            await asyncio.sleep(1)


async def start_workers():
    """Start the dedicated worker pool with priority queue, auto-scaling, and stuck job recovery."""
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

    # Start anti-starvation loop
    asyncio.create_task(_anti_starvation_loop())

    # Start stuck job recovery loop
    asyncio.create_task(_stuck_job_recovery_loop())

    # Recover interrupted jobs from previous server lifecycle
    try:
        stale_jobs = await db.pipeline_jobs.find(
            {"status": {"$in": ["PROCESSING", "QUEUED"]}},
            {"job_id": 1, "user_id": 1, "credits_charged": 1, "created_at": 1,
             "title": 1, "queue_priority": 1, "stages": 1, "scenes": 1,
             "scene_images": 1, "scene_voices": 1, "current_stage": 1,
             "progress": 1, "_id": 0}
        ).to_list(length=50)

        restart_ts = datetime.now(timezone.utc).isoformat()
        resumed_count = 0
        fallback_count = 0
        failed_count = 0

        for job_doc in stale_jobs:
            jid = job_doc.get("job_id", "")
            uid = job_doc.get("user_id")
            credits = job_doc.get("credits_charged", 0)
            stages = job_doc.get("stages", {})
            current_stage = job_doc.get("current_stage", "unknown")
            progress = job_doc.get("progress", 0)

            # Check which stages completed
            completed_stages = [s for s, d in stages.items() if d.get("status") == "COMPLETED"]
            has_scenes = len(job_doc.get("scenes", [])) > 0
            has_images = len(job_doc.get("scene_images", {})) > 0
            has_voices = len(job_doc.get("scene_voices", {})) > 0

            logger.info(
                f"[RESTART-RECOVERY] Job {jid[:8]} interrupted at stage='{current_stage}' "
                f"progress={progress}% completed_stages={completed_stages} "
                f"scenes={has_scenes} images={has_images} voices={has_voices} "
                f"restart_ts={restart_ts}"
            )

            # Store crash diagnostic data
            crash_log = {
                "restart_timestamp": restart_ts,
                "job_id": jid,
                "stage_interrupted": current_stage,
                "progress_at_interrupt": progress,
                "completed_stages": completed_stages,
                "had_scenes": has_scenes,
                "had_images": has_images,
                "had_voices": has_voices,
                "reason": "server_restart",
            }
            await db.pipeline_jobs.update_one(
                {"job_id": jid},
                {"$push": {"crash_logs": crash_log}}
            )

            # Decision: Resume, Fallback, or Fail
            if completed_stages:
                # Has some progress — try to auto-resume from checkpoint
                try:
                    from services.pipeline_engine import resume_pipeline
                    await resume_pipeline(jid)

                    # Re-enqueue with original priority
                    user_plan = "free"
                    if job_doc.get("queue_priority") == 0:
                        user_plan = "admin"
                    elif job_doc.get("queue_priority") == 1:
                        user_plan = "monthly"

                    await enqueue_job(jid, user_id=uid or "", user_plan=user_plan)
                    resumed_count += 1
                    logger.info(f"[RESTART-RECOVERY] Auto-resumed job {jid[:8]} from checkpoint (completed: {completed_stages})")
                    continue
                except Exception as resume_err:
                    logger.warning(f"[RESTART-RECOVERY] Auto-resume failed for {jid[:8]}: {resume_err}")

                # Resume failed — try generating fallback if we have assets
                if has_scenes and has_images:
                    try:
                        from services.fallback_pipeline import run_fallback_pipeline
                        await run_fallback_pipeline(jid, current_stage or "render")
                        fallback_count += 1
                        logger.info(f"[RESTART-RECOVERY] Fallback generated for {jid[:8]} (scenes+images available)")
                        # Don't refund — user gets fallback assets
                        continue
                    except Exception as fb_err:
                        logger.warning(f"[RESTART-RECOVERY] Fallback failed for {jid[:8]}: {fb_err}")

            # No progress or all recovery failed — mark FAILED and refund
            await db.pipeline_jobs.update_one(
                {"job_id": jid},
                {"$set": {
                    "status": "FAILED",
                    "error": "Job interrupted by server restart. Credits refunded.",
                    "current_step": "Failed: server restarted during processing. Please try again.",
                    "updated_at": restart_ts,
                }}
            )
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
                logger.info(f"[RESTART-RECOVERY] Refunded {credits} credits for job {jid[:8]} (no recoverable progress)")
            failed_count += 1

        if stale_jobs:
            logger.info(
                f"[RESTART-RECOVERY] Processed {len(stale_jobs)} interrupted jobs: "
                f"{resumed_count} resumed, {fallback_count} fallback, {failed_count} failed"
            )
    except Exception as e:
        logger.warning(f"[RESTART-RECOVERY] Could not process stale jobs: {e}")


STUCK_JOB_TIMEOUT_MINUTES = 10

async def _stuck_job_recovery_loop():
    """Periodically check for stuck jobs and recover them."""
    logger.info("[STUCK-RECOVERY] Started stuck job recovery loop (checks every 2 min)")
    while True:
        try:
            await asyncio.sleep(120)

            cutoff = datetime.now(timezone.utc)
            from datetime import timedelta
            cutoff = cutoff - timedelta(minutes=STUCK_JOB_TIMEOUT_MINUTES)

            stuck_jobs = await db.pipeline_jobs.find({
                "status": "PROCESSING",
                "started_at": {"$lt": cutoff},
            }, {"job_id": 1, "user_id": 1, "credits_charged": 1, "current_stage": 1, "title": 1, "progress": 1, "queue_priority": 1, "_id": 0}).to_list(length=20)

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
    """Return current worker pool statistics including priority analytics."""
    free_count = _worker_stats["free_jobs_processed"]
    paid_count = _worker_stats["priority_jobs_processed"]
    admin_count = _worker_stats["admin_jobs_processed"]

    return {
        **_worker_stats,
        "min_workers": MIN_WORKERS,
        "max_workers": MAX_WORKERS,
        "num_workers": _active_worker_count,
        "max_concurrent": MAX_WORKERS,
        "workers_running": _workers_started,
        "scale_up_threshold": SCALE_UP_THRESHOLD,
        # Priority analytics
        "avg_wait_ms_free": int(_worker_stats["total_wait_ms_free"] / max(1, free_count)),
        "avg_wait_ms_paid": int(_worker_stats["total_wait_ms_paid"] / max(1, paid_count)),
        "avg_wait_ms_admin": int(_worker_stats["total_wait_ms_admin"] / max(1, admin_count)),
        "priority_config": {
            "admin": PRIORITY_ADMIN,
            "paid": PRIORITY_PAID,
            "free": PRIORITY_FREE,
            "anti_starvation_seconds": MAX_FREE_WAIT_SECONDS,
        },
    }
