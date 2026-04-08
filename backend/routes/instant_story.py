"""
Instant Story Generation — Public endpoint for zero-friction story creation.
No auth required. Rate-limited by IP. Text-only for speed.
"""

import logging
import os
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Request, HTTPException
from shared import db

logger = logging.getLogger("instant_story")

router = APIRouter(prefix="/public", tags=["instant-story"])

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 5


class QuickGenerateRequest(BaseModel):
    theme: Optional[str] = Field(None, max_length=500)
    source_title: Optional[str] = Field(None, max_length=200)
    source_snippet: Optional[str] = Field(None, max_length=1000)
    mode: str = Field("fresh", pattern="^(fresh|continue)$")
    session_id: Optional[str] = Field(None, max_length=64)


THEMES = [
    "A child discovers a magical door that only appears at midnight",
    "A lonely robot learns what friendship means in a futuristic city",
    "An underwater kingdom is discovered by a young explorer",
    "A mysterious forest where every tree tells a different story",
    "A time traveler accidentally changes their own childhood",
]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(ip: str) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=RATE_LIMIT_WINDOW)).isoformat()
    count = await db.instant_story_requests.count_documents({
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "created_at": {"$gte": cutoff},
    })
    return count < RATE_LIMIT_MAX


async def _log_request(ip: str, session_id: str, success: bool):
    await db.instant_story_requests.insert_one({
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
        "session_id": session_id or "anon",
        "success": success,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


@router.post("/quick-generate")
async def quick_generate(request: Request, body: QuickGenerateRequest):
    """Generate a short text story instantly. No auth required."""
    ip = _get_client_ip(request)

    if not await _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    if not EMERGENT_KEY:
        raise HTTPException(status_code=503, detail="Generation service temporarily unavailable.")

    import random

    if body.mode == "continue" and body.source_snippet:
        prompt = (
            f"Continue this story in 150-200 words. Make it vivid, engaging, and end on a cliffhanger "
            f"that makes the reader desperate to know what happens next.\n\n"
            f"Title: {body.source_title or 'Untitled'}\n"
            f"Story so far: {body.source_snippet}\n\n"
            f"Continue the story:"
        )
    else:
        theme = body.theme or random.choice(THEMES)
        prompt = (
            f"Write a short, captivating story (150-200 words) about: {theme}\n\n"
            f"Make it vivid and cinematic. End on a dramatic cliffhanger that makes "
            f"the reader desperate to know what happens next. Include sensory details "
            f"and emotional moments. Give it a creative title.\n\n"
            f"Format:\nTitle: [title]\n\n[story]"
        )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"instant_{body.session_id or 'anon'}",
            system_message="You are a master storyteller. Write vivid, cinematic stories that hook readers instantly.",
        )
        chat = chat.with_model("openai", "gpt-4o-mini")
        response = await chat.send_message(UserMessage(text=prompt))

        text = (response.text if hasattr(response, 'text') else str(response)).strip()

        title = "Your Story"
        story_text = text
        if text.startswith("Title:") or text.startswith("**Title"):
            lines = text.split("\n", 2)
            title = lines[0].replace("Title:", "").replace("**", "").replace("*", "").strip().strip('"')
            story_text = "\n".join(lines[1:]).strip()
        elif "\n\n" in text:
            parts = text.split("\n\n", 1)
            if len(parts[0]) < 100:
                title = parts[0].strip().strip("#").strip('"').strip("*").strip()
                story_text = parts[1].strip()
        
        # Clean markdown from title
        title = re.sub(r'[*#_`~]+', '', title).strip().strip('"').strip("'").strip()

        snippet = story_text[:200] + "..." if len(story_text) > 200 else story_text

        story_id = hashlib.md5(f"{time.time()}{ip}".encode()).hexdigest()[:12]

        await db.instant_stories.insert_one({
            "story_id": story_id,
            "title": title,
            "story_text": story_text,
            "snippet": snippet,
            "theme": body.theme,
            "mode": body.mode,
            "session_id": body.session_id or "anon",
            "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:16],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        await _log_request(ip, body.session_id, True)

        return {
            "story_id": story_id,
            "title": title,
            "story_text": story_text,
            "snippet": snippet,
            "status": "success",
        }

    except Exception as e:
        logger.error("[INSTANT_STORY] Generation failed: %s", e)
        await _log_request(ip, body.session_id, False)
        raise HTTPException(status_code=500, detail="Story generation failed. Please try again.")
