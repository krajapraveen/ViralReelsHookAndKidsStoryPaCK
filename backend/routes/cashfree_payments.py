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
    db, logger, get_current_user,
    log_exception, add_credits
)
from pydantic import BaseModel

router = APIRouter(prefix="/cashfree", tags=["Cashfree Payments"])

# Cashfree Configuration
CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_ENVIRONMENT = os.environ.get("CASHFREE_ENVIRONMENT", "PRODUCTION")

# Initialize Cashfree client
cashfree_client = None
try:
    from cashfree_pg.api_client import Cashfree
    from cashfree_pg.models.create_order_request import CreateOrderRequest
    from cashfree_pg.models.customer_details import CustomerDetails
    from cashfree_pg.models.order_meta import OrderMeta
    
    if CASHFREE_APP_ID and CASHFREE_SECRET_KEY:
        # Initialize Cashfree with environment
        env = Cashfree.PRODUCTION if CASHFREE_ENVIRONMENT == "PRODUCTION" else Cashfree.SANDBOX
        Cashfree.XClientId = CASHFREE_APP_ID
        Cashfree.XClientSecret = CASHFREE_SECRET_KEY
        Cashfree.XEnvironment = env
        cashfree_client = Cashfree
        logger.info(f"Cashfree client initialized in {CASHFREE_ENVIRONMENT} mode")
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


@router.get("/products")
async def get_cashfree_products():
    """Get available products for Cashfree"""
    return {
        "products": PRODUCTS,
        "gateway": "cashfree",
        "configured": cashfree_client is not None
    }


@router.post("/create-order")
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
        frontend_url = os.environ.get("FRONTEND_URL", "https://studio-deploy-2.preview.emergentagent.com")
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
        response = Cashfree.PGCreateOrder(api_version, order_request, None, None)
        
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
        from cashfree_pg.api_client import Cashfree
        response = Cashfree.PGFetchOrder(api_version, data.order_id, None)
        
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
                tx_type="PURCHASE"
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
                logger.warning("Invalid Cashfree webhook signature")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse webhook data
        webhook_data = json.loads(body_str)
        event_type = webhook_data.get("type", "")
        
        logger.info(f"Received Cashfree webhook: {event_type}")
        
        # Handle payment events
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            order_data = webhook_data.get("data", {}).get("order", {})
            order_id = order_data.get("order_id")
            
            if order_id:
                # Find order and update status
                order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
                
                if order and order["status"] != "PAID":
                    # Add credits
                    new_balance = await add_credits(
                        user_id=order["userId"],
                        amount=order["credits"],
                        description=f"Cashfree payment - {order.get('productName', '')}",
                        tx_type="PURCHASE"
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
                    
                    logger.info(f"Cashfree webhook: Payment success for order {order_id}")
        
        elif event_type == "PAYMENT_FAILED_WEBHOOK":
            order_data = webhook_data.get("data", {}).get("order", {})
            order_id = order_data.get("order_id")
            
            if order_id:
                await db.orders.update_one(
                    {"order_id": order_id, "gateway": "cashfree"},
                    {"$set": {"status": "FAILED", "failureReason": "Payment failed"}}
                )
        
        # Log webhook
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "gateway": "cashfree",
            "event": event_type,
            "payload": webhook_data,
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
