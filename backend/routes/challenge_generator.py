"""
Challenge Generator Module - Creator Challenge App
Creates day-by-day content challenges for creators
Route: /app/challenge-generator
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/challenge-generator", tags=["Challenge Generator"])

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================
CHALLENGE_PRICING = {
    "7_DAY": 6,
    "30_DAY": 15,
    "CAPTION_PACK": 3,
    "HASHTAG_BUNDLE": 2,
}

# =============================================================================
# TEMPLATE DATA (All Original - No AI Cost)
# =============================================================================

NICHE_TEMPLATES = {
    "luxury": {
        "themes": ["Lifestyle", "Travel", "Fashion", "Wellness", "Experiences"],
        "hooks": [
            "The secret to elevated living is...",
            "Why ordinary when you can have extraordinary?",
            "Unlock the lifestyle you deserve",
            "The difference between good and exceptional",
            "What luxury really means in [year]"
        ],
        "ctas": [
            "Save for your luxury inspiration board",
            "Tag someone who appreciates the finer things",
            "Follow for daily elegance",
            "Comment your dream destination",
            "Share with someone who needs this"
        ],
        "hashtags": {
            "generic": ["#luxurylifestyle", "#elegance", "#premium", "#exclusive", "#lifestyle"],
            "niche": ["#luxuryliving", "#highend", "#refinedtaste", "#luxurytravel", "#upscale"],
            "growth": ["#fyp", "#viral", "#trending", "#explorepage", "#reels"]
        }
    },
    "fitness": {
        "themes": ["Workout Tips", "Nutrition", "Motivation", "Progress", "Recovery"],
        "hooks": [
            "The workout that changed everything...",
            "Stop making this common mistake",
            "Your transformation starts today",
            "The truth about [topic] that trainers won't tell you",
            "Why you're not seeing results (and how to fix it)"
        ],
        "ctas": [
            "Save this workout for later",
            "Tag your gym buddy",
            "Drop a 💪 if you're ready to grow",
            "Comment 'READY' for the full plan",
            "Follow for daily fitness tips"
        ],
        "hashtags": {
            "generic": ["#fitness", "#workout", "#gym", "#health", "#fit"],
            "niche": ["#fitnessmotivation", "#gymlife", "#workoutmotivation", "#fitlife", "#healthylifestyle"],
            "growth": ["#fyp", "#viral", "#trending", "#fitfam", "#gains"]
        }
    },
    "kids_stories": {
        "themes": ["Storytelling", "Education", "Family Fun", "Bedtime", "Learning"],
        "hooks": [
            "The story that puts kids to sleep in minutes",
            "Watch their eyes light up with this tale",
            "A magical moment for your little ones",
            "The adventure begins...",
            "Once upon a time, something amazing happened"
        ],
        "ctas": [
            "Save for bedtime",
            "Tag a parent who needs this",
            "Follow for daily stories",
            "Share with your family",
            "Comment your child's favorite character"
        ],
        "hashtags": {
            "generic": ["#kidsstories", "#storytime", "#parenting", "#family", "#children"],
            "niche": ["#bedtimestories", "#kidsbooks", "#familytime", "#parentingtips", "#kidscontent"],
            "growth": ["#fyp", "#viral", "#momlife", "#dadlife", "#parenthood"]
        }
    },
    "motivation": {
        "themes": ["Mindset", "Success", "Growth", "Goals", "Daily Habits"],
        "hooks": [
            "The mindset shift that changes everything",
            "Why successful people do this every morning",
            "Stop waiting. Start now.",
            "The uncomfortable truth about success",
            "What nobody tells you about achieving your goals"
        ],
        "ctas": [
            "Save for your morning routine",
            "Tag someone who needs to hear this",
            "Follow for daily motivation",
            "Comment 'YES' if this resonates",
            "Share with someone who's working hard"
        ],
        "hashtags": {
            "generic": ["#motivation", "#mindset", "#success", "#goals", "#inspiration"],
            "niche": ["#growthmindset", "#successmindset", "#dailymotivation", "#personalgrowth", "#selfimprovement"],
            "growth": ["#fyp", "#viral", "#trending", "#motivational", "#inspired"]
        }
    },
    "business": {
        "themes": ["Entrepreneurship", "Marketing", "Sales", "Leadership", "Finance"],
        "hooks": [
            "The business strategy that 10x'd my revenue",
            "What I wish I knew before starting",
            "The mistake that almost cost me everything",
            "How to scale without burning out",
            "The secret sauce of successful businesses"
        ],
        "ctas": [
            "Save this for your business toolkit",
            "Tag a fellow entrepreneur",
            "Follow for business tips",
            "Comment 'GROWTH' for more strategies",
            "Share with your business partner"
        ],
        "hashtags": {
            "generic": ["#business", "#entrepreneur", "#startup", "#marketing", "#success"],
            "niche": ["#businesstips", "#entrepreneurlife", "#smallbusiness", "#businessowner", "#hustle"],
            "growth": ["#fyp", "#viral", "#trending", "#businessgrowth", "#money"]
        }
    }
}

PLATFORM_SPECS = {
    "instagram": {
        "optimal_times": ["7:00 AM", "12:00 PM", "7:00 PM"],
        "content_types": ["Reel", "Carousel", "Story", "Static Post"],
        "caption_length": "2200 chars max, 125-150 optimal",
        "hashtag_count": "20-30 recommended"
    },
    "youtube": {
        "optimal_times": ["2:00 PM", "4:00 PM", "9:00 PM"],
        "content_types": ["Short", "Long-form", "Premiere", "Community Post"],
        "caption_length": "5000 chars max",
        "hashtag_count": "3-5 in description"
    },
    "tiktok": {
        "optimal_times": ["7:00 AM", "12:00 PM", "3:00 PM", "7:00 PM"],
        "content_types": ["Video", "Duet", "Stitch", "Live"],
        "caption_length": "300 chars",
        "hashtag_count": "4-6 recommended"
    }
}

GOAL_STRATEGIES = {
    "followers": {
        "focus": "Engagement and shareability",
        "content_ratio": {"educational": 40, "entertaining": 40, "promotional": 20},
        "tip": "Focus on hooks that stop the scroll and end with clear follow CTAs"
    },
    "leads": {
        "focus": "Value delivery and conversion",
        "content_ratio": {"educational": 60, "entertaining": 20, "promotional": 20},
        "tip": "Offer valuable insights with lead magnets in bio"
    },
    "sales": {
        "focus": "Trust building and social proof",
        "content_ratio": {"educational": 30, "entertaining": 20, "promotional": 50},
        "tip": "Share testimonials, behind-the-scenes, and product demonstrations"
    },
    "engagement": {
        "focus": "Community building and interaction",
        "content_ratio": {"educational": 30, "entertaining": 50, "promotional": 20},
        "tip": "Ask questions, create polls, respond to every comment"
    }
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ChallengeRequest(BaseModel):
    challengeType: str = Field(default="7_day")  # 7_day, 30_day
    niche: str = Field(default="motivation")
    platform: str = Field(default="instagram")
    goal: str = Field(default="followers")  # followers, leads, sales, engagement
    timePerDay: int = Field(default=10, ge=5, le=60)  # minutes


class CaptionPackRequest(BaseModel):
    challengeId: str
    dayNumbers: List[int] = Field(default_factory=list, max_items=30)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_daily_content(
    day_num: int,
    niche: str,
    platform: str,
    goal: str,
    time_per_day: int
) -> dict:
    """Generate daily content plan (template-based, no AI)"""
    niche_data = NICHE_TEMPLATES.get(niche, NICHE_TEMPLATES["motivation"])
    platform_data = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["instagram"])
    goal_data = GOAL_STRATEGIES.get(goal, GOAL_STRATEGIES["followers"])
    
    # Cycle through themes
    theme_index = (day_num - 1) % len(niche_data["themes"])
    theme = niche_data["themes"][theme_index]
    
    # Select content type
    content_type = random.choice(platform_data["content_types"])
    
    # Generate hook
    hook = random.choice(niche_data["hooks"]).replace("[year]", "2026").replace("[topic]", theme.lower())
    
    # Generate CTA
    cta = random.choice(niche_data["ctas"])
    
    # Compile hashtags
    hashtags = (
        random.sample(niche_data["hashtags"]["generic"], 3) +
        random.sample(niche_data["hashtags"]["niche"], 3) +
        random.sample(niche_data["hashtags"]["growth"], 2)
    )
    
    # Optimal posting time
    posting_time = random.choice(platform_data["optimal_times"])
    
    # Content complexity based on time available
    if time_per_day <= 10:
        complexity = "Quick tip or quote"
    elif time_per_day <= 20:
        complexity = "Short-form content with graphics"
    else:
        complexity = "In-depth content with high production"
    
    return {
        "day": day_num,
        "theme": theme,
        "contentType": content_type,
        "hook": hook,
        "callToAction": cta,
        "hashtags": hashtags,
        "postingTime": posting_time,
        "complexity": complexity,
        "focusArea": goal_data["focus"],
        "tips": [
            goal_data["tip"],
            f"Use {platform_data['hashtag_count']} for this platform",
            f"Best caption length: {platform_data['caption_length']}"
        ]
    }


def generate_caption_template(day_content: dict, niche: str) -> str:
    """Generate caption template for a day"""
    templates = [
        f"{day_content['hook']}\n\n[Your main point here]\n\n{day_content['callToAction']}\n\n{' '.join(day_content['hashtags'])}",
        f"Day {day_content['day']} of my {niche} journey:\n\n{day_content['hook']}\n\n[Share your experience]\n\n{day_content['callToAction']}\n\n{' '.join(day_content['hashtags'])}",
        f"{day_content['hook']}\n\n3 things you need to know:\n1. [Point 1]\n2. [Point 2]\n3. [Point 3]\n\n{day_content['callToAction']}\n\n{' '.join(day_content['hashtags'])}"
    ]
    return random.choice(templates)


async def deduct_credits(user_id: str, amount: int, ref_type: str, ref_id: str):
    """Atomically deduct credits"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or user.get("credits", 0) < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {amount}")
    
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Failed to deduct credits")
    
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": amount,
        "refType": ref_type,
        "refId": ref_id,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_challenge_pricing():
    """Get pricing for challenge generator"""
    return {
        "pricing": CHALLENGE_PRICING,
        "challengeTypes": [
            {"type": "7_DAY", "name": "7-Day Challenge", "credits": CHALLENGE_PRICING["7_DAY"]},
            {"type": "30_DAY", "name": "30-Day Challenge", "credits": CHALLENGE_PRICING["30_DAY"]}
        ],
        "addOns": [
            {"type": "CAPTION_PACK", "name": "Caption Templates", "credits": CHALLENGE_PRICING["CAPTION_PACK"]},
            {"type": "HASHTAG_BUNDLE", "name": "Premium Hashtags", "credits": CHALLENGE_PRICING["HASHTAG_BUNDLE"]}
        ]
    }


