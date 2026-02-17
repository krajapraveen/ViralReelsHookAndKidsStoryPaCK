"""
Convert Feature Backend
Converts content between different formats (Story to Reel, Reel to Story, etc.)
"""
import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from shared import (
    db, get_current_user, deduct_credits, 
    EMERGENT_LLM_KEY, FILE_EXPIRY_MINUTES, LLM_AVAILABLE
)

logger = logging.getLogger(__name__)

# Router
convert_router = APIRouter(prefix="/convert", tags=["Convert"])

# Conversion costs
CONVERSION_COSTS = {
    "story_to_reel": 15,
    "reel_to_story": 10,
    "story_to_pdf": 5,
    "reel_to_carousel": 8,
    "story_to_thread": 5,
    "reel_to_shorts": 10,
    "text_to_story": 10,
    "text_to_reel": 15
}

# =============================================================================
# MODELS
# =============================================================================
class StoryToReelRequest(BaseModel):
    story_id: str
    reel_style: str = Field(default="engaging", description="Style: engaging, dramatic, educational, fun")
    include_visuals: bool = True
    target_duration: int = Field(default=30, ge=15, le=90)

class ReelToStoryRequest(BaseModel):
    reel_id: str
    story_style: str = Field(default="narrative", description="Style: narrative, educational, adventure")
    target_age_group: str = Field(default="kids", description="kids, teens, adults")

class TextToStoryRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    story_style: str = Field(default="adventure")
    target_age_group: str = Field(default="kids")
    include_moral: bool = True

class TextToReelRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000)
    reel_style: str = Field(default="engaging")
    platform: str = Field(default="instagram", description="instagram, tiktok, youtube")

class ConversionStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None

# =============================================================================
# CONVERSION ENDPOINTS
# =============================================================================
@convert_router.post("/story-to-reel")
async def convert_story_to_reel(
    data: StoryToReelRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Convert a kids story into a viral reel script - 15 credits"""
    cost = CONVERSION_COSTS["story_to_reel"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits for this conversion")
    
    # Get the story
    story = await db.generated_stories.find_one({"id": data.story_id, "userId": user["id"]}, {"_id": 0})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    job_id = str(uuid.uuid4())
    
    # Create job
    await db.conversion_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "story_to_reel",
        "sourceId": data.story_id,
        "sourceType": "story",
        "status": "processing",
        "progress": 0,
        "options": data.model_dump(),
        "result": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Deduct credits
    remaining = await deduct_credits(user["id"], cost, "Convert: Story to Reel")
    
    # Start background conversion
    async def run_conversion():
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 20}})
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"convert-{job_id}",
                system_message="You are an expert social media content creator who converts stories into viral reel scripts."
            ).with_model("gemini", "gemini-2.0-flash")
            
            story_content = story.get("content", story.get("story", ""))
            
            prompt = f"""Convert this kids story into a {data.target_duration}-second viral reel script.

STORY:
{story_content}

STYLE: {data.reel_style}

Create a reel script with:
1. Hook (first 3 seconds) - attention grabbing opener
2. Main content - key story points adapted for short-form video
3. Call to action
4. Suggested visuals/transitions
5. Background music suggestion
6. Hashtags (5-10 relevant ones)

Format as JSON with fields: hook, scenes (array with text, visual, duration), cta, music_suggestion, hashtags"""

            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 50}})
            
            result = await chat.send_message(UserMessage(text=prompt))
            
            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 80}})
            
            # Parse and store result
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "progress": 100,
                    "result": {"script": result, "source_story": data.story_id},
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            logger.info(f"Story-to-reel conversion {job_id} completed")
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            # Refund credits
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
    
    asyncio.create_task(run_conversion())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "pollUrl": f"/api/convert/status/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": remaining,
        "message": "Converting story to reel script..."
    }

@convert_router.post("/reel-to-story")
async def convert_reel_to_story(
    data: ReelToStoryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Convert a reel script into a full kids story - 10 credits"""
    cost = CONVERSION_COSTS["reel_to_story"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits for this conversion")
    
    # Get the reel
    reel = await db.generated_reels.find_one({"id": data.reel_id, "userId": user["id"]}, {"_id": 0})
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    job_id = str(uuid.uuid4())
    
    await db.conversion_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "reel_to_story",
        "sourceId": data.reel_id,
        "sourceType": "reel",
        "status": "processing",
        "progress": 0,
        "options": data.model_dump(),
        "result": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    remaining = await deduct_credits(user["id"], cost, "Convert: Reel to Story")
    
    async def run_conversion():
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 20}})
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"convert-{job_id}",
                system_message=f"You are a children's story writer creating {data.story_style} stories for {data.target_age_group}."
            ).with_model("gemini", "gemini-2.0-flash")
            
            reel_content = reel.get("script", reel.get("content", ""))
            
            prompt = f"""Expand this reel script into a full children's story.

REEL SCRIPT:
{reel_content}

TARGET: {data.target_age_group}
STYLE: {data.story_style}

Create a complete story with:
1. Title
2. Introduction (setting the scene)
3. Main story (with dialogue and descriptions)
4. Conclusion with moral lesson
5. Age-appropriate vocabulary
6. Suggested illustrations (3-5 scene descriptions)

Format as JSON with fields: title, introduction, story_parts (array), conclusion, moral, illustration_prompts (array)"""

            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 50}})
            
            result = await chat.send_message(UserMessage(text=prompt))
            
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "progress": 100,
                    "result": {"story": result, "source_reel": data.reel_id},
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
    
    asyncio.create_task(run_conversion())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "pollUrl": f"/api/convert/status/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": remaining
    }

