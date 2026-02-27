"""
Content Challenge Planner - Rebuilt from Challenge Generator
"Get a ready-to-post content plan in seconds."

4-Step Guided Wizard:
- Step 1: Choose Platform (Instagram, YouTube, LinkedIn, Kids Channel, Business)
- Step 2: Choose Duration (7, 14, 30 days)
- Step 3: Choose Goal (Followers, Sales, Engagement, Brand Growth)
- Step 4: Generate Plan

Zero AI Cost - Uses templates
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/content-challenge-planner", tags=["Content Challenge Planner"])

# =============================================================================
# COPYRIGHT PROTECTION - BLOCKED KEYWORDS
# =============================================================================
BLOCKED_KEYWORDS = [
    "mickey", "disney", "marvel", "avengers", "pokemon", "pikachu", "naruto",
    "goku", "harry potter", "batman", "superman", "spiderman", "spider-man",
    "taylor swift", "beyonce", "drake", "elon musk", "trump", "biden",
    "nike", "adidas", "apple", "google", "amazon", "coca cola"
]

def check_copyright_violation(text: str) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return keyword
    return None

# =============================================================================
# PRICING - SIMPLIFIED
# =============================================================================
PRICING = {
    "7_days": 10,
    "14_days": 18,
    "30_days": 30,
    "download_pdf": 5
}

# =============================================================================
# PLATFORMS
# =============================================================================
PLATFORMS = {
    "instagram": {
        "name": "Instagram",
        "icon": "instagram",
        "optimal_times": ["7:00 AM", "12:00 PM", "7:00 PM"],
        "content_types": ["Reel", "Carousel", "Story", "Post"]
    },
    "youtube": {
        "name": "YouTube",
        "icon": "youtube",
        "optimal_times": ["2:00 PM", "4:00 PM", "9:00 PM"],
        "content_types": ["Short", "Long-form", "Community Post"]
    },
    "linkedin": {
        "name": "LinkedIn",
        "icon": "linkedin",
        "optimal_times": ["8:00 AM", "12:00 PM", "5:00 PM"],
        "content_types": ["Text Post", "Article", "Carousel", "Video"]
    },
    "kids_channel": {
        "name": "Kids Channel",
        "icon": "baby",
        "optimal_times": ["9:00 AM", "3:00 PM", "7:00 PM"],
        "content_types": ["Story Video", "Educational", "Song", "Activity"]
    },
    "business": {
        "name": "Business",
        "icon": "briefcase",
        "optimal_times": ["9:00 AM", "1:00 PM", "6:00 PM"],
        "content_types": ["Case Study", "Tips", "Behind the Scenes", "Testimonial"]
    }
}

# =============================================================================
# GOALS
# =============================================================================
GOALS = {
    "followers": {
        "name": "Followers",
        "icon": "users",
        "focus": "Growth and engagement"
    },
    "sales": {
        "name": "Sales",
        "icon": "dollar-sign",
        "focus": "Conversion and trust"
    },
    "engagement": {
        "name": "Engagement",
        "icon": "message-circle",
        "focus": "Community and interaction"
    },
    "brand_growth": {
        "name": "Brand Growth",
        "icon": "trending-up",
        "focus": "Awareness and positioning"
    }
}

# =============================================================================
# CONTENT TEMPLATES BY PLATFORM AND GOAL
# =============================================================================
HOOKS_BY_GOAL = {
    "followers": [
        "Stop scrolling! This will change your perspective...",
        "If you're not doing this, you're missing out...",
        "The secret nobody tells you about...",
        "Watch this before it's too late...",
        "This is why you're stuck..."
    ],
    "sales": [
        "Here's how we helped [niche] get results...",
        "The exact strategy that generated...",
        "Why our customers keep coming back...",
        "Don't make this expensive mistake...",
        "The investment that pays for itself..."
    ],
    "engagement": [
        "Quick question for you all...",
        "Tell me if you relate to this...",
        "What's your take on this?",
        "Am I the only one who thinks...",
        "Rate this on a scale of 1-10..."
    ],
    "brand_growth": [
        "Here's what makes us different...",
        "The story behind our brand...",
        "Why we do what we do...",
        "Our mission is simple...",
        "This is our promise to you..."
    ]
}

CONTENT_IDEAS_BY_PLATFORM = {
    "instagram": [
        "Day in the life", "Quick tips carousel", "Before and after",
        "Tutorial reel", "Trending audio content", "Q&A story",
        "Behind the scenes", "Product showcase", "User testimonial",
        "Educational infographic", "Motivational quote", "Poll story"
    ],
    "youtube": [
        "How-to tutorial", "Top 5 list", "Challenge video",
        "Q&A session", "Product review", "Day in the life vlog",
        "Explainer short", "Trending topic reaction", "Tips compilation",
        "Success story", "Mistakes to avoid", "Quick hack"
    ],
    "linkedin": [
        "Industry insight", "Career lesson", "Leadership tip",
        "Success story", "Failure lesson", "Behind the scenes",
        "Hot take", "Resource share", "Team spotlight",
        "Industry news reaction", "Poll question", "Case study"
    ],
    "kids_channel": [
        "Educational story", "Fun learning activity", "Counting song",
        "Color learning", "Animal adventure", "Bedtime story",
        "Dance along", "Puzzle time", "Nature exploration",
        "Friendship lesson", "Healthy habits", "Creative craft"
    ],
    "business": [
        "Client success story", "Product feature spotlight", "Industry tips",
        "Team introduction", "Process explanation", "FAQ answer",
        "Myth busting", "Trend analysis", "How we help", 
        "Customer testimonial", "Behind the scenes", "Problem solving"
    ]
}

CAPTIONS_BY_GOAL = {
    "followers": [
        "If this helped you, follow for more daily tips!",
        "Save this for later and follow for more!",
        "Don't miss our next post - hit follow!"
    ],
    "sales": [
        "Ready to get started? Link in bio.",
        "DM us 'INFO' to learn more.",
        "Limited spots available - act now!"
    ],
    "engagement": [
        "Drop a [emoji] if you agree!",
        "Comment your thoughts below!",
        "Tag someone who needs to see this!"
    ],
    "brand_growth": [
        "Share this with someone who'd benefit!",
        "Follow our journey - more updates coming!",
        "What other topics should we cover?"
    ]
}

CTAS_BY_GOAL = {
    "followers": "Follow for daily value!",
    "sales": "Link in bio to get started",
    "engagement": "Comment below!",
    "brand_growth": "Share with your network"
}

HASHTAGS_BY_PLATFORM = {
    "instagram": ["#reels", "#instagood", "#trending", "#fyp", "#viral"],
    "youtube": ["#shorts", "#youtube", "#subscribe", "#viral", "#trending"],
    "linkedin": ["#linkedin", "#business", "#growth", "#professional", "#career"],
    "kids_channel": ["#kidscontent", "#learning", "#education", "#parenting", "#family"],
    "business": ["#business", "#entrepreneur", "#success", "#growth", "#marketing"]
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class GenerateRequest(BaseModel):
    platform: str = Field(..., description="instagram, youtube, linkedin, kids_channel, business")
    duration: int = Field(..., description="7, 14, or 30 days")
    goal: str = Field(..., description="followers, sales, engagement, brand_growth")

class DownloadRequest(BaseModel):
    plan_id: str

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def generate_day_plan(day_num: int, platform: str, goal: str) -> dict:
    """Generate content plan for a single day"""
    platform_data = PLATFORMS.get(platform, PLATFORMS["instagram"])
    
    # Select content type
    content_type = random.choice(platform_data["content_types"])
    
    # Select hook
    hook = random.choice(HOOKS_BY_GOAL.get(goal, HOOKS_BY_GOAL["followers"]))
    
    # Select content idea
    content_idea = random.choice(CONTENT_IDEAS_BY_PLATFORM.get(platform, CONTENT_IDEAS_BY_PLATFORM["instagram"]))
    
    # Select caption
    caption = random.choice(CAPTIONS_BY_GOAL.get(goal, CAPTIONS_BY_GOAL["followers"]))
    
    # Select CTA
    cta = CTAS_BY_GOAL.get(goal, "Follow for more!")
    
    # Select hashtags
    hashtags = random.sample(HASHTAGS_BY_PLATFORM.get(platform, HASHTAGS_BY_PLATFORM["instagram"]), 3)
    
    # Select posting time
    posting_time = random.choice(platform_data["optimal_times"])
    
    return {
        "day": day_num,
        "hook": hook,
        "content_idea": content_idea,
        "content_type": content_type,
        "caption": caption,
        "cta": cta,
        "hashtags": hashtags,
        "posting_time": posting_time
    }

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
@router.get("/config")
async def get_config():
    """Get feature configuration"""
    return {
        "platforms": PLATFORMS,
        "durations": [
            {"days": 7, "credits": PRICING["7_days"], "label": "7 Days"},
            {"days": 14, "credits": PRICING["14_days"], "label": "14 Days"},
            {"days": 30, "credits": PRICING["30_days"], "label": "30 Days"}
        ],
        "goals": GOALS,
        "add_ons": {
            "download_pdf": {"credits": PRICING["download_pdf"], "label": "Download PDF"}
        },
        "steps": [
            {"step": 1, "title": "Choose Platform", "description": "Select your content platform"},
            {"step": 2, "title": "Choose Duration", "description": "7, 14, or 30 day plan"},
            {"step": 3, "title": "Choose Goal", "description": "What do you want to achieve?"},
            {"step": 4, "title": "Generate", "description": "Get your content plan"}
        ]
    }

@router.post("/generate")
@limiter.limit("10/minute")
async def generate_plan(
    request: Request,
    data: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate content challenge plan - 4-step wizard endpoint"""
    user_id = user["id"]
    user_plan = user.get("plan", "free")
    
    # Validate inputs
    if data.platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform. Choose from: {list(PLATFORMS.keys())}")
    
    if data.duration not in [7, 14, 30]:
        raise HTTPException(status_code=400, detail="Duration must be 7, 14, or 30 days")
    
    if data.goal not in GOALS:
        raise HTTPException(status_code=400, detail=f"Invalid goal. Choose from: {list(GOALS.keys())}")
    
    # Calculate cost
    cost = PRICING[f"{data.duration}_days"]
    
    # Generate plan ID
    plan_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, cost, "CONTENT_CHALLENGE_PLANNER", plan_id)
    
    # Generate daily plans
    daily_plans = []
    for day in range(1, data.duration + 1):
        day_plan = generate_day_plan(day, data.platform, data.goal)
        daily_plans.append(day_plan)
    
    # Determine watermark status
    has_watermark = user_plan == "free"
    
    # Store plan
    plan_doc = {
        "id": plan_id,
        "userId": user_id,
        "platform": data.platform,
        "duration": data.duration,
        "goal": data.goal,
        "daily_plans": daily_plans,
        "credits_used": cost,
        "has_watermark": has_watermark,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.content_challenge_plans.insert_one(plan_doc)
    
    return {
        "success": True,
        "plan_id": plan_id,
        "platform": PLATFORMS[data.platform]["name"],
        "duration": data.duration,
        "goal": GOALS[data.goal]["name"],
        "daily_plans": daily_plans,
        "credits_used": cost,
        "has_watermark": has_watermark,
        "message": f"Your {data.duration}-day content plan is ready!"
    }

@router.post("/download-pdf")
async def download_pdf(
    data: DownloadRequest,
    user: dict = Depends(get_current_user)
):
    """Download plan as PDF - charges extra credits"""
    user_id = user["id"]
    
    # Get plan
    plan = await db.content_challenge_plans.find_one(
        {"id": data.plan_id, "userId": user_id},
        {"_id": 0}
    )
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if already downloaded
    if plan.get("pdf_downloaded"):
        return {"success": True, "message": "PDF already unlocked", "plan": plan}
    
    # Deduct credits
    download_id = str(uuid.uuid4())
    await deduct_credits(user_id, PRICING["download_pdf"], "PDF_DOWNLOAD", download_id)
    
    # Mark as downloaded
    await db.content_challenge_plans.update_one(
        {"id": data.plan_id},
        {"$set": {"pdf_downloaded": True}}
    )
    
    return {
        "success": True,
        "message": "PDF download unlocked!",
        "credits_used": PRICING["download_pdf"]
    }

@router.get("/plan/{plan_id}")
async def get_plan(plan_id: str, user: dict = Depends(get_current_user)):
    """Get plan details"""
    plan = await db.content_challenge_plans.find_one(
        {"id": plan_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan

@router.get("/history")
async def get_history(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get user's plan history"""
    plans = await db.content_challenge_plans.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    return {"plans": plans}
