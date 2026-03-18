"""
Story Series Engine — Stateful Narrative System
================================================
Turns one-off creations into ongoing story universes with:
- Structured story memory (canon events, open loops, character states)
- Character/World bibles for visual + narrative consistency
- 2-step episode flow: PLAN → GENERATE (never skip planning)
- Return hooks (suggestions, cliffhangers, branches)

Collections: story_series, story_episodes, character_bibles, world_bibles, story_memories
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

logger = logging.getLogger("story_series")

router = APIRouter(prefix="/story-series", tags=["Story Series Engine"])

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

# ─── LLM HELPERS ──────────────────────────────────────────────────────────────

async def _llm_json(system_msg: str, user_msg: str, session_id: str = "series") -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=_get_llm_key(), session_id=session_id, system_message=system_msg, model="gpt-4o-mini")
    response = await chat.send_message_async(UserMessage(content=user_msg))
    text = response.content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


# ═══════════════════════════════════════════════════════════════════════════════
# API 1: CREATE SERIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_series(request: CreateSeriesRequest, req=None):
    from shared import db
    from routes.auth import get_current_user

    user = await get_current_user(req)
    user_id = user["id"]

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
        "created_at": _now(), "updated_at": _now()
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
        "created_at": _now(), "updated_at": _now()
    }

    char_states = {}
    for i, c in enumerate(characters):
        char_states[c.get("name", f"char_{i}")] = {
            "emotion": "neutral", "goal": c.get("goals", ""),
            "location": "starting point", "status": "active"
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
        "forbidden_changes": [f"Do not change {c.get('name','')}'s appearance" for c in characters] + ["Do not change world setting randomly", "Maintain consistent art style"],
        "episode_summaries": [],
        "pending_hooks": [ep1.get("cliffhanger", "What happens next?")],
        "updated_after_episode_id": None,
        "updated_at": _now()
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
            "visual_style_constraints": {"style": request.style, "color_palette": world.get("visual_style", ""), "animation_style": "auto"},
            "consistency_rules": [f"Character {c.get('name','')}: {c.get('consistency_prompt','')}" for c in characters],
            "negative_constraints": UNIVERSAL_NEGATIVE_PROMPT.split(", "),
            "cliffhanger": {"type": "mystery", "description": ep1.get("cliffhanger", "")}
        },
        "tool_used": request.tool,
        "output_type": "video" if request.tool == "story_video" else "comic",
        "output_asset_url": None,
        "thumbnail_url": None,
        "scene_count": len(ep1.get("scenes", [])),
        "view_count": 0, "remix_count": 0, "share_count": 0,
        "created_at": _now(), "updated_at": _now()
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
        "created_at": _now(), "updated_at": _now()
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
        "characters": [{"name": c.get("name"), "role": c.get("role"), "appearance": c.get("appearance", "")} for c in characters],
        "world": {"name": world.get("world_name", ""), "setting": world.get("setting_description", "")[:200]},
        "cliffhanger": ep1.get("cliffhanger", ""),
        "status": "planned"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 2: MY SERIES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/my-series")
async def get_my_series(req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    series_list = await db.story_series.find(
        {"user_id": user["id"], "status": {"$in": ["active", "paused"]}},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(length=50)

    for s in series_list:
        latest_ep = await db.story_episodes.find_one(
            {"series_id": s["series_id"]},
            {"_id": 0, "title": 1, "episode_number": 1, "status": 1, "thumbnail_url": 1, "cliffhanger": 1},
            sort=[("episode_number", -1)]
        )
        s["latest_episode"] = latest_ep
        memory = await db.story_memories.find_one({"series_id": s["series_id"]}, {"_id": 0, "pending_hooks": 1})
        s["next_hook"] = (memory.get("pending_hooks") or [None])[0] if memory else None

    return {"success": True, "series": series_list, "total": len(series_list)}


# ═══════════════════════════════════════════════════════════════════════════════
# API 3: GET SERIES (full details + timeline)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{series_id}")
async def get_series(series_id: str, req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    series = await db.story_series.find_one({"series_id": series_id, "user_id": user["id"]}, {"_id": 0})
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episodes = await db.story_episodes.find({"series_id": series_id}, {"_id": 0}).sort("episode_number", 1).to_list(100)
    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})

    return {
        "success": True,
        "series": series,
        "episodes": episodes,
        "character_bible": char_bible,
        "world_bible": world_bible,
        "story_memory": memory
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 4: PLAN EPISODE (LLM-powered — the brain)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/plan-episode")
async def plan_episode(series_id: str, request: PlanEpisodeRequest, req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    series = await db.story_series.find_one({"series_id": series_id, "user_id": user["id"]}, {"_id": 0})
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    last_ep = await db.story_episodes.find_one({"series_id": series_id}, {"_id": 0}, sort=[("episode_number", -1)])
    next_num = (last_ep.get("episode_number", 0) if last_ep else 0) + 1

    mem_clean = {k: v for k, v in (memory or {}).items() if k not in ('_id', 'story_memory_id', 'series_id', 'updated_at')}
    wb_clean = {k: v for k, v in (world_bible or {}).items() if k not in ('_id', 'world_bible_id', 'series_id', 'created_at', 'updated_at')}

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

    user_msg = f"Previous episode: {last_ep.get('summary', 'First episode') if last_ep else 'None yet'}\n\nGenerate episode {next_num} plan."

    try:
        plan = await _llm_json(system_prompt, user_msg, f"plan_{series_id[:8]}_{next_num}")
    except Exception as e:
        logger.error(f"Episode planning failed: {e}")
        raise HTTPException(status_code=500, detail="Episode planning failed")

    episode_id = _uuid()
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
        "cliffhanger": plan.get("cliffhanger", {}).get("description", "") if isinstance(plan.get("cliffhanger"), dict) else str(plan.get("cliffhanger", "")),
        "status": "planned",
        "plan": plan,
        "tool_used": series.get("root_tool", "story_video"),
        "output_type": "video" if series.get("root_tool") == "story_video" else "comic",
        "output_asset_url": None, "thumbnail_url": None,
        "scene_count": len(plan.get("scene_breakdown", [])),
        "view_count": 0, "remix_count": 0, "share_count": 0,
        "created_at": _now(), "updated_at": _now()
    }

    await db.story_episodes.insert_one(episode)

    return {"success": True, "episode_id": episode_id, "episode_number": next_num, "plan": plan, "status": "planned"}


# ═══════════════════════════════════════════════════════════════════════════════
# API 5: GENERATE EPISODE (uses plan + existing pipeline)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/generate-episode")
async def generate_episode(series_id: str, request: GenerateEpisodeRequest, req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    series = await db.story_series.find_one({"series_id": series_id, "user_id": user["id"]}, {"_id": 0})
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    episode = await db.story_episodes.find_one({"episode_id": request.episode_id, "series_id": series_id}, {"_id": 0})
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.get("status") != "planned":
        raise HTTPException(status_code=400, detail=f"Episode is '{episode.get('status')}', expected 'planned'")

    plan = episode.get("plan", {})
    scenes = plan.get("scene_breakdown", [])
    if not scenes:
        raise HTTPException(status_code=400, detail="No scene breakdown. Plan first.")

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    characters = char_bible.get("characters", []) if char_bible else []
    char_consistency = "\n".join([f"Character {c.get('name','')}: {c.get('consistency_prompt', c.get('appearance',''))}" for c in characters])

    await db.story_episodes.update_one({"episode_id": request.episode_id}, {"$set": {"status": "generating", "updated_at": _now()}})

    # Create pipeline job for the existing Story Video engine
    job_id = _uuid()
    pipeline_job = {
        "job_id": job_id,
        "user_id": user["id"],
        "title": episode.get("title", "Series Episode"),
        "story_text": episode.get("summary", ""),
        "status": "QUEUED",
        "style": series.get("style", "cartoon_2d"),
        "age_group": series.get("audience_type", "kids_5_8"),
        "language": "english",
        "voice_preset": "warm_narrator",
        "animation_style": plan.get("visual_style_constraints", {}).get("animation_style", "auto") if isinstance(plan.get("visual_style_constraints"), dict) else "auto",
        "estimated_scenes": len(scenes),
        "series_episode_id": request.episode_id,
        "series_id": series_id,
        "pre_planned_scenes": [
            {
                "scene_number": s.get("scene_number", i + 1),
                "title": s.get("scene_title", f"Scene {i+1}"),
                "visual_prompt": f"{s.get('visual_prompt', s.get('description', ''))}\n\nCharacter Consistency:\n{char_consistency}\n\nAvoid: {UNIVERSAL_NEGATIVE_PROMPT}",
                "narration": s.get("description", ""),
                "emotion": s.get("emotion", "neutral"),
                "motion_hint": s.get("motion_hint", "slow zoom"),
                "duration": s.get("duration_seconds", 4),
                "characters": s.get("characters", []),
                "location": s.get("location", "")
            }
            for i, s in enumerate(scenes)
        ],
        "created_at": _now(), "updated_at": _now()
    }

    await db.pipeline_jobs.insert_one(pipeline_job)

    try:
        from services.pipeline_engine import enqueue_pipeline_job
        await enqueue_pipeline_job(db, job_id)
    except Exception as e:
        logger.warning(f"Enqueue failed, job created: {e}")

    await db.story_episodes.update_one({"episode_id": request.episode_id}, {"$set": {"pipeline_job_id": job_id, "updated_at": _now()}})

    return {"success": True, "episode_id": request.episode_id, "pipeline_job_id": job_id, "status": "generating"}


# ═══════════════════════════════════════════════════════════════════════════════
# API 6: SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/suggestions")
async def get_suggestions(series_id: str, req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    series = await db.story_series.find_one({"series_id": series_id, "user_id": user["id"]}, {"_id": 0})
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    mem_ctx = json.dumps({k: v for k, v in (memory or {}).items() if k not in ('_id', 'story_memory_id', 'series_id', 'updated_at')}, indent=2)[:3000]

    system_msg = """Generate 4 exciting next episode suggestions. Return ONLY valid JSON:
{"suggestions":[{"title":"string","description":"1-2 sentences","direction_type":"continue | twist | stakes | custom","excitement_level":"low | medium | high","emoji":"relevant_emoji"}]}"""

    try:
        result = await _llm_json(system_msg, f"Series: {series.get('title')}\nGenre: {series.get('genre')}\n\nMemory:\n{mem_ctx}", f"suggest_{series_id[:8]}")
        return {"success": True, "suggestions": result.get("suggestions", [])}
    except Exception:
        return {"success": True, "suggestions": [
            {"title": "Continue the Adventure", "description": "Pick up where we left off", "direction_type": "continue", "excitement_level": "medium", "emoji": "arrow_forward"},
            {"title": "Plot Twist!", "description": "An unexpected turn", "direction_type": "twist", "excitement_level": "high", "emoji": "cyclone"},
            {"title": "Raise the Stakes", "description": "Things get intense", "direction_type": "stakes", "excitement_level": "high", "emoji": "fire"},
            {"title": "New Direction", "description": "Take the story somewhere unexpected", "direction_type": "custom", "excitement_level": "medium", "emoji": "sparkles"},
        ]}


# ═══════════════════════════════════════════════════════════════════════════════
# API 7: UPDATE MEMORY (after episode completes)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/update-memory")
async def update_story_memory(series_id: str, episode_id: str = None, req=None):
    from shared import db

    episode = await db.story_episodes.find_one({"episode_id": episode_id, "series_id": series_id}, {"_id": 0})
    if not episode:
        return {"success": False, "error": "Episode not found"}

    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    if not memory:
        return {"success": False, "error": "Memory not found"}

    system_msg = """Extract structured story memory. Maintain previous memory and ADD new facts.
