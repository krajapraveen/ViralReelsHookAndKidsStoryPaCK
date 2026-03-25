"""
Content Seeding Engine — AI-powered story generation with strict HOOK → BUILD → CLIFFHANGER format.
Generates stories across categories, social media scripts, and publishes to platform pipeline.
All content is truth-based: quality-filtered, no placeholders.
"""
import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db, get_current_user

logger = logging.getLogger("creatorstudio.content_engine")
router = APIRouter(prefix="/content-engine", tags=["Content Engine"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ═══════════════════════════════════════════════════════════════
# CATEGORIES & PROMPTS
# ═══════════════════════════════════════════════════════════════

CATEGORIES = {
    "emotional": {
        "label": "Emotional",
        "themes": ["loss", "betrayal", "love", "reunion", "sacrifice", "forgiveness"],
        "styles": ["watercolor", "realistic"],
    },
    "mystery": {
        "label": "Mystery",
        "themes": ["unknown", "suspense", "conspiracy", "impossible event", "time anomaly"],
        "styles": ["realistic", "noir"],
    },
    "kids": {
        "label": "Kids",
        "themes": ["magical animals", "brave child", "enchanted forest", "sky kingdom", "friendly monster"],
        "styles": ["cartoon_2d", "watercolor"],
    },
    "horror": {
        "label": "Horror",
        "themes": ["fear", "tension", "isolation", "the unknown", "whispers", "shadows"],
        "styles": ["realistic", "noir"],
    },
    "viral": {
        "label": "Viral",
        "themes": ["weird twist", "shocking reveal", "impossible coincidence", "glitch in reality", "everyone stopped"],
        "styles": ["anime", "cartoon_2d"],
    },
}

ANIMATION_STYLES = ["cartoon_2d", "anime", "watercolor", "realistic"]

STORY_GEN_SYSTEM = """You are a viral story hook writer. You create ultra-short stories (3-4 lines max) that are IMPOSSIBLE to ignore.

STRICT FORMAT for each story:
LINE 1: HOOK — A single sentence that grabs instantly. Start mid-action or with something unexpected.
LINE 2-3: BUILD — Brief context that deepens curiosity.
LINE 4: CLIFFHANGER — An unresolved ending that makes the reader NEED to know what happens next.

RULES:
- Under 4 lines total, under 60 words
- Start with curiosity or shock
- End with UNRESOLVED TENSION — never resolve the story
- Instantly understandable — no complex world-building
- Usable as a reel script (spoken in under 15 seconds)
- Each story must be DIFFERENT in structure and approach
- NO generic openings like "Once upon a time" or "In a world where..."
- START with action, dialogue, or a shocking statement

QUALITY FILTERS — REJECT if:
- The ending feels complete or resolved
- The hook doesn't create immediate curiosity
- The story is predictable or generic
- It takes more than 3 seconds to understand
- It wouldn't make someone stop scrolling"""

SOCIAL_SCRIPT_SYSTEM = """You generate social media scripts from stories. For each story, produce:

1. REEL_SCRIPT: The story read aloud dramatically, ending with "Continue this story at the link" (under 15 seconds spoken)
2. CAPTION: A 1-2 line caption for Instagram/TikTok that creates curiosity and includes a CTA
3. HASHTAGS: 8-10 relevant hashtags including #ai #story #viral #shorts #animation

Output as JSON array. Each item: {"reel_script": "...", "caption": "...", "hashtags": "..."}"""


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class GenerateBatchRequest(BaseModel):
    count: int = Field(10, ge=1, le=50)
    categories: Optional[List[str]] = None  # None = all categories
    auto_publish: bool = False

class FeatureRequest(BaseModel):
    story_ids: List[str]
    featured: bool = True

class QualityTagRequest(BaseModel):
    story_id: str
    tag: str  # HIGH_VIRAL, EMOTIONAL_HOOK, FAST_CONVERSION, WEAK


def _admin_required(user: dict = Depends(get_current_user)):
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ═══════════════════════════════════════════════════════════════
# AI GENERATION
# ═══════════════════════════════════════════════════════════════

async def _generate_stories_ai(category: str, theme: str, count: int) -> list:
    """Generate stories using Emergent LLM (GPT-4o-mini)."""
    if not EMERGENT_LLM_KEY:
        logger.error("[CONTENT_ENGINE] No EMERGENT_LLM_KEY configured")
        return []

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    try:
        llm = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"content_engine_{uuid.uuid4().hex[:8]}",
            system_message=STORY_GEN_SYSTEM,
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.95, max_tokens=2000)

        prompt = f"""Generate exactly {count} unique viral story hooks in the "{category}" category with the theme "{theme}".

Each story MUST:
- Be 3-4 lines, under 60 words
- Follow HOOK → BUILD → CLIFFHANGER format
- End with UNRESOLVED tension
- Be instantly understandable
- Be different from each other in structure

Output as a JSON array of objects:
[{{"title": "short 3-5 word title", "story": "the full 3-4 line story text", "hook_line": "just the first line"}}]

Generate {count} stories NOW. Output ONLY valid JSON."""

        response = await llm.send_message(UserMessage(text=prompt))

        # Parse JSON from response
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        stories = json.loads(text)
        if not isinstance(stories, list):
            stories = [stories]

        return stories[:count]

    except Exception as e:
        logger.error(f"[CONTENT_ENGINE] AI generation failed: {e}")
        return []


async def _generate_social_scripts(stories: list) -> list:
    """Generate social media scripts for stories."""
    if not EMERGENT_LLM_KEY or not stories:
        return []

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    try:
        llm = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"social_scripts_{uuid.uuid4().hex[:8]}",
            system_message=SOCIAL_SCRIPT_SYSTEM,
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.8, max_tokens=3000)

        stories_text = "\n\n".join(
            [f"Story {i+1} ({s.get('title', 'untitled')}): {s.get('story', '')}" for i, s in enumerate(stories)]
        )

        prompt = f"""Generate social media scripts for these {len(stories)} stories:

{stories_text}

Output as JSON array with {len(stories)} items. Each: {{"reel_script": "...", "caption": "...", "hashtags": "..."}}
Output ONLY valid JSON."""

        response = await llm.send_message(UserMessage(text=prompt))

        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        scripts = json.loads(text)
        return scripts if isinstance(scripts, list) else []

    except Exception as e:
        logger.error(f"[CONTENT_ENGINE] Social script generation failed: {e}")
        return []


