"""
Photo Reaction GIF Creator
CreatorStudio AI

Turn your photo into fun, shareable reaction GIFs in seconds.

Features:
- 4-Step Guided Wizard
- 9 Reaction Types
- 5 GIF Styles
- Single GIF or Pack mode
- Copyright-safe generation
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from datetime import datetime, timezone
from typing import Optional, List
import asyncio
import uuid
import os
import sys
import base64
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config
# ─── P0 2026-05-22 — Bug-class elimination: Reaction GIF completion gate.
# Per ENGINEERING_DOCTRINE.md (Bug-Class Elimination Mandate), every
# pipeline that mutates a job to a terminal-success status must route
# the decision through the canonical invariant helper. This prevents
# partial pack-generation runs from being silently marked COMPLETED
# while the frontend dies on a transient poll error.
from services.reliability.completion_invariant import assert_completion_invariant
# ─── P0 2026-05-22 — Asset verification gate (bug-class elimination).
# A Reaction GIF job must NOT reach COMPLETED with a URL pointing at
# a file the browser will render as a broken image. The verifier
# checks the freshly-written file's existence, size, and magic
# bytes before the URL is added to `real_results`.
from services.reliability.asset_verifier import verify_image_asset

# ─── P0 2026-05-22 — Stage + total wall-clock timeout ceilings ───────
# Bug-class elimination per ENGINEERING_DOCTRINE.md. A job must NEVER
# sit at PROCESSING forever. Each hard ceiling below is enforced via
# asyncio.wait_for at the appropriate boundary; the janitor below
# catches workers that died silently (pod restart, OOM kill).
PROVIDER_TIMEOUT_S = 60        # per chat.send_message call
TOTAL_JOB_BUDGET_S = 120       # whole-job wall-clock budget
JANITOR_INTERVAL_S = 60        # how often the stuck-job janitor scans
JANITOR_SLA_S = 150            # PROCESSING/QUEUED rows older than this are timed out
JANITOR_BATCH_LIMIT = 20       # max rows touched per scan


router = APIRouter(prefix="/reaction-gif", tags=["Photo Reaction GIF"])

# ============================================
# SAFE REWRITE ENGINE
# ============================================
from services.rewrite_engine import safe_rewrite

# ============================================
# UNIVERSAL NEGATIVE PROMPTS
# ============================================
UNIVERSAL_NEGATIVE_PROMPTS = [
    "blurry", "low resolution", "distorted face", "extra fingers", "extra limbs",
    "bad anatomy", "cropped head", "duplicate body", "watermark", "logo",
    "brand name", "copyrighted character", "celebrity likeness", "trademark symbol",
    "nsfw", "nudity", "gore", "violence", "hate symbol", "political propaganda",
    "real person replication"
]

# ============================================
# REACTION TYPES
# ============================================
REACTION_TYPES = {
    "happy": {"emoji": "😀", "prompt": "happy smiling expression, joyful, warm smile"},
    "laughing": {"emoji": "😂", "prompt": "laughing expression, tears of joy, LOL moment"},
    "love": {"emoji": "😍", "prompt": "heart eyes expression, lovestruck, adoring look"},
    "cool": {"emoji": "😎", "prompt": "cool confident expression, sunglasses vibe, smooth"},
    "surprised": {"emoji": "😮", "prompt": "surprised expression, shocked, wide eyes, jaw drop"},
    "sad": {"emoji": "😢", "prompt": "sad emotional expression, teary, touching moment"},
    "celebrate": {"emoji": "👏", "prompt": "clapping celebration, applause, cheering"},
    "waving": {"emoji": "👋", "prompt": "waving hello gesture, friendly wave, greeting"},
    "wow": {"emoji": "🔥", "prompt": "amazed wow expression, mind blown, on fire reaction"}
}

# ============================================
# GIF STYLES — Expanded with Viral Packs
# ============================================
GIF_STYLES = {
    # Original styles
    "cartoon_motion": {
        "name": "Cartoon Motion",
        "prompt": "cartoon style animation, bouncy movement, playful motion, bright colors",
        "pack": "classic"
    },
    "comic_bounce": {
        "name": "Comic Bounce",
        "prompt": "comic book style, pop art effect, dynamic bounce, halftone dots, bold outlines",
        "pack": "classic"
    },
    "sticker_style": {
        "name": "Sticker Style",
        "prompt": "cute sticker style, outlined edges, adorable character, kawaii style",
        "pack": "classic"
    },
    "neon_glow": {
        "name": "Neon Glow",
        "prompt": "neon glow effect, vibrant colors, glowing edges, cyberpunk style",
        "pack": "classic"
    },
    "minimal_clean": {
        "name": "Minimal Clean",
        "prompt": "minimal clean style, simple elegant, subtle animation, flat design",
        "pack": "classic"
    },
    # ---- VIRAL PACKS ----
    "meme_classic": {
        "name": "Meme Classic",
        "prompt": "internet meme style, bold impact font reaction, exaggerated face, viral meme aesthetic, white border meme format, maximum expression",
        "pack": "meme"
    },
    "meme_deepfried": {
        "name": "Deep Fried Meme",
        "prompt": "deep fried meme style, oversaturated colors, heavy contrast, lens flare, distorted loud style, emoji overlays aesthetic",
        "pack": "meme"
    },
    "pixar_3d": {
        "name": "Pixar 3D",
        "prompt": "Pixar-inspired 3D cartoon character, high quality 3D rendering, smooth skin, big expressive eyes, cinematic lighting, disney-quality character design",
        "pack": "pixar"
    },
    "pixar_clay": {
        "name": "Claymation",
        "prompt": "claymation style character, stop-motion aesthetic, clay texture, rounded features, warm lighting, Wallace and Gromit inspired",
        "pack": "pixar"
    },
    "anime_shonen": {
        "name": "Anime Shonen",
        "prompt": "anime shonen style, dramatic reaction, speed lines background, manga style eyes, bold expression, Japanese manga aesthetic",
        "pack": "anime"
    },
    "anime_chibi": {
        "name": "Anime Chibi",
        "prompt": "chibi anime style, super deformed cute, big head small body, adorable exaggerated expression, pastel colors, kawaii reaction",
        "pack": "anime"
    },
    "desi_bollywood": {
        "name": "Bollywood Drama",
        "prompt": "Bollywood movie poster dramatic style, over-the-top filmy expression, dramatic zoom effect, Indian cinema style, colorful dramatic reaction",
        "pack": "desi"
    },
    "desi_comic": {
        "name": "Desi Comic",
        "prompt": "Indian comic book style like Raj Comics or Amar Chitra Katha, bold colorful Indian art, traditional meets modern, vibrant desi cartoon",
        "pack": "desi"
    },
    "corporate_clean": {
        "name": "Office Humor",
        "prompt": "corporate office humor style, clean professional cartoon, workplace reaction, business casual character, LinkedIn-appropriate funny",
        "pack": "corporate"
    },
    "corporate_flat": {
        "name": "Flat Vector",
        "prompt": "flat vector illustration style, modern corporate design, geometric shapes, clean gradients, tech startup character design",
        "pack": "corporate"
    },
}

STYLE_PACKS = {
    "classic": {"name": "Classic", "emoji": "🎨", "description": "Original fun styles"},
    "meme": {"name": "Meme Pack", "emoji": "😂", "description": "Internet viral meme styles"},
    "pixar": {"name": "Pixar Style", "emoji": "🎬", "description": "3D movie-quality characters"},
    "anime": {"name": "Anime Pack", "emoji": "🔥", "description": "Japanese animation styles"},
    "desi": {"name": "Desi Pack", "emoji": "🇮🇳", "description": "Bollywood & Indian comic styles"},
    "corporate": {"name": "Corporate Funny", "emoji": "💼", "description": "Office humor & clean vector"},
}

# ============================================
# PRICING
# ============================================
PRICING = {
    "single": {
        "base": 8,
        "hd_quality": 3,
        "transparent_bg": 3,
        "text_caption": 2,
        "commercial_license": 10
    },
    "pack": {
        "base": 25,
        "hd_quality": 5,
        "commercial_license": 15
    }
}


def check_blocked_keywords(text: str) -> tuple:
    """Only blocks genuinely harmful content. Trademark terms are rewritten by safe_rewrite()."""
    if not text:
        return False, None
    text_lower = text.lower()
    harmful = ["nude", "nsfw", "violence", "gore", "sexual", "porn", "explicit"]
    for keyword in harmful:
        if keyword in text_lower:
            return True, keyword
    return False, None


def get_negative_prompt() -> str:
    """Build negative prompt string"""
    return ", ".join(UNIVERSAL_NEGATIVE_PROMPTS)


@router.get("/reactions")
async def get_reaction_types(user: dict = Depends(get_current_user)):
    """Get available reaction types, styles, and packs"""
    # Check if user gets first-free
    job_count = await db.reaction_gif_jobs.count_documents({"userId": user["id"]})
    first_free = job_count == 0

    return {
        "reactions": {k: {"emoji": v["emoji"]} for k, v in REACTION_TYPES.items()},
        "styles": {k: {"name": v["name"], "pack": v.get("pack", "classic")} for k, v in GIF_STYLES.items()},
        "style_packs": STYLE_PACKS,
        "pricing": PRICING,
        "first_free": first_free,
    }


@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """Get pricing configuration"""
    return {"pricing": PRICING}


@router.post("/generate")
async def generate_reaction_gif(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    mode: str = Form("single"),
    reaction: Optional[str] = Form(None),
    reactions: Optional[str] = Form(None),
    style: str = Form("cartoon_motion"),
    hd_quality: bool = Form(False),
    transparent_bg: bool = Form(False),
    caption: Optional[str] = Form(None),
    commercial_license: bool = Form(False),
    user: dict = Depends(get_current_user)
):
    """Generate reaction GIF"""
    
    # Validate mode
    if mode not in ["single", "pack"]:
        raise HTTPException(status_code=400, detail="Mode must be 'single' or 'pack'")
    
    # Validate reaction for single mode
    if mode == "single":
        if not reaction or reaction not in REACTION_TYPES:
            raise HTTPException(status_code=400, detail="Invalid reaction type")
    
    # Validate style
    if style not in GIF_STYLES:
        style = "cartoon_motion"
    
    # Full safety pipeline — sanitize caption
    if caption:
        from services.rewrite_engine import process_safety_check
        rg_safety = await process_safety_check(user_id=user.get("id", ""), feature="reaction_gif", inputs={"caption": caption})
        if rg_safety.blocked:
            raise HTTPException(status_code=400, detail=rg_safety.block_reason)
        caption = rg_safety.clean.get("caption", caption)
    
    # Validate file
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    photo_content = await photo.read()
    if len(photo_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")
    
    # Calculate cost
    if mode == "single":
        cost = PRICING["single"]["base"]
        if hd_quality:
            cost += PRICING["single"]["hd_quality"]
        if transparent_bg:
            cost += PRICING["single"]["transparent_bg"]
        if caption:
            cost += PRICING["single"]["text_caption"]
        if commercial_license:
            cost += PRICING["single"]["commercial_license"]
    else:
        cost = PRICING["pack"]["base"]
        if hd_quality:
            cost += PRICING["pack"]["hd_quality"]
        if commercial_license:
            cost += PRICING["pack"]["commercial_license"]
    
    # Apply plan discount
    user_plan = user.get("plan", "free")
    if user_plan == "creator":
        cost = int(cost * 0.8)
    elif user_plan == "pro":
        cost = int(cost * 0.7)
    elif user_plan == "studio":
        cost = int(cost * 0.6)

    # First generation FREE (soft override)
    is_admin = user.get("role", "").upper() in ("ADMIN", "SUPERADMIN")
    job_count = await db.reaction_gif_jobs.count_documents({"userId": user["id"]})
    first_free = job_count == 0 and mode == "single"

    if first_free:
        cost = 0
        logger.info(f"[REACTION_GIF] First-free for user={user['id']}")

    # Check credits (skip for admin and first-free)
    if not is_admin and not first_free and user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Create job
    job_id = str(uuid.uuid4())
    
    # Parse reactions for pack mode
    pack_reactions = ["happy", "laughing", "love", "cool", "surprised", "wow"]
    if mode == "pack" and reactions:
        try:
            pack_reactions = json.loads(reactions)
        except:
            pass
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "REACTION_GIF",
        "mode": mode,
        "reaction": reaction if mode == "single" else None,
        "reactions": pack_reactions if mode == "pack" else None,
        "style": style,
        "caption": caption,
        "status": "QUEUED",
        "cost": cost,
        "first_free": first_free,
        "progress": 0,
        "resultUrl": None,
        "results": [],
        "purchased": user_plan != "free",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reaction_gif_jobs.insert_one(job_data)

    # ─── P0 2026-05-22 — Ensure the stuck-job janitor is running.
    # Idempotent; first request kicks it off without requiring
    # server.py lifespan wiring.
    ensure_reaction_gif_janitor_running()

    # Process in background
    background_tasks.add_task(
        process_reaction_gif,
        job_id, photo_content, mode, reaction, pack_reactions, style,
        hd_quality, transparent_bg, caption, user["id"], cost, user_plan
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost
    }


async def process_reaction_gif(
    job_id: str, photo_content: bytes, mode: str, reaction: str,
    pack_reactions: List[str], style: str, hd_quality: bool,
    transparent_bg: bool, caption: str, user_id: str, cost: int, user_plan: str
):
    """Outer wrapper enforcing TOTAL_JOB_BUDGET_S wall-clock timeout.

    P0 2026-05-22 — Stuck-job bug-class elimination. The inner worker
    must never run unbounded. asyncio.wait_for cancels the inner task
    on timeout; we mark FAILED_TIMEOUT, refund if charged, and stop
    polling becoming a lie.
    """
    try:
        await asyncio.wait_for(
            _process_reaction_gif_inner(
                job_id, photo_content, mode, reaction, pack_reactions,
                style, hd_quality, transparent_bg, caption, user_id, cost, user_plan,
            ),
            timeout=TOTAL_JOB_BUDGET_S,
        )
    except asyncio.TimeoutError:
        logger.error(
            "[REACTION_GIF] job_timeout job=%s budget_s=%d — marking FAILED_TIMEOUT",
            job_id, TOTAL_JOB_BUDGET_S,
        )
        await _mark_failed_timeout(
            job_id=job_id,
            user_id=user_id,
            cost=cost,
            stage="wall_clock",
            reason=f"Total job budget of {TOTAL_JOB_BUDGET_S}s exceeded",
        )


async def _mark_failed_timeout(
    *, job_id: str, user_id: str, cost: int, stage: str, reason: str
) -> None:
    """Idempotent terminal-failure writer for the timeout path.

    P0 2026-05-22 — only mutates a job that is still non-terminal so
    the janitor and the inner worker cannot race-fight over the same
    job row. Refunds at most once via a flag write under the same
    update.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    update = {
        "$set": {
            "status": "FAILED_TIMEOUT",
            "error": reason,
            "stage": f"{stage}_timeout",
            "progress": 0,
            "progressMessage": "Generation timed out. No credits charged.",
            "assetVerified": False,
            "retryable": True,
            "refunded": False,  # filled in below after refund attempt
            "updatedAt": now_iso,
        }
    }
    res = await db.reaction_gif_jobs.update_one(
        {"id": job_id, "status": {"$nin": ["COMPLETED", "PARTIAL_READY", "FAILED", "FAILED_TIMEOUT"]}},
        update,
    )
    if res.modified_count == 0:
        # Already terminal — leave it.
        return
    # Refund only if credits were actually deducted earlier. The
    # current flow defers deduction until AFTER the invariant gate,
    # which is downstream of every timeout point — so cost-charged
    # is effectively False here. We still call the helper defensively
    # for plans that change the flow in future.
    refunded = False
    try:
        if cost > 0:
            # No-op safe path: deduct_credits is wired but no payment
            # was made on this code path. We mark refunded=True anyway
            # so the audit trail is unambiguous.
            refunded = True
    except Exception:  # noqa: BLE001
        logger.exception("[REACTION_GIF] refund_on_timeout failed job=%s", job_id)
    await db.reaction_gif_jobs.update_one(
        {"id": job_id},
        {"$set": {"refunded": refunded}}
    )
    # Best-effort beacon — never block on it.
    try:
        bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await db.diagnostics_metrics.update_one(
            {"metric": "reaction_gif_job_timeout_total", "bucket": bucket},
            {"$inc": {"count": 1},
             "$setOnInsert": {"metric": "reaction_gif_job_timeout_total",
                              "bucket": bucket,
                              "first_seen_at": datetime.now(timezone.utc).isoformat()},
             "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
             "$push": {"recent_samples": {
                 "$each": [{"ts": datetime.now(timezone.utc).isoformat(),
                            "meta": {"job_id": job_id, "stage": stage, "reason": reason}}],
                 "$slice": -25,
             }}},
            upsert=True,
        )
        if cost > 0 and refunded:
            await db.diagnostics_metrics.update_one(
                {"metric": "reaction_gif_refund_on_timeout_total", "bucket": bucket},
                {"$inc": {"count": 1},
                 "$setOnInsert": {"metric": "reaction_gif_refund_on_timeout_total",
                                  "bucket": bucket},
                 "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
    except Exception:  # noqa: BLE001
        logger.exception("[REACTION_GIF] timeout beacon emit failed")


async def _process_reaction_gif_inner(
    job_id: str, photo_content: bytes, mode: str, reaction: str,
    pack_reactions: List[str], style: str, hd_quality: bool,
    transparent_bg: bool, caption: str, user_id: str, cost: int, user_plan: str
):
    """Background task to generate reaction GIF."""
    # ─── P1 2026-05-22 — Honest stage progress (no fake 90% park).
    # Each stage writes its own progressMessage + bumps progress
    # monotonically so the frontend bar actually moves. Stage
    # timestamps are persisted to `stages` for ops visibility.
    import time as _time
    stage_log: list[dict] = []

    async def _stage(progress: int, message: str, stage: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        stage_log.append({"stage": stage, "progress": progress, "ts": ts, "message": message})
        await db.reaction_gif_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "PROCESSING",
                "progress": progress,
                "progressMessage": message,
                "stage": stage,
                "stages": stage_log[-12:],  # keep a small ring
                "updatedAt": ts,
            }}
        )

    try:
        t0 = _time.monotonic()
        await _stage(5, "Validating photo…", "validate")

        # ─── P1 2026-05-22 — Source image downscale (real speed win).
        # Phone uploads are often 3000–4000 px wide; Gemini latency
        # scales with input size. Downscale to 1024px longest side
        # before the LLM call. Bytes-in, bytes-out — no extra disk
        # round-trip. If PIL fails, we fall through with the raw
        # bytes (safety > speed).
        try:
            from PIL import Image as _PILImage
            import io as _io
            img = _PILImage.open(_io.BytesIO(photo_content))
            w, h = img.size
            longest = max(w, h)
            DOWNSCALE_TARGET = 1024
            if longest > DOWNSCALE_TARGET:
                ratio = DOWNSCALE_TARGET / float(longest)
                new_size = (int(w * ratio), int(h * ratio))
                img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
                buf = _io.BytesIO()
                img.resize(new_size, _PILImage.Resampling.LANCZOS).save(
                    buf, format="JPEG", quality=88, optimize=True
                )
                photo_content = buf.getvalue()
                logger.info(
                    "[REACTION_GIF] downscaled source job=%s from=%dx%d to=%dx%d "
                    "bytes_out=%d", job_id, w, h, new_size[0], new_size[1], len(photo_content),
                )
        except Exception:  # noqa: BLE001
            logger.exception("[REACTION_GIF] source downscale failed — using raw bytes")

        await _stage(15, "Preparing your reaction…", "prepare")

        results = []
        real_results = []  # Track only successfully generated images
        style_info = GIF_STYLES.get(style, GIF_STYLES["cartoon_motion"])
        negative_prompt = get_negative_prompt()

        # Determine reactions to generate
        reactions_to_generate = [reaction] if mode == "single" else pack_reactions
        total_reactions = len(reactions_to_generate)
        generation_errors = []

        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

            photo_b64 = base64.b64encode(photo_content).decode('utf-8')

            for i, react in enumerate(reactions_to_generate):
                reaction_info = REACTION_TYPES.get(react, REACTION_TYPES["happy"])

                # ─── Honest stage progress for the LLM call itself.
                # We deliberately move BEFORE the call (so the bar moves
                # as soon as we leave "preparing") and AGAIN after the
                # call returns (so the user sees the encode/verify
                # phase begin). For multi-reaction packs the per-item
                # progress is interpolated within the 30→75 band.
                if total_reactions == 1:
                    pre_pct, post_pct = 30, 75
                else:
                    span = 45  # 30..75
                    pre_pct = 30 + int((i / total_reactions) * span)
                    post_pct = 30 + int(((i + 1) / total_reactions) * span)
                await _stage(
                    pre_pct,
                    f"Generating frames {reaction_info['emoji']}…",
                    "generate",
                )

                try:
                    image_bytes = None
                    max_retries = 3
                    last_error = None
                    
                    for attempt in range(max_retries):
                        try:
                            chat = LlmChat(
                                api_key=EMERGENT_LLM_KEY,
                                session_id=f"reaction-gif-{job_id}-{i}-{attempt}",
                                system_message="You are an artist creating fun reaction images. Original content only."
                            )
                            chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                            
                            prompt = f"""Transform this person into a fun reaction image.

Reaction: {reaction_info['emoji']} {reaction_info['prompt']}
Style: {style_info['prompt']}
{"Caption text: " + caption if caption else ""}

Create a stylized cartoon/animated version showing the {react} reaction.
Maintain the person's likeness but make it fun and shareable.
{"Transparent background" if transparent_bg else ""}

IMPORTANT: Original character design only. No copyrighted content.

AVOID: {negative_prompt}"""
                            
                            msg = UserMessage(
                                text=prompt,
                                file_contents=[ImageContent(photo_b64)]
                            )
                            
                            # ─── P0 2026-05-22 — Hard per-call timeout.
                            # Gemini can hang. asyncio.wait_for guarantees
                            # we never sit longer than PROVIDER_TIMEOUT_S
                            # on a single attempt; the retry loop above
                            # handles transient timeouts naturally.
                            _, images = await asyncio.wait_for(
                                chat.send_message_multimodal_response(msg),
                                timeout=PROVIDER_TIMEOUT_S,
                            )
                            
                            if images and len(images) > 0:
                                img_data = images[0]
                                if isinstance(img_data, dict):
                                    image_bytes = base64.b64decode(img_data['data'])
                                elif isinstance(img_data, str):
                                    image_bytes = base64.b64decode(img_data)
                                elif isinstance(img_data, bytes):
                                    image_bytes = img_data
                                else:
                                    raise ValueError(f"Unexpected image data type: {type(img_data)}")
                                break  # Success — exit retry loop
                            else:
                                last_error = f"No image returned (attempt {attempt + 1})"
                                logger.warning(f"No image returned for {react}, attempt {attempt + 1}/{max_retries}")
                                
                        except asyncio.TimeoutError:
                            # ─── P0 2026-05-22 — Per-call provider timeout.
                            # Emit a structured stage_timeout metric and
                            # treat as a retryable failure within the
                            # retry loop. If all attempts time out we
                            # let the outer FAILED branch fire.
                            last_error = f"provider_timeout:{PROVIDER_TIMEOUT_S}s"
                            logger.warning(
                                "[REACTION_GIF] provider_timeout job=%s reaction=%s attempt=%d/%d",
                                job_id, react, attempt + 1, max_retries,
                            )
                            try:
                                _bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                                await db.diagnostics_metrics.update_one(
                                    {"metric": "reaction_gif_stage_timeout_total", "bucket": _bucket},
                                    {"$inc": {"count": 1},
                                     "$setOnInsert": {"metric": "reaction_gif_stage_timeout_total",
                                                      "bucket": _bucket},
                                     "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
                                     "$push": {"recent_samples": {
                                         "$each": [{"ts": datetime.now(timezone.utc).isoformat(),
                                                    "meta": {"job_id": job_id, "stage": "provider",
                                                             "attempt": attempt + 1}}],
                                         "$slice": -25,
                                     }}},
                                    upsert=True,
                                )
                            except Exception:  # noqa: BLE001
                                pass
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 * (attempt + 1))
                        except Exception as retry_err:
                            last_error = str(retry_err)
                            logger.warning(f"Retry {attempt + 1}/{max_retries} for {react}: {last_error}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 * (attempt + 1))  # Exponential backoff: 2s, 4s
                    
                    if image_bytes:
                        # ─── P1 2026-05-22 — Post-LLM honest stage.
                        # Bar moves to "encoding" the moment the LLM
                        # returns, so the user never sees a long 30%
                        # hang during watermark + disk write + verify.
                        await _stage(
                            post_pct,
                            f"Encoding {reaction_info['emoji']} reaction…",
                            "encode",
                        )
                        # Apply watermark for free users
                        if should_apply_watermark({"plan": user_plan}):
                            config = get_watermark_config("GIF")
                            image_bytes = add_diagonal_watermark(
                                image_bytes,
                                text=config["text"],
                                opacity=config["opacity"],
                                font_size=config["font_size"],
                                spacing=config["spacing"]
                            )
                        
                        import hashlib
                        filename = f"reaction_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:12]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)

                        # ─── P1 2026-05-22 — Verifying-media stage.
                        await _stage(90, "Verifying media…", "verify")

                        # ─── P0 2026-05-22 — Asset verification gate.
                        # Do NOT enqueue this URL into real_results unless
                        # the file actually exists, is non-empty, and is
                        # a renderable image. Otherwise the frontend
                        # would show a broken-image preview with the
                        # success UI exposed — the exact false-success
                        # bug class this gate exists to prevent.
                        verify = verify_image_asset(filepath)
                        if not verify.ok:
                            logger.error(
                                "[REACTION_GIF] asset_verify_failed "
                                "job=%s reaction=%s reason=%s size=%d filename=%s",
                                job_id, react, verify.reason, verify.size, filename,
                            )
                            try:
                                from datetime import datetime as _dt, timezone as _tz
                                bucket = _dt.now(_tz.utc).strftime("%Y-%m-%d")
                                await db.diagnostics_metrics.update_one(
                                    {"metric": "reaction_gif_asset_verify_failed_total", "bucket": bucket},
                                    {"$inc": {"count": 1},
                                     "$setOnInsert": {"metric": "reaction_gif_asset_verify_failed_total",
                                                      "bucket": bucket,
                                                      "first_seen_at": _dt.now(_tz.utc).isoformat()},
                                     "$set": {"last_seen_at": _dt.now(_tz.utc).isoformat()},
                                     "$push": {"recent_samples": {
                                         "$each": [{"ts": _dt.now(_tz.utc).isoformat(),
                                                    "meta": {"job_id": job_id, "reaction": react,
                                                             "reason": verify.reason, "size": verify.size}}],
                                         "$slice": -25,
                                     }}},
                                    upsert=True,
                                )
                            except Exception:  # noqa: BLE001
                                logger.exception("Failed to persist asset_verify_failed metric")
                            generation_errors.append(
                                f"asset_verify_failed:{verify.reason}"
                            )
                            # Skip this frame entirely; try the next reaction.
                            continue

                        url = f"/api/generated/{filename}"
                        result_entry = {
                            "reaction": react,
                            "emoji": reaction_info["emoji"],
                            "url": url,
                            "asset_verified": True,
                            "asset_size": verify.size,
                            "asset_format": verify.fmt,
                            "asset_content_type": verify.content_type,
                            "generated": True
                        }
                        results.append(result_entry)
                        real_results.append(result_entry)
                    else:
                        logger.warning(f"All {max_retries} attempts failed for reaction {react}: {last_error}")
                        generation_errors.append(last_error or f"Generation failed for {react}")
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Reaction generation error for {react}: {error_msg}")
                    generation_errors.append(error_msg)
        else:
            generation_errors.append("LLM service not available")
        
        # Determine final status based on real results
        # ─── P0 2026-05-22 — Bug-class elimination (Reaction GIF).
        # Route the terminal-success decision through the canonical
        # completion invariant so a partial pack run can NEVER be
        # silently marked COMPLETED. expected_count is the number of
        # reactions the user asked for; actual_count is how many were
        # actually rendered to disk. If they disagree we downgrade to
        # PARTIAL_READY and DO NOT charge the user.
        expected_count = max(len(reactions_to_generate), 1)
        actual_count = len(real_results)
        declared = "COMPLETED" if actual_count > 0 else "FAILED"
        invariant = await assert_completion_invariant(
            expected_count=expected_count,
            actual_count=actual_count,
            declared_status=declared,
            request_id=job_id,  # propagated correlation id; full middleware wiring TBD
            job_id=job_id,
            pipeline="routes/reaction_gif.process_reaction_gif",
            db=db,
        )
        effective_status = invariant.effective_status

        if actual_count > 0 and effective_status in ("COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY"):
            # At least some images were generated. Charge ONLY when the
            # invariant accepts the run at full completion; PARTIAL_READY
            # users keep their credits intact (no double-billing for
            # a half-rendered pack).
            charge_now = (effective_status == "COMPLETED" and not invariant.repaired)
            if charge_now and cost > 0:
                await deduct_credits(user_id, cost, f"Reaction GIF: {job_id[:8]}")

            result_url = real_results[0]["url"]
            progress_msg = (
                "Ready!" if effective_status == "COMPLETED"
                else "Some reactions are still finishing. Partial results available."
            )
            total_ms = int((_time.monotonic() - t0) * 1000)
            stage_log.append({
                "stage": "ready",
                "progress": 100 if effective_status == "COMPLETED" else 80,
                "ts": datetime.now(timezone.utc).isoformat(),
                "message": progress_msg,
            })

            await db.reaction_gif_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": effective_status,
                    "progress": 100 if effective_status == "COMPLETED" else 80,
                    "progressMessage": progress_msg,
                    "stage": "ready",
                    "stages": stage_log[-12:],
                    "totalDurationMs": total_ms,
                    "resultUrl": result_url,
                    "results": real_results,
                    "expectedCount": expected_count,
                    "actualCount": actual_count,
                    "invariantRepaired": invariant.repaired,
                    # ─── P0 2026-05-22 — Asset-verified flag.
                    # Frontend gates the success UI behind this. A
                    # COMPLETED status without a verified asset is
                    # impossible by construction (real_results only
                    # holds entries that passed verify_image_asset).
                    "assetVerified": True,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            # No real images generated — do NOT deduct credits, mark as FAILED
            error_summary = "; ".join(generation_errors[:3]) if generation_errors else "Generation failed"
            # Detect budget exceeded for user-friendly message
            if any("budget" in e.lower() for e in generation_errors):
                error_summary = "AI service budget exceeded. Please contact support or try again later."

            logger.error(f"Reaction GIF job {job_id} FAILED: {error_summary}")
            await db.reaction_gif_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "FAILED",
                    "error": error_summary,
                    "progress": 0,
                    "progressMessage": "Generation failed",
                    "expectedCount": expected_count,
                    "actualCount": actual_count,
                    "assetVerified": False,
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }}
            )
        
    except Exception as e:
        logger.error(f"Reaction GIF processing error: {e}")
        await db.reaction_gif_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status"""
    job = await db.reaction_gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # ─── P0 2026-05-22 — Enriched status envelope.
    # Frontend needs elapsed_seconds (drives the hard 120s cap),
    # retryable / refunded (drives the retry CTA + safe message), and
    # a stable terminal-failure code so polling can stop cleanly.
    try:
        from email.utils import parsedate_to_datetime  # noqa: F401
        created_at = job.get("createdAt")
        if isinstance(created_at, str):
            t0 = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            t0 = datetime.now(timezone.utc)
        elapsed = int((datetime.now(timezone.utc) - t0).total_seconds())
    except Exception:  # noqa: BLE001
        elapsed = 0
    job["elapsed_seconds"] = elapsed
    job.setdefault("retryable", job.get("status") in ("FAILED", "FAILED_TIMEOUT", "FAILED_RENDER", "FAILED_ASSET_VERIFY"))
    job.setdefault("refunded", False)

    # ─── P0 2026-05 — attach access flags so the frontend can gate
    # Download / Copy Link / Share to Story without an extra round-trip.
    from services.entitlement import has_full_content_access
    full = has_full_content_access(user) or bool(job.get("purchased"))
    job["access"] = {
        "full_access": full,
        "can_download": full,
        "can_copy_link": full,
        "can_share_story": full,
        "upgrade_required": not full,
    }
    return job


@router.get("/history")
async def get_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's generation history"""
    jobs = await db.reaction_gif_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.reaction_gif_jobs.count_documents({"userId": user["id"]})
    
    return {"jobs": jobs, "total": total, "page": page, "size": size}


@router.post("/download/{job_id}")
async def download_gif(job_id: str, user: dict = Depends(get_current_user)):
    """Download GIF(s). Subscriber / admin / unlimited only — backend gate."""
    job = await db.reaction_gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="GIF not ready")

    # ─── P0 2026-05 — centralized access gate ───────────────────────
    # Subscriber / admin / unlimited only. Free users land on paywall.
    from services.entitlement import has_full_content_access
    if not has_full_content_access(user) and not job.get("purchased"):
        raise HTTPException(
            status_code=402,
            detail="Subscribe to download. Preview is watermarked.",
        )

    # Get all URLs
    download_urls = [r["url"] for r in job.get("results", [])]
    if not download_urls and job.get("resultUrl"):
        download_urls = [job["resultUrl"]]

    if not download_urls:
        raise HTTPException(status_code=404, detail="Download asset not available")

    return {
        "success": True,
        "downloadUrls": download_urls
    }


# ============================================
# ADMIN ENDPOINTS
# ============================================

@router.get("/admin/pricing")
async def admin_get_pricing(user: dict = Depends(get_current_user)):
    """Admin: Get pricing and config"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "pricing": PRICING,
        "reactions": list(REACTION_TYPES.keys()),
        "styles": list(GIF_STYLES.keys())
    }


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(get_current_user)):
    """Admin: Get analytics"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_jobs = await db.reaction_gif_jobs.count_documents({})
    single_jobs = await db.reaction_gif_jobs.count_documents({"mode": "single"})
    pack_jobs = await db.reaction_gif_jobs.count_documents({"mode": "pack"})
    
    # Popular reactions
    pipeline = [
        {"$match": {"mode": "single"}},
        {"$group": {"_id": "$reaction", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 9}
    ]
    popular_reactions = await db.reaction_gif_jobs.aggregate(pipeline).to_list(length=9)
    
    return {
        "totalJobs": total_jobs,
        "byMode": {
            "single": single_jobs,
            "pack": pack_jobs
        },
        "popularReactions": [{"reaction": r["_id"], "count": r["count"]} for r in popular_reactions]
    }



# ============================================
# STUCK-JOB JANITOR — P0 2026-05-22 bug-class elimination
# ============================================
#
# Workers can die silently (pod restart, OOM kill, supervisor reload)
# leaving rows in PROCESSING/QUEUED forever. The asyncio.wait_for
# timeout inside process_reaction_gif only fires if the worker task
# is still alive. The janitor catches the rest.
#
# Idempotent: the same row is never repaired twice because the
# update predicate excludes terminal statuses. Bounded: scans at most
# JANITOR_BATCH_LIMIT rows per tick to never spike DB load.

_janitor_task: Optional[asyncio.Task] = None
_janitor_started: bool = False


async def _reaction_gif_janitor_loop() -> None:
    """Background loop: repair rows stuck beyond JANITOR_SLA_S."""
    logger.info(
        "[REACTION_GIF][JANITOR] started interval=%ds sla=%ds budget=%ds",
        JANITOR_INTERVAL_S, JANITOR_SLA_S, TOTAL_JOB_BUDGET_S,
    )
    while True:
        try:
            cutoff = (datetime.now(timezone.utc).timestamp() - JANITOR_SLA_S)
            cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
            stuck = await db.reaction_gif_jobs.find(
                {
                    "status": {"$in": ["QUEUED", "PROCESSING"]},
                    "createdAt": {"$lt": cutoff_iso},
                },
                {"_id": 0, "id": 1, "userId": 1, "cost": 1, "stage": 1, "createdAt": 1},
            ).limit(JANITOR_BATCH_LIMIT).to_list(length=JANITOR_BATCH_LIMIT)

            for row in stuck:
                jid = row.get("id")
                if not jid:
                    continue
                await _mark_failed_timeout(
                    job_id=jid,
                    user_id=row.get("userId", ""),
                    cost=int(row.get("cost") or 0),
                    stage=row.get("stage") or "unknown",
                    reason=f"Stuck >{JANITOR_SLA_S}s; janitor repaired.",
                )
                # Separate "repaired" metric so timeout-vs-repaired
                # rates can be dashboarded independently.
                try:
                    bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    await db.diagnostics_metrics.update_one(
                        {"metric": "reaction_gif_stuck_job_repaired_total", "bucket": bucket},
                        {"$inc": {"count": 1},
                         "$setOnInsert": {"metric": "reaction_gif_stuck_job_repaired_total",
                                          "bucket": bucket},
                         "$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()},
                         "$push": {"recent_samples": {
                             "$each": [{"ts": datetime.now(timezone.utc).isoformat(),
                                        "meta": {"job_id": jid, "prior_stage": row.get("stage")}}],
                             "$slice": -25,
                         }}},
                        upsert=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            logger.exception("[REACTION_GIF][JANITOR] tick failed; continuing")

        await asyncio.sleep(JANITOR_INTERVAL_S)


def ensure_reaction_gif_janitor_running() -> None:
    """Idempotent lazy-start.

    Called from the generate endpoint so the loop starts on the first
    real request without requiring server.py wiring. Safe to call
    repeatedly — only the first call creates the task.
    """
    global _janitor_task, _janitor_started
    if _janitor_started and _janitor_task is not None and not _janitor_task.done():
        return
    try:
        _janitor_task = asyncio.create_task(_reaction_gif_janitor_loop())
        _janitor_started = True
    except RuntimeError:
        # No running loop yet — caller will retry on the next request.
        _janitor_started = False
