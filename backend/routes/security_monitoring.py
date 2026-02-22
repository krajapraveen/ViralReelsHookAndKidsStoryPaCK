"""
Production Security Monitoring Routes
Real-time threat detection, security events, and incident response
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import uuid
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user

# Import threat detection module
try:
    from utils.threat_detection import (
        threat_store, get_threat_stats, check_rate_limit,
        is_ip_blocked, is_ip_throttled, hash_ip, log_threat_event
    )
    THREAT_DETECTION_AVAILABLE = True
except ImportError:
    THREAT_DETECTION_AVAILABLE = False
    logger.warning("Threat detection module not available")

router = APIRouter(prefix="/security", tags=["Security Monitoring"])


class BlockIPRequest(BaseModel):
    ip_hash: str = Field(..., description="Hashed IP to block")
    duration_minutes: int = Field(60, ge=1, le=10080, description="Block duration (1 min to 7 days)")
    reason: str = Field("Manual block", max_length=500)


class SecurityAlert(BaseModel):
    alert_type: str
    severity: str
    message: str
    metadata: dict = {}


# In-memory alert store
active_alerts: List[dict] = []
MAX_ALERTS = 100


async def create_security_alert(alert_type: str, severity: str, message: str, 
                                 metadata: dict = None, notify: bool = True):
    """Create and store a security alert"""
    alert = {
        "id": str(uuid.uuid4()),
        "type": alert_type,
        "severity": severity,
        "message": message,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }
    
    active_alerts.append(alert)
    
    # Keep only last MAX_ALERTS
    while len(active_alerts) > MAX_ALERTS:
        active_alerts.pop(0)
    
    # Store in DB for persistence
    await db.security_alerts.insert_one(alert)
    
    # Log critical alerts
    if severity == "CRITICAL":
        logger.critical(f"SECURITY ALERT: {alert_type} - {message}")
    elif severity == "HIGH":
        logger.error(f"SECURITY ALERT: {alert_type} - {message}")
    else:
        logger.warning(f"SECURITY ALERT: {alert_type} - {message}")
    
    return alert


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/overview")
async def get_security_overview(admin: dict = Depends(get_admin_user)):
    """Get comprehensive security overview"""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    
    # Get threat stats
    threat_stats = get_threat_stats() if THREAT_DETECTION_AVAILABLE else {}
    
    # Get recent security events
    recent_events = await db.security_events.find(
        {"timestamp": {"$gte": day_ago.isoformat()}},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    # Get alert counts by severity
    alerts_by_severity = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }
    
    for alert in active_alerts:
        severity = alert.get("severity", "LOW")
        if severity in alerts_by_severity:
            alerts_by_severity[severity] += 1
    
    # Get failed login attempts
    failed_logins = await db.security_events.count_documents({
        "type": "AUTH_FAILURE",
        "timestamp": {"$gte": day_ago.isoformat()}
    })
    
    # Get rate limit events
    rate_limit_events = await db.security_events.count_documents({
        "type": "RATE_LIMIT_EXCEEDED",
        "timestamp": {"$gte": day_ago.isoformat()}
    })
    
    # Get suspicious activity
    suspicious_activity = await db.security_events.count_documents({
        "type": {"$in": ["SUSPICIOUS_REQUEST", "BLOCKED_ACCESS", "ABUSE_DETECTED"]},
        "timestamp": {"$gte": day_ago.isoformat()}
    })
    
    return {
        "status": "OPERATIONAL" if not alerts_by_severity["CRITICAL"] else "ALERT",
        "threatStats": threat_stats,
        "alertsSummary": alerts_by_severity,
        "last24Hours": {
            "failedLogins": failed_logins,
            "rateLimitEvents": rate_limit_events,
            "suspiciousActivity": suspicious_activity,
            "totalEvents": len(recent_events)
        },
        "recentEvents": recent_events[:10],
        "activeAlerts": len([a for a in active_alerts if not a.get("acknowledged")]),
        "timestamp": now.isoformat()
    }


@router.get("/alerts")
async def get_security_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50,
    admin: dict = Depends(get_admin_user)
):
    """Get security alerts with filtering"""
    query = {}
    
    if severity:
        query["severity"] = severity.upper()
    
    if acknowledged is not None:
        query["acknowledged"] = acknowledged
    
    alerts = await db.security_alerts.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "alerts": alerts,
        "total": len(alerts),
        "unacknowledged": len([a for a in alerts if not a.get("acknowledged")])
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, admin: dict = Depends(get_admin_user)):
    """Acknowledge a security alert"""
    result = await db.security_alerts.update_one(
        {"id": alert_id},
        {
            "$set": {
                "acknowledged": True,
                "acknowledgedBy": admin["id"],
                "acknowledgedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update in-memory store
    for alert in active_alerts:
        if alert.get("id") == alert_id:
            alert["acknowledged"] = True
            break
    
    return {"success": True, "message": "Alert acknowledged"}


@router.get("/events")
async def get_security_events(
    event_type: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    admin: dict = Depends(get_admin_user)
):
    """Get security events with filtering"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    query = {"timestamp": {"$gte": start_date.isoformat()}}
    
    if event_type:
        query["type"] = event_type.upper()
    
    events = await db.security_events.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Group by type for summary
    event_types = defaultdict(int)
    for event in events:
        event_types[event.get("type", "UNKNOWN")] += 1
    
    return {
        "events": events,
        "summary": dict(event_types),
        "total": len(events),
        "period": f"Last {days} days"
    }


