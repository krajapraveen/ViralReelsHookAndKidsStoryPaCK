"""
Generation Routes - Reel and Story Generation with ML Threat Detection
CreatorStudio AI Content Generation
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional
import uuid
import json
import httpx
import traceback
import os
import sys
import html

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, check_credits, deduct_credits, log_exception,
    LLM_AVAILABLE, EMERGENT_LLM_KEY, WORKER_URL,
    REEL_SYSTEM_PROMPT, REEL_USER_PROMPT_TEMPLATE,
    STORY_SYSTEM_PROMPT, STORY_USER_PROMPT_TEMPLATE
)
from models.schemas import GenerateReelRequest, GenerateStoryRequest
from ml_threat_detection import threat_intel
from security import log_security_event, limiter

router = APIRouter(prefix="/generate", tags=["Generation"])

# Credit costs
REEL_COST = 10
STORY_COST = 10


async def generate_reel_content_inline(data: dict) -> dict:
    """Generate reel content using LLM"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    unique_id = str(uuid.uuid4())[:8]
    
    prompt = REEL_USER_PROMPT_TEMPLATE.format(
        language=data.get("language", "English"),
        niche=data.get("niche", "General"),
        tone=data.get("tone", "Bold"),
        duration=data.get("duration", "30s"),
        goal=data.get("goal", "Engagement"),
        topic=data.get("topic", ""),
        uniqueId=unique_id
    )
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"reel-{unique_id}",
        system_message=REEL_SYSTEM_PROMPT
    ).with_model("gemini", "gemini-3-flash-preview")
    
    response = await chat.send_message(UserMessage(text=prompt))
    
    # Parse JSON response
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    return json.loads(response_text.strip())


async def generate_story_image(prompt: str, story_id: str, scene_index: int) -> str:
    """Generate an image for a story scene using Gemini Nano Banana"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        import base64
        
        # Enhance prompt for kid-friendly imagery
        full_prompt = f"Children's book illustration, colorful, whimsical, kid-friendly: {prompt}. Pixar-style 3D animation, soft lighting, friendly characters, vibrant colors."
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"story-img-{story_id}-{scene_index}",
            system_message="You are an AI image generator specializing in children's book illustrations."
        ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        msg = UserMessage(text=full_prompt)
        text_response, images = await chat.send_message_multimodal_response(msg)
        
        if images and len(images) > 0:
            # Save image to temp file
            image_bytes = base64.b64decode(images[0]['data'])
            filename = f"story_{story_id}_scene_{scene_index}.png"
            filepath = f"/tmp/{filename}"
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            return f"/api/generate/story-image/{story_id}/{filename}"
        
        return None
    except Exception as e:
        logger.warning(f"Story image generation failed: {e}")
        return None


async def generate_story_content_inline(data: dict, generate_images: bool = True) -> dict:
    """Generate story content using LLM with optional image generation"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    unique_id = str(uuid.uuid4())[:8]
    
    prompt = STORY_USER_PROMPT_TEMPLATE.format(
        genre=data.get("genre", "Adventure"),
        ageGroup=data.get("ageGroup", "4-6"),
        theme=data.get("theme", "Friendship"),
        scenes=data.get("sceneCount", 8),
        customElements=data.get("customGenre", ""),
        uniqueId=unique_id
    )
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"story-{unique_id}",
        system_message=STORY_SYSTEM_PROMPT
    ).with_model("gemini", "gemini-3-flash-preview")
    
    response = await chat.send_message(UserMessage(text=prompt))
    
    # Parse JSON response
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    
    result = json.loads(response_text.strip())
    
    # Generate cover image for the story
    if generate_images and result.get("scenes"):
        # Generate a cover image based on the story title and synopsis
        cover_prompt = f"{result.get('title', 'Story')}: {result.get('synopsis', '')}. Main characters: {', '.join([c.get('name', '') for c in result.get('characters', [])])}"
        cover_image_url = await generate_story_image(cover_prompt, unique_id, 0)
        if cover_image_url:
            result["coverImageUrl"] = cover_image_url
        
        # Generate image for the first scene
        first_scene = result["scenes"][0]
        visual_desc = first_scene.get("visualDescription") or first_scene.get("visual_description") or first_scene.get("sceneTitle", "")
        if visual_desc:
            scene_image_url = await generate_story_image(visual_desc, unique_id, 1)
            if scene_image_url:
                first_scene["imageUrl"] = scene_image_url
    
    return result


