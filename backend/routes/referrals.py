"""
Visionary Suite — Referral Bonus Program
Invite & Earn 300 Credits. Qualified-only (signup + first creation).

Flow:
  1. POST /api/referrals/click       (public, cookie-free, records click)
  2. POST /api/auth/register         (attach referral_code → SIGNED_UP attribution)
  3. POST /api/referrals/qualify     (user or cron, checks first creation → grants)
  4. GET  /api/referrals/me          (user dashboard)
  5. Admin surface: list/stats/actions
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import hashlib
import logging
import os
import re
import uuid

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger("referrals")
router = APIRouter(prefix="/referrals", tags=["referrals"])

# ─── Constants ──────────────────────────────────────────────────────────
# Tier-based reward economy (monetization hardening, April 2026)
REWARD_TIERS = {
    "FREE":    {"credits": 150, "cap": 2,  "max_monthly": 300,  "purchase_bonus": 200},
    "PAID":    {"credits": 300, "cap": 5,  "max_monthly": 1500, "purchase_bonus": 500},
    "PREMIUM": {"credits": 500, "cap": 10, "max_monthly": 5000, "purchase_bonus": 700},
}
REWARD_CREDITS = 150  # Legacy default (minimum — free tier)

REFERRAL_EXPIRY_DAYS = 45        # referral reward credits expire
PURCHASE_BONUS_EXPIRY_DAYS = 60  # purchase-bonus credits expire
ATTRIBUTION_WINDOW_DAYS = 30
PURCHASE_BONUS_WINDOW_DAYS = 30  # referred user must purchase within 30d to trigger bonus

STATUS_VALUES = [
    "CLICKED", "SIGNED_UP", "VERIFIED", "ACTIVATED",
    "QUALIFIED", "REJECTED", "REWARDED",
]

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "tempmail.com",
    "guerrillamail.com", "trashmail.com", "throwaway.email",
    "yopmail.com", "discard.email",
}


# ─── Models ─────────────────────────────────────────────────────────────
class ClickIn(BaseModel):
    code: str = Field(..., min_length=3, max_length=40)
    fingerprint: Optional[str] = None
    path: Optional[str] = None


class QualifyIn(BaseModel):
    # User can self-trigger; admin can force for a user_id
    user_id: Optional[str] = None


class AdminReviewIn(BaseModel):
    attribution_id: str
    action: str  # "APPROVE" | "REJECT" | "REVERSE"
    reason: Optional[str] = ""


# ─── Helpers ────────────────────────────────────────────────────────────
def _hash(s: str) -> str:
    salt = os.environ.get("REF_SALT", "vs-ref-default-salt")
    return hashlib.sha256(f"{salt}:{s or ''}".encode()).hexdigest()[:32]


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _slug_from_email_name(email: str, name: str) -> str:
    base = (name or email.split("@")[0]).strip().lower()
    base = re.sub(r"[^a-z0-9]+", "", base)[:14]
    if not base:
        base = "user"
    # Append 4-char suffix for uniqueness
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{base}{suffix}"


async def _ensure_profile(user: dict) -> dict:
    """Return (or create) a referral profile for this user."""
    user_id = user.get("id")
    profile = await db.referral_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if profile:
        return profile
    code = _slug_from_email_name(user.get("email", ""), user.get("name", ""))
    # Guarantee uniqueness
    while await db.referral_profiles.find_one({"referral_code": code}, {"_id": 0}):
        code = _slug_from_email_name(user.get("email", ""), user.get("name", ""))
    profile = {
        "user_id": user_id,
        "email": (user.get("email") or "").lower(),
        "referral_code": code,
        "total_invites": 0,
        "total_clicks": 0,
        "valid_referrals": 0,
        "pending_referrals": 0,
        "rejected_referrals": 0,
        "total_credits_earned": 0,
        "streak_bonus_granted": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.referral_profiles.insert_one({**profile})
    return profile


async def _find_profile_by_code(code: str) -> Optional[dict]:
    if not code:
        return None
    return await db.referral_profiles.find_one(
        {"referral_code": re.compile(f"^{re.escape(code)}$", re.IGNORECASE)},
        {"_id": 0},
    )


def _is_abusive_email(email: str) -> bool:
    domain = (email or "").split("@")[-1].lower()
    return domain in DISPOSABLE_DOMAINS


# ─── Tier & Cap Helpers ────────────────────────────────────────────────
PREMIUM_PLAN_VALUES = {"premium", "annual", "yearly", "yearly-premium", "annual-premium"}
PAID_PLAN_VALUES = {"paid", "weekly", "monthly", "quarterly", "basic", "pro", "starter", "standard"}


def _resolve_tier(user: dict) -> str:
    """Map a user's plan → reward tier."""
    if not user:
        return "FREE"
    plan = (user.get("plan_type") or "free").strip().lower()
    sub_status = (user.get("subscription_status") or "").strip().lower()
    # Only honor paid tier when subscription_status is active
    if sub_status not in ["active", "trialing"] and plan not in PREMIUM_PLAN_VALUES:
        # Exception: some users have plan_type set without sub_status → treat as FREE
        if plan == "free" or not plan:
            return "FREE"
    if plan in PREMIUM_PLAN_VALUES:
        return "PREMIUM"
    if plan in PAID_PLAN_VALUES and sub_status in ["active", "trialing"]:
        return "PAID"
    return "FREE"


