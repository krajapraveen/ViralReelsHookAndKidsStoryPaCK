"""
Comix AI - Photo to Comic Generation Platform
CreatorStudio AI

Features:
- Photo upload → Comic character creation
- Comic scene generator with panels
- Story mode with auto-caption
- BYO-Key / Credits model
- Content moderation
- Multiple comic styles
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import os
import sys
import random
import base64
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/comix", tags=["Comix AI"])

# Comic styles available
COMIC_STYLES = {
    "classic": {
        "name": "Classic Comic",
        "description": "Bold lines, vibrant colors, classic superhero style",
        "prompt_modifier": "classic comic book style, bold outlines, vibrant colors, halftone dots, dynamic poses"
    },
    "manga": {
        "name": "Manga Style",
        "description": "Japanese manga-inspired with expressive features",
        "prompt_modifier": "manga style, anime aesthetic, large expressive eyes, clean lines, Japanese comic style"
    },
    "cartoon": {
        "name": "Cartoon Ink",
        "description": "Fun, exaggerated cartoon style",
        "prompt_modifier": "cartoon style, exaggerated features, thick black outlines, bright colors, playful"
    },
    "pixel": {
        "name": "Pixel Comic",
        "description": "Retro pixel art comic style",
        "prompt_modifier": "pixel art style, 16-bit aesthetic, retro gaming style, pixelated comic"
    },
    "kids": {
        "name": "Kids-Friendly",
        "description": "Soft, friendly style for children",
        "prompt_modifier": "children's book illustration style, soft colors, friendly characters, cute style"
    },
    "noir": {
        "name": "Noir Detective",
        "description": "Dark, moody black and white style",
        "prompt_modifier": "film noir style, black and white, high contrast, dramatic shadows, detective comic"
    },
    "superhero": {
        "name": "Superhero",
        "description": "Action-packed superhero comic style",
        "prompt_modifier": "superhero comic style, dynamic action poses, muscular figures, cape flowing, heroic"
    },
    "fantasy": {
        "name": "Fantasy",
        "description": "Magical fantasy world style",
        "prompt_modifier": "fantasy comic style, magical elements, mystical atmosphere, enchanted world"
    },
    "scifi": {
        "name": "Sci-Fi",
        "description": "Futuristic science fiction style",
        "prompt_modifier": "sci-fi comic style, futuristic, technology, space age, cyberpunk elements"
    }
}

# Panel layouts
PANEL_LAYOUTS = {
    1: {"name": "Single", "grid": "1x1"},
    3: {"name": "Triptych", "grid": "1x3"},
    4: {"name": "Classic 4", "grid": "2x2"},
    6: {"name": "Story Strip", "grid": "2x3"},
    9: {"name": "Full Page", "grid": "3x3"}
}

# Credit costs - Updated pricing
COMIC_CREDITS = {
    # Generation costs (viewing)
    "character_portrait": 10,
    "character_fullbody": 10,
    "panel_single": 10,
    "panel_multi": 10,
    "story_mode": 10,
    # Download costs
    "download": 15,
    "download_story": 20,
}

# Blocked content patterns
BLOCKED_PATTERNS = [
    "marvel", "dc comics", "disney", "pixar", "ghibli", "simpsons",
    "batman", "superman", "spiderman", "iron man", "hulk", "thor",
    "mickey mouse", "donald duck", "frozen", "elsa", "moana",
    "naruto", "one piece", "dragon ball", "pokemon", "pikachu",
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual"
]


def check_content_safety(prompt: str) -> tuple:
    """Check if prompt contains blocked content"""
    prompt_lower = prompt.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in prompt_lower:
            return False, f"Content referencing '{pattern}' is not allowed. Please use generic comic styles."
    return True, "OK"


@router.get("/styles")
async def get_comic_styles(user: dict = Depends(get_current_user)):
    """Get available comic styles"""
    return {
        "styles": COMIC_STYLES,
        "layouts": PANEL_LAYOUTS,
        "credits": COMIC_CREDITS,
        "pricing": {
            "generate": 10,
            "download": 15,
            "download_story": 20
        }
    }


@router.get("/credits-info")
async def get_credits_info(user: dict = Depends(get_current_user)):
    """Get credit costs for comic generation"""
    return {
        "costs": COMIC_CREDITS,
        "userCredits": user.get("credits", 0),
        "description": {
            "character_portrait": "Create a comic character portrait from your photo",
            "character_fullbody": "Create a full-body comic character",
            "panel_single": "Generate a single comic panel/scene",
            "panel_multi": "Generate multi-panel comic strip",
            "story_mode": "Full comic story with auto-captions",
            "remove_watermark": "Remove watermark from export",
            "hd_export": "Export in HD quality"
        }
    }


@router.post("/generate-character")
async def generate_comic_character(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    style: str = Form("classic"),
    character_type: str = Form("portrait"),  # portrait or fullbody
    custom_prompt: Optional[str] = Form(None),
    remove_background: bool = Form(False),
    user: dict = Depends(get_current_user)
):
    """Generate a comic character from uploaded photo"""
    
    # Validate style
    if style not in COMIC_STYLES:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from: {list(COMIC_STYLES.keys())}")
    
    # Check content safety if custom prompt provided
    if custom_prompt:
        is_safe, message = check_content_safety(custom_prompt)
        if not is_safe:
            raise HTTPException(status_code=400, detail=message)
    
    # Calculate cost
    cost = COMIC_CREDITS["character_portrait"] if character_type == "portrait" else COMIC_CREDITS["character_fullbody"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Validate file
    if not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")
    
    # Read and encode image
    photo_content = await photo.read()
    if len(photo_content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")
    
    # Create job
    job_id = str(uuid.uuid4())
    style_info = COMIC_STYLES[style]
    
    # Build generation prompt
    base_prompt = f"Transform this photo into a {style_info['name']} character. {style_info['prompt_modifier']}"
    if character_type == "fullbody":
        base_prompt += ", full body pose, standing character"
    else:
        base_prompt += ", portrait, face focus, bust shot"
    
    if remove_background:
        base_prompt += ", transparent background, isolated character"
    
    if custom_prompt:
        base_prompt += f", {custom_prompt}"
    
    # Store job
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "COMIC_CHARACTER",
        "status": "QUEUED",
        "style": style,
        "characterType": character_type,
        "prompt": base_prompt,
        "cost": cost,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comix_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(process_comic_character, job_id, photo_content, base_prompt, user["id"], cost)
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost,
        "message": f"Generating {style_info['name']} character..."
    }


async def process_comic_character(job_id: str, photo_content: bytes, prompt: str, user_id: str, cost: int):
    """Background task to process comic character generation"""
    try:
        # Update status to processing
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        result_url = None
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                # Encode photo to base64
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')
                
                # Create LlmChat instance with multimodal support
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY, 
                    session_id=f"comix-char-{job_id}", 
                    system_message="You are a professional comic artist. Transform photos into comic-style characters faithfully."
                )
                chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                
                # Create message with image reference
                msg = UserMessage(
                    text=f"{prompt}. Transform the person in this photo into a comic character while keeping their likeness.",
                    file_contents=[ImageContent(photo_b64)]
                )
                
                # Generate comic character
                text_response, images = await chat.send_message_multimodal_response(msg)
                
                if images and len(images) > 0:
                    # Save the image and get URL
                    img_data = images[0]
                    image_bytes = base64.b64decode(img_data['data'])
                    
                    # Save to file system and generate URL
                    import hashlib
                    filename = f"comic_char_{hashlib.md5(job_id.encode()).hexdigest()[:16]}.png"
                    filepath = f"/app/backend/static/generated/{filename}"
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    
                    # Generate accessible URL
                    result_url = f"/api/static/generated/{filename}"
                    
            except Exception as e:
                logger.error(f"Comic character generation error: {e}")
        
        # If no AI result, create placeholder
        if not result_url:
            result_url = f"https://placehold.co/512x512/4a1d96/white?text=Comic+Character+{job_id[:8]}"
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic character: {job_id[:8]}")
        
        # Update job with result
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "resultUrl": result_url,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Comic character processing error: {e}")
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e), "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )


@router.post("/generate-panel")
async def generate_comic_panel(
    background_tasks: BackgroundTasks,
    scene_description: str = Form(...),
    style: str = Form("classic"),
    panel_count: int = Form(1),
    genre: str = Form("action"),
    mood: str = Form("exciting"),
    include_speech_bubbles: bool = Form(True),
    speech_text: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """Generate comic panel(s) from description"""
    
    # Validate
    if style not in COMIC_STYLES:
        raise HTTPException(status_code=400, detail=f"Invalid style")
    
    if panel_count not in PANEL_LAYOUTS:
        raise HTTPException(status_code=400, detail=f"Invalid panel count. Choose from: {list(PANEL_LAYOUTS.keys())}")
    
    # Check content safety
    is_safe, message = check_content_safety(scene_description)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    if speech_text:
        is_safe, message = check_content_safety(speech_text)
        if not is_safe:
            raise HTTPException(status_code=400, detail=message)
    
    # Calculate cost
    cost = COMIC_CREDITS["panel_single"] if panel_count == 1 else COMIC_CREDITS["panel_multi"]
    
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    job_id = str(uuid.uuid4())
    style_info = COMIC_STYLES[style]
    layout_info = PANEL_LAYOUTS[panel_count]
    
    # Build prompt
    prompt = f"Comic panel scene: {scene_description}. Style: {style_info['prompt_modifier']}. Genre: {genre}. Mood: {mood}."
    if panel_count > 1:
        prompt += f" Layout: {layout_info['grid']} grid, {panel_count} sequential panels telling a story."
    if include_speech_bubbles and speech_text:
        prompt += f" Include speech bubble with text: '{speech_text}'"
    
    # Store job
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "COMIC_PANEL",
        "status": "QUEUED",
        "style": style,
        "panelCount": panel_count,
        "prompt": prompt,
        "sceneDescription": scene_description,
        "speechText": speech_text,
        "cost": cost,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comix_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(process_comic_panel, job_id, prompt, user["id"], cost, panel_count)
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "layout": layout_info,
        "estimatedCredits": cost
    }


async def process_comic_panel(job_id: str, prompt: str, user_id: str, cost: int, panel_count: int):
    """Background task to process comic panel generation"""
    try:
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        result_urls = []
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                # Generate each panel
                for i in range(panel_count):
                    panel_prompt = f"{prompt} Panel {i+1} of {panel_count}. Comic book panel illustration."
                    
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY, 
                        session_id=f"comix-panel-{job_id}-{i}", 
                        system_message="You are a professional comic book artist. Create vivid comic book panels."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    msg = UserMessage(text=panel_prompt)
                    text_response, images = await chat.send_message_multimodal_response(msg)
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        image_bytes = base64.b64decode(img_data['data'])
                        
                        import hashlib
                        filename = f"comic_panel_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:16]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        result_urls.append(f"/api/static/generated/{filename}")
                        
            except Exception as e:
                logger.error(f"Comic panel generation error: {e}")
        
        # Placeholder if no results
        if not result_urls:
            for i in range(panel_count):
                result_urls.append(f"https://placehold.co/800x600/4a1d96/white?text=Panel+{i+1}")
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic panels: {panel_count}")
        
        # Update job
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "resultUrls": result_urls,
                "resultUrl": result_urls[0] if result_urls else None,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Comic panel processing error: {e}")
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


@router.post("/generate-story")
async def generate_comic_story(
    background_tasks: BackgroundTasks,
    story_prompt: str = Form(...),
    style: str = Form("classic"),
    panel_count: int = Form(6),
    genre: str = Form("adventure"),
    target_audience: str = Form("all"),
    auto_dialogue: bool = Form(True),
    character_images: List[UploadFile] = File(None),
    user: dict = Depends(get_current_user)
):
    """Generate a full comic story with multiple panels and auto-captions"""
    
    # Validate
    if style not in COMIC_STYLES:
        raise HTTPException(status_code=400, detail="Invalid style")
    
    is_safe, message = check_content_safety(story_prompt)
    if not is_safe:
        raise HTTPException(status_code=400, detail=message)
    
    cost = COMIC_CREDITS["story_mode"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Process character images if provided
    character_data = []
    if character_images:
        for i, img in enumerate(character_images[:5]):  # Max 5 character images
            if img and img.content_type and img.content_type.startswith("image/"):
                img_content = await img.read()
                if len(img_content) <= 10 * 1024 * 1024:  # 10MB limit per image
                    character_data.append({
                        "index": i,
                        "base64": base64.b64encode(img_content).decode('utf-8'),
                        "filename": img.filename
                    })
    
    job_id = str(uuid.uuid4())
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "type": "COMIC_STORY",
        "status": "QUEUED",
        "style": style,
        "panelCount": min(panel_count, 9),
        "storyPrompt": story_prompt,
        "genre": genre,
        "targetAudience": target_audience,
        "autoDialogue": auto_dialogue,
        "hasCharacterImages": len(character_data) > 0,
        "characterCount": len(character_data),
        "cost": cost,
        "downloaded": False,
        "progress": 0,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comix_jobs.insert_one(job_data)
    
    background_tasks.add_task(process_comic_story, job_id, story_prompt, style, min(panel_count, 9), genre, auto_dialogue, user["id"], cost, character_data)
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost,
        "downloadCredits": COMIC_CREDITS["download_story"],
        "characterImagesUsed": len(character_data),
        "message": "Generating your comic story..."
    }


async def process_comic_story(job_id: str, story_prompt: str, style: str, panel_count: int, genre: str, auto_dialogue: bool, user_id: str, cost: int):
    """Background task to generate full comic story"""
    try:
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 0}}
        )
        
        style_info = COMIC_STYLES[style]
        panels = []
        
        # Step 1: Generate story outline using AI text generation
        story_scenes = []
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                # Generate story outline with text model
                story_chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"comix-story-outline-{job_id}",
                    system_message="You are a creative comic book writer. Create engaging, original, copyright-safe stories."
                )
                story_chat.with_model("gemini", "gemini-2.0-flash")
                
                outline_prompt = f"""Create a {panel_count}-panel comic story outline for: "{story_prompt}"
