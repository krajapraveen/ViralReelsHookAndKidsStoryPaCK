"""
Worker Horizontal Scaling Configuration
Manages job queue processing with auto-scaling capabilities
"""
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# WORKER CONFIGURATION
# =============================================================================

WORKER_CONFIG = {
    # Base settings
    "min_workers": 2,
    "max_workers": 10,
    "scale_up_threshold": 20,  # Queue depth to trigger scale up
    "scale_down_threshold": 5,  # Queue depth to trigger scale down
    "scale_cooldown_seconds": 60,  # Min time between scaling operations
    
    # Job type priorities
    "priorities": {
        "TEXT_TO_IMAGE": 1,
        "TEXT_TO_VIDEO": 2,
        "IMAGE_TO_VIDEO": 3,
        "STORY_GENERATION": 1,
        "REEL_SCRIPT": 1,
        "COLORING_BOOK": 2,
    },
    
    # Timeouts per job type (seconds)
    "timeouts": {
        "TEXT_TO_IMAGE": 120,
        "TEXT_TO_VIDEO": 300,
        "IMAGE_TO_VIDEO": 300,
        "STORY_GENERATION": 60,
        "REEL_SCRIPT": 30,
        "COLORING_BOOK": 60,
    },
    
    # Retry configuration
    "max_retries": 3,
    "retry_delays": [5, 30, 120],  # Exponential backoff
    
    # Dead letter queue
    "dlq_enabled": True,
    "dlq_collection": "dead_letter_jobs",
}


# =============================================================================
# QUEUE METRICS
# =============================================================================

class QueueMetrics:
    """Track queue metrics for scaling decisions"""
    
    def __init__(self):
        self.current_workers = WORKER_CONFIG["min_workers"]
        self.last_scale_time = datetime.now(timezone.utc)
        self.queue_depths: list = []  # Rolling window
        self.processing_times: dict = {}  # Per job type
    
    def record_queue_depth(self, depth: int):
        """Record current queue depth"""
        self.queue_depths.append({
            "depth": depth,
            "time": datetime.now(timezone.utc).isoformat()
        })
        # Keep last 60 samples
        if len(self.queue_depths) > 60:
            self.queue_depths.pop(0)
    
    def get_average_depth(self) -> float:
        """Get average queue depth over window"""
        if not self.queue_depths:
            return 0
        return sum(d["depth"] for d in self.queue_depths) / len(self.queue_depths)
    
    def record_processing_time(self, job_type: str, duration_seconds: float):
        """Record job processing time"""
        if job_type not in self.processing_times:
            self.processing_times[job_type] = []
        self.processing_times[job_type].append(duration_seconds)
        # Keep last 100 samples per type
        if len(self.processing_times[job_type]) > 100:
            self.processing_times[job_type].pop(0)
    
    def get_avg_processing_time(self, job_type: str) -> float:
        """Get average processing time for job type"""
        times = self.processing_times.get(job_type, [])
        if not times:
            return WORKER_CONFIG["timeouts"].get(job_type, 120)
        return sum(times) / len(times)
    
    def should_scale_up(self) -> bool:
        """Determine if we should scale up workers"""
        avg_depth = self.get_average_depth()
        can_scale = (datetime.now(timezone.utc) - self.last_scale_time).total_seconds() > WORKER_CONFIG["scale_cooldown_seconds"]
        room_to_scale = self.current_workers < WORKER_CONFIG["max_workers"]
        
        return avg_depth > WORKER_CONFIG["scale_up_threshold"] and can_scale and room_to_scale
    
    def should_scale_down(self) -> bool:
        """Determine if we should scale down workers"""
        avg_depth = self.get_average_depth()
        can_scale = (datetime.now(timezone.utc) - self.last_scale_time).total_seconds() > WORKER_CONFIG["scale_cooldown_seconds"]
        room_to_scale = self.current_workers > WORKER_CONFIG["min_workers"]
        
        return avg_depth < WORKER_CONFIG["scale_down_threshold"] and can_scale and room_to_scale


# Global metrics instance
metrics = QueueMetrics()


# =============================================================================
# JOB PROCESSING
# =============================================================================