@router.get("/blocked-ips")
async def get_blocked_ips(admin: dict = Depends(get_admin_user)):
    """Get list of currently blocked IPs"""
    if not THREAT_DETECTION_AVAILABLE:
        return {"blocked": [], "throttled": [], "message": "Threat detection not available"}
    
    now = datetime.now(timezone.utc).timestamp()
    
    blocked = [
        {
            "ip_hash": ip_hash,
            "blocked_until": datetime.fromtimestamp(blocked_until, tz=timezone.utc).isoformat(),
            "remaining_seconds": int(blocked_until - now)
        }
        for ip_hash, blocked_until in threat_store.blocked_ips.items()
        if blocked_until > now
    ]
    
    throttled = [
        {
            "ip_hash": ip_hash,
            "throttled_until": datetime.fromtimestamp(throttled_until, tz=timezone.utc).isoformat(),
            "remaining_seconds": int(throttled_until - now)
        }
        for ip_hash, throttled_until in threat_store.throttled_ips.items()
        if throttled_until > now
    ]
    
    return {
        "blocked": blocked,
        "blocked_count": len(blocked),
        "throttled": throttled,
        "throttled_count": len(throttled)
    }


@router.post("/block-ip")
async def block_ip_manually(request: BlockIPRequest, admin: dict = Depends(get_admin_user)):
    """Manually block an IP address"""
    if not THREAT_DETECTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Threat detection not available")
    
    duration_seconds = request.duration_minutes * 60
    block_until = datetime.now(timezone.utc).timestamp() + duration_seconds
    
    # Since we have hashed IP, we need to store the mapping
    threat_store.blocked_ips[request.ip_hash] = block_until
    
    # Log the action
    await db.security_events.insert_one({
        "type": "MANUAL_BLOCK",
        "ip_hash": request.ip_hash,
        "admin_id": admin["id"],
        "duration_minutes": request.duration_minutes,
        "reason": request.reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    await create_security_alert(
        alert_type="IP_BLOCKED",
        severity="MEDIUM",
        message=f"IP manually blocked by admin for {request.duration_minutes} minutes",
        metadata={"ip_hash": request.ip_hash, "reason": request.reason}
    )
    
    return {
        "success": True,
        "message": f"IP blocked for {request.duration_minutes} minutes",
        "blocked_until": datetime.fromtimestamp(block_until, tz=timezone.utc).isoformat()
    }


@router.post("/unblock-ip/{ip_hash}")
async def unblock_ip(ip_hash: str, admin: dict = Depends(get_admin_user)):
    """Unblock an IP address"""
    if not THREAT_DETECTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Threat detection not available")
    
    if ip_hash in threat_store.blocked_ips:
        del threat_store.blocked_ips[ip_hash]
    
    if ip_hash in threat_store.throttled_ips:
        del threat_store.throttled_ips[ip_hash]
    
    # Reset IP score
    if ip_hash in threat_store.ip_scores:
        threat_store.ip_scores[ip_hash] = 0
    
    # Log the action
    await db.security_events.insert_one({
        "type": "MANUAL_UNBLOCK",
        "ip_hash": ip_hash,
        "admin_id": admin["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "message": "IP unblocked"}


@router.get("/rate-limits")
async def get_rate_limit_config(admin: dict = Depends(get_admin_user)):
    """Get current rate limit configuration"""
    if not THREAT_DETECTION_AVAILABLE:
        return {"message": "Threat detection not available"}
    
    from utils.threat_detection import RATE_WINDOWS, ABUSE_PATTERNS
    
    return {
        "rate_limits": RATE_WINDOWS,
        "abuse_patterns": ABUSE_PATTERNS,
        "status": "ACTIVE"
    }


@router.get("/ip-reputation")
async def get_ip_reputation_scores(
    limit: int = 50,
    min_score: int = 5,
    admin: dict = Depends(get_admin_user)
):
    """Get IPs with high risk scores"""
    if not THREAT_DETECTION_AVAILABLE:
        return {"high_risk_ips": [], "message": "Threat detection not available"}
    
    high_risk = [
        {
            "ip_hash": ip_hash,
            "score": score,
            "risk_level": "CRITICAL" if score >= 20 else "HIGH" if score >= 10 else "MEDIUM"
        }
        for ip_hash, score in threat_store.ip_scores.items()
        if score >= min_score
    ]
    
    # Sort by score descending
    high_risk.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "high_risk_ips": high_risk[:limit],
        "total_tracked": len(threat_store.ip_scores),
        "high_risk_count": len(high_risk)
    }


@router.get("/audit-log")
async def get_admin_audit_log(
    days: int = 30,
    limit: int = 100,
    admin: dict = Depends(get_admin_user)
):
    """Get admin action audit log"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    audit_events = await db.security_events.find(
        {
            "timestamp": {"$gte": start_date.isoformat()},
            "type": {"$in": ["MANUAL_BLOCK", "MANUAL_UNBLOCK", "ALERT_ACKNOWLEDGED", "CONFIG_CHANGE"]}
        },
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "audit_log": audit_events,
        "total": len(audit_events),
        "period": f"Last {days} days"
    }


@router.get("/health")
async def get_security_system_health():
    """Get security system health status"""
    status = {
        "threat_detection": "OPERATIONAL" if THREAT_DETECTION_AVAILABLE else "DISABLED",
        "rate_limiting": "OPERATIONAL" if THREAT_DETECTION_AVAILABLE else "DISABLED",
        "alert_system": "OPERATIONAL",
        "audit_logging": "OPERATIONAL"
    }
    
    # Check DB connectivity
    try:
        await db.security_events.find_one({})
        status["database"] = "OPERATIONAL"
    except:
        status["database"] = "ERROR"
    
    # Overall status
    all_operational = all(v == "OPERATIONAL" for v in status.values())
    
    return {
        "status": "HEALTHY" if all_operational else "DEGRADED",
        "components": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def security_monitoring_loop():
    """Background task for continuous security monitoring"""
    while True:
        try:
            # Check for anomalies
            if THREAT_DETECTION_AVAILABLE:
                stats = get_threat_stats()
                
                # Alert on high blocked IP count
                if stats.get("blocked_ips_count", 0) > 10:
                    await create_security_alert(
                        alert_type="HIGH_BLOCK_COUNT",
                        severity="MEDIUM",
                        message=f"Unusually high number of blocked IPs: {stats['blocked_ips_count']}",
                        metadata=stats
                    )
                
                # Alert on high-risk IP count
                if stats.get("high_risk_ips", 0) > 5:
                    await create_security_alert(
                        alert_type="HIGH_RISK_IPS",
                        severity="HIGH",
                        message=f"Multiple high-risk IPs detected: {stats['high_risk_ips']}",
                        metadata=stats
                    )
            
            # Clean up old alerts
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            await db.security_alerts.delete_many({
                "timestamp": {"$lt": cutoff},
                "acknowledged": True
            })
            
        except Exception as e:
            logger.error(f"Security monitoring error: {e}")
        
        await asyncio.sleep(300)  # Run every 5 minutes


async def start_security_monitoring():
    """Start security monitoring background task"""
    asyncio.create_task(security_monitoring_loop())
    logger.info("Security monitoring started")
