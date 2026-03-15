"""
Cashfree Subscription Service
Handles recurring billing, plan management, and subscription lifecycle
"""
import os
import httpx
import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Configuration
CASHFREE_ENV = os.environ.get("CASHFREE_ENVIRONMENT", "SANDBOX").upper()

if CASHFREE_ENV == "PRODUCTION":
    CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
    CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
    CASHFREE_WEBHOOK_SECRET = os.environ.get("CASHFREE_WEBHOOK_SECRET")
    CASHFREE_BASE_URL = "https://api.cashfree.com/pg/subscriptions"
    CASHFREE_PLAN_URL = "https://api.cashfree.com/pg/subscription/plans"
else:
    CASHFREE_APP_ID = os.environ.get("CASHFREE_SANDBOX_APP_ID")
    CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SANDBOX_SECRET_KEY")
    CASHFREE_WEBHOOK_SECRET = os.environ.get("CASHFREE_SANDBOX_WEBHOOK_SECRET")
    CASHFREE_BASE_URL = "https://sandbox.cashfree.com/pg/subscriptions"
    CASHFREE_PLAN_URL = "https://sandbox.cashfree.com/pg/subscription/plans"

# Subscription Plans Configuration
SUBSCRIPTION_PLANS = {
    "creator": {
        "plan_id": "creator_monthly",
        "name": "Creator Plan",
        "description": "Perfect for content creators - 20% discount on all features",
        "price_inr": 299,
        "price_usd": 4.99,
        "interval": "month",
        "interval_count": 1,
        "credits_per_cycle": 100,
        "discount_percent": 20,
        "features": [
            "20% discount on all generations",
            "100 credits per month",
            "No watermarks",
            "Priority email support"
        ]
    },
    "pro": {
        "plan_id": "pro_monthly",
        "name": "Pro Plan",
        "description": "For serious creators - Premium templates & 30% discount",
        "price_inr": 599,
        "price_usd": 9.99,
        "interval": "month",
        "interval_count": 1,
        "credits_per_cycle": 300,
        "discount_percent": 30,
        "features": [
            "30% discount on all generations",
            "300 credits per month",
            "Premium cover templates",
            "Priority generation queue",
            "No watermarks",
            "Priority support"
        ]
    },
    "studio": {
        "plan_id": "studio_monthly",
        "name": "Studio Plan",
        "description": "Ultimate plan - Unlimited previews, commercial rights, 40% discount",
        "price_inr": 1499,
        "price_usd": 24.99,
        "interval": "month",
        "interval_count": 1,
        "credits_per_cycle": 1000,
        "discount_percent": 40,
        "features": [
            "40% discount on all generations",
            "1000 credits per month",
            "Unlimited previews",
            "Commercial license included",
            "Premium templates",
            "Priority generation",
            "Dedicated support"
        ]
    }
}


