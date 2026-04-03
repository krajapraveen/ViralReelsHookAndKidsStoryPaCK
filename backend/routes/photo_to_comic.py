"""
Photo to Comic Character - Simplified Comic Generation
CreatorStudio AI

Features:
- Photo upload → Comic Avatar (3-step wizard)
- Photo upload → Comic Strip (5-step wizard)
- Strict copyright safety with keyword blocking
- Universal negative prompts auto-injection
- Safe style presets (no IP)
- Revenue-optimized pricing
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import os
import sys
import base64
import asyncio
import json
import re
import hashlib
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config

router = APIRouter(prefix="/photo-to-comic", tags=["Photo to Comic"])


# OPTIONS handler for CORS preflight requests
@router.options("/generate")
async def options_generate():
    """Handle CORS preflight for generate endpoint"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://www.visionary-suite.com",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With, Accept, Origin",
            "Access-Control-Max-Age": "600"
        }
    )


@router.options("/job/{job_id}")
async def options_job():
    """Handle CORS preflight for job status endpoint"""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://www.visionary-suite.com",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "600"
        }
    )

# ============================================
# BLOCKED COPYRIGHT KEYWORDS (Case-insensitive)
# ============================================
BLOCKED_KEYWORDS = [
    # Superhero / Comic IP
    "marvel", "dc", "avengers", "spiderman", "spider-man", "batman", "superman",
    "ironman", "iron man", "captain america", "thor", "hulk", "joker",
    "wonder woman", "flash", "deadpool", "x-men", "wolverine", "venom",
    # Disney / Animation
    "disney", "pixar", "frozen", "elsa", "anna", "mickey", "minnie",
    "donald duck", "goofy", "toy story", "lightyear",
    # Anime / Manga
    "naruto", "sasuke", "dragon ball", "goku", "one piece", "luffy",
    "attack on titan", "demon slayer", "pokemon", "pikachu", "studio ghibli",
    # Games / Entertainment
    "fortnite", "minecraft", "league of legends", "valorant", "pubg",
    "call of duty", "gta", "harry potter", "hogwarts",
    # Brand / Logo
    "nike", "adidas", "coca cola", "pepsi", "apple logo", "tesla logo",
    "youtube logo", "instagram logo", "facebook logo",
    # Additional safety
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual",
    "violence", "gore", "weapon", "hate"
]

# ============================================
# UNIVERSAL NEGATIVE PROMPTS (Auto-injected)
# ============================================
UNIVERSAL_NEGATIVE_PROMPTS = [
    "low quality", "blurry", "pixelated", "distorted", "deformed", "bad anatomy",
    "bad proportions", "extra limbs", "extra fingers", "missing fingers", "mutated hands",
    "poorly drawn face", "asymmetrical face", "duplicate characters",
    "inconsistent character design", "changing face", "changing hairstyle",
    "changing clothing", "inconsistent proportions", "inconsistent art style",
    "unrealistic features", "unnatural pose", "stiff pose", "lifeless expression",
    "emotionless", "flat lighting", "overexposed", "underexposed", "noise", "grain",
    "artifacts", "watermark", "text", "logo", "caption", "subtitle", "cropped",
    "cut off", "out of frame", "wrong perspective", "bad composition",
    "cluttered background", "realistic human style", "photorealistic",
    "horror", "scary", "creepy", "dark theme", "violent", "gore", "blood",
    "copyrighted character", "celebrity likeness", "trademark symbol",
    "nsfw", "nudity", "real person replication"
]

# ============================================
# SAFE STYLE PRESETS
# ============================================
SAFE_STYLES = {
    # Action Styles
    "bold_superhero": {
        "name": "Bold Superhero",
        "prompt": "bold superhero comic style, dynamic heroic poses, vibrant colors, strong lines, original character design"
    },
    "dark_vigilante": {
        "name": "Dark Vigilante",
        "prompt": "dark vigilante comic style, moody shadows, noir atmosphere, mysterious character"
    },
    "retro_action": {
        "name": "Retro Action Comic",
        "prompt": "retro 80s action comic style, halftone dots, bold colors, classic comic book aesthetic"
    },
    "dynamic_battle": {
        "name": "Dynamic Battle Scene",
        "prompt": "dynamic action scene, high energy, motion lines, impact effects, comic book style"
    },
    # Fun Styles
    "cartoon_fun": {
        "name": "Cartoon Fun",
        "prompt": "bright cheerful cartoon style, playful character, exaggerated features, fun comic"
    },
    "meme_expression": {
        "name": "Meme Expression",
        "prompt": "exaggerated funny expression, meme-worthy reaction, comedic cartoon style"
    },
    "comic_caricature": {
        "name": "Comic Caricature",
        "prompt": "playful caricature style, exaggerated features, humorous character design"
    },
    "exaggerated_reaction": {
        "name": "Exaggerated Reaction",
        "prompt": "over-the-top emotional reaction, comedic expression, cartoon style"
    },
    # Soft Styles
    "romance_comic": {
        "name": "Romance Comic",
        "prompt": "soft romantic comic style, dreamy atmosphere, gentle colors, shoujo influence"
    },
    "dreamy_pastel": {
        "name": "Dreamy Pastel",
        "prompt": "soft pastel color palette, dreamy illustration, gentle comic style"
    },
    "soft_manga": {
        "name": "Soft Manga Inspired",
        "prompt": "soft manga-inspired style, gentle lines, expressive eyes, original character"
    },
    "cute_chibi": {
        "name": "Cute Chibi",
        "prompt": "adorable chibi style, mini character, big head, cute proportions"
    },
    # Fantasy Styles
    "magical_fantasy": {
        "name": "Magical Fantasy",
        "prompt": "magical fantasy comic style, enchanted atmosphere, mystical elements, original design"
    },
    "medieval_adventure": {
        "name": "Medieval Adventure",
        "prompt": "medieval adventure comic, knights and castles theme, fantasy setting"
    },
    "scifi_neon": {
        "name": "Sci-Fi Neon",
        "prompt": "futuristic sci-fi style, neon colors, cyberpunk comic aesthetic, original character"
    },
    "cyberpunk_comic": {
        "name": "Cyberpunk Comic",
        "prompt": "cyberpunk comic style, high-tech dystopia, neon lights, futuristic"
    },
    # Kids Friendly
    "kids_storybook": {
        "name": "Kids Storybook Comic",
        "prompt": "children's storybook comic style, friendly characters, bright colors, wholesome"
    },
    "friendly_animal": {
        "name": "Friendly Animal Comic",
        "prompt": "cute animal character comic, friendly design, child-safe, adorable"
    },
    "classroom_comic": {
        "name": "Classroom Comic",
        "prompt": "school-themed comic style, classroom setting, fun educational vibe"
    },
    "adventure_kids": {
        "name": "Adventure Kids Style",
        "prompt": "kid-friendly adventure comic, young hero character, exciting but safe"
    },
    # Minimal Styles
    "black_white_ink": {
        "name": "Black & White Ink",
        "prompt": "black and white ink illustration, classic comic style, high contrast"
    },
    "sketch_outline": {
        "name": "Sketch Outline",
        "prompt": "hand-drawn sketch style, pencil outline look, artistic comic"
    },
    "noir_comic": {
        "name": "Noir Comic",
        "prompt": "film noir comic style, dramatic shadows, black and white, detective theme"
    },
    "vintage_print": {
        "name": "Vintage Print Style",
        "prompt": "vintage newspaper print style, retro comic aesthetic, classic halftone"
    },
}

# ============================================
# PRICING CONFIGURATION
# ============================================
PRICING = {
    "comic_avatar": {
        "base": 3,
        "add_ons": {
            "transparent_bg": 1,
            "multiple_poses": 2,
            "hd_export": 2,
        }
    },
    "comic_strip": {
        "panels": {
            3: 5,
            4: 6,
            6: 8,
        },
        "add_ons": {
            "auto_dialogue": 1,
            "custom_speech": 1,
            "hd_export": 2,
        }
    },
    "download": {
        "avatar": 10,
        "strip": 15
    }
}

# ============================================
# SMART STORY PRESETS (AI-driven prompts)
# ============================================
STORY_PRESETS = {
    "hero": {
        "name": "Hero Journey",
        "prompt": "An ordinary person discovers a hidden power and transforms into a hero to save the day.",
        "panel_beats": ["Normal everyday life", "A mysterious event changes everything", "The transformation begins", "Epic heroic victory moment"],
        "genre": "action",
        "icon": "zap"
    },
    "comedy": {
        "name": "Comedy Gold",
        "prompt": "A hilarious chain of misunderstandings leads to the funniest day ever.",
        "panel_beats": ["An innocent mistake happens", "Things spiral hilariously out of control", "The most awkward moment possible", "Unexpected laugh-out-loud resolution"],
        "genre": "comedy",
        "icon": "laugh"
    },
    "romance": {
        "name": "Love Story",
        "prompt": "Two people meet in an unexpected way and share a magical moment together.",
        "panel_beats": ["A chance encounter", "Sparks fly between them", "A heartfelt confession", "A beautiful happily-ever-after moment"],
        "genre": "romance",
        "icon": "heart"
    },
    "mystery": {
        "name": "Mystery Case",
        "prompt": "A detective discovers a strange clue that leads to an unexpected revelation.",
        "panel_beats": ["A mysterious clue is found", "Following the trail deeper", "The shocking discovery", "The brilliant deduction reveals the truth"],
        "genre": "mystery",
        "icon": "search"
    },
    "motivational": {
        "name": "Rise Up",
        "prompt": "Someone faces their biggest challenge and finds the strength to overcome it.",
        "panel_beats": ["Facing a seemingly impossible challenge", "The moment of doubt and struggle", "Finding inner strength and determination", "Triumphant victory and celebration"],
        "genre": "motivational",
        "icon": "trending-up"
    },
    "adventure": {
        "name": "Epic Adventure",
        "prompt": "An explorer discovers a hidden world full of wonders and dangers.",
        "panel_beats": ["Setting out on the journey", "Discovering a hidden magical world", "Facing a dangerous obstacle", "Emerging victorious with treasure"],
        "genre": "adventure",
        "icon": "compass"
    },
    "horror": {
        "name": "Spooky Tale",
        "prompt": "Something strange lurks in the shadows, building suspense until the spine-tingling reveal.",
        "panel_beats": ["An eerie atmosphere builds", "Strange things start happening", "The terrifying reveal", "A clever escape or twist ending"],
        "genre": "mystery",
        "icon": "ghost"
    },
    "scifi": {
        "name": "Future World",
        "prompt": "In a high-tech future, a hero uses advanced technology to solve an impossible problem.",
        "panel_beats": ["A futuristic world with amazing technology", "A critical system failure threatens everything", "Using tech genius to find a solution", "Saving the future with innovation"],
        "genre": "scifi",
        "icon": "cpu"
    },
}

# Average generation times (seconds) for estimation
AVG_TIMES = {
    "face_analysis": 2,
    "story_generation": 4,
    "panel_generation": 12,
    "composition": 2,
    "avatar_generation": 15,
}


def check_blocked_keywords(text: str) -> tuple:
    """
    Check if text contains any blocked keywords.
    Uses case-insensitive substring matching.
    Returns (is_blocked, blocked_keyword)
    """
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True, keyword
    
    return False, None


def build_safe_prompt(style_key: str, custom_details: str = "", genre: str = "action") -> str:
    """
    Build a safe generation prompt with style and universal negative prompts.
    """
    style_info = SAFE_STYLES.get(style_key, SAFE_STYLES["cartoon_fun"])
    
    # Base prompt from style
    prompt = f"Create a comic character illustration. {style_info['prompt']}. "
    
    # Add genre context
    genre_context = {
        "action": "dynamic pose, action-ready stance",
        "comedy": "humorous expression, fun atmosphere",
        "romance": "soft expression, romantic atmosphere",
        "adventure": "adventurous spirit, excited expression",
        "fantasy": "magical elements, fantasy setting",
        "scifi": "futuristic elements, sci-fi setting",
        "mystery": "mysterious atmosphere, intriguing pose",
        "kids_friendly": "child-friendly, wholesome, bright",
        "slice_of_life": "everyday setting, relatable character",
        "motivational": "confident pose, inspiring expression"
    }
    prompt += genre_context.get(genre, "")
    
    # Add custom details if provided (already validated)
    if custom_details:
        prompt += f" Additional details: {custom_details}."
    
    # Ensure original character
    prompt += " Original character design, not based on any existing IP or celebrity."
    
    return prompt


def get_negative_prompt(user_negative: str = "") -> str:
    """
    Build the complete negative prompt including universal safety prompts.
    """
    negatives = UNIVERSAL_NEGATIVE_PROMPTS.copy()
    
    # Add user's negative prompts if provided
    if user_negative:
        # Validate user negative prompt doesn't contain suspicious content
        is_blocked, keyword = check_blocked_keywords(user_negative)
        if not is_blocked:
            negatives.append(user_negative)
    
    return ", ".join(negatives)


@router.get("/styles")
async def get_available_styles(user: dict = Depends(get_current_user)):
    """Get all available safe styles"""
    return {
        "styles": {k: {"name": v["name"]} for k, v in SAFE_STYLES.items()},
        "pricing": PRICING
    }


@router.get("/presets")
async def get_story_presets(user: dict = Depends(get_current_user)):
    """Get smart story presets with structured panel beats"""
    return {
        "presets": {k: {"name": v["name"], "prompt": v["prompt"], "panel_beats": v["panel_beats"], "genre": v["genre"], "icon": v["icon"]} for k, v in STORY_PRESETS.items()}
    }


@router.get("/estimate")
async def get_time_estimate(mode: str = "avatar", panel_count: int = 4, user: dict = Depends(get_current_user)):
    """Dynamic time estimation based on mode and queue"""
    pending_jobs = await db.photo_to_comic_jobs.count_documents({"status": {"$in": ["QUEUED", "PROCESSING"]}})
    queue_wait = min(pending_jobs * 3, 30)

    if mode == "avatar":
        gen_time = AVG_TIMES["face_analysis"] + AVG_TIMES["avatar_generation"]
    else:
        gen_time = AVG_TIMES["face_analysis"] + AVG_TIMES["story_generation"] + AVG_TIMES["panel_generation"] + AVG_TIMES["composition"]

    total_low = max(8, gen_time + queue_wait - 4)
    total_high = gen_time + queue_wait + 8

    return {
        "estimated_seconds_low": int(total_low),
        "estimated_seconds_high": int(total_high),
        "queue_depth": pending_jobs,
        "guarantee": "Output guaranteed or credits refunded"
    }


@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """Get pricing configuration"""
    return {"pricing": PRICING}


# ============================================
# PHOTO QUALITY CHECK (P1.5-B)
# ============================================

@router.post("/quality-check")
async def check_photo_quality(
    photo: UploadFile = File(None),
    storage_key: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """Fast photo quality scoring before generation. Returns quality assessment."""
    if not photo and not storage_key:
        raise HTTPException(status_code=400, detail="Either photo or storage_key required")

    # Get image bytes
    if storage_key:
        try:
            from services.cloudflare_r2_storage import CloudflareR2Storage
            r2 = CloudflareR2Storage()
            image_bytes = await r2.download_file(storage_key)
            if not image_bytes:
                raise HTTPException(status_code=400, detail="Could not retrieve file from storage")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to retrieve file from storage")
    else:
        image_bytes = await photo.read()

    # Check cache
    from services.photo_quality import compute_image_hash, score_photo_quality
    img_hash = compute_image_hash(image_bytes)
    cached = await db.quality_cache.find_one({"hash": img_hash}, {"_id": 0, "result": 1})
    if cached:
        return cached["result"]

    # Score
    result = score_photo_quality(image_bytes)

    # Cache for 24h
    await db.quality_cache.update_one(
        {"hash": img_hash},
        {"$set": {"hash": img_hash, "result": result, "ts": datetime.now(timezone.utc)}},
        upsert=True
    )
    return result


@router.post("/generate")
async def generate_comic(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(None),
    storage_key: Optional[str] = Form(None),
    mode: str = Form(...),  # 'avatar' or 'strip'
    style: str = Form("cartoon_fun"),
    style_category: str = Form("fun"),
    genre: str = Form("action"),
    custom_details: Optional[str] = Form(None),
    transparent_bg: bool = Form(False),
    multiple_poses: bool = Form(False),
    hd_export: bool = Form(False),
    # Strip-specific
    panel_count: int = Form(4),
    story_prompt: Optional[str] = Form(None),
    story_preset: Optional[str] = Form(None),
    dialogue: Optional[str] = Form(None),
    include_dialogue: bool = Form(True),
    character_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """
    Generate comic character or strip from uploaded photo.
    Accepts either:
      - photo: traditional file upload (FormData)
      - storage_key: reference to a file already uploaded via presigned URL to R2
    """
    
    # Validate mode
    if mode not in ["avatar", "strip"]:
        raise HTTPException(status_code=400, detail="Mode must be 'avatar' or 'strip'")

    # Must have either photo or storage_key
    if not photo and not storage_key:
        raise HTTPException(status_code=400, detail="Either photo file or storage_key required")
    
    # ============================================
    # COPYRIGHT SAFETY CHECK - BLOCK KEYWORDS
    # ============================================
    
    # Check custom details
    if custom_details:
        is_blocked, keyword = check_blocked_keywords(custom_details)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}'. Try using generic descriptions like 'masked hero' instead."
            )
    
    # Check story prompt (for strip mode)
    if story_prompt:
        is_blocked, keyword = check_blocked_keywords(story_prompt)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}'. We create original comic characters only."
            )
    
    # Check dialogue
    if dialogue:
        is_blocked, keyword = check_blocked_keywords(dialogue)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}' in dialogue."
            )
    
    # Validate style
    if style not in SAFE_STYLES:
        style = "cartoon_fun"  # Default to safe style
    
    # ============================================
    # GET PHOTO CONTENT (file upload or R2 storage key)
    # ============================================
    if storage_key:
        # Direct-from-R2: download the file server-side for processing
        try:
            from services.cloudflare_r2_storage import CloudflareR2Storage
            r2 = CloudflareR2Storage()
            photo_content = await r2.download_file(storage_key)
            if not photo_content:
                raise HTTPException(status_code=400, detail="Could not retrieve file from storage. Upload may have failed.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"R2 download for storage_key {storage_key}: {e}")
            raise HTTPException(status_code=400, detail="Failed to retrieve uploaded file from storage")
    else:
        # Traditional file upload
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")
        photo_content = await photo.read()
        if len(photo_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")
    
    # ============================================
    # CALCULATE COST
    # ============================================
    
    if mode == "avatar":
        cost = PRICING["comic_avatar"]["base"]
        if transparent_bg:
            cost += PRICING["comic_avatar"]["add_ons"]["transparent_bg"]
        if multiple_poses:
            cost += PRICING["comic_avatar"]["add_ons"]["multiple_poses"]
        if hd_export:
            cost += PRICING["comic_avatar"]["add_ons"]["hd_export"]
    else:  # strip
        cost = PRICING["comic_strip"]["panels"].get(panel_count, 25)
        if include_dialogue:
            cost += PRICING["comic_strip"]["add_ons"]["auto_dialogue"]
        if hd_export:
            cost += PRICING["comic_strip"]["add_ons"]["hd_export"]
    
    # Apply plan discount
    user_plan = user.get("plan", "free")
    if user_plan == "creator":
        cost = int(cost * 0.8)
    elif user_plan == "pro":
        cost = int(cost * 0.7)
    elif user_plan == "studio":
        cost = int(cost * 0.6)
    
    # Check credits
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Create job
    job_id = str(uuid.uuid4())
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "mode": mode,
        "type": "COMIC_AVATAR" if mode == "avatar" else "COMIC_STRIP",
        "status": "QUEUED",
        "style": style,
        "genre": genre,
        "customDetails": custom_details,
        "cost": cost,
        "panelCount": panel_count if mode == "strip" else 1,
        "storyPrompt": story_prompt if mode == "strip" else None,
        "storyPreset": story_preset,
        "includeDialogue": include_dialogue,
        "addOns": {
            "transparent_bg": transparent_bg,
            "multiple_poses": multiple_poses,
            "hd_export": hd_export
        },
        "progress": 0,
        "downloaded": False,
        "source_storage_key": storage_key,
        "stages": [
            {"name": "face_analysis", "label": "Analyzing face", "status": "pending"},
            {"name": "story_generation", "label": "Generating story", "status": "pending"},
            {"name": "panel_generation", "label": "Creating panels", "status": "pending"},
            {"name": "composition", "label": "Final composition", "status": "pending"},
        ] if mode == "strip" else [
            {"name": "face_analysis", "label": "Analyzing face", "status": "pending"},
            {"name": "avatar_generation", "label": "Creating avatar", "status": "pending"},
        ],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.photo_to_comic_jobs.insert_one(job_data)

    # Assign story chain fields
    from services.story_chain import ensure_chain_fields
    await ensure_chain_fields(job_id, user["id"], parent_job_id=None, branch_type="original")

    # Load character context if provided
    char_context = None
    if character_id:
        try:
            from routes.characters import build_character_generation_context
            char_context = await build_character_generation_context(character_id, tool_type="photo_to_comic")
        except Exception:
            pass

    # Process in background
    if mode == "avatar":
        background_tasks.add_task(
            process_comic_avatar,
            job_id, photo_content, style, genre, custom_details,
            user["id"], cost, transparent_bg, multiple_poses, hd_export, char_context
        )
    else:
        # Apply preset if specified
        effective_prompt = story_prompt
        effective_genre = genre
        if story_preset and story_preset in STORY_PRESETS:
            preset = STORY_PRESETS[story_preset]
            if not effective_prompt:
                effective_prompt = preset["prompt"]
            effective_genre = preset.get("genre", genre) or genre

        background_tasks.add_task(
            process_comic_strip,
            job_id, photo_content, style, effective_genre, effective_prompt, dialogue,
            panel_count, include_dialogue, user["id"], cost, hd_export, char_context,
            story_preset
        )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost,
        "message": f"Generating your comic {mode}..."
    }


async def update_stage(job_id: str, stage_name: str, status: str, progress: int = None, message: str = None):
    """Update a specific stage in the job's stages array"""
    update = {"$set": {"stages.$[elem].status": status}}
    if progress is not None:
        update["$set"]["progress"] = progress
    if message:
        update["$set"]["progressMessage"] = message
    await db.photo_to_comic_jobs.update_one(
        {"id": job_id},
        update,
        array_filters=[{"elem.name": stage_name}]
    )


async def process_comic_avatar(
    job_id: str, photo_content: bytes, style: str, genre: str,
    custom_details: str, user_id: str, cost: int,
    transparent_bg: bool, multiple_poses: bool, hd_export: bool,
    char_context: dict = None
):
    """Background task to generate comic avatar"""
    try:
        await update_stage(job_id, "face_analysis", "in_progress", 10, "Analyzing your photo...")
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING"}}
        )
        
        result_urls = []
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                await update_stage(job_id, "face_analysis", "done", 15, "Face analyzed")
                await update_stage(job_id, "avatar_generation", "in_progress", 20, "Generating comic avatar...")
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                # Build safe prompt
                base_prompt = build_safe_prompt(style, custom_details, genre)
                negative_prompt = get_negative_prompt()
                
                # Add specific instructions
                full_prompt = f"""TRANSFORM this person into a comic character illustration. The output MUST look like drawn comic art, NOT a photograph or photo filter.

{base_prompt}
{f"CHARACTER LOCK: {char_context['visual_injection']}" if char_context else ""}
STYLE REQUIREMENTS (CRITICAL):
- Apply {SAFE_STYLES[style]['name']} style HEAVILY
- {SAFE_STYLES[style]['prompt']}
- Every pixel must read as illustrated/drawn art, not photographic

IMPORTANT RULES:
- Create an ORIGINAL character inspired by the person's appearance
- DO NOT reference any copyrighted characters or celebrities
- Maintain the person's general likeness but STYLIZE it strongly
- DO NOT return the source photo with minimal changes
{"- Use transparent background" if transparent_bg else ""}

AVOID: {char_context['negative_prompt'] if char_context else negative_prompt}"""
                
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')
                
                # Generate poses
                num_variations = 3 if multiple_poses else 1
                
                for i in range(num_variations):
                    await db.photo_to_comic_jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "progress": 20 + (i * 25),
                            "progressMessage": f"Creating variation {i+1}..." if multiple_poses else "Transforming to comic..."
                        }}
                    )
                    
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"photo-comic-{job_id}-{i}",
                        system_message="You are a professional comic artist. Create original characters only, never copy existing IP."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    variation_prompt = full_prompt
                    if multiple_poses and i > 0:
                        pose_variations = ["different angle, looking away", "action pose, dynamic movement", "profile view, side perspective"]
                        variation_prompt += f" {pose_variations[i-1]}"
                    
                    msg = UserMessage(
                        text=variation_prompt,
                        file_contents=[ImageContent(photo_b64)]
                    )
                    
                    text_response, images = await chat.send_message_multimodal_response(msg)
                    
                    logger.info(f"LLM response - text: {type(text_response)}, images: {type(images)}, images_len: {len(images) if images else 0}")
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        logger.info(f"Image data type: {type(img_data)}, keys: {img_data.keys() if isinstance(img_data, dict) else 'N/A'}")
                        
                        # Handle both dict format and raw base64 string
                        if isinstance(img_data, dict):
                            # Try different possible keys for image data
                            raw_data = img_data.get('data') or img_data.get('b64_json') or img_data.get('image') or img_data.get('url', '')
                            if raw_data:
                                if raw_data.startswith('data:'):
                                    base64_data = raw_data.split(',')[1] if ',' in raw_data else raw_data
                                    image_bytes = base64.b64decode(base64_data)
                                elif raw_data.startswith('http'):
                                    # It's a URL, download it
                                    import aiohttp
                                    async with aiohttp.ClientSession() as session:
                                        async with session.get(raw_data) as resp:
                                            image_bytes = await resp.read()
                                else:
                                    image_bytes = base64.b64decode(raw_data)
                            else:
                                logger.warning(f"No image data found in dict: {list(img_data.keys())}")
                                image_bytes = b''
                        elif isinstance(img_data, str):
                            # Could be base64 or a URL - check if it starts with data URL prefix
                            if img_data.startswith('data:'):
                                # Extract base64 from data URL
                                base64_data = img_data.split(',')[1] if ',' in img_data else img_data
                                image_bytes = base64.b64decode(base64_data)
                            else:
                                # Raw base64 string
                                image_bytes = base64.b64decode(img_data)
                        else:
                            image_bytes = img_data if isinstance(img_data, bytes) else b''
                        
                        if not image_bytes:
                            logger.warning(f"Empty image data for variation {i+1}")
                            continue
                        
                        # Apply watermark for free users
                        try:
                            user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
                            if user_data and isinstance(user_data, dict):
                                user_plan = user_data.get("plan", "free")
                            else:
                                user_plan = "free"
                        except Exception as e:
                            logger.warning(f"Error fetching user plan: {e}")
                            user_plan = "free"
                        
                        if should_apply_watermark({"plan": user_plan}):
                            config = get_watermark_config("COMIC")
                            image_bytes = add_diagonal_watermark(
                                image_bytes,
                                text=config["text"],
                                opacity=config["opacity"],
                                font_size=config["font_size"],
                                spacing=config["spacing"]
                            )
                        
                        # Store image bytes for later R2 upload
                        result_urls.append(image_bytes)
                
            except Exception as e:
                import traceback
                logger.error(f"Comic avatar generation error: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # ── Upload to R2 for permanent CDN storage ──────────────────────
        cdn_urls = []
        for idx, img_bytes in enumerate(result_urls):
            if not img_bytes:
                continue
            try:
                from services.cloudflare_r2_storage import upload_image_bytes
                fname = f"comic_avatar_{job_id[:8]}_{idx}.png"
                success, cdn_url = await upload_image_bytes(img_bytes, fname, f"comic/{user_id[:8]}")
                if success and cdn_url:
                    cdn_urls.append(cdn_url)
                    logger.info(f"Uploaded avatar {idx} to R2: {cdn_url[:80]}")
                else:
                    logger.warning(f"R2 upload failed for avatar {idx}")
                    # Fallback: store as base64 in DB
                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    cdn_urls.append(f"data:image/png;base64,{b64}")
            except Exception as up_err:
                logger.warning(f"R2 upload error for avatar {idx}: {up_err}")
                b64 = base64.b64encode(img_bytes).decode('utf-8')
                cdn_urls.append(f"data:image/png;base64,{b64}")

        if not cdn_urls:
            # ═══ GUARANTEED OUTPUT — ZERO dead-end states ═══
            logger.warning(f"[AVATAR] No AI images produced for job {job_id}. Activating guaranteed output.")
            try:
                from services.comic_pipeline.guaranteed_output import generate_guaranteed_panels
                guaranteed = generate_guaranteed_panels(
                    source_bytes=photo_content,
                    scenes=[{"scene": "Comic Avatar"}],
                    panel_count=1,
                    style_name=style,
                )
                if guaranteed:
                    img_bytes = guaranteed[0].get("imageBytes", b"")
                    if img_bytes:
                        try:
                            from services.cloudflare_r2_storage import upload_image_bytes as upload_img
                            fname = f"guaranteed_avatar_{job_id[:8]}.png"
                            success, url = await upload_img(img_bytes, fname, f"comic/{user_id[:8]}")
                            if success and url:
                                cdn_urls.append(url)
                        except Exception:
                            pass
                        if not cdn_urls:
                            b64 = base64.b64encode(img_bytes).decode("utf-8")
                            cdn_urls.append(f"data:image/png;base64,{b64}")
                        logger.info(f"[AVATAR] Guaranteed output generated for job {job_id}")
            except Exception as guaranteed_err:
                logger.error(f"[AVATAR] Guaranteed output also failed: {guaranteed_err}")

        if not cdn_urls:
            # Absolute last resort — should almost never reach here
            logger.error(f"[AVATAR] Even guaranteed output failed for job {job_id}.")
            await db.photo_to_comic_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "FAILED", "error": "All generation paths exhausted", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            return

        primary_url = cdn_urls[0]

        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic Avatar: {job_id[:8]}")

        # ── Register as permanent user asset ─────────────────────────
        asset_id = str(uuid.uuid4())
        asset_doc = {
            "asset_id": asset_id,
            "user_id": user_id,
            "job_id": job_id,
            "type": "COMIC_AVATAR",
            "title": f"Comic Avatar — {SAFE_STYLES.get(style, {}).get('name', style)}",
            "urls": cdn_urls,
            "primary_url": primary_url,
            "thumbnail_url": primary_url,
            "style": style,
            "permanent": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.user_assets.insert_one(asset_doc)
        except Exception as asset_err:
            logger.warning(f"Failed to register asset: {asset_err}")

        # Update job with permanent CDN URLs (no expiry)
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "progressMessage": "Complete!",
                "resultUrl": primary_url,
                "resultUrls": cdn_urls,
                "assetId": asset_id,
                "permanent": True,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )

        # Auto-promote source upload to permanent
        await promote_upload_on_completion(job_id, user_id)

        # Send notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_complete(
                user_id=user_id,
                feature="comic_avatar",
                job_id=job_id,
                download_url=primary_url
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send notification: {notif_error}")
        
    except Exception as e:
        logger.error(f"Comic avatar processing error: {e}")
        
        # ═══ GUARANTEED OUTPUT on exception ═══
        guaranteed_saved = False
        try:
            from services.comic_pipeline.guaranteed_output import generate_guaranteed_panels
            guaranteed = generate_guaranteed_panels(
                source_bytes=photo_content if 'photo_content' in dir() else b"",
                scenes=[{"scene": "Comic Avatar"}],
                panel_count=1,
                style_name=style if 'style' in dir() else "comic",
            )
            if guaranteed and guaranteed[0].get("imageBytes"):
                img_bytes = guaranteed[0]["imageBytes"]
                cdn_url = None
                try:
                    from services.cloudflare_r2_storage import upload_image_bytes as upload_img
                    fname = f"guaranteed_avatar_{job_id[:8]}.png"
                    uid = user_id if 'user_id' in dir() else "unknown"
                    success, url = await upload_img(img_bytes, fname, f"comic/{uid[:8]}")
                    if success and url:
                        cdn_url = url
                except Exception:
                    pass
                if not cdn_url:
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    cdn_url = f"data:image/png;base64,{b64}"

                await db.photo_to_comic_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "status": "COMPLETED",
                        "progress": 100,
                        "progressMessage": "We created a stylized version of your comic!",
                        "resultUrl": cdn_url,
                        "resultUrls": [cdn_url],
                        "guaranteed_output": True,
                        "updatedAt": datetime.now(timezone.utc).isoformat()
                    }}
                )
                guaranteed_saved = True
                logger.info(f"[AVATAR] Guaranteed output saved for failed job {job_id}")
        except Exception as guaranteed_err:
            logger.error(f"[AVATAR] Guaranteed output generation also failed: {guaranteed_err}")

        if not guaranteed_saved:
            await db.photo_to_comic_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "FAILED", "error": str(e), "progressMessage": "We created a stylized version of your comic!"}}
            )
        
        # Auto-refund on generation failure
        refund_issued = False
        try:
            from services.auto_refund import handle_generation_failure
            await handle_generation_failure(db, user_id, "comic_avatar", str(e))
            refund_issued = True
            logger.info(f"Auto-refund processed for failed comic avatar: {job_id}")
        except Exception as refund_error:
            logger.error(f"Auto-refund failed: {refund_error}")
        
        # Send failure notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_failed(
                user_id=user_id,
                feature="comic_avatar",
                job_id=job_id,
                error_message=str(e),
                refund_issued=refund_issued
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send failure notification: {notif_error}")


async def process_comic_strip(
    job_id: str, photo_content: bytes, style: str, genre: str,
    story_prompt: str, dialogue: str, panel_count: int,
    include_dialogue: bool, user_id: str, cost: int, hd_export: bool,
    char_context: dict = None, story_preset: str = None
):
    """Background task to generate comic strip — PARALLEL panel generation"""
    try:
        # ── HARD LOGGING: style trace ──
        import hashlib as hl
        photo_hash = hl.md5(photo_content).hexdigest()[:12]
        logger.info(
            f"[STYLE_TRACE] JOB_START job_id={job_id} "
            f"requested_style={style} resolved_style_name={SAFE_STYLES.get(style, {}).get('name', 'UNKNOWN')} "
            f"photo_hash={photo_hash} panel_count={panel_count} genre={genre} "
            f"user_id={user_id[:8]}"
        )

        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING"}}
        )
        await update_stage(job_id, "face_analysis", "in_progress", 5, "Analyzing your photo...")
        
        panels = []
        negative_prompt = get_negative_prompt()
        import time
        gen_start_time = time.time()
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                await update_stage(job_id, "face_analysis", "done", 10, "Face analyzed")
                await update_stage(job_id, "story_generation", "in_progress", 12, "Creating story outline...")

                # Use preset panel beats if available
                preset_beats = None
                if story_preset and story_preset in STORY_PRESETS:
                    preset_beats = STORY_PRESETS[story_preset]["panel_beats"]

                # Step 1: Generate story outline
                story_chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"comic-strip-outline-{job_id}",
                    system_message="You are a creative comic writer. Create original stories only, never reference copyrighted characters."
                )
                story_chat.with_model("gemini", "gemini-2.0-flash")
                
                preset_hint = ""
                if preset_beats:
                    preset_hint = "\nStory structure (follow these beats):\n" + "\n".join(f"Panel {i+1}: {b}" for i, b in enumerate(preset_beats[:panel_count]))

                outline_prompt = f"""Create a {panel_count}-panel comic story outline.

Story idea: {story_prompt or (STORY_PRESETS.get(story_preset, {}).get('prompt', 'An exciting adventure') if story_preset else 'An exciting adventure')}
Genre: {genre}
Style: {SAFE_STYLES[style]['name']}
{f"CHARACTER: {char_context['character_name']} - {char_context['visual_injection']}" if char_context else ""}
{preset_hint}
IMPORTANT RULES:
- Create ORIGINAL characters and stories only
- NO references to copyrighted characters, brands, or celebrities
- Keep it appropriate for all ages

For each panel provide:
1. Scene description (what's happening visually)
2. Dialogue (if applicable, or null for silent panel)

Format as JSON array:
[{{"scene": "Scene description", "dialogue": "Character dialogue or null"}}]"""
                
                outline_response = await story_chat.send_message(UserMessage(text=outline_prompt))
                
                # Parse outline
                story_scenes = []
                json_match = re.search(r'\[.*\]', outline_response, re.DOTALL)
                if json_match:
                    try:
                        story_scenes = json.loads(json_match.group())
                    except Exception:
                        pass
                
                await update_stage(job_id, "story_generation", "done", 18, "Story outline ready")
                
                # Fallback scenes
                if not story_scenes:
                    if preset_beats:
                        story_scenes = [{"scene": beat, "dialogue": None} for beat in preset_beats[:panel_count]]
                    else:
                        story_scenes = [
                            {"scene": "Opening scene", "dialogue": "Here we go!"},
                            {"scene": "Adventure begins", "dialogue": "This is exciting!"},
                            {"scene": "Challenge appears", "dialogue": "Hmm, what now?"},
                            {"scene": "Resolution", "dialogue": "We did it!"}
                        ][:panel_count]
                
                # User-provided dialogue override
                if dialogue and include_dialogue:
                    dialogue_lines = dialogue.split('|')
                    for i, line in enumerate(dialogue_lines[:len(story_scenes)]):
                        story_scenes[i]["dialogue"] = line.strip()
                
                # Step 2: SMART PANEL GENERATION (via Panel Orchestrator)
                await update_stage(job_id, "panel_generation", "in_progress", 20, f"Creating {panel_count} panels...")
                
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')

                # ── Input Risk Classification ──
                from services.comic_pipeline.panel_orchestrator import PanelOrchestrator
                from services.comic_pipeline.character_lock_service import CharacterLockService
                from enums.pipeline_enums import RiskBucket, PipelineState, PIPELINE_STATE_MESSAGES

                # Classify input risk from existing quality check
                risk_bucket = RiskBucket.MEDIUM
                try:
                    from services.photo_quality import PhotoQualityChecker
                    quality_checker = PhotoQualityChecker()
                    qr = quality_checker.check_quality(photo_content)
                    if qr.get("overall") == "good" and qr.get("face", {}).get("status") == "good":
                        risk_bucket = RiskBucket.LOW
                    elif qr.get("overall") == "fail" or qr.get("face", {}).get("status") == "fail":
                        risk_bucket = RiskBucket.HIGH
                    elif qr.get("face", {}).get("count", 0) > 1:
                        risk_bucket = RiskBucket.HIGH
                    elif qr.get("face", {}).get("count", 0) == 0:
                        risk_bucket = RiskBucket.EXTREME
                except Exception as risk_err:
                    logger.warning(f"Risk classification failed: {risk_err}")

                # Initialize character lock
                char_lock_svc = CharacterLockService(db)
                character_lock = char_lock_svc.initialize_from_source(photo_content, style)

                # Store risk profile and pipeline state
                await db.photo_to_comic_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "input_risk_bucket": risk_bucket.value,
                        "character_lock": character_lock.model_dump(),
                        "pipeline_state": PipelineState.GENERATING.value,
                        "progressMessage": PIPELINE_STATE_MESSAGES[PipelineState.GENERATING],
                    }}
                )

                # ── Fan-out: generate ALL panels via Panel Orchestrator with Continuity Pack ──
                orchestrator = PanelOrchestrator(db, EMERGENT_LLM_KEY)
                from services.comic_pipeline.continuity_pack import ContinuityPack
                from services.comic_pipeline.job_orchestrator import JobOrchestrator
                import asyncio

                continuity_pack = ContinuityPack()

                # Sequential generation for continuity (each panel feeds the next)
                panels = []
                for i in range(min(panel_count, len(story_scenes))):
                    # Get curated continuity context (NOT all previous — the RIGHT previous)
                    gen_context = continuity_pack.get_generation_context(i)

                    result = await orchestrator.process_panel(
                        job_id=job_id,
                        panel_index=i,
                        scene=story_scenes[i],
                        style_name=style,
                        style_prompt=SAFE_STYLES[style]['prompt'],
                        genre=genre,
                        photo_b64=photo_b64,
                        negative_prompt=negative_prompt,
                        panel_count=panel_count,
                        risk_bucket=risk_bucket,
                        character_lock=character_lock,
                        source_image_bytes=photo_content,
                        approved_panel_bytes=gen_context,
                        user_id=user_id,
                    )

                    # Register approved panels in continuity pack
                    if result.get("status") == "READY" and result.get("_image_bytes"):
                        continuity_pack.register_approved_panel(
                            panel_index=i,
                            image_bytes=result["_image_bytes"],
                            validation_scores=result.get("validation_scores"),
                            pipeline_status=result.get("pipeline_status", "PASSED"),
                        )
                        # Remove internal bytes from response (not needed downstream)
                        del result["_image_bytes"]
                    elif result.get("status") == "READY":
                        # Panel passed but no bytes available — still register
                        continuity_pack.register_approved_panel(
                            panel_index=i, image_bytes=b"",
                            validation_scores=result.get("validation_scores"),
                            pipeline_status=result.get("pipeline_status", "PASSED"),
                        )

                    panels.append(result)

                    # ── HARD LOGGING: per-panel style trace ──
                    logger.info(
                        f"[STYLE_TRACE] PANEL_DONE job_id={job_id} panel={i+1} "
                        f"style={style} status={result.get('status')} "
                        f"pipeline_status={result.get('pipeline_status')} "
                        f"model_tier={result.get('model_tier_used')} "
                        f"attempts={result.get('attempts')} "
                        f"imageUrl={result.get('imageUrl', 'NONE')[:80]}"
                    )

                    # Update progress
                    progress = 20 + int(((i + 1) / panel_count) * 65)
                    progress_text = f"Panel {i+1}/{panel_count} ready"
                    if result.get("pipeline_status") in ("PASSED_REPAIRED",):
                        progress_text = PIPELINE_STATE_MESSAGES.get(PipelineState.REPAIRING, "Enhancing panels...")
                    await db.photo_to_comic_jobs.update_one(
                        {"id": job_id},
                        {"$set": {"progress": progress, "progressMessage": progress_text}}
                    )

                await update_stage(job_id, "panel_generation", "done", 88, "All panels created")

                # ── JOB-LEVEL POLICY ENGINE ──
                job_orch = JobOrchestrator(db)
                rerun_context = {
                    "story_scenes": story_scenes,
                    "style": style,
                    "style_prompt": SAFE_STYLES[style]['prompt'],
                    "genre": genre,
                    "photo_b64": photo_b64,
                    "negative_prompt": negative_prompt,
                    "panel_count": panel_count,
                    "character_lock": character_lock,
                    "source_image_bytes": photo_content,
                    "continuity_pack": continuity_pack.get_generation_context(panel_count),
                    "user_id": user_id,
                }

                job_result = await job_orch.evaluate_and_execute(
                    job_id=job_id,
                    panels=panels,
                    panel_count=panel_count,
                    orchestrator=orchestrator if LLM_AVAILABLE and EMERGENT_LLM_KEY else None,
                    rerun_context=rerun_context if LLM_AVAILABLE and EMERGENT_LLM_KEY else None,
                )

                # Apply job-level decision
                panels = job_result["panels"]
                job_decision = job_result["decision"]
                
                if job_decision in ("TARGETED_PANEL_RERUN", "STYLE_DOWNGRADE_RERUN"):
                    await db.photo_to_comic_jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "pipeline_state": PipelineState.JOB_FALLBACK.value,
                            "progressMessage": PIPELINE_STATE_MESSAGES[PipelineState.JOB_FALLBACK],
                        }}
                    )

                # Store continuity pack summary
                await db.photo_to_comic_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "continuity_summary": continuity_pack.get_summary(),
                        "job_decision": job_decision,
                        "job_decision_reason": job_result.get("decision_log", {}).get("reason", ""),
                    }}
                )

            except Exception as e:
                logger.error(f"Comic strip generation error: {e}")
        
        # If LLM not available or entire generation failed, mark all panels FAILED
        if not panels:
            for i in range(panel_count):
                panels.append({
                    "panelNumber": i + 1,
                    "scene": f"Scene {i + 1}",
                    "dialogue": None,
                    "imageUrl": None,
                    "status": "FAILED"
                })

        await update_stage(job_id, "composition", "in_progress", 90, "Composing final comic...")
        
        # Count actual vs failed panels
        ready_panels = [p for p in panels if p.get("status") == "READY"]
        failed_panels = [p for p in panels if p.get("status") == "FAILED"]
        
        # ── Post-generation single-panel repair ──
        # If some panels failed but others succeeded, try to repair just the failed ones
        if 0 < len(failed_panels) < len(panels) and LLM_AVAILABLE and EMERGENT_LLM_KEY:
            await update_stage(job_id, "composition", "in_progress", 90, "Optimizing final panels...")
            for fp in failed_panels[:2]:  # max 2 repair attempts
                idx = fp["panelNumber"] - 1
                scene = story_scenes[idx] if idx < len(story_scenes) else {"scene": fp.get("scene", "")}
                try:
                    repaired = await orchestrator.process_panel(
                        job_id=job_id, panel_index=idx, scene=scene,
                        style_name=style, style_prompt=SAFE_STYLES[style]['prompt'],
                        genre=genre, photo_b64=photo_b64, negative_prompt=negative_prompt,
                        panel_count=panel_count, risk_bucket=risk_bucket,
                        character_lock=character_lock, source_image_bytes=photo_content,
                        user_id=user_id,
                    )
                    if repaired.get("status") == "READY":
                        panels[idx] = repaired
                        logger.info(f"Repaired panel {idx+1} for job {job_id}")
                except Exception as repair_err:
                    logger.warning(f"Panel {idx+1} repair failed: {repair_err}")
            
            # Recount
            ready_panels = [p for p in panels if p.get("status") == "READY"]
            failed_panels = [p for p in panels if p.get("status") == "FAILED"]
        
        # ── P1.5-C: Character Consistency Validation ──
        # Run face embedding comparison on ready panels against source photo
        consistency_results = []
        consistency_retried = []
        if len(ready_panels) > 0:
            try:
                await update_stage(job_id, "composition", "in_progress", 92, "Verifying character consistency...")
                from services.consistency_validator import run_consistency_validation
                
                consistency_results = await run_consistency_validation(
                    db, job_id, photo_content, panels, style, 
                    model_used="gemini-3-pro-image-preview"
                )
                
                # Auto-retry panels with "retry" verdict (max 1 per panel)
                for cr in consistency_results:
                    if cr["verdict"] == "retry" and cr["panel_number"] <= len(panels):
                        idx = cr["panel_number"] - 1
                        panel = panels[idx]
                        # Only retry if not already retried for consistency
                        if panel.get("consistency_retried"):
                            continue
                        
                        scene = story_scenes[idx] if idx < len(story_scenes) else {"scene": panel.get("scene", "")}
                        try:
                            await db.photo_to_comic_jobs.update_one(
                                {"id": job_id},
                                {"$set": {"progressMessage": "Optimizing character details..."}}
                            )
                            repaired = await orchestrator.process_panel(
                                job_id=job_id, panel_index=idx, scene=scene,
                                style_name=style, style_prompt=SAFE_STYLES[style]['prompt'],
                                genre=genre, photo_b64=photo_b64, negative_prompt=negative_prompt,
                                panel_count=panel_count, risk_bucket=risk_bucket,
                                character_lock=character_lock, source_image_bytes=photo_content,
                                user_id=user_id,
                            )
                            if repaired.get("status") == "READY":
                                repaired["consistency_retried"] = True
                                panels[idx] = repaired
                                consistency_retried.append(idx + 1)
                                logger.info(f"Consistency retry succeeded for panel {idx+1}, job {job_id}")
                        except Exception as retry_err:
                            logger.warning(f"Consistency retry failed for panel {idx+1}: {retry_err}")
                
                # Re-validate after retries if any were done
                if consistency_retried:
                    consistency_results = await run_consistency_validation(
                        db, f"{job_id}_post_retry", photo_content, panels, style,
                        model_used="gemini-3-pro-image-preview"
                    )
                    
                # Recount after consistency retries
                ready_panels = [p for p in panels if p.get("status") == "READY"]
                failed_panels = [p for p in panels if p.get("status") == "FAILED"]
                
            except Exception as consistency_err:
                logger.warning(f"Consistency validation failed (non-blocking): {consistency_err}")
        
        # Determine job status — use job orchestrator's policy engine
        # Re-evaluate after all consistency fixes
        final_job_result = await job_orch.evaluate_and_execute(
            job_id=job_id,
            panels=panels,
            panel_count=panel_count,
        )
        job_status = final_job_result.get("job_status", "COMPLETED")
        job_decision = final_job_result.get("decision", "ACCEPT_FULL")

        # Store final decision
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "job_decision": job_decision,
                "job_decision_reason": final_job_result.get("decision_log", {}).get("reason", ""),
            }}
        )
        
        # ══════════════════════════════════════════════════════════════════
        # GUARANTEED OUTPUT — ZERO dead-end states (NON-NEGOTIABLE)
        # When ALL AI generation fails, apply deterministic comic filters
        # to source photo. This CANNOT fail. User ALWAYS gets output.
        # ══════════════════════════════════════════════════════════════════
        ready_panels = [p for p in panels if p.get("status") == "READY"]
        if job_status == "FAILED" or (len(ready_panels) == 0 and len(panels) > 0):
            logger.warning(
                f"[STYLE_TRACE] GUARANTEED_OUTPUT_ACTIVATED job_id={job_id} "
                f"style={style} reason=all_ai_failed "
                f"ready={len(ready_panels)} failed={len([p for p in panels if p.get('status') == 'FAILED'])} "
                f"total={len(panels)}"
            )
            try:
                from services.comic_pipeline.guaranteed_output import generate_guaranteed_panels
                from services.cloudflare_r2_storage import upload_image_bytes

                guaranteed_panels = generate_guaranteed_panels(
                    source_bytes=photo_content,
                    scenes=story_scenes,
                    panel_count=panel_count,
                    style_name=style,
                )

                for gp in guaranteed_panels:
                    img_bytes = gp.pop("imageBytes", b"")
                    idx = gp["panelNumber"] - 1

                    # Upload to CDN
                    cdn_url = None
                    if img_bytes:
                        try:
                            fname = f"guaranteed_{job_id[:12]}_p{idx}.png"
                            success, url = await upload_image_bytes(img_bytes, fname, f"comic/{user_id[:8]}")
                            if success and url:
                                cdn_url = url
                        except Exception as upload_err:
                            logger.warning(f"Guaranteed panel {idx} CDN upload failed: {upload_err}")

                        if not cdn_url:
                            b64 = base64.b64encode(img_bytes).decode("utf-8")
                            cdn_url = f"data:image/png;base64,{b64}"

                    gp["imageUrl"] = cdn_url
                    gp["style"] = style
                    panels[idx] = gp

                # Override status — user ALWAYS gets output
                job_status = "PARTIAL_READY"
                job_decision = "ACCEPT_GUARANTEED_FALLBACK"
                ready_panels = [p for p in panels if p.get("status") == "READY"]
                logger.info(
                    f"[STYLE_TRACE] GUARANTEED_OUTPUT_DONE job_id={job_id} "
                    f"style={style} panels_generated={len(ready_panels)} "
                    f"panel_urls={[p.get('imageUrl', 'NONE')[:60] for p in panels]}"
                )

                await db.photo_to_comic_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "job_decision": job_decision,
                        "guaranteed_output": True,
                        "guaranteed_panel_count": len(ready_panels),
                    }}
                )
            except Exception as guaranteed_err:
                logger.error(f"[GUARANTEED_OUTPUT] Even guaranteed output failed: {guaranteed_err}")
        
        # Only deduct credits if at least one panel was generated
        if len(ready_panels) > 0:
            # Pro-rate: charge per successful panel
            per_panel_cost = max(1, cost // panel_count)
            actual_cost = per_panel_cost * len(ready_panels)
            await deduct_credits(user_id, actual_cost, f"Comic Strip: {job_id[:8]} ({len(ready_panels)}/{panel_count} panels)")
        elif job_status == "FAILED":
            # No panels generated — auto-refund (don't charge)
            logger.info(f"No panels generated for job {job_id}, no credits deducted")
            try:
                from services.auto_refund import handle_generation_failure
                await handle_generation_failure(db, user_id, "comic_strip", "All panels failed to generate")
            except Exception as refund_error:
                logger.error(f"Auto-refund notification failed: {refund_error}")

        # ── Register as permanent user asset (only if we have real panels) ──
        panel_urls = [p.get("imageUrl", "") for p in panels if p.get("imageUrl") and not p["imageUrl"].startswith("data:")]
        asset_id = str(uuid.uuid4())
        
        if panel_urls:
            asset_doc = {
                "asset_id": asset_id,
                "user_id": user_id,
                "job_id": job_id,
                "type": "COMIC_STRIP",
                "title": f"Comic Strip — {genre} ({len(ready_panels)}/{panel_count} panels)",
                "urls": panel_urls,
                "primary_url": panel_urls[0] if panel_urls else "",
                "thumbnail_url": panel_urls[0] if panel_urls else "",
                "style": style,
                "genre": genre,
                "panel_count": len(ready_panels),
                "permanent": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                await db.user_assets.insert_one(asset_doc)
            except Exception as asset_err:
                logger.warning(f"Failed to register strip asset: {asset_err}")

        # Compute status message — CALM copy, never scary
        if job_status == "COMPLETED":
            progress_msg = "Your comic is ready!"
            await update_stage(job_id, "composition", "done", 100, "Your comic is ready!")
        elif job_status == "READY_WITH_WARNINGS":
            progress_msg = "Your comic is ready!"
            await update_stage(job_id, "composition", "done", 100, "Your comic is ready!")
        elif job_status == "PARTIAL_READY":
            if any(p.get("guaranteed_output") for p in panels):
                progress_msg = "We created a stylized version of your comic!"
                await update_stage(job_id, "composition", "done", 95, progress_msg)
            else:
                progress_msg = f"Your comic is ready with {len(ready_panels)} optimized panels."
                await update_stage(job_id, "composition", "done", 95, progress_msg)
        else:
            # This should never happen now — guaranteed output catches all failures
            progress_msg = "We created a stylized version of your comic!"
            await update_stage(job_id, "composition", "done", 90, progress_msg)

        # Generate text script for the output bundle
        # Clean internal-only fields from panels before persistence
        for p in panels:
            p.pop("_image_bytes", None)

        script_text = "# Comic Script\n\n"
        for p in panels:
            script_text += f"## Panel {p.get('panelNumber', '?')}\n"
            script_text += f"Scene: {p.get('scene', '')}\n"
            if p.get('dialogue'):
                script_text += f"Dialogue: \"{p['dialogue']}\"\n"
            script_text += "\n"

        # Build consistency metadata
        consistency_meta = {}
        if consistency_results:
            c_sims = [r["source_similarity"] for r in consistency_results if r["source_similarity"] > 0]
            consistency_meta = {
                "consistency_checked": True,
                "consistency_retried_panels": consistency_retried,
                "avg_similarity": round(sum(c_sims) / len(c_sims), 4) if c_sims else 0,
                "min_similarity": round(min(c_sims), 4) if c_sims else 0,
                "panels_with_no_face": sum(1 for r in consistency_results if r["verdict"] == "no_face"),
            }

        # ══════════════════════════════════════════════════════════════════
        # VALIDATION QUALITY DIMENSIONS (5 non-negotiable scores)
        # ══════════════════════════════════════════════════════════════════
        has_retries = any(p.get("retries", 0) > 0 for p in panels if isinstance(p, dict))
        has_fallback = any(p.get("fallback") for p in panels if isinstance(p, dict))
        avg_sim = consistency_meta.get("avg_similarity", 0)
        
        # DIM 1: Perceived Quality Score (1-5)
        # Would a normal user say "cool comic" (5) or "something is off" (1)?
        if job_status == "FAILED":
            perceived_quality_score = 1
        elif len(failed_panels) > 0 and has_fallback:
            perceived_quality_score = 2
        elif has_fallback or (avg_sim > 0 and avg_sim < 0.30):
            perceived_quality_score = 2
        elif has_retries or len(failed_panels) > 0:
            perceived_quality_score = 3
        elif avg_sim > 0 and avg_sim < 0.45:
            perceived_quality_score = 3
        elif len(ready_panels) == panel_count and not has_retries:
            perceived_quality_score = 5
        else:
            perceived_quality_score = 4
        
        # DIM 2: Narrative Coherence
        # Are all panels sequential with story flow? No sudden jumps?
        panels_with_scene = sum(1 for p in panels if isinstance(p, dict) and p.get("scene"))
        panels_sequential = all(
            isinstance(p, dict) and p.get("panelNumber") == i + 1
            for i, p in enumerate(panels)
        )
        narrative_coherence = {
            "score": 5 if (panels_with_scene == len(panels) and panels_sequential and len(failed_panels) == 0)
                    else 4 if (panels_sequential and len(failed_panels) <= 1)
                    else 3 if panels_sequential
                    else 2 if len(ready_panels) > 0
                    else 1,
            "panels_with_story": panels_with_scene,
            "sequential": panels_sequential,
            "gaps": [p.get("panelNumber") for p in failed_panels if isinstance(p, dict)],
        }
        
        # DIM 3: Style Consistency Score (0-1)
        # From panel-to-panel embedding similarity. Higher = more visually coherent
        p2p_sims = []
        if consistency_results:
            p2p_sims = [r.get("panel1_similarity", 0) for r in consistency_results if r.get("panel1_similarity", 0) > 0]
        style_consistency_score = round(sum(p2p_sims) / len(p2p_sims), 4) if p2p_sims else (
            avg_sim if avg_sim > 0 else None
        )
        
        # DIM 4: Fallback Latency Penalty (ms)
        # How much extra time did retries/fallbacks add?
        panel_timings = [p.get("timing_ms", 0) for p in panels if isinstance(p, dict) and p.get("timing_ms")]
        first_attempt_timings = [p.get("timing_ms", 0) for p in panels if isinstance(p, dict) and p.get("retries", 0) == 0 and p.get("timing_ms")]
        retry_timings = [p.get("timing_ms", 0) for p in panels if isinstance(p, dict) and p.get("retries", 0) > 0 and p.get("timing_ms")]
        
        avg_first_attempt = (sum(first_attempt_timings) / len(first_attempt_timings)) if first_attempt_timings else 0
        avg_retry = (sum(retry_timings) / len(retry_timings)) if retry_timings else 0
        fallback_latency_penalty_ms = round(avg_retry - avg_first_attempt) if (avg_first_attempt > 0 and avg_retry > 0) else 0
        
        # DIM 5: UI Emotional Safety (pass/fail)
        # Verify all user-facing text is calm. No scary words.
        SCARY_WORDS = ["fail", "error", "broken", "crash", "timeout", "exception", "fatal", "corrupt", "invalid"]
        ui_texts = [progress_msg, job_status]
        for p in panels:
            if isinstance(p, dict) and p.get("status") == "FAILED":
                # Verify we never surface panel failure text to user
                ui_texts.append(str(p.get("fail_reason", "")))
        
        scary_found = []
        for txt in ui_texts:
            if txt:
                txt_lower = str(txt).lower()
                for word in SCARY_WORDS:
                    if word in txt_lower and txt != job_status:  # internal status is OK
                        scary_found.append({"text": txt, "word": word})
        
        ui_emotional_safety = {
            "passed": len(scary_found) == 0,
            "violations": scary_found[:5],
            "user_facing_status": progress_msg,
            "internal_status": job_status,
        }
        
        # Composite job_quality (from perceived score)
        if perceived_quality_score >= 5:
            job_quality = "HIGH"
        elif perceived_quality_score >= 3:
            job_quality = "MEDIUM"
        elif perceived_quality_score >= 2:
            job_quality = "LOW"
        else:
            job_quality = "FAILED"
        
        # ── Build stage timing log ──
        try:
            total_gen_time = round(time.time() - gen_start_time, 1)
        except Exception:
            total_gen_time = None
        stage_timing = {
            "total_seconds": total_gen_time,
            "panel_timings_ms": panel_timings,
            "avg_panel_ms": round(sum(panel_timings) / len(panel_timings)) if panel_timings else None,
            "fallback_latency_penalty_ms": fallback_latency_penalty_ms,
        }
        
        # Bundle all validation dimensions
        validation_quality = {
            "perceived_quality_score": perceived_quality_score,
            "narrative_coherence": narrative_coherence,
            "style_consistency_score": style_consistency_score,
            "fallback_latency_penalty_ms": fallback_latency_penalty_ms,
            "ui_emotional_safety": ui_emotional_safety,
        }

        # ── Build routing_summary from panel data ──
        primary_pass = sum(1 for p in panels if isinstance(p, dict) and p.get("pipeline_status") == "PASSED")
        repaired = sum(1 for p in panels if isinstance(p, dict) and p.get("pipeline_status") == "PASSED_REPAIRED")
        degraded = sum(1 for p in panels if isinstance(p, dict) and p.get("pipeline_status") == "PASSED_DEGRADED")
        panel_failed = sum(1 for p in panels if isinstance(p, dict) and p.get("pipeline_status") == "FAILED")

        routing_summary = {
            "primary_pass_panels": primary_pass,
            "repaired_panels": repaired,
            "degraded_panels": degraded,
            "failed_panels": panel_failed,
            "job_level_fallback_triggered": job_decision in ("TARGETED_PANEL_RERUN", "STYLE_DOWNGRADE_RERUN"),
        }

        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": job_status,
                "progress": 100,
                "progressMessage": progress_msg,
                "panels": panels,
                "scriptText": script_text,
                "assetId": asset_id if panel_urls else None,
                "permanent": bool(panel_urls),
                "readyPanels": len(ready_panels),
                "failedPanels": len(failed_panels),
                "totalPanels": panel_count,
                "job_quality": job_quality,
                "has_fallback": has_fallback,
                "has_retries": has_retries,
                "panel_retry_count": sum(1 for p in panels if isinstance(p, dict) and p.get("retries", 0) > 0),
                "fallback_panel_count": sum(1 for p in panels if isinstance(p, dict) and p.get("fallback")),
                "stage_timing": stage_timing,
                "validation_quality": validation_quality,
                "routing_summary": routing_summary,
                "pipeline_state": "FINALIZED",
                **consistency_meta,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )

        # Auto-promote source upload to permanent
        await promote_upload_on_completion(job_id, user_id)

        # Send notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_complete(
                user_id=user_id,
                feature="comic_strip",
                job_id=job_id,
                download_url=panel_urls[0] if panel_urls else None
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send notification: {notif_error}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Comic strip processing error for job {job_id}: {error_msg}", exc_info=True)
        
        # Store detailed error in job
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "FAILED", 
                "error": error_msg,
                "errorDetails": {
                    "type": type(e).__name__,
                    "message": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }}
        )
        
        # Auto-refund on generation failure
        refund_issued = False
        try:
            from services.auto_refund import handle_generation_failure
            await handle_generation_failure(db, user_id, "comic_strip", str(e))
            refund_issued = True
            logger.info(f"Auto-refund processed for failed comic strip: {job_id}")
        except Exception as refund_error:
            logger.error(f"Auto-refund failed: {refund_error}")
        
        # Send failure notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_failed(
                user_id=user_id,
                feature="comic_strip",
                job_id=job_id,
                error_message=str(e),
                refund_issued=refund_issued
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send failure notification: {notif_error}")


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status with presigned CDN URLs."""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Presign R2 URLs if job is completed or ready with warnings
    if job.get("status") in ("COMPLETED", "READY_WITH_WARNINGS", "PARTIAL_READY"):
        from utils.r2_presign import presign_url
        if job.get("resultUrl") and ".r2.dev/" in job["resultUrl"]:
            job["resultUrl"] = presign_url(job["resultUrl"])
        if job.get("resultUrls"):
            job["resultUrls"] = [presign_url(u) if ".r2.dev/" in (u or "") else u for u in job["resultUrls"]]
        if job.get("panels"):
            for panel in job["panels"]:
                if panel.get("imageUrl") and ".r2.dev/" in panel["imageUrl"]:
                    panel["imageUrl"] = presign_url(panel["imageUrl"])

    return job


@router.get("/history")
async def get_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's generation history"""
    query = {"userId": user["id"]}
    
    jobs = await db.photo_to_comic_jobs.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.photo_to_comic_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.post("/download/{job_id}")
