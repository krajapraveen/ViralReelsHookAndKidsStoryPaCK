"""
Multi-Queue Architecture — Tier-based queues with concurrency caps.

4 queues: premium, paid, free, background
- Each queue has its own concurrency limit
- Jobs are persisted to DB before queuing (crash-safe)
- On restart, queues are rebuilt from DB state

Queue placement order: premium → paid → free → background
Workers pull from highest-priority non-empty queue first.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any
from shared import db

logger = logging.getLogger("multi_queue")

QUEUE_CONFIG = {
    "premium":    {"concurrency": 5, "priority": 0},
    "paid":       {"concurrency": 3, "priority": 1},
    "free":       {"concurrency": 1, "priority": 2},
    "background": {"concurrency": 1, "priority": 3},
}

TIER_TO_QUEUE = {
    "free": "free",
    "paid": "paid",
    "premium": "premium",
}


class MultiQueueService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.queues: Dict[str, asyncio.Queue] = {
            name: asyncio.Queue() for name in QUEUE_CONFIG
        }
        self.active_counts: Dict[str, int] = {name: 0 for name in QUEUE_CONFIG}
        self.handlers: Dict[str, Callable] = {}
        self._running = False
        self._workers = []
        self._initialized = True

    def register_handler(self, job_type: str, handler: Callable):
        """Register an async handler for a job type."""
        self.handlers[job_type] = handler

    async def enqueue(self, job_id: str, queue_name: str):
        """Place a job into the correct queue. Job must already be in DB."""
        if queue_name not in self.queues:
            queue_name = "free"
        await self.queues[queue_name].put(job_id)
        logger.info(f"[QUEUE] Job {job_id[:8]} → {queue_name} queue (depth={self.queues[queue_name].qsize()})")

    async def rebuild_from_db(self):
        """Rebuild queues from DB on restart. Recover jobs that were queued/running."""
        recovered = 0
        cursor = db.comic_storybook_v2_jobs.find(
            {"status": {"$in": ["QUEUED", "PROCESSING", "REGENERATING"]}},
            {"_id": 0, "id": 1, "queue_name": 1, "status": 1}
        )
        async for job in cursor:
            queue_name = job.get("queue_name", "free")
            if queue_name not in self.queues:
                queue_name = "free"
            # Re-mark as QUEUED so worker picks it up
            await db.comic_storybook_v2_jobs.update_one(
                {"id": job["id"]},
                {"$set": {"status": "QUEUED"}}
            )
            await self.queues[queue_name].put(job["id"])
            recovered += 1
        if recovered:
            logger.info(f"[QUEUE] Recovered {recovered} jobs from DB on restart")

    async def _worker(self, worker_id: int):
        """Worker pulls from highest-priority non-empty queue respecting concurrency caps."""
        logger.info(f"[QUEUE] Worker {worker_id} started")
        while self._running:
            picked = False
            # Iterate queues in priority order
            for qname in sorted(QUEUE_CONFIG, key=lambda q: QUEUE_CONFIG[q]["priority"]):
                cap = QUEUE_CONFIG[qname]["concurrency"]
                if self.active_counts[qname] >= cap:
                    continue
                try:
                    job_id = self.queues[qname].get_nowait()
                except asyncio.QueueEmpty:
                    continue

                picked = True
                self.active_counts[qname] += 1
                try:
                    await self._execute_job(job_id, qname)
                finally:
                    self.active_counts[qname] -= 1
                break

            if not picked:
                await asyncio.sleep(0.5)
        logger.info(f"[QUEUE] Worker {worker_id} stopped")

    async def _execute_job(self, job_id: str, queue_name: str):
        """Load job from DB, dispatch to handler."""
        job = await db.comic_storybook_v2_jobs.find_one({"id": job_id}, {"_id": 0})
        if not job:
            logger.warning(f"[QUEUE] Job {job_id[:8]} not found in DB, skipping")
            return
        if job.get("status") == "CANCELLED":
            logger.info(f"[QUEUE] Job {job_id[:8]} was cancelled, skipping")
            return

        job_type = job.get("type", "COMIC_STORYBOOK")
        handler = self.handlers.get(job_type)
        if not handler:
            logger.error(f"[QUEUE] No handler for job type: {job_type}")
            await db.comic_storybook_v2_jobs.update_one(
                {"id": job_id}, {"$set": {"status": "FAILED", "error": f"No handler for {job_type}"}}
            )
            return

        logger.info(f"[QUEUE] Executing job {job_id[:8]} from {queue_name} queue")
        try:
            await handler(job)
        except Exception as e:
            logger.error(f"[QUEUE] Job {job_id[:8]} execution failed: {e}")
            await db.comic_storybook_v2_jobs.update_one(
                {"id": job_id}, {"$set": {"status": "FAILED", "error": str(e)[:500]}}
            )

    async def start(self, worker_count: int = 3):
        if self._running:
            return
        self._running = True
        await self.rebuild_from_db()
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info(f"[QUEUE] MultiQueueService started with {worker_count} workers")

    async def stop(self):
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()
        logger.info("[QUEUE] MultiQueueService stopped")

    def get_status(self) -> dict:
        return {
            "queues": {
                name: {
                    "depth": self.queues[name].qsize(),
                    "active": self.active_counts[name],
                    "concurrency_cap": QUEUE_CONFIG[name]["concurrency"],
                }
                for name in QUEUE_CONFIG
            },
            "running": self._running,
            "worker_count": len(self._workers),
        }


_service: Optional[MultiQueueService] = None


def get_multi_queue() -> MultiQueueService:
    global _service
    if _service is None:
        _service = MultiQueueService()
    return _service
