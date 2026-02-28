"""
Push Notification Service for Admin Alerts
Supports Web Push, Email, and SMS notifications for critical events
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import uuid
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user

router = APIRouter(prefix="/admin-notifications", tags=["Admin Notifications"])

# Notification Configuration
NOTIFICATION_TYPES = {
    "security_threat": {
        "name": "Security Threat",
        "severity": "critical",
        "channels": ["push", "email", "sms"],
        "icon": "🔴",
        "sound": "critical"
    },
    "high_value_conversion": {
        "name": "High-Value Conversion",
        "severity": "high",
        "channels": ["push", "email"],
        "icon": "💰",
        "sound": "success"
    },
    "failed_payment": {
        "name": "Failed Payment",
        "severity": "medium",
        "channels": ["push"],
        "icon": "⚠️",
        "sound": "warning"
    },
    "new_user_signup": {
        "name": "New User Signup",
        "severity": "low",
        "channels": ["push"],
        "icon": "👤",
        "sound": "notification"
    },
    "generation_failure": {
        "name": "Generation Failure",
        "severity": "medium",
        "channels": ["push"],
        "icon": "❌",
        "sound": "warning"
    },
    "system_alert": {
        "name": "System Alert",
        "severity": "high",
        "channels": ["push", "email"],
        "icon": "⚙️",
        "sound": "alert"
    }
}

# In-memory store for subscriptions (in production, use database)
push_subscriptions: Dict[str, List[dict]] = defaultdict(list)
notification_queue: List[dict] = []


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    user_agent: Optional[str] = None


class NotificationPreferences(BaseModel):
    security_threat: bool = True
    high_value_conversion: bool = True
    failed_payment: bool = True
    new_user_signup: bool = False
    generation_failure: bool = True
    system_alert: bool = True
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True


# ============================================================================
# NOTIFICATION CORE
# ============================================================================

async def send_notification(
    notification_type: str,
    title: str,
    message: str,
    data: dict = None,
    target_user_ids: List[str] = None,
    priority: str = "normal"
):
    """
    Send notification to admins via configured channels
    
    Args:
        notification_type: Type from NOTIFICATION_TYPES
        title: Notification title
        message: Notification body
        data: Additional data payload
        target_user_ids: Specific users to notify (None = all admins)
        priority: normal, high, critical
    """
    config = NOTIFICATION_TYPES.get(notification_type, NOTIFICATION_TYPES["system_alert"])
    
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "severity": config["severity"],
        "icon": config["icon"],
        "channels": config["channels"],
        "priority": priority,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "delivered": {}
    }
    
    # Store notification
    await db.admin_notifications.insert_one(notification)
    
    # Get admin preferences
    admins = await db.users.find(
        {"role": "ADMIN"},
        {"_id": 0, "id": 1, "email": 1, "phone": 1}
    ).to_list(100)
    
    if target_user_ids:
        admins = [a for a in admins if a["id"] in target_user_ids]
    
    for admin in admins:
        admin_id = admin["id"]
        
        # Get preferences
        prefs = await db.notification_preferences.find_one(
            {"userId": admin_id},
            {"_id": 0}
        )
        
        if not prefs:
            prefs = NotificationPreferences().model_dump()
        
        # Check if notification type is enabled
        if not prefs.get(notification_type, True):
            continue
        
        # Check quiet hours
        now_hour = datetime.now(timezone.utc).hour
        quiet_start = prefs.get("quiet_hours_start")
        quiet_end = prefs.get("quiet_hours_end")
        
        if quiet_start is not None and quiet_end is not None:
            if quiet_start <= now_hour < quiet_end:
                # In quiet hours, only send critical notifications
                if config["severity"] != "critical":
                    continue
        
        # Send via enabled channels
        delivery_status = {}
        
        # Web Push
        if "push" in config["channels"] and prefs.get("push_enabled", True):
            push_result = await send_web_push(admin_id, notification)
            delivery_status["push"] = push_result
        
        # Email
        if "email" in config["channels"] and prefs.get("email_enabled", True):
            email_result = await send_email_notification(
                admin.get("email"),
                title,
                message,
                notification_type
            )
            delivery_status["email"] = email_result
        
        # SMS (for critical only)
        if "sms" in config["channels"] and prefs.get("sms_enabled", False):
            if config["severity"] == "critical" and admin.get("phone"):
                sms_result = await send_sms_notification(
                    admin.get("phone"),
                    f"{config['icon']} {title}: {message[:100]}"
                )
                delivery_status["sms"] = sms_result
        
        # Update delivery status
        await db.admin_notifications.update_one(
            {"id": notification["id"]},
            {"$set": {f"delivered.{admin_id}": delivery_status}}
        )
    
    logger.info(f"Notification sent: {notification_type} - {title}")
    return notification


async def send_web_push(user_id: str, notification: dict) -> dict:
    """Send web push notification"""
    subscriptions = push_subscriptions.get(user_id, [])
    
    # Also fetch from database
    db_subs = await db.push_subscriptions.find(
        {"userId": user_id, "active": True},
        {"_id": 0}
    ).to_list(10)
    
    all_subs = subscriptions + db_subs
    
    if not all_subs:
        return {"status": "no_subscription"}
    
    payload = json.dumps({
        "title": notification["title"],
        "body": notification["message"],
        "icon": "/icon-192.png",
        "badge": notification["icon"],
        "data": {
            "id": notification["id"],
            "type": notification["type"],
            "url": "/app/admin/notifications"
        },
        "actions": [
            {"action": "view", "title": "View"},
            {"action": "dismiss", "title": "Dismiss"}
        ]
    })
    
    success_count = 0
    for sub in all_subs:
        try:
            # In production, use pywebpush library
            # For now, we queue for client polling
            notification_queue.append({
                "userId": user_id,
                "subscription": sub,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            success_count += 1
        except Exception as e:
            logger.error(f"Push notification error: {e}")
    
    return {"status": "queued", "sent": success_count}


async def send_email_notification(email: str, title: str, message: str, notification_type: str) -> dict:
    """Send email notification"""
    if not email:
        return {"status": "no_email"}
    
    try:
        # Use SendGrid if available
        sendgrid_key = os.environ.get("SENDGRID_API_KEY")
        
        if sendgrid_key:
            import httpx
            
            config = NOTIFICATION_TYPES.get(notification_type, {})
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">{config.get('icon', '🔔')} CreatorStudio AI</h1>
                </div>
                <div style="padding: 30px; background: #1e1b4b; color: #e0e0e0;">
                    <h2 style="color: #a78bfa; margin-top: 0;">{title}</h2>
                    <p style="font-size: 16px; line-height: 1.6;">{message}</p>
                    <div style="margin-top: 20px; padding: 15px; background: rgba(139, 92, 246, 0.2); border-radius: 8px;">
                        <p style="margin: 0; font-size: 14px; color: #a78bfa;">
                            Severity: <strong>{config.get('severity', 'medium').upper()}</strong>
                        </p>
                        <p style="margin: 5px 0 0 0; font-size: 12px; color: #888;">
                            {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                        </p>
                    </div>
                    <a href="https://visionary-suite.com/app/admin" 
                       style="display: inline-block; margin-top: 20px; padding: 12px 24px; 
                              background: #8b5cf6; color: white; text-decoration: none; 
                              border-radius: 8px; font-weight: bold;">
                        View Dashboard
                    </a>
                </div>
                <div style="padding: 15px; background: #0f0a2e; text-align: center;">
                    <p style="margin: 0; font-size: 12px; color: #666;">
                        CreatorStudio AI Admin Notifications
                    </p>
                </div>
            </div>
            """
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {sendgrid_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": email}]}],
                        "from": {"email": "noreply@visionary-suite.com", "name": "CreatorStudio AI"},
                        "subject": f"{config.get('icon', '🔔')} {title}",
                        "content": [
                            {"type": "text/plain", "value": message},
                            {"type": "text/html", "value": html_content}
                        ]
                    }
                )
                
                if response.status_code in [200, 202]:
                    return {"status": "sent"}
                else:
                    return {"status": "failed", "error": response.text}
        
        return {"status": "no_sendgrid"}
    
    except Exception as e:
        logger.error(f"Email notification error: {e}")
        return {"status": "error", "error": str(e)}


