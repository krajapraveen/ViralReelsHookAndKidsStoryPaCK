"""
Cashfree Payment Routes - Cashfree Payment Gateway Integration
CreatorStudio AI Payment Processing with Cashfree
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional
import uuid
import traceback
import logging
import os
import sys
import json
import hmac
import hashlib
import base64

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, get_admin_user,
    log_exception, add_credits, deduct_credits
)
from pydantic import BaseModel, Field

# Import payment monitoring
try:
    from utils.payment_monitoring import (
        track_payment_attempt,
        track_webhook_event,
        track_refund,
        get_payment_health_status
    )
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    logger.warning("Payment monitoring module not available")

router = APIRouter(prefix="/cashfree", tags=["Cashfree Payments"])

# Rate limiting for payment endpoints
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

# Cashfree Configuration - Select credentials based on environment
CASHFREE_ENVIRONMENT = os.environ.get("CASHFREE_ENVIRONMENT", "PRODUCTION")

# Use sandbox credentials for TEST environment, production credentials otherwise
if CASHFREE_ENVIRONMENT == "TEST":
    CASHFREE_APP_ID = os.environ.get("CASHFREE_SANDBOX_APP_ID")
    CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SANDBOX_SECRET_KEY")
    CASHFREE_WEBHOOK_SECRET = os.environ.get("CASHFREE_SANDBOX_WEBHOOK_SECRET")
    logger.info("Using Cashfree SANDBOX credentials")
else:
    CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
    CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
    CASHFREE_WEBHOOK_SECRET = os.environ.get("CASHFREE_WEBHOOK_SECRET")
    logger.info("Using Cashfree PRODUCTION credentials")

# Initialize Cashfree client
cashfree_client = None
cashfree_env = None
try:
    from cashfree_pg.api_client import Cashfree
    from cashfree_pg.models.create_order_request import CreateOrderRequest
    from cashfree_pg.models.customer_details import CustomerDetails
    from cashfree_pg.models.order_meta import OrderMeta
    
    if CASHFREE_APP_ID and CASHFREE_SECRET_KEY:
        # Initialize Cashfree with environment
        cashfree_env = Cashfree.PRODUCTION if CASHFREE_ENVIRONMENT == "PRODUCTION" else Cashfree.SANDBOX
        # Create client instance with proper initialization
        cashfree_client = Cashfree(
            XEnvironment=cashfree_env,
            XClientId=CASHFREE_APP_ID,
            XClientSecret=CASHFREE_SECRET_KEY
        )
        logger.info(f"Cashfree client initialized in {CASHFREE_ENVIRONMENT} mode with App ID: {CASHFREE_APP_ID[:10]}...")
    else:
        logger.warning(f"Cashfree credentials not found for {CASHFREE_ENVIRONMENT} environment")
except ImportError as e:
    logger.warning(f"Cashfree SDK not available: {e}")
except Exception as e:
    logger.error(f"Cashfree initialization error: {e}")

# Product definitions - Cashfree Only
PRODUCTS = {
    "starter": {"name": "Starter Pack", "credits": 100, "price": 499, "popular": False},
    "creator": {"name": "Creator Pack", "credits": 300, "price": 999, "popular": True},
    "pro": {"name": "Pro Pack", "credits": 1000, "price": 2499, "popular": False},
    "weekly": {"name": "Weekly Subscription", "credits": 50, "price": 199, "popular": False, "period": "weekly", "savings": "10%"},
    "monthly": {"name": "Monthly Subscription", "credits": 200, "price": 699, "popular": False, "period": "monthly", "savings": "20%"},
    "quarterly": {"name": "Quarterly Subscription", "credits": 500, "price": 1999, "popular": False, "period": "quarterly", "savings": "35%"},
    "yearly": {"name": "Yearly Subscription", "credits": 2500, "price": 5999, "popular": True, "period": "yearly", "savings": "50%"},
}

# Pydantic Models
class CashfreeOrderRequest(BaseModel):
    productId: str
    currency: str = "INR"

class CashfreeVerifyRequest(BaseModel):
    order_id: str
    cf_order_id: Optional[str] = None


class CashfreeRefundRequest(BaseModel):
    reason: str = Field(default="Customer requested refund", max_length=500)
    refund_amount: Optional[float] = None  # If None, full refund


class RefundStatus(BaseModel):
    order_id: str
    cf_order_id: Optional[str] = None


@router.get("/monitoring/health")
async def get_payment_monitoring_health(user: dict = Depends(get_admin_user)):
    """Get payment system health status (Admin only)"""
    if not MONITORING_ENABLED:
        return {
            "status": "MONITORING_DISABLED",
            "message": "Payment monitoring module not available"
        }
    
    try:
        health = await get_payment_health_status()
        return {
            "success": True,
            "gateway": "cashfree",
            "environment": CASHFREE_ENVIRONMENT,
            **health
        }
    except Exception as e:
        logger.error(f"Error fetching payment health: {e}")
        return {
            "success": False,
            "status": "ERROR",
            "message": str(e)
        }


@router.get("/products")
async def get_cashfree_products():
    """Get available products for Cashfree"""
    return {
        "products": PRODUCTS,
        "gateway": "cashfree",
        "configured": cashfree_client is not None
    }


@router.get("/plans")
async def get_cashfree_plans():
    """Alias for /products - Get available products for Cashfree"""
    return {
        "products": PRODUCTS,
        "gateway": "cashfree",
        "configured": cashfree_client is not None
    }


@router.post("/create-order")
@limiter.limit("5/minute")
async def create_cashfree_order(request: Request, data: CashfreeOrderRequest, user: dict = Depends(get_current_user)):
    """Create a Cashfree payment order"""
    if not cashfree_client:
        await log_exception(
            functionality="cashfree_create_order",
            error_type="GATEWAY_NOT_CONFIGURED",
            error_message="Cashfree payment gateway not configured",
            user_id=user["id"],
            user_email=user.get("email"),
            severity="CRITICAL"
        )
        raise HTTPException(status_code=500, detail="Cashfree payment gateway not configured")
    
    product = PRODUCTS.get(data.productId)
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product")
    
    try:
        from cashfree_pg.models.create_order_request import CreateOrderRequest
        from cashfree_pg.models.customer_details import CustomerDetails
        from cashfree_pg.models.order_meta import OrderMeta
        
        # Generate unique order ID
        order_id = f"cf_order_{user['id'][:8]}_{int(datetime.now().timestamp() * 1000)}"
        
        # Calculate amount
        amount = float(product["price"])
        
        # Create customer details
        customer_details = CustomerDetails(
            customer_id=user["id"],
            customer_email=user.get("email", ""),
            customer_phone=user.get("phone", "9999999999"),
            customer_name=user.get("name", "User")
        )
        
        # Create order meta with return URL
        frontend_url = os.environ.get("FRONTEND_URL", "https://ui-consistency-pass-2.preview.emergentagent.com")
        order_meta = OrderMeta(
            return_url=f"{frontend_url}/app/billing?order_id={order_id}&gateway=cashfree",
            notify_url=f"{frontend_url}/api/cashfree/webhook"
        )
        
        # Create order request
        order_request = CreateOrderRequest(
            order_id=order_id,
            order_amount=amount,
            order_currency=data.currency.upper(),
            customer_details=customer_details,
            order_meta=order_meta,
            order_note=f"Purchase {product['name']} - {product['credits']} credits"
        )
        
        # Create order via Cashfree API
        api_version = "2023-08-01"
        response = cashfree_client.PGCreateOrder(api_version, order_request, None, None)
        
        if response.data:
            # Save order to database
            order = {
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "userEmail": user.get("email", ""),
                "productId": data.productId,
                "productName": product["name"],
                "amount": int(amount * 100),  # Store in paise
                "currency": data.currency.upper(),
                "credits": product["credits"],
                "gateway": "cashfree",
                "cf_order_id": response.data.cf_order_id,
                "order_id": response.data.order_id,
                "payment_session_id": response.data.payment_session_id,
                "status": "PENDING",
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
            await db.orders.insert_one(order)
            
            logger.info(f"Cashfree order created: {response.data.order_id} for user {user['id']}")
            
            return {
                "success": True,
                "orderId": response.data.order_id,
                "cfOrderId": response.data.cf_order_id,
                "paymentSessionId": response.data.payment_session_id,
                "amount": amount,
                "currency": data.currency.upper(),
                "productName": product["name"],
                "credits": product["credits"],
                "environment": CASHFREE_ENVIRONMENT.lower()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create Cashfree order")
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        logger.error(f"Cashfree order creation error: {error_msg}")
        
        await log_exception(
            functionality="cashfree_create_order",
            error_type="ORDER_CREATION_FAILED",
            error_message=error_msg,
            user_id=user["id"],
            user_email=user.get("email"),
            stack_trace=stack_trace,
            severity="ERROR"
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create order: {error_msg}")


@router.post("/verify")
async def verify_cashfree_payment(request: Request, data: CashfreeVerifyRequest, user: dict = Depends(get_current_user)):
    """Verify Cashfree payment and add credits"""
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree payment gateway not configured")
    
    try:
        # Get order from database
        order = await db.orders.find_one({
            "order_id": data.order_id,
            "userId": user["id"],
            "gateway": "cashfree"
        }, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["status"] == "PAID":
            return {"message": "Payment already processed", "credits": user.get("credits", 0)}
        
        # Fetch order status from Cashfree
        api_version = "2023-08-01"
        response = cashfree_client.PGFetchOrder(api_version, data.order_id, None)
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Could not verify payment status")
        
        order_status = response.data.order_status
        
        if order_status == "PAID":
            # Add credits to user
            credits_to_add = order["credits"]
            new_balance = await add_credits(
                user_id=user["id"],
                amount=credits_to_add,
                description=f"Purchased {credits_to_add} credits via Cashfree - {order.get('productName', '')}",
                tx_type="PURCHASE",
                order_id=data.order_id
            )
            
            # Update order status
            await db.orders.update_one(
                {"id": order["id"]},
                {
                    "$set": {
                        "status": "PAID",
                        "paidAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Log payment
            await db.payment_logs.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "userEmail": user.get("email", ""),
                "gateway": "cashfree",
                "orderId": data.order_id,
                "amount": order["amount"],
                "currency": order.get("currency", "INR"),
                "status": "SUCCESS",
                "productId": order.get("productId", ""),
                "credits": credits_to_add,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"Cashfree payment successful: {data.order_id} - {credits_to_add} credits added to user {user['id']}")
            
            return {
                "success": True,
                "message": "Payment successful",
                "creditsAdded": credits_to_add,
                "newBalance": new_balance
            }
        elif order_status == "ACTIVE":
            return {
                "success": False,
                "message": "Payment is still pending",
                "status": order_status
            }
        else:
            # Update order status to failed
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"status": "FAILED", "failureReason": f"Order status: {order_status}"}}
            )
            
            return {
                "success": False,
                "message": f"Payment failed with status: {order_status}",
                "status": order_status
            }
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Cashfree verification error: {error_msg}")
        
        await log_exception(
            functionality="cashfree_verify",
            error_type="VERIFICATION_ERROR",
            error_message=error_msg,
            user_id=user["id"],
            user_email=user.get("email"),
            stack_trace=traceback.format_exc(),
            severity="ERROR"
        )
        
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {error_msg}")


@router.post("/webhook")
async def cashfree_webhook(request: Request):
    """Handle Cashfree webhook events"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Get signature headers
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")
        
        # Verify signature if secret is configured
        webhook_secret = os.environ.get("CASHFREE_WEBHOOK_SECRET")
        signature_valid = True
        
        if webhook_secret and signature:
            signed_payload = f"{timestamp}.{body_str}"
            expected_signature = base64.b64encode(
                hmac.new(
                    webhook_secret.encode('utf-8'),
                    msg=signed_payload.encode('utf-8'),
                    digestmod=hashlib.sha256
                ).digest()
            ).decode('utf-8')
            
            if not hmac.compare_digest(expected_signature, signature):
                signature_valid = False
                logger.warning("Invalid Cashfree webhook signature")
                
                # Track signature failure for monitoring
                if MONITORING_ENABLED:
                    webhook_data = json.loads(body_str) if body_str else {}
                    await track_webhook_event(
                        order_id=webhook_data.get("data", {}).get("order", {}).get("order_id", "unknown"),
                        event_type=webhook_data.get("type", "unknown"),
                        signature_valid=False,
                        payload={"error": "signature_mismatch"}
                    )
                
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse webhook data
        webhook_data = json.loads(body_str)
        event_type = webhook_data.get("type", "")
        
        logger.info(f"Received Cashfree webhook: {event_type}")
        
        # Track webhook event for monitoring
        if MONITORING_ENABLED:
            order_data = webhook_data.get("data", {}).get("order", {})
            await track_webhook_event(
                order_id=order_data.get("order_id", "unknown"),
                event_type=event_type,
                signature_valid=signature_valid,
                payload={"status": "received"}
            )
        
        # Handle payment events
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            order_data = webhook_data.get("data", {}).get("order", {})
            order_id = order_data.get("order_id")
            
            if order_id:
                # Find order and update status
                order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
                
                if order and order["status"] != "PAID":
                    # Add credits with order_id for tracking
                    await add_credits(
                        user_id=order["userId"],
                        amount=order["credits"],
                        description=f"Cashfree payment - {order.get('productName', '')}",
                        tx_type="PURCHASE",
                        order_id=order_id
                    )
                    
                    # Update order
                    await db.orders.update_one(
                        {"order_id": order_id},
                        {
                            "$set": {
                                "status": "PAID",
                                "paidAt": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    )
                    
                    # Track successful payment
                    if MONITORING_ENABLED:
                        await track_payment_attempt(
                            order_id=order_id,
                            status="SUCCESS",
                            amount=order.get("amount", 0),
                            user_id=order["userId"]
                        )
                    
                    logger.info(f"Cashfree webhook: Payment success for order {order_id}")
        
        elif event_type == "PAYMENT_FAILED_WEBHOOK":
            order_data = webhook_data.get("data", {}).get("order", {})
            order_id = order_data.get("order_id")
            failure_reason = webhook_data.get("data", {}).get("payment", {}).get("payment_message", "Payment failed")
            
            if order_id:
                order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
                
                await db.orders.update_one(
                    {"order_id": order_id, "gateway": "cashfree"},
                    {"$set": {"status": "FAILED", "failureReason": failure_reason}}
                )
                
                # Track failed payment for monitoring
                if MONITORING_ENABLED and order:
                    await track_payment_attempt(
                        order_id=order_id,
                        status="FAILED",
                        amount=order.get("amount", 0),
                        user_id=order.get("userId", ""),
                        error_message=failure_reason
                    )
        
        # Log webhook
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "gateway": "cashfree",
            "event": event_type,
            "payload": webhook_data,
            "signature_valid": signature_valid,
            "received_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "received", "event": event_type}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cashfree webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/health")
async def cashfree_health():
    """Check Cashfree gateway health"""
    return {
        "status": "healthy",
        "gateway": "cashfree",
        "configured": cashfree_client is not None,
        "environment": CASHFREE_ENVIRONMENT.lower()
    }


@router.get("/order/{order_id}/status")
async def get_order_status(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a specific order"""
    try:
        # Get user ID - handle both dict formats
        user_id = str(current_user.get("_id", current_user.get("id", current_user.get("user_id", ""))))
        
        # Find order in database (check both collections)
        order = await db.orders.find_one({
            "$or": [
                {"order_id": order_id},
                {"orderId": order_id}
            ]
        })
        
        if not order:
            order = await db.cashfree_orders.find_one({"orderId": order_id})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "orderId": order.get("order_id", order.get("orderId")),
            "cfOrderId": order.get("cf_order_id", order.get("cfOrderId")),
            "order_status": order.get("status", "PENDING"),
            "amount": order.get("amount"),
            "credits": order.get("credits"),
            "productId": order.get("productId"),
            "createdAt": str(order.get("createdAt", ""))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/history")
async def get_payment_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get payment history for the current user"""
    try:
        # Get user ID - handle both dict formats
        user_id = str(current_user.get("_id", current_user.get("id", current_user.get("user_id", ""))))
        
        # Find all orders for this user
        cursor = db.cashfree_orders.find(
            {"userId": user_id},
            {"_id": 0}
        ).sort("createdAt", -1).skip(skip).limit(limit)
        
        payments = await cursor.to_list(length=limit)
        
        # Get total count
        total = await db.cashfree_orders.count_documents({"userId": user_id})
        
        return {
            "payments": payments,
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logger.error(f"Error fetching payment history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REFUND ENDPOINTS (Admin Only)
# =============================================================================

@router.post("/refund/{order_id}")
@limiter.limit("10/minute")
async def create_cashfree_refund(
    order_id: str,
    request: Request,
    data: CashfreeRefundRequest,
    admin: dict = Depends(get_admin_user)
):
    """
    Process a refund for a Cashfree payment (Admin Only)
    
    - Full refund if refund_amount is not specified
    - Partial refund if refund_amount is specified
    - Revokes credits if they were granted
    """
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree payment gateway not configured")
    
    try:
        # Find the order
        order = await db.orders.find_one({
            "order_id": order_id,
            "gateway": "cashfree"
        }, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["status"] == "REFUNDED":
            raise HTTPException(status_code=400, detail="Order already refunded")
        
        if order["status"] != "PAID":
            raise HTTPException(status_code=400, detail=f"Cannot refund order with status: {order['status']}")
        
        # Calculate refund amount (convert from paise to rupees)
        order_amount_rupees = order["amount"] / 100
        refund_amount = data.refund_amount if data.refund_amount else order_amount_rupees
        
        if refund_amount > order_amount_rupees:
            raise HTTPException(status_code=400, detail=f"Refund amount ({refund_amount}) exceeds order amount ({order_amount_rupees})")
        
        # Generate unique refund ID
        refund_id = f"refund_{order_id}_{int(datetime.now().timestamp() * 1000)}"
        
        # Create refund via Cashfree API
        from cashfree_pg.models.create_refund_request import CreateRefundRequest
        
        refund_request = CreateRefundRequest(
            refund_amount=refund_amount,
            refund_id=refund_id,
            refund_note=data.reason[:100]  # Cashfree limits note length
        )
        
        api_version = "2023-08-01"
        response = cashfree_client.PGOrderCreateRefund(api_version, order_id, refund_request, None)
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create refund with Cashfree")
        
        # Determine if credits should be revoked
        credits_to_revoke = order.get("credits", 0)
        is_partial_refund = refund_amount < order_amount_rupees
        
        if is_partial_refund:
            # Calculate proportional credits to revoke
            credits_to_revoke = int(credits_to_revoke * (refund_amount / order_amount_rupees))
        
        # Revoke credits from user if they were granted
        user_id = order.get("userId")
        credits_revoked = 0
        if user_id and credits_to_revoke > 0:
            try:
                user = await db.users.find_one({"id": user_id}, {"_id": 0})
                if user:
                    current_credits = user.get("credits", 0)
                    new_credits = max(0, current_credits - credits_to_revoke)
                    credits_revoked = current_credits - new_credits
                    
                    await db.users.update_one(
                        {"id": user_id},
                        {"$set": {"credits": new_credits}}
                    )
                    
                    # Log credit revocation
                    await db.credit_ledger.insert_one({
                        "id": str(uuid.uuid4()),
                        "userId": user_id,
                        "amount": -credits_revoked,
                        "type": "REFUND_REVOCATION",
                        "description": f"Credits revoked due to refund - Order {order_id}",
                        "orderId": order_id,
                        "refundId": refund_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                logger.error(f"Failed to revoke credits for refund {refund_id}: {e}")
        
        # Update order status
        refund_status = "REFUNDED" if not is_partial_refund else "PARTIALLY_REFUNDED"
        await db.orders.update_one(
            {"order_id": order_id},
            {
                "$set": {
                    "status": refund_status,
                    "refundedAt": datetime.now(timezone.utc).isoformat(),
                    "refundId": response.data.refund_id,
                    "refundAmount": refund_amount,
                    "refundReason": data.reason,
                    "refundedBy": admin.get("email", admin.get("id")),
                    "creditsRevoked": credits_revoked
                }
            }
        )
        
        # Log the refund
        await db.refund_logs.insert_one({
            "id": str(uuid.uuid4()),
            "orderId": order_id,
            "refundId": response.data.refund_id,
            "cfRefundId": response.data.cf_refund_id if hasattr(response.data, 'cf_refund_id') else None,
            "userId": user_id,
            "userEmail": order.get("userEmail", ""),
            "amount": refund_amount,
            "currency": order.get("currency", "INR"),
            "reason": data.reason,
            "status": response.data.refund_status if hasattr(response.data, 'refund_status') else "PENDING",
            "creditsRevoked": credits_revoked,
            "processedBy": admin.get("email", admin.get("id")),
            "gateway": "cashfree",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Cashfree refund created: {refund_id} for order {order_id} by admin {admin.get('email')}")
        
        return {
            "success": True,
            "message": f"Refund of ₹{refund_amount} processed successfully",
            "refundId": response.data.refund_id,
            "refundAmount": refund_amount,
            "creditsRevoked": credits_revoked,
            "status": refund_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Cashfree refund error: {error_msg}")
        
        await log_exception(
            functionality="cashfree_refund",
            error_type="REFUND_FAILED",
            error_message=error_msg,
            user_id=admin.get("id"),
            user_email=admin.get("email"),
            stack_trace=traceback.format_exc(),
            severity="CRITICAL"
        )
        
        raise HTTPException(status_code=500, detail=f"Refund failed: {error_msg}")


@router.get("/refund/{order_id}/status")
async def get_refund_status(
    order_id: str,
    admin: dict = Depends(get_admin_user)
):
    """Get refund status for an order (Admin Only)"""
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree payment gateway not configured")
    
    try:
        # Get order from database
        order = await db.orders.find_one({
            "order_id": order_id,
            "gateway": "cashfree"
        }, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get all refunds from Cashfree
        api_version = "2023-08-01"
        response = cashfree_client.PGOrderFetchRefunds(api_version, order_id, None)
        
        refunds = []
        if response.data:
            for refund in response.data:
                refunds.append({
                    "refundId": refund.refund_id if hasattr(refund, 'refund_id') else None,
                    "cfRefundId": refund.cf_refund_id if hasattr(refund, 'cf_refund_id') else None,
                    "amount": refund.refund_amount if hasattr(refund, 'refund_amount') else None,
                    "status": refund.refund_status if hasattr(refund, 'refund_status') else None,
                    "processedAt": refund.processed_at if hasattr(refund, 'processed_at') else None
                })
        
        # Get local refund logs
        local_refunds = await db.refund_logs.find(
            {"orderId": order_id},
            {"_id": 0}
        ).to_list(length=10)
        
        return {
            "orderId": order_id,
            "orderStatus": order.get("status"),
            "orderAmount": order.get("amount", 0) / 100,
            "cashfreeRefunds": refunds,
            "localRefundLogs": local_refunds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get refund status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get refund status: {str(e)}")


@router.get("/orders/pending-delivery")
async def get_orders_pending_delivery(
    admin: dict = Depends(get_admin_user)
):
    """
    Get orders that are PAID but credits may not have been delivered (Admin Only)
    This helps identify "Paid but not delivered" cases for manual review
    """
    try:
        # Find orders that are PAID but might need review
        paid_orders = await db.orders.find(
            {
                "gateway": "cashfree",
                "status": "PAID"
            },
            {"_id": 0}
        ).sort("paidAt", -1).limit(100).to_list(length=100)
        
        # Check credit ledger for each order to verify delivery
        orders_needing_review = []
        for order in paid_orders:
            order_id = order.get("order_id")
            user_id = order.get("userId")
            
            # Check if credits were logged for this order
            credit_entry = await db.credit_ledger.find_one({
                "userId": user_id,
                "orderId": order_id,
                "type": "PURCHASE"
            }, {"_id": 0})
            
            if not credit_entry:
                orders_needing_review.append({
                    **order,
                    "issue": "NO_CREDIT_LEDGER_ENTRY",
                    "recommendation": "Verify user credits and manually add if missing, or refund"
                })
        
        return {
            "totalPaidOrders": len(paid_orders),
            "ordersNeedingReview": len(orders_needing_review),
            "orders": orders_needing_review
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending delivery orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/retry-delivery")
@limiter.limit("5/minute")
async def retry_credit_delivery(
    order_id: str,
    request: Request,
    admin: dict = Depends(get_admin_user)
):
    """
    Retry credit delivery for a PAID order that didn't receive credits (Admin Only)
    """
    try:
        order = await db.orders.find_one({
            "order_id": order_id,
            "gateway": "cashfree",
            "status": "PAID"
        }, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Paid order not found")
        
        user_id = order.get("userId")
        credits_to_add = order.get("credits", 0)
        
        if not user_id or credits_to_add <= 0:
            raise HTTPException(status_code=400, detail="Invalid order data")
        
        # Check if credits were already delivered
        existing_entry = await db.credit_ledger.find_one({
            "userId": user_id,
            "orderId": order_id,
            "type": "PURCHASE"
        }, {"_id": 0})
        
        if existing_entry:
            raise HTTPException(status_code=400, detail="Credits already delivered for this order")
        
        # Add credits
        new_balance = await add_credits(
            user_id=user_id,
            amount=credits_to_add,
            description=f"Manual credit delivery (retry) - {order.get('productName', '')}",
            tx_type="PURCHASE"
        )
        
        # Update order to mark delivery as completed
        await db.orders.update_one(
            {"order_id": order_id},
            {
                "$set": {
                    "deliveryRetried": True,
                    "deliveryRetriedAt": datetime.now(timezone.utc).isoformat(),
                    "deliveryRetriedBy": admin.get("email", admin.get("id"))
                }
            }
        )
        
        # Log the manual delivery
        await db.credit_ledger.update_one(
            {"userId": user_id, "orderId": order_id, "type": "PURCHASE"},
            {"$set": {"manualDelivery": True, "deliveredBy": admin.get("email")}}
        )
        
        logger.info(f"Manual credit delivery: {credits_to_add} credits for order {order_id} by admin {admin.get('email')}")
        
        return {
            "success": True,
            "message": f"Successfully delivered {credits_to_add} credits",
            "creditsAdded": credits_to_add,
            "newBalance": new_balance,
            "orderId": order_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry credit delivery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# INVOICE GENERATION ENDPOINT
# =============================================================================

@router.get("/invoice/{order_id}")
async def generate_invoice(order_id: str, user: dict = Depends(get_current_user)):
    """
    Generate and download invoice/receipt PDF for a completed payment
    """
    from fastapi.responses import Response
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    import io
    
    try:
        # Get order - user can only access their own orders
        order = await db.orders.find_one({
            "order_id": order_id,
            "userId": user["id"],
            "gateway": "cashfree"
        }, {"_id": 0})
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["status"] != "PAID":
            raise HTTPException(status_code=400, detail="Invoice only available for completed payments")
        
        # Get user details
        user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
        
        # Generate PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Colors
        primary_color = HexColor("#7c3aed")  # Purple
        text_color = HexColor("#1e293b")
        gray_color = HexColor("#64748b")
        
        # Header
        c.setFillColor(primary_color)
        c.rect(0, height - 100, width, 100, fill=True, stroke=False)
        
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 28)
        c.drawString(50, height - 60, "CreatorStudio AI")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, "Invoice / Receipt")
        
        # Invoice Details
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 140, "Invoice Details")
        
        c.setFont("Helvetica", 11)
        c.setFillColor(gray_color)
        
        y_pos = height - 165
        details = [
            ("Invoice Number:", order_id),
            ("Date:", order.get("paidAt", order.get("createdAt", "N/A"))[:10] if order.get("paidAt") or order.get("createdAt") else "N/A"),
            ("Status:", order["status"]),
            ("Payment Method:", "Cashfree Payment Gateway"),
        ]
        
        for label, value in details:
            c.setFillColor(gray_color)
            c.drawString(50, y_pos, label)
            c.setFillColor(text_color)
            c.drawString(180, y_pos, str(value))
            y_pos -= 20
        
        # Customer Details
        y_pos -= 30
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Customer Details")
        
        y_pos -= 25
        c.setFont("Helvetica", 11)
        customer_details = [
            ("Name:", user_data.get("name", "N/A")),
            ("Email:", user_data.get("email", "N/A")),
        ]
        
        for label, value in customer_details:
            c.setFillColor(gray_color)
            c.drawString(50, y_pos, label)
            c.setFillColor(text_color)
            c.drawString(180, y_pos, str(value))
            y_pos -= 20
        
        # Purchase Details
        y_pos -= 30
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Purchase Details")
        
        y_pos -= 25
        
        # Table header
        c.setFillColor(primary_color)
        c.rect(50, y_pos - 5, width - 100, 25, fill=True, stroke=False)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_pos + 2, "Item")
        c.drawString(350, y_pos + 2, "Credits")
        c.drawString(450, y_pos + 2, "Amount")
        
        # Table row
        y_pos -= 30
        c.setFillColor(text_color)
        c.setFont("Helvetica", 10)
        c.drawString(60, y_pos, order.get("productName", "Credit Pack"))
        c.drawString(350, y_pos, str(order.get("credits", 0)))
        
        # Amount in INR
        amount_inr = order.get("amount", 0) / 100
        c.drawString(450, y_pos, f"₹{amount_inr:.2f}")
        
        # Total
        y_pos -= 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(350, y_pos, "Total:")
        c.setFillColor(primary_color)
        c.drawString(450, y_pos, f"₹{amount_inr:.2f}")
        
        # Footer
        c.setFillColor(gray_color)
        c.setFont("Helvetica", 9)
        c.drawString(50, 80, "Thank you for your purchase!")
        c.drawString(50, 65, "For support, contact: support@creatorstudio.ai")
        c.drawString(50, 50, f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        c.save()
        
        # Return PDF
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{order_id}.pdf",
                "Content-Type": "application/pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoice generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Invoice generation failed: {str(e)}")