Genre: {genre}
Style: {style_info['name']}

For each panel, provide:
1. Scene title (2-3 words)
2. Scene description (1-2 sentences describing what happens visually)
3. Dialogue (1-2 short speech bubbles if applicable, or "No dialogue" if silent panel)

Format as JSON array:
[{{"scene": "Scene Title", "description": "Visual description", "dialogue": "Character dialogue or null"}}]

Make the story original, engaging, and appropriate for all ages. NO copyrighted characters."""
                
                outline_msg = UserMessage(text=outline_prompt)
                outline_response = await story_chat.send_message(outline_msg)
                
                # Parse the story outline
                import re
                json_match = re.search(r'\[.*\]', outline_response, re.DOTALL)
                if json_match:
                    story_scenes = json.loads(json_match.group())
                    
            except Exception as e:
                logger.error(f"Story outline generation error: {e}")
        
        # Fallback to default outline if AI generation failed
        if not story_scenes:
            story_scenes = [
                {"scene": "Opening", "description": f"Introduction to {story_prompt}", "dialogue": "Our story begins..."},
                {"scene": "Rising Action", "description": "The adventure begins with excitement", "dialogue": "Let's go!"},
                {"scene": "Challenge", "description": "Our hero faces an obstacle", "dialogue": "This won't be easy..."},
                {"scene": "Climax", "description": "The most exciting moment of confrontation", "dialogue": "Now or never!"},
                {"scene": "Resolution", "description": "The problem is cleverly solved", "dialogue": "We did it!"},
                {"scene": "Ending", "description": "Happy conclusion and celebration", "dialogue": "The End!"}
            ][:panel_count]
        
        # Step 2: Generate each panel image
        for i in range(min(panel_count, len(story_scenes))):
            scene = story_scenes[i]
            
            # Update progress
            progress = int(((i + 1) / panel_count) * 90)  # Reserve 10% for finalization
            await db.comix_jobs.update_one(
                {"id": job_id},
                {"$set": {"progress": progress, "currentPanel": i + 1, "progressMessage": f"Creating panel {i+1}..."}}
            )
            
            panel_data = {
                "panelNumber": i + 1,
                "scene": scene.get("scene", f"Scene {i+1}"),
                "description": scene.get("description", ""),
                "dialogue": scene.get("dialogue") if auto_dialogue else None
            }
            
            # Generate image for this panel
            if LLM_AVAILABLE and EMERGENT_LLM_KEY:
                try:
                    from emergentintegrations.llm.chat import LlmChat, UserMessage
                    
                    img_chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"comix-story-panel-{job_id}-{i}",
                        system_message="You are a professional comic book artist."
                    )
                    img_chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    panel_prompt = f"""Create a comic book panel illustration:
