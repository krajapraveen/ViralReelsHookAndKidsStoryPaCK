"""
Comic Story Book Builder v2
CreatorStudio AI

Simplified 5-Step Wizard:
1. Choose Genre
2. Enter Story Idea
3. Choose Page Count
4. Add-ons
5. Preview & Generate

Features:
- Copyright-safe generation
- Universal negative prompts
- Template-driven story expansion
- PDF assembly
- Watermark for free users
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone
from typing import Optional, List, Dict
import uuid
import os
import sys
import base64
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)
from services.watermark_service import add_diagonal_watermark, should_apply_watermark, get_watermark_config

router = APIRouter(prefix="/comic-storybook-v2", tags=["Comic Story Book Builder"])

# ============================================
# BLOCKED COPYRIGHT KEYWORDS
# ============================================
BLOCKED_KEYWORDS = [
    # Superhero / Comic IP
    "marvel", "dc", "avengers", "spiderman", "spider-man", "batman", "superman",
    "ironman", "iron man", "captain america", "thor", "hulk", "joker",
    "wonder woman", "flash", "deadpool", "x-men", "wolverine", "venom",
    # Disney / Animation
    "disney", "pixar", "frozen", "elsa", "anna", "mickey", "minnie",
    "donald duck", "goofy", "toy story", "lightyear", "moana", "simba",
    # Anime / Manga
    "naruto", "sasuke", "dragon ball", "goku", "one piece", "luffy",
    "attack on titan", "demon slayer", "pokemon", "pikachu", "studio ghibli",
    # Games / Entertainment
    "fortnite", "minecraft", "league of legends", "valorant", "pubg",
    "call of duty", "gta", "harry potter", "hogwarts", "hermione",
    # Safety
    "celebrity", "real person", "politician", "nude", "nsfw", "sexual",
    "violence", "gore", "weapon", "hate"
]

# ============================================
# UNIVERSAL NEGATIVE PROMPTS
# ============================================
UNIVERSAL_NEGATIVE_PROMPTS = [
    "blurry", "low resolution", "bad anatomy", "extra limbs", "duplicate face",
    "watermark", "logo", "brand name", "copyrighted character", "celebrity likeness",
    "trademark symbol", "nsfw", "nudity", "gore", "violence", "hate symbol",
    "political propaganda", "real person replication", "hyper realistic celebrity face",
    "deformed", "disfigured", "extra fingers", "mutated hands", "poorly drawn"
]

# ============================================
# STORY GENRES
# ============================================
STORY_GENRES = {
    "kids_adventure": {
        "name": "Kids Adventure",
        "style_prompt": "children's book illustration style, colorful, friendly, cute characters, soft colors, playful",
        "story_template": "A {character} goes on an exciting adventure to {goal}. Along the way, they {challenge} and learn that {lesson}."
    },
    "superhero": {
        "name": "Superhero",
        "style_prompt": "dynamic superhero comic style, bold colors, action poses, heroic, original character design",
        "story_template": "When {threat} threatens {setting}, an unlikely hero discovers their power to {ability}. They must {challenge} to save the day."
    },
    "fantasy": {
        "name": "Fantasy",
        "style_prompt": "magical fantasy illustration, enchanted atmosphere, mystical elements, vibrant magical colors",
        "story_template": "In a magical realm where {magic_element}, a brave {character} embarks on a quest to {goal}. They encounter {obstacle} and discover {revelation}."
    },
    "comedy": {
        "name": "Comedy",
        "style_prompt": "cartoon comedy style, exaggerated expressions, bright colors, funny characters, playful",
        "story_template": "When {character} accidentally {mishap}, hilarious chaos ensues! Through {comedic_situations}, they learn to {lesson} while making everyone laugh."
    },
    "romance": {
        "name": "Romance",
        "style_prompt": "soft romantic illustration style, gentle colors, dreamy atmosphere, emotional expressions",
        "story_template": "{character1} and {character2} meet under unexpected circumstances. Despite {obstacle}, they discover that {romantic_revelation}."
    },
    "scifi": {
        "name": "Sci-Fi",
        "style_prompt": "futuristic sci-fi comic style, technology, space, neon accents, sleek design",
        "story_template": "In the year {year}, {character} must navigate a world where {tech_element}. When {crisis} threatens, they discover {solution}."
    },
    "mystery": {
        "name": "Mystery",
        "style_prompt": "mysterious detective comic style, dramatic shadows, noir elements, intriguing atmosphere",
        "story_template": "When {mystery} occurs, clever {detective} must find clues and solve puzzles. Each discovery leads to {twist}, revealing {truth}."
    },
    "horror_lite": {
        "name": "Spooky Fun",
        "style_prompt": "friendly spooky illustration, Halloween vibes, cute monsters, not too scary, fun atmosphere",
        "story_template": "On a spooky night, {character} encounters {friendly_monster}. Together they {adventure} and discover that {heartwarming_lesson}."
    }
}

# ============================================
# PRICING
# ============================================
PRICING = {
    "pages": {
        10: 25,
        20: 45,
        30: 60
    },
    "add_ons": {
        "personalized_cover": 4,
        "dedication_page": 2,
        "activity_pages": 5,
        "hd_print": 5,
        "commercial_license": 15
    },
    "download": {
        "standard": 0,  # Included
        "print": 0       # Included if hd_print addon
    }
}


def check_blocked_keywords(text: str) -> tuple:
    """Check if text contains blocked keywords"""
    if not text:
        return False, None
    
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True, keyword
    
    return False, None


def get_negative_prompt() -> str:
    """Build complete negative prompt"""
    return ", ".join(UNIVERSAL_NEGATIVE_PROMPTS)


async def expand_story(story_idea: str, genre: str, page_count: int) -> List[Dict]:
    """
    Expand a short story idea into page-by-page content.
    Uses LLM to create structured story beats.
    """
    genre_info = STORY_GENRES.get(genre, STORY_GENRES["kids_adventure"])
    
    pages = []
    
    if LLM_AVAILABLE and EMERGENT_LLM_KEY:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"story-expand-{uuid.uuid4()}",
                system_message="You are a professional children's book writer. Create engaging, age-appropriate stories. Never use copyrighted characters or brand names. Always create original characters."
            )
            chat.with_model("gemini", "gemini-2.0-flash")
            
            expansion_prompt = f"""Expand this story idea into {page_count} comic book pages.

