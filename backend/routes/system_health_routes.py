"""
System Health Dashboard API Routes
Provides endpoints for monitoring all critical systems
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.system_health_service import get_health_service

router = APIRouter(prefix="/system-health", tags=["System Health"])


def require_admin(user: dict):
    """Check if user is admin"""
    user_role = user.get("role", "").upper()
    if user_role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/status")
async def get_system_health_status(user: dict = Depends(get_current_user)):
    """
    Get comprehensive health status of all systems
    Returns: Database, API, Payment Gateway, Email Service status
    """
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        health_report = await health_service.check_all_systems()
        
        return {
            "success": True,
            **health_report
        }
    except Exception as e:
        logger.error(f"Health status check failed: {e}")
        return {
            "success": False,
            "overall_status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/database")
async def get_database_health(user: dict = Depends(get_current_user)):
    """Get detailed database health"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        result = await health_service.check_database_health()
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api")
async def get_api_health(user: dict = Depends(get_current_user)):
    """Get detailed API health"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        result = await health_service.check_api_health()
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/payment-gateway")
async def get_payment_health(user: dict = Depends(get_current_user)):
    """Get payment gateway health"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        result = await health_service.check_payment_gateway_health()
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Payment health check failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/email-service")
async def get_email_health(user: dict = Depends(get_current_user)):
    """Get email service health"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        result = await health_service.check_email_service_health()
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Email health check failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/alerts")
async def get_alert_history(
    days: int = 7,
    user: dict = Depends(get_current_user)
):
    """Get health alert history"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        alerts = await health_service.get_alert_history(days)
        return {
            "success": True,
            "period_days": days,
            "total": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Alert history fetch failed: {e}")
        return {"success": False, "error": str(e), "alerts": []}


@router.post("/test-alert")
async def send_test_alert(user: dict = Depends(get_current_user)):
    """Send a test health alert to verify email notifications"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        
        # Create a fake "down" service for testing
        test_service = {
            "service": "test_alert",
            "status": "DOWN",
            "error": "This is a test alert - no action required"
        }
        
        await health_service._send_health_alert(test_service)
        
        return {
            "success": True,
            "message": f"Test alert sent to {', '.join(health_service.alert_emails)}"
        }
    except Exception as e:
        logger.error(f"Test alert failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/uptime")
async def get_uptime_stats(
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get uptime statistics"""
    require_admin(user)
    
    try:
        health_service = get_health_service(db)
        stats = await health_service.get_uptime_stats(days)
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"Uptime stats fetch failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/quick-check")
async def quick_health_check():
    """
    Public quick health check endpoint
    Returns basic system status without authentication
    """
    try:
        # Just check database connectivity
        await db.command("ping")
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
