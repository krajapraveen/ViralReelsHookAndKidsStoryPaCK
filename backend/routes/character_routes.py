"""
Character Consistency Management Routes
Handles character creation, storage, and consistent generation
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from shared import db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/story-video-studio/characters", tags=["Character Consistency"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class CharacterCreate(BaseModel):
    name: str
    description: str
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    personality: Optional[str] = None
    age_group: str = "adult"  # child, teen, adult, elderly
    style: str = "cartoon"  # cartoon, anime, realistic, watercolor, comic, 3d_render
    reference_images: List[str] = []

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    personality: Optional[str] = None
    age_group: Optional[str] = None
    style: Optional[str] = None

class GenerateVariationsRequest(BaseModel):
    character_id: str
    poses: List[str] = ["standing"]
    expressions: List[str] = ["neutral"]
    count: int = 3

# =============================================================================
# CHARACTER CRUD ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_characters(
    current_user: dict = Depends(get_current_user)
):
    """List all characters for current user"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    characters = await db.story_characters.find(
        {"user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "characters": characters,
        "count": len(characters)
    }

@router.post("/create")
async def create_character(
    request: CharacterCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new character profile"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    character_id = str(uuid.uuid4())
    
    # Build the character prompt for consistent generation
    consistency_prompt = build_consistency_prompt(request)
    
    character_doc = {
        "character_id": character_id,
        "user_id": user_id,
        "name": request.name,
        "description": request.description,
        "appearance": request.appearance,
        "clothing": request.clothing,
        "personality": request.personality,
        "age_group": request.age_group,
        "style": request.style,
        "reference_images": request.reference_images,
        "consistency_prompt": consistency_prompt,
        "generated_variations": [],
        "usage_count": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted": False
    }
    
    await db.story_characters.insert_one(character_doc)
    
    # Remove _id for response
    character_doc.pop("_id", None)
    
    logger.info(f"Character created: {character_id} for user {user_id}")
    
    return {
        "success": True,
        "character_id": character_id,
        "character": character_doc,
        "message": "Character created successfully"
    }

@router.get("/{character_id}")
async def get_character(
    character_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific character"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    character = await db.story_characters.find_one(
        {"character_id": character_id, "user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0}
    )
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "success": True,
        "character": character
    }

@router.put("/{character_id}")
async def update_character(
    character_id: str,
    request: CharacterUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a character"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Build update dict with non-None values
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.story_characters.update_one(
        {"character_id": character_id, "user_id": user_id, "deleted": {"$ne": True}},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Regenerate consistency prompt if appearance/clothing/style changed
    if any(k in update_data for k in ["appearance", "clothing", "style", "description"]):
        character = await db.story_characters.find_one({"character_id": character_id})
        if character:
            consistency_prompt = build_consistency_prompt_from_doc(character)
            await db.story_characters.update_one(
                {"character_id": character_id},
                {"$set": {"consistency_prompt": consistency_prompt}}
            )
    
    return {
        "success": True,
        "message": "Character updated successfully"
    }

@router.delete("/{character_id}")
async def delete_character(
    character_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a character"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    result = await db.story_characters.update_one(
        {"character_id": character_id, "user_id": user_id},
        {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "success": True,
        "message": "Character deleted"
    }

# =============================================================================
# CHARACTER VARIATION GENERATION
# =============================================================================

@router.post("/generate-variations")
async def generate_character_variations(
    request: GenerateVariationsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate consistent character variations with different poses/expressions"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Get character
    character = await db.story_characters.find_one(
        {"character_id": request.character_id, "user_id": user_id, "deleted": {"$ne": True}}
    )
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    generated_images = []
    
    # Generate images for each pose/expression combination
    combinations = []
    for pose in request.poses:
        for expression in request.expressions:
            if len(combinations) >= request.count:
                break
            combinations.append((pose, expression))
    
    for pose, expression in combinations[:request.count]:
        try:
            # Build the prompt
            prompt = build_variation_prompt(character, pose, expression)
            
            # Generate image using the image generation service
            from routes.story_video_generation import generate_image_with_retry
            
            result = await generate_image_with_retry(
                prompt=prompt,
                negative_prompt="inconsistent character, different character, wrong features, deformed",
                style=character.get("style", "cartoon"),
                project_id=f"character_{request.character_id}",
                scene_number=len(generated_images) + 1,
                provider="openai"
            )
            
            if result.get("success"):
                generated_images.append({
                    "url": result["url"],
                    "pose": pose,
                    "expression": expression,
                    "prompt": prompt
                })
        except Exception as e:
            logger.error(f"Failed to generate variation: {e}")
            continue
    
    # Store generated variations
    if generated_images:
        await db.story_characters.update_one(
            {"character_id": request.character_id},
            {
                "$push": {"generated_variations": {"$each": generated_images}},
                "$inc": {"usage_count": len(generated_images)}
            }
        )
    
    return {
        "success": True,
        "images": generated_images,
        "count": len(generated_images),
        "message": f"Generated {len(generated_images)} character variations"
    }

@router.get("/{character_id}/prompt")
async def get_character_prompt(
    character_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get the consistency prompt for a character"""
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    character = await db.story_characters.find_one(
        {"character_id": character_id, "user_id": user_id, "deleted": {"$ne": True}},
        {"_id": 0, "consistency_prompt": 1, "name": 1}
    )
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {
        "success": True,
        "character_name": character.get("name"),
        "prompt": character.get("consistency_prompt", "")
    }

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_consistency_prompt(request: CharacterCreate) -> str:
    """Build a consistency prompt from character creation request"""
    parts = []
    
    if request.name:
        parts.append(f"Character: {request.name}")
    
    if request.appearance:
        parts.append(f"Appearance: {request.appearance}")
    
    if request.clothing:
        parts.append(f"Clothing: {request.clothing}")
    
    if request.description:
        parts.append(f"Description: {request.description}")
    
    if request.age_group:
        age_descriptions = {
            "child": "young child",
            "teen": "teenager",
            "adult": "adult",
            "elderly": "elderly person"
        }
        parts.append(f"Age: {age_descriptions.get(request.age_group, request.age_group)}")
    
    style_prompts = {
        "cartoon": "cartoon style, bold lines, vibrant colors",
        "anime": "anime style, expressive eyes, Japanese animation",
        "realistic": "realistic, detailed, photorealistic",
        "watercolor": "watercolor painting style, soft colors, artistic",
        "comic": "comic book style, dynamic, bold outlines",
        "3d_render": "3D rendered, CGI style, high quality render"
    }
    
    if request.style:
        parts.append(f"Style: {style_prompts.get(request.style, request.style)}")
    
    return ". ".join(parts)

def build_consistency_prompt_from_doc(doc: dict) -> str:
    """Build a consistency prompt from a MongoDB document"""
    class FakeRequest:
        pass
    
    req = FakeRequest()
    req.name = doc.get("name")
    req.appearance = doc.get("appearance")
    req.clothing = doc.get("clothing")
    req.description = doc.get("description")
    req.age_group = doc.get("age_group")
    req.style = doc.get("style")
    
    return build_consistency_prompt(req)

def build_variation_prompt(character: dict, pose: str, expression: str) -> str:
    """Build a prompt for generating a character variation"""
    base_prompt = character.get("consistency_prompt", "")
    
    pose_descriptions = {
        "standing": "standing upright, full body view",
        "sitting": "sitting down, relaxed pose",
        "walking": "walking, mid-stride",
        "running": "running, dynamic action pose",
        "jumping": "jumping, airborne, dynamic"
    }
    
    expression_descriptions = {
        "happy": "happy expression, smiling, joyful",
        "sad": "sad expression, downcast, melancholic",
        "angry": "angry expression, fierce, determined",
        "surprised": "surprised expression, wide eyes, shocked",
        "neutral": "neutral expression, calm, composed"
    }
    
    pose_desc = pose_descriptions.get(pose, pose)
    expr_desc = expression_descriptions.get(expression, expression)
    
    full_prompt = f"{base_prompt}. Pose: {pose_desc}. Expression: {expr_desc}. Same character, consistent appearance, same outfit."
    
    return full_prompt
