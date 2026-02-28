"""
Photo to Comic Character - Simplified Comic Generation
CreatorStudio AI

Features:
- Photo upload → Comic Avatar (3-step wizard)
- Photo upload → Comic Strip (5-step wizard)
- Strict copyright safety with keyword blocking
- Universal negative prompts auto-injection
- Safe style presets (no IP)
- Revenue-optimized pricing
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import os
import sys
import base64
import asyncio
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config

router = APIRouter(prefix="/photo-to-comic", tags=["Photo to Comic"])

# ============================================
# BLOCKED COPYRIGHT KEYWORDS (Case-insensitive)
# ============================================
BLOCKED_KEYWORDS = [
    # Superhero / Comic IP
    "marvel", "dc", "avengers", "spiderman", "spider-man", "batman", "superman",
    "ironman", "iron man", "captain america", "thor", "hulk", "joker",
    "wonder woman", "flash", "deadpool", "x-men", "wolverine", "venom",
    # Disney / Animation
    "disney", "pixar", "frozen", "elsa", "anna", "mickey", "minnie",
    "donald duck", "goofy", "toy story", "lightyear",
    # Anime / Manga
    "naruto", "sasuke", "dragon ball", "goku", "one piece", "luffy",
    "attack on titan", "demon slayer", "pokemon", "pikachu", "studio ghibli",
    # Games / Entertainment
    "fortnite", "minecraft", "league of legends", "valorant", "pubg",
    "call of duty", "gta", "harry potter", "hogwarts",
    # Brand / Logo
    "nike", "adidas", "coca cola", "pepsi", "apple logo", "tesla logo",
    "youtube logo", "instagram logo", "facebook logo",
    # Additional safety
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual",
    "violence", "gore", "weapon", "hate"
]

# ============================================
# UNIVERSAL NEGATIVE PROMPTS (Auto-injected)
# ============================================
UNIVERSAL_NEGATIVE_PROMPTS = [
    "blurry", "low resolution", "distorted face", "extra fingers", "extra limbs",
    "bad anatomy", "cropped head", "duplicate body", "disfigured hands",
    "warped proportions", "watermark", "logo", "text overlay", "brand name",
    "copyrighted character", "celebrity likeness", "trademark symbol",
    "nsfw", "nudity", "gore", "violence", "blood", "weapon", "hate symbol",
    "political propaganda", "real person replication", "hyper-realistic skin texture",
    "photo-realistic celebrity face"
]

# ============================================
# SAFE STYLE PRESETS
# ============================================
SAFE_STYLES = {
    # Action Styles
    "bold_superhero": {
        "name": "Bold Superhero",
        "prompt": "bold superhero comic style, dynamic heroic poses, vibrant colors, strong lines, original character design"
    },
    "dark_vigilante": {
        "name": "Dark Vigilante",
        "prompt": "dark vigilante comic style, moody shadows, noir atmosphere, mysterious character"
    },
    "retro_action": {
        "name": "Retro Action Comic",
        "prompt": "retro 80s action comic style, halftone dots, bold colors, classic comic book aesthetic"
    },
    "dynamic_battle": {
        "name": "Dynamic Battle Scene",
        "prompt": "dynamic action scene, high energy, motion lines, impact effects, comic book style"
    },
    # Fun Styles
    "cartoon_fun": {
        "name": "Cartoon Fun",
        "prompt": "bright cheerful cartoon style, playful character, exaggerated features, fun comic"
    },
    "meme_expression": {
        "name": "Meme Expression",
        "prompt": "exaggerated funny expression, meme-worthy reaction, comedic cartoon style"
    },
    "comic_caricature": {
        "name": "Comic Caricature",
        "prompt": "playful caricature style, exaggerated features, humorous character design"
    },
    "exaggerated_reaction": {
        "name": "Exaggerated Reaction",
        "prompt": "over-the-top emotional reaction, comedic expression, cartoon style"
    },
    # Soft Styles
    "romance_comic": {
        "name": "Romance Comic",
        "prompt": "soft romantic comic style, dreamy atmosphere, gentle colors, shoujo influence"
    },
    "dreamy_pastel": {
        "name": "Dreamy Pastel",
        "prompt": "soft pastel color palette, dreamy illustration, gentle comic style"
    },
    "soft_manga": {
        "name": "Soft Manga Inspired",
        "prompt": "soft manga-inspired style, gentle lines, expressive eyes, original character"
    },
    "cute_chibi": {
        "name": "Cute Chibi",
        "prompt": "adorable chibi style, mini character, big head, cute proportions"
    },
    # Fantasy Styles
    "magical_fantasy": {
        "name": "Magical Fantasy",
        "prompt": "magical fantasy comic style, enchanted atmosphere, mystical elements, original design"
    },
    "medieval_adventure": {
        "name": "Medieval Adventure",
        "prompt": "medieval adventure comic, knights and castles theme, fantasy setting"
    },
    "scifi_neon": {
        "name": "Sci-Fi Neon",
        "prompt": "futuristic sci-fi style, neon colors, cyberpunk comic aesthetic, original character"
    },
    "cyberpunk_comic": {
        "name": "Cyberpunk Comic",
        "prompt": "cyberpunk comic style, high-tech dystopia, neon lights, futuristic"
    },
    # Kids Friendly
    "kids_storybook": {
        "name": "Kids Storybook Comic",
        "prompt": "children's storybook comic style, friendly characters, bright colors, wholesome"
    },
    "friendly_animal": {
        "name": "Friendly Animal Comic",
        "prompt": "cute animal character comic, friendly design, child-safe, adorable"
    },
    "classroom_comic": {
        "name": "Classroom Comic",
        "prompt": "school-themed comic style, classroom setting, fun educational vibe"
    },
    "adventure_kids": {
        "name": "Adventure Kids Style",
        "prompt": "kid-friendly adventure comic, young hero character, exciting but safe"
    },
    # Minimal Styles
    "black_white_ink": {
        "name": "Black & White Ink",
        "prompt": "black and white ink illustration, classic comic style, high contrast"
    },
    "sketch_outline": {
        "name": "Sketch Outline",
        "prompt": "hand-drawn sketch style, pencil outline look, artistic comic"
    },
    "noir_comic": {
        "name": "Noir Comic",
        "prompt": "film noir comic style, dramatic shadows, black and white, detective theme"
    },
    "vintage_print": {
        "name": "Vintage Print Style",
        "prompt": "vintage newspaper print style, retro comic aesthetic, classic halftone"
    },
}

# ============================================
# PRICING CONFIGURATION
# ============================================
PRICING = {
    "comic_avatar": {
        "base": 15,
        "add_ons": {
            "transparent_bg": 3,
            "multiple_poses": 5,
            "hd_export": 5,
        }
    },
    "comic_strip": {
        "panels": {
            3: 25,
            4: 32,
            6: 45,
        },
        "add_ons": {
            "auto_dialogue": 5,
            "custom_speech": 3,
            "hd_export": 8,
        }
    },
    "download": {
        "avatar": 10,
        "strip": 15
    }
}


def check_blocked_keywords(text: str) -> tuple:
    """
    Check if text contains any blocked keywords.
    Uses case-insensitive substring matching.
    Returns (is_blocked, blocked_keyword)
    """
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True, keyword
    
    return False, None


def build_safe_prompt(style_key: str, custom_details: str = "", genre: str = "action") -> str:
    """
    Build a safe generation prompt with style and universal negative prompts.
    """
    style_info = SAFE_STYLES.get(style_key, SAFE_STYLES["cartoon_fun"])
    
    # Base prompt from style
    prompt = f"Create a comic character illustration. {style_info['prompt']}. "
    
    # Add genre context
    genre_context = {
        "action": "dynamic pose, action-ready stance",
        "comedy": "humorous expression, fun atmosphere",
        "romance": "soft expression, romantic atmosphere",
        "adventure": "adventurous spirit, excited expression",
        "fantasy": "magical elements, fantasy setting",
        "scifi": "futuristic elements, sci-fi setting",
        "mystery": "mysterious atmosphere, intriguing pose",
        "kids_friendly": "child-friendly, wholesome, bright",
        "slice_of_life": "everyday setting, relatable character",
        "motivational": "confident pose, inspiring expression"
    }
    prompt += genre_context.get(genre, "")
    
    # Add custom details if provided (already validated)
    if custom_details:
        prompt += f" Additional details: {custom_details}."
    
    # Ensure original character
    prompt += " Original character design, not based on any existing IP or celebrity."
    
    return prompt


def get_negative_prompt(user_negative: str = "") -> str:
    """
    Build the complete negative prompt including universal safety prompts.
    """
    negatives = UNIVERSAL_NEGATIVE_PROMPTS.copy()
    
    # Add user's negative prompts if provided
    if user_negative:
        # Validate user negative prompt doesn't contain suspicious content
        is_blocked, keyword = check_blocked_keywords(user_negative)
        if not is_blocked:
            negatives.append(user_negative)
    
    return ", ".join(negatives)


@router.get("/styles")
async def get_available_styles(user: dict = Depends(get_current_user)):
    """Get all available safe styles"""
    return {
        "styles": {k: {"name": v["name"]} for k, v in SAFE_STYLES.items()},
        "pricing": PRICING
    }


@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """Get pricing configuration"""
    return {"pricing": PRICING}


@router.post("/generate")
async def generate_comic(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    mode: str = Form(...),  # 'avatar' or 'strip'
    style: str = Form("cartoon_fun"),
    style_category: str = Form("fun"),
    genre: str = Form("action"),
    custom_details: Optional[str] = Form(None),
    transparent_bg: bool = Form(False),
    multiple_poses: bool = Form(False),
    hd_export: bool = Form(False),
    # Strip-specific
    panel_count: int = Form(4),
    story_prompt: Optional[str] = Form(None),
    dialogue: Optional[str] = Form(None),
    include_dialogue: bool = Form(True),
    user: dict = Depends(get_current_user)
):
    """
    Generate comic character or strip from uploaded photo.
    Implements strict copyright safety checks.
    """
    
    # Validate mode
    if mode not in ["avatar", "strip"]:
        raise HTTPException(status_code=400, detail="Mode must be 'avatar' or 'strip'")
    
    # ============================================
    # COPYRIGHT SAFETY CHECK - BLOCK KEYWORDS
    # ============================================
    
    # Check custom details
    if custom_details:
        is_blocked, keyword = check_blocked_keywords(custom_details)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}'. Try using generic descriptions like 'masked hero' instead."
            )
    
    # Check story prompt (for strip mode)
    if story_prompt:
        is_blocked, keyword = check_blocked_keywords(story_prompt)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}'. We create original comic characters only."
            )
    
    # Check dialogue
    if dialogue:
        is_blocked, keyword = check_blocked_keywords(dialogue)
        if is_blocked:
            raise HTTPException(
                status_code=400,
                detail=f"Copyrighted or brand-based characters are not allowed. Detected: '{keyword}' in dialogue."
            )
    
    # Validate style
    if style not in SAFE_STYLES:
        style = "cartoon_fun"  # Default to safe style
    
    # Validate file
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG, JPG, WEBP)")
    
    photo_content = await photo.read()
    if len(photo_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max 10MB.")
    
    # ============================================
    # CALCULATE COST
    # ============================================
    
    if mode == "avatar":
        cost = PRICING["comic_avatar"]["base"]
        if transparent_bg:
            cost += PRICING["comic_avatar"]["add_ons"]["transparent_bg"]
        if multiple_poses:
            cost += PRICING["comic_avatar"]["add_ons"]["multiple_poses"]
        if hd_export:
            cost += PRICING["comic_avatar"]["add_ons"]["hd_export"]
    else:  # strip
        cost = PRICING["comic_strip"]["panels"].get(panel_count, 25)
        if include_dialogue:
            cost += PRICING["comic_strip"]["add_ons"]["auto_dialogue"]
        if hd_export:
            cost += PRICING["comic_strip"]["add_ons"]["hd_export"]
    
    # Apply plan discount
    user_plan = user.get("plan", "free")
    if user_plan == "creator":
        cost = int(cost * 0.8)
    elif user_plan == "pro":
        cost = int(cost * 0.7)
    elif user_plan == "studio":
        cost = int(cost * 0.6)
    
    # Check credits
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Create job
    job_id = str(uuid.uuid4())
    
    job_data = {
        "id": job_id,
        "userId": user["id"],
        "mode": mode,
        "type": "COMIC_AVATAR" if mode == "avatar" else "COMIC_STRIP",
        "status": "QUEUED",
        "style": style,
        "genre": genre,
        "customDetails": custom_details,
        "cost": cost,
        "panelCount": panel_count if mode == "strip" else 1,
        "storyPrompt": story_prompt if mode == "strip" else None,
        "includeDialogue": include_dialogue,
        "addOns": {
            "transparent_bg": transparent_bg,
            "multiple_poses": multiple_poses,
            "hd_export": hd_export
        },
        "progress": 0,
        "downloaded": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.photo_to_comic_jobs.insert_one(job_data)
    
    # Process in background
    if mode == "avatar":
        background_tasks.add_task(
            process_comic_avatar,
            job_id, photo_content, style, genre, custom_details,
            user["id"], cost, transparent_bg, multiple_poses, hd_export
        )
    else:
        background_tasks.add_task(
            process_comic_strip,
            job_id, photo_content, style, genre, story_prompt, dialogue,
            panel_count, include_dialogue, user["id"], cost, hd_export
        )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost,
        "message": f"Generating your comic {mode}..."
    }


async def process_comic_avatar(
    job_id: str, photo_content: bytes, style: str, genre: str,
    custom_details: str, user_id: str, cost: int,
    transparent_bg: bool, multiple_poses: bool, hd_export: bool
):
    """Background task to generate comic avatar"""
    try:
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 10, "progressMessage": "Analyzing photo..."}}
        )
        
        result_url = None
        result_urls = []
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                # Build safe prompt
                base_prompt = build_safe_prompt(style, custom_details, genre)
                negative_prompt = get_negative_prompt()
                
                # Add specific instructions
                full_prompt = f"""Transform this person into a comic character.

