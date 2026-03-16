"""
Public API — Distribution Loop Engine
Public pages, explore feed, platform stats, view tracking.
No authentication required for read endpoints.
"""
import logging
import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from shared import db, logger

router = APIRouter(prefix="/public", tags=["public"])
logger = logging.getLogger("public_api")


def slugify(text: str) -> str:
    """Create URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


# ─── PLATFORM STATS (Real Data) ──────────────────────────────────────────

@router.get("/stats")
async def get_platform_stats():
    """Return real platform statistics for social proof."""
    users_count = await db.users.count_documents({})
    jobs_completed = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})

    # Count total scenes across completed jobs
    pipeline = [
        {"$match": {"status": "COMPLETED"}},
        {"$project": {"scene_count": {"$size": {"$ifNull": ["$scenes", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$scene_count"}}}
    ]
    scene_result = await db.pipeline_jobs.aggregate(pipeline).to_list(length=1)
    total_scenes = scene_result[0]["total"] if scene_result else 0

    # Count total generations from all tools
    gen_count = await db.generations.count_documents({})

    # Total creations = pipeline jobs + other generations
    total_creations = jobs_completed + gen_count

    return {
        "creators": users_count,
        "videos_created": jobs_completed,
        "total_creations": total_creations,
        "ai_scenes": total_scenes,
    }


# ─── PUBLIC CREATION PAGE ─────────────────────────────────────────────────

@router.get("/creation/{slug}")
async def get_public_creation(slug: str):
    """
    Get a public creation page by slug or job_id.
    Increments view count. No auth required.
    """
    # Try to find by slug first, then by job_id
    job = await db.pipeline_jobs.find_one(
        {"$or": [{"slug": slug}, {"job_id": slug}]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Creation not found")

    # Increment view count
    await db.pipeline_jobs.update_one(
        {"job_id": job["job_id"]},
        {"$inc": {"views": 1}}
    )

    # Get creator info
    creator = None
    if job.get("user_id"):
        creator = await db.users.find_one(
            {"id": job["user_id"]},
            {"_id": 0, "name": 1, "email": 1}
        )

    # Presign URLs
    from utils.r2_presign import presign_url
    thumbnail = presign_url(job.get("thumbnail_url", "")) if job.get("thumbnail_url") else None

    scenes = []
    for s in job.get("scenes", []):
        scene_data = {
            "narration": s.get("narration", ""),
            "image_url": presign_url(s["image_url"]) if s.get("image_url") else None,
            "audio_url": presign_url(s["audio_url"]) if s.get("audio_url") else None,
            "duration": s.get("duration"),
        }
        scenes.append(scene_data)

    return {
        "success": True,
        "creation": {
            "job_id": job["job_id"],
            "slug": job.get("slug", slug),
            "title": job.get("title", "Untitled"),
            "status": job.get("status"),
            "animation_style": job.get("animation_style"),
            "age_group": job.get("age_group"),
            "scenes": scenes,
            "thumbnail_url": thumbnail,
            "views": job.get("views", 0) + 1,
            "remix_count": job.get("remix_count", 0),
            "created_at": job.get("created_at"),
            "creator": {
                "name": creator.get("name", "Anonymous") if creator else "Anonymous",
            },
            "story_text": job.get("story_text", ""),
        }
    }


# ─── EXPLORE FEED ─────────────────────────────────────────────────────────

@router.get("/explore")
async def get_explore_feed(
    tab: str = Query("trending", regex="^(trending|newest|most_remixed)$"),
    limit: int = Query(12, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """
    Get explore feed — trending, newest, or most remixed creations.
    No auth required.
    """
    base_filter = {"status": "COMPLETED"}

    sort_map = {
        "trending": [("views", -1), ("remix_count", -1)],
        "newest": [("created_at", -1)],
        "most_remixed": [("remix_count", -1), ("views", -1)],
    }

    projection = {
        "_id": 0,
        "job_id": 1,
        "slug": 1,
        "title": 1,
        "animation_style": 1,
        "views": 1,
        "remix_count": 1,
        "created_at": 1,
        "thumbnail_url": 1,
        "user_id": 1,
    }

    cursor = db.pipeline_jobs.find(base_filter, projection)
    for field, direction in sort_map[tab]:
        cursor = cursor.sort(field, direction)
    items = await cursor.skip(skip).limit(limit).to_list(length=limit)

    total = await db.pipeline_jobs.count_documents(base_filter)

    # Presign thumbnails and get creator names
    from utils.r2_presign import presign_url
    for item in items:
        if item.get("thumbnail_url"):
            item["thumbnail_url"] = presign_url(item["thumbnail_url"])
        item.setdefault("views", 0)
        item.setdefault("remix_count", 0)
        item.setdefault("slug", item.get("job_id", ""))

    return {
        "success": True,
        "tab": tab,
        "items": items,
        "total": total,
        "has_more": skip + limit < total,
    }
