"""
Creator Tools Routes - Hashtag Bank, Thumbnails, Calendar, Carousel
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import json
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/creator-tools", tags=["Creator Tools"])

# Hashtag bank data
HASHTAG_BANK = {
    "fitness": ["#fitness", "#gym", "#workout", "#health", "#fitfam", "#training", "#bodybuilding", "#motivation", "#fitlife", "#exercise"],
    "business": ["#business", "#entrepreneur", "#success", "#motivation", "#marketing", "#startup", "#money", "#hustle", "#leadership", "#growth"],
    "travel": ["#travel", "#wanderlust", "#adventure", "#explore", "#vacation", "#travelphotography", "#instatravel", "#travelgram", "#nature", "#tourism"],
    "food": ["#food", "#foodie", "#foodporn", "#yummy", "#delicious", "#cooking", "#recipe", "#foodphotography", "#homemade", "#foodlover"],
    "fashion": ["#fashion", "#style", "#ootd", "#outfit", "#fashionblogger", "#streetstyle", "#fashionista", "#instafashion", "#trendy", "#lookoftheday"],
    "tech": ["#technology", "#tech", "#innovation", "#ai", "#coding", "#programming", "#software", "#digital", "#startup", "#developer"],
    "beauty": ["#beauty", "#makeup", "#skincare", "#cosmetics", "#beautyblogger", "#makeupartist", "#selfcare", "#glam", "#beautytips", "#skincareroutine"],
    "lifestyle": ["#lifestyle", "#life", "#happy", "#love", "#instagood", "#photooftheday", "#motivation", "#inspiration", "#daily", "#positivevibes"],
    "general": ["#viral", "#trending", "#fyp", "#explore", "#reels", "#instagram", "#content", "#creator", "#socialmedia", "#influencer"]
}

NICHES = list(HASHTAG_BANK.keys())


@router.get("/hashtags/{niche}")
async def get_hashtag_bank(niche: str, user: dict = Depends(get_current_user)):
    """Get hashtags for a specific niche"""
    niche_lower = niche.lower()
    hashtags = HASHTAG_BANK.get(niche_lower, HASHTAG_BANK["general"])
    
    return {
        "niche": niche,
        "hashtags": hashtags,
        "count": len(hashtags),
        "tip": "Mix 3-5 popular hashtags with 5-7 niche-specific ones for best reach"
    }


@router.get("/niches")
async def get_all_niches(user: dict = Depends(get_current_user)):
    """Get all available niches"""
    return {"niches": NICHES}


@router.post("/thumbnail-text")
async def generate_thumbnail_text(
    topic: str,
    style: str = "all",
    user: dict = Depends(get_current_user)
):
    """Generate thumbnail text ideas (1 credit)"""
    if user.get("credits", 0) < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    # Generate thumbnail text ideas
    ideas = {
        "clickbait": [
            f"You Won't Believe {topic}!",
            f"The {topic} Secret Nobody Tells You",
            f"I Tried {topic} and THIS Happened",
            f"Stop! Watch This Before {topic}",
            f"Why {topic} Changed Everything"
        ],
        "informative": [
            f"How to Master {topic}",
            f"{topic}: Complete Guide",
            f"Everything About {topic}",
            f"{topic} Tips & Tricks",
            f"Learn {topic} in 5 Minutes"
        ],
        "emotional": [
            f"The Truth About {topic}",
            f"Why I Love {topic}",
            f"{topic} Will Make You Cry",
            f"The {topic} Journey",
            f"How {topic} Changed My Life"
        ]
    }
    
    if style != "all" and style in ideas:
        result = {style: ideas[style]}
    else:
        result = ideas
    
    await deduct_credits(user["id"], 1, f"Thumbnail text: {topic[:30]}")
    
    return {
        "topic": topic,
        "ideas": result,
        "creditsUsed": 1
    }


@router.post("/content-calendar")
async def generate_content_calendar(
    niche: str,
    days: int = 30,
    include_full_scripts: bool = False,
    user: dict = Depends(get_current_user)
):
    """Generate a content calendar (5 credits)"""
    cost = 5
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Generate calendar
    calendar = []
    topics_pool = [
        "Behind the scenes", "Day in my life", "Tutorial", "Tips & tricks",
        "Q&A", "Challenge", "Story time", "Review", "Transformation",
        "Motivation", "How I started", "Mistakes to avoid", "Trending topic",
        "Collaboration idea", "User generated content"
    ]
    
    from datetime import date
    start_date = date.today()
    
    for i in range(min(days, 30)):
        current_date = start_date + timedelta(days=i)
        day_name = current_date.strftime("%A")
        
        # Vary content by day
        if day_name in ["Saturday", "Sunday"]:
            content_type = "Story/Behind the scenes"
        elif day_name == "Monday":
            content_type = "Motivation/Inspiration"
        elif day_name == "Wednesday":
            content_type = "Tutorial/Educational"
        else:
            content_type = topics_pool[i % len(topics_pool)]
        
        entry = {
            "date": current_date.isoformat(),
            "dayOfWeek": day_name,
            "contentType": content_type,
            "niche": niche,
            "suggestedTopic": f"{niche.title()} - {content_type}",
            "bestPostingTime": "6:00 PM - 9:00 PM" if day_name in ["Saturday", "Sunday"] else "12:00 PM - 1:00 PM"
        }
        
        if include_full_scripts:
            entry["scriptOutline"] = {
                "hook": f"Stop scrolling! Here's {content_type.lower()} you need...",
                "body": "Main content points here",
                "cta": "Follow for more!"
            }
        
        calendar.append(entry)
    
    await deduct_credits(user["id"], cost, f"Content calendar: {niche} ({days} days)")
    
    return {
        "niche": niche,
        "days": days,
        "calendar": calendar,
        "creditsUsed": cost
    }


@router.post("/carousel")
async def generate_carousel(
    topic: str,
    niche: str = "general",
    slides: int = 7,
    user: dict = Depends(get_current_user)
):
    """Generate carousel content (3 credits)"""
    cost = 3
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    slides = min(max(slides, 3), 10)  # 3-10 slides
    
    # Generate carousel
    carousel = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "niche": niche,
        "slides": []
    }
    
    # Cover slide
    carousel["slides"].append({
        "slideNumber": 1,
        "type": "cover",
        "headline": topic,
        "subheadline": f"Swipe to learn →",
        "designTip": "Use bold, contrasting colors"
    })
    
    # Content slides
    for i in range(2, slides):
        carousel["slides"].append({
            "slideNumber": i,
            "type": "content",
            "headline": f"Point {i-1}",
            "body": f"Key insight about {topic} - point {i-1}",
            "designTip": "Keep text minimal, use icons"
        })
    
    # CTA slide
    carousel["slides"].append({
        "slideNumber": slides,
        "type": "cta",
        "headline": "Want More?",
        "cta": "Follow + Save for later!",
        "designTip": "Include your handle/logo"
    })
    
    await deduct_credits(user["id"], cost, f"Carousel: {topic[:30]}")
    
    return {
        "success": True,
        "carousel": carousel,
        "creditsUsed": cost,
        "tips": [
            "First slide is key - make it scroll-stopping",
            "Keep each slide focused on ONE point",
            "Use consistent branding throughout",
            "End with a clear call-to-action"
        ]
    }
