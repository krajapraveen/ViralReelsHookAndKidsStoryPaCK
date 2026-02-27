"""
Coloring Book Creator - Complete Rebuild
5-Step Wizard Flow with Exact Pricing Structure
Revenue Optimized - Zero Extra Infra
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/coloring-book", tags=["Coloring Book"])


# =============================================================================
# EXACT PRICING CONFIGURATION (AS SPECIFIED)
# =============================================================================

# Story Mode Pricing - Push 20 pages as default (Most Popular)
STORY_MODE_PRICING = {
    "5_pages": {
        "pages": 5, 
        "credits": 10, 
        "label": "5 Pages"
    },
    "10_pages": {
        "pages": 10, 
        "credits": 18, 
        "label": "10 Pages", 
        "savings": "10%"
    },
    "20_pages": {
        "pages": 20, 
        "credits": 32, 
        "label": "20 Pages", 
        "badge": "MOST POPULAR", 
        "default": True, 
        "savings": "20%"
    },
    "30_pages": {
        "pages": 30, 
        "credits": 45, 
        "label": "30 Pages", 
        "badge": "BEST VALUE", 
        "savings": "25%"
    },
}

# Photo Mode Pricing - Batch discount increases usage
PHOTO_MODE_PRICING = {
    "1_image": {
        "images": 1, 
        "credits": 5, 
        "label": "1 Image"
    },
    "5_images": {
        "images": 5, 
        "credits": 20, 
        "label": "5 Images", 
        "savings": "20%", 
        "badge": "POPULAR"
    },
    "10_images": {
        "images": 10, 
        "credits": 35, 
        "label": "10 Images", 
        "badge": "BEST VALUE", 
        "savings": "30%"
    },
}

# Add-ons - High Profit, Low Cost (Pure pricing logic, no AI cost increase)
ADDONS = {
    "activity_pages": {
        "id": "activity_pages",
        "name": "Activity Pages",
        "description": "Puzzles, mazes & fun activities",
        "credits": 3,
        "icon": "puzzle",
        "pro_only": False
    },
    "personalized_cover": {
        "id": "personalized_cover",
        "name": "Personalized Cover",
        "description": "Custom cover with child's name",
        "credits": 4,
        "icon": "user",
        "default": True,  # Pre-selected for revenue optimization
        "pro_only": False
    },
    "dedication_page": {
        "id": "dedication_page",
        "name": "Dedication Page",
        "description": "Add a personal message",
        "credits": 2,
        "icon": "heart",
        "pro_only": False
    },
    "premium_templates": {
        "id": "premium_templates",
        "name": "Premium Cover Templates",
        "description": "Beautiful designer covers",
        "credits": 5,
        "icon": "crown",
        "pro_only": True  # Pro only
    },
    "hd_print": {
        "id": "hd_print",
        "name": "HD Print Version",
        "description": "High-resolution 300 DPI PDF",
        "credits": 5,
        "icon": "printer",
        "pro_only": False
    },
    "commercial_license": {
        "id": "commercial_license",
        "name": "Commercial License",
        "description": "Use for commercial purposes",
        "credits": 10,
        "icon": "briefcase",
        "pro_only": False
    }
}

# Subscription Benefits - Exact as specified
SUBSCRIPTION_BENEFITS = {
    "free": {
        "discount": 0,
        "preview_pages": 2,
        "watermark": True,
        "premium_templates": False,
        "priority_generation": False,
        "commercial_included": False,
        "unlimited_previews": False
    },
    "creator": {
        "discount": 20,  # 20% discount
        "preview_pages": 3,
        "watermark": False,
        "premium_templates": False,
        "priority_generation": False,
        "commercial_included": False,
        "unlimited_previews": False
    },
    "pro": {
        "discount": 30,  # 30% discount
        "preview_pages": 5,
        "watermark": False,
        "premium_templates": True,  # Premium covers unlocked
        "priority_generation": True,  # Priority generation
        "commercial_included": False,
        "unlimited_previews": False
    },
    "studio": {
        "discount": 40,  # 40% discount
        "preview_pages": -1,  # Unlimited previews
        "watermark": False,
        "premium_templates": True,
        "priority_generation": True,
        "commercial_included": True,  # Commercial rights included
        "unlimited_previews": True
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class StoryModeData(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ageGroup: str = Field(default="4-6")
    description: str = Field(..., min_length=10, max_length=2000)
    illustrationStyle: str = Field(default="cartoon")
    pageCount: str = Field(default="20")


class PhotoModeData(BaseModel):
    outlineStrength: int = Field(default=50, ge=0, le=100)
    removeBackground: bool = Field(default=False)


class CustomizeData(BaseModel):
    mode: str = Field(..., pattern="^(story|photo)$")
    pageOption: Optional[str] = None
    imageOption: Optional[str] = None
    paperSize: str = Field(default="A4")
    addons: List[str] = Field(default=[])
    childName: Optional[str] = Field(default=None, max_length=100)
    dedication: Optional[str] = Field(default=None, max_length=500)


class GenerateRequest(BaseModel):
    sessionId: str
    mode: str
    storyData: Optional[StoryModeData] = None
    photoData: Optional[PhotoModeData] = None
    customize: CustomizeData


class AnalyticsEvent(BaseModel):
    sessionId: str
    step: int
    action: str
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_cost(mode: str, option: str, addons: List[str], user_plan: str) -> Dict[str, Any]:
    """
    Calculate total cost with breakdown
    Revenue Psychology: Default 20 pages + Cover = 36 credits
    Expected AOV: 39 credits (with activity pages)
    """
    # Base cost
    if mode == "story":
        pricing = STORY_MODE_PRICING.get(option, STORY_MODE_PRICING["20_pages"])
        base_cost = pricing["credits"]
        base_label = pricing["label"]
    else:
        pricing = PHOTO_MODE_PRICING.get(option, PHOTO_MODE_PRICING["5_images"])
        base_cost = pricing["credits"]
        base_label = pricing["label"]
    
    # Add-on costs
    addon_costs = []
    addon_total = 0
    for addon_id in addons:
        addon = ADDONS.get(addon_id)
        if addon:
            # Skip pro-only addons for non-pro users
            if addon.get("pro_only") and user_plan not in ["pro", "studio"]:
                continue
            addon_costs.append({
                "id": addon_id,
                "name": addon["name"],
                "credits": addon["credits"]
            })
            addon_total += addon["credits"]
    
    # Apply subscription discount
    benefits = SUBSCRIPTION_BENEFITS.get(user_plan, SUBSCRIPTION_BENEFITS["free"])
    discount_percent = benefits["discount"]
    
    subtotal = base_cost + addon_total
    discount_amount = int(subtotal * discount_percent / 100)
    final_total = subtotal - discount_amount
    
    return {
        "base": {
            "label": base_label,
            "credits": base_cost
        },
        "addons": addon_costs,
        "addon_total": addon_total,
        "subtotal": subtotal,
        "discount": {
            "percent": discount_percent,
            "amount": discount_amount,
            "plan": user_plan
        },
        "total": final_total
    }


def get_preview_config(user_plan: str) -> Dict[str, Any]:
    """
    Get preview configuration based on plan
    Free users: 2 preview pages with watermark
    Paid users: More pages, no watermark
    """
    benefits = SUBSCRIPTION_BENEFITS.get(user_plan, SUBSCRIPTION_BENEFITS["free"])
    return {
        "pages": benefits["preview_pages"],
        "watermark": benefits["watermark"],
        "unlimited": benefits.get("unlimited_previews", False),
        "priority": benefits.get("priority_generation", False)
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """
    Get complete pricing configuration
    Revenue Psychology: Show savings, badges, and default to 20 pages
    """
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
            "storyPageOption": "20_pages",  # Push 20 pages as default
            "photoImageOption": "5_images",
            "preSelectedAddons": ["personalized_cover"]  # Pre-select cover for revenue
        },
        "psychology": {
            "bestValue": "20 Pages + Personalized Cover",
            "savings": "Save 15%",
            "expectedAOV": 39  # Expected average order value
        }
    }


@router.post("/calculate")
async def calculate_pricing(
    mode: str,
    option: str,
    addons: List[str] = Query(default=[]),
    user: dict = Depends(get_current_user)
):
    """
    Calculate live pricing - Must update live in UI
    Example: Base 32 + Cover 4 + Activity 3 = 39 credits
    """
    user_plan = user.get("plan", "free").lower()
    cost = calculate_cost(mode, option, addons, user_plan)
    
    return {
        "success": True,
        "breakdown": cost
    }


@router.get("/preview-config")
async def get_preview_configuration(user: dict = Depends(get_current_user)):
    """
    Get preview configuration
    Free users: 2 pages with watermark
    Paid users: More pages, no watermark
    """
    user_plan = user.get("plan", "free").lower()
    return {
        "success": True,
        "preview": get_preview_config(user_plan)
    }


@router.post("/session/start")
async def start_session(user: dict = Depends(get_current_user)):
    """
    Start a new coloring book creation session
    Track: Mode, Pages, Add-ons, Drop-off step
    """
    session_id = str(uuid.uuid4())
    
    session = {
        "id": session_id,
        "userId": user["id"],
        "status": "started",
        "currentStep": 1,
        "mode": None,
        "storyData": None,
        "photoData": None,
        "customize": None,
        "analytics": {
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "modeSelected": None,
            "pagesSelected": None,
            "addonsSelected": [],
            "dropOffStep": None,
            "completed": False
        },
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.coloring_sessions.insert_one(session)
    
    logger.info(f"Started coloring book session {session_id} for user {user['id']}")
    
    return {
        "success": True,
        "sessionId": session_id
    }


@router.post("/session/{session_id}/update")
async def update_session(
    session_id: str,
    step: int,
    data: Dict[str, Any],
    user: dict = Depends(get_current_user)
):
    """Update session progress for analytics tracking"""
    update_data = {
        "currentStep": step,
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    # Track analytics data
    if "mode" in data:
        update_data["analytics.modeSelected"] = data["mode"]
    if "pageOption" in data:
        update_data["analytics.pagesSelected"] = data["pageOption"]
    if "addons" in data:
        update_data["analytics.addonsSelected"] = data["addons"]
    
    update_data.update({k: v for k, v in data.items() if k not in ["mode", "pageOption", "addons"]})
    
    result = await db.coloring_sessions.update_one(
        {"id": session_id, "userId": user["id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True}


@router.post("/analytics/track")
async def track_analytics(event: AnalyticsEvent, user: dict = Depends(get_current_user)):
    """
    Track user analytics for drop-off analysis
    Admin Requirement: Mode, Pages, Add-ons, Drop-off step
    """
    analytics_entry = {
        "id": str(uuid.uuid4()),
        "sessionId": event.sessionId,
        "userId": user["id"],
        "step": event.step,
        "action": event.action,
        "data": event.data,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.coloring_analytics.insert_one(analytics_entry)
    
    # Update session drop-off tracking
    if event.action == "step_abandoned" or event.action == "page_exit":
        await db.coloring_sessions.update_one(
            {"id": event.sessionId},
            {"$set": {"analytics.dropOffStep": event.step}}
        )
    
    return {"success": True}


@router.post("/generate/preview")
async def generate_preview(
    request: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate preview pages (FREE)
    Free users: 2 pages with blur watermark
    Paid users: More pages, no watermark
    """
    user_plan = user.get("plan", "free").lower()
    preview_config = get_preview_config(user_plan)
    
    # Track analytics
    await db.coloring_analytics.insert_one({
        "id": str(uuid.uuid4()),
        "sessionId": request.sessionId,
        "userId": user["id"],
        "step": 4,
        "action": "preview_generated",
        "data": {
            "mode": request.mode,
            "plan": user_plan,
            "watermarked": preview_config["watermark"]
        },
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "preview": {
            "pages": preview_config["pages"],
            "watermark": preview_config["watermark"],
            "priority": preview_config["priority"],
            "message": "This is a preview. Final PDF will include all pages."
        }
    }


@router.post("/generate/full")
async def generate_full_book(
    request: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate full coloring book (charges credits)
    Expected AOV: 39 credits (20 pages + cover + activity)
    """
    user_id = user["id"]
    user_plan = user.get("plan", "free").lower()
    
    # Determine option from request
    mode = request.mode
    if mode == "story":
        page_count = request.storyData.pageCount if request.storyData else "20"
        option = f"{page_count}_pages"
    else:
        option = request.customize.imageOption or "5_images"
    
    addons = request.customize.addons
    
    # Calculate cost
    cost_breakdown = calculate_cost(mode, option, addons, user_plan)
    total_cost = cost_breakdown["total"]
    
    # Check credits
    user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    current_credits = user_data.get("credits", 0) if user_data else 0
    
    if current_credits < total_cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "required": total_cost,
                "available": current_credits,
                "message": f"Need {total_cost} credits. You have {current_credits}."
            }
        )
    
    # Deduct credits atomically
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": total_cost}},
        {"$inc": {"credits": -total_cost}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Failed to deduct credits")
    
    # Create generation record
    generation_id = str(uuid.uuid4())
    generation = {
        "id": generation_id,
        "sessionId": request.sessionId,
        "userId": user_id,
        "mode": mode,
        "option": option,
        "storyData": request.storyData.dict() if request.storyData else None,
        "photoData": request.photoData.dict() if request.photoData else None,
        "customize": request.customize.dict(),
        "costBreakdown": cost_breakdown,
        "creditsCharged": total_cost,
        "status": "completed",
        "downloadUrls": {
            "pdf": f"/api/coloring-book/download/{generation_id}/pdf",
            "hdPdf": f"/api/coloring-book/download/{generation_id}/hd-pdf",
            "shareLink": f"/share/coloring-book/{generation_id}"
        },
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.coloring_generations.insert_one(generation)
    
    # Log to credit ledger
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": total_cost,
        "refType": "COLORING_BOOK",
        "refId": generation_id,
        "status": "ACTIVE",
        "breakdown": cost_breakdown,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Update session as completed
    await db.coloring_sessions.update_one(
        {"id": request.sessionId},
        {
            "$set": {
                "status": "completed",
                "analytics.completed": True,
                "analytics.completedAt": datetime.now(timezone.utc).isoformat(),
                "analytics.totalCreditsSpent": total_cost,
                "generationId": generation_id
            }
        }
    )
    
    # Track analytics
    await db.coloring_analytics.insert_one({
        "id": str(uuid.uuid4()),
        "sessionId": request.sessionId,
        "userId": user_id,
        "step": 5,
        "action": "generation_completed",
        "data": {
            "mode": mode,
            "option": option,
            "addons": addons,
            "total_credits": total_cost,
            "plan": user_plan,
            "cost_breakdown": cost_breakdown
        },
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Generated coloring book {generation_id} for user {user_id}, charged {total_cost} credits")
    
    new_balance = current_credits - total_cost
    
    return {
        "success": True,
        "generationId": generation_id,
        "creditsCharged": total_cost,
        "newBalance": new_balance,
        "downloadUrls": generation["downloadUrls"],
        "message": "Coloring book generated successfully!"
    }


@router.post("/upsell/hd-upgrade")
async def upgrade_to_hd(
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Upsell: Upgrade to HD print quality (+5 credits)
    """
    user_id = user["id"]
    hd_cost = 5
    
    # Check generation exists and belongs to user
    generation = await db.coloring_generations.find_one(
        {"id": generation_id, "userId": user_id},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if generation.get("hdUpgraded"):
        raise HTTPException(status_code=400, detail="Already upgraded to HD")
    
    # Check credits
    user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    current_credits = user_data.get("credits", 0) if user_data else 0
    
    if current_credits < hd_cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "required": hd_cost,
                "available": current_credits
            }
        )
    
    # Deduct credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -hd_cost}}
    )
    
    # Update generation
    await db.coloring_generations.update_one(
        {"id": generation_id},
        {"$set": {"hdUpgraded": True, "hdUpgradedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log to ledger
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": hd_cost,
        "refType": "COLORING_BOOK_HD_UPGRADE",
        "refId": generation_id,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": "Upgraded to HD print quality",
        "creditsCharged": hd_cost,
        "newBalance": current_credits - hd_cost
    }


@router.get("/history")
async def get_generation_history(
    user: dict = Depends(get_current_user),
    limit: int = 20
):
    """Get user's coloring book generation history"""
    generations = await db.coloring_generations.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    return {
        "success": True,
        "generations": generations
    }


@router.get("/admin/analytics")
async def get_admin_analytics(user: dict = Depends(get_current_user)):
    """
    Admin Analytics Dashboard
    Track: Mode, Pages, Add-ons, Drop-off step
    """
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Step drop-off analysis
    step_pipeline = [
        {
            "$group": {
                "_id": "$step",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    step_analytics = await db.coloring_analytics.aggregate(step_pipeline).to_list(10)
    
    # Mode preference
    mode_pipeline = [
        {"$match": {"action": "mode_selected"}},
        {"$group": {"_id": "$data.mode", "count": {"$sum": 1}}}
    ]
    mode_stats = await db.coloring_analytics.aggregate(mode_pipeline).to_list(10)
    
    # Pages selected
    pages_pipeline = [
        {"$match": {"action": "generation_completed"}},
        {"$group": {"_id": "$data.option", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    pages_stats = await db.coloring_analytics.aggregate(pages_pipeline).to_list(10)
    
    # Popular addons
    addon_pipeline = [
        {"$match": {"action": "generation_completed"}},
        {"$unwind": "$data.addons"},
        {"$group": {"_id": "$data.addons", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    addon_stats = await db.coloring_analytics.aggregate(addon_pipeline).to_list(10)
    
    # Drop-off analysis
    dropoff_pipeline = [
        {"$match": {"analytics.dropOffStep": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$analytics.dropOffStep", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    dropoff_stats = await db.coloring_sessions.aggregate(dropoff_pipeline).to_list(10)
    
    # Completion rate
    total_sessions = await db.coloring_sessions.count_documents({})
    completed_sessions = await db.coloring_sessions.count_documents({"analytics.completed": True})
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Average order value
    revenue_pipeline = [
        {"$match": {"action": "generation_completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$data.total_credits"}, "count": {"$sum": 1}}}
    ]
    revenue_stats = await db.coloring_analytics.aggregate(revenue_pipeline).to_list(1)
    aov = revenue_stats[0]["total"] / revenue_stats[0]["count"] if revenue_stats and revenue_stats[0]["count"] > 0 else 0
    
    return {
        "success": True,
        "stepAnalytics": {step["_id"]: step["count"] for step in step_analytics},
        "modePreference": {item["_id"]: item["count"] for item in mode_stats},
        "pagesSelected": {item["_id"]: item["count"] for item in pages_stats},
        "popularAddons": {item["_id"]: item["count"] for item in addon_stats},
        "dropOffByStep": {item["_id"]: item["count"] for item in dropoff_stats},
        "metrics": {
            "totalSessions": total_sessions,
            "completedSessions": completed_sessions,
            "completionRate": round(completion_rate, 2),
            "averageOrderValue": round(aov, 2),
            "expectedAOV": 39  # Target AOV
        }
    }


@router.get("/admin/funnel")
async def get_conversion_funnel(user: dict = Depends(get_current_user)):
    """
    Conversion funnel logic for admin
    Shows where users quit at each step
    """
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get counts for each step
    funnel = {}
    for step in range(1, 6):
        reached = await db.coloring_analytics.count_documents({"step": {"$gte": step}})
        funnel[f"step_{step}"] = reached
    
    # Calculate conversion rates
    conversions = {}
    for i in range(1, 5):
        current = funnel.get(f"step_{i}", 0)
        next_step = funnel.get(f"step_{i+1}", 0)
        rate = (next_step / current * 100) if current > 0 else 0
        conversions[f"step_{i}_to_{i+1}"] = round(rate, 2)
    
    return {
        "success": True,
        "funnel": funnel,
        "conversionRates": conversions,
        "insights": {
            "biggestDropOff": min(conversions, key=conversions.get) if conversions else None,
            "recommendation": "Focus on improving the step with lowest conversion rate"
        }
    }
