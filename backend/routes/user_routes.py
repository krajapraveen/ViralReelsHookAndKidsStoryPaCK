"""
User Routes
Simple user profile and settings endpoints
"""
from fastapi import APIRouter, Depends
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_current_user

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    """Get current user profile - alias for /auth/me"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    
    if not user_data:
        return {
            "id": user["id"],
            "email": user.get("email", ""),
            "name": user.get("name", ""),
            "role": user.get("role", "USER"),
            "plan": user.get("plan", "free"),
            "credits": user.get("credits", 0)
        }
    
    return {
        "id": user_data.get("id"),
        "email": user_data.get("email", ""),
        "name": user_data.get("name", ""),
        "role": user_data.get("role", "USER"),
        "plan": user_data.get("plan", "free"),
        "credits": user_data.get("credits", 0),
        "createdAt": user_data.get("createdAt"),
        "tourCompleted": user_data.get("tourCompleted", False),
        "subscription": user_data.get("subscription")
    }


@router.get("/plan")
async def get_user_plan(user: dict = Depends(get_current_user)):
    """Get current user's subscription plan"""
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    return {
        "plan": user_data.get("plan", "free") if user_data else "free",
        "subscription": user_data.get("subscription") if user_data else None
    }
