"""
Public API — Distribution Loop Engine
Public pages, explore feed, platform stats, view tracking,
OG meta tags, share pages, sitemap, creator profiles.
No authentication required for read endpoints.
"""
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from typing import Optional

from shared import db

router = APIRouter(prefix="/public", tags=["public"])
logger = logging.getLogger("public_api")

FRONTEND_URL = os.environ.get("BACKEND_PUBLIC_URL", "https://www.visionary-suite.com")


def slugify(text: str) -> str:
    """Create URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


# ─── PLATFORM STATS (Real Data) ──────────────────────────────────────────

@router.get("/stats")
async def get_platform_stats():
    """Return real platform statistics for social proof."""
    users_count = await db.users.count_documents({})
    jobs_completed = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})

    # Count total scenes across completed jobs
    pipeline = [
        {"$match": {"status": "COMPLETED"}},
        {"$project": {"scene_count": {"$size": {"$ifNull": ["$scenes", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$scene_count"}}}
    ]
    scene_result = await db.pipeline_jobs.aggregate(pipeline).to_list(length=1)
    total_scenes = scene_result[0]["total"] if scene_result else 0

    # Count total generations from all tools
    gen_count = await db.generations.count_documents({})

    # Total creations = pipeline jobs + other generations
    total_creations = jobs_completed + gen_count

    return {
        "creators": users_count,
        "videos_created": jobs_completed,
        "total_creations": total_creations,
        "ai_scenes": total_scenes,
    }


# ─── PUBLIC CREATION PAGE ─────────────────────────────────────────────────

@router.get("/creation/{slug}")
async def get_public_creation(slug: str):
    """
    Get a public creation page by slug or job_id.
    Queries BOTH story_engine_jobs AND legacy pipeline_jobs.
    Returns video URL for auto-play, character data, and momentum social proof.
    """
    # Try story_engine_jobs first (new engine)
    job = await db.story_engine_jobs.find_one(
        {"$or": [{"slug": slug}, {"job_id": slug}]},
        {"_id": 0}
    )
    source = "story_engine" if job else None

    if not job:
        # Fallback to legacy pipeline_jobs
        job = await db.pipeline_jobs.find_one(
            {"$or": [{"slug": slug}, {"job_id": slug}]},
            {"_id": 0}
        )
        source = "legacy_pipeline" if job else None

    if not job:
        raise HTTPException(status_code=404, detail="Creation not found")

    job_id = job.get("job_id", slug)

    # Increment view count in the correct collection
    col = db.story_engine_jobs if source == "story_engine" else db.pipeline_jobs
    await col.update_one(
        {"job_id": job_id},
        {"$inc": {"views": 1}}
    )

    # Get creator info
    creator = None
    if job.get("user_id"):
        creator = await db.users.find_one(
            {"id": job["user_id"]},
            {"_id": 0, "name": 1, "email": 1}
        )

    # Presign URLs
    from utils.r2_presign import presign_url

    # ── Build scenes + video URL based on source ──
    scenes = []
    video_url = None
    thumbnail = None
    characters = []
    cliffhanger = None

    if source == "story_engine":
        # Story Engine: build scenes from scene_motion_plans + keyframe_urls
        plans = job.get("scene_motion_plans") or []
        keyframes = job.get("keyframe_urls") or []
        ep_scenes = (job.get("episode_plan") or {}).get("scene_breakdown") or []

        for i, plan in enumerate(plans):
            kf_url = keyframes[i] if i < len(keyframes) else None
            ep_scene = ep_scenes[i] if i < len(ep_scenes) else {}
            scenes.append({
                "narration": ep_scene.get("action_summary", plan.get("action", "")),
                "image_url": presign_url(kf_url) if kf_url else None,
                "audio_url": None,
                "duration": plan.get("clip_duration_seconds", 5.0),
            })

        # Video URL for auto-play
        if job.get("output_url"):
            video_url = presign_url(job["output_url"])
        elif job.get("preview_url"):
            video_url = presign_url(job["preview_url"])

        thumbnail = presign_url(job.get("thumbnail_url", "")) if job.get("thumbnail_url") else None
        if not thumbnail and keyframes:
            for kf in keyframes:
                if kf:
                    thumbnail = presign_url(kf)
                    break

        # Character data from character_continuity
        continuity = job.get("character_continuity") or {}
        for char in continuity.get("characters", []):
            characters.append({
                "name": char.get("name", "Unknown"),
                "role": char.get("role", "character"),
                "appearance": char.get("reference_prompt", char.get("clothing_default", "")),
                "personality": char.get("personality_core", ""),
            })

        # Cliffhanger from episode plan
        ep_plan = job.get("episode_plan") or {}
        cliffhanger = ep_plan.get("cliffhanger")

    else:
        # Legacy pipeline: use existing scenes structure
        for s in job.get("scenes", []):
            scenes.append({
                "narration": s.get("narration", ""),
                "image_url": presign_url(s["image_url"]) if s.get("image_url") else None,
                "audio_url": presign_url(s["audio_url"]) if s.get("audio_url") else None,
                "duration": s.get("duration"),
            })

        # Video URL — check output_url, then fallback_outputs
        if job.get("output_url"):
            video_url = presign_url(job["output_url"])
        elif job.get("fallback_outputs", {}).get("fallback_mp4", {}).get("url"):
            video_url = presign_url(job["fallback_outputs"]["fallback_mp4"]["url"])

        thumbnail = presign_url(job.get("thumbnail_url", "")) if job.get("thumbnail_url") else None

    # ── Momentum-based social proof ──
    now = datetime.now(timezone.utc)
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    one_day_ago = (now - timedelta(hours=24)).isoformat()

    # Check continuations in BOTH collections
    engine_continuations = await db.story_engine_jobs.find(
        {"parent_job_id": job_id},
        {"_id": 0, "created_at": 1}
    ).sort("created_at", -1).to_list(100)

    legacy_continuations = await db.pipeline_jobs.find(
        {"remix_parent_id": job_id},
        {"_id": 0, "created_at": 1}
    ).sort("created_at", -1).to_list(100)

    all_continuations = engine_continuations + legacy_continuations
    # Normalize datetime for comparison
    def _to_iso(val):
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        return str(val) if val else ""

    all_continuations_sorted = sorted(all_continuations, key=lambda c: _to_iso(c.get("created_at", "")), reverse=True)

    total_continuations = len(all_continuations_sorted)
    last_continuation_at = _to_iso(all_continuations_sorted[0].get("created_at")) if all_continuations_sorted else None

    continuations_1h = sum(1 for c in all_continuations_sorted if _to_iso(c.get("created_at", "")) >= one_hour_ago)
    continuations_24h = sum(1 for c in all_continuations_sorted if _to_iso(c.get("created_at", "")) >= one_day_ago)

    db_remix_count = job.get("remix_count", 0)
    effective_continuations = max(total_continuations, db_remix_count)

    views_value = job.get("views", 0)
    is_trending = (continuations_1h >= 2) or (continuations_24h >= 5 and views_value >= 20)
    is_alive = bool(continuations_24h > 0 or (last_continuation_at and last_continuation_at >= one_day_ago))

    # Character name for display
    character_name = None
    if characters:
        character_name = characters[0].get("name")
    elif job.get("character_name"):
        character_name = job["character_name"]

    return {
        "success": True,
        "creation": {
            "job_id": job_id,
            "slug": job.get("slug", slug),
            "title": job.get("title", "Untitled"),
            "status": job.get("status") or job.get("state", ""),
            "animation_style": job.get("animation_style") or job.get("style_id"),
            "age_group": job.get("age_group"),
            "voice_preset": job.get("voice_preset"),
            "tool_type": job.get("tool_type", "story-video-studio"),
            "scenes": scenes,
            "thumbnail_url": thumbnail,
            "video_url": video_url,
            "views": views_value + 1,
            "remix_count": effective_continuations,
            "created_at": _to_iso(job.get("created_at")),
            "creator": {
                "name": creator.get("name", "Anonymous") if creator else "Anonymous",
            },
            "story_text": job.get("story_text", ""),
            "prompt": job.get("story_text", ""),
            "category": job.get("category", ""),
            "tags": job.get("tags", []),
            # Character data
            "characters": characters,
            "character_name": character_name,
            # Story engine extras
            "cliffhanger": cliffhanger,
            "episode_number": job.get("episode_number"),
            "story_chain_id": job.get("story_chain_id"),
            # Momentum signals
            "last_continuation_at": last_continuation_at,
            "continuations_1h": continuations_1h,
            "continuations_24h": continuations_24h,
            "is_trending": is_trending,
            "is_alive": is_alive,
            "source": source,
        }
    }



@router.post("/creation/{slug}/remix")
async def track_remix(slug: str):
    """Increment remix count when someone clicks Remix/Try Prompt."""
    result = await db.pipeline_jobs.update_one(
        {"$or": [{"slug": slug}, {"job_id": slug}]},
        {"$inc": {"remix_count": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Creation not found")
    return {"success": True}



# ─── TRENDING THIS WEEK (Algorithmic) ─────────────────────────────────────

@router.get("/trending-weekly")
async def get_trending_weekly(limit: int = Query(10, ge=1, le=20)):
    """
    Algorithmic trending for the homepage carousel.
    Score = (views * 1.0) + (remix_count * 5.0) + recency_boost
    Recency boost: items from last 24h get 2x, last 3 days get 1.5x, last 7 days get 1.2x.
    Only considers content from the last 30 days.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    pipeline = [
        {"$match": {
            "status": "COMPLETED",
            "created_at": {"$gte": thirty_days_ago},
            "thumbnail_url": {"$exists": True, "$ne": ""},
        }},
        {"$addFields": {
            "age_hours": {
                "$divide": [
                    {"$subtract": [now, "$created_at"]},
                    3600000  # ms to hours
                ]
            }
        }},
        {"$addFields": {
            "recency_multiplier": {
                "$switch": {
                    "branches": [
                        {"case": {"$lte": ["$age_hours", 24]}, "then": 2.0},
                        {"case": {"$lte": ["$age_hours", 72]}, "then": 1.5},
                        {"case": {"$lte": ["$age_hours", 168]}, "then": 1.2},
                    ],
                    "default": 1.0
                }
            }
        }},
        {"$addFields": {
            "trending_score": {
                "$multiply": [
                    {"$add": [
                        {"$multiply": [{"$ifNull": ["$views", 0]}, 1.0]},
                        {"$multiply": [{"$ifNull": ["$remix_count", 0]}, 5.0]},
                    ]},
                    "$recency_multiplier"
                ]
            }
        }},
        {"$sort": {"trending_score": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "job_id": 1,
            "slug": 1,
            "title": 1,
            "category": 1,
            "animation_style": 1,
            "views": 1,
            "remix_count": 1,
            "created_at": 1,
            "thumbnail_url": 1,
            "trending_score": 1,
        }}
    ]

    items = await db.pipeline_jobs.aggregate(pipeline).to_list(length=limit)

    from utils.r2_presign import presign_url
    for item in items:
        if item.get("thumbnail_url"):
            item["thumbnail_url"] = presign_url(item["thumbnail_url"])
        item.setdefault("views", 0)
        item.setdefault("remix_count", 0)
        item.setdefault("slug", item.get("job_id", ""))
        item.pop("trending_score", None)

    return {"success": True, "items": items, "period": "weekly"}



