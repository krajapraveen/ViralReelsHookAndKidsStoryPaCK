"""
Referral & Gift Card System
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import os
import sys
import secrets
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, add_credits

router = APIRouter(prefix="/referral", tags=["Referral & Gift Cards"])

# ============================================
# REFERRAL SYSTEM
# ============================================

REFERRAL_CONFIG = {
    "referrer_bonus": 50,       # Credits for the referrer
    "referee_bonus": 25,        # Credits for the new user
    "min_purchase": 100,        # Minimum purchase to qualify
    "max_referrals_per_month": 50,  # Monthly limit
    "tiers": {
        "bronze": {"min_referrals": 1, "bonus_multiplier": 1.0},
        "silver": {"min_referrals": 5, "bonus_multiplier": 1.2},
        "gold": {"min_referrals": 15, "bonus_multiplier": 1.5},
        "platinum": {"min_referrals": 30, "bonus_multiplier": 2.0}
    }
}

GIFT_CARD_CONFIG = {
    "denominations": [
        {"value": 50, "price": 50, "label": "50 Credits"},
        {"value": 100, "price": 95, "label": "100 Credits", "discount": "5% off"},
        {"value": 250, "price": 225, "label": "250 Credits", "discount": "10% off"},
        {"value": 500, "price": 425, "label": "500 Credits", "discount": "15% off"},
        {"value": 1000, "price": 800, "label": "1000 Credits", "discount": "20% off", "badge": "BEST VALUE"},
    ],
    "expiry_days": 365,  # Gift cards expire in 1 year
    "max_per_purchase": 10
}


def generate_referral_code(user_id: str) -> str:
    """Generate a unique referral code for a user"""
    hash_input = f"{user_id}-{secrets.token_hex(4)}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()


def generate_gift_card_code() -> str:
    """Generate a unique gift card code"""
    return f"GC-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"


def get_referral_tier(total_referrals: int) -> dict:
    """Determine referral tier based on total successful referrals"""
    tier = "bronze"
    for tier_name, tier_config in REFERRAL_CONFIG["tiers"].items():
        if total_referrals >= tier_config["min_referrals"]:
            tier = tier_name
    return {
        "name": tier,
        **REFERRAL_CONFIG["tiers"][tier]
    }


# ============================================
# REFERRAL ENDPOINTS
# ============================================

@router.get("/code")
async def get_referral_code(user: dict = Depends(get_current_user)):
    """Get or create user's referral code"""
    existing = await db.referral_codes.find_one(
        {"userId": user["id"]},
        {"_id": 0}
    )
    
    if existing:
        return {
            "success": True,
            "code": existing["code"],
            "link": f"https://creatorstudio.ai/signup?ref={existing['code']}",
            "totalReferrals": existing.get("totalReferrals", 0),
            "totalEarned": existing.get("totalEarned", 0),
            "tier": get_referral_tier(existing.get("totalReferrals", 0))
        }
    
    # Create new referral code
    code = generate_referral_code(user["id"])
    
    await db.referral_codes.insert_one({
        "userId": user["id"],
        "code": code,
        "totalReferrals": 0,
        "totalEarned": 0,
        "pendingReferrals": 0,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "code": code,
        "link": f"https://creatorstudio.ai/signup?ref={code}",
        "totalReferrals": 0,
        "totalEarned": 0,
        "tier": get_referral_tier(0)
    }


@router.get("/stats")
async def get_referral_stats(user: dict = Depends(get_current_user)):
    """Get detailed referral statistics"""
    code_data = await db.referral_codes.find_one(
        {"userId": user["id"]},
        {"_id": 0}
    )
    
    if not code_data:
        return {
            "success": False,
            "message": "No referral code found. Generate one first."
        }
    
    # Get recent referrals
    recent_referrals = await db.referrals.find(
        {"referrerId": user["id"]},
        {"_id": 0, "refereeEmail": 1, "status": 1, "bonus": 1, "createdAt": 1}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    # Get monthly count
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_count = await db.referrals.count_documents({
        "referrerId": user["id"],
        "status": "completed",
        "createdAt": {"$gte": month_start.isoformat()}
    })
    
    tier = get_referral_tier(code_data.get("totalReferrals", 0))
    
    return {
        "success": True,
        "code": code_data["code"],
        "stats": {
            "totalReferrals": code_data.get("totalReferrals", 0),
            "totalEarned": code_data.get("totalEarned", 0),
            "pendingReferrals": code_data.get("pendingReferrals", 0),
            "monthlyReferrals": monthly_count,
            "monthlyLimit": REFERRAL_CONFIG["max_referrals_per_month"]
        },
        "tier": tier,
        "recentReferrals": recent_referrals,
        "bonusPerReferral": int(REFERRAL_CONFIG["referrer_bonus"] * tier["bonus_multiplier"])
    }


@router.post("/validate/{code}")
async def validate_referral_code(code: str):
    """Validate a referral code (for signup flow)"""
    code_data = await db.referral_codes.find_one(
        {"code": code.upper()},
        {"_id": 0, "userId": 1, "code": 1}
    )
    
    if not code_data:
        return {"valid": False, "message": "Invalid referral code"}
    
    # Get referrer info
    referrer = await db.users.find_one(
        {"id": code_data["userId"]},
        {"_id": 0, "name": 1, "email": 1}
    )
    
    return {
        "valid": True,
        "code": code_data["code"],
        "referrerName": referrer.get("name", "A friend") if referrer else "A friend",
        "bonusCredits": REFERRAL_CONFIG["referee_bonus"]
    }


@router.post("/apply")
async def apply_referral(
    background_tasks: BackgroundTasks,
    referee_id: str,
    code: str,
    user: dict = Depends(get_current_user)
):
    """Apply referral bonus when a referred user makes first purchase"""
    # Admin or system only
    if user.get("role") not in ["admin", "system"]:
        # Also allow the referred user to trigger this
        if user["id"] != referee_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    code_data = await db.referral_codes.find_one({"code": code.upper()})
    if not code_data:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    # Check if already applied
    existing = await db.referrals.find_one({
        "refereeId": referee_id,
        "status": "completed"
    })
    if existing:
        return {"success": False, "message": "Referral already applied"}
    
    # Check monthly limit
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_count = await db.referrals.count_documents({
        "referrerId": code_data["userId"],
        "status": "completed",
        "createdAt": {"$gte": month_start.isoformat()}
    })
    
    if monthly_count >= REFERRAL_CONFIG["max_referrals_per_month"]:
        return {"success": False, "message": "Referrer has reached monthly limit"}
    
    # Calculate bonus with tier multiplier
    tier = get_referral_tier(code_data.get("totalReferrals", 0))
    referrer_bonus = int(REFERRAL_CONFIG["referrer_bonus"] * tier["bonus_multiplier"])
    referee_bonus = REFERRAL_CONFIG["referee_bonus"]
    
    # Add credits to referrer
    await add_credits(code_data["userId"], referrer_bonus, f"Referral bonus: {referee_id[:8]}")
    
    # Add credits to referee
    await add_credits(referee_id, referee_bonus, "Welcome referral bonus")
    
    # Record referral
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()),
        "referrerId": code_data["userId"],
        "refereeId": referee_id,
        "code": code.upper(),
        "status": "completed",
        "referrerBonus": referrer_bonus,
        "refereeBonus": referee_bonus,
        "tier": tier["name"],
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Update referral code stats
    await db.referral_codes.update_one(
        {"code": code.upper()},
        {
            "$inc": {
                "totalReferrals": 1,
                "totalEarned": referrer_bonus
            }
        }
    )
    
    return {
        "success": True,
        "referrerBonus": referrer_bonus,
        "refereeBonus": referee_bonus,
        "message": "Referral bonus applied successfully"
    }


@router.get("/leaderboard")
async def get_referral_leaderboard(user: dict = Depends(get_current_user)):
    """Get top referrers leaderboard"""
    pipeline = [
        {"$sort": {"totalReferrals": -1}},
        {"$limit": 20},
        {"$lookup": {
            "from": "users",
            "localField": "userId",
            "foreignField": "id",
            "as": "user"
        }},
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0,
            "name": {"$ifNull": ["$user.name", "Anonymous"]},
            "totalReferrals": 1,
            "totalEarned": 1,
            "tier": 1
        }}
    ]
    
    leaders = await db.referral_codes.aggregate(pipeline).to_list(length=20)
    
    # Add tier info
    for leader in leaders:
        leader["tier"] = get_referral_tier(leader.get("totalReferrals", 0))["name"]
    
    return {
        "success": True,
        "leaderboard": leaders
    }


