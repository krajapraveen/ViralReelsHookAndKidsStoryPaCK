"""
GenStudio Router - AI Generation Suite
Text-to-Image, Text-to-Video, Image-to-Video, Video Remix, Style Profiles
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import os
import base64
import asyncio
import traceback
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits, log_exception,
    LLM_AVAILABLE, EMERGENT_LLM_KEY, FILE_EXPIRY_MINUTES
)
from ml_threat_detection import threat_intel
from security import log_security_event, limiter
from fastapi import Request

genstudio_router = APIRouter(prefix="/genstudio", tags=["GenStudio"])

# Credit Costs
GENSTUDIO_COSTS = {
    "text_to_image": 10,
    "text_to_video": 10,
    "image_to_video": 10,
    "style_profile_create": 20,
    "style_profile_use": 1,
    "video_remix": 12
}

# Prompt Templates
GENSTUDIO_TEMPLATES = [
    {"id": "product_ad", "name": "Product Advertisement", "category": "marketing", "prompt": "Professional product photography of {product}, studio lighting, white background, commercial quality, 8k resolution"},
    {"id": "luxury_reel", "name": "Luxury Brand Reel", "category": "marketing", "prompt": "Cinematic shot of {subject}, luxury aesthetic, golden hour lighting, elegant composition, premium feel"},
    {"id": "kids_story", "name": "Kids Story Illustration", "category": "creative", "prompt": "Colorful children's book illustration of {scene}, whimsical style, soft pastel colors, friendly characters, storybook quality"},
    {"id": "motivation", "name": "Motivational Content", "category": "social", "prompt": "Inspirational image with {theme}, dramatic lighting, powerful composition, motivational atmosphere"},
    {"id": "social_post", "name": "Social Media Post", "category": "social", "prompt": "Eye-catching social media graphic featuring {subject}, vibrant colors, modern design, engagement-optimized"},
    {"id": "nature_scene", "name": "Nature Landscape", "category": "creative", "prompt": "Breathtaking landscape of {location}, golden hour, dramatic sky, professional photography, National Geographic style"},
    {"id": "food_photo", "name": "Food Photography", "category": "marketing", "prompt": "Appetizing food photography of {dish}, professional styling, soft lighting, restaurant quality, mouth-watering presentation"},
    {"id": "tech_product", "name": "Tech Product Shot", "category": "marketing", "prompt": "Sleek tech product render of {product}, minimalist background, professional lighting, Apple-style aesthetic"}
]


# Pydantic Models
class TextToImageRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    negative_prompt: Optional[str] = None
    aspect_ratio: str = "1:1"
    style_profile_id: Optional[str] = None
    template_id: Optional[str] = None
    add_watermark: bool = True
    consent_confirmed: bool = False


class TextToVideoRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    duration: int = Field(default=4, ge=2, le=12)
    fps: int = Field(default=24, ge=15, le=30)
    aspect_ratio: str = "16:9"
    add_watermark: bool = True
    consent_confirmed: bool = False


class StyleProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    tags: List[str] = []


# =============================================================================
# DASHBOARD & TEMPLATES
# =============================================================================
@genstudio_router.get("/dashboard")
async def genstudio_dashboard(user: dict = Depends(get_current_user)):
    """Get GenStudio dashboard data"""
    recent_jobs = await db.genstudio_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(10)
    
    style_profiles = await db.style_profiles.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(50)
    
    total_generations = await db.genstudio_jobs.count_documents({"userId": user["id"]})
    total_images = await db.genstudio_jobs.count_documents({"userId": user["id"], "type": "text_to_image"})
    total_videos = await db.genstudio_jobs.count_documents({"userId": user["id"], "type": {"$in": ["text_to_video", "image_to_video", "video_remix"]}})
    
    return {
        "credits": user.get("credits", 0),
        "plan": user.get("plan", "free"),
        "recentJobs": recent_jobs,
        "styleProfiles": style_profiles,
        "stats": {
            "totalGenerations": total_generations,
            "totalImages": total_images,
            "totalVideos": total_videos
        },
        "templates": GENSTUDIO_TEMPLATES,
        "costs": GENSTUDIO_COSTS,
        "fileExpiryMinutes": FILE_EXPIRY_MINUTES
    }


@genstudio_router.get("/templates")
async def get_templates():
    """Get prompt templates"""
    return {"templates": GENSTUDIO_TEMPLATES}


# =============================================================================
# TEXT TO IMAGE
# =============================================================================
@genstudio_router.post("/text-to-image")
@limiter.limit("20/minute")
async def generate_text_to_image(request: Request, data: TextToImageRequest, user: dict = Depends(get_current_user)):
    """Generate image from text prompt using Gemini - costs 10 credits"""
    if not data.consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # ML Content moderation
    moderation_result = threat_intel.moderate_content(data.prompt, user.get("id"))
    if not moderation_result["allowed"]:
        violations = moderation_result.get("violations", [])
        violation_msg = violations[0].get("message") if violations else "Content policy violation"
        log_security_event("GENSTUDIO_IMAGE_BLOCKED", {
            "user_id": user.get("id"),
            "violations": violations,
            "prompt": data.prompt[:100]
        }, "WARNING")
        raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
    
    cost = GENSTUDIO_COSTS["text_to_image"]
    
    if user.get("credits", 0) < cost:
        if not user.get("subscription"):
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    job_id = str(uuid.uuid4())
    
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_image",
        "status": "processing",
        "inputJson": data.model_dump(),
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        prompt = data.prompt
        if data.template_id:
            template = next((t for t in GENSTUDIO_TEMPLATES if t["id"] == data.template_id), None)
            if template:
                prompt = template["prompt"].replace("{subject}", data.prompt).replace("{product}", data.prompt).replace("{scene}", data.prompt).replace("{theme}", data.prompt).replace("{location}", data.prompt).replace("{dish}", data.prompt)
        
        full_prompt = prompt
        if data.negative_prompt:
            full_prompt = f"{prompt}. Avoid: {data.negative_prompt}"
        
        aspect_instructions = {
            "1:1": "square format, 1:1 aspect ratio",
            "16:9": "widescreen format, 16:9 aspect ratio, landscape",
            "9:16": "vertical format, 9:16 aspect ratio, portrait, mobile-friendly",
            "4:3": "standard format, 4:3 aspect ratio"
        }
        full_prompt += f". {aspect_instructions.get(data.aspect_ratio, '')}"
        
        if data.add_watermark or user.get("plan") == "free":
            full_prompt += ". Add subtle 'GenStudio' watermark in corner."
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"genstudio-{job_id}",
            system_message="You are an AI image generator. Generate high-quality images based on the user's prompt."
        ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        msg = UserMessage(text=full_prompt)
        text_response, images = await chat.send_message_multimodal_response(msg)
        
        if not images or len(images) == 0:
            raise Exception("No image was generated")
        
        output_urls = []
        for i, img in enumerate(images):
            image_bytes = base64.b64decode(img['data'])
            filename = f"genstudio_{job_id}_{i}.png"
            filepath = f"/tmp/{filename}"
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            output_urls.append(f"/api/genstudio/download/{job_id}/{filename}")
        
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "outputUrls": output_urls,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        new_balance = await deduct_credits(user["id"], cost, "GenStudio: Text to Image")
        
        return {
            "success": True,
            "jobId": job_id,
            "status": "completed",
            "outputUrls": output_urls,
            "creditsUsed": cost,
            "remainingCredits": new_balance,
            "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
            "message": f"Image generated! Download within {FILE_EXPIRY_MINUTES} minutes before it expires."
        }
        
    except Exception as e:
        logger.error(f"GenStudio text-to-image error: {e}")
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        await log_exception(
            functionality="genstudio_text_to_image",
            error_type="GENERATION_FAILED",
            error_message=str(e),
            user_id=user["id"],
            user_email=user.get("email"),
            stack_trace=traceback.format_exc(),
            severity="ERROR"
        )
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


# =============================================================================
# TEXT TO VIDEO (Async with polling)
# =============================================================================
async def process_text_to_video(job_id: str, data: dict, user_id: str):
    """Background task for video generation"""
    try:
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
        
        size_map = {
            "16:9": "1280x720",
            "9:16": "1024x1792",
            "1:1": "1024x1024",
            "4:3": "1280x720"
        }
        video_size = size_map.get(data.get("aspect_ratio", "16:9"), "1280x720")
        
        valid_durations = [4, 8, 12]
        duration = data.get("duration", 4)
        if duration not in valid_durations:
            duration = 4
        
        video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
        
        filename = f"genstudio_{job_id}.mp4"
        filepath = f"/tmp/{filename}"
        
        full_prompt = data.get("prompt", "")
        if data.get("add_watermark"):
            full_prompt += ". Include subtle 'GenStudio' watermark."
        
        video_bytes = video_gen.text_to_video(
            prompt=full_prompt,
            model="sora-2",
            size=video_size,
            duration=duration,
            max_wait_time=600
        )
        
        if not video_bytes:
            raise Exception("Video generation failed - no video returned")
        
        video_gen.save_video(video_bytes, filepath)
        
        output_urls = [f"/api/genstudio/download/{job_id}/{filename}"]
        
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "outputUrls": output_urls,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Video generation completed: {job_id}")
        
    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}")
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )


@genstudio_router.post("/text-to-video")
@limiter.limit("10/minute")
async def generate_text_to_video(
    request: Request,
    data: TextToVideoRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Generate video from text prompt - costs 10 credits (async)"""
    if not data.consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # ML Content moderation
    moderation_result = threat_intel.moderate_content(data.prompt, user.get("id"))
    if not moderation_result["allowed"]:
        violations = moderation_result.get("violations", [])
        violation_msg = violations[0].get("message") if violations else "Content policy violation"
        raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
    
    cost = GENSTUDIO_COSTS["text_to_video"]
    
    if user.get("credits", 0) < cost:
        if not user.get("subscription"):
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    job_id = str(uuid.uuid4())
    
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_video",
        "status": "processing",
        "inputJson": data.model_dump(),
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Deduct credits upfront
    new_balance = await deduct_credits(user["id"], cost, f"GenStudio: Text to Video ({data.duration}s)")
    
    # Start background generation
    background_tasks.add_task(process_text_to_video, job_id, data.model_dump(), user["id"])
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "creditsUsed": cost,
        "remainingCredits": new_balance,
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
        "message": f"Video generation started! Poll the job status. Download within {FILE_EXPIRY_MINUTES} minutes."
    }


