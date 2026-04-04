"""
Media Token Service — DB-backed opaque tokens for secure media access.

Replaces JWT-only signing with server-stored, hashed tokens.
Supports: single-use downloads, limited-use previews, session binding,
IP/UA consistency checks, revocation, and concurrency limits.
"""
import hashlib
import secrets
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from shared import db

logger = logging.getLogger("creatorstudio.media_token_service")

# ── Configuration ──
DOWNLOAD_TTL_SECONDS = 60
PREVIEW_TTL_SECONDS = 120
HLS_TTL_SECONDS = 300
DOWNLOAD_MAX_USES = 1
PREVIEW_MAX_USES = 10
HLS_MANIFEST_MAX_USES = 50
HLS_SEGMENT_MAX_USES = 3

# Concurrency
FREE_SESSION_LIMIT = 1
PAID_SESSION_LIMIT = 3

# Abuse thresholds
DOWNLOAD_RATE_LIMIT_PER_HOUR = 30
ABUSE_MULTI_IP_WINDOW_SECONDS = 60


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


async def issue_token(
    user_id: str,
    asset_id: str,
    file_ref: str,
    asset_type: str,
    purpose: str,
    ip: str,
    user_agent: str,
    session_id: Optional[str] = None,
    max_uses: Optional[int] = None,
    ttl_seconds: Optional[int] = None,
) -> dict:
    """Issue a new opaque media token. Returns raw token + metadata."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    if purpose == "download":
        mu = max_uses or DOWNLOAD_MAX_USES
        ttl = ttl_seconds or DOWNLOAD_TTL_SECONDS
    elif purpose == "hls_manifest":
        mu = max_uses or HLS_MANIFEST_MAX_USES
        ttl = ttl_seconds or HLS_TTL_SECONDS
    elif purpose == "hls_segment":
        mu = max_uses or HLS_SEGMENT_MAX_USES
        ttl = ttl_seconds or HLS_TTL_SECONDS
    else:
        mu = max_uses or PREVIEW_MAX_USES
        ttl = ttl_seconds or PREVIEW_TTL_SECONDS

    now = datetime.now(timezone.utc)
    doc = {
        "token_hash": token_hash,
        "user_id": user_id,
        "asset_id": asset_id,
        "file_ref": file_ref,
        "asset_type": asset_type,
        "purpose": purpose,
        "expires_at": now + timedelta(seconds=ttl),
        "max_uses": mu,
        "used_count": 0,
        "session_id": session_id or str(uuid.uuid4()),
        "ip_hash": _hash_value(ip),
        "ua_hash": _hash_value(user_agent),
        "status": "active",
        "created_at": now,
    }
    await db.media_tokens.insert_one(doc)
    return {"token": raw_token, "ttl": ttl, "purpose": purpose, "max_uses": mu}


async def validate_token(raw_token: str, ip: str, user_agent: str) -> dict:
    """
    Validate an opaque token. Returns the token doc on success.
    Raises ValueError with descriptive message on failure.
    """
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)

    # Atomic: find active token and increment used_count
    doc = await db.media_tokens.find_one_and_update(
        {
            "token_hash": token_hash,
            "status": "active",
            "expires_at": {"$gt": now},
        },
        {"$inc": {"used_count": 1}, "$set": {"last_used_at": now}},
        return_document=True,
        projection={"_id": 0},
    )

    if not doc:
        # Check why it failed
        expired = await db.media_tokens.find_one({"token_hash": token_hash}, {"_id": 0, "status": 1, "expires_at": 1})
        if not expired:
            raise ValueError("Token not found")
        if expired.get("status") == "revoked":
            raise ValueError("Token revoked")
        if expired.get("expires_at") and expired["expires_at"] <= now:
            await db.media_tokens.update_one({"token_hash": token_hash}, {"$set": {"status": "expired"}})
            raise ValueError("Token expired")
        raise ValueError("Token invalid")

    # Check max_uses
    if doc["used_count"] > doc["max_uses"]:
        await db.media_tokens.update_one(
            {"token_hash": token_hash},
            {"$set": {"status": "exhausted"}},
        )
        raise ValueError("Token exhausted (max uses exceeded)")

    # Anti-replay: check IP/UA consistency for download tokens
    if doc["purpose"] == "download":
        current_ip_hash = _hash_value(ip)
        current_ua_hash = _hash_value(user_agent)
        if doc["ip_hash"] != current_ip_hash or doc["ua_hash"] != current_ua_hash:
            await _create_abuse_flag(
                doc["user_id"], "multi_ip_token_use",
                {"token_hash": token_hash[:12], "asset_id": doc["asset_id"],
                 "original_ip_hash": doc["ip_hash"], "current_ip_hash": current_ip_hash},
            )
            await db.media_tokens.update_one(
                {"token_hash": token_hash}, {"$set": {"status": "revoked"}},
            )
            raise ValueError("Token used from different origin — revoked")

    return doc


async def revoke_token(raw_token: str) -> bool:
    token_hash = _hash_token(raw_token)
    result = await db.media_tokens.update_one(
        {"token_hash": token_hash, "status": "active"},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


async def revoke_user_tokens(user_id: str, reason: str = "admin_action") -> int:
    result = await db.media_tokens.update_many(
        {"user_id": user_id, "status": "active"},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc), "revoke_reason": reason}},
    )
    return result.modified_count


async def check_rate_limit(user_id: str) -> bool:
    """Returns True if user is within rate limit."""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    count = await db.media_tokens.count_documents({
        "user_id": user_id,
        "purpose": "download",
        "created_at": {"$gte": one_hour_ago},
    })
    return count < DOWNLOAD_RATE_LIMIT_PER_HOUR


# ── Session / Concurrency ──

async def create_session(user_id: str, ip: str, user_agent: str, user_role: str) -> dict:
    """Create a media session. Enforces concurrency limits by plan."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    is_paid = user_role.upper() in ("ADMIN", "SUPERADMIN", "PREMIUM", "PRO")
    limit = PAID_SESSION_LIMIT if is_paid else FREE_SESSION_LIMIT

    active = await db.user_media_sessions.count_documents({
        "user_id": user_id,
        "status": "active",
        "last_active": {"$gte": now - timedelta(minutes=10)},
    })

    if active >= limit:
        # Kill oldest session
        oldest = await db.user_media_sessions.find_one(
            {"user_id": user_id, "status": "active"},
            sort=[("started_at", 1)],
        )
        if oldest:
            await db.user_media_sessions.update_one(
                {"session_id": oldest["session_id"]},
                {"$set": {"status": "terminated", "terminated_at": now, "terminate_reason": "concurrency_limit"}},
            )
            # Revoke tokens for terminated session
            await db.media_tokens.update_many(
                {"session_id": oldest["session_id"], "status": "active"},
                {"$set": {"status": "revoked", "revoke_reason": "session_terminated"}},
            )

    doc = {
        "session_id": session_id,
        "user_id": user_id,
        "started_at": now,
        "last_active": now,
        "status": "active",
        "ip": _hash_value(ip),
        "ua_hash": _hash_value(user_agent),
    }
    await db.user_media_sessions.insert_one(doc)
    return {"session_id": session_id, "limit": limit, "active_sessions": min(active + 1, limit)}


