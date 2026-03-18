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


class ConfirmCharactersRequest(BaseModel):
    characters: list  # [{name, role, confirmed: bool, ...}]


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

    # ── AUTO-CHARACTER EXTRACTION: Score, deduplicate, prepare for confirmation ──
    extracted_characters = _score_and_deduplicate_characters(characters, ep1)

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
        "extraction_status": "pending_confirmation",
        "extracted_characters": extracted_characters,
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
        "extracted_characters": extracted_characters,
        "extraction_status": "pending_confirmation",
        "world": {
            "name": world.get("world_name", ""),
            "setting": world.get("setting_description", "")[:200],
        },
        "cliffhanger": ep1.get("cliffhanger", ""),
        "status": "planned",
    }


# ─── CHARACTER EXTRACTION: Scoring & Deduplication ────────────────────────────

MAIN_ROLES = {"protagonist", "antagonist", "main", "hero", "heroine", "villain"}
SUPPORTING_ROLES = {"sidekick", "mentor", "supporting", "ally", "companion", "guide"}
BACKGROUND_ROLES = {"background", "minor", "extra", "narrator", "crowd"}


def _score_and_deduplicate_characters(characters: list, episode_data: dict) -> list:
    """
    Score each character for confidence and role importance.
    Deduplicate by name similarity. Return max 3, confidence >= 0.7.
    """
    if not characters:
        return []

    # Count scene appearances for each character
    scenes = episode_data.get("scenes", [])
    char_scene_counts = {}
    for scene in scenes:
        for char_name in scene.get("characters", []):
            key = char_name.strip().lower()
            char_scene_counts[key] = char_scene_counts.get(key, 0) + 1

    total_scenes = max(len(scenes), 1)
    scored = []

    for c in characters:
        name = c.get("name", "").strip()
        if not name:
            continue

        role_raw = c.get("role", "").strip().lower()

        # Role importance score (0.0 - 0.4)
        if role_raw in MAIN_ROLES:
            role_score = 0.4
            role_label = "main"
        elif role_raw in SUPPORTING_ROLES:
            role_score = 0.25
            role_label = "supporting"
        elif role_raw in BACKGROUND_ROLES:
            role_score = 0.05
            role_label = "background"
        else:
            role_score = 0.2
            role_label = "supporting"

        # Scene presence score (0.0 - 0.3)
        appearances = char_scene_counts.get(name.lower(), 0)
        presence_score = min(appearances / total_scenes, 1.0) * 0.3

        # Detail richness score (0.0 - 0.3)
        detail_fields = [
            c.get("appearance"), c.get("clothing"), c.get("personality_traits"),
            c.get("goals"), c.get("fears"), c.get("consistency_prompt"),
        ]
        filled = sum(1 for f in detail_fields if f)
        detail_score = (filled / max(len(detail_fields), 1)) * 0.3

        confidence = round(role_score + presence_score + detail_score, 2)

        scored.append({
            "extraction_id": _uuid(),
            "name": name,
            "role": c.get("role", "unknown"),
            "role_importance": role_label,
            "confidence": confidence,
            "appearance": c.get("appearance", ""),
            "clothing": c.get("clothing", ""),
            "personality_traits": c.get("personality_traits", []),
            "goals": c.get("goals", ""),
            "fears": c.get("fears", ""),
            "voice_style": c.get("voice_style", ""),
            "consistency_prompt": c.get("consistency_prompt", ""),
            "scene_appearances": appearances,
        })

    # Sort by confidence descending
    scored.sort(key=lambda x: x["confidence"], reverse=True)

    # Deduplicate by name similarity
    deduped = []
    seen_names = set()
    for char in scored:
        name_key = char["name"].lower().replace("_", " ").replace("-", " ").strip()
        # Check for near-duplicates (Fox, Fox_2, The Fox)
        is_dup = False
        for seen in seen_names:
            if name_key in seen or seen in name_key:
                is_dup = True
                break
            # Simple word overlap check
            words_a = set(name_key.split())
            words_b = set(seen.split())
            if words_a and words_b and len(words_a & words_b) / max(len(words_a | words_b), 1) > 0.5:
                is_dup = True
                break
        if not is_dup:
            seen_names.add(name_key)
            deduped.append(char)

    # Filter: confidence >= 0.7, max 3
    qualified = [c for c in deduped if c["confidence"] >= 0.7][:3]

    # If no characters meet threshold, take top 2 if confidence >= 0.5
    if not qualified:
        qualified = [c for c in deduped if c["confidence"] >= 0.5][:2]

    return qualified


