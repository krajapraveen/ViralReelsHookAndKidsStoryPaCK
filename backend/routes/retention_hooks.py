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
    """Public: Get today's daily challenge with leaderboard entries."""
    svc = get_retention_service(db)
    challenge = await svc.get_todays_challenge()
    leaderboard = []
    if challenge:
        leaderboard = await svc.get_challenge_entries(challenge["challenge_id"], limit=10)
    return {"success": True, "challenge": challenge, "leaderboard": leaderboard}


@router.get("/challenge/winner")
async def get_challenge_winner():
    """Public: Get today's featured challenge winner (highest weighted score)."""
    svc = get_retention_service(db)
    challenge = await svc.get_todays_challenge()
    if not challenge:
        return {"success": True, "winner": None}
    entries = await svc.get_challenge_entries(challenge["challenge_id"], limit=50)
    if not entries:
        return {"success": True, "winner": None}

    # Compute weighted scores and pick winner
    job_ids = [e["job_id"] for e in entries]
    remix_stats = await svc.get_job_remix_stats(job_ids)

    best = None
    best_score = -1
    best_reason = "Most viewed"
    for e in entries:
        rc = remix_stats.get(e["job_id"], 0)
        views = e.get("views", 0) or 0
        score = rc * 0.6 + views * 0.4
        if score > best_score:
            best_score = score
            best = {**e, "remix_count": rc, "views": views, "score": round(score, 1)}
            if rc > views:
                best_reason = "Most remixed today"
            elif views > 0:
                best_reason = "Most viewed challenge entry"
            else:
                best_reason = "Today's featured entry"

    if best:
        # Get creator name (if public profile)
        creator_name = "Anonymous Creator"
        if best.get("user_id"):
            user = await db.users.find_one({"id": best["user_id"]}, {"_id": 0, "name": 1, "display_name": 1})
            if user:
                creator_name = user.get("display_name") or user.get("name") or "Anonymous Creator"
        best["creator_name"] = creator_name
        best["reason_badge"] = best_reason
        best["challenge_title"] = challenge.get("title", "")

    return {"success": True, "winner": best}


@router.get("/challenge/winners/archive")
async def get_past_winners(limit: int = 7):
    """Public: Get past challenge winners (last N days)."""
    winners = await db.challenge_winners.find(
        {}, {"_id": 0}
    ).sort("date", -1).limit(limit).to_list(length=limit)
    return {"success": True, "winners": winners}


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


@router.post("/improve-consistency/{job_id}")
async def improve_consistency(job_id: str, user: dict = Depends(get_current_user)):
    """Targeted retry: regenerate only the character consistency stage for a completed job.
    Max 1 improvement attempt per job."""
    user_id = user.get("id") or str(user.get("_id"))

    job = await db.story_engine_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0, "user_id": 1, "state": 1, "fallback_in_use": 1, "consistency_retry_count": 1, "title": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your job")
    if job.get("state") not in ("READY", "PARTIAL_READY"):
        raise HTTPException(status_code=400, detail="Job must be completed first")

    # Max 1 retry
    if job.get("consistency_retry_count", 0) >= 1:
        raise HTTPException(status_code=400, detail="Consistency improvement already attempted for this job")

    # Mark as improving
    await db.story_engine_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"consistency_retry_count": 1, "consistency_improving": True}}
    )

    # Track analytics
    try:
        await db.analytics_events.insert_one({
            "event": "consistency_improvement_started",
            "user_id": user_id,
            "data": {"job_id": job_id, "title": job.get("title", "")},
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception:
        pass

    return {"success": True, "message": "Consistency improvement started", "job_id": job_id}


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


# ─── CREATOR DIGEST ──────────────────────────────────────────────────────────

@router.get("/digest/preview/{user_id}")
async def preview_digest(user_id: str, user: dict = Depends(get_current_user)):
    """Admin: Preview a digest for any user without sending."""
    if user.get("role", "").upper() not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")
    svc = get_retention_service(db)
    digest = await svc.compute_digest(user_id)
    if not digest:
        return {"success": True, "digest": None, "reason": "No meaningful activity this week"}
    return {"success": True, "digest": digest}


@router.post("/digest/send/{user_id}")
async def send_single_digest(user_id: str, user: dict = Depends(get_current_user)):
    """Admin: Send digest to a specific user (for testing)."""
    if user.get("role", "").upper() not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")
    svc = get_retention_service(db)
    digest = await svc.compute_digest(user_id)
    if not digest:
        return {"success": False, "reason": "No meaningful activity — digest skipped"}
    result = await svc.send_digest(user_id, digest)
    return {"success": True, "sent": result is not None, "digest": digest}


@router.post("/digest/run")
async def run_weekly_digest(user: dict = Depends(get_current_user)):
    """Admin: Trigger weekly digest run for all active creators."""
    if user.get("role", "").upper() not in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(status_code=403, detail="Admin only")
    svc = get_retention_service(db)
    summary = await svc.run_weekly_digest()
    return {"success": True, "summary": summary}
