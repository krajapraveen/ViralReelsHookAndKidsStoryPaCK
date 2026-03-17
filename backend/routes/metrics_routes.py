"""
Re-engagement metrics tracking and reporting.
Instruments: continue_rate, 24h_return_rate, avg_chain_length, suggestion_ctr, resume_from_banner_rate
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/metrics", tags=["Metrics"])


class TrackEventRequest(BaseModel):
    event: str  # e.g. "continue_from_banner", "suggestion_click", "chain_continue", "login_interstitial_continue"
    chain_id: Optional[str] = None
    meta: Optional[dict] = None


@router.post("/track")
async def track_event(req: TrackEventRequest, user: dict = Depends(get_current_user)):
    """Lightweight event ingestion for re-engagement metrics."""
    await db.reengagement_events.insert_one({
        "user_id": user["id"],
        "event": req.event,
        "chain_id": req.chain_id,
        "meta": req.meta or {},
        "ts": datetime.now(timezone.utc),
    })
    return {"ok": True}


@router.get("/reengagement")
async def reengagement_report(admin: dict = Depends(get_admin_user)):
    """Admin-only aggregated re-engagement dashboard."""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    # ── continue_rate: chains with >1 completed episode / all chains with >=1 completed
    all_chains = await db.photo_to_comic_jobs.aggregate([
        {"$match": {"story_chain_id": {"$exists": True}, "status": {"$in": ["COMPLETED", "PARTIAL_COMPLETE"]}}},
        {"$group": {"_id": "$story_chain_id", "ep": {"$sum": 1}}},
    ]).to_list(10000)
    total_chains = len(all_chains)
    continued_chains = sum(1 for c in all_chains if c["ep"] > 1)
    continue_rate = round(continued_chains / total_chains * 100, 1) if total_chains else 0

    # ── avg_chain_length
    avg_chain_length = round(sum(c["ep"] for c in all_chains) / total_chains, 1) if total_chains else 0

    # ── 24h_return_rate: users who had activity >24h ago AND activity in last 24h
    recent_users = set()
    async for doc in db.reengagement_events.find({"ts": {"$gte": day_ago}}, {"user_id": 1}):
        recent_users.add(doc["user_id"])
    older_users = set()
    async for doc in db.reengagement_events.find({"ts": {"$lt": day_ago, "$gte": week_ago}}, {"user_id": 1}):
        older_users.add(doc["user_id"])
    returning = recent_users & older_users
    return_rate_24h = round(len(returning) / len(older_users) * 100, 1) if older_users else 0

    # ── suggestion_ctr: suggestion_click / suggestion_view
    views = await db.reengagement_events.count_documents({"event": "suggestion_view", "ts": {"$gte": week_ago}})
    clicks = await db.reengagement_events.count_documents({"event": "suggestion_click", "ts": {"$gte": week_ago}})
    suggestion_ctr = round(clicks / views * 100, 1) if views else 0

    # ── resume_from_banner_rate
    banner_shows = await db.reengagement_events.count_documents({"event": "banner_shown", "ts": {"$gte": week_ago}})
    banner_clicks = await db.reengagement_events.count_documents({"event": "continue_from_banner", "ts": {"$gte": week_ago}})
    banner_rate = round(banner_clicks / banner_shows * 100, 1) if banner_shows else 0

    # ── interstitial metrics
    interstitial_shown = await db.reengagement_events.count_documents({"event": "login_interstitial_shown", "ts": {"$gte": week_ago}})
    interstitial_clicked = await db.reengagement_events.count_documents({"event": "login_interstitial_continue", "ts": {"$gte": week_ago}})
    interstitial_rate = round(interstitial_clicked / interstitial_shown * 100, 1) if interstitial_shown else 0

    return {
        "period": "7d",
        "continue_rate": continue_rate,
        "avg_chain_length": avg_chain_length,
        "return_rate_24h": return_rate_24h,
        "suggestion_ctr": suggestion_ctr,
        "resume_from_banner_rate": banner_rate,
        "login_interstitial_rate": interstitial_rate,
        "raw": {
            "total_chains": total_chains,
            "continued_chains": continued_chains,
            "suggestion_views": views,
            "suggestion_clicks": clicks,
            "banner_shows": banner_shows,
            "banner_clicks": banner_clicks,
            "interstitial_shown": interstitial_shown,
            "interstitial_clicked": interstitial_clicked,
        }
    }
