"""
Anti-Abuse & Legal Safety — Copyright blocking, celebrity detection,
rate limiting, and concurrency controls.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("story_engine.safety")

# ═══════════════════════════════════════════════════════════════
# BLOCKED TERMS — Copyrighted characters & celebrities
# ═══════════════════════════════════════════════════════════════

COPYRIGHTED_CHARACTERS = {
    # Disney / Pixar
    "mickey mouse", "minnie mouse", "donald duck", "goofy", "elsa", "anna", "frozen",
    "simba", "mufasa", "lion king", "nemo", "dory", "woody", "buzz lightyear",
    "moana", "rapunzel", "cinderella", "snow white", "ariel", "little mermaid",
    # Marvel / DC
    "spider-man", "spiderman", "iron man", "ironman", "captain america", "thor",
    "hulk", "black widow", "batman", "superman", "wonder woman", "joker",
    "avengers", "justice league", "x-men",
    # Anime / Manga
    "goku", "naruto", "luffy", "sailor moon", "pikachu", "pokemon",
    "totoro", "spirited away", "attack on titan", "demon slayer",
    # Other
    "harry potter", "hogwarts", "shrek", "spongebob", "paw patrol",
    "peppa pig", "bluey", "cocomelon",
}

CELEBRITY_NAMES = {
    "taylor swift", "beyonce", "drake", "kanye west", "kim kardashian",
    "elon musk", "donald trump", "joe biden", "barack obama", "vladimir putin",
    "cristiano ronaldo", "lionel messi", "lebron james",
    "oprah winfrey", "jeff bezos", "mark zuckerberg",
}

BLOCKED_BRANDS = {
    "coca cola", "pepsi", "mcdonalds", "nike", "adidas", "apple",
    "google", "amazon", "facebook", "instagram", "tiktok", "youtube",
    "netflix", "spotify", "disney", "pixar", "marvel", "dc comics",
}


def check_content_safety(text: str) -> Optional[str]:
    """
    Check text for copyrighted characters, celebrities, and blocked brands.
    Returns violation message or None if clean.
    """
    text_lower = text.lower()

    for term in COPYRIGHTED_CHARACTERS:
        if term in text_lower:
            return f"Blocked: '{term}' is a copyrighted character. Use original characters instead."

    for term in CELEBRITY_NAMES:
        if term in text_lower:
            return f"Blocked: '{term}' is a real person. No celebrity likeness allowed without consent."

    for term in BLOCKED_BRANDS:
        if term in text_lower:
            return f"Blocked: '{term}' is a trademarked brand. Remove brand references."

    return None


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
        return f"Rate limit: You have {active_count} active jobs. Max {MAX_CONCURRENT_JOBS} concurrent."

    # Hourly limit
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    hourly_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": one_hour_ago},
    })
    if hourly_count >= MAX_JOBS_PER_HOUR:
        return f"Rate limit: {MAX_JOBS_PER_HOUR} jobs per hour exceeded. Please wait."

    # Daily limit
    day_start = now.replace(hour=0, minute=0, second=0).isoformat()
    daily_count = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": day_start},
    })
    if daily_count >= MAX_JOBS_PER_DAY:
        return f"Rate limit: {MAX_JOBS_PER_DAY} jobs per day exceeded."

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
        return "Abuse detection: Too many rapid submissions. Please slow down."

    # Repeated failures (possible probing)
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    failed = await db.story_engine_jobs.count_documents({
        "user_id": user_id,
        "state": "FAILED",
        "created_at": {"$gte": one_hour_ago},
    })
    if failed >= 8:
        return "Abuse detection: High failure rate. Account flagged for review."

    return None