def _current_month_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


async def _ensure_monthly_reset(profile: dict) -> dict:
    """Reset monthly counters if we crossed a month boundary."""
    current = _current_month_key()
    if profile.get("last_reset_month") != current:
        await db.referral_profiles.update_one(
            {"user_id": profile["user_id"]},
            {"$set": {
                "monthly_reward_count": 0,
                "monthly_reward_credits": 0,
                "last_reset_month": current,
            }}
        )
        profile["monthly_reward_count"] = 0
        profile["monthly_reward_credits"] = 0
        profile["last_reset_month"] = current
    return profile


async def _compute_cap_state(user_id: str) -> dict:
    """Return {tier, credits_per_ref, cap, monthly_used, monthly_credits, remaining, upsell}"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "plan_type": 1, "subscription_status": 1})
    tier = _resolve_tier(user or {})
    config = REWARD_TIERS[tier]
    profile = await db.referral_profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}
    if profile:
        profile = await _ensure_monthly_reset(profile)
    used = int(profile.get("monthly_reward_count") or 0)
    earned = int(profile.get("monthly_reward_credits") or 0)
    remaining = max(0, config["cap"] - used)
    return {
        "tier": tier,
        "credits_per_ref": config["credits"],
        "cap": config["cap"],
        "monthly_used": used,
        "monthly_credits": earned,
        "max_monthly_credits": config["max_monthly"],
        "remaining": remaining,
        "purchase_bonus": config["purchase_bonus"],
        "cap_reached": remaining == 0,
    }


# ─── Signup hook (called from auth.py register) ─────────────────────────
async def attach_referral_on_signup(
    new_user_id: str, new_email: str, referral_code: Optional[str],
    ip_address: Optional[str] = None, fingerprint: Optional[str] = None,
) -> Optional[str]:
    """Called from /api/auth/register after user created. Non-blocking."""
    if not referral_code:
        return None
    code = referral_code.strip()
    profile = await _find_profile_by_code(code)
    if not profile:
        logger.info(f"[REF] Unknown code '{code}' for new user {new_user_id[:8]}")
        return None

    referrer_id = profile["user_id"]

    # ── Fraud checks ──
    reject_reason = None

    if referrer_id == new_user_id:
        reject_reason = "SELF_REFERRAL"
    elif _is_abusive_email(new_email):
        reject_reason = "DISPOSABLE_EMAIL"
    else:
        # Check if same IP or fingerprint used by referrer
        referrer_user = await db.users.find_one(
            {"id": referrer_id},
            {"_id": 0, "email": 1, "ip_address": 1}
        )
        if referrer_user:
            if ip_address and referrer_user.get("ip_address") == ip_address:
                reject_reason = "SAME_IP"
            # Same device fingerprint (fingerprint hash)
            if not reject_reason and fingerprint:
                fp_hash = _hash(fingerprint)
                existing_same_fp = await db.referral_attributions.find_one({
                    "fingerprint_hash": fp_hash,
                    "referrer_user_id": referrer_id,
                })
                if existing_same_fp:
                    reject_reason = "SAME_DEVICE"

    # Already exists? (rare — duplicate signup attempt)
    existing = await db.referral_attributions.find_one(
        {"referred_user_id": new_user_id}, {"_id": 0}
    )
    if existing:
        return existing.get("id")

    now = datetime.now(timezone.utc).isoformat()
    attr_id = str(uuid.uuid4())
    attr = {
        "id": attr_id,
        "referrer_user_id": referrer_id,
        "referrer_code": profile["referral_code"],
        "referred_user_id": new_user_id,
        "referred_email": (new_email or "").lower(),
        "status": "REJECTED" if reject_reason else "SIGNED_UP",
        "reason": reject_reason,
        "ip_hash": _hash(ip_address or ""),
        "fingerprint_hash": _hash(fingerprint or ""),
        "created_at": now,
        "updated_at": now,
        "qualified_at": None,
        "rewarded_at": None,
    }
    await db.referral_attributions.insert_one({**attr})

    # Update counters
    if reject_reason:
        await db.referral_profiles.update_one(
            {"user_id": referrer_id},
            {"$inc": {"total_invites": 1, "rejected_referrals": 1}}
        )
        logger.info(f"[REF] Signup attribution REJECTED ({reject_reason}) for {profile['referral_code']}")
    else:
        await db.referral_profiles.update_one(
            {"user_id": referrer_id},
            {"$inc": {"total_invites": 1, "pending_referrals": 1}}
        )
        logger.info(f"[REF] Signup attributed to {profile['referral_code']} → {new_user_id[:8]}")

    return attr_id


async def _grant_reward(referrer_id: str, referred_user_id: str, attribution_id: str) -> dict:
    """Idempotent — returns dict {granted, credits, reason, tier}."""
    # Prevent duplicate reward
    existing = await db.referral_rewards.find_one(
        {"attribution_id": attribution_id}, {"_id": 0}
    )
    if existing:
        return {"granted": False, "reason": "ALREADY_GRANTED", "credits": 0}

    # Tier + cap check
    cap_state = await _compute_cap_state(referrer_id)
    if cap_state["cap_reached"]:
        # Block reward, mark attribution as cap-blocked (keep pending for visibility)
        await db.referral_profiles.update_one(
            {"user_id": referrer_id},
            {"$inc": {"monthly_cap_hits": 1}}
        )
        logger.info(f"[REF] Cap reached for {referrer_id[:8]} tier={cap_state['tier']}")
        return {"granted": False, "reason": "CAP_REACHED", "credits": 0, "tier": cap_state["tier"]}

    credits = cap_state["credits_per_ref"]
    tier = cap_state["tier"]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_at = (now + timedelta(days=REFERRAL_EXPIRY_DAYS)).isoformat()

    reward_id = str(uuid.uuid4())
    await db.referral_rewards.insert_one({
        "id": reward_id,
        "attribution_id": attribution_id,
        "referrer_user_id": referrer_id,
        "referred_user_id": referred_user_id,
        "credits": credits,
        "tier": tier,
        "status": "GRANTED",
        "granted_at": now_iso,
        "expires_at": expires_at,
    })
    # Add credits to referrer
    await db.users.update_one({"id": referrer_id}, {"$inc": {"credits": credits}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": referrer_id,
        "amount": credits,
        "type": "REFERRAL_REWARD",
        "source_type": "REFERRAL_REWARD",
        "source_user_id": referred_user_id,
        "referral_id": attribution_id,
        "reward_id": reward_id,
        "expires_at": expires_at,
        "description": f"Referral reward ({tier}) — new creator joined and started creating",
        "createdAt": now_iso,
    })
    # Update profile counters (lifetime + monthly)
    await _ensure_profile_by_id(referrer_id)
    await db.referral_profiles.update_one(
        {"user_id": referrer_id},
        {
            "$inc": {
                "valid_referrals": 1,
                "pending_referrals": -1,
                "total_credits_earned": credits,
                "lifetime_referrals": 1,
                "monthly_reward_count": 1,
                "monthly_reward_credits": credits,
            },
            "$set": {"current_reward_tier": tier, "last_reset_month": _current_month_key()}
        }
    )
    # Streak bonus — every 3 valid referrals, +500 (same tier as reward)
    profile = await db.referral_profiles.find_one({"user_id": referrer_id}, {"_id": 0})
    if profile:
        valid = profile.get("valid_referrals", 0)
        streak_already = profile.get("streak_bonus_granted", 0)
        expected_streaks = valid // 3
        if expected_streaks > streak_already:
            bonus = (expected_streaks - streak_already) * 500
            await db.users.update_one({"id": referrer_id}, {"$inc": {"credits": bonus}})
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": referrer_id,
                "amount": bonus,
                "type": "REFERRAL_STREAK_BONUS",
                "source_type": "REFERRAL_STREAK",
                "expires_at": expires_at,
                "description": f"Streak bonus — {expected_streaks * 3} valid referrals",
                "createdAt": now_iso,
            })
            await db.referral_profiles.update_one(
                {"user_id": referrer_id},
                {"$inc": {"total_credits_earned": bonus}, "$set": {"streak_bonus_granted": expected_streaks}}
            )
    logger.info(f"[REF] +{credits} ({tier}) granted to {referrer_id[:8]} (attrib {attribution_id[:8]})")
    return {"granted": True, "credits": credits, "tier": tier}


async def _ensure_profile_by_id(user_id: str):
    """Ensure a profile doc exists for this user_id (no-op if exists)."""
    existing = await db.referral_profiles.find_one({"user_id": user_id}, {"_id": 0, "user_id": 1})
    if existing:
        return
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
    if not user:
        return
    await _ensure_profile({"id": user_id, "email": user.get("email"), "name": user.get("name")})


async def _has_first_creation(user_id: str) -> bool:
    """Check if user has at least one completed project/job."""
    # Check pipeline_jobs table (main generation path)
    job = await db.pipeline_jobs.find_one(
        {"user_id": user_id, "status": {"$in": ["COMPLETED", "PARTIAL_COMPLETE"]}},
        {"_id": 0, "id": 1},
    )
    if job:
        return True
    # Fallback — check stories / scenes / any completed asset
    story = await db.stories.find_one(
        {"user_id": user_id, "state": {"$in": ["READY", "COMPLETED", "PARTIAL_READY"]}},
        {"_id": 0, "id": 1},
    )
    return bool(story)


async def grant_referral_purchase_bonus(user_id: str, payment_amount: float = 0.0) -> dict:
    """
    Called from payment success webhook when a referred user purchases.
    Grants a one-time bonus to the original referrer based on their tier.
    Idempotent per-attribution.
    """
    # Find attribution where this user was the referred party, and status already REWARDED
    attr = await db.referral_attributions.find_one(
        {"referred_user_id": user_id, "status": {"$in": ["REWARDED", "QUALIFIED"]}},
        {"_id": 0}
    )
    if not attr:
        return {"granted": False, "reason": "NOT_REFERRED"}

    # Must be within purchase-bonus window
    try:
        created = datetime.fromisoformat(attr["created_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - created).days > PURCHASE_BONUS_WINDOW_DAYS:
            return {"granted": False, "reason": "WINDOW_EXPIRED"}
    except Exception:
        pass

    # Idempotency — check if bonus already granted for this attribution
    already = await db.referral_rewards.find_one({
        "attribution_id": attr["id"],
        "type": "PURCHASE_BONUS",
    }, {"_id": 0})
    if already:
        return {"granted": False, "reason": "ALREADY_GRANTED"}

    referrer_id = attr["referrer_user_id"]
    cap_state = await _compute_cap_state(referrer_id)
    bonus_amount = cap_state["purchase_bonus"]
    tier = cap_state["tier"]

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_at = (now + timedelta(days=PURCHASE_BONUS_EXPIRY_DAYS)).isoformat()

    reward_id = str(uuid.uuid4())
    await db.referral_rewards.insert_one({
        "id": reward_id,
        "attribution_id": attr["id"],
        "type": "PURCHASE_BONUS",
        "referrer_user_id": referrer_id,
        "referred_user_id": user_id,
        "credits": bonus_amount,
        "tier": tier,
        "status": "GRANTED",
        "granted_at": now_iso,
        "expires_at": expires_at,
        "payment_amount": payment_amount,
    })
    await db.users.update_one({"id": referrer_id}, {"$inc": {"credits": bonus_amount}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": referrer_id,
        "amount": bonus_amount,
        "type": "REFERRAL_PURCHASE_BONUS",
        "source_type": "REFERRAL_PURCHASE_BONUS",
        "source_user_id": user_id,
        "referral_id": attr["id"],
        "reward_id": reward_id,
        "expires_at": expires_at,
        "description": f"Referral purchase bonus ({tier}) — your invite converted to paid",
        "createdAt": now_iso,
    })
    await _ensure_profile_by_id(referrer_id)
    await db.referral_profiles.update_one(
        {"user_id": referrer_id},
        {"$inc": {
            "paid_referral_conversions": 1,
            "total_credits_earned": bonus_amount,
        }}
    )
    logger.info(f"[REF] Purchase bonus +{bonus_amount} ({tier}) for {referrer_id[:8]}")
    return {"granted": True, "credits": bonus_amount, "tier": tier}


async def expire_referral_credits() -> int:
    """Sweep expired REFERRAL_REWARD / REFERRAL_PURCHASE_BONUS credits.

    Looks at ledger entries where source_type is referral-related and expires_at has passed.
    Deducts unexpired-yet-unused credits from user balance (best-effort), marks rewards as EXPIRED.

    Simple model: for each referral_rewards doc in GRANTED status with expires_at < now,
    deduct `credits` from user balance and flip to EXPIRED.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    expired_rewards = await db.referral_rewards.find({
        "status": "GRANTED",
        "expires_at": {"$lt": now_iso},
    }, {"_id": 0}).to_list(10000)

    count = 0
    for r in expired_rewards:
        uid = r.get("referrer_user_id")
        credits = r.get("credits", 0)
        if not uid or credits <= 0:
            continue
        # Deduct but never below 0
        user = await db.users.find_one({"id": uid}, {"_id": 0, "credits": 1})
        if not user:
            continue
        current = int(user.get("credits") or 0)
        deduction = min(current, credits)  # only deduct what's still available
        if deduction > 0:
            await db.users.update_one({"id": uid}, {"$inc": {"credits": -deduction}})
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": uid,
            "amount": -deduction,
            "type": "REFERRAL_EXPIRY",
            "source_type": "REFERRAL_EXPIRY",
            "reward_id": r.get("id"),
            "description": f"Referral credits expired (was {credits})",
            "createdAt": now_iso,
        })
        await db.referral_rewards.update_one(
            {"id": r["id"]},
            {"$set": {"status": "EXPIRED", "expired_at": now_iso, "expired_deducted": deduction}}
        )
        count += 1
    if count:
        logger.info(f"[REF] Expired {count} referral rewards")
    return count


