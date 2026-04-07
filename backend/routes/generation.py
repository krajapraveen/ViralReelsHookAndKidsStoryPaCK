"""
Generation Routes - Reel and Story Generation with ML Threat Detection
CreatorStudio AI Content Generation
"""
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
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
    REEL_REFERENCE_SYSTEM_PROMPT, REEL_REFERENCE_USER_PROMPT_TEMPLATE,
    STORY_SYSTEM_PROMPT, STORY_USER_PROMPT_TEMPLATE
)
from models.schemas import GenerateReelRequest, GenerateStoryRequest
from ml_threat_detection import threat_intel
from security import log_security_event, limiter, rate_limit_generation
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config
from services.rewrite_engine import safe_rewrite

router = APIRouter(prefix="/generate", tags=["Generation"])

# Credit costs
REEL_COST = 1
STORY_COST = 1


async def generate_reel_content_inline(data: dict) -> dict:
    """Generate reel content using LLM with automatic retry"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import asyncio
    
    unique_id = str(uuid.uuid4())[:8]
    max_retries = 3
    attempt = 0
    last_error = None
    
    # Check if this is a reference-based generation
    ref_url = data.get("reference_url")
    ref_text = data.get("reference_text")
    is_reference_mode = bool(ref_url or ref_text)
    
    # If reference URL provided, try to extract content
    reference_content = ""
    if ref_url:
        extracted = await extract_url_content(ref_url)
        if extracted:
            reference_content = extracted
        elif ref_text:
            # URL failed but we have fallback text
            reference_content = ref_text
            logger.info("URL extraction failed, falling back to provided text")
        else:
            # URL failed and no text fallback — still proceed with topic only
            is_reference_mode = False
            logger.warning(f"URL extraction failed for {ref_url}, falling back to standard generation")
    elif ref_text:
        reference_content = ref_text
    
    while attempt <= max_retries:
        try:
            if attempt > 0:
                logger.info(f"Retrying reel generation, attempt {attempt + 1}")
                await asyncio.sleep(min(3 * (2 ** attempt), 30))
            
            if is_reference_mode and reference_content:
                # Reference-based generation
                prompt = REEL_REFERENCE_USER_PROMPT_TEMPLATE.format(
                    reference_content=reference_content[:3000],
                    reference_notes=data.get("reference_notes", "No specific notes provided"),
                    language=data.get("language", "English"),
                    niche=data.get("niche", "General"),
                    tone=data.get("tone", "Bold"),
                    duration=data.get("duration", "30s"),
                    goal=data.get("goal", "Engagement"),
                    topic=data.get("topic", ""),
                    platform=data.get("platform", "Instagram"),
                    hookStyle=data.get("hookStyle", "Curiosity"),
                    reelFormat=data.get("reelFormat", "Talking Head"),
                    ctaType=data.get("ctaType", "Follow"),
                    audience=data.get("audience", "General"),
                    outputType=data.get("outputType", "full_plan"),
                    uniqueId=unique_id
                )
                system_prompt = REEL_REFERENCE_SYSTEM_PROMPT
            else:
                # Standard generation
                prompt = REEL_USER_PROMPT_TEMPLATE.format(
                    language=data.get("language", "English"),
                    niche=data.get("niche", "General"),
                    tone=data.get("tone", "Bold"),
                    duration=data.get("duration", "30s"),
                    goal=data.get("goal", "Engagement"),
                    topic=data.get("topic", ""),
                    platform=data.get("platform", "Instagram"),
                    hookStyle=data.get("hookStyle", "Curiosity"),
                    reelFormat=data.get("reelFormat", "Talking Head"),
                    ctaType=data.get("ctaType", "Follow"),
                    audience=data.get("audience", "General"),
                    outputType=data.get("outputType", "full_plan"),
                    uniqueId=unique_id
                )
                system_prompt = REEL_SYSTEM_PROMPT
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"reel-{unique_id}-{attempt}",
                system_message=system_prompt
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
            
            # Mark if this was reference-based
            if is_reference_mode:
                result["is_reference_based"] = True
                result["reference_source"] = "url" if ref_url and reference_content != ref_text else "text"
            
            if attempt > 0:
                logger.info(f"Reel generation succeeded after {attempt + 1} attempts")
            
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"Reel generation attempt {attempt + 1} failed: {e}")
            attempt += 1
    
    # All retries exhausted
    logger.error(f"Reel generation failed after {max_retries + 1} attempts: {last_error}")
    raise last_error


async def extract_url_content(url: str) -> str:
    """Extract text content from a URL for reference analysis.
    Returns extracted text or empty string on failure."""
    import re
    
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client_http:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; CreatorStudioBot/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            response = await client_http.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"URL fetch returned status {response.status_code} for {url}")
                return ""
            
            content_type = response.headers.get("content-type", "")
            
            # Only process text/html content
            if "text/html" not in content_type and "text/plain" not in content_type:
                logger.warning(f"Non-text content type {content_type} for {url}")
                return ""
            
            html_content = response.text
            
            # Strip HTML tags to get raw text
            # Remove script/style blocks first
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<nav[^>]*>.*?</nav>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<footer[^>]*>.*?</footer>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<header[^>]*>.*?</header>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract meta description and og:description
            meta_desc = ""
            meta_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            if meta_match:
                meta_desc = meta_match.group(1)
            og_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            if og_match:
                meta_desc = og_match.group(1) or meta_desc
            
            # Extract title
            title = ""
            title_match = re.search(r'<title[^>]*>([^<]*)</title>', html_content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
            
            # Strip remaining HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            # Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Build reference content
            parts = []
            if title:
                parts.append(f"Title: {title}")
            if meta_desc:
                parts.append(f"Description: {meta_desc}")
            if text:
                # Take first 2500 chars of body text
                parts.append(f"Content: {text[:2500]}")
            
            extracted = "\n".join(parts)
            
            if len(extracted) < 20:
                logger.warning(f"Extracted content too short from {url}")
                return ""
            
            logger.info(f"Extracted {len(extracted)} chars from URL {url}")
            return extracted
            
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching URL {url}")
        return ""
    except Exception as e:
        logger.warning(f"URL extraction error for {url}: {e}")
        return ""


async def generate_story_image(prompt: str, story_id: str, scene_index: int, user_plan: str = "free") -> str:
    """Generate an image for a story scene using Gemini Nano Banana with automatic retry"""
    import base64
    import asyncio
    
    max_retries = 1
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            if attempt > 0:
                logger.info(f"Retrying story image generation for scene {scene_index}, attempt {attempt + 1}")
                await asyncio.sleep(2)
            
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            # Enhance prompt for kid-friendly imagery
            full_prompt = f"Children's book illustration, colorful, whimsical, kid-friendly: {prompt}. Modern 3D animation style, soft lighting, friendly characters, vibrant colors."
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"story-img-{story_id}-{scene_index}-{attempt}",
                system_message="You are an AI image generator specializing in children's book illustrations."
            ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
            
            msg = UserMessage(text=full_prompt)
            text_response, images = await asyncio.wait_for(
                chat.send_message_multimodal_response(msg),
                timeout=30.0
            )
            
            if images and len(images) > 0:
                # Handle both dict and string image formats
                img = images[0]
                if isinstance(img, dict):
                    img_data = img.get('data', '')
                elif isinstance(img, str):
                    img_data = img.split('base64,')[1] if 'base64,' in img else img
                else:
                    raise Exception(f"Unexpected image format: {type(img)}")

                image_bytes = base64.b64decode(img_data)
                
                # Apply watermark for free users
                if should_apply_watermark({"plan": user_plan}):
                    config = get_watermark_config("STORY")
                    image_bytes = add_diagonal_watermark(
                        image_bytes,
                        text=config["text"],
                        opacity=config["opacity"],
                        font_size=config["font_size"],
                        spacing=config["spacing"]
                    )
                
                filename = f"story_{story_id}_scene_{scene_index}.png"
                filepath = f"/tmp/{filename}"
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                
                if attempt > 0:
                    logger.info(f"Story image generation succeeded after {attempt + 1} attempts")
                
                return f"/api/generate/story-image/{story_id}/{filename}"
            
            raise Exception("No image was generated")
            
        except Exception as e:
            last_error = e
            logger.warning(f"Story image generation attempt {attempt + 1} failed: {e}")
            attempt += 1
    
    # All retries exhausted - return None (graceful degradation)
    logger.warning(f"Story image generation failed for scene {scene_index}: {last_error}")
    return None


async def generate_story_content_inline(data: dict, generate_images: bool = True, user_plan: str = "free") -> dict:
    """Generate story content using LLM with optional image generation and automatic retry"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import asyncio
    
    unique_id = str(uuid.uuid4())[:8]
    max_retries = 3
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            if attempt > 0:
                logger.info(f"Retrying story content generation, attempt {attempt + 1}")
                await asyncio.sleep(min(3 * (2 ** attempt), 30))
            
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
                session_id=f"story-{unique_id}-{attempt}",
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
            
            if attempt > 0:
                logger.info(f"Story content generation succeeded after {attempt + 1} attempts")
            
            # Generate cover image for the story (with built-in retry in generate_story_image)
            if generate_images and result.get("scenes"):
                # Generate a cover image based on the story title and synopsis
                characters = result.get('characters', [])
                char_names = ', '.join([
                    c.get('name', '') if isinstance(c, dict) else str(c)
                    for c in characters
                ]) if characters else ''
                cover_prompt = f"{result.get('title', 'Story')}: {result.get('synopsis', '')}. Main characters: {char_names}"
                cover_image_url = await generate_story_image(cover_prompt, unique_id, 0, user_plan)
                if cover_image_url:
                    result["coverImageUrl"] = cover_image_url
                
                # Generate image for the first scene
                first_scene = result["scenes"][0]
                visual_desc = first_scene.get("visualDescription") or first_scene.get("visual_description") or first_scene.get("sceneTitle", "")
                if visual_desc:
                    scene_image_url = await generate_story_image(visual_desc, unique_id, 1, user_plan)
                    if scene_image_url:
                        first_scene["imageUrl"] = scene_image_url
            
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"Story content generation attempt {attempt + 1} failed: {e}")
            attempt += 1
    
    # All retries exhausted
    logger.error(f"Story content generation failed after {max_retries + 1} attempts: {last_error}")
    raise last_error


