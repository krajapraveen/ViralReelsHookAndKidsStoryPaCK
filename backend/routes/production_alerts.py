"""
Production Alerts — Detect issues that hurt users before users notice
GET  /api/alerts/check — Run all alert checks
GET  /api/alerts/active — Get currently active alerts
POST /api/alerts/acknowledge/{alert_id} — Acknowledge an alert

Alert categories:
- failure_rate_spike
- queue_depth_spike
- generation_timeout_spike
- broken_downloads
- validation_failures
- credit_truth_mismatch
- provider_outage
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import logging
import uuid

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["Production Alerts"])

# Thresholds
FAILURE_RATE_WARNING = 20  # percent
FAILURE_RATE_CRITICAL = 50
QUEUE_DEPTH_WARNING = 10
QUEUE_DEPTH_CRITICAL = 30
TIMEOUT_SPIKE_THRESHOLD = 3  # 3+ timeouts in 1 hour


async def _check_all_alerts():
    """Run all alert checks. Returns list of active alerts."""
    alerts = []
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # 1. Failure Rate Spike
    try:
        total = await db.pipeline_jobs.count_documents({"created_at": {"$gte": one_hour_ago}})
        failed = await db.pipeline_jobs.count_documents({"status": "FAILED", "created_at": {"$gte": one_hour_ago}})
        rate = (failed / total * 100) if total > 0 else 0
        if rate >= FAILURE_RATE_CRITICAL:
            alerts.append({
                "id": f"failure_rate_{now.strftime('%Y%m%d%H')}",
                "type": "failure_rate_spike",
                "severity": "critical",
                "message": f"Failure rate is {rate:.0f}% ({failed}/{total} jobs in last hour)",
                "metric": {"rate": round(rate, 1), "failed": failed, "total": total},
            })
        elif rate >= FAILURE_RATE_WARNING and total > 3:
            alerts.append({
                "id": f"failure_rate_{now.strftime('%Y%m%d%H')}",
                "type": "failure_rate_spike",
                "severity": "warning",
                "message": f"Failure rate elevated: {rate:.0f}% ({failed}/{total} jobs)",
                "metric": {"rate": round(rate, 1), "failed": failed, "total": total},
            })
    except Exception as e:
        logger.error(f"Alert check failure_rate failed: {e}")

    # 2. Queue Depth Spike
    try:
        queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
        if queued >= QUEUE_DEPTH_CRITICAL:
            alerts.append({
                "id": f"queue_depth_{now.strftime('%Y%m%d%H')}",
                "type": "queue_depth_spike",
                "severity": "critical",
                "message": f"Queue depth critical: {queued} jobs waiting",
                "metric": {"queued": queued},
            })
        elif queued >= QUEUE_DEPTH_WARNING:
            alerts.append({
                "id": f"queue_depth_{now.strftime('%Y%m%d%H')}",
                "type": "queue_depth_spike",
                "severity": "warning",
                "message": f"Queue depth elevated: {queued} jobs",
                "metric": {"queued": queued},
            })
    except Exception as e:
        logger.error(f"Alert check queue_depth failed: {e}")

    # 3. Generation Timeout Spike
    try:
        timed_out = await db.pipeline_jobs.count_documents({
            "status": "FAILED",
            "error": {"$regex": "timeout|timed out", "$options": "i"},
            "created_at": {"$gte": one_hour_ago},
        })
        if timed_out >= TIMEOUT_SPIKE_THRESHOLD:
            alerts.append({
                "id": f"timeout_spike_{now.strftime('%Y%m%d%H')}",
                "type": "generation_timeout_spike",
                "severity": "warning",
                "message": f"{timed_out} generation timeouts in last hour",
                "metric": {"timeouts": timed_out},
            })
    except Exception as e:
        logger.error(f"Alert check timeouts failed: {e}")

    # 4. Broken Downloads
    try:
        broken_downloads = await db.downloads.count_documents({
            "status": "ready",
            "$or": [
                {"download_url": None},
                {"download_url": ""},
                {"download_url": {"$exists": False}},
            ]
        })
        if broken_downloads > 0:
            alerts.append({
                "id": f"broken_downloads_{now.strftime('%Y%m%d%H')}",
                "type": "broken_downloads",
                "severity": "critical",
                "message": f"{broken_downloads} downloads marked ready but missing URLs",
                "metric": {"count": broken_downloads},
            })
    except Exception as e:
        logger.error(f"Alert check broken_downloads failed: {e}")

    # 5. Credit Truth Mismatch — Admin with 0 credits
    try:
        admin_zero = await db.users.count_documents({"role": "ADMIN", "credits": {"$lte": 0}})
        if admin_zero > 0:
            alerts.append({
                "id": f"credit_mismatch_{now.strftime('%Y%m%d%H')}",
                "type": "credit_truth_mismatch",
                "severity": "critical",
                "message": f"{admin_zero} admin users have 0 or negative credits",
                "metric": {"admin_zero": admin_zero},
            })
    except Exception as e:
        logger.error(f"Alert check credit_truth failed: {e}")

    # 6. Provider Outage (check if AI keys exist)
    import os
    for key_name, label in [("EMERGENT_LLM_KEY", "Emergent LLM"), ("ELEVENLABS_API_KEY", "ElevenLabs")]:
        val = os.environ.get(key_name, "")
        if not val or len(val) < 10:
            alerts.append({
                "id": f"provider_{label.lower()}_{now.strftime('%Y%m%d')}",
                "type": "provider_outage",
                "severity": "critical",
                "message": f"{label} API key missing or invalid — generation will fail",
                "metric": {"provider": label, "key_present": bool(val)},
            })

    # 7. Stuck Processing (no progress in 10 min)
    try:
        stuck_threshold = now - timedelta(minutes=10)
        stuck = await db.pipeline_jobs.count_documents({
            "status": "PROCESSING",
            "started_at": {"$lt": stuck_threshold},
        })
        if stuck > 0:
            alerts.append({
                "id": f"stuck_jobs_{now.strftime('%Y%m%d%H')}",
                "type": "stuck_jobs",
                "severity": "warning",
                "message": f"{stuck} jobs stuck in PROCESSING for >10min",
                "metric": {"stuck_count": stuck},
            })
    except Exception as e:
        logger.error(f"Alert check stuck_jobs failed: {e}")

    # Add timestamp to all alerts
    for a in alerts:
        a["detected_at"] = now.isoformat()
        a["acknowledged"] = False

    return alerts


@router.get("/check")
async def check_alerts(admin: dict = Depends(get_admin_user)):
    """Run all alert checks. If critical issues found, triggers watchdog automatically."""
    alerts = await _check_all_alerts()

    # Persist new alerts
    for alert in alerts:
        await db.production_alerts.update_one(
            {"id": alert["id"]},
            {"$set": alert, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True
        )

    # Alert → Action coupling: critical alerts trigger watchdog
    has_critical = any(a["severity"] == "critical" for a in alerts)
    has_actionable = any(a["type"] in ("stuck_jobs", "failure_rate_spike", "credit_truth_mismatch", "broken_downloads") for a in alerts)
    watchdog_triggered = False
    if has_critical and has_actionable:
        try:
            from routes.watchdog import alert_triggered_watchdog
            await alert_triggered_watchdog()
            watchdog_triggered = True
        except Exception as e:
            logger.error(f"Alert-triggered watchdog failed: {e}")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_alerts": len(alerts),
        "critical": len([a for a in alerts if a["severity"] == "critical"]),
        "warnings": len([a for a in alerts if a["severity"] == "warning"]),
        "alerts": alerts,
        "system_status": "HEALTHY" if len(alerts) == 0 else "DEGRADED" if has_critical else "WARNING",
        "watchdog_auto_triggered": watchdog_triggered,
    }


@router.get("/active")
async def get_active_alerts(user: dict = Depends(get_current_user)):
    """Get currently active (unacknowledged) alerts."""
    alerts = await db.production_alerts.find(
        {"acknowledged": False},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(50)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str, admin: dict = Depends(get_admin_user)):
    """Acknowledge an alert."""
    result = await db.production_alerts.update_one(
        {"id": alert_id},
        {"$set": {"acknowledged": True, "acknowledged_at": datetime.now(timezone.utc).isoformat(), "acknowledged_by": admin.get("email")}}
    )
    if result.modified_count == 0:
        return {"success": False, "message": "Alert not found"}
    return {"success": True, "message": f"Alert {alert_id} acknowledged"}
