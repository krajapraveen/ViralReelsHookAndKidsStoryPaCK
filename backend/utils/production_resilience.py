"""
Production Resilience Module
Circuit breakers, connection pooling, request queuing, and graceful degradation
Designed to handle millions of concurrent users
"""
import asyncio
import time
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timezone, timedelta
from collections import deque
from functools import wraps
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import logger


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascade failures
    Automatically opens when failure rate exceeds threshold
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
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """Check if request can proceed"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.last_failure_time and \
                   time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info(f"Circuit breaker {self.name}: OPEN -> HALF_OPEN")
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
            
            return False
    
    async def record_success(self):
        """Record successful execution"""
        async with self._lock:
            self.success_count += 1
            
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name}: HALF_OPEN -> CLOSED (recovered)")
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = max(0, self.failure_count - 1)
    
    async def record_failure(self):
        """Record failed execution"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open returns to open
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name}: HALF_OPEN -> OPEN (failure during recovery)")
            
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker {self.name}: CLOSED -> OPEN (threshold reached: {self.failure_count})")
    
    def get_status(self) -> dict:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": datetime.fromtimestamp(self.last_failure_time, tz=timezone.utc).isoformat() if self.last_failure_time else None
        }


# Global circuit breakers for different services
CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {
    "llm_service": CircuitBreaker("llm_service", failure_threshold=5, recovery_timeout=60),
    "video_generation": CircuitBreaker("video_generation", failure_threshold=3, recovery_timeout=120),
    "image_generation": CircuitBreaker("image_generation", failure_threshold=5, recovery_timeout=60),
    "payment_gateway": CircuitBreaker("payment_gateway", failure_threshold=3, recovery_timeout=30),
    "database": CircuitBreaker("database", failure_threshold=10, recovery_timeout=15),
    "file_storage": CircuitBreaker("file_storage", failure_threshold=5, recovery_timeout=30),
}


def get_circuit_breaker(service: str) -> CircuitBreaker:
    """Get or create circuit breaker for service"""
    if service not in CIRCUIT_BREAKERS:
        CIRCUIT_BREAKERS[service] = CircuitBreaker(service)
    return CIRCUIT_BREAKERS[service]


def with_circuit_breaker(service: str):
    """Decorator to wrap function with circuit breaker"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = get_circuit_breaker(service)
            
            if not await cb.can_execute():
                raise CircuitBreakerOpenError(
                    f"Service {service} is currently unavailable (circuit open)"
                )
            
            try:
                result = await func(*args, **kwargs)
                await cb.record_success()
                return result
            except Exception as e:
                await cb.record_failure()
                raise
        
        return wrapper
    return decorator


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


# =============================================================================
# REQUEST QUEUE WITH PRIORITY
# =============================================================================

class PriorityLevel(Enum):
    CRITICAL = 0   # Admin operations, payments
    HIGH = 1       # Authenticated user requests
    NORMAL = 2     # Standard requests
    LOW = 3        # Background tasks


class RequestQueue:
    """
    Priority request queue with rate limiting and backpressure
    Prevents server overload under high traffic
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        max_concurrent: int = 100,
        timeout: float = 30.0
    ):
        self.max_queue_size = max_queue_size
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        
        self.queues: Dict[PriorityLevel, deque] = {
            level: deque() for level in PriorityLevel
        }
        
        self.active_count = 0
        self.total_queued = 0
        self.total_processed = 0
        self.total_rejected = 0
        
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def enqueue(
        self,
        func: Callable,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        *args,
        **kwargs
    ) -> Any:
        """Add request to queue and wait for execution"""
        async with self._lock:
            total_in_queue = sum(len(q) for q in self.queues.values())
            
            if total_in_queue >= self.max_queue_size:
                self.total_rejected += 1
                raise QueueFullError("Server is at capacity. Please try again later.")
            
            self.total_queued += 1
        
        # Acquire semaphore (limits concurrent executions)
        async with self._semaphore:
            self.active_count += 1
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
                self.total_processed += 1
                return result
            finally:
                self.active_count -= 1
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "active_requests": self.active_count,
            "max_concurrent": self.max_concurrent,
            "total_queued": self.total_queued,
            "total_processed": self.total_processed,
            "total_rejected": self.total_rejected,
            "queue_sizes": {
                level.name: len(queue) 
                for level, queue in self.queues.items()
            }
        }


class QueueFullError(Exception):
    """Raised when request queue is full"""
    pass


# Global request queue
REQUEST_QUEUE = RequestQueue(
    max_queue_size=10000,
    max_concurrent=200,  # Max concurrent generation jobs
    timeout=120.0  # 2 minute timeout for generation
)


# =============================================================================
# CONNECTION POOL MANAGEMENT
# =============================================================================

