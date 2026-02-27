"""
Coloring Book Creator - New Pricing & Business Logic
5-Step Wizard Flow with Revenue Optimization
"""
from fastapi import APIRouter, HTTPException, Depends
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
# NEW PRICING CONFIGURATION
# =============================================================================

STORY_MODE_PRICING = {
    "5_pages": {"pages": 5, "credits": 10, "label": "5 Pages"},
    "10_pages": {"pages": 10, "credits": 18, "label": "10 Pages", "savings": "10%"},
    "20_pages": {"pages": 20, "credits": 32, "label": "20 Pages", "badge": "MOST POPULAR", "default": True, "savings": "20%"},
    "30_pages": {"pages": 30, "credits": 45, "label": "30 Pages", "badge": "BEST VALUE", "savings": "25%"},
}

PHOTO_MODE_PRICING = {
    "1_image": {"images": 1, "credits": 5, "label": "1 Image"},
    "5_images": {"images": 5, "credits": 20, "label": "5 Images", "savings": "20%", "badge": "POPULAR"},
    "10_images": {"images": 10, "credits": 35, "label": "10 Images", "badge": "BEST VALUE", "savings": "30%"},
}

ADDONS = {
    "activity_pages": {
        "id": "activity_pages",
        "name": "Activity Pages",
        "description": "Puzzles, mazes & fun activities",
        "credits": 3,
        "icon": "puzzle"
    },
    "personalized_cover": {
        "id": "personalized_cover",
        "name": "Personalized Cover",
        "description": "Custom cover with child's name",
        "credits": 4,
        "icon": "user",
        "default": True  # Pre-selected for revenue
    },
    "dedication_page": {
        "id": "dedication_page",
        "name": "Dedication Page",
        "description": "Add a personal message",
        "credits": 2,
        "icon": "heart"
    },
    "premium_templates": {
        "id": "premium_templates",
        "name": "Premium Cover Templates",
        "description": "Beautiful designer covers",
        "credits": 5,
        "icon": "crown",
        "pro_only": True
    },
    "hd_print": {
        "id": "hd_print",
        "name": "HD Print Version",
        "description": "High-resolution 300 DPI PDF",
        "credits": 5,
        "icon": "printer"
    },
    "commercial_license": {
        "id": "commercial_license",
        "name": "Commercial License",
        "description": "Use for commercial purposes",
        "credits": 10,
        "icon": "briefcase"
    }
}

