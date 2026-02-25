"""
Optimized Background Workers for Fast Generation
CreatorStudio AI - Performance Optimized

Features:
- Parallel processing with asyncio
- Progress tracking at granular level
- Worker pool for load balancing
- Caching for faster generation
- Optimized prompts for speed
"""
import asyncio
import os
import sys
import base64
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import functools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import db, logger, LLM_AVAILABLE, EMERGENT_LLM_KEY

# Thread pool for CPU-bound operations
THREAD_POOL = ThreadPoolExecutor(max_workers=4)

# Generation cache for faster repeated generations
GENERATION_CACHE: Dict[str, str] = {}
CACHE_MAX_SIZE = 100


async def update_job_progress(collection: str, job_id: str, progress: int, message: str, status: str = None):
    """Update job progress in database - optimized single update"""
    update_data = {
        "progress": progress,
        "progressMessage": message,
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    if status:
        update_data["status"] = status
    
    await db[collection].update_one(
        {"id": job_id},
        {"$set": update_data}
    )


async def generate_image_fast(prompt: str, session_id: str, photo_b64: str = None) -> Optional[bytes]:
    """
    Generate image with optimized settings for speed.
    Uses simpler prompts and faster model parameters.
    """
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        return None
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message="Fast image generation. Be concise."
        )
        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        if photo_b64:
            msg = UserMessage(
                text=prompt,
                file_contents=[ImageContent(photo_b64)]
            )
        else:
            msg = UserMessage(text=prompt)
        
        text_response, images = await chat.send_message_multimodal_response(msg)
        
        if images and len(images) > 0:
            return base64.b64decode(images[0]['data'])
        
        return None
        
    except Exception as e:
        logger.error(f"Fast image generation error: {e}")
        return None


async def generate_images_parallel(prompts: List[Dict], photo_b64: str = None, max_concurrent: int = 3) -> List[Optional[bytes]]:
    """
    Generate multiple images in parallel for faster processing.
    Uses semaphore to limit concurrent API calls.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def generate_with_semaphore(prompt_data: Dict) -> Optional[bytes]:
        async with semaphore:
            return await generate_image_fast(
                prompt_data["prompt"],
                prompt_data["session_id"],
                photo_b64
            )
    
    tasks = [generate_with_semaphore(p) for p in prompts]
    return await asyncio.gather(*tasks)


def save_image_sync(image_bytes: bytes, filepath: str) -> bool:
    """Synchronous image save for thread pool"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        return True
    except Exception as e:
        logger.error(f"Save image error: {e}")
        return False


