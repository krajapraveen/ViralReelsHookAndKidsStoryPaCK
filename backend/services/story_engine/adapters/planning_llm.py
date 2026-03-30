"""
Planning LLM Adapter — Multi-level fallback for scene generation.

Fallback chain:
  Level 0: Primary model (GPT-4o-mini), full prompt, temp 0.7
  Level 1: Same model, reduced/cleaned prompt, temp 0.5
  Level 2: Fallback model (gemini-3-flash), reduced prompt
  Level 3: Deterministic splitter — no LLM, pure text splitting
"""
import os
import json
import logging
import re
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("story_engine.adapters.planning")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

EPISODE_PLAN_PROMPT = """You are a cinematic story planner who specializes in ADDICTIVE, UNFINISHED stories. Given a story prompt, produce a STRICT JSON episode plan.

Output ONLY valid JSON matching this exact schema:
{{
  "title": "episode title",
  "episode_number": {episode_number},
  "summary": "2-3 sentence summary",
  "emotional_arc": "emotion1 → emotion2 → TENSION_PEAK → cliffhanger_cut",
  "scene_breakdown": [
    {{
      "scene_number": 1,
      "location": "specific place",
      "time_of_day": "morning|afternoon|dusk|night",
      "characters_present": ["Name1", "Name2"],
      "action_summary": "what happens",
      "dialogue": "key line if any or null",
      "emotional_beat": "tension|joy|fear|surprise",
      "visual_style_notes": "lighting, angle, mood",
      "estimated_duration_seconds": 5.0
    }}
  ],
  "character_arcs": [
    {{
      "character_name": "Name",
      "role": "protagonist|antagonist|supporting",
      "emotional_journey": "start → middle → end emotion",
      "key_actions": ["action1", "action2"],
      "appearance_description": "detailed physical: hair, eyes, build, clothing",
      "voice_tone": "calm|dramatic|whisper|playful"
    }}
  ],
  "tension_peak": "the single most intense moment",
  "cliffhanger": "the unresolved ending hook — MUST be an interrupted action with NO resolution",
  "trigger_text": "a 4-8 word phrase that creates dread/curiosity",
  "cut_mood": "dread|shock|mystery|urgency|suspense",
  "visual_style_constraints": ["style1", "style2"],
  "negative_constraints": ["avoid1", "avoid2"],
  "narration_style": "dramatic|calm|mysterious|playful",
  "target_total_duration_seconds": 30.0
}}

CRITICAL RULES:
- 3-5 scenes, each 4-6 seconds (total 12-18 seconds of content)
- Build tension: calm → curious → tense → PEAK → CUT
- Story MUST be interrupted at 70-85% — NEVER show resolution
- Last scene MUST end mid-action
- Character descriptions must be specific enough for visual consistency
- NEVER RESOLVE THE STORY"""

REDUCED_PLAN_PROMPT = """You are a story planner. Given a story, produce a JSON plan.

Output ONLY valid JSON:
{{
  "title": "episode title",
  "episode_number": {episode_number},
  "summary": "brief summary",
  "emotional_arc": "start → middle → end",
  "scene_breakdown": [
    {{
      "scene_number": 1,
      "location": "place",
      "time_of_day": "morning",
      "characters_present": ["Name"],
      "action_summary": "what happens",
      "emotional_beat": "tension",
      "visual_style_notes": "style notes",
      "estimated_duration_seconds": 5.0
    }}
  ],
  "character_arcs": [
    {{
      "character_name": "Name",
      "role": "protagonist",
      "emotional_journey": "journey",
      "key_actions": ["action"],
      "appearance_description": "appearance",
      "voice_tone": "dramatic"
    }}
  ],
  "cliffhanger": "unresolved ending",
  "visual_style_constraints": ["style"],
  "negative_constraints": ["avoid"],
  "narration_style": "dramatic",
  "target_total_duration_seconds": 25.0
}}

Rules: 3-4 scenes max. Keep it simple. End mid-action."""

CHARACTER_CONTINUITY_PROMPT = """Given this episode plan and any previous character data, produce a CHARACTER CONTINUITY PACKAGE as strict JSON.

Output ONLY valid JSON:
{{
  "characters": [
    {{
      "name": "Character Name",
      "gender": "male|female|other",
      "age_range": "child|teen|20s|30s|40s|elderly",
      "build": "slim|average|athletic|stocky",
      "hair": "detailed hair description",
      "eyes": "eye color and shape",
      "skin_tone": "specific tone",
      "clothing_default": "exact clothing description",
      "distinguishing_features": "scars, accessories, etc",
      "reference_prompt": "complete prompt to regenerate this character consistently"
    }}
  ],
  "style_lock": "art style to lock across all scenes",
  "color_palette": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
  "environment_consistency": "description of consistent environment elements"
}}"""