def _quality_score(story: dict) -> dict:
    """Simple heuristic quality scoring."""
    text = story.get("story", "")
    hook = story.get("hook_line", "")
    words = text.split()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    score = 50  # base
    tags = []

    # Length check (3-4 lines, under 60 words)
    if 2 <= len(lines) <= 5 and len(words) <= 70:
        score += 15
    elif len(words) > 80:
        score -= 20

    # Hook quality
    if hook and len(hook.split()) <= 15:
        score += 10
    if any(w in hook.lower() for w in ["he", "she", "they", "i ", "the door", "found", "opened", "saw"]):
        score += 5  # Starts with action

    # Cliffhanger check (last line shouldn't feel complete)
    last_line = lines[-1] if lines else ""
    if last_line.endswith(("...", "—", "…")):
        score += 15
        tags.append("EMOTIONAL_HOOK")
    elif last_line.endswith(".") and not any(w in last_line.lower() for w in ["but", "then", "until", "and then"]):
        score -= 10  # Feels complete

    # Viral potential
    if any(w in text.lower() for w in ["impossible", "stopped", "froze", "vanished", "screamed", "whispered", "moved"]):
        score += 10
        tags.append("HIGH_VIRAL")

    # Fast conversion potential
    if len(words) <= 40:
        tags.append("FAST_CONVERSION")

    passed = score >= 50
    return {"score": min(score, 100), "tags": tags, "passed": passed}


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_batch(req: GenerateBatchRequest, admin: dict = Depends(_admin_required)):
    """Generate a batch of high-quality stories using AI. Admin only."""
    categories_to_use = req.categories or list(CATEGORIES.keys())
    invalid = [c for c in categories_to_use if c not in CATEGORIES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {invalid}")

    count_per_cat = max(1, req.count // len(categories_to_use))
    remainder = req.count - (count_per_cat * len(categories_to_use))

    all_stories = []
    generated = 0

    for i, cat_key in enumerate(categories_to_use):
        cat = CATEGORIES[cat_key]
        batch_count = count_per_cat + (1 if i < remainder else 0)
        if batch_count <= 0:
            continue

        import random
        theme = random.choice(cat["themes"])
        style = random.choice(cat.get("styles", ANIMATION_STYLES))

        raw_stories = await _generate_stories_ai(cat_key, theme, batch_count)

        for story in raw_stories:
            quality = _quality_score(story)
            if not quality["passed"]:
                logger.info(f"[CONTENT_ENGINE] Rejected low-quality story: score={quality['score']}")
                continue

            story_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            doc = {
                "story_id": story_id,
                "title": story.get("title", "Untitled Hook"),
                "story_text": story.get("story", ""),
                "hook_line": story.get("hook_line", ""),
                "category": cat_key,
                "category_label": cat["label"],
                "theme": theme,
                "animation_style": style,
                "quality_score": quality["score"],
                "quality_tags": quality["tags"],
                "social_scripts": None,
                "is_featured": False,
                "is_published": False,
                "status": "draft",
                "created_by": admin["id"],
                "created_at": now,
                "pipeline_job_id": None,
            }

            await db.seed_stories.insert_one({k: v for k, v in doc.items() if k != "_id"})
            all_stories.append(doc)
            generated += 1

    # Generate social scripts for the batch
    if all_stories:
        scripts = await _generate_social_scripts(all_stories)
        for i, script in enumerate(scripts):
            if i < len(all_stories):
                await db.seed_stories.update_one(
                    {"story_id": all_stories[i]["story_id"]},
                    {"$set": {"social_scripts": script}},
                )
                all_stories[i]["social_scripts"] = script

    # Auto-publish if requested
    published = 0
    if req.auto_publish and all_stories:
        for story in all_stories:
            job_id = await _publish_to_pipeline(story, admin["id"])
            if job_id:
                published += 1

    return {
        "success": True,
        "generated": generated,
        "published": published,
        "rejected": sum(1 for _ in range(req.count)) - generated,
        "stories": [{k: v for k, v in s.items() if k != "_id"} for s in all_stories],
    }


@router.get("/list")
async def list_stories(
    category: Optional[str] = None,
    status: Optional[str] = None,
    featured: Optional[bool] = None,
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: dict = Depends(_admin_required),
):
    """List generated stories with filters. Admin only."""
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if featured is not None:
        query["is_featured"] = featured
    if tag:
        query["quality_tags"] = tag

    total = await db.seed_stories.count_documents(query)
    cursor = db.seed_stories.find(query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    stories = await cursor.to_list(length=limit)

    # Stats
    stats = {
        "total": await db.seed_stories.count_documents({}),
        "draft": await db.seed_stories.count_documents({"status": "draft"}),
        "published": await db.seed_stories.count_documents({"status": "published"}),
        "featured": await db.seed_stories.count_documents({"is_featured": True}),
        "by_category": {},
    }
    for cat_key in CATEGORIES:
        stats["by_category"][cat_key] = await db.seed_stories.count_documents({"category": cat_key})

    return {
        "success": True,
        "stories": stories,
        "total": total,
        "page": page,
        "limit": limit,
        "stats": stats,
    }


@router.post("/feature")
async def toggle_feature(req: FeatureRequest, admin: dict = Depends(_admin_required)):
    """Mark stories as featured / unfeatured. Admin only."""
    result = await db.seed_stories.update_many(
        {"story_id": {"$in": req.story_ids}},
        {"$set": {"is_featured": req.featured}},
    )
    return {"success": True, "modified": result.modified_count}


@router.post("/tag")
async def tag_story(req: QualityTagRequest, admin: dict = Depends(_admin_required)):
    """Add or update quality tag on a story."""
    valid_tags = ["HIGH_VIRAL", "EMOTIONAL_HOOK", "FAST_CONVERSION", "WEAK"]
    if req.tag not in valid_tags:
        raise HTTPException(status_code=400, detail=f"Invalid tag. Use: {valid_tags}")

    if req.tag == "WEAK":
        await db.seed_stories.update_one(
            {"story_id": req.story_id},
            {"$set": {"status": "rejected", "quality_tags": ["WEAK"]}},
        )
    else:
        await db.seed_stories.update_one(
            {"story_id": req.story_id},
            {"$addToSet": {"quality_tags": req.tag}},
        )
    return {"success": True}


@router.post("/publish/{story_id}")
async def publish_story(story_id: str, admin: dict = Depends(_admin_required)):
    """Publish a single story to the video pipeline."""
    story = await db.seed_stories.find_one({"story_id": story_id}, {"_id": 0})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.get("status") == "published":
        return {"success": True, "message": "Already published", "job_id": story.get("pipeline_job_id")}

    job_id = await _publish_to_pipeline(story, admin["id"])
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to publish to pipeline")

    return {"success": True, "job_id": job_id, "message": "Story queued for video generation"}


@router.post("/publish-batch")
async def publish_batch(admin: dict = Depends(_admin_required)):
    """Publish all unpublished draft stories to the pipeline."""
    drafts = await db.seed_stories.find(
        {"status": "draft", "quality_tags": {"$ne": "WEAK"}},
        {"_id": 0},
    ).to_list(length=200)

    published = 0
    for story in drafts:
        job_id = await _publish_to_pipeline(story, admin["id"])
        if job_id:
            published += 1

    return {"success": True, "published": published, "total_drafts": len(drafts)}


@router.delete("/{story_id}")
async def delete_story(story_id: str, admin: dict = Depends(_admin_required)):
    """Delete a story. Admin only."""
    result = await db.seed_stories.delete_one({"story_id": story_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"success": True}


@router.get("/social-scripts/{story_id}")
async def get_social_scripts(story_id: str, admin: dict = Depends(_admin_required)):
    """Get social media scripts for a story."""
    story = await db.seed_stories.find_one({"story_id": story_id}, {"_id": 0})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if not story.get("social_scripts"):
        scripts = await _generate_social_scripts([story])
        if scripts:
            await db.seed_stories.update_one(
                {"story_id": story_id},
                {"$set": {"social_scripts": scripts[0]}},
            )
            story["social_scripts"] = scripts[0]

    return {
        "success": True,
        "story_id": story_id,
        "title": story.get("title"),
        "story_text": story.get("story_text"),
        "social_scripts": story.get("social_scripts"),
    }


# ═══════════════════════════════════════════════════════════════
# PIPELINE PUBLISHING
# ═══════════════════════════════════════════════════════════════

async def _publish_to_pipeline(story: dict, admin_user_id: str) -> Optional[str]:
    """Queue a seed story into the pipeline_jobs collection for video generation."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    import hashlib
    slug_base = story.get("title", "hook-story").lower()
    slug_base = "".join(c if c.isalnum() or c == " " else "" for c in slug_base).strip().replace(" ", "-")[:40]
    slug = f"{slug_base}-{hashlib.md5(job_id.encode()).hexdigest()[:8]}"

    job = {
        "job_id": job_id,
        "user_id": admin_user_id,
        "title": story.get("title", "Untitled Hook"),
        "story_text": story.get("story_text", ""),
        "animation_style": story.get("animation_style", "cartoon_2d"),
        "pipeline_type": "story_video",
        "status": "QUEUED",
        "slug": slug,
        "is_seed_content": True,
        "seed_story_id": story.get("story_id"),
        "public": True,
        "category": story.get("category"),
        "quality_tags": story.get("quality_tags", []),
        "created_at": now,
    }

    try:
        await db.pipeline_jobs.insert_one({k: v for k, v in job.items() if k != "_id"})
        await db.seed_stories.update_one(
            {"story_id": story["story_id"]},
            {"$set": {"status": "published", "is_published": True, "pipeline_job_id": job_id}},
        )
        logger.info(f"[CONTENT_ENGINE] Published story {story['story_id'][:8]} → job {job_id[:8]}")
        return job_id
    except Exception as e:
        logger.error(f"[CONTENT_ENGINE] Publish failed: {e}")
        return None
