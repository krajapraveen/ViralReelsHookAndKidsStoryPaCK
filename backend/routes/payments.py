"""
Payment Routes - Razorpay Integration with Exception Handling & Refunds
CreatorStudio AI Payment Processing
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional
import uuid
import traceback
import logging
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user,
    razorpay_client, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
    log_exception, log_payment, process_refund, add_credits
)
from models.schemas import CreateOrderRequest, VerifyPaymentRequest

router = APIRouter(prefix="/payments", tags=["Payments"])

# Product definitions - Cashfree Only (Razorpay removed)
PRODUCTS = {
    "starter": {"name": "Starter Pack", "credits": 100, "price": 499, "popular": False},
    "creator": {"name": "Creator Pack", "credits": 300, "price": 999, "popular": True},
    "pro": {"name": "Pro Pack", "credits": 1000, "price": 2499, "popular": False},
    "weekly": {"name": "Weekly Subscription", "credits": 50, "price": 199, "popular": False, "period": "weekly", "savings": "10%"},
    "monthly": {"name": "Monthly Subscription", "credits": 200, "price": 699, "popular": False, "period": "monthly", "savings": "20%"},
    "quarterly": {"name": "Quarterly Subscription", "credits": 500, "price": 1999, "popular": False, "period": "quarterly", "savings": "35%"},
    "yearly": {"name": "Yearly Subscription", "credits": 2500, "price": 5999, "popular": True, "period": "yearly", "savings": "50%"},
}

# Currency exchange rates (base: INR)
EXCHANGE_RATES = {
    "INR": 1.0,
    "USD": 0.012,
    "EUR": 0.011,
    "GBP": 0.0095
}


@router.get("/products")
async def get_products():
    """Get available products - Cashfree gateway"""
    return {"products": PRODUCTS, "gateway": "cashfree"}


@router.get("/currencies")
async def get_currencies():
    """Get supported currencies"""
    return {
        "currencies": list(EXCHANGE_RATES.keys()),
        "default": "INR"
    }


@router.get("/exchange-rate/{currency}")
async def get_exchange_rate(currency: str):
    """Get exchange rate for a currency"""
    rate = EXCHANGE_RATES.get(currency.upper(), 1.0)
    return {"currency": currency.upper(), "rate": rate}


@router.post("/create-order")
async def create_order(request: Request, data: CreateOrderRequest, user: dict = Depends(get_current_user)):
    """Create a Razorpay order with comprehensive exception handling"""
    if not razorpay_client:
        await log_exception(
            functionality="payment_create_order",
            error_type="GATEWAY_NOT_CONFIGURED",
            error_message="Payment gateway not configured",
            user_id=user["id"],
            user_email=user.get("email"),
            severity="CRITICAL"
        )
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    product = PRODUCTS.get(data.productId)
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product")
    
    # Calculate price in selected currency
    exchange_rate = EXCHANGE_RATES.get(data.currency.upper(), 1.0)
    price_inr = product["price"]
    
    # Convert to smallest currency unit (paise for INR, cents for USD, etc.)
    if data.currency.upper() == "INR":
        amount = price_inr * 100  # paise
    else:
        amount = int(price_inr * exchange_rate * 100)
    
    try:
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": data.currency.upper(),
            "receipt": f"order_{uuid.uuid4().hex[:12]}",
            "notes": {
                "productId": data.productId,
                "userId": user["id"],
                "credits": str(product["credits"]),
                "userEmail": user.get("email", "")
            }
        })
        
        # Save order to database
        order = {
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "userEmail": user.get("email", ""),
            "productId": data.productId,
            "productName": product["name"],
            "amount": amount,
            "currency": data.currency.upper(),
            "credits": product["credits"],
            "razorpay_order_id": razorpay_order["id"],
            "status": "PENDING",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.orders.insert_one(order)
        
        logger.info(f"Order created: {razorpay_order['id']} for user {user['id']}")
        
        return {
            "orderId": razorpay_order["id"],
            "amount": amount,
            "currency": data.currency.upper(),
            "keyId": RAZORPAY_KEY_ID,
            "productName": product["name"],
            "credits": product["credits"]
        }
        
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        logger.error(f"Order creation error: {error_msg}")
        
        await log_exception(
            functionality="payment_create_order",
            error_type="ORDER_CREATION_FAILED",
            error_message=error_msg,
            user_id=user["id"],
            user_email=user.get("email"),
            stack_trace=stack_trace,
            severity="ERROR"
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create order: {error_msg}")


@router.post("/verify")
async def verify_payment(request: Request, data: VerifyPaymentRequest, user: dict = Depends(get_current_user)):
    """Verify and complete a payment with full exception handling and refund capability"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    order = None
    payment_verified = False
    credits_added = False
    
    try:
        # Step 1: Verify signature
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": data.razorpay_order_id,
                "razorpay_payment_id": data.razorpay_payment_id,
                "razorpay_signature": data.razorpay_signature
            })
            payment_verified = True
        except Exception as sig_error:
            await log_payment(
                user_id=user["id"],
                user_email=user.get("email", ""),
                order_id=data.razorpay_order_id,
                amount=0,
                currency="INR",
                status="FAILED",
                product_id="",
                credits=0,
                failure_reason=f"Signature verification failed: {str(sig_error)}"
            )
            await log_exception(
                functionality="payment_verify",
                error_type="SIGNATURE_VERIFICATION_FAILED",
                error_message=str(sig_error),
                user_id=user["id"],
                user_email=user.get("email"),
                severity="WARNING"
            )
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Step 2: Get order
        order = await db.orders.find_one({
            "razorpay_order_id": data.razorpay_order_id,
            "userId": user["id"]
        }, {"_id": 0})
        
        if not order:
            await log_exception(
                functionality="payment_verify",
                error_type="ORDER_NOT_FOUND",
                error_message=f"Order not found: {data.razorpay_order_id}",
                user_id=user["id"],
                user_email=user.get("email"),
                severity="ERROR"
            )
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["status"] == "PAID":
            return {"message": "Payment already processed", "credits": user.get("credits", 0)}
        
        # Step 3: Add credits to user (CRITICAL - this is the delivery)
        try:
            credits_to_add = order["credits"]
            new_balance = await add_credits(
                user_id=user["id"],
                amount=credits_to_add,
                description=f"Purchased {credits_to_add} credits - {order.get('productName', '')}",
                tx_type="PURCHASE"
            )
            credits_added = True
            
        except Exception as credit_error:
            # CRITICAL: Payment succeeded but delivery failed - MUST REFUND
            error_msg = f"Credit delivery failed after payment: {str(credit_error)}"
            logger.error(error_msg)
            
            await log_exception(
                functionality="payment_credit_delivery",
                error_type="CREDIT_DELIVERY_FAILED",
                error_message=error_msg,
                user_id=user["id"],
                user_email=user.get("email"),
                stack_trace=traceback.format_exc(),
                severity="CRITICAL"
            )
            
            # Initiate refund
            try:
                refund_result = await process_refund(
                    order_id=data.razorpay_order_id,
                    payment_id=data.razorpay_payment_id,
                    reason="Credit delivery failed - automatic refund"
                )
                
                await log_payment(
                    user_id=user["id"],
                    user_email=user.get("email", ""),
                    order_id=data.razorpay_order_id,
                    amount=order["amount"],
                    currency=order.get("currency", "INR"),
                    status="REFUNDED",
                    product_id=order.get("productId", ""),
                    credits=order["credits"],
                    failure_reason="Credit delivery failed",
                    refund_id=refund_result.get("refund_id")
                )
                
                raise HTTPException(
                    status_code=500,
                    detail="Payment received but credit delivery failed. A refund has been initiated. Please try again."
                )
            except HTTPException:
                raise
            except Exception as refund_error:
                # Refund also failed - critical issue
                await log_exception(
                    functionality="payment_refund",
                    error_type="REFUND_FAILED_AFTER_DELIVERY_FAILURE",
                    error_message=f"Refund failed: {str(refund_error)}",
                    user_id=user["id"],
                    user_email=user.get("email"),
                    severity="CRITICAL"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Payment issue occurred. Our team has been notified and will process your refund manually."
                )
        
        # Step 4: Update order status
        await db.orders.update_one(
            {"id": order["id"]},
            {
                "$set": {
                    "status": "PAID",
                    "razorpay_payment_id": data.razorpay_payment_id,
                    "paidAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Step 5: Log successful payment
        await log_payment(
            user_id=user["id"],
            user_email=user.get("email", ""),
            order_id=data.razorpay_order_id,
            amount=order["amount"],
            currency=order.get("currency", "INR"),
            status="SUCCESS",
            product_id=order.get("productId", ""),
            credits=order["credits"]
        )
        
        logger.info(f"Payment successful: {data.razorpay_payment_id} - {order['credits']} credits added to user {user['id']}")
        
        return {
            "success": True,
            "message": "Payment successful",
            "creditsAdded": credits_to_add,
            "newBalance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        stack_trace = traceback.format_exc()
        
        logger.error(f"Payment verification error: {error_msg}")
        
        await log_exception(
            functionality="payment_verify",
            error_type="VERIFICATION_ERROR",
            error_message=error_msg,
            user_id=user["id"],
            user_email=user.get("email"),
            stack_trace=stack_trace,
            severity="CRITICAL"
        )
        
        # If payment was verified but something else failed, consider refund
        if payment_verified and not credits_added and order:
            try:
                await process_refund(
                    order_id=data.razorpay_order_id,
                    payment_id=data.razorpay_payment_id,
                    reason=f"Verification error after payment: {error_msg}"
                )
            except:
                pass  # Refund attempt logged separately
        
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {error_msg}")


@router.get("/history")
async def get_payment_history(page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    """Get user's payment history"""
    skip = page * size
    
    orders = await db.orders.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.orders.count_documents({"userId": user["id"]})
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/health")
async def payments_health():
    """Check payment gateway health"""
    return {
        "status": "healthy",
        "gateway": "razorpay",
        "configured": razorpay_client is not None,
        "mode": "test" if RAZORPAY_KEY_ID and "test" in RAZORPAY_KEY_ID else "live"
    }


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Handle Razorpay webhooks for subscription renewals and payment events"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Log webhook receipt
        logger.info(f"Received Razorpay webhook: {body_str[:200]}...")
        
        # Parse webhook data
        import json
        webhook_data = json.loads(body_str)
        event = webhook_data.get("event", "")
        
        # Handle different webhook events
        if event == "payment.captured":
            # Payment captured - usually handled in verify
            pass
        elif event == "payment.failed":
            # Payment failed
            payment = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment.get("order_id")
            error_desc = payment.get("error_description", "Unknown error")
            
            if order_id:
                await db.orders.update_one(
                    {"razorpay_order_id": order_id},
                    {"$set": {"status": "FAILED", "failureReason": error_desc}}
                )
                
                await log_payment(
                    user_id="webhook",
                    user_email="",
                    order_id=order_id,
                    amount=payment.get("amount", 0),
                    currency=payment.get("currency", "INR"),
                    status="FAILED",
                    product_id="",
                    credits=0,
                    failure_reason=error_desc
                )
                
        elif event == "refund.created":
            # Refund initiated
            refund = webhook_data.get("payload", {}).get("refund", {}).get("entity", {})
            payment_id = refund.get("payment_id")
            
            # Find and update order
            order = await db.orders.find_one({"razorpay_payment_id": payment_id}, {"_id": 0})
            if order:
                await db.orders.update_one(
                    {"razorpay_payment_id": payment_id},
                    {
                        "$set": {
                            "status": "REFUNDED",
                            "refund_id": refund.get("id"),
                            "refunded_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
        
        # Log webhook to database
        await db.webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "gateway": "razorpay",
            "event": event,
            "payload": webhook_data,
            "received_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "received", "event": event}
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        await log_exception(
            functionality="payment_webhook",
            error_type="WEBHOOK_PROCESSING_ERROR",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
            severity="WARNING"
        )
        return {"status": "error", "message": str(e)}


@router.post("/refund/{order_id}")
async def request_refund(order_id: str, reason: str = "Customer request", user: dict = Depends(get_current_user)):
    """Request a refund for an order (admin or order owner)"""
    order = await db.orders.find_one({"razorpay_order_id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check ownership or admin
    if order["userId"] != user["id"] and user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to refund this order")
    
    if order["status"] != "PAID":
        raise HTTPException(status_code=400, detail=f"Cannot refund order with status: {order['status']}")
    
    payment_id = order.get("razorpay_payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="No payment ID found for this order")
    
    result = await process_refund(order_id, payment_id, reason)
    
    # Deduct credits if they were already added
    if order.get("credits"):
        try:
            await db.users.update_one(
                {"id": order["userId"]},
                {"$inc": {"credits": -order["credits"]}}
            )
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": order["userId"],
                "amount": -order["credits"],
                "type": "REFUND",
                "description": f"Credits reversed due to refund - {reason}",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to reverse credits: {e}")
    
    return result
