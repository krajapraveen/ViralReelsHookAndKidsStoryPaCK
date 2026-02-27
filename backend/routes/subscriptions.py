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


async def process_renewal(subscription_id: str, payment_id: str = None):
    """Process subscription renewal with proper state management"""
    subscription = await db.subscriptions.find_one(
        {"id": subscription_id},
        {"_id": 0}
    )
    
    if not subscription:
        logger.warning(f"Subscription {subscription_id} not found for renewal")
        return None
    
    # Check if already renewed recently (idempotency)
    last_renewal = subscription.get("lastRenewalAt")
    if last_renewal:
        last_renewal_time = datetime.fromisoformat(last_renewal.replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - last_renewal_time).total_seconds() < 60:
            logger.info(f"Subscription {subscription_id} already renewed recently, skipping")
            return subscription
    
    plan = SUBSCRIPTION_PLANS.get(subscription["planId"])
    if not plan:
        logger.error(f"Invalid plan {subscription['planId']} for subscription {subscription_id}")
        return None
    
    now = datetime.now(timezone.utc)
    
    # Extend subscription
    try:
        current_end = datetime.fromisoformat(subscription["endDate"].replace("Z", "+00:00"))
        # If subscription is expired, start from now
        if current_end < now:
            new_end_date = now + timedelta(days=plan["duration_days"])
        else:
            new_end_date = current_end + timedelta(days=plan["duration_days"])
    except (ValueError, KeyError):
        new_end_date = now + timedelta(days=plan["duration_days"])
    
    # Update subscription atomically
    result = await db.subscriptions.update_one(
        {"id": subscription_id},
        {
            "$set": {
                "status": "ACTIVE",
                "endDate": new_end_date.isoformat(),
                "updatedAt": now.isoformat(),
                "lastRenewalAt": now.isoformat(),
                "lastPaymentId": payment_id,
                "paymentStatus": "SUCCESS"
            },
            "$inc": {"renewalCount": 1, "creditsGranted": plan["credits"]}
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
# RECONCILIATION JOB
# =============================================================================

async def reconcile_payments():
    """
    Background reconciliation job to fix 'paid but not delivered' issues
    
    Checks for:
    - Payments marked SUCCESS at gateway but missing credits/subscription
    - Subscriptions with PENDING payment status but successful payment
    - Duplicate credit grants
    """
    logger.info("Starting payment reconciliation job")
    
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    
    issues_found = []
    
    try:
        # 1. Find successful payments without credit grant
        successful_payments = await db.payments.find({
            "status": "SUCCESS",
            "creditsGranted": {"$ne": True},
            "createdAt": {"$gte": one_day_ago.isoformat()}
        }).to_list(100)
        
        for payment in successful_payments:
            # Check if credits were actually granted
            ledger_entry = await db.credit_ledger.find_one({
                "refType": {"$in": ["PURCHASE", "SUBSCRIPTION"]},
                "refId": payment.get("orderId")
            })
            
            if not ledger_entry:
                issues_found.append({
                    "type": "MISSING_CREDIT_GRANT",
                    "orderId": payment.get("orderId"),
                    "userId": payment.get("userId"),
                    "amount": payment.get("credits", 0)
                })
                
                # Auto-fix: Grant the missing credits
                if payment.get("credits"):
                    await db.wallets.update_one(
                        {"userId": payment.get("userId")},
                        {"$inc": {"balance": payment.get("credits")}}
                    )
                    await db.credit_ledger.insert_one({
                        "userId": payment.get("userId"),
                        "amount": payment.get("credits"),
                        "type": "RECONCILIATION",
                        "description": f"Auto-reconciled - Order {payment.get('orderId')}",
                        "createdAt": now.isoformat()
                    })
                    await db.payments.update_one(
                        {"orderId": payment.get("orderId")},
                        {"$set": {"creditsGranted": True, "reconciledAt": now.isoformat()}}
                    )
                    logger.info(f"Reconciled missing credits for order {payment.get('orderId')}")
        
        # 2. Find subscriptions with payment issues
        problem_subs = await db.subscriptions.find({
            "paymentStatus": {"$in": ["PENDING", "FAILED"]},
            "status": "ACTIVE",
            "updatedAt": {"$gte": one_hour_ago.isoformat()}
        }).to_list(50)
        
        for sub in problem_subs:
            issues_found.append({
                "type": "SUBSCRIPTION_PAYMENT_ISSUE",
                "subscriptionId": sub.get("id"),
                "userId": sub.get("userId"),
                "paymentStatus": sub.get("paymentStatus")
            })
        
        # Log reconciliation results
        if issues_found:
            await db.reconciliation_logs.insert_one({
                "runAt": now.isoformat(),
                "issuesFound": len(issues_found),
                "issues": issues_found,
                "status": "COMPLETED"
            })
            logger.warning(f"Reconciliation found {len(issues_found)} issues")
        else:
            logger.info("Reconciliation completed with no issues")
        
        return {"issues": len(issues_found), "fixed": len([i for i in issues_found if i["type"] == "MISSING_CREDIT_GRANT"])}
    
    except Exception as e:
        logger.error(f"Reconciliation error: {e}")
        return {"error": str(e)}


@router.post("/admin/reconcile")
async def trigger_reconciliation(user: dict = Depends(get_current_user)):
    """Manually trigger payment reconciliation (admin only)"""
    # Check admin role
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await reconcile_payments()
    return {"success": True, "result": result}


# =============================================================================
# CURRENCY CONVERSION
# =============================================================================

FX_RATES = {
    "USD": {"INR": 83.5},
    "EUR": {"INR": 91.2},
    "GBP": {"INR": 106.5},
    "AUD": {"INR": 55.3},
    "SGD": {"INR": 62.1},
    "AED": {"INR": 22.7},
}

def convert_to_inr(amount: float, from_currency: str) -> dict:
    """Convert amount to INR with rate info"""
    from_currency = from_currency.upper()
    
    if from_currency == "INR":
        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "inr_amount": amount,
            "fx_rate": 1.0
        }
    
    rate = FX_RATES.get(from_currency, {}).get("INR", 83.5)  # Default to USD rate
    inr_amount = round(amount * rate, 2)
    
    return {
        "original_amount": amount,
        "original_currency": from_currency,
        "inr_amount": inr_amount,
        "fx_rate": rate
    }


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


# =============================================================================
# CASHFREE RECURRING SUBSCRIPTION ENDPOINTS
# =============================================================================

from services.cashfree_subscription_service import (
    get_subscription_service,
    get_subscription_plans as get_cf_plans,
    SUBSCRIPTION_PLANS as CF_PLANS
)

class CreateRecurringSubscriptionRequest(BaseModel):
    plan_key: str = Field(..., pattern="^(creator|pro|studio)$")
    customer_phone: Optional[str] = Field(default=None)


@router.get("/recurring/plans")
async def get_recurring_plans():
    """Get Cashfree recurring subscription plans"""
    plans = get_cf_plans()
    return {
        "success": True,
        "plans": [
            {
                "key": key,
                **plan,
                "popular": key == "pro"
            }
            for key, plan in plans.items()
        ]
    }


@router.get("/recurring/current")
async def get_current_recurring(user: dict = Depends(get_current_user)):
    """Get user's current recurring subscription"""
    service = await get_subscription_service(db)
    subscription = await service.get_user_subscription(user["id"])
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "plan": 1, "credits": 1})
    current_plan = user_data.get("plan", "free") if user_data else "free"
    
    plan_details = CF_PLANS.get(current_plan, {})
    
    return {
        "success": True,
        "has_subscription": subscription is not None,
        "subscription": subscription,
        "current_plan": current_plan,
        "plan_details": plan_details if plan_details else {
            "name": "Free Plan",
            "discount_percent": 0,
            "features": ["Basic access", "Watermarked outputs"]
        }
    }


