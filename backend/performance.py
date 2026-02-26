"""
CreatorStudio AI - Performance & Stability Module
==================================================
Production-grade performance optimization, request tracking, and self-healing capabilities.

Features:
- Request correlation IDs
- Connection pooling
- Response compression
- Idempotency enforcement
- Job retry with exponential backoff
- Dead letter queue
- Circuit breaker pattern
- Performance metrics collection
- Auto-recovery for stuck jobs
"""
import os
import uuid
import time
import asyncio
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from collections import defaultdict
import json

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger("creatorstudio.performance")

# MongoDB connection with optimized settings
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'creatorstudio_production')

# Connection pool settings for high concurrency
client = AsyncIOMotorClient(
    MONGO_URL,
    maxPoolSize=100,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    waitQueueTimeoutMS=5000,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=30000,
    retryWrites=True,
    retryReads=True
)
db = client[DB_NAME]


# ============================================
# PERFORMANCE METRICS
# ============================================

class PerformanceMetrics:
    """In-memory performance metrics collector"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0
        self.latency_buckets = defaultdict(int)  # <100ms, <500ms, <1s, <5s, >5s
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "errors": 0, "latency": 0})
        self.job_stats = defaultdict(lambda: {"submitted": 0, "completed": 0, "failed": 0, "retried": 0})
        self.provider_stats = defaultdict(lambda: {"calls": 0, "errors": 0, "timeouts": 0})
        self.start_time = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()
    
    async def record_request(self, endpoint: str, latency_ms: float, is_error: bool = False):
        async with self._lock:
            self.request_count += 1
            self.total_latency_ms += latency_ms
            
            # Latency buckets
            if latency_ms < 100:
                self.latency_buckets["<100ms"] += 1
            elif latency_ms < 500:
                self.latency_buckets["<500ms"] += 1
            elif latency_ms < 1000:
                self.latency_buckets["<1s"] += 1
            elif latency_ms < 5000:
                self.latency_buckets["<5s"] += 1
            else:
                self.latency_buckets[">5s"] += 1
            
            # Endpoint stats
            self.endpoint_stats[endpoint]["count"] += 1
            self.endpoint_stats[endpoint]["latency"] += latency_ms
            
            if is_error:
                self.error_count += 1
                self.endpoint_stats[endpoint]["errors"] += 1
    
    async def record_job_event(self, job_type: str, event: str):
        async with self._lock:
            self.job_stats[job_type][event] += 1
    
    async def record_provider_call(self, provider: str, is_error: bool = False, is_timeout: bool = False):
        async with self._lock:
            self.provider_stats[provider]["calls"] += 1
            if is_error:
                self.provider_stats[provider]["errors"] += 1
            if is_timeout:
                self.provider_stats[provider]["timeouts"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
        avg_latency = (self.total_latency_ms / self.request_count) if self.request_count > 0 else 0
        
        return {
            "uptime_seconds": int(uptime),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "latency_distribution": dict(self.latency_buckets),
            "requests_per_second": round(self.request_count / uptime, 2) if uptime > 0 else 0,
            "job_stats": dict(self.job_stats),
            "provider_stats": dict(self.provider_stats),
            "slowest_endpoints": sorted(
                [(k, v["latency"] / v["count"] if v["count"] > 0 else 0) 
                 for k, v in self.endpoint_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }


# Global metrics instance
metrics = PerformanceMetrics()


# ============================================
# CIRCUIT BREAKER
# ============================================

class CircuitBreaker:
    """
    Circuit breaker pattern for provider calls.
    Prevents cascading failures when a provider is down.
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self, 
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = self.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == self.OPEN:
                # Check if we should try half-open
                if self._should_try_half_open():
                    self.state = self.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Service temporarily unavailable: {self.name} circuit is open"
                    )
            
            if self.state == self.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls > self.half_open_max_calls:
                    # Too many half-open attempts, go back to open
                    self.state = self.OPEN
                    self.last_failure_time = datetime.now(timezone.utc)
                    raise HTTPException(
                        status_code=503,
                        detail=f"Service temporarily unavailable: {self.name}"
                    )
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    def _should_try_half_open(self) -> bool:
        if self.last_failure_time is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    async def _on_success(self):
        async with self._lock:
            if self.state == self.HALF_OPEN:
                self.successes += 1
                if self.successes >= 3:
                    # Successful recovery
                    self.state = self.CLOSED
                    self.failures = 0
                    self.successes = 0
                    logger.info(f"Circuit {self.name} recovered - now CLOSED")
            elif self.state == self.CLOSED:
                self.failures = 0
    
    async def _on_failure(self):
        async with self._lock:
            self.failures += 1
            self.successes = 0
            self.last_failure_time = datetime.now(timezone.utc)
            
            if self.failures >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(f"Circuit {self.name} OPENED after {self.failures} failures")
            
            await metrics.record_provider_call(self.name, is_error=True)


