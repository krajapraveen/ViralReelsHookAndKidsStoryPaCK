"""
Daily Viral Idea Drop
Free 1 idea/day, Paid 10 ideas for 5 credits, Pro unlimited
Template-based, no AI, <200ms response
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import time
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/daily-viral-ideas", tags=["Daily Viral Ideas"])

# ==================== DEFAULT IDEAS BY NICHE ====================
NICHES = [
    "Tech", "Finance", "Fitness", "Food", "Travel", "Fashion", 
    "Gaming", "Education", "Business", "Lifestyle", "Health", "Entertainment"
]

DEFAULT_IDEAS = {
    "Tech": [
        {"idea": "AI tools that replaced $10k/month software", "type": "list"},
        {"idea": "Hidden iPhone features that save hours", "type": "tutorial"},
        {"idea": "Why this app is blowing up right now", "type": "review"},
        {"idea": "Tech gadgets under $50 that feel premium", "type": "list"},
        {"idea": "The browser extension that changed my workflow", "type": "review"},
        {"idea": "Stop using ChatGPT wrong - here's how", "type": "tutorial"},
        {"idea": "Apps that pay you to do nothing", "type": "list"},
        {"idea": "The tech trend that's quietly taking over", "type": "analysis"},
        {"idea": "Productivity setup that saves 2 hours daily", "type": "tutorial"},
        {"idea": "Free alternatives to expensive software", "type": "list"},
    ],
    "Finance": [
        {"idea": "The money rule that changed my life at 25", "type": "story"},
        {"idea": "Side hustles that actually pay $1000+/month", "type": "list"},
        {"idea": "Why the rich stay rich (it's not what you think)", "type": "analysis"},
        {"idea": "Budget hacks that feel like you got a raise", "type": "tutorial"},
        {"idea": "The investment mistake I wish I knew earlier", "type": "story"},
        {"idea": "How to save $500 this month without trying", "type": "tutorial"},
        {"idea": "Credit score secrets banks don't tell you", "type": "educational"},
        {"idea": "The 3 accounts everyone needs for wealth", "type": "tutorial"},
        {"idea": "Making money while you sleep - real methods", "type": "list"},
        {"idea": "Financial red flags in your 20s/30s", "type": "list"},
    ],
    "Fitness": [
        {"idea": "The workout split that actually builds muscle", "type": "tutorial"},
        {"idea": "Why you're not losing belly fat (science)", "type": "educational"},
        {"idea": "10 minute routine that replaced my gym", "type": "tutorial"},
        {"idea": "Protein myths debunked by science", "type": "educational"},
        {"idea": "The exercise order that maximizes gains", "type": "tutorial"},
        {"idea": "Recovery hacks pro athletes use", "type": "list"},
        {"idea": "Why your posture is sabotaging your gains", "type": "educational"},
        {"idea": "Meal prep that actually tastes good", "type": "tutorial"},
        {"idea": "The supplement stack that actually works", "type": "list"},
        {"idea": "Home workout that beats the gym", "type": "tutorial"},
    ],
    "Food": [
        {"idea": "5 minute meals that taste expensive", "type": "tutorial"},
        {"idea": "Restaurant secrets I learned as a chef", "type": "list"},
        {"idea": "The ingredient that transforms any dish", "type": "tutorial"},
        {"idea": "Meal prep mistakes ruining your food", "type": "educational"},
        {"idea": "Budget groceries that feel gourmet", "type": "list"},
        {"idea": "Why your food doesn't taste like restaurants", "type": "educational"},
        {"idea": "One pot meals that feed a family", "type": "tutorial"},
        {"idea": "The seasoning combo chefs use daily", "type": "tutorial"},
        {"idea": "Air fryer recipes that changed my kitchen", "type": "list"},
        {"idea": "Desserts that look hard but aren't", "type": "tutorial"},
    ],
    "Travel": [
        {"idea": "How I travel for free (legit methods)", "type": "tutorial"},
        {"idea": "Hidden gems in [popular city] tourists miss", "type": "list"},
        {"idea": "Flight hacks that save hundreds", "type": "tutorial"},
        {"idea": "Packing mistakes I see every trip", "type": "educational"},
        {"idea": "The travel app that's a game changer", "type": "review"},
        {"idea": "Budget destinations that feel luxury", "type": "list"},
        {"idea": "Hotel booking secrets that save 50%", "type": "tutorial"},
        {"idea": "Solo travel tips I wish I knew sooner", "type": "list"},
        {"idea": "Why you should travel off-season", "type": "educational"},
        {"idea": "The carry-on only challenge (how I did it)", "type": "story"},
    ],
    "Fashion": [
        {"idea": "Outfits that look expensive but aren't", "type": "list"},
        {"idea": "Style rules that make anyone look put together", "type": "tutorial"},
        {"idea": "The capsule wardrobe that works for anyone", "type": "tutorial"},
        {"idea": "Fashion mistakes that age you 10 years", "type": "educational"},
        {"idea": "Thrifting secrets for designer finds", "type": "tutorial"},
        {"idea": "Colors that instantly elevate your look", "type": "educational"},
        {"idea": "The accessories that complete any outfit", "type": "list"},
        {"idea": "Why expensive doesn't mean better dressed", "type": "analysis"},
        {"idea": "Wardrobe staples everyone needs", "type": "list"},
        {"idea": "How to dress for your body type", "type": "tutorial"},
    ],
    "Gaming": [
        {"idea": "Games that are worth every penny", "type": "list"},
        {"idea": "Gaming setup upgrades under $100", "type": "list"},
        {"idea": "Pro tips for [popular game] ranked", "type": "tutorial"},
        {"idea": "Underrated games you're sleeping on", "type": "list"},
        {"idea": "The settings pros use (copy these)", "type": "tutorial"},
        {"idea": "Gaming habits that are holding you back", "type": "educational"},
        {"idea": "Free games that are actually good", "type": "list"},
        {"idea": "Controller vs keyboard - the real answer", "type": "analysis"},
        {"idea": "How to improve at any game fast", "type": "tutorial"},
        {"idea": "Gaming snacks that won't ruin your setup", "type": "list"},
    ],
    "Education": [
        {"idea": "Study techniques that actually work", "type": "tutorial"},
        {"idea": "Free courses better than paid ones", "type": "list"},
        {"idea": "Why cramming doesn't work (and what does)", "type": "educational"},
        {"idea": "Note-taking methods for better retention", "type": "tutorial"},
        {"idea": "Skills that pay off forever", "type": "list"},
        {"idea": "The learning hack that saved my grades", "type": "story"},
        {"idea": "Online certifications worth getting", "type": "list"},
        {"idea": "How to learn anything in 30 days", "type": "tutorial"},
        {"idea": "Books that changed how I think", "type": "list"},
        {"idea": "Productivity systems for students", "type": "tutorial"},
    ],
    "Business": [
        {"idea": "Business ideas that need zero investment", "type": "list"},
        {"idea": "How I made my first $1000 online", "type": "story"},
        {"idea": "Email templates that close deals", "type": "tutorial"},
        {"idea": "LinkedIn hacks that get you noticed", "type": "tutorial"},
        {"idea": "Pricing mistakes killing your business", "type": "educational"},
        {"idea": "The morning routine of successful founders", "type": "list"},
        {"idea": "Sales techniques that feel authentic", "type": "tutorial"},
        {"idea": "Why most businesses fail year one", "type": "analysis"},
        {"idea": "Tools that run my entire business", "type": "list"},
        {"idea": "Networking tips for introverts", "type": "tutorial"},
    ],
    "Lifestyle": [
        {"idea": "Morning routines that actually stick", "type": "tutorial"},
        {"idea": "Habits that changed my life in 6 months", "type": "list"},
        {"idea": "The minimalism hack that freed my mind", "type": "story"},
        {"idea": "Why successful people wake up early", "type": "educational"},
        {"idea": "Organization tips for messy people", "type": "tutorial"},
        {"idea": "How to have more energy daily", "type": "tutorial"},
        {"idea": "The evening routine for better sleep", "type": "tutorial"},
        {"idea": "Purchases under $20 that improved my life", "type": "list"},
        {"idea": "How to actually keep new habits", "type": "educational"},
        {"idea": "Mental health practices that cost nothing", "type": "list"},
    ],
    "Health": [
        {"idea": "Health myths doctors wish you'd forget", "type": "educational"},
        {"idea": "The sleep hack that changed everything", "type": "story"},
        {"idea": "Why you're always tired (and how to fix it)", "type": "educational"},
        {"idea": "Supplements that actually have science", "type": "list"},
        {"idea": "Stress relief techniques that work fast", "type": "tutorial"},
        {"idea": "The hydration mistake almost everyone makes", "type": "educational"},
        {"idea": "Daily habits for mental clarity", "type": "list"},
        {"idea": "How to boost immunity naturally", "type": "tutorial"},
        {"idea": "Signs your body is telling you something", "type": "educational"},
        {"idea": "The morning drink that helps everything", "type": "tutorial"},
    ],
    "Entertainment": [
        {"idea": "Shows you'll binge in one sitting", "type": "list"},
        {"idea": "Movies that deserve more recognition", "type": "list"},
        {"idea": "Why this show has a cult following", "type": "review"},
        {"idea": "Best free streaming services ranked", "type": "list"},
        {"idea": "Shows that start slow but are worth it", "type": "list"},
        {"idea": "The documentary that will change your view", "type": "review"},
        {"idea": "Perfect date night movies by mood", "type": "list"},
        {"idea": "Podcasts that make commutes fly by", "type": "list"},
        {"idea": "Books being adapted into shows soon", "type": "list"},
        {"idea": "Hidden gems on [streaming platform]", "type": "list"},
    ],
}

# ==================== MODELS ====================
class IdeaItem(BaseModel):
    idea: str
    type: str
    niche: str
    trending_score: int = 0

class GetIdeasResponse(BaseModel):
    success: bool
    ideas: List[IdeaItem]
    is_pro: bool
    credits_used: int
    remaining_free_today: int

class UnlockResponse(BaseModel):
    success: bool
    ideas: List[IdeaItem]
    credits_used: int

# ==================== HELPER FUNCTIONS ====================
async def get_user_free_claim_today(user_id: str) -> bool:
    """Check if user already claimed free idea today"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    claim = await db.daily_idea_claims.find_one({
        "user_id": user_id,
        "claimed_at": {"$gte": today},
        "type": "free"
    })
    return claim is not None

