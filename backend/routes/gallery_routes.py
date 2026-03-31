"""
Gallery API — Discovery engine for Visionary Suite content.
Provides featured content, category rails, explore feed, and seeded demo content.
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import Header
import jwt
import os
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/gallery", tags=["gallery"])

# ── DB reference (set in server.py) ──
db = None

def set_db(database):
    global db
    db = database

# ── Seed Data ────────────────────────────────────────────────
SEED_CONTENT = [
    # Kids Stories
    {"title": "The Fox and the Magic Forest", "description": "A curious little fox discovers a hidden world of glowing mushrooms and friendly fireflies deep in an enchanted forest.", "category": "Kids Stories", "tags": ["kids", "fantasy", "animals", "bedtime"], "thumbnail_url": "https://images.pexels.com/photos/35303526/pexels-photo-35303526.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 45, "animation_style": "cartoon_2d", "views_count": 12400, "likes_count": 3200, "remixes_count": 890, "is_featured": True},
    {"title": "Luna and the Starlight Dragon", "description": "Little Luna befriends a baby dragon made of starlight and together they paint the night sky with constellations.", "category": "Kids Stories", "tags": ["kids", "fantasy", "dragons", "bedtime"], "thumbnail_url": "https://images.unsplash.com/photo-1686001407324-6959a43b6e6c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwxfHxzcGFjZSUyMGNvc21vcyUyMG5lYnVsYSUyMGNpbmVtYXRpY3xlbnwwfHx8fDE3NzQ5NzgyOTJ8MA&ixlib=rb-4.1.0&q=85", "duration_seconds": 60, "animation_style": "cartoon_2d", "views_count": 8700, "likes_count": 2100, "remixes_count": 540},
    {"title": "The Brave Little Penguin", "description": "A tiny penguin overcomes its fear of the big ocean and makes unlikely friends along the way.", "category": "Kids Stories", "tags": ["kids", "animals", "courage", "bedtime"], "thumbnail_url": "https://images.pexels.com/photos/7494509/pexels-photo-7494509.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 38, "animation_style": "cartoon_2d", "views_count": 15200, "likes_count": 4100, "remixes_count": 1200},
    {"title": "Moonlight Lullaby", "description": "The moon comes alive and sings a gentle lullaby to help all the forest animals fall asleep.", "category": "Kids Stories", "tags": ["kids", "bedtime", "music", "gentle"], "thumbnail_url": "https://images.pexels.com/photos/7494503/pexels-photo-7494503.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 30, "animation_style": "cartoon_2d", "views_count": 22000, "likes_count": 5800, "remixes_count": 1500},

    # Cinematic AI
    {"title": "Beyond the Nebula", "description": "A lone spacecraft discovers an ancient civilization hidden within a cosmic nebula at the edge of the known universe.", "category": "Cinematic AI", "tags": ["space", "cinematic", "sci-fi", "epic"], "thumbnail_url": "https://images.unsplash.com/photo-1754630551378-e1ecffe9da6b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwyfHxzcGFjZSUyMGNvc21vcyUyMG5lYnVsYSUyMGNpbmVtYXRpY3xlbnwwfHx8fDE3NzQ5NzgyOTJ8MA&ixlib=rb-4.1.0&q=85", "duration_seconds": 60, "animation_style": "cinematic", "views_count": 34500, "likes_count": 8900, "remixes_count": 2300, "is_featured": True},
    {"title": "The Last Sunrise", "description": "Earth's final sunset unfolds in breathtaking cinematic beauty as humanity prepares for its greatest journey.", "category": "Cinematic AI", "tags": ["cinematic", "emotional", "earth", "epic"], "thumbnail_url": "https://images.pexels.com/photos/30616136/pexels-photo-30616136.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 90, "animation_style": "cinematic", "views_count": 28000, "likes_count": 7200, "remixes_count": 1800},
    {"title": "Whispers of the Cosmos", "description": "A visual meditation through the galaxies, nebulae, and the silent beauty of deep space.", "category": "Cinematic AI", "tags": ["space", "meditation", "cinematic", "relaxing"], "thumbnail_url": "https://images.pexels.com/photos/30616137/pexels-photo-30616137.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 45, "animation_style": "cinematic", "views_count": 19000, "likes_count": 4600, "remixes_count": 950},

    # Emotional Stories
    {"title": "Letters Never Sent", "description": "An old man discovers a box of unsent letters from his late wife, each one a love story he never knew existed.", "category": "Emotional", "tags": ["emotional", "love", "story", "touching"], "thumbnail_url": "https://images.unsplash.com/photo-1766307543930-a35e9417b2d5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwxfHxtYWdpY2FsJTIwZm9yZXN0JTIwZmFpcnklMjB0YWxlJTIwaWxsdXN0cmF0aW9ufGVufDB8fHx8MTc3NDk3ODI4Mnww&ixlib=rb-4.1.0&q=85", "duration_seconds": 60, "animation_style": "cinematic", "views_count": 45000, "likes_count": 12000, "remixes_count": 3400, "is_featured": True},
    {"title": "The Promise Tree", "description": "Two childhood friends plant a tree with a promise to return — twenty years later, only one comes back.", "category": "Emotional", "tags": ["emotional", "friendship", "story", "deep"], "thumbnail_url": "https://images.unsplash.com/photo-1635752019785-6637044adea9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwzfHxtYWdpY2FsJTIwZm9yZXN0JTIwZmFpcnklMjB0YWxlJTIwaWxsdXN0cmF0aW9ufGVufDB8fHx8MTc3NDk3ODI4Mnww&ixlib=rb-4.1.0&q=85", "duration_seconds": 55, "animation_style": "cinematic", "views_count": 38000, "likes_count": 9800, "remixes_count": 2700},
    {"title": "The Last Dance", "description": "A grandfather teaches his granddaughter the waltz his wife taught him — one final dance before memories fade.", "category": "Emotional", "tags": ["emotional", "family", "touching", "story"], "thumbnail_url": "https://images.unsplash.com/photo-1763198216699-af7b7f910a3f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwyfHxtYWdpY2FsJTIwZm9yZXN0JTIwZmFpcnklMjB0YWxlJTIwaWxsdXN0cmF0aW9ufGVufDB8fHx8MTc3NDk3ODI4Mnww&ixlib=rb-4.1.0&q=85", "duration_seconds": 50, "animation_style": "cinematic", "views_count": 52000, "likes_count": 14000, "remixes_count": 4100},

    # Reels & Shorts
    {"title": "5AM Millionaire Morning Routine", "description": "What the top 1% do before sunrise — a cinematic breakdown of the perfect morning routine.", "category": "Reels & Shorts", "tags": ["reels", "motivation", "lifestyle", "viral"], "thumbnail_url": "https://images.unsplash.com/photo-1581223058481-f8838f2338b4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwzfHxtb3RpdmF0aW9uYWwlMjBzdW5yaXNlJTIwbW9ybmluZyUyMHJvdXRpbmV8ZW58MHx8fHwxNzc0OTc4MjkzfDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 30, "animation_style": "cinematic", "views_count": 1200000, "likes_count": 45000, "remixes_count": 12000, "is_featured": True},
    {"title": "3 Money Habits Rich People Never Tell You", "description": "The uncomfortable truths about wealth-building that nobody talks about.", "category": "Reels & Shorts", "tags": ["reels", "finance", "viral", "education"], "thumbnail_url": "https://images.unsplash.com/photo-1629124096115-97d90995157e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwxfHxidXNpbmVzcyUyMGVudHJlcHJlbmV1ciUyMHN1Y2Nlc3N8ZW58MHx8fHwxNzc0OTc4Mjk2fDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 15, "animation_style": "cinematic", "views_count": 890000, "likes_count": 32000, "remixes_count": 8900},
    {"title": "Stop Scrolling — Watch This", "description": "The most powerful 15-second motivation you'll see today.", "category": "Reels & Shorts", "tags": ["reels", "motivation", "viral", "short"], "thumbnail_url": "https://images.unsplash.com/photo-1737063677673-c78145e0b07d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwxfHxtb3RpdmF0aW9uYWwlMjBzdW5yaXNlJTIwbW9ybmluZyUyMHJvdXRpbmV8ZW58MHx8fHwxNzc0OTc4MjkzfDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 15, "animation_style": "cinematic", "views_count": 2300000, "likes_count": 89000, "remixes_count": 23000},
    {"title": "POV: You Finally Made It", "description": "The feeling when years of hustle finally pay off — a cinematic reel.", "category": "Reels & Shorts", "tags": ["reels", "motivation", "luxury", "cinematic"], "thumbnail_url": "https://images.unsplash.com/photo-1729450138844-dcace743b30c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwyfHxtb3RpdmF0aW9uYWwlMjBzdW5yaXNlJTIwbW9ybmluZyUyMHJvdXRpbmV8ZW58MHx8fHwxNzc0OTc4MjkzfDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 30, "animation_style": "cinematic", "views_count": 670000, "likes_count": 24000, "remixes_count": 6700},

    # Business / Promo
    {"title": "Your Brand Deserves This", "description": "A premium product showcase template that makes any brand look like a million dollars.", "category": "Business", "tags": ["business", "promo", "product", "luxury"], "thumbnail_url": "https://images.pexels.com/photos/30360272/pexels-photo-30360272.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 30, "animation_style": "cinematic", "views_count": 45000, "likes_count": 8900, "remixes_count": 3400},
    {"title": "Launch Day Energy", "description": "The ultimate product launch reel template — hype, energy, and conversions.", "category": "Business", "tags": ["business", "launch", "product", "energy"], "thumbnail_url": "https://images.pexels.com/photos/34610771/pexels-photo-34610771.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940", "duration_seconds": 15, "animation_style": "cinematic", "views_count": 67000, "likes_count": 12000, "remixes_count": 5600},
    {"title": "The Hustle Never Stops", "description": "A day-in-the-life style reel for entrepreneurs who want to inspire their audience.", "category": "Business", "tags": ["business", "entrepreneur", "hustle", "lifestyle"], "thumbnail_url": "https://images.unsplash.com/photo-1626105985478-82a838e3d104?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwyfHxidXNpbmVzcyUyMGVudHJlcHJlbmV1ciUyMHN1Y2Nlc3N8ZW58MHx8fHwxNzc0OTc4Mjk2fDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 60, "animation_style": "cinematic", "views_count": 340000, "likes_count": 15000, "remixes_count": 7800},

    # Luxury / Lifestyle
    {"title": "Silent Luxury", "description": "Old money aesthetics — because real luxury doesn't need to scream.", "category": "Luxury", "tags": ["luxury", "lifestyle", "aesthetic", "viral"], "thumbnail_url": "https://images.unsplash.com/photo-1768760819947-f6772ae3f433?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBsaWZlc3R5bGUlMjBjaW5lbWF0aWN8ZW58MHx8fHwxNzc0OTc4MjgzfDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 30, "animation_style": "cinematic", "views_count": 1800000, "likes_count": 67000, "remixes_count": 18000},
    {"title": "Drive Different", "description": "A cinematic car reel that makes any vehicle look like a supercar.", "category": "Luxury", "tags": ["luxury", "cars", "cinematic", "lifestyle"], "thumbnail_url": "https://images.unsplash.com/photo-1743294831502-76899d81db6c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHw0fHxsdXh1cnklMjBsaWZlc3R5bGUlMjBjaW5lbWF0aWN8ZW58MHx8fHwxNzc0OTc4MjgzfDA&ixlib=rb-4.1.0&q=85", "duration_seconds": 15, "animation_style": "cinematic", "views_count": 780000, "likes_count": 28000, "remixes_count": 9200},

    # Educational
    {"title": "How Your Brain Actually Learns", "description": "The neuroscience of learning explained in 60 seconds — with stunning visuals.", "category": "Educational", "tags": ["education", "science", "brain", "learning"], "thumbnail_url": "https://images.unsplash.com/photo-1735213005665-f5b93d0795fe?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwzfHxzcGFjZSUyMGNvc21vcyUyMG5lYnVsYSUyMGNpbmVtYXRpY3xlbnwwfHx8fDE3NzQ5NzgyOTJ8MA&ixlib=rb-4.1.0&q=85", "duration_seconds": 60, "animation_style": "cinematic", "views_count": 230000, "likes_count": 18000, "remixes_count": 4500},
    {"title": "The Hidden Math of Nature", "description": "Fibonacci sequences, golden ratios, and fractals — math is everywhere.", "category": "Educational", "tags": ["education", "math", "nature", "fascinating"], "thumbnail_url": "https://images.unsplash.com/photo-1586693231040-e89840e7d805?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHw0fHxtYWdpY2FsJTIwZm9yZXN0JTIwZmFpcnklMjB0YWxlJTIwaWxsdXN0cmF0aW9ufGVufDB8fHx8MTc3NDk3ODI4Mnww&ixlib=rb-4.1.0&q=85", "duration_seconds": 45, "animation_style": "cinematic", "views_count": 180000, "likes_count": 14000, "remixes_count": 3200},
]

RAIL_CATEGORIES = [
    {"id": "trending", "name": "Trending Now", "emoji": "fire", "sort": "ranking_score", "limit": 12},
    {"id": "most_remixed", "name": "Most Remixed", "emoji": "remix", "sort": "remixes_count", "limit": 12},
    {"id": "kids", "name": "Kids Stories", "emoji": "star", "filter": "Kids Stories", "limit": 12},
    {"id": "reels", "name": "Reels & Shorts", "emoji": "film", "filter": "Reels & Shorts", "limit": 12},
    {"id": "emotional", "name": "Emotional Stories", "emoji": "heart", "filter": "Emotional", "limit": 12},
    {"id": "cinematic", "name": "Cinematic AI", "emoji": "camera", "filter": "Cinematic AI", "limit": 12},
    {"id": "business", "name": "Business & Promo", "emoji": "briefcase", "filter": "Business", "limit": 12},
    {"id": "luxury", "name": "Luxury & Lifestyle", "emoji": "sparkles", "filter": "Luxury", "limit": 12},
    {"id": "educational", "name": "Educational", "emoji": "bulb", "filter": "Educational", "limit": 12},
]


async def seed_gallery_if_empty():
    """Auto-seed gallery content on startup if collection is empty."""
    if db is None:
        return
    count = await db.gallery_content.count_documents({})
    if count > 0:
        return

    now = datetime.now(timezone.utc)
    docs = []
    for i, item in enumerate(SEED_CONTENT):
        doc = {
            "item_id": str(uuid.uuid4()),
            "type": "story_video",
            "title": item["title"],
            "description": item["description"],
            "thumbnail_url": item["thumbnail_url"],
            "preview_video_url": None,
            "full_video_url": None,
            "duration_seconds": item["duration_seconds"],
            "aspect_ratio": "9:16",
            "creator_name": "Visionary Suite",
            "creator_id": "system",
            "views_count": item["views_count"],
            "likes_count": item["likes_count"],
            "remixes_count": item["remixes_count"],
            "is_featured": item.get("is_featured", False),
            "is_seeded": True,
            "tags": item["tags"],
            "category": item["category"],
            "animation_style": item.get("animation_style", "cinematic"),
            "language": "English",
            "created_at": now - timedelta(days=i * 2, hours=i * 3),
            "ranking_score": item["views_count"] * 0.2 + item["likes_count"] * 1.0 + item["remixes_count"] * 2.5,
            "status": "ready",
            "story_text": item["description"],
        }
        docs.append(doc)

    if docs:
        await db.gallery_content.insert_many(docs)
        await db.gallery_content.create_index("category")
        await db.gallery_content.create_index("ranking_score")
        await db.gallery_content.create_index("is_featured")
        await db.gallery_content.create_index([("tags", 1)])
        print(f"[Gallery] Seeded {len(docs)} gallery items")


async def _get_merged_content(category=None, sort_field="ranking_score", sort_dir=-1, limit=48):
    """Merge real pipeline_jobs + seeded gallery_content into a unified feed."""
    items = []

    # 1. Get real completed pipeline jobs
    real_query = {
        "status": "COMPLETED",
        "thumbnail_url": {"$exists": True, "$nin": [None, ""]},
    }
    if category and category != "all":
        real_query["$or"] = [
            {"animation_style": category},
            {"animation_style": category.lower().replace(" ", "_")},
        ]

    real_jobs = await db.pipeline_jobs.find(
        real_query,
        {"title": 1, "output_url": 1, "thumbnail_url": 1, "animation_style": 1, "timing": 1,
         "completed_at": 1, "job_id": 1, "story_text": 1, "remix_count": 1, "slug": 1,
         "age_group": 1, "voice_preset": 1, "scene_images": 1, "views": 1, "_id": 0}
    ).sort("completed_at", -1).to_list(length=limit)

    for job in real_jobs:
        if not job.get("thumbnail_url"):
            scene_imgs = job.get("scene_images", {})
            if scene_imgs:
                first_key = sorted(scene_imgs.keys())[0]
                if scene_imgs[first_key].get("url"):
                    job["thumbnail_url"] = scene_imgs[first_key]["url"]
        job.pop("scene_images", None)
        items.append({
            "item_id": job.get("job_id", ""),
            "type": "story_video",
            "title": job.get("title", "AI Story"),
            "description": (job.get("story_text", "") or "")[:200],
            "thumbnail_url": job.get("thumbnail_url", ""),
            "duration_seconds": int(job.get("timing", {}).get("total_ms", 30000) / 1000) if job.get("timing") else 30,
            "creator_name": "Community",
            "views_count": job.get("views", 0),
            "likes_count": 0,
            "remixes_count": job.get("remix_count", 0),
            "is_seeded": False,
            "category": job.get("animation_style", "cinematic"),
            "animation_style": job.get("animation_style", "cinematic"),
            "tags": [],
            "ranking_score": (job.get("views", 0) * 0.2) + (job.get("remix_count", 0) * 2.5),
            "story_text": job.get("story_text", ""),
            "output_url": job.get("output_url"),
        })

    # 2. Get seeded gallery content
    seed_query = {"status": "ready"}
    if category and category != "all":
        seed_query["category"] = category

    seeded = await db.gallery_content.find(
        seed_query, {"_id": 0}
    ).sort(sort_field, sort_dir).to_list(length=limit)

    for s in seeded:
        if s.get("item_id") not in [i["item_id"] for i in items]:
            items.append(s)

    # 3. Sort merged list
    if sort_field == "remixes_count":
        items.sort(key=lambda x: x.get("remixes_count", 0), reverse=True)
    elif sort_field == "created_at":
        items.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    else:
        items.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)

    return items[:limit]


@router.get("/featured")
async def get_featured():
    """Return featured hero items."""
    featured = await db.gallery_content.find(
        {"is_featured": True, "status": "ready"}, {"_id": 0}
    ).sort("ranking_score", -1).to_list(length=3)

    if not featured:
        featured = await db.gallery_content.find(
            {"status": "ready"}, {"_id": 0}
        ).sort("ranking_score", -1).to_list(length=3)

    return {"featured": featured}


@router.get("/rails")
async def get_rails():
    """Return categorized content rails for Netflix-style layout."""
    rails = []
    for rail_def in RAIL_CATEGORIES:
        query = {"status": "ready"}
        if "filter" in rail_def:
            query["category"] = rail_def["filter"]

        sort_field = rail_def.get("sort", "ranking_score")
        items = await db.gallery_content.find(
            query, {"_id": 0}
        ).sort(sort_field, -1).to_list(length=rail_def.get("limit", 12))

        # Supplement with real pipeline jobs if rail is sparse
        if len(items) < 4:
            real_query = {"status": "COMPLETED", "thumbnail_url": {"$exists": True, "$nin": [None, ""]}}
            real_jobs = await db.pipeline_jobs.find(
                real_query, {"title": 1, "thumbnail_url": 1, "job_id": 1, "story_text": 1,
                             "remix_count": 1, "animation_style": 1, "views": 1, "_id": 0}
            ).sort("completed_at", -1).to_list(length=8)

            for job in real_jobs:
                items.append({
                    "item_id": job.get("job_id", ""),
                    "title": job.get("title", "AI Story"),
                    "description": (job.get("story_text", "") or "")[:120],
                    "thumbnail_url": job.get("thumbnail_url", ""),
                    "duration_seconds": 30,
                    "views_count": job.get("views", 0),
                    "likes_count": 0,
                    "remixes_count": job.get("remix_count", 0),
                    "is_seeded": False,
                    "category": job.get("animation_style", ""),
                    "tags": [],
                    "ranking_score": 0,
                    "story_text": job.get("story_text", ""),
                })

        if items:
            rails.append({
                "id": rail_def["id"],
                "name": rail_def["name"],
                "emoji": rail_def["emoji"],
                "items": items,
            })

    return {"rails": rails}


@router.get("/explore")
async def get_explore(
    category: str = Query(None),
    sort: str = Query("trending"),
    cursor: int = Query(0),
    limit: int = Query(24),
):
    """Paginated explore feed with merged content."""
    sort_map = {
        "trending": "ranking_score",
        "newest": "created_at",
        "most_remixed": "remixes_count",
    }
    sort_field = sort_map.get(sort, "ranking_score")
    items = await _get_merged_content(
        category=category,
        sort_field=sort_field,
        limit=cursor + limit,
    )

    page = items[cursor:cursor + limit]
    return {
        "items": page,
        "total": len(items),
        "cursor": cursor + len(page),
        "has_more": cursor + limit < len(items),
    }


@router.get("/categories")
async def get_gallery_categories():
    """Return available categories with counts."""
    pipe = [
        {"$match": {"status": "ready"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.gallery_content.aggregate(pipe).to_list(length=20)
    categories = [{"id": r["_id"], "name": r["_id"], "count": r["count"]} for r in rows if r["_id"]]
    total = sum(c["count"] for c in categories)
    return {"categories": [{"id": "all", "name": "All", "count": total}] + categories}



def _get_user_id_from_token(authorization: str = None):
    """Extract user_id from JWT token, return None if invalid/missing."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ")[1]
        secret = os.environ.get("JWT_SECRET", "your-secret-key")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("user_id") or payload.get("sub")
    except Exception:
        return None


