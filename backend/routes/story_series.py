"""
Story Series Engine — Stateful Narrative System
================================================
Turns one-off creations into ongoing story universes with:
- Structured story memory (canon events, open loops, character states)
- Character/World bibles for visual + narrative consistency
- 2-step episode flow: PLAN → GENERATE (never skip planning)
- Return hooks (suggestions, cliffhangers, branches)

Pipeline: PLAN → GENERATE → VALIDATE → SAVE → MEMORY UPDATE

Collections: story_series, story_episodes, character_bibles, world_bibles, story_memories
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Query

from shared import db, get_current_user

logger = logging.getLogger("story_series")

router = APIRouter(prefix="/story-series", tags=["Story Series Engine"])

# ─── STATE MACHINE ────────────────────────────────────────────────────────────
# planned → generating → validating → ready / failed
EPISODE_STATUSES = ["planned", "generating", "validating", "ready", "failed"]

UNIVERSAL_NEGATIVE_PROMPT = (
    "low quality, blurry, pixelated, distorted, deformed, bad anatomy, bad proportions, "
    "extra limbs, extra fingers, missing fingers, mutated hands, poorly drawn face, "
    "asymmetrical face, duplicate characters, inconsistent character design, changing face, "
    "changing hairstyle, changing clothing, inconsistent proportions, inconsistent art style, "
    "unrealistic features, unnatural pose, stiff pose, lifeless expression, emotionless, "
    "flat lighting, overexposed, underexposed, noise, grain, artifacts, watermark, text, "
    "logo, caption, subtitle, cropped, cut off, out of frame, wrong perspective, "
    "bad composition, cluttered background, photorealistic, horror, scary, violent, gore"
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uuid():
    return str(uuid.uuid4())


def _get_llm_key():
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    return key


# ─── PYDANTIC MODELS ─────────────────────────────────────────────────────────

class CreateSeriesRequest(BaseModel):
    title: str
    initial_prompt: str
    genre: str = "adventure"
    audience: str = "kids_5_8"
    style: str = "cartoon_2d"
    tool: str = "story_video"


class PlanEpisodeRequest(BaseModel):
    direction_type: str = "continue"
    custom_prompt: Optional[str] = None


class GenerateEpisodeRequest(BaseModel):
    episode_id: str


class UpdateMemoryRequest(BaseModel):
    episode_id: str


# ─── LLM HELPERS ──────────────────────────────────────────────────────────────

async def _llm_json(system_msg: str, user_msg: str, session_id: str = "series") -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=_get_llm_key(),
        session_id=session_id,
        system_message=system_msg,
    )
    chat.with_model("openai", "gpt-4o-mini")
    response = await chat.send_message(UserMessage(text=user_msg))
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


# ═══════════════════════════════════════════════════════════════════════════════
# API 1: CREATE SERIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_series(request: CreateSeriesRequest, user: dict = Depends(get_current_user)):
    user_id = user["id"]
    user_plan = user.get("plan", "free")

    # Enforce series limit
    from config.monetization import check_series_limit
    current_count = await db.story_series.count_documents({"user_id": user_id, "status": {"$in": ["active", "paused"]}})
    limit_check = check_series_limit(user_plan, current_count)
    if not limit_check["can_create"]:
        raise HTTPException(status_code=403, detail=limit_check["upgrade_message"])

    series_id = _uuid()
    character_bible_id = _uuid()
    world_bible_id = _uuid()
    memory_id = _uuid()
    episode_id = _uuid()

    system_prompt = """You are a professional story series creator. Given an initial story prompt, generate the foundation for a multi-episode series.

Return ONLY valid JSON with this EXACT structure:
{
  "series_description": "2-3 sentence series description",
  "characters": [
    {
      "character_id": "char_1",
      "name": "string",
      "role": "protagonist | antagonist | sidekick | mentor",
      "appearance": "DETAILED physical description: hair color/style, eye color, skin tone, body build, height",
      "clothing": "EXACT outfit description with colors",
      "voice_style": "warm | energetic | calm | dramatic",
      "personality_traits": ["trait1", "trait2"],
      "goals": "character goal",
      "fears": "character fear",
      "consistency_prompt": "A complete visual prompt that locks this character's appearance for AI image generation"
    }
  ],
  "world": {
    "world_name": "string",
    "setting_description": "detailed setting",
    "visual_style": "color palette and art direction",
    "time_period": "string",
    "recurring_locations": ["location1", "location2"],
    "tone_rules": "overall tone",
    "continuity_constraints": ["rule1", "rule2"]
  },
  "episode_1": {
    "title": "episode title",
    "summary": "2-3 line summary",
    "scenes": [
      {
        "scene_number": 1,
        "scene_title": "string",
        "description": "what happens",
        "location": "where",
        "characters": ["char_name"],
        "emotion": "happy | fear | tension | wonder | sadness",
        "visual_prompt": "detailed prompt including full character appearance for consistency",
        "motion_hint": "camera movement or character action",
        "duration_seconds": 4
      }
    ],
    "cliffhanger": "what hooks the next episode"
  }
}"""

    user_prompt = f"""Create a story series foundation:
