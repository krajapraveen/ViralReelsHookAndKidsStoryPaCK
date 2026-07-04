"""Apple In-App Purchase endpoints.

Two surfaces:
  POST /api/iap/apple/verify   — client-triggered receipt validation for
                                  StoreKit 2 purchases (Bearer-JWT auth).
  POST /api/iap/apple/webhook  — App Store Server Notifications V2 (Apple
                                  posts signedPayload for renewals /
                                  refunds / cancellations). No auth —
                                  verified by JWS signature only.

Business rules (locked to the product catalogue in services/apple_iap.py):
  Consumable  → +N credits, no expiry, dedupe by transactionId
  Subscription→ +N credits per period + set subscription_status=active,
                subscription_expires_at, plan_type=<tier>; renewals repeat
                the grant only if the transactionId is new (idempotent).

Every credit grant writes a credit_ledger row via CreditsService.award_credits
using `apple_iap:<transactionId>` as the reference_id — this guarantees at
most one grant per transaction across replay, retry, and webhook.

Pinned by: tests/test_apple_iap_endpoints_2026_06.py
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from shared import get_current_user
from server import db  # module-level Motor db handle
from services.apple_iap import (
    CONSUMABLE_CREDIT_MAP,
    SUBSCRIPTION_MAP,
    AppleIAPNotConfigured,
    AppleIAPVerificationError,
    get_apple_iap_service,
)
from services.credits_service import get_credits_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iap/apple", tags=["iap-apple"])


# ── Request / response schemas ───────────────────────────────────────────────

class AppleVerifyRequest(BaseModel):
    """Body sent by the Expo client after a successful StoreKit 2 purchase."""
    platform: Optional[str] = Field(None, description="Always 'ios'")
    environment: Optional[str] = Field(None, description="Sandbox | Production (informational)")
    productId: str = Field(..., description="Apple product identifier that was purchased")
    transactionId: str = Field(..., description="Apple transaction ID from StoreKit 2")
    originalTransactionId: Optional[str] = Field(None, description="Original tx ID (subscriptions)")
    # jwsRepresentation is the source of truth — everything else is
    # cross-checked against its decoded claims.
    jwsRepresentation: str = Field(..., min_length=10, description="Signed JWS from StoreKit 2")
    transactionReceipt: Optional[str] = Field(None, description="Legacy SK1 receipt (unused, for logging)")


class AppleVerifyResponse(BaseModel):
    success: bool
    isConsumable: bool
    creditsGranted: Optional[int] = None
    subscriptionActive: Optional[bool] = None
    tier: Optional[str] = None
    expiresAt: Optional[str] = None
    totalCredits: int
    transactionId: str
    alreadyProcessed: bool = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _decode_dt(iso_millis: Optional[int]) -> Optional[datetime]:
    """Apple timestamps are milliseconds since epoch. Convert to aware UTC."""
    if not iso_millis:
        return None
    try:
        return datetime.fromtimestamp(int(iso_millis) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


async def _get_iap_service_or_503():
    try:
        return get_apple_iap_service()
    except AppleIAPNotConfigured as exc:
        # Return 503 (not 500) so the client can back off + retry — this
        # is the state during preview before App Store Connect banking
        # is approved.
        raise HTTPException(status_code=503, detail=str(exc))


# ── POST /api/iap/apple/verify ───────────────────────────────────────────────

@router.post("/verify", response_model=AppleVerifyResponse)
async def verify_apple_iap(
    payload: AppleVerifyRequest,
    user: dict = Depends(get_current_user),
):
    """Verify a StoreKit 2 signed transaction and grant entitlements."""
    service = await _get_iap_service_or_503()

    # 1. Verify + decode the JWS signature.
    try:
        tx = service.verify_transaction(payload.jwsRepresentation)
    except AppleIAPVerificationError as exc:
        logger.warning(f"Apple IAP verify failed for user={user['id']}: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Extract the authoritative claims from the JWS. NEVER trust the
    #    body fields for credit-granting decisions — the client can lie.
    verified_product_id = getattr(tx, "product_id", None) or ""
    verified_tx_id = str(getattr(tx, "transaction_id", "") or "")
    verified_original_tx_id = str(getattr(tx, "original_transaction_id", "") or "")
    verified_bundle_id = getattr(tx, "bundle_id", None) or ""
    verified_environment = getattr(tx, "environment", None)
    verified_environment_str = (
        verified_environment.value if hasattr(verified_environment, "value") else str(verified_environment or "")
    )
    expires_dt = _decode_dt(getattr(tx, "expires_date", None))
    purchase_dt = _decode_dt(getattr(tx, "purchase_date", None))

    if not verified_tx_id or not verified_product_id:
        raise HTTPException(status_code=400, detail="Apple JWS missing transactionId / productId")

    # 3. Bundle-ID guard — reject any receipt for a different app.
    if verified_bundle_id and verified_bundle_id != service.bundle_id:
        logger.warning(
            f"Apple IAP bundle_id mismatch: got={verified_bundle_id!r} "
            f"expected={service.bundle_id!r} user={user['id']}"
        )
        raise HTTPException(status_code=400, detail="Bundle ID mismatch")

    # 4. Cross-check optional body fields against the verified JWS. If
    #    the client claimed a different productId than the JWS says,
    #    reject — protects against a downgraded-price replay attack.
    if payload.productId and payload.productId != verified_product_id:
        logger.warning(
            f"Apple IAP body/JWS productId mismatch: body={payload.productId!r} "
            f"jws={verified_product_id!r} user={user['id']}"
        )
        raise HTTPException(status_code=400, detail="productId does not match verified receipt")

    # 5. Classify the product.
    consumable_credits = CONSUMABLE_CREDIT_MAP.get(verified_product_id)
    subscription_config = SUBSCRIPTION_MAP.get(verified_product_id)
    if consumable_credits is None and subscription_config is None:
        raise HTTPException(status_code=400, detail=f"Unknown product: {verified_product_id}")
    is_consumable = consumable_credits is not None

    # 6. Idempotency — write-once record in iap_transactions.
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = await db.iap_transactions.find_one(
        {"transactionId": verified_tx_id},
        {"_id": 0},
    )
    already_processed = existing is not None
    if not already_processed:
        await db.iap_transactions.insert_one({
            "userId": user["id"],
            "productId": verified_product_id,
            "transactionId": verified_tx_id,
            "originalTransactionId": verified_original_tx_id or verified_tx_id,
            "purchaseDate": purchase_dt.isoformat() if purchase_dt else None,
            "expiresDate": expires_dt.isoformat() if expires_dt else None,
            "environment": verified_environment_str,
            "isConsumable": is_consumable,
            "creditsGranted": consumable_credits or (subscription_config or {}).get("credits", 0),
            "source": "verify",
            "createdAt": now_iso,
        })

    # 7. Apply business rules. Fast path: the transaction is already in
    #    iap_transactions → return the existing state without touching
    #    credits again. This is the load-bearing idempotency guard: even
    #    if the client keeps retrying `/verify` for the same tx (network
    #    flake, double-tap), credits are granted at most once.
    credits_service = get_credits_service(db)
    reference_id = f"apple_iap:{verified_tx_id}"

    if already_processed:
        current = await db.users.find_one({"id": user["id"]}, {"_id": 0, "credits": 1})
        current_balance = int((current or {}).get("credits", 0))
        if is_consumable:
            return AppleVerifyResponse(
                success=True,
                isConsumable=True,
                creditsGranted=0,
                totalCredits=current_balance,
                transactionId=verified_tx_id,
                alreadyProcessed=True,
            )
        # Subscription replay — return the current tier state.
        u = current or {}
        return AppleVerifyResponse(
            success=True,
            isConsumable=False,
            creditsGranted=0,
            subscriptionActive=(u.get("subscription_status") == "active"),
            tier=(subscription_config or {}).get("tier"),
            expiresAt=u.get("subscription_expires_at"),
            totalCredits=current_balance,
            transactionId=verified_tx_id,
            alreadyProcessed=True,
        )

    if is_consumable:
        result = await credits_service.award_credits(
            user_id=user["id"],
            amount=consumable_credits,
            reason=f"Apple IAP consumable ({verified_product_id})",
            reference_id=reference_id,
        )
        return AppleVerifyResponse(
            success=True,
            isConsumable=True,
            creditsGranted=result.get("amount", 0),
            totalCredits=int(result.get("new_balance", 0)),
            transactionId=verified_tx_id,
            alreadyProcessed=already_processed,
        )

    # Subscription
    period_credits = int(subscription_config["credits"])
    tier = subscription_config["tier"]
    result = await credits_service.award_credits(
        user_id=user["id"],
        amount=period_credits,
        reason=f"Apple IAP subscription {tier} ({verified_product_id})",
        reference_id=reference_id,
    )
    subscription_active = bool(expires_dt and expires_dt > datetime.now(timezone.utc))
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "plan_type": tier,
            "subscription_status": "active" if subscription_active else "expired",
            "subscription_expires_at": expires_dt.isoformat() if expires_dt else None,
            "subscription_platform": "apple",
            "subscription_product_id": verified_product_id,
            "subscription_original_transaction_id": verified_original_tx_id or verified_tx_id,
            "updated_at": now_iso,
        }},
    )
    return AppleVerifyResponse(
        success=True,
        isConsumable=False,
        creditsGranted=result.get("amount", 0),
        subscriptionActive=subscription_active,
        tier=tier,
        expiresAt=expires_dt.isoformat() if expires_dt else None,
        totalCredits=int(result.get("new_balance", 0)),
        transactionId=verified_tx_id,
        alreadyProcessed=already_processed,
    )


# ── POST /api/iap/apple/webhook ──────────────────────────────────────────────

# Notification types we act on. Anything else is logged and acked with 200
# so Apple stops retrying (a persistent non-200 causes App Store to keep
# retrying for 3 days, drowning the logs).
_ENTITLEMENT_GRANT_TYPES = {"SUBSCRIBED", "DID_RENEW", "DID_CHANGE_RENEWAL_STATUS"}
_ENTITLEMENT_REVOKE_TYPES = {"EXPIRED", "REFUND", "REVOKE", "GRACE_PERIOD_EXPIRED"}


@router.post("/webhook")
async def apple_iap_webhook(request: Request):
    """App Store Server Notifications V2 handler.

    Apple retries non-200 responses for up to 3 days. We therefore ONLY
    return non-200 for genuinely un-recoverable issues (bad JWS, missing
    signedPayload). Everything else — including unknown notification
    types — is logged and 200'd.
    """
    body = await request.json()
    signed_payload = body.get("signedPayload") if isinstance(body, dict) else None
    if not signed_payload:
        raise HTTPException(status_code=400, detail="Missing signedPayload")

    try:
        service = get_apple_iap_service()
    except AppleIAPNotConfigured as exc:
        # We DO want Apple to retry when we're mid-deploy without creds.
        logger.warning(f"Apple IAP webhook received before configuration: {exc}")
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        notification = service.verify_notification(signed_payload)
    except AppleIAPVerificationError as exc:
        logger.warning(f"Apple IAP webhook signature verification failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    notification_type = getattr(notification, "notification_type", None)
    notification_type_str = (
        notification_type.value if hasattr(notification_type, "value") else str(notification_type or "")
    )
    subtype = getattr(notification, "subtype", None)
    subtype_str = subtype.value if hasattr(subtype, "value") else (str(subtype) if subtype else None)

    data = getattr(notification, "data", None)
    signed_tx_info = getattr(data, "signed_transaction_info", None) if data else None

    tx = None
    if signed_tx_info:
        try:
            tx = service.verify_transaction(signed_tx_info)
        except AppleIAPVerificationError as exc:
            logger.warning(f"Apple IAP webhook nested tx verification failed: {exc}")

    processed = False
    if tx:
        processed = await _apply_webhook_transaction(
            notification_type=notification_type_str,
            subtype=subtype_str,
            tx=tx,
        )

    logger.info(
        "Apple IAP webhook processed type=%s subtype=%s applied=%s tx_present=%s",
        notification_type_str, subtype_str, processed, tx is not None,
    )

    # Always 200 so Apple stops retrying. Failure details are in logs.
    return {
        "status": "ok",
        "notificationType": notification_type_str,
        "subtype": subtype_str,
        "processed": processed,
    }


async def _apply_webhook_transaction(*, notification_type: str, subtype: Optional[str], tx) -> bool:
    """Apply an entitlement change from an App Store Server Notification.

    Returns True when the transaction produced a state change (grant or
    revocation), False when it was ignored (unknown type / user unknown
    / duplicate).
    """
    verified_product_id = getattr(tx, "product_id", None) or ""
    verified_tx_id = str(getattr(tx, "transaction_id", "") or "")
    verified_original_tx_id = str(getattr(tx, "original_transaction_id", "") or "")
    expires_dt = _decode_dt(getattr(tx, "expires_date", None))
    purchase_dt = _decode_dt(getattr(tx, "purchase_date", None))
    now_iso = datetime.now(timezone.utc).isoformat()

    # Locate the user by originalTransactionId (subs) or transactionId (consumables).
    user = None
    for probe_id in (verified_original_tx_id, verified_tx_id):
        if not probe_id:
            continue
        prior = await db.iap_transactions.find_one(
            {"originalTransactionId": probe_id},
            {"_id": 0, "userId": 1},
        )
        if prior:
            user = await db.users.find_one({"id": prior["userId"]}, {"_id": 0})
            if user:
                break

    if not user:
        # Apple can send webhooks for transactions we haven't seen via
        # /verify yet (rare race). Log and ack so Apple stops retrying.
        logger.warning(
            f"Apple webhook for unknown user — type={notification_type} "
            f"tx={verified_tx_id} original={verified_original_tx_id}"
        )
        return False

    # Idempotent audit record — one row per (transactionId, notificationType).
    # `find_one` FIRST so we know whether this is a duplicate delivery
    # BEFORE we touch credits. Apple retries webhook deliveries aggressively
    # (up to 3 days) and re-delivers the same payload on any transient
    # network hiccup — without this guard a REFUND would deduct twice.
    duplicate_delivery = await db.iap_transactions.find_one(
        {"transactionId": verified_tx_id, "notificationType": notification_type},
        {"_id": 0, "userId": 1},
    ) is not None

    await db.iap_transactions.update_one(
        {"transactionId": verified_tx_id, "notificationType": notification_type},
        {"$setOnInsert": {
            "userId": user["id"],
            "productId": verified_product_id,
            "transactionId": verified_tx_id,
            "originalTransactionId": verified_original_tx_id or verified_tx_id,
            "purchaseDate": purchase_dt.isoformat() if purchase_dt else None,
            "expiresDate": expires_dt.isoformat() if expires_dt else None,
            "notificationType": notification_type,
            "subtype": subtype,
            "source": "webhook",
            "createdAt": now_iso,
        }},
        upsert=True,
    )

    subscription_config = SUBSCRIPTION_MAP.get(verified_product_id)
    consumable_credits = CONSUMABLE_CREDIT_MAP.get(verified_product_id)

    # If we've already applied this (transactionId, notificationType) pair,
    # short-circuit — no double-grant, no double-deduct on retries.
    if duplicate_delivery:
        return False

    # Grant path — subscription renewals grant a fresh period allowance
    # keyed off the NEW transactionId (Apple mints a fresh tx per renewal).
    if notification_type in _ENTITLEMENT_GRANT_TYPES and subscription_config:
        credits_service = get_credits_service(db)
        await credits_service.award_credits(
            user_id=user["id"],
            amount=int(subscription_config["credits"]),
            reason=f"Apple IAP {notification_type} {subscription_config['tier']}",
            reference_id=f"apple_iap:{verified_tx_id}",
        )
        subscription_active = bool(expires_dt and expires_dt > datetime.now(timezone.utc))
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {
                "plan_type": subscription_config["tier"],
                "subscription_status": "active" if subscription_active else "expired",
                "subscription_expires_at": expires_dt.isoformat() if expires_dt else None,
                "subscription_platform": "apple",
                "subscription_product_id": verified_product_id,
                "subscription_original_transaction_id": verified_original_tx_id or verified_tx_id,
                "updated_at": now_iso,
            }},
        )
        return True

    # Revoke path — expiry / refund / grace-period lapse.
    if notification_type in _ENTITLEMENT_REVOKE_TYPES:
        set_fields: dict = {
            "subscription_status": "expired",
            "updated_at": now_iso,
        }
        if notification_type == "REFUND":
            set_fields["subscription_status"] = "refunded"
            # Deduct the credits we granted for THIS transactionId
            # (refund parity with the original grant). Use refund_credits
            # so the ledger records a matching row.
            grant_amount = 0
            if subscription_config:
                grant_amount = int(subscription_config["credits"])
            elif consumable_credits:
                grant_amount = int(consumable_credits)
            if grant_amount > 0:
                credits_service = get_credits_service(db)
                try:
                    await credits_service.deduct_credits(
                        user_id=user["id"],
                        amount=grant_amount,
                        reason=f"Apple IAP REFUND ({verified_product_id})",
                        reference_id=f"apple_iap_refund:{verified_tx_id}",
                    )
                except Exception as exc:
                    # If the balance is below the refund amount we do
                    # NOT drive it negative; just log and continue.
                    logger.warning(
                        f"Apple IAP refund could not fully deduct "
                        f"user={user['id']} amount={grant_amount}: {exc}"
                    )
        await db.users.update_one({"id": user["id"]}, {"$set": set_fields})
        return True

    return False
