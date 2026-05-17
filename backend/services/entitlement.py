"""
Entitlement Resolver — Single source of truth for user access rights.
Computes can_download, can_preview, watermark_required etc. from user subscription state.

Also exposes 4 universal helpers (2026-05) used at the TOP of any
route that gates on credits / plan / admin status:

    is_unlimited_user(user)   — admin / owner / dev / qa / test / is_unlimited flag
    has_paid_access(user)     — credits > 0 OR paid plan (top-up or subscriber)
    has_premium_access(user)  — paid plan only (creator / pro / studio / starter / premium)
    require_credits(user, cost) — raises HTTPException(402) with exact message
                                  if insufficient; no-op if unlimited.

Rule of thumb: NEVER write `user.get('credits',0) < cost` inline in a
route again. Use require_credits().
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ─── 2026-05 Universal entitlement primitives ─────────────────────────────
_UNLIMITED_ROLES = {"admin", "owner", "dev", "qa", "test"}
_PREMIUM_PLANS = {"creator", "pro", "studio", "starter", "premium"}


def is_unlimited_user(user: Optional[dict]) -> bool:
    """True if the user bypasses ALL quota / credit gates.

    Triggered by:
      * `is_unlimited=True` flag on the user document
      * role in {admin, owner, dev, qa, test} (case-insensitive)
    """
    if not user:
        return False
    if user.get("is_unlimited", False):
        return True
    role = (user.get("role") or "").lower()
    return role in _UNLIMITED_ROLES


def has_paid_access(user: Optional[dict]) -> bool:
    """True if the user has any paid entitlement: unlimited, credits>0,
    or non-free plan. Use for "can use platform at all" gating."""
    if not user:
        return False
    if is_unlimited_user(user):
        return True
    if int(user.get("credits", 0) or 0) > 0:
        return True
    plan = (user.get("plan") or user.get("plan_type") or "free").lower()
    return plan not in ("free", "", "none")


def has_premium_access(user: Optional[dict]) -> bool:
    """True if the user is on a premium subscription tier.
    Used for premium-only extras (HD/PDF/premium styles) — credits alone NOT sufficient."""
    if not user:
        return False
    if is_unlimited_user(user):
        return True
    plan = (user.get("plan") or user.get("plan_type") or "free").lower()
    return plan in _PREMIUM_PLANS


def has_active_subscription(user: Optional[dict]) -> bool:
    """True if the user has an active paid subscription doc (live billing).
    Used by content gates that require *recurring* billing — e.g. Bedtime
    Stories full payload, premium-only deliverables.

    Triggered by `user.subscription.status == 'active'` and (if present)
    `user.subscription.endDate` is in the future.
    """
    if not user:
        return False
    sub = user.get("subscription")
    if not isinstance(sub, dict):
        return False
    if (sub.get("status") or "").lower() != "active":
        return False
    end = sub.get("endDate") or sub.get("end_date") or sub.get("expires_at")
    if not end:
        return True
    try:
        if isinstance(end, str):
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        else:
            end_dt = end
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        return end_dt > datetime.now(timezone.utc)
    except Exception:
        return True


def has_full_content_access(user: Optional[dict]) -> bool:
    """Combined gate for full long-form content payloads (Bedtime Stories,
    Story Series episodes, Comic exports). Returns True for:
      * unlimited users (admin / owner / dev / qa / test / is_unlimited)
      * premium subscription tier (creator / pro / studio / starter / premium)
      * active recurring subscription document (any plan)
    Returns False for free / preview / expired users.
    """
    if not user:
        return False
    return (
        is_unlimited_user(user)
        or has_premium_access(user)
        or has_active_subscription(user)
    )


def require_credits(user: Optional[dict], cost: int, *, feature: str = "this feature") -> None:
    """Canonical credit gate. Raises HTTPException(402) if insufficient.
    No-op for unlimited users.

        from services.entitlement import require_credits
        require_credits(user, cost=cost, feature="comic strip")

    Atomic deduction in credits_service still enforces the no-negative
    invariant at DB level — this is the pre-flight UX layer.
    """
    if is_unlimited_user(user):
        return
    available = int((user or {}).get("credits", 0) or 0)
    if available < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {cost}, Available: {available}.",
        )


def entitlement_snapshot(user: Optional[dict]) -> dict:
    """Single payload describing a user's entitlements (for /me endpoints)."""
    return {
        "is_unlimited": is_unlimited_user(user),
        "has_paid_access": has_paid_access(user),
        "has_premium_access": has_premium_access(user),
        "credits": int((user or {}).get("credits", 0) or 0),
        "plan": (user or {}).get("plan", "free"),
        "role": (user or {}).get("role", "user"),
    }