Title: {request.title}
Genre: {request.genre}
Audience: {request.audience}
Style: {request.style}
Initial Story: {request.initial_prompt}

Generate 4-5 scenes for Episode 1. Make characters visually distinct. Every scene visual_prompt MUST include full character appearance."""

    try:
        foundation = await _llm_json(system_prompt, user_prompt, f"create_{series_id[:8]}")
    except Exception as e:
        logger.error(f"LLM foundation generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate series foundation")

    characters = foundation.get("characters", [])
    world = foundation.get("world", {})
    ep1 = foundation.get("episode_1", {})

    char_bible = {
        "character_bible_id": character_bible_id,
        "series_id": series_id,
        "characters": characters,
        "created_at": _now(),
        "updated_at": _now(),
    }

    world_bible = {
        "world_bible_id": world_bible_id,
        "series_id": series_id,
        "world_name": world.get("world_name", request.title + " World"),
        "setting_description": world.get("setting_description", ""),
        "visual_style": world.get("visual_style", request.style),
        "time_period": world.get("time_period", "fantasy"),
        "recurring_locations": world.get("recurring_locations", []),
        "tone_rules": world.get("tone_rules", ""),
        "continuity_constraints": world.get("continuity_constraints", []),
        "created_at": _now(),
        "updated_at": _now(),
    }

    char_states = {}
    for i, c in enumerate(characters):
        char_states[c.get("name", f"char_{i}")] = {
            "emotion": "neutral",
            "goal": c.get("goals", ""),
            "location": "starting point",
            "status": "active",
        }

    story_memory = {
        "story_memory_id": memory_id,
        "series_id": series_id,
        "canon_events": [],
        "open_loops": [],
        "resolved_loops": [],
        "character_states": char_states,
        "relationship_graph": [],
        "world_state": [],
        "tone": world.get("tone_rules", "adventure"),
        "forbidden_changes": [
            f"Do not change {c.get('name','')}'s appearance" for c in characters
        ] + ["Do not change world setting randomly", "Maintain consistent art style"],
        "episode_summaries": [],
        "pending_hooks": [ep1.get("cliffhanger", "What happens next?")],
        "updated_after_episode_id": None,
        "updated_at": _now(),
    }

    episode = {
        "episode_id": episode_id,
        "series_id": series_id,
        "parent_episode_id": None,
        "branch_type": "mainline",
        "episode_number": 1,
        "title": ep1.get("title", f"{request.title} - Episode 1"),
        "summary": ep1.get("summary", ""),
        "story_prompt": request.initial_prompt,
        "episode_goal": "Introduce characters and world",
        "cliffhanger": ep1.get("cliffhanger", ""),
        "status": "planned",
        "plan": {
            "scene_breakdown": ep1.get("scenes", []),
            "character_arcs": [],
            "visual_style_constraints": {
                "style": request.style,
                "color_palette": world.get("visual_style", ""),
                "animation_style": "auto",
            },
            "consistency_rules": [
                f"Character {c.get('name','')}: {c.get('consistency_prompt','')}"
                for c in characters
            ],
            "negative_constraints": UNIVERSAL_NEGATIVE_PROMPT.split(", "),
            "cliffhanger": {
                "type": "mystery",
                "description": ep1.get("cliffhanger", ""),
            },
        },
        "tool_used": request.tool,
        "output_type": "video" if request.tool == "story_video" else "comic",
        "output_asset_url": None,
        "thumbnail_url": None,
        "scene_count": len(ep1.get("scenes", [])),
        "view_count": 0,
        "remix_count": 0,
        "share_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }

    series = {
        "series_id": series_id,
        "user_id": user_id,
        "title": request.title,
        "description": foundation.get("series_description", ""),
        "status": "active",
        "root_tool": request.tool,
        "genre": request.genre,
        "audience_type": request.audience,
        "style": request.style,
        "character_bible_id": character_bible_id,
        "world_bible_id": world_bible_id,
        "story_memory_id": memory_id,
        "episode_count": 1,
        "branch_count": 0,
        "cover_asset_url": None,
        "created_at": _now(),
        "updated_at": _now(),
    }

    await db.story_series.insert_one(series)
    await db.story_episodes.insert_one(episode)
    await db.character_bibles.insert_one(char_bible)
    await db.world_bibles.insert_one(world_bible)
    await db.story_memories.insert_one(story_memory)

    return {
        "success": True,
        "series_id": series_id,
        "episode_id": episode_id,
        "title": request.title,
        "description": foundation.get("series_description", ""),
        "episode_title": episode["title"],
        "scene_count": episode["scene_count"],
        "characters": [
            {"name": c.get("name"), "role": c.get("role"), "appearance": c.get("appearance", "")}
            for c in characters
        ],
        "world": {
            "name": world.get("world_name", ""),
            "setting": world.get("setting_description", "")[:200],
        },
        "cliffhanger": ep1.get("cliffhanger", ""),
        "status": "planned",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 2: MY SERIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/my-series")
async def get_my_series(user: dict = Depends(get_current_user)):
    series_list = await db.story_series.find(
        {"user_id": user["id"], "status": {"$in": ["active", "paused"]}},
        {"_id": 0},
    ).sort("updated_at", -1).to_list(length=50)

    for s in series_list:
        latest_ep = await db.story_episodes.find_one(
            {"series_id": s["series_id"]},
            {"_id": 0, "title": 1, "episode_number": 1, "status": 1, "thumbnail_url": 1, "cliffhanger": 1},
            sort=[("episode_number", -1)],
        )
        s["latest_episode"] = latest_ep

        # Compulsion data: unfinished count, next episode, hooks
        all_eps = await db.story_episodes.find(
            {"series_id": s["series_id"]},
            {"_id": 0, "status": 1, "episode_number": 1, "episode_id": 1},
        ).to_list(100)
        ready_count = sum(1 for e in all_eps if e.get("status") == "ready")
        planned_eps = [e for e in all_eps if e.get("status") == "planned"]
        next_planned = planned_eps[0] if planned_eps else None
        s["ready_count"] = ready_count
        s["total_episodes"] = len(all_eps)
        s["next_episode"] = next_planned
        s["episodes_left"] = len(all_eps) - ready_count

        memory = await db.story_memories.find_one(
            {"series_id": s["series_id"]}, {"_id": 0, "pending_hooks": 1, "open_loops": 1}
        )
        s["next_hook"] = (memory.get("pending_hooks") or [None])[0] if memory else None
        s["open_loops_count"] = len(memory.get("open_loops", [])) if memory else 0

    return {"success": True, "series": series_list, "total": len(series_list)}


# ═══════════════════════════════════════════════════════════════════════════════
# API 3: GET SERIES (full details + timeline)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{series_id}")
async def get_series(series_id: str, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episodes = await db.story_episodes.find(
        {"series_id": series_id}, {"_id": 0}
    ).sort("episode_number", 1).to_list(100)

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})

    return {
        "success": True,
        "series": series,
        "episodes": episodes,
        "character_bible": char_bible,
        "world_bible": world_bible,
        "story_memory": memory,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 4: PLAN EPISODE (LLM-powered — the brain)
# Step 1 of: PLAN → GENERATE → VALIDATE → SAVE → MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/plan-episode")
async def plan_episode(series_id: str, request: PlanEpisodeRequest, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Enforce episode limit
    from config.monetization import check_episode_limit
    user_plan = user.get("plan", "free")
    ep_count = await db.story_episodes.count_documents({"series_id": series_id})
    ep_check = check_episode_limit(user_plan, ep_count)
    if not ep_check["can_create"]:
        raise HTTPException(status_code=403, detail=ep_check["upgrade_message"])

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    last_ep = await db.story_episodes.find_one(
        {"series_id": series_id}, {"_id": 0}, sort=[("episode_number", -1)]
    )
    next_num = (last_ep.get("episode_number", 0) if last_ep else 0) + 1

    mem_clean = {
        k: v for k, v in (memory or {}).items()
        if k not in ("_id", "story_memory_id", "series_id", "updated_at")
    }
    wb_clean = {
        k: v for k, v in (world_bible or {}).items()
        if k not in ("_id", "world_bible_id", "series_id", "created_at", "updated_at")
    }

    system_prompt = f"""You are a professional story writer and series planner.

