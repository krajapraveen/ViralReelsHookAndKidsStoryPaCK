"""
Retention Routes — Daily challenges, ownership stats, leaderboard, email preview (admin).
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.retention_service import get_retention_service

router = APIRouter(prefix="/retention", tags=["Retention"])


# ─── DAILY CHALLENGE ──────────────────────────────────────────────────────────

@router.get("/challenge/today")
async def get_todays_challenge():
    """Public: Get today's daily challenge."""
    svc = get_retention_service(db)
    challenge = await svc.get_todays_challenge()
    return {"success": True, "challenge": challenge}


@router.post("/challenge")
async def create_challenge(request: Request, user: dict = Depends(get_current_user)):
    """Admin: Create a new daily challenge."""
    if user.get("role", "").upper() not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    title = body.get("title")
    prompt_seed = body.get("prompt_seed", "")
    active_date = body.get("active_date")
    category = body.get("category", "general")
    if not title or not active_date:
        raise HTTPException(status_code=400, detail="title and active_date required")
    svc = get_retention_service(db)
    challenge = await svc.create_challenge(title, prompt_seed, active_date, category)
    return {"success": True, "challenge": challenge}


@router.get("/challenge/{challenge_id}/entries")
async def get_challenge_entries(challenge_id: str):
    """Public: Get entries for a challenge."""
    svc = get_retention_service(db)
    entries = await svc.get_challenge_entries(challenge_id)
    return {"success": True, "entries": entries}


# ─── OWNERSHIP STATS ─────────────────────────────────────────────────────────

@router.post("/remix-stats")
async def get_remix_stats(request: Request, user: dict = Depends(get_current_user)):
    """Get remix counts for user's jobs. Body: { job_ids: [...] }"""
    body = await request.json()
    job_ids = body.get("job_ids", [])
    if not job_ids or len(job_ids) > 100:
        return {"success": True, "stats": {}}
    svc = get_retention_service(db)
    stats = await svc.get_job_remix_stats(job_ids)
    return {"success": True, "stats": stats}


# ─── LEADERBOARD ─────────────────────────────────────────────────────────────

@router.get("/top-stories")
async def get_top_stories():
    """Public: Get top stories this week."""
    svc = get_retention_service(db)
    stories = await svc.get_top_stories_today()
    return {"success": True, "stories": stories}


# ─── EMAIL PREVIEW (Admin) ───────────────────────────────────────────────────

@router.get("/email-events")
async def get_email_events(
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Admin: Preview simulated email events."""
    if user.get("role", "").upper() not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")
    events = await db.email_events.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    total = await db.email_events.count_documents({})
    return {"success": True, "events": events, "total": total}
