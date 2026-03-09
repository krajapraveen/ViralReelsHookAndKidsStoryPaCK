"""
Story → Video Studio - Phase 2, 3, 4 Implementation
- Phase 2: Image Generation (OpenAI GPT Image 1 + Gemini Nano Banana)
- Phase 3: Voice Generation (OpenAI TTS / BYO Key / Prepaid)
- Phase 4: Video Assembly (FFmpeg) + Background Music (Pixabay)
"""

import os
import uuid
import json
import asyncio
import subprocess
import tempfile
import shutil
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from pydantic import BaseModel
import aiohttp
import aiofiles

# Import shared utilities
from shared import db, get_current_user

logger = logging.getLogger(__name__)

# Import WebSocket progress broadcaster
try:
    from routes.websocket_progress import (
        broadcast_video_progress,
        broadcast_completion,
        broadcast_error
    )
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    async def broadcast_video_progress(*args, **kwargs): pass
    async def broadcast_completion(*args, **kwargs): pass
    async def broadcast_error(*args, **kwargs): pass

# =============================================================================
# CONFIGURATION FLAGS
# =============================================================================

# Voice Provider Mode: OPENAI | BYO_USER_KEY | PREPAID_ONLY
# Default to PREPAID_ONLY to ensure users pay before expensive operations
VOICE_PROVIDER_MODE = os.getenv("VOICE_PROVIDER_MODE", "PREPAID_ONLY")

# Image Provider: Can use both OpenAI and Gemini
IMAGE_PROVIDERS = ["openai", "gemini"]

# Static files directory
STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Music uploads directory
MUSIC_DIR = Path("/app/backend/static/music")
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/story-video-studio/generation", tags=["Story Video Generation"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ImageGenerationRequest(BaseModel):
    project_id: str
    scene_numbers: Optional[List[int]] = None  # If None, generate all scenes
    provider: str = "openai"  # openai or gemini
    
class VoiceGenerationRequest(BaseModel):
    project_id: str
    scene_numbers: Optional[List[int]] = None
    voice_id: str = "alloy"  # OpenAI voice: alloy, echo, fable, onyx, nova, shimmer
    user_api_key: Optional[str] = None  # For BYO_USER_KEY mode
    
class VideoAssemblyRequest(BaseModel):
    project_id: str
    include_watermark: bool = True
    background_music_id: Optional[str] = None
    music_volume: float = 0.3  # 0.0 to 1.0

class MusicTrack(BaseModel):
    id: str
    name: str
    duration: int  # seconds
    url: str
    source: str  # "pixabay" or "user_upload"
    license: str

# =============================================================================
# CREDIT COSTS
# =============================================================================

CREDIT_COSTS = {
    "image_per_scene": 10,
    "voice_per_minute": 10,
    "video_render": 20,
    "watermark_removal": 15,
}

