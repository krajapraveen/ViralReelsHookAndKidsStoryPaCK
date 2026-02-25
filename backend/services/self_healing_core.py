"""
CreatorStudio AI - Self-Healing System Core
============================================
Central module for automatic recovery, monitoring, and resilience.

Features:
- Correlation ID tracking for all requests
- Centralized metrics collection
- Circuit breaker management
- Job state machine
- Auto-recovery orchestration
"""
import asyncio
import time
import uuid
import json
import traceback
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
from functools import wraps
from dataclasses import dataclass, field, asdict
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger

# ============================================
# CORRELATION ID SYSTEM
# ============================================

class CorrelationContext:
    """Thread-local context for request correlation"""
    _context: Dict[str, Any] = {}
    
    @classmethod
    def set(cls, correlation_id: str, user_id: Optional[str] = None, 
            request_type: str = "unknown", metadata: Dict = None):
        cls._context = {
            "correlation_id": correlation_id,
            "user_id": user_id,
            "request_type": request_type,
            "start_time": time.time(),
            "metadata": metadata or {},
            "trace": []
        }
    
    @classmethod
    def get(cls) -> Dict[str, Any]:
        return cls._context.copy()
    
    @classmethod
    def get_id(cls) -> str:
        return cls._context.get("correlation_id", "unknown")
    
    @classmethod
    def add_trace(cls, step: str, status: str = "ok", details: Dict = None):
        if "trace" in cls._context:
            cls._context["trace"].append({
                "step": step,
                "status": status,
                "timestamp": time.time(),
                "details": details or {}
            })
    
    @classmethod
    def get_duration(cls) -> float:
        start = cls._context.get("start_time", time.time())
        return time.time() - start
    
    @classmethod
    def clear(cls):
        cls._context = {}


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing"""
    return f"req_{uuid.uuid4().hex[:16]}_{int(time.time())}"


def generate_idempotency_key(user_id: str, action: str, params_hash: str) -> str:
    """Generate idempotency key to prevent duplicate operations"""
    return f"idem_{user_id}_{action}_{params_hash}"


# ============================================
# METRICS COLLECTION
# ============================================

class MetricsCollector:
    """
    Centralized metrics collection for monitoring and alerting
    Collects: errors, latency, queue depth, success rates
    """
    
    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._start_time = time.time()
    
    async def increment(self, metric: str, value: int = 1, tags: Dict = None):
        """Increment a counter metric"""
        async with self._lock:
            self.counters[metric] += value
            self.metrics[metric].append({
                "type": "counter",
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {}
            })
    
    async def gauge(self, metric: str, value: float, tags: Dict = None):
        """Set a gauge metric (current value)"""
        async with self._lock:
            self.gauges[metric] = value
            self.metrics[metric].append({
                "type": "gauge",
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {}
            })
    
    async def histogram(self, metric: str, value: float, tags: Dict = None):
        """Record a histogram value (for percentiles)"""
        async with self._lock:
            self.histograms[metric].append(value)
            # Keep only last 1000 values per metric
            if len(self.histograms[metric]) > 1000:
                self.histograms[metric] = self.histograms[metric][-1000:]
            
            self.metrics[metric].append({
                "type": "histogram",
                "value": value,
                "timestamp": time.time(),
                "tags": tags or {}
            })
    
    async def record_request(self, endpoint: str, method: str, status_code: int, 
                            duration_ms: float, user_id: Optional[str] = None):
        """Record an API request for monitoring"""
        is_error = status_code >= 400
        
        await self.increment(f"requests.total", tags={"endpoint": endpoint, "method": method})
        await self.increment(f"requests.status.{status_code}")
        
        if is_error:
            await self.increment("requests.errors", tags={"endpoint": endpoint, "status": status_code})
        else:
            await self.increment("requests.success")
        
        await self.histogram("requests.latency_ms", duration_ms, tags={"endpoint": endpoint})
    
    async def record_job(self, job_type: str, status: str, duration_ms: Optional[float] = None):
        """Record a job execution"""
        await self.increment(f"jobs.{status}", tags={"type": job_type})
        if duration_ms:
            await self.histogram(f"jobs.duration_ms", duration_ms, tags={"type": job_type})
    
    async def record_payment(self, event: str, amount: float = 0, success: bool = True):
        """Record a payment event"""
        status = "success" if success else "failed"
        await self.increment(f"payments.{event}.{status}")
        if amount > 0:
            await self.histogram("payments.amount", amount)
    
    def get_error_rate(self, window_seconds: int = 300) -> float:
        """Calculate error rate over time window"""
        cutoff = time.time() - window_seconds
        total = 0
        errors = 0
        
        for entry in self.metrics.get("requests.total", []):
            if entry["timestamp"] >= cutoff:
                total += entry.get("value", 1)
        
        for entry in self.metrics.get("requests.errors", []):
            if entry["timestamp"] >= cutoff:
                errors += entry.get("value", 1)
        
        return (errors / total * 100) if total > 0 else 0.0
    
    def get_percentile(self, metric: str, percentile: int = 95) -> float:
        """Get percentile value for a histogram metric"""
        values = self.histograms.get(metric, [])
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def get_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        async with self._lock:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": time.time() - self._start_time,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "error_rate_5min": self.get_error_rate(300),
                "latency_p95_ms": self.get_percentile("requests.latency_ms", 95),
                "latency_p99_ms": self.get_percentile("requests.latency_ms", 99),
                "jobs_p95_ms": self.get_percentile("jobs.duration_ms", 95)
            }


# Global metrics instance
metrics = MetricsCollector()


# ============================================
# JOB STATE MACHINE
# ============================================

class JobState(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"
    CANCELLED = "cancelled"


class PaymentState(Enum):
    CREATED = "created"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RECONCILING = "reconciling"


@dataclass
class Job:
    """Job representation with state tracking"""
    job_id: str
    user_id: str
    job_type: str  # image, video, text, export
    state: JobState = JobState.PENDING
    correlation_id: str = ""
    idempotency_key: str = ""
    
    # Execution tracking
    attempt: int = 0
    max_attempts: int = 3
    last_error: str = ""
    last_step: str = ""
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Costs
    credits_reserved: int = 0
    credits_charged: int = 0
    
    # Results
    result_url: Optional[str] = None
    fallback_result: Optional[Dict] = None
    
    # Metadata
    params: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["state"] = self.state.value
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Job":
        data["state"] = JobState(data.get("state", "pending"))
        for field in ["created_at", "started_at", "completed_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================
# ALERT SYSTEM
# ============================================

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert representation"""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    metadata: Dict = field(default_factory=dict)


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self):
        self.alerts: deque = deque(maxlen=1000)
        self.alert_rules: List[Dict] = []
        self._lock = asyncio.Lock()
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        self.alert_rules = [
            {
                "name": "high_error_rate",
                "condition": lambda m: m.get_error_rate(300) > 1.0,
                "severity": AlertSeverity.ERROR,
                "title": "High Error Rate",
                "message": "Error rate exceeded 1% for 5 minutes",
                "cooldown_minutes": 5
            },
            {
                "name": "high_latency",
                "condition": lambda m: m.get_percentile("requests.latency_ms", 95) > 5000,
                "severity": AlertSeverity.WARNING,
                "title": "High Latency",
                "message": "P95 latency exceeded 5 seconds",
                "cooldown_minutes": 10
            },
            {
                "name": "payment_failures",
                "condition": lambda m: m.counters.get("payments.webhook.failed", 0) > 5,
                "severity": AlertSeverity.CRITICAL,
                "title": "Payment Webhook Failures",
                "message": "Multiple payment webhook failures detected",
                "cooldown_minutes": 15
            }
        ]
        self._last_alert_times: Dict[str, float] = {}
    
    async def check_rules(self, metrics_collector: MetricsCollector):
        """Check all alert rules against current metrics"""
        for rule in self.alert_rules:
            rule_name = rule["name"]
            cooldown = rule.get("cooldown_minutes", 5) * 60
            
            # Check cooldown
            last_time = self._last_alert_times.get(rule_name, 0)
            if time.time() - last_time < cooldown:
                continue
            
            # Check condition
            try:
                if rule["condition"](metrics_collector):
                    await self.create_alert(
                        severity=rule["severity"],
                        title=rule["title"],
                        message=rule["message"],
                        source=f"rule:{rule_name}"
                    )
                    self._last_alert_times[rule_name] = time.time()
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    async def create_alert(self, severity: AlertSeverity, title: str, message: str,
                          source: str, correlation_id: str = None, metadata: Dict = None) -> Alert:
        """Create a new alert"""
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:12]}",
            severity=severity,
            title=title,
            message=message,
            source=source,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
        
        async with self._lock:
            self.alerts.append(alert)
        
        # Log alert
        log_method = getattr(logger, severity.value, logger.warning)
        log_method(f"ALERT [{severity.value.upper()}] {title}: {message} (correlation_id={correlation_id})")
        
        # Store in database
        try:
            await db.alerts.insert_one({
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "correlation_id": alert.correlation_id,
                "created_at": alert.created_at,
                "acknowledged": False,
                "metadata": alert.metadata
            })
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")
        
        return alert
    
    async def get_active_alerts(self, severity: AlertSeverity = None) -> List[Dict]:
        """Get active (unresolved) alerts"""
        query = {"resolved_at": None}
        if severity:
            query["severity"] = severity.value
        
        try:
            cursor = db.alerts.find(query).sort("created_at", -1).limit(100)
            return await cursor.to_list(length=100)
        except Exception:
            return []
    
    async def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        await db.alerts.update_one(
            {"alert_id": alert_id},
            {"$set": {"acknowledged": True}}
        )
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        await db.alerts.update_one(
            {"alert_id": alert_id},
            {"$set": {"resolved_at": datetime.now(timezone.utc)}}
        )


