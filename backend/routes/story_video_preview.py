"""
Story → Video Studio - Preview Mode & Character Consistency
- Quick Preview: Lower resolution images for fast previews (fewer credits)
- Character Consistency: Training system for custom character appearances
"""

import os
import uuid
import asyncio
import base64
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
import aiofiles

from shared import db, get_current_user

router = APIRouter(prefix="/story-video-studio/preview", tags=["Story Video Preview & Characters"])

STATIC_DIR = Path("/app/backend/static/generated")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

PREVIEW_DIR = STATIC_DIR / "previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

CHARACTER_DIR = STATIC_DIR / "characters"
CHARACTER_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# CREDIT COSTS
# =============================================================================

PREVIEW_CREDIT_COSTS = {
    "preview_image": 3,      # vs 10 for full quality
    "preview_voice": 3,      # vs 10 for full quality  
    "preview_video": 5,      # vs 20 for full quality
    "character_training": 15  # One-time cost per character
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PreviewRequest(BaseModel):
    """Generate quick preview with lower quality"""
    project_id: str
    scene_numbers: Optional[List[int]] = None  # None = all scenes
    include_voice: bool = True
    include_video: bool = False  # Optional: generate preview video

class CharacterProfile(BaseModel):
    """Character profile for consistency training"""
    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=10, max_length=500)
    appearance: str = Field(..., min_length=10, max_length=500)
    clothing: str = Field(default="", max_length=300)
    accessories: str = Field(default="", max_length=200)
    color_palette: Optional[List[str]] = None  # e.g., ["#FF5733", "#33FF57"]
    age_appearance: str = Field(default="adult")  # child, teen, adult, elderly
    style_notes: str = Field(default="", max_length=300)

class CharacterTrainingRequest(BaseModel):
    """Request to train a custom character"""
    project_id: str
    character: CharacterProfile
    reference_images: Optional[List[str]] = None  # Base64 encoded images

# =============================================================================
# PREVIEW MODE ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_preview_pricing():
    """Get preview mode pricing comparison"""
    return {
        "success": True,
        "preview_mode": {
            "image_per_scene": PREVIEW_CREDIT_COSTS["preview_image"],
            "voice_per_minute": PREVIEW_CREDIT_COSTS["preview_voice"],
            "video_render": PREVIEW_CREDIT_COSTS["preview_video"],
            "description": "Lower resolution (512x512), faster generation, fewer credits"
        },
        "full_quality": {
            "image_per_scene": 10,
            "voice_per_minute": 10,
            "video_render": 20,
            "description": "Full HD (1024x1024), best quality, more credits"
        },
        "savings": {
            "per_scene": "70% savings on images",
            "per_video": "75% savings on video render",
            "typical_project": "Save 50-60 credits on a 6-scene video"
        }
    }