@router.post("/reel", dependencies=[Depends(rate_limit_generation)])
async def generate_reel(request: Request, data: GenerateReelRequest, user: dict = Depends(get_current_user)):
    """Generate a viral reel script - costs 10 credits"""
    try:
        # Sanitize input to prevent XSS
        sanitized_topic = html.escape(data.topic.strip())
        
        # Validate topic is not empty
        if not sanitized_topic:
            raise HTTPException(status_code=422, detail="Topic is required and cannot be empty")
        
        # Update data with sanitized topic
        data.topic = sanitized_topic
        
        # Full safety pipeline — sanitize risky terms
        from services.rewrite_engine import check_and_rewrite
        safety = await check_and_rewrite(user.get("id", ""), "reel_generation", data, ["topic", "niche", "tone"])
        if safety.blocked:
            raise HTTPException(status_code=400, detail=safety.block_reason)
        
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


async def generate_story_images_background(result: dict, generation_id: str, user_plan: str = "free"):
    """Generate story images in the background after text has been returned"""
    try:
        unique_id = generation_id[:8]
        updated = False

        if result.get("scenes"):
            characters = result.get('characters', [])
            char_names = ', '.join([
                c.get('name', '') if isinstance(c, dict) else str(c)
                for c in characters
            ]) if characters else ''
            cover_prompt = f"{result.get('title', 'Story')}: {result.get('synopsis', '')}. Main characters: {char_names}"
            cover_url = await generate_story_image(cover_prompt, unique_id, 0, user_plan)
            if cover_url:
                result["coverImageUrl"] = cover_url
                updated = True

            first_scene = result["scenes"][0]
            visual_desc = first_scene.get("visualDescription") or first_scene.get("visual_description") or first_scene.get("sceneTitle", "")
            if visual_desc:
                scene_url = await generate_story_image(visual_desc, unique_id, 1, user_plan)
                if scene_url:
                    first_scene["imageUrl"] = scene_url
                    updated = True

        if updated:
            await db.generations.update_one(
                {"id": generation_id},
                {"$set": {"outputJson": result, "imagesGenerated": True}}
            )
            logger.info(f"Background images generated for story {generation_id}")
    except Exception as e:
        logger.error(f"Background image generation failed for {generation_id}: {e}")


