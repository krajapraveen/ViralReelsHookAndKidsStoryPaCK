"""
Daily Report Routes
API endpoints for generating and sending daily visitor reports
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from services.daily_report_service import get_report_service

router = APIRouter(prefix="/daily-report", tags=["Daily Report"])


class SendReportRequest(BaseModel):
    recipients: Optional[List[str]] = None
    date: Optional[str] = None  # YYYY-MM-DD format


def require_admin(user: dict):
    """Check if user is admin"""
    user_role = user.get("role", "").upper()
    if user_role not in ["ADMIN", "SUPERADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/preview")
async def preview_daily_report(
    date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Preview the daily report without sending
    Admin only endpoint
    """
    require_admin(user)
    
    service = get_report_service(db)
    
    report_date = None
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    try:
        report = await service.generate_daily_report(report_date)
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.post("/send")
async def send_daily_report(
    request: SendReportRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Send the daily report to specified recipients
    Admin only endpoint
    """
    require_admin(user)
    
    service = get_report_service(db)
    
    report_date = None
    if request.date:
        try:
            report_date = datetime.strptime(request.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    try:
        # Generate report
        report = await service.generate_daily_report(report_date)
        
        # Send in background
        async def send_report():
            result = await service.send_daily_report(report, request.recipients)
            logger.info(f"Daily report send result: {result}")
        
        background_tasks.add_task(send_report)
        
        return {
            "success": True,
            "message": "Daily report is being sent",
            "report_date": report["report_date"],
            "recipients": request.recipients or ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"]
        }
    except Exception as e:
        logger.error(f"Error sending daily report: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending report: {str(e)}")


@router.post("/send-now")
async def send_report_immediately(
    user: dict = Depends(get_current_user)
):
    """
    Send today's report immediately
    Admin only endpoint
    """
    require_admin(user)
    
    service = get_report_service(db)
    
    try:
        report = await service.generate_daily_report()
        result = await service.send_daily_report(report)
        
        # Log the action
        await db.audit_logs.insert_one({
            "action": "DAILY_REPORT_SENT",
            "admin_id": user.get("id"),
            "admin_email": user.get("email"),
            "report_date": report["report_date"],
            "recipients": result.get("recipients", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": result["success"],
            "message": "Daily report sent successfully" if result["success"] else "Some emails failed",
            "report_date": result["report_date"],
            "recipients": result["recipients"]
        }
    except Exception as e:
        logger.error(f"Error sending daily report: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending report: {str(e)}")


@router.get("/schedule-status")
async def get_schedule_status(user: dict = Depends(get_current_user)):
    """
    Get the status of the daily report scheduler
    Admin only endpoint
    """
    require_admin(user)
    
    # Check last sent report
    last_sent = await db.audit_logs.find_one(
        {"action": "DAILY_REPORT_SENT"},
        {"_id": 0}
    )
    
    if last_sent:
        last_sent.pop("_id", None)
    
    return {
        "success": True,
        "schedule": {
            "enabled": True,
            "time": "23:55 UTC (End of Day)",
            "recipients": ["krajapraveen@gmail.com", "krajapraveen@visionary-suite.com"],
            "timezone": "UTC"
        },
        "last_sent": last_sent
    }


@router.get("/history")
async def get_report_history(
    days: int = 7,
    user: dict = Depends(get_current_user)
):
    """
    Get history of sent daily reports
    Admin only endpoint
    """
    require_admin(user)
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    history = await db.audit_logs.find(
        {
            "action": "DAILY_REPORT_SENT",
            "timestamp": {"$gte": start_date.isoformat()}
        },
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    return {
        "success": True,
        "period_days": days,
        "total_reports_sent": len(history),
        "history": history
    }
