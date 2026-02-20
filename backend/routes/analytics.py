"""
Analytics & Monitoring Dashboard Module
Tracks app usage, threat detection stats, and performance metrics
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/analytics", tags=["Analytics & Monitoring"])


# =============================================================================
# ANALYTICS TRACKING
# =============================================================================

async def track_event(user_id: str, event_type: str, event_data: dict):
    """Track an analytics event"""
    event = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "eventType": event_type,
        "eventData": event_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.analytics_events.insert_one(event)


async def track_page_view(user_id: str, page: str, referrer: str = None):
    """Track page view"""
    await track_event(user_id, "PAGE_VIEW", {"page": page, "referrer": referrer})


async def track_feature_usage(user_id: str, feature: str, action: str, metadata: dict = None):
    """Track feature usage"""
    await track_event(user_id, "FEATURE_USAGE", {
        "feature": feature,
        "action": action,
        "metadata": metadata or {}
    })


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.post("/track")
async def track_analytics_event(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Track analytics event from frontend"""
    try:
        data = await request.json()
        event_type = data.get("eventType", "CUSTOM")
        event_data = data.get("eventData", {})
        
        await track_event(user["id"], event_type, event_data)
        return {"success": True}
    except Exception as e:
        logger.error(f"Analytics tracking error: {e}")
        return {"success": False}


