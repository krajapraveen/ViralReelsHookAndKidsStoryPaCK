"""
GenStudio Router - AI Generation Suite
Text-to-Image, Text-to-Video, Image-to-Video, Video Remix, Style Profiles
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import os
import base64
import logging

logger = logging.getLogger(__name__)

# Router
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


def setup_genstudio_routes(router: APIRouter, db, get_current_user, LLM_AVAILABLE: bool, EMERGENT_LLM_KEY: str):
    """Setup GenStudio routes with dependencies injected from server.py"""
    
    @router.get("/dashboard")
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
            "costs": GENSTUDIO_COSTS
        }

    @router.get("/templates")
    async def get_templates():
        """Get prompt templates"""
        return {"templates": GENSTUDIO_TEMPLATES}

    @router.post("/text-to-image")
    async def generate_text_to_image(data: TextToImageRequest, user: dict = Depends(get_current_user)):
        """Generate image from text prompt using Gemini - costs 10 credits"""
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        if not data.consent_confirmed:
            raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
        
        prohibited_terms = ["celebrity", "famous person", "real person", "deepfake", "face swap"]
        prompt_lower = data.prompt.lower()
        for term in prohibited_terms:
            if term in prompt_lower:
                raise HTTPException(status_code=400, detail=f"Prohibited content detected: {term}. We don't allow identity cloning.")
        
        cost = GENSTUDIO_COSTS["text_to_image"]
        
        if user.get("credits", 0) < cost:
            user_subscription = user.get("subscription")
            if not user_subscription:
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
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        })
        
        try:
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
            )
            chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
            
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
            
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"credits": -cost}}
            )
            
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "amount": -cost,
                "type": "USAGE",
                "description": "GenStudio: Text to Image",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "jobId": job_id,
                "status": "completed",
                "outputUrls": output_urls,
                "creditsUsed": cost,
                "remainingCredits": user["credits"] - cost,
                "expiresIn": "15 minutes",
                "message": "Image generated! Download within 15 minutes before it expires."
            }
            
        except Exception as e:
            logger.error(f"GenStudio text-to-image error: {e}")
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

    @router.post("/text-to-video")
    async def generate_text_to_video(data: TextToVideoRequest, user: dict = Depends(get_current_user)):
        """Generate video from text prompt using Sora 2 - costs 10 credits"""
        from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
        
        if not data.consent_confirmed:
            raise HTTPException(status_code=400, detail="Please confirm you have rights/consent for this content")
        
        prohibited_terms = ["celebrity", "famous person", "real person", "deepfake", "face swap"]
        prompt_lower = data.prompt.lower()
        for term in prohibited_terms:
            if term in prompt_lower:
                raise HTTPException(status_code=400, detail=f"Prohibited content detected: {term}. We don't allow identity cloning.")
        
        cost = GENSTUDIO_COSTS["text_to_video"]
        
        if user.get("credits", 0) < cost:
            user_subscription = user.get("subscription")
            if not user_subscription:
                raise HTTPException(status_code=402, detail="You've used all your free credits! Please subscribe to continue.")
            raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
        
        job_id = str(uuid.uuid4())
        
        size_map = {
            "16:9": "1280x720",
            "9:16": "1024x1792",
            "1:1": "1024x1024",
            "4:3": "1280x720"
        }
        video_size = size_map.get(data.aspect_ratio, "1280x720")
        
        valid_durations = [4, 8, 12]
        duration = data.duration if data.duration in valid_durations else 4
        
        await db.genstudio_jobs.insert_one({
            "id": job_id,
            "userId": user["id"],
            "type": "text_to_video",
            "status": "processing",
            "inputJson": data.model_dump(),
            "costCredits": cost,
            "outputUrls": [],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        })
        
        try:
            video_gen = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)
            
            filename = f"genstudio_{job_id}.mp4"
            filepath = f"/tmp/{filename}"
            
            full_prompt = data.prompt
            if data.add_watermark or user.get("plan") == "free":
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
            
            await db.users.update_one(
                {"id": user["id"]},
                {"$inc": {"credits": -cost}}
            )
            
            await db.credit_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "userId": user["id"],
                "amount": -cost,
                "type": "USAGE",
                "description": f"GenStudio: Text to Video ({duration}s)",
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "jobId": job_id,
                "status": "completed",
                "outputUrls": output_urls,
                "creditsUsed": cost,
                "remainingCredits": user["credits"] - cost,
                "expiresIn": "15 minutes",
                "message": f"Video generated! Download within 15 minutes before it expires."
            }
            
        except Exception as e:
            logger.error(f"GenStudio text-to-video error: {e}")
            await db.genstudio_jobs.update_one(
                {"id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
            raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

    @router.get("/download/{job_id}/{filename}")
    async def download_genstudio_file(job_id: str, filename: str, user: dict = Depends(get_current_user)):
        """Download generated file - expires after 15 minutes"""
        job = await db.genstudio_jobs.find_one({"id": job_id, "userId": user["id"]}, {"_id": 0})
        if not job:
            raise HTTPException(status_code=404, detail="File not found or expired")
        
        expiry_str = job.get("expiresAt")
        if expiry_str:
            expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry_time:
                raise HTTPException(status_code=410, detail="Download link expired. Files are available for 15 minutes only.")
        
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

    @router.get("/history")
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
            "hasMore": skip + limit < total
        }

    @router.post("/style-profile")
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
        
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": -cost}}
        )
        
        await db.credit_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user["id"],
            "amount": -cost,
            "type": "USAGE",
            "description": f"GenStudio: Style Profile '{data.name}'",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "profileId": profile_id,
            "creditsUsed": cost,
            "remainingCredits": user["credits"] - cost,
            "message": "Style profile created! Now upload 10-20 reference images."
        }

    @router.get("/style-profiles")
    async def get_style_profiles(user: dict = Depends(get_current_user)):
        """Get user's style profiles"""
        profiles = await db.style_profiles.find(
            {"userId": user["id"]},
            {"_id": 0}
        ).to_list(50)
        
        return {"profiles": profiles, "count": len(profiles)}

    @router.delete("/style-profile/{profile_id}")
    async def delete_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
        """Delete a style profile"""
        result = await db.style_profiles.delete_one({"id": profile_id, "userId": user["id"]})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Style profile not found")
        
        return {"success": True, "message": "Style profile deleted"}

    @router.get("/job/{job_id}")
    async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
        """Get job status"""
        job = await db.genstudio_jobs.find_one(
            {"id": job_id, "userId": user["id"]},
            {"_id": 0}
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
    
    return router