# ============================================
# GIFT CARD ENDPOINTS
# ============================================

@router.get("/gift-cards/options")
async def get_gift_card_options(user: dict = Depends(get_current_user)):
    """Get available gift card denominations"""
    return {
        "success": True,
        "denominations": GIFT_CARD_CONFIG["denominations"],
        "expiryDays": GIFT_CARD_CONFIG["expiry_days"]
    }


@router.post("/gift-cards/purchase")
async def purchase_gift_card(
    denomination: int,
    quantity: int = 1,
    recipient_email: Optional[str] = None,
    message: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Purchase gift card(s)"""
    # Validate denomination
    valid_denomination = None
    for d in GIFT_CARD_CONFIG["denominations"]:
        if d["value"] == denomination:
            valid_denomination = d
            break
    
    if not valid_denomination:
        raise HTTPException(status_code=400, detail="Invalid denomination")
    
    if quantity < 1 or quantity > GIFT_CARD_CONFIG["max_per_purchase"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Quantity must be between 1 and {GIFT_CARD_CONFIG['max_per_purchase']}"
        )
    
    # Calculate total price
    total_price = valid_denomination["price"] * quantity
    
    # Check user credits
    if user.get("credits", 0) < total_price:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient credits. Need {total_price} credits."
        )
    
    # Generate gift cards
    gift_cards = []
    for _ in range(quantity):
        code = generate_gift_card_code()
        expiry_date = datetime.now(timezone.utc) + timedelta(days=GIFT_CARD_CONFIG["expiry_days"])
        
        card_data = {
            "id": str(uuid.uuid4()),
            "code": code,
            "value": valid_denomination["value"],
            "purchasedBy": user["id"],
            "recipientEmail": recipient_email,
            "message": message,
            "status": "active",
            "redeemedBy": None,
            "redeemedAt": None,
            "expiresAt": expiry_date.isoformat(),
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.gift_cards.insert_one(card_data)
        gift_cards.append({
            "code": code,
            "value": valid_denomination["value"],
            "expiresAt": expiry_date.isoformat()
        })
    
    # Deduct credits from purchaser
    from shared import deduct_credits
    await deduct_credits(user["id"], total_price, f"Gift card purchase: {quantity}x {denomination} credits")
    
    # TODO: Send email to recipient if provided
    
    return {
        "success": True,
        "giftCards": gift_cards,
        "totalPaid": total_price,
        "message": f"Successfully purchased {quantity} gift card(s)"
    }


@router.post("/gift-cards/redeem")
async def redeem_gift_card(code: str, user: dict = Depends(get_current_user)):
    """Redeem a gift card"""
    gift_card = await db.gift_cards.find_one({"code": code.upper()})
    
    if not gift_card:
        raise HTTPException(status_code=404, detail="Invalid gift card code")
    
    if gift_card.get("status") != "active":
        raise HTTPException(status_code=400, detail="Gift card has already been redeemed or expired")
    
    # Check expiry
    expiry = datetime.fromisoformat(gift_card["expiresAt"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expiry:
        await db.gift_cards.update_one(
            {"code": code.upper()},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Gift card has expired")
    
    # Redeem the gift card
    await db.gift_cards.update_one(
        {"code": code.upper()},
        {
            "$set": {
                "status": "redeemed",
                "redeemedBy": user["id"],
                "redeemedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Add credits to user
    await add_credits(user["id"], gift_card["value"], f"Gift card redeemed: {code[:8]}")
    
    return {
        "success": True,
        "creditsAdded": gift_card["value"],
        "message": f"Successfully redeemed {gift_card['value']} credits!"
    }


@router.get("/gift-cards/balance/{code}")
async def check_gift_card_balance(code: str):
    """Check gift card balance/status (public endpoint)"""
    gift_card = await db.gift_cards.find_one(
        {"code": code.upper()},
        {"_id": 0, "value": 1, "status": 1, "expiresAt": 1}
    )
    
    if not gift_card:
        return {"valid": False, "message": "Invalid gift card code"}
    
    # Check expiry
    expiry = datetime.fromisoformat(gift_card["expiresAt"].replace('Z', '+00:00'))
    is_expired = datetime.now(timezone.utc) > expiry
    
    return {
        "valid": True,
        "value": gift_card["value"],
        "status": "expired" if is_expired else gift_card["status"],
        "expiresAt": gift_card["expiresAt"],
        "canRedeem": gift_card["status"] == "active" and not is_expired
    }


@router.get("/gift-cards/my-cards")
async def get_my_gift_cards(user: dict = Depends(get_current_user)):
    """Get user's purchased and redeemed gift cards"""
    purchased = await db.gift_cards.find(
        {"purchasedBy": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(length=50)
    
    redeemed = await db.gift_cards.find(
        {"redeemedBy": user["id"]},
        {"_id": 0}
    ).sort("redeemedAt", -1).to_list(length=50)
    
    return {
        "success": True,
        "purchased": purchased,
        "redeemed": redeemed
    }


# ============================================
# ADMIN ENDPOINTS
# ============================================

@router.get("/admin/stats")
async def admin_referral_stats(user: dict = Depends(get_current_user)):
    """Admin: Get referral system statistics"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_referrals = await db.referrals.count_documents({})
    completed_referrals = await db.referrals.count_documents({"status": "completed"})
    total_codes = await db.referral_codes.count_documents({})
    
    # Gift card stats
    total_gift_cards = await db.gift_cards.count_documents({})
    active_gift_cards = await db.gift_cards.count_documents({"status": "active"})
    redeemed_gift_cards = await db.gift_cards.count_documents({"status": "redeemed"})
    
    # Calculate total value
    pipeline = [
        {"$match": {"status": "redeemed"}},
        {"$group": {"_id": None, "total": {"$sum": "$value"}}}
    ]
    redeemed_value = await db.gift_cards.aggregate(pipeline).to_list(length=1)
    
    return {
        "success": True,
        "referrals": {
            "totalCodes": total_codes,
            "totalReferrals": total_referrals,
            "completedReferrals": completed_referrals
        },
        "giftCards": {
            "total": total_gift_cards,
            "active": active_gift_cards,
            "redeemed": redeemed_gift_cards,
            "totalRedeemedValue": redeemed_value[0]["total"] if redeemed_value else 0
        }
    }
