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
REWARD_CREDITS = 300
ATTRIBUTION_WINDOW_DAYS = 30

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


async def _grant_reward(referrer_id: str, referred_user_id: str, attribution_id: str) -> bool:
    """Idempotent — returns True if granted this call."""
    # Prevent duplicate reward
    existing = await db.referral_rewards.find_one(
        {"attribution_id": attribution_id}, {"_id": 0}
    )
    if existing:
        return False

    now = datetime.now(timezone.utc).isoformat()
    reward_id = str(uuid.uuid4())
    await db.referral_rewards.insert_one({
        "id": reward_id,
        "attribution_id": attribution_id,
        "referrer_user_id": referrer_id,
        "referred_user_id": referred_user_id,
        "credits": REWARD_CREDITS,
        "status": "GRANTED",
        "granted_at": now,
    })
    # Add credits to referrer
    await db.users.update_one({"id": referrer_id}, {"$inc": {"credits": REWARD_CREDITS}})
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": referrer_id,
        "amount": REWARD_CREDITS,
        "type": "REFERRAL_BONUS",
        "description": "Referral reward — new creator joined and started creating",
        "source_user_id": referred_user_id,
        "createdAt": now,
    })
    # Update profile counters
    await db.referral_profiles.update_one(
        {"user_id": referrer_id},
        {
            "$inc": {
                "valid_referrals": 1,
                "pending_referrals": -1,
                "total_credits_earned": REWARD_CREDITS,
            }
        }
    )
    # Streak bonus — every 3 valid referrals, +500
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
                "description": f"Streak bonus — {expected_streaks * 3} valid referrals",
                "createdAt": now,
            })
            await db.referral_profiles.update_one(
                {"user_id": referrer_id},
                {"$inc": {"total_credits_earned": bonus}, "$set": {"streak_bonus_granted": expected_streaks}}
            )
    logger.info(f"[REF] +{REWARD_CREDITS} granted to {referrer_id[:8]} (attrib {attribution_id[:8]})")
    return True


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
    return {
        "profile": profile,
        "attributions": enriched,
        "rewards": rewards,
        "share_url": share_url,
        "reward_credits": REWARD_CREDITS,
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
    granted = await _grant_reward(attr["referrer_user_id"], target_user_id, attr["id"])
    if granted:
        await db.referral_attributions.update_one(
            {"id": attr["id"]},
            {"$set": {"status": "REWARDED", "rewarded_at": now}}
        )
    return {"qualified": True, "granted": granted, "credits": REWARD_CREDITS if granted else 0}


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
        granted = await _grant_reward(attr["referrer_user_id"], attr["referred_user_id"], attr["id"])
        if granted:
            await db.referral_attributions.update_one(
                {"id": attr["id"]},
                {"$set": {"status": "REWARDED", "rewarded_at": now}}
            )
        return {"success": True, "granted": granted}

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
