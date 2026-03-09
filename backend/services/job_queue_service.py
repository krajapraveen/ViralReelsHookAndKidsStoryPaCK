"""
Async Job Queue Service using In-Memory Queue with Worker Pools
For scalable background task processing

This service provides:
- Async job submission and processing
- Priority queues (high, normal, low)
- Job status tracking
- Automatic retries on failure
- Worker pool management
"""
import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

class JobPriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2

class JobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

@dataclass
class Job:
    """Represents an async job"""
    job_id: str
    job_type: str
    payload: Dict[str, Any]
    user_id: str
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    progress: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class JobQueueService:
    """In-memory async job queue with worker pools"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Job storage
        self.jobs: Dict[str, Job] = {}
        
        # Priority queues
        self.queues: Dict[JobPriority, asyncio.Queue] = {
            JobPriority.HIGH: asyncio.Queue(),
            JobPriority.NORMAL: asyncio.Queue(),
            JobPriority.LOW: asyncio.Queue()
        }
        
        # Worker pools by job type
        self.workers: Dict[str, List[asyncio.Task]] = defaultdict(list)
        self.worker_count = int(os.environ.get("JOB_QUEUE_WORKERS", "4"))
        
        # Job handlers by type
        self.handlers: Dict[str, Callable] = {}
        
        # Progress callbacks
        self.progress_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "by_type": defaultdict(lambda: {"submitted": 0, "completed": 0, "failed": 0})
        }
        
        self._running = False
        self._initialized = True
        logger.info("JobQueueService initialized")
    
    def register_handler(self, job_type: str, handler: Callable, progress_callback: Callable = None):
        """Register a handler for a job type"""
        self.handlers[job_type] = handler
        if progress_callback:
            self.progress_callbacks[job_type] = progress_callback
        logger.info(f"Registered handler for job type: {job_type}")
    
    async def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        user_id: str,
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Submit a new job to the queue"""
        
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            user_id=user_id,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        self.jobs[job_id] = job
        await self.queues[priority].put(job_id)
        job.status = JobStatus.QUEUED
        
        self.stats["total_submitted"] += 1
        self.stats["by_type"][job_type]["submitted"] += 1
        
        logger.info(f"Job {job_id} submitted: type={job_type}, priority={priority.name}, user={user_id}")
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status.value,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error,
            "retries": job.retries,
            "metadata": job.metadata
        }
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or queued job"""
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
            job.status = JobStatus.CANCELLED
            logger.info(f"Job {job_id} cancelled")
            return True
        
        return False
    
    async def update_progress(self, job_id: str, progress: int, metadata: Dict[str, Any] = None):
        """Update job progress"""
        job = self.jobs.get(job_id)
        if job:
            job.progress = progress
            if metadata:
                job.metadata.update(metadata)
            
            # Call progress callback if registered
            callback = self.progress_callbacks.get(job.job_type)
            if callback:
                try:
                    await callback(job_id, job.user_id, progress, metadata)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    async def _process_job(self, job_id: str):
        """Process a single job"""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        if job.status == JobStatus.CANCELLED:
            return
        
        handler = self.handlers.get(job.job_type)
        if not handler:
            job.status = JobStatus.FAILED
            job.error = f"No handler registered for job type: {job.job_type}"
            self.stats["total_failed"] += 1
            self.stats["by_type"][job.job_type]["failed"] += 1
            return
        
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        
        try:
            # Pass progress update function to handler
            async def progress_fn(progress: int, metadata: Dict = None):
                await self.update_progress(job_id, progress, metadata)
            
            result = await handler(job.payload, job.user_id, progress_fn)
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.result = result
            job.progress = 100
            
            self.stats["total_completed"] += 1
            self.stats["by_type"][job.job_type]["completed"] += 1
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.retries += 1
            
            if job.retries < job.max_retries:
                job.status = JobStatus.RETRYING
                await asyncio.sleep(2 ** job.retries)  # Exponential backoff
                await self.queues[job.priority].put(job_id)
                logger.info(f"Job {job_id} queued for retry ({job.retries}/{job.max_retries})")
            else:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error = str(e)
                
                self.stats["total_failed"] += 1
                self.stats["by_type"][job.job_type]["failed"] += 1
    
    async def _worker(self, worker_id: int):
        """Worker coroutine that processes jobs from queues"""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Check high priority first, then normal, then low
                job_id = None
                
                for priority in [JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
                    try:
                        job_id = self.queues[priority].get_nowait()
                        break
                    except asyncio.QueueEmpty:
                        continue
                
                if job_id:
                    await self._process_job(job_id)
                else:
                    await asyncio.sleep(0.1)  # Small delay if no jobs
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def start(self):
        """Start the job queue workers"""
        if self._running:
            return
        
        self._running = True
        
        # Start worker pool
        for i in range(self.worker_count):
            task = asyncio.create_task(self._worker(i))
            self.workers["default"].append(task)
        
        logger.info(f"JobQueueService started with {self.worker_count} workers")
    
    async def stop(self):
        """Stop the job queue workers"""
        self._running = False
        
        # Wait for workers to finish
        for worker_list in self.workers.values():
            for task in worker_list:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.workers.clear()
        logger.info("JobQueueService stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        queue_depths = {
            priority.name: self.queues[priority].qsize()
            for priority in JobPriority
        }
        
        return {
            "total_submitted": self.stats["total_submitted"],
            "total_completed": self.stats["total_completed"],
            "total_failed": self.stats["total_failed"],
            "success_rate": (
                self.stats["total_completed"] / self.stats["total_submitted"] * 100
                if self.stats["total_submitted"] > 0 else 0
            ),
            "queue_depths": queue_depths,
            "workers_active": sum(len(w) for w in self.workers.values()),
            "by_type": dict(self.stats["by_type"]),
            "jobs_in_memory": len(self.jobs)
        }
    
    def get_user_jobs(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get jobs for a specific user"""
        user_jobs = [
            job for job in self.jobs.values()
            if job.user_id == user_id
        ]
        
        # Sort by created_at desc
        user_jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return [
            {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status.value,
                "progress": job.progress,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in user_jobs[:limit]
        ]

# Singleton instance
_job_queue_service: Optional[JobQueueService] = None

def get_job_queue() -> JobQueueService:
    """Get the job queue service singleton"""
    global _job_queue_service
    if _job_queue_service is None:
        _job_queue_service = JobQueueService()
    return _job_queue_service

async def init_job_queue():
    """Initialize and start the job queue"""
    queue = get_job_queue()
    await queue.start()
    return queue