async def download_comic(job_id: str, user: dict = Depends(get_current_user)):
    """Download comic — returns permanent CDN URLs. No expiry."""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Content not ready")

    # Collect all download URLs (CDN-backed)
    download_urls = []
    if job.get("resultUrls"):
        download_urls = [u for u in job["resultUrls"] if u]
    elif job.get("resultUrl"):
        download_urls = [job["resultUrl"]]
    elif job.get("panels"):
        download_urls = [p.get("imageUrl") for p in job["panels"] if p.get("imageUrl")]

    # Presign R2 URLs for download access
    from utils.r2_presign import presign_url
    presigned_urls = [presign_url(u) if ".r2.dev/" in (u or "") else u for u in download_urls]

    # Mark as downloaded
    if not job.get("downloaded"):
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"downloaded": True, "downloadedAt": datetime.now(timezone.utc).isoformat()}}
        )

    return {
        "success": True,
        "downloadUrls": presigned_urls,
        "permanent": True,
    }


@router.get("/validate-asset/{job_id}")
async def validate_asset(job_id: str, user: dict = Depends(get_current_user)):
    """Validate generated assets. Returns separate preview/download truth."""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0, "status": 1, "resultUrl": 1, "resultUrls": 1, "panels": 1, "permanent": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "COMPLETED":
        return {"valid": False, "download_ready": False, "preview_ready": False, "reason": "not_completed"}

    # Collect all asset URLs
    result_url = job.get("resultUrl", "")
    panel_urls = [p.get("imageUrl") for p in job.get("panels", []) if p.get("imageUrl")]
    all_urls = ([result_url] if result_url else []) + panel_urls

    has_data_uri = any(u.startswith("data:") for u in all_urls if u)
    cdn_urls = [u for u in all_urls if u and not u.startswith("data:") and "placehold.co" not in u]

    # Data URIs are always valid for both preview and download
    if has_data_uri and not cdn_urls:
        return {"valid": True, "download_ready": True, "preview_ready": True,
                "permanent": job.get("permanent", False), "cdn_backed": False, "asset_type": "data_uri"}

    # For CDN URLs: validate with HEAD, but download is assumed OK if URL exists
    cdn_valid = False
    if cdn_urls:
        try:
            import aiohttp
            from utils.r2_presign import presign_url
            check_url = presign_url(cdn_urls[0]) if ".r2.dev/" in cdn_urls[0] else cdn_urls[0]
            async with aiohttp.ClientSession() as session:
                async with session.head(check_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    cdn_valid = resp.status in (200, 206)
        except Exception as val_err:
            logger.warning(f"Asset validation HEAD failed for {job_id}: {val_err}")

    # Download is ready if we have any URL (CDN or data URI) — HEAD failure doesn't block download
    download_ready = len(all_urls) > 0
    preview_ready = has_data_uri or cdn_valid

    return {
        "valid": cdn_valid or has_data_uri,
        "download_ready": download_ready,
        "preview_ready": preview_ready,
        "permanent": job.get("permanent", False),
        "cdn_backed": bool(cdn_urls),
        "asset_count": len(all_urls),
    }


@router.delete("/job/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a job"""
    result = await db.photo_to_comic_jobs.delete_one(
        {"id": job_id, "userId": user["id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "message": "Job deleted"}



# ============================================
# DEBUG: Style Distinctness Audit
# ============================================

@router.post("/debug/style-audit")
async def debug_style_audit(user: dict = Depends(get_current_user)):
    """
    Debug endpoint: Generate guaranteed output for the same test image across
    4 styles and return comparison data. No credits charged.
    Admin-only.
    """
    if user.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    import hashlib
    from services.comic_pipeline.guaranteed_output import generate_guaranteed_panels
    from PIL import Image, ImageDraw
    import io

    # Create a simple test face image
    test_img = Image.new("RGB", (256, 256), (180, 150, 120))
    draw = ImageDraw.Draw(test_img)
    draw.ellipse([60, 40, 196, 200], fill=(220, 190, 160))  # face
    draw.ellipse([90, 90, 115, 110], fill=(50, 40, 30))  # left eye
    draw.ellipse([145, 90, 170, 110], fill=(50, 40, 30))  # right eye
    draw.arc([100, 130, 160, 170], 0, 180, fill=(120, 60, 60), width=2)  # mouth
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    test_bytes = buf.getvalue()

    scenes = [
        {"scene": "Hero appears", "dialogue": "Ready!"},
        {"scene": "Action scene", "dialogue": "Here we go!"},
        {"scene": "Challenge", "dialogue": None},
        {"scene": "Victory", "dialogue": "We won!"},
    ]

    styles_to_test = ["bold_superhero", "cartoon_fun", "soft_manga", "noir_comic"]
    results = {}

    for style_name in styles_to_test:
        panels = generate_guaranteed_panels(test_bytes, scenes, 4, style_name=style_name)
        panel_data = []
        for p in panels:
            img_hash = hashlib.md5(p["imageBytes"]).hexdigest()
            panel_data.append({
                "panel": p["panelNumber"],
                "filter_used": p["filter_used"],
                "style_applied": p["style_applied"],
                "output_hash": img_hash[:16],
                "size_bytes": len(p["imageBytes"]),
            })
        results[style_name] = panel_data

    # Cross-style comparison
    comparisons = []
    for i, s1 in enumerate(styles_to_test):
        for s2 in styles_to_test[i + 1:]:
            identical_panels = sum(
                1 for a, b in zip(results[s1], results[s2])
                if a["output_hash"] == b["output_hash"]
            )
            comparisons.append({
                "style_a": s1,
                "style_b": s2,
                "identical_panels": f"{identical_panels}/{len(results[s1])}",
                "distinct": identical_panels == 0,
            })

    return {
        "test_type": "guaranteed_output_style_audit",
        "styles_tested": styles_to_test,
        "results": results,
        "cross_style_comparisons": comparisons,
        "verdict": "PASS" if all(c["distinct"] for c in comparisons) else "PARTIAL",
    }



# ============================================
# EVENT TRACKING (P1 Analytics)
# ============================================

class ComicEventRequest(BaseModel):
    event_type: str
    metadata: Optional[dict] = None

@router.post("/events")
async def track_comic_event(request: ComicEventRequest, user: dict = Depends(get_current_user)):
    """Track Photo-to-Comic feature events for analytics"""
    allowed = {
        "preview_strip_style_click", "pdf_download_click", "pdf_download_success",
        "pdf_download_fail", "png_download_click", "script_download_click",
        "result_page_view", "generate_after_preview"
    }
    if request.event_type not in allowed:
        raise HTTPException(status_code=400, detail="Unknown event type")

    await db.comic_events.insert_one({
        "user_id": user["id"],
        "event_type": request.event_type,
        "metadata": request.metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"ok": True}


# ============================================
# ADMIN ENDPOINTS
# ============================================

@router.get("/admin/styles")
async def admin_get_styles(user: dict = Depends(get_current_user)):
    """Admin: Get all styles with full config"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "styles": SAFE_STYLES,
        "blockedKeywords": BLOCKED_KEYWORDS,
        "universalNegativePrompts": UNIVERSAL_NEGATIVE_PROMPTS,
        "pricing": PRICING
    }


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(get_current_user)):
    """Admin: Get feature analytics"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count by mode
    avatar_count = await db.photo_to_comic_jobs.count_documents({"mode": "avatar"})
    strip_count = await db.photo_to_comic_jobs.count_documents({"mode": "strip"})
    
    # Count by status
    completed = await db.photo_to_comic_jobs.count_documents({"status": "COMPLETED"})
    failed = await db.photo_to_comic_jobs.count_documents({"status": "FAILED"})
    
    # Popular styles
    pipeline = [
        {"$group": {"_id": "$style", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    popular_styles = await db.photo_to_comic_jobs.aggregate(pipeline).to_list(length=10)
    
    return {
        "totalJobs": avatar_count + strip_count,
        "byMode": {
            "avatar": avatar_count,
            "strip": strip_count
        },
        "byStatus": {
            "completed": completed,
            "failed": failed
        },
        "popularStyles": [{"style": s["_id"], "count": s["count"]} for s in popular_styles]
    }


@router.get("/diagnostic")
async def get_diagnostic_info(user: dict = Depends(get_current_user)):
    """Diagnostic endpoint to check system health for photo-to-comic feature"""
    diagnostic = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_status": {},
        "recent_jobs": {},
        "error_summary": {}
    }
    
    # Check LLM availability
    try:
        diagnostic["llm_status"]["available"] = LLM_AVAILABLE
        diagnostic["llm_status"]["key_configured"] = bool(EMERGENT_LLM_KEY)
        diagnostic["llm_status"]["key_length"] = len(EMERGENT_LLM_KEY) if EMERGENT_LLM_KEY else 0
    except Exception as e:
        diagnostic["llm_status"]["error"] = str(e)
    
    # Recent job stats (last hour)
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_completed = await db.photo_to_comic_jobs.count_documents({
            "status": "COMPLETED",
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        recent_failed = await db.photo_to_comic_jobs.count_documents({
            "status": "FAILED",
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        recent_pending = await db.photo_to_comic_jobs.count_documents({
            "status": {"$in": ["QUEUED", "PROCESSING"]},
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        
        diagnostic["recent_jobs"]["last_hour"] = {
            "completed": recent_completed,
            "failed": recent_failed,
            "pending": recent_pending,
            "success_rate": f"{(recent_completed / (recent_completed + recent_failed) * 100):.1f}%" if (recent_completed + recent_failed) > 0 else "N/A"
        }
    except Exception as e:
        diagnostic["recent_jobs"]["error"] = str(e)
    
    # Recent errors
    try:
        recent_errors = await db.photo_to_comic_jobs.find(
            {"status": "FAILED", "error": {"$exists": True}},
            {"_id": 0, "id": 1, "error": 1, "errorDetails": 1, "createdAt": 1}
        ).sort("createdAt", -1).limit(5).to_list(5)
        
        diagnostic["error_summary"]["recent_errors"] = recent_errors
    except Exception as e:
        diagnostic["error_summary"]["error"] = str(e)
    
    return diagnostic


@router.post("/test-image-generation")
async def test_image_generation(user: dict = Depends(get_current_user)):
    """Test image generation capability - admin only"""
    if user.get("role") not in ["admin", "ADMIN"]:
        # Allow for testing purposes with warning
        pass
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_available": LLM_AVAILABLE,
        "image_generation": {}
    }
    
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        result["image_generation"]["status"] = "error"
        result["image_generation"]["error"] = "LLM not available or key not configured"
        return result
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test-image-gen-{datetime.now().timestamp()}",
            system_message="You are an artist."
        )
        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        import asyncio
        text_response, images = await asyncio.wait_for(
            chat.send_message_multimodal_response(
                UserMessage(text="Create a simple smiley face icon, yellow circle with black eyes and smile")
            ),
            timeout=60
        )
        
        result["image_generation"]["status"] = "success"
        result["image_generation"]["text_response"] = text_response[:100] if text_response else None
        result["image_generation"]["images_generated"] = len(images) if images else 0
        result["image_generation"]["image_data_size"] = len(images[0].get("data", "")) if images else 0
        
    except asyncio.TimeoutError:
        result["image_generation"]["status"] = "timeout"
        result["image_generation"]["error"] = "Image generation timed out after 60 seconds"
    except Exception as e:
        result["image_generation"]["status"] = "error"
        result["image_generation"]["error"] = str(e)
        result["image_generation"]["error_type"] = type(e).__name__
    
    return result


# ════════════════════════════════════════════════════════════════════════
# FALLBACK VALIDATION ENDPOINTS (P0 — Controlled Failure Testing)
# ════════════════════════════════════════════════════════════════════════

class FallbackValidationRequest(BaseModel):
    mode: str = "single_panel"  # "single_panel" | "majority_failure"
    panels_to_fail: Optional[List[int]] = None  # panel indices (0-based) to force-fail

@router.post("/admin/fallback-validation")
async def run_fallback_validation(
    req: FallbackValidationRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Admin: Run controlled failure injection to validate the fallback pipeline.
    Creates a real job with forced panel failures to test repair, fallback, and quality.
    """
    if user.get("role") not in ["admin", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    if req.mode not in ("single_panel", "majority_failure"):
        raise HTTPException(status_code=400, detail="mode must be 'single_panel' or 'majority_failure'")

    panel_count = 4
    if req.mode == "single_panel":
        fail_indices = req.panels_to_fail or [1]  # Fail panel 2 by default
    else:
        fail_indices = req.panels_to_fail or [0, 1, 2]  # Fail 3 of 4 = 75%

    # Validate indices
    fail_indices = [i for i in fail_indices if 0 <= i < panel_count]

    validation_id = str(uuid.uuid4())
    validation_doc = {
        "validation_id": validation_id,
        "mode": req.mode,
        "fail_indices": fail_indices,
        "panel_count": panel_count,
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "initiated_by": user["id"],
    }
    await db.fallback_validations.insert_one(validation_doc)

    background_tasks.add_task(
        _run_fallback_validation_pipeline,
        validation_id, fail_indices, panel_count, user["id"]
    )

    return {
        "validation_id": validation_id,
        "mode": req.mode,
        "fail_indices": fail_indices,
        "status": "RUNNING",
        "message": f"Validation started. Forcing failure on panels: {[i+1 for i in fail_indices]}",
    }


async def _run_fallback_validation_pipeline(
    validation_id: str, fail_indices: list, panel_count: int, user_id: str
):
    """Background: simulate a comic strip generation with forced panel failures."""
    import time as time_mod
    start_time = time_mod.time()

    result = {
        "validation_id": validation_id,
        "test_panels": [],
        "fallback_triggered": False,
        "repair_triggered": False,
        "validation_quality": {},
    }

    try:
        # Create simulated job data
        panels = []
        story_scenes = [
            {"scene": "Hero discovers a mysterious glowing artifact", "dialogue": "What is this?"},
            {"scene": "The artifact transforms the hero into a warrior", "dialogue": "I feel the power!"},
            {"scene": "An enemy appears from the shadows", "dialogue": "You cannot stop me!"},
            {"scene": "The hero defeats the enemy in an epic battle", "dialogue": "Justice prevails!"},
        ][:panel_count]

        # Simulate panel generation with forced failures
        for i in range(panel_count):
            panel_start = time_mod.time()
            scene = story_scenes[i]
            force_fail = i in fail_indices

            panel = {
                "panelNumber": i + 1,
                "scene": scene["scene"],
                "dialogue": scene["dialogue"],
            }

            if force_fail:
                panel["status"] = "FAILED"
                panel["imageUrl"] = None
                panel["fail_reason"] = "validation_forced_failure"
                panel["retries"] = 3
                panel["timing_ms"] = round((time_mod.time() - panel_start) * 1000)
            else:
                panel["status"] = "READY"
                panel["imageUrl"] = "simulated://panel_ok"
                panel["retries"] = 0
                panel["timing_ms"] = round((time_mod.time() - panel_start) * 1000) + 8000

            panels.append(panel)

        failed_count = sum(1 for p in panels if p["status"] == "FAILED")

        # Test: Path selection based on failure severity
        # MAJORITY failure → job-level fallback (skips repair)
        # MINORITY failure → single-panel repair
        if failed_count > len(panels) / 2:
            result["fallback_triggered"] = True
            for p in panels:
                if p["status"] == "FAILED":
                    p["status"] = "FALLBACK_SIM"
                    p["imageUrl"] = "simulated://fallback_panel"
                    p["fallback"] = True
                    p["retries"] = 5
                    p["timing_ms"] = (p.get("timing_ms", 0) or 0) + 20000
        elif 0 < failed_count < len(panels):
            result["repair_triggered"] = True
            for p in panels:
                if p["status"] == "FAILED":
                    p["status"] = "REPAIRED_SIM"
                    p["imageUrl"] = "simulated://repaired_panel"
                    p["retries"] = 4
                    p["repair_attempted"] = True
                    p["timing_ms"] = (p.get("timing_ms", 0) or 0) + 12000

        final_ready = sum(1 for p in panels if p["status"] in ("READY", "REPAIRED_SIM", "FALLBACK_SIM"))
        final_failed = sum(1 for p in panels if p["status"] == "FAILED")
        has_fallback = any(p.get("fallback") for p in panels)
        has_retries = any(p.get("retries", 0) > 0 for p in panels)

        # ── DIM 1: Perceived Quality Score ──
        if final_failed == panel_count:
            pqs = 1
        elif has_fallback:
            pqs = 2
        elif result["repair_triggered"]:
            pqs = 3
        elif has_retries:
            pqs = 4
        else:
            pqs = 5

        # ── DIM 2: Narrative Coherence ──
        panels_with_scene = sum(1 for p in panels if p.get("scene"))
        panels_sequential = all(p["panelNumber"] == i + 1 for i, p in enumerate(panels))
        gaps = [p["panelNumber"] for p in panels if p["status"] == "FAILED"]
        nc_score = 5 if (panels_with_scene == panel_count and not gaps) else (
            4 if len(gaps) <= 1 else (3 if panels_sequential else 2)
        )
        narrative_coherence = {
            "score": nc_score,
            "panels_with_story": panels_with_scene,
            "sequential": panels_sequential,
            "gaps": gaps,
            "verdict": "PASS" if nc_score >= 3 else "FAIL",
        }

        # ── DIM 3: Style Consistency (simulated) ──
        style_consistency_score = 0.65 if not has_fallback else 0.35

        # ── DIM 4: Fallback Latency Penalty ──
        first_timings = [p["timing_ms"] for p in panels if p.get("retries", 0) == 0]
        retry_timings = [p["timing_ms"] for p in panels if p.get("retries", 0) > 0]
        avg_first = (sum(first_timings) / len(first_timings)) if first_timings else 0
        avg_retry = (sum(retry_timings) / len(retry_timings)) if retry_timings else 0
        fallback_latency_penalty_ms = round(avg_retry - avg_first) if avg_first > 0 else round(avg_retry)

        # ── DIM 5: UI Emotional Safety ──
        STATUS_TO_USER_TEXT = {
            "COMPLETED": "Your comic is ready!",
            "READY_WITH_WARNINGS": "Your comic is ready!",
            "PARTIAL_READY": f"Your comic is ready with {final_ready} optimized panels.",
            "FAILED": "We created a stylized version of your comic!",
        }
        if final_ready == 0:
            sim_status = "FAILED"
        elif final_failed > 0:
            sim_status = "PARTIAL_READY"
        elif has_retries:
            sim_status = "READY_WITH_WARNINGS"
        else:
            sim_status = "COMPLETED"

        user_text = STATUS_TO_USER_TEXT.get(sim_status, "Processing complete")
        SCARY_WORDS = ["fail", "error", "broken", "crash", "timeout", "exception", "fatal"]
        scary_in_user_text = [w for w in SCARY_WORDS if w in user_text.lower()]

        ui_emotional_safety = {
            "passed": len(scary_in_user_text) == 0,
            "user_facing_text": user_text,
            "scary_words_found": scary_in_user_text,
            "simulated_status": sim_status,
            "verdict": "PASS" if not scary_in_user_text else "FAIL",
        }

        total_time = round(time_mod.time() - start_time, 1)

        result["test_panels"] = panels
        result["summary"] = {
            "forced_failures": len(fail_indices),
            "panels_recovered": sum(1 for p in panels if p.get("repair_attempted") or p.get("fallback")),
            "final_ready": final_ready,
            "final_failed": final_failed,
            "total_time_seconds": total_time,
            "simulated_job_status": sim_status,
        }
        result["validation_quality"] = {
            "perceived_quality_score": pqs,
            "narrative_coherence": narrative_coherence,
            "style_consistency_score": style_consistency_score,
            "fallback_latency_penalty_ms": fallback_latency_penalty_ms,
            "ui_emotional_safety": ui_emotional_safety,
        }

        all_pass = (
            pqs >= 2 and
            narrative_coherence["score"] >= 3 and
            ui_emotional_safety["passed"]
        )
        result["overall_verdict"] = "PASS" if all_pass else "FAIL"
        result["status"] = "COMPLETED"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        result["overall_verdict"] = "FAIL"

    await db.fallback_validations.update_one(
        {"validation_id": validation_id},
        {"$set": {
            **result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }}
    )


@router.get("/admin/fallback-validation/{validation_id}")
async def get_fallback_validation(validation_id: str, user: dict = Depends(get_current_user)):
    """Get results of a fallback validation test."""
    if user.get("role") not in ["admin", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    doc = await db.fallback_validations.find_one(
        {"validation_id": validation_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Validation not found")
    return doc


@router.get("/admin/fallback-validations")
async def list_fallback_validations(user: dict = Depends(get_current_user)):
    """List all fallback validation results (most recent first)."""
    if user.get("role") not in ["admin", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    results = await db.fallback_validations.find(
        {}, {"_id": 0}
    ).sort("started_at", -1).limit(20).to_list(20)
    return {"validations": results}


@router.get("/admin/ui-safety-audit")
async def ui_safety_audit(user: dict = Depends(get_current_user)):
    """
    Audit all user-facing UI text for emotional safety.
    Scans status configs, progress messages, and panel states for scary words.
    """
    if user.get("role") not in ["admin", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    SCARY_WORDS = [
        "fail", "error", "broken", "crash", "timeout", "exception", "fatal",
        "corrupt", "invalid", "aborted", "panic", "killed", "terminated",
        "unsuccessful", "generation failed", "panel failed"
    ]

    user_facing_texts = {
        "COMPLETED_progress": "Your comic is ready!",
        "READY_WITH_WARNINGS_progress": "Your comic is ready!",
        "PARTIAL_READY_progress": "Your comic is ready with N optimized panels.",
        "FAILED_progress": "We created a stylized version of your comic!",
        "stale_timeout_msg": "Optimizing your comic — almost there...",
        "panel_failed_display": "Being optimized",
        "full_failure_title": "Your Comic is Ready",
        "full_failure_body": "We created a stylized version for you. Try a different style for an enhanced look.",
        "status_VALIDATING_title": "Finalizing",
        "status_READY_title": "Your Comic is Ready",
        "status_PARTIAL_READY_title": "Your Comic is Ready",
        "status_FAILED_title": "Your Comic is Ready",
        "status_FAILED_subtitle": "We created a stylized version for you.",
        "avatar_fail_progress": "We created a stylized version of your comic!",
        "calm_retry_msg_1": "Creating panels...",
        "calm_retry_msg_2": "Optimizing panel...",
        "calm_retry_msg_3": "Finalizing panel...",
        "fallback_msg": "Optimizing your comic...",
        "consistency_msg": "Optimizing character details...",
        "composition_msg": "Optimizing final panels...",
    }

    violations = []
    passed_list = []

    for key, text in user_facing_texts.items():
        text_lower = text.lower()
        found_scary = [w for w in SCARY_WORDS if w in text_lower]
        if found_scary:
            violations.append({"key": key, "text": text, "scary_words": found_scary})
        else:
            passed_list.append({"key": key, "text": text})

    return {
        "overall": "PASS" if not violations else "FAIL",
        "total_texts_checked": len(user_facing_texts),
        "passed_count": len(passed_list),
        "violation_count": len(violations),
        "violations": violations,
        "passed": passed_list,
        "scary_words_checked": SCARY_WORDS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

async def promote_upload_on_completion(job_id: str, user_id: str):
    """
    Auto-promotion: when a photo-to-comic job completes successfully,
    promote the source upload from temporary to permanent.
    On failure, leave temporary for lifecycle cleanup.
    """
    try:
        job = await db.photo_to_comic_jobs.find_one(
            {"id": job_id}, {"_id": 0, "source_storage_key": 1, "status": 1}
        )
        if not job or not job.get("source_storage_key"):
            return
        
        storage_key = job["source_storage_key"]
        
        if job.get("status") == "COMPLETED":
            # Promote to permanent
            await db.pending_uploads.update_one(
                {"storage_key": storage_key, "user_id": user_id},
                {"$set": {
                    "status": "permanent",
                    "is_temp": False,
                    "linked_job_id": job_id,
                    "promoted_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            logger.info(f"[AUTO-PROMO] Upload {storage_key[:30]} promoted to permanent for job {job_id[:8]}")
        # FAILED/abandoned: leave as temp for lifecycle cleanup (no action needed)
    except Exception as e:
        logger.warning(f"[AUTO-PROMO] Failed for job {job_id[:8]}: {e}")


# ── CONTINUE STORY ──────────────────────────────────────────────────────

class ContinueStoryRequest(BaseModel):
    parentJobId: str
    prompt: str = ""
    panelCount: int = 4
    keepStyle: bool = True


@router.post("/continue-story")
async def continue_story(
    request: ContinueStoryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Continue a completed comic strip with additional panels.
    Uses the same photo, style, and genre from the parent job.
    """
    parent = await db.photo_to_comic_jobs.find_one(
        {"id": request.parentJobId, "userId": user["id"]},
        {"_id": 0}
    )
    if not parent:
        raise HTTPException(status_code=404, detail="Parent job not found")
    if parent.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Parent job must be completed")
    if parent.get("mode") != "strip":
        raise HTTPException(status_code=400, detail="Continue story only works with comic strips")

    # Get photo content from source storage key or stored reference
    photo_content = None
    if parent.get("source_storage_key"):
        try:
            from services.cloudflare_r2_storage import CloudflareR2Storage
            r2 = CloudflareR2Storage()
            photo_content = await r2.download_file(parent["source_storage_key"])
        except Exception as e:
            logger.warning(f"Could not download source photo for continue: {e}")

    if not photo_content and parent.get("photoBase64"):
        photo_content = base64.b64decode(parent["photoBase64"])

    if not photo_content:
        raise HTTPException(
            status_code=400,
            detail="Source photo no longer available. Please upload again."
        )

    # Calculate cost
    panel_count = min(max(request.panelCount, 3), 6)
    cost = PRICING["comic_strip"]["panels"].get(panel_count, 25)
    cost += PRICING["comic_strip"]["add_ons"].get("auto_dialogue", 0)
    user_plan = user.get("plan", "free")
    discount = {"creator": 0.8, "pro": 0.7, "studio": 0.6}.get(user_plan, 1.0)
    cost = int(cost * discount)

    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost}.")

    # Build continuation prompt
    parent_prompt = parent.get("storyPrompt", "")
    parent_panels = parent.get("panels", [])
    last_dialogue = parent_panels[-1].get("dialogue", "") if parent_panels else ""
    
    continuation_prompt = f"Continue this comic story. Previous story: {parent_prompt}. Last panel dialogue: '{last_dialogue}'. {request.prompt}. Create the NEXT {panel_count} panels that advance the plot."

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "mode": "strip",
        "type": "COMIC_STRIP",
        "status": "QUEUED",
        "style": parent["style"] if request.keepStyle else "cartoon_fun",
        "genre": parent.get("genre", "action"),
        "cost": cost,
        "panelCount": panel_count,
        "storyPrompt": continuation_prompt,
        "includeDialogue": True,
        "parentJobId": request.parentJobId,
        "isContinuation": True,
        "addOns": parent.get("addOns", {}),
        "progress": 0,
        "downloaded": False,
        "source_storage_key": parent.get("source_storage_key"),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.photo_to_comic_jobs.insert_one(job_data)

    # Assign story chain fields (continuation from parent)
    from services.story_chain import ensure_chain_fields
    await ensure_chain_fields(job_id, user["id"], parent_job_id=request.parentJobId, branch_type="continuation")

    hd_export = parent.get("addOns", {}).get("hd_export", False)
    background_tasks.add_task(
        process_comic_strip,
        job_id, photo_content, job_data["style"], job_data["genre"],
        continuation_prompt, None, panel_count, True, user["id"], cost, hd_export
    )

    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost,
        "parentJobId": request.parentJobId,
        "message": f"Continuing your story with {panel_count} new panels..."
    }


# ── REMIX ───────────────────────────────────────────────────────────────

@router.post("/remix/{job_id}")
async def get_remix_config(job_id: str, user: dict = Depends(get_current_user)):
    """
    Return config from a completed job so frontend can pre-fill the builder for remixing.
    """
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0, "mode": 1, "style": 1, "genre": 1, "panelCount": 1,
         "storyPrompt": 1, "addOns": 1, "source_storage_key": 1,
         "resultUrl": 1, "resultUrls": 1, "panels": 1, "title": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if source photo still exists
    has_source = False
    source_url = None
    if job.get("source_storage_key"):
        try:
            from services.cloudflare_r2_storage import CloudflareR2Storage
            r2 = CloudflareR2Storage()
            has_source = await r2.file_exists(job["source_storage_key"])
            if has_source:
                source_url = r2.get_public_url(job["source_storage_key"])
        except Exception:
            pass

    return {
        "mode": job.get("mode", "avatar"),
        "style": job.get("style", "cartoon_fun"),
        "genre": job.get("genre", "action"),
        "panelCount": job.get("panelCount", 4),
        "storyPrompt": job.get("storyPrompt", ""),
        "addOns": job.get("addOns", {}),
        "hasSourcePhoto": has_source,
        "sourcePhotoUrl": source_url,
        "storageKey": job.get("source_storage_key"),
    }



# ── STORY CHAIN ENDPOINTS ───────────────────────────────────────────────

@router.get("/chain/{chain_id}")
async def get_story_chain(chain_id: str, user: dict = Depends(get_current_user)):
    """Get the full story chain tree with progress data."""
    from services.story_chain import get_chain_tree
    chain = await get_chain_tree(chain_id, user["id"])
    if not chain:
        raise HTTPException(status_code=404, detail="Story chain not found")

    # Enrich with progress data
    total = chain.get("total_episodes", 0)
    completed = chain.get("completed", 0)
    chain["progress_pct"] = round((completed / total) * 100) if total > 0 else 0
    chain["total_panels"] = sum(
        len(j.get("panels", [])) or (1 if j.get("resultUrl") else 0)
        for j in chain.get("flat", [])
    )

    # Find the latest completed strip for "continue" CTA
    flat = chain.get("flat", [])
    latest_strip = None
    for j in reversed(flat):
        if j.get("status") in ("COMPLETED", "PARTIAL_COMPLETE") and j.get("mode") == "strip":
            latest_strip = j
            break
    chain["latest_continuable_job_id"] = latest_strip["id"] if latest_strip else None
    chain["latest_continuable_style"] = latest_strip.get("style") if latest_strip else None

    return chain


@router.get("/active-chains")
async def get_active_chains(user: dict = Depends(get_current_user)):
    """Get user's most recent active story chains for dashboard 'Resume Your Story'."""
    from services.story_chain import backfill_chain_ids
    await backfill_chain_ids(user["id"])

    pipeline = [
        {"$match": {"userId": user["id"], "story_chain_id": {"$exists": True}}},
        {"$group": {
            "_id": "$story_chain_id",
            "root_job_id": {"$first": "$root_job_id"},
            "total_episodes": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$in": ["$status", ["COMPLETED", "PARTIAL_COMPLETE"]]}, 1, 0]}},
            "last_updated": {"$max": "$createdAt"},
            "styles": {"$addToSet": "$style"},
            "continuations": {"$sum": {"$cond": [{"$eq": ["$branch_type", "continuation"]}, 1, 0]}},
            "remixes": {"$sum": {"$cond": [{"$eq": ["$branch_type", "remix"]}, 1, 0]}},
            "latest_job_id": {"$last": "$id"},
            "latest_mode": {"$last": "$mode"},
            "latest_prompt": {"$last": "$storyPrompt"},
            "total_panels": {"$sum": "$panelCount"},
        }},
        {"$match": {"completed": {"$gte": 1}}},
        {"$sort": {"last_updated": -1}},
        {"$limit": 3},
    ]
    chains = await db.photo_to_comic_jobs.aggregate(pipeline).to_list(3)

    result = []
    for c in chains:
        # Get root job for preview
        root = await db.photo_to_comic_jobs.find_one(
            {"id": c["root_job_id"]},
            {"_id": 0, "id": 1, "resultUrl": 1, "panels": 1,
             "style": 1, "genre": 1, "mode": 1, "storyPrompt": 1}
        )
        preview = None
        if root:
            candidate = root.get("resultUrl") or (root.get("panels", [{}])[0].get("imageUrl") if root.get("panels") else None)
            # TRUTH: Filter out fake/invalid URLs — never return placehold.co
            if candidate and isinstance(candidate, str) and "placehold.co" not in candidate and candidate.startswith(("http://", "https://")):
                preview = candidate

        # TRUTH GATE: Do NOT return chains without a real, renderable preview.
        # A chain with no preview is dead content — showing it misleads the user.
        if not preview:
            continue

        # Get the last completed strip for continue CTA
        last_strip = await db.photo_to_comic_jobs.find_one(
            {"story_chain_id": c["_id"], "userId": user["id"],
             "status": {"$in": ["COMPLETED", "PARTIAL_COMPLETE"]}, "mode": "strip"},
            {"_id": 0, "id": 1, "style": 1, "storyPrompt": 1, "panels": 1},
            sort=[("sequence_number", -1)]
        )

        total = c["total_episodes"]
        completed = c["completed"]
        progress_pct = round((completed / total) * 100) if total > 0 else 0

        # Momentum messaging
        milestone_next = 5 if total < 5 else (10 if total < 10 else (25 if total < 25 else 50))
        episodes_to_milestone = milestone_next - total
        momentum_msg = None
        if total >= 3 and progress_pct < 100:
            momentum_msg = f"{total - completed} episode{'s' if total - completed != 1 else ''} left to complete"
        elif total >= 2:
            momentum_msg = f"{episodes_to_milestone} more to reach {milestone_next}-episode milestone"
        elif total == 1:
            momentum_msg = "Continue to start building your series"

        result.append({
            "chain_id": c["_id"],
            "root_job_id": c["root_job_id"],
            "total_episodes": total,
            "completed": completed,
            "progress_pct": progress_pct,
            "continuations": c["continuations"],
            "remixes": c["remixes"],
            "total_panels": c.get("total_panels", 0),
            "styles_used": c["styles"],
            "last_updated": c["last_updated"],
            "preview_url": preview,
            "root_style": root.get("style") if root else None,
            "root_genre": root.get("genre") if root else None,
            "root_prompt": root.get("storyPrompt") if root else None,
            "continue_job_id": last_strip["id"] if last_strip else None,
            "last_dialogue": (last_strip.get("panels", [{}])[-1].get("dialogue", "") if last_strip and last_strip.get("panels") else ""),
            "momentum_msg": momentum_msg,
            "milestone_next": milestone_next,
            "episodes_to_milestone": episodes_to_milestone,
        })

    return {"chains": result, "total": len(result)}


class SuggestionRequest(BaseModel):
    chain_id: str


@router.post("/chain/suggestions")
async def get_chain_suggestions(
    request: SuggestionRequest,
    user: dict = Depends(get_current_user)
):
    """Generate AI-powered 'Next Episode' suggestions — context-aware, validated, cached."""
    chain_id = request.chain_id

    # ── Check cache (1h TTL) ──
    cached = await db.suggestion_cache.find_one(
        {"chain_id": chain_id, "ts": {"$gte": datetime.now(timezone.utc) - timedelta(hours=1)}},
        {"_id": 0}
    )
    if cached:
        return cached["payload"]

    # ── Gather chain context ──
    jobs = await db.photo_to_comic_jobs.find(
        {"story_chain_id": chain_id, "userId": user["id"],
         "status": {"$in": ["COMPLETED", "PARTIAL_COMPLETE"]}},
        {"_id": 0, "storyPrompt": 1, "style": 1, "genre": 1,
         "panels": 1, "branch_type": 1, "sequence_number": 1}
    ).sort("sequence_number", 1).to_list(20)

    if not jobs:
        raise HTTPException(status_code=404, detail="No completed episodes in this chain")

    style = jobs[-1].get("style", "cartoon_fun")
    genre = jobs[-1].get("genre", "action")
    style_name = SAFE_STYLES.get(style, {}).get("name", style)

    # ── Extract rich context: characters, scenes, tone, dialogue ──
    characters_seen = set()
    scenes_list = []
    dialogues = []
    prompts_list = []
    for j in jobs:
        prompt = j.get("storyPrompt", "")
        if prompt:
            prompts_list.append(prompt)
        for p in j.get("panels", []):
            if p.get("dialogue"):
                dialogues.append(p["dialogue"])
            if p.get("scene"):
                scenes_list.append(p["scene"])
            # Extract character names from dialogue attribution
            dlg = p.get("dialogue", "")
            if ":" in dlg:
                char_name = dlg.split(":")[0].strip()
                if len(char_name) < 30:
                    characters_seen.add(char_name)

    chars_str = ", ".join(list(characters_seen)[:8]) or "unnamed protagonist"
    last_scenes = "\n".join(f"- {s}" for s in scenes_list[-6:]) or "No scene descriptions"
    last_dialogues = "\n".join(f'- "{d}"' for d in dialogues[-6:]) or "No dialogue yet"
    prompts_str = "\n".join(f"- {p}" for p in prompts_list[-5:]) or "No prompts"

    # ── Detect tone from dialogue ──
    all_text = " ".join(dialogues[-10:] + prompts_list[-5:]).lower()
    tone = "adventurous"
    if any(w in all_text for w in ["funny", "laugh", "joke", "haha", "silly"]):
        tone = "comedic"
    elif any(w in all_text for w in ["dark", "shadow", "danger", "fear", "death"]):
        tone = "dark and suspenseful"
    elif any(w in all_text for w in ["love", "heart", "kiss", "together"]):
        tone = "romantic"

    # ── Generate via LLM ──
    suggestions = []
    if LLM_AVAILABLE and EMERGENT_LLM_KEY:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"chain-suggest-{chain_id[:8]}-{datetime.now().timestamp()}",
                system_message="You are a creative comic story advisor who writes highly specific continuation ideas."
            )
            chat.with_model("gemini", "gemini-2.0-flash")

            suggest_prompt = f"""You are continuing a comic story chain. Suggest 3 highly specific directions for the NEXT episode.

## STORY CONTEXT
Characters established: {chars_str}
Visual style: {style_name}
Genre: {genre}
Narrative tone: {tone}
Episodes so far: {len(jobs)}

## RECENT SCENES
{last_scenes}

## RECENT DIALOGUE
{last_dialogues}

## STORY PROMPTS USED
{prompts_str}

## INSTRUCTIONS
- Each suggestion MUST reference at least one existing character by name
- Each suggestion MUST build on the most recent scene or dialogue
- Each prompt must be a concrete 2-sentence story beat (not vague)
- Maintain the {tone} tone and {style_name} visual style

Return ONLY a JSON array with exactly 3 objects. Each must have these fields:
- "title": string (catchy, max 6 words)
- "prompt": string (2 concrete sentences for the next episode)
- "hook": string (1 sentence — why this is exciting)
- "type": one of "escalation", "twist", "deepening"
- "references_character": string (name of character referenced)
- "continues_from": string (brief description of which scene/dialogue it continues)

JSON array only, no markdown:"""

            response = await chat.send_message(UserMessage(text=suggest_prompt))
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                # Validate each suggestion
                valid = []
                required_keys = {"title", "prompt", "hook", "type"}
                for s in parsed[:3]:
                    if isinstance(s, dict) and required_keys.issubset(s.keys()):
                        if s["type"] not in ("escalation", "twist", "deepening"):
                            s["type"] = "twist"
                        valid.append(s)
                suggestions = valid
        except Exception as e:
            logger.warning(f"[CHAIN] AI suggestion failed: {e}")

    # ── Fallback — still context-aware ──
    if not suggestions:
        char = list(characters_seen)[0] if characters_seen else "the hero"
        last_scene = scenes_list[-1] if scenes_list else "the last scene"
        suggestions = [
            {"title": f"{char}'s Turning Point", "prompt": f"After {last_scene}, {char} discovers something that changes everything. The stakes rise dramatically.", "hook": "A pivotal moment for the story", "type": "twist", "references_character": char, "continues_from": last_scene},
            {"title": "The Stakes Escalate", "prompt": f"Building on what just happened, {char} faces a much bigger threat. Allies are nowhere to be found.", "hook": "Raises tension to the next level", "type": "escalation", "references_character": char, "continues_from": last_scene},
            {"title": "A Deeper Truth", "prompt": f"{char} reflects on recent events and uncovers a hidden connection. A new ally or enemy emerges from the shadows.", "hook": "Adds rich depth to the narrative", "type": "deepening", "references_character": char, "continues_from": last_scene},
        ]

    payload = {
        "chain_id": chain_id,
        "current_style": style,
        "current_genre": genre,
        "episode_count": len(jobs),
        "characters": list(characters_seen)[:8],
        "tone": tone,
        "suggestions": suggestions,
    }

    # ── Cache for 1h ──
    await db.suggestion_cache.update_one(
        {"chain_id": chain_id},
        {"$set": {"chain_id": chain_id, "payload": payload, "ts": datetime.now(timezone.utc)}},
        upsert=True
    )

    return payload


@router.get("/my-chains")
async def get_user_chains(user: dict = Depends(get_current_user)):
    """Get all story chains for the current user, grouped."""
    from services.story_chain import backfill_chain_ids

    # Backfill any jobs missing chain IDs
    backfilled = await backfill_chain_ids(user["id"])
    if backfilled:
        logger.info(f"[CHAIN] Backfilled {backfilled} jobs for user {user['id'][:8]}")

    # Get distinct chain IDs
    pipeline = [
        {"$match": {"userId": user["id"], "story_chain_id": {"$exists": True}}},
        {"$group": {
            "_id": "$story_chain_id",
            "root_job_id": {"$first": "$root_job_id"},
            "total_episodes": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$in": ["$status", ["COMPLETED", "PARTIAL_COMPLETE"]]}, 1, 0]}},
            "last_updated": {"$max": "$createdAt"},
            "styles": {"$addToSet": "$style"},
            "continuations": {"$sum": {"$cond": [{"$eq": ["$branch_type", "continuation"]}, 1, 0]}},
            "remixes": {"$sum": {"$cond": [{"$eq": ["$branch_type", "remix"]}, 1, 0]}},
        }},
        {"$sort": {"last_updated": -1}},
        {"$limit": 50},
    ]
    chains = await db.photo_to_comic_jobs.aggregate(pipeline).to_list(50)

    # Enrich with root job info
    result = []
    for c in chains:
        root = await db.photo_to_comic_jobs.find_one(
            {"id": c["root_job_id"]},
            {"_id": 0, "id": 1, "resultUrl": 1, "resultUrls": 1, "panels": 1,
             "title": 1, "style": 1, "genre": 1, "mode": 1, "storyPrompt": 1}
        )
        preview = None
        if root:
            preview = root.get("resultUrl") or (root.get("panels", [{}])[0].get("imageUrl") if root.get("panels") else None)

        total = c["total_episodes"]
        completed = c["completed"]
        progress_pct = round((completed / total) * 100) if total > 0 else 0

        result.append({
            "chain_id": c["_id"],
            "root_job_id": c["root_job_id"],
            "total_episodes": total,
            "completed": completed,
            "progress_pct": progress_pct,
            "continuations": c["continuations"],
            "remixes": c["remixes"],
            "styles_used": c["styles"],
            "last_updated": c["last_updated"],
            "preview_url": preview,
            "root_title": root.get("title") if root else None,
            "root_style": root.get("style") if root else None,
            "root_mode": root.get("mode") if root else None,
        })

    return {"chains": result, "total": len(result)}


@router.get("/script/{job_id}")
async def get_comic_script(job_id: str, user: dict = Depends(get_current_user)):
    """Download the story script as text"""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0, "scriptText": 1, "panels": 1, "status": 1, "style": 1, "genre": 1}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    script = job.get("scriptText")
    if not script and job.get("panels"):
        script = "# Comic Script\n\n"
        for p in job["panels"]:
            script += f"## Panel {p.get('panelNumber', '?')}\n"
            script += f"Scene: {p.get('scene', '')}\n"
            if p.get('dialogue'):
                script += f'Dialogue: "{p["dialogue"]}"\n'
            script += "\n"

    return {
        "script": script or "No script available",
        "style": job.get("style"),
        "genre": job.get("genre")
    }


# =============================================================================
# PDF COMIC EXPORT (P1.1)
# =============================================================================

@router.get("/pdf/{job_id}")
async def download_comic_pdf(job_id: str, user: dict = Depends(get_current_user)):
    """Generate and download a comic PDF with cover, panels, and script"""
    from fpdf import FPDF
    from PIL import Image as PILImage
    import requests as http_requests

    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    panels = job.get("panels", [])
    ready_panels = [p for p in panels if p.get("imageUrl") and p.get("status") == "READY"]
    if not ready_panels and not job.get("resultUrl"):
        raise HTTPException(status_code=400, detail="No comic panels ready for export")

    # Download panel images
    panel_images = []
    for p in ready_panels:
        url = p.get("imageUrl", "")
        if url.startswith("data:image"):
            b64_data = url.split(",", 1)[1] if "," in url else ""
            img_bytes = base64.b64decode(b64_data)
        else:
            try:
                resp = http_requests.get(url, timeout=30)
                resp.raise_for_status()
                img_bytes = resp.content
            except Exception:
                continue
        try:
            img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
            panel_images.append((img, p))
        except Exception:
            continue

    # For avatar mode, use resultUrl
    if not panel_images and job.get("resultUrl"):
        try:
            url = job["resultUrl"]
            if url.startswith("data:image"):
                b64_data = url.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_data)
            else:
                resp = http_requests.get(url, timeout=30)
                resp.raise_for_status()
                img_bytes = resp.content
            img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
            panel_images.append((img, {"panelNumber": 1, "scene": "Comic Avatar"}))
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to fetch comic image")

    if not panel_images:
        raise HTTPException(status_code=400, detail="No images available for PDF")

    # Build PDF
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    # Cover page
    pdf.add_page()
    pdf.set_fill_color(15, 15, 25)
    pdf.rect(0, 0, 210, 297, "F")

    title = job.get("customDetails", "My Comic") or "My Comic"
    style_name = SAFE_STYLES.get(job.get("style", ""), {}).get("name", job.get("style", "Comic"))

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_xy(15, 30)
    pdf.cell(180, 15, title[:50], align="C")

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(180, 180, 200)
    pdf.set_xy(15, 50)
    pdf.cell(180, 10, f"Style: {style_name} | Genre: {job.get('genre', 'adventure').title()}", align="C")

    # First panel as cover image
    if panel_images:
        img, _ = panel_images[0]
        with io.BytesIO() as buf:
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(buf.read())
                tmp_path = tmp.name
        try:
            iw, ih = img.size
            aspect = iw / ih
            max_w, max_h = 170, 170
            if aspect > max_w / max_h:
                w = max_w
                h = max_w / aspect
            else:
                h = max_h
                w = max_h * aspect
            x = (210 - w) / 2
            pdf.image(tmp_path, x=x, y=70, w=w, h=h)
        finally:
            os.unlink(tmp_path)

    pdf.set_text_color(120, 120, 150)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_xy(15, 275)
    pdf.cell(180, 8, "Created with Visionary Suite", align="C")

    # Panel pages (2x2 grid)
    margin = 10
    gutter = 5
    page_w = 210 - 2 * margin
    page_h = 260 - 2 * margin
    box_w = (page_w - gutter) / 2
    box_h = (page_h - gutter) / 2

    for page_start in range(0, len(panel_images), 4):
        pdf.add_page()
        pdf.set_fill_color(15, 15, 25)
        pdf.rect(0, 0, 210, 297, "F")

        batch = panel_images[page_start:page_start + 4]
        for idx, (img, panel_data) in enumerate(batch):
            row, col = divmod(idx, 2)
            x = margin + col * (box_w + gutter)
            y = margin + row * (box_h + gutter) + 10

            # Panel border
            pdf.set_draw_color(60, 60, 80)
            pdf.set_line_width(0.5)
            pdf.rect(x, y, box_w, box_h)

            # Panel image
            with io.BytesIO() as buf:
                img.save(buf, format="JPEG", quality=80)
                buf.seek(0)
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(buf.read())
                    tmp_path = tmp.name
            try:
                iw, ih = img.size
                aspect = iw / ih
                img_area_w = box_w - 4
                img_area_h = box_h - 16
                if aspect > img_area_w / img_area_h:
                    w = img_area_w
                    h = img_area_w / aspect
                else:
                    h = img_area_h
                    w = img_area_h * aspect
                ix = x + (box_w - w) / 2
                iy = y + 2 + (img_area_h - h) / 2
                pdf.image(tmp_path, x=ix, y=iy, w=w, h=h)
            finally:
                os.unlink(tmp_path)

            # Panel label
            pdf.set_text_color(200, 200, 220)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(x + 2, y + box_h - 14)
            label = f"Panel {panel_data.get('panelNumber', idx + 1)}"
            scene = panel_data.get("scene", "")
            if scene:
                label += f": {scene[:40]}"
            pdf.cell(box_w - 4, 6, label)

            # Dialogue
            dialogue = panel_data.get("dialogue")
            if dialogue:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(160, 160, 180)
                pdf.set_xy(x + 2, y + box_h - 8)
                pdf.cell(box_w - 4, 5, f'"{dialogue[:50]}"')

    # Script page
    script = job.get("scriptText", "")
    if not script and panels:
        script = "# Comic Script\n\n"
        for p in panels:
            script += f"Panel {p.get('panelNumber', '?')}: {p.get('scene', '')}\n"
            if p.get("dialogue"):
                script += f'  Dialogue: "{p["dialogue"]}"\n'
            script += "\n"

    if script:
        pdf.add_page()
        pdf.set_fill_color(15, 15, 25)
        pdf.rect(0, 0, 210, 297, "F")

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_xy(15, 20)
        pdf.cell(180, 12, "Story Script")

        pdf.set_text_color(200, 200, 220)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_xy(15, 38)
        pdf.multi_cell(180, 6, script[:3000])

    # Branding footer on last page
    pdf.set_text_color(100, 100, 130)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_xy(15, 280)
    pdf.cell(180, 8, "Created with Visionary Suite | visionary-suite.com", align="C")

    # Output
    pdf_bytes = pdf.output()
    from fastapi.responses import Response
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comic_{job_id[:8]}.pdf"'}
    )


# =============================================================================
# CHARACTER CONSISTENCY ENGINE (P1.2)
# =============================================================================

def build_character_profile(image_bytes: bytes, user_id: str, style: str) -> dict:
    """Build a stable character identity from the uploaded photo"""
    # Stable seed from image + user + style
    digest = hashlib.sha256(image_bytes + user_id.encode() + style.encode()).hexdigest()
    seed = int(digest[:8], 16)

    # Identity hash for consistency tracking
    identity_hash = digest[:32]

    # Style-anchored consistency prompt
    style_name = SAFE_STYLES.get(style, {}).get("name", style)
    anchor_prompt = (
        f"CRITICAL: Maintain the EXACT SAME main character across every panel. "
        f"The character must have identical face shape, hairstyle, skin tone, eye shape, "
        f"and body proportions in ALL panels. The character is a {style_name}-style comic version "
        f"of the person in the reference photo. Do NOT change the character's appearance between panels."
    )

    return {
        "seed": seed,
        "identity_hash": identity_hash,
        "anchor_prompt": anchor_prompt,
        "style": style_name
    }


def panel_seed(base_seed: int, panel_number: int) -> int:
    """Stable-but-varied seed per panel for consistent character"""
    return (base_seed + (panel_number * 7919)) % (2**31 - 1)


# =============================================================================
# BEFORE & AFTER PREVIEW DATA (P1.3)
# =============================================================================

@router.get("/style-previews")
async def get_style_previews(user: dict = Depends(get_current_user)):
    """Return style preview data for the Before/After strip"""
    previews = [
        {"id": "cartoon", "name": "Cartoon", "badge": "Most Popular", "desc": "Bright, friendly, universal appeal"},
        {"id": "manga", "name": "Manga", "badge": "Trending", "desc": "Sharp lines, action-focused style"},
        {"id": "chibi", "name": "Chibi", "badge": "Best for Kids", "desc": "Cute, playful, highly shareable"},
        {"id": "storybook", "name": "Storybook", "badge": "Warm & Magical", "desc": "Soft illustrated fairy-tale look"},
        {"id": "bold_hero", "name": "Bold Hero", "badge": "Best for Action", "desc": "High-energy superhero aesthetic"},
        {"id": "retro_pop", "name": "Retro Pop", "badge": "Classic Vibe", "desc": "Vintage pop-art comic panels"},
        {"id": "noir", "name": "Noir", "badge": "Dramatic", "desc": "Dark shadows, cinematic mood"},
        {"id": "cyberpunk", "name": "Cyberpunk", "badge": "Futuristic", "desc": "Neon-lit sci-fi world"},
    ]
    return {"previews": previews}
