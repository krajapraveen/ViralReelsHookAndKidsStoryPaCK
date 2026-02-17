"""
Convert Tools Routes - Content Conversion and Repurposing
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, Form
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import json
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits, FILE_EXPIRY_MINUTES,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/convert", tags=["Convert Tools"])

# Conversion costs
CONVERSION_COSTS = {
    "reel_to_carousel": 1,
    "story_to_reel": 1,
    "story_to_quote": 1,
    "text_to_story": 10,
    "text_to_reel": 15
}


@router.post("/reel-to-carousel/{generation_id}")
async def convert_reel_to_carousel(generation_id: str, user: dict = Depends(get_current_user)):
    """Convert a reel script to carousel format (1 credit)"""
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"], "type": "REEL"},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    cost = CONVERSION_COSTS["reel_to_carousel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    reel_data = generation.get("outputJson", {})
    script = reel_data.get("script", {})
    
    # Convert to carousel
    carousel = {
        "id": str(uuid.uuid4()),
        "sourceId": generation_id,
        "type": "carousel",
        "slides": [
            {"slideNumber": 1, "content": reel_data.get("best_hook", ""), "type": "cover"}
        ]
    }
    
    # Add scenes as slides
    for i, scene in enumerate(script.get("scenes", [])[:7], start=2):
        carousel["slides"].append({
            "slideNumber": i,
            "content": scene.get("on_screen_text", ""),
            "type": "content"
        })
    
    # CTA slide
    carousel["slides"].append({
        "slideNumber": len(carousel["slides"]) + 1,
        "content": script.get("cta", "Follow for more!"),
        "type": "cta"
    })
    
    await deduct_credits(user["id"], cost, "Reel to Carousel conversion")
    
    return {
        "success": True,
        "carousel": carousel,
        "creditsUsed": cost
    }


@router.post("/story-to-reel/{generation_id}")
async def convert_story_to_reel(generation_id: str, user: dict = Depends(get_current_user)):
    """Convert a story to reel format (1 credit)"""
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"], "type": "STORY"},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Story not found")
    
    cost = CONVERSION_COSTS["story_to_reel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    story_data = generation.get("outputJson", {})
    
    # Convert to reel format
    reel = {
        "id": str(uuid.uuid4()),
        "sourceId": generation_id,
        "type": "reel",
        "hooks": [
            f"You need to hear this story about {story_data.get('title', 'magic')}!",
            f"This story will change how you see {story_data.get('moral', 'life')}",
            f"Wait till you hear what happens in {story_data.get('title', 'this story')}!"
        ],
        "script": {
            "scenes": [
                {
                    "time": f"{i*5}-{(i+1)*5}s",
                    "text": scene.get("narration", "")[:100],
                    "visual": scene.get("visualDescription", "")
                }
                for i, scene in enumerate(story_data.get("scenes", [])[:6])
            ],
            "cta": f"Follow for more {story_data.get('genre', 'amazing')} stories!"
        },
        "caption": f"✨ {story_data.get('title', 'Story')} - A tale about {story_data.get('moral', 'adventure')}",
        "hashtags": ["#storytime", "#kidsstory", "#bedtimestory", "#storytelling", "#viral"]
    }
    
    await deduct_credits(user["id"], cost, "Story to Reel conversion")
    
    return {
        "success": True,
        "reel": reel,
        "creditsUsed": cost
    }


@router.post("/story-to-quote/{generation_id}")
async def convert_story_to_quote(generation_id: str, user: dict = Depends(get_current_user)):
    """Extract quotes from story (1 credit)"""
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"], "type": "STORY"},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Story not found")
    
    cost = CONVERSION_COSTS["story_to_quote"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    story_data = generation.get("outputJson", {})
    
    quotes = [
        f"'{story_data.get('moral', 'Every adventure begins with a single step.')}' - {story_data.get('title', 'Story')}",
        f"The greatest lessons come from the smallest moments.",
        f"In the world of {story_data.get('genre', 'adventure')}, anything is possible."
    ]
    
    await deduct_credits(user["id"], cost, "Story to Quote conversion")
    
    return {
        "success": True,
        "quotes": quotes,
        "creditsUsed": cost
    }


@router.post("/text-to-story")
async def convert_text_to_story(
    text: str = Form(...),
    genre: str = Form("Adventure"),
    age_group: str = Form("4-6"),
    user: dict = Depends(get_current_user)
):
    """Convert any text to a kids story (10 credits)"""
    cost = CONVERSION_COSTS["text_to_story"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text too short. Provide at least 10 characters.")
    
    # Create conversion job
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_story",
        "status": "processing",
        "input": {"text": text[:2000], "genre": genre, "ageGroup": age_group},
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    }
    await db.conversion_jobs.insert_one(job)
    
    # Generate story (simplified version - full would use LLM)
    story_output = {
        "title": f"The Story of {text[:30]}...",
        "synopsis": f"A {genre.lower()} story inspired by: {text[:100]}",
        "genre": genre,
        "ageGroup": age_group,
        "moral": "Every story has a lesson to teach",
        "scenes": [
            {
                "sceneNumber": 1,
                "sceneTitle": "The Beginning",
                "narration": f"Once upon a time, there was a story about {text[:50]}...",
                "visualDescription": "A colorful scene setting the stage"
            },
            {
                "sceneNumber": 2,
                "sceneTitle": "The Adventure",
                "narration": "The adventure was about to begin...",
                "visualDescription": "Exciting adventure scene"
            },
            {
                "sceneNumber": 3,
                "sceneTitle": "The End",
                "narration": "And they all learned an important lesson.",
                "visualDescription": "Happy ending scene"
            }
        ]
    }
    
    # Update job
    await db.conversion_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "completed", "output": story_output}}
    )
    
    await deduct_credits(user["id"], cost, "Text to Story conversion")
    
    return {
        "success": True,
        "jobId": job_id,
        "story": story_output,
        "creditsUsed": cost,
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes"
    }


@router.post("/text-to-reel")
async def convert_text_to_reel(
    text: str = Form(...),
    niche: str = Form("General"),
    tone: str = Form("Engaging"),
    user: dict = Depends(get_current_user)
):
    """Convert any text to a reel script (15 credits)"""
    cost = CONVERSION_COSTS["text_to_reel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text too short. Provide at least 10 characters.")
    
    # Create conversion job
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_reel",
        "status": "processing",
        "input": {"text": text[:2000], "niche": niche, "tone": tone},
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    }
    await db.conversion_jobs.insert_one(job)
    
    # Generate reel (simplified version)
    reel_output = {
        "hooks": [
            f"Stop! You need to know this about {text[:20]}...",
            f"This {niche.lower()} secret will change everything",
            f"3 things about {text[:20]} you didn't know"
        ],
        "best_hook": f"Stop! You need to know this about {text[:20]}...",
        "script": {
            "scenes": [
                {"time": "0-3s", "on_screen_text": "The Hook", "voiceover": f"Based on: {text[:50]}"},
                {"time": "3-15s", "on_screen_text": "Main Point", "voiceover": "Here's what you need to know..."},
                {"time": "15-30s", "on_screen_text": "Call to Action", "voiceover": "Follow for more!"}
            ],
            "cta": "Follow + Save for later!"
        },
        "caption_short": f"{niche} tip you need! 🔥",
        "caption_long": f"This {niche.lower()} insight based on: {text[:100]}...",
        "hashtags": [f"#{niche.lower().replace(' ', '')}", "#viral", "#trending", "#reels"],
        "posting_tips": ["Post between 6-9 PM", "Use trending audio"]
    }
    
    # Update job
    await db.conversion_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "completed", "output": reel_output}}
    )
    
    await deduct_credits(user["id"], cost, "Text to Reel conversion")
    
    return {
        "success": True,
        "jobId": job_id,
        "reel": reel_output,
        "creditsUsed": cost,
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes"
    }


@router.get("/status/{job_id}")
async def get_conversion_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get conversion job status"""
    job = await db.conversion_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history")
async def get_conversion_history(
    page: int = 0,
    size: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get conversion history"""
    skip = page * size
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    jobs = await db.conversion_jobs.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.conversion_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/costs")
async def get_conversion_costs():
    """Get conversion costs"""
    return {
        "costs": CONVERSION_COSTS,
        "description": {
            "reel_to_carousel": "Convert reel script to carousel slides",
            "story_to_reel": "Convert story to reel format",
            "story_to_quote": "Extract quotes from story",
            "text_to_story": "Transform any text into a kids story",
            "text_to_reel": "Transform any text into a reel script"
        }
    }