# Global alert manager
alert_manager = AlertManager()


# ============================================
# INCIDENT LOGGER
# ============================================

class IncidentLogger:
    """
    Centralized incident logging for debugging and audit
    """
    
    @staticmethod
    async def log_incident(
        incident_type: str,
        severity: str,
        description: str,
        correlation_id: str = None,
        user_id: str = None,
        error: Exception = None,
        context: Dict = None,
        resolution: str = None
    ):
        """Log an incident to database"""
        incident = {
            "incident_id": f"inc_{uuid.uuid4().hex[:12]}",
            "type": incident_type,
            "severity": severity,
            "description": description,
            "correlation_id": correlation_id or CorrelationContext.get_id(),
            "user_id": user_id,
            "error_message": str(error) if error else None,
            "error_traceback": traceback.format_exc() if error else None,
            "context": context or {},
            "resolution": resolution,
            "created_at": datetime.now(timezone.utc),
            "trace": CorrelationContext.get().get("trace", [])
        }
        
        try:
            await db.incidents.insert_one(incident)
        except Exception as e:
            logger.error(f"Failed to log incident: {e}")
        
        # Log to application logs
        logger.error(
            f"INCIDENT [{severity}] {incident_type}: {description} "
            f"(correlation_id={incident['correlation_id']}, user={user_id})"
        )
        
        return incident["incident_id"]
    
    @staticmethod
    async def get_recent_incidents(hours: int = 24, incident_type: str = None) -> List[Dict]:
        """Get recent incidents"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = {"created_at": {"$gte": cutoff}}
        if incident_type:
            query["type"] = incident_type
        
        try:
            cursor = db.incidents.find(query).sort("created_at", -1).limit(100)
            return await cursor.to_list(length=100)
        except Exception:
            return []


# ============================================
# SELF-HEALING ORCHESTRATOR
# ============================================

class SelfHealingOrchestrator:
    """
    Main orchestrator for automatic recovery and self-healing
    Coordinates circuit breakers, retries, fallbacks, and alerts
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, "CircuitBreaker"] = {}
        self.job_queues: Dict[str, asyncio.Queue] = {}
        self.recovery_handlers: Dict[str, Callable] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._reconciliation_task: Optional[asyncio.Task] = None
    
    def get_circuit_breaker(self, name: str, 
                           failure_threshold: int = 5,
                           recovery_timeout: float = 30.0) -> "CircuitBreaker":
        """Get or create a circuit breaker"""
        if name not in self.circuit_breakers:
            from utils.production_resilience import CircuitBreaker
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return self.circuit_breakers[name]
    
    def get_queue(self, queue_name: str) -> asyncio.Queue:
        """Get or create a job queue"""
        if queue_name not in self.job_queues:
            self.job_queues[queue_name] = asyncio.Queue(maxsize=1000)
        return self.job_queues[queue_name]
    
    def register_recovery_handler(self, job_type: str, handler: Callable):
        """Register a recovery handler for a job type"""
        self.recovery_handlers[job_type] = handler
    
    async def start_background_tasks(self):
        """Start background monitoring and reconciliation tasks"""
        if not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        if not self._reconciliation_task:
            self._reconciliation_task = asyncio.create_task(self._reconciliation_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Check alert rules
                await alert_manager.check_rules(metrics)
                
                # Update queue depth gauges
                for name, queue in self.job_queues.items():
                    await metrics.gauge(f"queue.{name}.depth", queue.qsize())
                
                # Check circuit breaker states
                for name, cb in self.circuit_breakers.items():
                    state = 1 if cb.state.value == "closed" else 0
                    await metrics.gauge(f"circuit_breaker.{name}.healthy", state)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _reconciliation_loop(self):
        """Background reconciliation loop for payments and jobs"""
        while True:
            try:
                await self._reconcile_payments()
                await self._reconcile_stuck_jobs()
            except Exception as e:
                logger.error(f"Error in reconciliation loop: {e}")
            
            await asyncio.sleep(120)  # Run every 2 minutes
    
    async def _reconcile_payments(self):
        """Reconcile payments that succeeded but weren't delivered"""
        # Find payments in SUCCESS state without credits/subscription delivered
        try:
            stuck_payments = await db.payments.find({
                "status": "SUCCESS",
                "delivered": {"$ne": True},
                "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
            }).to_list(length=100)
            
            for payment in stuck_payments:
                await self._handle_stuck_payment(payment)
                
        except Exception as e:
            logger.error(f"Payment reconciliation error: {e}")
    
    async def _handle_stuck_payment(self, payment: Dict):
        """Handle a payment that succeeded but wasn't delivered"""
        payment_id = payment.get("order_id") or payment.get("_id")
        user_id = payment.get("user_id")
        
        logger.warning(f"Reconciling stuck payment: {payment_id} for user {user_id}")
        
        # Try to deliver credits/subscription
        try:
            credits_amount = payment.get("credits", 0)
            if credits_amount > 0:
                from shared import add_credits
                await add_credits(user_id, credits_amount, f"Reconciled payment {payment_id}")
                
                await db.payments.update_one(
                    {"_id": payment["_id"]},
                    {"$set": {"delivered": True, "reconciled_at": datetime.now(timezone.utc)}}
                )
                
                await IncidentLogger.log_incident(
                    incident_type="payment_reconciliation",
                    severity="info",
                    description=f"Auto-reconciled payment {payment_id}",
                    user_id=user_id,
                    context={"credits": credits_amount}
                )
        except Exception as e:
            await IncidentLogger.log_incident(
                incident_type="payment_reconciliation_failed",
                severity="error",
                description=f"Failed to reconcile payment {payment_id}",
                user_id=user_id,
                error=e
            )
    
    async def _reconcile_stuck_jobs(self):
        """Find and recover stuck jobs"""
        try:
            # Find jobs stuck in PROCESSING for too long
            stuck_jobs = await db.jobs.find({
                "state": {"$in": ["processing", "queued"]},
                "updated_at": {"$lt": datetime.now(timezone.utc) - timedelta(minutes=30)}
            }).to_list(length=100)
            
            for job_data in stuck_jobs:
                job = Job.from_dict(job_data)
                await self._recover_stuck_job(job)
                
        except Exception as e:
            logger.error(f"Job reconciliation error: {e}")
    
    async def _recover_stuck_job(self, job: Job):
        """Attempt to recover a stuck job"""
        logger.warning(f"Recovering stuck job: {job.job_id} (type={job.job_type})")
        
        if job.attempt < job.max_attempts:
            # Re-queue the job
            job.state = JobState.RETRYING
            job.attempt += 1
            await self._save_job(job)
            
            queue = self.get_queue(job.job_type)
            await queue.put(job)
            
            await metrics.increment("jobs.recovered")
        else:
            # Execute fallback
            job.state = JobState.FALLBACK
            await self._execute_fallback(job)
    
    async def _execute_fallback(self, job: Job):
        """Execute fallback for a failed job"""
        handler = self.recovery_handlers.get(job.job_type)
        if handler:
            try:
                fallback_result = await handler(job)
                job.fallback_result = fallback_result
                job.state = JobState.COMPLETED
            except Exception as e:
                job.state = JobState.FAILED
                job.last_error = str(e)
        else:
            job.state = JobState.FAILED
            job.last_error = "No fallback handler available"
        
        await self._save_job(job)
        await metrics.increment(f"jobs.fallback.{job.job_type}")
    
    async def _save_job(self, job: Job):
        """Save job state to database"""
        job_dict = job.to_dict()
        job_dict["updated_at"] = datetime.now(timezone.utc)
        
        await db.jobs.update_one(
            {"job_id": job.job_id},
            {"$set": job_dict},
            upsert=True
        )


# Global orchestrator instance
orchestrator = SelfHealingOrchestrator()


# ============================================
# DECORATOR UTILITIES
# ============================================

def with_correlation(func):
    """Decorator to add correlation tracking to async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        correlation_id = kwargs.get("correlation_id") or generate_correlation_id()
        CorrelationContext.set(correlation_id)
        
        try:
            result = await func(*args, **kwargs)
            CorrelationContext.add_trace(func.__name__, "success")
            return result
        except Exception as e:
            CorrelationContext.add_trace(func.__name__, "error", {"error": str(e)})
            raise
        finally:
            CorrelationContext.clear()
    
    return wrapper


def with_retry(max_attempts: int = 3, backoff_base: float = 1.0, 
               retryable_exceptions: tuple = (Exception,)):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        wait_time = backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"after {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                        await metrics.increment("retries.total")
                    else:
                        await metrics.increment("retries.exhausted")
            
            raise last_exception
        
        return wrapper
    return decorator


def with_circuit_breaker(breaker_name: str, fallback: Callable = None):
    """Decorator to wrap function with circuit breaker"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = orchestrator.get_circuit_breaker(breaker_name)
            
            if not await cb.can_execute():
                await metrics.increment(f"circuit_breaker.{breaker_name}.rejected")
                
                if fallback:
                    return await fallback(*args, **kwargs)
                else:
                    raise Exception(f"Service {breaker_name} is temporarily unavailable")
            
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


def with_idempotency(key_generator: Callable):
    """Decorator to ensure idempotent execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate idempotency key
            idem_key = key_generator(*args, **kwargs)
            
            # Check if already executed
            existing = await db.idempotency_keys.find_one({"key": idem_key})
            if existing:
                logger.info(f"Idempotent request detected: {idem_key}")
                await metrics.increment("idempotency.cache_hit")
                return existing.get("result")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store result
            await db.idempotency_keys.insert_one({
                "key": idem_key,
                "result": result,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)
            })
            await metrics.increment("idempotency.cache_miss")
            
            return result
        
        return wrapper
    return decorator


# ============================================
# INITIALIZATION
# ============================================

async def initialize_self_healing():
    """Initialize the self-healing system"""
    logger.info("Initializing self-healing system...")
    
    # Create database indexes
    try:
        await db.alerts.create_index("created_at")
        await db.alerts.create_index("severity")
        await db.incidents.create_index("created_at")
        await db.incidents.create_index("correlation_id")
        await db.jobs.create_index("job_id", unique=True)
        await db.jobs.create_index([("state", 1), ("updated_at", 1)])
        await db.idempotency_keys.create_index("key", unique=True)
        await db.idempotency_keys.create_index("expires_at", expireAfterSeconds=0)
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")
    
    # Start background tasks
    await orchestrator.start_background_tasks()
    
    logger.info("Self-healing system initialized")
