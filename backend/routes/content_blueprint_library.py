"""
Content Blueprint Library Routes
CreatorStudio AI - Zero API Cost Digital Products

This feature provides pre-generated, database-served content products:
1. Viral Hook Bank - 500+ tested hooks for different niches
2. Reel Framework Packs - Complete content frameworks
3. Kids Story Idea Bank - Pre-written story concepts

ZERO LLM API CALLS - All content is pre-populated in database
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_admin_user, deduct_credits
from security import limiter

router = APIRouter(prefix="/blueprint-library", tags=["Content Blueprint Library"])

# ============================================================================
# PRICING CONFIGURATION (Credits)
# ============================================================================
PRICING = {
    "viral_hook_bank": {
        "single_hook": 1,
        "niche_pack": 15,  # ~50 hooks
        "full_access": 75   # All 500+ hooks
    },
    "reel_frameworks": {
        "single_framework": 5,
        "category_pack": 25,  # ~10 frameworks
        "full_access": 100   # All frameworks
    },
    "kids_story_ideas": {
        "single_idea": 3,
        "genre_pack": 20,    # ~15 ideas
        "full_access": 80    # All ideas
    }
}

# ============================================================================
# REQUEST MODELS
# ============================================================================
class PurchaseRequest(BaseModel):
    product_type: str = Field(..., description="viral_hook_bank, reel_frameworks, kids_story_ideas")
    purchase_tier: str = Field(..., description="single, pack, full_access")
    item_id: Optional[str] = Field(None, description="Specific item ID for single purchase")
    category: Optional[str] = Field(None, description="Category/niche/genre for pack purchase")


# ============================================================================
# CATALOG ENDPOINTS
# ============================================================================
@router.get("/catalog")
async def get_catalog(user: dict = Depends(get_current_user)):
    """
    Get the full catalog overview with pricing.
    """
    # Get counts from database
    hooks_count = await db.blueprint_hooks.count_documents({})
    frameworks_count = await db.blueprint_frameworks.count_documents({})
    story_ideas_count = await db.blueprint_story_ideas.count_documents({})
    
    # Get unique categories
    hook_niches = await db.blueprint_hooks.distinct("niche")
    framework_categories = await db.blueprint_frameworks.distinct("category")
    story_genres = await db.blueprint_story_ideas.distinct("genre")
    
    # Check user's purchases
    user_purchases = await db.blueprint_purchases.find(
        {"user_id": user["id"]},
        {"_id": 0, "product_type": 1, "purchase_tier": 1, "category": 1}
    ).to_list(100)
    
    purchased_items = {
        "viral_hook_bank": [],
        "reel_frameworks": [],
        "kids_story_ideas": []
    }
    
    for purchase in user_purchases:
        pt = purchase.get("product_type")
        if pt in purchased_items:
            purchased_items[pt].append({
                "tier": purchase.get("purchase_tier"),
                "category": purchase.get("category")
            })
    
    return {
        "products": [
            {
                "id": "viral_hook_bank",
                "name": "Viral Hook Bank",
                "description": "500+ tested viral hooks organized by niche. Proven to grab attention in the first 3 seconds.",
                "icon": "Zap",
                "item_count": hooks_count,
                "categories": hook_niches,
                "pricing": PRICING["viral_hook_bank"],
                "preview_available": True,
                "featured_items": await _get_featured_hooks()
            },
            {
                "id": "reel_frameworks",
                "name": "Reel Framework Packs",
                "description": "Complete reel templates with scripts, hooks, CTAs, and posting strategies. Just fill in your topic.",
                "icon": "Layout",
                "item_count": frameworks_count,
                "categories": framework_categories,
                "pricing": PRICING["reel_frameworks"],
                "preview_available": True,
                "featured_items": await _get_featured_frameworks()
            },
            {
                "id": "kids_story_ideas",
                "name": "Kids Story Idea Bank",
                "description": "200+ creative story concepts for kids content. Complete with characters, morals, and scene outlines.",
                "icon": "BookOpen",
                "item_count": story_ideas_count,
                "categories": story_genres,
                "pricing": PRICING["kids_story_ideas"],
                "preview_available": True,
                "featured_items": await _get_featured_story_ideas()
            }
        ],
        "user_credits": user.get("credits", 0),
        "user_purchases": purchased_items
    }


async def _get_featured_hooks():
    """Get featured hooks for catalog preview"""
    hooks = await db.blueprint_hooks.find(
        {"featured": True},
        {"_id": 0, "id": 1, "hook_text": 1, "niche": 1, "engagement_score": 1}
    ).limit(5).to_list(5)
    return hooks


async def _get_featured_frameworks():
    """Get featured frameworks for catalog preview"""
    frameworks = await db.blueprint_frameworks.find(
        {"featured": True},
        {"_id": 0, "id": 1, "title": 1, "category": 1, "description": 1}
    ).limit(3).to_list(3)
    return frameworks


async def _get_featured_story_ideas():
    """Get featured story ideas for catalog preview"""
    ideas = await db.blueprint_story_ideas.find(
        {"featured": True},
        {"_id": 0, "id": 1, "title": 1, "genre": 1, "age_group": 1}
    ).limit(5).to_list(5)
    return ideas


# ============================================================================
# VIRAL HOOK BANK
# ============================================================================
@router.get("/hooks")
@limiter.limit("60/minute")
async def get_hooks(
    request: Request,
    niche: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """
    Get hooks from the Viral Hook Bank.
    Users can preview hooks but full content requires purchase.
    """
    # Check user's access level
    purchases = await db.blueprint_purchases.find(
        {"user_id": user["id"], "product_type": "viral_hook_bank"},
        {"_id": 0}
    ).to_list(100)
    
    has_full_access = any(p.get("purchase_tier") == "full_access" for p in purchases)
    purchased_niches = [p.get("category") for p in purchases if p.get("purchase_tier") == "niche_pack"]
    purchased_singles = [p.get("item_id") for p in purchases if p.get("purchase_tier") == "single"]
    
    # Build query
    query = {}
    if niche:
        query["niche"] = niche
    
    skip = (page - 1) * size
    total = await db.blueprint_hooks.count_documents(query)
    
    # Get all unique niches for filter
    all_niches = await db.blueprint_hooks.distinct("niche")
    
    hooks = await db.blueprint_hooks.find(
        query,
        {"_id": 0}
    ).sort([("engagement_score", -1), ("created_at", -1)]).skip(skip).limit(size).to_list(size)
    
    # Add access info to each hook
    for hook in hooks:
        hook_niche = hook.get("niche")
        hook_id = hook.get("id")
        
        if has_full_access or hook_niche in purchased_niches or hook_id in purchased_singles:
            hook["is_unlocked"] = True
        else:
            hook["is_unlocked"] = False
            # Truncate the hook for preview
            if hook.get("hook_text") and len(hook["hook_text"]) > 30:
                hook["hook_text"] = hook["hook_text"][:30] + "..."
            # Hide premium fields
            hook.pop("variations", None)
            hook.pop("script_template", None)
    
    return {
        "hooks": hooks,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        },
        "niches": all_niches,
        "access": {
            "has_full_access": has_full_access,
            "purchased_niches": purchased_niches,
            "purchased_singles": len(purchased_singles)
        }
    }


@router.get("/hooks/{hook_id}")
async def get_hook_detail(hook_id: str, user: dict = Depends(get_current_user)):
    """
    Get a specific hook's full details.
    Requires purchase to view full content.
    """
    hook = await db.blueprint_hooks.find_one({"id": hook_id}, {"_id": 0})
    if not hook:
        raise HTTPException(status_code=404, detail="Hook not found")
    
    # Check access
    is_unlocked = await _check_hook_access(user["id"], hook_id, hook.get("niche"))
    
    if not is_unlocked:
        # Return limited preview
        return {
            "hook": {
                "id": hook["id"],
                "niche": hook["niche"],
                "hook_text": hook["hook_text"][:30] + "..." if len(hook.get("hook_text", "")) > 30 else hook.get("hook_text"),
                "engagement_score": hook.get("engagement_score"),
                "is_unlocked": False
            },
            "purchase_options": PRICING["viral_hook_bank"]
        }
    
    hook["is_unlocked"] = True
    return {"hook": hook}


async def _check_hook_access(user_id: str, hook_id: str, niche: str) -> bool:
    """Check if user has access to a specific hook"""
    purchase = await db.blueprint_purchases.find_one({
        "user_id": user_id,
        "product_type": "viral_hook_bank",
        "$or": [
            {"purchase_tier": "full_access"},
            {"purchase_tier": "niche_pack", "category": niche},
            {"purchase_tier": "single", "item_id": hook_id}
        ]
    })
    return purchase is not None


# ============================================================================
# REEL FRAMEWORKS
# ============================================================================
@router.get("/frameworks")
@limiter.limit("60/minute")
async def get_frameworks(
    request: Request,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Get reel frameworks.
    """
    # Check user's access
    purchases = await db.blueprint_purchases.find(
        {"user_id": user["id"], "product_type": "reel_frameworks"},
        {"_id": 0}
    ).to_list(100)
    
    has_full_access = any(p.get("purchase_tier") == "full_access" for p in purchases)
    purchased_categories = [p.get("category") for p in purchases if p.get("purchase_tier") == "category_pack"]
    purchased_singles = [p.get("item_id") for p in purchases if p.get("purchase_tier") == "single"]
    
    query = {}
    if category:
        query["category"] = category
    
    skip = (page - 1) * size
    total = await db.blueprint_frameworks.count_documents(query)
    all_categories = await db.blueprint_frameworks.distinct("category")
    
    frameworks = await db.blueprint_frameworks.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(size)
    
    for framework in frameworks:
        fw_category = framework.get("category")
        fw_id = framework.get("id")
        
        if has_full_access or fw_category in purchased_categories or fw_id in purchased_singles:
            framework["is_unlocked"] = True
        else:
            framework["is_unlocked"] = False
            # Hide premium content
            framework.pop("full_script", None)
            framework.pop("scene_breakdown", None)
            framework.pop("cta_options", None)
    
    return {
        "frameworks": frameworks,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        },
        "categories": all_categories,
        "access": {
            "has_full_access": has_full_access,
            "purchased_categories": purchased_categories
        }
    }