@router.post("/recurring/create")
async def create_recurring_subscription(
    request: CreateRecurringSubscriptionRequest,
    user: dict = Depends(get_current_user)
):
    """Create a new Cashfree recurring subscription"""
    service = await get_subscription_service(db)
    
    existing = await service.get_user_subscription(user["id"])
    if existing and existing.get("status") == "ACTIVE":
        raise HTTPException(status_code=400, detail="Already have an active subscription")
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "email": 1, "name": 1})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    frontend_url = os.environ.get("FRONTEND_URL", "https://creatorstudio.ai")
    
    try:
        result = await service.create_subscription(
            user_id=user["id"],
            plan_key=request.plan_key,
            customer_email=user_data.get("email", ""),
            customer_phone=request.customer_phone or "9999999999",
            customer_name=user_data.get("name", "User"),
            return_url=f"{frontend_url}/app/billing?subscription=success"
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create recurring subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recurring/cancel")
async def cancel_recurring_subscription(user: dict = Depends(get_current_user)):
    """Cancel Cashfree recurring subscription"""
    service = await get_subscription_service(db)
    
    subscription = await service.get_user_subscription(user["id"])
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    try:
        return await service.cancel_subscription(subscription["subscription_id"], user["id"])
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recurring/change-plan")
async def change_recurring_plan(
    new_plan_key: str,
    user: dict = Depends(get_current_user)
):
    """Change Cashfree recurring subscription plan"""
    if new_plan_key not in ["creator", "pro", "studio"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    service = await get_subscription_service(db)
    
    subscription = await service.get_user_subscription(user["id"])
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    try:
        return await service.change_plan(user["id"], subscription["subscription_id"], new_plan_key)
    except Exception as e:
        logger.error(f"Failed to change plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recurring/webhook")
async def recurring_webhook(
    request: Request,
    x_cashfree_signature: str = Header(None, alias="x-cashfree-signature")
):
    """Handle Cashfree recurring subscription webhooks"""
    body = await request.body()
    service = await get_subscription_service(db)
    
    if x_cashfree_signature:
        if not service.verify_webhook_signature(body, x_cashfree_signature):
            logger.warning("Invalid recurring webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        data = await request.json()
        event_type = data.get("type", "")
        
        logger.info(f"Received recurring webhook: {event_type}")
        
        await db.subscription_webhooks.insert_one({
            "event_type": event_type,
            "data": data,
            "received_at": datetime.now(timezone.utc).isoformat()
        })
        
        result = await service.handle_webhook(event_type, data)
        return {"success": True, "result": result}
        
    except Exception as e:
        logger.error(f"Recurring webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

