"""
Webhook Retry Queue Service
Handles failed webhook deliveries with exponential backoff retry logic.
"""

import asyncio
import aiohttp
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("creatorstudio")


class WebhookStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"  # Max retries reached


@dataclass
class WebhookDelivery:
    id: str
    webhook_type: str
    payload: Dict[str, Any]
    target_url: str
    status: WebhookStatus
    attempts: int
    max_attempts: int
    next_retry_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class WebhookRetryQueue:
    """
    Manages webhook delivery with retry logic.
    Uses exponential backoff: 1min, 5min, 15min, 1hr, 4hr
    """
    
    RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # seconds
    MAX_ATTEMPTS = 5
    
    def __init__(self, db):
        self.db = db
        self.collection = db.webhook_queue
        self._running = False
        self._task = None
    
    async def initialize(self):
        """Create indexes for efficient queries"""
        await self.collection.create_index("status")
        await self.collection.create_index("next_retry_at")
        await self.collection.create_index([("status", 1), ("next_retry_at", 1)])
        logger.info("Webhook retry queue initialized")
    
    async def enqueue(
        self,
        webhook_type: str,
        payload: Dict[str, Any],
        target_url: str,
        webhook_secret: Optional[str] = None
    ) -> str:
        """Add a webhook to the delivery queue"""
        import uuid
        
        webhook_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        delivery = {
            "id": webhook_id,
            "webhook_type": webhook_type,
            "payload": payload,
            "target_url": target_url,
            "webhook_secret": webhook_secret,
            "status": WebhookStatus.PENDING.value,
            "attempts": 0,
            "max_attempts": self.MAX_ATTEMPTS,
            "next_retry_at": now,
            "last_error": None,
            "last_response_code": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await self.collection.insert_one(delivery)
        logger.info(f"Webhook {webhook_id} enqueued for delivery to {target_url}")
        
        return webhook_id
    
    def _generate_signature(self, payload: str, secret: str, timestamp: str) -> str:
        """Generate HMAC signature for webhook"""
        data = timestamp + payload
        return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    
    async def _deliver_webhook(self, delivery: Dict[str, Any]) -> bool:
        """Attempt to deliver a single webhook"""
        webhook_id = delivery["id"]
        target_url = delivery["target_url"]
        payload = delivery["payload"]
        secret = delivery.get("webhook_secret")
        
        try:
            payload_str = json.dumps(payload)
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
            
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-ID": webhook_id,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Type": delivery["webhook_type"]
            }
            
            if secret:
                signature = self._generate_signature(payload_str, secret, timestamp)
                headers["X-Webhook-Signature"] = signature
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(target_url, data=payload_str, headers=headers) as resp:
                    response_code = resp.status
                    
                    # Update delivery record
                    now = datetime.now(timezone.utc)
                    
                    if 200 <= response_code < 300:
                        # Success
                        await self.collection.update_one(
                            {"id": webhook_id},
                            {"$set": {
                                "status": WebhookStatus.DELIVERED.value,
                                "last_response_code": response_code,
                                "delivered_at": now.isoformat(),
                                "updated_at": now.isoformat()
                            }}
                        )
                        logger.info(f"Webhook {webhook_id} delivered successfully")
                        return True
                    else:
                        # Failed - schedule retry
                        error_text = await resp.text()
                        await self._schedule_retry(
                            webhook_id,
                            delivery["attempts"] + 1,
                            f"HTTP {response_code}: {error_text[:200]}"
                        )
                        return False
                        
        except asyncio.TimeoutError:
            await self._schedule_retry(
                webhook_id,
                delivery["attempts"] + 1,
                "Request timeout"
            )
            return False
        except Exception as e:
            await self._schedule_retry(
                webhook_id,
                delivery["attempts"] + 1,
                str(e)
            )
            return False
    
    async def _schedule_retry(self, webhook_id: str, attempt: int, error: str):
        """Schedule a retry with exponential backoff"""
        now = datetime.now(timezone.utc)
        
        if attempt >= self.MAX_ATTEMPTS:
            # Max retries exhausted
            await self.collection.update_one(
                {"id": webhook_id},
                {"$set": {
                    "status": WebhookStatus.EXHAUSTED.value,
                    "attempts": attempt,
                    "last_error": error,
                    "updated_at": now.isoformat()
                }}
            )
            logger.warning(f"Webhook {webhook_id} exhausted after {attempt} attempts: {error}")
        else:
            # Schedule retry
            delay_seconds = self.RETRY_DELAYS[min(attempt - 1, len(self.RETRY_DELAYS) - 1)]
            next_retry = now + timedelta(seconds=delay_seconds)
            
            await self.collection.update_one(
                {"id": webhook_id},
                {"$set": {
                    "status": WebhookStatus.RETRYING.value,
                    "attempts": attempt,
                    "next_retry_at": next_retry.isoformat(),
                    "last_error": error,
                    "updated_at": now.isoformat()
                }}
            )
            logger.info(f"Webhook {webhook_id} scheduled for retry at {next_retry} (attempt {attempt})")
    
    async def process_queue(self):
        """Process pending and retry webhooks"""
        now = datetime.now(timezone.utc)
        
        # Find webhooks ready for delivery
        cursor = self.collection.find({
            "status": {"$in": [WebhookStatus.PENDING.value, WebhookStatus.RETRYING.value]},
            "next_retry_at": {"$lte": now.isoformat()}
        }).limit(50)
        
        webhooks = await cursor.to_list(length=50)
        
        if webhooks:
            logger.info(f"Processing {len(webhooks)} webhooks")
            
            # Process in parallel with concurrency limit
            semaphore = asyncio.Semaphore(10)
            
            async def process_with_semaphore(delivery):
                async with semaphore:
                    return await self._deliver_webhook(delivery)
            
            tasks = [process_with_semaphore(w) for w in webhooks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            delivered = sum(1 for r in results if r is True)
            logger.info(f"Webhook processing complete: {delivered}/{len(webhooks)} delivered")
    
    async def start_worker(self, interval: int = 30):
        """Start background worker to process queue"""
        self._running = True
        logger.info("Webhook retry worker started")
        
        while self._running:
            try:
                await self.process_queue()
            except Exception as e:
                logger.error(f"Webhook worker error: {e}")
            
            await asyncio.sleep(interval)
    
    def stop_worker(self):
        """Stop the background worker"""
        self._running = False
        logger.info("Webhook retry worker stopped")
    
    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=10)
        
        stats = {
            "pending": 0,
            "delivered": 0,
            "retrying": 0,
            "failed": 0,
            "exhausted": 0,
            "total": 0
        }
        
        for r in results:
            status = r["_id"]
            count = r["count"]
            if status in stats:
                stats[status] = count
            stats["total"] += count
        
        return stats
    
    async def get_failed_webhooks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of failed/exhausted webhooks"""
        cursor = self.collection.find(
            {"status": {"$in": [WebhookStatus.FAILED.value, WebhookStatus.EXHAUSTED.value]}},
            {"_id": 0, "webhook_secret": 0}
        ).sort("updated_at", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def retry_webhook(self, webhook_id: str) -> bool:
        """Manually retry a failed/exhausted webhook"""
        now = datetime.now(timezone.utc)
        
        result = await self.collection.update_one(
            {"id": webhook_id, "status": {"$in": [WebhookStatus.FAILED.value, WebhookStatus.EXHAUSTED.value]}},
            {"$set": {
                "status": WebhookStatus.PENDING.value,
                "attempts": 0,
                "next_retry_at": now.isoformat(),
                "updated_at": now.isoformat()
            }}
        )
        
        return result.modified_count > 0


# Global instance (initialized in server.py)
webhook_queue: Optional[WebhookRetryQueue] = None


def get_webhook_queue() -> WebhookRetryQueue:
    """Get the webhook queue instance"""
    global webhook_queue
    if webhook_queue is None:
        raise RuntimeError("Webhook queue not initialized")
    return webhook_queue
