"""
Character Universe + Social Layer — Follow, Feed, Rankings, Notifications.
Routes under /api/universe/
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared import db, get_current_user

router = APIRouter(prefix="/universe", tags=["universe"])


def _now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# FOLLOW CHARACTER
# ═══════════════════════════════════════════════════════════════════════════════

class FollowRequest(BaseModel):
    character_id: str

@router.post("/follow")
async def follow_character(data: FollowRequest, user: dict = Depends(get_current_user)):
    """Follow a character. Toggle on/off."""
    user_id = user["id"]
    existing = await db.character_follows.find_one(
        {"user_id": user_id, "character_id": data.character_id}, {"_id": 1}
    )
    if existing:
        await db.character_follows.delete_one({"user_id": user_id, "character_id": data.character_id})
        return {"success": True, "following": False, "message": "Unfollowed"}

    await db.character_follows.insert_one({
        "user_id": user_id,
        "character_id": data.character_id,
        "followed_at": _now().isoformat(),
    })

    # Notify character creator that someone followed their character
    try:
        profile = await db.character_profiles.find_one(
            {"character_id": data.character_id, "status": "active"},
            {"_id": 0, "name": 1, "user_id": 1}
        )
        if profile and profile.get("user_id") and profile["user_id"] != user_id:
            follower = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1})
            follower_name = follower.get("name", "Someone") if follower else "Someone"
            await create_notification(
                user_id=profile["user_id"],
                ntype="follow",
                title=f"{follower_name} followed {profile.get('name', 'your character')}",
                body="Your character is gaining fans!",
                link=f"/character/{data.character_id}",
                meta={"character_id": data.character_id}
            )
    except Exception:
        pass

    return {"success": True, "following": True, "message": "Following!"}


@router.get("/following/{character_id}")
async def check_following(character_id: str, user: dict = Depends(get_current_user)):
    """Check if current user follows a character."""
    existing = await db.character_follows.find_one(
        {"user_id": user["id"], "character_id": character_id}, {"_id": 1}
    )
    return {"following": bool(existing)}


@router.get("/my-follows")
async def get_my_follows(user: dict = Depends(get_current_user)):
    """Get all characters the user follows."""
    follows = await db.character_follows.find(
        {"user_id": user["id"]}, {"_id": 0, "character_id": 1, "followed_at": 1}
    ).sort("followed_at", -1).to_list(50)

    characters = []
    for f in follows:
        profile = await db.character_profiles.find_one(
            {"character_id": f["character_id"], "status": "active"},
            {"_id": 0, "character_id": 1, "name": 1, "role": 1, "portrait_url": 1}
        )
        if profile:
            story_count = await db.pipeline_jobs.count_documents({
                "$or": [
                    {"story_text": {"$regex": profile.get("name", "NOMATCH"), "$options": "i"}},
                    {"characters": f["character_id"]},
                ]
            })
            characters.append({**profile, "story_count": story_count, "followed_at": f["followed_at"]})

    return {"success": True, "characters": characters}


# ═══════════════════════════════════════════════════════════════════════════════
# CHARACTER FEED — Latest stories featuring a character
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/character/{character_id}/stories")
async def character_stories(character_id: str, limit: int = 20):
    """Public: Get latest stories featuring a character."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "status": "active"},
        {"_id": 0, "name": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    char_name = profile.get("name", "NOMATCH")
    stories = await db.pipeline_jobs.find(
        {
            "status": "COMPLETED",
            "thumbnail_url": {"$exists": True, "$nin": [None, ""]},
            "$or": [
                {"story_text": {"$regex": char_name, "$options": "i"}},
                {"characters": character_id},
                {"extracted_characters": {"$elemMatch": {"character_id": character_id}}},
            ]
        },
        {
            "_id": 0, "job_id": 1, "title": 1, "thumbnail_url": 1, "story_text": 1,
            "animation_style": 1, "views": 1, "remix_count": 1, "slug": 1,
            "created_at": 1, "completed_at": 1,
        }
    ).sort("completed_at", -1).limit(limit).to_list(limit)

    # Follower count
    follower_count = await db.character_follows.count_documents({"character_id": character_id})

    return {
        "success": True,
        "character_name": char_name,
        "follower_count": follower_count,
        "stories": stories,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user), limit: int = 20):
    """Get user's notifications."""
    notifications = await db.notifications.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    unread = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"success": True, "notifications": notifications, "unread_count": unread}


@router.post("/notifications/read")
async def mark_notifications_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    await db.notifications.update_many(
        {"user_id": user["id"], "read": False},
        {"$set": {"read": True, "read_at": _now().isoformat()}}
    )
    return {"success": True}


