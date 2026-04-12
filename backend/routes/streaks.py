"""
Competition-Based Streak System — Daily habit identity layer.

Streak increments when user participates in:
  - Battle (branch creation)
  - Daily War (war entry)
  - Story continuation/remix (episode or branch)

Reset: No participation in 28h (24h + 4h grace) → streak resets.
Boost: +2% per day, capped at 10% (5 days).
Notifications: "Your streak is about to break" for streak >= 2.

Collection: user_streaks
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, get_current_user, get_optional_user

logger = logging.getLogger("streaks")
router = APIRouter(prefix="/streaks", tags=["Streaks"])

STREAK_WINDOW_HOURS = 28
STREAK_BOOST_PER_DAY = 0.02
STREAK_BOOST_CAP = 0.10

STREAK_MILESTONES = {
    3: {"label": "Rising", "emoji_label": "Rising Competitor"},
    5: {"label": "Legendary", "emoji_label": "Legendary Streak"},
    7: {"label": "Unstoppable", "emoji_label": "Unstoppable Force"},
    14: {"label": "Mythic", "emoji_label": "Mythic Creator"},
    30: {"label": "Immortal", "emoji_label": "Immortal Legend"},
}


def get_streak_milestone(days):
    milestone = None
    for threshold in sorted(STREAK_MILESTONES.keys(), reverse=True):
        if days >= threshold:
            milestone = STREAK_MILESTONES[threshold]
            break
    return milestone


def get_next_milestone(days):
    for threshold in sorted(STREAK_MILESTONES.keys()):
        if days < threshold:
            return {"threshold": threshold, "days_remaining": threshold - days, **STREAK_MILESTONES[threshold]}
    return None


def compute_streak_boost(streak_days):
    return min(streak_days * STREAK_BOOST_PER_DAY, STREAK_BOOST_CAP)


async def get_user_streak(user_id):
    streak = await db.user_streaks.find_one({"user_id": user_id}, {"_id": 0})
    if not streak:
        streak = {
            "user_id": user_id, "current_streak": 0, "longest_streak": 0,
            "last_activity_date": None, "last_activity_at": None,
            "streak_boost": 0.0, "total_participations": 0,
        }
    return streak


async def record_participation(user_id, activity_type, job_id=None):
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    streak = await get_user_streak(user_id)
    last_date = streak.get("last_activity_date")
    current = streak.get("current_streak", 0)
    longest = streak.get("longest_streak", 0)

    if last_date == today_str:
        await db.user_streaks.update_one(
            {"user_id": user_id},
            {"$inc": {"total_participations": 1}, "$set": {"last_activity_at": now.isoformat()}},
            upsert=True,
        )
        return {"streak_changed": False, "current_streak": current}

    if last_date:
        last = datetime.strptime(last_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hours_since = (now - last).total_seconds() / 3600
        new_streak = current + 1 if hours_since <= STREAK_WINDOW_HOURS else 1
    else:
        new_streak = 1

    new_longest = max(longest, new_streak)
    boost = compute_streak_boost(new_streak)

    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id, "current_streak": new_streak, "longest_streak": new_longest,
            "last_activity_date": today_str, "last_activity_at": now.isoformat(), "streak_boost": boost,
        }, "$inc": {"total_participations": 1}},
        upsert=True,
    )

    event = "streak_incremented" if new_streak > 1 else "streak_started"
    try:
        await db.analytics_events.insert_one({
            "event": event, "user_id": user_id,
            "data": {"streak": new_streak, "activity_type": activity_type, "job_id": job_id, "boost": boost},
            "created_at": now.isoformat(),
        })
    except Exception:
        pass

    milestone_reached = None
    if new_streak in STREAK_MILESTONES:
        milestone_reached = STREAK_MILESTONES[new_streak]
        await db.notifications.insert_one({
            "user_id": user_id, "type": "streak_milestone",
            "title": f"{milestone_reached['emoji_label']} — {new_streak}-Day Streak!",
            "message": f"You've competed {new_streak} days in a row. Keep going!",
            "data": {"streak": new_streak, "milestone": milestone_reached["label"], "deep_link": "/app"},
            "read": False, "created_at": now.isoformat(),
        })

    return {"streak_changed": True, "current_streak": new_streak, "previous_streak": current,
            "boost": boost, "milestone_reached": milestone_reached}


async def check_streak_at_risk():
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    at_risk = await db.user_streaks.find(
        {"current_streak": {"$gte": 2}, "last_activity_date": yesterday_str},
        {"_id": 0, "user_id": 1, "current_streak": 1}
    ).to_list(100)

    for u in at_risk:
        existing = await db.notifications.find_one({
            "user_id": u["user_id"], "type": "streak_at_risk",
            "created_at": {"$gte": today_str},
        })
        if existing:
            continue

        streak = u["current_streak"]
        await db.notifications.insert_one({
            "user_id": u["user_id"], "type": "streak_at_risk",
            "title": f"Your {streak}-day streak is about to break!",
            "message": "Compete in a battle or war today to keep it alive.",
            "data": {"streak": streak, "deep_link": "/app/war"},
            "read": False, "created_at": now.isoformat(),
        })

        try:
            from routes.push_notifications import send_push_to_user
            await send_push_to_user(u["user_id"], "near_win",
                f"Your {streak}-day streak is about to break!",
                "Compete today to keep it alive. Don't lose your progress.", "/app/war")
        except Exception:
            pass


@router.get("/me")
async def get_my_streak(current_user: dict = Depends(get_current_user)):
    user_id = current_user.get("id") or str(current_user.get("_id"))
    streak = await get_user_streak(user_id)
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    current = streak.get("current_streak", 0)
    last_date = streak.get("last_activity_date")

    is_active = False
    if last_date:
        last = datetime.strptime(last_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        hours_since = (now - last).total_seconds() / 3600
        is_active = hours_since <= STREAK_WINDOW_HOURS

    if not is_active and current > 0:
        await db.user_streaks.update_one(
            {"user_id": user_id}, {"$set": {"current_streak": 0, "streak_boost": 0.0}}
        )
        try:
            await db.analytics_events.insert_one({
                "event": "streak_broken", "user_id": user_id,
                "data": {"broken_streak": current}, "created_at": now.isoformat(),
            })
        except Exception:
            pass
        current = 0

    participated_today = last_date == today_str
    boost = compute_streak_boost(current)

    return {
        "success": True,
        "streak": {
            "current": current, "longest": streak.get("longest_streak", 0),
            "is_active": is_active and current > 0, "participated_today": participated_today,
            "boost": boost, "boost_percent": f"+{boost*100:.0f}%",
            "total_participations": streak.get("total_participations", 0),
            "milestone": get_streak_milestone(current),
            "next_milestone": get_next_milestone(current),
        },
    }


@router.get("/leaderboard")
async def streak_leaderboard(limit: int = Query(default=10, le=30), current_user: dict = Depends(get_optional_user)):
    streaks = await db.user_streaks.find(
        {"current_streak": {"$gt": 0}}, {"_id": 0, "user_id": 1, "current_streak": 1, "longest_streak": 1}
    ).sort("current_streak", -1).limit(limit).to_list(limit)

    user_ids = [s["user_id"] for s in streaks]
    user_map = {}
    if user_ids:
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(50)
        user_map = {u["id"]: u.get("name") or u.get("email", "").split("@")[0] for u in users}

    for s in streaks:
        s["creator_name"] = user_map.get(s["user_id"], "Anonymous")
        s["milestone"] = get_streak_milestone(s["current_streak"])

    return {"success": True, "streaks": streaks, "total": len(streaks)}


async def create_streak_indexes():
    try:
        await db.user_streaks.create_index("user_id", unique=True)
        await db.user_streaks.create_index([("current_streak", -1)])
        await db.user_streaks.create_index("last_activity_date")
    except Exception as e:
        logger.warning(f"[STREAK] Index creation failed: {e}")
