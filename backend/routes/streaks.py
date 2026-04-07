"""
Streak & Progress Tracking — Daily generation streaks and milestone rewards.
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user

router = APIRouter(prefix="/streaks", tags=["Streaks"])


@router.get("/my")
async def get_my_streak(user: dict = Depends(get_current_user)):
    """Get current user's streak data: today's count, streak days, total all-time."""
    user_id = user.get("id", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    # Get today's generation count from jobs
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": today_start.isoformat()},
        "status": {"$in": ["COMPLETED", "PARTIAL"]},
    })

    # Get all-time count
    total_count = await db.jobs.count_documents({
        "user_id": user_id,
        "status": {"$in": ["COMPLETED", "PARTIAL"]},
    })

    # Streak: count consecutive days with at least 1 generation
    streak_days = 0
    check_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(30):  # max 30 day lookback
        day_start = check_date - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        had_gen = await db.jobs.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()},
            "status": {"$in": ["COMPLETED", "PARTIAL"]},
        })
        if had_gen > 0:
            streak_days += 1
        else:
            if i == 0:
                continue  # today might not have any yet
            break

    # Milestones
    milestones = [
        {"target": 3, "label": "Warming Up", "reward": "Keep going!"},
        {"target": 5, "label": "On Fire", "reward": "Unlock bonus style"},
        {"target": 10, "label": "Creative Machine", "reward": "Premium generation"},
        {"target": 25, "label": "Story Legend", "reward": "Exclusive badge"},
    ]
    current_milestone = None
    for m in milestones:
        if today_count < m["target"]:
            current_milestone = m
            break

    return {
        "today_count": today_count,
        "total_count": total_count,
        "streak_days": streak_days,
        "current_milestone": current_milestone,
        "milestones": milestones,
    }


@router.get("/social-proof")
async def get_social_proof():
    """Get real social proof numbers from DB."""
    total_users = await db.users.count_documents({})
    total_generations = await db.jobs.count_documents({"status": {"$in": ["COMPLETED", "PARTIAL"]}})

    # Active today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active_today = await db.jobs.distinct("user_id", {
        "created_at": {"$gte": today_start.isoformat()},
    })

    return {
        "total_creators": total_users,
        "total_generations": total_generations,
        "active_today": len(active_today),
    }
