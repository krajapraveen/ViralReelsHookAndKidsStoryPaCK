"""
Engagement System Routes — Daily Challenges, Streaks, Creator Levels, Trending
"""
import os
import random
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request

from shared import db, get_current_user, get_optional_user

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

    # Award credits via Credits Service
    reward = challenge["reward"]
    from services.credits_service import get_credits_service
    svc = get_credits_service(db)
    result = await svc.award_credits(user_id, reward, reason=f"Daily challenge: {challenge['challenge_id']}")
    await db.challenge_completions.insert_one({
        "user_id": user_id,
        "challenge_id": challenge["challenge_id"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "reward": reward,
    })

    return {"success": True, "reward": reward, "new_balance": result["new_balance"]}


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
        from services.credits_service import get_credits_service
        svc = get_credits_service(db)
        await svc.award_credits(user_id, milestone_reward, reason=f"Streak milestone: {new_streak} days")

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


# ═══════════════════════════════════════════════════════════════
# DETERMINISTIC MEDIA RESOLUTION — Module-level helpers
# Pipeline generates → DB stores → API returns → Frontend renders
# ═══════════════════════════════════════════════════════════════

def _to_r2_key(url: str) -> str | None:
    """Extract the R2 object key from any stored URL format."""
    if not url:
        return None
    try:
        base = url.split("?")[0]
        if ".r2.dev/" in base:
            return base.split(".r2.dev/", 1)[1]
        if ".r2.cloudflarestorage.com/" in base:
            parts = base.split(".r2.cloudflarestorage.com/", 1)
            if len(parts) > 1:
                bk = parts[1].split("/", 1)
                if len(bk) > 1:
                    return bk[1]
        if url.startswith("/api/media/r2/"):
            return url[len("/api/media/r2/"):]
        if not url.startswith("http") and not url.startswith("/"):
            return url
        return None
    except Exception:
        return None


def _to_proxy(url: str) -> str | None:
    """Convert any R2/CDN URL to same-origin proxy path for Safari safety."""
    key = _to_r2_key(url)
    return f"/api/media/r2/{key}" if key else None


def _resolve_media(job: dict) -> tuple:
    """Resolve thumbnail_small and poster_large from the strict media schema.
    Falls back to legacy flat fields ONLY for pre-migration jobs."""
    media = job.get("media") or {}
    thumb_raw = (media.get("thumbnail_small") or {}).get("url")
    poster_raw = (media.get("poster_large") or {}).get("url")

    if thumb_raw and poster_raw:
        return _to_proxy(thumb_raw), _to_proxy(poster_raw)

    thumb_raw = thumb_raw or job.get("thumbnail_small_url") or job.get("thumbnail_url")
    poster_raw = poster_raw or job.get("thumbnail_url") or job.get("thumbnail_small_url")

    if not thumb_raw:
        si = job.get("scene_images") or {}
        if si:
            fk = sorted(si.keys(), key=lambda k: int(k) if k.isdigit() else 999)[0] if si else None
            if fk and isinstance(si[fk], dict):
                thumb_raw = si[fk].get("url")

    return _to_proxy(thumb_raw), _to_proxy(poster_raw or thumb_raw)


def _has_displayable_media(item: dict) -> bool:
    """Returns True if the feed item has at least one displayable image."""
    media = item.get("media") or {}
    return bool(media.get("thumbnail_small_url") or media.get("poster_large_url"))


def _extract_hook(text: str) -> str:
    sentences = [s.strip() for s in (text or "").replace("\n", ". ").split(".") if s.strip() and len(s.strip()) > 5]
    return (sentences[0] + "...") if sentences else ""


def _extract_char_summary(job: dict) -> dict | None:
    cc = job.get("character_continuity") or {}
    chars = cc.get("characters", [])
    if chars and isinstance(chars, list) and len(chars) > 0:
        c = chars[0]
        return {"name": c.get("name"), "role": c.get("role")}
    return None


def _shape_item(job: dict, badge: str = "NEW") -> dict:
    """Shape a raw DB document into a standard feed item."""
    card_thumb, poster = _resolve_media(job)
    preview = _to_proxy(job.get("preview_url"))

    jid = job.get("job_id")
    return {
        "id": jid,
        "job_id": jid,
        "title": job.get("title", "Untitled"),
        "hook_text": _extract_hook(job.get("story_text", "")),
        "story_prompt": job.get("story_text", ""),
        "media": {
            "thumb_blur": None,
            "thumbnail_small_url": card_thumb,
            "poster_large_url": poster,
            "preview_short_url": preview,
            "media_version": "v3",
        },
        "output_url": _to_proxy(job.get("output_url")),
        "animation_style": job.get("animation_style", ""),
        "parent_video_id": job.get("parent_video_id"),
        "badge": badge,
        "created_at": job.get("created_at", ""),
        "character_summary": _extract_char_summary(job),
    }


# ─── GET /api/engagement/story-feed ──────────────────────────────────────
@router.get("/story-feed")
async def get_story_feed(user: dict = Depends(get_optional_user)):
    """Return personalized, pre-ranked homepage data.
    Backend owns ALL ordering — frontend is a dumb renderer.

    Response contract:
    {
      personalization: { enabled, profile_strength, event_count },
      hero: { ...story },
      rows: [ { key, title, icon, icon_color, stories: [...] }, ... ],
      features: [ { name, desc, icon, path, key, gradient, score }, ... ],
      live_stats: { stories_today, total_stories },
    }
    """
    from services.personalization_service import (
        get_or_create_profile, is_personalized, profile_strength as calc_strength,
        rank_stories, rank_rows, rank_features, select_hero, _empty_profile,
    )

    PROJ = {
        "_id": 0, "job_id": 1, "title": 1, "story_text": 1,
        "output_url": 1, "preview_url": 1,
        "remix_count": 1, "animation_style": 1, "created_at": 1,
        "parent_video_id": 1, "user_id": 1,
        "character_continuity": 1,
        "media": 1,
        "thumbnail_url": 1, "thumbnail_small_url": 1,
        "scene_images": 1,
    }

    # ── Fetch user profile (or cold-start empty) ──
    user_id = None
    if user:
        user_id = user.get("id") or str(user.get("_id", ""))
    profile = await get_or_create_profile(db, user_id) if user_id else _empty_profile("anonymous")
    personalized = is_personalized(profile)

    # ── Query stories from both collections ──
    se_all = await db.story_engine_jobs.find(
        {"state": "READY"},
        {**PROJ, "state": 1},
    ).sort("created_at", -1).to_list(length=30)

    pj_all = await db.pipeline_jobs.find(
        {"status": "COMPLETED"},
        PROJ,
    ).sort([("remix_count", -1), ("created_at", -1)]).to_list(length=40)

    # ── Shape all items ──
    def _shape_all(jobs, badge="NEW"):
        items = []
        for job in jobs:
            shaped = _shape_item(job, badge)
            if _has_displayable_media(shaped):
                items.append(shaped)
        return items

    all_se_items = _shape_all(se_all, "NEW")
    all_pj_items = _shape_all(pj_all, "TRENDING")

    # ── Build candidate pools ──
    seen_ids = set()
    trending_pool = []
    for item in all_se_items:
        trending_pool.append(item)
        seen_ids.add(item.get("job_id"))
    for item in all_pj_items:
        if item.get("job_id") not in seen_ids:
            trending_pool.append(item)

    # Fresh: sorted by created_at (normalize to str for mixed types)
    fresh_pool = sorted(
        [i for i in (all_se_items + all_pj_items)],
        key=lambda x: str(x.get("created_at", "")),
        reverse=True,
    )
    # Dedupe fresh
    fresh_seen = set()
    fresh_deduped = []
    for i in fresh_pool:
        jid = i.get("job_id")
        if jid not in fresh_seen:
            fresh_seen.add(jid)
            fresh_deduped.append({**i, "badge": "FRESH"})
    fresh_pool = fresh_deduped[:20]

    # Continue: user's own jobs
    continue_pool = []
    if user_id:
        user_se = await db.story_engine_jobs.find(
            {"user_id": user_id, "state": {"$in": ["READY", "PARTIAL_READY"]}},
            {**PROJ, "state": 1},
        ).sort("created_at", -1).to_list(length=10)
        for j in user_se:
            shaped = _shape_item(j, "CONTINUE")
            if _has_displayable_media(shaped):
                continue_pool.append(shaped)
        user_pj = await db.pipeline_jobs.find(
            {"user_id": user_id, "status": "COMPLETED"},
            PROJ,
        ).sort("created_at", -1).to_list(length=10)
        cont_seen = {j.get("job_id") for j in user_se}
        for j in user_pj:
            if j.get("job_id") not in cont_seen:
                shaped = _shape_item(j, "CONTINUE")
                if _has_displayable_media(shaped):
                    continue_pool.append(shaped)

    # Unfinished worlds
    partial_pj = await db.pipeline_jobs.find(
        {"status": "COMPLETED", "parent_video_id": {"$exists": False}},
        PROJ,
    ).sort("created_at", -1).to_list(length=12)
    unfinished_pool = [item for j in partial_pj if _has_displayable_media(item := _shape_item(j, "UNFINISHED"))]

    # ── RANK stories inside each pool ──
    if personalized:
        trending_ranked = rank_stories(trending_pool, profile)
        fresh_ranked = rank_stories(fresh_pool, profile)
        continue_ranked = rank_stories(continue_pool, profile) if continue_pool else []
        unfinished_ranked = rank_stories(unfinished_pool, profile)
    else:
        # Cold start: use default ordering (already sorted by DB query)
        trending_ranked = trending_pool
        fresh_ranked = fresh_pool
        continue_ranked = continue_pool
        unfinished_ranked = unfinished_pool

    # ── RANK rows ──
    row_candidates = {
        "continue_stories": continue_ranked,
        "trending_stories": trending_ranked,
        "fresh_stories": fresh_ranked,
        "unfinished_worlds": unfinished_ranked,
    }
    rows = rank_rows(row_candidates, profile)

    # Strip internal _score from story objects before response
    for row in rows:
        for s in row.get("stories", []):
            s.pop("_score", None)

    # ── SELECT hero ──
    hero_candidates = trending_ranked + fresh_ranked
    hero = select_hero(hero_candidates, profile) if personalized else None
    if not hero and hero_candidates:
        # Cold start: pick first with media
        for c in hero_candidates:
            media = c.get("media") or {}
            if media.get("thumbnail_small_url") or media.get("poster_large_url"):
                hero = c
                break
        if not hero:
            hero = hero_candidates[0] if hero_candidates else None
    if hero:
        hero.pop("_score", None)
        hero["badge"] = "FEATURED"

    # ── RANK features ──
    features = rank_features(profile) if personalized else rank_features(_empty_profile("anonymous"))

    # ── Characters (unchanged) ──
    char_profiles = await db.character_profiles.find(
        {},
        {"_id": 0, "character_id": 1, "name": 1, "species": 1, "personality": 1, "portrait_url": 1, "role": 1},
    ).to_list(length=6)
    characters = []
    seen_names = set()
    for c in char_profiles:
        name = c.get("name", "")
        if name and name not in seen_names:
            seen_names.add(name)
            characters.append({
                "character_id": c.get("character_id"),
                "name": name,
                "description": c.get("personality") or c.get("species") or c.get("role", ""),
                "image_url": c.get("portrait_url"),
            })

    # ── Live stats ──
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    se_today = await db.story_engine_jobs.count_documents({"created_at": {"$gte": today_start.isoformat()}})
    pj_today = await db.pipeline_jobs.count_documents({"created_at": {"$gte": today_start.isoformat()}})
    se_total = await db.story_engine_jobs.count_documents({"state": "READY"})
    pj_total = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})

    return {
        "personalization": {
            "enabled": personalized,
            "profile_strength": calc_strength(profile),
            "event_count": profile.get("counts", {}).get("total_events", 0),
        },
        "hero": hero,
        "rows": rows,
        "features": features,
        "characters": characters[:6],
        "live_stats": {
            "stories_today": se_today + pj_today,
            "total_stories": se_total + pj_total,
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
