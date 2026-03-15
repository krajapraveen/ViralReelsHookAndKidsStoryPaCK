"""
Trending Topics CRUD API for Admin Dashboard.
Manages weekly trending content topics that creators can use for inspiration.
"""

import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from shared import db, get_current_user

logger = logging.getLogger("content_trending")

router = APIRouter(prefix="/content", tags=["Content Trending"])


class TrendingTopicCreate(BaseModel):
    title: str
    niche: str = "business"
    hook_preview: str = ""
    suggested_angle: str = ""
    is_active: bool = True


@router.get("/trending")
async def get_trending_topics(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get all trending topics. Admin sees all, regular users see active only."""
    query = {}
    if active_only:
        query["is_active"] = True

    topics = await db.trending_topics.find(
        query, {"_id": 0}
    ).sort("createdAt", -1).to_list(length=100)

    return {"topics": topics, "count": len(topics)}


@router.post("/trending")
async def create_trending_topic(
    data: TrendingTopicCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new trending topic. Admin only."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    topic = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "niche": data.niche,
        "hook_preview": data.hook_preview,
        "suggested_angle": data.suggested_angle,
        "is_active": data.is_active,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.get("id"),
    }

    await db.trending_topics.insert_one(topic)
    logger.info(f"Trending topic created: {data.title}")

    return {"success": True, "topic": {k: v for k, v in topic.items() if k != "_id"}}


@router.delete("/trending/{topic_id}")
async def delete_trending_topic(
    topic_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a trending topic. Admin only."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.trending_topics.delete_one({"id": topic_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")

    return {"success": True}


@router.put("/trending/{topic_id}")
async def update_trending_topic(
    topic_id: str,
    data: TrendingTopicCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update a trending topic. Admin only."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.trending_topics.update_one(
        {"id": topic_id},
        {"$set": {
            "title": data.title,
            "niche": data.niche,
            "hook_preview": data.hook_preview,
            "suggested_angle": data.suggested_angle,
            "is_active": data.is_active,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")

    return {"success": True}
