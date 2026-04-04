"""
Daily Viral Idea Drop — V2 API Routes
Orchestrated bundle generation with immediate job_id return + polling.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from shared import db, get_current_user
from services.viral import viral_job_service as jobs
from services.viral.task_dispatch import dispatch_task, Q_ORCHESTRATOR

logger = logging.getLogger("viral.routes")
router = APIRouter(prefix="/viral-ideas", tags=["Viral Ideas V2"])


class GenerateBundleRequest(BaseModel):
    idea: str
    niche: str = "Tech"


class GenerateBundleResponse(BaseModel):
    job_id: str
    status: str
    message: str


# ==================== DAILY FEED ====================
@router.get("/daily-feed")
async def get_daily_feed(niche: Optional[str] = None):
    """Public endpoint: curated daily viral ideas"""
    from routes.daily_viral_ideas import get_daily_ideas, NICHES
    ideas = await get_daily_ideas(niche=niche, count=12)
    return {
        "success": True,
        "ideas": ideas,
        "niches": NICHES,
        "date": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).date().isoformat(),
    }


# ==================== GENERATE BUNDLE ====================
@router.post("/generate-bundle", response_model=GenerateBundleResponse)
async def generate_bundle(req: GenerateBundleRequest, user: dict = Depends(get_current_user)):
    """
    Kick off bundle generation. Returns immediately with job_id.
    Credits are deducted upfront.
    """
    user_id = str(user["id"])
    credit_cost = 5

    # Check credits
    if user.get("credits", 0) < credit_cost:
        raise HTTPException(status_code=402, detail="Insufficient credits. 5 credits required.")

    # Deduct credits BEFORE generation
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credit_cost}})

    # Log credit transaction
    await db.credit_transactions.insert_one({
        "user_id": user_id,
        "amount": -credit_cost,
        "type": "viral_bundle",
        "description": f"Viral content pack: {req.idea[:60]}",
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    })

    # Create job
    result = await jobs.create_job(db, user_id, req.idea, req.niche)
    job_id = result["job_id"]

    # Dispatch to orchestrator — returns immediately
    await dispatch_task(Q_ORCHESTRATOR, {
        "job_id": job_id,
        "idea": req.idea,
        "niche": req.niche,
    })

    return GenerateBundleResponse(
        job_id=job_id,
        status="pending",
        message="Your content pack is being created!",
    )


# ==================== JOB STATUS (POLLING) ====================
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Poll job status. Frontend polls every 2s until ready."""
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    tasks = await jobs.get_tasks_for_job(db, job_id)

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "tasks": [
            {
                "task_id": t["task_id"],
                "task_type": t["task_type"],
                "status": t["status"],
                "fallback_used": t.get("fallback_used", False),
            }
            for t in tasks
        ],
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
        "completed_at": job["completed_at"].isoformat() if job.get("completed_at") else None,
    }


# ==================== JOB ASSETS ====================
@router.get("/jobs/{job_id}/assets")
async def get_job_assets(job_id: str, user: dict = Depends(get_current_user)):
    """Get all completed assets for a job. Available even if packaging failed."""
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    assets = await jobs.get_assets(db, job_id)

    return {
        "job_id": job_id,
        "status": job["status"],
        "assets": [
            {
                "asset_id": a["asset_id"],
                "asset_type": a["asset_type"],
                "content": a.get("content"),
                "file_url": a.get("file_url"),
                "mime_type": a.get("mime_type", "text/plain"),
                "created_at": a["created_at"].isoformat() if a.get("created_at") else None,
            }
            for a in assets
        ],
    }


# ==================== USER'S JOBS ====================
@router.get("/my-jobs")
async def get_my_jobs(user: dict = Depends(get_current_user)):
    """Get user's recent generation jobs"""
    user_jobs = await jobs.get_user_jobs(db, str(user["id"]), limit=20)
    return {
        "jobs": [
            {
                "job_id": j["job_id"],
                "idea": j["idea"],
                "niche": j["niche"],
                "status": j["status"],
                "progress": j["progress"],
                "created_at": j["created_at"].isoformat() if j.get("created_at") else None,
                "completed_at": j["completed_at"].isoformat() if j.get("completed_at") else None,
            }
            for j in user_jobs
        ],
    }