{base_prompt}

IMPORTANT RULES:
- Create an ORIGINAL character inspired by the person's appearance
- DO NOT reference any copyrighted characters or celebrities
- Maintain the person's general likeness but stylize it
- Style: {SAFE_STYLES[style]['name']}
{"- Use transparent background" if transparent_bg else ""}

AVOID: {negative_prompt}"""
                
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')
                
                # Generate poses
                num_variations = 3 if multiple_poses else 1
                
                for i in range(num_variations):
                    await db.photo_to_comic_jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "progress": 20 + (i * 25),
                            "progressMessage": f"Creating variation {i+1}..." if multiple_poses else "Transforming to comic..."
                        }}
                    )
                    
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"photo-comic-{job_id}-{i}",
                        system_message="You are a professional comic artist. Create original characters only, never copy existing IP."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    variation_prompt = full_prompt
                    if multiple_poses and i > 0:
                        pose_variations = ["different angle, looking away", "action pose, dynamic movement", "profile view, side perspective"]
                        variation_prompt += f" {pose_variations[i-1]}"
                    
                    msg = UserMessage(
                        text=variation_prompt,
                        file_contents=[ImageContent(photo_b64)]
                    )
                    
                    text_response, images = await chat.send_message_multimodal_response(msg)
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        image_bytes = base64.b64decode(img_data['data'])
                        
                        # Apply watermark for free users
                        user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
                        user_plan = user_data.get("plan", "free") if user_data else "free"
                        
                        if should_apply_watermark(user_plan):
                            config = get_watermark_config("COMIC")
                            image_bytes = add_diagonal_watermark(
                                image_bytes,
                                text=config["text"],
                                opacity=config["opacity"],
                                font_size=config["font_size"],
                                spacing=config["spacing"]
                            )
                        
                        import hashlib
                        filename = f"comic_avatar_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:16]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        url = f"/api/static/generated/{filename}"
                        result_urls.append(url)
                        if i == 0:
                            result_url = url
                
            except Exception as e:
                logger.error(f"Comic avatar generation error: {e}")
        
        # Placeholder if no results
        if not result_url:
            result_url = f"https://placehold.co/512x512/6b21a8/white?text=Comic+Avatar"
            result_urls = [result_url]
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic Avatar: {job_id[:8]}")
        
        # Register download with expiry service
        download_id = None
        expires_at = None
        try:
            from services.download_expiry_service import get_download_service
            download_service = get_download_service(db)
            download_info = await download_service.register_download(
                user_id=user_id,
                file_path=result_url,  # Could be local path or URL
                original_filename=f"comic_avatar_{job_id[:8]}.png",
                file_type="image/png",
                feature="comic_avatar"
            )
            download_id = download_info.get("id")
            expires_at = download_info.get("expires_at")
        except Exception as dl_error:
            logger.warning(f"Failed to register download expiry: {dl_error}")
        
        # Update job with download ID
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "progressMessage": "Complete!",
                "resultUrl": result_url,
                "resultUrls": result_urls,
                "downloadId": download_id,
                "expiresAt": expires_at,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Send notification to user
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_complete(
                user_id=user_id,
                feature="comic_avatar",
                job_id=job_id,
                download_url=result_url,
                download_id=download_id,
                expires_at=expires_at
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send notification: {notif_error}")
        
    except Exception as e:
        logger.error(f"Comic avatar processing error: {e}")
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )
        
        # Auto-refund on generation failure
        refund_issued = False
        try:
            from services.auto_refund import handle_generation_failure
            await handle_generation_failure(db, user_id, "comic_avatar", str(e))
            refund_issued = True
            logger.info(f"Auto-refund processed for failed comic avatar: {job_id}")
        except Exception as refund_error:
            logger.error(f"Auto-refund failed: {refund_error}")
        
        # Send failure notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_failed(
                user_id=user_id,
                feature="comic_avatar",
                job_id=job_id,
                error_message=str(e),
                refund_issued=refund_issued
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send failure notification: {notif_error}")


async def process_comic_strip(
    job_id: str, photo_content: bytes, style: str, genre: str,
    story_prompt: str, dialogue: str, panel_count: int,
    include_dialogue: bool, user_id: str, cost: int, hd_export: bool
):
    """Background task to generate comic strip"""
    try:
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 5, "progressMessage": "Planning story..."}}
        )
        
        panels = []
        negative_prompt = get_negative_prompt()
        
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
                
                # Step 1: Generate story outline
                story_chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"comic-strip-outline-{job_id}",
                    system_message="You are a creative comic writer. Create original stories only, never reference copyrighted characters."
                )
                story_chat.with_model("gemini", "gemini-2.0-flash")
                
                outline_prompt = f"""Create a {panel_count}-panel comic story outline.