### SERIES CONTEXT
Title: {series.get('title', '')}
Genre: {series.get('genre', '')}
Audience: {series.get('audience_type', '')}
Style: {series.get('style', '')}

### CHARACTER BIBLE
{json.dumps(char_bible.get('characters', []) if char_bible else [], indent=2)[:3000]}

### WORLD BIBLE
{json.dumps(wb_clean, indent=2)[:2000]}

### STORY MEMORY
{json.dumps(mem_clean, indent=2)[:3000]}

### DIRECTION: {request.direction_type}
{f'Custom: {request.custom_prompt}' if request.custom_prompt else ''}

### INSTRUCTIONS
1. Maintain strict continuity with previous events.
2. Do NOT change character appearance or personality.
3. Use existing unresolved plot points.
4. Create a strong emotional arc.
5. Build towards a cliffhanger ending.
6. Every scene visual_prompt MUST include full character appearance descriptions.

Return ONLY valid JSON:
{{
  "episode_title": "string",
  "summary": "2-3 line summary",
  "theme": "theme",
  "tone": "light | dark | suspense | comedy",
  "character_arcs": [{{"name":"string","start_state":"string","end_state":"string","goal":"string","conflict":"string"}}],
  "scene_breakdown": [
    {{
      "scene_number": 1,
      "scene_title": "string",
      "description": "what happens",
      "location": "string",
      "characters": ["name"],
      "emotion": "happy | fear | tension | wonder | sadness",
      "visual_prompt": "DETAILED prompt with character appearances",
      "motion_hint": "camera/character movement",
      "dialogue": "optional",
      "duration_seconds": 4
    }}
  ],
  "continuity_notes": ["what must be maintained"],
  "cliffhanger": {{"type":"mystery | danger | emotional","description":"hook"}}
}}"""

    user_msg = (
        f"Previous episode: {last_ep.get('summary', 'First episode') if last_ep else 'None yet'}\n\n"
        f"Generate episode {next_num} plan."
    )

    try:
        plan = await _llm_json(system_prompt, user_msg, f"plan_{series_id[:8]}_{next_num}")
    except Exception as e:
        logger.error(f"Episode planning failed: {e}")
        raise HTTPException(status_code=500, detail="Episode planning failed")

    episode_id = _uuid()
    cliffhanger_raw = plan.get("cliffhanger", "")
    cliffhanger_text = (
        cliffhanger_raw.get("description", "") if isinstance(cliffhanger_raw, dict) else str(cliffhanger_raw)
    )

    episode = {
        "episode_id": episode_id,
        "series_id": series_id,
        "parent_episode_id": last_ep.get("episode_id") if last_ep else None,
        "branch_type": "mainline" if request.direction_type in ("continue", "stakes") else request.direction_type,
        "episode_number": next_num,
        "title": plan.get("episode_title", f"Episode {next_num}"),
        "summary": plan.get("summary", ""),
        "story_prompt": request.custom_prompt or f"Continue: {request.direction_type}",
        "episode_goal": plan.get("theme", ""),
        "cliffhanger": cliffhanger_text,
        "status": "planned",
        "plan": plan,
        "tool_used": series.get("root_tool", "story_video"),
        "output_type": "video" if series.get("root_tool") == "story_video" else "comic",
        "output_asset_url": None,
        "thumbnail_url": None,
        "scene_count": len(plan.get("scene_breakdown", [])),
        "view_count": 0,
        "remix_count": 0,
        "share_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }

    await db.story_episodes.insert_one(episode)

    # Update series episode count
    await db.story_series.update_one(
        {"series_id": series_id},
        {"$inc": {"episode_count": 1}, "$set": {"updated_at": _now()}},
    )

    return {
        "success": True,
        "episode_id": episode_id,
        "episode_number": next_num,
        "plan": plan,
        "status": "planned",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 5: GENERATE EPISODE (uses plan + existing pipeline)
# Step 2 of: PLAN → GENERATE → VALIDATE → SAVE → MEMORY
# Reuses existing Story Video / Comic pipelines. Does NOT rebuild them.
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/generate-episode")
async def generate_episode(series_id: str, request: GenerateEpisodeRequest, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episode = await db.story_episodes.find_one(
        {"episode_id": request.episode_id, "series_id": series_id}, {"_id": 0}
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.get("status") not in ("planned", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Episode is '{episode.get('status')}', expected 'planned' or 'failed'.",
        )

    plan = episode.get("plan", {})
    scenes = plan.get("scene_breakdown", [])
    if not scenes:
        raise HTTPException(status_code=400, detail="No scene breakdown in plan. Run plan-episode first.")

    # Build story text from plan for pipeline consumption
    story_text = episode.get("summary", "")
    if not story_text:
        story_text = " ".join(s.get("description", "") for s in scenes)

    # STATE: planned → generating
    await db.story_episodes.update_one(
        {"episode_id": request.episode_id},
        {"$set": {"status": "generating", "updated_at": _now()}},
    )

    tool = series.get("root_tool", "story_video")
    user_id = user["id"]
    user_plan = user.get("plan", "free")

    try:
        # Reuse existing pipeline infrastructure for proper credit handling + job structure
        from services.pipeline_engine import create_pipeline_job
        from services.pipeline_worker import enqueue_job

        result = await create_pipeline_job(
            user_id=user_id,
            title=episode.get("title", "Series Episode"),
            story_text=story_text,
            animation_style=series.get("style", "cartoon_2d"),
            age_group=series.get("audience_type", "kids_5_8"),
            voice_preset="narrator_warm",
            user_plan=user_plan,
        )

        job_id = result["job_id"]

        # Link pipeline job to series episode
        await db.pipeline_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "series_episode_id": request.episode_id,
                "series_id": series_id,
            }},
        )

        # Store job reference on episode
        await db.story_episodes.update_one(
            {"episode_id": request.episode_id},
            {"$set": {"pipeline_job_id": job_id, "updated_at": _now()}},
        )

        # Enqueue for processing
        await enqueue_job(job_id, user_id=user_id, user_plan=user_plan)

        return {
            "success": True,
            "episode_id": request.episode_id,
            "pipeline_job_id": job_id,
            "credits_charged": result.get("credits_charged", 0),
            "status": "generating",
            "tool": tool,
        }

    except ValueError as e:
        # Credit check or copyright failure from create_pipeline_job
        await db.story_episodes.update_one(
            {"episode_id": request.episode_id},
            {"$set": {"status": "failed", "updated_at": _now()}},
        )
        error_msg = str(e)
        if "credit" in error_msg.lower():
            raise HTTPException(status_code=402, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        await db.story_episodes.update_one(
            {"episode_id": request.episode_id},
            {"$set": {"status": "failed", "updated_at": _now()}},
        )
        logger.error(f"Generate episode failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start generation")


# ═══════════════════════════════════════════════════════════════════════════════
# API 6: SUGGESTIONS (AI-powered next episode ideas)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/suggestions")
async def get_suggestions(series_id: str, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    mem_ctx = json.dumps(
        {k: v for k, v in (memory or {}).items() if k not in ("_id", "story_memory_id", "series_id", "updated_at")},
        indent=2,
    )[:3000]

    system_msg = (
        'Generate 4 exciting next episode suggestions. Return ONLY valid JSON:\n'
        '{"suggestions":[{"title":"string","description":"1-2 sentences",'
        '"direction_type":"continue | twist | stakes | custom",'
        '"excitement_level":"low | medium | high","emoji":"relevant_emoji"}]}'
    )

    try:
        result = await _llm_json(
            system_msg,
            f"Series: {series.get('title')}\nGenre: {series.get('genre')}\n\nMemory:\n{mem_ctx}",
            f"suggest_{series_id[:8]}",
        )
        return {"success": True, "suggestions": result.get("suggestions", [])}
    except Exception:
        return {
            "success": True,
            "suggestions": [
                {"title": "Continue the Adventure", "description": "Pick up where we left off", "direction_type": "continue", "excitement_level": "medium", "emoji": "arrow_forward"},
                {"title": "Plot Twist!", "description": "An unexpected turn changes everything", "direction_type": "twist", "excitement_level": "high", "emoji": "cyclone"},
                {"title": "Raise the Stakes", "description": "Things get intense and dangerous", "direction_type": "stakes", "excitement_level": "high", "emoji": "fire"},
                {"title": "New Direction", "description": "Take the story somewhere unexpected", "direction_type": "custom", "excitement_level": "medium", "emoji": "sparkles"},
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# API 7: UPDATE MEMORY (atomic with retry — after episode completes)
# Final step: PLAN → GENERATE → VALIDATE → SAVE → MEMORY UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/update-memory")
async def update_story_memory(series_id: str, body: UpdateMemoryRequest, user: dict = Depends(get_current_user)):
    episode = await db.story_episodes.find_one(
        {"episode_id": body.episode_id, "series_id": series_id}, {"_id": 0}
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    result = await _update_memory_internal(series_id, body.episode_id)
    if not result:
        raise HTTPException(status_code=500, detail="Memory update failed after retries")
    return {"success": True, "memory_updated": True}


# ═══════════════════════════════════════════════════════════════════════════════
# API 8: EPISODE STATUS (with strict validation)
# STATE MACHINE: planned → generating → ready / failed
# HARD RULE: no READY without real output_url
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{series_id}/episode/{episode_id}/status")
async def check_episode_status(series_id: str, episode_id: str, user: dict = Depends(get_current_user)):
    episode = await db.story_episodes.find_one(
        {"episode_id": episode_id, "series_id": series_id}, {"_id": 0}
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    pj_id = episode.get("pipeline_job_id")
    pj = None
    if pj_id:
        pj = await db.pipeline_jobs.find_one(
            {"job_id": pj_id},
            {"_id": 0, "status": 1, "output_url": 1, "thumbnail_url": 1, "scene_images": 1, "progress": 1},
        )

    if pj:
        new_status = episode.get("status")
        out_url = pj.get("output_url")
        thumb = pj.get("thumbnail_url")

        # STRICT VALIDATION: no READY without real output
        if pj["status"] == "COMPLETED" and out_url and out_url.startswith("http"):
            new_status = "ready"
            if not thumb and pj.get("scene_images"):
                scene_imgs = pj["scene_images"]
                if isinstance(scene_imgs, dict):
                    for sn in sorted(scene_imgs.keys()):
                        urls = scene_imgs[sn]
                        if isinstance(urls, list) and urls:
                            thumb = urls[0]
                            break
                        elif isinstance(urls, str):
                            thumb = urls
                            break
        elif pj["status"] == "COMPLETED" and not out_url:
            # COMPLETED without output = FAILED. No exceptions.
            new_status = "failed"
        elif pj["status"] == "FAILED":
            new_status = "failed"
        elif pj["status"] in ("PROCESSING", "QUEUED"):
            new_status = "generating"

        if new_status != episode.get("status"):
            upd = {"status": new_status, "updated_at": _now()}
            if new_status == "ready" and out_url:
                upd["output_asset_url"] = out_url
            if thumb:
                upd["thumbnail_url"] = thumb
            await db.story_episodes.update_one({"episode_id": episode_id}, {"$set": upd})

            # Auto-update memory + series when episode becomes ready
            if new_status == "ready":
                await db.story_series.update_one(
                    {"series_id": series_id},
                    {"$set": {"updated_at": _now()}, "$inc": {"episode_count": 0}},
                )
                try:
                    await _update_memory_internal(series_id, episode_id)
                except Exception as e:
                    logger.warning(f"Auto memory update failed for {episode_id}: {e}")

            episode["status"] = new_status
            episode["output_asset_url"] = out_url if new_status == "ready" else None
            episode["thumbnail_url"] = thumb

    return {
        "success": True,
        "episode_id": episode_id,
        "status": episode.get("status"),
        "pipeline_status": pj.get("status") if pj else None,
        "output_url": episode.get("output_asset_url"),
        "thumbnail_url": episode.get("thumbnail_url"),
        "progress": pj.get("progress") if pj else None,
    }


# ─── INTERNAL: Atomic memory update with retry ───────────────────────────────

async def _update_memory_internal(series_id: str, episode_id: str) -> bool:
    """Internal memory update with 3 retry attempts. Returns True on success."""
    episode = await db.story_episodes.find_one(
        {"episode_id": episode_id, "series_id": series_id}, {"_id": 0}
    )
    if not episode:
        return False

    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    if not memory:
        return False

    system_msg = (
        "Extract structured story memory. Maintain previous memory and ADD new facts.\n"
        "Return ONLY valid JSON:\n"
        '{"canon_events":[],"open_loops":[],"resolved_loops":[],'
        '"character_states":{},"world_state":[],"pending_hooks":[]}'
    )

    ep_text = (
        f"Episode {episode.get('episode_number')}: {episode.get('title')}\n"
        f"Summary: {episode.get('summary', '')}\n"
        f"Cliffhanger: {episode.get('cliffhanger', '')}\n"
        f"Previous Canon: {json.dumps(memory.get('canon_events', [])[:10])}\n"
        f"Previous Loops: {json.dumps(memory.get('open_loops', [])[:5])}\n"
        f"Character States: {json.dumps(memory.get('character_states', {}))}"
    )

    plan = episode.get("plan", {})
    if plan.get("scene_breakdown"):
        ep_text += "\nScenes:\n" + "\n".join(
            f"S{s.get('scene_number', i+1)}: {s.get('description', '')}"
            for i, s in enumerate(plan["scene_breakdown"])
        )

    for attempt in range(3):
        try:
            extracted = await _llm_json(system_msg, ep_text, f"mem_{series_id[:8]}_{attempt}")

            # Deduplicate lists safely (some items may be dicts)
            def _dedup(lst):
                seen = set()
                result = []
                for item in lst:
                    key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
                    if key not in seen:
                        seen.add(key)
                        result.append(item)
                return result

            updated = {
                "canon_events": _dedup(
                    memory.get("canon_events", []) + extracted.get("canon_events", [])
                ),
                "open_loops": extracted.get("open_loops", memory.get("open_loops", [])),
                "resolved_loops": _dedup(
                    memory.get("resolved_loops", []) + extracted.get("resolved_loops", [])
                ),
                "character_states": {
                    **memory.get("character_states", {}),
                    **extracted.get("character_states", {}),
                },
                "world_state": _dedup(
                    memory.get("world_state", []) + extracted.get("world_state", [])
                ),
                "pending_hooks": extracted.get("pending_hooks", []),
                "episode_summaries": memory.get("episode_summaries", []) + [
                    {"episode_number": episode.get("episode_number"), "summary": episode.get("summary", "")}
                ],
                "updated_after_episode_id": episode_id,
                "updated_at": _now(),
            }

            await db.story_memories.update_one({"series_id": series_id}, {"$set": updated})
            logger.info(f"Memory updated for series {series_id} after episode {episode_id} (attempt {attempt+1})")
            return True
        except Exception as e:
            logger.warning(f"Memory update attempt {attempt+1} failed for {series_id}: {e}")

    logger.error(f"Memory update failed after 3 attempts for series {series_id}")
    return False



# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: BRANCHING, PUBLIC SERIES, GROWTH HOOKS
# ═══════════════════════════════════════════════════════════════════════════════


# ─── API 9: BRANCH FROM EPISODE ──────────────────────────────────────────────

class BranchEpisodeRequest(BaseModel):
    parent_episode_id: str
    direction_type: str = "twist"
    custom_prompt: Optional[str] = None


@router.post("/{series_id}/branch-episode")
async def branch_episode(series_id: str, request: BranchEpisodeRequest, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    parent = await db.story_episodes.find_one(
        {"episode_id": request.parent_episode_id, "series_id": series_id}, {"_id": 0}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent episode not found")

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})

    # Count existing branches from this parent
    branch_count = await db.story_episodes.count_documents(
        {"series_id": series_id, "parent_episode_id": request.parent_episode_id, "branch_type": {"$ne": "mainline"}}
    )

    mem_clean = {
        k: v for k, v in (memory or {}).items()
        if k not in ("_id", "story_memory_id", "series_id", "updated_at")
    }

    system_prompt = f"""You are a story writer creating an ALTERNATE BRANCH from an existing episode.
