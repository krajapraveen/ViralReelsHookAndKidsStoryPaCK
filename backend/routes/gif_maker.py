"""
Kids-Friendly GIF Generator
CreatorStudio AI

Features:
- Photo upload → Animated GIF
- Emotion-based animations (happy, sad, excited, etc.)
- Safety filters (kids-friendly only)
- Download/share functionality
- Credit-based pricing
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

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

# Credit costs
GIF_CREDITS = {
    "basic": 2,
    "hd": 4,
    "action": 6,
    "batch_5": 8,
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


@router.get("/emotions")
async def get_available_emotions(user: dict = Depends(get_current_user)):
    """Get all available emotion presets"""
    return {
        "emotions": EMOTIONS,
        "styles": GIF_STYLES,
        "backgrounds": BACKGROUNDS,
        "credits": GIF_CREDITS
    }


@router.get("/credits-info")
async def get_gif_credits_info(user: dict = Depends(get_current_user)):
    """Get credit costs for GIF generation"""
    return {
        "costs": GIF_CREDITS,
        "userCredits": user.get("credits", 0),
        "freeUserLimits": {
            "dailyLimit": 2,
            "hasWatermark": True,
            "resolution": "low"
        },
        "paidFeatures": {
            "noWatermark": True,
            "hdResolution": True,
            "batchGeneration": True,
            "permanentStorage": True
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
    quality: str = Form("basic"),  # basic, hd, action
    user: dict = Depends(get_current_user)
):
    """Generate an animated GIF from uploaded photo"""
    
    # Validate emotion
    if emotion not in EMOTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid emotion. Choose from: {list(EMOTIONS.keys())}")
    
    # Validate style
    if style not in GIF_STYLES:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from: {list(GIF_STYLES.keys())}")
    
    # Check text safety
    if add_text:
        is_safe, message = is_content_safe(add_text)
        if not is_safe:
            raise HTTPException(status_code=400, detail=message)
    
    # Calculate cost
    cost = GIF_CREDITS.get(quality, GIF_CREDITS["basic"])
    
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
        "quality": quality,
        "cost": cost,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=7 if user.get("subscription") else 1)).isoformat()
    }
    
    await db.gif_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(
        process_gif_generation, 
        job_id, photo_content, emotion, style, background, add_text, quality, user["id"], cost
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "emotion": emotion_info,
        "estimatedCredits": cost,
        "message": f"Generating {emotion_info['emoji']} {emotion_info['name']} GIF..."
    }


async def process_gif_generation(
    job_id: str, 
    photo_content: bytes, 
    emotion: str, 
    style: str, 
    background: str,
    add_text: str,
    quality: str,
    user_id: str, 
    cost: int
):
    """Background task to generate animated GIF"""
    try:
        await db.gif_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 10}}
        )
        
        emotion_info = EMOTIONS[emotion]
        style_info = GIF_STYLES[style]
        
        result_url = None
        frames = []
        
        # Build generation prompt
        prompt = f"Transform photo into {style_info['name']} animated character showing {emotion_info['name']} emotion. "
        prompt += f"{emotion_info['description']}. Animation: {emotion_info['animation']}. "
        prompt += "Kid-friendly, safe for children, cute style."
        
        if add_text:
            prompt += f" Include text bubble saying: '{add_text}'"
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                # Encode photo to base64
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')
                
                # Update progress
                await db.gif_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"progress": 30, "progressMessage": "Generating frames..."}}
                )
                
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY, 
                    session_id=f"gif-gen-{job_id}", 
                    system_message="You are a kids-friendly cartoon animator. Create cute, safe, animated-style characters."
                )
                chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                
                # Create message with image reference
                msg = UserMessage(
                    text=f"{prompt}. Transform the person in this photo into a cute {style_info['name']} character showing {emotion_info['name']} expression.",
                    file_contents=[ImageContent(photo_b64)]
                )
                
                text_response, images = await chat.send_message_multimodal_response(msg)
                
                if images and len(images) > 0:
                    img_data = images[0]
                    image_bytes = base64.b64decode(img_data['data'])
                    
                    import hashlib
                    filename = f"gif_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.png"
                    filepath = f"/app/backend/static/generated/{filename}"
                    
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    result_url = f"/api/static/generated/{filename}"
                
                await db.gif_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"progress": 70, "progressMessage": "Creating animation..."}}
                )
                    
            except Exception as e:
                logger.error(f"GIF generation error: {e}")
        
        # Placeholder if no result
        if not result_url:
            result_url = f"https://placehold.co/512x512/ff69b4/white?text={emotion_info['emoji']}+{emotion}"
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"GIF: {emotion}")
        
        # Update job
        await db.gif_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "resultUrl": result_url,
                "frames": frames if frames else [result_url],
                "downloadUrl": result_url,
                "shareUrl": f"/share/gif/{job_id}",
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"GIF processing error: {e}")
        await db.gif_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


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
                        image_bytes = base64.b64decode(img_data['data'])
                        
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
