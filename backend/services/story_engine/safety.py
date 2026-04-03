"""
Anti-Abuse & Legal Safety — Safe rewriting, celebrity detection,
rate limiting, and concurrency controls.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("story_engine.safety")

# ═══════════════════════════════════════════════════════════════
# SAFE REWRITE ENGINE — rewrite risky terms, never block
# ═══════════════════════════════════════════════════════════════

from services.rewrite_engine import safe_rewrite, RewriteResult


def check_content_safety(text: str) -> Optional[str]:
    """
    Legacy interface — now always returns None (no blocking).
    Callers should use safe_rewrite() directly for the rewritten text.
    Kept for backward compatibility so existing code doesn't break.
    """
    return None


def rewrite_content_safely(text: str) -> tuple:
    """
    Rewrite risky terms and return (rewritten_text, was_rewritten, user_note).
    Never raises, never blocks. Always returns usable text.
    """
    result = safe_rewrite(text)
    return result.rewritten_text, result.was_rewritten, result.user_note


# ═══════════════════════════════════════════════════════════════
# RATE LIMITING & CONCURRENCY
# ═══════════════════════════════════════════════════════════════

# Per-user limits
MAX_CONCURRENT_JOBS = 2
MAX_JOBS_PER_HOUR = 10
MAX_JOBS_PER_DAY = 50


async def check_rate_limits(db, user_id: str) -> Optional[str]:
    """
    Check user rate limits. Returns error message or None if within limits.
    """
    now = datetime.now(timezone.utc)

    # Concurrent jobs
    active_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "state": {"$nin": ["READY", "PARTIAL_READY", "FAILED"]},
    })
    if active_count >= MAX_CONCURRENT_JOBS:
        return f"SLOTS_BUSY:All rendering slots are busy ({active_count}/{MAX_CONCURRENT_JOBS}). Your current video is still being created — please wait for it to finish, then you can start a new one."

    # Hourly limit
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    hourly_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if hourly_count >= MAX_JOBS_PER_HOUR:
        return f"SLOTS_BUSY:You've created {hourly_count} videos in the last hour. To ensure quality for everyone, please wait a few minutes before starting another."

    # Daily limit
    day_start = now.replace(hour=0, minute=0, second=0).isoformat()
    daily_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": day_start},
    })
    if daily_count >= MAX_JOBS_PER_DAY:
        return f"SLOTS_BUSY:You've reached today's generation limit ({daily_count}/{MAX_JOBS_PER_DAY}). Your limit resets at midnight — come back tomorrow to create more!"

    return None


async def detect_abuse(db, user_id: str) -> Optional[str]:
    """
    Detect potential abuse patterns.
    """
    now = datetime.now(timezone.utc)
    ten_min_ago = (now - timedelta(minutes=10)).isoformat()

    # Rapid-fire submissions
    recent = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": ten_min_ago},
    })
    if recent >= 5:
        return "SLOTS_BUSY:You've submitted several videos in quick succession. Please wait a few minutes before starting another to ensure the best quality."

    # Repeated failures (possible probing)
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    failed = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "state": "FAILED",
        "created_at": {"$gte": one_hour_ago},
    })
    if failed >= 8:
        return "SLOTS_BUSY:We noticed several failed attempts. Our team is looking into it — please try again in a little while."

    return None
