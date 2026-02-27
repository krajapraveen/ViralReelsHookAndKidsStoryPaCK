"""
Enhanced Self-Healing System with Worker Retries
=================================================
Implements automatic issue resolution and recovery mechanisms.

Features:
- Individual worker retry logic with exponential backoff
- Service health monitoring
- Auto-recovery for common failures
- Circuit breaker pattern
- Incident logging and alerting
"""
import asyncio
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from collections import defaultdict
import logging

logger = logging.getLogger("self_healing")


class WorkerRetryConfig:
    """Configuration for worker retries"""
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_INITIAL_DELAY = 1.0  # seconds
    DEFAULT_MAX_DELAY = 60.0  # seconds
    DEFAULT_BACKOFF_MULTIPLIER = 2.0
    

class CircuitState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting services
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
    
    async def can_execute(self) -> bool:
        """Check if the circuit allows execution"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                return True
            return False
        
        # HALF_OPEN state
        if self.half_open_calls < self.half_open_max_calls:
            return True
        return False
    
    async def record_success(self):
        """Record a successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.successes = 0
                logger.info(f"Circuit {self.name} recovered to CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failures = max(0, self.failures - 1)  # Gradually reduce failure count
    
    async def record_failure(self):
        """Record a failed execution"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened again after failure in HALF_OPEN")
        elif self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened after {self.failures} failures")


class WorkerRetryHandler:
    """
    Handles retry logic for individual workers with exponential backoff
    """
    
    def __init__(
        self,
        max_retries: int = WorkerRetryConfig.DEFAULT_MAX_RETRIES,
        initial_delay: float = WorkerRetryConfig.DEFAULT_INITIAL_DELAY,
        max_delay: float = WorkerRetryConfig.DEFAULT_MAX_DELAY,
        backoff_multiplier: float = WorkerRetryConfig.DEFAULT_BACKOFF_MULTIPLIER
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.retry_counts = defaultdict(int)
        self.last_errors = {}
    
    async def execute_with_retry(
        self,
        func: Callable,
        worker_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a function with retry logic"""
        attempt = 0
        last_error = None
        
        while attempt <= self.max_retries:
            try:
                result = await func(*args, **kwargs)
                # Reset retry count on success
                self.retry_counts[worker_name] = 0
                return {"success": True, "result": result, "attempts": attempt + 1}
            
            except Exception as e:
                last_error = e
                attempt += 1
                self.retry_counts[worker_name] += 1
                self.last_errors[worker_name] = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if attempt <= self.max_retries:
                    delay = min(
                        self.initial_delay * (self.backoff_multiplier ** (attempt - 1)),
                        self.max_delay
                    )
                    logger.warning(
                        f"Worker {worker_name} attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
        
        logger.error(f"Worker {worker_name} failed after {self.max_retries} retries: {last_error}")
        return {
            "success": False,
            "error": str(last_error),
            "attempts": attempt,
            "exhausted": True
        }
    
    def get_worker_stats(self, worker_name: str) -> Dict[str, Any]:
        """Get retry statistics for a worker"""
        return {
            "worker_name": worker_name,
            "total_retries": self.retry_counts.get(worker_name, 0),
            "last_error": self.last_errors.get(worker_name)
        }


class EnhancedSelfHealingSystem:
    """
    Central self-healing system that monitors and recovers services
    """
    
    def __init__(self, db):
        self.db = db
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, WorkerRetryHandler] = {}
        self.health_checks: Dict[str, Callable] = {}
        self.recovery_actions: Dict[str, Callable] = {}
        self._running = False
        self._monitor_interval = 30  # seconds
        
        # Initialize default circuit breakers
        self._init_default_breakers()
    
    def _init_default_breakers(self):
        """Initialize circuit breakers for critical services"""
        services = [
            ("llm_api", 3, 60.0),  # LLM calls: 3 failures, 60s recovery
            ("image_gen", 5, 120.0),  # Image gen: 5 failures, 120s recovery
            ("video_gen", 5, 180.0),  # Video gen: 5 failures, 180s recovery
            ("payment", 2, 30.0),  # Payment: 2 failures, 30s recovery
            ("database", 5, 10.0),  # Database: 5 failures, 10s recovery
        ]
        
        for name, threshold, timeout in services:
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=threshold,
                recovery_timeout=timeout
            )
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name=name)
        return self.circuit_breakers[name]
    
    def get_retry_handler(self, worker_name: str) -> WorkerRetryHandler:
        """Get or create a retry handler for a worker"""
        if worker_name not in self.retry_handlers:
            self.retry_handlers[worker_name] = WorkerRetryHandler()
        return self.retry_handlers[worker_name]
    
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
    
    def register_recovery_action(self, issue_type: str, action_func: Callable):
        """Register a recovery action for an issue type"""
        self.recovery_actions[issue_type] = action_func
    
    async def start_monitoring(self):
        """Start the self-healing monitoring loop"""
        if self._running:
            return
        self._running = True
        logger.info("Self-healing monitoring started")
        
        while self._running:
            try:
                await self._run_health_checks()
                await self._check_stuck_jobs()
                await self._check_failed_payments()
            except Exception as e:
                logger.error(f"Self-healing monitoring error: {e}")
            await asyncio.sleep(self._monitor_interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._running = False
        logger.info("Self-healing monitoring stopped")
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        for name, check_func in self.health_checks.items():
            try:
                result = await check_func()
                if not result.get("healthy", False):
                    await self._handle_unhealthy_service(name, result)
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                await self._handle_unhealthy_service(name, {"error": str(e)})
    
    async def _handle_unhealthy_service(self, service_name: str, details: Dict):
        """Handle an unhealthy service"""
        # Log incident
        await self.db.self_healing_incidents.insert_one({
            "service": service_name,
            "type": "unhealthy",
            "details": details,
            "timestamp": datetime.now(timezone.utc),
            "resolved": False
        })
        
        # Attempt recovery if registered
        if service_name in self.recovery_actions:
            try:
                recovery_func = self.recovery_actions[service_name]
                await recovery_func(details)
                logger.info(f"Recovery action executed for {service_name}")
            except Exception as e:
                logger.error(f"Recovery action failed for {service_name}: {e}")
    
    async def _check_stuck_jobs(self):
        """Check for and recover stuck jobs"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        stuck_jobs = await self.db.genstudio_jobs.find({
            "status": {"$in": ["PROCESSING", "QUEUED"]},
            "updatedAt": {"$lt": cutoff.isoformat()}
        }, {"_id": 0}).to_list(50)
        
        for job in stuck_jobs:
            try:
                await self._recover_stuck_job(job)
            except Exception as e:
                logger.error(f"Failed to recover stuck job {job.get('id')}: {e}")
    
    async def _recover_stuck_job(self, job: Dict):
        """Attempt to recover a stuck job"""
        job_id = job.get("id")
        user_id = job.get("userId")
        current_retries = job.get("retryCount", 0)
        max_retries = 3
        
        if current_retries >= max_retries:
            # Mark as failed and trigger refund
            await self.db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "FAILED",
                    "errorDetails": "Job stuck and max retries exceeded",
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.warning(f"Job {job_id} marked as failed after max retries")
            
            # Log recovery incident
            await self.db.self_healing_incidents.insert_one({
                "service": "job_recovery",
                "type": "job_failed",
                "job_id": job_id,
                "user_id": user_id,
                "reason": "max_retries_exceeded",
                "timestamp": datetime.now(timezone.utc),
                "resolved": True
            })
        else:
            # Re-queue the job
            await self.db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "QUEUED",
                    "retryCount": current_retries + 1,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Re-queued stuck job {job_id} (retry {current_retries + 1})")
    
    async def _check_failed_payments(self):
        """Check for payment issues that need resolution"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Find successful payments without credit delivery
        undelivered = await self.db.orders.find({
            "status": "SUCCESS",
            "creditsDelivered": {"$ne": True},
            "createdAt": {"$gte": cutoff.isoformat()}
        }).to_list(50)
        
        for order in undelivered:
            try:
                await self._deliver_payment_credits(order)
            except Exception as e:
                logger.error(f"Failed to deliver credits for order {order.get('order_id')}: {e}")
    
    async def _deliver_payment_credits(self, order: Dict):
        """Attempt to deliver credits for a successful payment"""
        order_id = order.get("order_id")
        user_id = order.get("userId") or order.get("user_id")
        credits = order.get("credits", 0)
        
        if not user_id or credits <= 0:
            return
        
        # Add credits to user
        await self.db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Mark order as delivered
        await self.db.orders.update_one(
            {"order_id": order_id},
            {"$set": {
                "creditsDelivered": True,
                "deliveredAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Log incident
        await self.db.self_healing_incidents.insert_one({
            "service": "payment_recovery",
            "type": "credits_delivered",
            "order_id": order_id,
            "user_id": user_id,
            "credits": credits,
            "timestamp": datetime.now(timezone.utc),
            "resolved": True
        })
        
        logger.info(f"Delivered {credits} credits for order {order_id} to user {user_id}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        circuit_states = {}
        for name, cb in self.circuit_breakers.items():
            circuit_states[name] = {
                "state": cb.state,
                "failures": cb.failures,
                "healthy": cb.state == CircuitState.CLOSED
            }
        
        # Get recent incidents
        recent_incidents = await self.db.self_healing_incidents.count_documents({
            "timestamp": {"$gte": datetime.now(timezone.utc) - timedelta(hours=1)}
        })
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "circuit_breakers": circuit_states,
            "recent_incidents_1h": recent_incidents,
            "monitoring_active": self._running
        }


# Singleton holder
_self_healing_system = None

async def get_self_healing_system(db) -> EnhancedSelfHealingSystem:
    """Get or create the self-healing system singleton"""
    global _self_healing_system
    if _self_healing_system is None:
        _self_healing_system = EnhancedSelfHealingSystem(db)
    return _self_healing_system


def with_worker_retry(worker_name: str, max_retries: int = 3):
    """
    Decorator to add retry logic to worker functions
    
    Usage:
        @with_worker_retry("image_generator")
        async def generate_image(params):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = WorkerRetryHandler(max_retries=max_retries)
            result = await handler.execute_with_retry(func, worker_name, *args, **kwargs)
            
            if result["success"]:
                return result["result"]
            else:
                raise Exception(f"Worker {worker_name} failed after {max_retries} retries: {result['error']}")
        
        return wrapper
    return decorator


def with_circuit_breaker(service_name: str, fallback: Callable = None):
    """
    Decorator to wrap function with circuit breaker protection
    
    Usage:
        @with_circuit_breaker("llm_api", fallback=use_cached_response)
        async def call_llm(prompt):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from shared import db
            system = await get_self_healing_system(db)
            cb = system.get_circuit_breaker(service_name)
            
            if not await cb.can_execute():
                if fallback:
                    return await fallback(*args, **kwargs)
                raise Exception(f"Service {service_name} is temporarily unavailable (circuit open)")
            
            try:
                result = await func(*args, **kwargs)
                await cb.record_success()
                return result
            except Exception as e:
                await cb.record_failure()
                if fallback:
                    return await fallback(*args, **kwargs)
                raise
        
        return wrapper
    return decorator
