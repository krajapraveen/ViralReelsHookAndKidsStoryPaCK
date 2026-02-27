"""
System Resilience Dashboard API Routes
======================================
Real-time dashboard showing:
- Auto-refund statistics
- Self-healing incidents
- Circuit breaker status
- Worker retry metrics
- Payment reconciliation status
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_admin_user, get_current_user

router = APIRouter(prefix="/system-resilience", tags=["System Resilience"])


@router.get("/dashboard")
async def get_resilience_dashboard(
    admin: dict = Depends(get_admin_user)
):
    """
    Get comprehensive system resilience dashboard data
    Admin-only endpoint
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # Auto-refund statistics
    refund_stats_24h = await _get_refund_stats(last_24h)
    refund_stats_7d = await _get_refund_stats(last_7d)
    
    # Self-healing incidents
    incidents_24h = await _get_incident_stats(last_24h)
    incidents_7d = await _get_incident_stats(last_7d)
    
    # Circuit breaker status
    circuit_status = await _get_circuit_breaker_status()
    
    # Worker retry metrics
    worker_metrics = await _get_worker_retry_metrics(last_24h)
    
    # Payment reconciliation status
    payment_recon = await _get_payment_reconciliation_status(last_24h)
    
    # System health score (0-100)
    health_score = _calculate_health_score(
        refund_stats_24h, incidents_24h, circuit_status, payment_recon
    )
    
    return {
        "timestamp": now.isoformat(),
        "health_score": health_score,
        "health_status": _get_health_status(health_score),
        "auto_refunds": {
            "last_24h": refund_stats_24h,
            "last_7d": refund_stats_7d
        },
        "self_healing": {
            "incidents_24h": incidents_24h,
            "incidents_7d": incidents_7d
        },
        "circuit_breakers": circuit_status,
        "worker_retries": worker_metrics,
        "payment_reconciliation": payment_recon
    }


@router.get("/auto-refunds")
async def get_auto_refund_details(
    days: int = 7,
    admin: dict = Depends(get_admin_user)
):
    """Get detailed auto-refund statistics"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get refund logs
    refunds = await db.auto_refund_logs.find({
        "timestamp": {"$gte": start_date}
    }, {"_id": 0}).sort("timestamp", -1).to_list(500)
    
    # Group by reason
    by_reason = {}
    by_feature = {}
    daily_totals = {}
    
    for refund in refunds:
        reason = refund.get("reason", "unknown")
        feature = refund.get("feature", "unknown")
        credits = refund.get("credits_refunded", 0)
        date_key = refund.get("timestamp", datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        
        by_reason[reason] = by_reason.get(reason, {"count": 0, "credits": 0})
        by_reason[reason]["count"] += 1
        by_reason[reason]["credits"] += credits
        
        by_feature[feature] = by_feature.get(feature, {"count": 0, "credits": 0})
        by_feature[feature]["count"] += 1
        by_feature[feature]["credits"] += credits
        
        daily_totals[date_key] = daily_totals.get(date_key, {"count": 0, "credits": 0})
        daily_totals[date_key]["count"] += 1
        daily_totals[date_key]["credits"] += credits
    
    return {
        "period_days": days,
        "total_refunds": len(refunds),
        "total_credits_refunded": sum(r.get("credits_refunded", 0) for r in refunds),
        "by_reason": [{"reason": k, **v} for k, v in by_reason.items()],
        "by_feature": [{"feature": k, **v} for k, v in by_feature.items()],
        "daily_totals": [{"date": k, **v} for k, v in sorted(daily_totals.items())],
        "recent_refunds": refunds[:20]
    }


@router.get("/self-healing/incidents")
async def get_self_healing_incidents(
    days: int = 7,
    severity: Optional[str] = None,
    admin: dict = Depends(get_admin_user)
):
    """Get self-healing incident history"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = {"timestamp": {"$gte": start_date}}
    if severity:
        query["severity"] = severity
    
    incidents = await db.self_healing_incidents.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).to_list(500)
    
    # Group by type
    by_type = {}
    by_service = {}
    resolved_count = 0
    
    for incident in incidents:
        inc_type = incident.get("type", "unknown")
        service = incident.get("service", "unknown")
        
        by_type[inc_type] = by_type.get(inc_type, 0) + 1
        by_service[service] = by_service.get(service, 0) + 1
        
        if incident.get("resolved"):
            resolved_count += 1
    
    resolution_rate = (resolved_count / len(incidents) * 100) if incidents else 100
    
    return {
        "period_days": days,
        "total_incidents": len(incidents),
        "resolved_count": resolved_count,
        "resolution_rate": round(resolution_rate, 1),
        "by_type": [{"type": k, "count": v} for k, v in by_type.items()],
        "by_service": [{"service": k, "count": v} for k, v in by_service.items()],
        "recent_incidents": incidents[:20]
    }