This is NOT a continuation — it's a "what if" from a specific point.

### SERIES: {series.get('title', '')} ({series.get('genre', '')})
### PARENT EPISODE: {parent.get('title', '')}
Summary: {parent.get('summary', '')}
Cliffhanger: {parent.get('cliffhanger', '')}

### CHARACTER BIBLE
{json.dumps(char_bible.get('characters', []) if char_bible else [], indent=2)[:2000]}

### STORY MEMORY (canon up to branch point)
{json.dumps(mem_clean, indent=2)[:2000]}

### BRANCH DIRECTION: {request.direction_type}
{f'Custom: {request.custom_prompt}' if request.custom_prompt else ''}

Create a branching episode that diverges from the parent. Maintain character consistency.

Return ONLY valid JSON:
{{
  "episode_title": "string",
  "summary": "2-3 line summary",
  "branch_reason": "what diverges from the original path",
  "scene_breakdown": [
    {{
      "scene_number": 1,
      "scene_title": "string",
      "description": "what happens",
      "location": "string",
      "characters": ["name"],
      "emotion": "happy | fear | tension | wonder | sadness",
      "visual_prompt": "DETAILED prompt with character appearances",
      "motion_hint": "camera/character movement",
      "duration_seconds": 4
    }}
  ],
  "cliffhanger": {{"type":"mystery | danger | emotional","description":"hook"}}
}}"""

    try:
        plan = await _llm_json(system_prompt, f"Create alternate branch #{branch_count + 1}", f"branch_{series_id[:8]}")
    except Exception as e:
        logger.error(f"Branch planning failed: {e}")
        raise HTTPException(status_code=500, detail="Branch planning failed")

    episode_id = _uuid()
    cliffhanger_raw = plan.get("cliffhanger", "")
    cliffhanger_text = cliffhanger_raw.get("description", "") if isinstance(cliffhanger_raw, dict) else str(cliffhanger_raw)

    episode = {
        "episode_id": episode_id,
        "series_id": series_id,
        "parent_episode_id": request.parent_episode_id,
        "branch_type": request.direction_type,
        "episode_number": parent.get("episode_number", 1),
        "title": plan.get("episode_title", f"Branch: {request.direction_type}"),
        "summary": plan.get("summary", ""),
        "story_prompt": request.custom_prompt or f"Branch: {request.direction_type}",
        "episode_goal": plan.get("branch_reason", ""),
        "cliffhanger": cliffhanger_text,
        "status": "planned",
        "plan": plan,
        "tool_used": series.get("root_tool", "story_video"),
        "output_type": "video" if series.get("root_tool") == "story_video" else "comic",
        "output_asset_url": None,
        "thumbnail_url": None,
        "scene_count": len(plan.get("scene_breakdown", [])),
        "is_branch": True,
        "view_count": 0,
        "remix_count": 0,
        "share_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }

    await db.story_episodes.insert_one(episode)
    await db.story_series.update_one(
        {"series_id": series_id},
        {"$inc": {"branch_count": 1, "episode_count": 1}, "$set": {"updated_at": _now()}},
    )

    return {
        "success": True,
        "episode_id": episode_id,
        "branch_type": request.direction_type,
        "plan": plan,
        "status": "planned",
    }


# ─── API 10: PUBLIC SERIES VIEW (no auth) ────────────────────────────────────

@router.get("/public/{series_id}")
async def get_public_series(series_id: str):
    series = await db.story_series.find_one(
        {"series_id": series_id, "is_public": True}, {"_id": 0, "user_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found or not public")

    episodes = await db.story_episodes.find(
        {"series_id": series_id, "status": "ready"},
        {"_id": 0, "plan": 0},
    ).sort("episode_number", 1).to_list(100)

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0, "series_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0, "series_id": 0})

    # Track view
    await db.story_series.update_one({"series_id": series_id}, {"$inc": {"view_count": 1}})

    return {
        "success": True,
        "series": series,
        "episodes": episodes,
        "character_bible": char_bible,
        "world_bible": world_bible,
    }


# ─── API 11: TOGGLE PUBLIC / SHARE ───────────────────────────────────────────

class ShareRequest(BaseModel):
    is_public: bool = True


@router.post("/{series_id}/share")
async def toggle_share(series_id: str, body: ShareRequest, user: dict = Depends(get_current_user)):
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    await db.story_series.update_one(
        {"series_id": series_id},
        {"$set": {"is_public": body.is_public, "updated_at": _now()}},
    )

    share_url = f"/series/{series_id}" if body.is_public else None
    return {"success": True, "is_public": body.is_public, "share_url": share_url}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: DEEPER BIBLES, EMOTIONAL MEMORY
# ═══════════════════════════════════════════════════════════════════════════════


# ─── API 12: ENHANCE CHARACTER BIBLE ─────────────────────────────────────────

@router.post("/{series_id}/enhance-characters")
async def enhance_character_bible(series_id: str, user: dict = Depends(get_current_user)):
    """Use LLM to deepen character bibles with backstory, relationships, arc tracking."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})

    characters = char_bible.get("characters", []) if char_bible else []
    if not characters:
        raise HTTPException(status_code=400, detail="No characters to enhance")

    system_prompt = """Enhance these characters with deeper backstory, relationships, and arc tracking.
For EACH character, add: backstory, relationships (with other characters), emotional_baseline, growth_arc, signature_phrases.

Return ONLY valid JSON:
{"characters": [
  {
    "name": "existing name",
    "role": "existing role",
    "appearance": "existing appearance",
    "clothing": "existing clothing",
    "consistency_prompt": "existing prompt",
    "backstory": "2-3 sentence origin/history",
    "relationships": [{"with": "other char name", "type": "friend | rival | mentor | family", "dynamic": "description"}],
    "emotional_baseline": "their default emotional state and how they typically react",
    "growth_arc": "where this character is heading narratively",
    "signature_phrases": ["catchphrase or typical way of speaking"],
    "fears": "deepest fear",
    "goals": "core motivation"
  }
]}"""

    user_msg = (
        f"Series: {series.get('title')}\n"
        f"Characters: {json.dumps(characters, indent=2)[:3000]}\n"
        f"Story so far: {json.dumps(memory.get('canon_events', [])[:10]) if memory else '[]'}"
    )

    try:
        enhanced = await _llm_json(system_prompt, user_msg, f"enhance_char_{series_id[:8]}")
        new_chars = enhanced.get("characters", characters)

        # Merge: keep existing fields, add new ones
        merged = []
        for orig in characters:
            match = next((c for c in new_chars if c.get("name") == orig.get("name")), {})
            merged.append({**orig, **{k: v for k, v in match.items() if v}})

        await db.character_bibles.update_one(
            {"series_id": series_id},
            {"$set": {"characters": merged, "enhanced": True, "updated_at": _now()}},
        )
        return {"success": True, "characters": merged}
    except Exception as e:
        logger.error(f"Character enhancement failed: {e}")
        raise HTTPException(status_code=500, detail="Enhancement failed")