async def create_notification(user_id: str, ntype: str, title: str, body: str, link: str = None, meta: dict = None):
    """Utility: Create a notification for a user."""
    await db.notifications.insert_one({
        "user_id": user_id,
        "type": ntype,
        "title": title,
        "body": body,
        "link": link,
        "meta": meta or {},
        "read": False,
        "created_at": _now().isoformat(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# RANKINGS — Top Stories, Characters, Creators
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/rankings")
async def get_rankings():
    """Public: Get top stories, characters, and creators."""

    # Top Stories (by views + continuations)
    top_stories = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "thumbnail_url": {"$exists": True, "$nin": [None, ""]}},
        {"_id": 0, "job_id": 1, "title": 1, "thumbnail_url": 1, "views": 1,
         "remix_count": 1, "slug": 1, "animation_style": 1}
    ).sort("views", -1).limit(10).to_list(10)

    # Top Characters (by story count)
    char_pipeline = [
        {"$match": {"status": "active"}},
        {"$project": {"_id": 0, "character_id": 1, "name": 1, "role": 1, "portrait_url": 1}},
    ]
    characters = await db.character_profiles.aggregate(char_pipeline).to_list(50)
    char_rankings = []
    for c in characters[:20]:
        story_count = await db.pipeline_jobs.count_documents({
            "status": "COMPLETED",
            "$or": [
                {"story_text": {"$regex": c.get("name", "NOMATCH"), "$options": "i"}},
                {"characters": c["character_id"]},
            ]
        })
        follower_count = await db.character_follows.count_documents({"character_id": c["character_id"]})
        if story_count > 0:
            char_rankings.append({
                **c,
                "story_count": story_count,
                "follower_count": follower_count,
                "score": story_count * 2 + follower_count * 5,
            })
    char_rankings.sort(key=lambda x: x["score"], reverse=True)

    # Top Creators (by total views + stories)
    creator_pipeline = [
        {"$match": {"status": "COMPLETED", "user_id": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$user_id",
            "total_stories": {"$sum": 1},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "total_remixes": {"$sum": {"$ifNull": ["$remix_count", 0]}},
        }},
        {"$sort": {"total_views": -1}},
        {"$limit": 10},
    ]
    creator_raw = await db.pipeline_jobs.aggregate(creator_pipeline).to_list(10)
    top_creators = []
    for cr in creator_raw:
        user = await db.users.find_one({"id": cr["_id"]}, {"_id": 0, "name": 1})
        if user:
            top_creators.append({
                "name": user.get("name", "Anonymous"),
                "total_stories": cr["total_stories"],
                "total_views": cr["total_views"],
                "total_remixes": cr["total_remixes"],
            })

    return {
        "success": True,
        "top_stories": top_stories,
        "top_characters": char_rankings[:10],
        "top_creators": top_creators,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EPISODE LOCK SYSTEM — Series progression
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/series/{series_id}/episodes")
async def get_series_episodes(series_id: str):
    """Public: Get series info + episodes with lock status."""
    series = await db.story_series.find_one(
        {"$or": [{"series_id": series_id}, {"id": series_id}]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episodes = await db.story_episodes.find(
        {"$or": [{"series_id": series_id}, {"series_id": series.get("id", series_id)}]},
        {"_id": 0, "episode_id": 1, "episode_number": 1, "title": 1,
         "cliffhanger_text": 1, "status": 1, "job_id": 1, "thumbnail_url": 1,
         "narration_preview": 1, "created_at": 1}
    ).sort("episode_number", 1).to_list(50)

    # Determine lock status: episodes after the last COMPLETED one are locked
    last_completed_num = 0
    for ep in episodes:
        if ep.get("status") in ["ready", "COMPLETED", "READY"]:
            last_completed_num = max(last_completed_num, ep.get("episode_number", 0))

    processed = []
    for ep in episodes:
        ep_num = ep.get("episode_number", 0)
        is_locked = ep_num > last_completed_num + 1
        is_current = ep_num == last_completed_num + 1
        processed.append({
            **ep,
            "locked": is_locked,
            "is_current": is_current,
            "is_completed": ep_num <= last_completed_num,
        })

    return {
        "success": True,
        "series": {
            "series_id": series.get("series_id"),
            "title": series.get("title"),
            "description": series.get("description"),
            "genre": series.get("genre"),
            "character_ids": series.get("character_ids", []),
            "total_episodes": len(episodes),
        },
        "episodes": processed,
        "next_episode_number": last_completed_num + 1,
    }


@router.post("/series/{series_id}/continue")
async def continue_series(series_id: str):
    """Get prefilled prompt for continuing a series (next episode)."""
    series = await db.story_series.find_one({"series_id": series_id}, {"_id": 0})
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episodes = await db.story_episodes.find(
        {"series_id": series_id, "status": {"$in": ["ready", "COMPLETED", "READY"]}},
        {"_id": 0, "episode_number": 1, "title": 1, "cliffhanger_text": 1, "narration_preview": 1}
    ).sort("episode_number", -1).limit(1).to_list(1)

    last_ep = episodes[0] if episodes else None
    next_num = (last_ep.get("episode_number", 0) + 1) if last_ep else 1

    cliffhanger = last_ep.get("cliffhanger_text", "") if last_ep else ""
    last_narration = last_ep.get("narration_preview", "") if last_ep else ""

    prompt = f'[Episode {next_num} of "{series.get("title", "Untitled")}"]\n\n'
    if cliffhanger:
        prompt += f'Previously: {cliffhanger}\n\n'
    elif last_narration:
        prompt += f'Previously: {last_narration[:300]}...\n\n'
    prompt += f'Direction: Create Episode {next_num} with higher stakes. Continue the story with tension and a new cliffhanger ending.'

    return {
        "success": True,
        "series_id": series_id,
        "series_title": series.get("title"),
        "next_episode_number": next_num,
        "prompt": prompt,
        "cliffhanger": cliffhanger,
        "character_ids": series.get("character_ids", []),
    }