class ConnectionPool:
    """
    Connection pool for managing database and external API connections
    Prevents connection exhaustion under high load
    """
    
    def __init__(
        self,
        name: str,
        min_size: int = 10,
        max_size: int = 100,
        max_idle_time: float = 300.0
    ):
        self.name = name
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        
        self.active_connections = 0
        self.idle_connections = 0
        self.total_created = 0
        self.total_reused = 0
        
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire connection from pool"""
        async with self._lock:
            if self.idle_connections > 0:
                self.idle_connections -= 1
                self.active_connections += 1
                self.total_reused += 1
                return True
            
            if self.active_connections < self.max_size:
                self.active_connections += 1
                self.total_created += 1
                return True
            
            return False
    
    async def release(self):
        """Release connection back to pool"""
        async with self._lock:
            self.active_connections -= 1
            if self.idle_connections < self.min_size:
                self.idle_connections += 1
    
    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "active": self.active_connections,
            "idle": self.idle_connections,
            "total_created": self.total_created,
            "total_reused": self.total_reused,
            "utilization": f"{(self.active_connections / self.max_size) * 100:.1f}%"
        }


# Connection pools
CONNECTION_POOLS: Dict[str, ConnectionPool] = {
    "mongodb": ConnectionPool("mongodb", min_size=20, max_size=200),
    "llm_api": ConnectionPool("llm_api", min_size=10, max_size=50),
    "storage": ConnectionPool("storage", min_size=10, max_size=100),
}


# =============================================================================
# GRACEFUL DEGRADATION
# =============================================================================

class DegradationLevel(Enum):
    NORMAL = 0       # All features available
    REDUCED = 1      # Non-critical features disabled
    MINIMAL = 2      # Only essential features
    MAINTENANCE = 3  # Maintenance mode


class GracefulDegradation:
    """
    Manages service degradation under high load
    Automatically reduces functionality to maintain core services
    """
    
    def __init__(self):
        self.current_level = DegradationLevel.NORMAL
        self.disabled_features: set = set()
        self.load_threshold = 0.8  # 80% load triggers degradation
        self._lock = asyncio.Lock()
    
    async def check_and_adjust(self, current_load: float):
        """Adjust degradation level based on current load"""
        async with self._lock:
            if current_load >= 0.95:
                await self._set_level(DegradationLevel.MINIMAL)
            elif current_load >= 0.85:
                await self._set_level(DegradationLevel.REDUCED)
            elif current_load <= 0.5:
                await self._set_level(DegradationLevel.NORMAL)
    
    async def _set_level(self, level: DegradationLevel):
        """Set degradation level and update disabled features"""
        if level == self.current_level:
            return
        
        old_level = self.current_level
        self.current_level = level
        
        if level == DegradationLevel.NORMAL:
            self.disabled_features = set()
        elif level == DegradationLevel.REDUCED:
            self.disabled_features = {
                "video_generation",
                "bulk_downloads",
                "analytics_dashboard",
                "activity_monitoring"
            }
        elif level == DegradationLevel.MINIMAL:
            self.disabled_features = {
                "video_generation",
                "image_generation",
                "bulk_downloads",
                "analytics_dashboard",
                "activity_monitoring",
                "story_generation",
                "notifications"
            }
        
        logger.warning(f"Degradation level changed: {old_level.name} -> {level.name}")
    
    def is_feature_available(self, feature: str) -> bool:
        """Check if feature is currently available"""
        return feature not in self.disabled_features
    
    def get_status(self) -> dict:
        return {
            "level": self.current_level.name,
            "disabled_features": list(self.disabled_features)
        }


# Global degradation manager
DEGRADATION_MANAGER = GracefulDegradation()


def require_feature(feature: str):
    """Decorator to check feature availability"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not DEGRADATION_MANAGER.is_feature_available(feature):
                raise FeatureDisabledError(
                    f"Feature '{feature}' is temporarily disabled due to high server load. "
                    "Please try again in a few minutes."
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class FeatureDisabledError(Exception):
    """Raised when feature is disabled due to degradation"""
    pass


# =============================================================================
# HEALTH MONITORING
# =============================================================================

class HealthMonitor:
    """
    Monitors system health and triggers alerts
    """
    
    def __init__(self):
        self.metrics: Dict[str, float] = {
            "cpu_load": 0.0,
            "memory_usage": 0.0,
            "request_rate": 0.0,
            "error_rate": 0.0,
            "response_time_avg": 0.0,
            "queue_depth": 0
        }
        self.alerts: list = []
        self._lock = asyncio.Lock()
    
    async def update_metric(self, name: str, value: float):
        """Update a health metric"""
        async with self._lock:
            self.metrics[name] = value
            
            # Check for alerts
            if name == "error_rate" and value > 0.1:
                self._add_alert("HIGH_ERROR_RATE", f"Error rate at {value*100:.1f}%")
            elif name == "response_time_avg" and value > 5000:
                self._add_alert("SLOW_RESPONSE", f"Avg response time: {value:.0f}ms")
            elif name == "queue_depth" and value > 5000:
                self._add_alert("QUEUE_DEPTH", f"Request queue depth: {value}")
    
    def _add_alert(self, alert_type: str, message: str):
        """Add alert"""
        self.alerts.append({
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_health(self) -> dict:
        """Get overall health status"""
        is_healthy = (
            self.metrics.get("error_rate", 0) < 0.05 and
            self.metrics.get("response_time_avg", 0) < 3000 and
            self.metrics.get("queue_depth", 0) < 3000
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "metrics": self.metrics,
            "recent_alerts": self.alerts[-10:],
            "circuit_breakers": {
                name: cb.get_status() 
                for name, cb in CIRCUIT_BREAKERS.items()
            },
            "degradation": DEGRADATION_MANAGER.get_status(),
            "request_queue": REQUEST_QUEUE.get_stats()
        }


# Global health monitor
HEALTH_MONITOR = HealthMonitor()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'CircuitBreaker',
    'CircuitBreakerOpenError',
    'get_circuit_breaker',
    'with_circuit_breaker',
    'RequestQueue',
    'QueueFullError',
    'REQUEST_QUEUE',
    'ConnectionPool',
    'CONNECTION_POOLS',
    'GracefulDegradation',
    'DegradationLevel',
    'DEGRADATION_MANAGER',
    'require_feature',
    'FeatureDisabledError',
    'HealthMonitor',
    'HEALTH_MONITOR',
    'PriorityLevel'
]
