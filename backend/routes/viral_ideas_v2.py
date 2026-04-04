"""
Daily Viral Idea Drop — V2 API Routes
Orchestrated bundle generation with immediate job_id return + polling.
Includes feedback flow and repair endpoint.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from shared import db, get_current_user
from services.viral import viral_job_service as jobs
from services.viral.task_dispatch import dispatch_task, Q_ORCHESTRATOR, Q_REPAIR

logger = logging.getLogger("viral.routes")
router = APIRouter(prefix="/viral-ideas", tags=["Viral Ideas V2"])


class GenerateBundleRequest(BaseModel):
    idea: str
    niche: str = "Tech"


class GenerateBundleResponse(BaseModel):
    job_id: str
    status: str
    message: str


class FeedbackRequest(BaseModel):
    signal: str  # useful, not_useful, regenerate_angle, more_aggressive_hook, safer_hook, better_captions
    asset_type: Optional[str] = None  # hooks, script, captions, thumbnail, voiceover, video
    comment: Optional[str] = None


VALID_SIGNALS = {"useful", "not_useful", "regenerate_angle", "more_aggressive_hook", "safer_hook", "better_captions"}


# ==================== DAILY FEED ====================
@router.get("/daily-feed")
async def get_daily_feed(niche: Optional[str] = None):
    from routes.daily_viral_ideas import get_daily_ideas, NICHES
    ideas = await get_daily_ideas(niche=niche, count=12)
    return {
        "success": True,
        "ideas": ideas,
        "niches": NICHES,
        "date": datetime.now(timezone.utc).date().isoformat(),
    }


# ==================== GENERATE BUNDLE ====================
@router.post("/generate-bundle", response_model=GenerateBundleResponse)
async def generate_bundle(req: GenerateBundleRequest, user: dict = Depends(get_current_user)):
    user_id = str(user["id"])
    credit_cost = 5

    if user.get("credits", 0) < credit_cost:
        raise HTTPException(status_code=402, detail="Insufficient credits. 5 credits required.")

    await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": -credit_cost}})
    await db.credit_transactions.insert_one({
        "user_id": user_id,
        "amount": -credit_cost,
        "type": "viral_bundle",
        "description": f"Viral content pack: {req.idea[:60]}",
        "created_at": datetime.now(timezone.utc),
    })

    result = await jobs.create_job(db, user_id, req.idea, req.niche)
    job_id = result["job_id"]

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
                "attempts": t.get("attempts", 0),
                "failure_reason": t.get("failure_reason"),
            }
            for t in tasks
        ],
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
        "completed_at": job["completed_at"].isoformat() if job.get("completed_at") else None,
    }


# ==================== JOB ASSETS ====================
@router.get("/jobs/{job_id}/assets")
async def get_job_assets(job_id: str, user: dict = Depends(get_current_user)):
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


# ==================== FEEDBACK ====================
@router.post("/jobs/{job_id}/feedback")
async def submit_feedback(job_id: str, req: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Submit feedback signal for a job or specific asset."""
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    if req.signal not in VALID_SIGNALS:
        raise HTTPException(status_code=400, detail=f"Invalid signal. Valid: {', '.join(VALID_SIGNALS)}")

    await db.viral_feedback.insert_one({
        "feedback_id": str(uuid.uuid4()),
        "job_id": job_id,
        "user_id": str(user["id"]),
        "signal": req.signal,
        "asset_type": req.asset_type,
        "comment": req.comment,
        "idea": job.get("idea"),
        "niche": job.get("niche"),
        "created_at": datetime.now(timezone.utc),
    })

    return {"success": True, "message": "Feedback recorded"}


# ==================== REPAIR ====================
@router.post("/jobs/{job_id}/repair")
async def repair_job(job_id: str, user: dict = Depends(get_current_user), target_task_type: Optional[str] = None):
    """Repair a job by retrying failed/missing tasks."""
    job = await jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_id"] != str(user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    await dispatch_task(Q_REPAIR, {
        "job_id": job_id,
        "target_task_type": target_task_type,
    })

    return {"success": True, "message": "Repair initiated. Check status for updates."}


# ==================== FEEDBACK QUERY (for future ranking) ====================
@router.get("/feedback/summary")
async def get_feedback_summary(niche: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Query aggregated feedback — used for future ranking/personalization."""
    match = {}
    if niche:
        match["niche"] = niche

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"signal": "$signal", "asset_type": "$asset_type", "niche": "$niche"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"count": -1}},
        {"$limit": 50},
    ]
    results = await db.viral_feedback.aggregate(pipeline).to_list(50)
    return {
        "summary": [
            {
                "signal": r["_id"]["signal"],
                "asset_type": r["_id"].get("asset_type"),
                "niche": r["_id"].get("niche"),
                "count": r["count"],
            }
            for r in results
        ],
    }
