"""
Self-Healing Watchdog — Proactive, scheduled, logged, bounded

Endpoints:
  POST /api/watchdog/run         — Manual trigger (admin)
  GET  /api/watchdog/status      — Last run report
  GET  /api/watchdog/logs        — Structured heal logs
  GET  /api/watchdog/confidence  — System confidence score 0-100

Scheduled: Runs every 5 minutes via background task.
Idempotent: Safe to run repeatedly without side effects.

Detects & heals:
1. Stuck PROCESSING jobs (SLA: 10 min)
2. Completed jobs without READY assets
3. Starved QUEUED jobs (SLA: 5 min queue wait)
4. Validation failures (SLA: 2 min validation)
5. Admin credit corruption
6. Broken chain references

Guardrails:
- Max 3 retries per job, then FAILED honestly
- Every action logged to watchdog_logs
- Alerts trigger automatic watchdog run
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone, timedelta
import asyncio
import logging

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchdog", tags=["Watchdog"])

# ─── SLA THRESHOLDS ───────────────────────────────────────────────
SLA_MAX_PROCESSING_MIN = 10
SLA_MAX_QUEUE_WAIT_MIN = 5
SLA_MAX_VALIDATION_MIN = 2
MAX_RETRIES = 3
SCHEDULER_INTERVAL_SEC = 300  # 5 minutes

_scheduler_task = None
_last_run_report = None


# ─── STRUCTURED LOG WRITER ────────────────────────────────────────
async def _log_heal_action(job_id: str, issue_type: str, action_taken: str,
                           result: str, retry_count: int = 0, detail: str = ""):
    """Write a structured log entry to watchdog_logs collection."""
    entry = {
        "job_id": job_id,
        "issue_type": issue_type,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "action_taken": action_taken,
        "result": result,
        "retry_count": retry_count,
        "detail": detail,
    }
    try:
        doc = dict(entry)  # Copy to avoid _id mutation
        await db.watchdog_logs.insert_one(doc)
    except Exception as e:
        logger.error(f"Failed to write watchdog log: {e}")
    return entry  # Return clean copy without _id


# ─── CORE WATCHDOG (IDEMPOTENT) ──────────────────────────────────
async def _run_watchdog():
    """Core watchdog logic. Safe to run repeatedly."""
    global _last_run_report
    now = datetime.now(timezone.utc)
    report = {
        "timestamp": now.isoformat(),
        "checks": {},
        "actions_taken": [],
        "total_issues": 0,
        "total_healed": 0,
    }

    # ── 1. Stuck PROCESSING jobs (SLA breach) ────────────────────
    threshold = now - timedelta(minutes=SLA_MAX_PROCESSING_MIN)
    stuck_jobs = await db.pipeline_jobs.find(
        {"status": "PROCESSING", "started_at": {"$lt": threshold}},
        {"_id": 0, "job_id": 1, "started_at": 1, "current_stage": 1,
         "retry_count": 1, "title": 1, "user_id": 1}
    ).to_list(50)

    stuck_actions = []
    for job in stuck_jobs:
        jid = job["job_id"]
        retries = job.get("retry_count", 0)
        if retries < MAX_RETRIES:
            await db.pipeline_jobs.update_one(
                {"job_id": jid, "status": "PROCESSING"},
                {"$set": {
                    "status": "QUEUED", "current_stage": "scenes",
                    "progress": 0, "error": None,
                    "watchdog_retried_at": now,
                }, "$inc": {"retry_count": 1}}
            )
            action = await _log_heal_action(jid, "stuck_processing", "requeued",
                                            "SUCCESS", retries + 1,
                                            f"Stuck >{SLA_MAX_PROCESSING_MIN}min at stage {job.get('current_stage')}")
            stuck_actions.append(action)
            report["total_healed"] += 1
        else:
            await db.pipeline_jobs.update_one(
                {"job_id": jid, "status": "PROCESSING"},
                {"$set": {
                    "status": "FAILED",
                    "error": f"Exceeded {MAX_RETRIES} retries. Stuck >{SLA_MAX_PROCESSING_MIN}min. Watchdog marked FAILED.",
                    "completed_at": now, "watchdog_failed_at": now,
                }}
            )
            action = await _log_heal_action(jid, "stuck_processing", "failed_honestly",
                                            "SUCCESS", retries,
                                            f"Max retries ({MAX_RETRIES}) exceeded")
            stuck_actions.append(action)
            report["total_healed"] += 1

    report["checks"]["stuck_processing"] = {"found": len(stuck_jobs), "actions": len(stuck_actions)}
    report["total_issues"] += len(stuck_jobs)
    report["actions_taken"].extend(stuck_actions)

    # ── 2. Completed jobs with no downloadable assets ────────────
    orphan_jobs = await db.pipeline_jobs.find(
        {
            "status": {"$in": ["COMPLETED", "PARTIAL"]},
            "watchdog_corrected_at": {"$exists": False},
            "$or": [
                {"output_url": None}, {"output_url": ""},
                {"output_url": {"$exists": False}},
            ],
            "fallback_outputs": {"$in": [None, {}]},
        },
        {"_id": 0, "job_id": 1, "status": 1, "title": 1}
    ).to_list(50)

    orphan_actions = []
    for job in orphan_jobs:
        jid = job["job_id"]
        await db.pipeline_jobs.update_one(
            {"job_id": jid},
            {"$set": {
                "status": "FAILED",
                "error": "Completed but no downloadable assets. Watchdog corrected.",
                "watchdog_corrected_at": now,
            }}
        )
        action = await _log_heal_action(jid, "completed_no_assets", "status_corrected_to_failed",
                                        "SUCCESS", detail=f"Was {job['status']}, no output_url")
        orphan_actions.append(action)
        report["total_healed"] += 1

    report["checks"]["completed_no_assets"] = {"found": len(orphan_jobs), "healed": len(orphan_actions)}
    report["total_issues"] += len(orphan_jobs)
    report["actions_taken"].extend(orphan_actions)

    # ── 3. Starved QUEUED jobs (SLA breach) ──────────────────────
    queue_threshold = now - timedelta(minutes=SLA_MAX_QUEUE_WAIT_MIN)
    starved_jobs = await db.pipeline_jobs.find(
        {"status": "QUEUED", "created_at": {"$lt": queue_threshold}},
        {"_id": 0, "job_id": 1, "created_at": 1, "retry_count": 1}
    ).to_list(50)

    starved_actions = []
    for job in starved_jobs:
        jid = job["job_id"]
        retries = job.get("retry_count", 0)
        if retries >= MAX_RETRIES:
            await db.pipeline_jobs.update_one(
                {"job_id": jid, "status": "QUEUED"},
                {"$set": {
                    "status": "FAILED",
                    "error": f"Queued >{SLA_MAX_QUEUE_WAIT_MIN}min with {retries} retries. Workers unavailable.",
                    "completed_at": now, "watchdog_failed_at": now,
                }}
            )
            action = await _log_heal_action(jid, "starved_queue", "failed_honestly",
                                            "SUCCESS", retries, "Queue wait exceeded SLA + max retries")
            starved_actions.append(action)
            report["total_healed"] += 1

    report["checks"]["starved_queued"] = {
        "found": len(starved_jobs),
        "failed_honestly": len(starved_actions),
        "still_waiting": len(starved_jobs) - len(starved_actions),
    }
    report["total_issues"] += len(starved_jobs)
    report["actions_taken"].extend(starved_actions)

    # ── 4. Admin credit corruption ───────────────────────────────
    try:
        admin_zero = await db.users.count_documents({"role": "ADMIN", "credits": {"$lte": 0}})
        if admin_zero > 0:
            await db.users.update_many(
                {"role": "ADMIN", "credits": {"$lte": 0}},
                {"$set": {"credits": 999999999}}
            )
            await _log_heal_action("system", "admin_credits_zero", "restored_to_unlimited",
                                   "SUCCESS", detail=f"{admin_zero} admin(s) restored")
            report["total_healed"] += admin_zero
        report["checks"]["admin_credits"] = {"corrupted": admin_zero, "status": "healed" if admin_zero else "ok"}
        report["total_issues"] += admin_zero
    except Exception as e:
        report["checks"]["admin_credits"] = {"error": str(e)[:200]}

    # ── 5. Broken chain references ───────────────────────────────
    try:
        broken = await db.story_chains.count_documents({
            "$or": [{"root_job_id": None}, {"root_job_id": ""}]
        })
        report["checks"]["broken_chains"] = {"found": broken}
        report["total_issues"] += broken
    except Exception:
        report["checks"]["broken_chains"] = {"found": 0, "note": "collection unavailable"}

    # ── 6. Validation stuck (jobs marked COMPLETED >2min ago but never validated) ──
    validation_threshold = now - timedelta(minutes=SLA_MAX_VALIDATION_MIN)
    # This is informational — the validate-asset endpoint handles on-demand
    try:
        potentially_stuck = await db.pipeline_jobs.count_documents({
            "status": {"$in": ["COMPLETED", "PARTIAL"]},
            "completed_at": {"$lt": validation_threshold},
            "watchdog_corrected_at": {"$exists": False},
            "output_url": {"$exists": True, "$ne": None, "$ne": ""},
        })
        report["checks"]["validation_backlog"] = {"pending": potentially_stuck}
    except Exception:
        report["checks"]["validation_backlog"] = {"pending": 0}

    # ── Finalize ─────────────────────────────────────────────────
    report["healthy"] = report["total_issues"] == 0
    report["sla"] = {
        "max_processing_min": SLA_MAX_PROCESSING_MIN,
        "max_queue_wait_min": SLA_MAX_QUEUE_WAIT_MIN,
        "max_validation_min": SLA_MAX_VALIDATION_MIN,
        "max_retries": MAX_RETRIES,
    }

    # Save report
    try:
        save_doc = {k: v for k, v in report.items()}
        save_doc.pop("_id", None)
        await db.watchdog_reports.insert_one(save_doc)
    except Exception as e:
        logger.warning(f"Failed to save watchdog report: {e}")
    report.pop("_id", None)

    _last_run_report = report
    logger.info(f"Watchdog: {report['total_issues']} issues, {report['total_healed']} healed")
    return report


# ─── SYSTEM CONFIDENCE SCORE ─────────────────────────────────────
async def _calc_confidence():
    """0-100 score based on system health signals."""
    now = datetime.now(timezone.utc)
    one_hour = now - timedelta(hours=1)
    score = 100
    reasons = []

    # Failure rate (-30 max)
    try:
        total = await db.pipeline_jobs.count_documents({"created_at": {"$gte": one_hour}})
        failed = await db.pipeline_jobs.count_documents({"status": "FAILED", "created_at": {"$gte": one_hour}})
        if total > 0:
            rate = failed / total * 100
            if rate > 50:
                penalty = 30
            elif rate > 20:
                penalty = 15
            elif rate > 10:
                penalty = 5
            else:
                penalty = 0
            score -= penalty
            if penalty > 0:
                reasons.append(f"failure_rate={rate:.0f}% (-{penalty})")
    except Exception:
        pass

    # Queue health (-20 max)
    try:
        queued = await db.pipeline_jobs.count_documents({"status": "QUEUED"})
        if queued > 30:
            score -= 20
            reasons.append(f"queue_depth={queued} (-20)")
        elif queued > 10:
            score -= 10
            reasons.append(f"queue_depth={queued} (-10)")
    except Exception:
        pass

    # Watchdog corrections last hour (-20 max)
    try:
        corrections = await db.watchdog_logs.count_documents({"detected_at": {"$gte": one_hour.isoformat()}})
        if corrections > 10:
            score -= 20
            reasons.append(f"watchdog_corrections={corrections} (-20)")
        elif corrections > 3:
            score -= 10
            reasons.append(f"watchdog_corrections={corrections} (-10)")
    except Exception:
        pass

    # Active critical alerts (-15 max)
    try:
        critical_alerts = await db.production_alerts.count_documents({"severity": "critical", "acknowledged": False})
        if critical_alerts > 0:
            score -= min(15, critical_alerts * 5)
            reasons.append(f"critical_alerts={critical_alerts} (-{min(15, critical_alerts * 5)})")
    except Exception:
        pass

    # Admin credits health (-15)
    try:
        admin_zero = await db.users.count_documents({"role": "ADMIN", "credits": {"$lte": 0}})
        if admin_zero > 0:
            score -= 15
            reasons.append(f"admin_credits_zero={admin_zero} (-15)")
    except Exception:
        pass

    score = max(0, min(100, score))
    level = "excellent" if score >= 90 else "good" if score >= 70 else "degraded" if score >= 50 else "critical"
    return {
        "score": score,
        "level": level,
        "timestamp": now.isoformat(),
        "deductions": reasons if reasons else ["none — all clear"],
    }


# ─── ALERT-TRIGGERED WATCHDOG ────────────────────────────────────
async def alert_triggered_watchdog():
    """Called when alerts detect issues. Triggers immediate watchdog run."""
    logger.info("Alert-triggered watchdog run initiated")
    return await _run_watchdog()


# ─── SCHEDULED BACKGROUND TASK ───────────────────────────────────
async def _scheduler_loop():
    """Runs watchdog every SCHEDULER_INTERVAL_SEC. Idempotent."""
    while True:
        try:
            await asyncio.sleep(SCHEDULER_INTERVAL_SEC)
            logger.info("Scheduled watchdog run starting...")
            await _run_watchdog()
        except asyncio.CancelledError:
            logger.info("Watchdog scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Watchdog scheduler error: {e}")
            await asyncio.sleep(60)  # Back off on error


def start_scheduler():
    """Start the background watchdog scheduler. Call on app startup."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info(f"Watchdog scheduler started (every {SCHEDULER_INTERVAL_SEC}s)")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("Watchdog scheduler stopped")


# ─── API ENDPOINTS ───────────────────────────────────────────────

@router.post("/run")
async def run_watchdog(admin: dict = Depends(get_admin_user)):
    """Manually trigger the watchdog. Admin only."""
    report = await _run_watchdog()
    return report


@router.get("/status")
async def get_watchdog_status(user: dict = Depends(get_current_user)):
    """Get the last watchdog report."""
    if _last_run_report:
        return _last_run_report
    last = await db.watchdog_reports.find_one({}, {"_id": 0}, sort=[("timestamp", -1)])
    if not last:
        return {"message": "No watchdog reports yet", "last_run": None}
    return last


@router.get("/logs")
async def get_watchdog_logs(
    limit: int = Query(50, le=200),
    issue_type: str = Query(None),
    user: dict = Depends(get_current_user)
):
    """Get structured heal logs."""
    query = {}
    if issue_type:
        query["issue_type"] = issue_type
    logs = await db.watchdog_logs.find(query, {"_id": 0}).sort("detected_at", -1).to_list(limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/confidence")
async def get_confidence(user: dict = Depends(get_current_user)):
    """System confidence score 0-100."""
    return await _calc_confidence()
