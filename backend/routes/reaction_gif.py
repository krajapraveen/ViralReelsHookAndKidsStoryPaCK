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

router = APIRouter(prefix="/reaction-gif", tags=["Photo Reaction GIF"])

# ============================================
# BLOCKED KEYWORDS
# ============================================
BLOCKED_KEYWORDS = [
    "marvel", "dc", "disney", "naruto", "pokemon", "spiderman", "batman",
    "avengers", "goku", "harry potter", "hogwarts", "frozen", "elsa",
    "mickey", "minnie", "pixar", "fortnite", "minecraft", "celebrity",
    "politician", "real person", "nude", "nsfw", "violence", "gore"
]

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
# GIF STYLES
# ============================================
GIF_STYLES = {
    "cartoon_motion": {
        "name": "Cartoon Motion",
        "prompt": "cartoon style animation, bouncy movement, playful motion"
    },
    "comic_bounce": {
        "name": "Comic Bounce",
        "prompt": "comic book style, pop art effect, dynamic bounce"
    },
    "sticker_style": {
        "name": "Sticker Style",
        "prompt": "cute sticker style, outlined edges, adorable character"
    },
    "neon_glow": {
        "name": "Neon Glow",
        "prompt": "neon glow effect, vibrant colors, glowing edges"
    },
    "minimal_clean": {
        "name": "Minimal Clean",
        "prompt": "minimal clean style, simple elegant, subtle animation"
    }
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
    """Check for blocked keywords"""
    if not text:
        return False, None
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True, keyword
    return False, None


def get_negative_prompt() -> str:
    """Build negative prompt string"""
    return ", ".join(UNIVERSAL_NEGATIVE_PROMPTS)


@router.get("/reactions")
async def get_reaction_types(user: dict = Depends(get_current_user)):
    """Get available reaction types"""
    return {
        "reactions": {k: {"emoji": v["emoji"]} for k, v in REACTION_TYPES.items()},
        "styles": {k: {"name": v["name"]} for k, v in GIF_STYLES.items()},
        "pricing": PRICING
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
    
    # Check caption for blocked content
    if caption:
        is_blocked, keyword = check_blocked_keywords(caption)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Brand-based or copyrighted content is not allowed. Detected: '{keyword}'."
            )
    
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
    
    # Check credits
    if user.get("credits", 0) < cost:
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
        "progress": 0,
        "resultUrl": None,
        "results": [],
        "purchased": user_plan != "free",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reaction_gif_jobs.insert_one(job_data)
    
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
    """Background task to generate reaction GIF"""
    try:
        await db.reaction_gif_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 10, "progressMessage": "Processing photo..."}}
        )
        
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
                
                progress = 10 + int(((i + 1) / total_reactions) * 80)
                await db.reaction_gif_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "progress": progress,
                        "progressMessage": f"Creating {reaction_info['emoji']} reaction..."
                    }}
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
                            
                            _, images = await chat.send_message_multimodal_response(msg)
                            
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
                                
                        except Exception as retry_err:
                            last_error = str(retry_err)
                            logger.warning(f"Retry {attempt + 1}/{max_retries} for {react}: {last_error}")
                            if attempt < max_retries - 1:
                                import asyncio
                                await asyncio.sleep(2 * (attempt + 1))  # Exponential backoff: 2s, 4s
                    
                    if image_bytes:
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
                        
                        url = f"/api/generated/{filename}"
                        result_entry = {
                            "reaction": react,
                            "emoji": reaction_info["emoji"],
                            "url": url,
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
        if len(real_results) > 0:
            # At least some images were generated successfully — deduct credits
            await deduct_credits(user_id, cost, f"Reaction GIF: {job_id[:8]}")
            
            result_url = real_results[0]["url"]
            
            await db.reaction_gif_jobs.update_one(
                {"id": job_id},
                {"$set": {
                    "status": "COMPLETED",
                    "progress": 100,
                    "progressMessage": "Complete!",
                    "resultUrl": result_url,
                    "results": real_results,
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
    """Download GIF(s)"""
    job = await db.reaction_gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="GIF not ready")
    
    # Check if free user
    user_plan = user.get("plan", "free")
    if user_plan == "free" and not job.get("purchased"):
        raise HTTPException(
            status_code=403,
            detail="Upgrade to download. Preview is watermarked."
        )
    
    # Get all URLs
    download_urls = [r["url"] for r in job.get("results", [])]
    if not download_urls and job.get("resultUrl"):
        download_urls = [job["resultUrl"]]
    
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