@router.post("/story")
async def generate_story(request: Request, data: GenerateStoryRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Generate a kids story - costs 10 credits"""
    try:
        # Full safety pipeline — sanitize risky terms
        from services.rewrite_engine import check_and_rewrite
        safety = await check_and_rewrite(user.get("id", ""), "story_generation", data, ["theme", "genre", "customGenre"])
        if safety.blocked:
            raise HTTPException(status_code=400, detail=safety.block_reason)
        
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
        
        # Generate content WITHOUT images first (fast, <15s)
        result = None
        generation_error = None
        user_plan = user.get("plan", "free")
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                result = await generate_story_content_inline(data.model_dump(), generate_images=False, user_plan=user_plan)
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
        
        # Generate images in background (non-blocking)
        if LLM_AVAILABLE and EMERGENT_LLM_KEY and result.get("scenes"):
            background_tasks.add_task(
                generate_story_images_background,
                result=result,
                generation_id=generation_id,
                user_plan=user_plan
            )
        
        return {
            "success": True,
            "status": "COMPLETED",
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
        
        # SECURITY FIX: Sanitize inputs to prevent XSS
        topic = html.escape(data.topic.strip())
        niche = html.escape(data.niche or "General")
        
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
            "message": "Sign up for full access with 50 free credits!"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo reel generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed. Please try again.")
