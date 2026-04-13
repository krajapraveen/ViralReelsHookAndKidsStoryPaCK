"""
Engagement System Routes — Daily Challenges, Streaks, Creator Levels, Trending
"""
import os
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

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


def _to_cdn(url: str) -> str | None:
    """Return the R2 proxy path. CDN URLs are resolved on the frontend
    to avoid K8s ingress Cache-Control override while keeping compatibility."""
    key = _to_r2_key(url)
    return f"/api/media/r2/{key}" if key else None


def _resolve_media(job: dict) -> tuple:
    """Resolve thumbnail_small and poster_large from the strict media schema.
    Falls back to legacy flat fields ONLY for pre-migration jobs.
    Returns DIRECT R2 CDN URLs (bypasses K8s ingress Cache-Control override)."""
    media = job.get("media") or {}
    thumb_raw = (media.get("thumbnail_small") or {}).get("url")
    poster_raw = (media.get("poster_large") or {}).get("url")

    if thumb_raw and poster_raw:
        return _to_cdn(thumb_raw), _to_cdn(poster_raw)

    thumb_raw = thumb_raw or job.get("thumbnail_small_url") or job.get("thumbnail_url")
    poster_raw = poster_raw or job.get("thumbnail_url") or job.get("thumbnail_small_url")

    if not thumb_raw:
        si = job.get("scene_images") or {}
        if si:
            fk = sorted(si.keys(), key=lambda k: int(k) if k.isdigit() else 999)[0] if si else None
            if fk and isinstance(si[fk], dict):
                thumb_raw = si[fk].get("url")

    return _to_cdn(thumb_raw), _to_cdn(poster_raw or thumb_raw)


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
    """Shape a raw DB document into a standard feed item.
    Includes hook A/B data for personalized hook serving.
    URLs are DIRECT R2 CDN (bypass K8s ingress)."""
    card_thumb, poster = _resolve_media(job)
    preview = _to_cdn(job.get("preview_url"))

    jid = job.get("job_id")

    # Resolve thumb_blur from strict media schema
    media_obj = job.get("media") or {}
    thumb_blur = media_obj.get("thumb_blur")

    # Hook system: use stored hook_text, fallback to extracted hook from story_text
    hooks = job.get("hooks") or []
    hook_text = job.get("hook_text") or _extract_hook(job.get("story_text", ""))
    hook_locked = job.get("hook_locked", False)
    winning_hook = job.get("winning_hook")

    # Compute hook_strength for ranking
    hook_strength = 0.0
    if hooks:
        from services.hook_service import compute_hook_strength
        hook_strength = compute_hook_strength(hooks, hook_locked, winning_hook)

    return {
        "id": jid,
        "job_id": jid,
        "title": job.get("title", "Untitled"),
        "hook_text": hook_text,
        "story_prompt": job.get("story_text", ""),
        "media": {
            "thumb_blur": thumb_blur,
            "thumbnail_small_url": card_thumb,
            "poster_large_url": poster,
            "preview_short_url": preview,
            "media_version": "v3",
        },
        "output_url": _to_cdn(job.get("output_url")),
        "animation_style": job.get("animation_style", ""),
        "parent_video_id": job.get("parent_video_id"),
        "badge": badge,
        "created_at": job.get("created_at", ""),
        "character_summary": _extract_char_summary(job),
        "source": job.get("_source", "story_engine"),  # track collection origin
        "total_views": job.get("total_views", 0) or job.get("view_count", 0) or 0,
        "total_children": job.get("total_children", 0) or job.get("remix_count", 0) or 0,
        # Hook A/B internals (used by ranking, stripped before response)
        "_hooks": hooks,
        "_hook_locked": hook_locked,
        "_winning_hook": winning_hook,
        "hook_strength": hook_strength,
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
        # Hook A/B fields
        "hooks": 1, "hook_text": 1, "hook_locked": 1, "winning_hook": 1,
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
    # Tag pipeline_jobs source for downstream routing
    for pj in pj_all:
        pj["_source"] = "pipeline"

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
    # REGRESSION GUARD: If personalization scoring crashes, fall back to default ordering
    try:
        if personalized:
            trending_ranked = rank_stories(trending_pool, profile)
            fresh_ranked = rank_stories(fresh_pool, profile)
            continue_ranked = rank_stories(continue_pool, profile) if continue_pool else []
            unfinished_ranked = rank_stories(unfinished_pool, profile)
        else:
            trending_ranked = trending_pool
            fresh_ranked = fresh_pool
            continue_ranked = continue_pool
            unfinished_ranked = unfinished_pool
    except Exception as e:
        logger.error(f"[FEED] Personalization ranking failed, falling back to defaults: {e}")
        personalized = False
        trending_ranked = trending_pool
        fresh_ranked = fresh_pool
        continue_ranked = continue_pool
        unfinished_ranked = unfinished_pool

    # ── RANK rows ──
    try:
        row_candidates = {
            "continue_stories": continue_ranked,
            "trending_stories": trending_ranked,
            "fresh_stories": fresh_ranked,
            "unfinished_worlds": unfinished_ranked,
        }
        rows = rank_rows(row_candidates, profile)
    except Exception as e:
        logger.error(f"[FEED] Row ranking failed, building default rows: {e}")
        rows = []
        if continue_ranked:
            rows.append({"key": "continue_stories", "title": "Continue Your Story", "icon": "RefreshCw", "icon_color": "text-blue-400", "stories": continue_ranked})
        if trending_ranked:
            rows.append({"key": "trending_now", "title": "Trending Now", "icon": "Flame", "icon_color": "text-amber-400", "stories": trending_ranked})
        if fresh_ranked:
            rows.append({"key": "fresh_stories", "title": "Fresh Stories", "icon": "Sparkles", "icon_color": "text-violet-400", "stories": fresh_ranked})
        if unfinished_ranked:
            rows.append({"key": "unfinished_worlds", "title": "Unfinished Worlds", "icon": "Clock", "icon_color": "text-emerald-400", "stories": unfinished_ranked})

    # Strip internal fields + serve correct hook variant per user
    # REGRESSION GUARD: If hook serving crashes, still return clean stories
    try:
        from services.hook_service import select_hook_for_user

        def _clean_story(s):
            """Strip internals and serve the right hook via A/B."""
            hooks = s.pop("_hooks", [])
            hook_locked = s.pop("_hook_locked", False)
            winning_hook_id = s.pop("_winning_hook", None)
            s.pop("_score", None)
            s.pop("hook_strength", None)
            if hooks:
                selected = select_hook_for_user(hooks, hook_locked, winning_hook_id)
                if selected:
                    s["hook_text"] = selected["text"]
                    s["hook_variant_id"] = selected["id"]
    except Exception as e:
        logger.error(f"[FEED] Hook service import failed: {e}")
        def _clean_story(s):
            s.pop("_hooks", None)
            s.pop("_hook_locked", None)
            s.pop("_winning_hook", None)
            s.pop("_score", None)
            s.pop("hook_strength", None)

    for row in rows:
        for s in row.get("stories", []):
            _clean_story(s)

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
        _clean_story(hero)
        hero["badge"] = "FEATURED"

    # ── RANK features ──
    # REGRESSION GUARD: if feature ranking fails, return default-ordered features
    try:
        features = rank_features(profile) if personalized else rank_features(_empty_profile("anonymous"))
    except Exception as e:
        logger.error(f"[FEED] Feature ranking failed, using defaults: {e}")
        features = rank_features(_empty_profile("anonymous"))

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
        "cdn_base": os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", ""),
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


# ─── PREVIEW AUTOPLAY EVENT TRACKING ────────────────────────────────────
class PreviewEvent(BaseModel):
    job_id: str
    event_type: str  # "preview_impression", "preview_play", "preview_watch_complete", "preview_click"
    watch_time: Optional[float] = None
    surface: Optional[str] = None  # "hero", "card"
    timestamp: Optional[str] = None


@router.post("/preview-event")
async def track_preview_event(data: PreviewEvent, user: dict = Depends(get_optional_user)):
    """Track autoplay preview analytics for engagement optimization."""
    user_id = None
    if user:
        user_id = user.get("id") or str(user.get("_id", ""))

    await db.preview_events.insert_one({
        "job_id": data.job_id,
        "event_type": data.event_type,
        "user_id": user_id,
        "watch_time": data.watch_time,
        "surface": data.surface,
        "timestamp": data.timestamp or datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True}


# ─── REAL-TIME FEED EVENT (SESSION MOMENTUM + PROFILE UPDATE) ───────────

class FeedEvent(BaseModel):
    event_type: str  # click, skip_fast, preview_play, hook_seen, continue_click, watch_complete
    job_id: Optional[str] = None
    category: Optional[str] = None
    hook_text: Optional[str] = None
    watch_time: Optional[float] = None
    scroll_depth: Optional[int] = None


@router.post("/feed-event")
async def track_feed_event(data: FeedEvent, user: dict = Depends(get_optional_user)):
    """Real-time feed engagement tracker. Updates session momentum + profile.
    Returns session state so frontend knows when to request re-rank."""
    from services.personalization_service import update_profile_on_event, needs_recovery, get_session_intensity

    user_id = None
    if user:
        user_id = user.get("id") or str(user.get("_id", ""))

    meta = {
        "story_id": data.job_id,
        "category": data.category or "",
        "animation_style": data.category or "",
        "hook_text": data.hook_text,
    }

    session = None
    if user_id:
        session = await update_profile_on_event(db, user_id, data.event_type, meta)

    # Return session hints for frontend
    should_rerank = False
    recovery_needed = False
    if session:
        should_rerank = (session.get("session_actions", 0) % 5 == 0) and session.get("session_actions", 0) > 0
        profile = await db.user_homepage_profile.find_one({"user_id": user_id}, {"_id": 0})
        recovery_needed = needs_recovery(profile or {})

    return {
        "success": True,
        "session": {
            "momentum": session.get("momentum_score", 0.0) if session else 0.0,
            "actions": session.get("session_actions", 0) if session else 0,
            "consecutive_skips": session.get("consecutive_skips", 0) if session else 0,
            "should_rerank": should_rerank,
            "recovery_needed": recovery_needed,
            "intensity": get_session_intensity({"session": session}) if session else "low",
        },
    }


# ─── INFINITE SCROLL: MORE STORIES ──────────────────────────────────────

@router.get("/story-feed/more")
async def get_more_stories(
    offset: int = 0,
    limit: int = 12,
    user: dict = Depends(get_optional_user),
):
    """Load more stories for infinite scroll. Session-aware ranking with
    variable reward injection and recovery system."""
    from services.personalization_service import (
        get_or_create_profile, is_personalized, rank_stories,
        inject_variable_rewards, apply_recovery, needs_recovery,
        get_session_intensity, _empty_profile,
    )

    user_id = None
    if user:
        user_id = user.get("id") or str(user.get("_id", ""))
    profile = await get_or_create_profile(db, user_id) if user_id else _empty_profile("anonymous")
    personalized = is_personalized(profile)

    PROJ = {
        "_id": 0, "job_id": 1, "title": 1, "story_text": 1,
        "output_url": 1, "preview_url": 1,
        "remix_count": 1, "animation_style": 1, "created_at": 1,
        "parent_video_id": 1, "user_id": 1,
        "character_continuity": 1, "media": 1,
        "thumbnail_url": 1, "thumbnail_small_url": 1, "scene_images": 1,
        "hooks": 1, "hook_text": 1, "hook_locked": 1, "winning_hook": 1,
    }

    # Fetch more stories beyond the initial load
    se_more = await db.story_engine_jobs.find(
        {"state": "READY"}, PROJ,
    ).sort("created_at", -1).skip(offset).to_list(length=limit + 10)

    pj_more = await db.pipeline_jobs.find(
        {"status": "COMPLETED"}, PROJ,
    ).sort([("remix_count", -1), ("created_at", -1)]).skip(offset).to_list(length=limit + 10)

    items = []
    seen_ids = set()
    for job in se_more + pj_more:
        shaped = _shape_item(job, "DISCOVER")
        if _has_displayable_media(shaped) and shaped.get("job_id") not in seen_ids:
            seen_ids.add(shaped.get("job_id"))
            items.append(shaped)

    # Score and rank
    try:
        if personalized:
            items = rank_stories(items, profile)
    except Exception as e:
        logger.error(f"[FEED-MORE] Ranking failed: {e}")

    # Recovery: if user has been skipping, inject different content
    if needs_recovery(profile):
        items = apply_recovery(items, profile)
    else:
        # Variable reward injection: spike high-score items at random intervals
        items = inject_variable_rewards(items, profile)

    # Limit
    items = items[:limit]

    # Clean hook internals + serve A/B variant
    try:
        from services.hook_service import select_hook_for_user
        for s in items:
            hooks = s.pop("_hooks", [])
            hook_locked = s.pop("_hook_locked", False)
            winning_hook_id = s.pop("_winning_hook", None)
            s.pop("_score", None)
            s.pop("hook_strength", None)
            if hooks:
                selected = select_hook_for_user(hooks, hook_locked, winning_hook_id)
                if selected:
                    s["hook_text"] = selected["text"]
                    s["hook_variant_id"] = selected["id"]
    except Exception:
        for s in items:
            for k in ("_hooks", "_hook_locked", "_winning_hook", "_score", "hook_strength"):
                s.pop(k, None)

    has_more = len(se_more) + len(pj_more) > limit

    return {
        "stories": items,
        "offset": offset + len(items),
        "has_more": has_more,
        "session_intensity": get_session_intensity(profile) if personalized else "low",
        "cdn_base": os.environ.get("CLOUDFLARE_R2_PUBLIC_URL", ""),
    }


# ─── HOOK A/B EVENT TRACKING ────────────────────────────────────────────


class HookEvent(BaseModel):
    job_id: str
    hook_variant_id: str
    event_type: str  # "impression", "continue", "share", "completion"


@router.post("/hook-event")
async def track_hook_event(data: HookEvent):
    """
    Track hook A/B events. Updates hook metrics in story_engine_jobs.
    Checks lock condition and triggers evolution if needed.
    """
    from services.hook_service import (
        check_lock_condition, check_evolution_needed, get_evolution_targets,
        evolve_hook_from_best,
    )

    job = await db.story_engine_jobs.find_one(
        {"job_id": data.job_id},
        {"_id": 0, "hooks": 1, "hook_locked": 1, "winning_hook": 1, "story_text": 1, "title": 1},
    )
    if not job or not job.get("hooks"):
        return {"success": False, "error": "Job or hooks not found"}

    if job.get("hook_locked"):
        return {"success": True, "locked": True}

    hooks = job["hooks"]
    target = None
    for h in hooks:
        if h["id"] == data.hook_variant_id:
            target = h
            break

    if not target:
        return {"success": False, "error": "Hook variant not found"}

    # Increment the right counter
    field_map = {
        "impression": "impressions",
        "continue": "continues",
        "share": "shares",
        "completion": "completions",
    }
    counter = field_map.get(data.event_type)
    if counter:
        target[counter] = target.get(counter, 0) + 1

    update_set = {"hooks": hooks}

    # Check lock condition: ≥300 impressions + ≥15% margin
    should_lock, winner_id = check_lock_condition(hooks)
    if should_lock:
        update_set["hook_locked"] = True
        update_set["winning_hook"] = winner_id
        winner_hook = next((h for h in hooks if h["id"] == winner_id), None)
        if winner_hook:
            update_set["hook_text"] = winner_hook["text"]

    # Check evolution: every 100 impressions, drop worst, rewrite from best
    if not should_lock and check_evolution_needed(hooks):
        worst, best = get_evolution_targets(hooks)
        if worst and best and worst["id"] != best["id"]:
            new_text = await evolve_hook_from_best(
                best["text"],
                job.get("story_text", ""),
                job.get("title", ""),
            )
            # Replace worst hook with evolved variant
            for h in hooks:
                if h["id"] == worst["id"]:
                    h["text"] = new_text
                    h["impressions"] = 0
                    h["continues"] = 0
                    h["shares"] = 0
                    h["completions"] = 0
                    break
            update_set["hooks"] = hooks

    await db.story_engine_jobs.update_one(
        {"job_id": data.job_id},
        {"$set": update_set},
    )

    return {"success": True, "locked": should_lock, "evolved": check_evolution_needed(hooks)}


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
        # Only include stories with a resolved thumbnail (no blank cards)
        if thumb:
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
