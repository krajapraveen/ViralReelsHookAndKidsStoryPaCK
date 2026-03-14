"""
Credits Routes - Balance, Ledger, History, Packages
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_current_user

router = APIRouter(prefix="/credits", tags=["Credits"])


# Credit packages configuration
CREDIT_PACKAGES = [
    {"id": "starter", "name": "Starter Pack", "credits": 100, "price": 4.99, "currency": "USD", "popular": False},
    {"id": "basic", "name": "Basic Pack", "credits": 500, "price": 19.99, "currency": "USD", "popular": True},
    {"id": "pro", "name": "Pro Pack", "credits": 1500, "price": 49.99, "currency": "USD", "popular": False},
    {"id": "ultimate", "name": "Ultimate Pack", "credits": 5000, "price": 149.99, "currency": "USD", "popular": False},
]


@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages for purchase"""
    return CREDIT_PACKAGES


@router.get("/history")
async def get_credit_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get credit transaction history (alias for ledger)"""
    skip = page * size
    
    history = await db.credit_ledger.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.credit_ledger.count_documents({"userId": user["id"]})
    
    return {
        "history": history,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    """Get current credit balance. Admin/exempt users show unlimited."""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1, "subscription": 1, "plan": 1, "email": 1, "role": 1})
    email = user_data.get("email", "")
    role = user_data.get("role", "")
    EXEMPT_EMAILS = {"admin@creatorstudio.ai", "test@visionary-suite.com", "demo@visionary-suite.com"}
    is_exempt = email in EXEMPT_EMAILS or role in ("admin", "ADMIN")
    credits_val = 999999 if is_exempt else user_data.get("credits", 0)
    plan_val = "pro" if is_exempt else user_data.get("plan", "free")
    return {
        "credits": credits_val,
        "balance": credits_val,
        "subscription": user_data.get("subscription"),
        "plan": plan_val,
        "isFreeTier": plan_val == "free",
        "unlimited": is_exempt,
    }


@router.get("/check-upsell")
async def check_upsell(user: dict = Depends(get_current_user)):
    """Check if user should see an upsell prompt (low credits)."""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1, "plan": 1})
    credits_val = user_data.get("credits", 0) if user_data else 0
    plan_val = user_data.get("plan", "free") if user_data else "free"
    # Trigger upsell if credits < 10 (cost of 1 video)
    show_upsell = credits_val < 10
    return {
        "show_upsell": show_upsell,
        "credits": credits_val,
        "plan": plan_val,
    }


@router.get("/ledger")
async def get_ledger(
    page: int = 0,
    size: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get credit transaction history"""
    skip = page * size
    
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter.upper()
    
    ledger = await db.credit_ledger.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.credit_ledger.count_documents(query)
    
    # Calculate summary
    pipeline = [
        {"$match": {"userId": user["id"]}},
        {"$group": {
            "_id": "$type",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]
    summary_result = await db.credit_ledger.aggregate(pipeline).to_list(length=100)
    summary = {item["_id"]: {"total": item["total"], "count": item["count"]} for item in summary_result}
    
    return {
        "ledger": ledger,
        "total": total,
        "page": page,
        "size": size,
        "summary": summary
    }


@router.get("/usage")
async def get_usage_stats(user: dict = Depends(get_current_user)):
    """Get detailed credit usage statistics"""
    # Total spent
    spent_pipeline = [
        {"$match": {"userId": user["id"], "amount": {"$lt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$amount"}}}}
    ]
    spent_result = await db.credit_ledger.aggregate(spent_pipeline).to_list(length=1)
    total_spent = spent_result[0]["total"] if spent_result else 0
    
    # Total earned/purchased
    earned_pipeline = [
        {"$match": {"userId": user["id"], "amount": {"$gt": 0}}},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}}
    ]
    earned_result = await db.credit_ledger.aggregate(earned_pipeline).to_list(length=100)
    earned_by_type = {item["_id"]: item["total"] for item in earned_result}
    
    # Usage by feature
    usage_pipeline = [
        {"$match": {"userId": user["id"], "type": "USAGE"}},
        {"$group": {"_id": "$description", "total": {"$sum": {"$abs": "$amount"}}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]
    usage_result = await db.credit_ledger.aggregate(usage_pipeline).to_list(length=10)
    
    return {
        "currentBalance": user.get("credits", 0),
        "totalSpent": total_spent,
        "totalEarned": sum(earned_by_type.values()),
        "earnedByType": earned_by_type,
        "topUsage": [
            {"feature": item["_id"], "creditsUsed": item["total"], "count": item["count"]}
            for item in usage_result
        ]
    }
