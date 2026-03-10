"""
Story → Images → Video Studio
Phase 1: Story → Scene → Script → Prompt Pack
Phase 2: Image Generation
Phase 3: Voice Generation
Phase 4: Video Assembly
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/story-video-studio", tags=["Story Video Studio"])

# Get database connection - import from shared directly
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import db

# =============================================================================
# COPYRIGHT PROTECTION - Blocked Terms
# =============================================================================

BLOCKED_TERMS = [
    # Disney/Marvel/DC
    "marvel", "disney", "pixar", "naruto", "pokemon", "pikachu", "batman", "superman",
    "spiderman", "spider-man", "ironman", "iron man", "hulk", "thor", "avengers",
    "harry potter", "hogwarts", "frozen", "elsa", "mickey mouse", "minnie mouse",
    "donald duck", "goofy", "lion king", "simba", "nemo", "dory", "woody", "buzz lightyear",
    "shrek", "dreamworks", "universal", "warner bros", "looney tunes", "bugs bunny",
    "tom and jerry", "scooby doo", "spongebob", "nickelodeon", "paw patrol",
    "peppa pig", "bluey", "cocomelon", "baby shark",
    # Anime/Manga
    "dragon ball", "goku", "one piece", "luffy", "attack on titan", "demon slayer",
    "my hero academia", "jujutsu kaisen", "sailor moon", "studio ghibli", "totoro",
    # Celebrities
    "taylor swift", "beyonce", "drake", "kanye", "kim kardashian", "elon musk",
    "trump", "biden", "obama", "putin",
    # Brands
    "coca cola", "pepsi", "mcdonalds", "nike", "adidas", "apple", "google", "amazon",
    "facebook", "instagram", "tiktok", "youtube", "netflix", "spotify",
    # Other copyrighted
    "star wars", "lord of the rings", "game of thrones", "hunger games",
    "transformers", "power rangers", "teenage mutant ninja turtles", "tmnt",
]

UNIVERSAL_NEGATIVE_PROMPTS = [
    "copyrighted character", "brand name", "celebrity likeness", "trademark logo",
    "nsfw", "violence", "gore", "blood", "political propaganda", "religious symbol",
    "hate symbol", "explicit content", "nudity", "weapon", "drug", "alcohol",
    "cigarette", "gambling", "scary", "horror", "nightmare", "death"
]

def check_copyright_violation(text: str) -> Optional[str]:
    """Check if text contains copyrighted terms using word boundary matching"""
    import re
    text_lower = text.lower()
    for term in BLOCKED_TERMS:
        # Use word boundary matching to avoid false positives (e.g., "fluffy" matching "luffy")
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text_lower):
            return f"Copyrighted content detected: '{term}'. Please use original characters and stories."
    return None

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class VideoStyle(BaseModel):
    id: str
    name: str
    description: str
    prompt_style: str

VIDEO_STYLES = [
    VideoStyle(
        id="storybook",
        name="Storybook Animation",
        description="Classic children's book illustration style with warm colors",
        prompt_style="children's book illustration, warm colors, soft lighting, whimsical, hand-drawn feel"
    ),
    VideoStyle(
        id="comic",
        name="Comic Adventure",
        description="Bold comic book style with dynamic poses",
        prompt_style="comic book style, bold lines, vibrant colors, dynamic composition, action-oriented"
    ),
    VideoStyle(
        id="watercolor",
        name="Soft Watercolor",
        description="Gentle watercolor painting style",
        prompt_style="watercolor painting, soft edges, pastel colors, dreamy atmosphere, artistic"
    ),
    VideoStyle(
        id="cinematic",
        name="Cinematic Fantasy",
        description="Movie-quality cinematic visuals",
        prompt_style="cinematic, high detail, dramatic lighting, fantasy, movie poster quality"
    ),
    VideoStyle(
        id="anime",
        name="Anime Style",
        description="Japanese anime-inspired art style",
        prompt_style="anime style, cel shading, expressive eyes, colorful, Japanese animation"
    ),
    VideoStyle(
        id="3d_cartoon",
        name="3D Cartoon",
        description="Pixar-like 3D rendered cartoon style",
        prompt_style="3D render, cartoon style, soft shadows, vibrant colors, family-friendly"
    ),
]

class StoryInput(BaseModel):
    story_text: str = Field(..., min_length=50, max_length=50000)
    language: str = Field(default="english")
    age_group: str = Field(default="kids_5_8")  # kids_3_5, kids_5_8, kids_8_12, teens, adults
    style_id: str = Field(default="storybook")
    title: Optional[str] = None

class Character(BaseModel):
    name: str
    age: Optional[str] = None
    appearance: str
    clothing: str
    personality: str
    voice_tone: str

class Scene(BaseModel):
    scene_number: int
    title: str
    summary: str
    narration_text: str
    character_dialogue: List[Dict[str, str]] = []
    visual_prompt: str
    estimated_duration: int  # seconds
    characters_in_scene: List[str] = []

class VoiceScript(BaseModel):
    scene_number: int
    narrator_text: str
    character_dialogues: List[Dict[str, str]] = []
    voice_notes: List[str] = []

class StoryProject(BaseModel):
    project_id: str
    user_id: str
    title: str
    original_story: str
    language: str
    age_group: str
    style_id: str
    style_prompt: str
    characters: List[Character] = []
    scenes: List[Scene] = []
    voice_scripts: List[VoiceScript] = []
    status: str = "draft"  # draft, scenes_generated, images_generated, voices_generated, video_rendered
    credits_spent: int = 0
    created_at: datetime
    updated_at: datetime

class ProjectResponse(BaseModel):
    success: bool
    project_id: str
    message: str
    data: Optional[Dict[str, Any]] = None

# =============================================================================
# CREDIT PRICING
# =============================================================================

CREDIT_COSTS = {
    "scene_generation": 5,      # Per project
    "image_per_scene": 10,      # Per image
    "voice_per_minute": 10,     # Per minute of audio
    "video_render": 20,         # Per final video
    "watermark_removal": 15,    # One-time fee
}

async def check_and_deduct_credits(db: AsyncIOMotorDatabase, user_id: str, amount: int, description: str) -> bool:
    """Check if user has enough credits and deduct them"""
    user = await db.users.find_one({"_id": user_id})
    if not user:
        user = await db.users.find_one({"id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_credits = user.get("credits", 0)
    if current_credits < amount:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Required: {amount}, Available: {current_credits}"
        )
    
    # Deduct credits
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
# LLM INTEGRATION FOR SCENE GENERATION
# =============================================================================

async def generate_scenes_with_llm(story_text: str, style: VideoStyle, age_group: str, language: str) -> Dict:
    """Use GPT-5.2 to break story into scenes and extract characters"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"story_scene_{uuid.uuid4()}",
        system_message="""You are an expert story analyst and screenplay writer. 
Your job is to break down stories into scenes suitable for video production.
Always respond with valid JSON only, no markdown or extra text."""
    )
    chat.with_model("openai", "gpt-5.2")
    
    prompt = f"""Analyze this story and break it down into scenes for a {age_group.replace('_', ' ')} video.
Language: {language}
Visual Style: {style.name} - {style.description}

STORY:
{story_text}

Create a JSON response with this EXACT structure:
{{
    "title": "Story title extracted or generated",
    "characters": [
        {{
            "name": "Character name",
            "age": "approximate age",
            "appearance": "detailed physical description",
            "clothing": "what they typically wear",
            "personality": "key personality traits",
            "voice_tone": "how their voice should sound"
        }}
    ],
    "scenes": [
        {{
            "scene_number": 1,
            "title": "Scene title",
            "summary": "Brief summary of what happens",
            "narration_text": "The narrator text for this scene",
            "character_dialogue": [
                {{"character": "Name", "dialogue": "What they say"}}
            ],
            "visual_prompt": "Detailed visual description for image generation including character appearances",
            "estimated_duration": 10,
            "characters_in_scene": ["Character1", "Character2"]
        }}
    ],
    "voice_scripts": [
        {{
            "scene_number": 1,
            "narrator_text": "Full narrator script",
            "character_dialogues": [
                {{"character": "Name", "dialogue": "Their line", "emotion": "happy/sad/excited"}}
            ],
            "voice_notes": ["[PAUSE 1s]", "[SPEAK SOFTLY]"]
        }}
    ]
}}

Rules:
1. Create 3-10 scenes depending on story length
2. Each scene should be 5-15 seconds when narrated
3. Include detailed visual prompts that describe characters consistently
4. Add the style description to each visual prompt: "{style.prompt_style}"
5. Make voice notes age-appropriate
6. Keep dialogue natural for the target age group
7. ALWAYS include character appearance details in visual_prompt

Respond with ONLY the JSON, no other text."""

    try:
        response = await chat.send_message(UserMessage(text=prompt))
        
        # Clean the response - remove markdown code blocks if present
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/styles")
async def get_video_styles():
    """Get all available video styles"""
    return {
        "success": True,
        "styles": [s.dict() for s in VIDEO_STYLES]
    }