SCENE_MOTION_PROMPT = """Given this episode plan and character continuity, generate a SCENE MOTION PLAN for each scene.

Output ONLY valid JSON array:
[
  {{
    "scene_number": 1,
    "action": "character walks through misty forest",
    "emotion": "anxious",
    "camera_motion": "dolly_in|pan_left|pan_right|zoom_in|zoom_out|tracking|static|orbit|crane_up|tilt_up|tilt_down",
    "transition_type": "crossfade|cut|fade|dissolve",
    "motion_intensity": "subtle|moderate|dynamic|intense",
    "clip_duration_seconds": 5.0,
    "movement_notes": "fog drifts, leaves fall gently",
    "keyframe_prompt": "detailed prompt for the keyframe image",
    "video_prompt": "detailed prompt for the moving video clip"
  }}
]

RULES:
- keyframe_prompt must include character appearance from continuity package
- video_prompt must describe actual motion and movement
- camera_motion must enhance the emotional beat"""


# ═══════════════════════════════════════════════════════════════
# MULTI-LEVEL FALLBACK FOR SCENE GENERATION
# ═══════════════════════════════════════════════════════════════

async def generate_episode_plan_with_fallback(
    story_text: str,
    style_id: str = "cartoon_2d",
    episode_number: int = 1,
    previous_plan: Optional[Dict] = None,
    attempt_level: int = 0,
) -> Tuple[Optional[Dict], str]:
    """
    Multi-level fallback chain for episode plan generation.
    Returns (plan, model_used) tuple.

    Level 0: Primary model, full prompt
    Level 1: Same model, reduced prompt, lower temp
    Level 2: Fallback model, reduced prompt
    Level 3: Deterministic splitter (no LLM)
    """
    # Clamp story text to safe limits
    story_text = story_text[:4000]

    strategies = [
        {"model_provider": "openai", "model_name": "gpt-4o-mini", "prompt": "full", "temp": 0.7, "max_tokens": 3000},
        {"model_provider": "openai", "model_name": "gpt-4o-mini", "prompt": "reduced", "temp": 0.4, "max_tokens": 2000},
        {"model_provider": "google", "model_name": "gemini-2.0-flash", "prompt": "reduced", "temp": 0.3, "max_tokens": 2000},
        {"model_provider": "deterministic", "model_name": "text-splitter", "prompt": "none", "temp": 0, "max_tokens": 0},
    ]

    # Start from the appropriate level based on retry count
    start_level = min(attempt_level, len(strategies) - 1)

    for i in range(start_level, len(strategies)):
        strategy = strategies[i]
        model_name = f"{strategy['model_provider']}/{strategy['model_name']}"
        logger.info(f"[PLANNING] Attempting level {i} ({model_name})...")

        try:
            if strategy["model_provider"] == "deterministic":
                plan = _deterministic_scene_splitter(story_text, episode_number, style_id)
                if plan:
                    logger.info(f"[PLANNING] Deterministic fallback produced {len(plan.get('scene_breakdown', []))} scenes")
                    return plan, "deterministic/text-splitter"
                continue

            plan = await _call_llm_for_plan(
                story_text=story_text,
                style_id=style_id,
                episode_number=episode_number,
                previous_plan=previous_plan,
                model_provider=strategy["model_provider"],
                model_name=strategy["model_name"],
                prompt_mode=strategy["prompt"],
                temperature=strategy["temp"],
                max_tokens=strategy["max_tokens"],
            )

            if plan and _validate_plan(plan):
                plan = _enforce_plan_constraints(plan, story_text, episode_number)
                logger.info(f"[PLANNING] Level {i} succeeded ({model_name})")
                return plan, model_name
            else:
                logger.warning(f"[PLANNING] Level {i} ({model_name}) returned invalid plan")

        except Exception as e:
            logger.error(f"[PLANNING] Level {i} ({model_name}) failed: {e}")
            continue

    logger.error("[PLANNING] All strategies exhausted")
    return None, "none"


