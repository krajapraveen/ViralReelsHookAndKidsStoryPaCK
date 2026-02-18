"""
Style Profile Training Module
Handles image uploads and style profile management for GenStudio
"""
import os
import uuid
import base64
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from shared import db, get_current_user, deduct_credits, add_credits, EMERGENT_LLM_KEY, FILE_EXPIRY_MINUTES

logger = logging.getLogger(__name__)

# Router
style_profile_router = APIRouter(prefix="/style-profiles", tags=["Style Profiles"])

# Constants
MAX_IMAGES_PER_PROFILE = 20
MIN_IMAGES_FOR_TRAINING = 5
MAX_IMAGE_SIZE_MB = 10
STYLE_PROFILE_CREATE_COST = 20
STYLE_PROFILE_USE_COST = 1

# =============================================================================
# MODELS
# =============================================================================
class StyleProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    category: str = Field(default="general")

class StyleProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = None

# =============================================================================
# STYLE PROFILE CRUD
# =============================================================================
@style_profile_router.post("/create")
async def create_style_profile(data: StyleProfileCreate, user: dict = Depends(get_current_user)):
    """Create a new style profile - costs 20 credits"""
    
    # Check credits
    if user.get("credits", 0) < STYLE_PROFILE_CREATE_COST:
        raise HTTPException(status_code=400, detail=f"Need {STYLE_PROFILE_CREATE_COST} credits to create a style profile")
    
    # Check existing profiles limit (max 10 per user)
    existing_count = await db.style_profiles.count_documents({"userId": user["id"]})
    if existing_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 style profiles per user. Delete some to create new ones.")
    
    profile_id = str(uuid.uuid4())
    
    profile = {
        "id": profile_id,
        "userId": user["id"],
        "name": data.name,
        "description": data.description,
        "tags": data.tags[:10],  # Max 10 tags
        "category": data.category,
        "images": [],  # Will store image data
        "imageCount": 0,
        "trained": False,
        "trainingStatus": "pending",
        "styleVector": None,  # Will be populated after training
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.style_profiles.insert_one(profile)
    
    # Deduct credits
    remaining = await deduct_credits(user["id"], STYLE_PROFILE_CREATE_COST, f"Style Profile: {data.name}")
    
    return {
        "success": True,
        "profileId": profile_id,
        "creditsUsed": STYLE_PROFILE_CREATE_COST,
        "remainingCredits": remaining,
        "message": f"Style profile '{data.name}' created! Upload {MIN_IMAGES_FOR_TRAINING}-{MAX_IMAGES_PER_PROFILE} reference images to train.",
        "nextStep": f"Upload images using POST /api/style-profiles/{profile_id}/upload-image"
    }

@style_profile_router.get("/list")
async def list_style_profiles(user: dict = Depends(get_current_user)):
    """Get all user's style profiles"""
    profiles = await db.style_profiles.find(
        {"userId": user["id"]},
        {"_id": 0, "images": 0, "styleVector": 0}  # Exclude large fields
    ).sort("createdAt", -1).to_list(50)
    
    return {
        "profiles": profiles,
        "count": len(profiles),
        "maxAllowed": 10
    }

@style_profile_router.get("/{profile_id}")
async def get_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Get a specific style profile"""
    profile = await db.style_profiles.find_one(
        {"id": profile_id, "userId": user["id"]},
        {"_id": 0, "styleVector": 0}  # Exclude internal data
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    # Don't return full image data, just thumbnails/metadata
    if "images" in profile:
        profile["images"] = [
            {"id": img.get("id"), "uploadedAt": img.get("uploadedAt")}
            for img in profile.get("images", [])
        ]
    
    return profile

@style_profile_router.put("/{profile_id}")
async def update_style_profile(profile_id: str, data: StyleProfileUpdate, user: dict = Depends(get_current_user)):
    """Update style profile metadata"""
    profile = await db.style_profiles.find_one({"id": profile_id, "userId": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    
    if data.name:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.tags is not None:
        update_data["tags"] = data.tags[:10]
    
    await db.style_profiles.update_one(
        {"id": profile_id},
        {"$set": update_data}
    )
    
    return {"success": True, "message": "Profile updated"}

@style_profile_router.delete("/{profile_id}")
async def delete_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Delete a style profile"""
    result = await db.style_profiles.delete_one({"id": profile_id, "userId": user["id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    return {"success": True, "message": "Style profile deleted"}

# =============================================================================
# IMAGE UPLOAD & TRAINING
# =============================================================================
@style_profile_router.post("/{profile_id}/upload-image")
async def upload_profile_image(
    profile_id: str,
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Upload a reference image for style profile training"""
    
    # Validate profile exists and belongs to user
    profile = await db.style_profiles.find_one({"id": profile_id, "userId": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    # Check image limit
    current_count = profile.get("imageCount", 0)
    if current_count >= MAX_IMAGES_PER_PROFILE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum {MAX_IMAGES_PER_PROFILE} images per profile. Delete some to upload more."
        )
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Supported: PNG, JPEG, WebP")
    
    # Read and validate size
    image_content = await image.read()
    if len(image_content) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Image too large. Maximum {MAX_IMAGE_SIZE_MB}MB")
    
    # Encode image
    image_id = str(uuid.uuid4())
    image_data = {
        "id": image_id,
        "data": base64.b64encode(image_content).decode('utf-8'),
        "contentType": image.content_type,
        "size": len(image_content),
        "uploadedAt": datetime.now(timezone.utc).isoformat()
    }
    
    # Update profile
    new_count = current_count + 1
    can_train = new_count >= MIN_IMAGES_FOR_TRAINING
    
    await db.style_profiles.update_one(
        {"id": profile_id},
        {
            "$push": {"images": image_data},
            "$set": {
                "imageCount": new_count,
                "trainingStatus": "ready" if can_train else "needs_more_images",
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "imageId": image_id,
        "currentImageCount": new_count,
        "maxImages": MAX_IMAGES_PER_PROFILE,
        "canTrain": can_train,
        "message": f"Image uploaded ({new_count}/{MAX_IMAGES_PER_PROFILE}). " + 
                   (f"Ready to train!" if can_train else f"Upload at least {MIN_IMAGES_FOR_TRAINING - new_count} more images to train.")
    }

@style_profile_router.delete("/{profile_id}/image/{image_id}")
async def delete_profile_image(profile_id: str, image_id: str, user: dict = Depends(get_current_user)):
    """Delete an image from a style profile"""
    profile = await db.style_profiles.find_one({"id": profile_id, "userId": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    # Remove image
    await db.style_profiles.update_one(
        {"id": profile_id},
        {
            "$pull": {"images": {"id": image_id}},
            "$inc": {"imageCount": -1},
            "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Update training status
    new_count = profile.get("imageCount", 1) - 1
    await db.style_profiles.update_one(
        {"id": profile_id},
        {"$set": {"trainingStatus": "ready" if new_count >= MIN_IMAGES_FOR_TRAINING else "needs_more_images"}}
    )
    
    return {"success": True, "message": "Image deleted", "remainingImages": new_count}

@style_profile_router.post("/{profile_id}/train")
async def train_style_profile(profile_id: str, user: dict = Depends(get_current_user)):
    """Train a style profile using uploaded images"""
    
    profile = await db.style_profiles.find_one({"id": profile_id, "userId": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    # Check image count
    image_count = profile.get("imageCount", 0)
    if image_count < MIN_IMAGES_FOR_TRAINING:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {MIN_IMAGES_FOR_TRAINING} images to train. Current: {image_count}"
        )
    
    # Mark as training
    await db.style_profiles.update_one(
        {"id": profile_id},
        {"$set": {"trainingStatus": "training", "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    try:
        # Use Gemini to analyze images and extract style characteristics
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"style-train-{profile_id}",
            system_message="You are an expert art director and style analyst. Analyze images to extract consistent visual style characteristics."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        # Analyze first 5 images (to save costs)
        images_to_analyze = profile.get("images", [])[:5]
        
        style_prompt = """Analyze these reference images and extract a comprehensive style guide including:
1. Color palette (primary, secondary, accent colors)
2. Lighting style (soft, dramatic, natural, etc.)
3. Composition preferences
4. Texture and material qualities
5. Mood and atmosphere
6. Art style (realistic, illustrative, minimalist, etc.)

Output a JSON object with these style characteristics that can be used to generate consistent content."""

        # Build message with images
        file_contents = []
        for img in images_to_analyze:
            file_contents.append(FileContent(
                content_type=img.get("contentType", "image/png"),
                file_content_base64=img.get("data", "")
            ))
        
        msg = UserMessage(text=style_prompt, file_contents=file_contents)
        style_analysis = await chat.send_message(msg)
        
        # Store style vector
        await db.style_profiles.update_one(
            {"id": profile_id},
            {"$set": {
                "trained": True,
                "trainingStatus": "completed",
                "styleVector": style_analysis,
                "trainedAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        logger.info(f"Style profile {profile_id} trained successfully")
        
        return {
            "success": True,
            "message": "Style profile trained successfully!",
            "styleGuide": style_analysis[:500] + "..." if len(style_analysis) > 500 else style_analysis,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Style training error: {e}")
        await db.style_profiles.update_one(
            {"id": profile_id},
            {"$set": {"trainingStatus": "failed", "trainingError": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@style_profile_router.get("/{profile_id}/style-guide")
async def get_style_guide(profile_id: str, user: dict = Depends(get_current_user)):
    """Get the trained style guide for a profile"""
    profile = await db.style_profiles.find_one(
        {"id": profile_id, "userId": user["id"]},
        {"_id": 0, "styleVector": 1, "trained": 1, "trainingStatus": 1}
    )
    
    if not profile:
        raise HTTPException(status_code=404, detail="Style profile not found")
    
    if not profile.get("trained"):
        raise HTTPException(status_code=400, detail="Profile not trained yet. Upload images and train first.")
    
    return {
        "trained": profile.get("trained", False),
        "status": profile.get("trainingStatus", "unknown"),
        "styleGuide": profile.get("styleVector", "")
    }

# =============================================================================
# HELPER FUNCTION FOR GENERATION
# =============================================================================
async def get_style_prompt_enhancement(profile_id: str, user_id: str) -> Optional[str]:
    """
    Get style enhancement prompt for generation
    Called by generation endpoints when style_profile_id is provided
    """
    if not profile_id:
        return None
    
    profile = await db.style_profiles.find_one(
        {"id": profile_id, "userId": user_id},
        {"_id": 0, "styleVector": 1, "trained": 1}
    )
    
    if not profile or not profile.get("trained"):
        return None
    
    return profile.get("styleVector")

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    'style_profile_router',
    'get_style_prompt_enhancement'
]