async def check_pro_subscription(user: dict) -> bool:
    """Check if user has Pro subscription"""
    subscription = await db.subscriptions.find_one({
        "user_id": str(user["id"]),
        "status": "active",
        "plan": {"$in": ["pro", "premium", "unlimited"]}
    })
    return subscription is not None

async def get_daily_ideas(niche: str = None, count: int = 10) -> List[dict]:
    """Get today's viral ideas from DB or defaults"""
    today = datetime.now(timezone.utc).date().isoformat()
    
    query = {"date": today, "active": {"$ne": False}}
    if niche:
        query["niche"] = niche
    
    ideas = await db.daily_viral_ideas.find(query).to_list(count)
    
    if not ideas:
        # Use defaults
        if niche and niche in DEFAULT_IDEAS:
            selected = random.sample(DEFAULT_IDEAS[niche], min(count, len(DEFAULT_IDEAS[niche])))
            ideas = [{"idea": i["idea"], "type": i["type"], "niche": niche, "trending_score": random.randint(70, 100)} for i in selected]
        else:
            # Mix from all niches
            all_ideas = []
            for n, idea_list in DEFAULT_IDEAS.items():
                for idea in idea_list:
                    all_ideas.append({**idea, "niche": n, "trending_score": random.randint(70, 100)})
            random.shuffle(all_ideas)
            ideas = all_ideas[:count]
    
    return ideas

# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    return {
        "niches": NICHES,
        "free_ideas_per_day": 1,
        "pack_cost": 5,
        "pack_size": 10,
        "pro_unlimited": True
    }

@router.get("/free")
async def get_free_idea(user: dict = Depends(get_current_user)):
    """Get single free idea for the day"""
    user_id = str(user["id"])
    
    # Check if Pro subscriber
    is_pro = await check_pro_subscription(user)
    if is_pro:
        # Pro users get all ideas
        ideas = await get_daily_ideas(count=10)
        return GetIdeasResponse(
            success=True,
            ideas=[IdeaItem(**i) for i in ideas],
            is_pro=True,
            credits_used=0,
            remaining_free_today=0
        )
    
    # Check if already claimed today
    already_claimed = await get_user_free_claim_today(user_id)
    if already_claimed:
        return GetIdeasResponse(
            success=True,
            ideas=[],
            is_pro=False,
            credits_used=0,
            remaining_free_today=0
        )
    
    # Get 1 free idea
    ideas = await get_daily_ideas(count=1)
    
    # Record claim
    await db.daily_idea_claims.insert_one({
        "user_id": user_id,
        "claimed_at": datetime.now(timezone.utc),
        "type": "free"
    })
    
    # Track analytics
    await db.template_analytics.insert_one({
        "feature": "daily_viral_ideas",
        "user_id": user_id,
        "type": "free",
        "created_at": datetime.now(timezone.utc)
    })
    
    return GetIdeasResponse(
        success=True,
        ideas=[IdeaItem(**i) for i in ideas],
        is_pro=False,
        credits_used=0,
        remaining_free_today=0
    )

