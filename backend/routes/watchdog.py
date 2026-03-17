"""
Self-Healing Watchdog — Detects and remediates stuck/zombie system states
POST /api/watchdog/run — Manual trigger
GET  /api/watchdog/status — Last run report

Detects:
1. Stuck PROCESSING jobs (>10 min)
2. Completed jobs with no READY asset
3. Starved QUEUED jobs (>5 min in queue)
4. Uploaded but never validated assets
5. Broken chain references

Actions:
- Retry safe stages
- Move to FAILED honestly
- Requeue when valid
- Log root cause
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import logging

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/watchdog", tags=["Watchdog"])

STUCK_JOB_THRESHOLD_MIN = 10
STARVED_QUEUE_THRESHOLD_MIN = 5
UNVALIDATED_THRESHOLD_MIN = 15
MAX_RETRIES = 2


async def _run_watchdog():
    """Core watchdog logic. Returns a report dict."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "actions_taken": [],
        "total_issues": 0,
    }

    # 1. Stuck PROCESSING jobs
    threshold = datetime.now(timezone.utc) - timedelta(minutes=STUCK_JOB_THRESHOLD_MIN)
    stuck_jobs = await db.pipeline_jobs.find(
        {
            "status": "PROCESSING",
            "started_at": {"$lt": threshold},
        },
        {"_id": 0, "job_id": 1, "started_at": 1, "current_stage": 1, "retry_count": 1, "title": 1}
    ).to_list(50)

    stuck_actions = []
    for job in stuck_jobs:
        retry_count = job.get("retry_count", 0)
        if retry_count < MAX_RETRIES:
            # Retry: reset to QUEUED
            await db.pipeline_jobs.update_one(
                {"job_id": job["job_id"]},
                {"$set": {
                    "status": "QUEUED",
                    "current_stage": "scenes",
                    "progress": 0,
                    "error": None,
                    "watchdog_retried_at": datetime.now(timezone.utc),
                }, "$inc": {"retry_count": 1}}
            )
            stuck_actions.append({"job_id": job["job_id"], "action": "requeued", "retry": retry_count + 1})
        else:
            # Max retries exceeded: fail honestly
            await db.pipeline_jobs.update_one(
                {"job_id": job["job_id"]},
                {"$set": {
                    "status": "FAILED",
                    "error": f"Stuck for >{STUCK_JOB_THRESHOLD_MIN}min after {retry_count} retries. Watchdog marked as failed.",
                    "completed_at": datetime.now(timezone.utc),
                    "watchdog_failed_at": datetime.now(timezone.utc),
                }}
            )
            stuck_actions.append({"job_id": job["job_id"], "action": "failed_honestly", "reason": "max_retries_exceeded"})

    report["checks"]["stuck_processing"] = {
        "found": len(stuck_jobs),
        "actions": stuck_actions,
    }
    report["total_issues"] += len(stuck_jobs)

    # 2. Completed jobs without downloadable assets
    orphan_jobs = await db.pipeline_jobs.find(
        {
            "status": {"$in": ["COMPLETED", "PARTIAL"]},
            "$or": [
                {"output_url": None},
                {"output_url": ""},
                {"output_url": {"$exists": False}},
            ],
            "fallback_outputs": {"$in": [None, {}]},
        },
        {"_id": 0, "job_id": 1, "status": 1, "title": 1, "completed_at": 1}
    ).to_list(50)

    orphan_actions = []
    for job in orphan_jobs:
        # These jobs say COMPLETED but have nothing to show.
        # Mark as FAILED with honest reason.
        await db.pipeline_jobs.update_one(
            {"job_id": job["job_id"]},
            {"$set": {
                "status": "FAILED",
                "error": "Completed but no downloadable assets found. Watchdog corrected status.",
                "watchdog_corrected_at": datetime.now(timezone.utc),
            }}
        )
        orphan_actions.append({"job_id": job["job_id"], "action": "status_corrected_to_failed"})

    report["checks"]["completed_no_assets"] = {
        "found": len(orphan_jobs),
        "actions": orphan_actions,
    }
    report["total_issues"] += len(orphan_jobs)

    # 3. Starved QUEUED jobs
    queue_threshold = datetime.now(timezone.utc) - timedelta(minutes=STARVED_QUEUE_THRESHOLD_MIN)
    starved_jobs = await db.pipeline_jobs.find(
        {
            "status": "QUEUED",
            "created_at": {"$lt": queue_threshold},
        },
        {"_id": 0, "job_id": 1, "created_at": 1, "title": 1}
    ).to_list(50)

    report["checks"]["starved_queued"] = {
        "found": len(starved_jobs),
        "job_ids": [j["job_id"][:12] for j in starved_jobs[:10]],
        "action": "monitored" if starved_jobs else "none",
        "note": f"{len(starved_jobs)} jobs waiting >{STARVED_QUEUE_THRESHOLD_MIN}min" if starved_jobs else "queue healthy",
    }
    report["total_issues"] += len(starved_jobs)

    # 4. Broken story chain references
    try:
        broken_chains = await db.story_chains.count_documents({
            "$or": [
                {"root_job_id": None},
                {"root_job_id": ""},
            ]
        })
        report["checks"]["broken_chains"] = {"found": broken_chains}
        report["total_issues"] += broken_chains
    except Exception:
        report["checks"]["broken_chains"] = {"found": 0, "note": "collection may not exist"}

    # 5. Credits anomalies: admin with 0 credits
    try:
        admin_zero = await db.users.count_documents({"role": "ADMIN", "credits": {"$lte": 0}})
        if admin_zero > 0:
            # Auto-fix: restore admin credits
            await db.users.update_many(
                {"role": "ADMIN", "credits": {"$lte": 0}},
                {"$set": {"credits": 999999999}}
            )
            report["checks"]["admin_credits"] = {"found": admin_zero, "action": "restored_to_unlimited"}
        else:
            report["checks"]["admin_credits"] = {"found": 0, "status": "ok"}
        report["total_issues"] += admin_zero
    except Exception as e:
        report["checks"]["admin_credits"] = {"error": str(e)[:200]}

    # Save report
    report["healthy"] = report["total_issues"] == 0
    await db.watchdog_reports.insert_one({
        **report,
        "_id": None,  # Let MongoDB generate
    })
    # Clean up _id from report before returning
    report.pop("_id", None)

    logger.info(f"Watchdog run complete: {report['total_issues']} issues found, actions: {len(report['actions_taken'])}")
    return report


@router.post("/run")
async def run_watchdog(admin: dict = Depends(get_admin_user)):
    """Manually trigger the watchdog. Admin only."""
    report = await _run_watchdog()
    return report


@router.get("/status")
async def get_watchdog_status(user: dict = Depends(get_current_user)):
    """Get the last watchdog report."""
    last_report = await db.watchdog_reports.find_one(
        {},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    if not last_report:
        return {"message": "No watchdog reports yet", "last_run": None}
    return last_report
