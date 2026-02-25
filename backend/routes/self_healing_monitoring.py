"""
CreatorStudio AI - Self-Healing Monitoring API
===============================================
API endpoints for monitoring dashboard, alerts, and system health.

Features:
- Real-time metrics dashboard
- Alert management
- Incident tracking
- System health status
- Recovery status
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user, get_current_user
from services.self_healing_core import (
    metrics, alert_manager, IncidentLogger, orchestrator,
    AlertSeverity, CorrelationContext
)
from services.payment_recovery_service import PaymentHealthMonitor
from services.download_recovery_service import StorageHealthService

router = APIRouter(prefix="/monitoring", tags=["Self-Healing Monitoring"])


# ============================================
# DASHBOARD ENDPOINTS
# ============================================

@router.get("/dashboard")
async def get_monitoring_dashboard(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get comprehensive monitoring dashboard data
    """
    try:
        # Collect all metrics
        metrics_snapshot = await metrics.get_snapshot()
        payment_health = await PaymentHealthMonitor.check_health()
        storage_health = await StorageHealthService.check_storage_health()
        
        # Get active alerts
        active_alerts = await alert_manager.get_active_alerts()
        
        # Get recent incidents
        recent_incidents = await IncidentLogger.get_recent_incidents(hours=24)
        
        # Get circuit breaker statuses
        circuit_breakers = {}
        for name, cb in orchestrator.circuit_breakers.items():
            circuit_breakers[name] = {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time
            }
        
        # Get queue depths
        queue_depths = {}
        for name, queue in orchestrator.job_queues.items():
            queue_depths[name] = queue.qsize() if hasattr(queue, 'qsize') else 0
        
        # Calculate overall system health
        system_health = "healthy"
        health_issues = []
        
        if metrics_snapshot.get("error_rate_5min", 0) > 5:
            system_health = "critical"
            health_issues.append("High error rate")
        elif metrics_snapshot.get("error_rate_5min", 0) > 1:
            system_health = "degraded"
            health_issues.append("Elevated error rate")
        
        if payment_health.get("status") == "critical":
            system_health = "critical"
            health_issues.append("Payment system critical")
        elif payment_health.get("status") == "degraded":
            if system_health == "healthy":
                system_health = "degraded"
            health_issues.append("Payment system degraded")
        
        if storage_health.get("overall") == "critical":
            system_health = "critical"
            health_issues.append("Storage critical")
        elif storage_health.get("overall") == "degraded":
            if system_health == "healthy":
                system_health = "degraded"
            health_issues.append("Storage degraded")
        
        # Count open circuit breakers
        open_circuits = sum(1 for cb in circuit_breakers.values() if cb["state"] == "open")
        if open_circuits > 0:
            if system_health == "healthy":
                system_health = "degraded"
            health_issues.append(f"{open_circuits} circuit breaker(s) open")
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_health": system_health,
            "health_issues": health_issues,
            "metrics": metrics_snapshot,
            "payment_health": payment_health,
            "storage_health": storage_health,
            "circuit_breakers": circuit_breakers,
            "queue_depths": queue_depths,
            "active_alerts_count": len(active_alerts),
            "recent_incidents_count": len(recent_incidents),
            "alerts": active_alerts[:10],  # Latest 10 alerts
            "incidents": recent_incidents[:10]  # Latest 10 incidents
        }
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_system_health():
    """
    Quick health check endpoint (no auth required for monitoring systems)
    """
    try:
        error_rate = metrics.get_error_rate(60)  # Last minute
        
        # Quick checks
        checks = {
            "api": "healthy",
            "database": "unknown",
            "error_rate_ok": error_rate < 5
        }
        
        # Database check
        try:
            await db.command("ping")
            checks["database"] = "healthy"
        except Exception:
            checks["database"] = "unhealthy"
        
        overall = "healthy"
        if checks["database"] != "healthy":
            overall = "critical"
        elif not checks["error_rate_ok"]:
            overall = "degraded"
        
        return {
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "error_rate_1min": round(error_rate, 2)
        }
        
    except Exception as e:
        return {
            "status": "critical",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================
# METRICS ENDPOINTS
# ============================================

@router.get("/metrics")
async def get_metrics(
    window_minutes: int = Query(default=5, ge=1, le=60),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed metrics
    """
    snapshot = await metrics.get_snapshot()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "window_minutes": window_minutes,
        "metrics": snapshot,
        "percentiles": {
            "latency_p50": metrics.get_percentile("requests.latency_ms", 50),
            "latency_p95": metrics.get_percentile("requests.latency_ms", 95),
            "latency_p99": metrics.get_percentile("requests.latency_ms", 99),
            "jobs_p50": metrics.get_percentile("jobs.duration_ms", 50),
            "jobs_p95": metrics.get_percentile("jobs.duration_ms", 95)
        }
    }


@router.get("/metrics/requests")
async def get_request_metrics(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get request metrics over time
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Aggregate request metrics from database
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {
                "hour": {"$hour": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"}
            },
            "total": {"$sum": 1},
            "errors": {"$sum": {"$cond": [{"$gte": ["$status_code", 400]}, 1, 0]}},
            "avg_latency": {"$avg": "$latency_ms"}
        }},
        {"$sort": {"_id.day": 1, "_id.hour": 1}}
    ]
    
    try:
        results = await db.request_logs.aggregate(pipeline).to_list(length=200)
    except Exception:
        results = []
    
    return {
        "hours": hours,
        "data": results,
        "current": {
            "total": metrics.counters.get("requests.total", 0),
            "errors": metrics.counters.get("requests.errors", 0),
            "error_rate": metrics.get_error_rate(300)
        }
    }


# ============================================
# ALERTS ENDPOINTS
# ============================================

@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    resolved: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get alerts
    """
    query = {}
    
    if severity:
        query["severity"] = severity
    
    if not resolved:
        query["resolved_at"] = None
    
    try:
        cursor = db.alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)
        
        return {
            "count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Acknowledge an alert
    """
    await alert_manager.acknowledge_alert(alert_id)
    return {"success": True, "alert_id": alert_id}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Resolve an alert
    """
    await alert_manager.resolve_alert(alert_id)
    return {"success": True, "alert_id": alert_id}


# ============================================
# INCIDENTS ENDPOINTS
# ============================================

@router.get("/incidents")
async def get_incidents(
    hours: int = Query(default=24, ge=1, le=168),
    incident_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get incidents
    """
    incidents = await IncidentLogger.get_recent_incidents(hours, incident_type)
    
    return {
        "hours": hours,
        "count": len(incidents),
        "incidents": incidents[:limit]
    }


@router.get("/incidents/{incident_id}")
async def get_incident_detail(
    incident_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed incident information
    """
    incident = await db.incidents.find_one({"incident_id": incident_id})
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    incident["_id"] = str(incident["_id"])
    return incident


# ============================================
# CIRCUIT BREAKERS ENDPOINTS
# ============================================

@router.get("/circuit-breakers")
async def get_circuit_breakers(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get circuit breaker statuses
    """
    breakers = {}
    
    for name, cb in orchestrator.circuit_breakers.items():
        breakers[name] = {
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "success_count": cb.success_count,
            "last_failure_time": cb.last_failure_time,
            "failure_threshold": cb.failure_threshold,
            "recovery_timeout": cb.recovery_timeout
        }
    
    return {
        "circuit_breakers": breakers,
        "summary": {
            "total": len(breakers),
            "closed": sum(1 for b in breakers.values() if b["state"] == "closed"),
            "open": sum(1 for b in breakers.values() if b["state"] == "open"),
            "half_open": sum(1 for b in breakers.values() if b["state"] == "half_open")
        }
    }


@router.post("/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Manually reset a circuit breaker
    """
    if name not in orchestrator.circuit_breakers:
        raise HTTPException(status_code=404, detail="Circuit breaker not found")
    
    cb = orchestrator.circuit_breakers[name]
    async with cb._lock:
        cb.state = cb.state.__class__.CLOSED
        cb.failure_count = 0
        cb.success_count = 0
    
    logger.info(f"Circuit breaker {name} manually reset by {current_user.get('email')}")
    
    return {"success": True, "name": name, "new_state": "closed"}


# ============================================
# JOBS ENDPOINTS
# ============================================

@router.get("/jobs")
async def get_jobs(
    state: Optional[str] = None,
    job_type: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get job statuses
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = {"created_at": {"$gte": cutoff}}
    
    if state:
        query["state"] = state
    if job_type:
        query["job_type"] = job_type
    
    try:
        cursor = db.jobs.find(query).sort("created_at", -1).limit(limit)
        jobs = await cursor.to_list(length=limit)
        
        for job in jobs:
            job["_id"] = str(job["_id"])
        
        # Get summary
        summary_pipeline = [
            {"$match": {"created_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$state",
                "count": {"$sum": 1}
            }}
        ]
        summary_results = await db.jobs.aggregate(summary_pipeline).to_list(length=10)
        summary = {r["_id"]: r["count"] for r in summary_results}
        
        return {
            "hours": hours,
            "count": len(jobs),
            "summary": summary,
            "jobs": jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/queues")
async def get_job_queues(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get job queue depths
    """
    queues = {}
    
    for name, queue in orchestrator.job_queues.items():
        queues[name] = {
            "depth": queue.qsize() if hasattr(queue, 'qsize') else 0,
            "maxsize": queue.maxsize if hasattr(queue, 'maxsize') else 0
        }
    
    return {"queues": queues}


# ============================================
# PAYMENTS ENDPOINTS
# ============================================

@router.get("/payments/health")
async def get_payment_health(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get payment system health
    """
    return await PaymentHealthMonitor.check_health()


@router.get("/payments/reconciliation")
async def get_reconciliation_status(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get payment reconciliation status
    """
    # Get stuck payments
    stuck = await db.payment_records.find({
        "state": "success",
        "delivered": False
    }).to_list(length=100)
    
    # Get recently reconciled
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    reconciled = await db.payment_records.count_documents({
        "reconciled_at": {"$gte": day_ago}
    })
    
    # Get recent refunds
    refunds = await db.payment_records.count_documents({
        "state": "refunded",
        "refunded_at": {"$gte": day_ago}
    })
    
    return {
        "stuck_payments": len(stuck),
        "reconciled_24h": reconciled,
        "refunds_24h": refunds,
        "stuck_details": [
            {
                "order_id": p.get("order_id"),
                "user_id": p.get("user_id"),
                "amount": p.get("amount"),
                "created_at": p.get("created_at"),
                "attempts": p.get("reconciliation_attempts", 0)
            }
            for p in stuck[:10]
        ]
    }


@router.post("/payments/{order_id}/reconcile")
async def manual_reconcile_payment(
    order_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Manually trigger reconciliation for a payment
    """
    from services.payment_recovery_service import Payment, PaymentDeliveryService
    
    payment_data = await db.payment_records.find_one({"order_id": order_id})
    
    if not payment_data:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = Payment.from_dict(payment_data)
    result = await PaymentDeliveryService.deliver_payment(payment)
    
    logger.info(f"Manual reconciliation for {order_id} by {current_user.get('email')}: {result}")
    
    return result


# ============================================
# STORAGE ENDPOINTS
# ============================================

@router.get("/storage/health")
async def get_storage_health(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get storage system health
    """
    return await StorageHealthService.check_storage_health()



# ============================================
# CLIENT ERROR LOGGING
# ============================================

class ClientErrorRequest:
    """Model for client error logging"""
    pass

from pydantic import BaseModel
from typing import Optional

class ClientErrorLog(BaseModel):
    error: str
    stack: Optional[str] = None
    componentStack: Optional[str] = None
    url: str
    userAgent: str
    timestamp: str

@router.post("/client-error")
async def log_client_error(
    error: ClientErrorLog,
    current_user: dict = Depends(get_current_user)
):
    """
    Log client-side errors for monitoring
    """
    user_id = str(current_user.get("_id", "anonymous"))
    
    try:
        await db.client_errors.insert_one({
            "user_id": user_id,
            "error": error.error,
            "stack": error.stack,
            "component_stack": error.componentStack,
            "url": error.url,
            "user_agent": error.userAgent,
            "timestamp": error.timestamp,
            "created_at": datetime.now(timezone.utc)
        })
        
        await metrics.increment("client_errors.total")
        
    except Exception as e:
        logger.warning(f"Failed to log client error: {e}")
    
    return {"status": "logged"}
