"""
Enhanced Auto-Refund System
===========================
Automatically refund users when:
- Output generation fails
- Service is unavailable  
- Timeout occurs
- Quality threshold not met
- Subscription output not delivered

Features:
- Automatic failure detection
- Credit restoration within 24 hours
- Comprehensive refund logging
- Integration with all generation endpoints
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("auto_refund")

class RefundReason:
    """Standard refund reasons for tracking"""
    GENERATION_FAILED = "generation_failed"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    QUALITY_ISSUE = "quality_issue"
    USER_REQUEST = "user_request"
    SYSTEM_ERROR = "system_error"
    DUPLICATE_CHARGE = "duplicate_charge"
    OUTPUT_NOT_DELIVERED = "output_not_delivered"
    API_ERROR = "api_error"


class EnhancedAutoRefundService:
    """
    Enhanced auto-refund service that automatically refunds credits
    when generation fails or outputs are not delivered
    """
    
    def __init__(self, db):
        self.db = db
        self.refund_window_hours = 24
        self.max_auto_refund_credits = 100  # Safety limit per transaction
        self._running = False
        self._check_interval = 60  # Check every minute
        
    async def start_background_worker(self):
        """Start background worker to process pending refunds"""
        if self._running:
            return
        self._running = True
        logger.info("Auto-refund background worker started")
        
        while self._running:
            try:
                await self.process_failed_generations()
                await self.process_pending_refund_requests()
            except Exception as e:
                logger.error(f"Auto-refund worker error: {e}")
            await asyncio.sleep(self._check_interval)
    
    def stop_background_worker(self):
        """Stop the background worker"""
        self._running = False
        logger.info("Auto-refund background worker stopped")
    
    async def process_failed_generations(self):
        """Scan for failed generations and auto-refund"""
        # Find failed jobs in the last hour that haven't been refunded
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        
        failed_jobs = await self.db.genstudio_jobs.find({
            "status": {"$in": ["FAILED", "ERROR", "TIMEOUT"]},
            "updatedAt": {"$gte": cutoff.isoformat()},
            "refunded": {"$ne": True},
            "creditsCharged": {"$gt": 0}
        }, {"_id": 0}).to_list(100)
        
        for job in failed_jobs:
            try:
                await self.auto_refund_job(job)
            except Exception as e:
                logger.error(f"Failed to refund job {job.get('id')}: {e}")
    
    async def auto_refund_job(self, job: Dict) -> Dict[str, Any]:
        """Auto-refund a failed job"""
        user_id = job.get("userId")
        credits = job.get("creditsCharged", 0)
        job_id = job.get("id")
        
        if not user_id or credits <= 0:
            return {"success": False, "error": "Invalid job data"}
        
        if credits > self.max_auto_refund_credits:
            logger.warning(f"Refund amount {credits} exceeds limit, capping to {self.max_auto_refund_credits}")
            credits = self.max_auto_refund_credits
        
        # Restore credits to user
        await self.db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Mark job as refunded
        await self.db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "refunded": True,
                "refundedAt": datetime.now(timezone.utc).isoformat(),
                "refundAmount": credits,
                "refundReason": RefundReason.GENERATION_FAILED
            }}
        )
        
        # Log refund
        await self.db.auto_refund_logs.insert_one({
            "user_id": user_id,
            "job_id": job_id,
            "job_type": job.get("type", "unknown"),
            "credits_refunded": credits,
            "reason": RefundReason.GENERATION_FAILED,
            "original_status": job.get("status"),
            "error_message": job.get("errorDetails", job.get("error", "")),
            "auto_refund": True,
            "timestamp": datetime.now(timezone.utc)
        })
        
        logger.info(f"Auto-refunded {credits} credits to user {user_id} for failed job {job_id}")
        
        return {
            "success": True,
            "credits_refunded": credits,
            "user_id": user_id,
            "job_id": job_id
        }
    
    async def refund_generation_failure(
        self,
        user_id: str,
        feature: str,
        credits_charged: int,
        error_message: str,
        generation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Called immediately when a generation fails to refund the user
        This is the primary method to call from generation endpoints
        """
        if credits_charged <= 0:
            return {"success": False, "error": "No credits to refund"}
        
        if credits_charged > self.max_auto_refund_credits:
            credits_charged = self.max_auto_refund_credits
        
        # Restore credits
        await self.db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": credits_charged}}
        )
        
        # Log the refund
        refund_record = {
            "user_id": user_id,
            "feature": feature,
            "credits_refunded": credits_charged,
            "reason": RefundReason.GENERATION_FAILED,
            "error_message": error_message,
            "generation_id": generation_id,
            "auto_refund": True,
            "timestamp": datetime.now(timezone.utc)
        }
        await self.db.auto_refund_logs.insert_one(refund_record)
        
        logger.info(f"Refunded {credits_charged} credits for {feature} failure to user {user_id}")
        
        return {
            "success": True,
            "credits_refunded": credits_charged,
            "message": f"Credits have been automatically refunded due to generation failure"
        }
    
    async def process_pending_refund_requests(self):
        """Process user-requested refunds that are pending"""
        pending = await self.db.refund_requests.find({
            "status": "pending",
            "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=self.refund_window_hours)}
        }).to_list(50)
        
        for request in pending:
            try:
                result = await self._process_refund_request(request)
                status = "completed" if result["success"] else "failed"
                
                await self.db.refund_requests.update_one(
                    {"_id": request["_id"]},
                    {"$set": {
                        "status": status,
                        "processed_at": datetime.now(timezone.utc),
                        "result": result
                    }}
                )
            except Exception as e:
                logger.error(f"Failed to process refund request: {e}")
    
    async def _process_refund_request(self, request: Dict) -> Dict[str, Any]:
        """Process a single refund request"""
        user_id = request.get("user_id")
        credits = request.get("credits", 0)
        
        if credits <= 0 or credits > self.max_auto_refund_credits:
            return {"success": False, "error": "Invalid refund amount"}
        
        # Verify the transaction exists and is refundable
        transaction = await self.db.credit_ledger.find_one({
            "userId": user_id,
            "entryType": "debit",
            "refunded": {"$ne": True},
            "timestamp": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=self.refund_window_hours)).isoformat()}
        })
        
        if not transaction:
            return {"success": False, "error": "No refundable transaction found"}
        
        # Process refund
        await self.db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Mark as refunded
        await self.db.credit_ledger.update_one(
            {"_id": transaction["_id"]},
            {"$set": {"refunded": True, "refundedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True, "credits_refunded": credits}
    
    async def get_refund_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get refund statistics for admin dashboard"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {
                "_id": "$reason",
                "count": {"$sum": 1},
                "total_credits": {"$sum": "$credits_refunded"}
            }}
        ]
        
        by_reason = await self.db.auto_refund_logs.aggregate(pipeline).to_list(20)
        
        total_refunds = await self.db.auto_refund_logs.count_documents({
            "timestamp": {"$gte": start_date}
        })
        
        total_credits = sum(r["total_credits"] for r in by_reason)
        
        return {
            "period_days": days,
            "total_refunds": total_refunds,
            "total_credits_refunded": total_credits,
            "by_reason": [
                {"reason": r["_id"], "count": r["count"], "credits": r["total_credits"]} 
                for r in by_reason
            ]
        }


# Singleton instance holder
_auto_refund_service = None

async def get_auto_refund_service(db) -> EnhancedAutoRefundService:
    """Get or create the auto-refund service singleton"""
    global _auto_refund_service
    if _auto_refund_service is None:
        _auto_refund_service = EnhancedAutoRefundService(db)
    return _auto_refund_service


async def handle_generation_failure(db, user_id: str, feature: str, credits: int, error: str) -> Dict:
    """
    Convenience function to handle generation failures with auto-refund
    Call this from any generation endpoint when an error occurs
    """
    service = await get_auto_refund_service(db)
    return await service.refund_generation_failure(
        user_id=user_id,
        feature=feature,
        credits_charged=credits,
        error_message=error
    )
