"""
Audit Dashboard Routes
CreatorStudio AI - Admin Audit Log Dashboard

Provides endpoints for admins to view:
- All audit logs with filtering
- Security event summaries
- Revenue protection metrics
- Real-time activity monitoring
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user
from security import limiter
from services.audit_log_service import (
    get_audit_service, 
    AuditEventType, 
    AuditSeverity
)

router = APIRouter(prefix="/admin/audit", tags=["Admin - Audit Dashboard"])


@router.get("/logs")
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user)
):
    """
    Get paginated audit logs with filters.
    """
    try:
        audit_service = get_audit_service(db)
        
        # Convert string params to enums if provided
        event_enum = None
        if event_type:
            try:
                event_enum = AuditEventType(event_type)
            except ValueError:
                pass  # Invalid event type, ignore filter
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AuditSeverity(severity.upper())
            except ValueError:
                pass
        
        result = await audit_service.get_logs(
            event_type=event_enum,
            user_id=user_id,
            severity=severity_enum,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")


@router.get("/security-summary")
@limiter.limit("30/minute")
async def get_security_summary(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    admin: dict = Depends(get_admin_user)
):
    """
    Get security event summary for the dashboard.
    Shows login failures, account locks, IP blocks, etc.
    """
    try:
        audit_service = get_audit_service(db)
        summary = await audit_service.get_security_summary(days=days)
        
        # Add threat level indicator
        total_events = summary.get("total_security_events", 0)
        if total_events > 100:
            threat_level = "HIGH"
        elif total_events > 50:
            threat_level = "MEDIUM"
        elif total_events > 10:
            threat_level = "LOW"
        else:
            threat_level = "MINIMAL"
        
        summary["threat_level"] = threat_level
        
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching security summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch security summary")


@router.get("/revenue-summary")
@limiter.limit("30/minute")
async def get_revenue_summary(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin: dict = Depends(get_admin_user)
):
    """
    Get revenue protection summary.
    Shows payment success/failure rates, refunds, generation stats.
    """
    try:
        audit_service = get_audit_service(db)
        summary = await audit_service.get_revenue_summary(days=days)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching revenue summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch revenue summary")


@router.get("/event-types")
async def get_event_types(admin: dict = Depends(get_admin_user)):
    """
    Get list of all audit event types for filtering.
    """
    return {
        "event_types": [
            {"value": e.value, "category": e.value.split("_")[0]}
            for e in AuditEventType
        ],
        "severities": [s.value for s in AuditSeverity]
    }


@router.get("/credit-modifications")
@limiter.limit("30/minute")
async def get_credit_modifications(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    admin: dict = Depends(get_admin_user)
):
    """
    Get all credit modification events (admin resets, refunds, etc.)
    Critical for revenue protection auditing.
    """
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        credit_events = [
            AuditEventType.CREDIT_ADMIN_MODIFY.value,
            AuditEventType.CREDIT_REFUND.value,
            AuditEventType.CREDIT_BONUS.value
        ]
        
        skip = (page - 1) * size
        
        query = {
            "event_type": {"$in": credit_events},
            "timestamp": {"$gte": start_date}
        }
        
        total = await db.audit_logs.count_documents(query)
        
        logs = await db.audit_logs.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(size).to_list(size)
        
        # Enrich with user emails
        user_ids = list(set([log.get("user_id") for log in logs if log.get("user_id")]))
        admin_ids = list(set([log.get("admin_id") for log in logs if log.get("admin_id")]))
        
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}},
                {"_id": 0, "id": 1, "email": 1, "name": 1}
            ).to_list(len(user_ids))
            users_map = {u["id"]: u for u in users}
        
        admins_map = {}
        if admin_ids:
            admins = await db.users.find(
                {"id": {"$in": admin_ids}},
                {"_id": 0, "id": 1, "email": 1, "name": 1}
            ).to_list(len(admin_ids))
            admins_map = {a["id"]: a for a in admins}
        
        for log in logs:
            if log.get("user_id") in users_map:
                log["user_info"] = users_map[log["user_id"]]
            if log.get("admin_id") in admins_map:
                log["admin_info"] = admins_map[log["admin_id"]]
        
        # Calculate totals
        total_pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$event_type",
                "total_amount": {"$sum": "$details.amount"},
                "count": {"$sum": 1}
            }}
        ]
        
        totals = await db.audit_logs.aggregate(total_pipeline).to_list(10)
        
        return {
            "logs": logs,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            },
            "summary": {t["_id"]: {"total": t["total_amount"], "count": t["count"]} for t in totals},
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error fetching credit modifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credit modifications")


@router.get("/suspicious-users")
@limiter.limit("30/minute")
async def get_suspicious_users(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    admin: dict = Depends(get_admin_user)
):
    """
    Get users with suspicious activity patterns.
    Flags users with multiple security events.
    """
    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        security_events = [
            AuditEventType.SECURITY_LOGIN_FAILED.value,
            AuditEventType.SECURITY_ACCOUNT_LOCKED.value,
            AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY.value,
            AuditEventType.SECURITY_RATE_LIMIT.value,
            AuditEventType.SECURITY_CONTENT_BLOCKED.value
        ]
        
        # Group by user
        pipeline = [
            {
                "$match": {
                    "event_type": {"$in": security_events},
                    "timestamp": {"$gte": start_date},
                    "user_id": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "event_count": {"$sum": 1},
                    "event_types": {"$addToSet": "$event_type"},
                    "last_event": {"$max": "$timestamp"},
                    "ips_used": {"$addToSet": "$ip_address"}
                }
            },
            {"$sort": {"event_count": -1}},
            {"$limit": 20}
        ]
        
        suspicious_users = await db.audit_logs.aggregate(pipeline).to_list(20)
        
        # Enrich with user details
        user_ids = [u["_id"] for u in suspicious_users]
        users_map = {}
        if user_ids:
            users = await db.users.find(
                {"id": {"$in": user_ids}},
                {"_id": 0, "id": 1, "email": 1, "name": 1, "createdAt": 1}
            ).to_list(len(user_ids))
            users_map = {u["id"]: u for u in users}
        
        result = []
        for user in suspicious_users:
            user_info = users_map.get(user["_id"], {})
            result.append({
                "user_id": user["_id"],
                "email": user_info.get("email", "Unknown"),
                "name": user_info.get("name", ""),
                "event_count": user["event_count"],
                "event_types": user["event_types"],
                "last_event": user["last_event"],
                "unique_ips": len([ip for ip in user["ips_used"] if ip]),
                "risk_level": "HIGH" if user["event_count"] > 10 else "MEDIUM" if user["event_count"] > 5 else "LOW"
            })
        
        return {
            "suspicious_users": result,
            "period_days": days,
            "total_flagged": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error fetching suspicious users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch suspicious users")


@router.get("/real-time-activity")
@limiter.limit("120/minute")
async def get_real_time_activity(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_admin_user)
):
    """
    Get real-time activity feed for dashboard.
    Shows most recent events across all types.
    """
    try:
        # Get most recent events
        recent_events = await db.audit_logs.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Categorize by type
        security_events = [e for e in recent_events if e.get("event_type", "").startswith("SECURITY_")]
        payment_events = [e for e in recent_events if e.get("event_type", "").startswith("PAYMENT_")]
        credit_events = [e for e in recent_events if e.get("event_type", "").startswith("CREDIT_")]
        
        return {
            "all_events": recent_events,
            "security_events": security_events[:5],
            "payment_events": payment_events[:5],
            "credit_events": credit_events[:5],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching real-time activity: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch activity")
