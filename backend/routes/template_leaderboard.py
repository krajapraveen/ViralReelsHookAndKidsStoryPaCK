"""
Template Performance Leaderboard & Advanced Analytics Export
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import json
import csv
import io

from shared import db, get_admin_user

router = APIRouter(prefix="/template-leaderboard", tags=["Template Leaderboard"])

# Credit values per feature
FEATURE_CREDITS = {
    "instagram_bio_generator": 5,
    "comment_reply_bank": 10,
    "bedtime_story_builder": 10,
    "youtube_thumbnail_generator": 5,
    "brand_story_builder": 18,
    "offer_generator": 20,
    "story_hook_generator": 8,
    "daily_viral_ideas": 2.5
}

# Assume $0.10 per credit for revenue calculation
CREDIT_VALUE_USD = 0.10

@router.get("/revenue-rankings")
async def get_revenue_rankings(
    days: int = 30,
    limit: int = 20,
    admin: dict = Depends(get_admin_user)
):
    """Get template revenue rankings - which templates generate most revenue"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Aggregate by feature and options
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {
                "feature": "$feature",
                "niche": {"$ifNull": ["$niche", "N/A"]},
                "tone": {"$ifNull": ["$tone", "N/A"]}
            },
            "generations": {"$sum": 1},
            "unique_users": {"$addToSet": "$user_id"}
        }},
        {"$project": {
            "feature": "$_id.feature",
            "niche": "$_id.niche",
            "tone": "$_id.tone",
            "generations": 1,
            "unique_users": {"$size": "$unique_users"}
        }},
        {"$sort": {"generations": -1}},
        {"$limit": limit}
    ]
    
    results = await db.template_analytics.aggregate(pipeline).to_list(limit)
    
    # Calculate revenue for each
    rankings = []
    for r in results:
        feature = r.get("feature", "unknown")
        generations = r.get("generations", 0)
        credits = generations * FEATURE_CREDITS.get(feature, 5)
        revenue = credits * CREDIT_VALUE_USD
        
        rankings.append({
            "rank": len(rankings) + 1,
            "feature": feature,
            "niche": r.get("niche", "N/A"),
            "tone": r.get("tone", "N/A"),
            "generations": generations,
            "unique_users": r.get("unique_users", 0),
            "credits_generated": int(credits),
            "revenue_usd": round(revenue, 2)
        })
    
    # Calculate totals
    total_revenue = sum(r["revenue_usd"] for r in rankings)
    total_generations = sum(r["generations"] for r in rankings)
    
    return {
        "rankings": rankings,
        "summary": {
            "total_revenue_usd": round(total_revenue, 2),
            "total_generations": total_generations,
            "period_days": days,
            "avg_revenue_per_gen": round(total_revenue / max(total_generations, 1), 3)
        }
    }

