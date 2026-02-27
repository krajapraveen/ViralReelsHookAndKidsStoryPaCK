"""
Coloring Book Module - Backend API
Zero-cost architecture: All image processing happens client-side
Backend only handles: story data, credits, and export logging
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, log_exception
from security import limiter

router = APIRouter(prefix="/coloring-book", tags=["Coloring Book"])


# =============================================================================
# PRICING CONFIGURATION - NEW STRUCTURE (AS SPECIFIED BY USER)
# =============================================================================

# Story Mode Pricing - Push 20 pages as default (Most Popular)
STORY_MODE_PRICING = {
    "5_pages": {"pages": 5, "credits": 10, "label": "5 Pages"},
    "10_pages": {"pages": 10, "credits": 18, "label": "10 Pages", "savings": "10%"},
    "20_pages": {"pages": 20, "credits": 32, "label": "20 Pages", "badge": "MOST POPULAR", "default": True, "savings": "20%"},
    "30_pages": {"pages": 30, "credits": 45, "label": "30 Pages", "badge": "BEST VALUE", "savings": "25%"},
}

# Photo Mode Pricing - Batch discount increases usage
PHOTO_MODE_PRICING = {
    "1_image": {"images": 1, "credits": 5, "label": "1 Image"},
    "5_images": {"images": 5, "credits": 20, "label": "5 Images", "savings": "20%", "badge": "POPULAR"},
    "10_images": {"images": 10, "credits": 35, "label": "10 Images", "badge": "BEST VALUE", "savings": "30%"},
}

# Add-ons - High Profit, Low Cost
ADDONS = {
    "activity_pages": {"id": "activity_pages", "name": "Activity Pages", "description": "Puzzles, mazes & fun activities", "credits": 3, "icon": "puzzle"},
    "personalized_cover": {"id": "personalized_cover", "name": "Personalized Cover", "description": "Custom cover with child's name", "credits": 4, "icon": "user", "default": True},
    "dedication_page": {"id": "dedication_page", "name": "Dedication Page", "description": "Add a personal message", "credits": 2, "icon": "heart"},
    "premium_templates": {"id": "premium_templates", "name": "Premium Cover Templates", "description": "Beautiful designer covers", "credits": 5, "icon": "crown", "pro_only": True},
    "hd_print": {"id": "hd_print", "name": "HD Print Version", "description": "High-resolution 300 DPI PDF", "credits": 5, "icon": "printer"},
    "commercial_license": {"id": "commercial_license", "name": "Commercial License", "description": "Use for commercial purposes", "credits": 10, "icon": "briefcase"}
}

# Subscription Benefits
SUBSCRIPTION_BENEFITS = {
    "free": {"discount": 0, "preview_pages": 2, "watermark": True, "premium_templates": False, "priority_generation": False},
    "creator": {"discount": 20, "preview_pages": 3, "watermark": False, "premium_templates": False, "priority_generation": False},
    "pro": {"discount": 30, "preview_pages": 5, "watermark": False, "premium_templates": True, "priority_generation": True},
    "studio": {"discount": 40, "preview_pages": -1, "watermark": False, "premium_templates": True, "priority_generation": True, "commercial_included": True}
}

# Legacy pricing (keeping for backward compatibility with old frontend)
COLORING_BOOK_PRICING = {
    "BASE_EXPORT": 5,
    "ACTIVITY_PAGES": 2,
    "PERSONALIZED_COVER": 1,
    "PER_EXTRA_PAGE": 0.5,
}

# Regional pricing for subscriptions (for future integration)
REGIONAL_PRICING = {
    "INR": {
        "weekly": {"price": 99, "exports": 5, "worksheets": 5},
        "monthly": {"price": 299, "exports": 25, "worksheets": -1, "recommended": True},  # -1 = unlimited
        "quarterly": {"price": 699, "exports": 100, "worksheets": -1, "best_value": True},
        "single_book": {"price": 149}
    },
    "USD": {
        "weekly": {"price": 4.99, "exports": 5, "worksheets": 5},
        "monthly": {"price": 9.99, "exports": 25, "worksheets": -1, "recommended": True},
        "quarterly": {"price": 24.99, "exports": 100, "worksheets": -1, "best_value": True},
        "single_book": {"price": 4.99}
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class ExportConfig(BaseModel):
    pageCount: int = Field(default=10, ge=8, le=12)
    includeActivityPages: bool = Field(default=False)
    personalizedCover: bool = Field(default=False)
    childName: Optional[str] = Field(default=None, max_length=100)
    dedication: Optional[str] = Field(default=None, max_length=300)
    paperSize: str = Field(default="A4")  # A4 or Letter


class ExportRequest(BaseModel):
    storyId: str
    config: ExportConfig
    mode: str = Field(default="placeholder")  # "placeholder" or "photo"
    processedSceneCount: int = Field(default=0, description="Number of scenes with processed images")


class ExportLogEntry(BaseModel):
    storyId: str
    mode: str
    pageCount: int
    includeActivityPages: bool
    personalizedCover: bool
    creditsCharged: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def calculate_export_cost(config: ExportConfig) -> int:
    """Calculate credit cost for coloring book export"""
    cost = COLORING_BOOK_PRICING["BASE_EXPORT"]
    
    if config.includeActivityPages:
        cost += COLORING_BOOK_PRICING["ACTIVITY_PAGES"]
    
    if config.personalizedCover:
        cost += COLORING_BOOK_PRICING["PERSONALIZED_COVER"]
    
    # Extra pages beyond 10
    if config.pageCount > 10:
        cost += int((config.pageCount - 10) * COLORING_BOOK_PRICING["PER_EXTRA_PAGE"])
    
    return cost


async def deduct_credits_atomic(user_id: str, amount: int, ref_type: str, ref_id: str) -> bool:
    """Atomically deduct credits from user's balance with ledger entry"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_balance = user.get("credits", 0)
    if current_balance < amount:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Need {amount}, have {current_balance}"
        )
    
    # Deduct credits
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Failed to deduct credits")
    
    # Log to ledger
    ledger_entry = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",  # Direct capture for completed exports
        "amount": amount,
        "refType": ref_type,
        "refId": ref_id,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.credit_ledger.insert_one(ledger_entry)
    
    logger.info(f"Deducted {amount} credits from user {user_id} for {ref_type}:{ref_id}")
    return True


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/pricing")
async def get_coloring_book_pricing(user: dict = Depends(get_current_user)):
    """Get complete pricing configuration - NEW 5-STEP WIZARD STRUCTURE"""
    user_plan = user.get("plan", "free").lower()
    benefits = SUBSCRIPTION_BENEFITS.get(user_plan, SUBSCRIPTION_BENEFITS["free"])
    
    # Mark pro-only addons with lock status
    addons_with_access = {}
    for addon_id, addon in ADDONS.items():
        is_locked = addon.get("pro_only", False) and user_plan not in ["pro", "studio"]
        addons_with_access[addon_id] = {
            **addon,
            "locked": is_locked,
            "unlock_plan": "pro" if addon.get("pro_only") else None
        }
    
    return {
        "success": True,
        "storyMode": STORY_MODE_PRICING,
        "photoMode": PHOTO_MODE_PRICING,
        "addons": addons_with_access,
        "subscription": {
            "plan": user_plan,
            "benefits": benefits
        },
        "defaults": {
            "storyPageOption": "20_pages",
            "photoImageOption": "5_images",
            "preSelectedAddons": ["personalized_cover"]
        },
        "psychology": {
            "bestValue": "20 Pages + Personalized Cover",
            "savings": "Save 15%",
            "expectedAOV": 39
        },
        # Legacy fields for backward compatibility
        "creditPricing": COLORING_BOOK_PRICING,
        "freePreview": {
            "pages": benefits["preview_pages"],
            "hasWatermark": benefits["watermark"]
        },
        "note": "Credits deducted only after successful generation"
    }


