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


# ─── GET /api/engagement/story-feed ──────────────────────────────────────
@router.get("/story-feed")
async def get_story_feed():
    """Return story-first dashboard data: hero, trending stories, characters, live counter."""

    def to_proxy_url(stored_url: str) -> str:
        """Convert R2 stored URL to backend proxy URL for reliable delivery."""
        if not stored_url:
            return stored_url
        try:
            base = stored_url.split('?')[0]  # strip query params
            # Handle r2.dev public URLs: https://pub-xxx.r2.dev/{key}
            if '.r2.dev/' in base:
                key = base.split('.r2.dev/', 1)[1]
                return f"/api/media/r2/{key}"
            # Handle r2.cloudflarestorage.com URLs: https://{acct}.r2.cloudflarestorage.com/{bucket}/{key}
            if '.r2.cloudflarestorage.com/' in base:
                parts = base.split('.r2.cloudflarestorage.com/', 1)
                if len(parts) > 1:
                    bucket_and_key = parts[1].split('/', 1)
                    if len(bucket_and_key) > 1:
                        return f"/api/media/r2/{bucket_and_key[1]}"
            return stored_url
        except Exception:
            return stored_url

    def resolve_thumbnail(job: dict) -> str | None:
        """Resolve thumbnail: prefer thumbnail_url, fallback to first scene image via proxy."""
        thumb = to_proxy_url(job.get("thumbnail_url"))
        if thumb:
            return thumb
        # Fallback: use the first scene image — always route through proxy for cross-domain reliability
        scene_imgs = job.get("scene_images", {})
        if scene_imgs:
            first_key = sorted(scene_imgs.keys(), key=lambda k: int(k) if k.isdigit() else 999)[0] if scene_imgs else None
            if first_key and isinstance(scene_imgs[first_key], dict):
                # Prefer r2_key for clean proxy URL
                r2_key = scene_imgs[first_key].get("r2_key")
                if r2_key:
                    return f"/api/media/r2/{r2_key}"
                # Fallback: convert direct URL to proxy
                img_url = scene_imgs[first_key].get("url")
                if img_url:
                    return to_proxy_url(img_url)
        return None

    # Hero story: best completed story (prefer one with thumbnail+video, fallback to any)
    hero_job = await db.pipeline_jobs.find_one(
        {"status": "COMPLETED", "output_url": {"$exists": True, "$ne": None}, "thumbnail_url": {"$exists": True, "$ne": None}},
        {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "thumbnail_url": 1, "output_url": 1, "preview_url": 1, "remix_count": 1, "animation_style": 1, "scene_images": 1},
    )
    # Fallback: any completed story with video (no thumbnail required)
    if not hero_job:
        hero_job = await db.pipeline_jobs.find_one(
            {"status": "COMPLETED", "output_url": {"$exists": True, "$ne": None}},
            {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "thumbnail_url": 1, "output_url": 1, "preview_url": 1, "remix_count": 1, "animation_style": 1, "scene_images": 1},
        )
    # Fallback: any completed story at all
    if not hero_job:
        hero_job = await db.pipeline_jobs.find_one(
            {"status": "COMPLETED"},
            {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "thumbnail_url": 1, "output_url": 1, "preview_url": 1, "remix_count": 1, "animation_style": 1, "scene_images": 1},
        )
    if hero_job:
        hero_job["thumbnail_url"] = resolve_thumbnail(hero_job)
        hero_job["output_url"] = to_proxy_url(hero_job.get("output_url"))
        hero_job["preview_url"] = to_proxy_url(hero_job.get("preview_url"))
        hero_job.pop("scene_images", None)
        # Extract hook line from story text
        text = hero_job.get("story_text", "")
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]
        hero_job["hook_text"] = (sentences[0] + "...") if sentences else ""

    # Trending stories: top 20 completed stories (no thumbnail requirement — fallback to scene images)
    trending = await db.pipeline_jobs.find(
        {"status": "COMPLETED"},
        {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "thumbnail_url": 1, "output_url": 1, "preview_url": 1, "remix_count": 1, "animation_style": 1, "created_at": 1, "scene_images": 1},
    ).sort([("remix_count", -1), ("created_at", -1)]).to_list(length=20)

    for job in trending:
        job["thumbnail_url"] = resolve_thumbnail(job)
        job["output_url"] = to_proxy_url(job.get("output_url"))
        job["preview_url"] = to_proxy_url(job.get("preview_url"))
        job.pop("scene_images", None)
        text = job.get("story_text", "")
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]
        job["hook_text"] = (sentences[0] + "...") if sentences else ""
        job.pop("story_text", None)

    # Popular characters
    chars = await db.character_profiles.find(
        {},
        {"_id": 0, "character_id": 1, "name": 1, "species_or_type": 1, "personality_summary": 1},
    ).to_list(length=6)

    # Also try story_characters for richer data
    story_chars = await db.story_characters.find(
        {"name": {"$not": {"$regex": "^TEST_"}}},
        {"_id": 0, "character_id": 1, "name": 1, "description": 1, "reference_images": 1, "appearance": 1},
    ).to_list(length=6)

    # Merge — prefer story_characters which have images
    all_chars = []
    seen = set()
    for c in story_chars + chars:
        name = c.get("name", "")
        if name and name not in seen:
            seen.add(name)
            imgs = c.get("reference_images", [])
            all_chars.append({
                "character_id": c.get("character_id"),
                "name": name,
                "description": c.get("description") or c.get("personality_summary") or c.get("species_or_type", ""),
                "image_url": imgs[0] if imgs else None,
            })
    all_chars = all_chars[:6]

    # Live counter: stories created today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stories_today = await db.pipeline_jobs.count_documents({
        "created_at": {"$gte": today_start.isoformat()},
    })
    total_stories = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})
    total_continuations = await db.pipeline_jobs.count_documents({"is_continuation": True})

    return {
        "hero": hero_job,
        "trending": trending,
        "characters": all_chars,
        "live_stats": {
            "stories_today": stories_today,
            "total_stories": total_stories,
            "total_continuations": total_continuations,
        },
    }