@router.get("/top-performers")
async def get_top_performers(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get top performing templates by different metrics"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Top by volume
    pipeline_volume = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$feature", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    by_volume = await db.template_analytics.aggregate(pipeline_volume).to_list(5)
    
    # Top by unique users
    pipeline_users = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$feature", "users": {"$addToSet": "$user_id"}}},
        {"$project": {"feature": "$_id", "user_count": {"$size": "$users"}}},
        {"$sort": {"user_count": -1}},
        {"$limit": 5}
    ]
    by_users = await db.template_analytics.aggregate(pipeline_users).to_list(5)
    
    # Top niches
    pipeline_niches = [
        {"$match": {"created_at": {"$gte": start_date}, "niche": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$niche", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_niches = await db.template_analytics.aggregate(pipeline_niches).to_list(10)
    
    # Top tones
    pipeline_tones = [
        {"$match": {"created_at": {"$gte": start_date}, "tone": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$tone", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_tones = await db.template_analytics.aggregate(pipeline_tones).to_list(10)
    
    return {
        "by_volume": [{"feature": r["_id"], "generations": r["count"]} for r in by_volume],
        "by_unique_users": [{"feature": r["feature"], "users": r["user_count"]} for r in by_users],
        "top_niches": [{"niche": r["_id"], "count": r["count"]} for r in top_niches],
        "top_tones": [{"tone": r["_id"], "count": r["count"]} for r in top_tones],
        "period_days": days
    }

@router.get("/growth-trends")
async def get_growth_trends(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get growth trends - compare current period vs previous"""
    current_start = datetime.now(timezone.utc) - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)
    
    # Current period by feature
    current_pipeline = [
        {"$match": {"created_at": {"$gte": current_start}}},
        {"$group": {"_id": "$feature", "count": {"$sum": 1}}}
    ]
    current_data = {r["_id"]: r["count"] for r in await db.template_analytics.aggregate(current_pipeline).to_list(20)}
    
    # Previous period by feature
    previous_pipeline = [
        {"$match": {"created_at": {"$gte": previous_start, "$lt": current_start}}},
        {"$group": {"_id": "$feature", "count": {"$sum": 1}}}
    ]
    previous_data = {r["_id"]: r["count"] for r in await db.template_analytics.aggregate(previous_pipeline).to_list(20)}
    
    # Calculate growth
    trends = []
    all_features = set(list(current_data.keys()) + list(previous_data.keys()))
    
    for feature in all_features:
        current = current_data.get(feature, 0)
        previous = previous_data.get(feature, 0)
        
        if previous > 0:
            growth = ((current - previous) / previous) * 100
        elif current > 0:
            growth = 100
        else:
            growth = 0
        
        trends.append({
            "feature": feature,
            "current_period": current,
            "previous_period": previous,
            "growth_percent": round(growth, 1),
            "trend": "up" if growth > 0 else ("down" if growth < 0 else "flat")
        })
    
    # Sort by growth
    trends.sort(key=lambda x: x["growth_percent"], reverse=True)
    
    return {
        "trends": trends,
        "period_days": days,
        "comparison": f"Last {days} days vs previous {days} days"
    }

# ==================== ADVANCED ANALYTICS EXPORT ====================

@router.get("/export/json")
async def export_analytics_json(
    days: int = 30,
    include_raw: bool = False,
    admin: dict = Depends(get_admin_user)
):
    """Export analytics data as JSON"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get aggregated data
    rankings = await get_revenue_rankings(days=days, limit=100, admin=admin)
    top_performers = await get_top_performers(days=days, admin=admin)
    growth_trends = await get_growth_trends(days=days, admin=admin)
    
    export_data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "revenue_rankings": rankings,
        "top_performers": top_performers,
        "growth_trends": growth_trends
    }
    
    if include_raw:
        # Include raw analytics data
        raw_data = await db.template_analytics.find(
            {"created_at": {"$gte": start_date}}
        ).to_list(10000)
        
        for r in raw_data:
            r["id"] = str(r.pop("_id"))
            r["created_at"] = r["created_at"].isoformat()
        
        export_data["raw_data"] = raw_data
    
    return {
        "format": "json",
        "data": export_data,
        "filename": f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    }

@router.get("/export/csv")
async def export_analytics_csv(
    days: int = 30,
    report_type: str = "summary",
    admin: dict = Depends(get_admin_user)
):
    """Export analytics data as CSV"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    output = io.StringIO()
    
    if report_type == "summary":
        # Summary report
        rankings_data = await get_revenue_rankings(days=days, limit=100, admin=admin)
        rankings = rankings_data.get("rankings", [])
        
        if rankings:
            writer = csv.DictWriter(output, fieldnames=rankings[0].keys())
            writer.writeheader()
            writer.writerows(rankings)
    
    elif report_type == "daily":
        # Daily breakdown
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "feature": "$feature"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.date": 1}}
        ]
        
        data = await db.template_analytics.aggregate(pipeline).to_list(1000)
        
        rows = [{"date": d["_id"]["date"], "feature": d["_id"]["feature"], "generations": d["count"]} for d in data]
        
        if rows:
            writer = csv.DictWriter(output, fieldnames=["date", "feature", "generations"])
            writer.writeheader()
            writer.writerows(rows)
    
    elif report_type == "raw":
        # Raw data export
        data = await db.template_analytics.find(
            {"created_at": {"$gte": start_date}}
        ).to_list(10000)
        
        if data:
            for d in data:
                d["id"] = str(d.pop("_id"))
                d["created_at"] = d["created_at"].isoformat()
            
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            for row in data:
                # Flatten any nested dicts
                flat_row = {}
                for k, v in row.items():
                    flat_row[k] = str(v) if isinstance(v, dict) else v
                writer.writerow(flat_row)
    
    return {
        "format": "csv",
        "data": output.getvalue(),
        "filename": f"analytics_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"
    }
