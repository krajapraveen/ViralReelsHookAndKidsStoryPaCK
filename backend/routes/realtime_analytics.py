"""
Real-Time Analytics API - Enhanced
Features:
- Live metrics with WebSocket updates
- Email alerts for unusual activity patterns
- Export to CSV/PDF
- Custom date range filters
- Granular revenue breakdowns
- Production monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import os
import sys
import io
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, get_current_user

router = APIRouter(prefix="/realtime-analytics", tags=["Real-Time Analytics"])

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# Alert thresholds configuration
ALERT_THRESHOLDS = {
    "failed_jobs_rate": 20,  # Alert if failure rate > 20%
    "failed_logins_count": 10,  # Alert if > 10 failed logins in 15 min
    "no_activity_minutes": 30,  # Alert if no activity for 30 min during business hours
    "revenue_drop_percent": 50,  # Alert if revenue drops 50% vs previous period
    "new_users_spike": 50,  # Alert if > 50 new users in 1 hour (potential bot)
}

# Store last alert times to prevent spam
last_alert_times: Dict[str, datetime] = {}
ALERT_COOLDOWN_MINUTES = 30


async def check_alert_cooldown(alert_type: str) -> bool:
    """Check if enough time has passed since last alert of this type"""
    now = datetime.now(timezone.utc)
    last_time = last_alert_times.get(alert_type)
    if last_time and (now - last_time).total_seconds() < ALERT_COOLDOWN_MINUTES * 60:
        return False
    return True


async def send_alert_email(alert_type: str, subject: str, message: str):
    """Send alert email to admin"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sendgrid_key = os.environ.get("SENDGRID_API_KEY")
        admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
        sender_email = os.environ.get("SENDER_EMAIL", "alerts@creatorstudio.ai")
        
        if not sendgrid_key or not admin_email:
            logger.warning("SendGrid not configured for alerts")
            return
        
        # Check cooldown
        if not await check_alert_cooldown(alert_type):
            logger.info(f"Alert {alert_type} skipped - cooldown active")
            return
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">⚠️ CreatorStudio AI Alert</h1>
            </div>
            <div style="background: #1a1a2e; color: #eee; padding: 20px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #ffd700;">{subject}</h2>
                <p style="line-height: 1.6;">{message}</p>
                <hr style="border-color: #333; margin: 20px 0;">
                <p style="color: #888; font-size: 12px;">
                    Alert Type: {alert_type}<br>
                    Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                    <a href="https://pipeline-debug-2.preview.emergentagent.com/app/admin/realtime-analytics" style="color: #667eea;">View Real-Time Analytics →</a>
                </p>
            </div>
        </div>
        """
        
        mail = Mail(
            from_email=sender_email,
            to_emails=admin_email,
            subject=f"[CreatorStudio Alert] {subject}",
            html_content=html_content
        )
        
        sg = SendGridAPIClient(sendgrid_key)
        sg.send(mail)
        
        # Update last alert time
        last_alert_times[alert_type] = datetime.now(timezone.utc)
        
        # Log alert
        await db.analytics_alerts.insert_one({
            "type": alert_type,
            "subject": subject,
            "message": message,
            "sentAt": datetime.now(timezone.utc).isoformat(),
            "sentTo": admin_email
        })
        
        logger.info(f"Alert email sent: {alert_type} - {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")


async def check_and_send_alerts():
    """Check metrics and send alerts if thresholds exceeded"""
    now = datetime.now(timezone.utc)
    last_15min = now - timedelta(minutes=15)
    last_hour = now - timedelta(hours=1)
    
    alerts_to_send = []
    
    # Check 1: High failure rate
    total_jobs = await db.jobs.count_documents({"createdAt": {"$gte": last_hour.isoformat()}})
    failed_jobs = await db.jobs.count_documents({
        "createdAt": {"$gte": last_hour.isoformat()},
        "status": "failed"
    })
    
    if total_jobs > 10:  # Only alert if significant activity
        failure_rate = (failed_jobs / total_jobs) * 100
        if failure_rate > ALERT_THRESHOLDS["failed_jobs_rate"]:
            alerts_to_send.append({
                "type": "high_failure_rate",
                "subject": f"High Job Failure Rate: {failure_rate:.1f}%",
                "message": f"In the last hour, {failed_jobs} out of {total_jobs} jobs failed ({failure_rate:.1f}%). This exceeds the threshold of {ALERT_THRESHOLDS['failed_jobs_rate']}%. Please investigate potential issues with AI generation services."
            })
    
    # Check 2: Failed login attempts (security)
    failed_logins = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": last_15min.isoformat()},
        "status": "failed"
    })
    
    if failed_logins > ALERT_THRESHOLDS["failed_logins_count"]:
        alerts_to_send.append({
            "type": "failed_logins_spike",
            "subject": f"Security Alert: {failed_logins} Failed Login Attempts",
            "message": f"Detected {failed_logins} failed login attempts in the last 15 minutes. This could indicate a brute force attack or credential stuffing attempt. Consider implementing additional security measures."
        })
    
    # Check 3: Unusual new user spike (potential bot registration)
    new_users = await db.users.count_documents({
        "createdAt": {"$gte": last_hour.isoformat()}
    })
    
    if new_users > ALERT_THRESHOLDS["new_users_spike"]:
        alerts_to_send.append({
            "type": "new_users_spike",
            "subject": f"Unusual Activity: {new_users} New Registrations",
            "message": f"Detected {new_users} new user registrations in the last hour. This is unusually high and could indicate bot activity. Please review recent registrations and consider implementing CAPTCHA if not already enabled."
        })
    
    # Send all alerts
    for alert in alerts_to_send:
        await send_alert_email(alert["type"], alert["subject"], alert["message"])


async def get_realtime_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Fetch current real-time metrics from database with optional date range"""
    now = datetime.now(timezone.utc)
    
    # Use custom date range or defaults
    if start_date and end_date:
        period_start = start_date
        period_end = end_date
    else:
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_hour = now - timedelta(hours=1)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # Active users (logged in within last 15 minutes)
    active_users = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": (now - timedelta(minutes=15)).isoformat()},
        "status": "success"
    })
    
    # Period stats
    period_generations = await db.generations.count_documents({
        "createdAt": {"$gte": period_start.isoformat(), "$lte": period_end.isoformat()}
    })
    
    period_logins = await db.user_login_activity.count_documents({
        "timestamp": {"$gte": period_start.isoformat(), "$lte": period_end.isoformat()},
        "status": "success"
    })
    
    # Today's stats (always show today regardless of filter)
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
    
    # Period revenue
    period_revenue_pipeline = [
        {"$match": {"createdAt": {"$gte": period_start.isoformat(), "$lte": period_end.isoformat()}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    period_revenue_result = await db.payments.aggregate(period_revenue_pipeline).to_list(1)
    period_revenue = period_revenue_result[0]["total"] if period_revenue_result else 0
    
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
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat()
        },
        "liveMetrics": {
            "activeUsers": active_users,
            "totalUsers": total_users,
            "newUsersToday": new_users_today,
            "todayLogins": today_logins,
            "todayGenerations": today_generations,
            "creditsUsedToday": credits_used_today,
            "periodGenerations": period_generations,
            "periodLogins": period_logins
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
            "periodRevenue": period_revenue,
            "currency": "INR"
        },
        "generationsByType": [{"type": g["_id"] or "Unknown", "count": g["count"]} for g in gen_by_type],
        "hourlyActivity": hourly_activity,
        "recentActivity": recent_activities
    }


@router.get("/snapshot")
async def get_analytics_snapshot(
    user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    background_tasks: BackgroundTasks = None
):
    """Get current analytics snapshot with optional date range filter"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Parse date range if provided
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        
        metrics = await get_realtime_metrics(start, end)
        
        # Check for alerts in background
        if background_tasks:
            background_tasks.add_task(check_and_send_alerts)
        
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
        # Send initial data
        metrics = await get_realtime_metrics()
        await websocket.send_json({"type": "snapshot", "data": metrics})
        
        while True:
            # Wait for client messages or timeout for periodic updates
            try:
                # Check for client commands (with 10 second timeout)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                
                if data.get("command") == "refresh":
                    metrics = await get_realtime_metrics()
                    await websocket.send_json({"type": "snapshot", "data": metrics})
                elif data.get("command") == "subscribe":
                    # Client subscribing to specific metric updates
                    pass
                    
            except asyncio.TimeoutError:
                # Send periodic update
                metrics = await get_realtime_metrics()
                await websocket.send_json({"type": "update", "data": metrics})
                
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@router.get("/generation-trends")
async def get_generation_trends(
    user: dict = Depends(get_current_user),
    days: int = Query(7, ge=1, le=90, description="Number of days to fetch")
):
    """Get generation trends for specified number of days"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    trends = []
    
    for i in range(days):
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
    return {"trends": trends, "days": days}


@router.get("/revenue-breakdown")
async def get_revenue_breakdown(
    user: dict = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    group_by: str = Query("plan", description="Group by: plan, day, week, month")
):
    """Get detailed revenue breakdown with multiple grouping options"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    result = {
        "period": f"Last {days} days",
        "startDate": start_date.isoformat(),
        "endDate": now.isoformat()
    }
    
    # Revenue by plan type
    plan_breakdown = await db.payments.aggregate([
        {"$match": {"createdAt": {"$gte": start_date.isoformat()}, "status": "paid"}},
        {"$group": {
            "_id": "$planType",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1},
            "avgTransaction": {"$avg": "$amount"}
        }},
        {"$sort": {"total": -1}}
    ]).to_list(20)
    
    result["byPlan"] = [
        {
            "plan": b["_id"] or "Credits",
            "revenue": b["total"],
            "transactions": b["count"],
            "avgTransaction": round(b["avgTransaction"], 2) if b["avgTransaction"] else 0
        }
        for b in plan_breakdown
    ]
    
    # Daily revenue trend
    daily_revenue = []
    for i in range(min(days, 30)):  # Max 30 days for daily view
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_total = await db.payments.aggregate([
            {"$match": {
                "createdAt": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()},
                "status": "paid"
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]).to_list(1)
        
        daily_revenue.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "day": day_start.strftime("%a"),
            "revenue": day_total[0]["total"] if day_total else 0,
            "transactions": day_total[0]["count"] if day_total else 0
        })
    
    daily_revenue.reverse()
    result["dailyTrend"] = daily_revenue
    
    # Revenue by payment method
    method_breakdown = await db.payments.aggregate([
        {"$match": {"createdAt": {"$gte": start_date.isoformat()}, "status": "paid"}},
        {"$group": {
            "_id": "$paymentMethod",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total": -1}}
    ]).to_list(10)
    
    result["byPaymentMethod"] = [
        {"method": m["_id"] or "Unknown", "revenue": m["total"], "transactions": m["count"]}
        for m in method_breakdown
    ]
    
    # Top spending users
    top_users = await db.payments.aggregate([
        {"$match": {"createdAt": {"$gte": start_date.isoformat()}, "status": "paid"}},
        {"$group": {
            "_id": "$userId",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # Get user emails for top spenders
    user_details = []
    for u in top_users:
        user_doc = await db.users.find_one({"id": u["_id"]}, {"_id": 0, "email": 1, "name": 1})
        user_details.append({
            "userId": u["_id"],
            "email": user_doc.get("email", "Unknown") if user_doc else "Unknown",
            "name": user_doc.get("name", "") if user_doc else "",
            "totalSpent": u["total"],
            "transactions": u["count"]
        })
    
    result["topUsers"] = user_details
    
    # Summary totals
    total_revenue = sum(b["total"] for b in plan_breakdown)
    total_transactions = sum(b["count"] for b in plan_breakdown)
    
    result["summary"] = {
        "totalRevenue": total_revenue,
        "totalTransactions": total_transactions,
        "avgTransactionValue": round(total_revenue / max(total_transactions, 1), 2),
        "currency": "INR"
    }
    
    return result


@router.get("/export/csv")
async def export_analytics_csv(
    user: dict = Depends(get_current_user),
    data_type: str = Query("overview", description="Data type: overview, generations, revenue, users"),
    days: int = Query(30, ge=1, le=365)
):
    """Export analytics data to CSV"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    if data_type == "overview":
        # Daily overview
        writer.writerow(["Date", "Generations", "Logins", "New Users", "Revenue (INR)", "Credits Used"])
        
        for i in range(days):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            gens = await db.generations.count_documents({
                "createdAt": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
            })
            logins = await db.user_login_activity.count_documents({
                "timestamp": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()},
                "status": "success"
            })
            new_users = await db.users.count_documents({
                "createdAt": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
            })
            
            rev_result = await db.payments.aggregate([
                {"$match": {"createdAt": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}, "status": "paid"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]).to_list(1)
            revenue = rev_result[0]["total"] if rev_result else 0
            
            credits_result = await db.credit_transactions.aggregate([
                {"$match": {"timestamp": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]).to_list(1)
            credits = abs(credits_result[0]["total"]) if credits_result else 0
            
            writer.writerow([day_start.strftime("%Y-%m-%d"), gens, logins, new_users, revenue, credits])
    
    elif data_type == "generations":
        writer.writerow(["Date", "Time", "Type", "User ID", "Status", "Credits Used"])
        
        generations = await db.generations.find(
            {"createdAt": {"$gte": start_date.isoformat()}},
            {"_id": 0, "createdAt": 1, "type": 1, "userId": 1, "status": 1, "creditsUsed": 1}
        ).sort("createdAt", -1).limit(10000).to_list(10000)
        
        for gen in generations:
            created = gen.get("createdAt", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    date_str = time_str = created
            else:
                date_str = time_str = ""
            
            writer.writerow([
                date_str,
                time_str,
                gen.get("type", ""),
                gen.get("userId", ""),
                gen.get("status", ""),
                gen.get("creditsUsed", 0)
            ])
    
    elif data_type == "revenue":
        writer.writerow(["Date", "Time", "Amount (INR)", "Plan Type", "Payment Method", "User ID", "Status"])
        
        payments = await db.payments.find(
            {"createdAt": {"$gte": start_date.isoformat()}},
            {"_id": 0}
        ).sort("createdAt", -1).limit(10000).to_list(10000)
        
        for payment in payments:
            created = payment.get("createdAt", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    date_str = time_str = created
            else:
                date_str = time_str = ""
            
            writer.writerow([
                date_str,
                time_str,
                payment.get("amount", 0),
                payment.get("planType", ""),
                payment.get("paymentMethod", ""),
                payment.get("userId", ""),
                payment.get("status", "")
            ])
    
    elif data_type == "users":
        writer.writerow(["User ID", "Email", "Name", "Role", "Credits", "Created Date", "Last Login"])
        
        users = await db.users.find(
            {},
            {"_id": 0, "id": 1, "email": 1, "name": 1, "role": 1, "credits": 1, "createdAt": 1}
        ).sort("createdAt", -1).limit(10000).to_list(10000)
        
        for u in users:
            # Get last login
            last_login = await db.user_login_activity.find_one(
                {"user_id": u.get("id"), "status": "success"},
                {"_id": 0, "timestamp": 1},
                sort=[("timestamp", -1)]
            )
            
            writer.writerow([
                u.get("id", ""),
                u.get("email", ""),
                u.get("name", ""),
                u.get("role", "USER"),
                u.get("credits", 0),
                u.get("createdAt", ""),
                last_login.get("timestamp", "") if last_login else ""
            ])
    
    output.seek(0)
    
    filename = f"creatorstudio_{data_type}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/pdf")
async def export_analytics_pdf(
    user: dict = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30)
):
    """Export analytics summary to PDF"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation not available")
    
    now = datetime.now(timezone.utc)
    metrics = await get_realtime_metrics()
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(102, 126, 234)
    pdf.cell(0, 15, "CreatorStudio AI Analytics Report", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5, f"Period: Last {days} days", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    
    # Live Metrics Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Live Metrics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(102, 126, 234)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 11)
    live = metrics.get("liveMetrics", {})
    metrics_data = [
        ("Active Users", live.get("activeUsers", 0)),
        ("Total Users", live.get("totalUsers", 0)),
        ("New Users Today", live.get("newUsersToday", 0)),
        ("Today's Generations", live.get("todayGenerations", 0)),
        ("Today's Logins", live.get("todayLogins", 0)),
        ("Credits Used Today", live.get("creditsUsedToday", 0)),
    ]
    
    for label, value in metrics_data:
        pdf.cell(80, 8, label + ":", 0)
        pdf.cell(0, 8, str(value), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Performance Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Performance (Last 24 Hours)", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 11)
    perf = metrics.get("performance", {})
    pdf.cell(80, 8, "Success Rate:", 0)
    pdf.cell(0, 8, f"{perf.get('successRate', 0)}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 8, "Total Jobs:", 0)
    pdf.cell(0, 8, str(perf.get('totalJobs24h', 0)), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 8, "Successful Jobs:", 0)
    pdf.cell(0, 8, str(perf.get('successfulJobs24h', 0)), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 8, "Failed Jobs:", 0)
    pdf.cell(0, 8, str(perf.get('failedJobs24h', 0)), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Revenue Section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Revenue", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 11)
    rev = metrics.get("revenue", {})
    pdf.cell(80, 8, "Today's Revenue:", 0)
    pdf.cell(0, 8, f"INR {rev.get('today', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(80, 8, "Last 7 Days:", 0)
    pdf.cell(0, 8, f"INR {rev.get('last7Days', 0):,.2f}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Generations by Type
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Generations by Type (24h)", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "", 11)
    for gen_type in metrics.get("generationsByType", [])[:10]:
        pdf.cell(80, 8, gen_type.get("type", "Unknown") + ":", 0)
        pdf.cell(0, 8, str(gen_type.get("count", 0)), new_x="LMARGIN", new_y="NEXT")
    
    # Footer
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, "CreatorStudio AI - Confidential Analytics Report", new_x="LMARGIN", new_y="NEXT", align="C")
    
    # Output PDF
    pdf_output = bytes(pdf.output())
    
    filename = f"creatorstudio_analytics_{now.strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/alerts/history")
async def get_alert_history(
    user: dict = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30)
):
    """Get history of sent alerts"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    alerts = await db.analytics_alerts.find(
        {"sentAt": {"$gte": start_date.isoformat()}},
        {"_id": 0}
    ).sort("sentAt", -1).limit(100).to_list(100)
    
    return {"alerts": alerts, "period": f"Last {days} days"}


@router.post("/alerts/test")
async def test_alert(user: dict = Depends(get_current_user)):
    """Send a test alert email"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await send_alert_email(
        "test_alert",
        "Test Alert - System Working",
        "This is a test alert to verify that the email notification system is working correctly. No action is required."
    )
    
    return {"success": True, "message": "Test alert sent"}


@router.get("/alerts/config")
async def get_alert_config(user: dict = Depends(get_current_user)):
    """Get current alert threshold configuration"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "thresholds": ALERT_THRESHOLDS,
        "cooldownMinutes": ALERT_COOLDOWN_MINUTES,
        "emailConfigured": bool(os.environ.get("SENDGRID_API_KEY") and os.environ.get("ADMIN_ALERT_EMAIL"))
    }


@router.get("/monitoring/health")
async def get_system_health(user: dict = Depends(get_current_user)):
    """Get comprehensive system health metrics for production monitoring"""
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc)
    last_5min = now - timedelta(minutes=5)
    last_hour = now - timedelta(hours=1)
    
    # Database health
    try:
        await db.command("ping")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Recent error rate
    total_jobs = await db.jobs.count_documents({"createdAt": {"$gte": last_hour.isoformat()}})
    failed_jobs = await db.jobs.count_documents({
        "createdAt": {"$gte": last_hour.isoformat()},
        "status": "failed"
    })
    error_rate = round((failed_jobs / max(total_jobs, 1)) * 100, 2)
    
    # API response tracking (if implemented)
    avg_response_time = "N/A"  # Would need middleware tracking
    
    # Active connections
    websocket_connections = len(active_connections)
    
    # Recent activity indicator
    recent_activity = await db.generations.count_documents({
        "createdAt": {"$gte": last_5min.isoformat()}
    })
    
    # Memory/CPU would need psutil (optional)
    try:
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
    except ImportError:
        cpu_percent = "N/A"
        memory_percent = "N/A"
    
    return {
        "timestamp": now.isoformat(),
        "status": "healthy" if db_status == "healthy" and error_rate < 20 else "degraded",
        "components": {
            "database": db_status,
            "api": "healthy",
            "websocket": f"{websocket_connections} active connections"
        },
        "metrics": {
            "errorRate1h": f"{error_rate}%",
            "totalJobs1h": total_jobs,
            "failedJobs1h": failed_jobs,
            "recentActivity5min": recent_activity,
            "avgResponseTime": avg_response_time
        },
        "system": {
            "cpuPercent": cpu_percent,
            "memoryPercent": memory_percent
        },
        "alerts": {
            "configured": bool(os.environ.get("SENDGRID_API_KEY")),
            "lastAlertsSent": len(last_alert_times)
        }
    }
