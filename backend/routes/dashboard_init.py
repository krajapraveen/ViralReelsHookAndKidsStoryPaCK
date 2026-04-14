"""
Dashboard Init — Single consolidated endpoint for the entire dashboard.
Replaces 7 separate API calls with 1.
"""
import os
import sys
import logging
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from cachetools import TTLCache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

logger = logging.getLogger("dashboard_init")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_init_cache = TTLCache(maxsize=64, ttl=20)


async def _get_story_feed(user_id):
    """Lean version of engagement/story-feed — returns just what the dashboard needs."""
    try:
        stories = await db.story_engine_jobs.find(
            {"user_id": user_id, "state": {"$in": ["READY", "PARTIAL_READY", "COMPLETED"]}},
            {"_id": 0, "job_id": 1, "title": 1, "state": 1, "animation_style": 1,
             "thumbnail_url": 1, "created_at": 1, "total_views": 1, "total_shares": 1,
             "battle_score": 1, "total_children": 1, "output_url": 1}
        ).sort([("created_at", -1)]).limit(12).to_list(12)
        return {"stories": stories, "count": len(stories)}
    except Exception as e:
        logger.warning(f"Feed fetch failed: {e}")
        return {"stories": [], "count": 0}


async def _get_challenge_today():
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        challenge = await db.daily_challenges.find_one(
            {"date": today, "active": True}, {"_id": 0}
        )
        return challenge
    except Exception:
        return None


async def _get_challenge_winner():
    try:
        winner = await db.challenge_winners.find_one(
            {}, {"_id": 0}, sort=[("created_at", -1)]
        )
        return winner
    except Exception:
        return None


async def _get_top_stories():
    try:
        stories = await db.story_engine_jobs.find(
            {"state": {"$in": ["READY", "COMPLETED"]}, "visibility": {"$in": ["public", None]}},
            {"_id": 0, "job_id": 1, "title": 1, "total_views": 1, "total_shares": 1,
             "battle_score": 1, "thumbnail_url": 1, "user_id": 1, "animation_style": 1}
        ).sort([("battle_score", -1)]).limit(5).to_list(5)
        return stories
    except Exception:
        return []


async def _get_viral_status(user_id):
    try:
        stats = await db.viral_rewards.find_one(
            {"user_id": user_id}, {"_id": 0}
        )
        return stats
    except Exception:
        return None


async def _get_viral_leaderboard():
    try:
        leaders = await db.viral_rewards.find(
            {}, {"_id": 0, "user_id": 1, "total_shares": 1, "total_credits_earned": 1}
        ).sort([("total_shares", -1)]).limit(5).to_list(5)
        return leaders
    except Exception:
        return []


@router.get("/init")
async def dashboard_init(current_user: dict = Depends(get_current_user)):
    """
    Single consolidated dashboard endpoint. Returns everything the dashboard needs
    in one request, replacing 7 separate API calls. Cached for 20s.
    """
    user_id = current_user.get("id") or str(current_user.get("_id", ""))

    cache_key = f"dash_init:{user_id}"
    cached = _init_cache.get(cache_key)
    if cached:
        return cached

    # Run all queries in parallel
    feed, challenge, winner, top_stories, viral_status, viral_leaderboard = await asyncio.gather(
        _get_story_feed(user_id),
        _get_challenge_today(),
        _get_challenge_winner(),
        _get_top_stories(),
        _get_viral_status(user_id),
        _get_viral_leaderboard(),
        return_exceptions=True,
    )

    # Safely extract results (replace exceptions with defaults)
    if isinstance(feed, Exception):
        feed = {"stories": [], "count": 0}
    if isinstance(challenge, Exception):
        challenge = None
    if isinstance(winner, Exception):
        winner = None
    if isinstance(top_stories, Exception):
        top_stories = []
    if isinstance(viral_status, Exception):
        viral_status = None
    if isinstance(viral_leaderboard, Exception):
        viral_leaderboard = []

    result = {
        "success": True,
        "feed": feed,
        "daily_challenge": challenge,
        "challenge_winner": winner,
        "top_stories": top_stories,
        "viral_status": viral_status,
        "viral_leaderboard": viral_leaderboard,
    }

    _init_cache[cache_key] = result
    return result