@router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    admin: dict = Depends(get_admin_user)
):
    """Get current circuit breaker status for all services"""
    # Try to get from enhanced self-healing system
    try:
        from services.enhanced_self_healing_system import get_self_healing_system
        system = await get_self_healing_system(db)
        
        breakers = {}
        for name, cb in system.circuit_breakers.items():
            breakers[name] = {
                "state": cb.state,
                "failures": cb.failures,
                "successes": cb.successes,
                "healthy": cb.state == "closed",
                "failure_threshold": cb.failure_threshold,
                "recovery_timeout": cb.recovery_timeout
            }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "circuit_breakers": breakers,
            "total_services": len(breakers),
            "healthy_count": sum(1 for b in breakers.values() if b["healthy"]),
            "degraded_count": sum(1 for b in breakers.values() if not b["healthy"])
        }
    except Exception as e:
        # Return default status if system not initialized
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "circuit_breakers": {
                "llm_api": {"state": "closed", "healthy": True},
                "image_gen": {"state": "closed", "healthy": True},
                "video_gen": {"state": "closed", "healthy": True},
                "payment": {"state": "closed", "healthy": True},
                "database": {"state": "closed", "healthy": True}
            },
            "total_services": 5,
            "healthy_count": 5,
            "degraded_count": 0,
            "note": f"Using default status: {str(e)}"
        }


@router.get("/worker-metrics")
async def get_worker_metrics(
    hours: int = 24,
    admin: dict = Depends(get_admin_user)
):
    """Get worker retry and performance metrics"""
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get job statistics
    jobs_processed = await db.genstudio_jobs.count_documents({
        "updatedAt": {"$gte": start_time.isoformat()},
        "status": "COMPLETED"
    })
    
    jobs_failed = await db.genstudio_jobs.count_documents({
        "updatedAt": {"$gte": start_time.isoformat()},
        "status": "FAILED"
    })
    
    jobs_retried = await db.genstudio_jobs.count_documents({
        "updatedAt": {"$gte": start_time.isoformat()},
        "retryCount": {"$gt": 0}
    })
    
    # Get average processing time
    pipeline = [
        {"$match": {
            "updatedAt": {"$gte": start_time.isoformat()},
            "status": "COMPLETED"
        }},
        {"$group": {
            "_id": "$type",
            "count": {"$sum": 1},
            "avg_processing_time": {"$avg": "$processingTimeMs"}
        }}
    ]
    
    processing_times = await db.genstudio_jobs.aggregate(pipeline).to_list(20)
    
    total_jobs = jobs_processed + jobs_failed
    success_rate = (jobs_processed / total_jobs * 100) if total_jobs > 0 else 100
    retry_rate = (jobs_retried / total_jobs * 100) if total_jobs > 0 else 0
    
    return {
        "period_hours": hours,
        "total_jobs": total_jobs,
        "jobs_processed": jobs_processed,
        "jobs_failed": jobs_failed,
        "jobs_retried": jobs_retried,
        "success_rate": round(success_rate, 1),
        "retry_rate": round(retry_rate, 1),
        "processing_times_by_type": [
            {"type": p["_id"], "count": p["count"], "avg_ms": round(p.get("avg_processing_time", 0), 0)}
            for p in processing_times
        ]
    }


