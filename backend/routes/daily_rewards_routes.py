"""
Daily Rewards & Gamification System
Encourages daily logins with streak bonuses and credit rewards
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/daily-rewards", tags=["Daily Rewards"])

# Reward configuration
DAILY_REWARDS = {
    1: {"credits": 2, "label": "Day 1"},
    2: {"credits": 3, "label": "Day 2"},
    3: {"credits": 4, "label": "Day 3"},
    4: {"credits": 5, "label": "Day 4"},
    5: {"credits": 6, "label": "Day 5"},
    6: {"credits": 8, "label": "Day 6"},
    7: {"credits": 10, "label": "Day 7 Bonus!"},
}

STREAK_BONUSES = {
    7: 15,   # 1 week streak bonus
    14: 25,  # 2 week streak bonus
    30: 50,  # 1 month streak bonus
}


async def get_user_streak_info(user_id: str) -> Dict[str, Any]:
    """Get user's current streak and reward status"""
    
    streak_data = await db.daily_streaks.find_one({"user_id": user_id})
    
    if not streak_data:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "last_claim_date": None,
            "total_rewards_claimed": 0,
            "can_claim_today": True
        }
    
    last_claim = streak_data.get("last_claim_date")
    current_streak = streak_data.get("current_streak", 0)
    
    # Check if user already claimed today
    can_claim_today = True
    if last_claim:
        last_claim_date = datetime.fromisoformat(last_claim.replace('Z', '+00:00')) if isinstance(last_claim, str) else last_claim
        today = datetime.now(timezone.utc).date()
        last_claim_day = last_claim_date.date() if hasattr(last_claim_date, 'date') else last_claim_date
        
        if last_claim_day == today:
            can_claim_today = False
        elif (today - last_claim_day).days > 1:
            # Streak broken - reset
            current_streak = 0
    
    return {
        "current_streak": current_streak,
        "longest_streak": streak_data.get("longest_streak", 0),
        "last_claim_date": streak_data.get("last_claim_date"),
        "total_rewards_claimed": streak_data.get("total_rewards_claimed", 0),
        "can_claim_today": can_claim_today
    }


@router.get("/status")
async def get_reward_status(user: dict = Depends(get_current_user)):
    """Get current daily reward status"""
    
    user_id = user.get("id")
    streak_info = await get_user_streak_info(user_id)
    
    # Calculate today's reward
    day_in_week = (streak_info["current_streak"] % 7) + 1 if streak_info["can_claim_today"] else ((streak_info["current_streak"] - 1) % 7) + 1
    today_reward = DAILY_REWARDS.get(day_in_week, DAILY_REWARDS[1])
    
    # Check for streak bonuses
    streak_bonus = 0
    for streak_threshold, bonus in STREAK_BONUSES.items():
        if streak_info["current_streak"] + 1 == streak_threshold:
            streak_bonus = bonus
            break
    
    # Get weekly progress
    weekly_progress = []
    current_day = streak_info["current_streak"] % 7
    for day in range(1, 8):
        weekly_progress.append({
            "day": day,
            "credits": DAILY_REWARDS[day]["credits"],
            "label": DAILY_REWARDS[day]["label"],
            "claimed": day <= current_day if not streak_info["can_claim_today"] else day < current_day,
            "is_today": day == day_in_week and streak_info["can_claim_today"],
            "is_next": day == day_in_week + 1 if not streak_info["can_claim_today"] else False
        })
    
    return {
        "success": True,
        "can_claim": streak_info["can_claim_today"],
        "current_streak": streak_info["current_streak"],
        "longest_streak": streak_info["longest_streak"],
        "total_rewards_claimed": streak_info["total_rewards_claimed"],
        "today_reward": {
            "credits": today_reward["credits"],
            "label": today_reward["label"],
            "streak_bonus": streak_bonus,
            "total": today_reward["credits"] + streak_bonus
        },
        "weekly_progress": weekly_progress,
        "streak_bonuses": [
            {"streak": 7, "bonus": 15, "label": "1 Week", "achieved": streak_info["current_streak"] >= 7},
            {"streak": 14, "bonus": 25, "label": "2 Weeks", "achieved": streak_info["current_streak"] >= 14},
            {"streak": 30, "bonus": 50, "label": "1 Month", "achieved": streak_info["current_streak"] >= 30},
        ]
    }