@router.post("/reel")
async def generate_reel(data: GenerateReelRequest, user: dict = Depends(get_current_user)):
    """Generate a viral reel script - costs 10 credits"""
    try:
        # Validate topic is not empty
        if not data.topic or not data.topic.strip():
            raise HTTPException(status_code=422, detail="Topic is required and cannot be empty")
        
        # ML-based content moderation
        content_to_check = f"{data.topic} {data.niche} {data.tone}"
        moderation_result = threat_intel.moderate_content(content_to_check, user.get("id"))
        
        if not moderation_result["allowed"]:
            violations = moderation_result.get("violations", [])
            violation_msg = violations[0].get("message") if violations else "Content policy violation"
            
            log_security_event("REEL_CONTENT_BLOCKED", {
                "user_id": user.get("id"),
                "violations": violations,
                "topic": data.topic[:100]
            }, "WARNING")
            
            raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
        
        # Check credits
        await check_credits(user, REEL_COST, "reel generation")
        
        # Generate content
        result = None
        generation_error = None
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                result = await generate_reel_content_inline(data.model_dump())
            except Exception as inline_error:
                logger.warning(f"Inline reel generation failed: {inline_error}")
                generation_error = str(inline_error)
        
        # Fallback to worker
        if result is None and WORKER_URL:
            try:
                async with httpx.AsyncClient(timeout=90.0) as client_http:
                    response = await client_http.post(
                        f"{WORKER_URL}/generate/reel",
                        json=data.model_dump()
                    )
                    if response.status_code == 200:
                        result = response.json()
            except Exception as worker_error:
                logger.warning(f"Worker reel generation failed: {worker_error}")
        
        if result is None:
            error_msg = generation_error or "AI service unavailable. Please try again."
            await log_exception(
                functionality="reel_generation",
                error_type="GENERATION_FAILED",
                error_message=error_msg,
                user_id=user["id"],
                user_email=user.get("email"),
                severity="ERROR"
            )
            raise HTTPException(status_code=503, detail=error_msg)
        
        # Deduct credits
        new_balance = await deduct_credits(
            user["id"],
            REEL_COST,
            f"Reel script generation: {data.topic[:50]}"
        )
        
        # Save generation
        generation_id = str(uuid.uuid4())
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "REEL",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": REEL_COST,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "result": result,
            "creditsUsed": REEL_COST,
            "remainingCredits": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reel generation error: {e}")
        await log_exception(
            functionality="reel_generation",
            error_type="UNEXPECTED_ERROR",
            error_message=str(e),
            user_id=user.get("id"),
            user_email=user.get("email"),
            stack_trace=traceback.format_exc(),
            severity="ERROR"
        )
        raise HTTPException(status_code=500, detail="Generation failed")


@router.post("/story")
async def generate_story(data: GenerateStoryRequest, user: dict = Depends(get_current_user)):
    """Generate a kids story - costs 10 credits"""
    try:
        # ML-based content moderation
        content_to_check = f"{data.theme} {data.genre} {data.customGenre or ''}"
        moderation_result = threat_intel.moderate_content(content_to_check, user.get("id"))
        
        if not moderation_result["allowed"]:
            violations = moderation_result.get("violations", [])
            violation_msg = violations[0].get("message") if violations else "Content policy violation"
            
            log_security_event("STORY_CONTENT_BLOCKED", {
                "user_id": user.get("id"),
                "violations": violations,
                "theme": data.theme[:50]
            }, "WARNING")
            
            raise HTTPException(status_code=400, detail=f"Content blocked: {violation_msg}")
        
        # Check credits
        await check_credits(user, STORY_COST, "story generation")
        
        # Generate content
        result = None
        generation_error = None
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                result = await generate_story_content_inline(data.model_dump())
            except Exception as inline_error:
                logger.warning(f"Inline story generation failed: {inline_error}")
                generation_error = str(inline_error)
        
        # Fallback to worker
        if result is None and WORKER_URL:
            try:
                async with httpx.AsyncClient(timeout=90.0) as client_http:
                    response = await client_http.post(
                        f"{WORKER_URL}/generate/story",
                        json=data.model_dump()
                    )
                    if response.status_code == 200:
                        result = response.json()
            except Exception as worker_error:
                logger.warning(f"Worker story generation failed: {worker_error}")
        
        if result is None:
            error_msg = generation_error or "AI service unavailable. Please try again."
            await log_exception(
                functionality="story_generation",
                error_type="GENERATION_FAILED",
                error_message=error_msg,
                user_id=user["id"],
                user_email=user.get("email"),
                severity="ERROR"
            )
            raise HTTPException(status_code=503, detail=error_msg)
        
        # Deduct credits
        new_balance = await deduct_credits(
            user["id"],
            STORY_COST,
            f"Story generation: {data.genre} - {data.theme[:30]}"
        )
        
        # Save generation
        generation_id = str(uuid.uuid4())
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "STORY",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": STORY_COST,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "result": result,
            "creditsUsed": STORY_COST,
            "remainingCredits": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        await log_exception(
            functionality="story_generation",
            error_type="UNEXPECTED_ERROR",
            error_message=str(e),
            user_id=user.get("id"),
            user_email=user.get("email"),
            stack_trace=traceback.format_exc(),
            severity="ERROR"
        )
        raise HTTPException(status_code=500, detail="Generation failed")


