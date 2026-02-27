"""
Advanced Analytics Export API Routes
=====================================
Enhanced export endpoints with multiple formats,
filtering, and comprehensive data export.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_admin_user
from services.advanced_analytics_export import AnalyticsExportService, ExportFormat

router = APIRouter(prefix="/analytics-export", tags=["Analytics Export"])


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    return {
        "formats": [
            {"id": "json", "name": "JSON", "mime_type": "application/json", "supports_compression": True},
            {"id": "csv", "name": "CSV", "mime_type": "text/csv", "supports_compression": True}
        ],
        "export_types": [
            "template_analytics",
            "user_activity",
            "revenue_report",
            "system_health",
            "comprehensive"
        ]
    }


@router.get("/template-analytics")
async def export_template_analytics(
    template_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    include_details: bool = False,
    admin: dict = Depends(get_admin_user)
):
    """
    Export template analytics data
    
    Parameters:
    - template_type: Filter by specific template type
    - start_date: Start date (ISO format)
    - end_date: End date (ISO format)
    - format: json or csv
    - include_details: Include detailed records
    """
    service = AnalyticsExportService(db)
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    result = await service.export_template_analytics(
        template_type=template_type,
        start_date=start_dt,
        end_date=end_dt,
        format=format,
        include_details=include_details
    )
    
    if format == "csv":
        return Response(
            content=result["data"],
            media_type=result["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'}
        )
    
    return result["data"]


@router.get("/user-activity")
async def export_user_activity(
    user_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    admin: dict = Depends(get_admin_user)
):
    """Export user activity data"""
    service = AnalyticsExportService(db)
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    result = await service.export_user_activity(
        user_id=user_id,
        activity_type=activity_type,
        start_date=start_dt,
        end_date=end_dt,
        format=format
    )
    
    if format == "csv":
        return Response(
            content=result["data"],
            media_type=result["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'}
        )
    
    return result["data"]


@router.get("/revenue-report")
async def export_revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    format: str = "json",
    admin: dict = Depends(get_admin_user)
):
    """
    Export revenue report with aggregations
    
    Parameters:
    - group_by: day, week, or month
    """
    if group_by not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="group_by must be day, week, or month")
    
    service = AnalyticsExportService(db)
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    result = await service.export_revenue_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by,
        format=format
    )
    
    if format == "csv":
        return Response(
            content=result["data"],
            media_type=result["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'}
        )
    
    return result["data"]


@router.get("/system-health")
async def export_system_health(
    days: int = 30,
    format: str = "json",
    admin: dict = Depends(get_admin_user)
):
    """Export system health metrics"""
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    
    service = AnalyticsExportService(db)
    
    result = await service.export_system_health(days=days, format=format)
    
    if format == "csv":
        return Response(
            content=result["data"],
            media_type=result["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'}
        )
    
    return result["data"]


@router.get("/comprehensive")
async def export_comprehensive(
    include_templates: bool = True,
    include_users: bool = True,
    include_revenue: bool = True,
    include_health: bool = True,
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """
    Create comprehensive ZIP export with all data
    
    Returns a ZIP file containing all requested exports.
    """
    service = AnalyticsExportService(db)
    
    result = await service.create_comprehensive_export(
        include_templates=include_templates,
        include_users=include_users,
        include_revenue=include_revenue,
        include_health=include_health,
        days=days
    )
    
    return Response(
        content=result["data"],
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "X-Files-Included": ",".join(result["files_included"])
        }
    )


@router.get("/quick-stats")
async def get_quick_stats(
    admin: dict = Depends(get_admin_user)
):
    """Get quick statistics without full export"""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Today's stats
    today_orders = await db.orders.count_documents({
        "createdAt": {"$gte": today.isoformat()},
        "status": "SUCCESS"
    })
    
    today_jobs = await db.genstudio_jobs.count_documents({
        "createdAt": {"$gte": today.isoformat()}
    })
    
    # Weekly stats
    week_revenue_pipeline = [
        {"$match": {
            "createdAt": {"$gte": week_ago.isoformat()},
            "status": "SUCCESS"
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    week_revenue = await db.orders.aggregate(week_revenue_pipeline).to_list(1)
    
    # Monthly stats
    month_revenue_pipeline = [
        {"$match": {
            "createdAt": {"$gte": month_ago.isoformat()},
            "status": "SUCCESS"
        }},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    month_revenue = await db.orders.aggregate(month_revenue_pipeline).to_list(1)
    
    # Active users
    active_users = await db.users.count_documents({
        "lastLogin": {"$gte": week_ago.isoformat()}
    })
    
    return {
        "timestamp": now.isoformat(),
        "today": {
            "orders": today_orders,
            "jobs": today_jobs
        },
        "week": {
            "revenue": week_revenue[0]["total"] if week_revenue else 0,
            "active_users": active_users
        },
        "month": {
            "revenue": month_revenue[0]["total"] if month_revenue else 0
        }
    }