@router.post("/card-click")
async def track_card_click(data: dict):
    """Track story card clicks for A/B testing CTA variants."""
    await db.card_clicks.insert_one({
        "story_id": data.get("story_id"),
        "cta_variant": data.get("cta_variant"),
        "source": data.get("source", "dashboard"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True}


@router.get("/card-analytics")
async def card_analytics():
    """A/B test results for card CTA variants."""
    pipeline = [
        {"$group": {"_id": "$cta_variant", "clicks": {"$sum": 1}}},
        {"$sort": {"clicks": -1}},
    ]
    results = await db.card_clicks.aggregate(pipeline).to_list(100)
    total = sum(r["clicks"] for r in results)
    return {
        "total_clicks": total,
        "variants": [
            {"variant": r["_id"], "clicks": r["clicks"], "pct": round(r["clicks"] / total * 100, 1) if total else 0}
            for r in results
        ],
    }


# ─── Category keyword patterns for explore ──────────────────────────
_CAT_PATTERNS = {
    "emotional": "love|heart|dream|memory|hope|wish|sky|star|light|tear|goodbye|coral|sky|moon",
    "mystery": "mystery|secret|dark|shadow|hidden|night|door|lost|key|puzzle|whisper|forgotten",
    "kids": None,  # determined by age_group
    "viral": "adventure|magic|brave|journey|quest|amazing|epic|power|hero|robot|fox|pirate",
}


@router.get("/explore")
async def explore_stories(category: str = "all", sort: str = "trending", cursor: int = 0, limit: int = 12):
    """Gallery / Explore endpoint with category filters, sort, and cursor pagination."""

    def to_proxy_url(stored_url: str) -> str:
        if not stored_url:
            return stored_url
        try:
            base = stored_url.split('?')[0]
            if '.r2.dev/' in base:
                key = base.split('.r2.dev/', 1)[1]
                return f"/api/media/r2/{key}"
            if '.r2.cloudflarestorage.com/' in base:
                parts = base.split('.r2.cloudflarestorage.com/', 1)
                if len(parts) > 1:
                    bucket_and_key = parts[1].split('/', 1)
                    if len(bucket_and_key) > 1:
                        return f"/api/media/r2/{bucket_and_key[1]}"
            return stored_url
        except Exception:
            return stored_url

    # Include stories that have thumbnail OR scene_images
    base_q = {"status": "COMPLETED", "$or": [
        {"thumbnail_url": {"$exists": True, "$ne": None}},
        {"scene_images": {"$exists": True, "$ne": {}}},
    ]}
    query = {**base_q}

    if category == "kids":
        query["age_group"] = {"$regex": "kids|toddler|child", "$options": "i"}
    elif category in _CAT_PATTERNS and _CAT_PATTERNS[category]:
        query["title"] = {"$regex": _CAT_PATTERNS[category], "$options": "i"}

    sort_map = {
        "trending": [("remix_count", -1), ("created_at", -1)],
        "new": [("created_at", -1)],
        "most_continued": [("remix_count", -1)],
    }
    sort_key = sort_map.get(sort, sort_map["trending"])

    total = await db.pipeline_jobs.count_documents(query)
    raw = await db.pipeline_jobs.find(
        query,
        {"_id": 0, "job_id": 1, "title": 1, "story_text": 1, "thumbnail_url": 1,
         "animation_style": 1, "age_group": 1, "remix_count": 1, "created_at": 1, "scene_images": 1},
    ).sort(sort_key).skip(cursor).limit(limit).to_list(limit)

    stories = []
    for job in raw:
        # Resolve thumbnail: prefer thumbnail_url, fallback to first scene image via proxy
        thumb = to_proxy_url(job.get("thumbnail_url"))
        if not thumb:
            scene_imgs = job.get("scene_images", {})
            if scene_imgs:
                first_key = sorted(scene_imgs.keys(), key=lambda k: int(k) if k.isdigit() else 999)[0] if scene_imgs else None
                if first_key and isinstance(scene_imgs[first_key], dict):
                    r2_key = scene_imgs[first_key].get("r2_key")
                    if r2_key:
                        thumb = f"/api/media/r2/{r2_key}"
                    else:
                        thumb = to_proxy_url(scene_imgs[first_key].get("url"))
        job["thumbnail_url"] = thumb
        job.pop("scene_images", None)
        text = job.get("story_text", "")
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]
        job["hook_text"] = (sentences[0] + "...") if sentences else job.get("title", "")
        job.pop("story_text", None)
        stories.append(job)

    # Category counts
    counts = {"all": await db.pipeline_jobs.count_documents(base_q)}
    counts["kids"] = await db.pipeline_jobs.count_documents({**base_q, "age_group": {"$regex": "kids|toddler|child", "$options": "i"}})
    for cat, pat in _CAT_PATTERNS.items():
        if cat != "kids" and pat:
            counts[cat] = await db.pipeline_jobs.count_documents({**base_q, "title": {"$regex": pat, "$options": "i"}})

    return {
        "stories": stories,
        "next_cursor": cursor + limit if cursor + limit < total else None,
        "total": total,
        "categories": counts,
    }