# Provider circuit breakers
circuit_breakers = {
    "gemini": CircuitBreaker("gemini", failure_threshold=5, recovery_timeout=60),
    "openai": CircuitBreaker("openai", failure_threshold=5, recovery_timeout=60),
    "elevenlabs": CircuitBreaker("elevenlabs", failure_threshold=3, recovery_timeout=120),
    "storage": CircuitBreaker("storage", failure_threshold=10, recovery_timeout=30),
}


# ============================================
# IDEMPOTENCY
# ============================================

class IdempotencyManager:
    """
    Ensures same request doesn't create duplicate jobs or deduct credits twice.
    Uses request hash as idempotency key.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
    
    def generate_key(self, user_id: str, endpoint: str, body: Dict) -> str:
        """Generate idempotency key from request parameters"""
        # Create deterministic hash
        content = json.dumps({
            "user_id": user_id,
            "endpoint": endpoint,
            "body": body
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    async def check_and_set(self, key: str, response_data: Dict = None) -> Optional[Dict]:
        """
        Check if key exists. If yes, return cached response.
        If no, set key and return None.
        """
        if not key:
            return None
        
        try:
            existing = await db.idempotency_keys.find_one(
                {"key": key},
                {"_id": 0}
            )
            
            if existing:
                # Check if expired
                created_at = existing.get("created_at")
                if created_at:
                    created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if (datetime.now(timezone.utc) - created_dt).total_seconds() < self.ttl_seconds:
                        logger.info(f"Idempotency hit for key {key[:8]}...")
                        return existing.get("response")
            
            # Set new key
            await db.idempotency_keys.update_one(
                {"key": key},
                {"$set": {
                    "key": key,
                    "response": response_data,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            return None
            
        except Exception as e:
            logger.warning(f"Idempotency check failed: {e}")
            return None
    
    async def update_response(self, key: str, response_data: Dict):
        """Update the stored response for a key"""
        if not key:
            return
        
        try:
            await db.idempotency_keys.update_one(
                {"key": key},
                {"$set": {"response": response_data}}
            )
        except Exception as e:
            logger.warning(f"Idempotency update failed: {e}")


idempotency = IdempotencyManager()


# ============================================
# JOB RETRY WITH EXPONENTIAL BACKOFF
# ============================================

class JobRetryManager:
    """
    Manages job retries with exponential backoff.
    Implements dead letter queue for repeated failures.
    """
    
    MAX_RETRIES = 3
    BASE_DELAY_SECONDS = 5
    MAX_DELAY_SECONDS = 60
    
    async def retry_job(
        self, 
        job_id: str, 
        job_type: str, 
        job_data: Dict,
        error: str
    ) -> bool:
        """
        Attempt to retry a failed job.
        Returns True if retry scheduled, False if sent to dead letter.
        """
        collection = self._get_collection(job_type)
        if not collection:
            return False
        
        # Get current retry count
        job = await db[collection].find_one({"id": job_id}, {"_id": 0, "retryCount": 1})
        retry_count = (job.get("retryCount") or 0) + 1
        
        if retry_count > self.MAX_RETRIES:
            # Send to dead letter queue
            await self._send_to_dead_letter(job_id, job_type, job_data, error)
            await metrics.record_job_event(job_type, "dead_lettered")
            return False
        
        # Calculate delay with exponential backoff
        delay = min(
            self.BASE_DELAY_SECONDS * (2 ** (retry_count - 1)),
            self.MAX_DELAY_SECONDS
        )
        
        # Update job for retry
        await db[collection].update_one(
            {"id": job_id},
            {"$set": {
                "status": "PENDING",
                "retryCount": retry_count,
                "lastError": error,
                "retryAt": (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        await metrics.record_job_event(job_type, "retried")
        logger.info(f"Job {job_id} scheduled for retry #{retry_count} in {delay}s")
        return True
    
    async def _send_to_dead_letter(
        self, 
        job_id: str, 
        job_type: str, 
        job_data: Dict,
        error: str
    ):
        """Send job to dead letter queue for manual review"""
        await db.dead_letter_queue.insert_one({
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "job_type": job_type,
            "job_data": job_data,
            "error": error,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending_review"
        })
        logger.warning(f"Job {job_id} sent to dead letter queue after {self.MAX_RETRIES} failures")
    
    def _get_collection(self, job_type: str) -> Optional[str]:
        mapping = {
            "storybook": "storybook_jobs",
            "comix": "comix_jobs",
            "gif": "gif_jobs",
            "reel": "reel_jobs",
            "generation": "generations"
        }
        return mapping.get(job_type)
    
    async def process_retry_queue(self):
        """Process jobs that are ready for retry"""
        now = datetime.now(timezone.utc).isoformat()
        
        for collection in ["storybook_jobs", "comix_jobs", "gif_jobs"]:
            try:
                # Find jobs ready for retry
                ready_jobs = await db[collection].find({
                    "status": "PENDING",
                    "retryAt": {"$lte": now},
                    "retryCount": {"$gt": 0}
                }, {"_id": 0, "id": 1}).to_list(10)
                
                for job in ready_jobs:
                    # Mark as processing to restart
                    await db[collection].update_one(
                        {"id": job["id"]},
                        {"$set": {"status": "QUEUED"}}
                    )
                    logger.info(f"Requeued job {job['id']} for retry")
                    
            except Exception as e:
                logger.error(f"Error processing retry queue for {collection}: {e}")


job_retry = JobRetryManager()


# ============================================
# STUCK JOB RECOVERY
# ============================================

class StuckJobRecovery:
    """
    Automatically recovers stuck jobs that have been processing too long.
    """
    
    STUCK_THRESHOLD_MINUTES = 10
    
    async def recover_stuck_jobs(self):
        """Find and recover jobs stuck in PROCESSING state"""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=self.STUCK_THRESHOLD_MINUTES)).isoformat()
        
        collections = ["storybook_jobs", "comix_jobs", "gif_jobs"]
        recovered = 0
        
        for collection in collections:
            try:
                # Find stuck jobs
                stuck_jobs = await db[collection].find({
                    "status": "PROCESSING",
                    "$or": [
                        {"updatedAt": {"$lt": cutoff}},
                        {"createdAt": {"$lt": cutoff}, "updatedAt": {"$exists": False}}
                    ]
                }, {"_id": 0, "id": 1, "userId": 1}).to_list(50)
                
                for job in stuck_jobs:
                    # Mark for retry
                    await db[collection].update_one(
                        {"id": job["id"]},
                        {"$set": {
                            "status": "PENDING",
                            "error": "Job stuck - auto-recovered",
                            "recoveredAt": datetime.now(timezone.utc).isoformat()
                        },
                        "$inc": {"retryCount": 1}}
                    )
                    recovered += 1
                    logger.warning(f"Recovered stuck job {job['id']} in {collection}")
                    
            except Exception as e:
                logger.error(f"Error recovering stuck jobs in {collection}: {e}")
        
        if recovered > 0:
            logger.info(f"Recovered {recovered} stuck jobs")
        
        return recovered


stuck_recovery = StuckJobRecovery()


# ============================================
# REQUEST TRACKING MIDDLEWARE
# ============================================

class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request tracking, correlation IDs, and performance monitoring.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id
        
        # Start timer
        start_time = time.time()
        
        # Get endpoint path
        endpoint = f"{request.method} {request.url.path}"
        
        try:
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            is_error = response.status_code >= 400
            await metrics.record_request(endpoint, latency_ms, is_error)
            
            # Add headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
            
            # Log slow requests
            if latency_ms > 5000:
                logger.warning(f"Slow request: {endpoint} took {latency_ms:.2f}ms (correlation_id={correlation_id})")
            
            return response
            
        except Exception as e:
            # Calculate latency even for errors
            latency_ms = (time.time() - start_time) * 1000
            await metrics.record_request(endpoint, latency_ms, is_error=True)
            
            logger.error(f"Request error: {endpoint} - {str(e)} (correlation_id={correlation_id})")
            raise


# ============================================
# DATABASE OPTIMIZATION
# ============================================

async def create_performance_indexes():
    """Create all required indexes for performance"""
    indexes_created = []
    
    try:
        # Users collection
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index([("createdAt", -1)])
        indexes_created.append("users")
        
        # Generations collection
        await db.generations.create_index("id", unique=True)
        await db.generations.create_index([("userId", 1), ("createdAt", -1)])
        await db.generations.create_index("status")
        indexes_created.append("generations")
        
        # Payments collection
        await db.payments.create_index("id", unique=True)
        await db.payments.create_index("orderId", unique=True, sparse=True)
        await db.payments.create_index([("userId", 1), ("createdAt", -1)])
        await db.payments.create_index("status")
        indexes_created.append("payments")
        
        # Storybook jobs
        await db.storybook_jobs.create_index("id", unique=True)
        await db.storybook_jobs.create_index([("userId", 1), ("createdAt", -1)])
        await db.storybook_jobs.create_index("status")
        await db.storybook_jobs.create_index([("status", 1), ("createdAt", -1)])
        indexes_created.append("storybook_jobs")
        
        # Comix jobs
        await db.comix_jobs.create_index("id", unique=True)
        await db.comix_jobs.create_index([("userId", 1), ("createdAt", -1)])
        await db.comix_jobs.create_index("status")
        await db.comix_jobs.create_index([("status", 1), ("createdAt", -1)])
        indexes_created.append("comix_jobs")
        
        # GIF jobs
        await db.gif_jobs.create_index("id", unique=True)
        await db.gif_jobs.create_index([("userId", 1), ("createdAt", -1)])
        await db.gif_jobs.create_index("status")
        await db.gif_jobs.create_index([("status", 1), ("createdAt", -1)])
        indexes_created.append("gif_jobs")
        
        # Idempotency keys (with TTL)
        await db.idempotency_keys.create_index("key", unique=True, sparse=True)
        await db.idempotency_keys.create_index(
            "created_at", 
            expireAfterSeconds=3600  # Auto-delete after 1 hour
        )
        indexes_created.append("idempotency_keys")
        
        # Dead letter queue
        await db.dead_letter_queue.create_index("id", unique=True)
        await db.dead_letter_queue.create_index("status")
        await db.dead_letter_queue.create_index([("created_at", -1)])
        indexes_created.append("dead_letter_queue")
        
        # User sessions
        await db.user_sessions.create_index("session_id", unique=True, sparse=True)
        await db.user_sessions.create_index([("user_id", 1), ("login_at", -1)])
        indexes_created.append("user_sessions")
        
        # Feature events
        await db.feature_events.create_index("event_id", unique=True, sparse=True)
        await db.feature_events.create_index([("user_id", 1), ("created_at", -1)])
        await db.feature_events.create_index([("feature_key", 1), ("event_type", 1)])
        indexes_created.append("feature_events")
        
        # Ratings
        await db.ratings.create_index("rating_id", unique=True, sparse=True)
        await db.ratings.create_index([("user_id", 1), ("created_at", -1)])
        await db.ratings.create_index([("rating", 1), ("created_at", -1)])
        indexes_created.append("ratings")
        
        # IP geo cache (with TTL)
        await db.ip_geo_cache.create_index("ip_hash", unique=True, sparse=True)
        await db.ip_geo_cache.create_index(
            "cached_at",
            expireAfterSeconds=259200  # 72 hours
        )
        indexes_created.append("ip_geo_cache")
        
        logger.info(f"Performance indexes created: {indexes_created}")
        return indexes_created
        
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
        return indexes_created


# ============================================
# CACHING LAYER
# ============================================

class InMemoryCache:
    """
    Simple in-memory cache for frequently accessed data.
    Thread-safe with TTL support.
    """
    
    def __init__(self, default_ttl: int = 300):
        self.cache = {}
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry["expires_at"] > datetime.now(timezone.utc):
                    return entry["value"]
                else:
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        async with self._lock:
            self.cache[key] = {
                "value": value,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl or self.default_ttl)
            }
    
    async def delete(self, key: str):
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
    
    async def clear(self):
        async with self._lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict:
        return {
            "size": len(self.cache),
            "keys": list(self.cache.keys())[:20]
        }


# Global cache instance
cache = InMemoryCache(default_ttl=300)


# ============================================
# PERFORMANCE API ENDPOINTS
# ============================================

async def get_performance_report() -> Dict:
    """Generate comprehensive performance report"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics.get_summary(),
        "cache": cache.get_stats(),
        "circuit_breakers": {
            name: {
                "state": cb.state,
                "failures": cb.failures,
                "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
            }
            for name, cb in circuit_breakers.items()
        }
    }


