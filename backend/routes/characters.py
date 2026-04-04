"""
AI Character Memory — Structured Persistence System
====================================================
Not a prompt shortcut. A stateful identity system with:
- Identity layer (profile)
- Visual consistency layer (visual bible)
- Narrative memory layer (memory log)
- Safety layer (copyright/compliance)
- Generation contract (prompt package builder)

Collections: character_profiles, character_visual_bibles,
             character_memory_logs, character_safety_profiles
"""

import os
import json
import uuid
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends

from shared import db, get_current_user

logger = logging.getLogger("characters")

router = APIRouter(prefix="/characters", tags=["AI Character Memory"])


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).isoformat()

def _uuid():
    return str(uuid.uuid4())

def _get_llm_key():
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")
    return key

async def _llm_json(system_msg, user_msg, session_id):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=_get_llm_key(), session_id=session_id, system_message=system_msg)
    chat.with_model("openai", "gpt-4o-mini")
    response = await chat.send_message(UserMessage(text=user_msg))
    text = response.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY LAYER — 3-tier protection
# ═══════════════════════════════════════════════════════════════════════════════

# Tier 1: Exact blocked names (copyrighted characters, brands, celebrities)
BLOCKED_IP_NAMES = {
    # Disney/Pixar
    "elsa", "anna", "moana", "rapunzel", "ariel", "simba", "nemo", "dory",
    "woody", "buzz lightyear", "lightning mcqueen", "ratatouille", "wall-e",
    "baymax", "stitch", "tinker bell", "cinderella", "snow white", "mulan",
    "pocahontas", "jasmine", "belle", "aurora", "tiana", "merida",
    # Marvel
    "spider-man", "spiderman", "iron man", "ironman", "captain america",
    "thor", "hulk", "black widow", "hawkeye", "black panther", "thanos",
    "wolverine", "deadpool", "doctor strange", "scarlet witch", "vision",
    "ant-man", "wasp", "shang-chi", "moon knight", "groot", "rocket raccoon",
    # DC
    "batman", "superman", "wonder woman", "flash", "aquaman", "green lantern",
    "harley quinn", "joker", "catwoman", "robin", "cyborg", "batgirl",
    # Anime/Manga
    "naruto", "goku", "luffy", "pikachu", "ash ketchum", "sailor moon",
    "vegeta", "sasuke", "kakashi", "sakura haruno", "itachi",
    "light yagami", "eren jaeger", "mikasa", "levi ackerman",
    "saitama", "deku", "todoroki", "bakugo", "all might",
    # Other major IP
    "mario", "luigi", "link", "zelda", "sonic", "mega man",
    "harry potter", "hermione", "dumbledore", "voldemort",
    "gandalf", "frodo", "aragorn", "legolas", "sauron",
    "darth vader", "luke skywalker", "yoda", "obi-wan", "palpatine",
    "shrek", "spongebob", "bugs bunny", "mickey mouse", "donald duck",
    "winnie the pooh", "peppa pig", "thomas the tank engine",
    "hello kitty", "doraemon", "totoro",
}

# Tier 2: Similarity patterns (phrases that signal IP mimicry)
SIMILARITY_PATTERNS = [
    r"\blike\s+(spider[- ]?man|batman|superman|elsa|naruto|goku|mario|sonic)\b",
    r"\bsimilar\s+to\s+(spider[- ]?man|batman|elsa|naruto|goku|disney|marvel|dc)\b",
    r"\b(marvel|dc|disney|pixar|nintendo|pokemon)\s+style\s+hero\b",
    r"\b(exact|identical)\s+(copy|clone|replica)\b",
    r"\bcosplay(?:ing)?\s+as\s+",
    r"\bdressed\s+as\s+(spider[- ]?man|batman|superman|elsa|naruto)\b",
    r"\b(spider[- ]?man|batman|superman)\s+but\b",
]

# Tier 3: Celebrity/real-person patterns
CELEBRITY_PATTERNS = [
    r"\b(looks?\s+like|resembl(?:es?|ing)|based\s+on)\s+[A-Z][a-z]+\s+[A-Z][a-z]+",
    r"\b(celebrity|famous\s+person|real\s+person|actor|actress|singer)\b",
]


from services.rewrite_engine import safe_rewrite
from services.rewrite_engine.policy_engine import evaluate_policy, Decision