async def _call_llm_for_plan(
    story_text: str,
    style_id: str,
    episode_number: int,
    previous_plan: Optional[Dict],
    model_provider: str,
    model_name: str,
    prompt_mode: str,
    temperature: float,
    max_tokens: int,
) -> Optional[Dict]:
    """Call LLM with specified model and prompt configuration."""
    if not EMERGENT_KEY:
        logger.error("[PLANNING] No EMERGENT_LLM_KEY configured")
        return None

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    prompt_template = EPISODE_PLAN_PROMPT if prompt_mode == "full" else REDUCED_PLAN_PROMPT

    llm = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"plan_{episode_number}_{model_provider}",
        system_message=prompt_template.format(episode_number=episode_number),
    )
    llm = llm.with_model(model_provider, model_name)
    llm = llm.with_params(temperature=temperature, max_tokens=max_tokens)

    context = f"Story: {story_text[:3000]}\nStyle: {style_id}\nEpisode: {episode_number}"
    if previous_plan and prompt_mode == "full":
        context += f"\n\nPrevious episode plan:\n{json.dumps(previous_plan, indent=2)[:1000]}"

    response = await llm.send_message(UserMessage(text=context))
    return _parse_json(response)


def _validate_plan(plan: dict) -> bool:
    """Strict validation of LLM-generated plan."""
    if not isinstance(plan, dict):
        return False
    if not plan.get("title"):
        return False
    scenes = plan.get("scene_breakdown", [])
    if not scenes or not isinstance(scenes, list):
        return False
    if len(scenes) < 1 or len(scenes) > 12:
        return False
    # Validate each scene has required fields
    for scene in scenes:
        if not isinstance(scene, dict):
            return False
        if not scene.get("action_summary") and not scene.get("location"):
            return False
    # Character arcs
    chars = plan.get("character_arcs", [])
    if not chars or not isinstance(chars, list):
        return False
    return True


def _enforce_plan_constraints(plan: dict, story_text: str, episode_number: int) -> dict:
    """Enforce hard constraints on the plan."""
    # Cap scenes
    scenes = plan.get("scene_breakdown", [])
    if len(scenes) > 6:
        plan["scene_breakdown"] = scenes[:6]

    # Ensure scene numbers are sequential
    for i, scene in enumerate(plan.get("scene_breakdown", [])):
        scene["scene_number"] = i + 1
        # Cap per-scene duration
        dur = scene.get("estimated_duration_seconds", 5.0)
        scene["estimated_duration_seconds"] = max(3.0, min(dur, 8.0))

    # Ensure episode number
    plan["episode_number"] = episode_number

    # Ensure cliffhanger
    if not plan.get("cliffhanger") or len(plan.get("cliffhanger", "")) < 10:
        plan["cliffhanger"] = "But what they found next changed everything..."

    # Ensure trigger text
    if not plan.get("trigger_text") or len(plan.get("trigger_text", "")) < 5:
        plan["trigger_text"] = _generate_trigger_text(plan)

    # Ensure tension peak
    if not plan.get("tension_peak"):
        scenes = plan.get("scene_breakdown", [])
        if scenes:
            peak_scene = scenes[int(len(scenes) * 0.75)] if len(scenes) > 2 else scenes[-1]
            plan["tension_peak"] = peak_scene.get("action_summary", "The moment everything changes...")

    # Ensure cut mood
    if not plan.get("cut_mood"):
        plan["cut_mood"] = "suspense"

    return plan


