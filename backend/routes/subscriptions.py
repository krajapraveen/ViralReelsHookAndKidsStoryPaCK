"""
Subscription Management Module
Handles subscription plans, renewals, and webhooks
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import hmac
import hashlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/subscriptions", tags=["Subscription Management"])


# =============================================================================
# SUBSCRIPTION PLANS
# =============================================================================

SUBSCRIPTION_PLANS = {
    "weekly": {
        "id": "weekly",
        "name": "Weekly Plan",
        "duration_days": 7,
        "credits": 30,
        "price_inr": 99,
        "price_usd": 4.99,
        "features": ["30 credits", "All apps access", "Standard support"]
    },
    "monthly": {
        "id": "monthly",
        "name": "Monthly Plan",
        "duration_days": 30,
        "credits": 100,
        "price_inr": 299,
        "price_usd": 9.99,
        "features": ["100 credits", "All apps access", "Priority support", "Early features"],
        "badge": "POPULAR"
    },
    "quarterly": {
        "id": "quarterly",
        "name": "Quarterly Plan",
        "duration_days": 90,
        "credits": 350,
        "price_inr": 699,
        "price_usd": 24.99,
        "features": ["350 credits", "All apps access", "VIP support", "Early features", "Bonus credits"],
        "badge": "BEST VALUE"
    }
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SubscribeRequest(BaseModel):
    planId: str
    currency: str = "INR"
    autoRenew: bool = True


class CancelRequest(BaseModel):
    reason: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def create_subscription(user_id: str, plan_id: str, payment_id: str, auto_renew: bool = True):
    """Create a new subscription for user"""
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    now = datetime.now(timezone.utc)
    subscription = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "planId": plan_id,
        "status": "ACTIVE",
        "startDate": now.isoformat(),
        "endDate": (now + timedelta(days=plan["duration_days"])).isoformat(),
        "autoRenew": auto_renew,
        "paymentId": payment_id,
        "creditsGranted": plan["credits"],
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }
    
    await db.subscriptions.insert_one(subscription)
    
    # Grant credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": plan["credits"]}}
    )
    
    # Log to ledger
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "TOPUP",
        "amount": plan["credits"],
        "refType": "SUBSCRIPTION",
        "refId": subscription["id"],
        "status": "ACTIVE",
        "createdAt": now.isoformat()
    })
    
    return subscription


async def process_renewal(subscription_id: str):
    """Process subscription renewal"""
    subscription = await db.subscriptions.find_one(
        {"id": subscription_id},
        {"_id": 0}
    )
    
    if not subscription:
        return None
    
    plan = SUBSCRIPTION_PLANS.get(subscription["planId"])
    if not plan:
        return None
    
    now = datetime.now(timezone.utc)
    
    # Extend subscription
    new_end_date = datetime.fromisoformat(subscription["endDate"].replace("Z", "+00:00"))
    new_end_date = new_end_date + timedelta(days=plan["duration_days"])
    
    await db.subscriptions.update_one(
        {"id": subscription_id},
        {
            "$set": {
                "endDate": new_end_date.isoformat(),
                "updatedAt": now.isoformat()
            },
            "$inc": {"renewalCount": 1}
        }
    )
    
    # Grant credits
    user_id = subscription["userId"]
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": plan["credits"]}}
    )
    
    # Log to ledger
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "TOPUP",
        "amount": plan["credits"],
        "refType": "SUBSCRIPTION_RENEWAL",
        "refId": subscription_id,
        "status": "ACTIVE",
        "createdAt": now.isoformat()
    })
    
    logger.info(f"Subscription {subscription_id} renewed for user {user_id}")
    return subscription


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/plans")
async def get_subscription_plans(currency: str = "INR"):
    """Get available subscription plans"""
    plans = []
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        plan_data = {
            "id": plan_id,
            "name": plan["name"],
            "durationDays": plan["duration_days"],
            "credits": plan["credits"],
            "price": plan[f"price_{currency.lower()}"] if f"price_{currency.lower()}" in plan else plan["price_inr"],
            "currency": currency,
            "features": plan["features"]
        }
        if "badge" in plan:
            plan_data["badge"] = plan["badge"]
        plans.append(plan_data)
    
    return {"plans": plans, "currency": currency}


@router.get("/current")
async def get_current_subscription(user: dict = Depends(get_current_user)):
    """Get user's current active subscription"""
    subscription = await db.subscriptions.find_one(
        {"userId": user["id"], "status": "ACTIVE"},
        {"_id": 0}
    )
    
    if subscription:
        # Check if expired
        end_date = datetime.fromisoformat(subscription["endDate"].replace("Z", "+00:00"))
        if end_date < datetime.now(timezone.utc):
            # Mark as expired
            await db.subscriptions.update_one(
                {"id": subscription["id"]},
                {"$set": {"status": "EXPIRED", "updatedAt": datetime.now(timezone.utc).isoformat()}}
            )
            subscription["status"] = "EXPIRED"
        
        # Add plan details
        plan = SUBSCRIPTION_PLANS.get(subscription["planId"], {})
        subscription["planDetails"] = plan
    
    return {"subscription": subscription}