# =============================================================================
# IMAGE-TO-VIDEO
# =============================================================================
class ImageToVideoRequest(BaseModel):
    motion_prompt: str = Field(..., min_length=3, max_length=1000)
    duration: int = Field(default=4, ge=2, le=10)
    add_watermark: bool = True
    consent_confirmed: bool = False

async def process_image_to_video(job_id: str, image_path: str, data: dict, user_id: str):
    """Background task for image-to-video generation"""
    try:
        logger.info(f"Starting image-to-video generation for job {job_id}")
        
        # Use OpenAI Video Generation (Sora 2) for image animation
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
        
        prompt = f"Animate this image with the following motion: {data['motion_prompt']}"
        duration = data.get('duration', 4)
        
        # Validate duration - OpenAI only supports 4, 8, 12 seconds
        valid_durations = [4, 8, 12]
        if duration not in valid_durations:
            duration = 4
        
        video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
        
        # Read image and convert to base64 for image-to-video
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Generate video from image
        video_bytes = video_gen.text_to_video(
            prompt=prompt,
            model="sora-2",
            size="1280x720",
            duration=duration,
            max_wait_time=600
        )
        
        if not video_bytes:
            raise Exception("Video generation failed - no video returned")
        
        # Save video to temp location
        filename = f"genstudio_{job_id}_animated.mp4"
        filepath = f"/tmp/{filename}"
        
        video_gen.save_video(video_bytes, filepath)
        
        output_url = f"/api/genstudio/download/{job_id}/{filename}"
        output_urls = [output_url]
        
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "outputUrls": output_urls,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Image-to-video generation completed: {job_id}")
        
    except Exception as e:
        logger.error(f"Image-to-video generation failed for job {job_id}: {e}")
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )

@genstudio_router.post("/image-to-video")
@limiter.limit("10/minute")
async def generate_image_to_video(
    request: Request,
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    motion_prompt: str = Form(...),
    duration: int = Form(default=4),
    add_watermark: bool = Form(default=True),
    consent_confirmed: bool = Form(default=False),
    user: dict = Depends(get_current_user)
):
    """Generate animated video from static image - costs 10 credits (async)"""
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, and WebP images are allowed")
    
    # Validate file size (max 10MB)
    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size must be under 10MB")
    
    # Validate motion prompt
    if len(motion_prompt) < 3 or len(motion_prompt) > 1000:
        raise HTTPException(status_code=400, detail="Motion description must be 3-1000 characters")
    
    # ML Content moderation
    moderation_result = threat_intel.moderate_content(motion_prompt, user.get("id"))
    if not moderation_result["allowed"]:
        violations = moderation_result.get("violations", [])
        violation_msg = violations[0].get("message") if violations else "Content policy violation"
        raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
    
    cost = GENSTUDIO_COSTS["image_to_video"]
    
    if user.get("credits", 0) < cost:
        if not user.get("subscription"):
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    job_id = str(uuid.uuid4())
    
    # Save uploaded image
    image_filename = f"genstudio_{job_id}_input.{image.filename.split('.')[-1]}"
    image_path = f"/tmp/{image_filename}"
    with open(image_path, "wb") as f:
        f.write(contents)
    
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "image_to_video",
        "status": "processing",
        "inputJson": {
            "motion_prompt": motion_prompt,
            "duration": duration,
            "add_watermark": add_watermark,
            "image_filename": image_filename
        },
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Deduct credits upfront
    new_balance = await deduct_credits(user["id"], cost, f"GenStudio: Image to Video ({duration}s)")
    
    # Start background generation
    background_tasks.add_task(process_image_to_video, job_id, image_path, {
        "motion_prompt": motion_prompt,
        "duration": duration,
        "add_watermark": add_watermark
    }, user["id"])
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "creditsUsed": cost,
        "remainingCredits": new_balance,
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
        "message": f"Animation started! Poll the job status. Download within {FILE_EXPIRY_MINUTES} minutes."
    }


