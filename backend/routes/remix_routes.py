"""
Remix & Variations Engine — Routes
Tracks remix lineage, provides variation configs per tool, logs remix analytics.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from shared import db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/remix", tags=["remix"])

# ─── Variation configs per tool ────────────────────────────────────────
VARIATION_CONFIGS = {
    "story-video-studio": {
        "quick": [
            {"label": "Funny", "modifier": "Make it funny and humorous with comedic timing"},
            {"label": "Dramatic", "modifier": "Make it dramatic and intense with suspense"},
            {"label": "Anime Style", "modifier": "Recreate in anime art style"},
            {"label": "Short Version", "modifier": "Create a 15-second short version"},
        ],
        "styles": ["Pixar", "Anime", "Comic", "Watercolor", "Cinematic", "Cartoon 2D", "Realistic"],
        "actions": [
            {"label": "Create Part 2", "type": "continue", "target": "story-video-studio"},
            {"label": "Short Reel Version", "type": "convert", "target": "reels"},
            {"label": "Different Animation Style", "type": "style", "target": "story-video-studio"},
            {"label": "Funny Version", "type": "tone", "target": "story-video-studio"},
            {"label": "Kids Version", "type": "tone", "target": "story-video-studio"},
            {"label": "Turn Into Comic", "type": "convert", "target": "comic-storybook"},
        ],
    },
    "photo-to-comic": {
        "quick": [
            {"label": "Anime Style", "modifier": "Convert to Japanese anime art style"},
            {"label": "Pixar Style", "modifier": "Convert to Pixar 3D animation style"},
            {"label": "Villain Version", "modifier": "Transform into a dark villain character"},
            {"label": "Hero Version", "modifier": "Transform into a heroic superhero character"},
        ],
        "styles": ["Anime", "Pixar", "Marvel Comic", "Manga", "Watercolor", "Pop Art"],
        "actions": [
            {"label": "Anime Style", "type": "style", "target": "photo-to-comic"},
            {"label": "Pixar Style", "type": "style", "target": "photo-to-comic"},
            {"label": "Villain Version", "type": "tone", "target": "photo-to-comic"},
            {"label": "Hero Version", "type": "tone", "target": "photo-to-comic"},
            {"label": "Turn Into Story", "type": "convert", "target": "stories"},
            {"label": "Create Comic Storybook", "type": "convert", "target": "comic-storybook"},
        ],
    },
    "reels": {
        "quick": [
            {"label": "Different Hook", "modifier": "Write with a completely different opening hook"},
            {"label": "Funny Tone", "modifier": "Rewrite in a funny and entertaining tone"},
            {"label": "Dramatic", "modifier": "Rewrite in a dramatic, intense tone"},
            {"label": "Short Version", "modifier": "Compress into a 15-second script"},
        ],
        "styles": ["Professional", "Casual", "Funny", "Dramatic", "Motivational", "Educational"],
        "actions": [
            {"label": "Different Hook", "type": "tone", "target": "reels"},
            {"label": "Different Tone", "type": "tone", "target": "reels"},
            {"label": "More Dramatic", "type": "tone", "target": "reels"},
            {"label": "Funny Version", "type": "tone", "target": "reels"},
            {"label": "YouTube Shorts Version", "type": "tone", "target": "reels"},
        ],
    },
    "gif-maker": {
        "quick": [
            {"label": "Different Emotion", "modifier": "Create with a different emotion"},
            {"label": "Meme Caption", "modifier": "Add a funny meme-style caption"},
            {"label": "Loop Faster", "modifier": "Make the animation loop faster"},
            {"label": "Dramatic", "modifier": "Make it more dramatic and intense"},
        ],
        "styles": ["Cartoon", "Realistic", "Pixel Art", "Watercolor", "Neon"],
        "actions": [
            {"label": "Different Emotion", "type": "tone", "target": "gif-maker"},
            {"label": "Add Meme Caption", "type": "tone", "target": "gif-maker"},
            {"label": "Loop Faster", "type": "style", "target": "gif-maker"},
            {"label": "Turn Into Reel", "type": "convert", "target": "reels"},
        ],
    },
    "stories": {
        "quick": [
            {"label": "Continue Story", "modifier": "Write the next chapter continuing from where it left off"},
            {"label": "Different Ending", "modifier": "Rewrite with a completely different ending"},
            {"label": "Funny Version", "modifier": "Rewrite in a humorous and comedic style"},
            {"label": "Dark Version", "modifier": "Rewrite in a darker, more suspenseful tone"},
        ],
        "styles": ["Fantasy", "Sci-Fi", "Horror", "Romance", "Comedy", "Adventure", "Mystery"],
        "actions": [
            {"label": "Continue Story", "type": "continue", "target": "stories"},
            {"label": "Different Ending", "type": "tone", "target": "stories"},
            {"label": "Change Genre", "type": "style", "target": "stories"},
            {"label": "Turn Into Video", "type": "convert", "target": "story-video-studio"},
            {"label": "Turn Into Comic", "type": "convert", "target": "comic-storybook"},
        ],
    },
    "bedtime-story-builder": {
        "quick": [
            {"label": "Animal Version", "modifier": "Rewrite with animal characters instead"},
            {"label": "Space Version", "modifier": "Set the story in outer space"},
            {"label": "Funny Version", "modifier": "Make it silly and funny for kids"},
            {"label": "Short Version", "modifier": "Create a shorter 2-minute version"},
        ],
        "styles": ["Fantasy", "Adventure", "Fairy Tale", "Space", "Underwater", "Forest"],
        "actions": [
            {"label": "Different Characters", "type": "tone", "target": "bedtime-story-builder"},
            {"label": "Animal Version", "type": "tone", "target": "bedtime-story-builder"},
            {"label": "Space Version", "type": "tone", "target": "bedtime-story-builder"},
            {"label": "Create Sequel", "type": "continue", "target": "bedtime-story-builder"},
            {"label": "Turn Into Video", "type": "convert", "target": "story-video-studio"},
        ],
    },
    "comic-storybook": {
        "quick": [
            {"label": "Anime Style", "modifier": "Redraw in Japanese anime art style"},
            {"label": "Watercolor", "modifier": "Redraw in soft watercolor style"},
            {"label": "Dark Version", "modifier": "Make the story darker and more dramatic"},
            {"label": "Add Character", "modifier": "Add a new interesting character to the story"},
        ],
        "styles": ["Manga", "Marvel", "Watercolor", "Pixel Art", "Minimalist", "Cartoon"],
        "actions": [
            {"label": "Different Art Style", "type": "style", "target": "comic-storybook"},
            {"label": "Alternate Ending", "type": "tone", "target": "comic-storybook"},
            {"label": "Add New Character", "type": "continue", "target": "comic-storybook"},
            {"label": "Turn Into Video", "type": "convert", "target": "story-video-studio"},
        ],
    },
}


class RemixRequest(BaseModel):
    source_tool: str
    target_tool: str
    original_prompt: str
    variation_type: str = Field(description="quick|style|tone|convert|continue|regenerate")
    variation_label: str = ""
    modifier: str = ""
    style: Optional[str] = None
    original_generation_id: Optional[str] = None
    parent_generation_id: Optional[str] = None
    original_settings: Optional[dict] = None


# ─── GET /api/remix/variations/{tool_type} ──────────────────────────────
@router.get("/variations/{tool_type}")
async def get_variations(tool_type: str):
    """Return variation config for a given tool."""
    config = VARIATION_CONFIGS.get(tool_type)
    if not config:
        return {"quick": [], "styles": [], "actions": []}
    return config


# ─── POST /api/remix/track ──────────────────────────────────────────────
@router.post("/track")
async def track_remix(req: RemixRequest, current_user: dict = Depends(get_current_user)):
    """Track a remix/variation action for analytics."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    doc = {
        "user_id": user_id,
        "source_tool": req.source_tool,
        "target_tool": req.target_tool,
        "variation_type": req.variation_type,
        "variation_label": req.variation_label,
        "original_prompt": req.original_prompt[:500],
        "modifier": req.modifier[:300],
        "style": req.style,
        "original_generation_id": req.original_generation_id,
        "parent_generation_id": req.parent_generation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.remix_events.insert_one(doc)
    logger.info(f"[REMIX] User {user_id[:8]} remixed {req.source_tool} → {req.target_tool} ({req.variation_type})")

    return {"success": True, "tracked": True}


# ─── GET /api/remix/stats ───────────────────────────────────────────────
@router.get("/stats")
async def get_remix_stats(current_user: dict = Depends(get_current_user)):
    """Return remix analytics for admin dashboard."""
    user_id = current_user.get("id") or str(current_user.get("_id"))

    user_role = current_user.get("role", "")
    if user_role not in ("ADMIN", "admin"):
        total = await db.remix_events.count_documents({"user_id": user_id})
        return {"total_remixes": total}

    total = await db.remix_events.count_documents({})

    pipeline = [
        {"$group": {"_id": "$variation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_type = {d["_id"]: d["count"] async for d in db.remix_events.aggregate(pipeline)}

    pipeline2 = [
        {"$group": {"_id": "$source_tool", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_tool = {d["_id"]: d["count"] async for d in db.remix_events.aggregate(pipeline2)}

    cross_tool = await db.remix_events.count_documents({
        "$expr": {"$ne": ["$source_tool", "$target_tool"]}
    })

    return {
        "total_remixes": total,
        "by_type": by_type,
        "by_source_tool": by_tool,
        "cross_tool_conversions": cross_tool,
    }
