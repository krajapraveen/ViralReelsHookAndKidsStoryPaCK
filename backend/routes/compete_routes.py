"""
Compete Mechanics — Top Story Today, Most Continued, Fastest Growing Character
All data is truth-based from real DB records. No synthetic data.
"""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Query
from shared import db

logger = logging.getLogger("creatorstudio.compete")
router = APIRouter(prefix="/compete", tags=["compete"])


def _cutoff(hours: int = 24):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@router.get("/trending")
async def get_trending():
    """Get all compete metrics in a single call for the frontend."""
    cutoff_24h = _cutoff(24)
    cutoff_7d = _cutoff(168)

    # ── Top Story Today (by continuation + share events in last 24h) ──
    top_story = None
    cont_pipeline = [
        {"$match": {
            "event": {"$in": ["share_to_continue", "share_click", "continue_click"]},
            "timestamp": {"$gte": cutoff_24h},
            "source_job_id": {"$exists": True, "$ne": None},
        }},
        {"$group": {"_id": "$source_job_id", "score": {"$sum": 1}}},
        {"$sort": {"score": -1}},
        {"$limit": 1},
    ]
    async for doc in db.growth_events.aggregate(cont_pipeline):
        job = await db.pipeline_jobs.find_one(
            {"job_id": doc["_id"], "status": "COMPLETED", "thumbnail_url": {"$exists": True, "$ne": None}},
            {"_id": 0, "job_id": 1, "title": 1, "slug": 1, "thumbnail_url": 1, "animation_style": 1},
        )
        if job:
            top_story = {**job, "score": doc["score"], "badge": "#1 Trending"}

    # Fallback: most recent completed story with shares
    if not top_story:
        share_reward = await db.share_rewards.find_one(
            {"type": {"$in": ["continuation_reward", None]}},
            {"_id": 0, "source_job_id": 1},
            sort=[("timestamp", -1)],
        )
        if share_reward and share_reward.get("source_job_id"):
            job = await db.pipeline_jobs.find_one(
                {"job_id": share_reward["source_job_id"], "status": "COMPLETED"},
                {"_id": 0, "job_id": 1, "title": 1, "slug": 1, "thumbnail_url": 1, "animation_style": 1},
            )
            if job:
                top_story = {**job, "score": 1, "badge": "#1 Trending"}

    # ── Most Continued Story (all time, by continuation rewards) ──
    most_continued = None
    mc_pipeline = [
        {"$match": {"type": "continuation_reward"}},
        {"$group": {"_id": "$source_job_id", "continuations": {"$sum": 1}}},
        {"$sort": {"continuations": -1}},
        {"$limit": 1},
    ]
    async for doc in db.share_rewards.aggregate(mc_pipeline):
        job = await db.pipeline_jobs.find_one(
            {"job_id": doc["_id"], "status": "COMPLETED"},
            {"_id": 0, "job_id": 1, "title": 1, "slug": 1, "thumbnail_url": 1, "animation_style": 1},
        )
        if job:
            most_continued = {**job, "continuations": doc["continuations"], "badge": "Most Continued"}

    # ── Fastest Growing Character (most new stories in 24h) ──
    fastest_char = None
    char_pipeline = [
        {"$match": {
            "status": "COMPLETED",
            "completed_at": {"$gte": cutoff_24h},
            "extracted_characters": {"$exists": True, "$ne": []},
        }},
        {"$unwind": "$extracted_characters"},
        {"$group": {
            "_id": "$extracted_characters.name",
            "story_count": {"$sum": 1},
            "latest_thumbnail": {"$last": "$thumbnail_url"},
        }},
        {"$sort": {"story_count": -1}},
        {"$limit": 1},
    ]
    async for doc in db.pipeline_jobs.aggregate(char_pipeline):
        if doc["_id"] and doc["story_count"] > 0:
            fastest_char = {
                "name": doc["_id"],
                "stories_24h": doc["story_count"],
                "thumbnail": doc.get("latest_thumbnail"),
                "badge": "Rising Fast",
            }

    # ── Rising Stories (top 5 by recent activity, last 7 days) ──
    rising = []
    rising_pipeline = [
        {"$match": {
            "event": {"$in": ["share_click", "continue_click", "share_to_continue"]},
            "timestamp": {"$gte": cutoff_7d},
            "source_job_id": {"$exists": True, "$ne": None},
        }},
        {"$group": {"_id": "$source_job_id", "score": {"$sum": 1}}},
        {"$sort": {"score": -1}},
        {"$limit": 5},
    ]
    async for doc in db.growth_events.aggregate(rising_pipeline):
        job = await db.pipeline_jobs.find_one(
            {"job_id": doc["_id"], "status": "COMPLETED", "thumbnail_url": {"$exists": True, "$ne": None}},
            {"_id": 0, "job_id": 1, "title": 1, "slug": 1, "thumbnail_url": 1, "animation_style": 1},
        )
        if job:
            rising.append({**job, "score": doc["score"]})

    has_data = bool(top_story or most_continued or fastest_char or rising)

    return {
        "success": True,
        "has_data": has_data,
        "top_story_today": top_story,
        "most_continued": most_continued,
        "fastest_character": fastest_char,
        "rising_stories": rising,
    }


@router.get("/live-viewers")
async def get_live_viewers():
    """Real viewer count from recent sessions (last 5 min). No fake numbers."""
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    count = await db.user_sessions.count_documents({
        "last_active": {"$gte": five_min_ago}
    })

    # Also count recent page_view events as a proxy
    pv_count = await db.growth_events.count_documents({
        "event": "page_view",
        "timestamp": {"$gte": five_min_ago},
    })

    total = max(count, pv_count)

    return {
        "success": True,
        "viewers": total,
        "label": f"{total} people viewing now" if total >= 3 else "Few people viewing now" if total > 0 else None,
        "show": total > 0,
    }
