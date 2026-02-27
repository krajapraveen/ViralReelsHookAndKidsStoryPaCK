"""
Story Episode Creator - Rebuilt from Story Series
"Turn one idea into a binge-worthy mini series."

3-Step Guided Wizard:
- Step 1: Enter Your Idea (2-3 lines)
- Step 2: Choose Series Length (3/5/7 episodes)
- Step 3: Generate Series

Zero AI Cost - Uses templates
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import random
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/story-episode-creator", tags=["Story Episode Creator"])

# =============================================================================
# COPYRIGHT PROTECTION - BLOCKED KEYWORDS
# =============================================================================
BLOCKED_KEYWORDS = [
    # Disney
    "mickey", "minnie", "donald duck", "goofy", "pluto", "elsa", "anna", "moana",
    "simba", "nemo", "dory", "woody", "buzz lightyear", "frozen",
    # Marvel
    "spider-man", "spiderman", "iron man", "hulk", "thor", "avengers", "captain america",
    "black widow", "thanos", "groot", "deadpool",
    # DC
    "batman", "superman", "wonder woman", "aquaman", "joker", "harley quinn",
    # Anime
    "naruto", "goku", "dragon ball", "one piece", "luffy", "pokemon", "pikachu",
    # Other IP
    "harry potter", "hogwarts", "shrek", "spongebob", "dora", "peppa pig",
    "paw patrol", "cocomelon", "bluey", "hello kitty", "totoro",
    # Celebrities
    "taylor swift", "beyonce", "drake", "elon musk", "trump", "biden",
    # Brands
    "nike", "adidas", "apple", "google", "amazon", "microsoft", "coca cola"
]

def check_copyright_violation(text: str) -> Optional[str]:
    """Check for copyrighted content"""
    if not text:
        return None
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return keyword
    return None

# =============================================================================
# PRICING - SIMPLIFIED
# =============================================================================
PRICING = {
    "3_episodes": 15,
    "5_episodes": 25,
    "7_episodes": 35,
    "export_pdf": 10,
    "commercial_license": 15
}

# =============================================================================
# EPISODE TEMPLATES (No AI Cost)
# =============================================================================
EPISODE_STRUCTURES = {
    "opening": [
        "{hero} discovers something unexpected in their everyday life.",
        "A mysterious event changes {hero}'s world forever.",
        "{hero} receives a strange message that starts an adventure.",
        "Everything seems normal until {hero} finds something unusual.",
        "The day begins like any other, but {hero} soon learns otherwise."
    ],
    "rising_action": [
        "{hero} faces their first major challenge.",
        "New allies appear to help {hero} on their journey.",
        "A hidden secret is revealed that changes everything.",
        "{hero} must make a difficult choice.",
        "The stakes get higher as {hero} ventures deeper."
    ],
    "climax": [
        "{hero} confronts the biggest obstacle yet.",
        "Everything {hero} has learned is put to the test.",
        "A surprise twist forces {hero} to think differently.",
        "{hero} discovers their true strength.",
        "The moment of truth arrives for {hero}."
    ],
    "falling_action": [
        "{hero} begins to see the path forward.",
        "Allies come together to support {hero}.",
        "The pieces of the puzzle start to fit together.",
        "{hero} gains new understanding.",
        "Hope returns as {hero} finds a solution."
    ],
    "resolution": [
        "{hero} achieves their goal and celebrates.",
        "The adventure ends, but the memories last forever.",
        "{hero} returns home changed for the better.",
        "New friendships are celebrated.",
        "And so, {hero}'s journey continues..."
    ]
}

CLIFFHANGERS = [
    "But just as {hero} relaxed, a shadow appeared...",
    "Little did {hero} know, someone was watching...",
    "And then, something unexpected happened...",
    "The ground began to shake beneath {hero}'s feet...",
    "A mysterious figure stepped out of the darkness...",
    "But the adventure was far from over...",
    "What {hero} saw next changed everything...",
    "And that's when {hero} heard a sound that changed everything..."
]

EPISODE_HOOKS = [
    "What will {hero} do next?",
    "Can {hero} overcome this challenge?",
    "The next chapter awaits...",
    "Stay tuned for more adventure!",
    "The story continues..."
]

# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class GenerateRequest(BaseModel):
    story_idea: str = Field(..., min_length=10, max_length=500, description="2-3 line story idea")
    episode_count: int = Field(..., description="3, 5, or 7 episodes")
    add_ons: List[str] = Field(default_factory=list, description="export_pdf, commercial_license")

class ExportRequest(BaseModel):
    series_id: str

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def extract_hero_name(story_idea: str) -> str:
    """Extract or generate hero name from story idea"""
    # Try to find a name (capitalized word)
    words = story_idea.split()
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word and clean_word[0].isupper() and len(clean_word) > 2:
            if clean_word.lower() not in ['the', 'and', 'but', 'for', 'with', 'from']:
                return clean_word
    # Default names if no name found
    return random.choice(["Alex", "Sam", "Luna", "Max", "Mia", "Leo", "Zoe", "Jack"])

def generate_episode(episode_num: int, total_episodes: int, hero: str, story_idea: str) -> dict:
    """Generate a single episode using templates"""
    # Determine arc position
    if episode_num == 1:
        arc_stage = "opening"
    elif episode_num == total_episodes:
        arc_stage = "resolution"
    elif episode_num == total_episodes // 2 + 1:
        arc_stage = "climax"
    elif episode_num < total_episodes // 2 + 1:
        arc_stage = "rising_action"
    else:
        arc_stage = "falling_action"
    
    # Generate episode content
    scene_template = random.choice(EPISODE_STRUCTURES[arc_stage])
    scene_description = scene_template.replace("{hero}", hero)
    
    # Generate title
    title_templates = [
        f"Episode {episode_num}: The {arc_stage.replace('_', ' ').title()}",
        f"Episode {episode_num}: {hero}'s {arc_stage.replace('_', ' ').title()}",
        f"Episode {episode_num}: A New {arc_stage.replace('_', ' ').title()}"
    ]
    title = random.choice(title_templates)
    
    # Generate script outline
    script_points = [scene_description]
    # Add 3-5 more scene beats
    for _ in range(random.randint(3, 5)):
        beat_template = random.choice(EPISODE_STRUCTURES[arc_stage])
        script_points.append(beat_template.replace("{hero}", hero))
    
    # Generate cliffhanger (except for final episode)
    cliffhanger = None
    if episode_num < total_episodes:
        cliffhanger = random.choice(CLIFFHANGERS).replace("{hero}", hero)
    
    # Generate next episode hook
    next_hook = None
    if episode_num < total_episodes:
        next_hook = random.choice(EPISODE_HOOKS).replace("{hero}", hero)
    
    return {
        "episode_number": episode_num,
        "title": title,
        "summary": scene_description,
        "script_outline": script_points,
        "cliffhanger": cliffhanger,
        "next_episode_hook": next_hook
    }

async def deduct_credits(user_id: str, amount: int, ref_type: str, ref_id: str):
    """Atomically deduct credits"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or user.get("credits", 0) < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {amount}, you have {user.get('credits', 0) if user else 0}")
    
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Failed to deduct credits")
    
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "entryType": "CAPTURE",
        "amount": amount,
        "refType": ref_type,
        "refId": ref_id,
        "status": "ACTIVE",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })

# =============================================================================
# SAMPLE PREVIEW DATA (Try Before You Buy)
# =============================================================================
SAMPLE_PREVIEW = {
    "story_idea": "A young inventor named Mia discovers a magical toolbox that brings her drawings to life.",
    "hero_name": "Mia",
    "episode_count": 3,
    "episodes": [
        {
            "episode_number": 1,
            "title": "Episode 1: The Discovery",
            "summary": "Mia discovers something unexpected in her everyday life when she finds a glowing toolbox in her grandmother's attic.",
            "script_outline": [
                "Mia explores her grandmother's dusty attic during a rainy afternoon",
                "She finds a mysterious wooden toolbox with strange symbols",
                "When Mia opens it, the tools inside glow with magical light",
                "Her first drawing - a butterfly - comes to life!"
            ],
            "cliffhanger": "But just as Mia relaxed, a shadow appeared at the attic window...",
            "next_episode_hook": "What will Mia do next?"
        },
        {
            "episode_number": 2,
            "title": "Episode 2: The Rising Challenge",
            "summary": "Mia faces her first major challenge when her magical creations start causing chaos in the neighborhood.",
            "script_outline": [
                "Mia's drawings are running wild through the streets",
                "The neighborhood kids think it's amazing but adults are worried",
                "Mia must learn to control her magical abilities",
                "She discovers the toolbox responds to her emotions"
            ],
            "cliffhanger": "Little did Mia know, someone was watching her every move...",
            "next_episode_hook": "Can Mia overcome this challenge?"
        },
        {
            "episode_number": 3,
            "title": "Episode 3: The Resolution",
            "summary": "Mia achieves her goal and celebrates when she learns the true power of creativity and friendship.",
            "script_outline": [
                "Mia realizes the toolbox belonged to her great-grandmother, also an inventor",
                "She uses her powers to help a lost child find their way home",
                "The neighborhood embraces Mia's gift",
                "Mia promises to use her magic responsibly"
            ],
            "cliffhanger": None,
            "next_episode_hook": None
        }
    ],
    "is_preview": True,
    "preview_message": "This is a FREE preview. Generate your own unique series!"
}

# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/config")
async def get_config():
    """Get feature configuration"""
    return {
        "pricing": {
            "3_episodes": {"credits": PRICING["3_episodes"], "label": "3 Episodes"},
            "5_episodes": {"credits": PRICING["5_episodes"], "label": "5 Episodes"},
            "7_episodes": {"credits": PRICING["7_episodes"], "label": "7 Episodes"}
        },
        "add_ons": {
            "export_pdf": {"credits": PRICING["export_pdf"], "label": "Export PDF"},
            "commercial_license": {"credits": PRICING["commercial_license"], "label": "Commercial License"}
        },
        "steps": [
            {"step": 1, "title": "Enter Your Idea", "description": "Describe your story in 2-3 lines"},
            {"step": 2, "title": "Choose Length", "description": "Select 3, 5, or 7 episodes"},
            {"step": 3, "title": "Generate", "description": "Create your mini series"}
        ]
    }

@router.get("/preview")
async def get_preview():
    """Get a FREE sample preview - Try Before You Buy"""
    return SAMPLE_PREVIEW

@router.post("/generate")
@limiter.limit("10/minute")
async def generate_series(
    request: Request,
    data: GenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate episode series - 3-step wizard endpoint"""
    user_id = user["id"]
    user_plan = user.get("plan", "free")
    
    # Validate episode count
    if data.episode_count not in [3, 5, 7]:
        raise HTTPException(status_code=400, detail="Episode count must be 3, 5, or 7")
    
    # COPYRIGHT CHECK
    violation = check_copyright_violation(data.story_idea)
    if violation:
        raise HTTPException(
            status_code=400, 
            detail=f"Branded or copyrighted content is not allowed. Detected: '{violation}'"
        )
    
    # Calculate total cost
    base_cost = PRICING[f"{data.episode_count}_episodes"]
    addon_cost = sum(PRICING.get(addon, 0) for addon in data.add_ons)
    total_cost = base_cost + addon_cost
    
    # Generate series ID
    series_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, total_cost, "STORY_EPISODE_CREATOR", series_id)
    
    # Extract hero name from story idea
    hero = extract_hero_name(data.story_idea)
    
    # Generate all episodes
    episodes = []
    for i in range(1, data.episode_count + 1):
        episode = generate_episode(i, data.episode_count, hero, data.story_idea)
        episodes.append(episode)
    
    # Determine if watermark needed (free users)
    has_watermark = user_plan == "free" and "commercial_license" not in data.add_ons
    
    # Store series
    series_doc = {
        "id": series_id,
        "userId": user_id,
        "story_idea": data.story_idea,
        "hero_name": hero,
        "episode_count": data.episode_count,
        "episodes": episodes,
        "add_ons": data.add_ons,
        "credits_used": total_cost,
        "has_watermark": has_watermark,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.story_episode_series.insert_one(series_doc)
    
    return {
        "success": True,
        "series_id": series_id,
        "hero_name": hero,
        "episode_count": data.episode_count,
        "episodes": episodes,
        "credits_used": total_cost,
        "has_watermark": has_watermark,
        "message": f"Your {data.episode_count}-episode series is ready!"
    }

@router.post("/export-pdf")
async def export_pdf(
    data: ExportRequest,
    user: dict = Depends(get_current_user)
):
    """Export series as PDF - charges extra credits"""
    user_id = user["id"]
    
    # Get series
    series = await db.story_episode_series.find_one(
        {"id": data.series_id, "userId": user_id},
        {"_id": 0}
    )
    
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    # Check if already has PDF export
    if "export_pdf" in series.get("add_ons", []):
        return {"success": True, "message": "PDF export already unlocked", "series": series}
    
    # Deduct credits for PDF export
    export_id = str(uuid.uuid4())
    await deduct_credits(user_id, PRICING["export_pdf"], "PDF_EXPORT", export_id)
    
    # Update series with export addon
    await db.story_episode_series.update_one(
        {"id": data.series_id},
        {"$push": {"add_ons": "export_pdf"}}
    )
    
    return {
        "success": True,
        "message": "PDF export unlocked!",
        "credits_used": PRICING["export_pdf"]
    }

@router.get("/series/{series_id}")
async def get_series(series_id: str, user: dict = Depends(get_current_user)):
    """Get series details"""
    series = await db.story_episode_series.find_one(
        {"id": series_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    return series

@router.get("/history")
async def get_history(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get user's series history"""
    series_list = await db.story_episode_series.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    return {"series": series_list}