async def touch_session(session_id: str):
    await db.user_media_sessions.update_one(
        {"session_id": session_id},
        {"$set": {"last_active": datetime.now(timezone.utc)}},
    )


# ── Abuse Response ──

async def _create_abuse_flag(user_id: str, reason: str, details: dict):
    await db.media_abuse_flags.insert_one({
        "flag_id": str(uuid.uuid4()),
        "user_id": user_id,
        "reason": reason,
        "details": details,
        "status": "open",
        "severity": "high" if reason in ("multi_ip_token_use", "rate_exceeded_severe") else "medium",
        "created_at": datetime.now(timezone.utc),
    })
    logger.warning(f"ABUSE FLAG: user={user_id} reason={reason}")


async def check_and_respond_to_abuse(user_id: str, ip: str, action: str) -> dict:
    """
    Check for abuse patterns and take automatic action.
    Returns dict with status and any action taken.
    """
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # Check if user is suspended
    suspension = await db.media_suspensions.find_one({
        "user_id": user_id,
        "status": "active",
        "expires_at": {"$gt": now},
    }, {"_id": 0})
    if suspension:
        return {"blocked": True, "reason": "suspended", "expires_at": suspension["expires_at"].isoformat()}

    # Count recent download tokens
    recent_downloads = await db.media_tokens.count_documents({
        "user_id": user_id,
        "purpose": "download",
        "created_at": {"$gte": one_hour_ago},
    })

    # Severe abuse: > 2x rate limit
    if recent_downloads > DOWNLOAD_RATE_LIMIT_PER_HOUR * 2:
        await _create_abuse_flag(user_id, "rate_exceeded_severe", {
            "downloads_in_hour": recent_downloads,
            "limit": DOWNLOAD_RATE_LIMIT_PER_HOUR,
        })
        await revoke_user_tokens(user_id, reason="severe_abuse")
        await suspend_user_media(user_id, duration_minutes=30, reason="auto_severe_abuse")
        return {"blocked": True, "reason": "severe_abuse_auto_suspended", "action": "suspended_30min"}

    # Moderate abuse: > rate limit
    if recent_downloads > DOWNLOAD_RATE_LIMIT_PER_HOUR:
        await _create_abuse_flag(user_id, "rate_exceeded", {
            "downloads_in_hour": recent_downloads,
            "limit": DOWNLOAD_RATE_LIMIT_PER_HOUR,
        })
        return {"blocked": True, "reason": "rate_limited"}

    # Check multi-IP pattern
    recent_ips = await db.media_access_log.distinct("ip", {
        "user_id": user_id,
        "timestamp": {"$gte": now - timedelta(seconds=ABUSE_MULTI_IP_WINDOW_SECONDS)},
    })
    if len(recent_ips) > 3:
        await _create_abuse_flag(user_id, "multi_ip_access", {
            "unique_ips_in_window": len(recent_ips),
            "window_seconds": ABUSE_MULTI_IP_WINDOW_SECONDS,
        })

    return {"blocked": False}


async def suspend_user_media(user_id: str, duration_minutes: int = 60, reason: str = "admin_action") -> dict:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=duration_minutes)
    await db.media_suspensions.insert_one({
        "suspension_id": str(uuid.uuid4()),
        "user_id": user_id,
        "status": "active",
        "reason": reason,
        "created_at": now,
        "expires_at": expires,
    })
    revoked = await revoke_user_tokens(user_id, reason=f"suspension:{reason}")
    return {"suspended": True, "expires_at": expires.isoformat(), "tokens_revoked": revoked}


async def unsuspend_user_media(user_id: str) -> bool:
    result = await db.media_suspensions.update_many(
        {"user_id": user_id, "status": "active"},
        {"$set": {"status": "lifted", "lifted_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count > 0


async def log_media_event(user_id: str, action: str, ip: str, user_agent: str, **extra):
    await db.media_access_log.insert_one({
        "user_id": user_id,
        "action": action,
        "ip": ip,
        "user_agent": user_agent[:200],
        "timestamp": datetime.now(timezone.utc),
        **extra,
    })
