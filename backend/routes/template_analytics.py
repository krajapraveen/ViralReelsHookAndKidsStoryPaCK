"""
Template Analytics Dashboard
Business Intelligence for template-based features
Admin only
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from collections import defaultdict

from shared import db, get_admin_user

router = APIRouter(prefix="/template-analytics", tags=["Template Analytics"])

# ==================== MODELS ====================
class FeatureStats(BaseModel):
    feature: str
    total_generations: int
    credits_consumed: int
    unique_users: int
    avg_generation_time_ms: float
    top_options: List[Dict[str, Any]]

class TrendingItem(BaseModel):
    name: str
    count: int
    growth_percent: float

class AnalyticsDashboard(BaseModel):
    total_generations: int
    total_credits_consumed: int
    total_unique_users: int
    features: List[FeatureStats]
    trending_niches: List[TrendingItem]
    trending_tones: List[TrendingItem]
    daily_usage: List[Dict[str, Any]]
    conversion_rate: float
    period_days: int

# ==================== FEATURE CONFIGS ====================
FEATURES = [
    "instagram_bio_generator",
    "comment_reply_bank",
    "bedtime_story_builder",
    "youtube_thumbnail_generator",
    "brand_story_builder",
    "offer_generator",
    "story_hook_generator",
    "daily_viral_ideas"
]

FEATURE_CREDITS = {
    "instagram_bio_generator": 5,
    "comment_reply_bank": 10,  # Average
    "bedtime_story_builder": 10,
    "youtube_thumbnail_generator": 5,
    "brand_story_builder": 18,
    "offer_generator": 20,
    "story_hook_generator": 8,
    "daily_viral_ideas": 2.5  # Average (free + paid)
}

# ==================== ENDPOINTS ====================
@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
) -> AnalyticsDashboard:
    """Get comprehensive template analytics dashboard"""
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate all template analytics
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$feature",
            "total": {"$sum": 1},
            "users": {"$addToSet": "$user_id"}
        }}
    ]
    
    feature_data = await db.template_analytics.aggregate(pipeline).to_list(100)
    
    total_generations = 0
    total_credits = 0
    all_users = set()
    features = []
    
    for fd in feature_data:
        feature = fd["_id"]
        count = fd["total"]
        users = fd["users"]
        
        total_generations += count
        total_credits += count * FEATURE_CREDITS.get(feature, 5)
        all_users.update(users)
        
        # Get top options for this feature
        top_options = await get_top_options(feature, start_date)
        
        features.append(FeatureStats(
            feature=feature,
            total_generations=count,
            credits_consumed=int(count * FEATURE_CREDITS.get(feature, 5)),
            unique_users=len(users),
            avg_generation_time_ms=50.0,  # Default estimate
            top_options=top_options
        ))
    
    # Get trending niches
    trending_niches = await get_trending_metric("niche", start_date, days)
    
    # Get trending tones
    trending_tones = await get_trending_metric("tone", start_date, days)
    
    # Get daily usage
    daily_usage = await get_daily_usage(start_date)
    
    # Calculate conversion rate (users who generated vs total users)
    total_users = await db.users.count_documents({"created_at": {"$gte": start_date}})
    conversion_rate = (len(all_users) / max(total_users, 1)) * 100
    
    return AnalyticsDashboard(
        total_generations=total_generations,
        total_credits_consumed=int(total_credits),
        total_unique_users=len(all_users),
        features=features,
        trending_niches=trending_niches,
        trending_tones=trending_tones,
        daily_usage=daily_usage,
        conversion_rate=round(conversion_rate, 2),
        period_days=days
    )

async def get_top_options(feature: str, start_date: datetime) -> List[Dict[str, Any]]:
    """Get top used options for a feature"""
    # Try different option fields based on feature
    option_fields = ["niche", "tone", "genre", "emotion", "industry", "age_group"]
    
    results = []
    for field in option_fields:
        pipeline = [
            {"$match": {"feature": feature, "created_at": {"$gte": start_date}, field: {"$exists": True}}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        
        data = await db.template_analytics.aggregate(pipeline).to_list(5)
        for d in data:
            if d["_id"]:
                results.append({"option": field, "value": d["_id"], "count": d["count"]})
    
    # Sort by count and return top 5
    results.sort(key=lambda x: x["count"], reverse=True)
    return results[:5]

async def get_trending_metric(field: str, start_date: datetime, days: int) -> List[TrendingItem]:
    """Get trending values for a metric with growth calculation"""
    # Current period
    pipeline_current = [
        {"$match": {"created_at": {"$gte": start_date}, field: {"$exists": True, "$ne": None}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    current_data = await db.template_analytics.aggregate(pipeline_current).to_list(10)
    
    # Previous period
    prev_start = start_date - timedelta(days=days)
    pipeline_prev = [
        {"$match": {"created_at": {"$gte": prev_start, "$lt": start_date}, field: {"$exists": True, "$ne": None}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}}
    ]
    
    prev_data = {d["_id"]: d["count"] for d in await db.template_analytics.aggregate(pipeline_prev).to_list(100)}
    
    trending = []
    for item in current_data:
        if item["_id"]:
            prev_count = prev_data.get(item["_id"], 0)
            if prev_count > 0:
                growth = ((item["count"] - prev_count) / prev_count) * 100
            else:
                growth = 100.0 if item["count"] > 0 else 0.0
            
            trending.append(TrendingItem(
                name=str(item["_id"]),
                count=item["count"],
                growth_percent=round(growth, 1)
            ))
    
    return trending

async def get_daily_usage(start_date: datetime) -> List[Dict[str, Any]]:
    """Get daily usage breakdown"""
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "total": {"$sum": 1},
            "users": {"$addToSet": "$user_id"}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {
            "date": "$_id",
            "generations": "$total",
            "unique_users": {"$size": "$users"}
        }}
    ]
    
    return await db.template_analytics.aggregate(pipeline).to_list(100)

@router.get("/feature/{feature}")
async def get_feature_analytics(
    feature: str,
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get detailed analytics for a specific feature"""
    if feature not in FEATURES:
        raise HTTPException(status_code=400, detail=f"Invalid feature. Choose from: {', '.join(FEATURES)}")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Total generations
    total = await db.template_analytics.count_documents({
        "feature": feature,
        "created_at": {"$gte": start_date}
    })
    
    # Unique users
    users_pipeline = [
        {"$match": {"feature": feature, "created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$user_id"}}
    ]
    unique_users = len(await db.template_analytics.aggregate(users_pipeline).to_list(10000))
    
    # Option breakdowns
    breakdowns = {}
    for field in ["niche", "tone", "genre", "emotion", "industry"]:
        pipeline = [
            {"$match": {"feature": feature, "created_at": {"$gte": start_date}, field: {"$exists": True}}},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        data = await db.template_analytics.aggregate(pipeline).to_list(20)
        if data:
            breakdowns[field] = [{"value": d["_id"], "count": d["count"]} for d in data if d["_id"]]
    
    # Daily trend
    daily_pipeline = [
        {"$match": {"feature": feature, "created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_trend = await db.template_analytics.aggregate(daily_pipeline).to_list(100)
    
    return {
        "feature": feature,
        "period_days": days,
        "total_generations": total,
        "unique_users": unique_users,
        "credits_per_generation": FEATURE_CREDITS.get(feature, 5),
        "total_credits": total * FEATURE_CREDITS.get(feature, 5),
        "breakdowns": breakdowns,
        "daily_trend": [{"date": d["_id"], "count": d["count"]} for d in daily_trend]
    }

@router.get("/realtime")
async def get_realtime_stats(admin: dict = Depends(get_admin_user)):
    """Get real-time stats for last hour"""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    
    pipeline = [
        {"$match": {"created_at": {"$gte": one_hour_ago}}},
        {"$group": {
            "_id": "$feature",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    stats = await db.template_analytics.aggregate(pipeline).to_list(20)
    
    total = sum(s["count"] for s in stats)
    
    return {
        "period": "1h",
        "total_generations": total,
        "by_feature": [{"feature": s["_id"], "count": s["count"]} for s in stats],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/revenue-impact")
async def get_revenue_impact(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get revenue impact of template features"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Credits consumed by feature
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$feature", "count": {"$sum": 1}}}
    ]
    
    data = await db.template_analytics.aggregate(pipeline).to_list(100)
    
    revenue_by_feature = []
    total_credits = 0
    
    for d in data:
        feature = d["_id"]
        count = d["count"]
        credits = count * FEATURE_CREDITS.get(feature, 5)
        total_credits += credits
        
        revenue_by_feature.append({
            "feature": feature,
            "generations": count,
            "credits_consumed": credits,
            "credit_value_usd": round(credits * 0.10, 2)  # Assuming $0.10 per credit
        })
    
    # Sort by credits
    revenue_by_feature.sort(key=lambda x: x["credits_consumed"], reverse=True)
    
    return {
        "period_days": days,
        "total_credits_consumed": total_credits,
        "total_revenue_usd": round(total_credits * 0.10, 2),
        "by_feature": revenue_by_feature,
        "avg_daily_revenue": round((total_credits * 0.10) / max(days, 1), 2)
    }

@router.get("/user-segments")
async def get_user_segments(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Analyze user segments by usage patterns"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Group users by generation count
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$user_id",
            "total_generations": {"$sum": 1},
            "features_used": {"$addToSet": "$feature"}
        }}
    ]
    
    user_data = await db.template_analytics.aggregate(pipeline).to_list(10000)
    
    # Segment users
    segments = {
        "power_users": 0,     # 50+ generations
        "regular_users": 0,  # 10-49 generations
        "casual_users": 0,   # 2-9 generations
        "one_time": 0        # 1 generation
    }
    
    multi_feature_users = 0
    
    for user in user_data:
        count = user["total_generations"]
        if count >= 50:
            segments["power_users"] += 1
        elif count >= 10:
            segments["regular_users"] += 1
        elif count >= 2:
            segments["casual_users"] += 1
        else:
            segments["one_time"] += 1
        
        if len(user["features_used"]) > 1:
            multi_feature_users += 1
    
    total_users = len(user_data)
    
    return {
        "period_days": days,
        "total_active_users": total_users,
        "segments": segments,
        "segment_percentages": {
            k: round((v / max(total_users, 1)) * 100, 1)
            for k, v in segments.items()
        },
        "multi_feature_users": multi_feature_users,
        "multi_feature_percent": round((multi_feature_users / max(total_users, 1)) * 100, 1)
    }