# ─── Pre-existing download/watermark resolver (unchanged) ────────────────


def resolve_entitlements(user: dict) -> dict:
    """
    Compute user entitlements from subscription state.

    Business rules:
    - Free users: preview only, watermark required, no download
    - Active paid subscribers (starter / creator / pro / studio / premium): preview + download
    - Active paid + top-ups: preview + download, extra credits
    - Top-up alone WITHOUT active subscription does NOT unlock generic Story Engine download
      (per-job credit-paid deliverables like Comic Story Book have their OWN ownership
       gate; this resolver covers the generic Story Engine media entitlement)
    - Unlimited users (admin / owner / dev / qa / test / is_unlimited flag): full access
    """
    plan_type = user.get("plan_type") or user.get("plan") or "free"
    sub_status = user.get("subscription_status", "inactive")
    expires_at = user.get("subscription_expires_at")

    # P0 2026-05-19 — Unlimited bypass (admin / owner / dev / qa / test /
    # is_unlimited flag). Previously this resolver only honored role ==
    # ADMIN / SUPERADMIN and disagreed with `is_unlimited_user()` —
    # producing the production "Upgrade to Download" trap for admin/QA
    # users on their own completed deliverables.
    if is_unlimited_user(user):
        return {
            "can_preview": True,
            "can_download": True,
            "can_generate": True,
            "watermark_required": False,
            "preview_only": False,
            "upgrade_required": False,
            "plan_type": plan_type,
            "subscription_active": True,
        }

    # P0 2026-05-19 — Eligible paid plans now aligned with the canonical
    # `_PREMIUM_PLANS` set so creator / studio users (who DO pay
    # recurring) aren't blocked from downloading their own assets.
    eligible_plans = _PREMIUM_PLANS  # {"creator", "pro", "studio", "starter", "premium"}

    # Check if subscription is currently active
    subscription_active = False
    if sub_status == "active" and plan_type in eligible_plans:
        # Check expiry
        if expires_at:
            try:
                if isinstance(expires_at, str):
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                else:
                    exp_dt = expires_at
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                subscription_active = exp_dt > datetime.now(timezone.utc)
            except (ValueError, TypeError):
                subscription_active = False
        else:
            # No expiry set — treat as active if status says active
            subscription_active = True
    elif sub_status == "trial":
        subscription_active = True

    # Compute entitlements
    can_download = subscription_active and plan_type in eligible_plans

    return {
        "can_preview": True,
        "can_download": can_download,
        "can_generate": True,  # Credits handle generation limits
        "watermark_required": not can_download,
        "preview_only": not can_download,
        "upgrade_required": not can_download,
        "plan_type": plan_type,
        "subscription_active": subscription_active,
    }


def can_download_asset(user: dict) -> bool:
    """Quick check: can this user download assets?"""
    return resolve_entitlements(user)["can_download"]


def get_media_access(user: dict, asset_owner_id: Optional[str] = None) -> dict:
    """
    Get media access flags for API responses.
    Frontend must render from these flags only.
    """
    ent = resolve_entitlements(user)
    user_id = user.get("id", "")

    # Build fingerprint for watermark
    fingerprint = user_id[:8].upper() if user_id else "ANON"

    return {
        "can_preview": ent["can_preview"],
        "can_download": ent["can_download"],
        "watermark_required": ent["watermark_required"],
        "preview_only": ent["preview_only"],
        "upgrade_required": ent["upgrade_required"],
        "plan_type": ent["plan_type"],
        "watermark_text": f"Visionary Suite \u2022 Free Preview \u2022 U:{fingerprint}" if ent["watermark_required"] else None,
    }