@router.get("/payment-reconciliation")
async def get_payment_reconciliation_status(
    hours: int = 24,
    admin: dict = Depends(get_admin_user)
):
    """Get payment reconciliation status"""
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Successful payments
    successful_payments = await db.orders.count_documents({
        "createdAt": {"$gte": start_time.isoformat()},
        "status": "SUCCESS"
    })
    
    # Failed payments
    failed_payments = await db.orders.count_documents({
        "createdAt": {"$gte": start_time.isoformat()},
        "status": {"$in": ["FAILED", "CANCELLED"]}
    })
    
    # Pending payments
    pending_payments = await db.orders.count_documents({
        "createdAt": {"$gte": start_time.isoformat()},
        "status": "PENDING"
    })
    
    # Reconciled (delivered after initial failure)
    reconciled = await db.orders.count_documents({
        "deliveredAt": {"$gte": start_time.isoformat()},
        "creditsDelivered": True
    })
    
    # Refunds processed
    refunds = await db.refund_logs.count_documents({
        "timestamp": {"$gte": start_time}
    })
    
    total = successful_payments + failed_payments + pending_payments
    
    return {
        "period_hours": hours,
        "total_transactions": total,
        "successful": successful_payments,
        "failed": failed_payments,
        "pending": pending_payments,
        "reconciled": reconciled,
        "refunds_processed": refunds,
        "success_rate": round((successful_payments / total * 100) if total > 0 else 100, 1)
    }


# Helper functions
async def _get_refund_stats(since: datetime) -> Dict[str, Any]:
    """Get refund statistics since a given time"""
    count = await db.auto_refund_logs.count_documents({
        "timestamp": {"$gte": since}
    })
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": None, "total_credits": {"$sum": "$credits_refunded"}}}
    ]
    result = await db.auto_refund_logs.aggregate(pipeline).to_list(1)
    total_credits = result[0]["total_credits"] if result else 0
    
    return {
        "count": count,
        "total_credits": total_credits
    }


async def _get_incident_stats(since: datetime) -> Dict[str, Any]:
    """Get incident statistics since a given time"""
    total = await db.self_healing_incidents.count_documents({
        "timestamp": {"$gte": since}
    })
    
    resolved = await db.self_healing_incidents.count_documents({
        "timestamp": {"$gte": since},
        "resolved": True
    })
    
    return {
        "total": total,
        "resolved": resolved,
        "unresolved": total - resolved
    }


async def _get_circuit_breaker_status() -> Dict[str, Any]:
    """Get current circuit breaker status"""
    try:
        from services.enhanced_self_healing_system import get_self_healing_system
        system = await get_self_healing_system(db)
        
        return {
            name: {
                "state": cb.state,
                "healthy": cb.state == "closed"
            }
            for name, cb in system.circuit_breakers.items()
        }
    except:
        return {
            "llm_api": {"state": "closed", "healthy": True},
            "image_gen": {"state": "closed", "healthy": True},
            "payment": {"state": "closed", "healthy": True}
        }


async def _get_worker_retry_metrics(since: datetime) -> Dict[str, Any]:
    """Get worker retry metrics"""
    retried = await db.genstudio_jobs.count_documents({
        "updatedAt": {"$gte": since.isoformat()},
        "retryCount": {"$gt": 0}
    })
    
    total = await db.genstudio_jobs.count_documents({
        "updatedAt": {"$gte": since.isoformat()}
    })
    
    return {
        "total_jobs": total,
        "retried_jobs": retried,
        "retry_rate": round((retried / total * 100) if total > 0 else 0, 1)
    }


async def _get_payment_reconciliation_status(since: datetime) -> Dict[str, Any]:
    """Get payment reconciliation status"""
    reconciled = await db.orders.count_documents({
        "deliveredAt": {"$gte": since.isoformat()},
        "creditsDelivered": True
    })
    
    pending = await db.orders.count_documents({
        "createdAt": {"$gte": since.isoformat()},
        "status": "SUCCESS",
        "creditsDelivered": {"$ne": True}
    })
    
    return {
        "reconciled": reconciled,
        "pending_delivery": pending
    }


def _calculate_health_score(refunds, incidents, circuits, payments) -> int:
    """Calculate overall system health score (0-100)"""
    score = 100
    
    # Deduct for refunds (max -20)
    refund_count = refunds.get("count", 0)
    if refund_count > 10:
        score -= min(20, refund_count - 10)
    
    # Deduct for unresolved incidents (max -30)
    unresolved = incidents.get("unresolved", 0)
    score -= min(30, unresolved * 5)
    
    # Deduct for unhealthy circuits (max -30)
    unhealthy = sum(1 for c in circuits.values() if not c.get("healthy", True))
    score -= unhealthy * 10
    
    # Deduct for pending payments (max -20)
    pending = payments.get("pending_delivery", 0)
    score -= min(20, pending * 5)
    
    return max(0, score)


def _get_health_status(score: int) -> str:
    """Get health status label from score"""
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "degraded"
    else:
        return "critical"