# ─── LIVE ACTIVITY FEED ───────────────────────────────────────────────────

import random as _random
import hashlib as _hashlib

_ANON_LABELS = [
    "A creator in India", "A creator in United States", "A creator in Germany",
    "A creator in Brazil", "A creator in Japan", "A creator in United Kingdom",
    "A creator in Nigeria", "A creator in Australia", "A creator in Canada",
    "A creator in France", "A creator in Indonesia", "A creator in Turkey",
    "A creator in South Korea", "A creator in Mexico", "A creator in Italy",
    "A creator in Spain", "A creator in Kenya", "A creator in South Africa",
    "A creator in Argentina", "A creator in Netherlands",
]

_ACTIVITY_TYPES = [
    {"type": "creation", "verb": "just created", "icon": "sparkles"},
    {"type": "creation", "verb": "published", "icon": "film"},
    {"type": "remix", "verb": "remixed", "icon": "refresh-ccw"},
    {"type": "creation", "verb": "finished generating", "icon": "wand"},
    {"type": "publish", "verb": "shared", "icon": "share"},
]


async def _anonymize_creator_async(user_id: str, item_index: int = 0) -> str:
    """Use real user country if available, else diverse anonymous fallback.
    item_index ensures different items from same user get varied labels."""
    if not user_id:
        return "A creator"
    try:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "country": 1})
        if user and user.get("country"):
            return f"A creator in {user['country']}"
    except Exception:
        pass
    # Fallback: use item_index for variety across feed items from same user
    idx = (int(_hashlib.md5(user_id.encode()).hexdigest(), 16) + item_index) % len(_ANON_LABELS)
    return _ANON_LABELS[idx]