@router.get("/niches")
async def get_available_niches():
    """Get available niches"""
    return {
        "niches": list(NICHE_TEMPLATES.keys()),
        "descriptions": {
            "luxury": "High-end lifestyle and premium content",
            "fitness": "Health, workout, and wellness content",
            "kids_stories": "Family and children-focused storytelling",
            "motivation": "Inspirational and self-improvement content",
            "business": "Entrepreneurship and business growth"
        }
    }


@router.get("/platforms")
async def get_platforms():
    """Get supported platforms and specs"""
    return {"platforms": PLATFORM_SPECS}


@router.get("/goals")
async def get_goals():
    """Get available goals and strategies"""
    return {"goals": GOAL_STRATEGIES}


@router.post("/generate")
@limiter.limit("5/minute")
async def generate_challenge(
    request: Request,
    data: ChallengeRequest,
    user: dict = Depends(get_current_user)
):
    """Generate content challenge"""
    user_id = user["id"]
    
    # Determine days and pricing
    if data.challengeType == "30_day":
        days = 30
        cost = CHALLENGE_PRICING["30_DAY"]
    else:
        days = 7
        cost = CHALLENGE_PRICING["7_DAY"]
    
    challenge_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, cost, "CHALLENGE", challenge_id)
    
    # Generate daily content
    daily_plans = []
    for day in range(1, days + 1):
        plan = generate_daily_content(
            day_num=day,
            niche=data.niche,
            platform=data.platform,
            goal=data.goal,
            time_per_day=data.timePerDay
        )
        daily_plans.append(plan)
    
    # Store challenge
    challenge_doc = {
        "id": challenge_id,
        "userId": user_id,
        "challengeType": data.challengeType,
        "niche": data.niche,
        "platform": data.platform,
        "goal": data.goal,
        "timePerDay": data.timePerDay,
        "days": days,
        "dailyPlans": daily_plans,
        "creditsUsed": cost,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "startDate": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    }
    
    await db.content_challenges.insert_one(challenge_doc)
    
    return {
        "success": True,
        "challengeId": challenge_id,
        "days": days,
        "creditsUsed": cost,
        "dailyPlans": daily_plans,
        "platformSpecs": PLATFORM_SPECS.get(data.platform, {}),
        "goalStrategy": GOAL_STRATEGIES.get(data.goal, {}),
        "disclaimer": "Generated content is template-based and should be reviewed before posting."
    }


