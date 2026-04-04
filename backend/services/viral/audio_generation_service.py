"""
Audio Generation Service
Primary: OpenAI TTS via Emergent LLM Key
Fallback: Skip gracefully — pack completes without audio
"""
import os
import logging

logger = logging.getLogger("viral.audio_gen")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

VOICE_TONES = {
    "neutral": "alloy",
    "energetic": "shimmer",
    "dramatic": "onyx",
}


async def generate_voiceover(text: str, tone: str = "energetic") -> dict:
    """
    Generate TTS voiceover from text.
    Returns {"audio_bytes": bytes|None, "fallback_used": bool, "skipped": bool, "tone": str}
    """
    voice = VOICE_TONES.get(tone, "alloy")

    if not EMERGENT_KEY:
        logger.warning("[AUDIO] No EMERGENT_LLM_KEY — skipping TTS")
        return {"audio_bytes": None, "fallback_used": False, "skipped": True, "tone": tone}

    if not text or len(text.strip()) < 10:
        logger.warning("[AUDIO] Text too short for TTS — skipping")
        return {"audio_bytes": None, "fallback_used": False, "skipped": True, "tone": tone}

    try:
        from emergentintegrations.llm.openai import OpenAITextToSpeech

        tts = OpenAITextToSpeech(api_key=EMERGENT_KEY)
        audio_bytes = await tts.generate_speech(
            text=text[:4096],
            model="tts-1",
            voice=voice,
            speed=1.0,
            response_format="mp3",
        )

        if not audio_bytes:
            logger.warning("[AUDIO] TTS returned empty bytes")
            return {"audio_bytes": None, "fallback_used": False, "skipped": True, "tone": tone}

        size_kb = len(audio_bytes) / 1024
        logger.info(f"[AUDIO] Voiceover generated ({size_kb:.0f}KB, voice={voice}, tone={tone})")
        return {"audio_bytes": audio_bytes, "fallback_used": False, "skipped": False, "tone": tone}

    except Exception as e:
        logger.warning(f"[AUDIO] TTS failed (tone={tone}): {e}")
        return {"audio_bytes": None, "fallback_used": False, "skipped": True, "tone": tone}
