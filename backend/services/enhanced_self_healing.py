"""
Enhanced Self-Healing System
Automatically detect and resolve issues without admin intervention
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import traceback

class IssueType(str, Enum):
    SERVICE_DOWN = "service_down"
    HIGH_ERROR_RATE = "high_error_rate"
    SLOW_RESPONSE = "slow_response"
    MEMORY_LEAK = "memory_leak"
    DATABASE_CONNECTION = "database_connection"
    PAYMENT_FAILURE = "payment_failure"
    GENERATION_FAILURE = "generation_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SelfHealingAction(str, Enum):
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RETRY_OPERATION = "retry_operation"
    FAILOVER = "failover"
    RATE_LIMIT = "rate_limit"
    AUTO_REFUND = "auto_refund"
    NOTIFY_ADMIN = "notify_admin"
    QUARANTINE = "quarantine"

class EnhancedSelfHealingSystem:
    def __init__(self, db):
        self.db = db
        self.is_active = True
        self.healing_in_progress = {}
        self.error_thresholds = {
            IssueType.HIGH_ERROR_RATE: 10,  # errors per minute
            IssueType.SLOW_RESPONSE: 5000,  # ms
            IssueType.PAYMENT_FAILURE: 3,   # consecutive failures
        }
        
    async def activate(self):
        """Activate self-healing system"""
        self.is_active = True
        await self._log_event("system", "Self-healing system activated")
        
    async def deactivate(self):
        """Deactivate self-healing system"""
        self.is_active = False
        await self._log_event("system", "Self-healing system deactivated")
    
    async def detect_issue(
        self,
        issue_type: IssueType,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect and classify an issue"""
        
        severity = self._determine_severity(issue_type, context)
        
        issue = {
            "type": issue_type.value,
            "severity": severity.value,
            "context": context,
            "detected_at": datetime.now(timezone.utc),
            "status": "detected",
            "healing_actions": []
        }
        
        # Log issue
        result = await self.db.self_healing_issues.insert_one(issue)
        issue["id"] = str(result.inserted_id)
        
        return issue
    
    def _determine_severity(self, issue_type: IssueType, context: Dict) -> IssueSeverity:
        """Determine issue severity"""
        
        if issue_type == IssueType.SERVICE_DOWN:
            return IssueSeverity.CRITICAL
        elif issue_type == IssueType.PAYMENT_FAILURE:
            return IssueSeverity.HIGH
        elif issue_type == IssueType.HIGH_ERROR_RATE:
            error_count = context.get("error_count", 0)
            if error_count > 50:
                return IssueSeverity.CRITICAL
            elif error_count > 20:
                return IssueSeverity.HIGH
            return IssueSeverity.MEDIUM
        elif issue_type == IssueType.SLOW_RESPONSE:
            response_time = context.get("response_time_ms", 0)
            if response_time > 10000:
                return IssueSeverity.HIGH
            return IssueSeverity.MEDIUM
        
        return IssueSeverity.LOW
    
    async def heal(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to heal an issue"""
        
        if not self.is_active:
            return {"success": False, "reason": "Self-healing system inactive"}
        
        issue_type = IssueType(issue["type"])
        issue_id = issue.get("id", "unknown")
        
        # Prevent duplicate healing
        if issue_id in self.healing_in_progress:
            return {"success": False, "reason": "Healing already in progress"}
        
        self.healing_in_progress[issue_id] = True
        
        try:
            # Determine healing action
            action = self._get_healing_action(issue_type, issue.get("severity", "medium"))
            
            # Execute healing
            result = await self._execute_healing_action(action, issue)
            
            # Update issue status
            await self.db.self_healing_issues.update_one(
                {"_id": issue["id"]} if "id" in issue else {"type": issue["type"]},
                {"$set": {
                    "status": "healed" if result["success"] else "failed",
                    "healing_actions": issue.get("healing_actions", []) + [action.value],
                    "healed_at": datetime.now(timezone.utc) if result["success"] else None,
                    "healing_result": result
                }}
            )
            
            await self._log_event(
                "healing",
                f"Healing {'successful' if result['success'] else 'failed'} for {issue_type.value}",
                {"action": action.value, "result": result}
            )
            
            return result
            
        except Exception as e:
            await self._log_event("error", f"Healing error: {str(e)}", {"traceback": traceback.format_exc()})
            return {"success": False, "error": str(e)}
        finally:
            if issue_id in self.healing_in_progress:
                del self.healing_in_progress[issue_id]
    
    def _get_healing_action(self, issue_type: IssueType, severity: str) -> SelfHealingAction:
        """Determine appropriate healing action"""
        
        action_map = {
            IssueType.SERVICE_DOWN: SelfHealingAction.RESTART_SERVICE,
            IssueType.HIGH_ERROR_RATE: SelfHealingAction.RATE_LIMIT,
            IssueType.SLOW_RESPONSE: SelfHealingAction.CLEAR_CACHE,
            IssueType.PAYMENT_FAILURE: SelfHealingAction.AUTO_REFUND,
            IssueType.GENERATION_FAILURE: SelfHealingAction.RETRY_OPERATION,
            IssueType.DATABASE_CONNECTION: SelfHealingAction.FAILOVER,
            IssueType.RATE_LIMIT_EXCEEDED: SelfHealingAction.QUARANTINE,
        }
        
        return action_map.get(issue_type, SelfHealingAction.NOTIFY_ADMIN)
    
    async def _execute_healing_action(
        self,
        action: SelfHealingAction,
        issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a healing action"""
        
        context = issue.get("context", {})
        
        if action == SelfHealingAction.RETRY_OPERATION:
            return await self._retry_operation(context)
        
        elif action == SelfHealingAction.AUTO_REFUND:
            return await self._auto_refund(context)
        
        elif action == SelfHealingAction.CLEAR_CACHE:
            return await self._clear_cache(context)
        
        elif action == SelfHealingAction.RATE_LIMIT:
            return await self._apply_rate_limit(context)
        
        elif action == SelfHealingAction.QUARANTINE:
            return await self._quarantine_user(context)
        
        elif action == SelfHealingAction.NOTIFY_ADMIN:
            return await self._notify_admin(issue)
        
        return {"success": False, "reason": "Unknown action"}
    
    async def _retry_operation(self, context: Dict) -> Dict[str, Any]:
        """Retry a failed operation"""
        user_id = context.get("user_id")
        operation = context.get("operation")
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Log retry attempt
                await self._log_event(
                    "retry",
                    f"Retry attempt {attempt + 1}/{max_retries}",
                    {"user_id": user_id, "operation": operation}
                )
                
                # Mark as needs retry for the worker
                if user_id and operation:
                    await self.db.pending_retries.insert_one({
                        "user_id": user_id,
                        "operation": operation,
                        "context": context,
                        "attempt": attempt + 1,
                        "created_at": datetime.now(timezone.utc)
                    })
                
                return {"success": True, "attempts": attempt + 1}
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "attempts": attempt + 1}
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "reason": "Max retries exceeded"}
    
    async def _auto_refund(self, context: Dict) -> Dict[str, Any]:
        """Auto-refund on payment/generation failure"""
        from services.auto_refund import AutoRefundService
        
        user_id = context.get("user_id")
        if not user_id:
            return {"success": False, "error": "No user_id in context"}
        
        service = AutoRefundService(self.db)
        result = await service.auto_refund_failed_generation(
            user_id=user_id,
            feature=context.get("feature", "unknown"),
            error_message=context.get("error", "Auto-refund triggered by self-healing")
        )
        
        return result
    
    async def _clear_cache(self, context: Dict) -> Dict[str, Any]:
        """Clear relevant caches"""
        # Clear template caches
        await self.db.template_cache.delete_many({})
        return {"success": True, "action": "cache_cleared"}
    
    async def _apply_rate_limit(self, context: Dict) -> Dict[str, Any]:
        """Apply temporary rate limiting"""
        await self.db.rate_limits.insert_one({
            "type": "temporary",
            "reason": "high_error_rate",
            "multiplier": 0.5,  # Reduce rate by 50%
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
            "created_at": datetime.now(timezone.utc)
        })
        return {"success": True, "action": "rate_limit_applied", "duration_minutes": 15}
    
    async def _quarantine_user(self, context: Dict) -> Dict[str, Any]:
        """Quarantine a problematic user/IP"""
        ip = context.get("ip_address")
        user_id = context.get("user_id")
        
        if ip:
            await self.db.quarantined_ips.insert_one({
                "ip": ip,
                "reason": "rate_limit_exceeded",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                "created_at": datetime.now(timezone.utc)
            })
        
        return {"success": True, "quarantined": ip or user_id}
    
    async def _notify_admin(self, issue: Dict) -> Dict[str, Any]:
        """Notify admin of unresolvable issue"""
        await self.db.admin_notifications.insert_one({
            "type": "self_healing_failure",
            "issue": issue,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })
        return {"success": True, "action": "admin_notified"}
    
    async def _log_event(self, event_type: str, message: str, data: Dict = None):
        """Log self-healing event"""
        await self.db.self_healing_logs.insert_one({
            "event_type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc)
        })
    
    async def get_status(self) -> Dict[str, Any]:
        """Get self-healing system status"""
        recent_issues = await self.db.self_healing_issues.count_documents({
            "detected_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        })
        
        healed_issues = await self.db.self_healing_issues.count_documents({
            "status": "healed",
            "healed_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        })
        
        return {
            "is_active": self.is_active,
            "healing_in_progress": len(self.healing_in_progress),
            "issues_last_24h": recent_issues,
            "healed_last_24h": healed_issues,
            "success_rate": round((healed_issues / max(recent_issues, 1)) * 100, 1)
        }

# Global instance
_self_healing_system = None

def get_self_healing_system(db):
    global _self_healing_system
    if _self_healing_system is None:
        _self_healing_system = EnhancedSelfHealingSystem(db)
    return _self_healing_system
