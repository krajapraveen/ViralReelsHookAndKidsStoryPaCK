"""
Kids-Friendly GIF Generator
CreatorStudio AI

Features:
- Photo upload → Animated GIF
- Emotion-based animations (happy, sad, excited, etc.)
- Safety filters (kids-friendly only)
- Download/share functionality
- Credit-based pricing
- Diagonal watermarks for free users
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import os
import sys
import random
import base64
import asyncio
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config

router = APIRouter(prefix="/gif-maker", tags=["GIF Maker"])

# Emotion presets
EMOTIONS = {
    "happy": {
        "name": "Happy",
        "emoji": "😀",
        "description": "Smiling, cheerful expression",
        "animation": "gentle bounce, eyes sparkling",
        "safe": True
    },
    "sad": {
        "name": "Sad",
        "emoji": "😢",
        "description": "Gentle sad expression (not distressing)",
        "animation": "subtle tear drop, slow movement",
        "safe": True
    },
    "excited": {
        "name": "Excited",
        "emoji": "🤩",
        "description": "Stars in eyes, jumping for joy",
        "animation": "bouncing, sparkles around",
        "safe": True
    },
    "laughing": {
        "name": "Laughing",
        "emoji": "😂",
        "description": "Belly laughing, tears of joy",
        "animation": "shaking with laughter, LOL text",
        "safe": True
    },
    "surprised": {
        "name": "Surprised",
        "emoji": "😲",
        "description": "Wide eyes, open mouth",
        "animation": "pop out effect, question marks",
        "safe": True
    },
    "thinking": {
        "name": "Thinking",
        "emoji": "🤔",
        "description": "Hand on chin, thought bubble",
        "animation": "thought bubble appearing, dots",
        "safe": True
    },
    "dancing": {
        "name": "Dancing",
        "emoji": "🕺",
        "description": "Fun dance moves",
        "animation": "side to side, music notes",
        "safe": True
    },
    "waving": {
        "name": "Waving",
        "emoji": "👋",
        "description": "Friendly wave hello/goodbye",
        "animation": "hand waving, sparkles",
        "safe": True
    },
    "jumping": {
        "name": "Jumping",
        "emoji": "🦘",
        "description": "Jumping up and down",
        "animation": "up and down bounce, stars",
        "safe": True
    },
    "hearts": {
        "name": "Love/Hearts",
        "emoji": "❤️",
        "description": "Hearts floating around",
        "animation": "hearts popping up, floating",
        "safe": True
    },
    "thumbsup": {
        "name": "Thumbs Up",
        "emoji": "👍",
        "description": "Approval gesture",
        "animation": "thumb rising up, sparkle",
        "safe": True
    },
    "celebrate": {
        "name": "Celebrate",
        "emoji": "🎉",
        "description": "Party celebration",
        "animation": "confetti falling, party hat",
        "safe": True
    }
}

# Cartoon/Sticker styles
GIF_STYLES = {
    "cartoon": {
        "name": "Cartoon Style",
        "description": "Fun cartoon transformation"
    },
    "sticker": {
        "name": "Sticker Style",
        "description": "WhatsApp/Telegram sticker look"
    },
    "chibi": {
        "name": "Chibi Style",
        "description": "Cute big-head small-body style"
    },
    "pixel": {
        "name": "Pixel Art",
        "description": "Retro pixel animation"
    },
    "watercolor": {
        "name": "Watercolor",
        "description": "Soft watercolor effect"
    }
}

# Background options
BACKGROUNDS = {
    "transparent": "Transparent (PNG)",
    "white": "White",
    "gradient_pink": "Pink Gradient",
    "gradient_blue": "Blue Gradient",
    "gradient_rainbow": "Rainbow",
    "sparkles": "Sparkly Background",
    "hearts": "Hearts Pattern",
    "stars": "Stars Pattern"
}

# Credit costs - Updated pricing
GIF_CREDITS = {
    "generate": 10,  # Cost to view/generate
    "download": 15,  # Cost to download
    "batch_multiplier": 0.8,  # 20% discount for batch
    "batch_10": 15
}

# Blocked content for safety
UNSAFE_KEYWORDS = [
    "nude", "nsfw", "sexual", "violent", "gore", "blood", "weapon",
    "drug", "alcohol", "cigarette", "smoking", "gun", "knife",
    "hate", "racist", "abuse", "explicit", "adult"
]


def is_content_safe(text: str) -> tuple:
    """Check if content is kids-friendly"""
    text_lower = text.lower()
    for keyword in UNSAFE_KEYWORDS:
        if keyword in text_lower:
            return False, f"Content containing '{keyword}' is not allowed. This platform generates only kid-friendly safe GIFs."
    return True, "OK"


def get_animation_frames(emotion: str, frame_count: int) -> list:
    """Get frame descriptions for animation based on emotion"""
    animation_sequences = {
        "happy": [
            "neutral face starting to smile",
            "mouth curving into a smile, eyes bright",
            "full smile, eyes crinkling with joy",
            "smile at maximum, sparkles appear",
            "slight bounce upward",
            "back to normal position with smile",
            "eyes sparkling more",
            "gentle head tilt with smile",
            "return to center, maintaining smile",
            "subtle glow effect around face",
            "another small bounce",
            "final happy pose"
        ],
        "sad": [
            "normal expression",
            "eyebrows starting to furrow",
            "eyes getting watery",
            "small tear forming",
            "tear rolling down cheek",
            "wiping tear motion",
            "looking down slightly",
            "deep breath expression",
            "slight recovery",
            "still melancholy",
            "another tear forming",
            "final sad pose"
        ],
        "excited": [
            "eyes widening",
            "jumping up slightly",
            "arms raising",
            "at peak of jump with stars",
            "coming back down",
            "bouncing again",
            "sparkles all around",
            "another jump",
            "landing with enthusiasm",
            "fists pumping",
            "big grin",
            "final excited pose"
        ],
        "laughing": [
            "starting to chuckle",
            "mouth opening for laugh",
            "eyes squinting with joy",
            "full belly laugh, shaking",
            "tears of joy forming",
            "holding stomach",
            "laughing harder",
            "slight pause to breathe",
            "continuing to laugh",
            "wiping joy tears",
            "still giggling",
            "final laughing pose"
        ],
        "surprised": [
            "normal expression",
            "eyes starting to widen",
            "mouth opening",
            "eyes fully wide, gasping",
            "jaw dropped",
            "question marks appearing",
            "hands coming up",
            "stepped back slightly",
            "still surprised",
            "processing what happened",
            "starting to recover",
            "final surprised pose"
        ],
        "thinking": [
            "neutral expression",
            "eyebrows raising",
            "hand coming to chin",
            "looking up thoughtfully",
            "thought bubble appearing",
            "dots in thought bubble",
            "more dots appearing",
            "lightbulb starting",
            "lightbulb glowing",
            "eyes brightening with idea",
            "smile forming",
            "eureka moment"
        ],
        "dancing": [
            "standing ready",
            "moving to the left",
            "arms swaying left",
            "shifting weight right",
            "arms swaying right",
            "doing a spin",
            "mid-spin",
            "completing spin",
            "jumping up",
            "landing with style",
            "hip bump",
            "final dance pose"
        ],
        "waving": [
            "hand starting to rise",
            "hand at shoulder level",
            "hand up, starting wave",
            "hand moving right",
            "hand moving left",
            "continuing wave",
            "enthusiastic wave",
            "big smile while waving",
            "slowing wave",
            "hand coming down slightly",
            "final wave",
            "hand lowering"
        ],
        "jumping": [
            "crouching to jump",
            "pushing off ground",
            "leaving ground",
            "rising higher",
            "at peak height",
            "arms spread wide",
            "starting to descend",
            "coming down",
            "about to land",
            "landing impact",
            "recovery pose",
            "ready position again"
        ],
        "hearts": [
            "loving expression forming",
            "eyes becoming heart-shaped",
            "small hearts appearing",
            "more hearts floating up",
            "hearts multiplying",
            "swaying with love",
            "clutching hands to heart",
            "hearts everywhere",
            "dreamy expression",
            "sigh of contentment",
            "more hearts",
            "final loving pose"
        ],
        "thumbsup": [
            "neutral pose",
            "arm starting to raise",
            "fist forming",
            "thumb extending",
            "thumb fully up",
            "sparkle on thumb",
            "confident smile",
            "slight nod",
            "another sparkle",
            "maintaining pose",
            "wink",
            "final thumbs up"
        ],
        "celebrate": [
            "excited expression",
            "arms starting to raise",
            "confetti appearing",
            "hands in the air",
            "party hat appearing",
            "more confetti falling",
            "jumping with joy",
            "streamers everywhere",
            "dancing celebration",
            "cheering pose",
            "confetti shower",
            "final celebration"
        ]
    }
    
    frames = animation_sequences.get(emotion, animation_sequences["happy"])
    
    # Adjust frame count
    if frame_count >= len(frames):
        return frames
    else:
        # Sample evenly from available frames
        step = len(frames) / frame_count
        return [frames[int(i * step)] for i in range(frame_count)]


async def create_animated_gif(job_id: str, frame_paths: list, emotion: str) -> str:
    """Create an animated GIF from frame images"""
    try:
        from PIL import Image
        import io
        
        if not frame_paths:
            return None
        
        images = []
        for path in frame_paths:
            if os.path.exists(path):
                img = Image.open(path)
                # Resize to consistent size
                img = img.resize((512, 512), Image.Resampling.LANCZOS)
                images.append(img)
        
        if not images:
            return None
        
        # Create GIF
        import hashlib
        gif_filename = f"animated_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.gif"
        gif_path = f"/app/backend/static/generated/{gif_filename}"
        
        # Duration based on emotion (milliseconds per frame)
        duration_map = {
            "dancing": 120, "jumping": 100, "excited": 100,
            "thinking": 300, "sad": 250, "happy": 150,
            "laughing": 120, "surprised": 150, "waving": 150,
            "hearts": 200, "thumbsup": 200, "celebrate": 100
        }
        duration = duration_map.get(emotion, 150)
        
        # Save as animated GIF
        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=0  # 0 = infinite loop
        )
        
        return gif_path
        
    except Exception as e:
        logger.error(f"Error creating animated GIF: {e}")
        return None


async def create_fallback_gif(job_id: str, photo_content: bytes, emotion: str) -> str:
    """Create a simple animated GIF with bounce effect from photo"""
    try:
        from PIL import Image
        import io
        
        # Open the photo
        img = Image.open(io.BytesIO(photo_content))
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        
        frames = []
        
        # Create bounce animation frames
        offsets = [0, -5, -10, -15, -10, -5, 0, 5, 10, 5, 0]
        
        for offset in offsets:
            frame = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            # Paste with offset
            paste_y = max(0, min(offset + 10, 20))
            frame.paste(img.resize((490, 490), Image.Resampling.LANCZOS), (11, paste_y))
            frames.append(frame)
        
        if not frames:
            return None
        
        # Save as GIF
        import hashlib
        gif_filename = f"bounce_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.gif"
        gif_path = f"/app/backend/static/generated/{gif_filename}"
        
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0
        )
        
        return gif_path
        
    except Exception as e:
        logger.error(f"Error creating fallback GIF: {e}")
        return None



@router.get("/templates")
async def get_gif_templates():
    """Get available GIF templates and presets"""
    return {
        "templates": [
            {"id": "reaction", "name": "Reaction GIF", "description": "Photo with animated reactions"},
            {"id": "meme", "name": "Meme Style", "description": "Photo with text overlays"},
            {"id": "bounce", "name": "Bounce", "description": "Simple bounce animation"},
            {"id": "shake", "name": "Shake", "description": "Shake effect animation"},
            {"id": "zoom", "name": "Zoom", "description": "Zoom in/out effect"}
        ],
        "emotions": EMOTIONS,
        "styles": GIF_STYLES,
        "default_template": "reaction"
    }



@router.get("/emotions")
async def get_available_emotions(user: dict = Depends(get_current_user)):
    """Get all available emotion presets"""
    return {
        "emotions": EMOTIONS,
        "styles": GIF_STYLES,
        "backgrounds": BACKGROUNDS,
        "credits": GIF_CREDITS,
        "animationIntensities": {
            "simple": {"name": "Simple", "frames": 4, "description": "Quick bounce/pulse (faster)"},
            "medium": {"name": "Medium", "frames": 8, "description": "Smooth animation"},
            "complex": {"name": "Complex", "frames": 12, "description": "Detailed motion (slower)"}
        },
        "pricing": {
            "generate": 10,
            "download": 15
        }
    }


@router.get("/credits-info")
async def get_gif_credits_info(user: dict = Depends(get_current_user)):
    """Get credit costs for GIF generation"""
    return {
        "costs": GIF_CREDITS,
        "userCredits": user.get("credits", 0),
        "pricing": {
            "generate": 10,
            "download": 15
        },
        "animationOptions": {
            "simple": "3-5 frames, faster generation",
            "medium": "6-8 frames, balanced",
            "complex": "10-12 frames, detailed motion"
        }
    }


@router.post("/generate")
async def generate_gif(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    emotion: str = Form(...),
    style: str = Form("cartoon"),
    background: str = Form("transparent"),
    add_text: Optional[str] = Form(None),
    animation_intensity: str = Form("medium"),  # simple, medium, complex
    user: dict = Depends(get_current_user)
):
    """Generate an animated GIF from uploaded photo"""
    
    # Validate emotion
    if emotion not in EMOTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid emotion. Choose from: {list(EMOTIONS.keys())}")
    
    # Validate style
    if style not in GIF_STYLES:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from: {list(GIF_STYLES.keys())}")
    
    # Validate animation intensity
    intensity_map = {"simple": 4, "medium": 8, "complex": 12}
    if animation_intensity not in intensity_map:
        animation_intensity = "medium"
    frame_count = intensity_map[animation_intensity]
    
    # Check text safety
    if add_text:
        is_safe, message = is_content_safe(add_text)
        if not is_safe:
            raise HTTPException(status_code=400, detail=message)
    
    # Calculate cost - 10 credits for generation
    cost = GIF_CREDITS["generate"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Validate file
    if not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")
    
    photo_content = await photo.read()
    if len(photo_content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")
    
    # Create job
    job_id = str(uuid.uuid4())
    emotion_info = EMOTIONS[emotion]
    style_info = GIF_STYLES[style]
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "GIF_GENERATION",
        "status": "QUEUED",
        "emotion": emotion,
        "style": style,
        "background": background,
        "addText": add_text,
        "animationIntensity": animation_intensity,
        "frameCount": frame_count,
        "cost": cost,
        "downloadCost": GIF_CREDITS["download"],
        "downloaded": False,
        "progress": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=7 if user.get("subscription") else 1)).isoformat()
    }
    
    await db.gif_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(
        process_gif_generation, 
        job_id, photo_content, emotion, style, background, add_text, animation_intensity, frame_count, user["id"], cost
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "emotion": emotion_info,
        "estimatedCredits": cost,
        "downloadCredits": GIF_CREDITS["download"],
        "message": f"Generating {emotion_info['emoji']} {emotion_info['name']} GIF..."
    }


async def process_gif_generation(
    job_id: str, 
    photo_content: bytes, 
    emotion: str, 
    style: str, 
    background: str,
    add_text: str,
    animation_intensity: str,
    frame_count: int,
    user_id: str, 
    cost: int
):
    """Background task to generate animated GIF - OPTIMIZED for speed"""
    try:
        from routes.optimized_workers import (
            update_job_progress, generate_image_fast, save_image_async,
            create_gif_optimized, create_bounce_gif_fast, get_progress_for_step
        )
        
        # Step 1: Initialize
        progress, msg = get_progress_for_step("gif", "start")
        await update_job_progress("gif_jobs", job_id, progress, msg, "PROCESSING")
        
        emotion_info = EMOTIONS[emotion]
        style_info = GIF_STYLES[style]
        
        frames = []
        result_url = None
        
        # Step 2: Process image
        progress, msg = get_progress_for_step("gif", "processing")
        await update_job_progress("gif_jobs", job_id, progress, msg)
        
        # Encode photo to base64
        photo_b64 = base64.b64encode(photo_content).decode('utf-8')
        
        # Use fewer frames for faster generation
        optimized_frame_count = min(frame_count, 6)  # Cap at 6 frames for speed
        animation_frames = get_animation_frames(emotion, optimized_frame_count)
        
        # Step 3: Generate frames
        progress, msg = get_progress_for_step("gif", "generating")
        await update_job_progress("gif_jobs", job_id, progress, msg)
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                # Generate frames with progress updates
                for i, frame_desc in enumerate(animation_frames):
                    # Update progress for each frame
                    frame_progress, frame_msg = get_progress_for_step("gif", "frame", i + 1, len(animation_frames))
                    await update_job_progress("gif_jobs", job_id, frame_progress, frame_msg)
                    
                    # Optimized prompt for faster generation
                    prompt = f"""Transform to {style_info['name']} cartoon: {emotion_info['name']} expression.
