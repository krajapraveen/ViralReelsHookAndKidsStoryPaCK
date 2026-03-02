"""
Database Environment Monitoring Routes
API endpoints for monitoring database environment and triggering alerts
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/environment-monitor", tags=["Environment Monitoring"])

# Get database configuration
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "")


def require_admin(user: dict):
    """Check if user is admin"""
    user_role = user.get("role", "").upper()
    if user_role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_monitor():
    """Get or create environment monitor instance"""
    from services.database_environment_monitor import get_environment_monitor
    return get_environment_monitor(db, DB_NAME, MONGO_URL)


@router.get("/status")
async def get_environment_status(user: dict = Depends(get_current_user)):
    """Get current environment status"""
    require_admin(user)
    
    monitor = get_monitor()
    status = await monitor.get_environment_status()
    
    return {
        "success": True,
        "data": status
    }


@router.get("/check")
async def check_environment(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Check for environment mismatches and trigger alerts if needed.
    This endpoint can be called periodically by a cron job or monitoring service.
    """
    require_admin(user)
    
    monitor = get_monitor()
    
    # Get request domain
    host = request.headers.get("host", "")
    origin = request.headers.get("origin", "")
    request_domain = origin or host
    
    result = await monitor.check_environment_mismatch(request_domain)
    
    return {
        "success": True,
        "check_result": result
    }


@router.post("/check-production")
async def check_production_environment(
    user: dict = Depends(get_current_user)
):
    """
    Explicitly check if production domain is using correct database.
    Simulates a request from www.visionary-suite.com
    """
    require_admin(user)
    
    monitor = get_monitor()
    
    # Simulate production domain request
    result = await monitor.check_environment_mismatch("www.visionary-suite.com")
    
    return {
        "success": True,
        "production_check": result,
        "message": "Alert sent" if result.get("mismatch_detected") else "No mismatch detected"
    }


@router.get("/alerts")
async def get_environment_alerts(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get history of environment alerts"""
    require_admin(user)
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    alerts = await db.environment_alerts.find(
        {"timestamp": {"$gte": start_date.isoformat()}},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    return {
        "success": True,
        "period_days": days,
        "total_alerts": len(alerts),
        "alerts": alerts
    }


@router.get("/database-info")
async def get_database_info(user: dict = Depends(get_current_user)):
    """Get current database connection information"""
    require_admin(user)
    
    monitor = get_monitor()
    env_info = monitor.detect_environment()
    
    # Get database stats
    try:
        stats = await db.command("dbStats")
        db_stats = {
            "collections": stats.get("collections", 0),
            "objects": stats.get("objects", 0),
            "dataSize": stats.get("dataSize", 0),
            "storageSize": stats.get("storageSize", 0)
        }
    except Exception as e:
        db_stats = {"error": str(e)}
    
    return {
        "success": True,
        "database": {
            "name": DB_NAME,
            "environment": env_info["detected_environment"],
            "is_production": env_info["is_production_db"],
            "connection": env_info["mongo_url_masked"],
            "is_localhost": env_info["is_localhost"],
            "is_cloud": env_info["is_cloud_db"]
        },
        "stats": db_stats
    }


@router.post("/test-alert")
async def send_test_alert(user: dict = Depends(get_current_user)):
    """Send a test alert to verify email configuration"""
    require_admin(user)
    
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    SENDER_EMAIL = os.environ.get("SENDGRID_FROM_EMAIL", "alerts@visionary-suite.com")
    
    if not SENDGRID_API_KEY:
        return {"success": False, "error": "SendGrid not configured"}
    
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    
    results = []
    recipients = ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]
    
    for recipient in recipients:
        try:
            message = Mail(
                from_email=Email(SENDER_EMAIL, "Visionary Suite Alerts"),
                to_emails=To(recipient),
                subject="✅ Test Alert - Database Environment Monitor Active",
                html_content=f"""
                <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #10b981;">✅ Database Environment Monitor Test</h2>
                    <p>This is a test alert to confirm the monitoring system is working correctly.</p>
                    <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 15px 0;">
                        <p><strong>Current Database:</strong> {DB_NAME}</p>
                        <p><strong>Timestamp:</strong> {datetime.now(timezone.utc).isoformat()}</p>
                        <p><strong>Triggered By:</strong> {user.get('email')}</p>
                    </div>
                    <p style="color: #6b7280; font-size: 12px;">
                        The monitoring system will alert you if www.visionary-suite.com connects to a QA or Preview database.
                    </p>
                </body>
                </html>
                """
            )
            
            response = sg.send(message)
            results.append({
                "recipient": recipient,
                "success": response.status_code in [200, 201, 202],
                "status_code": response.status_code
            })
        except Exception as e:
            results.append({
                "recipient": recipient,
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": all(r["success"] for r in results),
        "message": "Test alerts sent",
        "results": results
    }


@router.get("/health-check")
async def environment_health_check():
    """
    Public health check endpoint that includes environment info.
    Can be called by external monitoring services.
    """
    monitor = get_monitor()
    env_info = monitor.detect_environment()
    
    # Determine if this is a healthy state
    is_healthy = env_info["is_production_db"] and not env_info["is_qa_db"] and not env_info["is_preview_db"]
    
    return {
        "status": "healthy" if is_healthy else "warning",
        "database": env_info["database_name"],
        "environment": env_info["detected_environment"],
        "is_production": env_info["is_production_db"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }
