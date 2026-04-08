"""
Instant Story Generation — Public endpoint for zero-friction story creation.
No auth required. Rate-limited by IP. Text-only for speed.
"""

import logging
import os
import re
import time
import random
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Request, HTTPException
from shared import db

logger = logging.getLogger("instant_story")

router = APIRouter(prefix="/public", tags=["instant-story"])

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
# LOAD_TEST_MODE: "mock" = mock LLM + skip ratelimit, "real" = real LLM + skip ratelimit, "" = production
LOAD_TEST_MODE = os.environ.get("LOAD_TEST_MODE", "").lower()

RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 5

# Concurrency limiter — prevents event loop saturation from too many concurrent LLM calls
LLM_SEMAPHORE = asyncio.Semaphore(10)


class QuickGenerateRequest(BaseModel):
    theme: Optional[str] = Field(None, max_length=500)
    source_title: Optional[str] = Field(None, max_length=200)
    source_snippet: Optional[str] = Field(None, max_length=1000)
    mode: str = Field("fresh", pattern="^(fresh|continue)$")
    session_id: Optional[str] = Field(None, max_length=64)
    device_token: Optional[str] = Field(None, max_length=128)


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

    if LOAD_TEST_MODE not in ("mock", "real") and not await _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # Mock mode for load testing — returns instant response without LLM call
    if LOAD_TEST_MODE == "mock":
        await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate minimal processing
        story_id = hashlib.sha256(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]
        mock_title = random.choice(["The Midnight Portal", "Shadows in the Deep", "The Last Signal", "Echoes of Tomorrow", "The Forgotten Key"])
        mock_text = (
            "The air crackled with electricity as she stepped through the threshold. "
            "Everything she knew — her home, her family, the world itself — shattered like glass behind her.\n\n"
            "Ahead lay a corridor of pure light, stretching into infinity. And at the end, "
            "a figure waited. Not standing. Not sitting. Floating.\n\n"
            "\"We've been expecting you,\" the figure said, its voice resonating in frequencies "
            "that made her teeth ache. \"For three thousand years.\"\n\n"
            "She opened her mouth to speak. But the words that came out weren't her own..."
        )
        # Skip DB writes in mock for max throughput
        return {"story_id": story_id, "title": mock_title, "story_text": mock_text, "status": "success", "allow_free_view": True}

    # --- Multi-signal first-time free viewing check ---
    # Primary: device_token (localStorage-persisted), Secondary: user_id (if logged in), Tertiary: IP hash
    ip_hash_val = hashlib.sha256(ip.encode()).hexdigest()[:16]

    # Extract user_id from auth token if present (optional, non-blocking)
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import jwt
            payload = jwt.decode(auth_header.split(" ", 1)[1], options={"verify_signature": False})
            user_id = payload.get("sub")
        except Exception:
            pass

    # Build multi-signal query: device_token > user_id > IP
    or_conditions = []
    if body.device_token:
        or_conditions.append({"device_token": body.device_token})
    if user_id:
        or_conditions.append({"user_id": user_id})
    or_conditions.append({"ip_hash": ip_hash_val})
    benefit_query = {"$or": or_conditions} if len(or_conditions) > 1 else or_conditions[0]

    benefit = await db.first_time_benefits.find_one(benefit_query, {"_id": 0})

    if benefit is None:
        # First-time user → free viewing for their first story
        allow_free_view = True
        # Mark benefit IMMEDIATELY to prevent concurrent/multi-tab abuse
        await db.first_time_benefits.insert_one({
            "device_token": body.device_token or "",
            "user_id": user_id or "",
            "ip_hash": ip_hash_val,
            "benefit_session_id": body.session_id or "anon",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif benefit.get("benefit_session_id") == (body.session_id or "anon") and body.mode == "continue":
        # Same session, continuing the free story → still allowed
        allow_free_view = True
    else:
        # Returning user (diff session) OR second story attempt (same session, fresh) → paywall
        allow_free_view = False

    if not EMERGENT_KEY:
        raise HTTPException(status_code=503, detail="Generation service temporarily unavailable.")

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
        # Use semaphore to limit concurrent LLM calls — prevents event loop saturation
        async with LLM_SEMAPHORE:
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
            "allow_free_view": allow_free_view,
        }

    except Exception as e:
        logger.error("[INSTANT_STORY] Generation failed: %s", e)
        await _log_request(ip, body.session_id, False)
        raise HTTPException(status_code=500, detail="Story generation failed. Please try again.")