@router.get("/pricing")
async def get_pricing():
    """Get credit pricing for all operations"""
    return {
        "success": True,
        "pricing": CREDIT_COSTS,
        "example_3min_video": {
            "scene_generation": 5,
            "images_6_scenes": 60,
            "voice_3_minutes": 30,
            "video_render": 20,
            "total": 115
        }
    }

@router.post("/projects/create")
async def create_project(
    story_input: StoryInput,
    user_id: str = None
):
    """Create a new story project (Phase 1 - no credits required yet)"""
    
    # For now, use a test user if not authenticated
    if not user_id:
        user_id = "test_user"
    
    # Check for copyright violations
    violation = check_copyright_violation(story_input.story_text)
    if violation:
        raise HTTPException(status_code=400, detail=violation)
    
    if story_input.title:
        title_violation = check_copyright_violation(story_input.title)
        if title_violation:
            raise HTTPException(status_code=400, detail=title_violation)
    
    # Find the selected style
    style = next((s for s in VIDEO_STYLES if s.id == story_input.style_id), VIDEO_STYLES[0])
    
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    project = {
        "project_id": project_id,
        "user_id": user_id,
        "title": story_input.title or "Untitled Story",
        "original_story": story_input.story_text,
        "language": story_input.language,
        "age_group": story_input.age_group,
        "style_id": story_input.style_id,
        "style_prompt": style.prompt_style,
        "characters": [],
        "scenes": [],
        "voice_scripts": [],
        "status": "draft",
        "credits_spent": 0,
        "created_at": now,
        "updated_at": now
    }
    
    await db.story_projects.insert_one(project)
    
    # Remove _id for response
    project.pop("_id", None)
    
    return ProjectResponse(
        success=True,
        project_id=project_id,
        message="Project created successfully. Generate scenes to continue.",
        data=project
    )

