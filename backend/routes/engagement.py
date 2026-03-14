"""
Engagement System Routes — Daily Challenges, Streaks, Creator Levels, Trending
"""
import random
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException

from shared import db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/engagement", tags=["engagement"])

# ─── Daily Challenge Templates (rotate daily) ─────────────────────────
CHALLENGE_POOL = [
    {"prompt": "Create a superhero rescue story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Generate a viral motivational reel script", "tool": "reels", "reward": 10, "category": "social"},
    {"prompt": "Turn a photo into a comic-style character", "tool": "photo-to-comic", "reward": 10, "category": "image"},
    {"prompt": "Create a kids bedtime story about a brave kitten", "tool": "bedtime-story-builder", "reward": 10, "category": "story"},
    {"prompt": "Design a coloring book page with a dragon", "tool": "coloring-book", "reward": 10, "category": "image"},
    {"prompt": "Write 5 Instagram bios for a travel blogger", "tool": "instagram-bio-generator", "reward": 10, "category": "social"},
    {"prompt": "Create a funny reaction GIF about Monday mornings", "tool": "gif-maker", "reward": 10, "category": "image"},
    {"prompt": "Generate a fantasy adventure comic storybook", "tool": "comic-storybook", "reward": 15, "category": "story"},
    {"prompt": "Create a space exploration story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Write a reel script about productivity tips", "tool": "reels", "reward": 10, "category": "social"},
    {"prompt": "Create a magical forest bedtime story", "tool": "bedtime-story-builder", "reward": 10, "category": "story"},
    {"prompt": "Generate a brand story for an eco-friendly startup", "tool": "brand-story-builder", "reward": 15, "category": "social"},
    {"prompt": "Create a pirate adventure story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Design a coloring page with underwater creatures", "tool": "coloring-book", "reward": 10, "category": "image"},
    {"prompt": "Write captions for 3 fitness posts", "tool": "caption-rewriter", "reward": 10, "category": "social"},
    {"prompt": "Create a robot adventure comic storybook", "tool": "comic-storybook", "reward": 15, "category": "story"},
    {"prompt": "Generate a 30-second dinosaur story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Write a reel script about healthy recipes", "tool": "reels", "reward": 10, "category": "social"},
    {"prompt": "Create a fairy tale bedtime story with a fox", "tool": "bedtime-story-builder", "reward": 10, "category": "story"},
    {"prompt": "Create a superhero origin story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Generate a funny animal reaction GIF", "tool": "gif-maker", "reward": 10, "category": "image"},
    {"prompt": "Write a reel script about morning routines", "tool": "reels", "reward": 10, "category": "social"},
    {"prompt": "Create a coloring book page with forest animals", "tool": "coloring-book", "reward": 10, "category": "image"},
    {"prompt": "Generate a treasure hunt adventure story video", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Write a brand story for a coffee shop", "tool": "brand-story-builder", "reward": 15, "category": "social"},
    {"prompt": "Create a mystery adventure comic storybook", "tool": "comic-storybook", "reward": 15, "category": "story"},
    {"prompt": "Write Instagram bios for a food blogger", "tool": "instagram-bio-generator", "reward": 10, "category": "social"},
    {"prompt": "Create a dragon story video for kids", "tool": "story-video-studio", "reward": 10, "category": "video"},
    {"prompt": "Generate a reel script about travel tips", "tool": "reels", "reward": 10, "category": "social"},
    {"prompt": "Create a coloring page with space rockets", "tool": "coloring-book", "reward": 10, "category": "image"},
]

# ─── Streak milestones ─────────────────────────────────────────────────
STREAK_MILESTONES = {3: 10, 7: 25, 14: 50, 30: 100, 60: 250, 100: 500}

# ─── Creator levels ────────────────────────────────────────────────────
CREATOR_LEVELS = [
    (0, "Beginner"),
    (10, "Creator"),
    (50, "Creator Pro"),
    (150, "AI Producer"),
    (500, "Visionary"),
]


def _get_today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_daily_challenge(date_str: str) -> dict:
    """Deterministic daily challenge based on date."""
    seed = int(date_str.replace("-", ""))
    idx = seed % len(CHALLENGE_POOL)
    challenge = CHALLENGE_POOL[idx]
    return {**challenge, "date": date_str, "challenge_id": f"daily_{date_str}"}


def _get_creator_level(count: int) -> dict:
    level_name = "Beginner"
    current_threshold = 0
    next_threshold = 10
    for i, (threshold, name) in enumerate(CREATOR_LEVELS):
        if count >= threshold:
            level_name = name
            current_threshold = threshold
            next_threshold = CREATOR_LEVELS[i + 1][0] if i + 1 < len(CREATOR_LEVELS) else threshold + 500
    progress = min(100, round((count - current_threshold) / max(1, next_threshold - current_threshold) * 100))
    return {"level": level_name, "creation_count": count, "next_level_at": next_threshold, "progress": progress}


# ─── GET /api/engagement/dashboard ─────────────────────────────────────
@router.get("/dashboard")
async def get_engagement_dashboard(current_user: dict = Depends(get_current_user)):
    """Return all engagement data for dashboard sidebar."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    today = _get_today()

    # 1. Daily challenge
    challenge = _get_daily_challenge(today)
    completion = await db.challenge_completions.find_one(
        {"user_id": user_id, "challenge_id": challenge["challenge_id"]}, {"_id": 0}
    )
    challenge["completed"] = completion is not None

    # 2. Streak
    streak_doc = await db.creation_streaks.find_one({"user_id": user_id}, {"_id": 0})
    if not streak_doc:
        streak_doc = {"current_streak": 0, "longest_streak": 0, "last_creation_date": None}
    streak = {
        "current": streak_doc.get("current_streak", 0),
        "longest": streak_doc.get("longest_streak", 0),
        "last_date": streak_doc.get("last_creation_date"),
    }

    # 3. Creator level
    total_creations = await db.generations.count_documents({"userId": user_id, "status": "SUCCEEDED"})
    total_creations += await db.pipeline_jobs.count_documents({"user_id": user_id, "status": "COMPLETED"})
    level = _get_creator_level(total_creations)

    # 4. AI Ideas (deterministic per day, rotated)
    seed = int(today.replace("-", "")) + hash(user_id) % 100
    rng = random.Random(seed)
    ideas_pool = [
        {"text": "Create a motivational Instagram reel", "tool": "reels"},
        {"text": "Generate a kids bedtime story video", "tool": "story-video-studio"},
        {"text": "Turn your selfie into a comic hero", "tool": "photo-to-comic"},
        {"text": "Create a funny reaction GIF", "tool": "gif-maker"},
        {"text": "Design a coloring page for kids", "tool": "coloring-book"},
        {"text": "Write viral captions for your posts", "tool": "caption-rewriter"},
        {"text": "Create a fantasy comic storybook", "tool": "comic-storybook"},
        {"text": "Generate a brand story for your business", "tool": "brand-story-builder"},
        {"text": "Create a space adventure story video", "tool": "story-video-studio"},
        {"text": "Write a hook for your next reel", "tool": "reels"},
    ]
    rng.shuffle(ideas_pool)
    ideas = ideas_pool[:4]

    return {
        "challenge": challenge,
        "streak": streak,
        "level": level,
        "ideas": ideas,
    }


# ─── POST /api/engagement/challenge/complete ───────────────────────────
@router.post("/challenge/complete")
async def complete_daily_challenge(current_user: dict = Depends(get_current_user)):
    """Mark today's challenge as complete and award credits."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    today = _get_today()
    challenge = _get_daily_challenge(today)

    # Check if already completed
    existing = await db.challenge_completions.find_one(
        {"user_id": user_id, "challenge_id": challenge["challenge_id"]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Challenge already completed today")

    # Award credits
    reward = challenge["reward"]
    await db.users.update_one({"id": user_id}, {"$inc": {"credits": reward}})
    await db.challenge_completions.insert_one({
        "user_id": user_id,
        "challenge_id": challenge["challenge_id"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "reward": reward,
    })

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "credits": 1})
    logger.info(f"[ENGAGEMENT] User {user_id[:8]} completed challenge, awarded {reward} credits")
    return {"success": True, "reward": reward, "new_balance": user.get("credits", 0)}


# ─── POST /api/engagement/streak/update ────────────────────────────────
@router.post("/streak/update")
async def update_creation_streak(current_user: dict = Depends(get_current_user)):
    """Called after a successful generation to update streak."""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    today = _get_today()

    streak_doc = await db.creation_streaks.find_one({"user_id": user_id})
    if not streak_doc:
        # First creation ever
        await db.creation_streaks.insert_one({
            "user_id": user_id,
            "current_streak": 1,
            "longest_streak": 1,
            "last_creation_date": today,
        })
        return {"success": True, "streak": 1, "milestone_reward": 0}

    last_date = streak_doc.get("last_creation_date", "")
    current = streak_doc.get("current_streak", 0)
    longest = streak_doc.get("longest_streak", 0)

    if last_date == today:
        # Already created today
        return {"success": True, "streak": current, "milestone_reward": 0}

    # Check if yesterday
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_date == yesterday:
        new_streak = current + 1
    else:
        new_streak = 1  # Streak broken

    new_longest = max(longest, new_streak)
    await db.creation_streaks.update_one(
        {"user_id": user_id},
        {"$set": {"current_streak": new_streak, "longest_streak": new_longest, "last_creation_date": today}}
    )

    # Check milestone rewards
    milestone_reward = 0
    if new_streak in STREAK_MILESTONES:
        milestone_reward = STREAK_MILESTONES[new_streak]
        await db.users.update_one({"id": user_id}, {"$inc": {"credits": milestone_reward}})
        logger.info(f"[ENGAGEMENT] User {user_id[:8]} hit {new_streak}-day streak, awarded {milestone_reward} credits")

    return {"success": True, "streak": new_streak, "milestone_reward": milestone_reward}


# ─── GET /api/engagement/trending ──────────────────────────────────────
@router.get("/trending")
async def get_trending_creations():
    """Return top 6 trending gallery items."""
    jobs = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "output_url": {"$exists": True, "$ne": None}},
        {"_id": 0, "job_id": 1, "title": 1, "animation_style": 1, "remix_count": 1, "thumbnail_url": 1}
    ).sort("remix_count", -1).to_list(length=6)

    # Presign thumbnail URLs
    from utils.r2_presign import presign_url
    for j in jobs:
        if j.get("thumbnail_url"):
            j["thumbnail_url"] = presign_url(j["thumbnail_url"])

    return {"trending": jobs}