def _deterministic_scene_splitter(story_text: str, episode_number: int = 1, style_id: str = "cartoon_2d") -> Optional[Dict]:
    """
    Emergency fallback: deterministic scene generation from text.
    No LLM needed. Splits story into chunks and creates structured scenes.
    """
    # Clean and split text
    text = story_text.strip()
    if not text:
        return None

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return None

    # Group into 3-5 scene chunks
    target_scenes = min(5, max(3, len(sentences) // 3))
    chunk_size = max(1, len(sentences) // target_scenes)

    scenes = []
    for i in range(target_scenes):
        start = i * chunk_size
        end = start + chunk_size if i < target_scenes - 1 else len(sentences)
        chunk = " ".join(sentences[start:end])
        if not chunk.strip():
            continue

        scenes.append({
            "scene_number": i + 1,
            "location": "story setting",
            "time_of_day": ["morning", "afternoon", "dusk", "night"][i % 4],
            "characters_present": ["Main Character"],
            "action_summary": chunk[:300],
            "dialogue": None,
            "emotional_beat": ["curiosity", "tension", "surprise", "fear", "suspense"][i % 5],
            "visual_style_notes": f"cinematic, {style_id.replace('_', ' ')} style",
            "estimated_duration_seconds": 5.0,
        })

    if not scenes:
        return None

    # Extract a rough title
    first_sentence = sentences[0][:80] if sentences else "Untitled Story"
    title = first_sentence.rstrip(".!?")

    # Build character from context
    char_name = "The Protagonist"
    for word in text.split()[:50]:
        if word[0].isupper() and len(word) > 2 and word not in ("The", "And", "But", "His", "Her", "Its", "She", "They"):
            char_name = word
            break

    plan = {
        "title": title[:100],
        "episode_number": episode_number,
        "summary": text[:200],
        "emotional_arc": "curiosity -> tension -> suspense -> cliffhanger",
        "scene_breakdown": scenes,
        "character_arcs": [{
            "character_name": char_name,
            "role": "protagonist",
            "emotional_journey": "uncertain -> determined -> interrupted",
            "key_actions": ["discovers something", "faces a challenge"],
            "appearance_description": "determined expression, practical clothing",
            "voice_tone": "dramatic",
        }],
        "tension_peak": scenes[-2]["action_summary"] if len(scenes) > 1 else scenes[0]["action_summary"],
        "cliffhanger": "But what happened next would change everything...",
        "trigger_text": "Something wasn't right...",
        "cut_mood": "suspense",
        "visual_style_constraints": [style_id.replace("_", " ")],
        "negative_constraints": ["no real people", "no graphic violence"],
        "narration_style": "dramatic",
        "target_total_duration_seconds": len(scenes) * 5.0,
    }

    return plan


# ═══════════════════════════════════════════════════════════════
# LEGACY ENTRY POINT — kept for backward compat
# ═══════════════════════════════════════════════════════════════

async def generate_episode_plan(
    story_text: str,
    style_id: str = "cartoon_2d",
    episode_number: int = 1,
    previous_plan: Optional[Dict] = None,
) -> Optional[Dict]:
    """Legacy entry point. Delegates to fallback chain at level 0."""
    plan, _ = await generate_episode_plan_with_fallback(
        story_text=story_text,
        style_id=style_id,
        episode_number=episode_number,
        previous_plan=previous_plan,
        attempt_level=0,
    )
    return plan


async def generate_character_continuity(
    episode_plan: Dict,
    existing_package: Optional[Dict] = None,
    style_id: str = "cartoon_2d",
) -> Optional[Dict]:
    if not EMERGENT_KEY:
        return None

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    try:
        llm = LlmChat(
            api_key=EMERGENT_KEY,
            session_id="continuity",
            system_message=CHARACTER_CONTINUITY_PROMPT,
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.5, max_tokens=2000)

        prompt = f"Episode plan:\n{json.dumps(episode_plan, indent=2)[:2000]}\nStyle: {style_id}"
        if existing_package:
            prompt += f"\n\nExisting continuity:\n{json.dumps(existing_package, indent=2)[:1500]}"

        response = await llm.send_message(UserMessage(text=prompt))
        return _parse_json(response)

    except Exception as e:
        logger.error(f"[PLANNING] Character continuity generation failed: {e}")
        return None


async def generate_scene_motion_plans(
    episode_plan: Dict,
    continuity: Dict,
    style_id: str = "cartoon_2d",
) -> Optional[List[Dict]]:
    if not EMERGENT_KEY:
        return None

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    try:
        llm = LlmChat(
            api_key=EMERGENT_KEY,
            session_id="motion",
            system_message=SCENE_MOTION_PROMPT,
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.7, max_tokens=4000)

        prompt = (
            f"Episode plan:\n{json.dumps(episode_plan, indent=2)[:2000]}\n\n"
            f"Character continuity:\n{json.dumps(continuity, indent=2)[:1500]}\n\n"
            f"Style: {style_id}"
        )

        response = await llm.send_message(UserMessage(text=prompt))
        result = _parse_json(response)
        return result if isinstance(result, list) else None

    except Exception as e:
        logger.error(f"[PLANNING] Scene motion plan generation failed: {e}")
        return None


def _parse_json(text: str) -> Optional[any]:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"[PLANNING] JSON parse failed: {e}")
        return None


def _generate_trigger_text(plan: Dict) -> str:
    TRIGGER_BANK = [
        "He shouldn't have looked...",
        "Something moved in the dark.",
        "This wasn't supposed to happen.",
        "Nobody was supposed to find this.",
        "The silence was wrong.",
        "Too late to turn back.",
        "It was watching them.",
        "The door wasn't there before.",
    ]
    title = plan.get("title", "")
    cliffhanger = plan.get("cliffhanger", "")
    h = sum(ord(c) for c in (title + cliffhanger))
    return TRIGGER_BANK[h % len(TRIGGER_BANK)]