async def send_sms_notification(phone: str, message: str) -> dict:
    """Send SMS notification via Twilio"""
    if not phone:
        return {"status": "no_phone"}
    
    try:
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
        
        if twilio_sid and twilio_token and twilio_phone:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                    auth=(twilio_sid, twilio_token),
                    data={
                        "From": twilio_phone,
                        "To": phone,
                        "Body": message
                    }
                )
                
                if response.status_code in [200, 201]:
                    return {"status": "sent"}
                else:
                    return {"status": "failed", "error": response.text}
        
        return {"status": "no_twilio"}
    
    except Exception as e:
        logger.error(f"SMS notification error: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# NOTIFICATION TRIGGERS - These are called from other parts of the app
# ============================================================================

async def notify_security_threat(
    threat_type: str,
    details: str,
    ip_address: str = None,
    user_id: str = None
):
    """Notify admins about security threats"""
    await send_notification(
        notification_type="security_threat",
        title=f"Security Alert: {threat_type}",
        message=details,
        data={
            "threat_type": threat_type,
            "ip_address": ip_address,
            "user_id": user_id
        },
        priority="critical"
    )


async def notify_high_value_conversion(
    amount: float,
    currency: str,
    user_email: str,
    plan: str
):
    """Notify admins about high-value conversions"""
    threshold = 1000  # Notify for orders above ₹1000
    
    if amount >= threshold:
        await send_notification(
            notification_type="high_value_conversion",
            title=f"High-Value Conversion: ₹{amount:,.2f}",
            message=f"New {plan} subscription by {user_email}",
            data={
                "amount": amount,
                "currency": currency,
                "user_email": user_email,
                "plan": plan
            },
            priority="high"
        )


async def notify_generation_failure(
    job_id: str,
    job_type: str,
    error_message: str,
    user_id: str
):
    """Notify admins about repeated generation failures"""
    # Check if this user has multiple failures in the last hour
    hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    failure_count = await db.genstudio_jobs.count_documents({
        "userId": user_id,
        "status": "failed",
        "createdAt": {"$gte": hour_ago}
    })
    
    if failure_count >= 3:  # Multiple failures trigger notification
        await send_notification(
            notification_type="generation_failure",
            title=f"Multiple Generation Failures",
            message=f"User has {failure_count} failed {job_type} jobs in the last hour: {error_message[:100]}",
            data={
                "job_id": job_id,
                "job_type": job_type,
                "failure_count": failure_count,
                "user_id": user_id
            },
            priority="normal"
        )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/subscribe")
async def subscribe_to_push(
    subscription: PushSubscription,
    admin: dict = Depends(get_admin_user)
):
    """Subscribe to push notifications"""
    sub_data = {
        "id": str(uuid.uuid4()),
        "userId": admin["id"],
        "endpoint": subscription.endpoint,
        "keys": subscription.keys,
        "userAgent": subscription.user_agent,
        "active": True,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in database
    await db.push_subscriptions.update_one(
        {"userId": admin["id"], "endpoint": subscription.endpoint},
        {"$set": sub_data},
        upsert=True
    )
    
    # Also add to in-memory store
    push_subscriptions[admin["id"]].append(sub_data)
    
    return {"success": True, "message": "Subscribed to push notifications"}


@router.delete("/unsubscribe")
async def unsubscribe_from_push(
    endpoint: str,
    admin: dict = Depends(get_admin_user)
):
    """Unsubscribe from push notifications"""
    await db.push_subscriptions.update_one(
        {"userId": admin["id"], "endpoint": endpoint},
        {"$set": {"active": False}}
    )
    
    # Remove from in-memory store
    push_subscriptions[admin["id"]] = [
        s for s in push_subscriptions[admin["id"]]
        if s.get("endpoint") != endpoint
    ]
    
    return {"success": True, "message": "Unsubscribed from push notifications"}


@router.get("/preferences")
async def get_notification_preferences(admin: dict = Depends(get_admin_user)):
    """Get notification preferences"""
    prefs = await db.notification_preferences.find_one(
        {"userId": admin["id"]},
        {"_id": 0}
    )
    
    if not prefs:
        prefs = NotificationPreferences().model_dump()
        prefs["userId"] = admin["id"]
    
    return prefs


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    admin: dict = Depends(get_admin_user)
):
    """Update notification preferences"""
    prefs_data = preferences.model_dump()
    prefs_data["userId"] = admin["id"]
    prefs_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    await db.notification_preferences.update_one(
        {"userId": admin["id"]},
        {"$set": prefs_data},
        upsert=True
    )
    
    return {"success": True, "preferences": prefs_data}


@router.get("/list")
async def list_notifications(
    limit: int = 50,
    unread_only: bool = False,
    admin: dict = Depends(get_admin_user)
):
    """Get admin notifications"""
    query = {}
    
    if unread_only:
        query["read"] = False
    
    notifications = await db.admin_notifications.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    unread_count = await db.admin_notifications.count_documents({"read": False})
    
    return {
        "notifications": notifications,
        "total": len(notifications),
        "unreadCount": unread_count
    }


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Mark notification as read"""
    result = await db.admin_notifications.update_one(
        {"id": notification_id},
        {"$set": {"read": True, "readAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}


@router.post("/mark-all-read")
async def mark_all_notifications_read(admin: dict = Depends(get_admin_user)):
    """Mark all notifications as read"""
    result = await db.admin_notifications.update_many(
        {"read": False},
        {"$set": {"read": True, "readAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "marked": result.modified_count}


@router.get("/poll")
async def poll_notifications(admin: dict = Depends(get_admin_user)):
    """Poll for new notifications (for real-time updates without WebSocket)"""
    # Get notifications from last 30 seconds
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    
    new_notifications = await db.admin_notifications.find(
        {"timestamp": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(10)
    
    unread_count = await db.admin_notifications.count_documents({"read": False})
    
    return {
        "new": new_notifications,
        "unreadCount": unread_count,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/test")
async def send_test_notification(admin: dict = Depends(get_admin_user)):
    """Send a test notification"""
    notification = await send_notification(
        notification_type="system_alert",
        title="Test Notification",
        message="This is a test notification from CreatorStudio AI admin panel.",
        data={"test": True},
        target_user_ids=[admin["id"]],
        priority="normal"
    )
    
    return {
        "success": True,
        "message": "Test notification sent",
        "notification_id": notification["id"]
    }


# Export notification functions for use in other modules
__all__ = [
    'send_notification',
    'notify_security_threat',
    'notify_high_value_conversion',
    'notify_generation_failure'
]
