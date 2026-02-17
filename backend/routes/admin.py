"""Admin routes"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from ..utils.auth import get_current_user, get_admin_user
from ..utils.database import db

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/analytics/dashboard")
async def get_admin_analytics(days: int = 30, user: dict = Depends(get_admin_user)):
    """Get admin dashboard analytics"""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    start_iso = start_date.isoformat()
    
    # User stats
    total_users = await db.users.count_documents({})
    new_users = await db.users.count_documents({"createdAt": {"$gte": start_iso}})
    
    # Generation stats
    total_generations = await db.generations.count_documents({})
    reel_generations = await db.generations.count_documents({"type": "REEL"})
    story_generations = await db.generations.count_documents({"type": "STORY"})
    recent_generations = await db.generations.count_documents({"createdAt": {"$gte": start_iso}})
    
    # Revenue stats  
    pipeline = [
        {"$match": {"status": "PAID", "createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]
    revenue_result = await db.orders.aggregate(pipeline).to_list(length=1)
    revenue = revenue_result[0] if revenue_result else {"total": 0, "count": 0}
    
    # Credit usage
    credit_pipeline = [
        {"$match": {"type": "USAGE", "createdAt": {"$gte": start_iso}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$amount"}}}}
    ]
    credit_result = await db.credit_ledger.aggregate(credit_pipeline).to_list(length=1)
    credits_used = credit_result[0].get("total", 0) if credit_result else 0
    
    # Recent activity
    recent_users = await db.users.find(
        {},
        {"_id": 0, "password": 0}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    recent_gens = await db.generations.find(
        {},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(length=10)
    
    return {
        "users": {
            "total": total_users,
            "new": new_users,
            "recentUsers": recent_users
        },
        "generations": {
            "total": total_generations,
            "reels": reel_generations,
            "stories": story_generations,
            "recent": recent_generations,
            "recentGenerations": recent_gens
        },
        "revenue": {
            "total": revenue.get("total", 0),
            "orders": revenue.get("count", 0)
        },
        "credits": {
            "used": credits_used
        },
        "period": {
            "days": days,
            "start": start_iso,
            "end": end_date.isoformat()
        }
    }


@router.get("/feedback/all")
async def get_all_feedback(user: dict = Depends(get_admin_user)):
    """Get all user feedback"""
    feedback = await db.feedback.find(
        {},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(length=1000)
    
    # Calculate stats
    total = len(feedback)
    ratings = [f.get("rating", 0) for f in feedback if f.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Category breakdown
    categories = {}
    for f in feedback:
        cat = f.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "feedback": feedback,
        "stats": {
            "total": total,
            "averageRating": round(avg_rating, 2),
            "byCategory": categories
        }
    }


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, user: dict = Depends(get_admin_user)):
    """Delete a feedback entry"""
    result = await db.feedback.delete_one({"id": feedback_id})
    if result.deleted_count == 0:
        return {"message": "Feedback not found"}
    return {"message": "Feedback deleted"}


@router.get("/analytics/track/{event}")
async def track_event(event: str):
    """Track an analytics event (placeholder)"""
    return {"status": "tracked", "event": event}


@router.get("/story-templates/stats")
async def get_story_template_stats(user: dict = Depends(get_current_user)):
    """Get story template usage statistics"""
    # Get all templates with usage stats
    templates = await db.story_templates.find(
        {},
        {"_id": 0, "id": 1, "title": 1, "genre": 1, "ageGroup": 1, "usageCount": 1}
    ).sort("usageCount", -1).to_list(length=100)
    
    # Calculate totals
    total_templates = len(templates)
    total_usage = sum(t.get("usageCount", 0) for t in templates)
    
    # Genre breakdown
    genre_stats = {}
    for t in templates:
        genre = t.get("genre", "Unknown")
        if genre not in genre_stats:
            genre_stats[genre] = {"count": 0, "usage": 0}
        genre_stats[genre]["count"] += 1
        genre_stats[genre]["usage"] += t.get("usageCount", 0)
    
    return {
        "templates": templates[:20],  # Top 20
        "stats": {
            "totalTemplates": total_templates,
            "totalUsage": total_usage,
            "byGenre": genre_stats
        }
    }
