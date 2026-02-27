"""
Admin Audit Log API Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from shared import db, get_admin_user
from services.audit_log import get_audit_logs, get_audit_log_stats, AuditAction

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin Audit Logs"])

class AuditLogQuery(BaseModel):
    admin_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    days: int = 30
    limit: int = 100
    skip: int = 0

@router.get("/actions")
async def get_action_types(admin: dict = Depends(get_admin_user)):
    """Get all available audit action types"""
    return {
        "actions": [
            {"value": action.value, "label": action.value.replace("_", " ").title()}
            for action in AuditAction
        ]
    }

@router.get("/logs")
async def list_audit_logs(
    admin_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    days: int = 30,
    limit: int = 100,
    skip: int = 0,
    admin: dict = Depends(get_admin_user)
):
    """Get paginated audit logs with filters"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    logs = await get_audit_logs(
        db,
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        limit=limit,
        skip=skip
    )
    
    # Get total count
    query = {"timestamp": {"$gte": start_date}}
    if admin_id:
        query["admin_id"] = admin_id
    if action:
        query["action"] = action
    if resource_type:
        query["resource_type"] = resource_type
    
    total = await db.admin_audit_logs.count_documents(query)
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip,
        "has_more": skip + len(logs) < total
    }

@router.get("/stats")
async def get_stats(
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get audit log statistics"""
    return await get_audit_log_stats(db, days)

@router.get("/export")
async def export_audit_logs(
    days: int = 30,
    format: str = "json",
    admin: dict = Depends(get_admin_user)
):
    """Export audit logs (JSON or CSV)"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    logs = await get_audit_logs(
        db,
        start_date=start_date,
        limit=10000
    )
    
    if format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        if logs:
            writer = csv.DictWriter(output, fieldnames=logs[0].keys())
            writer.writeheader()
            for log in logs:
                # Flatten details dict for CSV
                row = {**log}
                row["details"] = str(row.get("details", {}))
                writer.writerow(row)
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    
    return {
        "format": "json",
        "data": logs,
        "count": len(logs)
    }
