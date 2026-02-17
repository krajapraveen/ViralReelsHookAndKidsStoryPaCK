"""Credits management routes"""
from fastapi import APIRouter, Depends
from ..utils.auth import get_current_user
from ..utils.database import db

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    """Get user's current credit balance"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "balance": user_data.get("credits", 0),
        "isFreeTier": user_data.get("role") == "user",
        "plan": user_data.get("plan", "free")
    }


@router.get("/ledger")
async def get_ledger(page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    """Get user's credit transaction history"""
    skip = page * size
    
    transactions = await db.credit_ledger.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.credit_ledger.count_documents({"userId": user["id"]})
    
    return {
        "transactions": transactions,
        "total": total,
        "page": page,
        "size": size
    }