@router.get("/frameworks/{framework_id}")
async def get_framework_detail(framework_id: str, user: dict = Depends(get_current_user)):
    """Get a specific framework's full details."""
    framework = await db.blueprint_frameworks.find_one({"id": framework_id}, {"_id": 0})
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")
    
    # Check access
    is_unlocked = await _check_framework_access(user["id"], framework_id, framework.get("category"))
    
    if not is_unlocked:
        return {
            "framework": {
                "id": framework["id"],
                "title": framework["title"],
                "category": framework["category"],
                "description": framework.get("description"),
                "preview_hook": framework.get("preview_hook"),
                "is_unlocked": False
            },
            "purchase_options": PRICING["reel_frameworks"]
        }
    
    framework["is_unlocked"] = True
    return {"framework": framework}


async def _check_framework_access(user_id: str, framework_id: str, category: str) -> bool:
    """Check if user has access to a specific framework"""
    purchase = await db.blueprint_purchases.find_one({
        "user_id": user_id,
        "product_type": "reel_frameworks",
        "$or": [
            {"purchase_tier": "full_access"},
            {"purchase_tier": "category_pack", "category": category},
            {"purchase_tier": "single", "item_id": framework_id}
        ]
    })
    return purchase is not None


# ============================================================================
# KIDS STORY IDEAS
# ============================================================================
@router.get("/story-ideas")
@limiter.limit("60/minute")
async def get_story_ideas(
    request: Request,
    genre: Optional[str] = None,
    age_group: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(15, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """
    Get kids story ideas.
    """
    # Check user's access
    purchases = await db.blueprint_purchases.find(
        {"user_id": user["id"], "product_type": "kids_story_ideas"},
        {"_id": 0}
    ).to_list(100)
    
    has_full_access = any(p.get("purchase_tier") == "full_access" for p in purchases)
    purchased_genres = [p.get("category") for p in purchases if p.get("purchase_tier") == "genre_pack"]
    purchased_singles = [p.get("item_id") for p in purchases if p.get("purchase_tier") == "single"]
    
    query = {}
    if genre:
        query["genre"] = genre
    if age_group:
        query["age_group"] = age_group
    
    skip = (page - 1) * size
    total = await db.blueprint_story_ideas.count_documents(query)
    all_genres = await db.blueprint_story_ideas.distinct("genre")
    all_age_groups = await db.blueprint_story_ideas.distinct("age_group")
    
    ideas = await db.blueprint_story_ideas.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(size).to_list(size)
    
    for idea in ideas:
        idea_genre = idea.get("genre")
        idea_id = idea.get("id")
        
        if has_full_access or idea_genre in purchased_genres or idea_id in purchased_singles:
            idea["is_unlocked"] = True
        else:
            idea["is_unlocked"] = False
            # Hide premium content
            idea.pop("full_synopsis", None)
            idea.pop("scene_outlines", None)
            idea.pop("character_details", None)
    
    return {
        "ideas": ideas,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        },
        "genres": all_genres,
        "age_groups": all_age_groups,
        "access": {
            "has_full_access": has_full_access,
            "purchased_genres": purchased_genres
        }
    }


@router.get("/story-ideas/{idea_id}")
async def get_story_idea_detail(idea_id: str, user: dict = Depends(get_current_user)):
    """Get a specific story idea's full details."""
    idea = await db.blueprint_story_ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea:
        raise HTTPException(status_code=404, detail="Story idea not found")
    
    # Check access
    is_unlocked = await _check_story_idea_access(user["id"], idea_id, idea.get("genre"))
    
    if not is_unlocked:
        return {
            "idea": {
                "id": idea["id"],
                "title": idea["title"],
                "genre": idea["genre"],
                "age_group": idea.get("age_group"),
                "brief_synopsis": idea.get("brief_synopsis"),
                "is_unlocked": False
            },
            "purchase_options": PRICING["kids_story_ideas"]
        }
    
    idea["is_unlocked"] = True
    return {"idea": idea}


async def _check_story_idea_access(user_id: str, idea_id: str, genre: str) -> bool:
    """Check if user has access to a specific story idea"""
    purchase = await db.blueprint_purchases.find_one({
        "user_id": user_id,
        "product_type": "kids_story_ideas",
        "$or": [
            {"purchase_tier": "full_access"},
            {"purchase_tier": "genre_pack", "category": genre},
            {"purchase_tier": "single", "item_id": idea_id}
        ]
    })
    return purchase is not None


# ============================================================================
# PURCHASE ENDPOINTS
# ============================================================================
@router.post("/purchase")
@limiter.limit("30/minute")
async def purchase_content(
    request: Request,
    data: PurchaseRequest,
    user: dict = Depends(get_current_user)
):
    """
    Purchase content from the Blueprint Library.
    Deducts credits and grants access.
    """
    product_type = data.product_type
    purchase_tier = data.purchase_tier
    
    # Validate product type
    if product_type not in PRICING:
        raise HTTPException(status_code=400, detail="Invalid product type")
    
    # Map tier names
    tier_map = {
        "single": ["single_hook", "single_framework", "single_idea"],
        "pack": ["niche_pack", "category_pack", "genre_pack"],
        "full_access": ["full_access"]
    }
    
    # Get correct pricing key
    pricing_key = None
    product_pricing = PRICING[product_type]
    
    if purchase_tier == "single":
        if product_type == "viral_hook_bank":
            pricing_key = "single_hook"
        elif product_type == "reel_frameworks":
            pricing_key = "single_framework"
        else:
            pricing_key = "single_idea"
    elif purchase_tier == "pack":
        if product_type == "viral_hook_bank":
            pricing_key = "niche_pack"
        elif product_type == "reel_frameworks":
            pricing_key = "category_pack"
        else:
            pricing_key = "genre_pack"
    elif purchase_tier == "full_access":
        pricing_key = "full_access"
    else:
        raise HTTPException(status_code=400, detail="Invalid purchase tier")
    
    credits_required = product_pricing.get(pricing_key, 0)
    
    if credits_required <= 0:
        raise HTTPException(status_code=400, detail="Invalid pricing configuration")
    
    # Validate single/pack purchase requirements
    if purchase_tier == "single" and not data.item_id:
        raise HTTPException(status_code=400, detail="Item ID required for single purchase")
    
    if purchase_tier == "pack" and not data.category:
        raise HTTPException(status_code=400, detail="Category/niche/genre required for pack purchase")
    
    # Check if already purchased
    existing_query = {
        "user_id": user["id"],
        "product_type": product_type
    }
    
    if purchase_tier == "full_access":
        existing_query["purchase_tier"] = "full_access"
    elif purchase_tier == "pack":
        existing_query["purchase_tier"] = purchase_tier
        existing_query["category"] = data.category
    elif purchase_tier == "single":
        existing_query["purchase_tier"] = purchase_tier
        existing_query["item_id"] = data.item_id
    
    existing = await db.blueprint_purchases.find_one(existing_query)
    if existing:
        raise HTTPException(status_code=400, detail="You already own this content")
    
    # Check if user has full access (makes other purchases redundant)
    if purchase_tier != "full_access":
        has_full = await db.blueprint_purchases.find_one({
            "user_id": user["id"],
            "product_type": product_type,
            "purchase_tier": "full_access"
        })
        if has_full:
            raise HTTPException(status_code=400, detail="You already have full access to this product")
    
    # Deduct credits
    try:
        new_balance = await deduct_credits(
            user["id"],
            credits_required,
            f"Blueprint Library: {product_type} - {purchase_tier}"
        )
    except HTTPException as e:
        raise e
    
    # Create purchase record
    purchase = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "product_type": product_type,
        "purchase_tier": purchase_tier,
        "item_id": data.item_id,
        "category": data.category,
        "credits_spent": credits_required,
        "purchased_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.blueprint_purchases.insert_one(purchase)
    
    logger.info(f"Blueprint purchase: user={user['id']}, product={product_type}, tier={purchase_tier}, credits={credits_required}")
    
    return {
        "success": True,
        "message": "Purchase successful!",
        "purchase_id": purchase["id"],
        "credits_spent": credits_required,
        "new_balance": new_balance,
        "access_granted": {
            "product_type": product_type,
            "tier": purchase_tier,
            "category": data.category,
            "item_id": data.item_id
        }
    }


@router.get("/my-purchases")
async def get_my_purchases(user: dict = Depends(get_current_user)):
    """
    Get user's purchase history for the Blueprint Library.
    """
    purchases = await db.blueprint_purchases.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("purchased_at", -1).to_list(100)
    
    # Group by product type
    by_product = {
        "viral_hook_bank": [],
        "reel_frameworks": [],
        "kids_story_ideas": []
    }
    
    total_spent = 0
    for p in purchases:
        pt = p.get("product_type")
        if pt in by_product:
            by_product[pt].append(p)
        total_spent += p.get("credits_spent", 0)
    
    return {
        "purchases": purchases,
        "by_product": by_product,
        "total_spent": total_spent,
        "total_purchases": len(purchases)
    }


# ============================================================================
# ADMIN: SEED DATABASE ENDPOINT
# ============================================================================
@router.post("/admin/seed-database")
async def seed_blueprint_database(admin: dict = Depends(get_admin_user)):
    """
    Seed the Blueprint Library database with initial content.
    Admin only endpoint - run once to populate content.
    """
    hooks_created = await _seed_hooks()
    frameworks_created = await _seed_frameworks()
    story_ideas_created = await _seed_story_ideas()
    
    return {
        "success": True,
        "seeded": {
            "hooks": hooks_created,
            "frameworks": frameworks_created,
            "story_ideas": story_ideas_created
        }
    }


async def _seed_hooks():
    """Seed viral hooks database"""
    existing = await db.blueprint_hooks.count_documents({})
    if existing > 0:
        return 0  # Already seeded
    
    hooks_data = [
        # Motivation Niche
        {"niche": "Motivation", "hook_text": "Stop scrolling. This will change your life.", "engagement_score": 95, "featured": True,
         "variations": ["Wait. What I'm about to say will change everything.", "Before you scroll, hear this one thing."],
         "script_template": "Hook → Pain point → Solution → Transformation story → CTA", "best_for": "Personal growth, mindset shifts"},
        
        {"niche": "Motivation", "hook_text": "3 things I wish I knew before turning 30", "engagement_score": 92, "featured": True,
         "variations": ["5 lessons nobody taught me in my 20s", "What I'd tell my younger self"],
         "script_template": "Hook → List format → Personal story for each → Key takeaway", "best_for": "Age-based content, life lessons"},
        
        {"niche": "Motivation", "hook_text": "This is your sign to finally start.", "engagement_score": 88, "featured": False,
         "variations": ["If you needed permission, here it is.", "The universe is telling you something."],
         "script_template": "Hook → Why people hesitate → Permission granted → Action step", "best_for": "Call to action content"},
        
        {"niche": "Motivation", "hook_text": "Nobody talks about this side of success...", "engagement_score": 91, "featured": True,
         "variations": ["The dark side of achievement nobody shows", "What success really costs"],
         "script_template": "Hook → Hidden truth → Real examples → Balance perspective", "best_for": "Authenticity content"},
        
        {"niche": "Motivation", "hook_text": "I failed 47 times before this worked.", "engagement_score": 89, "featured": False,
         "variations": ["After 100 rejections, I finally understood", "My biggest failure taught me this"],
         "script_template": "Hook → Failure story → Turning point → Lesson learned → Current success", "best_for": "Resilience content"},
        
        # Business/Finance Niche
        {"niche": "Business", "hook_text": "POV: You finally understood passive income", "engagement_score": 94, "featured": True,
         "variations": ["POV: Money works for you now", "POV: You escaped the 9-5"],
         "script_template": "Hook → Before/After → How it works → Simple first step", "best_for": "Financial education"},
        
        {"niche": "Business", "hook_text": "This $0 strategy made me $10K last month", "engagement_score": 93, "featured": True,
         "variations": ["How I made $5K with zero investment", "Free method that changed everything"],
         "script_template": "Hook → Strategy reveal → Step-by-step → Results proof → Your turn", "best_for": "Low-barrier strategies"},
        
        {"niche": "Business", "hook_text": "Rich people don't want you to know this.", "engagement_score": 87, "featured": False,
         "variations": ["The 1% keeps this secret", "Why they don't teach this in school"],
         "script_template": "Hook → Hidden knowledge → Why it's hidden → How to use it", "best_for": "Financial secrets content"},
        
        {"niche": "Business", "hook_text": "I quit my 6-figure job for this.", "engagement_score": 90, "featured": False,
         "variations": ["Why I left corporate America", "Trading security for freedom"],
         "script_template": "Hook → Corporate story → Decision moment → New life → Advice", "best_for": "Career change content"},
        
        {"niche": "Business", "hook_text": "Your boss doesn't want you to see this.", "engagement_score": 86, "featured": False,
         "variations": ["What HR won't tell you", "The truth about your salary"],
         "script_template": "Hook → Hidden truth → Why it matters → What to do", "best_for": "Career advice"},
        
        # Fitness/Health Niche
        {"niche": "Fitness", "hook_text": "I lost 30 lbs without giving up pizza.", "engagement_score": 96, "featured": True,
         "variations": ["How I got abs eating what I love", "The diet that doesn't feel like one"],
         "script_template": "Hook → Before photo → Secret method → Daily routine → After photo", "best_for": "Weight loss content"},
        
        {"niche": "Fitness", "hook_text": "Stop doing crunches. Here's what actually works.", "engagement_score": 91, "featured": True,
         "variations": ["The exercise you're wasting time on", "Why your workouts aren't working"],
         "script_template": "Hook → Myth bust → Real science → Better alternative → Demo", "best_for": "Exercise education"},
        
        {"niche": "Fitness", "hook_text": "5-minute morning routine that changed my body", "engagement_score": 89, "featured": False,
         "variations": ["The habit that transformed my health", "What I do before breakfast every day"],
         "script_template": "Hook → Routine demo → Why it works → Results → Challenge", "best_for": "Routine content"},
        
        {"niche": "Fitness", "hook_text": "Your trainer is lying to you about this.", "engagement_score": 85, "featured": False,
         "variations": ["Gym secrets they don't tell you", "Why your progress stalled"],
         "script_template": "Hook → Industry truth → Real approach → Better results", "best_for": "Myth-busting"},
        
        # Lifestyle Niche
        {"niche": "Lifestyle", "hook_text": "Things I stopped buying after 30 (and don't miss)", "engagement_score": 88, "featured": True,
         "variations": ["What I removed from my life", "Decluttering changed everything"],
         "script_template": "Hook → List of items → Why each → Money saved → Quality of life", "best_for": "Minimalism content"},
        
        {"niche": "Lifestyle", "hook_text": "This $20 item upgraded my entire life.", "engagement_score": 90, "featured": True,
         "variations": ["Best purchase I ever made", "Life-changing for under $50"],
         "script_template": "Hook → Item reveal → How you use it → Before/After → Where to get it", "best_for": "Product recommendations"},
        
        {"niche": "Lifestyle", "hook_text": "Living alone taught me these 5 things.", "engagement_score": 86, "featured": False,
         "variations": ["What independence really means", "Lessons from solo life"],
         "script_template": "Hook → Life lessons → Personal stories → Growth shown", "best_for": "Personal growth"},
        
        # Parenting Niche
        {"niche": "Parenting", "hook_text": "Wish I knew this before becoming a parent.", "engagement_score": 92, "featured": True,
         "variations": ["What nobody tells new parents", "Parenting secrets from year 1"],
         "script_template": "Hook → Real challenges → Solutions found → Advice", "best_for": "New parent content"},
        
        {"niche": "Parenting", "hook_text": "My toddler taught me more than my MBA.", "engagement_score": 87, "featured": False,
         "variations": ["Business lessons from a 3-year-old", "What kids understand that adults forgot"],
         "script_template": "Hook → Lesson reveal → How it applies → Reflection", "best_for": "Parenting wisdom"},
        
        # Relationships Niche
        {"niche": "Relationships", "hook_text": "Green flags I ignored (and regret it)", "engagement_score": 89, "featured": True,
         "variations": ["Signs I missed in my last relationship", "What I should have valued"],
         "script_template": "Hook → Green flags list → Why they matter → Learn from me", "best_for": "Dating advice"},
        
        {"niche": "Relationships", "hook_text": "The text that saved my relationship.", "engagement_score": 91, "featured": True,
         "variations": ["One conversation changed everything", "How we almost broke up"],
         "script_template": "Hook → Crisis moment → The message → Turnaround → Lesson", "best_for": "Relationship stories"},
        
        # Tech/Productivity Niche
        {"niche": "Tech", "hook_text": "iPhone settings you didn't know existed.", "engagement_score": 94, "featured": True,
         "variations": ["Hidden features on your phone", "Settings to change right now"],
         "script_template": "Hook → Setting reveal → How to access → Why it helps", "best_for": "Tech tips"},
        
        {"niche": "Tech", "hook_text": "This free app replaced 5 paid ones.", "engagement_score": 93, "featured": True,
         "variations": ["Apps you're overpaying for", "Free alternatives that work better"],
         "script_template": "Hook → App reveal → Features demo → Download link", "best_for": "App recommendations"},
        
        # Food Niche
        {"niche": "Food", "hook_text": "Restaurant secret they don't want you to know.", "engagement_score": 88, "featured": True,
         "variations": ["Why restaurant food tastes better", "Chef secrets revealed"],
         "script_template": "Hook → Secret reveal → How to do it at home → Demo", "best_for": "Cooking tips"},
        
        {"niche": "Food", "hook_text": "5-ingredient dinner that tastes like takeout.", "engagement_score": 90, "featured": True,
         "variations": ["Easy meal that impresses everyone", "Recipe that looks hard but isn't"],
         "script_template": "Hook → Ingredients → Quick demo → Final reveal → Tag someone", "best_for": "Recipe content"},
    ]
    
    # Add IDs and timestamps
    for i, hook in enumerate(hooks_data):
        hook["id"] = str(uuid.uuid4())
        hook["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.blueprint_hooks.insert_many(hooks_data)
    return len(hooks_data)


async def _seed_frameworks():
    """Seed reel frameworks database"""
    existing = await db.blueprint_frameworks.count_documents({})
    if existing > 0:
        return 0
    
    frameworks_data = [
        # Educational Category
        {
            "category": "Educational",
            "title": "The 3-Step Revelation Framework",
            "description": "Perfect for teaching something new in under 60 seconds. Hook → Problem → 3 Steps → CTA",
            "featured": True,
            "preview_hook": "Stop! Before you scroll, you need to know this...",
            "full_script": {
                "hook": {"text": "[PROBLEM] is ruining your [GOAL]. Here's the fix in 3 steps.", "duration": "0-3s"},
                "step1": {"text": "Step 1: [ACTION]. This alone will [BENEFIT].", "duration": "3-12s"},
                "step2": {"text": "Step 2: [ACTION]. Most people skip this but it's crucial.", "duration": "12-22s"},
                "step3": {"text": "Step 3: [ACTION]. This is where the magic happens.", "duration": "22-28s"},
                "cta": {"text": "Follow for more [NICHE] tips that actually work!", "duration": "28-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Text overlay with hook", "action": "Direct eye contact"},
                {"scene": 2, "visual": "Step 1 demonstration", "action": "Show, don't just tell"},
                {"scene": 3, "visual": "Step 2 demonstration", "action": "Use B-roll if needed"},
                {"scene": 4, "visual": "Step 3 demonstration", "action": "Show transformation"},
                {"scene": 5, "visual": "Call to action", "action": "Point at follow button"}
            ],
            "cta_options": ["Follow for more", "Save this for later", "Comment your question", "Share with someone who needs this"],
            "best_niches": ["Business", "Fitness", "Tech", "Finance"],
            "estimated_engagement": "High"
        },
        
        {
            "category": "Educational",
            "title": "The Myth-Buster Framework",
            "description": "Challenge common beliefs and provide the truth. Great for building authority.",
            "featured": True,
            "preview_hook": "Everything you know about [TOPIC] is wrong...",
            "full_script": {
                "hook": {"text": "You've been lied to about [TOPIC]. Here's the truth.", "duration": "0-3s"},
                "myth": {"text": "The myth: [COMMON BELIEF]. Everyone thinks this works.", "duration": "3-10s"},
                "truth": {"text": "The truth: [REALITY]. Here's why [EXPLANATION].", "duration": "10-20s"},
                "proof": {"text": "The proof: [EVIDENCE/RESULTS]. I tested this myself.", "duration": "20-26s"},
                "cta": {"text": "Mind blown? Follow for more truth bombs.", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Dramatic reveal face", "action": "Build curiosity"},
                {"scene": 2, "visual": "Show the myth visually", "action": "Use text overlay"},
                {"scene": 3, "visual": "Truth demonstration", "action": "Show evidence"},
                {"scene": 4, "visual": "Before/after or data", "action": "Prove your point"},
                {"scene": 5, "visual": "Engaging CTA", "action": "Ask for follow"}
            ],
            "cta_options": ["Share this with someone who believes the myth", "Comment if you knew this", "Follow for more"],
            "best_niches": ["Fitness", "Finance", "Health", "Business"],
            "estimated_engagement": "Very High"
        },
        
        # Story Category
        {
            "category": "Story",
            "title": "The Personal Journey Framework",
            "description": "Share your transformation story to connect emotionally with your audience.",
            "featured": True,
            "preview_hook": "A year ago, I was [STRUGGLE]. Now I'm [SUCCESS].",
            "full_script": {
                "hook": {"text": "12 months ago, I [STRUGGLE]. Today, I [ACHIEVEMENT].", "duration": "0-4s"},
                "struggle": {"text": "I was [DESCRIBE LOW POINT]. I felt [EMOTION].", "duration": "4-12s"},
                "turning_point": {"text": "Then I discovered [INSIGHT/METHOD]. Everything changed.", "duration": "12-20s"},
                "transformation": {"text": "Now I [RESULT]. And you can too.", "duration": "20-26s"},
                "cta": {"text": "Follow my journey. Comment 'HOW' for the full breakdown.", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Split screen before/after", "action": "Show transformation"},
                {"scene": 2, "visual": "Old photos/footage", "action": "Show the struggle"},
                {"scene": 3, "visual": "Lightbulb moment", "action": "Dramatic reveal"},
                {"scene": 4, "visual": "Current success", "action": "Show results"},
                {"scene": 5, "visual": "Direct to camera", "action": "Invite engagement"}
            ],
            "cta_options": ["Comment 'ME' if this resonates", "Follow for part 2", "DM me for help"],
            "best_niches": ["Motivation", "Fitness", "Business", "Lifestyle"],
            "estimated_engagement": "Very High"
        },
        
        # Controversial Category
        {
            "category": "Controversial",
            "title": "The Unpopular Opinion Framework",
            "description": "Share a bold take that sparks debate and engagement.",
            "featured": False,
            "preview_hook": "Unpopular opinion: [BOLD STATEMENT]",
            "full_script": {
                "hook": {"text": "Unpopular opinion that might get me cancelled...", "duration": "0-3s"},
                "opinion": {"text": "[BOLD STATEMENT]. I know, I know. Let me explain.", "duration": "3-10s"},
                "reasoning": {"text": "Here's why: [LOGIC/EVIDENCE]. Think about it.", "duration": "10-20s"},
                "challenge": {"text": "Change my mind. Comment your take below.", "duration": "20-26s"},
                "cta": {"text": "Follow if you're not afraid of real talk.", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Bold text overlay", "action": "Create tension"},
                {"scene": 2, "visual": "State the opinion", "action": "Own it confidently"},
                {"scene": 3, "visual": "Explain reasoning", "action": "Be logical"},
                {"scene": 4, "visual": "Invite debate", "action": "Show openness"},
                {"scene": 5, "visual": "CTA", "action": "Bold finish"}
            ],
            "cta_options": ["Agree or disagree?", "Change my mind", "Hot take? Follow for more"],
            "best_niches": ["Business", "Lifestyle", "Relationships", "Finance"],
            "estimated_engagement": "Very High (Viral Potential)"
        },
        
        # How-To Category
        {
            "category": "How-To",
            "title": "The Quick Tutorial Framework",
            "description": "Teach a specific skill in 30 seconds or less.",
            "featured": True,
            "preview_hook": "Learn [SKILL] in 30 seconds. Ready?",
            "full_script": {
                "hook": {"text": "Learn [SKILL] in 30 seconds. Watch carefully.", "duration": "0-3s"},
                "setup": {"text": "First, [PREPARE]. This is crucial.", "duration": "3-8s"},
                "action": {"text": "Now [DO THE THING]. See how I [TECHNIQUE]?", "duration": "8-18s"},
                "tip": {"text": "Pro tip: [INSIDER KNOWLEDGE]. This is what separates beginners from pros.", "duration": "18-25s"},
                "cta": {"text": "Save this. Practice. Tag me when you nail it!", "duration": "25-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "Promise the result", "action": "Build anticipation"},
                {"scene": 2, "visual": "Show setup", "action": "Clear instruction"},
                {"scene": 3, "visual": "Demo the skill", "action": "Slow motion if needed"},
                {"scene": 4, "visual": "Share the tip", "action": "Add value"},
                {"scene": 5, "visual": "CTA", "action": "Encourage practice"}
            ],
            "cta_options": ["Save for later", "Tag someone who needs this", "Show me yours!"],
            "best_niches": ["Tech", "Fitness", "Food", "Art"],
            "estimated_engagement": "High"
        },
        
        # List Category
        {
            "category": "List",
            "title": "The Rapid Fire Tips Framework",
            "description": "Share 5-7 quick tips that provide massive value fast.",
            "featured": False,
            "preview_hook": "7 [TOPIC] tips in 30 seconds. Don't blink.",
            "full_script": {
                "hook": {"text": "7 [TOPIC] tips. 30 seconds. Don't blink. Let's go!", "duration": "0-3s"},
                "tips": {"text": "1. [TIP]\n2. [TIP]\n3. [TIP]\n4. [TIP]\n5. [TIP]\n6. [TIP]\n7. [TIP]", "duration": "3-26s"},
                "cta": {"text": "Which one are you trying first? Comment the number!", "duration": "26-30s"}
            },
            "scene_breakdown": [
                {"scene": 1, "visual": "High energy open", "action": "Set the pace"},
                {"scene": 2, "visual": "Rapid text + demo", "action": "Keep it moving"},
                {"scene": 3, "visual": "Continue momentum", "action": "No pauses"},
                {"scene": 4, "visual": "Land strong", "action": "Memorable finish"},
                {"scene": 5, "visual": "CTA", "action": "Get interaction"}
            ],
            "cta_options": ["Comment your favorite", "Save this list", "Which did you not know?"],
            "best_niches": ["Any", "Works universally"],
            "estimated_engagement": "High"
        }
    ]
    
    for framework in frameworks_data:
        framework["id"] = str(uuid.uuid4())
        framework["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.blueprint_frameworks.insert_many(frameworks_data)
    return len(frameworks_data)


async def _seed_story_ideas():
    """Seed kids story ideas database"""
    existing = await db.blueprint_story_ideas.count_documents({})
    if existing > 0:
        return 0
    
    story_ideas_data = [
        # Adventure Genre
        {
            "genre": "Adventure",
            "age_group": "4-6",
            "title": "The Rainbow Bridge Kingdom",
            "brief_synopsis": "A curious bunny discovers a hidden rainbow bridge leading to a kingdom in the clouds.",
            "featured": True,
            "full_synopsis": "Bella the bunny finds a shimmering rainbow after a spring rain. When she hops onto it, she discovers it's actually a bridge to a magical kingdom in the clouds! There, she meets cloud puppies, star fish, and a kind moon queen who needs help finding her lost crown before nightfall.",
            "characters": [
                {"name": "Bella", "type": "Protagonist", "description": "A curious white bunny with big floppy ears"},
                {"name": "Moon Queen Celeste", "type": "Guide", "description": "A gentle queen made of moonlight"},
                {"name": "Fluffy", "type": "Sidekick", "description": "A playful cloud puppy"}
            ],
            "moral": "Curiosity leads to wonderful discoveries",
            "scene_outlines": [
                {"scene": 1, "title": "The Rainbow Appears", "description": "Bella sees a rainbow and decides to follow it"},
                {"scene": 2, "title": "The Bridge", "description": "She discovers the rainbow is a bridge"},
                {"scene": 3, "title": "Cloud Kingdom", "description": "Bella enters the magical cloud kingdom"},
                {"scene": 4, "title": "Meeting the Queen", "description": "Moon Queen asks for help finding her crown"},
                {"scene": 5, "title": "The Search", "description": "Bella and Fluffy search together"},
                {"scene": 6, "title": "Found!", "description": "They find the crown with teamwork"},
                {"scene": 7, "title": "Celebration", "description": "The kingdom celebrates"},
                {"scene": 8, "title": "Home", "description": "Bella returns home with a new friend"}
            ]
        },
        
        {
            "genre": "Adventure",
            "age_group": "6-8",
            "title": "The Dinosaur Time Express",
            "brief_synopsis": "Two siblings find a toy train that actually travels back in time to meet friendly dinosaurs.",
            "featured": True,
            "full_synopsis": "Maya and her brother Kai find an old toy train in grandma's attic. When they say 'choo choo' together, it grows big and takes them back to dinosaur times! They befriend a baby T-Rex who's lost and help him find his family while avoiding a grumpy volcano.",
            "characters": [
                {"name": "Maya", "type": "Protagonist", "description": "A brave 7-year-old girl who loves science"},
                {"name": "Kai", "type": "Protagonist", "description": "Maya's curious 5-year-old brother"},
                {"name": "Rex Jr.", "type": "Friend", "description": "A friendly baby T-Rex who's lost"},
                {"name": "Mama Rex", "type": "Supporting", "description": "Rex Jr.'s worried mother"}
            ],
            "moral": "Family always finds a way back to each other",
            "scene_outlines": [
                {"scene": 1, "title": "The Attic Discovery", "description": "Kids find the magical train"},
                {"scene": 2, "title": "Time Travel!", "description": "The train takes them to dinosaur times"},
                {"scene": 3, "title": "A New Friend", "description": "They meet crying Rex Jr."},
                {"scene": 4, "title": "The Journey Begins", "description": "They decide to help Rex find home"},
                {"scene": 5, "title": "Volcano Valley", "description": "They must cross a dangerous area"},
                {"scene": 6, "title": "Clever Plan", "description": "Maya uses science to solve a problem"},
                {"scene": 7, "title": "Reunion", "description": "Rex Jr. finds his family"},
                {"scene": 8, "title": "Back Home", "description": "Kids return with amazing memories"}
            ]
        },
        
        # Friendship Genre
        {
            "genre": "Friendship",
            "age_group": "3-5",
            "title": "The Shy Star Who Learned to Shine",
            "brief_synopsis": "A little star is too shy to shine bright until she makes her first friend.",
            "featured": True,
            "full_synopsis": "Twinkle is a small star who's afraid to shine because she thinks she's not bright enough. She hides behind bigger stars until a lonely comet named Zoom flies by looking for a friend. Together, they discover that friendship makes everyone shine brighter.",
            "characters": [
                {"name": "Twinkle", "type": "Protagonist", "description": "A small, shy star who dims her light"},
                {"name": "Zoom", "type": "Best Friend", "description": "A friendly comet who's searching for friends"},
                {"name": "Big Star Boris", "type": "Supporting", "description": "A kind giant star who encourages Twinkle"}
            ],
            "moral": "True friends help you shine your brightest",
            "scene_outlines": [
                {"scene": 1, "title": "Hiding", "description": "Twinkle hides behind bigger stars"},
                {"scene": 2, "title": "Zoom Arrives", "description": "A lonely comet flies through the sky"},
                {"scene": 3, "title": "First Hello", "description": "Zoom notices Twinkle and says hi"},
                {"scene": 4, "title": "New Friends", "description": "They start playing together"},
                {"scene": 5, "title": "The Dark Night", "description": "The sky needs more light"},
                {"scene": 6, "title": "Zoom Encourages", "description": "Zoom believes in Twinkle"},
                {"scene": 7, "title": "Shining Bright", "description": "Twinkle shines her brightest ever"},
                {"scene": 8, "title": "Forever Friends", "description": "They light up the sky together"}
            ]
        },
        
        {
            "genre": "Friendship",
            "age_group": "4-6",
            "title": "The Grumpy Dragon's Birthday Party",
            "brief_synopsis": "A dragon who thinks he has no friends discovers everyone has been planning a surprise party.",
            "featured": False,
            "full_synopsis": "Grumbles the dragon wakes up on his birthday feeling sad because he thinks everyone forgot. His fire isn't even working well because he's so gloomy. Little does he know, all the forest animals are preparing the biggest surprise party ever!",
            "characters": [
                {"name": "Grumbles", "type": "Protagonist", "description": "A purple dragon who looks scary but is actually sweet"},
                {"name": "Pepper", "type": "Best Friend", "description": "A tiny mouse who organized the party"},
                {"name": "Forest Friends", "type": "Supporting", "description": "Rabbits, birds, and squirrels helping"}
            ],
            "moral": "You have more friends than you realize",
            "scene_outlines": [
                {"scene": 1, "title": "Sad Morning", "description": "Grumbles wakes up alone on his birthday"},
                {"scene": 2, "title": "Empty Forest", "description": "No one seems to be around"},
                {"scene": 3, "title": "Secret Planning", "description": "Meanwhile, animals prepare the party"},
                {"scene": 4, "title": "Grumbles Searches", "description": "He looks for his friends"},
                {"scene": 5, "title": "Almost Gives Up", "description": "He sits sadly by the lake"},
                {"scene": 6, "title": "SURPRISE!", "description": "Everyone jumps out"},
                {"scene": 7, "title": "Best Party Ever", "description": "Dancing, cake, and fun"},
                {"scene": 8, "title": "Grateful Heart", "description": "Grumbles realizes how loved he is"}
            ]
        },
        
        # Educational Genre
        {
            "genre": "Educational",
            "age_group": "5-7",
            "title": "The Water Drop's Big Journey",
            "brief_synopsis": "Follow Drip the water drop as she travels through the water cycle and makes new friends.",
            "featured": True,
            "full_synopsis": "Drip is a water drop living in the ocean. She dreams of seeing the world. When the sun warms her up, she rises into the sky, becomes part of a cloud, falls as rain, flows through a river, and finally returns to the ocean - making friends at every stop!",
            "characters": [
                {"name": "Drip", "type": "Protagonist", "description": "A curious water drop with big dreams"},
                {"name": "Sunny", "type": "Guide", "description": "A warm sun who helps Drip evaporate"},
                {"name": "Cloud Carl", "type": "Friend", "description": "A fluffy cloud who becomes Drip's ride"}
            ],
            "moral": "Every journey brings you back home, but you're never the same",
            "scene_outlines": [
                {"scene": 1, "title": "Ocean Home", "description": "Drip lives in the vast ocean"},
                {"scene": 2, "title": "Sunny's Warmth", "description": "The sun warms Drip up"},
                {"scene": 3, "title": "Rising Up", "description": "Drip evaporates into the sky"},
                {"scene": 4, "title": "Cloud Life", "description": "Drip joins Cloud Carl"},
                {"scene": 5, "title": "Rain Time", "description": "She falls as rain on a mountain"},
                {"scene": 6, "title": "River Adventure", "description": "Flowing through streams and rivers"},
                {"scene": 7, "title": "Home Again", "description": "Drip returns to the ocean"},
                {"scene": 8, "title": "Story Time", "description": "She shares her adventures"}
            ]
        },
        
        # Fantasy Genre
        {
            "genre": "Fantasy",
            "age_group": "4-6",
            "title": "The Magical Pajama Kingdom",
            "brief_synopsis": "When kids put on their pajamas at night, they secretly travel to a magical kingdom.",
            "featured": True,
            "full_synopsis": "Every night when Zara puts on her special star pajamas, she's transported to the Pajama Kingdom where teddy bears rule, pillows are clouds you can bounce on, and the lullaby river sings sweet songs. Tonight, she must help save the kingdom from the Snore Monster!",
            "characters": [
                {"name": "Zara", "type": "Protagonist", "description": "A brave girl in star pajamas"},
                {"name": "King Teddy", "type": "Guide", "description": "A wise teddy bear king"},
                {"name": "Snore Monster", "type": "Antagonist", "description": "A sleepy monster who just wants a friend"}
            ],
            "moral": "Even things that seem scary might just need kindness",
            "scene_outlines": [
                {"scene": 1, "title": "Bedtime", "description": "Zara puts on her magical pajamas"},
                {"scene": 2, "title": "Transportation", "description": "She arrives in Pajama Kingdom"},
                {"scene": 3, "title": "Kingdom Tour", "description": "King Teddy shows her around"},
                {"scene": 4, "title": "The Problem", "description": "Snore Monster is causing trouble"},
                {"scene": 5, "title": "The Approach", "description": "Zara decides to talk to it"},
                {"scene": 6, "title": "Understanding", "description": "Snore Monster is just lonely"},
                {"scene": 7, "title": "New Friend", "description": "Everyone becomes friends"},
                {"scene": 8, "title": "Sweet Dreams", "description": "Zara wakes up happy"}
            ]
        },
        
        # Nature Genre
        {
            "genre": "Nature",
            "age_group": "3-5",
            "title": "The Little Seed's Dream",
            "brief_synopsis": "A tiny seed dreams of becoming a beautiful flower and learns patience along the way.",
            "featured": False,
            "full_synopsis": "Sunny the seed is buried in the dark soil and feels scared. She doesn't understand why she can't see the sun. With help from Wally the worm and Rachel the rain, she learns that growing takes time - and when she finally blooms, it's more beautiful than she ever imagined.",
            "characters": [
                {"name": "Sunny", "type": "Protagonist", "description": "A small sunflower seed full of dreams"},
                {"name": "Wally", "type": "Helper", "description": "A friendly worm who loosens the soil"},
                {"name": "Rachel", "type": "Helper", "description": "A gentle raindrop who brings water"}
            ],
            "moral": "Good things come to those who wait and keep trying",
            "scene_outlines": [
                {"scene": 1, "title": "Planted", "description": "Sunny gets planted in the soil"},
                {"scene": 2, "title": "The Dark", "description": "It's dark and scary underground"},
                {"scene": 3, "title": "Meeting Wally", "description": "A worm explains the process"},
                {"scene": 4, "title": "Rain Comes", "description": "Rachel the raindrop helps"},
                {"scene": 5, "title": "First Sprout", "description": "Sunny pushes through the soil"},
                {"scene": 6, "title": "Growing Tall", "description": "She grows bigger each day"},
                {"scene": 7, "title": "Blooming", "description": "Sunny becomes a beautiful sunflower"},
                {"scene": 8, "title": "Making Seeds", "description": "Now she has seeds of her own"}
            ]
        },
        
        # Kindness Genre
        {
            "genre": "Kindness",
            "age_group": "4-6",
            "title": "The Sharing Rainbow",
            "brief_synopsis": "When animals argue over who owns the rainbow, they learn it belongs to everyone.",
            "featured": True,
            "full_synopsis": "After a beautiful rain, a rainbow appears and all the forest animals claim it as theirs. The birds say it's theirs because they can fly to it. The fish say it touches the water. The deer say it's in their forest. Wise Owl helps them understand that the best things in life are meant to be shared.",
            "characters": [
                {"name": "Wise Owl", "type": "Guide", "description": "An elderly owl who teaches the lesson"},
                {"name": "Robin", "type": "Supporting", "description": "A bird who claims the sky"},
                {"name": "Goldie", "type": "Supporting", "description": "A fish who claims the water"},
                {"name": "Daisy Deer", "type": "Supporting", "description": "A deer who claims the forest"}
            ],
            "moral": "The best things in life are better when shared",
            "scene_outlines": [
                {"scene": 1, "title": "Rainbow Appears", "description": "A beautiful rainbow forms"},
                {"scene": 2, "title": "Mine!", "description": "Robin claims it belongs to birds"},
                {"scene": 3, "title": "No, Mine!", "description": "Goldie says it's the fish's"},
                {"scene": 4, "title": "Arguments", "description": "Everyone is upset"},
                {"scene": 5, "title": "Owl Arrives", "description": "Wise Owl hears the commotion"},
                {"scene": 6, "title": "The Lesson", "description": "Owl explains sharing"},
                {"scene": 7, "title": "Understanding", "description": "Animals realize the truth"},
                {"scene": 8, "title": "Together", "description": "They enjoy the rainbow together"}
            ]
        }
    ]
    
    for idea in story_ideas_data:
        idea["id"] = str(uuid.uuid4())
        idea["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.blueprint_story_ideas.insert_many(story_ideas_data)
    return len(story_ideas_data)