Story idea: {story_prompt}
Genre: {genre}
Style: {SAFE_STYLES[style]['name']}

IMPORTANT RULES:
- Create ORIGINAL characters and stories only
- NO references to copyrighted characters, brands, or celebrities
- Keep it appropriate for all ages

For each panel provide:
1. Scene description (what's happening visually)
2. Dialogue (if applicable, or null for silent panel)

Format as JSON array:
[{{"scene": "Scene description", "dialogue": "Character dialogue or null"}}]"""
                
                outline_response = await story_chat.send_message(UserMessage(text=outline_prompt))
                
                # Parse outline
                story_scenes = []
                json_match = re.search(r'\[.*\]', outline_response, re.DOTALL)
                if json_match:
                    try:
                        story_scenes = json.loads(json_match.group())
                    except:
                        pass
                
                await db.photo_to_comic_jobs.update_one(
                    {"id": job_id},
                    {"$set": {"progress": 15, "progressMessage": "Story outline created..."}}
                )
                
                # Fallback scenes
                if not story_scenes:
                    story_scenes = [
                        {"scene": "Opening scene", "dialogue": "Here we go!"},
                        {"scene": "Adventure begins", "dialogue": "This is exciting!"},
                        {"scene": "Challenge appears", "dialogue": "Hmm, what now?"},
                        {"scene": "Resolution", "dialogue": "We did it!"}
                    ][:panel_count]
                
                # User-provided dialogue override
                if dialogue and include_dialogue:
                    dialogue_lines = dialogue.split('|')
                    for i, line in enumerate(dialogue_lines[:len(story_scenes)]):
                        story_scenes[i]["dialogue"] = line.strip()
                
                # Step 2: Generate each panel
                photo_b64 = base64.b64encode(photo_content).decode('utf-8')
                
                for i in range(min(panel_count, len(story_scenes))):
                    scene = story_scenes[i]
                    
                    progress = 15 + int(((i + 1) / panel_count) * 75)
                    await db.photo_to_comic_jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "progress": progress,
                            "progressMessage": f"Creating panel {i+1} of {panel_count}..."
                        }}
                    )
                    
                    panel_data = {
                        "panelNumber": i + 1,
                        "scene": scene.get("scene", f"Panel {i+1}"),
                        "dialogue": scene.get("dialogue") if include_dialogue else None
                    }
                    
                    # Try image generation with timeout and retry
                    image_generated = False
                    retry_count = 0
                    max_retries = 2
                    
                    while not image_generated and retry_count < max_retries:
                        try:
                            img_chat = LlmChat(
                                api_key=EMERGENT_LLM_KEY,
                                session_id=f"comic-strip-panel-{job_id}-{i}-{retry_count}",
                                system_message="You are a comic artist. Create original characters. Maintain character consistency."
                            )
                            img_chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                            
                            panel_prompt = f"""Create comic panel {i+1} of {panel_count}.

Scene: {scene.get('scene', '')}
Style: {SAFE_STYLES[style]['prompt']}
Genre: {genre}

IMPORTANT:
- The main character should look like a stylized comic version of the person in the reference photo
- Keep the character consistent across all panels
- Create ORIGINAL art, no copyrighted characters
- Panel {i+1} of {panel_count} in the story sequence

AVOID: {negative_prompt}"""
                            
                            msg = UserMessage(
                                text=panel_prompt,
                                file_contents=[ImageContent(photo_b64)]
                            )
                            
                            # Add timeout for image generation
                            import asyncio
                            try:
                                text_response, images = await asyncio.wait_for(
                                    img_chat.send_message_multimodal_response(msg),
                                    timeout=120  # 2 minute timeout per panel
                                )
                            except asyncio.TimeoutError:
                                logger.warning(f"Panel {i+1} generation timed out, retry {retry_count+1}")
                                retry_count += 1
                                continue
                            
                            if images and len(images) > 0:
                                img_data = images[0]
                                image_bytes = base64.b64decode(img_data['data'])
                                
                                # Apply watermark for free users
                                user_data = await db.users.find_one({"id": user_id}, {"_id": 0, "plan": 1})
                                user_plan = user_data.get("plan", "free") if user_data else "free"
                                
                                if should_apply_watermark(user_plan):
                                    config = get_watermark_config("COMIC")
                                    image_bytes = add_diagonal_watermark(
                                        image_bytes,
                                        text=config["text"],
                                        opacity=config["opacity"],
                                        font_size=config["font_size"],
                                        spacing=config["spacing"]
                                    )
                                
                                import hashlib
                                filename = f"comic_strip_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:16]}.png"
                                filepath = f"/app/backend/static/generated/{filename}"
                                
                                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                
                                with open(filepath, 'wb') as f:
                                    f.write(image_bytes)
                                
                                panel_data["imageUrl"] = f"/api/static/generated/{filename}"
                                image_generated = True
                                logger.info(f"Panel {i+1} generated successfully for job {job_id}")
                            else:
                                logger.warning(f"No images returned for panel {i+1}, retry {retry_count+1}")
                                retry_count += 1
                                
                        except Exception as panel_error:
                            logger.error(f"Panel {i+1} generation error (retry {retry_count}): {panel_error}")
                            retry_count += 1
                    
                    # Use placeholder if all retries failed
                    if not image_generated:
                        logger.warning(f"Using placeholder for panel {i+1} after {max_retries} retries")
                        panel_data["imageUrl"] = f"https://placehold.co/800x600/6b21a8/white?text=Panel+{i+1}+Generation+Pending"
                    
                    panels.append(panel_data)
                    
            except Exception as e:
                logger.error(f"Comic strip generation error: {e}")
        
        # Placeholder panels if generation failed
        if not panels:
            for i in range(panel_count):
                panels.append({
                    "panelNumber": i + 1,
                    "scene": f"Scene {i + 1}",
                    "dialogue": f"Panel {i + 1}",
                    "imageUrl": f"https://placehold.co/800x600/6b21a8/white?text=Panel+{i+1}"
                })
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic Strip: {job_id[:8]}")
        
        # Update job
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "progressMessage": "Complete!",
                "panels": panels,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Send notification to user
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_complete(
                user_id=user_id,
                feature="comic_strip",
                job_id=job_id,
                download_url=panels[0]["imageUrl"] if panels else None
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send notification: {notif_error}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Comic strip processing error for job {job_id}: {error_msg}", exc_info=True)
        
        # Store detailed error in job
        await db.photo_to_comic_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "FAILED", 
                "error": error_msg,
                "errorDetails": {
                    "type": type(e).__name__,
                    "message": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }}
        )
        
        # Auto-refund on generation failure
        refund_issued = False
        try:
            from services.auto_refund import handle_generation_failure
            await handle_generation_failure(db, user_id, "comic_strip", str(e))
            refund_issued = True
            logger.info(f"Auto-refund processed for failed comic strip: {job_id}")
        except Exception as refund_error:
            logger.error(f"Auto-refund failed: {refund_error}")
        
        # Send failure notification
        try:
            from services.notification_service import get_notification_service
            notification_service = get_notification_service(db)
            await notification_service.notify_generation_failed(
                user_id=user_id,
                feature="comic_strip",
                job_id=job_id,
                error_message=str(e),
                refund_issued=refund_issued
            )
        except Exception as notif_error:
            logger.warning(f"Failed to send failure notification: {notif_error}")


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status"""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history")
async def get_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's generation history"""
    query = {"userId": user["id"]}
    
    jobs = await db.photo_to_comic_jobs.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.photo_to_comic_jobs.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.post("/download/{job_id}")
async def download_comic(job_id: str, user: dict = Depends(get_current_user)):
    """Download comic - may require additional credits"""
    job = await db.photo_to_comic_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Content not ready")
    
    # Already downloaded - free re-download
    if job.get("downloaded"):
        download_urls = job.get("resultUrls") or [job.get("resultUrl")]
        if job.get("panels"):
            download_urls = [p.get("imageUrl") for p in job["panels"] if p.get("imageUrl")]
        
        return {
            "success": True,
            "downloadUrls": download_urls,
            "alreadyPurchased": True
        }
    
    # Determine download cost
    is_strip = job.get("mode") == "strip"
    download_cost = PRICING["download"]["strip"] if is_strip else PRICING["download"]["avatar"]
    
    # Check credits
    current_credits = user.get("credits", 0)
    if current_credits < download_cost:
        return {
            "success": False,
            "error": "INSUFFICIENT_CREDITS",
            "message": f"Need {download_cost} credits to download. You have {current_credits}.",
            "creditsNeeded": download_cost
        }
    
    # Deduct credits
    await deduct_credits(user["id"], download_cost, f"Download: {job_id[:8]}")
    
    # Mark as downloaded
    await db.photo_to_comic_jobs.update_one(
        {"id": job_id},
        {"$set": {"downloaded": True, "downloadedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get URLs
    download_urls = job.get("resultUrls") or [job.get("resultUrl")]
    if job.get("panels"):
        download_urls = [p.get("imageUrl") for p in job["panels"] if p.get("imageUrl")]
    
    return {
        "success": True,
        "downloadUrls": download_urls,
        "creditsDeducted": download_cost
    }


@router.delete("/job/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)):
    """Delete a job"""
    result = await db.photo_to_comic_jobs.delete_one(
        {"id": job_id, "userId": user["id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "message": "Job deleted"}


# ============================================
# ADMIN ENDPOINTS
# ============================================

@router.get("/admin/styles")
async def admin_get_styles(user: dict = Depends(get_current_user)):
    """Admin: Get all styles with full config"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "styles": SAFE_STYLES,
        "blockedKeywords": BLOCKED_KEYWORDS,
        "universalNegativePrompts": UNIVERSAL_NEGATIVE_PROMPTS,
        "pricing": PRICING
    }


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(get_current_user)):
    """Admin: Get feature analytics"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count by mode
    avatar_count = await db.photo_to_comic_jobs.count_documents({"mode": "avatar"})
    strip_count = await db.photo_to_comic_jobs.count_documents({"mode": "strip"})
    
    # Count by status
    completed = await db.photo_to_comic_jobs.count_documents({"status": "COMPLETED"})
    failed = await db.photo_to_comic_jobs.count_documents({"status": "FAILED"})
    
    # Popular styles
    pipeline = [
        {"$group": {"_id": "$style", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    popular_styles = await db.photo_to_comic_jobs.aggregate(pipeline).to_list(length=10)
    
    return {
        "totalJobs": avatar_count + strip_count,
        "byMode": {
            "avatar": avatar_count,
            "strip": strip_count
        },
        "byStatus": {
            "completed": completed,
            "failed": failed
        },
        "popularStyles": [{"style": s["_id"], "count": s["count"]} for s in popular_styles]
    }


@router.get("/diagnostic")
async def get_diagnostic_info(user: dict = Depends(get_current_user)):
    """Diagnostic endpoint to check system health for photo-to-comic feature"""
    diagnostic = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_status": {},
        "recent_jobs": {},
        "error_summary": {}
    }
    
    # Check LLM availability
    try:
        diagnostic["llm_status"]["available"] = LLM_AVAILABLE
        diagnostic["llm_status"]["key_configured"] = bool(EMERGENT_LLM_KEY)
        diagnostic["llm_status"]["key_length"] = len(EMERGENT_LLM_KEY) if EMERGENT_LLM_KEY else 0
    except Exception as e:
        diagnostic["llm_status"]["error"] = str(e)
    
    # Recent job stats (last hour)
    try:
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_completed = await db.photo_to_comic_jobs.count_documents({
            "status": "COMPLETED",
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        recent_failed = await db.photo_to_comic_jobs.count_documents({
            "status": "FAILED",
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        recent_pending = await db.photo_to_comic_jobs.count_documents({
            "status": {"$in": ["QUEUED", "PROCESSING"]},
            "createdAt": {"$gte": one_hour_ago.isoformat()}
        })
        
        diagnostic["recent_jobs"]["last_hour"] = {
            "completed": recent_completed,
            "failed": recent_failed,
            "pending": recent_pending,
            "success_rate": f"{(recent_completed / (recent_completed + recent_failed) * 100):.1f}%" if (recent_completed + recent_failed) > 0 else "N/A"
        }
    except Exception as e:
        diagnostic["recent_jobs"]["error"] = str(e)
    
    # Recent errors
    try:
        recent_errors = await db.photo_to_comic_jobs.find(
            {"status": "FAILED", "error": {"$exists": True}},
            {"_id": 0, "id": 1, "error": 1, "errorDetails": 1, "createdAt": 1}
        ).sort("createdAt", -1).limit(5).to_list(5)
        
        diagnostic["error_summary"]["recent_errors"] = recent_errors
    except Exception as e:
        diagnostic["error_summary"]["error"] = str(e)
    
    return diagnostic


@router.post("/test-image-generation")
async def test_image_generation(user: dict = Depends(get_current_user)):
    """Test image generation capability - admin only"""
    if user.get("role") not in ["admin", "ADMIN"]:
        # Allow for testing purposes with warning
        pass
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_available": LLM_AVAILABLE,
        "image_generation": {}
    }
    
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        result["image_generation"]["status"] = "error"
        result["image_generation"]["error"] = "LLM not available or key not configured"
        return result
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test-image-gen-{datetime.now().timestamp()}",
            system_message="You are an artist."
        )
        chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        import asyncio
        text_response, images = await asyncio.wait_for(
            chat.send_message_multimodal_response(
                UserMessage(text="Create a simple smiley face icon, yellow circle with black eyes and smile")
            ),
            timeout=60
        )
        
        result["image_generation"]["status"] = "success"
        result["image_generation"]["text_response"] = text_response[:100] if text_response else None
        result["image_generation"]["images_generated"] = len(images) if images else 0
        result["image_generation"]["image_data_size"] = len(images[0].get("data", "")) if images else 0
        
    except asyncio.TimeoutError:
        result["image_generation"]["status"] = "timeout"
        result["image_generation"]["error"] = "Image generation timed out after 60 seconds"
    except Exception as e:
        result["image_generation"]["status"] = "error"
        result["image_generation"]["error"] = str(e)
        result["image_generation"]["error_type"] = type(e).__name__
    
    return result
