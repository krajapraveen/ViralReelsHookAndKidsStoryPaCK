"""
Real-Time Analytics API
Provides live metrics for user activity, generation success rates, and revenue
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user

router = APIRouter(prefix="/realtime-analytics", tags=["Real-Time Analytics"])

# Store active WebSocket connections
active_connections: List[WebSocket] = []


async def get_realtime_metrics() -> Dict[str, Any]:
    """Fetch current real-time metrics from database"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # Active users (logged in within last 15 minutes)
    active_users = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": (now - timedelta(minutes=15)).isoformat()},
        "status": "success"
    })
    
    # Today's stats
    today_generations = await db.generations.count_documents({
        "createdAt": {"$gte": today_start.isoformat()}
    })
    
    today_logins = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": today_start.isoformat()},
        "status": "success"
    })
    
    # Generation success rate (last 24h)
    total_jobs_24h = await db.jobs.count_documents({
        "createdAt": {"$gte": last_24h.isoformat()}
    })
    
    successful_jobs_24h = await db.jobs.count_documents({
        "createdAt": {"$gte": last_24h.isoformat()},
        "status": "completed"
    })
    
    success_rate = round((successful_jobs_24h / max(total_jobs_24h, 1)) * 100, 1)
    
    # Revenue metrics (last 7 days)
    revenue_pipeline = [
        {"$match": {"createdAt": {"$gte": last_7d.isoformat()}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    revenue_result = await db.payments.aggregate(revenue_pipeline).to_list(1)
    revenue_7d = revenue_result[0]["total"] if revenue_result else 0
    
    # Today's revenue
    today_revenue_pipeline = [
        {"$match": {"createdAt": {"$gte": today_start.isoformat()}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    today_revenue_result = await db.payments.aggregate(today_revenue_pipeline).to_list(1)
    today_revenue = today_revenue_result[0]["total"] if today_revenue_result else 0
    
    # Generation by type (last 24h)
    gen_by_type = await db.generations.aggregate([
        {"$match": {"createdAt": {"$gte": last_24h.isoformat()}}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(20)
    
    # Credits used today
    credits_pipeline = [
        {"$match": {"timestamp": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    credits_result = await db.credit_transactions.aggregate(credits_pipeline).to_list(1)
    credits_used_today = abs(credits_result[0]["total"]) if credits_result else 0
    
    # Hourly activity (last 24 hours)
    hourly_activity = []
    for i in range(24):
        hour_start = now - timedelta(hours=i+1)
        hour_end = now - timedelta(hours=i)
        count = await db.generations.count_documents({
            "createdAt": {"$gte": hour_start.isoformat(), "$lt": hour_end.isoformat()}
        })
        hourly_activity.append({
            "hour": hour_start.strftime("%H:00"),
            "generations": count
        })
    hourly_activity.reverse()
    
    # Recent activity feed (last 10 events)
    recent_activities = []
    
    # Recent generations
    recent_gens = await db.generations.find(
        {},
        {"_id": 0, "type": 1, "createdAt": 1, "userId": 1}
    ).sort("createdAt", -1).limit(5).to_list(5)
    
    for gen in recent_gens:
        recent_activities.append({
            "type": "generation",
            "event": f"{gen.get('type', 'Content')} generated",
            "timestamp": gen.get("createdAt", ""),
            "icon": "sparkles"
        })
    
    # Recent logins
    recent_logins = await db.user_login_activity.find(
        {"status": "success"},
        {"_id": 0, "identifier": 1, "timestamp": 1, "country": 1}
    ).sort("timestamp", -1).limit(5).to_list(5)
    
    for login in recent_logins:
        recent_activities.append({
            "type": "login",
            "event": f"User logged in from {login.get('country', 'Unknown')}",
            "timestamp": login.get("timestamp", ""),
            "icon": "user"
        })
    
    # Sort by timestamp
    recent_activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    recent_activities = recent_activities[:10]
    
    # Total users
    total_users = await db.users.count_documents({})
    
    # New users today
    new_users_today = await db.users.count_documents({
        "createdAt": {"$gte": today_start.isoformat()}
    })
    
    return {
        "timestamp": now.isoformat(),
        "liveMetrics": {
            "activeUsers": active_users,
            "totalUsers": total_users,
            "newUsersToday": new_users_today,
            "todayLogins": today_logins,
            "todayGenerations": today_generations,
            "creditsUsedToday": credits_used_today
        },
        "performance": {
            "successRate": success_rate,
            "totalJobs24h": total_jobs_24h,
            "successfulJobs24h": successful_jobs_24h,
            "failedJobs24h": total_jobs_24h - successful_jobs_24h
        },
        "revenue": {
            "today": today_revenue,
            "last7Days": revenue_7d,
            "currency": "INR"
        },
        "generationsByType": [{"type": g["_id"] or "Unknown", "count": g["count"]} for g in gen_by_type],
        "hourlyActivity": hourly_activity,
        "recentActivity": recent_activities
    }


@router.get("/snapshot")
async def get_analytics_snapshot(user: dict = Depends(get_current_user)):
    """Get current analytics snapshot"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        metrics = await get_realtime_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error fetching realtime analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


@router.get("/live-stats")
async def get_live_stats(user: dict = Depends(get_current_user)):
    """Get simplified live stats for dashboard widget"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    last_5min = now - timedelta(minutes=5)
    
    # Quick stats
    active_sessions = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": last_5min.isoformat()},
        "status": "success"
    })
    
    recent_generations = await db.generations.count_documents({
        "createdAt": {"$gte": last_5min.isoformat()}
    })
    
    return {
        "activeSessions": active_sessions,
        "recentGenerations": recent_generations,
        "serverTime": now.isoformat(),
        "status": "healthy"
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send metrics every 10 seconds
            metrics = await get_realtime_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@router.get("/generation-trends")
async def get_generation_trends(user: dict = Depends(get_current_user)):
    """Get generation trends for the last 7 days"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    trends = []
    
    for i in range(7):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        count = await db.generations.count_documents({
            "createdAt": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        
        trends.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "day": day_start.strftime("%a"),
            "generations": count
        })
    
    trends.reverse()
    return {"trends": trends}


@router.get("/revenue-breakdown")
async def get_revenue_breakdown(user: dict = Depends(get_current_user)):
    """Get revenue breakdown by plan type"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    last_30d = now - timedelta(days=30)
    
    breakdown = await db.payments.aggregate([
        {"$match": {"createdAt": {"$gte": last_30d.isoformat()}, "status": "paid"}},
        {"$group": {
            "_id": "$planType",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total": -1}}
    ]).to_list(20)
    
    return {
        "breakdown": [
            {"plan": b["_id"] or "Credits", "revenue": b["total"], "transactions": b["count"]}
            for b in breakdown
        ],
        "period": "Last 30 days"
    }