@convert_router.post("/text-to-story")
async def convert_text_to_story(
    data: TextToStoryRequest,
    user: dict = Depends(get_current_user)
):
    """Convert any text into a kids story - 10 credits"""
    cost = CONVERSION_COSTS["text_to_story"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits")
    
    job_id = str(uuid.uuid4())
    
    await db.conversion_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_story",
        "sourceType": "text",
        "status": "processing",
        "progress": 0,
        "options": data.model_dump(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    remaining = await deduct_credits(user["id"], cost, "Convert: Text to Story")
    
    async def run_conversion():
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 30}})
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"convert-{job_id}",
                system_message=f"You are a creative children's story writer specializing in {data.story_style} stories."
            ).with_model("gemini", "gemini-2.0-flash")
            
            prompt = f"""Transform this text into an engaging children's story.

TEXT:
{data.text}

STYLE: {data.story_style}
AGE GROUP: {data.target_age_group}
INCLUDE MORAL: {data.include_moral}

Create a complete story with title, chapters/sections, dialogue, descriptions, and {"a meaningful moral lesson" if data.include_moral else "an engaging conclusion"}.

Format as a complete, readable story."""

            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 60}})
            
            result = await chat.send_message(UserMessage(text=prompt))
            
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "progress": 100,
                    "result": {"story": result},
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
    
    asyncio.create_task(run_conversion())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "pollUrl": f"/api/convert/status/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": remaining
    }

@convert_router.post("/text-to-reel")
async def convert_text_to_reel(
    data: TextToReelRequest,
    user: dict = Depends(get_current_user)
):
    """Convert any text into a reel script - 15 credits"""
    cost = CONVERSION_COSTS["text_to_reel"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits")
    
    job_id = str(uuid.uuid4())
    
    await db.conversion_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_reel",
        "sourceType": "text",
        "status": "processing",
        "progress": 0,
        "options": data.model_dump(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    remaining = await deduct_credits(user["id"], cost, "Convert: Text to Reel")
    
    async def run_conversion():
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 30}})
            
            platform_specs = {
                "instagram": "9:16 vertical, 30-60 seconds, trending audio friendly",
                "tiktok": "9:16 vertical, 15-60 seconds, fast-paced, trend-focused",
                "youtube": "9:16 shorts format, up to 60 seconds, YouTube SEO optimized"
            }
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"convert-{job_id}",
                system_message=f"You are a viral content creator specializing in {data.platform} reels."
            ).with_model("gemini", "gemini-2.0-flash")
            
            prompt = f"""Transform this text into a viral reel script for {data.platform}.

TEXT:
{data.text}

PLATFORM: {data.platform} ({platform_specs.get(data.platform, '')})
STYLE: {data.reel_style}

Create a complete reel script with:
1. HOOK (first 3 seconds - must be attention-grabbing)
2. CONTENT (main message in short, punchy segments)
3. CTA (call to action)
4. VISUAL DIRECTIONS (what to show on screen)
5. AUDIO SUGGESTIONS (music/sound effects)
6. HASHTAGS (10 relevant hashtags for {data.platform})
7. CAPTION (engaging caption for the post)

Format as JSON."""

            await db.conversion_jobs.update_one({"id": job_id}, {"$set": {"progress": 60}})
            
            result = await chat.send_message(UserMessage(text=prompt))
            
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "completed",
                    "progress": 100,
                    "result": {"script": result, "platform": data.platform},
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await db.conversion_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            await db.users.update_one({"id": user["id"]}, {"$inc": {"credits": cost}})
    
    asyncio.create_task(run_conversion())
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "pollUrl": f"/api/convert/status/{job_id}",
        "creditsUsed": cost,
        "remainingCredits": remaining
    }

# =============================================================================
# STATUS & HISTORY
# =============================================================================
@convert_router.get("/status/{job_id}")
async def get_conversion_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get conversion job status"""
    job = await db.conversion_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Conversion job not found")
    
    return job

@convert_router.get("/history")
async def get_conversion_history(
    page: int = 1,
    limit: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get conversion history"""
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    skip = (page - 1) * limit
    
    jobs = await db.conversion_jobs.find(
        query,
        {"_id": 0, "result": 0}  # Exclude large result field
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.conversion_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit
    }

@convert_router.get("/costs")
async def get_conversion_costs():
    """Get conversion costs"""
    return {
        "costs": CONVERSION_COSTS,
        "descriptions": {
            "story_to_reel": "Convert a kids story into a viral reel script",
            "reel_to_story": "Expand a reel script into a full story",
            "story_to_pdf": "Generate a printable PDF storybook",
            "reel_to_carousel": "Convert reel into Instagram carousel",
            "story_to_thread": "Convert story into Twitter/X thread",
            "reel_to_shorts": "Optimize reel for YouTube Shorts",
            "text_to_story": "Transform any text into a kids story",
            "text_to_reel": "Transform any text into a reel script"
        }
    }

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = ['convert_router']