@router.post("/caption-pack")
async def generate_caption_pack(
    data: CaptionPackRequest,
    user: dict = Depends(get_current_user)
):
    """Generate caption templates for challenge days"""
    user_id = user["id"]
    cost = CHALLENGE_PRICING["CAPTION_PACK"]
    
    # Get challenge
    challenge = await db.content_challenges.find_one(
        {"id": data.challengeId, "userId": user_id},
        {"_id": 0}
    )
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    pack_id = str(uuid.uuid4())
    await deduct_credits(user_id, cost, "CAPTION_PACK", pack_id)
    
    # Generate captions for requested days
    captions = {}
    daily_plans = challenge.get("dailyPlans", [])
    
    for day_num in (data.dayNumbers or range(1, len(daily_plans) + 1)):
        if 1 <= day_num <= len(daily_plans):
            day_content = daily_plans[day_num - 1]
            captions[day_num] = generate_caption_template(day_content, challenge["niche"])
    
    # Update challenge with captions
    await db.content_challenges.update_one(
        {"id": data.challengeId},
        {"$set": {"captionPack": captions, "captionPackGeneratedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "success": True,
        "challengeId": data.challengeId,
        "captions": captions,
        "creditsUsed": cost
    }


@router.get("/challenge/{challenge_id}")
async def get_challenge(challenge_id: str, user: dict = Depends(get_current_user)):
    """Get challenge details"""
    challenge = await db.content_challenges.find_one(
        {"id": challenge_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return challenge


@router.get("/history")
async def get_challenge_history(
    user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's challenge history"""
    user_id = user["id"]
    
    challenges = await db.content_challenges.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.content_challenges.count_documents({"userId": user_id})
    
    return {
        "challenges": challenges,
        "total": total
    }
