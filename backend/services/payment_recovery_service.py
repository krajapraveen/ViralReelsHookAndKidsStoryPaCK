"""
CreatorStudio AI - Payment Recovery Service
============================================
Automatic payment reconciliation, delivery verification, and refund handling.

Features:
- Payment state machine
- Webhook verification
- Auto-reconciliation for stuck payments
- Auto-refund for failed deliveries
- Credit/subscription delivery tracking
"""
import asyncio
import hmac
import hashlib
import json
import time
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, add_credits
from services.self_healing_core import (
    PaymentState, metrics, alert_manager, IncidentLogger, 
    AlertSeverity, CorrelationContext
)

# ============================================
# PAYMENT CONFIGURATION
# ============================================

# Cashfree Configuration
CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_WEBHOOK_SECRET = os.environ.get("CASHFREE_WEBHOOK_SECRET")

# Auto-refund settings
AUTO_REFUND_ENABLED = os.environ.get("AUTO_REFUND_ENABLED", "true").lower() == "true"
AUTO_REFUND_DELAY_MINUTES = int(os.environ.get("AUTO_REFUND_DELAY_MINUTES", "30"))
MAX_RECONCILIATION_ATTEMPTS = int(os.environ.get("MAX_RECONCILIATION_ATTEMPTS", "3"))

# Product definitions (must match cashfree_payments.py)
PRODUCTS = {
    "starter": {"name": "Starter Pack", "credits": 100, "price": 499},
    "creator": {"name": "Creator Pack", "credits": 300, "price": 999},
    "pro": {"name": "Pro Pack", "credits": 1000, "price": 2499},
    "enterprise": {"name": "Enterprise Pack", "credits": 5000, "price": 9999},
}


# ============================================
# PAYMENT STATE MACHINE
# ============================================