class CashfreeSubscriptionService:
    """Handles Cashfree Subscription API interactions"""
    
    def __init__(self, db):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "x-api-version": "2025-01-01",
            "x-client-id": CASHFREE_APP_ID,
            "x-client-secret": CASHFREE_SECRET_KEY,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
    
    async def create_plan(self, plan_key: str, currency: str = "INR") -> Dict[str, Any]:
        """Create a subscription plan in Cashfree"""
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_key}")
        
        plan_amount = plan["price_inr"] if currency == "INR" else plan.get("price_usd", plan["price_inr"])
        
        payload = {
            "plan_name": plan["name"],
            "plan_amount": plan_amount,
            "plan_currency": currency,
            "billing_frequency": "MONTHLY",
            "billing_cycles": -1,  # Indefinite
            "is_auto_collect": True
        }
        
        try:
            response = await self.client.post(
                CASHFREE_PLAN_URL,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create plan: {e.response.text}")
            raise
    
    async def create_subscription(
        self,
        user_id: str,
        plan_key: str,
        customer_email: str,
        customer_phone: str,
        customer_name: str,
        return_url: str,
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """Create a new subscription for a user"""
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            raise ValueError(f"Unknown plan: {plan_key}")
        
        subscription_id = f"sub_{user_id[:8]}_{int(datetime.now(timezone.utc).timestamp())}"
        
        plan_amount = plan["price_inr"] if currency == "INR" else plan.get("price_usd", plan["price_inr"])
        
        payload = {
            "subscription_id": subscription_id,
            "customer_details": {
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone
            },
            "plan_details": {
                "plan_name": plan["name"],
                "plan_type": "PERIODIC",
                "plan_amount": plan_amount,
                "plan_max_amount": plan_amount,
                "plan_currency": currency,
                "plan_interval_type": "MONTH",
                "plan_intervals": 1
            },
            "authorization_details": {
                "authorization_amount": 1,  # Small auth amount
                "authorization_amount_refund": True
            },
            "subscription_meta": {
                "return_url": return_url + f"&subscription_id={subscription_id}",
                "notify_url": f"{os.environ.get('BACKEND_URL', '')}/api/subscriptions/recurring/webhook"
            },
            "subscription_note": f"CreatorStudio {plan['name']} Subscription"
        }
        
        try:
            response = await self.client.post(
                CASHFREE_BASE_URL,
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()
            
            # Log full response for debugging
            logger.info(f"Cashfree subscription response: {result}")
            
            # Extract payment link from different possible locations
            # Cashfree sandbox doesn't return direct payment_link, need to construct from session
            cf_subscription_id = result.get("cf_subscription_id")
            subscription_session_id = result.get("subscription_session_id", "")
            
            # Construct payment URL - sandbox uses a different URL
            if CASHFREE_ENV == "PRODUCTION":
                payment_link = f"https://payments.cashfree.com/subscription/?session_id={subscription_session_id}"
            else:
                payment_link = f"https://payments-test.cashfree.com/subscription/?session_id={subscription_session_id}"
            
            if not subscription_session_id:
                payment_link = result.get("subscription_payment_link") or result.get("data", {}).get("subscription_payment_link")
            
            # Store subscription in database
            subscription_doc = {
                "subscription_id": subscription_id,
                "cf_subscription_id": result.get("cf_subscription_id") or result.get("subscription_id") or result.get("data", {}).get("cf_subscription_id"),
                "user_id": user_id,
                "plan_key": plan_key,
                "plan_name": plan["name"],
                "status": result.get("subscription_status") or result.get("data", {}).get("subscription_status") or "INITIALIZED",
                "price": plan["price_inr"],
                "currency": "INR",
                "credits_per_cycle": plan["credits_per_cycle"],
                "discount_percent": plan["discount_percent"],
                "payment_link": payment_link,
                "raw_response": result,  # Store for debugging
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.subscriptions.insert_one(subscription_doc)
            
            logger.info(f"Created subscription {subscription_id} for user {user_id}")
            
            return {
                "success": True,
                "subscription_id": subscription_id,
                "payment_link": subscription_doc["payment_link"],
                "plan": plan
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create subscription: {e.response.text}")
            # Return a fallback response for testing
            return {
                "success": False,
                "error": str(e),
                "message": "Cashfree API error. Please try again or contact support.",
                "debug": e.response.text if hasattr(e, 'response') else str(e)
            }
    
    async def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription details from Cashfree"""
        try:
            response = await self.client.get(
                f"{CASHFREE_BASE_URL}/{subscription_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get subscription: {e.response.text}")
            return None
    
    async def cancel_subscription(self, subscription_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            response = await self.client.post(
                f"{CASHFREE_BASE_URL}/{subscription_id}/cancel",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            # Update database
            await self.db.subscriptions.update_one(
                {"subscription_id": subscription_id, "user_id": user_id},
                {
                    "$set": {
                        "status": "CANCELLED",
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            # Update user plan
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "plan": "free",
                        "subscription_id": None,
                        "plan_updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            logger.info(f"Cancelled subscription {subscription_id} for user {user_id}")
            
            return {"success": True, "message": "Subscription cancelled"}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel subscription: {e.response.text}")
            raise
    
    async def pause_subscription(self, subscription_id: str, user_id: str) -> Dict[str, Any]:
        """Pause a subscription"""
        try:
            response = await self.client.post(
                f"{CASHFREE_BASE_URL}/{subscription_id}/pause",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            await self.db.subscriptions.update_one(
                {"subscription_id": subscription_id, "user_id": user_id},
                {
                    "$set": {
                        "status": "PAUSED",
                        "paused_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return {"success": True, "message": "Subscription paused"}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to pause subscription: {e.response.text}")
            raise
    
    async def resume_subscription(self, subscription_id: str, user_id: str) -> Dict[str, Any]:
        """Resume a paused subscription"""
        try:
            response = await self.client.post(
                f"{CASHFREE_BASE_URL}/{subscription_id}/activate",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            await self.db.subscriptions.update_one(
                {"subscription_id": subscription_id, "user_id": user_id},
                {
                    "$set": {
                        "status": "ACTIVE",
                        "resumed_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return {"success": True, "message": "Subscription resumed"}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to resume subscription: {e.response.text}")
            raise
    
    async def change_plan(
        self,
        user_id: str,
        current_subscription_id: str,
        new_plan_key: str
    ) -> Dict[str, Any]:
        """Change subscription plan (upgrade/downgrade)"""
        new_plan = SUBSCRIPTION_PLANS.get(new_plan_key)
        if not new_plan:
            raise ValueError(f"Unknown plan: {new_plan_key}")
        
        # Get current subscription
        current_sub = await self.db.subscriptions.find_one(
            {"subscription_id": current_subscription_id, "user_id": user_id}
        )
        
        if not current_sub:
            raise ValueError("Current subscription not found")
        
        # For plan changes, we cancel the old subscription and create a new one
        # Get user details
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            raise ValueError("User not found")
        
        # Cancel current subscription
        await self.cancel_subscription(current_subscription_id, user_id)
        
        # Create new subscription
        return await self.create_subscription(
            user_id=user_id,
            plan_key=new_plan_key,
            customer_email=user.get("email", ""),
            customer_phone=user.get("phone", ""),
            customer_name=user.get("name", "User"),
            return_url=f"{os.environ.get('FRONTEND_URL', '')}/app/billing"
        )
    
    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's active subscription"""
        subscription = await self.db.subscriptions.find_one(
            {"user_id": user_id, "status": {"$in": ["ACTIVE", "INITIALIZED"]}},
            {"_id": 0}
        )
        return subscription
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Cashfree webhook signature"""
        computed_signature = hmac.new(
            CASHFREE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed_signature, signature)
    
    async def handle_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Cashfree subscription webhook events"""
        subscription_id = data.get("subscription", {}).get("subscription_id")
        cf_subscription_id = data.get("subscription", {}).get("cf_subscription_id")
        
        logger.info(f"Processing webhook: {event_type} for subscription {subscription_id}")
        
        # Get subscription from database
        subscription = await self.db.subscriptions.find_one(
            {"$or": [
                {"subscription_id": subscription_id},
                {"cf_subscription_id": cf_subscription_id}
            ]}
        )
        
        if not subscription:
            logger.warning(f"Subscription not found for webhook: {subscription_id}")
            return {"success": False, "message": "Subscription not found"}
        
        user_id = subscription.get("user_id")
        plan_key = subscription.get("plan_key")
        plan = SUBSCRIPTION_PLANS.get(plan_key, {})
        
        result = {"success": True, "processed": event_type}
        
        if event_type == "SUBSCRIPTION_STATUS_CHANGE":
            new_status = data.get("subscription", {}).get("status")
            await self._handle_status_change(subscription, new_status, user_id, plan)
            result["new_status"] = new_status
        
        elif event_type == "PAYMENT_SUCCESS":
            await self._handle_payment_success(subscription, data, user_id, plan)
            result["credits_added"] = plan.get("credits_per_cycle", 0)
        
        elif event_type == "PAYMENT_FAILED":
            await self._handle_payment_failed(subscription, data, user_id)
            result["action"] = "retry_scheduled"
        
        elif event_type == "SUBSCRIPTION_CANCELLED":
            await self._handle_cancellation(subscription, user_id)
            result["action"] = "downgraded_to_free"
        
        return result
    
    async def _handle_status_change(
        self, 
        subscription: Dict, 
        new_status: str, 
        user_id: str, 
        plan: Dict
    ):
        """Handle subscription status changes"""
        await self.db.subscriptions.update_one(
            {"subscription_id": subscription["subscription_id"]},
            {
                "$set": {
                    "status": new_status,
                    "status_updated_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if new_status == "ACTIVE":
            # Activate user's plan
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "plan": subscription.get("plan_key", "creator"),
                        "subscription_id": subscription["subscription_id"],
                        "plan_activated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            logger.info(f"Activated {subscription.get('plan_key')} plan for user {user_id}")
        
        elif new_status in ["CANCELLED", "EXPIRED"]:
            # Downgrade to free
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "plan": "free",
                        "subscription_id": None,
                        "plan_downgraded_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            logger.info(f"Downgraded user {user_id} to free plan")
    
    async def _handle_payment_success(
        self, 
        subscription: Dict, 
        data: Dict, 
        user_id: str, 
        plan: Dict
    ):
        """Handle successful subscription payment - add credits"""
        payment_id = data.get("payment", {}).get("cf_payment_id")
        credits_to_add = plan.get("credits_per_cycle", 0)
        
        # Check for duplicate payment
        existing = await self.db.subscription_payments.find_one(
            {"payment_id": payment_id}
        )
        if existing:
            logger.warning(f"Duplicate payment webhook: {payment_id}")
            return
        
        # Record payment
        payment_record = {
            "payment_id": payment_id,
            "subscription_id": subscription["subscription_id"],
            "user_id": user_id,
            "amount": data.get("payment", {}).get("payment_amount", 0),
            "credits_added": credits_to_add,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.subscription_payments.insert_one(payment_record)
        
        # Add credits to user
        await self.db.users.update_one(
            {"id": user_id},
            {
                "$inc": {"credits": credits_to_add},
                "$set": {
                    "last_credit_refresh": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Update subscription
        await self.db.subscriptions.update_one(
            {"subscription_id": subscription["subscription_id"]},
            {
                "$set": {
                    "last_payment_at": datetime.now(timezone.utc).isoformat(),
                    "next_billing_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                },
                "$inc": {"total_payments": 1}
            }
        )
        
        # Log to credit ledger
        await self.db.credit_ledger.insert_one({
            "user_id": user_id,
            "entry_type": "SUBSCRIPTION_CREDIT",
            "amount": credits_to_add,
            "ref_type": "SUBSCRIPTION",
            "ref_id": subscription["subscription_id"],
            "description": f"{plan.get('name', 'Subscription')} monthly credits",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"Added {credits_to_add} credits to user {user_id} for subscription payment")
    
    async def _handle_payment_failed(
        self, 
        subscription: Dict, 
        data: Dict, 
        user_id: str
    ):
        """Handle failed subscription payment"""
        await self.db.subscriptions.update_one(
            {"subscription_id": subscription["subscription_id"]},
            {
                "$set": {
                    "last_payment_failed_at": datetime.now(timezone.utc).isoformat(),
                    "payment_failure_reason": data.get("payment", {}).get("payment_status_reason", "Unknown")
                },
                "$inc": {"failed_payments": 1}
            }
        )
        
        # Log incident
        await self.db.incidents.insert_one({
            "type": "subscription_payment_failed",
            "severity": "warning",
            "user_id": user_id,
            "subscription_id": subscription["subscription_id"],
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        logger.warning(f"Payment failed for subscription {subscription['subscription_id']}")
    
    async def _handle_cancellation(self, subscription: Dict, user_id: str):
        """Handle subscription cancellation"""
        await self.db.subscriptions.update_one(
            {"subscription_id": subscription["subscription_id"]},
            {
                "$set": {
                    "status": "CANCELLED",
                    "cancelled_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        await self.db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "plan": "free",
                    "subscription_id": None,
                    "plan_downgraded_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        logger.info(f"Subscription cancelled for user {user_id}")


# Global instance
_subscription_service: Optional[CashfreeSubscriptionService] = None


async def get_subscription_service(db) -> CashfreeSubscriptionService:
    """Get or create subscription service singleton"""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = CashfreeSubscriptionService(db)
    return _subscription_service


def get_subscription_plans() -> Dict[str, Dict]:
    """Get all available subscription plans"""
    return SUBSCRIPTION_PLANS
