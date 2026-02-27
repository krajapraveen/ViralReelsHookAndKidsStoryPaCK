"""
YouTube Thumbnail Text Generator
Template-based, no AI, <200ms response
Price: 5 credits
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import time
from datetime import datetime, timezone
from bson import ObjectId

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/youtube-thumbnail-generator", tags=["YouTube Thumbnail Generator"])

# ==================== COPYRIGHT PROTECTION ====================
BLOCKED_KEYWORDS = [
    "marvel", "disney", "pixar", "harry potter", "pokemon", "naruto", "spiderman", 
    "batman", "superman", "avengers", "frozen", "mickey", "donald duck", "goofy",
    "star wars", "lord of the rings", "game of thrones", "stranger things",
    "netflix", "amazon", "google", "apple", "microsoft", "facebook", "instagram",
    "tiktok", "youtube", "twitter", "coca cola", "pepsi", "mcdonalds", "nike", "adidas",
    "gucci", "louis vuitton", "rolex", "ferrari", "lamborghini", "tesla", "elon musk",
    "jeff bezos", "mark zuckerberg", "bill gates", "taylor swift", "beyonce", "drake",
    "kanye", "kardashian", "jenner", "bieber", "ariana grande", "selena gomez"
]

def check_copyright(text: str) -> bool:
    """Returns True if blocked content detected"""
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# ==================== DEFAULT TEMPLATES ====================
DEFAULT_HOOKS = [
    # Curiosity-driven
    {"niche": "general", "emotion": "curiosity", "template": "Why Nobody Talks About {topic}"},
    {"niche": "general", "emotion": "curiosity", "template": "The Hidden Truth About {topic}"},
    {"niche": "general", "emotion": "curiosity", "template": "{topic} Secrets Revealed"},
    {"niche": "general", "emotion": "curiosity", "template": "What They Don't Tell You About {topic}"},
    {"niche": "general", "emotion": "curiosity", "template": "I Discovered {topic}"},
    
    # Shock/Surprise
    {"niche": "general", "emotion": "shock", "template": "{topic} Changed Everything"},
    {"niche": "general", "emotion": "shock", "template": "I Was Wrong About {topic}"},
    {"niche": "general", "emotion": "shock", "template": "{topic} Exposed"},
    {"niche": "general", "emotion": "shock", "template": "The {topic} Lie"},
    {"niche": "general", "emotion": "shock", "template": "{topic} Is Dead"},
    
    # Fear/Urgency
    {"niche": "general", "emotion": "fear", "template": "Stop Doing {topic} NOW"},
    {"niche": "general", "emotion": "fear", "template": "{topic} Is Killing Your Growth"},
    {"niche": "general", "emotion": "fear", "template": "Warning: {topic}"},
    {"niche": "general", "emotion": "fear", "template": "Don't Make This {topic} Mistake"},
    {"niche": "general", "emotion": "fear", "template": "{topic} Red Flags"},
    
    # Excitement
    {"niche": "general", "emotion": "excitement", "template": "{topic} That Actually Works"},
    {"niche": "general", "emotion": "excitement", "template": "Best {topic} Ever"},
    {"niche": "general", "emotion": "excitement", "template": "{topic} Game Changer"},
    {"niche": "general", "emotion": "excitement", "template": "This {topic} Is INSANE"},
    {"niche": "general", "emotion": "excitement", "template": "{topic} Breakthrough"},
    
    # Tutorial/How-to
    {"niche": "tutorial", "emotion": "curiosity", "template": "How I Master {topic}"},
    {"niche": "tutorial", "emotion": "curiosity", "template": "{topic} In 5 Minutes"},
    {"niche": "tutorial", "emotion": "curiosity", "template": "Easy {topic} Tutorial"},
    {"niche": "tutorial", "emotion": "excitement", "template": "{topic} Made Simple"},
    {"niche": "tutorial", "emotion": "excitement", "template": "Quick {topic} Guide"},
    
    # Tech niche
    {"niche": "tech", "emotion": "shock", "template": "{topic} Is Broken"},
    {"niche": "tech", "emotion": "curiosity", "template": "{topic} Tips Nobody Knows"},
    {"niche": "tech", "emotion": "excitement", "template": "New {topic} Update"},
    {"niche": "tech", "emotion": "fear", "template": "{topic} Security Alert"},
    
    # Gaming niche
    {"niche": "gaming", "emotion": "excitement", "template": "{topic} World Record"},
    {"niche": "gaming", "emotion": "shock", "template": "{topic} Rage Quit"},
    {"niche": "gaming", "emotion": "curiosity", "template": "Secret {topic} Trick"},
    
    # Finance niche
    {"niche": "finance", "emotion": "fear", "template": "{topic} Market Crash?"},
    {"niche": "finance", "emotion": "curiosity", "template": "How To {topic} Rich"},
    {"niche": "finance", "emotion": "excitement", "template": "{topic} Made Me $$$"},
    
    # Fitness niche
    {"niche": "fitness", "emotion": "shock", "template": "{topic} Is Making You Fat"},
    {"niche": "fitness", "emotion": "excitement", "template": "{topic} Results In Days"},
    {"niche": "fitness", "emotion": "curiosity", "template": "My {topic} Transformation"},
]

NICHES = ["general", "tutorial", "tech", "gaming", "finance", "fitness", "lifestyle", "food", "travel", "business"]
EMOTIONS = ["curiosity", "shock", "fear", "excitement", "inspiration"]

# ==================== MODELS ====================
class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100)
    niche: str = Field(default="general")
    emotion: str = Field(default="curiosity")

class ThumbnailText(BaseModel):
    original: str
    all_caps: str
    title_case: str
    bold_short: str

class GenerateResponse(BaseModel):
    success: bool
    thumbnails: List[ThumbnailText]
    credits_used: int
    generation_time_ms: int

# ==================== HELPER FUNCTIONS ====================
def format_thumbnail_text(text: str) -> ThumbnailText:
    """Convert text to 3 styles"""
    # Clean up and format
    words = text.split()
    short_version = " ".join(words[:4]) if len(words) > 4 else text
    
    return ThumbnailText(
        original=text,
        all_caps=text.upper(),
        title_case=text.title(),
        bold_short=short_version.upper()
    )

async def get_hooks_from_db(niche: str, emotion: str, count: int = 10) -> List[dict]:
    """Fetch hooks from database or use defaults"""
    hooks = await db.thumbnail_hooks.find({
        "$or": [
            {"niche": niche, "emotion": emotion, "active": {"$ne": False}},
            {"niche": "general", "emotion": emotion, "active": {"$ne": False}},
            {"niche": niche, "active": {"$ne": False}},
            {"niche": "general", "active": {"$ne": False}}
        ]
    }).to_list(100)
    
    if not hooks:
        # Use defaults matching criteria
        hooks = [h for h in DEFAULT_HOOKS if h.get("niche") == niche or h.get("niche") == "general"]
        if emotion != "curiosity":
            emotion_hooks = [h for h in hooks if h.get("emotion") == emotion]
            if emotion_hooks:
                hooks = emotion_hooks
    
    # Randomize and limit
    random.shuffle(hooks)
    return hooks[:count]

async def track_generation(user_id: str, niche: str, emotion: str, topic: str):
    """Track generation for analytics"""
    await db.template_analytics.insert_one({
        "feature": "youtube_thumbnail_generator",
        "user_id": user_id,
        "niche": niche,
        "emotion": emotion,
        "topic": topic,
        "created_at": datetime.now(timezone.utc)
    })

# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    """Get generator configuration"""
    return {
        "niches": NICHES,
        "emotions": EMOTIONS,
        "credit_cost": 5,
        "output_count": 10,
        "max_topic_length": 100
    }

@router.post("/generate", response_model=GenerateResponse)
async def generate_thumbnails(request: GenerateRequest, user: dict = Depends(get_current_user)):
    """Generate 10 thumbnail text ideas in 3 styles"""
    start_time = time.time()
    
    # Copyright check
    if check_copyright(request.topic):
        raise HTTPException(status_code=400, detail="Input contains blocked content. Please avoid copyrighted or trademarked terms.")
    
    # Check credits BEFORE generation
    if user.get("credits", 0) < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits. 5 credits required.")
    
    # Deduct credits
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -5}}
    )
    
    try:
        # Fetch templates
        hooks = await get_hooks_from_db(request.niche, request.emotion, 10)
        
        # Generate thumbnails
        thumbnails = []
        for hook in hooks:
            template = hook.get("template", "{topic} Revealed")
            text = template.replace("{topic}", request.topic.strip())
            thumbnails.append(format_thumbnail_text(text))
        
        # Ensure we have 10 results
        while len(thumbnails) < 10:
            # Generate variations
            base = f"{request.topic} Secrets"
            thumbnails.append(format_thumbnail_text(base))
        
        # Track for analytics
        await track_generation(str(user["id"]), request.niche, request.emotion, request.topic)
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return GenerateResponse(
            success=True,
            thumbnails=thumbnails[:10],
            credits_used=5,
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        # Refund on error
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": 5}}
        )
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/hooks")
async def get_hooks(admin: dict = Depends(get_admin_user)):
    """Get all thumbnail hooks"""
    hooks = await db.thumbnail_hooks.find({}).to_list(500)
    for h in hooks:
        h["id"] = str(h.pop("_id"))
    return {"hooks": hooks}

@router.post("/admin/hooks")
async def create_hook(data: dict, admin: dict = Depends(get_admin_user)):
    """Create new hook template"""
    hook = {
        "niche": data.get("niche", "general"),
        "emotion": data.get("emotion", "curiosity"),
        "template": data.get("template"),
        "active": data.get("active", True),
        "created_at": datetime.now(timezone.utc),
        "created_by": str(admin["_id"])
    }
    result = await db.thumbnail_hooks.insert_one(hook)
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/admin/hooks/{hook_id}")
async def delete_hook(hook_id: str, admin: dict = Depends(get_admin_user)):
    """Delete hook template"""
    result = await db.thumbnail_hooks.delete_one({"_id": ObjectId(hook_id)})
    return {"success": result.deleted_count > 0}

# Initialize default hooks
async def init_default_hooks():
    """Initialize default hooks if none exist"""
    count = await db.thumbnail_hooks.count_documents({})
    if count == 0:
        for hook in DEFAULT_HOOKS:
            hook["active"] = True
            hook["created_at"] = datetime.now(timezone.utc)
        await db.thumbnail_hooks.insert_many(DEFAULT_HOOKS)