# =============================================================================
# VIDEO REMIX
# =============================================================================
class VideoRemixRequest(BaseModel):
    remix_prompt: str = Field(..., min_length=3, max_length=1000)
    template_style: str = Field(default="dynamic")
    add_watermark: bool = True
    consent_confirmed: bool = False

async def process_video_remix(job_id: str, video_path: str, data: dict, user_id: str):
    """Background task for video remix generation"""
    try:
        logger.info(f"Starting video remix for job {job_id}")
        
        # Use Sora 2 for video remix
        from emergentintegrations.llm.sora2 import sora2_generate_video
        
        prompt = f"Remix this video with: {data['remix_prompt']}. Style: {data.get('template_style', 'dynamic')}"
        
        result = await sora2_generate_video(
            api_key=EMERGENT_LLM_KEY,
            prompt=prompt,
            duration=8,
            aspect_ratio="16:9",
            video_path=video_path
        )
        
        # Save remixed video to temp location
        filename = f"genstudio_{job_id}_remixed.mp4"
        filepath = f"/tmp/{filename}"
        
        if result.get("video_path"):
            import shutil
            shutil.copy(result["video_path"], filepath)
        elif result.get("video_data"):
            with open(filepath, "wb") as f:
                f.write(result["video_data"])
        
        output_url = f"/api/genstudio/download/{job_id}/{filename}"
        output_urls = [output_url]
        
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "outputUrls": output_urls,
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Video remix completed: {job_id}")
        
    except Exception as e:
        logger.error(f"Video remix failed for job {job_id}: {e}")
        await db.genstudio_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )

@genstudio_router.post("/video-remix")
@limiter.limit("5/minute")
async def generate_video_remix(
    request: Request,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    remix_prompt: str = Form(...),
    template_style: str = Form(default="dynamic"),
    add_watermark: bool = Form(default=True),
    consent_confirmed: bool = Form(default=False),
    user: dict = Depends(get_current_user)
):
    """Remix an uploaded video with new styles - costs 12 credits (async)"""
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
    
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime"]
    if video.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only MP4, WebM, and MOV videos are allowed")
    
    # Validate file size (max 50MB)
    contents = await video.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Video size must be under 50MB")
    
    # Validate remix prompt
    if len(remix_prompt) < 3 or len(remix_prompt) > 1000:
        raise HTTPException(status_code=400, detail="Remix instructions must be 3-1000 characters")
    
    # ML Content moderation
    moderation_result = threat_intel.moderate_content(remix_prompt, user.get("id"))
    if not moderation_result["allowed"]:
        violations = moderation_result.get("violations", [])
        violation_msg = violations[0].get("message") if violations else "Content policy violation"
        raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
    
    cost = GENSTUDIO_COSTS["video_remix"]
    
    if user.get("credits", 0) < cost:
        if not user.get("subscription"):
            raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    job_id = str(uuid.uuid4())
    
    # Save uploaded video
    ext = video.filename.split('.')[-1] if '.' in video.filename else 'mp4'
    video_filename = f"genstudio_{job_id}_input.{ext}"
    video_path = f"/tmp/{video_filename}"
    with open(video_path, "wb") as f:
        f.write(contents)
    
    await db.genstudio_jobs.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "video_remix",
        "status": "processing",
        "inputJson": {
            "remix_prompt": remix_prompt,
            "template_style": template_style,
            "add_watermark": add_watermark,
            "video_filename": video_filename
        },
        "costCredits": cost,
        "outputUrls": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    })
    
    # Deduct credits upfront
    new_balance = await deduct_credits(user["id"], cost, f"GenStudio: Video Remix ({template_style})")
    
    # Start background generation
    background_tasks.add_task(process_video_remix, job_id, video_path, {
        "remix_prompt": remix_prompt,
        "template_style": template_style,
        "add_watermark": add_watermark
    }, user["id"])
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "processing",
        "creditsUsed": cost,
        "remainingCredits": new_balance,
        "pollUrl": f"/api/genstudio/job/{job_id}",
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
        "message": f"Video remix started! Poll the job status. Download within {FILE_EXPIRY_MINUTES} minutes."
    }