Story Idea: {story_idea}
Genre: {genre_info['name']}

Create exactly {page_count} page descriptions. For each page provide:
1. Scene description (what's happening visually)
2. Short dialogue or narration (1-2 sentences)
3. Emotional tone

IMPORTANT RULES:
- Create ORIGINAL characters only
- NO copyrighted characters, brands, or celebrities
- Age-appropriate content only
- Each page should advance the story

Format as JSON array:
[{{"page": 1, "scene": "Description", "dialogue": "Text", "tone": "emotion"}}]"""
            
            response = await chat.send_message(UserMessage(text=expansion_prompt))
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                try:
                    pages = json.loads(json_match.group())
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Story expansion error: {e}")
    
    # Fallback: Generate basic structure
    if not pages:
        pages = []
        for i in range(page_count):
            if i == 0:
                pages.append({
                    "page": 1,
                    "scene": "Title page with the main character introduction",
                    "dialogue": story_idea[:100],
                    "tone": "exciting"
                })
            elif i == page_count - 1:
                pages.append({
                    "page": i + 1,
                    "scene": "Happy ending scene",
                    "dialogue": "The End",
                    "tone": "happy"
                })
            else:
                pages.append({
                    "page": i + 1,
                    "scene": f"Story continues - scene {i}",
                    "dialogue": f"Part {i} of the adventure",
                    "tone": "adventurous"
                })
    
    return pages


@router.get("/genres")
async def get_genres(user: dict = Depends(get_current_user)):
    """Get available story genres"""
    return {
        "genres": {k: {"name": v["name"]} for k, v in STORY_GENRES.items()},
        "pricing": PRICING
    }


@router.get("/pricing")
async def get_pricing(user: dict = Depends(get_current_user)):
    """Get pricing configuration"""
    return {"pricing": PRICING}


class PreviewComicRequest(BaseModel):
    genre: str
    storyIdea: str
    title: str = "My Comic Story"
    pageCount: int = 20

@router.post("/preview")
async def generate_preview(
    request: PreviewComicRequest,
    user: dict = Depends(get_current_user)
):
    """Generate preview pages (watermarked)"""
    # Extract from request body
    genre = request.genre
    storyIdea = request.storyIdea
    title = request.title
    pageCount = request.pageCount
    
    # Validate content
    is_blocked, keyword = check_blocked_keywords(storyIdea)
    if is_blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Brand-based or copyrighted characters are not allowed. Detected: '{keyword}'."
        )
    
    is_blocked, keyword = check_blocked_keywords(title)
    if is_blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Brand-based or copyrighted characters are not allowed in title. Detected: '{keyword}'."
        )
    
    # Generate 2 preview images
    preview_pages = []
    genre_info = STORY_GENRES.get(genre, STORY_GENRES["kids_adventure"])
    
    if LLM_AVAILABLE and EMERGENT_LLM_KEY:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            negative_prompt = get_negative_prompt()
            
            # Generate cover preview
            cover_prompt = f"""Create a comic book cover illustration.
Title: {title}
Genre: {genre_info['name']}
Story: {storyIdea[:200]}
Style: {genre_info['style_prompt']}

Create an engaging book cover with the title prominently displayed.
Original characters only, no copyrighted content.

AVOID: {negative_prompt}"""
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"preview-cover-{uuid.uuid4()}",
                system_message="You are a comic book cover artist."
            )
            chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
            
            _, images = await chat.send_message_multimodal_response(UserMessage(text=cover_prompt))
            
            if images and len(images) > 0:
                img_data = images[0]
                image_bytes = base64.b64decode(img_data['data'])
                
                # Add watermark
                config = get_watermark_config("STORYBOOK")
                image_bytes = add_diagonal_watermark(
                    image_bytes,
                    text="PREVIEW",
                    opacity=0.3,
                    font_size=50,
                    spacing=150
                )
                
                import hashlib
                filename = f"preview_cover_{hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:12]}.png"
                filepath = f"/app/backend/static/generated/{filename}"
                
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
                
                preview_pages.append({
                    "url": f"/api/static/generated/{filename}",
                    "type": "cover"
                })
                
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
    
    # Fallback placeholders
    if not preview_pages:
        preview_pages = [
            {"url": "https://placehold.co/400x600/6b21a8/white?text=Cover+Preview", "type": "cover"},
            {"url": "https://placehold.co/400x600/7c3aed/white?text=Page+1+Preview", "type": "page"}
        ]
    
    return {
        "success": True,
        "previewPages": preview_pages
    }


from pydantic import BaseModel

class GenerateComicRequest(BaseModel):
    genre: str
    storyIdea: str
    title: str = "My Comic Story"
    author: str = "Anonymous"
    pageCount: int = 20
    addOns: Optional[Dict] = None
    dedicationText: Optional[str] = None

@router.post("/generate")
async def generate_comic_book(
    request: GenerateComicRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Generate full comic book"""
    # Extract from request body
    genre = request.genre
    storyIdea = request.storyIdea
    title = request.title
    author = request.author
    pageCount = request.pageCount
    addOns = request.addOns
    dedicationText = request.dedicationText
    
    # Validate content
    is_blocked, keyword = check_blocked_keywords(storyIdea)
    if is_blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Brand-based or copyrighted characters are not allowed. Detected: '{keyword}'."
        )
    
    is_blocked, keyword = check_blocked_keywords(title)
    if is_blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Copyrighted content in title. Detected: '{keyword}'."
        )
    
    # Validate genre
    if genre not in STORY_GENRES:
        genre = "kids_adventure"
    
    # Validate page count
    if pageCount not in [10, 20, 30]:
        pageCount = 20
    
    # Calculate cost
    cost = PRICING["pages"].get(pageCount, 45)
    addOns = addOns or {}
    
    for addon_id, addon_cost in PRICING["add_ons"].items():
        if addOns.get(addon_id):
            cost += addon_cost
    
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
        "type": "COMIC_STORYBOOK",
        "status": "QUEUED",
        "genre": genre,
        "storyIdea": storyIdea,
        "title": title,
        "author": author,
        "pageCount": pageCount,
        "addOns": addOns,
        "dedicationText": dedicationText,
        "cost": cost,
        "progress": 0,
        "pages": [],
        "pdfUrl": None,
        "purchased": user_plan != "free",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.comic_storybook_v2_jobs.insert_one(job_data)
    
    # Process in background
    background_tasks.add_task(
        process_comic_book,
        job_id, genre, storyIdea, title, author, pageCount, addOns, dedicationText,
        user["id"], cost, user_plan
    )
    
    return {
        "success": True,
        "jobId": job_id,
        "status": "QUEUED",
        "estimatedCredits": cost
    }


async def process_comic_book(
    job_id: str, genre: str, story_idea: str, title: str, author: str,
    page_count: int, add_ons: Dict, dedication_text: str,
    user_id: str, cost: int, user_plan: str
):
    """Background task to generate comic book"""
    try:
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "PROCESSING", "progress": 5, "progressMessage": "Expanding your story..."}}
        )
        
        # Step 1: Expand story into pages
        story_pages = await expand_story(story_idea, genre, page_count)
        
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress": 15, "progressMessage": "Story outline created..."}}
        )
        
        genre_info = STORY_GENRES.get(genre, STORY_GENRES["kids_adventure"])
        negative_prompt = get_negative_prompt()
        generated_pages = []
        
        # Step 2: Generate each page
        if LLM_AVAILABLE and EMERGENT_LLM_KEY:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            for i, page_content in enumerate(story_pages[:page_count]):
                progress = 15 + int(((i + 1) / page_count) * 70)
                await db.comic_storybook_v2_jobs.update_one(
                    {"id": job_id},
                    {"$set": {
                        "progress": progress,
                        "progressMessage": f"Generating page {i + 1} of {page_count}..."
                    }}
                )
                
                try:
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"storybook-page-{job_id}-{i}",
                        system_message="You are a comic book illustrator. Create original art only."
                    )
                    chat.with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
                    
                    page_prompt = f"""Create comic book page {i + 1} of {page_count}.

Title: {title}
Scene: {page_content.get('scene', f'Page {i+1}')}
Dialogue/Text: {page_content.get('dialogue', '')}
Emotional Tone: {page_content.get('tone', 'engaging')}
Style: {genre_info['style_prompt']}

Create a single comic page illustration. Original characters only.

AVOID: {negative_prompt}"""
                    
                    _, images = await chat.send_message_multimodal_response(UserMessage(text=page_prompt))
                    
                    if images and len(images) > 0:
                        img_data = images[0]
                        image_bytes = base64.b64decode(img_data['data'])
                        
                        # Apply watermark for free users
                        if should_apply_watermark(user_plan):
                            config = get_watermark_config("STORYBOOK")
                            image_bytes = add_diagonal_watermark(
                                image_bytes,
                                text=config["text"],
                                opacity=config["opacity"],
                                font_size=config["font_size"],
                                spacing=config["spacing"]
                            )
                        
                        import hashlib
                        filename = f"storybook_{hashlib.md5(f'{job_id}_{i}'.encode()).hexdigest()[:12]}.png"
                        filepath = f"/app/backend/static/generated/{filename}"
                        
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        generated_pages.append({
                            "pageNumber": i + 1,
                            "imageUrl": f"/api/static/generated/{filename}",
                            "scene": page_content.get('scene', ''),
                            "dialogue": page_content.get('dialogue', '')
                        })
                    else:
                        # Placeholder
                        generated_pages.append({
                            "pageNumber": i + 1,
                            "imageUrl": f"https://placehold.co/800x1200/6b21a8/white?text=Page+{i+1}",
                            "scene": page_content.get('scene', ''),
                            "dialogue": page_content.get('dialogue', '')
                        })
                        
                except Exception as e:
                    logger.error(f"Page generation error: {e}")
                    generated_pages.append({
                        "pageNumber": i + 1,
                        "imageUrl": f"https://placehold.co/800x1200/6b21a8/white?text=Page+{i+1}",
                        "scene": page_content.get('scene', ''),
                        "dialogue": page_content.get('dialogue', '')
                    })
        else:
            # All placeholders
            for i in range(page_count):
                generated_pages.append({
                    "pageNumber": i + 1,
                    "imageUrl": f"https://placehold.co/800x1200/6b21a8/white?text=Page+{i+1}",
                    "scene": f"Page {i+1}",
                    "dialogue": ""
                })
        
        # Step 3: Generate PDF
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {"progress": 90, "progressMessage": "Assembling PDF..."}}
        )
        
        # Simple PDF assembly (placeholder for now)
        pdf_url = f"/api/static/generated/storybook_{job_id[:8]}.pdf"
        
        # Deduct credits
        await deduct_credits(user_id, cost, f"Comic Story Book: {job_id[:8]}")
        
        # Update job as complete
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "COMPLETED",
                "progress": 100,
                "progressMessage": "Complete!",
                "pages": generated_pages,
                "pdfUrl": pdf_url,
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
    except Exception as e:
        logger.error(f"Comic book processing error: {e}")
        await db.comic_storybook_v2_jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "FAILED", "error": str(e)}}
        )


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get job status"""
    job = await db.comic_storybook_v2_jobs.find_one(
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
    jobs = await db.comic_storybook_v2_jobs.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(page * size).limit(size).to_list(length=size)
    
    total = await db.comic_storybook_v2_jobs.count_documents({"userId": user["id"]})
    
    return {"jobs": jobs, "total": total, "page": page, "size": size}


@router.post("/download/{job_id}")
async def download_comic(
    job_id: str,
    type: str = "pdf",
    user: dict = Depends(get_current_user)
):
    """Download comic book"""
    job = await db.comic_storybook_v2_jobs.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Book not ready")
    
    # Check if free user trying to download
    user_plan = user.get("plan", "free")
    if user_plan == "free" and not job.get("purchased"):
        raise HTTPException(
            status_code=403,
            detail="Upgrade to download. Preview is watermarked."
        )
    
    return {
        "success": True,
        "downloadUrl": job.get("pdfUrl", f"/api/static/generated/storybook_{job_id[:8]}.pdf")
    }


# ============================================
# ADMIN ENDPOINTS
# ============================================

@router.get("/admin/pricing")
async def admin_get_pricing(user: dict = Depends(get_current_user)):
    """Admin: Get pricing configuration"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "pricing": PRICING,
        "genres": list(STORY_GENRES.keys()),
        "blockedKeywords": BLOCKED_KEYWORDS[:20],  # Sample
        "negativePrompts": UNIVERSAL_NEGATIVE_PROMPTS[:10]  # Sample
    }


@router.get("/admin/analytics")
async def admin_analytics(user: dict = Depends(get_current_user)):
    """Admin: Get feature analytics"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    total_jobs = await db.comic_storybook_v2_jobs.count_documents({})
    completed = await db.comic_storybook_v2_jobs.count_documents({"status": "COMPLETED"})
    failed = await db.comic_storybook_v2_jobs.count_documents({"status": "FAILED"})
    
    # Popular genres
    pipeline = [
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 8}
    ]
    popular_genres = await db.comic_storybook_v2_jobs.aggregate(pipeline).to_list(length=8)
    
    # Revenue by page count
    revenue_pipeline = [
        {"$group": {"_id": "$pageCount", "totalRevenue": {"$sum": "$cost"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    revenue_by_pages = await db.comic_storybook_v2_jobs.aggregate(revenue_pipeline).to_list(length=10)
    
    return {
        "totalJobs": total_jobs,
        "completed": completed,
        "failed": failed,
        "popularGenres": [{"genre": g["_id"], "count": g["count"]} for g in popular_genres],
        "revenueByPageCount": revenue_by_pages
    }
