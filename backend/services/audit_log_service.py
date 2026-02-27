"""
Audit Log Service
CreatorStudio AI - Comprehensive audit logging for admin dashboard

Tracks critical user actions:
- Credit modifications (admin and automatic)
- Payment events (success, failure, refund)
- Security events (login attempts, blocks, suspicious activity)
- Generation events (for revenue tracking)
- Admin actions (user modifications, system changes)
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    # User Actions
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_REGISTER = "USER_REGISTER"
    USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE"
    USER_PROFILE_UPDATE = "USER_PROFILE_UPDATE"
    
    # Credit Events
    CREDIT_PURCHASE = "CREDIT_PURCHASE"
    CREDIT_USAGE = "CREDIT_USAGE"
    CREDIT_REFUND = "CREDIT_REFUND"
    CREDIT_ADMIN_MODIFY = "CREDIT_ADMIN_MODIFY"
    CREDIT_BONUS = "CREDIT_BONUS"
    
    # Payment Events
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    
    # Generation Events
    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    GENERATION_FAILED = "GENERATION_FAILED"
    
    # Security Events
    SECURITY_LOGIN_FAILED = "SECURITY_LOGIN_FAILED"
    SECURITY_ACCOUNT_LOCKED = "SECURITY_ACCOUNT_LOCKED"
    SECURITY_IP_BLOCKED = "SECURITY_IP_BLOCKED"
    SECURITY_SUSPICIOUS_ACTIVITY = "SECURITY_SUSPICIOUS_ACTIVITY"
    SECURITY_RATE_LIMIT = "SECURITY_RATE_LIMIT"
    SECURITY_CONTENT_BLOCKED = "SECURITY_CONTENT_BLOCKED"
    
    # Admin Actions
    ADMIN_USER_MODIFY = "ADMIN_USER_MODIFY"
    ADMIN_CREDIT_RESET = "ADMIN_CREDIT_RESET"
    ADMIN_BLOCK_IP = "ADMIN_BLOCK_IP"
    ADMIN_FORCE_LOGOUT = "ADMIN_FORCE_LOGOUT"
    ADMIN_SYSTEM_CHANGE = "ADMIN_SYSTEM_CHANGE"
    
    # Download Events
    DOWNLOAD_REQUESTED = "DOWNLOAD_REQUESTED"
    DOWNLOAD_COMPLETED = "DOWNLOAD_COMPLETED"
    DOWNLOAD_BLOCKED = "DOWNLOAD_BLOCKED"


class AuditSeverity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditLogService:
    """
    Centralized audit logging service for tracking all critical events.
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.audit_logs
    
    async def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        admin_id: Optional[str] = None,
        admin_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an audit event.
        
        Returns the audit log ID.
        """
        log_id = str(uuid.uuid4())
        
        audit_entry = {
            "id": log_id,
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": user_id,
            "user_email": user_email,
            "admin_id": admin_id,
            "admin_email": admin_email,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.collection.insert_one(audit_entry)
        
        # Log to application logger for real-time monitoring
        if severity in [AuditSeverity.WARNING, AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            logger.warning(f"AUDIT [{severity.value}]: {event_type.value} - user={user_id or admin_id} - {details}")
        
        return log_id
    
    async def log_credit_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        amount: int,
        old_balance: int,
        new_balance: int,
        reason: str,
        admin_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a credit-related event"""
        await self.log(
            event_type=event_type,
            user_id=user_id,
            details={
                "amount": amount,
                "old_balance": old_balance,
                "new_balance": new_balance,
                "reason": reason
            },
            severity=AuditSeverity.INFO if amount >= 0 else AuditSeverity.WARNING,
            admin_id=admin_id,
            ip_address=ip_address
        )
    
    async def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None,
        severity: AuditSeverity = AuditSeverity.WARNING
    ):
        """Log a security-related event"""
        await self.log(
            event_type=event_type,
            user_id=user_id,
            details=details,
            severity=severity,
            ip_address=ip_address
        )
    
    async def log_payment_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        order_id: str,
        amount: float,
        currency: str = "INR",
        gateway: str = "cashfree",
        status: str = "SUCCESS",
        failure_reason: Optional[str] = None
    ):
        """Log a payment-related event"""
        severity = AuditSeverity.INFO if status == "SUCCESS" else AuditSeverity.WARNING
        
        await self.log(
            event_type=event_type,
            user_id=user_id,
            details={
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
                "gateway": gateway,
                "status": status,
                "failure_reason": failure_reason
            },
            severity=severity
        )
    
    async def log_generation_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        generation_type: str,
        credits_used: int,
        status: str,
        generation_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Log a generation-related event"""
        severity = AuditSeverity.INFO if status == "SUCCESS" else AuditSeverity.WARNING
        
        await self.log(
            event_type=event_type,
            user_id=user_id,
            details={
                "generation_id": generation_id,
                "generation_type": generation_type,
                "credits_used": credits_used,
                "status": status,
                "error_message": error_message
            },
            severity=severity
        )
    
    async def log_admin_action(
        self,
        event_type: AuditEventType,
        admin_id: str,
        admin_email: str,
        target_user_id: Optional[str] = None,
        action: str = "",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ):
        """Log an admin action"""
        await self.log(
            event_type=event_type,
            user_id=target_user_id,
            admin_id=admin_id,
            admin_email=admin_email,
            details={
                "action": action,
                **(details or {})
            },
            severity=AuditSeverity.WARNING,  # Admin actions always warrant attention
            ip_address=ip_address
        )
    
    async def get_logs(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        size: int = 50
    ) -> Dict:
        """
        Get paginated audit logs with filters.
        """
        query = {}
        
        if event_type:
            query["event_type"] = event_type.value
        
        if user_id:
            query["$or"] = [
                {"user_id": user_id},
                {"admin_id": user_id}
            ]
        
        if severity:
            query["severity"] = severity.value
        
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date
            else:
                query["timestamp"] = {"$lte": end_date}
        
        skip = (page - 1) * size
        total = await self.collection.count_documents(query)
        
        logs = await self.collection.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).skip(skip).limit(size).to_list(size)
        
        return {
            "logs": logs,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    
    async def get_security_summary(self, days: int = 7) -> Dict:
        """
        Get a summary of security events for the dashboard.
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        security_events = [
            AuditEventType.SECURITY_LOGIN_FAILED.value,
            AuditEventType.SECURITY_ACCOUNT_LOCKED.value,
            AuditEventType.SECURITY_IP_BLOCKED.value,
            AuditEventType.SECURITY_SUSPICIOUS_ACTIVITY.value,
            AuditEventType.SECURITY_RATE_LIMIT.value,
            AuditEventType.SECURITY_CONTENT_BLOCKED.value
        ]
        
        # Count by event type
        pipeline = [
            {
                "$match": {
                    "event_type": {"$in": security_events},
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(100)
        event_counts = {r["_id"]: r["count"] for r in results}
        
        # Get total
        total_security_events = sum(event_counts.values())
        
        # Get recent critical events
        critical_events = await self.collection.find(
            {
                "event_type": {"$in": security_events},
                "severity": {"$in": ["WARNING", "ERROR", "CRITICAL"]},
                "timestamp": {"$gte": start_date}
            },
            {"_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(10)
        
        # Get unique IPs with issues
        ip_pipeline = [
            {
                "$match": {
                    "event_type": {"$in": security_events},
                    "timestamp": {"$gte": start_date},
                    "ip_address": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$ip_address",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_flagged_ips = await self.collection.aggregate(ip_pipeline).to_list(10)
        
        return {
            "period_days": days,
            "total_security_events": total_security_events,
            "event_breakdown": event_counts,
            "login_failures": event_counts.get(AuditEventType.SECURITY_LOGIN_FAILED.value, 0),
            "accounts_locked": event_counts.get(AuditEventType.SECURITY_ACCOUNT_LOCKED.value, 0),
            "ips_blocked": event_counts.get(AuditEventType.SECURITY_IP_BLOCKED.value, 0),
            "content_blocked": event_counts.get(AuditEventType.SECURITY_CONTENT_BLOCKED.value, 0),
            "rate_limits_hit": event_counts.get(AuditEventType.SECURITY_RATE_LIMIT.value, 0),
            "recent_critical_events": critical_events,
            "top_flagged_ips": [{"ip": ip["_id"], "count": ip["count"]} for ip in top_flagged_ips]
        }
    
    async def get_revenue_summary(self, days: int = 30) -> Dict:
        """
        Get revenue-related audit summary.
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Payment success
        success_pipeline = [
            {
                "$match": {
                    "event_type": AuditEventType.PAYMENT_SUCCESS.value,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$details.amount"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        success_results = await self.collection.aggregate(success_pipeline).to_list(1)
        success_data = success_results[0] if success_results else {"total_amount": 0, "count": 0}
        
        # Payment failures
        failure_count = await self.collection.count_documents({
            "event_type": AuditEventType.PAYMENT_FAILED.value,
            "timestamp": {"$gte": start_date}
        })
        
        # Refunds
        refund_pipeline = [
            {
                "$match": {
                    "event_type": AuditEventType.PAYMENT_REFUNDED.value,
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$details.amount"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        refund_results = await self.collection.aggregate(refund_pipeline).to_list(1)
        refund_data = refund_results[0] if refund_results else {"total_amount": 0, "count": 0}
        
        # Generation stats
        generation_count = await self.collection.count_documents({
            "event_type": AuditEventType.GENERATION_COMPLETED.value,
            "timestamp": {"$gte": start_date}
        })
        
        generation_failed = await self.collection.count_documents({
            "event_type": AuditEventType.GENERATION_FAILED.value,
            "timestamp": {"$gte": start_date}
        })
        
        return {
            "period_days": days,
            "revenue": {
                "total_amount": success_data.get("total_amount", 0),
                "transaction_count": success_data.get("count", 0)
            },
            "refunds": {
                "total_amount": refund_data.get("total_amount", 0),
                "count": refund_data.get("count", 0)
            },
            "payment_failures": failure_count,
            "generations": {
                "completed": generation_count,
                "failed": generation_failed,
                "success_rate": round(generation_count / (generation_count + generation_failed) * 100, 1) if (generation_count + generation_failed) > 0 else 0
            }
        }


# Singleton instance
_audit_service = None


def get_audit_service(db) -> AuditLogService:
    """Get or create the audit log service singleton"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditLogService(db)
    return _audit_service


__all__ = [
    'AuditLogService',
    'AuditEventType',
    'AuditSeverity',
    'get_audit_service'
]
