"""
Admin Payment Verification Dashboard API
Build for investigation and correction — not just dashboards.
Answer in under 2 minutes: Did user pay? Did we grant access? Did webhook arrive? Did money settle?
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import hashlib
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user, add_credits

router = APIRouter(prefix="/admin/payments", tags=["Admin Payments"])

# Cashfree config
CASHFREE_APP_ID = os.environ.get("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.environ.get("CASHFREE_SECRET_KEY")
CASHFREE_ENVIRONMENT = "PRODUCTION"

# Initialize Cashfree client
cashfree_client = None
try:
    from cashfree_pg.api_client import Cashfree
    if CASHFREE_APP_ID and CASHFREE_SECRET_KEY:
        cashfree_env = Cashfree.PRODUCTION if CASHFREE_ENVIRONMENT == "PRODUCTION" else Cashfree.SANDBOX
        cashfree_client = Cashfree(
            XEnvironment=cashfree_env,
            XClientId=CASHFREE_APP_ID,
            XClientSecret=CASHFREE_SECRET_KEY
        )
except Exception as e:
    logger.warning(f"Admin payments: Cashfree SDK init failed: {e}")

API_VERSION = "2023-08-01"


def _safe_order(o):
    """Remove _id and convert for JSON response"""
    if o and "_id" in o:
        del o["_id"]
    return o


# ─── STATS ───────────────────────────────────────────────
@router.get("/stats")
async def get_payment_stats(user: dict = Depends(get_admin_user)):
    """Top summary strip — key operational metrics"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    pipeline_today = [
        {"$match": {"gateway": "cashfree", "createdAt": {"$gte": today_start.isoformat()}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$displayAmount"}
        }}
    ]
    status_counts_today = {}
    total_revenue_today = 0
    async for doc in db.orders.aggregate(pipeline_today):
        status_counts_today[doc["_id"]] = doc["count"]
        if doc["_id"] in ("SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED", "PAID"):
            total_revenue_today += doc["total_amount"]

    orders_today = sum(status_counts_today.values())
    succeeded_today = sum(status_counts_today.get(s, 0) for s in ("SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED", "PAID"))
    failed_today = status_counts_today.get("FAILED", 0)

    # Webhook stats today
    webhook_total = await db.webhook_events.count_documents({"receivedAt": {"$gte": today_start.isoformat()}})
    webhook_failed = await db.webhook_events.count_documents({
        "receivedAt": {"$gte": today_start.isoformat()},
        "status": {"$in": ["FAILED", "ERROR"]}
    })

    # Unreconciled: orders SUCCESS in Cashfree but entitlement not applied
    unreconciled = await db.orders.count_documents({
        "gateway": "cashfree",
        "status": {"$in": ["SUCCESS", "PAID"]},
        "entitlementApplied": {"$ne": True},
        "createdAt": {"$gte": week_ago.isoformat()}
    })

    # Settlements pending
    settlements_pending = await db.orders.count_documents({
        "gateway": "cashfree",
        "status": {"$in": ["SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED"]},
        "settlementStatus": {"$exists": False},
        "createdAt": {"$gte": week_ago.isoformat()}
    })

    # Total settled amount
    settled_pipeline = [
        {"$match": {"gateway": "cashfree", "settlementStatus": "SUCCESS", "createdAt": {"$gte": today_start.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$displayAmount"}}}
    ]
    settled_amount = 0
    async for doc in db.orders.aggregate(settled_pipeline):
        settled_amount = doc["total"]

    # Refunds today
    refunds_today = await db.refund_logs.count_documents({"createdAt": {"$gte": today_start.isoformat()}})

    return {
        "environment": CASHFREE_ENVIRONMENT,
        "cashfree_configured": cashfree_client is not None,
        "orders_today": orders_today,
        "succeeded_today": succeeded_today,
        "failed_today": failed_today,
        "webhook_events_today": webhook_total,
        "webhook_failures_today": webhook_failed,
        "unreconciled_orders": unreconciled,
        "settlements_pending": settlements_pending,
        "settled_amount_today": settled_amount,
        "revenue_today": total_revenue_today,
        "refunds_today": refunds_today,
    }


# ─── ORDERS ──────────────────────────────────────────────
@router.get("/orders")
async def get_orders(
    user: dict = Depends(get_admin_user),
    status: Optional[str] = None,
    email: Optional[str] = None,
    order_id: Optional[str] = None,
    unreconciled_only: bool = False,
    days: int = Query(default=7, le=90),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    """Order list with filters — one-row truth per order"""
    query = {"gateway": "cashfree"}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query["createdAt"] = {"$gte": cutoff}

    if status:
        query["status"] = status
    if email:
        query["userEmail"] = {"$regex": email, "$options": "i"}
    if order_id:
        query["order_id"] = {"$regex": order_id, "$options": "i"}
    if unreconciled_only:
        query["status"] = {"$in": ["SUCCESS", "PAID"]}
        query["entitlementApplied"] = {"$ne": True}

    total = await db.orders.count_documents(query)
    orders = []
    cursor = db.orders.find(query, {"_id": 0}).sort("createdAt", -1).skip(skip).limit(limit)
    async for o in cursor:
        # Enrich with user lookup
        user_doc = await db.users.find_one({"id": o.get("userId")}, {"_id": 0, "email": 1, "credits": 1, "subscription": 1})
        o["user_current_credits"] = user_doc.get("credits") if user_doc else None
        o["user_subscription"] = user_doc.get("subscription") if user_doc else None
        # Webhook status for this order
        webhook = await db.webhook_events.find_one({"orderId": o.get("order_id")}, {"_id": 0, "status": 1, "signatureVerified": 1, "receivedAt": 1})
        o["webhook_received"] = webhook is not None
        o["webhook_status"] = webhook.get("status") if webhook else None
        o["webhook_signature_ok"] = webhook.get("signatureVerified") if webhook else None
        orders.append(o)

    return {"total": total, "orders": orders, "environment": CASHFREE_ENVIRONMENT}


# ─── SINGLE ORDER DRILLDOWN ─────────────────────────────
@router.get("/orders/{order_id}")
async def get_order_drilldown(order_id: str, user: dict = Depends(get_admin_user)):
    """Deep drilldown: internal state + Cashfree truth + webhook trace"""
    # Panel 1: Internal order
    order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # User info
    user_doc = await db.users.find_one({"id": order.get("userId")}, {"_id": 0, "email": 1, "credits": 1, "subscription": 1, "name": 1})

    # Panel 2: Cashfree truth (live fetch)
    cashfree_order = None
    cashfree_payments = []
    cashfree_settlements = []
    cashfree_error = None

    if cashfree_client:
        request_id = str(uuid.uuid4())
        try:
            # Fetch order from Cashfree
            cf_response = cashfree_client.PGFetchOrder(API_VERSION, order_id, None, None)
            if cf_response and cf_response.data:
                d = cf_response.data
                cashfree_order = {
                    "order_id": getattr(d, "order_id", None),
                    "cf_order_id": getattr(d, "cf_order_id", None),
                    "order_status": getattr(d, "order_status", None),
                    "order_amount": getattr(d, "order_amount", None),
                    "order_currency": getattr(d, "order_currency", None),
                    "created_at": str(getattr(d, "created_at", None)),
                }
        except Exception as e:
            cashfree_error = f"Fetch order failed: {str(e)}"
            logger.error(f"[{request_id}] Cashfree fetch order error: {e}")

        try:
            # Fetch payments for order
            pay_response = cashfree_client.PGOrderFetchPayments(API_VERSION, order_id, None, None)
            if pay_response and pay_response.data:
                for p in pay_response.data:
                    cashfree_payments.append({
                        "cf_payment_id": getattr(p, "cf_payment_id", None),
                        "payment_status": getattr(p, "payment_status", None),
                        "payment_amount": getattr(p, "payment_amount", None),
                        "payment_method": str(getattr(p, "payment_method", None)),
                        "payment_time": str(getattr(p, "payment_time", None)),
                        "error_details": getattr(p, "error_details", None),
                    })
        except Exception as e:
            if not cashfree_error:
                cashfree_error = f"Fetch payments failed: {str(e)}"
            logger.error(f"[{request_id}] Cashfree fetch payments error: {e}")

        try:
            # Fetch settlements
            settle_response = cashfree_client.PGOrderFetchSettlements(API_VERSION, order_id, None, None)
            if settle_response and settle_response.data:
                for s in settle_response.data:
                    cashfree_settlements.append({
                        "cf_settlement_id": getattr(s, "cf_settlement_id", None),
                        "settlement_amount": getattr(s, "settlement_amount", None),
                        "service_charge": getattr(s, "service_charge", None),
                        "service_tax": getattr(s, "service_tax", None),
                        "transfer_time": str(getattr(s, "transfer_time", None)),
                        "transfer_utr": getattr(s, "transfer_utr", None),
                    })
        except Exception as e:
            logger.error(f"[{request_id}] Cashfree fetch settlements error: {e}")

    # Panel 3: Webhook trace
    webhooks = []
    cursor = db.webhook_events.find({"orderId": order_id}, {"_id": 0}).sort("receivedAt", -1)
    async for w in cursor:
        webhooks.append(w)

    # Credit transactions for this order
    credit_txns = []
    cursor = db.credit_transactions.find({"order_id": order_id}, {"_id": 0}).sort("created_at", -1)
    async for t in cursor:
        credit_txns.append(t)

    # Build mismatch flags
    mismatches = []
    cf_status = cashfree_order.get("order_status") if cashfree_order else None
    internal_status = order.get("status")
    entitlement = order.get("entitlementApplied", False)

    if cf_status == "PAID" and internal_status not in ("SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED"):
        mismatches.append("PAID_IN_CASHFREE_NOT_IN_DB")
    if entitlement and cf_status and cf_status != "PAID":
        mismatches.append("ACCESS_GRANTED_WITHOUT_PAYMENT")
    if cf_status == "PAID" and not webhooks:
        mismatches.append("WEBHOOK_MISSING")
    if cf_status == "PAID" and not cashfree_settlements:
        mismatches.append("SETTLEMENT_PENDING")
    if len([w for w in webhooks if w.get("status") == "PROCESSED"]) > 1:
        mismatches.append("DUPLICATE_WEBHOOK")
    failed_sig = [w for w in webhooks if w.get("signatureVerified") is False]
    if failed_sig:
        mismatches.append("SIGNATURE_VERIFICATION_FAILED")

    return {
        "environment": CASHFREE_ENVIRONMENT,
        "order": order,
        "user": user_doc,
        "cashfree": {
            "order": cashfree_order,
            "payments": cashfree_payments,
            "settlements": cashfree_settlements,
            "error": cashfree_error,
        },
        "webhooks": webhooks,
        "credit_transactions": credit_txns,
        "mismatches": mismatches,
        "mismatch_count": len(mismatches),
    }


# ─── RECONCILE ───────────────────────────────────────────
@router.post("/reconcile/{order_id}")
async def reconcile_order(order_id: str, user: dict = Depends(get_admin_user)):
    """
    Reconcile single order: Cashfree = source of truth.
    Fetches order + payments + settlements from Cashfree,
    compares with DB, fixes mismatches.
    """
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree client not configured")

    request_id = str(uuid.uuid4())
    actions_taken = []
    errors = []

    # 1. Fetch internal order
    order = await db.orders.find_one({"order_id": order_id, "gateway": "cashfree"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in DB")

    # 2. Fetch Cashfree order truth
    cf_order_status = None
    try:
        cf_response = cashfree_client.PGFetchOrder(API_VERSION, order_id, None, None)
        if cf_response and cf_response.data:
            cf_order_status = getattr(cf_response.data, "order_status", None)
            actions_taken.append(f"Fetched Cashfree order: status={cf_order_status}")
    except Exception as e:
        errors.append(f"[{request_id}] Fetch order failed: {str(e)}")

    # 3. Fetch Cashfree payments
    successful_payment = None
    try:
        pay_response = cashfree_client.PGOrderFetchPayments(API_VERSION, order_id, None, None)
        if pay_response and pay_response.data:
            for p in pay_response.data:
                if getattr(p, "payment_status", "") == "SUCCESS":
                    successful_payment = {
                        "cf_payment_id": getattr(p, "cf_payment_id", None),
                        "payment_amount": getattr(p, "payment_amount", None),
                        "payment_time": str(getattr(p, "payment_time", None)),
                    }
                    break
            actions_taken.append(f"Fetched {len(pay_response.data)} payment attempts")
    except Exception as e:
        errors.append(f"[{request_id}] Fetch payments failed: {str(e)}")

    # 4. Fetch settlements
    settlement = None
    try:
        settle_response = cashfree_client.PGOrderFetchSettlements(API_VERSION, order_id, None, None)
        if settle_response and settle_response.data:
            for s in settle_response.data:
                settlement = {
                    "cf_settlement_id": getattr(s, "cf_settlement_id", None),
                    "settlement_amount": getattr(s, "settlement_amount", None),
                    "transfer_utr": getattr(s, "transfer_utr", None),
                    "transfer_time": str(getattr(s, "transfer_time", None)),
                }
                break
            actions_taken.append(f"Fetched settlement: {settlement}")
    except Exception as e:
        logger.info(f"[{request_id}] No settlement yet for {order_id}: {e}")

    # 5. Reconciliation logic
    internal_status = order.get("status")
    entitlement = order.get("entitlementApplied", False)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Case: Cashfree says PAID but our DB doesn't reflect it
    if cf_order_status == "PAID" and internal_status not in ("SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED"):
        # Fix: update status and grant entitlement
        credits_to_add = order.get("credits", 0)
        user_id = order.get("userId")

        if user_id and credits_to_add > 0 and not entitlement:
            try:
                new_balance = await add_credits(
                    user_id=user_id,
                    amount=credits_to_add,
                    description=f"Reconciliation - {order.get('productName', '')}",
                    tx_type="RECONCILIATION",
                    order_id=order_id
                )
                product_type = order.get("productType", "topup")
                final_status = "SUBSCRIPTION_ACTIVATED" if product_type == "subscription" else "CREDIT_APPLIED"

                if product_type == "subscription":
                    product_id = order.get("productId", "")
                    try:
                        from config.pricing import SUBSCRIPTION_PLANS
                        plan = SUBSCRIPTION_PLANS.get(product_id, {})
                        duration_days = plan.get("duration_days", 30)
                    except Exception:
                        duration_days = 30
                    await db.users.update_one(
                        {"id": user_id},
                        {"$set": {"subscription": {
                            "planId": product_id,
                            "planName": order.get("productName", ""),
                            "status": "active",
                            "startDate": now_iso,
                            "endDate": (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat(),
                            "orderId": order_id,
                            "source": "reconciliation",
                        }}}
                    )

                await db.orders.update_one(
                    {"order_id": order_id},
                    {"$set": {
                        "status": final_status,
                        "entitlementApplied": True,
                        "entitlementAppliedAt": now_iso,
                        "reconciledAt": now_iso,
                        "reconciledBy": user.get("email", "admin"),
                    },
                    "$push": {"statusHistory": {"status": f"RECONCILED_{final_status}", "at": now_iso}}}
                )
                actions_taken.append(f"FIXED: Granted {credits_to_add} credits, new balance={new_balance}, status={final_status}")
            except Exception as e:
                errors.append(f"Failed to grant entitlement: {str(e)}")
        else:
            await db.orders.update_one(
                {"order_id": order_id},
                {"$set": {"status": "SUCCESS", "reconciledAt": now_iso},
                 "$push": {"statusHistory": {"status": "RECONCILED_STATUS_FIX", "at": now_iso}}}
            )
            actions_taken.append("FIXED: Updated status to SUCCESS (entitlement already applied or invalid)")

    # Case: Entitlement applied without payment success
    elif entitlement and cf_order_status != "PAID":
        actions_taken.append(f"WARNING: Entitlement applied but Cashfree status is '{cf_order_status}' — requires manual review")

    # Case: Already reconciled
    elif cf_order_status == "PAID" and internal_status in ("SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED") and entitlement:
        actions_taken.append("OK: Order already properly reconciled")
    else:
        actions_taken.append(f"No action needed: cf_status={cf_order_status}, db_status={internal_status}")

    # 6. Update settlement status if available
    if settlement:
        await db.orders.update_one(
            {"order_id": order_id},
            {"$set": {
                "settlementStatus": "SUCCESS",
                "settlementId": settlement.get("cf_settlement_id"),
                "settlementAmount": settlement.get("settlement_amount"),
                "settlementUTR": settlement.get("transfer_utr"),
                "settledAt": settlement.get("transfer_time"),
            }}
        )
        actions_taken.append(f"Updated settlement: UTR={settlement.get('transfer_utr')}")

    # 7. Log reconciliation run
    await db.payment_reconciliation_runs.insert_one({
        "run_id": request_id,
        "order_id": order_id,
        "started_at": now_iso,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "actions_taken": actions_taken,
        "errors": errors,
        "admin_email": user.get("email"),
        "cf_order_status": cf_order_status,
        "internal_status_before": internal_status,
    })

    return {
        "order_id": order_id,
        "request_id": request_id,
        "cf_order_status": cf_order_status,
        "internal_status_before": internal_status,
        "actions_taken": actions_taken,
        "errors": errors,
        "settlement": settlement,
        "successful_payment": successful_payment,
    }


# ─── WEBHOOKS ────────────────────────────────────────────
@router.get("/webhooks")
async def get_webhooks(
    user: dict = Depends(get_admin_user),
    order_id: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(default=7, le=90),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    """Webhook log viewer with filters"""
    query = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query["receivedAt"] = {"$gte": cutoff}

    if order_id:
        query["orderId"] = {"$regex": order_id, "$options": "i"}
    if status:
        query["status"] = status

    total = await db.webhook_events.count_documents(query)
    webhooks = []
    cursor = db.webhook_events.find(query, {"_id": 0}).sort("receivedAt", -1).skip(skip).limit(limit)
    async for w in cursor:
        webhooks.append(w)

    return {"total": total, "webhooks": webhooks}


# ─── SETTLEMENTS ─────────────────────────────────────────
@router.get("/settlements")
async def get_settlements(
    user: dict = Depends(get_admin_user),
    days: int = Query(default=7, le=90),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
):
    """Settlement status for orders"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    query = {
        "gateway": "cashfree",
        "status": {"$in": ["SUCCESS", "CREDIT_APPLIED", "SUBSCRIPTION_ACTIVATED"]},
        "createdAt": {"$gte": cutoff},
    }

    total = await db.orders.count_documents(query)
    orders = []
    cursor = db.orders.find(query, {
        "_id": 0, "order_id": 1, "userEmail": 1, "productName": 1,
        "displayAmount": 1, "status": 1, "settlementStatus": 1,
        "settlementId": 1, "settlementAmount": 1, "settlementUTR": 1,
        "settledAt": 1, "paidAt": 1, "createdAt": 1, "currency": 1,
    }).sort("createdAt", -1).skip(skip).limit(limit)
    async for o in cursor:
        orders.append(o)

    return {"total": total, "settlements": orders}


# ─── FETCH FROM CASHFREE (manual action) ─────────────────
@router.post("/fetch-cashfree/{order_id}")
async def fetch_from_cashfree(order_id: str, user: dict = Depends(get_admin_user)):
    """Manually fetch order + payments + settlements from Cashfree (does NOT modify DB)"""
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree client not configured")

    result = {"order": None, "payments": [], "settlements": [], "errors": []}
    request_id = str(uuid.uuid4())

    try:
        cf_response = cashfree_client.PGFetchOrder(API_VERSION, order_id, None, None)
        if cf_response and cf_response.data:
            d = cf_response.data
            result["order"] = {
                "order_id": getattr(d, "order_id", None),
                "cf_order_id": getattr(d, "cf_order_id", None),
                "order_status": getattr(d, "order_status", None),
                "order_amount": getattr(d, "order_amount", None),
                "order_currency": getattr(d, "order_currency", None),
                "created_at": str(getattr(d, "created_at", None)),
            }
    except Exception as e:
        result["errors"].append(f"Fetch order: {str(e)}")

    try:
        pay_response = cashfree_client.PGOrderFetchPayments(API_VERSION, order_id, None, None)
        if pay_response and pay_response.data:
            for p in pay_response.data:
                result["payments"].append({
                    "cf_payment_id": getattr(p, "cf_payment_id", None),
                    "payment_status": getattr(p, "payment_status", None),
                    "payment_amount": getattr(p, "payment_amount", None),
                    "payment_method": str(getattr(p, "payment_method", None)),
                    "payment_time": str(getattr(p, "payment_time", None)),
                })
    except Exception as e:
        result["errors"].append(f"Fetch payments: {str(e)}")

    try:
        settle_response = cashfree_client.PGOrderFetchSettlements(API_VERSION, order_id, None, None)
        if settle_response and settle_response.data:
            for s in settle_response.data:
                result["settlements"].append({
                    "cf_settlement_id": getattr(s, "cf_settlement_id", None),
                    "settlement_amount": getattr(s, "settlement_amount", None),
                    "service_charge": getattr(s, "service_charge", None),
                    "service_tax": getattr(s, "service_tax", None),
                    "transfer_time": str(getattr(s, "transfer_time", None)),
                    "transfer_utr": getattr(s, "transfer_utr", None),
                })
    except Exception as e:
        result["errors"].append(f"Fetch settlements: {str(e)}")

    result["request_id"] = request_id
    result["environment"] = CASHFREE_ENVIRONMENT
    return result


# ─── REPLAY WEBHOOK LOGIC ───────────────────────────────
@router.post("/replay-webhook/{order_id}")
async def replay_webhook_logic(order_id: str, user: dict = Depends(get_admin_user)):
    """
    Re-run the webhook processing logic for an order.
    Does NOT re-verify signature — uses Cashfree API as source of truth instead.
    """
    if not cashfree_client:
        raise HTTPException(status_code=500, detail="Cashfree client not configured")

    # Fetch fresh status from Cashfree
    try:
        cf_response = cashfree_client.PGFetchOrder(API_VERSION, order_id, None, None)
        if not cf_response or not cf_response.data:
            raise HTTPException(status_code=404, detail="Order not found in Cashfree")

        cf_status = getattr(cf_response.data, "order_status", None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cashfree API error: {str(e)}")

    if cf_status != "PAID":
        return {"status": "NO_ACTION", "message": f"Cashfree order status is '{cf_status}', not PAID. No replay needed."}

    # Fetch payment details
    payment_data = {}
    try:
        pay_response = cashfree_client.PGOrderFetchPayments(API_VERSION, order_id, None, None)
        if pay_response and pay_response.data:
            for p in pay_response.data:
                if getattr(p, "payment_status", "") == "SUCCESS":
                    payment_data = {
                        "cf_payment_id": getattr(p, "cf_payment_id", None),
                        "payment_amount": getattr(p, "payment_amount", None),
                        "payment_time": str(getattr(p, "payment_time", None)),
                    }
                    break
    except Exception:
        pass

    # Use the existing WebhookProcessor logic
    try:
        from routes.cashfree_webhook_handler import WebhookProcessor
        result = await WebhookProcessor.process_payment_success(order_id, payment_data)
        return {
            "status": "REPLAYED",
            "cf_order_status": cf_status,
            "result": result,
            "admin": user.get("email"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")