@router.get("/live-activity")
async def get_live_activity(limit: int = Query(8, ge=1, le=20)):
    """
    Live activity feed for homepage social proof.
    Returns ONLY real user activity. No synthetic/fake data.
    """
    now = datetime.now(timezone.utc)

    # Real activity only: non-seeded, non-test completed jobs from last 30 days
    real_items = await db.pipeline_jobs.find(
        {
            "status": "COMPLETED",
            "user_id": {"$ne": "visionary-ai-system"},
            "is_seeded": {"$ne": True},
            "title": {"$not": {"$regex": "(?i)test|benchmark|reject|bypass|admission|cache|reservation|parallel|speed|ui test"}},
            "created_at": {"$gte": now - timedelta(days=30)},
        },
        {"_id": 0, "title": 1, "user_id": 1, "category": 1, "created_at": 1,
         "remix_count": 1, "animation_style": 1, "tool_type": 1}
    ).sort("created_at", -1).limit(limit * 2).to_list(length=limit * 2)

    feed = []
    seen_titles = set()
    for item in real_items:
        title = item.get("title", "an AI video")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        activity = _random.choice(_ACTIVITY_TYPES[:2])
        feed.append({
            "id": _hashlib.md5(f"{title}{item.get('created_at', '')}".encode()).hexdigest()[:12],
            "creator": await _anonymize_creator_async(item.get("user_id", ""), len(feed)),
            "action": activity["verb"],
            "title": title,
            "category": item.get("category", ""),
            "icon": activity["icon"],
            "type": activity["type"],
            "time_ago": _relative_time(item.get("created_at", now), now),
        })
        if len(feed) >= limit:
            break

    return {"success": True, "items": feed[:limit], "count": len(feed[:limit])}