async def referral_expiry_loop():
    """Background loop — runs every 6 hours."""
    import asyncio
    await asyncio.sleep(60)
    logger.info("[REF] Expiry loop started")
    while True:
        try:
            await expire_referral_credits()
        except Exception as e:
            logger.error(f"[REF] Expiry sweep error: {e}")
        await asyncio.sleep(21600)  # 6h


# ─── Public endpoints ───────────────────────────────────────────────────

@router.post("/click")
async def track_click(click: ClickIn, request: Request):
    """Record an invite-link click. No auth required."""
    profile = await _find_profile_by_code(click.code)
    if not profile:
        return {"success": False, "valid": False, "reason": "UNKNOWN_CODE"}

    await db.referral_events.insert_one({
        "id": str(uuid.uuid4()),
        "event_type": "CLICK",
        "referral_code": profile["referral_code"],
        "referrer_user_id": profile["user_id"],
        "ip_hash": _hash(_client_ip(request)),
        "fingerprint_hash": _hash(click.fingerprint or ""),
        "path": click.path,
        "user_agent": (request.headers.get("user-agent", "") or "")[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.referral_profiles.update_one(
        {"user_id": profile["user_id"]},
        {"$inc": {"total_clicks": 1}}
    )
    return {
        "success": True,
        "valid": True,
        "referrer_name": None,  # Don't leak PII
        "referral_code": profile["referral_code"],
    }


@router.get("/lookup/{code}")
async def lookup_code(code: str):
    """Check if a code is valid — used by /refer page."""
    profile = await _find_profile_by_code(code)
    if not profile:
        return {"valid": False}
    # Don't leak user identity — just confirm validity
    return {"valid": True, "code": profile["referral_code"]}


@router.get("/me")
async def get_my_referrals(user: dict = Depends(get_current_user)):
    """Dashboard payload for the signed-in user."""
    profile = await _ensure_profile(user)

    attributions = await db.referral_attributions.find(
        {"referrer_user_id": user.get("id")}, {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)

    # Enrich with friend names (first letter only) for privacy
    enriched = []
    for a in attributions:
        friend = await db.users.find_one(
            {"id": a.get("referred_user_id")},
            {"_id": 0, "name": 1, "email": 1}
        )
        masked = None
        if friend:
            name = friend.get("name") or friend.get("email", "").split("@")[0]
            masked = (name[0].upper() + "***") if name else "F***"
        enriched.append({
            **a,
            "friend_display": masked,
        })

    rewards = await db.referral_rewards.find(
        {"referrer_user_id": user.get("id")}, {"_id": 0}
    ).sort("granted_at", -1).limit(50).to_list(50)

    share_url = f"https://www.visionary-suite.com/refer?code={profile['referral_code']}"
    cap_state = await _compute_cap_state(user.get("id"))
    return {
        "profile": profile,
        "attributions": enriched,
        "rewards": rewards,
        "share_url": share_url,
        "reward_credits": cap_state["credits_per_ref"],
        "cap_state": cap_state,
        "reward_tiers": REWARD_TIERS,
    }


@router.post("/qualify")
async def qualify_referral(body: QualifyIn, user: dict = Depends(get_current_user)):
    """
    Idempotent. Called from dashboard / project completion.
    Checks if current user was referred + has first creation → grants referrer.
    Admin may pass body.user_id to force-check another user.
    """
    target_user_id = body.user_id if (body.user_id and user.get("role") in ["ADMIN", "admin"]) else user.get("id")

    attr = await db.referral_attributions.find_one(
        {"referred_user_id": target_user_id, "status": {"$in": ["SIGNED_UP", "VERIFIED", "ACTIVATED"]}},
        {"_id": 0}
    )
    if not attr:
        return {"qualified": False, "reason": "NO_PENDING_ATTRIBUTION"}

    # Within attribution window?
    try:
        created = datetime.fromisoformat(attr["created_at"].replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - created).days > ATTRIBUTION_WINDOW_DAYS:
            await db.referral_attributions.update_one(
                {"id": attr["id"]},
                {"$set": {"status": "REJECTED", "reason": "WINDOW_EXPIRED",
                          "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"qualified": False, "reason": "WINDOW_EXPIRED"}
    except Exception:
        pass

    if not await _has_first_creation(target_user_id):
        return {"qualified": False, "reason": "NO_FIRST_CREATION"}

    # Promote + grant
    now = datetime.now(timezone.utc).isoformat()
    await db.referral_attributions.update_one(
        {"id": attr["id"]},
        {"$set": {"status": "QUALIFIED", "qualified_at": now, "updated_at": now}}
    )
    result = await _grant_reward(attr["referrer_user_id"], target_user_id, attr["id"])
    if result.get("granted"):
        await db.referral_attributions.update_one(
            {"id": attr["id"]},
            {"$set": {"status": "REWARDED", "rewarded_at": now}}
        )
    return {
        "qualified": True,
        "granted": result.get("granted", False),
        "credits": result.get("credits", 0),
        "tier": result.get("tier"),
        "reason": result.get("reason"),
    }


# ─── Admin endpoints ────────────────────────────────────────────────────

@router.get("/admin/overview")
async def admin_overview(admin: dict = Depends(get_admin_user)):
    total_profiles = await db.referral_profiles.count_documents({})
    total_clicks = await db.referral_events.count_documents({"event_type": "CLICK"})
    total_attributions = await db.referral_attributions.count_documents({})
    qualified = await db.referral_attributions.count_documents({"status": {"$in": ["QUALIFIED", "REWARDED"]}})
    rejected = await db.referral_attributions.count_documents({"status": "REJECTED"})
    pending = await db.referral_attributions.count_documents({"status": {"$in": ["SIGNED_UP", "VERIFIED", "ACTIVATED"]}})

    credits_pipeline = [
        {"$match": {"status": "GRANTED"}},
        {"$group": {"_id": None, "sum": {"$sum": "$credits"}, "count": {"$sum": 1}}},
    ]
    granted = await db.referral_rewards.aggregate(credits_pipeline).to_list(1)
    credits_granted = granted[0]["sum"] if granted else 0
    rewards_count = granted[0]["count"] if granted else 0

    # Top 10 referrers
    top = await db.referral_profiles.find(
        {"valid_referrals": {"$gt": 0}}, {"_id": 0}
    ).sort("valid_referrals", -1).limit(10).to_list(10)

    conv_rate = (qualified / total_attributions * 100) if total_attributions else 0

    # ── Monetization hardening metrics ──
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    credits_month = await db.referral_rewards.aggregate([
        {"$match": {"status": "GRANTED", "granted_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "sum": {"$sum": "$credits"}}}
    ]).to_list(1)
    credits_issued_this_month = credits_month[0]["sum"] if credits_month else 0

    # Purchase bonuses
    purchase_bonuses = await db.referral_rewards.count_documents({"type": "PURCHASE_BONUS", "status": "GRANTED"})
    referred_paid_users = await db.referral_rewards.distinct("referred_user_id", {"type": "PURCHASE_BONUS"})

    # Cap hits by tier
    cap_hits_pipeline = [
        {"$match": {"monthly_cap_hits": {"$gt": 0}}},
        {"$group": {"_id": "$current_reward_tier", "hits": {"$sum": "$monthly_cap_hits"}}},
    ]
    cap_hits = {}
    async for row in db.referral_profiles.aggregate(cap_hits_pipeline):
        cap_hits[row["_id"] or "UNKNOWN"] = row["hits"]

    # Expired credits
    expired_count = await db.referral_rewards.count_documents({"status": "EXPIRED"})
    expired_sum_agg = await db.referral_rewards.aggregate([
        {"$match": {"status": "EXPIRED"}},
        {"$group": {"_id": None, "sum": {"$sum": "$credits"}}}
    ]).to_list(1)
    expired_sum = expired_sum_agg[0]["sum"] if expired_sum_agg else 0

    return {
        "total_profiles": total_profiles,
        "total_clicks": total_clicks,
        "total_attributions": total_attributions,
        "qualified": qualified,
        "pending": pending,
        "rejected": rejected,
        "rewards_granted_count": rewards_count,
        "credits_granted": credits_granted,
        "conversion_rate": round(conv_rate, 2),
        "top_referrers": top,
        # Monetization hardening
        "credits_issued_this_month": credits_issued_this_month,
        "purchase_bonuses_granted": purchase_bonuses,
        "referred_paid_users": len(referred_paid_users),
        "cap_hits_by_tier": cap_hits,
        "expired_rewards_count": expired_count,
        "expired_credits_sum": expired_sum,
        "reward_tiers": REWARD_TIERS,
    }


@router.get("/admin/attributions")
async def admin_attributions(
    admin: dict = Depends(get_admin_user),
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    q = {}
    if status and status in STATUS_VALUES:
        q["status"] = status
    total = await db.referral_attributions.count_documents(q)
    rows = await db.referral_attributions.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    # Enrich with names
    for r in rows:
        referrer = await db.users.find_one({"id": r.get("referrer_user_id")}, {"_id": 0, "email": 1, "name": 1})
        referred = await db.users.find_one({"id": r.get("referred_user_id")}, {"_id": 0, "email": 1, "name": 1})
        r["referrer_email"] = (referrer or {}).get("email")
        r["referred_email_display"] = (referred or {}).get("email")
    return {"success": True, "total": total, "rows": rows}


@router.post("/admin/review")
async def admin_review(body: AdminReviewIn, admin: dict = Depends(get_admin_user)):
    attr = await db.referral_attributions.find_one({"id": body.attribution_id}, {"_id": 0})
    if not attr:
        raise HTTPException(status_code=404, detail="Attribution not found")
    now = datetime.now(timezone.utc).isoformat()
    action = body.action.upper()

    if action == "APPROVE":
        # Force qualify + grant (bypass first-creation check)
        if attr.get("status") in ["REWARDED"]:
            raise HTTPException(status_code=400, detail="Already rewarded")
        await db.referral_attributions.update_one(
            {"id": attr["id"]},
            {"$set": {"status": "QUALIFIED", "qualified_at": now, "reason": body.reason or "ADMIN_APPROVED", "updated_at": now}}
        )
        granted_result = await _grant_reward(attr["referrer_user_id"], attr["referred_user_id"], attr["id"])
        granted = granted_result.get("granted", False)
        if granted:
            await db.referral_attributions.update_one(
                {"id": attr["id"]},
                {"$set": {"status": "REWARDED", "rewarded_at": now}}
            )
        return {"success": True, "granted": granted, "credits": granted_result.get("credits", 0), "reason": granted_result.get("reason")}

    if action == "REJECT":
        await db.referral_attributions.update_one(
            {"id": attr["id"]},
            {"$set": {"status": "REJECTED", "reason": body.reason or "ADMIN_REJECTED", "updated_at": now}}
        )
        # If it was pending, decrement counters
        if attr.get("status") in ["SIGNED_UP", "VERIFIED", "ACTIVATED"]:
            await db.referral_profiles.update_one(
                {"user_id": attr["referrer_user_id"]},
                {"$inc": {"pending_referrals": -1, "rejected_referrals": 1}}
            )
        return {"success": True}

    if action == "REVERSE":
        # Revoke reward + deduct credits (if granted)
        reward = await db.referral_rewards.find_one({"attribution_id": attr["id"], "status": "GRANTED"}, {"_id": 0})
        if not reward:
            raise HTTPException(status_code=400, detail="No active reward to reverse")
        await db.referral_rewards.update_one(
            {"id": reward["id"]},
            {"$set": {"status": "REVERSED", "reversed_at": now, "reversed_by": admin.get("id"), "reason": body.reason or ""}}
        )
        credits = reward.get("credits", REWARD_CREDITS)
        await db.users.update_one({"id": attr["referrer_user_id"]}, {"$inc": {"credits": -credits}})
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": attr["referrer_user_id"],
            "amount": -credits,
            "type": "REFERRAL_REVERSAL",
            "description": f"Reversed reward (attribution {attr['id'][:8]})",
            "createdAt": now,
        })
        await db.referral_attributions.update_one(
            {"id": attr["id"]},
            {"$set": {"status": "REJECTED", "reason": body.reason or "ADMIN_REVERSED", "updated_at": now}}
        )
        await db.referral_profiles.update_one(
            {"user_id": attr["referrer_user_id"]},
            {"$inc": {"valid_referrals": -1, "rejected_referrals": 1, "total_credits_earned": -credits}}
        )
        return {"success": True, "reversed_credits": credits}

    raise HTTPException(status_code=400, detail="Unknown action")


@router.post("/admin/run-expiry-sweep")
async def admin_run_expiry_sweep(admin: dict = Depends(get_admin_user)):
    """Manually trigger expiry sweep."""
    count = await expire_referral_credits()
    return {"success": True, "expired_count": count}


@router.post("/admin/grant-purchase-bonus/{user_id}")
async def admin_force_purchase_bonus(user_id: str, admin: dict = Depends(get_admin_user)):
    """Admin override — manually trigger purchase bonus for a user."""
    result = await grant_referral_purchase_bonus(user_id, 0.0)
    return {"success": True, **result}