@router.post("/unlock")
async def unlock_full_pack(user: dict = Depends(get_current_user)):
    """Unlock full pack of 10 ideas for 5 credits"""
    user_id = str(user["id"])
    
    # Check if Pro subscriber (free for them)
    is_pro = await check_pro_subscription(user)
    if is_pro:
        ideas = await get_daily_ideas(count=10)
        return UnlockResponse(
            success=True,
            ideas=[IdeaItem(**i) for i in ideas],
            credits_used=0
        )
    
    # Check credits
    if user.get("credits", 0) < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits. 5 credits required.")
    
    # Deduct credits BEFORE generation
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -5}}
    )
    
    try:
        ideas = await get_daily_ideas(count=10)
        
        # Record unlock
        await db.daily_idea_claims.insert_one({
            "user_id": user_id,
            "claimed_at": datetime.now(timezone.utc),
            "type": "paid_pack"
        })
        
        # Track analytics
        await db.template_analytics.insert_one({
            "feature": "daily_viral_ideas",
            "user_id": user_id,
            "type": "paid_pack",
            "created_at": datetime.now(timezone.utc)
        })
        
        return UnlockResponse(
            success=True,
            ideas=[IdeaItem(**i) for i in ideas],
            credits_used=5
        )
        
    except Exception as e:
        # Refund on error
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": 5}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to unlock: {str(e)}")

@router.get("/by-niche/{niche}")
async def get_ideas_by_niche(niche: str, user: dict = Depends(get_current_user)):
    """Get ideas for specific niche (Pro only or costs credits)"""
    if niche not in NICHES:
        raise HTTPException(status_code=400, detail=f"Invalid niche. Choose from: {', '.join(NICHES)}")
    
    is_pro = await check_pro_subscription(user)
    
    if not is_pro:
        # Requires paid unlock
        if user.get("credits", 0) < 5:
            raise HTTPException(status_code=402, detail="Unlock full pack required. 5 credits needed.")
    
    ideas = await get_daily_ideas(niche=niche, count=10)
    
    return {
        "success": True,
        "niche": niche,
        "ideas": [IdeaItem(**i) for i in ideas],
        "is_pro": is_pro
    }

# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/ideas")
async def get_all_ideas(admin: dict = Depends(get_admin_user)):
    """Get all daily ideas"""
    ideas = await db.daily_viral_ideas.find({}).sort("date", -1).to_list(500)
    for i in ideas:
        i["id"] = str(i.pop("_id"))
    return {"ideas": ideas}

@router.post("/admin/ideas")
async def create_idea(data: dict, admin: dict = Depends(get_admin_user)):
    """Create new daily idea"""
    idea = {
        "date": data.get("date", datetime.now(timezone.utc).date().isoformat()),
        "niche": data.get("niche", "Tech"),
        "idea": data.get("idea"),
        "type": data.get("type", "list"),
        "trending_score": data.get("trending_score", 80),
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "created_by": str(admin["_id"])
    }
    result = await db.daily_viral_ideas.insert_one(idea)
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/admin/ideas/{idea_id}")
async def delete_idea(idea_id: str, admin: dict = Depends(get_admin_user)):
    """Delete daily idea"""
    result = await db.daily_viral_ideas.delete_one({"_id": ObjectId(idea_id)})
    return {"success": result.deleted_count > 0}

@router.post("/admin/seed-today")
async def seed_today_ideas(admin: dict = Depends(get_admin_user)):
    """Seed today's ideas from defaults"""
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Check if today already seeded
    existing = await db.daily_viral_ideas.count_documents({"date": today})
    if existing > 0:
        return {"success": False, "message": "Today already seeded", "count": existing}
    
    # Seed from all niches
    count = 0
    for niche, ideas in DEFAULT_IDEAS.items():
        selected = random.sample(ideas, min(5, len(ideas)))
        for idea in selected:
            await db.daily_viral_ideas.insert_one({
                "date": today,
                "niche": niche,
                "idea": idea["idea"],
                "type": idea["type"],
                "trending_score": random.randint(70, 100),
                "active": True,
                "created_at": datetime.now(timezone.utc)
            })
            count += 1
    
    return {"success": True, "message": f"Seeded {count} ideas for today"}
