"""
Enhanced Auto-Scaling & Self-Healing Service
Implements dynamic worker scaling, circuit breakers, and reconciliation jobs
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if requests can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._transition_to_half_open()
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls
        
        return False
    
    def record_success(self):
        """Record a successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self._transition_to_closed()
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to open state"""
        logger.warning(f"Circuit {self.name} opened after {self.failure_count} failures")
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.success_count = 0
    
    def _transition_to_half_open(self):
        """Transition to half-open state"""
        logger.info(f"Circuit {self.name} entering half-open state")
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
    
    def _transition_to_closed(self):
        """Transition to closed state"""
        logger.info(f"Circuit {self.name} recovered and closed")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0
        self.success_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "can_execute": self.can_execute()
        }
    
    def get_fallback_response(self) -> Dict[str, Any]:
        """Get fallback response when circuit is open"""
        return {
            "success": False,
            "error": "service_unavailable",
            "message": f"Service temporarily unavailable. Please try again in {self.recovery_timeout} seconds.",
            "retry_after": self.recovery_timeout
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self.circuits: Dict[str, CircuitBreaker] = {}
        self._initialize_default_circuits()
    
    def _initialize_default_circuits(self):
        """Initialize circuit breakers for known services"""
        self.circuits["gemini"] = CircuitBreaker(
            name="gemini",
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        self.circuits["openai"] = CircuitBreaker(
            name="openai",
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        self.circuits["sora"] = CircuitBreaker(
            name="sora",
            failure_threshold=3,
            recovery_timeout=120,  # Video gen needs longer recovery
            half_open_max_calls=2
        )
        self.circuits["elevenlabs"] = CircuitBreaker(
            name="elevenlabs",
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        self.circuits["storage"] = CircuitBreaker(
            name="storage",
            failure_threshold=10,
            recovery_timeout=30,
            half_open_max_calls=5
        )
        self.circuits["payment"] = CircuitBreaker(
            name="payment",
            failure_threshold=3,
            recovery_timeout=120,
            half_open_max_calls=2
        )
    
    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.circuits:
            self.circuits[name] = CircuitBreaker(name=name)
        return self.circuits[name]
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        return {name: cb.get_status() for name, cb in self.circuits.items()}
    
    async def execute_with_circuit(
        self, 
        circuit_name: str, 
        func: Callable,
        fallback: Callable = None,
        *args, 
        **kwargs
    ) -> Any:
        """Execute a function with circuit breaker protection"""
        circuit = self.get_circuit(circuit_name)
        
        if not circuit.can_execute():
            logger.warning(f"Circuit {circuit_name} is open, using fallback")
            if fallback:
                return await fallback(*args, **kwargs)
            return circuit.get_fallback_response()
        
        try:
            result = await func(*args, **kwargs)
            circuit.record_success()
            return result
        except Exception as e:
            circuit.record_failure()
            logger.error(f"Circuit {circuit_name} failure: {e}")
            if fallback:
                return await fallback(*args, **kwargs)
            raise


class DynamicScaler:
    """Dynamic worker scaling based on queue metrics"""
    
    def __init__(self, db, min_workers: int = 1, max_workers: int = 10):
        self.db = db
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.current_workers = min_workers
        self.scaling_history: List[Dict] = []
        
        # Scaling thresholds
        self.scale_up_queue_threshold = 10
        self.scale_up_age_threshold = 60  # seconds
        self.scale_down_idle_threshold = 300  # seconds
    
    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Get current queue metrics"""
        # Count jobs by status
        queued = await self.db.genstudio_jobs.count_documents({"status": "QUEUED"})
        processing = await self.db.genstudio_jobs.count_documents({"status": "PROCESSING"})
        
        # Get oldest queued job
        oldest_job = await self.db.genstudio_jobs.find_one(
            {"status": "QUEUED"},
            {"_id": 0, "createdAt": 1},
            sort=[("createdAt", 1)]
        )
        
        oldest_age = 0
        if oldest_job and oldest_job.get("createdAt"):
            try:
                created = datetime.fromisoformat(oldest_job["createdAt"].replace("Z", "+00:00"))
                oldest_age = (datetime.now(timezone.utc) - created).total_seconds()
            except:
                pass
        
        return {
            "queue_depth": queued,
            "processing": processing,
            "oldest_job_age_seconds": oldest_age,
            "current_workers": self.current_workers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def evaluate_scaling(self) -> Dict[str, Any]:
        """Evaluate if scaling is needed"""
        metrics = await self.get_queue_metrics()
        
        decision = {
            "action": "none",
            "reason": "metrics within normal range",
            "metrics": metrics
        }
        
        queue_depth = metrics["queue_depth"]
        oldest_age = metrics["oldest_job_age_seconds"]
        
        # Scale up conditions
        if queue_depth > self.scale_up_queue_threshold:
            if self.current_workers < self.max_workers:
                decision["action"] = "scale_up"
                decision["reason"] = f"Queue depth {queue_depth} exceeds threshold {self.scale_up_queue_threshold}"
        elif oldest_age > self.scale_up_age_threshold:
            if self.current_workers < self.max_workers:
                decision["action"] = "scale_up"
                decision["reason"] = f"Oldest job age {oldest_age}s exceeds threshold {self.scale_up_age_threshold}s"
        
        # Scale down conditions
        elif queue_depth == 0 and metrics["processing"] == 0:
            if self.current_workers > self.min_workers:
                decision["action"] = "scale_down"
                decision["reason"] = "No jobs in queue or processing"
        
        return decision
    
    async def apply_scaling_decision(self, decision: Dict[str, Any]) -> bool:
        """Apply a scaling decision"""
        action = decision.get("action", "none")
        
        if action == "none":
            return False
        
        old_workers = self.current_workers
        
        if action == "scale_up":
            self.current_workers = min(self.current_workers + 1, self.max_workers)
        elif action == "scale_down":
            self.current_workers = max(self.current_workers - 1, self.min_workers)
        
        if old_workers != self.current_workers:
            self.scaling_history.append({
                "action": action,
                "from": old_workers,
                "to": self.current_workers,
                "reason": decision.get("reason"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.info(f"Scaled workers from {old_workers} to {self.current_workers}: {decision.get('reason')}")
            return True
        
        return False
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status"""
        return {
            "current_workers": self.current_workers,
            "min_workers": self.min_workers,
            "max_workers": self.max_workers,
            "recent_history": self.scaling_history[-10:] if self.scaling_history else [],
            "thresholds": {
                "scale_up_queue": self.scale_up_queue_threshold,
                "scale_up_age_seconds": self.scale_up_age_threshold,
                "scale_down_idle_seconds": self.scale_down_idle_threshold
            }
        }


class SelfHealingReconciler:
    """Reconciliation jobs for self-healing"""
    
    def __init__(self, db):
        self.db = db
        self.last_run: Optional[datetime] = None
        self.run_interval = 300  # 5 minutes
    
    async def reconcile_stuck_jobs(self, max_age_minutes: int = 30) -> Dict[str, Any]:
        """Find and retry stuck processing jobs"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        
        # Find stuck jobs
        stuck_jobs = await self.db.genstudio_jobs.find({
            "status": "PROCESSING",
            "startedAt": {"$lt": cutoff.isoformat()}
        }, {"_id": 0, "id": 1, "userId": 1, "jobType": 1, "startedAt": 1}).to_list(100)
        
        results = {
            "found": len(stuck_jobs),
            "requeued": 0,
            "failed": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for job in stuck_jobs:
            try:
                # Check retry count
                job_data = await self.db.genstudio_jobs.find_one(
                    {"id": job["id"]},
                    {"_id": 0, "retryCount": 1}
                )
                retry_count = job_data.get("retryCount", 0) if job_data else 0
                
                if retry_count >= 3:
                    # Move to failed
                    await self.db.genstudio_jobs.update_one(
                        {"id": job["id"]},
                        {"$set": {
                            "status": "FAILED",
                            "errorMessage": "Job stuck for too long after multiple retries",
                            "failedAt": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    results["failed"] += 1
                else:
                    # Requeue
                    await self.db.genstudio_jobs.update_one(
                        {"id": job["id"]},
                        {
                            "$set": {
                                "status": "QUEUED",
                                "lastError": "Requeued after being stuck",
                                "requeuedAt": datetime.now(timezone.utc).isoformat()
                            },
                            "$inc": {"retryCount": 1}
                        }
                    )
                    results["requeued"] += 1
                    logger.info(f"Requeued stuck job {job['id']}")
            
            except Exception as e:
                logger.error(f"Error reconciling stuck job {job['id']}: {e}")
        
        return results
    
    async def reconcile_payment_issues(self) -> Dict[str, Any]:
        """Find and fix payment reconciliation issues"""
        results = {
            "paid_not_delivered": 0,
            "credits_mismatch": 0,
            "fixed": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Find paid orders without credited users
        paid_orders = await self.db.orders.find({
            "status": "PAID",
            "credited": {"$ne": True}
        }, {"_id": 0}).limit(50).to_list(50)
        
        results["paid_not_delivered"] = len(paid_orders)
        
        for order in paid_orders:
            try:
                user_id = order.get("userId")
                credits = order.get("credits", 0)
                
                if user_id and credits > 0:
                    # Credit the user
                    await self.db.users.update_one(
                        {"id": user_id},
                        {"$inc": {"credits": credits}}
                    )
                    
                    # Mark order as credited
                    await self.db.orders.update_one(
                        {"order_id": order.get("order_id")},
                        {"$set": {
                            "credited": True,
                            "reconciledAt": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    results["fixed"] += 1
                    logger.info(f"Reconciled payment {order.get('order_id')}: credited {credits} to user {user_id}")
            
            except Exception as e:
                logger.error(f"Error reconciling payment {order.get('order_id')}: {e}")
        
        return results
    
    async def run_full_reconciliation(self) -> Dict[str, Any]:
        """Run all reconciliation tasks"""
        self.last_run = datetime.now(timezone.utc)
        
        results = {
            "stuck_jobs": await self.reconcile_stuck_jobs(),
            "payments": await self.reconcile_payment_issues(),
            "timestamp": self.last_run.isoformat()
        }
        
        logger.info(f"Self-healing reconciliation complete: {results}")
        return results


# Global instances
_circuit_manager: Optional[CircuitBreakerManager] = None
_dynamic_scaler: Optional[DynamicScaler] = None
_self_healer: Optional[SelfHealingReconciler] = None


def get_circuit_manager() -> CircuitBreakerManager:
    """Get or create circuit breaker manager"""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager


async def get_dynamic_scaler(db) -> DynamicScaler:
    """Get or create dynamic scaler"""
    global _dynamic_scaler
    if _dynamic_scaler is None:
        _dynamic_scaler = DynamicScaler(db)
    return _dynamic_scaler


async def get_self_healer(db) -> SelfHealingReconciler:
    """Get or create self-healer"""
    global _self_healer
    if _self_healer is None:
        _self_healer = SelfHealingReconciler(db)
    return _self_healer