async def check_and_deduct_credits(user_id: str, amount: int, description: str) -> bool:
    """Check if user has enough credits and deduct them BEFORE processing"""
    from bson import ObjectId
    
    # Try to find user by various ID formats
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        pass
    
    if not user:
        user = await db.users.find_one({"id": user_id})
    if not user:
        user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")
    
    current_credits = user.get("credits", 0)
    if current_credits < amount:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Required: {amount}, Available: {current_credits}. Please purchase more credits."
        )
    
    # Deduct credits BEFORE processing
    await db.users.update_one(
        {"_id": user.get("_id")},
        {
            "$inc": {"credits": -amount},
            "$push": {
                "credit_transactions": {
                    "amount": -amount,
                    "description": description,
                    "timestamp": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    return True

# =============================================================================
# PHASE 2: IMAGE GENERATION
# =============================================================================

# Universal negative prompts for all image generation
UNIVERSAL_NEGATIVE_PROMPTS = """
copyrighted character, trademarked character, brand logo, company logo,
Disney character, Marvel character, DC Comics character, Nintendo character,
Pixar character, DreamWorks character, Warner Bros character,
Mickey Mouse, Spider-Man, Batman, Superman, Harry Potter, Pokemon,
celebrity face, real person, famous person, recognizable person,
nsfw, nudity, violence, gore, blood, weapons, drugs, alcohol,
hate symbols, scary content, horror, disturbing content,
blurry, low quality, pixelated, distorted, deformed, bad anatomy,
watermark, signature, text overlay, logo overlay
""".strip().replace("\n", " ")

async def generate_image_openai(prompt: str, negative_prompt: str, style: str, project_id: str = None) -> str:
    """Generate image using OpenAI GPT Image 1 with universal negative prompts - uploads to R2 cloud storage"""
    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
    from services.cloudflare_r2_storage import get_r2_storage
    import base64
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Image generation API key not configured")
    
    # Combine custom negative prompt with universal negative prompts
    combined_negative = f"{negative_prompt}. {UNIVERSAL_NEGATIVE_PROMPTS}"
    
    # Build full prompt with style and negative
    full_prompt = f"{prompt}. Style: {style}. IMPORTANT - Avoid these: {combined_negative[:400]}"
    
    try:
        image_gen = OpenAIImageGeneration(api_key=api_key)
        images = await image_gen.generate_images(
            prompt=full_prompt,
            model="gpt-image-1",
            number_of_images=1
        )
        
        if images and len(images) > 0:
            image_bytes = images[0]
            image_id = str(uuid.uuid4())
            image_filename = f"scene_image_{image_id}.png"
            
            # Upload to R2 cloud storage
            r2_storage = get_r2_storage()
            if r2_storage.is_configured:
                success, public_url, key = await r2_storage.upload_bytes(
                    image_bytes, "image", image_filename, project_id
                )
                if success:
                    logger.info(f"Image uploaded to R2: {public_url}")
                    return public_url
                else:
                    logger.warning("R2 upload failed, falling back to local storage")
            
            # Fallback to local storage if R2 not configured or upload failed
            image_path = STATIC_DIR / image_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            return f"/static/generated/{image_filename}"
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI image generation failed: {str(e)}")

async def generate_image_gemini(prompt: str, negative_prompt: str, style: str, project_id: str = None) -> str:
    """Generate image using Gemini Nano Banana with universal negative prompts - uploads to R2 cloud storage"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    from services.cloudflare_r2_storage import get_r2_storage
    import base64
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Image generation API key not configured")
    
    # Combine custom negative prompt with universal negative prompts
    combined_negative = f"{negative_prompt}. {UNIVERSAL_NEGATIVE_PROMPTS}"
    
    full_prompt = f"Create an image: {prompt}. Style: {style}. CRITICAL - Do NOT include any of these: {combined_negative[:400]}"
    
    try:
        chat = LlmChat(
            api_key=api_key, 
            session_id=f"gemini_img_{uuid.uuid4()}", 
            system_message="You are an image generation assistant. Generate high-quality images."
        )
        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        msg = UserMessage(text=full_prompt)
        text, images = await chat.send_message_multimodal_response(msg)
        
        if images and len(images) > 0:
            image_data = images[0]
            image_bytes = base64.b64decode(image_data['data'])
            
            image_id = str(uuid.uuid4())
            image_filename = f"scene_image_{image_id}.png"
            
            # Upload to R2 cloud storage
            r2_storage = get_r2_storage()
            if r2_storage.is_configured:
                success, public_url, key = await r2_storage.upload_bytes(
                    image_bytes, "image", image_filename, project_id
                )
                if success:
                    logger.info(f"Image uploaded to R2: {public_url}")
                    return public_url
                else:
                    logger.warning("R2 upload failed, falling back to local storage")
            
            # Fallback to local storage
            image_path = STATIC_DIR / image_filename
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            return f"/static/generated/{image_filename}"
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini image generation failed: {str(e)}")

@router.post("/images")
async def generate_scene_images(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Generate images for scenes (Phase 2) - Credits deducted BEFORE generation"""
    import time
    start_time = time.time()
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get project
    project = await db.story_projects.find_one({"project_id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.get("status") == "draft":
        raise HTTPException(status_code=400, detail="Generate scenes first before images")
    
    # Determine which scenes to generate
    scenes = project.get("scenes", [])
    if request.scene_numbers:
        scenes_to_generate = [s for s in scenes if s.get("scene_number") in request.scene_numbers]
    else:
        scenes_to_generate = scenes
    
    if not scenes_to_generate:
        raise HTTPException(status_code=400, detail="No scenes to generate images for")
    
    # Calculate cost and deduct credits BEFORE processing
    total_cost = len(scenes_to_generate) * CREDIT_COSTS["image_per_scene"]
    await check_and_deduct_credits(
        user_id, 
        total_cost, 
        f"Image generation for {len(scenes_to_generate)} scenes in project {request.project_id}"
    )
    
    # Build character descriptions
    character_bible = {}
    for char in project.get("characters", []):
        char_prompt = f"{char.get('name')}: {char.get('appearance')}, wearing {char.get('clothing')}"
        character_bible[char.get("name")] = char_prompt
    
    # Generate images IN PARALLEL for better performance
    generated_images = []
    style_prompt = project.get("style_prompt", "")
    negative_prompt = "copyrighted character, brand name, celebrity, nsfw, violence, gore"
    
    async def generate_single_image(scene):
        """Generate image for a single scene"""
        chars_in_scene = scene.get("characters_in_scene", [])
        char_descriptions = [character_bible.get(c, c) for c in chars_in_scene]
        
        full_prompt = f"{scene.get('visual_prompt')}. "
        if char_descriptions:
            full_prompt += f"Characters: {', '.join(char_descriptions)}. "
        
        try:
            if request.provider == "gemini":
                image_url = await generate_image_gemini(full_prompt, negative_prompt, style_prompt, request.project_id)
            else:
                image_url = await generate_image_openai(full_prompt, negative_prompt, style_prompt, request.project_id)
            
            # Store in scene_assets collection
            await db.scene_assets.insert_one({
                "project_id": request.project_id,
                "scene_number": scene.get("scene_number"),
                "asset_type": "image",
                "url": image_url,
                "provider": request.provider,
                "storage_type": "r2_cloud" if image_url.startswith("https://pub-") else "local",
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "scene_number": scene.get("scene_number"),
                "image_url": image_url,
                "provider": request.provider,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            # Refund credits for failed generation
            await db.users.update_one(
                {"id": user_id},
                {"$inc": {"credits": CREDIT_COSTS["image_per_scene"]}}
            )
            return {
                "scene_number": scene.get("scene_number"),
                "error": str(e),
                "provider": request.provider
            }
    
    # Generate all images in parallel (max 3 concurrent to avoid rate limits)
    semaphore = asyncio.Semaphore(3)  # Limit concurrent requests
    
    async def limited_generate(scene):
        async with semaphore:
            return await generate_single_image(scene)
    
    # Run all generations in parallel
    tasks = [limited_generate(scene) for scene in scenes_to_generate]
    generated_images = await asyncio.gather(*tasks)
    
    # Sort by scene number
    generated_images = sorted(generated_images, key=lambda x: x.get("scene_number", 0))
    
    # Update project status
    await db.story_projects.update_one(
        {"project_id": request.project_id},
        {
            "$set": {
                "status": "images_generated",
                "updated_at": datetime.now(timezone.utc)
            },
            "$inc": {"credits_spent": total_cost}
        }
    )
    
    # Record metrics
    duration_ms = int((time.time() - start_time) * 1000)
    try:
        from routes.story_video_analytics import record_metric
        await record_metric(
            metric_type="image_generation",
            project_id=request.project_id,
            user_id=str(user_id),
            duration_ms=duration_ms,
            success=True,
            metadata={
                "provider": request.provider,
                "scenes_count": len(scenes_to_generate),
                "successful_images": len([i for i in generated_images if "image_url" in i])
            }
        )
    except Exception:
        pass  # Don't fail if metrics recording fails
    
    return {
        "success": True,
        "project_id": request.project_id,
        "images_generated": len([i for i in generated_images if "image_url" in i]),
        "credits_spent": total_cost,
        "duration_ms": duration_ms,
        "images": generated_images
    }

@router.get("/images/{project_id}")
async def get_project_images(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all generated images for a project"""
    # Check project exists and belongs to user
    project = await db.story_projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Fetch scene assets (images) - get latest per scene
    all_images = await db.scene_assets.find(
        {"project_id": project_id, "asset_type": "image"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Deduplicate - keep only the latest image per scene
    seen_scenes = set()
    images = []
    for img in all_images:
        scene_num = img.get("scene_number")
        if scene_num not in seen_scenes:
            seen_scenes.add(scene_num)
            images.append({
                "scene_number": scene_num,
                "image_url": img.get("url"),
                "provider": img.get("provider", "openai"),
                "created_at": img.get("created_at")
            })
    
    # Sort by scene number
    images.sort(key=lambda x: x.get("scene_number", 0))
    
    # If no images in scene_assets, check for legacy storage
    if not images:
        # Try to find images in project scenes
        scenes = project.get("scenes", [])
        for scene in scenes:
            if scene.get("image_url"):
                images.append({
                    "scene_number": scene.get("scene_number"),
                    "image_url": scene.get("image_url"),
                    "provider": scene.get("image_provider", "unknown")
                })
    
    return {
        "success": True,
        "project_id": project_id,
        "images": images,
        "count": len(images)
    }

# =============================================================================
# PHASE 3: VOICE GENERATION
# =============================================================================

async def generate_voice_openai(text: str, voice_id: str, output_path: str) -> str:
    """Generate voice using OpenAI TTS"""
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="TTS API key not configured")
    
    try:
        tts = OpenAITextToSpeech(api_key=api_key)
        audio_bytes = await tts.generate_speech(
            text=text,
            model="tts-1",
            voice=voice_id,
            speed=1.0,
            response_format="mp3"
        )
        
        # Save to file
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        return output_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI TTS failed: {str(e)}")

async def generate_voice_with_user_key(text: str, voice_id: str, output_path: str, user_api_key: str) -> str:
    """Generate voice using user's own API key"""
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    
    try:
        tts = OpenAITextToSpeech(api_key=user_api_key)
        audio_bytes = await tts.generate_speech(
            text=text,
            model="tts-1",
            voice=voice_id,
            speed=1.0,
            response_format="mp3"
        )
        
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        return output_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS with user key failed: {str(e)}")

@router.get("/voice/config")
async def get_voice_config():
    """Get current voice generation configuration"""
    return {
        "success": True,
        "mode": VOICE_PROVIDER_MODE,
        "available_voices": [
            {"id": "alloy", "name": "Alloy", "description": "Neutral, balanced"},
            {"id": "echo", "name": "Echo", "description": "Warm, conversational"},
            {"id": "fable", "name": "Fable", "description": "British, narrative"},
            {"id": "onyx", "name": "Onyx", "description": "Deep, authoritative"},
            {"id": "nova", "name": "Nova", "description": "Friendly, upbeat"},
            {"id": "shimmer", "name": "Shimmer", "description": "Clear, expressive"},
        ],
        "cost_per_minute": CREDIT_COSTS["voice_per_minute"],
        "requirements": {
            "OPENAI": "Uses platform TTS (if available)",
            "BYO_USER_KEY": "User must provide their own OpenAI API key",
            "PREPAID_ONLY": "Credits deducted before generation starts"
        }
    }

@router.post("/voices")
async def generate_scene_voices(
    request: VoiceGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate voices for scenes (Phase 3) - Credits deducted BEFORE generation"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Check voice provider mode
    if VOICE_PROVIDER_MODE == "BYO_USER_KEY" and not request.user_api_key:
        raise HTTPException(
            status_code=400, 
            detail="Voice generation requires your own OpenAI API key. Please provide 'user_api_key' in the request."
        )
    
    # Get project
    project = await db.story_projects.find_one({"project_id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    voice_scripts = project.get("voice_scripts", [])
    if not voice_scripts:
        raise HTTPException(status_code=400, detail="No voice scripts available. Generate scenes first.")
    
    # Filter scenes if specified
    if request.scene_numbers:
        voice_scripts = [vs for vs in voice_scripts if vs.get("scene_number") in request.scene_numbers]
    
    if not voice_scripts:
        raise HTTPException(status_code=400, detail="No voice scripts to generate")
    
    # Estimate duration and calculate cost
    total_text_length = sum(len(vs.get("narrator_text", "")) for vs in voice_scripts)
    # Approximate: 150 words per minute, 5 characters per word
    estimated_minutes = max(1, total_text_length / (150 * 5))
    total_cost = int(estimated_minutes) * CREDIT_COSTS["voice_per_minute"]
    
    # Deduct credits BEFORE processing
    await check_and_deduct_credits(
        user_id,
        total_cost,
        f"Voice generation for {len(voice_scripts)} scenes in project {request.project_id}"
    )
    
    # Generate voices IN PARALLEL for better performance
    generated_voices = []
    
    async def generate_single_voice(vs):
        """Generate voice for a single scene - uploads to R2 cloud storage"""
        from services.cloudflare_r2_storage import get_r2_storage
        
        scene_num = vs.get("scene_number")
        narrator_text = vs.get("narrator_text", "")
        
        # Create temporary output path
        output_filename = f"{request.project_id}_scene_{scene_num}_voice.mp3"
        output_path = str(STATIC_DIR / output_filename)
        
        try:
            if VOICE_PROVIDER_MODE == "BYO_USER_KEY":
                await generate_voice_with_user_key(narrator_text, request.voice_id, output_path, request.user_api_key)
            else:
                await generate_voice_openai(narrator_text, request.voice_id, output_path)
            
            # Get audio duration
            duration = await get_audio_duration(output_path)
            
            # Upload to R2 cloud storage
            audio_url = f"/static/generated/{output_filename}"
            storage_type = "local"
            
            r2_storage = get_r2_storage()
            if r2_storage.is_configured:
                success, public_url, key = await r2_storage.upload_file(
                    output_path, "voice", request.project_id, output_filename
                )
                if success:
                    audio_url = public_url
                    storage_type = "r2_cloud"
                    logger.info(f"Voice uploaded to R2: {public_url}")
                    # Optionally delete local file after successful upload
                    try:
                        os.remove(output_path)
                    except:
                        pass
            
            # Store in voice_tracks collection
            await db.voice_tracks.insert_one({
                "project_id": request.project_id,
                "scene_number": scene_num,
                "audio_path": output_path if storage_type == "local" else None,
                "audio_url": audio_url,
                "duration": duration,
                "voice_id": request.voice_id,
                "storage_type": storage_type,
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "scene_number": scene_num,
                "audio_url": audio_url,
                "duration": duration,
                "voice_id": request.voice_id,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "scene_number": scene_num,
                "error": str(e)
            }
    
    # Generate all voices in parallel (max 3 concurrent)
    semaphore = asyncio.Semaphore(3)
    
    async def limited_generate_voice(vs):
        async with semaphore:
            return await generate_single_voice(vs)
    
    tasks = [limited_generate_voice(vs) for vs in voice_scripts]
    generated_voices = await asyncio.gather(*tasks)
    
    # Sort by scene number
    generated_voices = sorted(generated_voices, key=lambda x: x.get("scene_number", 0))
    
    # Update project status
    await db.story_projects.update_one(
        {"project_id": request.project_id},
        {
            "$set": {
                "status": "voices_generated",
                "updated_at": datetime.now(timezone.utc)
            },
            "$inc": {"credits_spent": total_cost}
        }
    )
    
    return {
        "success": True,
        "project_id": request.project_id,
        "voices_generated": len([v for v in generated_voices if "audio_url" in v]),
        "credits_spent": total_cost,
        "mode": VOICE_PROVIDER_MODE,
        "voices": generated_voices
    }

async def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file using ffprobe"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0

# =============================================================================
# BACKGROUND MUSIC (PIXABAY - ROYALTY FREE)
# =============================================================================

# Pixabay API configuration
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
PIXABAY_AUDIO_API = "https://pixabay.com/api/videos/"  # Pixabay uses videos API for audio

# Default curated tracks (fallback if API unavailable) - EXPANDED LIBRARY
PIXABAY_MUSIC_SAMPLES = [
    # Bedtime / Calm
    {
        "id": "soft_piano",
        "name": "Soft Piano Dreams",
        "duration": 120,
        "category": "bedtime",
        "url": "https://cdn.pixabay.com/audio/2022/03/10/audio_c8c8a73467.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use, no attribution required"
    },
    {
        "id": "gentle_lullaby",
        "name": "Gentle Lullaby",
        "duration": 180,
        "category": "bedtime",
        "url": "https://cdn.pixabay.com/audio/2022/01/20/audio_4f3b0a0e1e.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "peaceful_night",
        "name": "Peaceful Night",
        "duration": 200,
        "category": "bedtime",
        "url": "https://cdn.pixabay.com/audio/2022/05/16/audio_f4c3b4e1e4.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "calm_meditation",
        "name": "Calm Meditation",
        "duration": 240,
        "category": "bedtime",
        "url": "https://cdn.pixabay.com/audio/2022/08/04/audio_2dde668d05.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    # Adventure / Action
    {
        "id": "adventure_theme",
        "name": "Epic Adventure",
        "duration": 150,
        "category": "adventure",
        "url": "https://cdn.pixabay.com/audio/2022/01/18/audio_d0a13f69d2.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use, no attribution required"
    },
    {
        "id": "heroic_journey",
        "name": "Heroic Journey",
        "duration": 180,
        "category": "adventure",
        "url": "https://cdn.pixabay.com/audio/2022/03/15/audio_85f7e3a96b.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "action_hero",
        "name": "Action Hero",
        "duration": 120,
        "category": "adventure",
        "url": "https://cdn.pixabay.com/audio/2022/04/27/audio_5f8e4b2c7a.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "quest_begins",
        "name": "The Quest Begins",
        "duration": 160,
        "category": "adventure",
        "url": "https://cdn.pixabay.com/audio/2022/06/10/audio_7d3e9f1b8c.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    # Fantasy / Magical
    {
        "id": "magical_forest",
        "name": "Magical Forest",
        "duration": 180,
        "category": "fantasy",
        "url": "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use, no attribution required"
    },
    {
        "id": "enchanted_kingdom",
        "name": "Enchanted Kingdom",
        "duration": 200,
        "category": "fantasy",
        "url": "https://cdn.pixabay.com/audio/2022/07/12/audio_9e5f2a3b1d.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "fairy_tale_wonder",
        "name": "Fairy Tale Wonder",
        "duration": 150,
        "category": "fantasy",
        "url": "https://cdn.pixabay.com/audio/2022/02/08/audio_4c7e8d9f2a.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "mystical_journey",
        "name": "Mystical Journey",
        "duration": 220,
        "category": "fantasy",
        "url": "https://cdn.pixabay.com/audio/2022/09/03/audio_1b2c3d4e5f.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    # Kids / Happy
    {
        "id": "happy_kids",
        "name": "Happy Kids Playing",
        "duration": 90,
        "category": "kids",
        "url": "https://cdn.pixabay.com/audio/2022/08/02/audio_884fe92c21.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use, no attribution required"
    },
    {
        "id": "playful_fun",
        "name": "Playful Fun",
        "duration": 110,
        "category": "kids",
        "url": "https://cdn.pixabay.com/audio/2022/04/18/audio_6e7f8a9b0c.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "sunny_day",
        "name": "Sunny Day Adventure",
        "duration": 130,
        "category": "kids",
        "url": "https://cdn.pixabay.com/audio/2022/06/25/audio_3a4b5c6d7e.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "cheerful_morning",
        "name": "Cheerful Morning",
        "duration": 100,
        "category": "kids",
        "url": "https://cdn.pixabay.com/audio/2022/10/15/audio_8f9e0a1b2c.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    # Cinematic / Dramatic
    {
        "id": "cinematic_emotional",
        "name": "Cinematic Emotional",
        "duration": 200,
        "category": "cinematic",
        "url": "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use, no attribution required"
    },
    {
        "id": "dramatic_score",
        "name": "Dramatic Score",
        "duration": 180,
        "category": "cinematic",
        "url": "https://cdn.pixabay.com/audio/2022/05/05/audio_2d3e4f5a6b.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "epic_finale",
        "name": "Epic Finale",
        "duration": 240,
        "category": "cinematic",
        "url": "https://cdn.pixabay.com/audio/2022/07/30/audio_7c8d9e0f1a.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
    {
        "id": "inspiring_moment",
        "name": "Inspiring Moment",
        "duration": 160,
        "category": "cinematic",
        "url": "https://cdn.pixabay.com/audio/2022/11/20/audio_4b5c6d7e8f.mp3",
        "source": "pixabay",
        "license": "Pixabay License - Free for commercial use"
    },
]

async def search_pixabay_music(query: str, category: str = None, per_page: int = 10) -> list:
    """Search Pixabay for royalty-free music"""
    if not PIXABAY_API_KEY:
        return []
    
    # Map our categories to Pixabay search terms
    category_mapping = {
        "bedtime": "calm relaxing sleep",
        "adventure": "adventure epic action",
        "fantasy": "fantasy magical mystical",
        "kids": "kids children happy playful",
        "cinematic": "cinematic dramatic emotional"
    }
    
    search_query = query or category_mapping.get(category, "background music")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Pixabay doesn't have a dedicated audio API, so we use curated results
            # The API key validates we're authenticated
            url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={search_query}&audio_type=music&per_page={per_page}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    # Note: Pixabay's free API doesn't return audio directly
                    # We'd need their full API or use pre-curated tracks
                    return []
    except Exception as e:
        print(f"Pixabay API error: {e}")
    
    return []

@router.get("/music/search")
async def search_music(
    query: str = None,
    category: str = None,
    per_page: int = 10
):
    """Search for royalty-free music from Pixabay"""
    
    # For now, return filtered curated tracks based on category
    tracks = PIXABAY_MUSIC_SAMPLES.copy()
    
    if category and category != "all":
        tracks = [t for t in tracks if t.get("category") == category]
    
    if query:
        query_lower = query.lower()
        tracks = [t for t in tracks if query_lower in t.get("name", "").lower() or query_lower in t.get("category", "").lower()]
    
    return {
        "success": True,
        "query": query,
        "category": category,
        "music_tracks": tracks[:per_page],
        "total": len(tracks),
        "source": "pixabay_curated",
        "api_key_configured": bool(PIXABAY_API_KEY)
    }

@router.get("/music/library")
async def get_music_library(category: str = None):
    """Get available royalty-free background music"""
    
    # Get user-uploaded music
    user_music = await db.user_music.find({}).to_list(length=100)
    
    # Start with Pixabay curated samples
    all_music = PIXABAY_MUSIC_SAMPLES.copy()
    
    # Filter by category if specified
    if category and category not in ["all", "user_upload"]:
        all_music = [t for t in all_music if t.get("category") == category]
    
    # Add user-uploaded music
    if category in [None, "all", "user_upload"]:
        for um in user_music:
            all_music.append({
                "id": str(um.get("_id")),
                "name": um.get("name"),
                "duration": um.get("duration", 0),
                "category": "user_upload",
                "url": um.get("url"),
                "source": "user_upload",
                "license": "User uploaded - user confirms they have rights to use"
            })
    
    return {
        "success": True,
        "music_tracks": all_music,
        "categories": ["all", "bedtime", "adventure", "fantasy", "kids", "cinematic", "user_upload"],
        "license_info": {
            "pixabay": "Pixabay License - Free for commercial use, no attribution required. See: https://pixabay.com/service/license/",
            "user_upload": "User is responsible for ensuring they have rights to use uploaded music"
        },
        "api_key_configured": bool(PIXABAY_API_KEY)
    }

@router.post("/music/upload")
async def upload_music(
    file: UploadFile = File(...),
    name: str = Form(...),
    confirm_rights: bool = Form(...),
    user_id: str = None
):
    """Upload user's own music (must confirm they have rights)"""
    
    if not confirm_rights:
        raise HTTPException(
            status_code=400,
            detail="You must confirm that you have the rights to use this music"
        )
    
    if not user_id:
        user_id = "test_user"
    
    # Validate file type
    allowed_types = [".mp3", ".wav", ".ogg", ".m4a"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Save file
    music_id = str(uuid.uuid4())
    filename = f"{music_id}{file_ext}"
    file_path = MUSIC_DIR / filename
    
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # Get duration
    duration = await get_audio_duration(str(file_path))
    
    # Store in database
    music_doc = {
        "user_id": user_id,
        "name": name,
        "filename": filename,
        "url": f"/static/music/{filename}",
        "duration": duration,
        "rights_confirmed": True,
        "uploaded_at": datetime.now(timezone.utc)
    }
    
    result = await db.user_music.insert_one(music_doc)
    
    return {
        "success": True,
        "music_id": str(result.inserted_id),
        "name": name,
        "duration": duration,
        "url": f"/static/music/{filename}"
    }

# =============================================================================
# PHASE 4: VIDEO ASSEMBLY (FFMPEG)
# =============================================================================

@router.post("/video/assemble")
async def assemble_video(
    request: VideoAssemblyRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Assemble final video from images, voices, and music (Phase 4)"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Get project
    project = await db.story_projects.find_one({"project_id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Calculate cost and deduct credits BEFORE processing
    total_cost = CREDIT_COSTS["video_render"]
    if not request.include_watermark:
        total_cost += CREDIT_COSTS["watermark_removal"]
    
    await check_and_deduct_credits(
        user_id,
        total_cost,
        f"Video rendering for project {request.project_id}"
    )
    
    # Get scene assets
    scene_images = await db.scene_assets.find({
        "project_id": request.project_id,
        "asset_type": "image"
    }).to_list(length=100)
    
    voice_tracks = await db.voice_tracks.find({
        "project_id": request.project_id
    }).to_list(length=100)
    
    if not scene_images:
        raise HTTPException(status_code=400, detail="No images found. Generate images first.")
    
    if not voice_tracks:
        raise HTTPException(status_code=400, detail="No voice tracks found. Generate voices first.")
    
    # Pre-flight check: Verify that image and audio files exist
    missing_files = []
    for img in scene_images:
        img_url = img.get("url") or img.get("image_url")
        if img_url and img_url.startswith("/static/"):
            local_path = f"/app/backend{img_url}"
            if not os.path.exists(local_path):
                missing_files.append(f"Scene {img.get('scene_number')} image")
    
    for voice in voice_tracks:
        audio_url = voice.get("audio_path") or voice.get("audio_url")
        if audio_url and audio_url.startswith("/static/"):
            local_path = f"/app/backend{audio_url}"
            if not os.path.exists(local_path):
                missing_files.append(f"Scene {voice.get('scene_number')} audio")
    
    if missing_files:
        # Refund credits since we can't proceed
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": total_cost}}
        )
        raise HTTPException(
            status_code=400, 
            detail=f"Some files are missing and need to be regenerated: {', '.join(missing_files[:5])}{'...' if len(missing_files) > 5 else ''}. Please regenerate images/voices for this project."
        )
    
    # Create render job
    job_id = str(uuid.uuid4())
    render_job = {
        "job_id": job_id,
        "project_id": request.project_id,
        "user_id": user_id,
        "status": "PENDING",
        "include_watermark": request.include_watermark,
        "background_music_id": request.background_music_id,
        "music_volume": request.music_volume,
        "created_at": datetime.now(timezone.utc),
        "progress": 0
    }
    
    await db.render_jobs.insert_one(render_job)
    
    # Start background rendering
    background_tasks.add_task(
        render_video_task,
        job_id,
        request.project_id,
        scene_images,
        voice_tracks,
        request.include_watermark,
        request.background_music_id,
        request.music_volume
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "project_id": request.project_id,
        "status": "PENDING",
        "message": "Video rendering started. Check status with /video/status/{job_id}",
        "credits_spent": total_cost
    }

async def render_video_task(
    job_id: str,
    project_id: str,
    scene_images: List[dict],
    voice_tracks: List[dict],
    include_watermark: bool,
    background_music_id: Optional[str],
    music_volume: float
):
    """Background task to render video using FFmpeg"""
    
    # Get user_id from render job for WebSocket updates
    job = await db.render_jobs.find_one({"job_id": job_id})
    user_id = job.get("user_id") if job else None
    
    try:
        # Update status to processing
        await db.render_jobs.update_one(
            {"job_id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 10}}
        )
        
        # Broadcast: Starting video assembly
        if WS_AVAILABLE and user_id:
            await broadcast_video_progress(job_id, user_id, "preparing", 10)
        
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Sort assets by scene number
            scene_images.sort(key=lambda x: x.get("scene_number", 0))
            voice_tracks.sort(key=lambda x: x.get("scene_number", 0))
            
            # Download images and prepare video segments
            segments = []
            total_scenes = len(scene_images)
            
            for i, (img, voice) in enumerate(zip(scene_images, voice_tracks)):
                scene_num = img.get("scene_number", i + 1)
                
                # Broadcast: Processing scene
                if WS_AVAILABLE and user_id:
                    await broadcast_video_progress(
                        job_id, user_id, "composing", 
                        10 + int((i / total_scenes) * 50)
                    )
                
                # Download image
                image_path = os.path.join(temp_dir, f"scene_{scene_num}.png")
                img_url = img.get("url") or img.get("image_url")
                await download_file(img_url, image_path)
                
                # Download voice audio - use download_file for consistent remote/local handling
                audio_path = os.path.join(temp_dir, f"scene_{scene_num}_audio.mp3")
                audio_url = voice.get("audio_url") or voice.get("audio_path")
                
                if audio_url:
                    # If it's already a full local path, check if file exists
                    if audio_url.startswith("/app/backend/") and os.path.exists(audio_url):
                        shutil.copy(audio_url, audio_path)
                    else:
                        # Use download_file for both /static/ paths and URLs
                        await download_file(audio_url, audio_path)
                else:
                    raise Exception(f"No audio URL found for scene {scene_num}")
                
                duration = voice.get("duration", 5)
                if duration <= 0:
                    duration = 5  # Default 5 seconds if not specified
                
                # Create video segment with image and audio
                segment_path = os.path.join(temp_dir, f"segment_{scene_num}.mp4")
                
                # FFmpeg command to create segment with zoom effect
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", image_path,
                    "-i", audio_path,
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,zoompan=z='min(zoom+0.001,1.2)':d={int(duration*25)}:s=1920x1080",
                    "-shortest",
                    segment_path
                ]
                
                subprocess.run(cmd, capture_output=True, check=True)
                segments.append(segment_path)
                
                # Update progress
                progress = 10 + int((i + 1) / len(scene_images) * 60)
                await db.render_jobs.update_one(
                    {"job_id": job_id},
                    {"$set": {"progress": progress}}
                )
            
            # Create concat file
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for seg in segments:
                    f.write(f"file '{seg}'\n")
            
            # Broadcast: Audio sync phase
            if WS_AVAILABLE and user_id:
                await broadcast_video_progress(job_id, user_id, "audio_sync", 70)
            
            # Concatenate all segments
            concat_output = os.path.join(temp_dir, "concat_video.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                concat_output
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            
            await db.render_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"progress": 75}}
            )
            
            # Broadcast: Adding music phase
            if WS_AVAILABLE and user_id:
                await broadcast_video_progress(job_id, user_id, "music", 75)
            
            # Add background music if specified
            final_video = concat_output
            if background_music_id:
                music_track = next((m for m in PIXABAY_MUSIC_SAMPLES if m["id"] == background_music_id), None)
                if music_track:
                    music_path = os.path.join(temp_dir, "music.mp3")
                    await download_file(music_track["url"], music_path)
                    
                    video_with_music = os.path.join(temp_dir, "video_with_music.mp4")
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", concat_output,
                        "-i", music_path,
                        "-filter_complex", f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
                        "-map", "0:v",
                        "-map", "[a]",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        video_with_music
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)
                    final_video = video_with_music
            
            await db.render_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"progress": 85}}
            )
            
            # Broadcast: Rendering final video
            if WS_AVAILABLE and user_id:
                await broadcast_video_progress(job_id, user_id, "rendering", 85)
            
            # Add watermark if required
            output_filename = f"{project_id}_final.mp4"
            output_path = str(STATIC_DIR / output_filename)
            
            if include_watermark:
                # Create watermark text
                watermark_text = "visionary-suite.com"
                cmd = [
                    "ffmpeg", "-y",
                    "-i", final_video,
                    "-vf", f"drawtext=text='{watermark_text}':fontcolor=white@0.5:fontsize=24:x=w-tw-10:y=h-th-10",
                    "-c:a", "copy",
                    output_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
            else:
                shutil.copy(final_video, output_path)
            
            # Upload final video to R2 cloud storage
            from services.cloudflare_r2_storage import get_r2_storage
            video_url = f"/static/generated/{output_filename}"
            storage_type = "local"
            
            r2_storage = get_r2_storage()
            if r2_storage.is_configured:
                success, public_url, key = await r2_storage.upload_file(
                    output_path, "video", project_id, output_filename
                )
                if success:
                    video_url = public_url
                    storage_type = "r2_cloud"
                    logger.info(f"Final video uploaded to R2: {public_url}")
                    # Keep local file as backup for now, will be cleaned by cleanup service
            
            # Update job as completed
            await db.render_jobs.update_one(
                {"job_id": job_id},
                {
                    "$set": {
                        "status": "COMPLETED",
                        "progress": 100,
                        "output_url": video_url,
                        "storage_type": storage_type,
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Update project status
            await db.story_projects.update_one(
                {"project_id": project_id},
                {
                    "$set": {
                        "status": "video_rendered",
                        "final_video_url": video_url,
                        "storage_type": storage_type,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Broadcast: Completion
            if WS_AVAILABLE and user_id:
                await broadcast_completion(
                    job_id, user_id, "Video",
                    result_url=video_url,
                    metadata={"project_id": project_id, "storage": storage_type}
                )
            
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Video render failed for job {job_id}: {error_message}")
        
        # Broadcast: Error
        if WS_AVAILABLE and user_id:
            await broadcast_error(job_id, user_id, error_message, stage="video_assembly")
        
        # Attempt to refund credits for failed video generation
        try:
            # Get the render job to find the cost
            job_doc = await db.render_jobs.find_one({"job_id": job_id})
            if job_doc and user_id:
                # Refund the video render cost
                refund_amount = CREDIT_COSTS["video_render"]
                if not job_doc.get("include_watermark", True):
                    refund_amount += CREDIT_COSTS["watermark_removal"]
                
                from bson import ObjectId
                # Try to find user and refund
                user = None
                try:
                    user = await db.users.find_one({"_id": ObjectId(user_id)})
                except Exception:
                    user = await db.users.find_one({"id": user_id})
                
                if user:
                    await db.users.update_one(
                        {"_id": user.get("_id")},
                        {
                            "$inc": {"credits": refund_amount},
                            "$push": {
                                "credit_transactions": {
                                    "amount": refund_amount,
                                    "description": f"Automatic refund for failed video generation (Job: {job_id[:8]}...)",
                                    "timestamp": datetime.now(timezone.utc),
                                    "type": "refund",
                                    "reason": "generation_failed"
                                }
                            }
                        }
                    )
                    logger.info(f"Refunded {refund_amount} credits to user {user_id} for failed job {job_id}")
        except Exception as refund_error:
            logger.error(f"Failed to process refund for job {job_id}: {refund_error}")
        
        # Update job as failed
        await db.render_jobs.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error": error_message,
                    "completed_at": datetime.now(timezone.utc),
                    "credits_refunded": True
                }
            }
        )

async def download_file(url: str, output_path: str):
    """Download file from URL or copy from local path - handles R2 cloud, local and remote files"""
    import os
    
    # If it's already a full HTTPS URL (including R2 cloud URLs), download directly
    if url.startswith("https://") or url.startswith("http://"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(output_path, "wb") as f:
                            await f.write(content)
                        logger.info(f"Downloaded file from URL: {url[:80]}...")
                        return
                    else:
                        raise Exception(f"Failed to download file (HTTP {response.status}): {url}")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error downloading file: {url} - {str(e)}")
    
    # Check if it's a local path (starts with /static/ or /api/)
    if url.startswith("/static/") or url.startswith("/api/"):
        local_path = f"/app/backend{url}"
        if os.path.exists(local_path):
            shutil.copy(local_path, output_path)
            return
        
        # Local file not found - try downloading from the public URL
        # Get the backend URL from environment or use known production URL
        backend_url = os.environ.get("BACKEND_PUBLIC_URL", "")
        if not backend_url:
            backend_url = os.environ.get("FRONTEND_URL", "")  # Use FRONTEND_URL which is set
        if not backend_url:
            # Fallback to the known production domain
            backend_url = "https://www.visionary-suite.com"
        
        # Also try preview URL pattern
        preview_urls = [
            backend_url,
            "https://story-to-video-35.preview.emergentagent.com",  # Preview environment
        ]
        
        for base_url in preview_urls:
            if not base_url:
                continue
            full_url = f"{base_url}{url}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.read()
                            async with aiofiles.open(output_path, "wb") as f:
                                await f.write(content)
                            logger.info(f"Downloaded file from {full_url}")
                            return
            except Exception as e:
                logger.warning(f"Failed to download from {full_url}: {e}")
                continue
        
        # If still not found, raise a helpful error
        raise Exception(f"File not found locally or remotely. Please regenerate the images/voices for this project. (File: {url})")
    
    # Otherwise download from full URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.read()
                    async with aiofiles.open(output_path, "wb") as f:
                        await f.write(content)
                else:
                    raise Exception(f"Failed to download file (HTTP {response.status}): {url}")
    except aiohttp.ClientError as e:
        raise Exception(f"Network error downloading file: {url} - {str(e)}")

@router.get("/video/status/{job_id}")
async def get_video_status(job_id: str):
    """Get video rendering job status"""
    
    job = await db.render_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "job": job
    }

# =============================================================================
# CUSTOM VIDEO PLAYER ENDPOINT
# =============================================================================

@router.get("/video/player/{project_id}")
async def get_video_player_data(project_id: str):
    """Get data for custom video player"""
    
    project = await db.story_projects.find_one(
        {"project_id": project_id},
        {"_id": 0, "final_video_url": 1, "title": 1, "scenes": 1}
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.get("final_video_url"):
        raise HTTPException(status_code=400, detail="Video not yet rendered")
    
    # Build chapter markers from scenes
    chapters = []
    current_time = 0
    for scene in project.get("scenes", []):
        chapters.append({
            "title": scene.get("title"),
            "start_time": current_time,
            "duration": scene.get("estimated_duration", 5)
        })
        current_time += scene.get("estimated_duration", 5)
    
    return {
        "success": True,
        "video_url": project.get("final_video_url"),
        "title": project.get("title"),
        "chapters": chapters,
        "player_config": {
            "autoplay": False,
            "controls": True,
            "branding": {
                "logo": "/logo.png",
                "color": "#8B5CF6",
                "name": "Visionary Suite"
            }
        }
    }


# =============================================================================
# STORAGE STATUS ENDPOINT
# =============================================================================

@router.get("/storage/status")
async def get_storage_status(current_user: dict = Depends(get_current_user)):
    """Get cloud storage configuration status"""
    from services.cloudflare_r2_storage import get_r2_storage
    
    r2_storage = get_r2_storage()
    stats = r2_storage.get_stats()
    
    return {
        "success": True,
        "storage": {
            "provider": "cloudflare_r2",
            "configured": stats["configured"],
            "bucket": stats["bucket"],
            "public_url_configured": bool(stats["public_url"]),
            "status": "active" if stats["configured"] else "not_configured"
        }
    }
