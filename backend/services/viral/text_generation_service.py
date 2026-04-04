"""
Text Generation Service
Primary: GPT-4o-mini
Fallback: Gemini
Last resort: Deterministic templates
"""
import os
import json
import logging
import random

logger = logging.getLogger("viral.text_gen")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def generate_hooks(idea: str, niche: str, count: int = 3) -> dict:
    """Returns {"hooks": [...], "fallback_used": bool}"""
    # Level 1: GPT-4o-mini
    if EMERGENT_KEY:
        try:
            hooks = await _llm_hooks(idea, niche, count, "openai", "gpt-4o-mini")
            if hooks and len(hooks) >= 1:
                return {"hooks": hooks[:count], "fallback_used": False}
        except Exception as e:
            logger.warning(f"[HOOKS] GPT-4o-mini failed: {e}")

        # Level 2: Gemini
        try:
            hooks = await _llm_hooks(idea, niche, count, "google", "gemini-2.0-flash")
            if hooks and len(hooks) >= 1:
                return {"hooks": hooks[:count], "fallback_used": True}
        except Exception as e:
            logger.warning(f"[HOOKS] Gemini fallback failed: {e}")

    # Level 3: Deterministic
    from services.viral.fallback_service import generate_fallback_hooks
    return {"hooks": generate_fallback_hooks(idea, niche, count), "fallback_used": True}


async def generate_script(idea: str, niche: str, hook: str) -> dict:
    """Returns {"script": str, "fallback_used": bool}"""
    if EMERGENT_KEY:
        try:
            script = await _llm_script(idea, niche, hook, "openai", "gpt-4o-mini")
            if script and len(script) > 100:
                return {"script": script, "fallback_used": False}
        except Exception as e:
            logger.warning(f"[SCRIPT] GPT-4o-mini failed: {e}")

        try:
            script = await _llm_script(idea, niche, hook, "google", "gemini-2.0-flash")
            if script and len(script) > 100:
                return {"script": script, "fallback_used": True}
        except Exception as e:
            logger.warning(f"[SCRIPT] Gemini fallback failed: {e}")

    from services.viral.fallback_service import generate_fallback_script
    return {"script": generate_fallback_script(idea, niche, hook), "fallback_used": True}


async def generate_captions(idea: str, niche: str, hook: str) -> dict:
    """Returns {"captions": {platform: text}, "fallback_used": bool}"""
    if EMERGENT_KEY:
        try:
            captions = await _llm_captions(idea, niche, hook, "openai", "gpt-4o-mini")
            if captions and len(captions) >= 3:
                return {"captions": captions, "fallback_used": False}
        except Exception as e:
            logger.warning(f"[CAPTIONS] GPT-4o-mini failed: {e}")

        try:
            captions = await _llm_captions(idea, niche, hook, "google", "gemini-2.0-flash")
            if captions and len(captions) >= 3:
                return {"captions": captions, "fallback_used": True}
        except Exception as e:
            logger.warning(f"[CAPTIONS] Gemini fallback failed: {e}")

    from services.viral.fallback_service import generate_fallback_captions
    return {"captions": generate_fallback_captions(idea, niche, hook), "fallback_used": True}


async def _llm_hooks(idea: str, niche: str, count: int, provider: str, model: str) -> list:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    llm = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"viral_hooks_{random.randint(1000,9999)}",
        system_message=(
            "You are a viral content hook generator. Create ultra-addictive, curiosity-gap hooks. "
            "Each hook: max 15 words, creates irresistible need to know more, feels incomplete. "
            "Return ONLY the hooks, one per line, no numbering."
        ),
    )
    llm = llm.with_model(provider, model)
    llm = llm.with_params(temperature=0.9, max_tokens=300)
    prompt = f"Generate {count} viral hooks for this content idea:\nIdea: {idea}\nNiche: {niche}\n\nReturn {count} hooks, one per line."
    response = await llm.send_message(UserMessage(text=prompt))
    lines = [line.strip().lstrip("-•*0123456789. ").strip('"').strip("'") for line in response.strip().split("\n") if line.strip()]
    return [h for h in lines if 3 <= len(h.split()) <= 20 and len(h) > 5]


async def _llm_script(idea: str, niche: str, hook: str, provider: str, model: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    llm = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"viral_script_{random.randint(1000,9999)}",
        system_message=(
            "You are a professional short-form video scriptwriter. Write scripts optimized for "
            "45-60 second videos. Structure: Hook (0-3s), Problem (3-10s), Solution (10-30s), "
            "Payoff (30-40s), CTA (40-45s). Use conversational, energetic tone."
        ),
    )
    llm = llm.with_model(provider, model)
    llm = llm.with_params(temperature=0.7, max_tokens=800)
    prompt = (
        f"Write a 45-second viral video script.\n\n"
        f"Hook: {hook}\nIdea: {idea}\nNiche: {niche}\n\n"
        f"Include section headers with timestamps. Make it punchy and actionable."
    )
    return await llm.send_message(UserMessage(text=prompt))


async def _llm_captions(idea: str, niche: str, hook: str, provider: str, model: str) -> dict:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    llm = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"viral_captions_{random.randint(1000,9999)}",
        system_message=(
            "You are a social media caption expert. Write platform-optimized captions. "
            "Return ONLY valid JSON with keys: instagram, tiktok, twitter, youtube_short, linkedin. "
            "Each caption should match that platform's style and include relevant hashtags."
        ),
    )
    llm = llm.with_model(provider, model)
    llm = llm.with_params(temperature=0.8, max_tokens=600)
    prompt = (
        f"Write social media captions for this content:\n\n"
        f"Hook: {hook}\nIdea: {idea}\nNiche: {niche}\n\n"
        f"Return ONLY valid JSON with keys: instagram, tiktok, twitter, youtube_short, linkedin"
    )
    response = await llm.send_message(UserMessage(text=prompt))
    # Extract JSON from response
    text = response.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