# ─── API 13: ENHANCE WORLD BIBLE ─────────────────────────────────────────────

@router.post("/{series_id}/enhance-world")
async def enhance_world_bible(series_id: str, user: dict = Depends(get_current_user)):
    """Use LLM to deepen world bible with lore, rules, locations."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    if not world_bible:
        raise HTTPException(status_code=400, detail="No world bible found")

    system_prompt = """Enhance this world with deeper lore, rules, and locations.

Return ONLY valid JSON:
{
  "world_name": "existing name",
  "setting_description": "enhanced description",
  "visual_style": "existing style",
  "lore": "2-3 paragraph world history and mythology",
  "rules": ["rule that governs this world"],
  "locations": [{"name": "string", "description": "string", "significance": "string", "mood": "string"}],
  "factions": [{"name": "string", "description": "string", "alignment": "string"}],
  "secrets": ["hidden world detail that can drive future plots"],
  "atmosphere": "sensory description of the world's feeling"
}"""

    user_msg = f"World: {json.dumps({k: v for k, v in world_bible.items() if k not in ('_id', 'world_bible_id', 'series_id', 'created_at', 'updated_at')}, indent=2)[:2000]}"

    try:
        enhanced = await _llm_json(system_prompt, user_msg, f"enhance_world_{series_id[:8]}")
        update_data = {k: v for k, v in enhanced.items() if v}
        update_data["enhanced"] = True
        update_data["updated_at"] = _now()

        await db.world_bibles.update_one({"series_id": series_id}, {"$set": update_data})
        return {"success": True, "world": {**world_bible, **update_data}}
    except Exception as e:
        logger.error(f"World enhancement failed: {e}")
        raise HTTPException(status_code=500, detail="Enhancement failed")


# ─── API 14: EMOTIONAL ARC ───────────────────────────────────────────────────

@router.get("/{series_id}/emotional-arc")
async def get_emotional_arc(series_id: str, user: dict = Depends(get_current_user)):
    """Calculate and return the emotional arc across all episodes."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episodes = await db.story_episodes.find(
        {"series_id": series_id, "branch_type": "mainline"},
        {"_id": 0, "episode_number": 1, "title": 1, "summary": 1, "plan": 1, "status": 1},
    ).sort("episode_number", 1).to_list(100)

    EMOTION_SCORES = {
        "happy": 0.8, "wonder": 0.7, "hope": 0.6,
        "neutral": 0.5, "tension": 0.4, "sadness": 0.3,
        "fear": 0.2, "anger": 0.15, "despair": 0.1,
    }

    arc = []
    for ep in episodes:
        scenes = ep.get("plan", {}).get("scene_breakdown", [])
        if not scenes:
            arc.append({
                "episode": ep.get("episode_number"),
                "title": ep.get("title", ""),
                "avg_emotion": 0.5,
                "dominant_emotion": "neutral",
                "tension": 0.5,
            })
            continue

        emotions = [s.get("emotion", "neutral") for s in scenes]
        scores = [EMOTION_SCORES.get(e.lower(), 0.5) for e in emotions]
        dominant = max(set(emotions), key=emotions.count) if emotions else "neutral"

        arc.append({
            "episode": ep.get("episode_number"),
            "title": ep.get("title", ""),
            "avg_emotion": round(sum(scores) / len(scores), 2),
            "dominant_emotion": dominant,
            "tension": round(1 - (sum(scores) / len(scores)), 2),
            "scene_emotions": emotions,
        })

    return {"success": True, "series_id": series_id, "arc": arc}