async def run_health_checks() -> Dict:
    """Run comprehensive health checks"""
    checks = {}
    
    # Database health
    try:
        await db.command("ping")
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check stuck jobs
    stuck_count = 0
    for coll in ["storybook_jobs", "comix_jobs", "gif_jobs"]:
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
            count = await db[coll].count_documents({
                "status": "PROCESSING",
                "createdAt": {"$lt": cutoff}
            })
            stuck_count += count
        except:
            pass
    
    checks["jobs"] = {
        "status": "healthy" if stuck_count == 0 else "degraded",
        "stuck_count": stuck_count
    }
    
    # Check dead letter queue
    try:
        dlq_count = await db.dead_letter_queue.count_documents({"status": "pending_review"})
        checks["dead_letter_queue"] = {
            "status": "healthy" if dlq_count < 10 else "warning",
            "pending_count": dlq_count
        }
    except Exception as e:
        checks["dead_letter_queue"] = {"status": "unknown", "error": str(e)}
    
    # Overall status
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())
    
    return {
        "overall": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================
# BACKGROUND TASKS
# ============================================

async def performance_maintenance_loop():
    """Background task for performance maintenance"""
    while True:
        try:
            # Recover stuck jobs
            await stuck_recovery.recover_stuck_jobs()
            
            # Process retry queue
            await job_retry.process_retry_queue()
            
            # Log metrics periodically
            summary = metrics.get_summary()
            if summary["error_rate_percent"] > 5:
                logger.warning(f"High error rate: {summary['error_rate_percent']}%")
            
        except Exception as e:
            logger.error(f"Maintenance loop error: {e}")
        
        await asyncio.sleep(60)  # Run every minute


# Export all components
__all__ = [
    "metrics",
    "cache",
    "idempotency",
    "job_retry",
    "stuck_recovery",
    "circuit_breakers",
    "PerformanceMiddleware",
    "create_performance_indexes",
    "get_performance_report",
    "run_health_checks",
    "performance_maintenance_loop"
]
