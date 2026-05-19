"""
Conversion-state endpoints — P0 2026-05-22 Phase A.

This module exposes the three frontend-readable endpoints that
together make Google Ads conversion firing webhook-confirmed:

  • GET /api/users/me/activation
      → server-authoritative first_project_completed_at + fire_now
        boolean (transitions True exactly once per user).

  • GET /api/cashfree/conversion-status?order_id=...
      → reflects the Cashfree webhook truth so the frontend can ONLY
        fire the purchase conversion AFTER the webhook has confirmed
        the order. Replaces the legacy frontend-optimistic fire.

  • POST /api/cashfree/conversion-acknowledged
      → flips `conversion_fired=true` on the order. Idempotent.
        Together with the GET predicate above, this guarantees the
        purchase conversion fires at most once across refresh,
        multi-tab, redirect replay, and webhook replay.

Doctrine refs:
  • rule 3 (canonicalize critical state) — order.webhook_confirmed
    and order.conversion_fired are the canonical conversion truth.
  • rule 4 (async jobs idempotent) — POST endpoint compare-and-sets.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from shared import db, logger, get_current_user
from services.activation_truth import get_activation_state

router = APIRouter(tags=["conversions"])


# ─── Activation truth (first_project_created) ──────────────────────


@router.get("/users/me/activation")
async def get_my_activation(user: dict = Depends(get_current_user)):
    """Returns the server-authoritative activation state for the
    current user.

    fire_now=True flips on exactly one request — the one that crosses
    the boundary from "no project ever" to "first project completed".
    Frontend uses this to fire the Google Ads first-project conversion
    exactly once across all tabs, refreshes, and pipeline retries.
    """
    state = await get_activation_state(user["id"])
    return {
        "user_id": user["id"],
        **state,
    }


# ─── Cashfree purchase conversion handshake ────────────────────────


@router.get("/cashfree/conversion-status")
async def get_cashfree_conversion_status(
    order_id: str = Query(..., min_length=4, max_length=128),
    user: dict = Depends(get_current_user),
):
    """Returns the webhook-confirmed conversion state for an order.

    Frontend polls this after the user returns from Cashfree's hosted
    page. The purchase conversion may ONLY fire when
    webhook_confirmed=true AND conversion_fired=false.
    """
    order = await db.orders.find_one(
        {"order_id": order_id, "userId": user["id"]},
        {"_id": 0},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order_id,
        "status": order.get("status"),
        # webhook_confirmed is the canonical webhook truth flag.
        # The cashfree webhook handler sets this to True alongside
        # marking the order PAID / CREDIT_APPLIED / SUBSCRIPTION_ACTIVATED.
        "webhook_confirmed": bool(order.get("webhook_confirmed", False)),
        # conversion_fired flips True after the frontend acknowledges.
        # Idempotent across refresh, multi-tab, and redirect replay.
        "conversion_fired": bool(order.get("conversion_fired", False)),
        "value": order.get("amount") or 0,
        "currency": order.get("currency") or "INR",
        "source_platform": order.get("source_platform") or "direct",
        "product_id": order.get("productId"),
    }


class ConversionAckPayload(BaseModel):
    order_id: str = Field(..., min_length=4, max_length=128)


@router.post("/cashfree/conversion-acknowledged")
async def acknowledge_cashfree_conversion(
    payload: ConversionAckPayload,
    user: dict = Depends(get_current_user),
):
    """Persist that the frontend successfully fired the Google Ads
    purchase conversion for this order. Idempotent — only the first
    call flips the flag; subsequent calls return first_ack=False.

    The compound predicate ensures we never flip the flag on an
    order that the webhook has not yet confirmed.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    result = await db.orders.update_one(
        {
            "order_id": payload.order_id,
            "userId": user["id"],
            "webhook_confirmed": True,
            "conversion_fired": {"$ne": True},
        },
        {"$set": {"conversion_fired": True, "conversion_fired_at": now_iso}},
    )
    first_ack = result.modified_count == 1
    if first_ack:
        logger.info(
            "[CONVERSIONS] purchase_conversion_acknowledged order=%s user=%s",
            payload.order_id, user["id"],
        )
    return {"order_id": payload.order_id, "first_ack": first_ack}
