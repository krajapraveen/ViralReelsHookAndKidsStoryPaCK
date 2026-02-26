"""
Worker Queue System - Separate Queues for Different Job Types
Implements priority lanes with dedicated workers for optimal performance
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Job priority levels - lower number = higher priority"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class QueueType(Enum):
    """Worker queue types - separate queues for different workloads"""
    TEXT = "text"       # Fast text-only jobs (reels, scripts)
    IMAGE = "image"     # Image generation jobs
    VIDEO = "video"     # Video generation jobs (slowest)
    BATCH = "batch"     # Batch processing jobs


# Queue Configuration
QUEUE_CONFIG = {
    QueueType.TEXT: {
        "max_concurrent": 5,
        "timeout_seconds": 60,
        "priority": JobPriority.HIGH,
        "job_types": ["STORY_GENERATION", "REEL_GENERATION"],
        "retry_limit": 3,
        "retry_delays": [5, 15, 30],
    },
    QueueType.IMAGE: {
        "max_concurrent": 3,
        "timeout_seconds": 120,
        "priority": JobPriority.NORMAL,
        "job_types": ["TEXT_TO_IMAGE"],
        "retry_limit": 3,
        "retry_delays": [10, 30, 60],
    },
    QueueType.VIDEO: {
        "max_concurrent": 2,
        "timeout_seconds": 600,
        "priority": JobPriority.LOW,
        "job_types": ["TEXT_TO_VIDEO", "IMAGE_TO_VIDEO", "VIDEO_REMIX"],
        "retry_limit": 2,
        "retry_delays": [30, 120],
    },
    QueueType.BATCH: {
        "max_concurrent": 1,
        "timeout_seconds": 1800,
        "priority": JobPriority.LOW,
        "job_types": ["BATCH_EXPORT", "BULK_GENERATE"],
        "retry_limit": 1,
        "retry_delays": [60],
    }
}


# Reverse mapping: job_type -> queue
JOB_TYPE_TO_QUEUE = {}
for queue_type, config in QUEUE_CONFIG.items():
    for job_type in config["job_types"]:
        JOB_TYPE_TO_QUEUE[job_type] = queue_type


class WorkerQueue:
    """Individual worker queue for a specific job type category"""
    
    def __init__(self, queue_type: QueueType, db, processor: Callable):
        self.queue_type = queue_type
        self.config = QUEUE_CONFIG[queue_type]
        self.db = db
        self.processor = processor
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self.metrics = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "retried": 0,
            "avg_processing_time": 0,
            "processing_times": [],
        }
    
    @property
    def collection_name(self) -> str:
        return "genstudio_jobs"
    
    async def get_next_jobs(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get next jobs for this queue based on job types"""
        if limit is None:
            limit = self.config["max_concurrent"] - len(self.active_jobs)
        
        if limit <= 0:
            return []
        
        jobs = await self.db[self.collection_name].find(
            {
                "status": "QUEUED",
                "jobType": {"$in": self.config["job_types"]},
                "$or": [
                    {"lockedUntil": {"$exists": False}},
                    {"lockedUntil": {"$lt": datetime.now(timezone.utc).isoformat()}}
                ]
            },
            {"_id": 0}
        ).sort([("priority", 1), ("createdAt", 1)]).limit(limit).to_list(limit)
        
        return jobs
    
    async def lock_job(self, job_id: str) -> bool:
        """Lock a job for processing"""
        lock_until = (datetime.now(timezone.utc) + timedelta(seconds=self.config["timeout_seconds"])).isoformat()
        
        result = await self.db[self.collection_name].update_one(
            {
                "id": job_id,
                "status": "QUEUED",
                "$or": [
                    {"lockedUntil": {"$exists": False}},
                    {"lockedUntil": {"$lt": datetime.now(timezone.utc).isoformat()}}
                ]
            },
            {
                "$set": {
                    "status": "PROCESSING",
                    "lockedUntil": lock_until,
                    "startedAt": datetime.now(timezone.utc).isoformat(),
                    "queueType": self.queue_type.value
                },
                "$inc": {"attempts": 1}
            }
        )
        
        return result.modified_count > 0
    
    async def process_job_with_timeout(self, job: Dict[str, Any]):
        """Process a job with timeout handling"""
        job_id = job["id"]
        start_time = datetime.now(timezone.utc)
        
        try:
            # Wrap processor with timeout
            result = await asyncio.wait_for(
                self.processor(job),
                timeout=self.config["timeout_seconds"]
            )
            
            # Record success metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._record_processing_time(processing_time)
            self.metrics["succeeded"] += 1
            self.metrics["processed"] += 1
            
            logger.info(f"[{self.queue_type.value}] Job {job_id} completed in {processing_time:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"[{self.queue_type.value}] Job {job_id} timed out after {self.config['timeout_seconds']}s")
            await self._handle_job_failure(job, f"Job timed out after {self.config['timeout_seconds']} seconds")
            self.metrics["failed"] += 1
            self.metrics["processed"] += 1
            
        except Exception as e:
            logger.error(f"[{self.queue_type.value}] Job {job_id} failed: {str(e)}")
            await self._handle_job_failure(job, str(e))
            self.metrics["failed"] += 1
            self.metrics["processed"] += 1
        
        finally:
            self.active_jobs.pop(job_id, None)
    
    async def _handle_job_failure(self, job: Dict[str, Any], error: str):
        """Handle job failure with retry logic"""
        job_id = job["id"]
        attempts = job.get("attempts", 1)
        
        # Check if we should retry
        if attempts < self.config["retry_limit"]:
            delay_idx = min(attempts - 1, len(self.config["retry_delays"]) - 1)
            retry_delay = self.config["retry_delays"][delay_idx]
            retry_at = (datetime.now(timezone.utc) + timedelta(seconds=retry_delay)).isoformat()
            
            await self.db[self.collection_name].update_one(
                {"id": job_id},
                {
                    "$set": {
                        "status": "QUEUED",
                        "lastError": error,
                        "lockedUntil": retry_at,
                        "retryCount": attempts
                    }
                }
            )
            
            self.metrics["retried"] += 1
            logger.info(f"[{self.queue_type.value}] Job {job_id} scheduled for retry in {retry_delay}s (attempt {attempts + 1}/{self.config['retry_limit']})")
        else:
            # Move to failed status - will trigger fallback output
            await self.db[self.collection_name].update_one(
                {"id": job_id},
                {
                    "$set": {
                        "status": "FAILED",
                        "errorMessage": error,
                        "completedAt": datetime.now(timezone.utc).isoformat(),
                        "exhaustedRetries": True
                    }
                }
            )
            logger.error(f"[{self.queue_type.value}] Job {job_id} failed after {attempts} attempts: {error}")
    
    def _record_processing_time(self, time_seconds: float):
        """Record processing time for metrics"""
        self.metrics["processing_times"].append(time_seconds)
        # Keep last 100 samples
        if len(self.metrics["processing_times"]) > 100:
            self.metrics["processing_times"].pop(0)
        self.metrics["avg_processing_time"] = sum(self.metrics["processing_times"]) / len(self.metrics["processing_times"])
    
    async def run(self, poll_interval: float = 2.0):
        """Main worker loop"""
        self.is_running = True
        logger.info(f"[{self.queue_type.value}] Worker queue started (max_concurrent: {self.config['max_concurrent']})")
        
        while self.is_running:
            try:
                # Get available slots
                available_slots = self.config["max_concurrent"] - len(self.active_jobs)
                
                if available_slots > 0:
                    jobs = await self.get_next_jobs(available_slots)
                    
                    for job in jobs:
                        job_id = job["id"]
                        
                        # Try to lock the job
                        if await self.lock_job(job_id):
                            # Create task for processing
                            task = asyncio.create_task(self.process_job_with_timeout(job))
                            self.active_jobs[job_id] = task
                            logger.info(f"[{self.queue_type.value}] Started processing job {job_id}")
                
            except Exception as e:
                logger.error(f"[{self.queue_type.value}] Worker loop error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    def stop(self):
        """Stop the worker queue"""
        self.is_running = False
        logger.info(f"[{self.queue_type.value}] Worker queue stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get queue status and metrics"""
        return {
            "queue_type": self.queue_type.value,
            "is_running": self.is_running,
            "active_jobs": len(self.active_jobs),
            "max_concurrent": self.config["max_concurrent"],
            "job_types": self.config["job_types"],
            "metrics": {
                "processed": self.metrics["processed"],
                "succeeded": self.metrics["succeeded"],
                "failed": self.metrics["failed"],
                "retried": self.metrics["retried"],
                "avg_processing_time_seconds": round(self.metrics["avg_processing_time"], 2),
                "success_rate": round(self.metrics["succeeded"] / max(self.metrics["processed"], 1) * 100, 1)
            }
        }


class WorkerQueueManager:
    """Manager for all worker queues"""
    
    def __init__(self, db, processor: Callable):
        self.db = db
        self.processor = processor
        self.queues: Dict[QueueType, WorkerQueue] = {}
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all worker queues"""
        if self.is_initialized:
            return
        
        for queue_type in QUEUE_CONFIG.keys():
            self.queues[queue_type] = WorkerQueue(queue_type, self.db, self.processor)
        
        self.is_initialized = True
        logger.info("Worker queue manager initialized with separate queues")
    
    async def start_all(self):
        """Start all worker queues"""
        tasks = []
        for queue in self.queues.values():
            tasks.append(asyncio.create_task(queue.run()))
        
        logger.info(f"Started {len(tasks)} worker queues")
        return tasks
    
    def stop_all(self):
        """Stop all worker queues"""
        for queue in self.queues.values():
            queue.stop()
        logger.info("All worker queues stopped")
    
    def get_queue_for_job_type(self, job_type: str) -> Optional[WorkerQueue]:
        """Get the appropriate queue for a job type"""
        queue_type = JOB_TYPE_TO_QUEUE.get(job_type)
        if queue_type:
            return self.queues.get(queue_type)
        return None
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all queues"""
        queue_statuses = {}
        total_active = 0
        total_processed = 0
        total_succeeded = 0
        
        for queue_type, queue in self.queues.items():
            status = queue.get_status()
            queue_statuses[queue_type.value] = status
            total_active += status["active_jobs"]
            total_processed += status["metrics"]["processed"]
            total_succeeded += status["metrics"]["succeeded"]
        
        return {
            "total_active_jobs": total_active,
            "total_processed": total_processed,
            "overall_success_rate": round(total_succeeded / max(total_processed, 1) * 100, 1),
            "queues": queue_statuses
        }


# Singleton instance (to be initialized with db)
_queue_manager: Optional[WorkerQueueManager] = None


async def get_queue_manager(db, processor: Callable) -> WorkerQueueManager:
    """Get or create the queue manager singleton"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = WorkerQueueManager(db, processor)
        await _queue_manager.initialize()
    return _queue_manager


def get_job_queue_type(job_type: str) -> str:
    """Get the queue type for a given job type"""
    queue_type = JOB_TYPE_TO_QUEUE.get(job_type)
    return queue_type.value if queue_type else "unknown"
