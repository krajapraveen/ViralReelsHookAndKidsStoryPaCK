"""
Planning LLM Adapter — Interface for Qwen2.5-14B-Instruct.
Generates structured episode plans, scene breakdowns, and continuity packages.

In production: connects to self-hosted Qwen via API.
Currently: uses Emergent LLM key (GPT-4o-mini) as planning proxy.
"""
import os
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger("story_engine.adapters.planning")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

EPISODE_PLAN_PROMPT = """You are a cinematic story planner. Given a story prompt, produce a STRICT JSON episode plan.

Output ONLY valid JSON matching this exact schema:
{{
  "title": "episode title",
  "episode_number": {episode_number},
  "summary": "2-3 sentence summary",
  "emotional_arc": "emotion1 → emotion2 → emotion3 → cliffhanger",
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
  "cliffhanger": "the unresolved ending hook",
  "visual_style_constraints": ["style1", "style2"],
  "negative_constraints": ["avoid1", "avoid2"],
  "narration_style": "dramatic|calm|mysterious|playful",
  "target_total_duration_seconds": 30.0
}}

RULES:
- 3-6 scenes, each 4-8 seconds
- Every story MUST end with an unresolved cliffhanger
- Character descriptions must be specific enough for visual consistency
- Include at least 1 character with full appearance details
- Scene locations must be visually describable"""

CHARACTER_CONTINUITY_PROMPT = """Given this episode plan and any previous character data, produce a CHARACTER CONTINUITY PACKAGE as strict JSON.

This package locks visual traits for consistent generation across all scenes and future episodes.

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
    "movement_notes": "fog drifts, leaves fall gently, character's coat flutters",
    "keyframe_prompt": "detailed prompt for the keyframe image of this scene including character appearance, location, lighting, style",
    "video_prompt": "detailed prompt for the moving video clip including motion, camera movement, atmosphere"
  }}
]

RULES:
- keyframe_prompt must include character appearance from continuity package
- video_prompt must describe actual motion and movement
- camera_motion must enhance the emotional beat
- motion_intensity matches the scene's energy"""


async def generate_episode_plan(
    story_text: str,
    style_id: str = "cartoon_2d",
    episode_number: int = 1,
    previous_plan: Optional[Dict] = None,
) -> Optional[Dict]:
    """Generate structured episode plan from story text."""
    if not EMERGENT_KEY:
        logger.error("[PLANNING] No EMERGENT_LLM_KEY configured")
        return None

    from emergentintegrations.llm.chat import LlmChat, UserMessage

    try:
        llm = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"plan_{episode_number}",
            system_message=EPISODE_PLAN_PROMPT.format(episode_number=episode_number),
        )
        llm = llm.with_model("openai", "gpt-4o-mini")
        llm = llm.with_params(temperature=0.7, max_tokens=3000)

        context = f"Story: {story_text}\nStyle: {style_id}\nEpisode: {episode_number}"
        if previous_plan:
            context += f"\n\nPrevious episode plan for continuity:\n{json.dumps(previous_plan, indent=2)[:1500]}"

        response = await llm.send_message(UserMessage(text=context))
        return _parse_json(response)

    except Exception as e:
        logger.error(f"[PLANNING] Episode plan generation failed: {e}")
        return None


async def generate_character_continuity(
    episode_plan: Dict,
    existing_package: Optional[Dict] = None,
    style_id: str = "cartoon_2d",
) -> Optional[Dict]:
    """Generate or update character continuity package."""
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
            prompt += f"\n\nExisting continuity (update/extend, don't break):\n{json.dumps(existing_package, indent=2)[:1500]}"

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
    """Generate per-scene motion plans."""
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
    """Parse JSON from LLM response, handling markdown code blocks."""
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
