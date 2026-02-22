"""
Cashfree Webhook Edge Case Handler
Comprehensive handling for all payment webhook scenarios
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from datetime import datetime, timezone, timedelta
import uuid
import json
import hmac
import hashlib
import base64
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, add_credits, deduct_credits

router = APIRouter(prefix="/cashfree-webhook", tags=["Cashfree Webhooks"])

# Webhook Configuration
WEBHOOK_SECRET = os.environ.get("CASHFREE_WEBHOOK_SECRET", "")
IDEMPOTENCY_WINDOW_HOURS = 24  # How long to track processed webhooks
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAYS = [5, 30, 120]  # Seconds between retries


class WebhookProcessor:
    """Handles webhook processing with edge case handling"""
    
    @staticmethod
    async def verify_signature(request: Request, body: bytes) -> bool:
        """Verify Cashfree webhook signature"""
        if not WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured - skipping signature verification")
            return True
        
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")
        
        if not signature or not timestamp:
            logger.warning("Missing signature headers")
            return False
        
        # Check timestamp freshness (prevent replay attacks)
        try:
            webhook_time = int(timestamp)
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            # Reject if webhook is older than 5 minutes
            if abs(current_time - webhook_time) > 300:
                logger.warning(f"Webhook timestamp too old: {webhook_time}")
                return False
        except ValueError:
            logger.warning(f"Invalid timestamp format: {timestamp}")
            return False
        
        # Verify HMAC signature
        body_str = body.decode('utf-8')
        signed_payload = f"{timestamp}.{body_str}"
        
        expected_signature = base64.b64encode(
            hmac.new(
                WEBHOOK_SECRET.encode('utf-8'),
                msg=signed_payload.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    async def check_idempotency(event_id: str, order_id: str) -> bool:
        """Check if this webhook event has already been processed"""
        existing = await db.webhook_events.find_one({
            "$or": [
                {"eventId": event_id},
                {"orderId": order_id, "status": "PROCESSED"}
            ]
        })
        
        if existing:
            logger.info(f"Duplicate webhook detected: event_id={event_id}, order_id={order_id}")
            return True
        
        return False
    
    @staticmethod
    async def record_webhook_event(event_id: str, order_id: str, event_type: str, 
                                   payload: dict, status: str = "PENDING"):
        """Record webhook event for tracking and idempotency"""
        await db.webhook_events.update_one(
            {"eventId": event_id},
            {
                "$set": {
                    "eventId": event_id,
                    "orderId": order_id,
                    "eventType": event_type,
                    "status": status,
                    "payload": payload,
                    "processedAt": datetime.now(timezone.utc).isoformat() if status == "PROCESSED" else None,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                },
                "$setOnInsert": {
                    "receivedAt": datetime.now(timezone.utc).isoformat(),
                    "retryCount": 0
                }
            },
            upsert=True
        )
    
    @staticmethod
    async def process_payment_success(order_id: str, payment_data: dict) -> dict:
        """Process successful payment"""
        order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
        
        if not order:
            return {"status": "ERROR", "message": f"Order not found: {order_id}"}
        
        # Already processed
        if order["status"] == "PAID":
            return {"status": "DUPLICATE", "message": "Payment already processed"}
        
        # Add credits
        credits_to_add = order.get("credits", 0)
        user_id = order.get("userId")
        
        if not user_id or credits_to_add <= 0:
            return {"status": "ERROR", "message": "Invalid order data"}
        
        try:
            new_balance = await add_credits(
                user_id=user_id,
                amount=credits_to_add,
                description=f"Cashfree payment - {order.get('productName', '')} (Webhook)",
                tx_type="PURCHASE",
                order_id=order_id
            )
            
            # Update order status
            await db.orders.update_one(
                {"order_id": order_id},
                {
                    "$set": {
                        "status": "PAID",
                        "paidAt": datetime.now(timezone.utc).isoformat(),
                        "paymentDetails": payment_data
                    }
                }
            )
            
            logger.info(f"Payment success processed: order={order_id}, credits={credits_to_add}, new_balance={new_balance}")
            
            return {
                "status": "SUCCESS",
                "message": f"Added {credits_to_add} credits",
                "newBalance": new_balance
            }
        
        except Exception as e:
            logger.error(f"Error processing payment success: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    @staticmethod
    async def process_payment_failed(order_id: str, failure_data: dict) -> dict:
        """Process failed payment"""
        failure_reason = failure_data.get("payment_message", "Payment failed")
        error_code = failure_data.get("payment_status", "UNKNOWN")
        
        await db.orders.update_one(
            {"order_id": order_id, "gateway": "cashfree"},
            {
                "$set": {
                    "status": "FAILED",
                    "failureReason": failure_reason,
                    "errorCode": error_code,
                    "failedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Payment failed recorded: order={order_id}, reason={failure_reason}")
        
        return {"status": "SUCCESS", "message": f"Recorded failure: {failure_reason}"}
    
    @staticmethod
    async def process_payment_pending(order_id: str, pending_data: dict) -> dict:
        """Process pending/processing payment"""
        await db.orders.update_one(
            {"order_id": order_id, "gateway": "cashfree"},
            {
                "$set": {
                    "status": "PROCESSING",
                    "pendingDetails": pending_data,
                    "lastUpdated": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Payment pending recorded: order={order_id}")
        
        return {"status": "SUCCESS", "message": "Recorded pending status"}
    
    @staticmethod
    async def process_refund(order_id: str, refund_data: dict) -> dict:
        """Process refund webhook"""
        refund_status = refund_data.get("refund_status", "")
        refund_amount = refund_data.get("refund_amount", 0)
        refund_id = refund_data.get("refund_id", "")
        
        order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
        
        if not order:
            return {"status": "ERROR", "message": f"Order not found: {order_id}"}
        
        if refund_status == "SUCCESS":
            # Calculate credits to revoke
            # If partial refund, calculate proportionally
            original_amount = order.get("amount", 0) / 100  # Convert from paise
            original_credits = order.get("credits", 0)
            
            if original_amount > 0:
                credits_to_revoke = int((refund_amount / original_amount) * original_credits)
            else:
                credits_to_revoke = original_credits
            
            user_id = order.get("userId")
            
            if user_id and credits_to_revoke > 0:
                try:
                    await deduct_credits(
                        user_id=user_id,
                        amount=credits_to_revoke,
                        description=f"Refund - Order {order_id}",
                        tx_type="REFUND"
                    )
                    
                    # Update order with refund info
                    await db.orders.update_one(
                        {"order_id": order_id},
                        {
                            "$set": {
                                "status": "REFUNDED",
                                "refundId": refund_id,
                                "refundAmount": refund_amount,
                                "creditsRevoked": credits_to_revoke,
                                "refundedAt": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    )
                    
                    # Log refund
                    await db.refund_logs.insert_one({
                        "id": str(uuid.uuid4()),
                        "orderId": order_id,
                        "refundId": refund_id,
                        "userId": user_id,
                        "refundAmount": refund_amount,
                        "creditsRevoked": credits_to_revoke,
                        "status": "SUCCESS",
                        "createdAt": datetime.now(timezone.utc).isoformat()
                    })
                    
                    logger.info(f"Refund processed: order={order_id}, credits_revoked={credits_to_revoke}")
                    
                    return {
                        "status": "SUCCESS",
                        "message": f"Revoked {credits_to_revoke} credits",
                        "refundId": refund_id
                    }
                
                except Exception as e:
                    logger.error(f"Error processing refund: {e}")
                    return {"status": "ERROR", "message": str(e)}
        
        elif refund_status == "PENDING":
            await db.orders.update_one(
                {"order_id": order_id},
                {
                    "$set": {
                        "refundStatus": "PENDING",
                        "refundId": refund_id,
                        "lastUpdated": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            return {"status": "SUCCESS", "message": "Refund pending"}
        
        return {"status": "ERROR", "message": f"Unknown refund status: {refund_status}"}
    
    @staticmethod
    async def process_settlement(order_id: str, settlement_data: dict) -> dict:
        """Process settlement webhook"""
        await db.orders.update_one(
            {"order_id": order_id},
            {
                "$set": {
                    "settlementStatus": settlement_data.get("settlement_status", ""),
                    "settlementId": settlement_data.get("settlement_id", ""),
                    "settledAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Settlement recorded: order={order_id}")
        
        return {"status": "SUCCESS", "message": "Settlement recorded"}


processor = WebhookProcessor()


@router.post("/handle")
async def handle_cashfree_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Comprehensive Cashfree webhook handler with edge case handling
    
    Handles:
    - Payment success
    - Payment failure
    - Payment pending/processing
    - Refund success/failure
    - Settlement events
    - Duplicate delivery protection
    - Signature verification
    - Timeout handling (via background tasks)
    """
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verify signature
        if not await processor.verify_signature(request, body):
            await db.webhook_security_events.insert_one({
                "type": "SIGNATURE_FAILURE",
                "ip": request.client.host if request.client else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "headers": dict(request.headers)
            })
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse webhook data
        try:
            webhook_data = json.loads(body_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        event_type = webhook_data.get("type", "UNKNOWN")
        event_id = webhook_data.get("event_id", str(uuid.uuid4()))
        
        # Extract order data
        data = webhook_data.get("data", {})
        order_data = data.get("order", {})
        payment_data = data.get("payment", {})
        refund_data = data.get("refund", {})
        settlement_data = data.get("settlement", {})
        
        order_id = order_data.get("order_id", "")
        
        if not order_id:
            logger.warning(f"Webhook received without order_id: {event_type}")
            return {"status": "IGNORED", "message": "No order_id in payload"}
        
        # Check idempotency (prevent duplicate processing)
        if await processor.check_idempotency(event_id, order_id):
            return {"status": "DUPLICATE", "message": "Event already processed"}
        
        # Record webhook receipt
        await processor.record_webhook_event(
            event_id=event_id,
            order_id=order_id,
            event_type=event_type,
            payload=webhook_data,
            status="PROCESSING"
        )
        
        # Process based on event type
        result = {"status": "UNKNOWN", "message": "Unhandled event type"}
        
        try:
            if event_type == "PAYMENT_SUCCESS_WEBHOOK":
                result = await processor.process_payment_success(order_id, payment_data)
            
            elif event_type == "PAYMENT_FAILED_WEBHOOK":
                result = await processor.process_payment_failed(order_id, payment_data)
            
            elif event_type == "PAYMENT_USER_DROPPED_WEBHOOK":
                result = await processor.process_payment_failed(order_id, {
                    "payment_message": "User dropped payment",
                    "payment_status": "USER_DROPPED"
                })
            
            elif event_type == "PAYMENT_PENDING_WEBHOOK":
                result = await processor.process_payment_pending(order_id, payment_data)
            
            elif event_type in ["REFUND_SUCCESS_WEBHOOK", "REFUND_FAILED_WEBHOOK"]:
                result = await processor.process_refund(order_id, refund_data)
            
            elif event_type == "SETTLEMENT_WEBHOOK":
                result = await processor.process_settlement(order_id, settlement_data)
            
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                result = {"status": "IGNORED", "message": f"Event type {event_type} not handled"}
            
            # Update webhook record status
            final_status = "PROCESSED" if result.get("status") in ["SUCCESS", "DUPLICATE"] else "FAILED"
            await processor.record_webhook_event(
                event_id=event_id,
                order_id=order_id,
                event_type=event_type,
                payload=webhook_data,
                status=final_status
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {e}")
            
            # Record failure for retry
            await db.webhook_events.update_one(
                {"eventId": event_id},
                {
                    "$set": {
                        "status": "FAILED",
                        "errorMessage": str(e),
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    },
                    "$inc": {"retryCount": 1}
                }
            )
            
            # Schedule retry in background
            background_tasks.add_task(retry_failed_webhook, event_id)
            
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def retry_failed_webhook(event_id: str):
    """Retry failed webhook processing with exponential backoff"""
    event = await db.webhook_events.find_one({"eventId": event_id}, {"_id": 0})
    
    if not event:
        return
    
    retry_count = event.get("retryCount", 0)
    
    if retry_count >= MAX_RETRY_ATTEMPTS:
        logger.error(f"Max retries exceeded for webhook {event_id}")
        await db.webhook_events.update_one(
            {"eventId": event_id},
            {"$set": {"status": "PERMANENTLY_FAILED"}}
        )
        return
    
    # Wait before retry
    delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
    await asyncio.sleep(delay)
    
    # Retry processing
    try:
        event_type = event.get("eventType", "")
        order_id = event.get("orderId", "")
        payload = event.get("payload", {})
        
        data = payload.get("data", {})
        payment_data = data.get("payment", {})
        refund_data = data.get("refund", {})
        
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            result = await processor.process_payment_success(order_id, payment_data)
        elif event_type == "PAYMENT_FAILED_WEBHOOK":
            result = await processor.process_payment_failed(order_id, payment_data)
        elif event_type in ["REFUND_SUCCESS_WEBHOOK", "REFUND_FAILED_WEBHOOK"]:
            result = await processor.process_refund(order_id, refund_data)
        else:
            result = {"status": "IGNORED"}
        
        if result.get("status") == "SUCCESS":
            await db.webhook_events.update_one(
                {"eventId": event_id},
                {"$set": {"status": "PROCESSED"}}
            )
            logger.info(f"Webhook retry successful: {event_id}")
    
    except Exception as e:
        logger.error(f"Webhook retry failed: {event_id}, error: {e}")


@router.get("/failed")
async def get_failed_webhooks(limit: int = 50):
    """Get list of failed webhooks for manual review (Admin only)"""
    failed = await db.webhook_events.find(
        {"status": {"$in": ["FAILED", "PERMANENTLY_FAILED"]}},
        {"_id": 0}
    ).sort("receivedAt", -1).limit(limit).to_list(limit)
    
    return {"failed_webhooks": failed, "count": len(failed)}


@router.post("/retry/{event_id}")
async def manual_retry_webhook(event_id: str, background_tasks: BackgroundTasks):
    """Manually retry a failed webhook (Admin only)"""
    event = await db.webhook_events.find_one({"eventId": event_id}, {"_id": 0})
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    # Reset retry count for manual retry
    await db.webhook_events.update_one(
        {"eventId": event_id},
        {
            "$set": {
                "status": "PENDING_RETRY",
                "retryCount": 0,
                "manualRetry": True
            }
        }
    )
    
    background_tasks.add_task(retry_failed_webhook, event_id)
    
    return {"status": "QUEUED", "message": f"Retry queued for event {event_id}"}


@router.get("/stats")
async def get_webhook_stats():
    """Get webhook processing statistics"""
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    
    pipeline = [
        {"$match": {"receivedAt": {"$gte": day_ago.isoformat()}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    stats = await db.webhook_events.aggregate(pipeline).to_list(10)
    
    stats_dict = {item["_id"]: item["count"] for item in stats}
    
    return {
        "period": "last_24_hours",
        "total": sum(stats_dict.values()),
        "processed": stats_dict.get("PROCESSED", 0),
        "failed": stats_dict.get("FAILED", 0),
        "permanently_failed": stats_dict.get("PERMANENTLY_FAILED", 0),
        "pending": stats_dict.get("PENDING", 0)
    }
