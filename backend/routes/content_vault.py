"""
Content Vault Routes - Saved Content, Trending Topics
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_current_user, get_admin_user
from models.schemas import TrendingTopicCreate

router = APIRouter(prefix="/content", tags=["Content Vault"])


@router.get("/vault")
async def get_content_vault(niche: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get user's saved content vault"""
    query = {"userId": user["id"]}
    if niche:
        query["niche"] = niche
    
    # Get saved generations
    generations = await db.generations.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).limit(100).to_list(length=100)
    
    # Get saved prompts
    saved_prompts = await db.saved_prompts.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(length=100)
    
    # Get saved hooks
    saved_hooks = await db.saved_hooks.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(length=100)
    
    # Stats
    stats = {
        "totalGenerations": len(generations),
        "reels": len([g for g in generations if g.get("type") == "REEL"]),
        "stories": len([g for g in generations if g.get("type") == "STORY"]),
        "savedPrompts": len(saved_prompts),
        "savedHooks": len(saved_hooks)
    }
    
    return {
        "generations": generations,
        "savedPrompts": saved_prompts,
        "savedHooks": saved_hooks,
        "stats": stats
    }


@router.post("/save-prompt")
async def save_prompt(prompt: str, category: str = "general", user: dict = Depends(get_current_user)):
    """Save a prompt to vault"""
    saved = {
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "prompt": prompt,
        "category": category,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.saved_prompts.insert_one(saved)
    return {"success": True, "id": saved["id"]}


@router.post("/save-hook")
async def save_hook(hook: str, niche: str = "general", user: dict = Depends(get_current_user)):
    """Save a hook to vault"""
    saved = {
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "hook": hook,
        "niche": niche,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.saved_hooks.insert_one(saved)
    return {"success": True, "id": saved["id"]}


@router.get("/trending")
async def get_trending_topics(
    active_only: bool = True,
    niche: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get trending topics"""
    query = {}
    if active_only:
        query["active"] = True
    if niche:
        query["niche"] = niche
    
    topics = await db.trending_topics.find(
        query,
        {"_id": 0}
    ).sort("engagement_score", -1).limit(50).to_list(length=50)
    
    return {"topics": topics, "count": len(topics)}


@router.post("/trending")
async def create_trending_topic(data: TrendingTopicCreate, user: dict = Depends(get_admin_user)):
    """Create a trending topic (admin only)"""
    topic = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "niche": data.niche,
        "hashtags": data.hashtags,
        "engagement_score": data.engagement_score,
        "active": True,
        "createdBy": user["id"],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.trending_topics.insert_one(topic)
    return {"success": True, "topicId": topic["id"]}


@router.delete("/trending/{topic_id}")
async def delete_trending_topic(topic_id: str, user: dict = Depends(get_admin_user)):
    """Delete a trending topic (admin only)"""
    result = await db.trending_topics.delete_one({"id": topic_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"success": True, "message": "Topic deleted"}


@router.delete("/vault/{item_id}")
async def delete_vault_item(item_id: str, item_type: str, user: dict = Depends(get_current_user)):
    """Delete an item from vault"""
    collection_map = {
        "prompt": db.saved_prompts,
        "hook": db.saved_hooks,
        "generation": db.generations
    }
    
    collection = collection_map.get(item_type)
    if not collection:
        raise HTTPException(status_code=400, detail="Invalid item type")
    
    result = await collection.delete_one({"id": item_id, "userId": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"success": True, "message": "Item deleted"}