SUBSCRIPTION_BENEFITS = {
    "free": {
        "discount": 0,
        "preview_pages": 2,
        "watermark": True,
        "premium_templates": False,
        "priority_generation": False,
        "commercial_included": False
    },
    "creator": {
        "discount": 20,
        "preview_pages": 3,
        "watermark": False,
        "premium_templates": False,
        "priority_generation": False,
        "commercial_included": False
    },
    "pro": {
        "discount": 30,
        "preview_pages": 5,
        "watermark": False,
        "premium_templates": True,
        "priority_generation": True,
        "commercial_included": False
    },
    "studio": {
        "discount": 40,
        "preview_pages": -1,  # Unlimited
        "watermark": False,
        "premium_templates": True,
        "priority_generation": True,
        "commercial_included": True
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class StoryModeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ageGroup: str = Field(default="4-6")
    description: str = Field(..., min_length=10, max_length=2000)
    pageOption: str = Field(default="20_pages")
    illustrationStyle: str = Field(default="cartoon")


class PhotoModeRequest(BaseModel):
    imageOption: str = Field(default="5_images")
    outlineStrength: int = Field(default=50, ge=0, le=100)
    removeBackground: bool = Field(default=False)


class CustomizeRequest(BaseModel):
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
    storyData: Optional[StoryModeRequest] = None
    photoData: Optional[PhotoModeRequest] = None
    customize: CustomizeRequest


class AnalyticsEvent(BaseModel):
    sessionId: str
    step: int
    action: str
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_cost(mode: str, option: str, addons: List[str], user_plan: str) -> Dict[str, Any]:
    """Calculate total cost with breakdown"""
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
            # Check if pro-only addon
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
    """Get preview configuration based on plan"""
    benefits = SUBSCRIPTION_BENEFITS.get(user_plan, SUBSCRIPTION_BENEFITS["free"])
    return {
        "pages": benefits["preview_pages"],
        "watermark": benefits["watermark"],
        "unlimited": benefits["preview_pages"] == -1
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """Get complete pricing configuration"""
    user_plan = user.get("plan", "free").lower()
    benefits = SUBSCRIPTION_BENEFITS.get(user_plan, SUBSCRIPTION_BENEFITS["free"])
    
    # Mark pro-only addons
    addons_with_access = {}
    for addon_id, addon in ADDONS.items():
        addons_with_access[addon_id] = {
            **addon,
            "locked": addon.get("pro_only", False) and user_plan not in ["pro", "studio"],
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
        }
    }


@router.post("/calculate")
async def calculate_pricing(
    mode: str,
    option: str,
    addons: List[str] = [],
    user: dict = Depends(get_current_user)
):
    """Calculate live pricing"""
    user_plan = user.get("plan", "free").lower()
    cost = calculate_cost(mode, option, addons, user_plan)
    
    return {
        "success": True,
        "breakdown": cost
    }


@router.get("/preview-config")
async def get_preview_configuration(user: dict = Depends(get_current_user)):
    """Get preview configuration for user"""
    user_plan = user.get("plan", "free").lower()
    return {
        "success": True,
        "preview": get_preview_config(user_plan)
    }


@router.post("/session/start")
async def start_session(user: dict = Depends(get_current_user)):
    """Start a new coloring book creation session"""
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
    """Update session progress"""
    result = await db.coloring_sessions.update_one(
        {"id": session_id, "userId": user["id"]},
        {
            "$set": {
                "currentStep": step,
                **data,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True}


@router.post("/analytics/track")
async def track_analytics(event: AnalyticsEvent, user: dict = Depends(get_current_user)):
    """Track user analytics for drop-off analysis"""
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
    
    return {"success": True}


@router.post("/generate/preview")
async def generate_preview(
    request: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate preview pages (free, with watermark for free users)"""
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
            "plan": user_plan
        },
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "preview": {
            "pages": preview_config["pages"],
            "watermark": preview_config["watermark"],
            "message": "This is a preview. Final PDF will include all pages."
        }
    }


@router.post("/generate/full")
async def generate_full_book(
    request: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate full coloring book (charges credits)"""
    user_id = user["id"]
    user_plan = user.get("plan", "free").lower()
    
    # Calculate cost
    mode = request.mode
    option = request.customize.pageOption if mode == "story" else request.customize.imageOption
    addons = request.customize.addons
    
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
                "available": current_credits
            }
        )
    
    # Deduct credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -total_cost}}
    )
    
    # Create generation record
    generation_id = str(uuid.uuid4())
    generation = {
        "id": generation_id,
        "sessionId": request.sessionId,
        "userId": user_id,
        "mode": mode,
        "storyData": request.storyData.dict() if request.storyData else None,
        "photoData": request.photoData.dict() if request.photoData else None,
        "customize": request.customize.dict(),
        "costBreakdown": cost_breakdown,
        "creditsCharged": total_cost,
        "status": "completed",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.coloring_generations.insert_one(generation)
    
    # Log to ledger
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": total_cost,
        "refType": "COLORING_BOOK",
        "refId": generation_id,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
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
            "plan": user_plan
        },
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Generated coloring book {generation_id} for user {user_id}, charged {total_cost} credits")
    
    return {
        "success": True,
        "generationId": generation_id,
        "creditsCharged": total_cost,
        "newBalance": current_credits - total_cost
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
    """Get analytics for admin dashboard"""
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Aggregate analytics
    pipeline = [
        {
            "$group": {
                "_id": {
                    "step": "$step",
                    "action": "$action"
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id.step": 1}}
    ]
    
    analytics = await db.coloring_analytics.aggregate(pipeline).to_list(100)
    
    # Drop-off analysis
    step_counts = {}
    for item in analytics:
        step = item["_id"]["step"]
        if step not in step_counts:
            step_counts[step] = 0
        step_counts[step] += item["count"]
    
    # Mode preference
    mode_pipeline = [
        {"$match": {"action": "mode_selected"}},
        {"$group": {"_id": "$data.mode", "count": {"$sum": 1}}}
    ]
    mode_stats = await db.coloring_analytics.aggregate(mode_pipeline).to_list(10)
    
    # Popular addons
    addon_pipeline = [
        {"$match": {"action": "generation_completed"}},
        {"$unwind": "$data.addons"},
        {"$group": {"_id": "$data.addons", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    addon_stats = await db.coloring_analytics.aggregate(addon_pipeline).to_list(10)
    
    return {
        "success": True,
        "stepDropoff": step_counts,
        "modePreference": {item["_id"]: item["count"] for item in mode_stats},
        "popularAddons": {item["_id"]: item["count"] for item in addon_stats}
    }
