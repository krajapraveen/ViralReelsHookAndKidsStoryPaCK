"""
Admin Audit Log Service
Track all admin actions for security and compliance
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
from enum import Enum

class AuditAction(str, Enum):
    # Template Management
    TEMPLATE_CREATE = "template_create"
    TEMPLATE_UPDATE = "template_update"
    TEMPLATE_DELETE = "template_delete"
    TEMPLATE_ACTIVATE = "template_activate"
    TEMPLATE_DEACTIVATE = "template_deactivate"
    
    # User Management
    USER_ROLE_CHANGE = "user_role_change"
    USER_BAN = "user_ban"
    USER_UNBAN = "user_unban"
    USER_CREDIT_ADJUST = "user_credit_adjust"
    
    # Content Management
    CONTENT_DELETE = "content_delete"
    CONTENT_FLAG = "content_flag"
    
    # System Actions
    WEBHOOK_RETRY = "webhook_retry"
    CONFIG_UPDATE = "config_update"
    EXPORT_DATA = "export_data"
    
    # Security Actions
    IP_BLOCK = "ip_block"
    IP_UNBLOCK = "ip_unblock"
    SECURITY_ALERT = "security_alert"

async def log_admin_action(
    db,
    admin_id: str,
    admin_email: str,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> str:
    """Log an admin action to the audit log"""
    log_entry = {
        "admin_id": admin_id,
        "admin_email": admin_email,
        "action": action.value if isinstance(action, AuditAction) else action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc)
    }
    
    result = await db.admin_audit_logs.insert_one(log_entry)
    return str(result.inserted_id)

async def get_audit_logs(
    db,
    admin_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """Query audit logs with filters"""
    query = {}
    
    if admin_id:
        query["admin_id"] = admin_id
    if action:
        query["action"] = action
    if resource_type:
        query["resource_type"] = resource_type
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date
        else:
            query["timestamp"] = {"$lte": end_date}
    
    cursor = db.admin_audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(limit)
    
    for log in logs:
        log["id"] = str(log.pop("_id"))
        log["timestamp"] = log["timestamp"].isoformat()
    
    return logs

async def get_audit_log_stats(db, days: int = 30) -> Dict[str, Any]:
    """Get audit log statistics"""
    from datetime import timedelta
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Actions by type
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    actions_by_type = await db.admin_audit_logs.aggregate(pipeline).to_list(50)
    
    # Actions by admin
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_date}}},
        {"$group": {"_id": "$admin_email", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    actions_by_admin = await db.admin_audit_logs.aggregate(pipeline).to_list(10)
    
    # Total count
    total = await db.admin_audit_logs.count_documents({"timestamp": {"$gte": start_date}})
    
    return {
        "total_actions": total,
        "actions_by_type": [{"action": a["_id"], "count": a["count"]} for a in actions_by_type],
        "actions_by_admin": [{"admin": a["_id"], "count": a["count"]} for a in actions_by_admin],
        "period_days": days
    }
