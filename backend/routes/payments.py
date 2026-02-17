"""Payment routes"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
import uuid
import os
import razorpay
import logging

from ..utils.auth import get_current_user
from ..utils.database import db
from ..models.schemas import CreateOrderRequest, VerifyPaymentRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Product definitions
PRODUCTS = {
    "starter": {"name": "Starter Pack", "credits": 100, "price": 499, "popular": False},
    "creator": {"name": "Creator Pack", "credits": 300, "price": 999, "popular": True},
    "pro": {"name": "Pro Pack", "credits": 1000, "price": 2499, "popular": False},
    "quarterly": {"name": "Quarterly Subscription", "credits": 500, "price": 1999, "popular": False, "period": "quarterly"},
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
    """Get available products"""
    return {"products": PRODUCTS, "razorpayKeyId": RAZORPAY_KEY_ID}


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
async def create_order(data: CreateOrderRequest, user: dict = Depends(get_current_user)):
    """Create a Razorpay order"""
    if not razorpay_client:
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
        # Convert INR to target currency and to cents
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
                "credits": str(product["credits"])
            }
        })
        
        # Save order to database
        order = {
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "productId": data.productId,
            "amount": amount,
            "currency": data.currency.upper(),
            "credits": product["credits"],
            "razorpay_order_id": razorpay_order["id"],
            "status": "PENDING",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.orders.insert_one(order)
        
        return {
            "orderId": razorpay_order["id"],
            "amount": amount,
            "currency": data.currency.upper(),
            "keyId": RAZORPAY_KEY_ID,
            "productName": product["name"],
            "credits": product["credits"]
        }
        
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.post("/verify")
async def verify_payment(data: VerifyPaymentRequest, user: dict = Depends(get_current_user)):
    """Verify and complete a payment"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature
        })
        
        # Get order
        order = await db.orders.find_one({
            "razorpay_order_id": data.razorpay_order_id,
            "userId": user["id"]
        })
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order["status"] == "PAID":
            return {"message": "Payment already processed", "credits": user["credits"]}
        
        # Update order status
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
        
        # Add credits to user
        credits_to_add = order["credits"]
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": credits_to_add}}
        )
        
        # Log credit addition
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": credits_to_add,
            "type": "PURCHASE",
            "description": f"Purchased {credits_to_add} credits",
            "orderId": order["id"],
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Get updated user
        updated_user = await db.users.find_one({"id": user["id"]})
        
        return {
            "success": True,
            "message": "Payment successful",
            "creditsAdded": credits_to_add,
            "newBalance": updated_user["credits"]
        }
        
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


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
    return {"status": "healthy", "gateway": "razorpay", "configured": razorpay_client is not None}


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Handle Razorpay webhooks"""
    # Webhook handling for subscription renewals, etc.
    body = await request.body()
    logger.info(f"Received webhook: {body[:200]}")
    return {"status": "received"}
