"""
Story Engine API Routes — Private Story-to-Video pipeline endpoints.
Handles job creation, pipeline execution, status polling, and admin controls.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db, get_current_user

from services.story_engine.schemas import CreateStoryRequest, JobState
from services.story_engine.pipeline import create_job, run_pipeline, get_job_status
from services.story_engine.cost_guard import pre_flight_check
from services.story_engine.safety import check_content_safety

logger = logging.getLogger("story_engine.routes")
router = APIRouter(prefix="/story-engine", tags=["Story Engine"])


def _get_admin(user: dict = Depends(get_current_user)):
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ═══════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/create")
async def create_story_job(
    req: CreateStoryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Create a new Story Engine job. Performs credit check, safety check,
    and atomically deducts credits. Returns job_id for status polling.
    Pipeline runs in background.
    """
    result = await create_job(
        user_id=user["id"],
        story_text=req.story_text,
        title=req.title or "Untitled",
        style_id=req.style_id,
        language=req.language,
        age_group=req.age_group,
        parent_job_id=req.parent_job_id,
        story_chain_id=req.story_chain_id,
    )

    if not result.get("success"):
        error = result.get("error", "Job creation failed")
        if error == "insufficient_credits":
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": (
                    f"You need {result['credit_check']['required']} credits for Story-to-Video. "
                    f"You currently have {result['credit_check']['current']} credits. "
                    f"Buy at least {result['credit_check']['shortfall']} more credits to continue."
                ),
                "credit_check": result["credit_check"],
            }
        raise HTTPException(status_code=400, detail=error)

    # Run pipeline in background
    job_id = result["job_id"]
    background_tasks.add_task(run_pipeline, job_id)

    return {
        "success": True,
        "job_id": job_id,
        "state": result["state"],
        "credits_deducted": result["credits_deducted"],
        "cost_estimate": result["cost_estimate"],
        "message": "Job created. Pipeline running in background. Poll /status for progress.",
    }


@router.get("/status/{job_id}")
async def get_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get current job status with progress percentage and stage results."""
    status = await get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership (or admin)
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0, "user_id": 1})
    if job and job["user_id"] != user["id"] and user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not your job")

    return {"success": True, **status}


@router.get("/credit-check")
async def credit_check(user: dict = Depends(get_current_user)):
    """
    Pre-flight credit check. Call this BEFORE showing the generation form.
    Returns whether user can afford Story-to-Video.
    """
    user_doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1})
    credits = user_doc.get("credits", 0) if user_doc else 0

    estimate = pre_flight_check(credits)
    return {
        "success": True,
        "sufficient": estimate.sufficient,
        "required": estimate.total_credits_required,
        "current": credits,
        "shortfall": estimate.shortfall,
        "breakdown": estimate.breakdown,
    }


@router.get("/my-jobs")
async def list_user_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """List user's Story Engine jobs with pagination."""
    total = await db.story_engine_jobs.count_documents({"user_id": user["id"]})
    cursor = db.story_engine_jobs.find(
        {"user_id": user["id"]},
        {"_id": 0},
    ).sort("created_at", -1).skip((page - 1) * limit).limit(limit)

    jobs = []
    async for doc in cursor:
        state = JobState(doc["state"])
        from services.story_engine.state_machine import get_progress, get_label
        jobs.append({
            "job_id": doc["job_id"],
            "title": doc.get("title"),
            "state": doc["state"],
            "progress_percent": get_progress(state),
            "current_stage": get_label(state),
            "episode_number": doc.get("episode_number"),
            "style_id": doc.get("style_id"),
            "output_url": doc.get("output_url"),
            "preview_url": doc.get("preview_url"),
            "thumbnail_url": doc.get("thumbnail_url"),
            "created_at": doc.get("created_at"),
            "completed_at": doc.get("completed_at"),
        })

    return {"success": True, "jobs": jobs, "total": total, "page": page}


@router.get("/chain/{chain_id}")
async def get_story_chain(chain_id: str, user: dict = Depends(get_current_user)):
    """Get all episodes in a story chain."""
    cursor = db.story_engine_jobs.find(
        {"story_chain_id": chain_id},
        {"_id": 0, "job_id": 1, "title": 1, "state": 1, "episode_number": 1,
         "output_url": 1, "thumbnail_url": 1, "created_at": 1},
    ).sort("episode_number", 1)

    episodes = await cursor.to_list(length=100)
    return {"success": True, "chain_id": chain_id, "episodes": episodes, "total": len(episodes)}


# ═══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/admin/jobs")
async def admin_list_jobs(
    state: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(_get_admin),
):
    """Admin: List all Story Engine jobs with filters."""
    query = {}
    if state:
        query["state"] = state

    total = await db.story_engine_jobs.count_documents(query)
    cursor = db.story_engine_jobs.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    jobs = await cursor.to_list(length=limit)

    # Stats
    stats = {}
    for s in JobState:
        stats[s.value] = await db.story_engine_jobs.count_documents({"state": s.value})

    return {"success": True, "jobs": jobs, "total": total, "stats": stats, "page": page}


@router.get("/admin/job/{job_id}")
async def admin_get_job(job_id: str, admin: dict = Depends(_get_admin)):
    """Admin: Get full job details including all plans and stage results."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True, "job": job}


@router.post("/admin/retry/{job_id}")
async def admin_retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(_get_admin),
):
    """Admin: Retry a failed job from the beginning."""
    job = await db.story_engine_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["state"] not in ("FAILED", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail=f"Can only retry FAILED/PARTIAL_READY jobs, current: {job['state']}")

    if job.get("retry_count", 0) >= job.get("max_retries", 2):
        raise HTTPException(status_code=400, detail="Max retries exceeded")

    # Reset to INIT
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"state": JobState.INIT.value, "error_message": None}, "$inc": {"retry_count": 1}},
    )

    background_tasks.add_task(run_pipeline, job_id)

    return {"success": True, "message": f"Retrying job {job_id[:8]} (attempt {job.get('retry_count', 0) + 1})"}


@router.get("/admin/pipeline-health")
async def admin_pipeline_health(admin: dict = Depends(_get_admin)):
    """Admin: Pipeline health overview."""
    import os

    total_jobs = await db.story_engine_jobs.count_documents({})
    active = await db.story_engine_jobs.count_documents({"state": {"$nin": ["READY", "PARTIAL_READY", "FAILED"]}})
    ready = await db.story_engine_jobs.count_documents({"state": "READY"})
    failed = await db.story_engine_jobs.count_documents({"state": "FAILED"})

    return {
        "success": True,
        "total_jobs": total_jobs,
        "active_jobs": active,
        "ready_jobs": ready,
        "failed_jobs": failed,
        "success_rate": round(ready / max(total_jobs, 1) * 100, 1),
        "gpu_endpoints": {
            "wan_t2v": bool(os.environ.get("WAN_T2V_ENDPOINT")),
            "wan_i2v": bool(os.environ.get("WAN_I2V_ENDPOINT")),
            "keyframe": bool(os.environ.get("KEYFRAME_GEN_ENDPOINT")),
            "kokoro_tts": bool(os.environ.get("KOKORO_TTS_ENDPOINT")),
        },
        "note": "GPU workers not connected" if not os.environ.get("WAN_T2V_ENDPOINT") else "GPU workers active",
    }