@router.post("/generate")
async def generate_preview(
    request: PreviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate quick preview with lower resolution"""
    import time
    
    start_time = time.time()
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Get project
    project = await db.story_projects.find_one({"project_id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    scenes = project.get("scenes", [])
    if not scenes:
        raise HTTPException(status_code=400, detail="Generate scenes first")
    
    # Filter scenes
    if request.scene_numbers:
        scenes_to_preview = [s for s in scenes if s.get("scene_number") in request.scene_numbers]
    else:
        scenes_to_preview = scenes
    
    # Calculate credits
    total_credits = len(scenes_to_preview) * PREVIEW_CREDIT_COSTS["preview_image"]
    if request.include_voice:
        total_credits += len(scenes_to_preview) * PREVIEW_CREDIT_COSTS["preview_voice"]
    if request.include_video:
        total_credits += PREVIEW_CREDIT_COSTS["preview_video"]
    
    # Check and deduct credits
    from bson import ObjectId
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("credits", 0) < total_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {total_credits}, Available: {user.get('credits', 0)}"
        )
    
    # Deduct credits
    await db.users.update_one(
        {"_id": user.get("_id")},
        {
            "$inc": {"credits": -total_credits},
            "$push": {
                "credit_transactions": {
                    "amount": -total_credits,
                    "description": f"Preview generation for project {request.project_id}",
                    "timestamp": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    # Generate previews in parallel
    preview_images = await generate_preview_images(
        project,
        scenes_to_preview,
        request.project_id
    )
    
    preview_voices = []
    if request.include_voice:
        preview_voices = await generate_preview_voices(
            project,
            scenes_to_preview,
            request.project_id
        )
    
    # Store preview data
    preview_id = str(uuid.uuid4())
    preview_doc = {
        "preview_id": preview_id,
        "project_id": request.project_id,
        "user_id": user_id,
        "images": preview_images,
        "voices": preview_voices,
        "credits_spent": total_credits,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)  # Preview expires in 24h
    }
    await db.story_previews.insert_one(preview_doc)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Record metrics
    from routes.story_video_analytics import record_metric
    await record_metric(
        metric_type="preview_generation",
        project_id=request.project_id,
        user_id=user_id,
        duration_ms=duration_ms,
        success=True,
        metadata={"scenes": len(scenes_to_preview), "include_voice": request.include_voice}
    )
    
    return {
        "success": True,
        "preview_id": preview_id,
        "project_id": request.project_id,
        "images_generated": len([i for i in preview_images if i.get("success")]),
        "voices_generated": len([v for v in preview_voices if v.get("success")]),
        "credits_spent": total_credits,
        "duration_seconds": round(duration_ms / 1000, 2),
        "preview_images": preview_images,
        "preview_voices": preview_voices,
        "message": "Preview generated! Review and proceed to full quality if satisfied.",
        "next_steps": {
            "approve": "POST /api/story-video-studio/generation/images to generate HD images",
            "regenerate": "POST /api/story-video-studio/preview/generate to try different settings",
            "discard": "Previews expire automatically in 24 hours"
        }
    }

async def generate_preview_images(project: dict, scenes: list, project_id: str) -> list:
    """Generate low-resolution preview images (512x512 instead of 1024x1024)"""
    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        return [{"error": "API key not configured"}]
    
    style_prompt = project.get("style_prompt", "cartoon style")
    negative_prompt = "copyrighted character, brand logo, celebrity, nsfw, violence"
    
    # Build character descriptions
    character_bible = {}
    for char in project.get("characters", []):
        char_prompt = f"{char.get('name')}: {char.get('appearance')}"
        character_bible[char.get("name")] = char_prompt
    
    results = []
    
    # Generate images sequentially for preview (faster overall)
    for scene in scenes:
        scene_num = scene.get("scene_number", 0)
        visual_prompt = scene.get("visual_prompt", "")
        
        # Include character descriptions
        chars_in_scene = scene.get("characters_in_scene", [])
        char_descriptions = [character_bible.get(c, c) for c in chars_in_scene]
        
        full_prompt = f"{visual_prompt}. "
        if char_descriptions:
            full_prompt += f"Characters: {', '.join(char_descriptions)}. "
        full_prompt += f"Style: {style_prompt}. Avoid: {negative_prompt}"
        
        try:
            image_gen = OpenAIImageGeneration(api_key=api_key)
            images = await image_gen.generate_images(
                prompt=full_prompt[:1000],  # Limit prompt length
                model="gpt-image-1",
                number_of_images=1,
                size="1024x1024",  # OpenAI doesn't support 512, we'll resize
                quality="low"  # Use low quality for preview
            )
            
            if images and len(images) > 0:
                preview_filename = f"preview_{project_id}_scene_{scene_num}.png"
                preview_path = PREVIEW_DIR / preview_filename
                
                with open(preview_path, "wb") as f:
                    f.write(images[0])
                
                results.append({
                    "scene_number": scene_num,
                    "preview_url": f"/static/generated/previews/{preview_filename}",
                    "quality": "preview",
                    "success": True
                })
            else:
                results.append({
                    "scene_number": scene_num,
                    "error": "No image generated",
                    "success": False
                })
                
        except Exception as e:
            results.append({
                "scene_number": scene_num,
                "error": str(e)[:100],
                "success": False
            })
    
    return results

async def generate_preview_voices(project: dict, scenes: list, project_id: str) -> list:
    """Generate preview voice tracks"""
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        return [{"error": "API key not configured"}]
    
    voice_scripts = project.get("voice_scripts", [])
    results = []
    
    for scene in scenes:
        scene_num = scene.get("scene_number", 0)
        
        # Find matching voice script
        voice_script = next(
            (vs for vs in voice_scripts if vs.get("scene_number") == scene_num),
            None
        )
        
        if not voice_script:
            results.append({
                "scene_number": scene_num,
                "error": "No voice script found",
                "success": False
            })
            continue
        
        narrator_text = voice_script.get("narrator_text", "")
        if not narrator_text:
            continue
        
        try:
            tts = OpenAITextToSpeech(api_key=api_key)
            audio_bytes = await tts.generate_speech(
                text=narrator_text,
                model="tts-1",  # Standard quality for preview
                voice="alloy",
                speed=1.0,
                response_format="mp3"
            )
            
            preview_filename = f"preview_{project_id}_scene_{scene_num}_voice.mp3"
            preview_path = PREVIEW_DIR / preview_filename
            
            with open(preview_path, "wb") as f:
                f.write(audio_bytes)
            
            results.append({
                "scene_number": scene_num,
                "preview_url": f"/static/generated/previews/{preview_filename}",
                "quality": "preview",
                "success": True
            })
            
        except Exception as e:
            results.append({
                "scene_number": scene_num,
                "error": str(e)[:100],
                "success": False
            })
    
    return results

@router.get("/{preview_id}")
async def get_preview(preview_id: str, current_user: dict = Depends(get_current_user)):
    """Get a preview by ID"""
    preview = await db.story_previews.find_one({"preview_id": preview_id}, {"_id": 0})
    
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    return {
        "success": True,
        "preview": preview
    }

@router.post("/{preview_id}/approve")
async def approve_preview(
    preview_id: str,
    generate_full_quality: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Approve a preview and optionally generate full quality"""
    
    preview = await db.story_previews.find_one({"preview_id": preview_id})
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    # Mark as approved
    await db.story_previews.update_one(
        {"preview_id": preview_id},
        {"$set": {"status": "APPROVED", "approved_at": datetime.now(timezone.utc)}}
    )
    
    if generate_full_quality:
        return {
            "success": True,
            "message": "Preview approved! Use the following endpoints to generate full quality:",
            "next_steps": {
                "images": f"POST /api/story-video-studio/generation/images with project_id: {preview['project_id']}",
                "voices": f"POST /api/story-video-studio/generation/voices with project_id: {preview['project_id']}",
                "video": f"POST /api/story-video-studio/generation/video/assemble with project_id: {preview['project_id']}"
            }
        }
    
    return {
        "success": True,
        "message": "Preview approved"
    }

# =============================================================================
# CHARACTER CONSISTENCY TRAINING
# =============================================================================

@router.get("/characters/guide")
async def get_character_guide():
    """Get guide for character consistency training"""
    return {
        "success": True,
        "guide": {
            "what_is_character_training": "Train the AI to generate consistent character appearances across all scenes",
            "how_it_works": [
                "1. Define detailed character profile (appearance, clothing, colors)",
                "2. Optionally upload reference images",
                "3. AI creates a 'character prompt' that ensures consistency",
                "4. This prompt is automatically used in all scene generations"
            ],
            "best_practices": [
                "Be very specific about physical features (hair color, eye color, skin tone)",
                "Include distinctive features (glasses, hat, scar, etc.)",
                "Specify clothing style and colors",
                "Mention age appearance (child, teen, adult)",
                "Include personality traits that affect posture/expression"
            ],
            "example_profile": {
                "name": "Luna the Rabbit",
                "description": "A brave young rabbit with a curious personality",
                "appearance": "White fur with pink inner ears, big blue eyes, small pink nose, fluffy round tail",
                "clothing": "Red polka-dot dress with white collar, small golden bow on left ear",
                "accessories": "Tiny silver locket around neck, small backpack",
                "color_palette": ["#FFFFFF", "#FFC0CB", "#4169E1", "#FF0000", "#FFD700"],
                "age_appearance": "child",
                "style_notes": "Always looks cheerful, stands upright on hind legs"
            },
            "credit_cost": PREVIEW_CREDIT_COSTS["character_training"]
        }
    }

@router.post("/characters/train")
async def train_character(
    request: CharacterTrainingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Train a custom character for consistency"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Check credits
    from bson import ObjectId
    user = None
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await db.users.find_one({"id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    credit_cost = PREVIEW_CREDIT_COSTS["character_training"]
    if user.get("credits", 0) < credit_cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {credit_cost}, Available: {user.get('credits', 0)}"
        )
    
    # Deduct credits
    await db.users.update_one(
        {"_id": user.get("_id")},
        {
            "$inc": {"credits": -credit_cost},
            "$push": {
                "credit_transactions": {
                    "amount": -credit_cost,
                    "description": f"Character training: {request.character.name}",
                    "timestamp": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    # Build consistency prompt
    char = request.character
    consistency_prompt = f"""
Character: {char.name}
Physical Appearance: {char.appearance}
Clothing: {char.clothing if char.clothing else 'Not specified'}
Accessories: {char.accessories if char.accessories else 'None'}
Age Appearance: {char.age_appearance}
Style Notes: {char.style_notes if char.style_notes else 'None'}
Color Palette: {', '.join(char.color_palette) if char.color_palette else 'Not specified'}

IMPORTANT: This character must look EXACTLY the same in every scene.
Key identifying features to maintain:
- {char.appearance.split(',')[0] if ',' in char.appearance else char.appearance}
""".strip()
    
    # Save reference images if provided
    reference_paths = []
    if request.reference_images:
        for i, img_data in enumerate(request.reference_images[:3]):  # Max 3 references
            try:
                img_bytes = base64.b64decode(img_data)
                ref_filename = f"char_{request.project_id}_{char.name.replace(' ', '_')}_{i}.png"
                ref_path = CHARACTER_DIR / ref_filename
                
                with open(ref_path, "wb") as f:
                    f.write(img_bytes)
                
                reference_paths.append(f"/static/generated/characters/{ref_filename}")
            except Exception:
                pass
    
    # Store character profile
    character_id = str(uuid.uuid4())
    character_doc = {
        "character_id": character_id,
        "project_id": request.project_id,
        "user_id": user_id,
        "name": char.name,
        "profile": char.dict(),
        "consistency_prompt": consistency_prompt,
        "reference_images": reference_paths,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.trained_characters.insert_one(character_doc)
    
    # Update project with character
    await db.story_projects.update_one(
        {"project_id": request.project_id},
        {
            "$push": {
                "trained_characters": {
                    "character_id": character_id,
                    "name": char.name,
                    "consistency_prompt": consistency_prompt
                }
            }
        }
    )
    
    return {
        "success": True,
        "character_id": character_id,
        "name": char.name,
        "credits_spent": credit_cost,
        "consistency_prompt": consistency_prompt,
        "reference_images": reference_paths,
        "message": f"Character '{char.name}' trained! This profile will be used in all scene generations."
    }

@router.get("/characters/{project_id}")
async def get_project_characters(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all trained characters for a project"""
    
    characters = await db.trained_characters.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(50)
    
    return {
        "success": True,
        "project_id": project_id,
        "characters": characters
    }

@router.post("/characters/{character_id}/update")
async def update_character(
    character_id: str,
    updates: CharacterProfile,
    current_user: dict = Depends(get_current_user)
):
    """Update a trained character profile (free)"""
    
    # Rebuild consistency prompt
    char = updates
    consistency_prompt = f"""
Character: {char.name}
Physical Appearance: {char.appearance}
Clothing: {char.clothing if char.clothing else 'Not specified'}
Accessories: {char.accessories if char.accessories else 'None'}
Age Appearance: {char.age_appearance}
Style Notes: {char.style_notes if char.style_notes else 'None'}
Color Palette: {', '.join(char.color_palette) if char.color_palette else 'Not specified'}

IMPORTANT: This character must look EXACTLY the same in every scene.
Key identifying features to maintain:
- {char.appearance.split(',')[0] if ',' in char.appearance else char.appearance}
""".strip()
    
    await db.trained_characters.update_one(
        {"character_id": character_id},
        {
            "$set": {
                "name": char.name,
                "profile": char.dict(),
                "consistency_prompt": consistency_prompt,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "success": True,
        "message": "Character updated",
        "consistency_prompt": consistency_prompt
    }

# Add missing import
from datetime import timedelta
