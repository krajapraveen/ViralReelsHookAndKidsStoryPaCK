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
    """Generate a content calendar (10 credits, 25 with scripts)"""
    cost = 25 if include_full_scripts else 10
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


# =============================================================================
# TRENDING TOPICS
# =============================================================================
@router.get("/trending")
async def get_trending_topics(
    niche: str = "general",
    limit: int = 8,
    user: dict = Depends(get_current_user)
):
    """Get weekly trending topics for content creation - FREE"""
    
    # Trending topics data by niche
    TRENDING_DATA = {
        "fitness": [
            {"topic": "Morning Workout Routines", "hook": "5 AM club secrets that actually work", "engagement": "High"},
            {"topic": "Protein Myths Debunked", "hook": "Stop believing these protein lies", "engagement": "Very High"},
            {"topic": "Home Gym Essentials", "hook": "Build a killer gym for under $500", "engagement": "High"},
            {"topic": "Recovery Days", "hook": "Why rest days make you stronger", "engagement": "Medium"},
            {"topic": "Meal Prep Hacks", "hook": "Prep a week of meals in 2 hours", "engagement": "Very High"},
            {"topic": "Cardio vs Weights", "hook": "The truth nobody tells you", "engagement": "High"},
            {"topic": "Sleep & Gains", "hook": "How sleep affects your muscles", "engagement": "Medium"},
            {"topic": "Beginner Mistakes", "hook": "Avoid these gym newbie errors", "engagement": "Very High"}
        ],
        "business": [
            {"topic": "AI Tools for Entrepreneurs", "hook": "10 AI tools that 10x productivity", "engagement": "Very High"},
            {"topic": "Side Hustle Ideas 2026", "hook": "Start earning $5K/month from home", "engagement": "Very High"},
            {"topic": "Personal Branding", "hook": "Build a brand that attracts clients", "engagement": "High"},
            {"topic": "Remote Team Management", "hook": "Lead teams across timezones", "engagement": "Medium"},
            {"topic": "Pricing Strategies", "hook": "Stop undercharging for your work", "engagement": "High"},
            {"topic": "Email Marketing Secrets", "hook": "Get 50% open rates consistently", "engagement": "High"},
            {"topic": "Content Repurposing", "hook": "1 piece of content → 10 posts", "engagement": "Very High"},
            {"topic": "Networking Tips", "hook": "Connect with anyone on LinkedIn", "engagement": "Medium"}
        ],
        "travel": [
            {"topic": "Budget Travel Hacks", "hook": "Travel Europe for $50/day", "engagement": "Very High"},
            {"topic": "Hidden Gems 2026", "hook": "Places tourists haven't discovered", "engagement": "High"},
            {"topic": "Solo Travel Safety", "hook": "Stay safe while exploring alone", "engagement": "High"},
            {"topic": "Travel Photography", "hook": "Phone photos that look professional", "engagement": "Medium"},
            {"topic": "Packing Light", "hook": "2 weeks in a carry-on bag", "engagement": "High"},
            {"topic": "Flight Deals", "hook": "Find $200 international flights", "engagement": "Very High"},
            {"topic": "Digital Nomad Life", "hook": "Work from anywhere guide", "engagement": "High"},
            {"topic": "Local Experiences", "hook": "Skip tourist traps, live like locals", "engagement": "Medium"}
        ],
        "food": [
            {"topic": "5-Minute Meals", "hook": "Healthy dinners faster than delivery", "engagement": "Very High"},
            {"topic": "Meal Prep Sunday", "hook": "Prep your entire week in 2 hours", "engagement": "High"},
            {"topic": "Air Fryer Recipes", "hook": "Crispy everything without the oil", "engagement": "Very High"},
            {"topic": "Budget Cooking", "hook": "Feed a family for $50/week", "engagement": "High"},
            {"topic": "Viral TikTok Recipes", "hook": "Recipes that actually work", "engagement": "High"},
            {"topic": "Healthy Snacks", "hook": "Guilt-free snacks you'll love", "engagement": "Medium"},
            {"topic": "One-Pot Wonders", "hook": "Less dishes, more flavor", "engagement": "High"},
            {"topic": "Food Photography", "hook": "Make your food look Instagram-worthy", "engagement": "Medium"}
        ],
        "tech": [
            {"topic": "AI Tools Revolution", "hook": "Tools that are replacing jobs", "engagement": "Very High"},
            {"topic": "Coding in 2026", "hook": "Languages worth learning now", "engagement": "High"},
            {"topic": "Cybersecurity Basics", "hook": "Protect yourself online", "engagement": "High"},
            {"topic": "No-Code Apps", "hook": "Build apps without coding", "engagement": "Very High"},
            {"topic": "Tech Career Tips", "hook": "Land your dream tech job", "engagement": "High"},
            {"topic": "Productivity Apps", "hook": "Apps that save 10 hours/week", "engagement": "High"},
            {"topic": "Web3 Explained", "hook": "Blockchain made simple", "engagement": "Medium"},
            {"topic": "Automation Hacks", "hook": "Automate your boring tasks", "engagement": "Very High"}
        ],
        "general": [
            {"topic": "Productivity Hacks", "hook": "Do more in less time", "engagement": "Very High"},
            {"topic": "Morning Routines", "hook": "How successful people start their day", "engagement": "High"},
            {"topic": "Money Saving Tips", "hook": "Save $500/month with these tricks", "engagement": "Very High"},
            {"topic": "Self Improvement", "hook": "Small changes, big results", "engagement": "High"},
            {"topic": "Mental Health", "hook": "Daily habits for better mental health", "engagement": "High"},
            {"topic": "Life Hacks", "hook": "Simple tricks that change everything", "engagement": "Very High"},
            {"topic": "Goal Setting", "hook": "Actually achieve your goals this year", "engagement": "Medium"},
            {"topic": "Time Management", "hook": "Master your calendar", "engagement": "High"}
        ]
    }
    
    # Get topics for the requested niche (default to general if not found)
    topics = TRENDING_DATA.get(niche.lower(), TRENDING_DATA["general"])[:limit]
    
    return {
        "success": True,
        "niche": niche,
        "weekOf": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topics": topics,
        "tips": [
            "Jump on trending topics within 24-48 hours for maximum reach",
            "Add your unique perspective to stand out",
            "Use the hook as your opening line",
            "High engagement topics = more algorithm boost"
        ]
    }