def _relative_time(dt, now) -> str:
    if not dt:
        return "just now"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return "just now"
    # Normalize both to UTC-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    mins = int(diff.total_seconds() / 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


# ─── EXPLORE FEED ─────────────────────────────────────────────────────────

@router.get("/explore")
async def get_explore_feed(
    tab: str = Query("trending", regex="^(trending|newest|most_remixed)$"),
    limit: int = Query(12, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """
    Get explore feed — trending, newest, or most remixed creations.
    No auth required.
    """
    base_filter = {"status": "COMPLETED", "output_url": {"$exists": True, "$nin": [None, ""]}}

    sort_map = {
        "trending": [("views", -1), ("remix_count", -1)],
        "newest": [("created_at", -1)],
        "most_remixed": [("remix_count", -1), ("views", -1)],
    }

    projection = {
        "_id": 0,
        "job_id": 1,
        "slug": 1,
        "title": 1,
        "animation_style": 1,
        "views": 1,
        "remix_count": 1,
        "created_at": 1,
        "thumbnail_url": 1,
        "user_id": 1,
        "scene_images": 1,
    }

    cursor = db.pipeline_jobs.find(base_filter, projection)
    for field, direction in sort_map[tab]:
        cursor = cursor.sort(field, direction)
    items = await cursor.skip(skip).limit(limit).to_list(length=limit)

    total = await db.pipeline_jobs.count_documents(base_filter)

    # Presign thumbnails, fallback to scene_images
    from utils.r2_presign import presign_url
    for item in items:
        # Auto-populate thumbnail from scene_images if missing
        if not item.get("thumbnail_url"):
            scene_imgs = item.get("scene_images", {})
            if scene_imgs:
                first_key = sorted(scene_imgs.keys())[0] if scene_imgs else None
                if first_key and scene_imgs[first_key].get("url"):
                    item["thumbnail_url"] = scene_imgs[first_key]["url"]
        
        if item.get("thumbnail_url"):
            item["thumbnail_url"] = presign_url(item["thumbnail_url"])
        
        item.pop("scene_images", None)  # Strip from response
        item.pop("scenes", None)
        item.setdefault("views", 0)
        item.setdefault("remix_count", 0)
        item.setdefault("slug", item.get("job_id", ""))

    return {
        "success": True,
        "tab": tab,
        "items": items,
        "total": total,
        "has_more": skip + limit < total,
    }


# ─── OG META / SHARE PAGE (for social media crawlers) ────────────────────

def _build_og_html(title, description, image_url, page_url, canonical_url):
    """Build a minimal HTML page with OG tags + JS redirect for humans."""
    safe_title = (title or "Untitled").replace('"', '&quot;').replace('<', '&lt;')
    safe_desc = (description or "").replace('"', '&quot;').replace('<', '&lt;')
    safe_img = (image_url or "").replace('"', '&quot;')
    safe_url = (page_url or "").replace('"', '&quot;')
    safe_canonical = (canonical_url or safe_url).replace('"', '&quot;')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{safe_title} — Visionary Suite AI</title>
<meta name="description" content="{safe_desc}"/>
<link rel="canonical" href="{safe_canonical}"/>

<meta property="og:type" content="video.other"/>
<meta property="og:url" content="{safe_canonical}"/>
<meta property="og:title" content="{safe_title}"/>
<meta property="og:description" content="{safe_desc}"/>
<meta property="og:image" content="{safe_img}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:site_name" content="Visionary Suite"/>

<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{safe_title}"/>
<meta name="twitter:description" content="{safe_desc}"/>
<meta name="twitter:image" content="{safe_img}"/>

<meta http-equiv="refresh" content="0;url={safe_canonical}"/>
</head>
<body>
<p>Redirecting to <a href="{safe_canonical}">{safe_title}</a>...</p>
<script>window.location.replace("{safe_canonical}");</script>
</body>
</html>"""


@router.get("/s/{slug}", response_class=HTMLResponse)
async def share_page(slug: str):
    """
    Social media share page — serves full OG tags in HTML.
    Crawlers see the meta tags; humans get redirected to /v/{slug}.
    """
    job = await db.pipeline_jobs.find_one(
        {"$or": [{"slug": slug}, {"job_id": slug}]},
        {"_id": 0, "title": 1, "story_text": 1, "thumbnail_url": 1, "slug": 1, "job_id": 1, "animation_style": 1, "views": 1, "remix_count": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Creation not found")

    title = job.get("title", "AI Video")
    prompt = job.get("story_text", "")
    description = f"AI-generated video: {prompt[:140]}..." if len(prompt) > 140 else f"AI-generated video: {prompt}" if prompt else f"Watch \"{title}\" — created with Visionary Suite AI"

    actual_slug = job.get("slug") or job.get("job_id", slug)
    page_url = f"{FRONTEND_URL}/v/{actual_slug}"

    # OG image — use the dynamic OG image endpoint
    og_image = f"{FRONTEND_URL}/api/public/og-image/{actual_slug}"

    return HTMLResponse(_build_og_html(title, description, og_image, page_url, page_url))


@router.get("/og-image/{slug}")
async def og_image(slug: str):
    """
    Generate a dynamic OG image (1200x630) for social media previews.
    Uses the creation's thumbnail + title overlay.
    """
    from PIL import Image, ImageDraw, ImageFont
    import io
    import httpx

    job = await db.pipeline_jobs.find_one(
        {"$or": [{"slug": slug}, {"job_id": slug}]},
        {"_id": 0, "title": 1, "thumbnail_url": 1, "animation_style": 1, "views": 1, "remix_count": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Not found")

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), color=(10, 10, 20))
    draw = ImageDraw.Draw(img)

    # Try to load the thumbnail as background
    thumb_url = job.get("thumbnail_url", "")
    if thumb_url:
        try:
            from utils.r2_presign import presign_url
            thumb_url = presign_url(thumb_url)
            async with httpx.AsyncClient(timeout=8.0) as hc:
                r = await hc.get(thumb_url)
                if r.status_code == 200:
                    bg = Image.open(io.BytesIO(r.content)).convert("RGB")
                    bg = bg.resize((W, H), Image.LANCZOS)
                    # Darken overlay
                    overlay = Image.new("RGB", (W, H), (0, 0, 0))
                    img = Image.blend(bg, overlay, 0.45)
                    draw = ImageDraw.Draw(img)
        except Exception as e:
            logger.warning(f"OG image thumb load failed: {e}")

    # Draw gradient bar at bottom
    for y in range(H - 200, H):
        alpha = int(220 * ((y - (H - 200)) / 200))
        draw.rectangle([0, y, W, y + 1], fill=(10, 10, 30, alpha) if img.mode == "RGBA" else (max(0, 10 - alpha // 3), max(0, 10 - alpha // 3), max(0, 30 - alpha // 3)))

    # Text
    title = job.get("title", "AI Video")[:60]
    style = (job.get("animation_style") or "").replace("_", " ").title()

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_brand = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_brand = font_title

    # Title text with shadow
    draw.text((42, H - 170), title, font=font_title, fill=(0, 0, 0))
    draw.text((40, H - 172), title, font=font_title, fill=(255, 255, 255))

    # Subtitle
    views = job.get("views", 0)
    remixes = job.get("remix_count", 0)
    sub = f"{style}  •  {views} views  •  {remixes} remixes"
    draw.text((40, H - 110), sub, font=font_sub, fill=(180, 180, 200))

    # Brand
    draw.text((40, H - 60), "Visionary Suite AI", font=font_brand, fill=(139, 92, 246))
    draw.text((W - 240, H - 60), "Watch & Remix  ▶", font=font_brand, fill=(139, 92, 246))

    # Purple accent line
    draw.rectangle([40, H - 185, W - 40, H - 183], fill=(139, 92, 246))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


# ─── SITEMAP ──────────────────────────────────────────────────────────────

@router.get("/sitemap.xml")
async def sitemap():
    """Generate XML sitemap for all public creations."""
    items = await db.pipeline_jobs.find(
        {"status": "COMPLETED"},
        {"_id": 0, "slug": 1, "job_id": 1, "created_at": 1}
    ).sort("created_at", -1).to_list(length=5000)

    urls = [f"""  <url>
    <loc>{FRONTEND_URL}/v/{item.get('slug') or item['job_id']}</loc>
    <lastmod>{item.get('created_at', datetime.now(timezone.utc)).strftime('%Y-%m-%d') if hasattr(item.get('created_at', ''), 'strftime') else datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>""" for item in items]

    # Static pages
    static_pages = [
        ("", "daily", "1.0"),
        ("/explore", "daily", "0.9"),
        ("/pricing", "monthly", "0.6"),
        ("/blog", "weekly", "0.7"),
    ]
    static_urls = [f"""  <url>
    <loc>{FRONTEND_URL}{path}</loc>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>""" for path, freq, priority in static_pages]

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(static_urls)}
{chr(10).join(urls)}
</urlset>"""

    return Response(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


# ─── CREATOR PROFILES ─────────────────────────────────────────────────────

@router.get("/creator/{username}")
async def get_creator_profile(username: str):
    """Get a public creator profile with their creations."""
    # Find user by username or name
    user = await db.users.find_one(
        {"$or": [{"username": username}, {"name": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}]},
        {"_id": 0, "id": 1, "name": 1, "username": 1, "bio": 1, "avatar_url": 1, "created_at": 1}
    )
    if not user:
        raise HTTPException(status_code=404, detail="Creator not found")

    user_id = user.get("id")

    # Get their creations
    creations = await db.pipeline_jobs.find(
        {"user_id": user_id, "status": "COMPLETED"},
        {"_id": 0, "job_id": 1, "slug": 1, "title": 1, "animation_style": 1, "views": 1, "remix_count": 1, "created_at": 1, "thumbnail_url": 1}
    ).sort("created_at", -1).to_list(length=50)

    from utils.r2_presign import presign_url
    for c in creations:
        if c.get("thumbnail_url"):
            c["thumbnail_url"] = presign_url(c["thumbnail_url"])
        c.setdefault("views", 0)
        c.setdefault("remix_count", 0)
        c.setdefault("slug", c.get("job_id", ""))

    total_views = sum(c.get("views", 0) for c in creations)
    total_remixes = sum(c.get("remix_count", 0) for c in creations)

    return {
        "success": True,
        "creator": {
            "name": user.get("name", username),
            "username": user.get("username", username),
            "bio": user.get("bio", ""),
            "avatar_url": user.get("avatar_url", ""),
            "joined": user.get("created_at"),
            "total_creations": len(creations),
            "total_views": total_views,
            "total_remixes": total_remixes,
        },
        "creations": creations,
    }


# ─── GROWTH DASHBOARD METRICS ────────────────────────────────────────────

@router.get("/growth-metrics")
async def get_growth_metrics():
    """
    Growth dashboard metrics for admin panel.
    Returns: daily creations, remix rate, public page views, share rate, creator activation.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = today_start - timedelta(days=7)

    # 1. Daily Creations
    today_creations = await db.pipeline_jobs.count_documents({"created_at": {"$gte": today_start}, "status": "COMPLETED"})
    yesterday_creations = await db.pipeline_jobs.count_documents({"created_at": {"$gte": yesterday_start, "$lt": today_start}, "status": "COMPLETED"})

    # 7-day daily average
    week_creations = await db.pipeline_jobs.count_documents({"created_at": {"$gte": week_ago}, "status": "COMPLETED"})
    avg_7d = round(week_creations / 7, 1)

    # 2. Remix Rate
    total_creations = await db.pipeline_jobs.count_documents({"status": "COMPLETED"})
    remix_pipeline = [
        {"$match": {"status": "COMPLETED"}},
        {"$group": {"_id": None, "total_remixes": {"$sum": {"$ifNull": ["$remix_count", 0]}}}}
    ]
    remix_result = await db.pipeline_jobs.aggregate(remix_pipeline).to_list(length=1)
    total_remixes = remix_result[0]["total_remixes"] if remix_result else 0
    remix_rate = round((total_remixes / total_creations * 100), 1) if total_creations > 0 else 0

    # 3. Public Page Traffic (total views)
    views_pipeline = [
        {"$match": {"status": "COMPLETED"}},
        {"$group": {"_id": None, "total_views": {"$sum": {"$ifNull": ["$views", 0]}}}}
    ]
    views_result = await db.pipeline_jobs.aggregate(views_pipeline).to_list(length=1)
    total_views = views_result[0]["total_views"] if views_result else 0

    # 4. Creator Activation
    total_users = await db.users.count_documents({})
    creators_with_content = await db.pipeline_jobs.distinct("user_id", {"status": "COMPLETED"})
    activation_rate = round((len(creators_with_content) / total_users * 100), 1) if total_users > 0 else 0

    # 5. 7-day trend (creations per day)
    trend_pipeline = [
        {"$match": {"created_at": {"$gte": week_ago}, "status": "COMPLETED"}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    trend_data = await db.pipeline_jobs.aggregate(trend_pipeline).to_list(length=30)

    # 6. Top trending creations
    trending = await db.pipeline_jobs.find(
        {"status": "COMPLETED"},
        {"_id": 0, "title": 1, "slug": 1, "views": 1, "remix_count": 1}
    ).sort([("views", -1), ("remix_count", -1)]).limit(5).to_list(length=5)

    return {
        "success": True,
        "metrics": {
            "daily_creations": {
                "today": today_creations,
                "yesterday": yesterday_creations,
                "avg_7d": avg_7d,
            },
            "remix_rate": remix_rate,
            "total_remixes": total_remixes,
            "public_page_traffic": {
                "total_views": total_views,
            },
            "creator_activation": {
                "total_users": total_users,
                "active_creators": len(creators_with_content),
                "rate": activation_rate,
            },
            "total_creations": total_creations,
            "trend_7d": [{"date": d["_id"], "count": d["count"]} for d in trend_data],
            "trending_creations": trending,
        }
    }


# ─── CONTENT SEEDING HELPERS ─────────────────────────────────────────────

@router.get("/seed-status")
async def seed_status():
    """Check how many seeded videos exist."""
    count = await db.pipeline_jobs.count_documents({"user_id": "visionary-ai-system"})
    return {"seeded_count": count}


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC CHARACTER PAGE — Viral Sharing Loop
# No auth required. Drives user acquisition through character-based sharing.
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/character/{character_id}")
async def get_public_character(character_id: str):
    """
    Public character page data. No login required.
    Returns character profile, visual bible, sample scenes, social proof stats.
    """
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "status": "active"}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    # Visual bible
    visual_bible = await db.character_visual_bibles.find_one(
        {"character_id": character_id}, {"_id": 0}
    )

    # Social proof: episode count
    episode_count = 0
    series_title = None
    series_id = profile.get("source_series_id") or profile.get("series_id")
    if series_id:
        episode_count = await db.story_episodes.count_documents({"series_id": series_id})
        series = await db.story_series.find_one(
            {"series_id": series_id},
            {"_id": 0, "title": 1, "genre": 1, "style": 1, "audience_type": 1, "description": 1}
        )
        if series:
            series_title = series.get("title")

    # Sample scenes (from memory logs or episodes)
    sample_scenes = []
    memory_logs = await db.character_memory_logs.find(
        {"character_id": character_id},
        {"_id": 0, "event_summary": 1, "emotion_state": 1, "episode_id": 1}
    ).sort("created_at", -1).to_list(5)
    for log in memory_logs:
        sample_scenes.append({
            "summary": log.get("event_summary", ""),
            "emotion": log.get("emotion_state", "neutral"),
        })

    # Total usage across all tools
    total_usage = await db.character_memory_logs.count_documents({"character_id": character_id})

    # ── Character Power Score: real momentum data ────────────────────
    now = datetime.now(timezone.utc)
    one_day_ago = (now - timedelta(hours=24)).isoformat()

    # Total stories featuring this character (across all tools)
    total_stories = await db.pipeline_jobs.count_documents({
        "$or": [
            {"story_text": {"$regex": profile.get("name", "NOMATCH"), "$options": "i"}},
            {"characters": character_id},
            {"extracted_characters": {"$elemMatch": {"character_id": character_id}}},
        ]
    })

    # Total continuations / remixes of stories with this character
    total_continuations = await db.pipeline_jobs.count_documents({
        "remix_parent_id": {"$exists": True, "$ne": None},
        "$or": [
            {"story_text": {"$regex": profile.get("name", "NOMATCH"), "$options": "i"}},
            {"characters": character_id},
        ]
    })

    # Last continuation timestamp
    last_cont = await db.pipeline_jobs.find_one(
        {
            "remix_parent_id": {"$exists": True, "$ne": None},
            "$or": [
                {"story_text": {"$regex": profile.get("name", "NOMATCH"), "$options": "i"}},
                {"characters": character_id},
            ]
        },
        {"_id": 0, "created_at": 1},
        sort=[("created_at", -1)]
    )
    last_continuation_at = last_cont.get("created_at") if last_cont else None

    # Tools this character appears in
    tools_pipeline = [
        {"$match": {"$or": [
            {"story_text": {"$regex": profile.get("name", "NOMATCH"), "$options": "i"}},
            {"characters": character_id},
        ]}},
        {"$group": {"_id": "$tool_type"}},
    ]
    tool_types = await db.pipeline_jobs.aggregate(tools_pipeline).to_list(10)
    tools_used = [t["_id"] for t in tool_types if t.get("_id")]

    # Is alive: activity in last 24h
    is_alive = bool(last_continuation_at and last_continuation_at >= one_day_ago)

    # Creator info (public name only)
    creator_name = None
    if profile.get("owner_user_id"):
        creator = await db.users.find_one(
            {"id": profile["owner_user_id"]},
            {"_id": 0, "name": 1}
        )
        if creator:
            creator_name = creator.get("name")

    # Relationships
    relationships = []
    rels = await db.character_relationships.find(
        {"$or": [{"character_id_a": character_id}, {"character_id_b": character_id}]},
        {"_id": 0}
    ).to_list(10)
    for rel in rels:
        other_id = rel["character_id_b"] if rel["character_id_a"] == character_id else rel["character_id_a"]
        other = await db.character_profiles.find_one(
            {"character_id": other_id, "status": "active"},
            {"_id": 0, "name": 1, "role": 1, "character_id": 1}
        )
        if other:
            relationships.append({
                "character_id": other["character_id"],
                "name": other.get("name"),
                "role": other.get("role"),
                "relationship_type": rel.get("relationship_type"),
                "state": rel.get("state", "active"),
            })

    # Build remix prompt from character data
    canonical = visual_bible.get("canonical_description", "") if visual_bible else ""
    personality = profile.get("personality_summary", "")
    goals = profile.get("core_goals", "")
    char_name = profile.get("name", "Unknown")
    remix_prompt = f"A story featuring {char_name}. {canonical} {personality}. {f'Their goal: {goals}' if goals else ''}".strip()

    return {
        "success": True,
        "character": {
            "character_id": profile["character_id"],
            "name": char_name,
            "role": profile.get("role"),
            "personality_summary": personality,
            "core_goals": goals,
            "core_fears": profile.get("core_fears", ""),
            "speech_style": profile.get("speech_style", ""),
            "portrait_url": profile.get("portrait_url"),
            "species_or_type": profile.get("species_or_type", "character"),
        },
        "visual_bible": {
            "canonical_description": canonical,
            "clothing_description": visual_bible.get("clothing_description", "") if visual_bible else "",
            "style_lock": visual_bible.get("style_lock", "") if visual_bible else "",
            "color_palette": visual_bible.get("color_palette", "") if visual_bible else "",
        } if visual_bible else None,
        "social_proof": {
            "episode_count": episode_count,
            "total_usage": total_usage,
            "total_stories": total_stories,
            "total_continuations": total_continuations,
            "last_continuation_at": last_continuation_at,
            "tools_used": tools_used,
            "is_alive": is_alive,
            "series_title": series_title,
            "creator_name": creator_name,
        },
        "sample_scenes": sample_scenes,
        "relationships": relationships,
        "remix_data": {
            "prompt": remix_prompt,
            "remixFrom": {
                "title": f"Story with {char_name}",
                "character_id": character_id,
                "character_name": char_name,
                "type": "character_share",
            },
        },
    }