@router.post("/claim")
async def claim_daily_reward(user: dict = Depends(get_current_user)):
    """Claim today's daily reward"""
    
    user_id = user.get("id")
    streak_info = await get_user_streak_info(user_id)
    
    if not streak_info["can_claim_today"]:
        raise HTTPException(status_code=400, detail="Already claimed today's reward")
    
    # Calculate new streak
    new_streak = streak_info["current_streak"] + 1
    day_in_week = (new_streak - 1) % 7 + 1
    reward = DAILY_REWARDS.get(day_in_week, DAILY_REWARDS[1])
    
    # Check for streak bonus
    streak_bonus = STREAK_BONUSES.get(new_streak, 0)
    total_credits = reward["credits"] + streak_bonus
    
    # Update user credits
    user_data = await db.users.find_one({"_id": user.get("_id")})
    current_credits = user_data.get("credits", 0) if user_data else 0
    new_credits = current_credits + total_credits
    
    await db.users.update_one(
        {"_id": user.get("_id")},
        {"$set": {"credits": new_credits}}
    )
    
    # Update streak data
    now = datetime.now(timezone.utc).isoformat()
    longest_streak = max(new_streak, streak_info["longest_streak"])
    
    await db.daily_streaks.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "current_streak": new_streak,
                "longest_streak": longest_streak,
                "last_claim_date": now,
            },
            "$inc": {
                "total_rewards_claimed": total_credits
            }
        },
        upsert=True
    )
    
    # Log the reward claim
    await db.reward_claims.insert_one({
        "user_id": user_id,
        "timestamp": now,
        "day_in_week": day_in_week,
        "base_credits": reward["credits"],
        "streak_bonus": streak_bonus,
        "total_credits": total_credits,
        "new_streak": new_streak
    })
    
    logger.info(f"User {user.get('email')} claimed daily reward: {total_credits} credits (streak: {new_streak})")
    
    return {
        "success": True,
        "message": f"Claimed {total_credits} credits!",
        "reward": {
            "base_credits": reward["credits"],
            "streak_bonus": streak_bonus,
            "total_credits": total_credits,
            "day_label": reward["label"]
        },
        "new_balance": new_credits,
        "streak": {
            "current": new_streak,
            "longest": longest_streak,
            "is_milestone": streak_bonus > 0
        }
    }


@router.get("/leaderboard")
async def get_streak_leaderboard(user: dict = Depends(get_current_user)):
    """Get top streak holders"""
    
    top_streaks = await db.daily_streaks.find(
        {},
        {"_id": 0, "user_id": 1, "current_streak": 1, "longest_streak": 1, "total_rewards_claimed": 1}
    ).sort("longest_streak", -1).limit(10).to_list(10)
    
    # Get user names for leaderboard
    leaderboard = []
    for i, streak in enumerate(top_streaks):
        user_data = await db.users.find_one({"id": streak["user_id"]})
        name = user_data.get("name", "Anonymous") if user_data else "Anonymous"
        # Mask name for privacy
        masked_name = name[0] + "***" + name[-1] if len(name) > 2 else name
        
        leaderboard.append({
            "rank": i + 1,
            "name": masked_name,
            "longest_streak": streak.get("longest_streak", 0),
            "current_streak": streak.get("current_streak", 0),
            "total_rewards": streak.get("total_rewards_claimed", 0)
        })
    
    return {
        "success": True,
        "leaderboard": leaderboard
    }


@router.get("/history")
async def get_reward_history(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get user's reward claim history"""
    
    user_id = user.get("id")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    claims = await db.reward_claims.find(
        {"user_id": user_id, "timestamp": {"$gte": start_date}},
        {"_id": 0}
    ).sort("timestamp", -1).limit(100).to_list(100)
    
    total_earned = sum(c.get("total_credits", 0) for c in claims)
    
    return {
        "success": True,
        "period_days": days,
        "total_earned": total_earned,
        "claim_count": len(claims),
        "history": claims
    }