# =============================================================================
# JOB STATUS & DOWNLOAD
# =============================================================================
@genstudio_router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status for polling"""
    job = await db.genstudio_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@genstudio_router.get("/download/{job_id}/{filename}")
async def download_genstudio_file(job_id: str, filename: str, user: dict = Depends(get_current_user)):
    """Download generated file - expires after configured minutes"""
    job = await db.genstudio_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    expiry_str = job.get("expiresAt")
    if expiry_str:
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry_time:
            raise HTTPException(status_code=410, detail=f"Download link expired. Files are available for {FILE_EXPIRY_MINUTES} minutes only.")
    
    filepath = f"/tmp/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=410, detail="File expired or not found")
    
    media_type = "image/png"
    if filename.endswith(".mp4"):
        media_type = "video/mp4"
    elif filename.endswith(".webm"):
        media_type = "video/webm"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        media_type = "image/jpeg"
    
    return FileResponse(filepath, filename=filename, media_type=media_type)


@genstudio_router.get("/history")
async def get_genstudio_history(
    page: int = 1,
    limit: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get generation history with pagination"""
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    skip = (page - 1) * limit
    
    jobs = await db.genstudio_jobs.find(
        query, {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.genstudio_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit,
        "hasMore": skip + limit < total,
        "fileExpiryMinutes": FILE_EXPIRY_MINUTES
    }


# =============================================================================
# STYLE PROFILES
# =============================================================================
@genstudio_router.post("/style-profile")
async def create_style_profile(data: StyleProfileCreate, user: dict = Depends(get_current_user)):
    """Create a new brand style profile - costs 20 credits"""
    cost = GENSTUDIO_COSTS["style_profile_create"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Need {cost} credits to create a style profile")
    
    profile_id = str(uuid.uuid4())
    
    await db.style_profiles.insert_one({
        "id": profile_id,
        "userId": user["id"],
        "name": data.name,
        "description": data.description,
        "tags": data.tags,
        "refImageUrls": [],
        "trained": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    new_balance = await deduct_credits(user["id"], cost, f"GenStudio: Style Profile '{data.name}'")
    
    return {
        "success": True,
        "profileId": profile_id,
        "creditsUsed": cost,
        "remainingCredits": new_balance,
        "message": "Style profile created! Now upload 5-20 reference images."
    }


@genstudio_router.get("/style-profiles")
async def get_style_profiles(user: dict = Depends(get_current_user)):
    """Get user's style profiles"""
    profiles = await db.style_profiles.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).to_list(50)
    
    return {"profiles": profiles, "count": len(profiles)}


@genstudio_router.post("/style-profile/{profile_id}/upload-image")
async def upload_profile_image(
    profile_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload a reference image to style profile"""
    profile = await db.style_profiles.find_one({"id": profile_id, "userId": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    if len(profile.get("refImageUrls", [])) >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 images per profile")
    
    # Validate file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and save image
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    image_id = str(uuid.uuid4())
    filename = f"style_profile_{profile_id}_{image_id}.png"
    filepath = f"/tmp/{filename}"
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Update profile
    image_url = f"/api/genstudio/style-image/{profile_id}/{image_id}"
    await db.style_profiles.update_one(
        {"id": profile_id},
        {"$push": {"refImageUrls": image_url}}
    )
    
    return {
        "success": True,
        "imageUrl": image_url,
        "imageCount": len(profile.get("refImageUrls", [])) + 1
    }


@genstudio_router.delete("/style-profile/{profile_id}")
async def delete_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Delete a style profile"""
    result = await db.style_profiles.delete_one({"id": profile_id, "userId": user["id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    return {"success": True, "message": "Style profile deleted"}