@dataclass
class Payment:
    """Payment record with state tracking"""
    order_id: str
    user_id: str
    amount: float
    currency: str = "INR"
    product_id: str = ""
    credits: int = 0
    
    # State tracking
    state: PaymentState = PaymentState.CREATED
    previous_state: Optional[PaymentState] = None
    
    # Gateway details
    gateway_order_id: str = ""
    gateway_payment_id: str = ""
    gateway_signature: str = ""
    
    # Delivery tracking
    delivered: bool = False
    delivery_attempts: int = 0
    delivery_error: str = ""
    delivered_at: Optional[datetime] = None
    
    # Reconciliation
    reconciliation_attempts: int = 0
    last_reconciliation: Optional[datetime] = None
    
    # Refund tracking
    refund_requested: bool = False
    refund_id: str = ""
    refunded_at: Optional[datetime] = None
    refund_amount: float = 0
    refund_reason: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metadata
    correlation_id: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def can_transition_to(self, new_state: PaymentState) -> bool:
        """Check if state transition is valid"""
        valid_transitions = {
            PaymentState.CREATED: [PaymentState.PENDING, PaymentState.CANCELLED],
            PaymentState.PENDING: [PaymentState.SUCCESS, PaymentState.FAILED, PaymentState.CANCELLED],
            PaymentState.SUCCESS: [PaymentState.REFUNDED, PaymentState.RECONCILING],
            PaymentState.FAILED: [PaymentState.REFUNDED],
            PaymentState.RECONCILING: [PaymentState.SUCCESS, PaymentState.REFUNDED],
            PaymentState.CANCELLED: [],
            PaymentState.REFUNDED: []
        }
        return new_state in valid_transitions.get(self.state, [])
    
    def transition_to(self, new_state: PaymentState) -> bool:
        """Transition to new state if valid"""
        if self.can_transition_to(new_state):
            self.previous_state = self.state
            self.state = new_state
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency,
            "product_id": self.product_id,
            "credits": self.credits,
            "state": self.state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "gateway_order_id": self.gateway_order_id,
            "gateway_payment_id": self.gateway_payment_id,
            "delivered": self.delivered,
            "delivery_attempts": self.delivery_attempts,
            "delivery_error": self.delivery_error,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "reconciliation_attempts": self.reconciliation_attempts,
            "last_reconciliation": self.last_reconciliation.isoformat() if self.last_reconciliation else None,
            "refund_requested": self.refund_requested,
            "refund_id": self.refund_id,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
            "refund_amount": self.refund_amount,
            "refund_reason": self.refund_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Payment":
        data["state"] = PaymentState(data.get("state", "created"))
        if data.get("previous_state"):
            data["previous_state"] = PaymentState(data["previous_state"])
        for field in ["delivered_at", "last_reconciliation", "refunded_at", "created_at", "updated_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================
# WEBHOOK VERIFICATION
# ============================================

class WebhookVerifier:
    """Verifies Cashfree webhook signatures"""
    
    @staticmethod
    def verify_cashfree_signature(payload: bytes, signature: str, timestamp: str) -> bool:
        """
        Verify Cashfree webhook signature
        """
        if not CASHFREE_WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured - skipping verification")
            return True
        
        try:
            # Cashfree signature format: timestamp.payload
            sign_string = f"{timestamp}{payload.decode()}"
            
            expected_signature = hmac.new(
                CASHFREE_WEBHOOK_SECRET.encode(),
                sign_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def verify_payment_amount(payment: Payment, webhook_amount: float) -> bool:
        """Verify payment amount matches"""
        return abs(payment.amount - webhook_amount) < 0.01


# ============================================
# PAYMENT DELIVERY SERVICE
# ============================================

class PaymentDeliveryService:
    """
    Handles delivery of credits/subscriptions after successful payment
    """
    
    @staticmethod
    async def deliver_payment(payment: Payment) -> Dict[str, Any]:
        """
        Deliver credits/subscription for a successful payment
        """
        if payment.delivered:
            return {"success": True, "message": "Already delivered"}
        
        payment.delivery_attempts += 1
        payment.updated_at = datetime.now(timezone.utc)
        
        try:
            # Deliver credits
            if payment.credits > 0:
                await add_credits(
                    payment.user_id,
                    payment.credits,
                    f"Payment {payment.order_id} - {payment.product_id}"
                )
            
            # Handle subscription (if applicable)
            if payment.product_id and "subscription" in payment.product_id.lower():
                await PaymentDeliveryService._activate_subscription(payment)
            
            # Mark as delivered
            payment.delivered = True
            payment.delivered_at = datetime.now(timezone.utc)
            payment.delivery_error = ""
            
            await PaymentDeliveryService._save_payment(payment)
            await metrics.record_payment("delivery", payment.amount, success=True)
            
            logger.info(f"Payment {payment.order_id} delivered: {payment.credits} credits to user {payment.user_id}")
            
            return {"success": True, "credits_delivered": payment.credits}
            
        except Exception as e:
            payment.delivery_error = str(e)
            await PaymentDeliveryService._save_payment(payment)
            await metrics.record_payment("delivery", payment.amount, success=False)
            
            logger.error(f"Payment delivery failed for {payment.order_id}: {e}")
            
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _activate_subscription(payment: Payment):
        """Activate user subscription"""
        subscription_duration_days = 30  # Default monthly
        
        await db.users.update_one(
            {"_id": payment.user_id},
            {
                "$set": {
                    "subscription": {
                        "plan": payment.product_id,
                        "started_at": datetime.now(timezone.utc),
                        "expires_at": datetime.now(timezone.utc) + timedelta(days=subscription_duration_days),
                        "payment_id": payment.order_id
                    }
                }
            }
        )
    
    @staticmethod
    async def _save_payment(payment: Payment):
        """Save payment to database"""
        await db.payment_records.update_one(
            {"order_id": payment.order_id},
            {"$set": payment.to_dict()},
            upsert=True
        )


# ============================================
# PAYMENT RECONCILIATION SERVICE
# ============================================

class PaymentReconciliationService:
    """
    Automatically reconciles payments that succeeded but weren't delivered
    """
    
    @staticmethod
    async def run_reconciliation():
        """
        Find and reconcile stuck payments
        Runs every 2-5 minutes via background task
        """
        logger.info("Running payment reconciliation...")
        
        # Find stuck payments (SUCCESS but not delivered)
        stuck_payments = await db.payment_records.find({
            "state": PaymentState.SUCCESS.value,
            "delivered": False,
            "reconciliation_attempts": {"$lt": MAX_RECONCILIATION_ATTEMPTS},
            "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=24)}
        }).to_list(length=100)
        
        reconciled_count = 0
        failed_count = 0
        
        for payment_data in stuck_payments:
            payment = Payment.from_dict(payment_data)
            
            # Skip if recently reconciled
            if payment.last_reconciliation:
                time_since_last = datetime.now(timezone.utc) - payment.last_reconciliation
                if time_since_last.total_seconds() < 120:  # 2 minutes
                    continue
            
            payment.reconciliation_attempts += 1
            payment.last_reconciliation = datetime.now(timezone.utc)
            payment.transition_to(PaymentState.RECONCILING)
            
            logger.info(f"Reconciling payment {payment.order_id} (attempt {payment.reconciliation_attempts})")
            
            # Attempt delivery
            result = await PaymentDeliveryService.deliver_payment(payment)
            
            if result["success"]:
                payment.transition_to(PaymentState.SUCCESS)
                reconciled_count += 1
                
                await IncidentLogger.log_incident(
                    incident_type="payment_reconciled",
                    severity="info",
                    description=f"Auto-reconciled payment {payment.order_id}",
                    user_id=payment.user_id,
                    correlation_id=payment.correlation_id,
                    context={"credits": payment.credits, "amount": payment.amount},
                    resolution="Credits delivered automatically"
                )
            else:
                failed_count += 1
                
                # Check if we should auto-refund
                if payment.reconciliation_attempts >= MAX_RECONCILIATION_ATTEMPTS:
                    await PaymentReconciliationService._initiate_auto_refund(payment)
            
            await PaymentDeliveryService._save_payment(payment)
        
        logger.info(f"Reconciliation complete: {reconciled_count} reconciled, {failed_count} failed")
        await metrics.gauge("reconciliation.stuck_payments", len(stuck_payments))
        
        return {"reconciled": reconciled_count, "failed": failed_count}
    
    @staticmethod
    async def _initiate_auto_refund(payment: Payment):
        """Initiate auto-refund for undeliverable payment"""
        if not AUTO_REFUND_ENABLED:
            logger.warning(f"Auto-refund disabled for payment {payment.order_id}")
            
            # Create alert for manual intervention
            await alert_manager.create_alert(
                severity=AlertSeverity.CRITICAL,
                title="Payment Delivery Failed - Manual Intervention Required",
                message=f"Payment {payment.order_id} for user {payment.user_id} could not be delivered after {MAX_RECONCILIATION_ATTEMPTS} attempts",
                source="payment_reconciliation",
                correlation_id=payment.correlation_id,
                metadata={"amount": payment.amount, "credits": payment.credits}
            )
            return
        
        logger.info(f"Initiating auto-refund for payment {payment.order_id}")
        
        result = await PaymentRefundService.request_refund(
            payment,
            reason="Auto-refund: Delivery failed after multiple attempts"
        )
        
        if result["success"]:
            await IncidentLogger.log_incident(
                incident_type="payment_auto_refunded",
                severity="warning",
                description=f"Auto-refunded payment {payment.order_id}",
                user_id=payment.user_id,
                correlation_id=payment.correlation_id,
                context={"amount": payment.amount, "refund_id": result.get("refund_id")},
                resolution="Full refund processed automatically"
            )


# ============================================
# PAYMENT REFUND SERVICE
# ============================================

class PaymentRefundService:
    """
    Handles refund requests and processing
    """
    
    @staticmethod
    async def request_refund(payment: Payment, reason: str, amount: float = None) -> Dict[str, Any]:
        """
        Request a refund for a payment
        """
        if payment.refund_requested:
            return {"success": False, "error": "Refund already requested"}
        
        if payment.state == PaymentState.REFUNDED:
            return {"success": False, "error": "Already refunded"}
        
        refund_amount = amount or payment.amount
        payment.refund_requested = True
        payment.refund_amount = refund_amount
        payment.refund_reason = reason
        
        try:
            # Call Cashfree refund API
            refund_result = await PaymentRefundService._process_cashfree_refund(payment, refund_amount)
            
            if refund_result["success"]:
                payment.refund_id = refund_result["refund_id"]
                payment.refunded_at = datetime.now(timezone.utc)
                payment.transition_to(PaymentState.REFUNDED)
                
                # If credits were delivered, deduct them back
                if payment.delivered and payment.credits > 0:
                    try:
                        from shared import deduct_credits
                        await deduct_credits(
                            payment.user_id,
                            payment.credits,
                            f"Refund for payment {payment.order_id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to deduct refunded credits: {e}")
                
                await PaymentDeliveryService._save_payment(payment)
                await metrics.record_payment("refund", refund_amount, success=True)
                
                logger.info(f"Refund processed for payment {payment.order_id}: {refund_amount}")
                
                return {"success": True, "refund_id": payment.refund_id}
            else:
                await PaymentDeliveryService._save_payment(payment)
                await metrics.record_payment("refund", refund_amount, success=False)
                
                return {"success": False, "error": refund_result.get("error", "Refund failed")}
                
        except Exception as e:
            logger.error(f"Refund error for payment {payment.order_id}: {e}")
            await PaymentDeliveryService._save_payment(payment)
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _process_cashfree_refund(payment: Payment, amount: float) -> Dict[str, Any]:
        """
        Process refund via Cashfree API
        """
        try:
            from cashfree_pg.api_client import Cashfree
            from cashfree_pg.models.create_refund_request import CreateRefundRequest
            
            if not CASHFREE_APP_ID or not CASHFREE_SECRET_KEY:
                logger.error("Cashfree credentials not configured")
                return {"success": False, "error": "Payment gateway not configured"}
            
            cashfree_env = Cashfree.PRODUCTION if os.environ.get("CASHFREE_ENVIRONMENT") == "PRODUCTION" else Cashfree.SANDBOX
            cashfree_client = Cashfree(
                XEnvironment=cashfree_env,
                XClientId=CASHFREE_APP_ID,
                XClientSecret=CASHFREE_SECRET_KEY
            )
            
            refund_id = f"refund_{uuid.uuid4().hex[:12]}"
            
            refund_request = CreateRefundRequest(
                refund_id=refund_id,
                refund_amount=amount,
                refund_note=payment.refund_reason[:100]
            )
            
            response = cashfree_client.PGOrderCreateRefund(
                payment.gateway_order_id,
                refund_request,
                None
            )
            
            if response and hasattr(response, 'refund_id'):
                return {"success": True, "refund_id": response.refund_id}
            else:
                return {"success": False, "error": "Refund API returned no refund_id"}
                
        except ImportError:
            logger.warning("Cashfree SDK not available - simulating refund")
            return {"success": True, "refund_id": f"sim_refund_{uuid.uuid4().hex[:8]}"}
        except Exception as e:
            logger.error(f"Cashfree refund API error: {e}")
            return {"success": False, "error": str(e)}


# ============================================
# PAYMENT HEALTH MONITOR
# ============================================

class PaymentHealthMonitor:
    """
    Monitors payment system health and triggers alerts
    """
    
    @staticmethod
    async def check_health() -> Dict[str, Any]:
        """
        Check overall payment system health
        """
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)
        
        # Aggregate metrics
        pipeline = [
            {"$match": {"created_at": {"$gte": day_ago}}},
            {"$group": {
                "_id": "$state",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }}
        ]
        
        try:
            results = await db.payment_records.aggregate(pipeline).to_list(length=100)
            state_counts = {r["_id"]: {"count": r["count"], "amount": r["total_amount"]} for r in results}
        except Exception:
            state_counts = {}
        
        # Calculate health metrics
        total = sum(s.get("count", 0) for s in state_counts.values())
        successful = state_counts.get("success", {}).get("count", 0)
        failed = state_counts.get("failed", {}).get("count", 0)
        pending = state_counts.get("pending", {}).get("count", 0)
        
        success_rate = (successful / total * 100) if total > 0 else 100
        
        # Count stuck payments
        stuck_count = await db.payment_records.count_documents({
            "state": "success",
            "delivered": False,
            "created_at": {"$gte": hour_ago}
        })
        
        health = {
            "status": "healthy" if success_rate >= 95 and stuck_count == 0 else "degraded" if success_rate >= 80 else "critical",
            "metrics": {
                "total_24h": total,
                "successful_24h": successful,
                "failed_24h": failed,
                "pending": pending,
                "success_rate": round(success_rate, 2),
                "stuck_payments": stuck_count,
                "total_amount_24h": state_counts.get("success", {}).get("amount", 0)
            },
            "timestamp": now.isoformat()
        }
        
        # Trigger alert if health is critical
        if health["status"] == "critical":
            await alert_manager.create_alert(
                severity=AlertSeverity.CRITICAL,
                title="Payment System Health Critical",
                message=f"Payment success rate dropped to {success_rate:.1f}%, {stuck_count} stuck payments",
                source="payment_health_monitor"
            )
        elif stuck_count > 0:
            await alert_manager.create_alert(
                severity=AlertSeverity.WARNING,
                title="Stuck Payments Detected",
                message=f"{stuck_count} payments are stuck (paid but not delivered)",
                source="payment_health_monitor"
            )
        
        return health


# ============================================
# BACKGROUND TASKS
# ============================================

async def start_payment_reconciliation_task():
    """Background task for payment reconciliation"""
    while True:
        try:
            await PaymentReconciliationService.run_reconciliation()
            await PaymentHealthMonitor.check_health()
        except Exception as e:
            logger.error(f"Payment reconciliation task error: {e}")
        
        await asyncio.sleep(120)  # Run every 2 minutes