# ═══════════════════════════════════════════════════════════════════════════════
# API: CONFIRM EXTRACTED CHARACTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/confirm-characters")
async def confirm_characters(series_id: str, request: ConfirmCharactersRequest, user: dict = Depends(get_current_user)):
    """
    User confirms/edits extracted characters. Creates persistent character_profiles
    and attaches them to the series.
    """
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    confirmed_chars = [c for c in request.characters if c.get("confirmed", True)]
    if not confirmed_chars:
        # No characters confirmed — just mark as dismissed
        await db.story_series.update_one(
            {"series_id": series_id},
            {"$set": {"extraction_status": "dismissed", "updated_at": _now()}}
        )
        return {"success": True, "message": "No characters confirmed", "created": 0}

    from routes.characters import screen_safety

    created_ids = []
    for char in confirmed_chars[:3]:
        name = char.get("name", "").strip()
        if not name:
            continue

        # Safety check
        safety = screen_safety(name, char.get("appearance", ""))
        if not safety["safe"]:
            logger.warning(f"Character '{name}' failed safety: {safety['reason']}")
            continue

        character_id = _uuid()
        visual_bible_id = _uuid()
        safety_profile_id = _uuid()

        role = char.get("role", "hero")
        appearance = char.get("appearance", "")
        clothing = char.get("clothing", "")
        consistency_prompt = char.get("consistency_prompt", "")
        personality = ", ".join(char.get("personality_traits", [])) if isinstance(char.get("personality_traits"), list) else str(char.get("personality_traits", ""))

        # Build canonical description
        canonical = consistency_prompt or f"{name}: {appearance}. Wearing {clothing}." if appearance else f"{name}, a {role} character."

        profile = {
            "character_id": character_id,
            "series_id": series_id,
            "owner_user_id": user["id"],
            "name": name,
            "species_or_type": "character",
            "role": role,
            "age_band": "adult",
            "gender_presentation": None,
            "personality_summary": personality,
            "backstory_summary": None,
            "core_goals": char.get("goals", ""),
            "core_fears": char.get("fears", ""),
            "speech_style": char.get("voice_style", ""),
            "default_emotional_range": "neutral",
            "portrait_url": None,
            "status": "active",
            "auto_extracted": True,
            "source_series_id": series_id,
            "created_at": _now(),
            "updated_at": _now(),
        }

        visual_bible = {
            "visual_bible_id": visual_bible_id,
            "character_id": character_id,
            "version": 1,
            "canonical_description": canonical,
            "face_description": "",
            "hair_description": "",
            "body_description": appearance,
            "clothing_description": clothing,
            "color_palette": "",
            "accessories": "",
            "style_lock": series.get("style", "cartoon_2d"),
            "do_not_change_rules": [
                f"Always use same appearance for {name}",
                f"Same clothing: {clothing}" if clothing else f"Consistent outfit for {name}",
                f"Same art style: {series.get('style', 'cartoon_2d')}",
            ],
            "reference_asset_ids": [],
            "negative_constraints": ["no character redesign", "no style drift"],
            "created_at": _now(),
            "updated_at": _now(),
        }

        safety_profile = {
            "safety_profile_id": safety_profile_id,
            "character_id": character_id,
            "is_user_uploaded_likeness": False,
            "consent_status": "not_required",
            "is_minor_like": False,
            "disallowed_transformations": ["photorealistic", "nsfw", "violent"],
            "copyright_risk_flags": [],
            "celebrity_similarity_block": False,
            "brand_similarity_block": False,
            "protected_ip_similarity_block": False,
            "compliance_notes": "Auto-extracted from series Episode 1",
            "created_at": _now(),
        }

        await db.character_profiles.insert_one(profile)
        await db.character_visual_bibles.insert_one(visual_bible)
        await db.character_safety_profiles.insert_one(safety_profile)
        created_ids.append(character_id)

        logger.info(f"Auto-extracted character created: {character_id} '{name}' for series {series_id}")

    # Attach all to series
    if created_ids:
        await db.story_series.update_one(
            {"series_id": series_id},
            {
                "$set": {
                    "extraction_status": "confirmed",
                    "updated_at": _now(),
                },
                "$addToSet": {"attached_characters": {"$each": created_ids}},
            }
        )

    return {
        "success": True,
        "created": len(created_ids),
        "character_ids": created_ids,
        "extraction_status": "confirmed",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API: DISMISS EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/dismiss-extraction")
async def dismiss_extraction(series_id: str, user: dict = Depends(get_current_user)):
    """User dismisses auto-extracted characters."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0, "series_id": 1}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    await db.story_series.update_one(
        {"series_id": series_id},
        {"$set": {"extraction_status": "dismissed", "updated_at": _now()}}
    )
    return {"success": True, "extraction_status": "dismissed"}


# ═══════════════════════════════════════════════════════════════════════════════
# API: GET EXTRACTED CHARACTERS (for timeline banner re-display)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{series_id}/extracted-characters")
async def get_extracted_characters(series_id: str, user: dict = Depends(get_current_user)):
    """Get pending extracted characters for a series."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]},
        {"_id": 0, "extracted_characters": 1, "extraction_status": 1}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    return {
        "success": True,
        "extracted_characters": series.get("extracted_characters", []),
        "extraction_status": series.get("extraction_status", "none"),
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

    # Load attached persistent character memories
    attached_chars = series.get("attached_characters", [])
    char_memory_blocks = ""
    if attached_chars:
        from routes.characters import build_character_prompt_package, format_prompt_package_for_llm
        packages = []
        for cid in attached_chars[:5]:
            pkg = await build_character_prompt_package(cid, series_id)
            if pkg:
                packages.append(format_prompt_package_for_llm(pkg))
        if packages:
            char_memory_blocks = "\n\n---\n\n".join(packages)

    mem_clean = {
        k: v for k, v in (memory or {}).items()
        if k not in ("_id", "story_memory_id", "series_id", "updated_at")
    }
    wb_clean = {
        k: v for k, v in (world_bible or {}).items()
        if k not in ("_id", "world_bible_id", "series_id", "created_at", "updated_at")
    }

    # Build character section: merge persistent memory with series char bible
    char_section = json.dumps(char_bible.get('characters', []) if char_bible else [], indent=2)[:3000]
    if char_memory_blocks:
        char_section = f"""{char_memory_blocks}

### SERIES CHARACTER BIBLE (supplementary)
{char_section}"""
    else:
        char_section = f"{char_section}"

    system_prompt = f"""You are a professional story writer and series planner.

### SERIES CONTEXT
Title: {series.get('title', '')}
Genre: {series.get('genre', '')}
Audience: {series.get('audience_type', '')}
Style: {series.get('style', '')}

### CHARACTER BIBLE
{char_section}

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

    # Inject attached character visual locks into scene prompts
    attached_chars = series.get("attached_characters", [])
    char_visual_lock = ""
    if attached_chars:
        from routes.characters import build_character_prompt_package, CHARACTER_NEGATIVE_PROMPT
        for cid in attached_chars[:5]:
            pkg = await build_character_prompt_package(cid, series_id)
            if pkg and pkg.get("visual_lock_block"):
                vl = pkg["visual_lock_block"]
                char_visual_lock += (
                    f" {vl.get('canonical_description', '')}. "
                    f"Rules: {', '.join(vl.get('do_not_change_rules', [])[:4])}. "
                )

    # Enrich scene visual prompts with character visual locks
    if char_visual_lock:
        for scene in scenes:
            if scene.get("visual_prompt"):
                scene["visual_prompt"] = f"{scene['visual_prompt']}. CHARACTER LOCK: {char_visual_lock.strip()}"
        # Update plan with enriched scenes
        plan["scene_breakdown"] = scenes

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

    # Fetch rich context: memory, characters, world, recent episodes
    memory = await db.story_memories.find_one({"series_id": series_id}, {"_id": 0})
    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})
    recent_eps = await db.story_episodes.find(
        {"series_id": series_id},
        {"_id": 0, "title": 1, "episode_number": 1, "summary": 1, "cliffhanger": 1, "status": 1},
    ).sort("episode_number", -1).to_list(5)

    # Build structured context
    ctx_parts = [f"Series: {series.get('title')}", f"Genre: {series.get('genre')}"]

    # Characters with goals and relationships
    if char_bible and char_bible.get("characters"):
        chars = char_bible["characters"][:6]
        char_lines = []
        for c in chars:
            line = f"- {c.get('name', '?')} ({c.get('role', '?')}): {c.get('personality_traits', [])}"
            if c.get("goals"):
                line += f" | Goal: {c['goals']}"
            if c.get("backstory"):
                line += f" | Backstory: {str(c['backstory'])[:80]}"
            if c.get("relationships"):
                rels = c["relationships"]
                if isinstance(rels, list):
                    line += f" | Rels: {', '.join(str(r)[:40] for r in rels[:3])}"
                elif isinstance(rels, dict):
                    line += f" | Rels: {json.dumps(rels)[:120]}"
            char_lines.append(line)
        ctx_parts.append("\nCharacters:\n" + "\n".join(char_lines))

    # World setting
    if world_bible:
        world_info = f"\nWorld: {world_bible.get('world_name', '')}"
        if world_bible.get("setting_description"):
            world_info += f" - {world_bible['setting_description'][:150]}"
        if world_bible.get("lore"):
            world_info += f"\nLore: {json.dumps(world_bible['lore'])[:200]}"
        if world_bible.get("locations"):
            world_info += f"\nLocations: {json.dumps(world_bible['locations'])[:200]}"
        ctx_parts.append(world_info)

    # Recent episode arc
    if recent_eps:
        ep_lines = []
        for ep in reversed(recent_eps):
            line = f"Ep{ep.get('episode_number', '?')}: {ep.get('title', '?')} [{ep.get('status', '?')}]"
            if ep.get("summary"):
                line += f" - {ep['summary'][:100]}"
            if ep.get("cliffhanger"):
                line += f" | Cliffhanger: {ep['cliffhanger'][:80]}"
            ep_lines.append(line)
        ctx_parts.append("\nRecent Episodes:\n" + "\n".join(ep_lines))

    # Memory: open loops, pending hooks, character states
    if memory:
        mem_parts = []
        if memory.get("open_loops"):
            mem_parts.append(f"Open Loops: {json.dumps(memory['open_loops'][:5])}")
        if memory.get("pending_hooks"):
            mem_parts.append(f"Pending Hooks: {json.dumps(memory['pending_hooks'][:5])}")
        if memory.get("character_states"):
            mem_parts.append(f"Character States: {json.dumps(memory['character_states'])[:300]}")
        if memory.get("canon_events"):
            mem_parts.append(f"Canon Events (last 5): {json.dumps(memory['canon_events'][-5:])}")
        if mem_parts:
            ctx_parts.append("\nStory Memory:\n" + "\n".join(mem_parts))

    user_msg = "\n".join(ctx_parts)[:4000]

    system_msg = (
        "You are a master storyteller. Given the full context of a series — its characters, world, "
        "recent episodes, open plot threads, and emotional arc — generate 4 compelling next episode suggestions.\n\n"
        "Each suggestion should:\n"
        "- Reference specific characters, locations, or unresolved plot threads from the context\n"
        "- Vary in tone and direction (one continuation, one twist, one high-stakes, one wildcard)\n"
        "- Have a hook that makes the reader NEED to know what happens next\n\n"
        'Return ONLY valid JSON:\n'
        '{"suggestions":[{"title":"string","description":"2-3 sentences referencing characters/events",'
        '"direction_type":"continue | twist | stakes | custom",'
        '"excitement_level":"low | medium | high","emoji":"relevant_emoji"}]}'
    )

    try:
        result = await _llm_json(system_msg, user_msg, f"suggest_{series_id[:8]}")
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

            # Also write character memory for attached persistent characters
            try:
                series_doc = await db.story_series.find_one({"series_id": series_id}, {"_id": 0, "attached_characters": 1})
                attached = (series_doc or {}).get("attached_characters", [])
                if attached:
                    from routes.characters import write_character_memory
                    for cid in attached:
                        char_states = extracted.get("character_states", {})
                        # Find this character's state
                        profile = await db.character_profiles.find_one({"character_id": cid}, {"_id": 0, "name": 1})
                        char_name = (profile or {}).get("name", "")
                        emotion = "neutral"
                        goal = ""
                        if char_name and char_name.lower() in {k.lower(): k for k in char_states}:
                            real_key = {k.lower(): k for k in char_states}.get(char_name.lower(), char_name)
                            state = char_states.get(real_key, {})
                            if isinstance(state, dict):
                                emotion = state.get("emotion", state.get("mood", "neutral"))
                                goal = state.get("goal", "")
                            elif isinstance(state, str):
                                emotion = state

                        await write_character_memory(
                            character_id=cid,
                            episode_id=episode_id,
                            event_summary=episode.get("summary", ""),
                            emotion_state=str(emotion),
                            goal_state=str(goal),
                            open_loops=extracted.get("open_loops", []),
                            resolved_loops=extracted.get("resolved_loops", []),
                        )
            except Exception as cm_err:
                logger.warning(f"Character memory write failed: {cm_err}")

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


# ═══════════════════════════════════════════════════════════════════════════════
# API 15: GENERATE SERIES COVER IMAGE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{series_id}/generate-cover")
async def generate_series_cover(series_id: str, user: dict = Depends(get_current_user)):
    """Generate a cover image for a series based on its characters, world, and genre."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    char_bible = await db.character_bibles.find_one({"series_id": series_id}, {"_id": 0})
    world_bible = await db.world_bibles.find_one({"series_id": series_id}, {"_id": 0})

    # Build an image prompt from series data
    char_desc = ""
    if char_bible and char_bible.get("characters"):
        main_chars = [c for c in char_bible["characters"] if c.get("role") in ("protagonist", "sidekick")][:2]
        if not main_chars:
            main_chars = char_bible["characters"][:2]
        char_desc = ", ".join(
            f"{c.get('name', '')} ({c.get('appearance', '')[:80]}, {c.get('clothing', '')[:60]})"
            for c in main_chars
        )

    world_desc = ""
    if world_bible:
        world_desc = f"{world_bible.get('world_name', '')}: {world_bible.get('setting_description', '')[:120]}"

    style_map = {
        "cartoon_2d": "vibrant cartoon illustration, clean lines, bold colors",
        "anime": "anime art style, dramatic lighting",
        "watercolor": "watercolor painting style, soft edges",
        "comic": "comic book cover style, dynamic composition",
        "cinematic": "cinematic digital painting, dramatic lighting, movie poster quality",
    }
    style_prompt = style_map.get(series.get("style", ""), "vibrant digital illustration, professional quality")

    genre = series.get("genre", "adventure")
    title = series.get("title", "Untitled")
    description = series.get("description", "")[:200]

    prompt = (
        f"A stunning series cover illustration for '{title}', a {genre} story. "
        f"{description}. "
        f"Characters: {char_desc}. " if char_desc else f"A stunning series cover illustration for '{title}', a {genre} story. {description}. "
    )
    if world_desc:
        prompt += f"Setting: {world_desc}. "
    prompt += f"Style: {style_prompt}. Cinematic composition, eye-catching, no text or words on the image."

    try:
        from services.image_gen_direct import generate_image_direct
        api_key = _get_llm_key()
        image_bytes_list = await generate_image_direct(
            api_key=api_key,
            prompt=prompt[:4000],
            model="gpt-image-1",
            quality="medium",
            size="1024x1536",
            n=1,
        )
        if not image_bytes_list:
            raise HTTPException(status_code=500, detail="Image generation returned no results")

        # Upload to R2
        from services.cloudflare_r2_storage import upload_image_bytes
        success, cover_url = await upload_image_bytes(
            image_bytes_list[0],
            f"cover_{series_id[:8]}.png",
            series_id,
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload cover image")

        # Save URL to series
        await db.story_series.update_one(
            {"series_id": series_id},
            {"$set": {"cover_asset_url": cover_url, "updated_at": _now()}},
        )

        logger.info(f"Generated cover for series {series_id}: {cover_url}")
        return {"success": True, "cover_url": cover_url, "series_id": series_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cover generation failed for {series_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Cover generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# SERIES COMPLETION REWARDS — Retention Engine
# Triggers on story milestones. Offers emotional + functional rewards.
# Makes completion → new start loop.
# ═══════════════════════════════════════════════════════════════════════════════

MILESTONE_CONFIG = [
    {
        "threshold": 3,
        "title": "Story Taking Shape",
        "subtitle": "3 episodes crafted",
        "emotional_message": "Your story world is alive. The characters are finding their voice.",
        "rewards": [
            {"type": "unlock", "label": "Alternate Ending", "description": "Create a branching storyline"},
        ],
        "next_loop": {"type": "continue", "label": "Keep Building", "description": "Your story has momentum"},
    },
    {
        "threshold": 5,
        "title": "Story Complete",
        "subtitle": "A full story arc delivered",
        "emotional_message": "You did it. A complete story, beginning to end. Few creators make it this far.",
        "rewards": [
            {"type": "unlock", "label": "Start Season 2", "description": "Continue the saga with new arcs"},
            {"type": "unlock", "label": "Villain Origin Story", "description": "Tell the antagonist's side"},
        ],
        "next_loop": {"type": "season_2", "label": "Start Season 2", "description": "New arcs, same beloved characters"},
    },
    {
        "threshold": 10,
        "title": "Epic Saga",
        "subtitle": "10 episodes. Legendary.",
        "emotional_message": "This is no longer a story. This is a universe. You've built something extraordinary.",
        "rewards": [
            {"type": "unlock", "label": "Alternate Universe", "description": "What if everything was different?"},
            {"type": "unlock", "label": "Character Spinoff", "description": "Give a side character their own series"},
            {"type": "bonus_credits", "label": "50 Bonus Credits", "description": "A reward for dedication", "amount": 50},
        ],
        "next_loop": {"type": "spinoff", "label": "Create Spinoff Series", "description": "Your characters deserve new stories"},
    },
]


def _check_milestones(episode_count: int, claimed_milestones: list) -> list:
    """Check which milestones have been reached but not yet claimed."""
    unclaimed = []
    for m in MILESTONE_CONFIG:
        if episode_count >= m["threshold"] and m["threshold"] not in claimed_milestones:
            unclaimed.append(m)
    return unclaimed


@router.get("/{series_id}/rewards")
async def get_series_rewards(series_id: str, user: dict = Depends(get_current_user)):
    """Get reward status for a series: pending milestones and claimed rewards."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]},
        {"_id": 0, "series_id": 1, "title": 1}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    ep_count = await db.story_episodes.count_documents({"series_id": series_id})

    # Get claimed milestones
    reward_doc = await db.series_rewards.find_one(
        {"series_id": series_id, "user_id": user["id"]},
        {"_id": 0}
    )
    claimed = reward_doc.get("claimed_milestones", []) if reward_doc else []

    pending = _check_milestones(ep_count, claimed)

    # Progress to next milestone
    next_milestone = None
    for m in MILESTONE_CONFIG:
        if ep_count < m["threshold"]:
            next_milestone = {
                "threshold": m["threshold"],
                "title": m["title"],
                "episodes_remaining": m["threshold"] - ep_count,
                "progress": round(ep_count / m["threshold"] * 100),
            }
            break

    return {
        "success": True,
        "episode_count": ep_count,
        "series_title": series.get("title"),
        "pending_rewards": pending,
        "claimed_milestones": claimed,
        "next_milestone": next_milestone,
        "all_milestones": [
            {
                "threshold": m["threshold"],
                "title": m["title"],
                "claimed": m["threshold"] in claimed,
                "reached": ep_count >= m["threshold"],
            }
            for m in MILESTONE_CONFIG
        ],
    }


@router.post("/{series_id}/claim-reward")
async def claim_reward(series_id: str, milestone: int = 0, user: dict = Depends(get_current_user)):
    """Claim a specific milestone reward."""
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]},
        {"_id": 0, "series_id": 1, "title": 1}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    ep_count = await db.story_episodes.count_documents({"series_id": series_id})

    # Validate milestone exists and is reached
    milestone_config = next((m for m in MILESTONE_CONFIG if m["threshold"] == milestone), None)
    if not milestone_config:
        raise HTTPException(status_code=400, detail="Invalid milestone")
    if ep_count < milestone:
        raise HTTPException(status_code=400, detail=f"Need {milestone} episodes, have {ep_count}")

    # Check if already claimed
    reward_doc = await db.series_rewards.find_one(
        {"series_id": series_id, "user_id": user["id"]},
        {"_id": 0}
    )
    claimed = reward_doc.get("claimed_milestones", []) if reward_doc else []
    if milestone in claimed:
        raise HTTPException(status_code=400, detail="Already claimed")

    # Process rewards
    for reward in milestone_config.get("rewards", []):
        if reward["type"] == "bonus_credits" and reward.get("amount"):
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"credits": reward["amount"]}}
            )
            logger.info(f"Awarded {reward['amount']} bonus credits to {user['id']} for milestone {milestone}")

    # Record claim
    await db.series_rewards.update_one(
        {"series_id": series_id, "user_id": user["id"]},
        {
            "$addToSet": {"claimed_milestones": milestone},
            "$set": {"updated_at": _now()},
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )

    return {
        "success": True,
        "milestone": milestone,
        "title": milestone_config["title"],
        "subtitle": milestone_config["subtitle"],
        "emotional_message": milestone_config["emotional_message"],
        "rewards": milestone_config["rewards"],
        "next_loop": milestone_config["next_loop"],
    }