@router.get("/user-stats")
async def get_user_stats(user: dict = Depends(get_current_user)):
    """Get current user's usage statistics"""
    user_id = user["id"]
    now = datetime.now(timezone.utc)
    
    # Get counts for different features
    stats = {
        "storySeries": await db.story_series.count_documents({"userId": user_id}),
        "challenges": await db.content_challenges.count_documents({"userId": user_id}),
        "toneRewrites": await db.tone_rewrites.count_documents({"userId": user_id}),
        "coloringBooks": await db.coloring_book_exports.count_documents({"userId": user_id}),
        "genstudioJobs": await db.genstudio_jobs.count_documents({"userId": user_id}),
        "totalGenerations": await db.generations.count_documents({"userId": user_id}),
    }
    
    # Get credits used this month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    credits_used = await db.credit_ledger.aggregate([
        {"$match": {
            "userId": user_id,
            "entryType": "CAPTURE",
            "createdAt": {"$gte": month_start.isoformat()}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    stats["creditsUsedThisMonth"] = credits_used[0]["total"] if credits_used else 0
    stats["currentBalance"] = user.get("credits", 0)
    
    return stats


# =============================================================================
# ADMIN ENDPOINTS - MONITORING DASHBOARD
# =============================================================================

@router.get("/admin/overview")
async def get_admin_overview(admin: dict = Depends(get_admin_user)):
    """Get admin dashboard overview"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # User counts
    total_users = await db.users.count_documents({})
    active_users_today = await db.analytics_events.distinct("userId", {
        "timestamp": {"$gte": today_start.isoformat()}
    })
    new_users_week = await db.users.count_documents({
        "createdAt": {"$gte": week_start.isoformat()}
    })
    
    # Revenue (from payments)
    revenue_month = await db.payments.aggregate([
        {"$match": {"status": "SUCCESS", "createdAt": {"$gte": month_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)
    
    # Job stats
    total_jobs = await db.genstudio_jobs.count_documents({})
    successful_jobs = await db.genstudio_jobs.count_documents({"status": "SUCCEEDED"})
    failed_jobs = await db.genstudio_jobs.count_documents({"status": "FAILED"})
    
    # Feature usage
    feature_usage = {
        "storySeries": await db.story_series.count_documents({}),
        "challenges": await db.content_challenges.count_documents({}),
        "toneRewrites": await db.tone_rewrites.count_documents({}),
        "coloringBooks": await db.coloring_book_exports.count_documents({}),
        "genstudioJobs": total_jobs
    }
    
    return {
        "users": {
            "total": total_users,
            "activeToday": len(active_users_today),
            "newThisWeek": new_users_week
        },
        "revenue": {
            "thisMonth": revenue_month[0]["total"] if revenue_month else 0,
            "currency": "INR"
        },
        "jobs": {
            "total": total_jobs,
            "successful": successful_jobs,
            "failed": failed_jobs,
            "successRate": round(successful_jobs / max(total_jobs, 1) * 100, 2)
        },
        "featureUsage": feature_usage,
        "timestamp": now.isoformat()
    }


@router.get("/admin/threat-stats")
async def get_threat_stats(admin: dict = Depends(get_admin_user)):
    """Get threat detection statistics"""
    # Import directly to avoid utils package initialization issues
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location(
        "threat_detection", 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils", "threat_detection.py")
    )
    threat_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(threat_module)
    
    stats = threat_module.get_threat_stats()
    
    # Get recent security events from logs
    recent_events = await db.security_events.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    return {
        "currentStatus": stats,
        "recentEvents": recent_events,
        "rateWindows": {
            "auth": "10 requests/minute",
            "generation": "5 requests/minute",
            "export": "10 requests/minute",
            "payment": "5 requests/minute",
            "api": "100 requests/minute"
        }
    }


@router.get("/admin/app-usage")
async def get_app_usage_stats(
    admin: dict = Depends(get_admin_user),
    days: int = 30
):
    """Get detailed app usage statistics"""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Daily usage breakdown
    daily_stats = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_filter = {
            "createdAt": {
                "$gte": day_start.isoformat(),
                "$lt": day_end.isoformat()
            }
        }
        
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "storySeries": await db.story_series.count_documents(day_filter),
            "challenges": await db.content_challenges.count_documents(day_filter),
            "toneRewrites": await db.tone_rewrites.count_documents(day_filter),
            "coloringBooks": await db.coloring_book_exports.count_documents(day_filter),
            "genstudioJobs": await db.genstudio_jobs.count_documents(day_filter)
        })
    
    # Top features by usage
    feature_totals = {
        "Story Series": await db.story_series.count_documents({}),
        "Challenge Generator": await db.content_challenges.count_documents({}),
        "Tone Switcher": await db.tone_rewrites.count_documents({}),
        "Coloring Book": await db.coloring_book_exports.count_documents({}),
        "GenStudio": await db.genstudio_jobs.count_documents({})
    }
    
    return {
        "dailyStats": daily_stats[::-1],  # Oldest first
        "featureTotals": feature_totals,
        "period": f"Last {days} days"
    }


@router.get("/admin/performance")
async def get_performance_metrics(admin: dict = Depends(get_admin_user)):
    """Get system performance metrics"""
    # Job processing times
    recent_jobs = await db.genstudio_jobs.find(
        {"status": "SUCCEEDED"},
        {"_id": 0, "createdAt": 1, "updatedAt": 1, "jobType": 1}
    ).sort("createdAt", -1).limit(100).to_list(100)
    
    processing_times = {}
    for job in recent_jobs:
        try:
            created = datetime.fromisoformat(job["createdAt"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(job["updatedAt"].replace("Z", "+00:00"))
            duration = (updated - created).total_seconds()
            
            job_type = job["jobType"]
            if job_type not in processing_times:
                processing_times[job_type] = []
            processing_times[job_type].append(duration)
        except:
            pass
    
    # Calculate averages
    avg_times = {}
    for job_type, times in processing_times.items():
        if times:
            avg_times[job_type] = {
                "average": round(sum(times) / len(times), 2),
                "min": round(min(times), 2),
                "max": round(max(times), 2),
                "samples": len(times)
            }
    
    return {
        "jobProcessingTimes": avg_times,
        "dbCollections": {
            "users": await db.users.count_documents({}),
            "jobs": await db.genstudio_jobs.count_documents({}),
            "payments": await db.payments.count_documents({}),
            "ledger": await db.credit_ledger.count_documents({})
        }
    }
