"""
Enhanced Worker System with Auto-scaling and Load Balancing
Provides individual workers for each functionality with optimal performance
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    SCALING = "scaling"
    SHUTDOWN = "shutdown"


class JobPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Job:
    id: str
    feature: str
    user_id: str
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "queued"
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class WorkerMetrics:
    jobs_processed: int = 0
    jobs_failed: int = 0
    total_processing_time: float = 0
    avg_processing_time: float = 0
    last_job_time: Optional[datetime] = None
    idle_since: Optional[datetime] = None


class FeatureWorker:
    """Individual worker for a specific feature"""
    
    def __init__(self, worker_id: str, feature: str, handler: Callable):
        self.worker_id = worker_id
        self.feature = feature
        self.handler = handler
        self.status = WorkerStatus.IDLE
        self.metrics = WorkerMetrics()
        self.current_job: Optional[Job] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self, queue: asyncio.Queue):
        """Start the worker processing loop"""
        self._running = True
        self.metrics.idle_since = datetime.now(timezone.utc)
        
        while self._running:
            try:
                # Wait for a job with timeout
                try:
                    job = await asyncio.wait_for(queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                if job is None:  # Shutdown signal
                    break
                
                await self.process_job(job)
                queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
    
    async def process_job(self, job: Job):
        """Process a single job"""
        self.status = WorkerStatus.BUSY
        self.current_job = job
        self.metrics.idle_since = None
        job.started_at = datetime.now(timezone.utc)
        job.status = "processing"
        
        start_time = time.time()
        
        try:
            # Execute the handler
            result = await self.handler(job.payload)
            
            job.result = result
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            
            self.metrics.jobs_processed += 1
            
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.error = str(e)
            job.status = "failed"
            job.retry_count += 1
            
            self.metrics.jobs_failed += 1
            
            # Re-queue if retries available
            if job.retry_count < job.max_retries:
                job.status = "queued"
                return job  # Return for re-queueing
        
        finally:
            processing_time = time.time() - start_time
            self.metrics.total_processing_time += processing_time
            self.metrics.avg_processing_time = (
                self.metrics.total_processing_time / 
                max(self.metrics.jobs_processed + self.metrics.jobs_failed, 1)
            )
            self.metrics.last_job_time = datetime.now(timezone.utc)
            self.status = WorkerStatus.IDLE
            self.current_job = None
            self.metrics.idle_since = datetime.now(timezone.utc)
        
        return None
    
    def stop(self):
        """Stop the worker"""
        self._running = False
        self.status = WorkerStatus.SHUTDOWN


class FeatureWorkerPool:
    """Pool of workers for a specific feature with auto-scaling"""
    
    def __init__(
        self,
        feature: str,
        handler: Callable,
        min_workers: int = 2,
        max_workers: int = 10,
        scale_up_threshold: float = 0.8,  # Scale up when 80% busy
        scale_down_threshold: float = 0.3,  # Scale down when 30% busy
        scale_interval: float = 10.0  # Check every 10 seconds
    ):
        self.feature = feature
        self.handler = handler
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.scale_interval = scale_interval
        
        self.workers: Dict[str, FeatureWorker] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.jobs: Dict[str, Job] = {}  # Track all jobs
        self._running = False
        self._scale_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.total_jobs_queued = 0
        self.total_jobs_completed = 0
        self.total_jobs_failed = 0
        self.peak_queue_size = 0
        self.scale_up_count = 0
        self.scale_down_count = 0
    
    async def start(self):
        """Start the worker pool"""
        self._running = True
        
        # Start minimum number of workers
        for i in range(self.min_workers):
            await self._add_worker()
        
        # Start auto-scaling task
        self._scale_task = asyncio.create_task(self._auto_scale_loop())
        
        logger.info(f"Feature pool '{self.feature}' started with {self.min_workers} workers")
    
    async def stop(self):
        """Stop the worker pool"""
        self._running = False
        
        # Stop scaling
        if self._scale_task:
            self._scale_task.cancel()
        
        # Signal workers to stop
        for _ in self.workers:
            await self.job_queue.put(None)
        
        # Stop all workers
        for worker in self.workers.values():
            worker.stop()
        
        logger.info(f"Feature pool '{self.feature}' stopped")
    
    async def _add_worker(self) -> Optional[FeatureWorker]:
        """Add a new worker to the pool"""
        if len(self.workers) >= self.max_workers:
            return None
        
        worker_id = f"{self.feature}_worker_{uuid.uuid4().hex[:8]}"
        worker = FeatureWorker(worker_id, self.feature, self.handler)
        self.workers[worker_id] = worker
        
        # Start worker in background
        asyncio.create_task(worker.start(self.job_queue))
        
        logger.info(f"Added worker {worker_id} to {self.feature} pool (total: {len(self.workers)})")
        return worker
    
    async def _remove_worker(self) -> bool:
        """Remove an idle worker from the pool"""
        if len(self.workers) <= self.min_workers:
            return False
        
        # Find an idle worker
        for worker_id, worker in list(self.workers.items()):
            if worker.status == WorkerStatus.IDLE:
                worker.stop()
                del self.workers[worker_id]
                logger.info(f"Removed worker {worker_id} from {self.feature} pool (total: {len(self.workers)})")
                return True
        
        return False
    
    async def _auto_scale_loop(self):
        """Auto-scaling loop"""
        while self._running:
            try:
                await asyncio.sleep(self.scale_interval)
                await self._check_and_scale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scale error for {self.feature}: {e}")
    
    async def _check_and_scale(self):
        """Check current load and scale if needed"""
        if not self.workers:
            return
        
        # Calculate busy ratio
        busy_count = sum(1 for w in self.workers.values() if w.status == WorkerStatus.BUSY)
        busy_ratio = busy_count / len(self.workers)
        
        # Also consider queue size
        queue_size = self.job_queue.qsize()
        self.peak_queue_size = max(self.peak_queue_size, queue_size)
        
        # Scale up if high load
        if busy_ratio >= self.scale_up_threshold or queue_size > len(self.workers) * 2:
            if len(self.workers) < self.max_workers:
                await self._add_worker()
                self.scale_up_count += 1
                logger.info(f"Scaled up {self.feature}: {len(self.workers)} workers, queue: {queue_size}")
        
        # Scale down if low load
        elif busy_ratio <= self.scale_down_threshold and queue_size == 0:
            if await self._remove_worker():
                self.scale_down_count += 1
                logger.info(f"Scaled down {self.feature}: {len(self.workers)} workers")
    
    async def submit_job(
        self,
        user_id: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL
    ) -> Job:
        """Submit a job to the pool"""
        job = Job(
            id=uuid.uuid4().hex,
            feature=self.feature,
            user_id=user_id,
            payload=payload,
            priority=priority
        )
        
        self.jobs[job.id] = job
        self.total_jobs_queued += 1
        
        # Add to queue (priority queue would be better but this is simpler)
        await self.job_queue.put(job)
        
        return job
    
    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics"""
        worker_metrics = []
        for worker in self.workers.values():
            worker_metrics.append({
                "id": worker.worker_id,
                "status": worker.status.value,
                "jobs_processed": worker.metrics.jobs_processed,
                "jobs_failed": worker.metrics.jobs_failed,
                "avg_processing_time_ms": round(worker.metrics.avg_processing_time * 1000, 2),
            })
        
        return {
            "feature": self.feature,
            "workers_count": len(self.workers),
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "queue_size": self.job_queue.qsize(),
            "peak_queue_size": self.peak_queue_size,
            "total_jobs_queued": self.total_jobs_queued,
            "total_jobs_completed": self.total_jobs_completed,
            "total_jobs_failed": self.total_jobs_failed,
            "scale_up_count": self.scale_up_count,
            "scale_down_count": self.scale_down_count,
            "workers": worker_metrics
        }