def screen_safety(name: str, description: str, appearance: str = "") -> dict:
    """
    Safety screening with safe rewrite + policy engine.
    Returns {safe: bool, reason: str, tier: int, rewritten_name: str, rewritten_description: str, rewritten_appearance: str}.
    Rewrites trademark/copyright terms. Only blocks genuinely dangerous content via policy engine.
    """
    combined = f"{name} {description} {appearance}"

    # Policy engine — block genuinely dangerous content
    policy = evaluate_policy(combined)
    if policy.decision == Decision.BLOCK:
        return {
            "safe": False,
            "reason": policy.block_reason,
            "tier": 0,
        }

    # Rewrite risky trademark/copyright terms instead of blocking
    name_result = safe_rewrite(name)
    desc_result = safe_rewrite(description)
    appear_result = safe_rewrite(appearance)

    was_rewritten = name_result.was_rewritten or desc_result.was_rewritten or appear_result.was_rewritten

    return {
        "safe": True,
        "reason": name_result.user_note if was_rewritten else None,
        "tier": 0,
        "was_rewritten": was_rewritten,
        "rewritten_name": name_result.rewritten_text,
        "rewritten_description": desc_result.rewritten_text,
        "rewritten_appearance": appear_result.rewritten_text,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL CHARACTER NEGATIVE PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

CHARACTER_NEGATIVE_PROMPT = (
    "low quality, blurry, pixelated, distorted, deformed, bad anatomy, bad proportions, "
    "extra limbs, extra fingers, missing fingers, mutated hands, poorly drawn face, "
    "asymmetrical face, duplicate characters, inconsistent character design, changing face, "
    "changing hairstyle, changing clothing, inconsistent proportions, inconsistent art style, "
    "unrealistic features, unnatural pose, stiff pose, lifeless expression, emotionless, "
    "flat lighting, overexposed, underexposed, noise, grain, artifacts, watermark, text, "
    "logo, caption, subtitle, cropped, cut off, out of frame, wrong perspective, "
    "bad composition, photorealistic human face, celebrity resemblance, "
    "copyrighted character resemblance, trademark mascot resemblance"
)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateCharacterRequest(BaseModel):
    name: str
    species_or_type: str = "human"
    role: str = "hero"
    age_band: str = "adult"
    gender_presentation: Optional[str] = None
    personality_summary: Optional[str] = None
    backstory_summary: Optional[str] = None
    core_goals: Optional[str] = None
    core_fears: Optional[str] = None
    speech_style: Optional[str] = None
    # Visual
    face_description: Optional[str] = None
    hair_description: Optional[str] = None
    body_description: Optional[str] = None
    clothing_description: Optional[str] = None
    color_palette: Optional[str] = None
    accessories: Optional[str] = None
    style_lock: str = "cartoon_2d"
    # Series link
    series_id: Optional[str] = None
    # Raw UI field aliases (accept both old and new field names)
    personality: Optional[str] = None
    style: Optional[str] = None
    voice: Optional[str] = None

    def resolved_personality(self) -> str:
        return self.personality_summary or self.personality or "A unique character"

    def resolved_style(self) -> str:
        STYLE_MAP = {
            "anime": "anime", "cartoon": "cartoon_2d", "realistic": "cinematic",
            "watercolor": "watercolor", "pixel art": "comic", "chibi": "cartoon_2d",
        }
        raw = self.style_lock if self.style_lock != "cartoon_2d" else (self.style or "cartoon_2d")
        return STYLE_MAP.get(raw.lower(), raw.lower()) if raw else "cartoon_2d"

    def resolved_gender(self) -> str:
        return self.gender_presentation or self.voice or ""


class UpdateCharacterRequest(BaseModel):
    name: Optional[str] = None
    personality_summary: Optional[str] = None
    backstory_summary: Optional[str] = None
    core_goals: Optional[str] = None
    core_fears: Optional[str] = None
    speech_style: Optional[str] = None
    status: Optional[str] = None


class AttachCharacterRequest(BaseModel):
    character_id: str


# ═══════════════════════════════════════════════════════════════════════════════
# API 1: CREATE CHARACTER
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/create")
async def create_character(request: CreateCharacterRequest, user: dict = Depends(get_current_user)):
    """Create an original character with LLM-generated visual bible."""
    user_id = user["id"]
    # Resolve aliased fields (accept both raw UI and mapped field names)
    resolved_personality = request.resolved_personality()
    resolved_style = request.resolved_style()
    resolved_gender = request.resolved_gender()
    logger.info(f"[CHARACTER] Create request from user={user_id}: name={request.name} style={resolved_style} gender={resolved_gender} personality={resolved_personality[:50]}")

    # Safety screening
    appearance_text = " ".join(filter(None, [
        request.face_description, request.hair_description,
        request.body_description, request.clothing_description,
    ]))
    safety = screen_safety(request.name, resolved_personality, appearance_text)
    if not safety["safe"]:
        raise HTTPException(status_code=422, detail={
            "error": "safety_block",
            "reason": safety["reason"],
            "tier": safety["tier"],
        })
    # Apply rewritten values if terms were sanitized
    if safety.get("was_rewritten"):
        request.name = safety["rewritten_name"]
        resolved_personality = safety["rewritten_description"]

    character_id = _uuid()
    visual_bible_id = _uuid()
    safety_profile_id = _uuid()

    # Override request fields with resolved values before passing to LLM
    request.personality_summary = resolved_personality
    request.style_lock = resolved_style
    request.gender_presentation = resolved_gender

    # Generate visual bible via LLM if user didn't provide full details
    visual_bible_data = await _generate_visual_bible(request, character_id)

    # Character profile
    profile = {
        "character_id": character_id,
        "series_id": request.series_id,
        "owner_user_id": user_id,
        "name": request.name,
        "species_or_type": request.species_or_type,
        "role": request.role,
        "age_band": request.age_band,
        "gender_presentation": resolved_gender,
        "personality_summary": resolved_personality,
        "style_lock": resolved_style,
        "backstory_summary": request.backstory_summary,
        "core_goals": request.core_goals,
        "core_fears": request.core_fears,
        "speech_style": request.speech_style,
        "default_emotional_range": "neutral",
        "portrait_url": None,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
    }

    # Visual bible
    visual_bible = {
        "visual_bible_id": visual_bible_id,
        "character_id": character_id,
        "version": 1,
        "canonical_description": visual_bible_data.get("canonical_description", ""),
        "face_description": visual_bible_data.get("face_description", request.face_description or ""),
        "hair_description": visual_bible_data.get("hair_description", request.hair_description or ""),
        "body_description": visual_bible_data.get("body_description", request.body_description or ""),
        "clothing_description": visual_bible_data.get("clothing_description", request.clothing_description or ""),
        "color_palette": visual_bible_data.get("color_palette", request.color_palette or ""),
        "accessories": visual_bible_data.get("accessories", request.accessories or ""),
        "style_lock": request.style_lock,
        "do_not_change_rules": visual_bible_data.get("do_not_change_rules", []),
        "reference_asset_ids": [],
        "negative_constraints": visual_bible_data.get("negative_constraints", []),
        "created_at": _now(),
        "updated_at": _now(),
    }

    # Safety profile
    safety_profile = {
        "safety_profile_id": safety_profile_id,
        "character_id": character_id,
        "is_user_uploaded_likeness": False,
        "consent_status": "not_required",
        "is_minor_like": request.age_band in ("child", "teen"),
        "disallowed_transformations": ["photorealistic", "nsfw", "violent"],
        "copyright_risk_flags": [],
        "celebrity_similarity_block": False,
        "brand_similarity_block": False,
        "protected_ip_similarity_block": False,
        "compliance_notes": "Original generated character",
        "created_at": _now(),
    }

    await db.character_profiles.insert_one(profile)
    await db.character_visual_bibles.insert_one(visual_bible)
    await db.character_safety_profiles.insert_one(safety_profile)

    logger.info(f"Character created: {character_id} '{request.name}' by user {user_id}")

    return {
        "success": True,
        "character_id": character_id,
        "name": request.name,
        "role": request.role,
        "style_lock": request.style_lock,
        "visual_bible": {
            "canonical_description": visual_bible["canonical_description"],
            "do_not_change_rules": visual_bible["do_not_change_rules"],
        },
    }


async def _generate_visual_bible(request: CreateCharacterRequest, character_id: str) -> dict:
    """Use LLM to generate a complete visual bible from user inputs."""
    user_parts = []
    if request.face_description:
        user_parts.append(f"Face: {request.face_description}")
    if request.hair_description:
        user_parts.append(f"Hair: {request.hair_description}")
    if request.body_description:
        user_parts.append(f"Body: {request.body_description}")
    if request.clothing_description:
        user_parts.append(f"Clothing: {request.clothing_description}")
    if request.color_palette:
        user_parts.append(f"Colors: {request.color_palette}")
    if request.accessories:
        user_parts.append(f"Accessories: {request.accessories}")

    user_input = "\n".join(user_parts) if user_parts else "No specific appearance given. Generate original."

    system_msg = """You are a character design expert. Given character info, generate a complete visual bible.
Return ONLY valid JSON:
{
  "canonical_description": "Complete visual description in one paragraph for AI image generation",
  "face_description": "detailed face",
  "hair_description": "detailed hair",
  "body_description": "detailed body build and proportions",
  "clothing_description": "detailed outfit with colors",
  "color_palette": "main colors: X, Y, Z",
  "accessories": "notable items",
  "do_not_change_rules": ["rule1", "rule2", "rule3", "rule4"],
  "negative_constraints": ["constraint1", "constraint2"]
}
Make do_not_change_rules specific: same eye color, same scarf, same face shape, etc.
Make the canonical_description vivid and self-contained for image generation."""

    user_msg = (
        f"Character: {request.name}\n"
        f"Species: {request.species_or_type}\n"
        f"Role: {request.role}\n"
        f"Age: {request.age_band}\n"
        f"Style: {request.style_lock}\n"
        f"Personality: {request.personality_summary}\n"
        f"User-provided appearance:\n{user_input}"
    )

    try:
        return await _llm_json(system_msg, user_msg, f"vbible_{character_id[:8]}")
    except Exception as e:
        logger.error(f"Visual bible generation failed: {e}")
        # Fallback: use user inputs directly
        return {
            "canonical_description": f"{request.name}, a {request.species_or_type} {request.role}. {user_input}",
            "face_description": request.face_description or "",
            "hair_description": request.hair_description or "",
            "body_description": request.body_description or "",
            "clothing_description": request.clothing_description or "",
            "color_palette": request.color_palette or "",
            "accessories": request.accessories or "",
            "do_not_change_rules": [f"same {request.species_or_type} design", "same clothing", "same colors"],
            "negative_constraints": ["no character redesign", "no style drift"],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# API 2: MY CHARACTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/my-characters")
async def get_my_characters(user: dict = Depends(get_current_user)):
    """List user's characters."""
    characters = await db.character_profiles.find(
        {"owner_user_id": user["id"], "status": {"$in": ["active", "retired"]}},
        {"_id": 0},
    ).sort("updated_at", -1).to_list(100)

    # Enrich with visual bible summary
    for c in characters:
        vb = await db.character_visual_bibles.find_one(
            {"character_id": c["character_id"]},
            {"_id": 0, "canonical_description": 1, "style_lock": 1, "do_not_change_rules": 1},
        )
        c["visual_summary"] = vb.get("canonical_description", "")[:150] if vb else ""
        c["style_lock"] = vb.get("style_lock", "") if vb else ""

        # Count memory entries
        mem_count = await db.character_memory_logs.count_documents({"character_id": c["character_id"]})
        c["memory_entries"] = mem_count

    return {"success": True, "characters": characters, "total": len(characters)}


# ═══════════════════════════════════════════════════════════════════════════════
# API 3: GET CHARACTER (full detail)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{character_id}")
async def get_character(character_id: str, user: dict = Depends(get_current_user)):
    """Get full character detail: profile + visual bible + safety + memory."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    visual_bible = await db.character_visual_bibles.find_one(
        {"character_id": character_id}, {"_id": 0}
    )
    safety = await db.character_safety_profiles.find_one(
        {"character_id": character_id}, {"_id": 0}
    )
    recent_memory = await db.character_memory_logs.find(
        {"character_id": character_id}, {"_id": 0}
    ).sort("timestamp", -1).to_list(20)

    return {
        "success": True,
        "profile": profile,
        "visual_bible": visual_bible,
        "safety_profile": safety,
        "memory_log": recent_memory,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API 4: UPDATE CHARACTER
# ═══════════════════════════════════════════════════════════════════════════════

@router.patch("/{character_id}")
async def update_character(character_id: str, request: UpdateCharacterRequest, user: dict = Depends(get_current_user)):
    """Update character profile fields."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    updates = {k: v for k, v in request.dict(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Safety re-check if name or personality changed
    if "name" in updates or "personality_summary" in updates:
        name = updates.get("name", profile["name"])
        personality = updates.get("personality_summary", profile["personality_summary"])
        safety = screen_safety(name, personality)
        if not safety["safe"]:
            raise HTTPException(status_code=422, detail={
                "error": "safety_block", "reason": safety["reason"], "tier": safety["tier"],
            })
        # Apply rewritten values if sanitized
        if safety.get("was_rewritten"):
            if "name" in updates:
                updates["name"] = safety["rewritten_name"]
            if "personality_summary" in updates:
                updates["personality_summary"] = safety["rewritten_description"]

    updates["updated_at"] = _now()
    await db.character_profiles.update_one(
        {"character_id": character_id}, {"$set": updates}
    )

    return {"success": True, "character_id": character_id, "updated_fields": list(updates.keys())}


# ═══════════════════════════════════════════════════════════════════════════════
# API 5: GET CHARACTER MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{character_id}/memory")
async def get_character_memory(character_id: str, user: dict = Depends(get_current_user)):
    """Get character memory timeline."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    memories = await db.character_memory_logs.find(
        {"character_id": character_id}, {"_id": 0}
    ).sort("timestamp", -1).to_list(100)

    return {"success": True, "character_id": character_id, "memories": memories, "total": len(memories)}


# ═══════════════════════════════════════════════════════════════════════════════
# API 6: GENERATE CANONICAL PORTRAIT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{character_id}/generate-portrait")
async def generate_portrait(character_id: str, user: dict = Depends(get_current_user)):
    """Generate a canonical reference portrait from visual bible."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    visual_bible = await db.character_visual_bibles.find_one(
        {"character_id": character_id}, {"_id": 0}
    )
    if not visual_bible:
        raise HTTPException(status_code=400, detail="No visual bible found")

    style_map = {
        "cartoon_2d": "vibrant 2D cartoon illustration, clean lines, bold colors",
        "anime": "anime art style, dramatic lighting, large expressive eyes",
        "watercolor": "watercolor painting style, soft edges, pastel tones",
        "comic": "comic book art style, dynamic lines, vivid colors",
        "cinematic": "cinematic digital painting, dramatic lighting, realistic proportions",
    }
    style = style_map.get(visual_bible.get("style_lock", ""), "vibrant cartoon illustration")

    prompt = (
        f"Character portrait of {profile['name']}: "
        f"{visual_bible.get('canonical_description', '')} "
        f"Style: {style}. "
        f"Full body view, neutral pose, clean background, character sheet style. "
        f"No text, no words, no watermarks."
    )

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
            raise HTTPException(status_code=500, detail="Portrait generation returned no results")

        from services.cloudflare_r2_storage import upload_image_bytes
        success, portrait_url = await upload_image_bytes(
            image_bytes_list[0], f"portrait_{character_id[:8]}.png", character_id
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload portrait")

        await db.character_profiles.update_one(
            {"character_id": character_id},
            {"$set": {"portrait_url": portrait_url, "updated_at": _now()}}
        )

        logger.info(f"Portrait generated for character {character_id}: {portrait_url}")
        return {"success": True, "portrait_url": portrait_url, "character_id": character_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portrait generation failed for {character_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Portrait generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# THE HEART: CHARACTER PROMPT PACKAGE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

async def build_character_prompt_package(character_id: str, series_id: str = None, scene_context: str = "") -> dict:
    """
    Build the generation contract for a character.
    Returns 5 blocks: identity, visual_lock, memory, scene, negative_constraints.
    This is the core function that makes character memory work in pipelines.
    """
    profile = await db.character_profiles.find_one({"character_id": character_id}, {"_id": 0})
    if not profile:
        return None

    visual_bible = await db.character_visual_bibles.find_one({"character_id": character_id}, {"_id": 0})

    # Get latest memory entries (scoped to series if provided)
    mem_filter = {"character_id": character_id}
    if series_id:
        # Get episodes from this series for context
        ep_ids = await db.story_episodes.find(
            {"series_id": series_id}, {"_id": 0, "episode_id": 1}
        ).to_list(100)
        ep_id_list = [e["episode_id"] for e in ep_ids]
        if ep_id_list:
            mem_filter["episode_id"] = {"$in": ep_id_list}

    recent_memories = await db.character_memory_logs.find(
        mem_filter, {"_id": 0}
    ).sort("timestamp", -1).to_list(5)

    # Block 1: Identity
    identity_block = {
        "name": profile.get("name", ""),
        "role": profile.get("role", ""),
        "species_or_type": profile.get("species_or_type", ""),
        "personality": profile.get("personality_summary", ""),
        "goals": profile.get("core_goals", ""),
        "fears": profile.get("core_fears", ""),
        "speech_style": profile.get("speech_style", ""),
    }

    # Block 2: Visual Lock
    visual_lock_block = {}
    if visual_bible:
        visual_lock_block = {
            "canonical_description": visual_bible.get("canonical_description", ""),
            "face": visual_bible.get("face_description", ""),
            "hair": visual_bible.get("hair_description", ""),
            "body": visual_bible.get("body_description", ""),
            "clothing": visual_bible.get("clothing_description", ""),
            "color_palette": visual_bible.get("color_palette", ""),
            "accessories": visual_bible.get("accessories", ""),
            "style_lock": visual_bible.get("style_lock", ""),
            "do_not_change_rules": visual_bible.get("do_not_change_rules", []),
        }

    # Block 3: Memory
    memory_block = {
        "recent_events": [],
        "current_emotion": "neutral",
        "open_loops": [],
        "relationship_changes": [],
    }
    if recent_memories:
        memory_block["recent_events"] = [m.get("event_summary", "") for m in recent_memories if m.get("event_summary")]
        memory_block["current_emotion"] = recent_memories[0].get("emotion_state", "neutral")
        all_open = []
        for m in recent_memories:
            all_open.extend(m.get("open_loops", []))
        memory_block["open_loops"] = list(set(all_open))[:5]
        all_rels = []
        for m in recent_memories:
            all_rels.extend(m.get("relationship_changes", []))
        memory_block["relationship_changes"] = all_rels[:5]

    # Block 4: Scene
    scene_block = scene_context

    # Block 5: Negative Constraints
    negative_constraints = [
        "no character redesign",
        "no copyrighted resemblance",
        "no trademark mascot resemblance",
        "no distorted face",
        "no style drift from locked style",
    ]
    if visual_bible:
        negative_constraints.extend(visual_bible.get("negative_constraints", []))
        for rule in visual_bible.get("do_not_change_rules", []):
            negative_constraints.append(f"do not change: {rule}")

    return {
        "character_id": character_id,
        "identity_block": identity_block,
        "visual_lock_block": visual_lock_block,
        "memory_block": memory_block,
        "scene_block": scene_block,
        "negative_constraints": list(set(negative_constraints)),
        "negative_prompt": CHARACTER_NEGATIVE_PROMPT,
    }


def format_prompt_package_for_llm(package: dict) -> str:
    """Format the prompt package into text blocks for LLM injection."""
    if not package:
        return ""

    parts = []

    # Identity
    ib = package.get("identity_block", {})
    parts.append(
        f"### CHARACTER: {ib.get('name', '')}\n"
        f"Role: {ib.get('role', '')}\n"
        f"Species: {ib.get('species_or_type', '')}\n"
        f"Personality: {ib.get('personality', '')}\n"
        f"Goals: {ib.get('goals', '')}\n"
        f"Fears: {ib.get('fears', '')}\n"
        f"Speech: {ib.get('speech_style', '')}"
    )

    # Visual Lock
    vl = package.get("visual_lock_block", {})
    if vl:
        parts.append(
            f"### VISUAL LOCK (DO NOT CHANGE)\n"
            f"{vl.get('canonical_description', '')}\n"
            f"Style: {vl.get('style_lock', '')}\n"
            f"Rules: {', '.join(vl.get('do_not_change_rules', []))}"
        )

    # Memory State
    mb = package.get("memory_block", {})
    if mb.get("recent_events"):
        parts.append(
            f"### CURRENT STATE\n"
            f"Recent: {'; '.join(mb['recent_events'][:3])}\n"
            f"Emotion: {mb.get('current_emotion', 'neutral')}\n"
            f"Unresolved: {'; '.join(mb.get('open_loops', []))}"
        )

    # Negative
    nc = package.get("negative_constraints", [])
    if nc:
        parts.append(f"### CONSTRAINTS\n{'; '.join(nc[:10])}")

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# API 7: ATTACH CHARACTER TO SERIES
# (lives here, not in story_series.py, to keep character logic together)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/attach-to-series/{series_id}")
async def attach_character_to_series(series_id: str, request: AttachCharacterRequest, user: dict = Depends(get_current_user)):
    """Link a persistent character to a story series."""
    # Verify series ownership
    series = await db.story_series.find_one(
        {"series_id": series_id, "user_id": user["id"]}, {"_id": 0, "series_id": 1, "attached_characters": 1}
    )
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    # Verify character ownership
    profile = await db.character_profiles.find_one(
        {"character_id": request.character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1, "name": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    # Add to series attached_characters list (avoid duplicates)
    existing = series.get("attached_characters", [])
    if request.character_id in existing:
        return {"success": True, "message": "Character already attached", "already_attached": True}

    await db.story_series.update_one(
        {"series_id": series_id},
        {"$addToSet": {"attached_characters": request.character_id}, "$set": {"updated_at": _now()}}
    )

    # Also link character to series
    await db.character_profiles.update_one(
        {"character_id": request.character_id},
        {"$set": {"series_id": series_id, "updated_at": _now()}}
    )

    logger.info(f"Character {request.character_id} attached to series {series_id}")
    return {
        "success": True,
        "character_id": request.character_id,
        "character_name": profile["name"],
        "series_id": series_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY LOG WRITER (called by pipelines after generation)
# ═══════════════════════════════════════════════════════════════════════════════

async def write_character_memory(
    character_id: str,
    episode_id: str,
    event_summary: str,
    emotion_state: str = "neutral",
    goal_state: str = "",
    relationship_changes: list = None,
    location_state: str = "",
    open_loops: list = None,
    resolved_loops: list = None,
):
    """Write a memory log entry for a character after an episode."""
    entry = {
        "memory_log_id": _uuid(),
        "character_id": character_id,
        "episode_id": episode_id,
        "event_summary": event_summary,
        "emotion_state": emotion_state,
        "goal_state": goal_state,
        "relationship_changes": relationship_changes or [],
        "location_state": location_state,
        "injuries_or_changes": "",
        "open_loops": open_loops or [],
        "resolved_loops": resolved_loops or [],
        "timestamp": _now(),
    }
    await db.character_memory_logs.insert_one(entry)
    logger.info(f"Memory written for character {character_id}, episode {episode_id}")
    return entry["memory_log_id"]


# ═══════════════════════════════════════════════════════════════════════════════
# CONTINUITY VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════
# The most important guard in the system. Checks:
#   - canonical prompt package presence
#   - visual lock rules applied
#   - style drift detection
#   - IP resemblance risk
#   - output asset existence
# Returns continuity_score, drift_flags, retry_recommended

DRIFT_CHECK_SYSTEM_PROMPT = """You are a strict continuity validator for character consistency.

Given a character's canonical visual bible and a generation prompt that was used, check for drift.

Return ONLY valid JSON:
{
  "continuity_score": 0-100,
  "drift_flags": [
    {"type": "appearance|clothing|style|personality|ip_resemblance", "severity": "low|medium|high", "detail": "what drifted"}
  ],
  "rules_applied": true/false,
  "negative_prompt_present": true/false,
  "retry_recommended": true/false,
  "summary": "one-line assessment"
}

Score guide:
- 90-100: Perfect continuity, no drift detected
- 70-89: Minor drift, acceptable for most uses
- 50-69: Notable drift, review recommended
- 0-49: Significant drift, retry recommended

Check specifically:
1. Does the generation prompt contain the character's canonical description?
2. Are do_not_change_rules reflected in the prompt?
3. Is the style lock maintained?
4. Is the negative constraint block present?
5. Any sign of copyrighted character resemblance?"""


async def validate_character_continuity(
    character_id: str,
    generation_prompt: str,
    output_asset_url: str = None,
    tool_type: str = "story_video",
) -> dict:
    """
    Validate that a generation output maintains character continuity.
    Called automatically after generation, or manually via API.
    """
    profile = await db.character_profiles.find_one({"character_id": character_id}, {"_id": 0})
    if not profile:
        return {"continuity_score": 0, "drift_flags": [{"type": "appearance", "severity": "high", "detail": "Character not found"}], "retry_recommended": True}

    visual_bible = await db.character_visual_bibles.find_one({"character_id": character_id}, {"_id": 0})
    await db.character_safety_profiles.find_one({"character_id": character_id}, {"_id": 0})

    # Rule-based checks first (fast, no LLM needed)
    rule_flags = []
    score = 100

    # Check 1: Canonical description present in prompt
    if visual_bible and visual_bible.get("canonical_description"):
        canon = visual_bible["canonical_description"][:50].lower()
        if canon not in generation_prompt.lower():
            rule_flags.append({"type": "appearance", "severity": "medium", "detail": "Canonical description not found in generation prompt"})
            score -= 15

    # Check 2: Do-not-change rules applied
    if visual_bible and visual_bible.get("do_not_change_rules"):
        rules_found = 0
        for rule in visual_bible["do_not_change_rules"][:5]:
            if any(word.lower() in generation_prompt.lower() for word in rule.split()[:3]):
                rules_found += 1
        if len(visual_bible["do_not_change_rules"]) > 0:
            rules_ratio = rules_found / min(len(visual_bible["do_not_change_rules"]), 5)
            if rules_ratio < 0.5:
                rule_flags.append({"type": "appearance", "severity": "high", "detail": f"Only {rules_found}/{min(len(visual_bible['do_not_change_rules']), 5)} visual lock rules found in prompt"})
                score -= 20

    # Check 3: Style lock maintained
    if visual_bible and visual_bible.get("style_lock"):
        style = visual_bible["style_lock"].replace("_", " ")
        if style not in generation_prompt.lower() and visual_bible["style_lock"] not in generation_prompt.lower():
            rule_flags.append({"type": "style", "severity": "medium", "detail": f"Style lock '{visual_bible['style_lock']}' not found in prompt"})
            score -= 10

    # Check 4: Negative constraints present
    neg_keywords = ["no character redesign", "no copyrighted", "no distorted"]
    neg_found = sum(1 for kw in neg_keywords if kw.lower() in generation_prompt.lower())
    if neg_found == 0:
        rule_flags.append({"type": "appearance", "severity": "low", "detail": "No negative constraints found in prompt"})
        score -= 5

    # Check 5: IP resemblance — use rewrite engine to detect risky terms
    from services.rewrite_engine.rule_rewriter import has_risky_terms
    if has_risky_terms(generation_prompt):
        rule_flags.append({"type": "ip_resemblance", "severity": "info", "detail": "Risky terms detected in prompt — rewrite engine will sanitize at generation time"})
        score -= 5

    # Check 6: Output asset exists
    has_output = bool(output_asset_url)
    if not has_output:
        rule_flags.append({"type": "appearance", "severity": "low", "detail": "No output asset URL provided for visual validation"})

    score = max(0, score)
    retry_recommended = score < 50

    result = {
        "character_id": character_id,
        "character_name": profile.get("name", ""),
        "tool_type": tool_type,
        "continuity_score": score,
        "drift_flags": rule_flags,
        "rules_applied": len(rule_flags) == 0 or score >= 70,
        "negative_prompt_present": neg_found > 0,
        "retry_recommended": retry_recommended,
        "output_asset_url": output_asset_url,
        "validated_at": _now(),
        "summary": (
            "Perfect continuity" if score >= 90 else
            "Minor drift detected" if score >= 70 else
            "Notable drift — review recommended" if score >= 50 else
            "Significant drift — retry recommended"
        ),
    }

    # Store validation result
    result["validation_id"] = _uuid()
    await db.character_continuity_validations.insert_one({**result})

    logger.info(f"Continuity validation for {character_id}: score={score}, flags={len(rule_flags)}")
    return {k: v for k, v in result.items() if k != "_id"}


@router.post("/{character_id}/validate-continuity")
async def validate_continuity_api(character_id: str, user: dict = Depends(get_current_user)):
    """Manually trigger continuity validation for a character's last generation."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get last validation or generate a check from the prompt package
    pkg = await build_character_prompt_package(character_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="No prompt package available")

    prompt_text = format_prompt_package_for_llm(pkg)
    result = await validate_character_continuity(
        character_id, prompt_text, profile.get("portrait_url"), "manual_check"
    )
    return {"success": True, **result}


@router.get("/{character_id}/continuity-history")
async def get_continuity_history(character_id: str, user: dict = Depends(get_current_user)):
    """Get continuity validation history for a character."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    validations = await db.character_continuity_validations.find(
        {"character_id": character_id}, {"_id": 0}
    ).sort("validated_at", -1).to_list(50)

    avg_score = 0
    if validations:
        avg_score = sum(v.get("continuity_score", 0) for v in validations) / len(validations)

    return {
        "success": True,
        "character_id": character_id,
        "validations": validations,
        "total": len(validations),
        "average_score": round(avg_score, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE PROFILE
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceProfileRequest(BaseModel):
    voice_provider: str = "openai"
    voice_id: str = "alloy"
    tone: str = "warm"
    pace: str = "moderate"
    accent: Optional[str] = None
    energy_level: str = "medium"
    sample_text: Optional[str] = None
    do_not_change_rules: Optional[List[str]] = None


@router.post("/{character_id}/voice-profile")
async def set_voice_profile(character_id: str, request: VoiceProfileRequest, user: dict = Depends(get_current_user)):
    """Create or update voice profile for a character."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    voice_data = {
        "voice_profile_id": _uuid(),
        "character_id": character_id,
        "voice_provider": request.voice_provider,
        "voice_id": request.voice_id,
        "tone": request.tone,
        "pace": request.pace,
        "accent": request.accent,
        "energy_level": request.energy_level,
        "sample_text": request.sample_text or f"Hello, I'm {profile['name']}. {profile.get('personality_summary', '')}",
        "do_not_change_rules": request.do_not_change_rules or [f"same {request.tone} tone", f"same {request.pace} pace"],
        "created_at": _now(),
        "updated_at": _now(),
    }

    await db.character_voice_profiles.update_one(
        {"character_id": character_id},
        {"$set": voice_data},
        upsert=True,
    )

    logger.info(f"Voice profile set for character {character_id}: {request.voice_id}")
    return {"success": True, "character_id": character_id, "voice_profile": {k: v for k, v in voice_data.items() if k != "_id"}}


@router.get("/{character_id}/voice-profile")
async def get_voice_profile(character_id: str, user: dict = Depends(get_current_user)):
    """Get voice profile for a character."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    voice = await db.character_voice_profiles.find_one({"character_id": character_id}, {"_id": 0})
    return {"success": True, "character_id": character_id, "voice_profile": voice}


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE FROM REFERENCE (Path B) — with consent guardrails
# ═══════════════════════════════════════════════════════════════════════════════

class CreateFromReferenceRequest(BaseModel):
    name: str
    role: str = "hero"
    personality_summary: str
    desired_stylization: str = "cartoon_2d"
    is_real_person: bool = False
    consent_confirmed: bool = False
    consent_scope: Optional[str] = None  # "personal_use", "commercial", "all"


@router.post("/create-from-reference")
async def create_from_reference(request: CreateFromReferenceRequest, user: dict = Depends(get_current_user)):
    """
    Create character inspired by reference attributes.
    Real-person likeness requires explicit consent.
    Does NOT blindly clone — extracts generic attributes and stylizes.
    """
    # Safety: name check
    safety = screen_safety(request.name, request.personality_summary)
    if not safety["safe"]:
        raise HTTPException(status_code=422, detail={
            "error": "safety_block", "reason": safety["reason"], "tier": safety["tier"],
        })
    # Apply rewritten values if sanitized
    if safety.get("was_rewritten"):
        request.name = safety["rewritten_name"]
        request.personality_summary = safety["rewritten_description"]

    # Real-person consent gate
    if request.is_real_person and not request.consent_confirmed:
        raise HTTPException(status_code=422, detail={
            "error": "consent_required",
            "reason": "Creating persistent characters based on real people requires explicit consent. Please confirm you have the right to create this likeness.",
        })

    character_id = _uuid()

    # Generate stylized character — NOT a clone, but "inspired by"
    system_msg = """You are a character designer. Create an ORIGINAL stylized character inspired by described attributes.
Do NOT create a direct likeness. Transform into a distinct, original character with unique features.
If the source is a real person, the output must be clearly fictional and non-identifiable.

Return ONLY valid JSON:
{
  "canonical_description": "Original character description (must be clearly distinct from source)",
  "face_description": "unique stylized face",
  "hair_description": "stylized hair",
  "body_description": "body description",
  "clothing_description": "original outfit",
  "color_palette": "color scheme",
  "accessories": "unique items",
  "do_not_change_rules": ["rule1", "rule2", "rule3"],
  "negative_constraints": ["no real-person likeness", "no photorealistic face"]
}"""

    user_msg = (
        f"Create an ORIGINAL {request.desired_stylization} character named {request.name}.\n"
        f"Role: {request.role}\n"
        f"Personality: {request.personality_summary}\n"
        f"Style: {request.desired_stylization}\n"
        f"IMPORTANT: Must be clearly original and distinct. Not a copy of any real person."
    )

    try:
        vb_data = await _llm_json(system_msg, user_msg, f"ref_{character_id[:8]}")
    except Exception:
        vb_data = {
            "canonical_description": f"Original {request.desired_stylization} character named {request.name}",
            "face_description": "", "hair_description": "", "body_description": "",
            "clothing_description": "", "color_palette": "", "accessories": "",
            "do_not_change_rules": ["same style", "same clothing"],
            "negative_constraints": ["no real-person likeness"],
        }

    # Ensure negative constraints always include real-person protection
    neg = vb_data.get("negative_constraints", [])
    if "no real-person likeness" not in neg:
        neg.append("no real-person likeness")
    if "no photorealistic face" not in neg:
        neg.append("no photorealistic face")
    vb_data["negative_constraints"] = neg

    profile = {
        "character_id": character_id,
        "series_id": None,
        "owner_user_id": user["id"],
        "name": request.name,
        "species_or_type": "human",
        "role": request.role,
        "age_band": "adult",
        "gender_presentation": None,
        "personality_summary": request.personality_summary,
        "backstory_summary": None,
        "core_goals": None,
        "core_fears": None,
        "speech_style": None,
        "default_emotional_range": "neutral",
        "portrait_url": None,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
    }

    visual_bible = {
        "visual_bible_id": _uuid(),
        "character_id": character_id,
        **{k: vb_data.get(k, "") for k in [
            "canonical_description", "face_description", "hair_description",
            "body_description", "clothing_description", "color_palette", "accessories",
        ]},
        "style_lock": request.desired_stylization,
        "do_not_change_rules": vb_data.get("do_not_change_rules", []),
        "reference_asset_ids": [],
        "negative_constraints": vb_data["negative_constraints"],
        "created_at": _now(),
        "updated_at": _now(),
    }

    safety_profile = {
        "safety_profile_id": _uuid(),
        "character_id": character_id,
        "is_user_uploaded_likeness": request.is_real_person,
        "consent_status": "confirmed" if request.consent_confirmed else "not_required",
        "consent_scope": request.consent_scope if request.is_real_person else None,
        "is_minor_like": False,
        "disallowed_transformations": ["photorealistic", "nsfw", "violent", "direct_likeness"],
        "copyright_risk_flags": ["reference_based"] if request.is_real_person else [],
        "celebrity_similarity_block": True,
        "brand_similarity_block": False,
        "protected_ip_similarity_block": False,
        "compliance_notes": f"Reference-inspired character. Real person: {request.is_real_person}. Consent: {request.consent_confirmed}.",
        "created_at": _now(),
    }

    await db.character_profiles.insert_one(profile)
    await db.character_visual_bibles.insert_one(visual_bible)
    await db.character_safety_profiles.insert_one(safety_profile)

    logger.info(f"Reference-based character created: {character_id} (real_person={request.is_real_person})")
    return {
        "success": True,
        "character_id": character_id,
        "name": request.name,
        "reference_based": True,
        "consent_status": safety_profile["consent_status"],
        "visual_bible": {
            "canonical_description": visual_bible["canonical_description"],
            "negative_constraints": visual_bible["negative_constraints"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-TOOL CHARACTER GENERATION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════
# One shared function. Every tool adapts from this.
# build_character_generation_context(character_id, series_id, tool_type, scene_context)

TOOL_STYLE_HINTS = {
    "story_video": "cinematic narrative illustration with consistent character design across scenes",
    "comic_storybook": "comic book panel illustration with consistent character across pages",
    "photo_to_comic": "comic character transformation maintaining character identity",
    "gif_maker": "animated character maintaining visual identity across frames",
}


async def build_character_generation_context(
    character_id: str,
    series_id: str = None,
    tool_type: str = "story_video",
    scene_context: str = "",
) -> dict:
    """
    Unified character generation context for ALL tools.
    Returns formatted prompt blocks + negative prompt ready for injection.
    """
    package = await build_character_prompt_package(character_id, series_id, scene_context)
    if not package:
        return None

    # Format the prompt text
    prompt_text = format_prompt_package_for_llm(package)

    # Build visual prompt injection (for image generation)
    vl = package.get("visual_lock_block", {})
    visual_injection = ""
    if vl:
        visual_injection = (
            f"{vl.get('canonical_description', '')}. "
            f"Style: {vl.get('style_lock', '')}. "
            f"Rules: {', '.join(vl.get('do_not_change_rules', [])[:5])}."
        )

    # Tool-specific style hint
    tool_hint = TOOL_STYLE_HINTS.get(tool_type, "consistent character design")

    # Build the complete negative prompt
    neg_parts = [CHARACTER_NEGATIVE_PROMPT]
    for nc in package.get("negative_constraints", []):
        if nc.lower() not in CHARACTER_NEGATIVE_PROMPT.lower():
            neg_parts.append(nc)

    return {
        "character_id": character_id,
        "character_name": package["identity_block"].get("name", ""),
        "tool_type": tool_type,
        "prompt_text": prompt_text,
        "visual_injection": visual_injection,
        "tool_hint": tool_hint,
        "negative_prompt": ", ".join(neg_parts),
        "identity_block": package["identity_block"],
        "visual_lock_block": package.get("visual_lock_block", {}),
        "memory_block": package.get("memory_block", {}),
    }


async def get_series_character_contexts(series_id: str, tool_type: str = "story_video", scene_context: str = "") -> list:
    """Get generation contexts for ALL characters attached to a series."""
    series = await db.story_series.find_one({"series_id": series_id}, {"_id": 0, "attached_characters": 1})
    if not series or not series.get("attached_characters"):
        return []

    contexts = []
    for cid in series["attached_characters"][:5]:
        ctx = await build_character_generation_context(cid, series_id, tool_type, scene_context)
        if ctx:
            contexts.append(ctx)
    return contexts


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT C.1: EDITABLE VISUAL BIBLES (with versioning + validation)
# ═══════════════════════════════════════════════════════════════════════════════

# Editable fields (safe to change)
EDITABLE_VB_FIELDS = {
    "clothing_description", "accessories", "color_palette",
    "face_description", "hair_description", "body_description",
    "canonical_description", "do_not_change_rules", "negative_constraints",
}
# Locked fields (require explicit style_reset flag)
LOCKED_VB_FIELDS = {"style_lock"}


class EditVisualBibleRequest(BaseModel):
    clothing_description: Optional[str] = None
    accessories: Optional[str] = None
    color_palette: Optional[str] = None
    face_description: Optional[str] = None
    hair_description: Optional[str] = None
    body_description: Optional[str] = None
    canonical_description: Optional[str] = None
    do_not_change_rules: Optional[List[str]] = None
    negative_constraints: Optional[List[str]] = None
    style_lock: Optional[str] = None
    style_reset: bool = False  # Must be true to change style_lock


@router.patch("/{character_id}/visual-bible")
async def edit_visual_bible(character_id: str, request: EditVisualBibleRequest, user: dict = Depends(get_current_user)):
    """
    Edit visual bible with versioning + automatic continuity validation.
    - Editable fields: clothing, accessories, color_palette, face, hair, body, canonical desc, rules
    - Locked: style_lock (requires style_reset=true)
    - Every edit bumps version and triggers validation
    """
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    current_vb = await db.character_visual_bibles.find_one({"character_id": character_id}, {"_id": 0})
    if not current_vb:
        raise HTTPException(status_code=404, detail="No visual bible found")

    updates = {}
    for field in EDITABLE_VB_FIELDS:
        val = getattr(request, field, None)
        if val is not None:
            updates[field] = val

    # Style lock requires explicit reset
    if request.style_lock and request.style_lock != current_vb.get("style_lock"):
        if not request.style_reset:
            raise HTTPException(status_code=422, detail={
                "error": "style_lock_protected",
                "reason": "Changing style_lock requires style_reset=true. This may affect consistency across previous episodes.",
                "current_style": current_vb.get("style_lock"),
            })
        updates["style_lock"] = request.style_lock

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Safety re-check on canonical description
    if "canonical_description" in updates:
        safety = screen_safety(profile["name"], updates["canonical_description"])
        if not safety["safe"]:
            raise HTTPException(status_code=422, detail={
                "error": "safety_block", "reason": safety["reason"], "tier": safety["tier"],
            })
        # Apply rewritten canonical description if sanitized
        if safety.get("was_rewritten"):
            updates["canonical_description"] = safety["rewritten_description"]

    # Version bump
    old_version = current_vb.get("version", 1)
    new_version = old_version + 1
    updates["version"] = new_version
    updates["updated_at"] = _now()

    # Archive old version
    await db.character_visual_bible_history.insert_one({
        "character_id": character_id,
        "version": old_version,
        "snapshot": {k: v for k, v in current_vb.items() if k != "_id"},
        "archived_at": _now(),
    })

    await db.character_visual_bibles.update_one(
        {"character_id": character_id}, {"$set": updates}
    )

    # Auto-validate continuity after edit
    await db.character_visual_bibles.find_one({"character_id": character_id}, {"_id": 0})
    pkg = await build_character_prompt_package(character_id)
    prompt_text = format_prompt_package_for_llm(pkg) if pkg else ""
    validation = await validate_character_continuity(character_id, prompt_text, profile.get("portrait_url"), "visual_edit")

    logger.info(f"Visual bible edited for {character_id}: v{old_version}->v{new_version}, continuity={validation['continuity_score']}")

    return {
        "success": True,
        "character_id": character_id,
        "old_version": old_version,
        "new_version": new_version,
        "updated_fields": list(updates.keys()),
        "continuity_check": {
            "score": validation["continuity_score"],
            "drift_flags": validation["drift_flags"],
            "summary": validation["summary"],
        },
        "impact_warning": "This change may affect consistency across previous episodes." if new_version > 2 else None,
    }


@router.get("/{character_id}/visual-bible-history")
async def get_visual_bible_history(character_id: str, user: dict = Depends(get_current_user)):
    """Get version history of visual bible edits."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    history = await db.character_visual_bible_history.find(
        {"character_id": character_id}, {"_id": 0}
    ).sort("version", -1).to_list(50)

    current = await db.character_visual_bibles.find_one({"character_id": character_id}, {"_id": 0})

    return {
        "success": True,
        "character_id": character_id,
        "current_version": current.get("version", 1) if current else 0,
        "history": history,
        "total_versions": len(history) + 1,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT C.2: RELATIONSHIP GRAPH (lightweight)
# ═══════════════════════════════════════════════════════════════════════════════

RELATIONSHIP_TYPES = {"friend", "enemy", "mentor", "family", "rival", "ally", "unknown"}
RELATIONSHIP_STATES = {"trusting", "conflict", "neutral", "developing", "broken"}


class AddRelationshipRequest(BaseModel):
    related_character_id: str
    relationship_type: str = "unknown"
    relationship_state: str = "neutral"


@router.post("/{character_id}/relationships")
async def add_relationship(character_id: str, request: AddRelationshipRequest, user: dict = Depends(get_current_user)):
    """Add or update a relationship between two characters."""
    # Verify both characters owned by user
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1, "name": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    related = await db.character_profiles.find_one(
        {"character_id": request.related_character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1, "name": 1}
    )
    if not related:
        raise HTTPException(status_code=404, detail="Related character not found")

    if character_id == request.related_character_id:
        raise HTTPException(status_code=400, detail="Cannot create self-relationship")

    rel_type = request.relationship_type if request.relationship_type in RELATIONSHIP_TYPES else "unknown"
    rel_state = request.relationship_state if request.relationship_state in RELATIONSHIP_STATES else "neutral"

    # Upsert both directions (A->B and B->A)
    for src, dst in [(character_id, request.related_character_id), (request.related_character_id, character_id)]:
        await db.character_relationships.update_one(
            {"character_id": src, "related_character_id": dst},
            {"$set": {
                "relationship_id": _uuid(),
                "character_id": src,
                "related_character_id": dst,
                "relationship_type": rel_type,
                "relationship_state": rel_state,
                "last_updated_episode_id": None,
                "updated_at": _now(),
            }},
            upsert=True,
        )

    logger.info(f"Relationship set: {profile['name']} <-> {related['name']}: {rel_type}/{rel_state}")
    return {
        "success": True,
        "character_id": character_id,
        "related_character_id": request.related_character_id,
        "relationship_type": rel_type,
        "relationship_state": rel_state,
        "character_name": profile["name"],
        "related_name": related["name"],
    }


@router.get("/{character_id}/relationships")
async def get_relationships(character_id: str, user: dict = Depends(get_current_user)):
    """Get relationship graph for a character."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    rels = await db.character_relationships.find(
        {"character_id": character_id}, {"_id": 0}
    ).to_list(50)

    # Enrich with names and portraits
    for r in rels:
        related = await db.character_profiles.find_one(
            {"character_id": r["related_character_id"]},
            {"_id": 0, "name": 1, "portrait_url": 1, "species_or_type": 1, "role": 1}
        )
        if related:
            r["related_name"] = related["name"]
            r["related_portrait_url"] = related.get("portrait_url")
            r["related_species"] = related.get("species_or_type", "")
            r["related_role"] = related.get("role", "")

    return {"success": True, "character_id": character_id, "relationships": rels, "total": len(rels)}


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT C.3: EMOTIONAL MEMORY (simple categorical model)
# ═══════════════════════════════════════════════════════════════════════════════

EMOTIONS = {"happy", "sad", "tense", "scared", "confident", "angry", "neutral", "hopeful", "determined"}


@router.get("/{character_id}/emotional-arc")
async def get_emotional_arc(character_id: str, user: dict = Depends(get_current_user)):
    """Get emotional arc — simple emotion + intensity per episode."""
    profile = await db.character_profiles.find_one(
        {"character_id": character_id, "owner_user_id": user["id"]}, {"_id": 0, "character_id": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Character not found")

    memories = await db.character_memory_logs.find(
        {"character_id": character_id}, {"_id": 0}
    ).sort("timestamp", 1).to_list(100)

    # Build simple emotional arc from memory logs
    arc = []
    for m in memories:
        emotion_raw = m.get("emotion_state", "neutral")
        # Normalize emotion to our simple categorical model
        emotion = emotion_raw.lower().strip() if emotion_raw else "neutral"
        if emotion not in EMOTIONS:
            # Map common variants
            mapping = {
                "afraid": "scared", "fearful": "scared", "worried": "tense",
                "relieved": "happy", "excited": "happy", "joyful": "happy",
                "anxious": "tense", "nervous": "tense", "frustrated": "angry",
                "brave": "confident", "courageous": "determined",
            }
            emotion = mapping.get(emotion, "neutral")

        # Derive intensity from context (simple heuristic)
        intensity = 3  # default medium
        event = m.get("event_summary", "")
        if any(w in event.lower() for w in ["rescued", "saved", "victory", "defeated"]):
            intensity = 5
        elif any(w in event.lower() for w in ["danger", "storm", "attack", "crisis"]):
            intensity = 4
        elif any(w in event.lower() for w in ["worried", "uncertain", "confused"]):
            intensity = 2

        arc.append({
            "episode_id": m.get("episode_id"),
            "emotion": emotion,
            "intensity": intensity,
            "event_summary": event[:100],
            "timestamp": m.get("timestamp"),
        })

    # Derive trend
    trend = "stable"
    if len(arc) >= 2:
        emotions_list = [a["emotion"] for a in arc]
        positive = {"happy", "confident", "hopeful", "determined"}
        negative = {"sad", "scared", "angry", "tense"}
        pos_count = sum(1 for e in emotions_list[-3:] if e in positive)
        neg_count = sum(1 for e in emotions_list[-3:] if e in negative)
        if pos_count > neg_count:
            trend = "improving"
        elif neg_count > pos_count:
            trend = "declining"

    return {
        "success": True,
        "character_id": character_id,
        "arc": arc,
        "total_entries": len(arc),
        "trend": trend,
        "current_emotion": arc[-1]["emotion"] if arc else "neutral",
        "current_intensity": arc[-1]["intensity"] if arc else 3,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT C.4: LIBRARY SEARCH/FILTER (basic)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/search/query")
async def search_characters(
    q: str = "",
    role: str = "",
    sort_by: str = "updated_at",
    user: dict = Depends(get_current_user),
):
    """Search and filter characters. Basic: name search, role filter, sort."""
    query = {"owner_user_id": user["id"], "status": {"$in": ["active", "retired"]}}

    if q:
        query["name"] = {"$regex": q, "$options": "i"}
    if role:
        query["role"] = role

    sort_field = "updated_at"
    if sort_by == "name":
        sort_field = "name"
    elif sort_by == "created_at":
        sort_field = "created_at"

    sort_dir = -1 if sort_field != "name" else 1

    characters = await db.character_profiles.find(query, {"_id": 0}).sort(sort_field, sort_dir).to_list(100)

    # Enrich
    for c in characters:
        vb = await db.character_visual_bibles.find_one(
            {"character_id": c["character_id"]},
            {"_id": 0, "canonical_description": 1, "style_lock": 1, "version": 1},
        )
        c["visual_summary"] = vb.get("canonical_description", "")[:150] if vb else ""
        c["style_lock"] = vb.get("style_lock", "") if vb else ""
        c["vb_version"] = vb.get("version", 1) if vb else 0
        mem_count = await db.character_memory_logs.count_documents({"character_id": c["character_id"]})
        c["memory_entries"] = mem_count

    return {"success": True, "characters": characters, "total": len(characters), "query": q, "role_filter": role}