@router.get("/")
async def get_generations(
    type: Optional[str] = None,
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's generation history"""
    skip = page * size
    
    query = {"userId": user["id"]}
    if type:
        query["type"] = type.upper()
    
    generations = await db.generations.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.generations.count_documents(query)
    
    return {
        "generations": generations,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/story-image/{story_id}/{filename}")
async def get_story_image(story_id: str, filename: str):
    """Serve generated story images"""
    from fastapi.responses import FileResponse
    import os
    
    filepath = f"/tmp/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found or expired")
    
    return FileResponse(filepath, media_type="image/png")


@router.get("/{generation_id}")
async def get_generation(generation_id: str, user: dict = Depends(get_current_user)):
    """Get a specific generation by ID"""
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return generation


@router.post("/demo/reel")
async def demo_reel(data: GenerateReelRequest):
    """Demo reel generation without authentication (limited)"""
    try:
        # Content moderation for demo
        content_to_check = f"{data.topic} {data.niche}"
        moderation_result = threat_intel.moderate_content(content_to_check)
        
        if not moderation_result["allowed"]:
            raise HTTPException(status_code=400, detail="Content not allowed for demo")
        
        # Validate topic
        if not data.topic or len(data.topic.strip()) < 3:
            raise HTTPException(status_code=400, detail="Topic must be at least 3 characters")
        
        if len(data.topic) > 500:
            raise HTTPException(status_code=400, detail="Topic must be less than 500 characters")
        
        topic = data.topic.strip()
        niche = data.niche or "General"
        
        # Return generated demo data
        return {
            "success": True,
            "isDemo": True,
            "result": {
                "hooks": [
                    f"Stop! This {niche} secret will change everything about {topic}",
                    f"I wish I knew this {topic} hack sooner - it changed my life",
                    f"The {niche} method nobody talks about for {topic}",
                    f"Why {topic} is the next big thing in {niche}",
                    f"3 seconds to understand {topic} like a pro"
                ],
                "best_hook": f"Stop! This {niche} secret will change everything about {topic}",
                "script": {
                    "scenes": [
                        {"time": "0-3s", "on_screen_text": "The hook", "voiceover": f"What if I told you there's a secret about {topic}...", "broll": ["attention-grabbing visual"]},
                        {"time": "3-10s", "on_screen_text": "The problem", "voiceover": f"Most people struggle with {topic} because they don't know this...", "broll": ["relatable struggle shot"]},
                        {"time": "10-25s", "on_screen_text": "The solution", "voiceover": f"Here's the {niche} approach that actually works...", "broll": ["demonstration visuals"]},
                        {"time": "25-30s", "on_screen_text": "CTA", "voiceover": "Follow for more tips!", "broll": ["engaging outro"]}
                    ],
                    "cta": "Follow for more tips!"
                },
                "caption_short": f"Game-changing {topic} tip! 🔥 #{niche.lower().replace(' ', '')}",
                "caption_long": f"This {topic} insight in {niche} will transform your approach. Most people don't realize how simple it can be once you understand the fundamentals. Save this for later! 💡",
                "hashtags": [f"#{niche.lower().replace(' ', '')}", "#viral", "#trending", f"#{topic.split()[0].lower() if topic.split() else 'tips'}", "#reels"],
                "posting_tips": ["Post between 6-9 PM for best engagement", "Use trending audio to boost reach", "Engage with comments in first hour", "Share to your story"]
            },
            "message": "Sign up for full access with 100 free credits!"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo reel generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed. Please try again.")