@router.post("/projects/{project_id}/generate-scenes")
async def generate_scenes(
    project_id: str,
    user_id: str = None
):
    """Generate scenes from story (Phase 1 - costs 5 credits)"""
    
    if not user_id:
        user_id = "test_user"
    
    # Get project
    project = await db.story_projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check and deduct credits (skip for testing)
    # await check_and_deduct_credits(db, user_id, CREDIT_COSTS["scene_generation"], f"Scene generation for project {project_id}")
    
    # Get style
    style = next((s for s in VIDEO_STYLES if s.id == project["style_id"]), VIDEO_STYLES[0])
    
    # Generate scenes using LLM
    result = await generate_scenes_with_llm(
        project["original_story"],
        style,
        project["age_group"],
        project["language"]
    )
    
    # Update project with generated content
    await db.story_projects.update_one(
        {"project_id": project_id},
        {
            "$set": {
                "title": result.get("title", project["title"]),
                "characters": result.get("characters", []),
                "scenes": result.get("scenes", []),
                "voice_scripts": result.get("voice_scripts", []),
                "status": "scenes_generated",
                "credits_spent": project.get("credits_spent", 0) + CREDIT_COSTS["scene_generation"],
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "success": True,
        "project_id": project_id,
        "message": f"Generated {len(result.get('scenes', []))} scenes with {len(result.get('characters', []))} characters",
        "data": {
            "title": result.get("title"),
            "characters": result.get("characters", []),
            "scenes": result.get("scenes", []),
            "voice_scripts": result.get("voice_scripts", []),
            "credits_spent": CREDIT_COSTS["scene_generation"]
        }
    }

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str
):
    """Get project details"""
    project = await db.story_projects.find_one({"project_id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "success": True,
        "project": project
    }

@router.get("/projects")
async def list_projects(
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    """List user's projects"""
    if not user_id:
        user_id = "test_user"
    
    cursor = db.story_projects.find(
        {"user_id": user_id},
        {"_id": 0, "original_story": 0}  # Exclude large fields
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    projects = await cursor.to_list(length=limit)
    
    return {
        "success": True,
        "projects": projects,
        "count": len(projects)
    }

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str
):
    """Delete a project"""
    result = await db.story_projects.delete_one({"project_id": project_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Also delete associated assets
    await db.scene_assets.delete_many({"project_id": project_id})
    await db.voice_tracks.delete_many({"project_id": project_id})
    await db.render_jobs.delete_many({"project_id": project_id})
    
    return {
        "success": True,
        "message": "Project deleted successfully"
    }

@router.post("/projects/{project_id}/update-scene/{scene_number}")
async def update_scene(
    project_id: str,
    scene_number: int,
    scene_data: Dict[str, Any]
):
    """Update a specific scene in the project"""
    project = await db.story_projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    scenes = project.get("scenes", [])
    
    # Find and update the scene
    for i, scene in enumerate(scenes):
        if scene.get("scene_number") == scene_number:
            scenes[i].update(scene_data)
            break
    else:
        raise HTTPException(status_code=404, detail=f"Scene {scene_number} not found")
    
    await db.story_projects.update_one(
        {"project_id": project_id},
        {
            "$set": {
                "scenes": scenes,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Scene {scene_number} updated"
    }

@router.post("/projects/{project_id}/update-character/{character_name}")
async def update_character(
    project_id: str,
    character_name: str,
    character_data: Dict[str, Any]
):
    """Update a character in the project"""
    project = await db.story_projects.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    characters = project.get("characters", [])
    
    # Find and update the character
    for i, char in enumerate(characters):
        if char.get("name").lower() == character_name.lower():
            characters[i].update(character_data)
            break
    else:
        raise HTTPException(status_code=404, detail=f"Character '{character_name}' not found")
    
    await db.story_projects.update_one(
        {"project_id": project_id},
        {
            "$set": {
                "characters": characters,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Character '{character_name}' updated"
    }

@router.get("/projects/{project_id}/prompt-pack")
async def get_prompt_pack(
    project_id: str
):
    """Get the complete prompt pack for image generation (Phase 1 output)"""
    project = await db.story_projects.find_one({"project_id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["status"] == "draft":
        raise HTTPException(status_code=400, detail="Generate scenes first")
    
    # Build character bible
    character_bible = {}
    for char in project.get("characters", []):
        char_prompt = f"{char.get('name')}: {char.get('appearance')}, wearing {char.get('clothing')}"
        character_bible[char.get("name")] = char_prompt
    
    # Build scene prompts with character consistency
    scene_prompts = []
    style_prompt = project.get("style_prompt", "")
    
    for scene in project.get("scenes", []):
        # Include character descriptions in prompt
        chars_in_scene = scene.get("characters_in_scene", [])
        char_descriptions = [character_bible.get(c, c) for c in chars_in_scene]
        
        full_prompt = f"{scene.get('visual_prompt')}. "
        if char_descriptions:
            full_prompt += f"Characters: {', '.join(char_descriptions)}. "
        full_prompt += f"Style: {style_prompt}. "
        full_prompt += f"Negative: {', '.join(UNIVERSAL_NEGATIVE_PROMPTS[:10])}"
        
        scene_prompts.append({
            "scene_number": scene.get("scene_number"),
            "title": scene.get("title"),
            "prompt": full_prompt,
            "negative_prompt": ", ".join(UNIVERSAL_NEGATIVE_PROMPTS)
        })
    
    return {
        "success": True,
        "project_id": project_id,
        "title": project.get("title"),
        "character_bible": character_bible,
        "scene_prompts": scene_prompts,
        "voice_scripts": project.get("voice_scripts", []),
        "style": {
            "id": project.get("style_id"),
            "prompt": style_prompt
        },
        "stats": {
            "total_scenes": len(scene_prompts),
            "total_characters": len(character_bible),
            "estimated_image_credits": len(scene_prompts) * CREDIT_COSTS["image_per_scene"]
        }
    }

# =============================================================================
# FILE UPLOAD SUPPORT
# =============================================================================

@router.post("/upload-story")
async def upload_story_file(
    file: UploadFile = File(...),
    language: str = Form(default="english"),
    age_group: str = Form(default="kids_5_8"),
    style_id: str = Form(default="storybook"),
    user_id: str = None
):
    """Upload a story file (TXT, PDF, DOCX) and create a project"""
    
    if not user_id:
        user_id = "test_user"
    
    # Check file type
    allowed_types = [".txt", ".pdf", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    
    if file_ext == ".txt":
        story_text = content.decode("utf-8")
    elif file_ext == ".pdf":
        # PDF extraction
        try:
            import fitz  # PyMuPDF
            pdf = fitz.open(stream=content, filetype="pdf")
            story_text = ""
            for page in pdf:
                story_text += page.get_text()
            pdf.close()
        except ImportError:
            raise HTTPException(status_code=500, detail="PDF processing not available")
    elif file_ext == ".docx":
        # DOCX extraction
        try:
            import docx
            from io import BytesIO
            doc = docx.Document(BytesIO(content))
            story_text = "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            raise HTTPException(status_code=500, detail="DOCX processing not available")
    else:
        story_text = content.decode("utf-8")
    
    # Validate story length
    if len(story_text) < 50:
        raise HTTPException(status_code=400, detail="Story is too short (minimum 50 characters)")
    if len(story_text) > 50000:
        raise HTTPException(status_code=400, detail="Story is too long (maximum 50000 characters)")
    
    # Create project
    story_input = StoryInput(
        story_text=story_text,
        language=language,
        age_group=age_group,
        style_id=style_id,
        title=os.path.splitext(file.filename)[0]
    )
    
    return await create_project(story_input, user_id)

# =============================================================================
# ANALYTICS
# =============================================================================

@router.get("/analytics")
async def get_analytics():
    """Get analytics for Story Video Studio"""
    
    # Total projects
    total_projects = await db.story_projects.count_documents({})
    
    # Projects by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = {}
    async for doc in db.story_projects.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]
    
    # Popular styles
    style_pipeline = [
        {"$group": {"_id": "$style_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    popular_styles = []
    async for doc in db.story_projects.aggregate(style_pipeline):
        popular_styles.append({"style": doc["_id"], "count": doc["count"]})
    
    # Total credits spent
    credits_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$credits_spent"}}}
    ]
    total_credits = 0
    async for doc in db.story_projects.aggregate(credits_pipeline):
        total_credits = doc.get("total", 0)
    
    return {
        "success": True,
        "analytics": {
            "total_projects": total_projects,
            "projects_by_status": status_counts,
            "popular_styles": popular_styles,
            "total_credits_spent": total_credits
        }
    }
