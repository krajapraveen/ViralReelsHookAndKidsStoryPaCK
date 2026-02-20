"""
Payment Monitoring & Alerting System
Real-time monitoring of payment flows with email and SMS alerts
"""
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("payment_monitoring")

# Configuration
ADMIN_ALERT_EMAIL = os.environ.get("ADMIN_ALERT_EMAIL", "krajapraveen@visionary-suite.com")
ALERT_SMS_NUMBER = os.environ.get("ALERT_SMS_NUMBER", "+919704248880")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "alerts@creatorstudio.ai")

# Alert thresholds
ALERT_THRESHOLDS = {
    "failure_rate_percent": 10,  # Alert if failure rate exceeds 10%
    "consecutive_failures": 3,   # Alert after 3 consecutive failures
    "webhook_signature_failures": 2,  # Alert after 2 signature failures
    "refund_amount_threshold": 10000,  # Alert for refunds > ₹10,000
    "pending_orders_threshold": 10,  # Alert if > 10 orders pending for > 30 mins
}

# In-memory tracking (can be moved to Redis for production scaling)
payment_metrics = {
    "total_attempts": 0,
    "successful": 0,
    "failed": 0,
    "consecutive_failures": 0,
    "webhook_signature_failures": 0,
    "last_success": None,
    "last_failure": None,
    "alerts_sent_today": 0,
    "last_alert_time": None,
}


