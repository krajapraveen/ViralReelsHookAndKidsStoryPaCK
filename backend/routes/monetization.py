"""
Monetization API Routes
Handles pricing, upsells, premium access, and credit management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from config.monetization import (
    SUBSCRIPTION_PLANS, VARIATION_PRICING, UPSELL_OPTIONS,
    BUNDLE_PRICING, PREMIUM_STYLES, CREDIT_PSYCHOLOGY,
    DASHBOARD_PRIORITY, CREATOR_BOOST_PACK,
    get_variation_cost, is_style_premium, can_access_style,
    get_upsell_cost, get_bundle_cost, get_all_styles
)

router = APIRouter(prefix="/monetization", tags=["Monetization"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class UpsellPurchaseRequest(BaseModel):
    generationId: str
    upsellId: str


class DailyRewardClaimRequest(BaseModel):
    pass


class StyleAccessRequest(BaseModel):
    feature: str
    styleId: str


# =============================================================================
# PRICING ENDPOINTS
# =============================================================================

@router.get("/plans")
async def get_subscription_plans():
    """Get all subscription plans with pricing"""
    return {
        "success": True,
        "plans": list(SUBSCRIPTION_PLANS.values()),
        "currency": {
            "primary": "INR",
            "symbol": "₹"
        }
    }


@router.get("/variations")
async def get_variation_pricing():
    """Get multi-output variation pricing"""
    return {
        "success": True,
        "variations": VARIATION_PRICING,
        "description": "Generate multiple variations in one batch"
    }


@router.get("/bundles/{feature}")
async def get_bundle_pricing(feature: str):
    """Get bundle pricing for a feature"""
    bundles = BUNDLE_PRICING.get(feature)
    if not bundles:
        return {"success": True, "bundles": {}}
    
    return {
        "success": True,
        "feature": feature,
        "bundles": bundles
    }


@router.get("/upsells")
async def get_upsell_options(user: dict = Depends(get_current_user)):
    """Get available upsell options with user-specific pricing"""
    user_plan = user.get("plan", "free")
    
    upsells = {}
    for upsell_id, upsell in UPSELL_OPTIONS.items():
        cost = get_upsell_cost(upsell_id, user_plan)
        upsells[upsell_id] = {
            **upsell,
            "cost": cost,
            "free_for_user": cost == 0
        }
    
    return {
        "success": True,
        "upsells": upsells,
        "user_plan": user_plan
    }


# =============================================================================
# STYLE ACCESS ENDPOINTS
# =============================================================================

@router.get("/styles/{feature}")
async def get_feature_styles(feature: str, user: dict = Depends(get_current_user)):
    """Get all styles for a feature with lock status based on user plan"""
    user_plan = user.get("plan", "free")
    all_styles = get_all_styles(feature)
    
    # Add user-specific access info
    for style in all_styles:
        style["can_access"] = can_access_style(user_plan, feature, style["id"])
        if style["locked"] and not style["can_access"]:
            style["unlock_plan"] = "pro"
    
    return {
        "success": True,
        "feature": feature,
        "styles": all_styles,
        "user_plan": user_plan,
        "has_premium_access": SUBSCRIPTION_PLANS.get(user_plan, {}).get("limitations", {}).get("premium_styles", False)
    }


@router.post("/styles/check-access")
async def check_style_access(request: StyleAccessRequest, user: dict = Depends(get_current_user)):
    """Check if user can access a specific style"""
    user_plan = user.get("plan", "free")
    
    can_access = can_access_style(user_plan, request.feature, request.styleId)
    is_premium = is_style_premium(request.feature, request.styleId)
    
    return {
        "success": True,
        "can_access": can_access,
        "is_premium": is_premium,
        "user_plan": user_plan,
        "upgrade_required": is_premium and not can_access,
        "upgrade_to": "pro" if not can_access else None
    }


# =============================================================================
# UPSELL PURCHASE ENDPOINTS
# =============================================================================

@router.post("/upsell/purchase")
async def purchase_upsell(request: UpsellPurchaseRequest, user: dict = Depends(get_current_user)):
    """Purchase an upsell for a generation"""
    user_id = user["id"]
    user_plan = user.get("plan", "free")
    
    # Get upsell info
    upsell = UPSELL_OPTIONS.get(request.upsellId)
    if not upsell:
        raise HTTPException(status_code=400, detail="Invalid upsell option")
    
    # Calculate cost
    cost = get_upsell_cost(request.upsellId, user_plan)
    
    if cost == 0:
        # Free for user's plan
        return {
            "success": True,
            "message": f"{upsell['name']} is included in your plan!",
            "cost": 0,
            "applied": True
        }
    
    # Check user credits
    user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    current_credits = user_data.get("credits", 0) if user_data else 0
    
    if current_credits < cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "required": cost,
                "available": current_credits,
                "message": f"Need {cost} credits for {upsell['name']}"
            }
        )
    
    # Deduct credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -cost}}
    )
    
    # Record the upsell purchase
    await db.upsell_purchases.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "generationId": request.generationId,
        "upsellId": request.upsellId,
        "cost": cost,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"User {user_id} purchased upsell {request.upsellId} for {cost} credits")
    
    return {
        "success": True,
        "message": f"{upsell['name']} applied successfully!",
        "cost": cost,
        "applied": True,
        "new_balance": current_credits - cost
    }


# =============================================================================
# DAILY REWARD ENDPOINTS
# =============================================================================

@router.post("/daily-reward/claim")
async def claim_daily_reward(user: dict = Depends(get_current_user)):
    """Claim daily login reward"""
    user_id = user["id"]
    reward_credits = CREDIT_PSYCHOLOGY["daily_login_reward"]
    
    # Check if already claimed today
    today = datetime.now(timezone.utc).date().isoformat()
    existing_claim = await db.daily_rewards.find_one({
        "userId": user_id,
        "date": today
    })
    
    if existing_claim:
        return {
            "success": False,
            "message": "Already claimed today's reward!",
            "next_claim": "Tomorrow",
            "already_claimed": True
        }
    
    # Grant credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": reward_credits}}
    )
    
    # Record the claim
    await db.daily_rewards.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "date": today,
        "credits": reward_credits,
        "claimedAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Get new balance
    user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    new_balance = user_data.get("credits", 0) if user_data else reward_credits
    
    logger.info(f"User {user_id} claimed daily reward: {reward_credits} credits")
    
    return {
        "success": True,
        "message": f"🎁 Claimed {reward_credits} credits!",
        "credits_earned": reward_credits,
        "new_balance": new_balance,
        "streak": await _get_login_streak(user_id)
    }


@router.get("/daily-reward/status")
async def get_daily_reward_status(user: dict = Depends(get_current_user)):
    """Check daily reward status"""
    user_id = user["id"]
    today = datetime.now(timezone.utc).date().isoformat()
    
    existing_claim = await db.daily_rewards.find_one({
        "userId": user_id,
        "date": today
    })
    
    return {
        "success": True,
        "claimed_today": existing_claim is not None,
        "reward_amount": CREDIT_PSYCHOLOGY["daily_login_reward"],
        "streak": await _get_login_streak(user_id)
    }


async def _get_login_streak(user_id: str) -> int:
    """Calculate consecutive login days"""
    today = datetime.now(timezone.utc).date()
    streak = 0
    
    for i in range(30):  # Check up to 30 days
        check_date = (today - timedelta(days=i)).isoformat()
        claim = await db.daily_rewards.find_one({
            "userId": user_id,
            "date": check_date
        })
        
        if claim:
            streak += 1
        elif i > 0:  # Allow today to be unclaimed
            break
    
    return streak


# =============================================================================
# CREDIT PSYCHOLOGY ENDPOINTS
# =============================================================================

@router.get("/credit-status")
async def get_credit_status(user: dict = Depends(get_current_user)):
    """Get credit status with psychology indicators"""
    credits = user.get("credits", 0)
    plan = user.get("plan", "free")
    
    low_threshold = CREDIT_PSYCHOLOGY["low_balance_threshold"]
    critical_threshold = CREDIT_PSYCHOLOGY["critical_balance_threshold"]
    
    status = "normal"
    message = None
    urgency = None
    
    if credits <= critical_threshold:
        status = "critical"
        message = f"⚠️ Only {credits} credits left!"
        urgency = "high"
    elif credits <= low_threshold:
        status = "low"
        message = f"Running low on credits ({credits} remaining)"
        urgency = "medium"
    
    return {
        "success": True,
        "credits": credits,
        "status": status,
        "message": message,
        "urgency": urgency,
        "thresholds": {
            "low": low_threshold,
            "critical": critical_threshold
        },
        "plan": plan,
        "show_topup_prompt": status in ["low", "critical"]
    }


# =============================================================================
# DASHBOARD CONFIG ENDPOINTS
# =============================================================================

@router.get("/dashboard-config")
async def get_dashboard_config(user: dict = Depends(get_current_user)):
    """Get dashboard configuration with priority order"""
    user_plan = user.get("plan", "free")
    
    # Add trending badges based on usage (mock for now)
    primary_tools = []
    for tool in DASHBOARD_PRIORITY:
        primary_tools.append({
            **tool,
            "show_trending": tool.get("trending", False)
        })
    
    return {
        "success": True,
        "primary_tools": primary_tools,
        "creator_boost_pack": CREATOR_BOOST_PACK,
        "user_plan": user_plan,
        "daily_reward_available": not await _check_daily_claimed(user["id"])
    }


async def _check_daily_claimed(user_id: str) -> bool:
    """Check if daily reward claimed"""
    today = datetime.now(timezone.utc).date().isoformat()
    claim = await db.daily_rewards.find_one({
        "userId": user_id,
        "date": today
    })
    return claim is not None


# =============================================================================
# WATERMARK LOGIC
# =============================================================================

@router.get("/watermark-status")
async def get_watermark_status(user: dict = Depends(get_current_user)):
    """Check if user's outputs should have watermarks"""
    user_plan = user.get("plan", "free")
    plan_config = SUBSCRIPTION_PLANS.get(user_plan, SUBSCRIPTION_PLANS["free"])
    
    watermark_free = plan_config.get("limitations", {}).get("watermark_free", False)
    
    return {
        "success": True,
        "add_watermark": not watermark_free,
        "plan": user_plan,
        "upgrade_to_remove": "creator" if not watermark_free else None
    }