async def get_next_job(db) -> Optional[Dict[str, Any]]:
    """Get next job from queue with priority ordering"""
    # Sort by priority then by creation time
    job = await db.jobs.find_one_and_update(
        {
            "status": "PENDING",
            "$or": [
                {"lockedUntil": {"$exists": False}},
                {"lockedUntil": {"$lt": datetime.now(timezone.utc).isoformat()}}
            ]
        },
        {
            "$set": {
                "status": "PROCESSING",
                "startedAt": datetime.now(timezone.utc).isoformat(),
                "lockedUntil": (datetime.now(timezone.utc).replace(minute=datetime.now().minute + 5)).isoformat()
            },
            "$inc": {"attempts": 1}
        },
        sort=[("priority", 1), ("createdAt", 1)],
        return_document=True
    )
    return job


async def move_to_dlq(db, job: Dict[str, Any], error: str):
    """Move failed job to dead letter queue"""
    if not WORKER_CONFIG["dlq_enabled"]:
        return
    
    dlq_entry = {
        **job,
        "originalId": str(job.get("_id")),
        "movedAt": datetime.now(timezone.utc).isoformat(),
        "lastError": error,
        "status": "DEAD_LETTER"
    }
    dlq_entry.pop("_id", None)
    
    await db[WORKER_CONFIG["dlq_collection"]].insert_one(dlq_entry)
    await db.jobs.delete_one({"_id": job["_id"]})
    
    logger.warning(f"Job {job.get('id')} moved to dead letter queue: {error}")


async def retry_job(db, job: Dict[str, Any], error: str) -> bool:
    """Retry a failed job with exponential backoff"""
    attempts = job.get("attempts", 1)
    
    if attempts >= WORKER_CONFIG["max_retries"]:
        await move_to_dlq(db, job, error)
        return False
    
    retry_delay = WORKER_CONFIG["retry_delays"][min(attempts - 1, len(WORKER_CONFIG["retry_delays"]) - 1)]
    next_attempt = datetime.now(timezone.utc).replace(second=datetime.now().second + retry_delay)
    
    await db.jobs.update_one(
        {"_id": job["_id"]},
        {
            "$set": {
                "status": "PENDING",
                "lastError": error,
                "lockedUntil": next_attempt.isoformat()
            }
        }
    )
    
    logger.info(f"Job {job.get('id')} scheduled for retry in {retry_delay}s (attempt {attempts + 1})")
    return True


# =============================================================================
# SCALING OPERATIONS
# =============================================================================

async def scale_workers(direction: str) -> Dict[str, Any]:
    """Scale workers up or down"""
    if direction == "up" and metrics.should_scale_up():
        metrics.current_workers += 1
        metrics.last_scale_time = datetime.now(timezone.utc)
        logger.info(f"Scaled up to {metrics.current_workers} workers")
        return {"action": "scaled_up", "workers": metrics.current_workers}
    
    elif direction == "down" and metrics.should_scale_down():
        metrics.current_workers -= 1
        metrics.last_scale_time = datetime.now(timezone.utc)
        logger.info(f"Scaled down to {metrics.current_workers} workers")
        return {"action": "scaled_down", "workers": metrics.current_workers}
    
    return {"action": "no_change", "workers": metrics.current_workers}


async def get_scaling_status(db) -> Dict[str, Any]:
    """Get current scaling status"""
    queue_depth = await db.jobs.count_documents({"status": "PENDING"})
    processing = await db.jobs.count_documents({"status": "PROCESSING"})
    
    metrics.record_queue_depth(queue_depth)
    
    return {
        "current_workers": metrics.current_workers,
        "min_workers": WORKER_CONFIG["min_workers"],
        "max_workers": WORKER_CONFIG["max_workers"],
        "queue_depth": queue_depth,
        "processing": processing,
        "avg_queue_depth": metrics.get_average_depth(),
        "should_scale_up": metrics.should_scale_up(),
        "should_scale_down": metrics.should_scale_down(),
        "last_scale": metrics.last_scale_time.isoformat(),
        "processing_times": {
            job_type: metrics.get_avg_processing_time(job_type)
            for job_type in WORKER_CONFIG["priorities"].keys()
        }
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'WORKER_CONFIG',
    'QueueMetrics',
    'metrics',
    'get_next_job',
    'move_to_dlq',
    'retry_job',
    'scale_workers',
    'get_scaling_status'
]
