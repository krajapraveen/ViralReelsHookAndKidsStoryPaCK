"""
Auto-Refund System
Automatically refund users when:
- Output generation fails
- Service is unavailable
- Timeout occurs
- Quality threshold not met
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
import asyncio

class RefundReason:
    GENERATION_FAILED = "generation_failed"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    QUALITY_ISSUE = "quality_issue"
    USER_REQUEST = "user_request"
    SYSTEM_ERROR = "system_error"
    DUPLICATE_CHARGE = "duplicate_charge"

class AutoRefundService:
    def __init__(self, db):
        self.db = db
        self.refund_window_hours = 24  # Refunds within 24 hours
        
    async def check_and_refund(
        self,
        user_id: str,
        transaction_id: str,
        reason: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check eligibility and process refund"""
        
        # Find the transaction
        transaction = await self.db.credit_transactions.find_one({
            "_id": ObjectId(transaction_id),
            "user_id": user_id
        })
        
        if not transaction:
            # Try finding by other criteria
            transaction = await self.db.credit_transactions.find_one({
                "user_id": user_id,
                "type": "debit",
                "refunded": {"$ne": True}
            }, sort=[("created_at", -1)])
        
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
        
        # Check if already refunded
        if transaction.get("refunded"):
            return {"success": False, "error": "Already refunded"}
        
        # Check refund window
        created_at = transaction.get("created_at", datetime.now(timezone.utc))
        if datetime.now(timezone.utc) - created_at > timedelta(hours=self.refund_window_hours):
            return {"success": False, "error": "Refund window expired"}
        
        # Process refund
        credits_to_refund = abs(transaction.get("amount", 0))
        
        if credits_to_refund <= 0:
            return {"success": False, "error": "Invalid refund amount"}
        
        # Add credits back to user
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credits": credits_to_refund}}
        )
        
        # Mark transaction as refunded
        await self.db.credit_transactions.update_one(
            {"_id": transaction["_id"]},
            {"$set": {
                "refunded": True,
                "refund_reason": reason,
                "refund_details": details,
                "refunded_at": datetime.now(timezone.utc)
            }}
        )
        
        # Log refund
        await self.db.refund_logs.insert_one({
            "user_id": user_id,
            "transaction_id": str(transaction["_id"]),
            "credits_refunded": credits_to_refund,
            "reason": reason,
            "details": details,
            "auto_refund": True,
            "timestamp": datetime.now(timezone.utc)
        })
        
        return {
            "success": True,
            "credits_refunded": credits_to_refund,
            "reason": reason
        }
    
    async def auto_refund_failed_generation(
        self,
        user_id: str,
        feature: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Auto-refund when generation fails"""
        
        # Find the most recent debit for this feature
        transaction = await self.db.credit_transactions.find_one({
            "user_id": user_id,
            "feature": feature,
            "type": "debit",
            "refunded": {"$ne": True},
            "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=5)}
        }, sort=[("created_at", -1)])
        
        if not transaction:
            return {"success": False, "error": "No recent transaction found"}
        
        return await self.check_and_refund(
            user_id=user_id,
            transaction_id=str(transaction["_id"]),
            reason=RefundReason.GENERATION_FAILED,
            details=error_message
        )
    
    async def process_pending_refunds(self) -> Dict[str, Any]:
        """Process all pending refund requests"""
        
        pending = await self.db.refund_requests.find({
            "status": "pending"
        }).to_list(100)
        
        processed = 0
        failed = 0
        
        for request in pending:
            result = await self.check_and_refund(
                user_id=request["user_id"],
                transaction_id=request.get("transaction_id", ""),
                reason=request.get("reason", RefundReason.USER_REQUEST),
                details=request.get("details")
            )
            
            if result["success"]:
                await self.db.refund_requests.update_one(
                    {"_id": request["_id"]},
                    {"$set": {"status": "completed", "processed_at": datetime.now(timezone.utc)}}
                )
                processed += 1
            else:
                await self.db.refund_requests.update_one(
                    {"_id": request["_id"]},
                    {"$set": {"status": "failed", "error": result.get("error")}}
                )
                failed += 1
        
        return {
            "processed": processed,
            "failed": failed,
            "total": len(pending)
        }
    
    async def get_refund_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get refund statistics"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {
                "_id": "$reason",
                "count": {"$sum": 1},
                "total_credits": {"$sum": "$credits_refunded"}
            }}
        ]
        
        by_reason = await self.db.refund_logs.aggregate(pipeline).to_list(20)
        
        total_refunds = await self.db.refund_logs.count_documents({
            "timestamp": {"$gte": start_date}
        })
        
        total_credits = sum(r["total_credits"] for r in by_reason)
        
        return {
            "period_days": days,
            "total_refunds": total_refunds,
            "total_credits_refunded": total_credits,
            "by_reason": [{"reason": r["_id"], "count": r["count"], "credits": r["total_credits"]} for r in by_reason]
        }

# Helper function for routes
async def handle_generation_failure(db, user_id: str, feature: str, error: str):
    """Call this when a generation fails to auto-refund"""
    service = AutoRefundService(db)
    result = await service.auto_refund_failed_generation(user_id, feature, error)
    return result