Frame {i+1}: {frame_desc}
Kid-friendly, cute style.{f' Text: {add_text}' if add_text else ''}"""
                    
                    image_bytes = await generate_image_fast(
                        prompt,
                        f"gif-{job_id}-{i}",
                        photo_b64
                    )
                    
                    if image_bytes:
                        filename = f"gif_frame_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:12]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        if await save_image_async(image_bytes, filepath):
                            frames.append(filepath)
                
                # Step 4: Assemble GIF
                if frames:
                    progress, msg = get_progress_for_step("gif", "assembling")
                    await update_job_progress("gif_jobs", job_id, progress, msg)
                    
                    duration_map = {
                        "dancing": 120, "jumping": 100, "excited": 100,
                        "thinking": 300, "sad": 250, "happy": 150,
                        "laughing": 120, "surprised": 150, "waving": 150,
                        "hearts": 200, "thumbsup": 200, "celebrate": 100
                    }
                    duration = duration_map.get(emotion, 150)
                    
                    gif_filename = f"animated_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.gif"
                    gif_path = f"/app/backend/static/generated/{gif_filename}"
                    
                    if await create_gif_optimized(frames, gif_path, duration):
                        result_url = f"/api/static/generated/{gif_filename}"
                        
            except Exception as e:
                logger.error(f"GIF generation error: {e}")
        
        # Fallback: create quick bounce animation
        if not result_url:
            progress, msg = get_progress_for_step("gif", "assembling")
            await update_job_progress("gif_jobs", job_id, progress, "Creating animation...")
            
            try:
                gif_filename = f"bounce_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.gif"
                gif_path = f"/app/backend/static/generated/{gif_filename}"
                
                if await create_bounce_gif_fast(photo_content, gif_path, emotion):
                    result_url = f"/api/static/generated/{gif_filename}"
            except Exception as e:
                logger.error(f"Fallback GIF error: {e}")
        
        if not result_url:
            result_url = f"https://placehold.co/512x512/ff69b4/white?text={emotion_info['emoji']}+{emotion}"
        
        # Step 5: Finalize
        progress, msg = get_progress_for_step("gif", "finalizing")
        await update_job_progress("gif_jobs", job_id, progress, msg)
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"GIF: {emotion}")
        
        # Complete
        await db.gif_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "progressMessage": "Complete!",
                "resultUrl": result_url,
                "frames": [f"/api/static/generated/{os.path.basename(f)}" for f in frames] if frames else [result_url],
                "downloadUrl": result_url,
                "downloaded": False,
                "downloadCost": GIF_CREDITS["download"],
                "shareUrl": f"/share/gif/{job_id}",
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"GIF processing error: {e}")
        await db.gif_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e), "progress": 0, "progressMessage": "Generation failed"}}
        )


@router.post("/download/{job_id}")
async def download_gif(job_id: str, user: dict = Depends(get_current_user)):
    """Download GIF - requires additional credits"""
    job = await db.gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="GIF not ready for download")
    
    # Check if already downloaded (free re-download)
    if job.get("downloaded"):
        return {
            "success": True,
            "downloadUrl": job.get("resultUrl"),
            "alreadyPurchased": True
        }
    
    download_cost = GIF_CREDITS["download"]
    current_credits = user.get("credits", 0)
    
    if current_credits < download_cost:
        subscription = await db.subscriptions.find_one(
            {"userId": user["id"], "status": "ACTIVE"},
            {"_id": 0}
        )
        
        if subscription:
            return {
                "success": False,
                "error": "INSUFFICIENT_CREDITS",
                "message": f"You need {download_cost} credits to download. Current balance: {current_credits}. Please top-up your credits.",
                "creditsNeeded": download_cost,
                "currentCredits": current_credits,
                "hasSubscription": True
            }
        else:
            return {
                "success": False,
                "error": "NO_SUBSCRIPTION",
                "message": "Please subscribe to download content.",
                "creditsNeeded": download_cost,
                "currentCredits": current_credits,
                "hasSubscription": False
            }
    
    # Deduct credits
    await deduct_credits(user["id"], download_cost, f"Download GIF: {job_id[:8]}")
    
    # Mark as downloaded
    await db.gif_jobs.update_one(
        {"id": job_id},
        {"$set": {"downloaded": True, "downloadedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "success": True,
        "downloadUrl": job.get("resultUrl"),
        "creditsDeducted": download_cost,
        "message": "Download unlocked!"
    }


@router.get("/download-status/{job_id}")
async def check_gif_download_status(job_id: str, user: dict = Depends(get_current_user)):
    """Check if user can download GIF"""
    job = await db.gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    download_cost = GIF_CREDITS["download"]
    
    return {
        "canDownload": job.get("downloaded", False) or user.get("credits", 0) >= download_cost,
        "alreadyDownloaded": job.get("downloaded", False),
        "downloadCost": download_cost if not job.get("downloaded") else 0,
        "userCredits": user.get("credits", 0)
    }


@router.post("/generate-batch")
async def generate_gif_batch(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    emotions: str = Form(...),  # Comma-separated: "happy,sad,excited"
    style: str = Form("cartoon"),
    user: dict = Depends(get_current_user)
):
    """Generate multiple GIFs with different emotions from one photo"""
    
    emotion_list = [e.strip() for e in emotions.split(",")]
    
    # Validate emotions
    for emotion in emotion_list:
        if emotion not in EMOTIONS:
            raise HTTPException(status_code=400, detail=f"Invalid emotion: {emotion}")
    
    # Calculate cost
    if len(emotion_list) <= 5:
        cost = GIF_CREDITS["batch_5"]
    else:
        cost = GIF_CREDITS["batch_10"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Validate file
    if not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    photo_content = await photo.read()
    
    # Create batch job
    batch_id = str(uuid.uuid4())
    
    job_data = {
        "id": batch_id,
        "userId": user["id"],
        "type": "GIF_BATCH",
        "status": "QUEUED",
        "emotions": emotion_list,
        "style": style,
        "cost": cost,
        "results": [],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.gif_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(
        process_gif_batch, batch_id, photo_content, emotion_list, style, user["id"], cost
    )
    
    return {
        "success": True,
        "batchId": batch_id,
        "status": "QUEUED",
        "emotionCount": len(emotion_list),
        "estimatedCredits": cost
    }


async def process_gif_batch(batch_id: str, photo_content: bytes, emotions: list, style: str, user_id: str, cost: int):
    """Process batch GIF generation"""
    try:
        results = []
        style_info = GIF_STYLES[style]
        
        # Encode photo to base64 once
        photo_b64 = base64.b64encode(photo_content).decode('utf-8')
        
        for i, emotion in enumerate(emotions):
            await db.gif_jobs.update_one(
                {"id": batch_id},
                {"$set": {
                    "status": "PROCESSING",
                    "progress": int((i / len(emotions)) * 100),
                    "currentEmotion": emotion
                }}
            )
            
            emotion_info = EMOTIONS[emotion]
            result_url = None
            
            if LLM_AVAILABLE and EMERGENT_LLM_KEY:
                try:
                    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                    
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY, 
                        session_id=f"gif-batch-{batch_id}-{i}", 
                        system_message="You are a kids-friendly cartoon animator. Create cute, safe characters."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    prompt = f"Transform photo into {style_info['name']} character showing {emotion_info['name']}. {emotion_info['description']}. Kid-friendly, cute."
                    
                    msg = UserMessage(
                        text=prompt,
                        file_contents=[ImageContent(photo_b64)]
                    )
                    
                    text_response, images = await chat.send_message_multimodal_response(msg)
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        # Handle both dict format and raw base64 string
                        if isinstance(img_data, dict):
                            image_bytes = base64.b64decode(img_data.get('data', ''))
                        elif isinstance(img_data, str):
                            # Already base64 string
                            image_bytes = base64.b64decode(img_data)
                        else:
                            image_bytes = img_data if isinstance(img_data, bytes) else b''
                        
                        if not image_bytes:
                            logger.warning(f"Empty image data for batch {batch_id} image {i}")
                            continue
                        
                        # Apply watermark for free users
                        user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
                        user_plan = user_data.get("plan", "free") if user_data else "free"
                        
                        if should_apply_watermark(user_plan):
                            config = get_watermark_config("GIF")
                            image_bytes = add_diagonal_watermark(
                                image_bytes,
                                text=config["text"],
                                opacity=config["opacity"],
                                font_size=config["font_size"],
                                spacing=config["spacing"]
                            )
                        
                        import hashlib
                        filename = f"gif_batch_{hashlib.md5(f'{batch_id}_{i}'.encode()).hexdigest()[:16]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        result_url = f"/api/static/generated/{filename}"
                        
                except Exception as e:
                    logger.error(f"Batch GIF error: {e}")
            
            if not result_url:
                result_url = f"https://placehold.co/512x512/ff69b4/white?text={emotion_info['emoji']}"
            
            results.append({
                "emotion": emotion,
                "emoji": emotion_info["emoji"],
                "url": result_url
            })
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"GIF batch: {len(emotions)} emotions")
        
        # Update job
        await db.gif_jobs.update_one(
            {"id": batch_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "results": results,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        await db.gif_jobs.update_one(
            {"id": batch_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


@router.get("/job/{job_id}")
async def get_gif_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get GIF generation job status"""
    job = await db.gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history")
