"""
Content Vault & Trending Topics Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/content", tags=["Content Vault & Trending"])

# Import from main server
from server import get_current_user, get_admin_user, db

# =============================================================================
# CONTENT VAULT DATA
# =============================================================================

CONTENT_VAULT = {
    "viral_hooks": [
        # Luxury (50)
        {"id": 1, "niche": "luxury", "hook": "This is what $10,000 gets you in Dubai", "category": "lifestyle"},
        {"id": 2, "niche": "luxury", "hook": "Rich people never do this one thing", "category": "mindset"},
        {"id": 3, "niche": "luxury", "hook": "The watch billionaires actually wear", "category": "product"},
        {"id": 4, "niche": "luxury", "hook": "I spent a week living like a millionaire", "category": "experience"},
        {"id": 5, "niche": "luxury", "hook": "Why wealthy people wake up at 5 AM", "category": "routine"},
        {"id": 6, "niche": "luxury", "hook": "Inside a $50 million penthouse", "category": "property"},
        {"id": 7, "niche": "luxury", "hook": "The car that screams success", "category": "product"},
        {"id": 8, "niche": "luxury", "hook": "How the 1% vacation differently", "category": "travel"},
        {"id": 9, "niche": "luxury", "hook": "Signs you're becoming wealthy", "category": "mindset"},
        {"id": 10, "niche": "luxury", "hook": "Rich habits that cost nothing", "category": "mindset"},
        
        # Relationship (50)
        {"id": 11, "niche": "relationship", "hook": "If they do this, they're not the one", "category": "red_flags"},
        {"id": 12, "niche": "relationship", "hook": "The text that makes them obsessed", "category": "texting"},
        {"id": 13, "niche": "relationship", "hook": "Why your situationship won't commit", "category": "dating"},
        {"id": 14, "niche": "relationship", "hook": "Green flags you're ignoring", "category": "green_flags"},
        {"id": 15, "niche": "relationship", "hook": "The 3-second rule that changes everything", "category": "dating"},
        {"id": 16, "niche": "relationship", "hook": "What men secretly want but won't say", "category": "psychology"},
        {"id": 17, "niche": "relationship", "hook": "Stop doing this on dates", "category": "dating"},
        {"id": 18, "niche": "relationship", "hook": "Why your ex keeps coming back", "category": "psychology"},
        {"id": 19, "niche": "relationship", "hook": "The attachment style ruining your love life", "category": "psychology"},
        {"id": 20, "niche": "relationship", "hook": "How to make them miss you", "category": "strategy"},
        
        # Health (50)
        {"id": 21, "niche": "health", "hook": "I lost 20kg doing just this", "category": "weight_loss"},
        {"id": 22, "niche": "health", "hook": "Stop eating this every morning", "category": "nutrition"},
        {"id": 23, "niche": "health", "hook": "The workout nobody talks about", "category": "fitness"},
        {"id": 24, "niche": "health", "hook": "This changed my body in 30 days", "category": "transformation"},
        {"id": 25, "niche": "health", "hook": "Why you're always tired", "category": "energy"},
        {"id": 26, "niche": "health", "hook": "The morning routine that transformed me", "category": "routine"},
        {"id": 27, "niche": "health", "hook": "Foods that age you faster", "category": "nutrition"},
        {"id": 28, "niche": "health", "hook": "The exercise that burns the most fat", "category": "fitness"},
        {"id": 29, "niche": "health", "hook": "What I eat in a day to stay fit", "category": "nutrition"},
        {"id": 30, "niche": "health", "hook": "Stop doing this at the gym", "category": "fitness"},
        
        # Motivation (50)
        {"id": 31, "niche": "motivation", "hook": "This is your sign to start", "category": "inspiration"},
        {"id": 32, "niche": "motivation", "hook": "They laughed until I succeeded", "category": "success_story"},
        {"id": 33, "niche": "motivation", "hook": "You're closer than you think", "category": "encouragement"},
        {"id": 34, "niche": "motivation", "hook": "Nobody is coming to save you", "category": "tough_love"},
        {"id": 35, "niche": "motivation", "hook": "The mindset that changed everything", "category": "mindset"},
        {"id": 36, "niche": "motivation", "hook": "Watch this when you want to quit", "category": "perseverance"},
        {"id": 37, "niche": "motivation", "hook": "Your excuses are holding you back", "category": "tough_love"},
        {"id": 38, "niche": "motivation", "hook": "Remember why you started", "category": "inspiration"},
        {"id": 39, "niche": "motivation", "hook": "Stop waiting for the perfect moment", "category": "action"},
        {"id": 40, "niche": "motivation", "hook": "The habit that changed my life", "category": "habits"},
        
        # Business (50)
        {"id": 41, "niche": "business", "hook": "I made ₹1 lakh doing this", "category": "income"},
        {"id": 42, "niche": "business", "hook": "The side hustle that actually works", "category": "side_hustle"},
        {"id": 43, "niche": "business", "hook": "Stop trading time for money", "category": "passive_income"},
        {"id": 44, "niche": "business", "hook": "Why your business isn't growing", "category": "growth"},
        {"id": 45, "niche": "business", "hook": "The email that got me 10 clients", "category": "sales"},
        {"id": 46, "niche": "business", "hook": "How I got my first customer", "category": "startup"},
        {"id": 47, "niche": "business", "hook": "The pricing mistake killing your sales", "category": "pricing"},
        {"id": 48, "niche": "business", "hook": "Tools that 10x'd my productivity", "category": "tools"},
        {"id": 49, "niche": "business", "hook": "What I'd do differently starting over", "category": "lessons"},
        {"id": 50, "niche": "business", "hook": "The skill that makes you rich", "category": "skills"},
    ],
    
    "reel_structures": [
        {"id": 1, "name": "Hook-Problem-Solution", "structure": ["Hook (0-3s)", "Problem (3-10s)", "Solution (10-25s)", "CTA (25-30s)"], "best_for": "Educational"},
        {"id": 2, "name": "Storytime", "structure": ["Teaser hook", "Background", "Rising action", "Climax", "Resolution"], "best_for": "Personal stories"},
        {"id": 3, "name": "List Format", "structure": ["Big claim", "Point 1", "Point 2", "Point 3", "Bonus tip", "CTA"], "best_for": "Tips & tricks"},
        {"id": 4, "name": "Before/After", "structure": ["Show 'after' result", "Rewind to 'before'", "Show transformation", "Call to action"], "best_for": "Transformations"},
        {"id": 5, "name": "POV Style", "structure": ["POV: [situation]", "Show relatable scenario", "Unexpected twist", "Resolution"], "best_for": "Relatable content"},
        {"id": 6, "name": "Day in Life", "structure": ["Morning routine", "Work/Activity", "Afternoon", "Evening", "Reflection"], "best_for": "Lifestyle content"},
        {"id": 7, "name": "Tutorial", "structure": ["What you'll learn", "Step 1", "Step 2", "Step 3", "Final result"], "best_for": "How-to content"},
        {"id": 8, "name": "Myth Busting", "structure": ["State the myth", "Why people believe it", "The truth", "Proof/Evidence", "What to do instead"], "best_for": "Educational"},
        {"id": 9, "name": "Reaction", "structure": ["Show original content", "Your reaction", "Add value/insight", "Engage viewers"], "best_for": "Trending topics"},
        {"id": 10, "name": "Challenge", "structure": ["Explain challenge", "Attempt", "Struggle", "Success/Fail", "Lessons learned"], "best_for": "Engagement"},
    ],
    
    "kids_themes": [
        {"id": 1, "theme": "Friendship", "moral": "True friends help each other", "age_group": "4-8"},
        {"id": 2, "theme": "Courage", "moral": "Being brave doesn't mean not being scared", "age_group": "6-10"},
        {"id": 3, "theme": "Kindness", "moral": "Small acts of kindness make a big difference", "age_group": "4-8"},
        {"id": 4, "theme": "Honesty", "moral": "Telling the truth is always the right choice", "age_group": "5-9"},
        {"id": 5, "theme": "Perseverance", "moral": "Never give up on your dreams", "age_group": "6-10"},
        {"id": 6, "theme": "Sharing", "moral": "Sharing makes everyone happy", "age_group": "3-6"},
        {"id": 7, "theme": "Respect", "moral": "Treat others how you want to be treated", "age_group": "5-10"},
        {"id": 8, "theme": "Curiosity", "moral": "Asking questions helps us learn", "age_group": "4-8"},
        {"id": 9, "theme": "Teamwork", "moral": "Together we can achieve more", "age_group": "5-10"},
        {"id": 10, "theme": "Gratitude", "moral": "Be thankful for what you have", "age_group": "4-9"},
    ],
    
    "moral_templates": [
        {"id": 1, "moral": "Believe in yourself and anything is possible", "theme": "Self-confidence"},
        {"id": 2, "moral": "It's okay to make mistakes - that's how we learn", "theme": "Learning"},
        {"id": 3, "moral": "Everyone is special in their own way", "theme": "Uniqueness"},
        {"id": 4, "moral": "Family and friends are the greatest treasure", "theme": "Relationships"},
        {"id": 5, "moral": "Hard work always pays off in the end", "theme": "Hard work"},
        {"id": 6, "moral": "Be kind to everyone, even strangers", "theme": "Kindness"},
        {"id": 7, "moral": "Dreams come true for those who work for them", "theme": "Dreams"},
        {"id": 8, "moral": "The best things in life aren't things", "theme": "Values"},
        {"id": 9, "moral": "Every problem has a solution", "theme": "Problem-solving"},
        {"id": 10, "moral": "Love is the greatest magic of all", "theme": "Love"},
    ]
}

# User plan access levels
PLAN_ACCESS = {
    "free": {"hooks": 20, "structures": 5, "themes": 5, "morals": 5},
    "starter": {"hooks": 100, "structures": 10, "themes": 10, "morals": 10},
    "pro": {"hooks": 500, "structures": 200, "themes": 100, "morals": 50},
    "lifetime": {"hooks": 500, "structures": 200, "themes": 100, "morals": 50}  # No updates
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TrendingTopicCreate(BaseModel):
    title: str
    niche: str
    description: str
    hook_preview: str
    suggested_angle: str
    week_start: str
    week_end: str

class TrendingTopicUpdate(BaseModel):
    title: Optional[str] = None
    niche: Optional[str] = None
    description: Optional[str] = None
    hook_preview: Optional[str] = None
    suggested_angle: Optional[str] = None
    status: Optional[str] = None
    week_start: Optional[str] = None
    week_end: Optional[str] = None

# =============================================================================
# CONTENT VAULT ENDPOINTS
# =============================================================================

@router.get("/vault")
async def get_content_vault(
    category: Optional[str] = None,
    niche: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get content vault items based on user's plan"""
    # Determine user's plan access
    user_plan = user.get("plan", "free")
    access = PLAN_ACCESS.get(user_plan, PLAN_ACCESS["free"])
    
    result = {
        "plan": user_plan,
        "access_level": access,
        "viral_hooks": [],
        "reel_structures": [],
        "kids_themes": [],
        "moral_templates": [],
        "is_limited": user_plan == "free"
    }
    
    # Filter hooks
    hooks = CONTENT_VAULT["viral_hooks"]
    if niche:
        hooks = [h for h in hooks if h["niche"] == niche.lower()]
    result["viral_hooks"] = hooks[:access["hooks"]]
    result["total_hooks"] = len(CONTENT_VAULT["viral_hooks"])
    
    # Structures
    result["reel_structures"] = CONTENT_VAULT["reel_structures"][:access["structures"]]
    result["total_structures"] = len(CONTENT_VAULT["reel_structures"])
    
    # Kids themes
    result["kids_themes"] = CONTENT_VAULT["kids_themes"][:access["themes"]]
    result["total_themes"] = len(CONTENT_VAULT["kids_themes"])
    
    # Morals
    result["moral_templates"] = CONTENT_VAULT["moral_templates"][:access["morals"]]
    result["total_morals"] = len(CONTENT_VAULT["moral_templates"])
    
    if user_plan == "free":
        result["upgrade_message"] = "Upgrade to Pro to unlock 500+ viral hooks, 200 reel structures, and weekly updates!"
    
    return result


