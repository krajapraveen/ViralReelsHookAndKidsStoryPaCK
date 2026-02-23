"""
Health Check Routes
CreatorStudio AI - Production Grade Health Monitoring
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import os
import sys
import psutil
import asyncio

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, FILE_EXPIRY_MINUTES, get_admin_user

# Import production resilience components
try:
    from utils.production_resilience import (
        HEALTH_MONITOR, DEGRADATION_MANAGER, REQUEST_QUEUE,
        CIRCUIT_BREAKERS, CONNECTION_POOLS
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """Main health check endpoint"""
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Update health monitor
    if RESILIENCE_AVAILABLE:
        await HEALTH_MONITOR.update_metric("cpu_load", cpu_percent / 100)
        await HEALTH_MONITOR.update_metric("memory_usage", memory.percent / 100)
        
        # Check degradation level based on load
        current_load = max(cpu_percent / 100, memory.percent / 100)
        await DEGRADATION_MANAGER.check_and_adjust(current_load)
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_expiry_minutes": FILE_EXPIRY_MINUTES,
        "security": "enabled",
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2)
        }
    }


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready")
async def readiness():
    """Kubernetes readiness probe"""
    try:
        # Check database connection
        await db.command("ping")
        
        # Check if degradation is too severe
        if RESILIENCE_AVAILABLE:
            from utils.production_resilience import DegradationLevel
            if DEGRADATION_MANAGER.current_level == DegradationLevel.MAINTENANCE:
                return {"status": "not_ready", "reason": "maintenance_mode"}
        
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@router.get("/metrics")
async def metrics():
    """Basic metrics endpoint"""
    try:
        user_count = await db.users.count_documents({})
        generation_count = await db.generations.count_documents({})
        genstudio_count = await db.genstudio_jobs.count_documents({})
        
        # Get active job counts
        active_jobs = await db.genstudio_jobs.count_documents({"status": "processing"})
        failed_jobs_24h = await db.genstudio_jobs.count_documents({
            "status": "failed",
            "createdAt": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}
        })
        
        return {
            "users": user_count,
            "generations": generation_count,
            "genstudioJobs": genstudio_count,
            "activeJobs": active_jobs,
            "failedJobs24h": failed_jobs_24h,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/production")
async def production_health():
    """
    Comprehensive production health dashboard
    Shows circuit breakers, queues, degradation status
    """
    if not RESILIENCE_AVAILABLE:
        return {"error": "Production resilience module not available"}
    
    return HEALTH_MONITOR.get_health()


@router.get("/circuit-breakers")
async def circuit_breaker_status(admin: dict = Depends(get_admin_user)):
    """Get status of all circuit breakers (admin only)"""
    if not RESILIENCE_AVAILABLE:
        return {"error": "Production resilience module not available"}
    
    return {
        "circuit_breakers": {
            name: cb.get_status()
            for name, cb in CIRCUIT_BREAKERS.items()
        }
    }


@router.post("/circuit-breakers/{service}/reset")
async def reset_circuit_breaker(service: str, admin: dict = Depends(get_admin_user)):
    """Manually reset a circuit breaker (admin only)"""
    if not RESILIENCE_AVAILABLE:
        return {"error": "Production resilience module not available"}
    
    if service not in CIRCUIT_BREAKERS:
        return {"error": f"Unknown service: {service}"}
    
    cb = CIRCUIT_BREAKERS[service]
    from utils.production_resilience import CircuitState
    cb.state = CircuitState.CLOSED
    cb.failure_count = 0
    cb.success_count = 0
    
    return {"success": True, "message": f"Circuit breaker {service} reset to CLOSED"}


@router.get("/queue-stats")
async def queue_stats():
    """Get request queue statistics"""
    if not RESILIENCE_AVAILABLE:
        return {"error": "Production resilience module not available"}
    
    return REQUEST_QUEUE.get_stats()


@router.get("/degradation")
async def degradation_status():
    """Get current degradation level and disabled features"""
    if not RESILIENCE_AVAILABLE:
        return {"level": "NORMAL", "disabled_features": []}
    
    return DEGRADATION_MANAGER.get_status()