async def save_image_async(image_bytes: bytes, filepath: str) -> bool:
    """Async wrapper for image saving using thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(THREAD_POOL, save_image_sync, image_bytes, filepath)


async def create_gif_optimized(frames: List[str], output_path: str, duration: int = 150) -> bool:
    """Create animated GIF from frames - optimized for speed"""
    try:
        from PIL import Image
        
        loop = asyncio.get_event_loop()
        
        def create_gif_sync():
            try:
                images = []
                for path in frames:
                    if os.path.exists(path):
                        img = Image.open(path)
                        img = img.resize((512, 512), Image.Resampling.BILINEAR)  # BILINEAR is faster than LANCZOS
                        images.append(img)
                
                if not images:
                    return False
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    duration=duration,
                    loop=0,
                    optimize=True  # Optimize GIF size
                )
                return True
            except Exception as e:
                logger.error(f"GIF creation error: {e}")
                return False
        
        return await loop.run_in_executor(THREAD_POOL, create_gif_sync)
        
    except Exception as e:
        logger.error(f"GIF optimized creation error: {e}")
        return False


async def create_bounce_gif_fast(photo_content: bytes, output_path: str, emotion: str = "happy") -> bool:
    """Create a quick bounce animation GIF from photo"""
    try:
        from PIL import Image
        import io
        
        loop = asyncio.get_event_loop()
        
        def create_bounce_sync():
            try:
                img = Image.open(io.BytesIO(photo_content))
                img = img.resize((512, 512), Image.Resampling.BILINEAR)
                
                frames = []
                # Simpler bounce with fewer frames for speed
                offsets = [0, -8, -12, -8, 0, 4, 0]
                
                for offset in offsets:
                    frame = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
                    paste_y = max(0, min(offset + 12, 24))
                    resized = img.resize((488, 488), Image.Resampling.BILINEAR)
                    frame.paste(resized, (12, paste_y))
                    frames.append(frame)
                
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=100,
                    loop=0,
                    optimize=True
                )
                return True
            except Exception as e:
                logger.error(f"Bounce GIF error: {e}")
                return False
        
        return await loop.run_in_executor(THREAD_POOL, create_bounce_sync)
        
    except Exception as e:
        logger.error(f"Bounce GIF creation error: {e}")
        return False


# Progress step configurations for each generation type
PROGRESS_STEPS = {
    "gif": {
        "start": {"progress": 5, "message": "Initializing..."},
        "processing": {"progress": 15, "message": "Processing image..."},
        "generating": {"progress": 30, "message": "Generating animation frames..."},
        "frame_base": 30,
        "frame_range": 50,  # Progress from 30 to 80
        "assembling": {"progress": 85, "message": "Assembling GIF..."},
        "finalizing": {"progress": 95, "message": "Finalizing..."},
        "complete": {"progress": 100, "message": "Complete!"}
    },
    "comic_character": {
        "start": {"progress": 5, "message": "Analyzing photo..."},
        "processing": {"progress": 20, "message": "Processing character..."},
        "generating": {"progress": 40, "message": "Generating comic style..."},
        "enhancing": {"progress": 70, "message": "Enhancing details..."},
        "finalizing": {"progress": 90, "message": "Finalizing character..."},
        "complete": {"progress": 100, "message": "Character ready!"}
    },
    "comic_panel": {
        "start": {"progress": 5, "message": "Creating scene..."},
        "layout": {"progress": 20, "message": "Designing panel layout..."},
        "generating": {"progress": 40, "message": "Generating artwork..."},
        "bubbles": {"progress": 70, "message": "Adding speech bubbles..."},
        "effects": {"progress": 85, "message": "Adding effects..."},
        "complete": {"progress": 100, "message": "Panel complete!"}
    },
    "comic_story": {
        "start": {"progress": 5, "message": "Planning story..."},
        "script": {"progress": 15, "message": "Writing script..."},
        "layout": {"progress": 25, "message": "Creating layouts..."},
        "panel_base": 25,
        "panel_range": 60,  # Progress from 25 to 85
        "assembly": {"progress": 90, "message": "Assembling story..."},
        "complete": {"progress": 100, "message": "Story complete!"}
    },
    "storybook": {
        "start": {"progress": 5, "message": "Reading story..."},
        "parsing": {"progress": 15, "message": "Parsing scenes..."},
        "illustrating_base": 15,
        "illustrating_range": 70,  # Progress from 15 to 85
        "layout": {"progress": 88, "message": "Creating book layout..."},
        "pdf": {"progress": 95, "message": "Generating PDF..."},
        "complete": {"progress": 100, "message": "Storybook ready!"}
    }
}


def get_progress_for_step(gen_type: str, step: str, current_item: int = 0, total_items: int = 1) -> tuple:
    """Get progress percentage and message for a generation step"""
    steps = PROGRESS_STEPS.get(gen_type, PROGRESS_STEPS["gif"])
    
    if step in steps:
        step_data = steps[step]
        return step_data["progress"], step_data["message"]
    
    # Handle dynamic progress for frame/panel generation
    if step == "frame" and "frame_base" in steps:
        base = steps["frame_base"]
        range_val = steps["frame_range"]
        progress = base + int((current_item / max(total_items, 1)) * range_val)
        return progress, f"Generating frame {current_item}/{total_items}..."
    
    if step == "panel" and "panel_base" in steps:
        base = steps["panel_base"]
        range_val = steps["panel_range"]
        progress = base + int((current_item / max(total_items, 1)) * range_val)
        return progress, f"Creating panel {current_item}/{total_items}..."
    
    if step == "illustrating" and "illustrating_base" in steps:
        base = steps["illustrating_base"]
        range_val = steps["illustrating_range"]
        progress = base + int((current_item / max(total_items, 1)) * range_val)
        return progress, f"Illustrating page {current_item}/{total_items}..."
    
    return 50, "Processing..."


# Cleanup old thread pool on module reload
def cleanup():
    """Cleanup resources on shutdown"""
    THREAD_POOL.shutdown(wait=False)


# Export for use in other modules
__all__ = [
    'update_job_progress',
    'generate_image_fast',
    'generate_images_parallel',
    'save_image_async',
    'create_gif_optimized',
    'create_bounce_gif_fast',
    'get_progress_for_step',
    'PROGRESS_STEPS',
    'THREAD_POOL'
]
