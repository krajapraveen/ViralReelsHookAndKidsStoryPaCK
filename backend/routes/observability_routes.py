"""
Observability APIs — Backend-only endpoints for pipeline health monitoring.

Endpoints:
  GET  /api/observability/queue-status     — Queue depths + concurrency per tier
  GET  /api/observability/pipeline-health  — Stage failures, retry counts, avg times
  GET  /api/observability/cost-summary     — Cost per job, per user, system total
  GET  /api/observability/guardrail-state  — Kill switch, degradation state
  POST /api/observability/replay-job       — Replay whole job / failed stage / failed panels
  POST /api/observability/kill-switch      — Admin toggle kill switch

All endpoints require admin auth.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.multi_queue import get_multi_queue
from services.cost_guardrails import get_guardrail_status, SYSTEM_DAILY_COST_CEILING, SYSTEM_SEVERE_THRESHOLD
from services.admission_controller import get_system_status

router = APIRouter(prefix="/observability", tags=["Observability"])


def _require_admin(user: dict):
    if str(user.get("role", "")).lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/queue-status")
async def queue_status(user: dict = Depends(get_current_user)):
    _require_admin(user)
    mq = get_multi_queue()
    return mq.get_status()


@router.get("/pipeline-health")
async def pipeline_health(hours: int = 24, user: dict = Depends(get_current_user)):
    _require_admin(user)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Stage failure counts
    stage_stats = await db.job_stage_runs.aggregate([
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": {"stage": "$stage_name", "status": "$status"},
            "count": {"$sum": 1},
            "avg_attempts": {"$avg": "$attempt_count"},
        }},
    ]).to_list(100)

    # Job status breakdown
    job_stats = await db.comic_storybook_v2_jobs.aggregate([
        {"$match": {"createdAt": {"$gte": since}, "type": "COMIC_STORYBOOK"}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
        }},
    ]).to_list(20)

    # Average time per stage (completed stages only)
    avg_times = await db.job_stage_runs.aggregate([
        {"$match": {"created_at": {"$gte": since}, "status": "completed", "started_at": {"$exists": True}, "finished_at": {"$exists": True}}},
        {"$project": {
            "stage_name": 1,
            "duration_str": {"$subtract": [{"$dateFromString": {"dateString": "$finished_at"}}, {"$dateFromString": {"dateString": "$started_at"}}]},
        }},
        {"$group": {
            "_id": "$stage_name",
            "avg_duration_ms": {"$avg": "$duration_str"},
            "count": {"$sum": 1},
        }},
    ]).to_list(20)

    # Partial success count
    partial_count = await db.comic_storybook_v2_jobs.count_documents({
        "status": "PARTIAL_COMPLETE", "createdAt": {"$gte": since}
    })

    # Regeneration jobs
    regen_stats = await db.comic_storybook_v2_jobs.aggregate([
        {"$match": {"type": "PANEL_REGENERATION", "createdAt": {"$gte": since}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]).to_list(10)

    return {
        "period_hours": hours,
        "stage_stats": stage_stats,
        "job_status_breakdown": {s["_id"]: s["count"] for s in job_stats},
        "avg_stage_times": {s["_id"]: {"avg_ms": s["avg_duration_ms"], "samples": s["count"]} for s in avg_times},
        "partial_complete_count": partial_count,
        "regeneration_stats": {s["_id"]: s["count"] for s in regen_stats},
    }


@router.get("/cost-summary")
async def cost_summary(hours: int = 24, user: dict = Depends(get_current_user)):
    _require_admin(user)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Total cost
    total_pipeline = [
        {"$match": {"createdAt": {"$gte": since}, "type": "COMIC_STORYBOOK"}},
        {"$group": {"_id": None, "total_cost": {"$sum": "$cost"}, "total_jobs": {"$sum": 1}}},
    ]
    total_result = await db.comic_storybook_v2_jobs.aggregate(total_pipeline).to_list(1)
    totals = total_result[0] if total_result else {"total_cost": 0, "total_jobs": 0}

    # Cost per user (top 10)
    per_user = await db.comic_storybook_v2_jobs.aggregate([
        {"$match": {"createdAt": {"$gte": since}, "type": "COMIC_STORYBOOK"}},
        {"$group": {"_id": "$userId", "cost": {"$sum": "$cost"}, "jobs": {"$sum": 1}}},
        {"$sort": {"cost": -1}},
        {"$limit": 10},
    ]).to_list(10)

    # Average cost per job
    avg_cost = totals.get("total_cost", 0) / totals.get("total_jobs", 1) if totals.get("total_jobs") else 0

    return {
        "period_hours": hours,
        "total_cost": totals.get("total_cost", 0),
        "total_jobs": totals.get("total_jobs", 0),
        "avg_cost_per_job": round(avg_cost, 2),
        "top_users_by_cost": [{"user_id": u["_id"][:12] + "...", "cost": u["cost"], "jobs": u["jobs"]} for u in per_user],
    }


@router.get("/guardrail-state")
async def guardrail_state(user: dict = Depends(get_current_user)):
    _require_admin(user)
    guardrails = await get_guardrail_status()
    system = await get_system_status()
    return {
        "guardrails": guardrails,
        "admission": system,
    }


class ReplayRequest(BaseModel):
    job_id: str
    mode: str = "full"  # "full" | "failed_stage" | "failed_panels"
    stage_name: Optional[str] = None


@router.post("/replay-job")
async def replay_job(request: ReplayRequest, user: dict = Depends(get_current_user)):
    _require_admin(user)

    job = await db.comic_storybook_v2_jobs.find_one({"id": request.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.mode == "full":
        # Reset job to QUEUED and re-enqueue
        await db.comic_storybook_v2_jobs.update_one(
            {"id": request.job_id},
            {"$set": {"status": "QUEUED", "progress": 0, "error": None, "current_stage": "queued"}}
        )
        await db.job_stage_runs.update_many(
            {"job_id": request.job_id},
            {"$set": {"status": "queued", "attempt_count": 0}}
        )
        mq = get_multi_queue()
        await mq.enqueue(request.job_id, job.get("queue_name", "free"))
        return {"success": True, "mode": "full", "message": f"Job {request.job_id[:8]} re-queued for full replay"}

    elif request.mode == "failed_panels":
        failed = job.get("failed_panels", [])
        if not failed:
            raise HTTPException(status_code=400, detail="No failed panels to replay")

        from routes.comic_storybook_v2 import queue_background_regeneration
        await queue_background_regeneration(
            request.job_id, failed, job.get("genre", "kids_adventure"),
            job.get("title", "Comic"), job.get("tier", "free"), job["userId"]
        )
        return {"success": True, "mode": "failed_panels", "pages": failed, "message": f"Queued regeneration for {len(failed)} panels"}

    elif request.mode == "failed_stage":
        if not request.stage_name:
            raise HTTPException(status_code=400, detail="stage_name required for failed_stage mode")
        # For now, failed_stage replay re-runs the full pipeline (stages are sequential)
        await db.comic_storybook_v2_jobs.update_one(
            {"id": request.job_id},
            {"$set": {"status": "QUEUED", "progress": 0, "error": None, "current_stage": "queued"}}
        )
        await db.job_stage_runs.update_many(
            {"job_id": request.job_id},
            {"$set": {"status": "queued", "attempt_count": 0}}
        )
        mq = get_multi_queue()
        await mq.enqueue(request.job_id, job.get("queue_name", "free"))
        return {"success": True, "mode": "failed_stage", "message": f"Job {request.job_id[:8]} re-queued (full re-run from failed stage)"}

    raise HTTPException(status_code=400, detail="Invalid mode. Use: full, failed_stage, failed_panels")


class KillSwitchRequest(BaseModel):
    ceiling: Optional[int] = None
    severe_threshold: Optional[int] = None


@router.post("/kill-switch")
async def toggle_kill_switch(request: KillSwitchRequest, user: dict = Depends(get_current_user)):
    _require_admin(user)
    import services.cost_guardrails as cg

    changes = {}
    if request.ceiling is not None:
        cg.SYSTEM_DAILY_COST_CEILING = request.ceiling
        changes["ceiling"] = request.ceiling
    if request.severe_threshold is not None:
        cg.SYSTEM_SEVERE_THRESHOLD = request.severe_threshold
        changes["severe_threshold"] = request.severe_threshold

    current = await get_guardrail_status()
    return {
        "success": True,
        "changes": changes,
        "current_state": current,
    }