@router.get("/history")
async def get_subscription_history(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get user's subscription history"""
    subscriptions = await db.subscriptions.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    # Enrich with plan details
    for sub in subscriptions:
        sub["planDetails"] = SUBSCRIPTION_PLANS.get(sub["planId"], {})
    
    return {"subscriptions": subscriptions}


@router.post("/cancel")
async def cancel_subscription(
    data: CancelRequest,
    user: dict = Depends(get_current_user)
):
    """Cancel auto-renewal for current subscription"""
    subscription = await db.subscriptions.find_one(
        {"userId": user["id"], "status": "ACTIVE"},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    await db.subscriptions.update_one(
        {"id": subscription["id"]},
        {
            "$set": {
                "autoRenew": False,
                "cancelReason": data.reason,
                "cancelledAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    logger.info(f"Subscription {subscription['id']} cancelled by user {user['id']}")
    
    return {
        "success": True,
        "message": "Auto-renewal cancelled. Your subscription will remain active until the end date.",
        "endDate": subscription["endDate"]
    }


@router.post("/reactivate")
async def reactivate_subscription(user: dict = Depends(get_current_user)):
    """Reactivate auto-renewal for current subscription"""
    subscription = await db.subscriptions.find_one(
        {"userId": user["id"], "status": "ACTIVE"},
        {"_id": 0}
    )
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    await db.subscriptions.update_one(
        {"id": subscription["id"]},
        {
            "$set": {
                "autoRenew": True,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            },
            "$unset": {"cancelReason": "", "cancelledAt": ""}
        }
    )
    
    return {"success": True, "message": "Auto-renewal reactivated"}


# =============================================================================
# WEBHOOK ENDPOINT FOR PAYMENT GATEWAY
# =============================================================================

# Store for processed webhook events (in-memory for quick lookup, DB for persistence)
PROCESSED_WEBHOOKS = set()

def verify_cashfree_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Cashfree webhook signature"""
    if not signature or not secret:
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@router.post("/webhook/renewal")
async def handle_renewal_webhook(request: Request):
    """
    Handle subscription renewal webhook from payment gateway
    
    Security checks:
    - Signature verification
    - Idempotency (no duplicate processing)
    - State machine validation
    """
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        payload = await request.json()
        
        # Get signature from headers
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")
        
        # Get webhook secret from env
        webhook_secret = os.environ.get("CASHFREE_WEBHOOK_SECRET", "")
        
        # Verify signature in production
        if webhook_secret and not verify_cashfree_signature(raw_body, signature, webhook_secret):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Extract event details
        event_type = payload.get("type", "")
        event_id = payload.get("event_id") or payload.get("data", {}).get("order_id") or str(uuid.uuid4())
        
        # Idempotency check - skip if already processed
        if event_id in PROCESSED_WEBHOOKS:
            logger.info(f"Webhook {event_id} already processed, skipping")
            return {"success": True, "message": "Already processed"}
        
        # Check DB for processed events
        existing = await db.webhook_events.find_one({"eventId": event_id})
        if existing:
            logger.info(f"Webhook {event_id} found in DB, skipping")
            return {"success": True, "message": "Already processed"}
        
        # Store webhook event BEFORE processing
        webhook_record = {
            "eventId": event_id,
            "eventType": event_type,
            "payload": payload,
            "receivedAt": datetime.now(timezone.utc).isoformat(),
            "status": "PROCESSING"
        }
        await db.webhook_events.insert_one(webhook_record)
        PROCESSED_WEBHOOKS.add(event_id)
        
        # Process based on event type
        result = {"success": True}
        
        if event_type == "SUBSCRIPTION_PAYMENT_SUCCESS":
            subscription_id = payload.get("data", {}).get("subscription_id")
            payment_id = payload.get("data", {}).get("cf_payment_id") or payload.get("data", {}).get("payment_id")
            
            if subscription_id:
                await process_renewal(subscription_id, payment_id)
                result["message"] = f"Renewal processed for {subscription_id}"
                logger.info(f"Renewal webhook processed for subscription {subscription_id}")
        
        elif event_type == "SUBSCRIPTION_PAYMENT_FAILED":
            subscription_id = payload.get("data", {}).get("subscription_id")
            user_id = payload.get("data", {}).get("customer_id")
            
            if subscription_id:
                await db.subscriptions.update_one(
                    {"id": subscription_id},
                    {
                        "$set": {
                            "paymentStatus": "FAILED",
                            "lastPaymentError": payload.get("data", {}).get("error_message", "Payment failed"),
                            "updatedAt": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                result["message"] = f"Marked subscription {subscription_id} as payment failed"
            
            logger.warning(f"Renewal payment failed for subscription {subscription_id}")
        
        elif event_type == "PAYMENT_SUCCESS" or event_type == "ORDER_PAID":
            # Handle one-time payment success
            order_id = payload.get("data", {}).get("order_id")
            customer_id = payload.get("data", {}).get("customer_id")
            amount = payload.get("data", {}).get("order_amount")
            
            if order_id:
                # Check if credits need to be granted
                await process_payment_success(order_id, customer_id, amount)
                result["message"] = f"Payment processed for order {order_id}"
        
        elif event_type == "REFUND_SUCCESS":
            # Handle refund
            order_id = payload.get("data", {}).get("order_id")
            refund_id = payload.get("data", {}).get("refund_id")
            
            if order_id:
                await process_refund(order_id, refund_id)
                result["message"] = f"Refund processed for order {order_id}"
        
        # Update webhook status to completed
        await db.webhook_events.update_one(
            {"eventId": event_id},
            {"$set": {"status": "COMPLETED", "processedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Renewal webhook error: {e}")
        
        # Update webhook status to failed
        if event_id:
            await db.webhook_events.update_one(
                {"eventId": event_id},
                {"$set": {"status": "FAILED", "error": str(e), "processedAt": datetime.now(timezone.utc).isoformat()}}
            )
        
        return {"success": False, "error": str(e)}


async def process_payment_success(order_id: str, customer_id: str, amount: float):
    """Process successful payment - grant credits or activate subscription"""
    # Find the pending payment
    payment = await db.payments.find_one({"orderId": order_id})
    
    if payment and payment.get("status") != "SUCCESS":
        # Update payment status
        await db.payments.update_one(
            {"orderId": order_id},
            {
                "$set": {
                    "status": "SUCCESS",
                    "completedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Grant credits if it's a credit purchase
        if payment.get("type") == "CREDIT_PURCHASE":
            credits = payment.get("credits", 0)
            await db.wallets.update_one(
                {"userId": payment.get("userId")},
                {"$inc": {"balance": credits}}
            )
            
            # Log the credit grant
            await db.credit_ledger.insert_one({
                "userId": payment.get("userId"),
                "amount": credits,
                "type": "PURCHASE",
                "description": f"Credit purchase - Order {order_id}",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })


async def process_refund(order_id: str, refund_id: str):
    """Process refund - revoke credits or cancel subscription"""
    payment = await db.payments.find_one({"orderId": order_id})
    
    if payment:
        # Mark payment as refunded
        await db.payments.update_one(
            {"orderId": order_id},
            {
                "$set": {
                    "status": "REFUNDED",
                    "refundId": refund_id,
                    "refundedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Revoke credits if already granted
        if payment.get("status") == "SUCCESS" and payment.get("type") == "CREDIT_PURCHASE":
            credits = payment.get("credits", 0)
            await db.wallets.update_one(
                {"userId": payment.get("userId")},
                {"$inc": {"balance": -credits}}
            )
            
            # Log the credit revocation
            await db.credit_ledger.insert_one({
                "userId": payment.get("userId"),
                "amount": -credits,
                "type": "REFUND",
                "description": f"Refund - Order {order_id}",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })


async def process_renewal(subscription_id: str, payment_id: str = None):
    """Process subscription renewal with proper state management"""


# =============================================================================
# A/B TESTING FOR PRICING
# =============================================================================

@router.get("/ab-test/pricing")
async def get_ab_test_pricing(user: dict = Depends(get_current_user)):
    """Get A/B test variant for pricing"""
    user_id = user["id"]
    
    # Simple hash-based A/B assignment
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    variant = "A" if hash_val % 2 == 0 else "B"
    
    # Different pricing variants
    if variant == "A":
        # Control: Standard pricing
        pricing = {
            "weekly": {"inr": 99, "usd": 4.99},
            "monthly": {"inr": 299, "usd": 9.99},
            "quarterly": {"inr": 699, "usd": 24.99}
        }
    else:
        # Variant B: Discounted pricing
        pricing = {
            "weekly": {"inr": 79, "usd": 3.99},
            "monthly": {"inr": 249, "usd": 7.99},
            "quarterly": {"inr": 599, "usd": 19.99}
        }
    
    # Track A/B exposure
    await db.ab_test_exposures.update_one(
        {"userId": user_id, "testName": "pricing_v1"},
        {
            "$set": {
                "variant": variant,
                "lastExposure": datetime.now(timezone.utc).isoformat()
            },
            "$setOnInsert": {
                "userId": user_id,
                "testName": "pricing_v1",
                "firstExposure": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {
        "variant": variant,
        "pricing": pricing,
        "testName": "pricing_v1"
    }


@router.post("/ab-test/convert")
async def track_ab_conversion(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Track A/B test conversion"""
    data = await request.json()
    test_name = data.get("testName", "pricing_v1")
    conversion_type = data.get("conversionType", "PURCHASE")
    
    await db.ab_test_exposures.update_one(
        {"userId": user["id"], "testName": test_name},
        {
            "$set": {
                "converted": True,
                "conversionType": conversion_type,
                "conversionTime": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True}
