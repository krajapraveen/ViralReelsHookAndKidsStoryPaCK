"""
Entitlement Resolver — Single source of truth for user access rights.
Computes can_download, can_preview, watermark_required etc. from user subscription state.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_entitlements(user: dict) -> dict:
    """
    Compute user entitlements from subscription state.
    
    Business rules:
    - Free users: preview only, watermark required, no download
    - Active paid subscribers: preview + download
    - Active paid + top-ups: preview + download, extra credits
    - Top-up alone WITHOUT active subscription does NOT unlock download
    """
    plan_type = user.get("plan_type", "free")
    sub_status = user.get("subscription_status", "inactive")
    expires_at = user.get("subscription_expires_at")
    role = (user.get("role") or "").upper()

    # Admin override — full access
    if role in ("ADMIN", "SUPERADMIN"):
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

    # Check if subscription is currently active
    subscription_active = False
    if sub_status == "active" and plan_type in ("starter", "pro", "premium"):
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
    can_download = subscription_active and plan_type in ("starter", "pro", "premium")

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