class EnhancedWorkerSystem:
    """
    Enhanced worker system with individual workers per feature,
    auto-scaling, and load balancing
    """
    
    def __init__(self, db):
        self.db = db
        self.feature_pools: Dict[str, FeatureWorkerPool] = {}
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Default configuration per feature
        self.feature_configs = {
            "comic_avatar": {"min": 3, "max": 15, "scale_up": 0.7, "scale_down": 0.2},
            "comic_strip": {"min": 2, "max": 10, "scale_up": 0.75, "scale_down": 0.25},
            "comic_storybook": {"min": 2, "max": 8, "scale_up": 0.8, "scale_down": 0.3},
            "gif_maker": {"min": 2, "max": 8, "scale_up": 0.75, "scale_down": 0.25},
            "coloring_book": {"min": 2, "max": 6, "scale_up": 0.8, "scale_down": 0.3},
            "reel_generator": {"min": 2, "max": 10, "scale_up": 0.7, "scale_down": 0.2},
            "story_generator": {"min": 2, "max": 8, "scale_up": 0.75, "scale_down": 0.25},
            "caption_rewriter": {"min": 2, "max": 6, "scale_up": 0.8, "scale_down": 0.3},
            "tone_switcher": {"min": 2, "max": 6, "scale_up": 0.8, "scale_down": 0.3},
            "hashtag_generator": {"min": 2, "max": 6, "scale_up": 0.8, "scale_down": 0.3},
            "bio_generator": {"min": 2, "max": 6, "scale_up": 0.8, "scale_down": 0.3},
            "default": {"min": 2, "max": 8, "scale_up": 0.75, "scale_down": 0.25}
        }
    
    def register_feature(self, feature: str, handler: Callable):
        """Register a feature with its handler"""
        config = self.feature_configs.get(feature, self.feature_configs["default"])
        
        pool = FeatureWorkerPool(
            feature=feature,
            handler=handler,
            min_workers=config["min"],
            max_workers=config["max"],
            scale_up_threshold=config["scale_up"],
            scale_down_threshold=config["scale_down"]
        )
        
        self.feature_pools[feature] = pool
        logger.info(f"Registered feature '{feature}' with config: {config}")
    
    async def start(self):
        """Start the worker system"""
        self._running = True
        
        # Start all feature pools
        for feature, pool in self.feature_pools.items():
            await pool.start()
        
        # Start health check
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Enhanced worker system started with {len(self.feature_pools)} feature pools")
    
    async def stop(self):
        """Stop the worker system"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        for pool in self.feature_pools.values():
            await pool.stop()
        
        logger.info("Enhanced worker system stopped")
    
    async def _health_check_loop(self):
        """Periodic health check"""
        while self._running:
            try:
                await asyncio.sleep(30)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _perform_health_check(self):
        """Perform health check on all pools"""
        for feature, pool in self.feature_pools.items():
            metrics = pool.get_metrics()
            
            # Log warnings for potential issues
            if metrics["queue_size"] > metrics["max_workers"] * 3:
                logger.warning(f"High queue for {feature}: {metrics['queue_size']} jobs waiting")
            
            # Store metrics in DB for monitoring
            await self.db.worker_metrics.update_one(
                {"feature": feature},
                {"$set": {
                    **metrics,
                    "timestamp": datetime.now(timezone.utc)
                }},
                upsert=True
            )
    
    async def submit_job(
        self,
        feature: str,
        user_id: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL
    ) -> Optional[Job]:
        """Submit a job to the appropriate feature pool"""
        pool = self.feature_pools.get(feature)
        if not pool:
            logger.error(f"No pool registered for feature: {feature}")
            return None
        
        return await pool.submit_job(user_id, payload, priority)
    
    def get_job_status(self, feature: str, job_id: str) -> Optional[Job]:
        """Get job status"""
        pool = self.feature_pools.get(feature)
        if not pool:
            return None
        return pool.get_job_status(job_id)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics"""
        pool_metrics = {}
        total_workers = 0
        total_queued = 0
        total_completed = 0
        total_failed = 0
        
        for feature, pool in self.feature_pools.items():
            metrics = pool.get_metrics()
            pool_metrics[feature] = metrics
            total_workers += metrics["workers_count"]
            total_queued += metrics["total_jobs_queued"]
            total_completed += metrics["total_jobs_completed"]
            total_failed += metrics["total_jobs_failed"]
        
        return {
            "status": "running" if self._running else "stopped",
            "total_feature_pools": len(self.feature_pools),
            "total_workers": total_workers,
            "total_jobs_queued": total_queued,
            "total_jobs_completed": total_completed,
            "total_jobs_failed": total_failed,
            "pools": pool_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_worker_system: Optional[EnhancedWorkerSystem] = None


def get_worker_system(db) -> EnhancedWorkerSystem:
    """Get or create the worker system singleton"""
    global _worker_system
    if _worker_system is None:
        _worker_system = EnhancedWorkerSystem(db)
    return _worker_system


# Convenience decorator for feature handlers
def feature_handler(feature: str):
    """Decorator to register a function as a feature handler"""
    def decorator(func):
        async def wrapper(payload):
            return await func(payload)
        wrapper._feature = feature
        return wrapper
    return decorator