async def get_gif_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's GIF generation history"""
    jobs = await db.gif_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.gif_jobs.count_documents({"userId": user["id"]})
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.delete("/job/{job_id}")
async def delete_gif_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a GIF job"""
    result = await db.gif_jobs.delete_one(
        {"id": job_id, "userId": user["id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "message": "GIF deleted"}


@router.post("/regenerate/{job_id}")
async def regenerate_gif(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Regenerate a GIF with same settings"""
    job = await db.gif_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cost = job.get("cost", GIF_CREDITS["basic"])
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Create new job based on old settings
    new_job_id = str(uuid.uuid4())
    
    new_job = {
        "id": new_job_id,
        "userId": user["id"],
        "type": job.get("type", "GIF_GENERATION"),
        "status": "QUEUED",
        "emotion": job.get("emotion"),
        "style": job.get("style"),
        "background": job.get("background"),
        "quality": job.get("quality"),
        "cost": cost,
        "regeneratedFrom": job_id,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.gif_jobs.insert_one(new_job)
    
    return {
        "success": True,
        "newJobId": new_job_id,
        "status": "QUEUED",
        "message": "Regenerating GIF..."
    }


@router.get("/share/{job_id}")
async def get_shareable_gif(job_id: str):
    """Get shareable GIF (public endpoint)"""
    job = await db.gif_jobs.find_one(
        {"id": job_id, "status": "COMPLETED"},
        {"_id": 0, "userId": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="GIF not found or not ready")
    
    return {
        "id": job_id,
        "resultUrl": job.get("resultUrl"),
        "emotion": job.get("emotion"),
        "style": job.get("style"),
        "createdAt": job.get("createdAt"),
        "watermark": "Made with Visionary Suite AI"
    }