Return ONLY valid JSON:
{"canon_events":[],"open_loops":[],"resolved_loops":[],"character_states":{},"world_state":[],"pending_hooks":[]}"""

    ep_text = f"""Episode {episode.get('episode_number')}: {episode.get('title')}
Summary: {episode.get('summary', '')}
Cliffhanger: {episode.get('cliffhanger', '')}
Previous Canon: {json.dumps(memory.get('canon_events', [])[:10])}
Previous Loops: {json.dumps(memory.get('open_loops', [])[:5])}
Character States: {json.dumps(memory.get('character_states', {}))}"""

    plan = episode.get("plan", {})
    if plan.get("scene_breakdown"):
        ep_text += "\nScenes:\n" + "\n".join([f"S{s.get('scene_number',i+1)}: {s.get('description','')}" for i, s in enumerate(plan["scene_breakdown"])])

    try:
        extracted = await _llm_json(system_msg, ep_text, f"mem_{series_id[:8]}")
    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        return {"success": False, "error": "Memory extraction failed"}

    updated = {
        "canon_events": list(set(memory.get("canon_events", []) + extracted.get("canon_events", []))),
        "open_loops": extracted.get("open_loops", memory.get("open_loops", [])),
        "resolved_loops": list(set(memory.get("resolved_loops", []) + extracted.get("resolved_loops", []))),
        "character_states": {**memory.get("character_states", {}), **extracted.get("character_states", {})},
        "world_state": list(set(memory.get("world_state", []) + extracted.get("world_state", []))),
        "pending_hooks": extracted.get("pending_hooks", []),
        "episode_summaries": memory.get("episode_summaries", []) + [{"episode_number": episode.get("episode_number"), "summary": episode.get("summary", "")}],
        "updated_after_episode_id": episode_id,
        "updated_at": _now()
    }

    await db.story_memories.update_one({"series_id": series_id}, {"$set": updated})
    return {"success": True, "memory_updated": True}


# ═══════════════════════════════════════════════════════════════════════════════
# API 8: EPISODE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{series_id}/episode/{episode_id}/status")
async def check_episode_status(series_id: str, episode_id: str, req=None):
    from shared import db
    from routes.auth import get_current_user
    user = await get_current_user(req)

    episode = await db.story_episodes.find_one({"episode_id": episode_id, "series_id": series_id}, {"_id": 0})
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    pj_id = episode.get("pipeline_job_id")
    pj = None
    if pj_id:
        pj = await db.pipeline_jobs.find_one({"job_id": pj_id}, {"_id": 0, "status": 1, "output_url": 1, "thumbnail_url": 1, "scene_images": 1, "progress": 1})

    if pj:
        new_status = episode.get("status")
        out_url = pj.get("output_url")
        thumb = pj.get("thumbnail_url")

        if pj["status"] == "COMPLETED" and out_url:
            new_status = "ready"
            if not thumb and pj.get("scene_images"):
                for sn in sorted(pj["scene_images"].keys()) if isinstance(pj["scene_images"], dict) else []:
                    urls = pj["scene_images"][sn]
                    if isinstance(urls, list) and urls:
                        thumb = urls[0]; break
                    elif isinstance(urls, str):
                        thumb = urls; break
        elif pj["status"] == "COMPLETED" and not out_url:
            new_status = "partial_ready"
        elif pj["status"] == "FAILED":
            new_status = "failed"
        elif pj["status"] in ("PROCESSING", "QUEUED"):
            new_status = "generating"

        if new_status != episode.get("status"):
            upd = {"status": new_status, "updated_at": _now()}
            if out_url: upd["output_asset_url"] = out_url
            if thumb: upd["thumbnail_url"] = thumb
            await db.story_episodes.update_one({"episode_id": episode_id}, {"$set": upd})

            if new_status == "ready":
                await db.story_series.update_one({"series_id": series_id}, {"$set": {"updated_at": _now()}})
                try:
                    await update_story_memory(series_id, episode_id, req)
                except Exception:
                    pass

            episode["status"] = new_status
            episode["output_asset_url"] = out_url
            episode["thumbnail_url"] = thumb

    return {
        "success": True,
        "episode_id": episode_id,
        "status": episode.get("status"),
        "pipeline_status": pj.get("status") if pj else None,
        "output_url": episode.get("output_asset_url"),
        "thumbnail_url": episode.get("thumbnail_url"),
        "progress": pj.get("progress") if pj else None
    }