async def send_email_alert(subject: str, body: str, priority: str = "HIGH"):
    """Send email alert via SendGrid"""
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured - email alert skipped")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{
                        "to": [{"email": ADMIN_ALERT_EMAIL}],
                        "subject": f"[{priority}] CreatorStudio Payment Alert: {subject}"
                    }],
                    "from": {"email": SENDER_EMAIL, "name": "CreatorStudio Alerts"},
                    "content": [{
                        "type": "text/html",
                        "value": f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; padding: 20px;">
                            <h2 style="color: {'#dc2626' if priority == 'CRITICAL' else '#f59e0b'};">
                                Payment System Alert
                            </h2>
                            <p><strong>Priority:</strong> {priority}</p>
                            <p><strong>Time:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                            <hr>
                            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
                                {body}
                            </div>
                            <hr>
                            <p style="color: #6b7280; font-size: 12px;">
                                This is an automated alert from CreatorStudio AI Payment Monitoring System.
                            </p>
                        </body>
                        </html>
                        """
                    }]
                },
                timeout=10.0
            )
            
            if response.status_code in [200, 202]:
                logger.info(f"Email alert sent: {subject}")
                return True
            else:
                logger.error(f"Email alert failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Email alert error: {e}")
        return False


async def send_sms_alert(message: str):
    """Send SMS alert via Twilio or fallback to email"""
    # For now, we'll use a webhook-based approach or log
    # In production, integrate with Twilio/MSG91/etc.
    logger.info(f"SMS Alert to {ALERT_SMS_NUMBER}: {message}")
    
    # Fallback: Send SMS content via email
    await send_email_alert(
        subject="SMS Alert",
        body=f"<p><strong>SMS to {ALERT_SMS_NUMBER}:</strong></p><p>{message}</p>",
        priority="HIGH"
    )
    return True


async def track_payment_attempt(
    order_id: str,
    status: str,
    amount: float,
    user_id: str,
    error_message: Optional[str] = None
):
    """Track payment attempt and trigger alerts if needed"""
    global payment_metrics
    
    payment_metrics["total_attempts"] += 1
    
    if status == "SUCCESS":
        payment_metrics["successful"] += 1
        payment_metrics["consecutive_failures"] = 0
        payment_metrics["last_success"] = datetime.now(timezone.utc)
        
    elif status in ["FAILED", "CANCELLED", "TIMEOUT"]:
        payment_metrics["failed"] += 1
        payment_metrics["consecutive_failures"] += 1
        payment_metrics["last_failure"] = datetime.now(timezone.utc)
        
        # Check consecutive failure threshold
        if payment_metrics["consecutive_failures"] >= ALERT_THRESHOLDS["consecutive_failures"]:
            await send_alert(
                alert_type="CONSECUTIVE_FAILURES",
                details={
                    "count": payment_metrics["consecutive_failures"],
                    "last_order_id": order_id,
                    "last_error": error_message,
                    "amount": amount
                }
            )
    
    # Check failure rate
    if payment_metrics["total_attempts"] >= 10:
        failure_rate = (payment_metrics["failed"] / payment_metrics["total_attempts"]) * 100
        if failure_rate >= ALERT_THRESHOLDS["failure_rate_percent"]:
            await send_alert(
                alert_type="HIGH_FAILURE_RATE",
                details={
                    "failure_rate": f"{failure_rate:.1f}%",
                    "total_attempts": payment_metrics["total_attempts"],
                    "failed": payment_metrics["failed"]
                }
            )


async def track_webhook_event(
    order_id: str,
    event_type: str,
    signature_valid: bool,
    payload: Dict[str, Any]
):
    """Track webhook events and signature validation"""
    global payment_metrics
    
    if not signature_valid:
        payment_metrics["webhook_signature_failures"] += 1
        
        if payment_metrics["webhook_signature_failures"] >= ALERT_THRESHOLDS["webhook_signature_failures"]:
            await send_alert(
                alert_type="WEBHOOK_SIGNATURE_FAILURE",
                details={
                    "order_id": order_id,
                    "event_type": event_type,
                    "failure_count": payment_metrics["webhook_signature_failures"],
                    "potential_attack": True
                },
                priority="CRITICAL"
            )


async def track_refund(
    order_id: str,
    refund_amount: float,
    reason: str,
    admin_email: str
):
    """Track refunds and alert on large amounts"""
    if refund_amount >= ALERT_THRESHOLDS["refund_amount_threshold"]:
        await send_alert(
            alert_type="LARGE_REFUND",
            details={
                "order_id": order_id,
                "amount": f"₹{refund_amount:,.2f}",
                "reason": reason,
                "processed_by": admin_email
            }
        )


async def send_alert(
    alert_type: str,
    details: Dict[str, Any],
    priority: str = "HIGH"
):
    """Send alert via configured channels"""
    global payment_metrics
    
    # Rate limit alerts (max 1 per minute for same type)
    now = datetime.now(timezone.utc)
    if payment_metrics["last_alert_time"]:
        time_since_last = (now - payment_metrics["last_alert_time"]).total_seconds()
        if time_since_last < 60:
            logger.info(f"Alert rate limited: {alert_type}")
            return
    
    payment_metrics["last_alert_time"] = now
    payment_metrics["alerts_sent_today"] += 1
    
    # Build alert message
    alert_messages = {
        "CONSECUTIVE_FAILURES": f"""
            <h3>Consecutive Payment Failures Detected</h3>
            <p><strong>Failure Count:</strong> {details.get('count')}</p>
            <p><strong>Last Order ID:</strong> {details.get('last_order_id')}</p>
            <p><strong>Amount:</strong> ₹{details.get('amount', 0):,.2f}</p>
            <p><strong>Error:</strong> {details.get('last_error', 'Unknown')}</p>
            <p style="color: #dc2626;"><strong>Action Required:</strong> Check Cashfree dashboard and server logs immediately.</p>
        """,
        "HIGH_FAILURE_RATE": f"""
            <h3>High Payment Failure Rate Alert</h3>
            <p><strong>Failure Rate:</strong> {details.get('failure_rate')}</p>
            <p><strong>Total Attempts:</strong> {details.get('total_attempts')}</p>
            <p><strong>Failed Payments:</strong> {details.get('failed')}</p>
            <p style="color: #dc2626;"><strong>Action Required:</strong> Review payment gateway configuration and check for issues.</p>
        """,
        "WEBHOOK_SIGNATURE_FAILURE": f"""
            <h3>⚠️ SECURITY ALERT: Webhook Signature Validation Failed</h3>
            <p><strong>Order ID:</strong> {details.get('order_id')}</p>
            <p><strong>Event Type:</strong> {details.get('event_type')}</p>
            <p><strong>Failure Count:</strong> {details.get('failure_count')}</p>
            <p style="color: #dc2626; font-weight: bold;">
                This could indicate a potential attack or misconfigured webhook secret.
                Verify your CASHFREE_WEBHOOK_SECRET immediately!
            </p>
        """,
        "LARGE_REFUND": f"""
            <h3>Large Refund Processed</h3>
            <p><strong>Order ID:</strong> {details.get('order_id')}</p>
            <p><strong>Refund Amount:</strong> {details.get('amount')}</p>
            <p><strong>Reason:</strong> {details.get('reason')}</p>
            <p><strong>Processed By:</strong> {details.get('processed_by')}</p>
        """,
        "PENDING_ORDERS": f"""
            <h3>Multiple Orders Stuck in Pending State</h3>
            <p><strong>Pending Orders:</strong> {details.get('count')}</p>
            <p><strong>Oldest Order:</strong> {details.get('oldest_order_id')}</p>
            <p><strong>Pending Since:</strong> {details.get('pending_since')}</p>
            <p style="color: #f59e0b;"><strong>Action:</strong> Run reconciliation job or check webhook delivery.</p>
        """
    }
    
    body = alert_messages.get(alert_type, f"<p>Alert Type: {alert_type}</p><pre>{details}</pre>")
    
    # Send email alert
    await send_email_alert(
        subject=alert_type.replace("_", " ").title(),
        body=body,
        priority=priority
    )
    
    # Send SMS for critical alerts
    if priority == "CRITICAL":
        sms_message = f"CRITICAL: {alert_type} - Check email for details. Order: {details.get('order_id', 'N/A')}"
        await send_sms_alert(sms_message)


async def get_payment_health_status() -> Dict[str, Any]:
    """Get current payment system health status"""
    global payment_metrics
    
    total = payment_metrics["total_attempts"]
    success_rate = (payment_metrics["successful"] / total * 100) if total > 0 else 100
    
    health = "HEALTHY"
    if payment_metrics["consecutive_failures"] >= 2:
        health = "DEGRADED"
    if payment_metrics["consecutive_failures"] >= ALERT_THRESHOLDS["consecutive_failures"]:
        health = "CRITICAL"
    
    return {
        "status": health,
        "metrics": {
            "total_attempts": total,
            "successful": payment_metrics["successful"],
            "failed": payment_metrics["failed"],
            "success_rate": f"{success_rate:.1f}%",
            "consecutive_failures": payment_metrics["consecutive_failures"],
            "webhook_signature_failures": payment_metrics["webhook_signature_failures"],
            "last_success": payment_metrics["last_success"].isoformat() if payment_metrics["last_success"] else None,
            "last_failure": payment_metrics["last_failure"].isoformat() if payment_metrics["last_failure"] else None,
        },
        "alerts_sent_today": payment_metrics["alerts_sent_today"],
        "thresholds": ALERT_THRESHOLDS
    }


def reset_daily_metrics():
    """Reset daily metrics - call at midnight"""
    global payment_metrics
    payment_metrics["total_attempts"] = 0
    payment_metrics["successful"] = 0
    payment_metrics["failed"] = 0
    payment_metrics["alerts_sent_today"] = 0