@router.get("/stories")
async def get_user_stories(
    user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's stories available for coloring book generation"""
    user_id = user["id"]
    
    # Fetch stories from the generations collection
    stories = await db.generations.find(
        {"userId": user_id, "type": "story"},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    # Also check genstudio_jobs for story generations
    story_jobs = await db.genstudio_jobs.find(
        {"userId": user_id, "jobType": "STORY_GENERATION", "status": "SUCCEEDED"},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    # Combine and format
    formatted_stories = []
    
    for story in stories:
        formatted_stories.append({
            "id": story.get("id"),
            "title": story.get("result", {}).get("title", "Untitled Story"),
            "synopsis": story.get("result", {}).get("synopsis", ""),
            "genre": story.get("result", {}).get("genre", ""),
            "scenes": story.get("result", {}).get("scenes", []),
            "moral": story.get("result", {}).get("moral", ""),
            "createdAt": story.get("createdAt"),
            "source": "generations"
        })
    
    for job in story_jobs:
        result = job.get("resultJson", {})
        if result:
            formatted_stories.append({
                "id": job.get("id"),
                "title": result.get("title", "Untitled Story"),
                "synopsis": result.get("synopsis", ""),
                "genre": result.get("genre", ""),
                "scenes": result.get("scenes", []),
                "moral": result.get("moral", ""),
                "createdAt": job.get("createdAt"),
                "source": "genstudio_jobs"
            })
    
    return {
        "stories": formatted_stories,
        "total": len(formatted_stories)
    }


@router.get("/stories/{story_id}")
async def get_story_for_coloring(story_id: str, user: dict = Depends(get_current_user)):
    """Get a specific story with scenes for coloring book generation"""
    user_id = user["id"]
    
    # Try generations collection first
    story = await db.generations.find_one(
        {"id": story_id, "userId": user_id, "type": "story"},
        {"_id": 0}
    )
    
    if story:
        result = story.get("result", {})
        return {
            "id": story_id,
            "title": result.get("title", "Untitled Story"),
            "synopsis": result.get("synopsis", ""),
            "genre": result.get("genre", ""),
            "scenes": result.get("scenes", []),
            "moral": result.get("moral", ""),
            "characters": result.get("characters", []),
            "ending": result.get("ending", ""),
            "createdAt": story.get("createdAt")
        }
    
    # Try genstudio_jobs
    job = await db.genstudio_jobs.find_one(
        {"id": story_id, "userId": user_id, "jobType": "STORY_GENERATION", "status": "SUCCEEDED"},
        {"_id": 0}
    )
    
    if job:
        result = job.get("resultJson", {})
        return {
            "id": story_id,
            "title": result.get("title", "Untitled Story"),
            "synopsis": result.get("synopsis", ""),
            "genre": result.get("genre", ""),
            "scenes": result.get("scenes", []),
            "moral": result.get("moral", ""),
            "characters": result.get("characters", []),
            "ending": result.get("ending", ""),
            "createdAt": job.get("createdAt")
        }
    
    raise HTTPException(status_code=404, detail="Story not found")


@router.post("/calculate-cost")
async def calculate_cost(config: ExportConfig, user: dict = Depends(get_current_user)):
    """Calculate credit cost for export without charging"""
    cost = calculate_export_cost(config)
    user_balance = user.get("credits", 0)
    
    return {
        "cost": cost,
        "breakdown": {
            "base": COLORING_BOOK_PRICING["BASE_EXPORT"],
            "activityPages": COLORING_BOOK_PRICING["ACTIVITY_PAGES"] if config.includeActivityPages else 0,
            "personalizedCover": COLORING_BOOK_PRICING["PERSONALIZED_COVER"] if config.personalizedCover else 0,
            "extraPages": int((config.pageCount - 10) * COLORING_BOOK_PRICING["PER_EXTRA_PAGE"]) if config.pageCount > 10 else 0
        },
        "userBalance": user_balance,
        "canAfford": user_balance >= cost
    }


@router.post("/export")
@limiter.limit("10/minute")
async def log_export_and_charge(
    request: Request,
    data: ExportRequest,
    user: dict = Depends(get_current_user)
):
    """
    Log successful export and charge credits.
    Called AFTER client-side PDF generation succeeds.
    
    This endpoint:
    1. Validates the export request
    2. Deducts credits atomically
    3. Logs the export for analytics
    
    Note: The actual PDF generation happens client-side. This is just for
    credit management and analytics.
    """
    user_id = user["id"]
    
    # Calculate cost
    cost = calculate_export_cost(data.config)
    
    # Generate export ID for idempotency
    export_id = str(uuid.uuid4())
    
    try:
        # Deduct credits
        await deduct_credits_atomic(user_id, cost, "COLORING_BOOK_EXPORT", export_id)
        
        # Log export
        export_log = {
            "id": export_id,
            "userId": user_id,
            "storyId": data.storyId,
            "mode": data.mode,
            "pageCount": data.config.pageCount,
            "includeActivityPages": data.config.includeActivityPages,
            "personalizedCover": data.config.personalizedCover,
            "childName": data.config.childName,
            "paperSize": data.config.paperSize,
            "processedSceneCount": data.processedSceneCount,
            "creditsCharged": cost,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.coloring_book_exports.insert_one(export_log)
        
        logger.info(f"Coloring book export logged: {export_id} for user {user_id}")
        
        return {
            "success": True,
            "exportId": export_id,
            "creditsCharged": cost,
            "message": "Export logged and credits charged successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export logging failed: {e}")
        await log_exception(
            functionality="coloring_book_export",
            error_type="EXPORT_LOG_FAILED",
            error_message=str(e),
            user_id=user_id,
            severity="ERROR"
        )
        raise HTTPException(status_code=500, detail="Export logging failed")


@router.get("/export-history")
async def get_export_history(
    user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's coloring book export history"""
    user_id = user["id"]
    
    exports = await db.coloring_book_exports.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.coloring_book_exports.count_documents({"userId": user_id})
    
    return {
        "exports": exports,
        "total": total
    }


@router.get("/templates")
async def get_activity_templates():
    """Get available activity page templates (SVG-based, free)"""
    templates = [
        {
            "id": "match_characters",
            "name": "Match the Characters",
            "description": "Match character names to their pictures",
            "type": "matching"
        },
        {
            "id": "find_hidden",
            "name": "Find Hidden Items",
            "description": "Circle hidden items in the scene",
            "type": "hidden_objects"
        },
        {
            "id": "vocabulary",
            "name": "Story Vocabulary",
            "description": "Learn new words from the story",
            "type": "vocabulary"
        },
        {
            "id": "maze",
            "name": "Story Maze",
            "description": "Help the character find their way",
            "type": "maze"
        },
        {
            "id": "word_search",
            "name": "Word Search",
            "description": "Find story words in the puzzle",
            "type": "word_search"
        },
        {
            "id": "certificate",
            "name": "Completion Certificate",
            "description": "I finished my coloring book!",
            "type": "certificate"
        }
    ]
    
    return {"templates": templates}


@router.get("/svg-assets")
async def get_svg_assets():
    """
    Get free SVG assets for DIY placeholder mode.
    These are simple, original shapes that can be used as guides.
    """
    assets = {
        "shapes": [
            {"id": "star", "path": "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"},
            {"id": "cloud", "path": "M18.5 11c.88 0 1.73.18 2.5.5V11a6 6 0 00-6-6c-2.97 0-5.46 2.17-5.92 5.02A4.5 4.5 0 005 14.5 4.5 4.5 0 009.5 19h9a4.5 4.5 0 000-9h-.5c0 .34-.04.67-.1 1h.6z"},
            {"id": "tree", "path": "M12 2L4 14h4v8h8v-8h4L12 2z"},
            {"id": "sun", "path": "M12 7a5 5 0 100 10 5 5 0 000-10zM12 1v3M12 20v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M1 12h3M20 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"},
            {"id": "heart", "path": "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"},
            {"id": "moon", "path": "M12 3a9 9 0 109 9c0-.46-.04-.92-.1-1.36a5.389 5.389 0 01-4.4 2.26 5.403 5.403 0 01-3.14-9.8c-.44-.06-.9-.1-1.36-.1z"},
            {"id": "house", "path": "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"},
            {"id": "flower", "path": "M12 15a3 3 0 100-6 3 3 0 000 6zM12 4a2.5 2.5 0 000 5 2.5 2.5 0 000-5zM7.5 7a2.5 2.5 0 100 5M16.5 7a2.5 2.5 0 000 5M7.5 12a2.5 2.5 0 100 5M16.5 12a2.5 2.5 0 000 5M12 16a2.5 2.5 0 000 5"}
        ],
        "borders": [
            {"id": "simple_border", "description": "Simple rectangular border"},
            {"id": "wavy_border", "description": "Wavy decorative border"},
            {"id": "dotted_border", "description": "Dotted frame border"}
        ]
    }
    
    return assets