@router.get("/feed")
async def get_immersive_feed(
    seed_item_id: str = Query(None),
    limit: int = Query(20),
):
    """Return ordered items for TikTok-style immersive viewing.
    Starts from seed_item_id if provided, else top-ranked items."""
    all_items = await _get_merged_content(sort_field="ranking_score", limit=100)
    if not all_items:
        return {"items": [], "seed_index": 0}

    seed_index = 0
    if seed_item_id:
        for i, item in enumerate(all_items):
            if item.get("item_id") == seed_item_id:
                seed_index = i
                break

    start = max(0, seed_index - 2)
    end = min(len(all_items), start + limit)
    feed = all_items[start:end]
    relative_seed = seed_index - start

    return {"items": feed, "seed_index": relative_seed, "total": len(all_items)}


@router.get("/user-feed")
async def get_user_feed(authorization: str = Header(None)):
    """Return personalized sections for logged-in users:
    your_creations, continue_watching, for_you."""
    user_id = _get_user_id_from_token(authorization)
    if not user_id:
        return {"your_creations": [], "continue_watching": [], "for_you": []}

    # Your Creations — user's completed pipeline jobs
    your_jobs = await db.pipeline_jobs.find(
        {"user_id": user_id, "status": "COMPLETED", "thumbnail_url": {"$exists": True, "$nin": [None, ""]}},
        {"title": 1, "thumbnail_url": 1, "job_id": 1, "story_text": 1, "animation_style": 1,
         "remix_count": 1, "views": 1, "completed_at": 1, "scene_images": 1, "_id": 0}
    ).sort("completed_at", -1).to_list(length=12)

    your_creations = []
    for job in your_jobs:
        thumb = job.get("thumbnail_url")
        if not thumb:
            si = job.get("scene_images", {})
            if si:
                first_key = sorted(si.keys())[0]
                thumb = si[first_key].get("url", "")
        your_creations.append({
            "item_id": job.get("job_id", ""),
            "type": "story_video",
            "title": job.get("title", "My Story"),
            "description": (job.get("story_text", "") or "")[:150],
            "thumbnail_url": thumb or "",
            "duration_seconds": 30,
            "views_count": job.get("views", 0),
            "likes_count": 0,
            "remixes_count": job.get("remix_count", 0),
            "is_seeded": False,
            "category": job.get("animation_style", ""),
            "tags": [],
            "ranking_score": 0,
            "story_text": job.get("story_text", ""),
        })

    # Continue Watching — recently viewed gallery items
    recent_views = await db.gallery_views.find(
        {"user_id": user_id},
        {"item_id": 1, "_id": 0}
    ).sort("viewed_at", -1).to_list(length=12)

    continue_ids = [v["item_id"] for v in recent_views]
    continue_watching = []
    if continue_ids:
        for cid in continue_ids:
            doc = await db.gallery_content.find_one({"item_id": cid}, {"_id": 0})
            if doc:
                continue_watching.append(doc)
            else:
                job = await db.pipeline_jobs.find_one(
                    {"job_id": cid, "status": "COMPLETED"},
                    {"title": 1, "thumbnail_url": 1, "job_id": 1, "story_text": 1,
                     "animation_style": 1, "remix_count": 1, "views": 1, "_id": 0}
                )
                if job:
                    continue_watching.append({
                        "item_id": job.get("job_id", ""),
                        "title": job.get("title", "AI Story"),
                        "thumbnail_url": job.get("thumbnail_url", ""),
                        "duration_seconds": 30,
                        "views_count": job.get("views", 0),
                        "remixes_count": job.get("remix_count", 0),
                        "is_seeded": False,
                        "category": job.get("animation_style", ""),
                    })

    # For You — based on user's creation categories + top content
    user_categories = [j.get("animation_style", "") for j in your_jobs if j.get("animation_style")]
    for_you = []
    if user_categories:
        top_cat = max(set(user_categories), key=user_categories.count)
        for_you = await db.gallery_content.find(
            {"category": {"$regex": top_cat, "$options": "i"}, "status": "ready"},
            {"_id": 0}
        ).sort("ranking_score", -1).to_list(length=12)
    if len(for_you) < 6:
        fill = await db.gallery_content.find(
            {"status": "ready"}, {"_id": 0}
        ).sort("ranking_score", -1).to_list(length=12)
        existing_ids = {i.get("item_id") for i in for_you}
        for f in fill:
            if f.get("item_id") not in existing_ids:
                for_you.append(f)
            if len(for_you) >= 12:
                break

    return {
        "your_creations": your_creations,
        "continue_watching": continue_watching,
        "for_you": for_you,
    }


@router.post("/view")
async def track_gallery_view(
    data: dict,
    authorization: str = Header(None),
):
    """Track that a user viewed a gallery item (for Continue Watching)."""
    user_id = _get_user_id_from_token(authorization)
    item_id = data.get("item_id")
    if not user_id or not item_id:
        return {"ok": True}

    await db.gallery_views.update_one(
        {"user_id": user_id, "item_id": item_id},
        {"$set": {"user_id": user_id, "item_id": item_id, "viewed_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"ok": True}
