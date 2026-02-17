"""
Credits Routes - Balance, Ledger, History
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional

from ..shared import db, get_current_user

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    """Get current credit balance"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1, "subscription": 1, "plan": 1})
    return {
        "credits": user_data.get("credits", 0),
        "subscription": user_data.get("subscription"),
        "plan": user_data.get("plan", "free")
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