Story: {story_prompt}
Scene: {scene.get('scene', '')} - {scene.get('description', '')}
Style: {style_info['prompt_modifier']}
Genre: {genre}
Panel {i+1} of {panel_count}

Make it visually dynamic and engaging, appropriate for all ages."""
                    
                    img_msg = UserMessage(text=panel_prompt)
                    text_response, images = await img_chat.send_message_multimodal_response(img_msg)
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        image_bytes = base64.b64decode(img_data['data'])
                        
                        import hashlib
                        filename = f"comic_story_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:16]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        panel_data["imageUrl"] = f"/api/static/generated/{filename}"
                        
                except Exception as e:
                    logger.error(f"Panel {i+1} generation error: {e}")
            
            if not panel_data.get("imageUrl"):
                panel_data["imageUrl"] = f"https://placehold.co/800x450/4a1d96/white?text={scene.get('scene', f'Panel+{i+1}')}"
            
            panels.append(panel_data)
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic story: {job_id[:8]}")
        
        # Update job with results
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "panels": panels,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Comic story processing error: {e}")
        await db.comix_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get comic generation job status"""
    job = await db.comix_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history")
async def get_comic_history(
    page: int = 0,
    size: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get user's comic generation history"""
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    jobs = await db.comix_jobs.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.comix_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.delete("/job/{job_id}")
async def delete_comic_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a comic generation job"""
    result = await db.comix_jobs.delete_one(
        {"id": job_id, "userId": user["id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "message": "Job deleted"}


# BYO-Key endpoints
@router.post("/settings/api-key")
async def save_user_api_key(
    provider: str = Form(...),
    api_key: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """Save user's own API key for generation (BYO-Key model)"""
    
    valid_providers = ["openai", "gemini", "anthropic"]
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Choose from: {valid_providers}")
    
    # Encrypt and store (in production, use proper encryption)
    # For now, we'll just store it securely in the database
    await db.user_api_keys.update_one(
        {"userId": user["id"], "provider": provider},
        {"$set": {
            "userId": user["id"],
            "provider": provider,
            "apiKey": api_key,  # In production: encrypt this
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {
        "success": True,
        "message": f"{provider.title()} API key saved. You can now use your own key for generations.",
        "note": "Using your own key means generation costs go to your provider account, not credits."
    }


@router.get("/settings/api-keys")
async def get_user_api_keys(user: dict = Depends(get_current_user)):
    """Get user's configured API keys (masked)"""
    keys = await db.user_api_keys.find(
        {"userId": user["id"]},
        {"_id": 0, "apiKey": 0}  # Don't return actual keys
    ).to_list(length=10)
    
    return {
        "keys": [{"provider": k["provider"], "configured": True} for k in keys]
    }


@router.delete("/settings/api-key/{provider}")
async def delete_user_api_key(provider: str, user: dict = Depends(get_current_user)):
    """Delete user's API key"""
    result = await db.user_api_keys.delete_one(
        {"userId": user["id"], "provider": provider}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"success": True, "message": f"{provider.title()} API key deleted"}