@router.get("/vault/niches")
async def get_vault_niches(user: dict = Depends(get_current_user)):
    """Get available niches in content vault"""
    niches = list(set(h["niche"] for h in CONTENT_VAULT["viral_hooks"]))
    return {
        "niches": niches,
        "total_per_niche": {n: len([h for h in CONTENT_VAULT["viral_hooks"] if h["niche"] == n]) for n in niches}
    }


# =============================================================================
# TRENDING TOPICS ENDPOINTS (Admin CMS)
# =============================================================================

@router.get("/trending")
async def get_trending_topics(
    active_only: bool = True,
    niche: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get current trending topics"""
    query = {}
    if active_only:
        query["status"] = "active"
    if niche:
        query["niche"] = niche.lower()
    
    topics = await db.trending_topics.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).limit(20).to_list(length=20)
    
    return {
        "topics": topics,
        "total": len(topics),
        "last_updated": topics[0].get("createdAt") if topics else None
    }


@router.post("/trending")
async def create_trending_topic(
    data: TrendingTopicCreate,
    user: dict = Depends(get_admin_user)
):
    """Create a new trending topic (Admin only)"""
    topic = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "niche": data.niche.lower(),
        "description": data.description,
        "hook_preview": data.hook_preview,
        "suggested_angle": data.suggested_angle,
        "status": "active",
        "week_start": data.week_start,
        "week_end": data.week_end,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "createdBy": user["id"]
    }
    
    await db.trending_topics.insert_one(topic)
    
    return {"success": True, "topic": topic}


@router.put("/trending/{topic_id}")
async def update_trending_topic(
    topic_id: str,
    data: TrendingTopicUpdate,
    user: dict = Depends(get_admin_user)
):
    """Update a trending topic (Admin only)"""
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.trending_topics.update_one(
        {"id": topic_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"success": True, "message": "Topic updated"}


@router.delete("/trending/{topic_id}")
async def delete_trending_topic(
    topic_id: str,
    user: dict = Depends(get_admin_user)
):
    """Delete a trending topic (Admin only)"""
    result = await db.trending_topics.delete_one({"id": topic_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"success": True, "message": "Topic deleted"}


@router.post("/trending/{topic_id}/toggle")
async def toggle_trending_topic(
    topic_id: str,
    user: dict = Depends(get_admin_user)
):
    """Toggle trending topic active/inactive status"""
    topic = await db.trending_topics.find_one({"id": topic_id})
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    new_status = "inactive" if topic.get("status") == "active" else "active"
    
    await db.trending_topics.update_one(
        {"id": topic_id},
        {"$set": {"status": new_status, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "status": new_status}
