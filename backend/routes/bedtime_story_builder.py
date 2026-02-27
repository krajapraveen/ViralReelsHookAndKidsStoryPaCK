"""
Kids Bedtime Story Audio Script Builder
Template-based story script generator with voice notes and SFX cues.
No AI, no external APIs - pure template assembly.
"""

import random
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared import get_current_user, get_admin_user, db

logger = logging.getLogger("creatorstudio")
router = APIRouter(prefix="/bedtime-story-builder", tags=["Bedtime Story Builder"])
limiter = Limiter(key_func=get_remote_address)

# Pricing
STORY_COST = 10
PDF_EXPORT_COST = 2
SERIES_PACK_COST = 25

# =============================================================================
# BLOCKED KEYWORDS
# =============================================================================

BLOCKED_KEYWORDS = [
    "marvel", "disney", "pixar", "ghibli", "harry potter", "pokemon",
    "naruto", "avengers", "spiderman", "batman", "frozen", "elsa",
    "mickey", "minnie", "dora", "peppa", "paw patrol", "bluey",
    "cocomelon", "baby shark", "taylor swift", "beyonce"
]


def check_blocked_content(text: str) -> bool:
    """Check for blocked content"""
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return False
    return True


# =============================================================================
# MODELS
# =============================================================================

class GenerateStoryRequest(BaseModel):
    age_group: str = Field(..., description="3-5, 6-8, or 9-12")
    theme: str
    moral: str
    length: str = Field(..., description="3, 5, or 8 minutes")
    voice_style: str
    child_name: Optional[str] = None


# =============================================================================
# DEFAULT DATA - COMPREHENSIVE TEMPLATES
# =============================================================================

DEFAULT_THEMES = [
    "Friendship", "Bravery", "Kindness", "Sharing", "Honesty",
    "Bedtime Calm", "Animals", "Magic", "School", "Nature",
    "Adventure", "Family", "Dreams", "Helping Others"
]

DEFAULT_MORALS = [
    "Be kind", "Try again", "Tell truth", "Help friends",
    "Be brave", "Be thankful", "Share with others", "Listen carefully",
    "Believe in yourself", "Work together"
]

DEFAULT_VOICE_STYLES = [
    {"id": "calm_parent", "name": "Calm Mom/Dad"},
    {"id": "playful_storyteller", "name": "Playful Storyteller"},
    {"id": "gentle_teacher", "name": "Gentle Teacher"}
]

DEFAULT_CHARACTERS = [
    "Luna the little rabbit", "Max the curious kitten", "Bella the friendly bear",
    "Oliver the wise owl", "Lily the adventurous ladybug", "Sam the sleepy squirrel",
    "Rosie the gentle deer", "Charlie the brave chipmunk", "Daisy the dancing butterfly",
    "Finn the friendly fox", "Ruby the rainbow bird", "Teddy the tiny turtle"
]

DEFAULT_PLACES = [
    "a quiet forest", "a cozy meadow", "a magical garden", "a peaceful pond",
    "a sunny hillside", "a dreamy cloud kingdom", "a sparkling stream",
    "a starlit clearing", "a warm little cottage", "a secret treehouse"
]

DEFAULT_OBJECTS = [
    "a glowing acorn", "a special feather", "a tiny star", "a magical flower",
    "a friendship bracelet", "a golden leaf", "a dream catcher", "a soft blanket",
    "a music box", "a wishing stone"
]

# Story skeleton templates by length
STORY_SKELETONS = {
    "3": {
        "scenes": [
            {"scene_type": "opening", "beats": 2, "pacing": "slow"},
            {"scene_type": "setup", "beats": 2, "pacing": "normal"},
            {"scene_type": "lesson", "beats": 2, "pacing": "slow"},
            {"scene_type": "calm_end", "beats": 2, "pacing": "very_slow"}
        ]
    },
    "5": {
        "scenes": [
            {"scene_type": "opening", "beats": 3, "pacing": "slow"},
            {"scene_type": "setup", "beats": 3, "pacing": "normal"},
            {"scene_type": "conflict", "beats": 3, "pacing": "normal"},
            {"scene_type": "lesson", "beats": 3, "pacing": "slow"},
            {"scene_type": "calm_end", "beats": 3, "pacing": "very_slow"}
        ]
    },
    "8": {
        "scenes": [
            {"scene_type": "opening", "beats": 4, "pacing": "slow"},
            {"scene_type": "setup", "beats": 4, "pacing": "normal"},
            {"scene_type": "conflict", "beats": 4, "pacing": "normal"},
            {"scene_type": "challenge", "beats": 3, "pacing": "normal"},
            {"scene_type": "resolution", "beats": 3, "pacing": "slow"},
            {"scene_type": "lesson", "beats": 3, "pacing": "slow"},
            {"scene_type": "calm_end", "beats": 4, "pacing": "very_slow"}
        ]
    }
}

# Narration sentences by scene type and theme
DEFAULT_NARRATION_TEMPLATES = {
    "opening": {
        "Friendship": [
            "Once upon a time, [PAUSE 1s] in {place}, there lived {character}.",
            "In a world where friends are like stars, [PAUSE 1s] our story begins...",
            "The moon was rising softly [PAUSE 0.5s] as {character} began a special journey.",
            "Close your eyes and imagine {place}... [PAUSE 1s] Are you ready?"
        ],
        "Bravery": [
            "Once upon a time, [PAUSE 1s] in {place}, lived {character} who dreamed of being brave.",
            "In the land of gentle heroes, [PAUSE 1s] a new adventure was about to begin...",
            "The evening stars twinkled [PAUSE 0.5s] as {character} made a brave decision."
        ],
        "Kindness": [
            "Once upon a time, [PAUSE 1s] in the warmest corner of {place}, lived {character}.",
            "In a world where kindness shines bright, [PAUSE 1s] our gentle story begins...",
            "The sunset painted the sky pink [PAUSE 0.5s] as {character} set out to spread joy."
        ],
        "Bedtime Calm": [
            "The stars began to twinkle [PAUSE 1s] as night came to {place}...",
            "Shhhh... [WHISPER] Listen closely... [PAUSE 1s] It's time for a peaceful story.",
            "The moon smiled down [PAUSE 0.5s] on {place} where {character} was getting sleepy."
        ],
        "default": [
            "Once upon a time, [PAUSE 1s] in {place}, there lived {character}.",
            "Our story begins [PAUSE 0.5s] on a beautiful evening in {place}...",
            "Long ago, [PAUSE 1s] when the world was full of wonder, {character} lived happily."
        ]
    },
    "setup": {
        "default": [
            "[SMILE] {character} loved to explore and discover new things.",
            "Every day was an adventure, [PAUSE 0.5s] full of wonderful surprises.",
            "One special evening, [PAUSE 0.5s] something magical was about to happen.",
            "{character} found {object} that sparkled in the moonlight. [PAUSE 0.5s]",
            "The gentle breeze carried whispers of something exciting... [PAUSE 0.5s]"
        ]
    },
    "conflict": {
        "default": [
            "But then, [PAUSE 0.5s] [SLOW] something unexpected happened...",
            "{character} wasn't sure what to do. [PAUSE 1s] Have you ever felt that way?",
            "The path ahead seemed a little uncertain... [PAUSE 0.5s]",
            "[EMPHASIZE] This was the moment that would change everything."
        ]
    },
    "challenge": {
        "default": [
            "{character} took a deep breath [PAUSE 0.5s] and tried again.",
            "It wasn't easy, [PAUSE 0.5s] but giving up wasn't an option.",
            "With determination in their heart, [PAUSE 0.5s] {character} pressed on.",
            "Sometimes the hardest things [PAUSE 0.5s] teach us the most."
        ]
    },
    "resolution": {
        "default": [
            "[SMILE] And then, something wonderful happened...",
            "Everything started to make sense [PAUSE 0.5s] when {character} realized...",
            "The answer had been there all along, [PAUSE 0.5s] waiting to be discovered.",
            "[SLOW] Like magic, everything fell into place."
        ]
    },
    "lesson": {
        "Be kind": [
            "[SLOW] {character} learned that kindness makes everyone feel warm inside.",
            "Being kind, [PAUSE 0.5s] even in small ways, [PAUSE 0.5s] creates big happiness.",
            "[EMPHASIZE] Kindness is like a gentle light that never runs out."
        ],
        "Try again": [
            "[SLOW] {character} discovered that trying again is how we grow stronger.",
            "Every mistake [PAUSE 0.5s] is just another step toward success.",
            "[EMPHASIZE] The bravest thing is to try, try again."
        ],
        "Tell truth": [
            "[SLOW] {character} learned that the truth, while sometimes hard, sets us free.",
            "Honesty [PAUSE 0.5s] builds bridges of trust with everyone we meet.",
            "[EMPHASIZE] The truth is always the best friend we can have."
        ],
        "Help friends": [
            "[SLOW] {character} discovered that helping others fills our own heart with joy.",
            "When we help our friends, [PAUSE 0.5s] we make the world a little brighter.",
            "[EMPHASIZE] Together, we can do amazing things."
        ],
        "Be brave": [
            "[SLOW] {character} learned that being brave doesn't mean not being scared.",
            "Courage [PAUSE 0.5s] is doing what's right even when it's hard.",
            "[EMPHASIZE] True bravery comes from the heart."
        ],
        "Be thankful": [
            "[SLOW] {character} learned to be thankful for all the little blessings.",
            "Gratitude [PAUSE 0.5s] turns ordinary days into wonderful adventures.",
            "[EMPHASIZE] When we're thankful, happiness grows."
        ],
        "default": [
            "[SLOW] And so, {character} learned something very special that day.",
            "The most important lessons [PAUSE 0.5s] come from the heart.",
            "[EMPHASIZE] This was a gift that would last forever."
        ]
    },
    "calm_end": {
        "default": [
            "[WHISPER] And as the stars twinkled above, [PAUSE 1s] {character} felt peaceful and sleepy...",
            "[SLOW] The moon smiled down, [PAUSE 0.5s] wrapping everything in soft, dreamy light...",
            "[WHISPER] Close your eyes now... [PAUSE 1s] The story is ending, [PAUSE 0.5s] and sweet dreams are beginning...",
            "[SLOW] {character} yawned softly [PAUSE 0.5s] and snuggled into a warm, cozy sleep...",
            "[WHISPER] And they all slept peacefully, [PAUSE 1s] knowing tomorrow would bring new adventures...",
            "[SLOW] The night wrapped its gentle arms around {place}... [PAUSE 1s] Goodnight, little one...",
            "[WHISPER] Sweet dreams... [PAUSE 2s] The End."
        ]
    }
}

# Voice notes by style
VOICE_NOTES = {
    "calm_parent": {
        "opening": "Speak slowly and warmly, like sharing a secret with your child. Keep your voice soft and inviting.",
        "setup": "Maintain a gentle pace. Smile as you speak - they can hear it in your voice.",
        "conflict": "Slightly lower your voice to create gentle tension. Keep it mysterious but not scary.",
        "challenge": "Add warmth and encouragement. Your child should feel supported.",
        "resolution": "Let relief and joy flow into your voice. This is the happy turning point.",
        "lesson": "Slow down significantly. This is the heart of the story. Make each word count.",
        "calm_end": "Whisper softly. Let your voice become drowsy. This is the lullaby part."
    },
    "playful_storyteller": {
        "opening": "Start with energy and wonder! Use your 'magic storyteller' voice.",
        "setup": "Be animated and expressive. Create voices for characters if you like!",
        "conflict": "Build drama playfully - make it an adventure, not scary.",
        "challenge": "Encourage with enthusiasm! Cheer the character on.",
        "resolution": "Celebrate with joy! Let your voice show the triumph.",
        "lesson": "Transition to a wiser, gentler tone. Become the sage storyteller.",
        "calm_end": "Slowly wind down your energy. Transform into a gentle, sleepy narrator."
    },
    "gentle_teacher": {
        "opening": "Begin with clear, calm articulation. Create a learning atmosphere.",
        "setup": "Use a nurturing tone that invites curiosity.",
        "conflict": "Present the problem thoughtfully, inviting the listener to think.",
        "challenge": "Speak with patient encouragement.",
        "resolution": "Show satisfaction in discovery. Celebrate learning.",
        "lesson": "This is teaching time - slow and meaningful. Let each word land.",
        "calm_end": "Transition to a soothing, almost lullaby-like quality."
    }
}

# SFX cues by theme and scene
SFX_CUES = {
    "opening": [
        "[SFX: soft wind chimes]",
        "[SFX: gentle crickets chirping]",
        "[SFX: soft owl hooting in distance]",
        "[SFX: magical sparkle sound]"
    ],
    "setup": [
        "[SFX: soft footsteps on grass]",
        "[SFX: leaves rustling gently]",
        "[SFX: birds chirping softly]",
        "[SFX: stream bubbling quietly]"
    ],
    "conflict": [
        "[SFX: thoughtful humming]",
        "[SFX: gentle questioning tone]",
        "[SFX: soft mystery chime]"
    ],
    "challenge": [
        "[SFX: determined footsteps]",
        "[SFX: encouraging musical note]"
    ],
    "resolution": [
        "[SFX: happy sparkle sound]",
        "[SFX: warm musical flourish]",
        "[SFX: joyful chime]"
    ],
    "lesson": [
        "[SFX: gentle heartwarming music]",
        "[SFX: soft wisdom chime]"
    ],
    "calm_end": [
        "[SFX: soft lullaby humming]",
        "[SFX: gentle music box]",
        "[SFX: peaceful night sounds]",
        "[SFX: soft yawning sound]",
        "[SFX: sleepy wind chimes]",
        "[SFX: fading crickets]"
    ],
    "Bedtime Calm": [
        "[SFX: soft breathing]",
        "[SFX: cozy blanket rustling]",
        "[SFX: gentle heartbeat]"
    ],
    "Animals": [
        "[SFX: soft animal sounds]",
        "[SFX: gentle paw steps]"
    ],
    "Magic": [
        "[SFX: sparkle magic sound]",
        "[SFX: wand wave effect]"
    ],
    "Nature": [
        "[SFX: gentle rain drops]",
        "[SFX: peaceful forest sounds]"
    ]
}


# =============================================================================
# DATABASE SEEDING
# =============================================================================

async def seed_bedtime_story_data():
    """Seed default data if collections are empty"""
    
    # Seed themes
    if await db.story_themes.count_documents({}) == 0:
        import uuid
        themes = [{"id": str(uuid.uuid4()), "name": t, "active": True} for t in DEFAULT_THEMES]
        await db.story_themes.insert_many(themes)
        logger.info(f"Seeded {len(themes)} story themes")
    
    # Seed morals
    if await db.story_morals.count_documents({}) == 0:
        import uuid
        morals = [{"id": str(uuid.uuid4()), "name": m, "active": True} for m in DEFAULT_MORALS]
        await db.story_morals.insert_many(morals)
        logger.info(f"Seeded {len(morals)} story morals")


# =============================================================================
# STORY GENERATION ENGINE
# =============================================================================

def fill_placeholders(text: str, context: Dict[str, str]) -> str:
    """Fill template placeholders with context values"""
    result = text
    for key, value in context.items():
        result = result.replace("{" + key + "}", value)
    return result


def generate_story_script(
    age_group: str,
    theme: str,
    moral: str,
    length: str,
    voice_style: str,
    child_name: Optional[str] = None
) -> Dict[str, Any]:
    """Generate complete story script with voice notes and SFX"""
    
    # Select random elements
    character = random.choice(DEFAULT_CHARACTERS)
    place = random.choice(DEFAULT_PLACES)
    obj = random.choice(DEFAULT_OBJECTS)
    
    # Context for placeholder filling
    context = {
        "character": character,
        "place": place,
        "object": obj,
        "childName": child_name or "little one"
    }
    
    # Get skeleton based on length
    skeleton = STORY_SKELETONS.get(length, STORY_SKELETONS["5"])
    
    # Build script
    script_lines = []
    voice_notes = []
    sfx_cues = []
    
    for scene in skeleton["scenes"]:
        scene_type = scene["scene_type"]
        beats = scene["beats"]
        pacing = scene["pacing"]
        
        # Get narration templates for this scene
        scene_templates = DEFAULT_NARRATION_TEMPLATES.get(scene_type, {})
        
        # Try theme-specific, then moral-specific, then default
        templates = scene_templates.get(theme, 
                    scene_templates.get(moral, 
                    scene_templates.get("default", [])))
        
        if not templates:
            templates = scene_templates.get("default", ["The story continues..."])
        
        # Select templates for this scene
        selected = random.sample(templates, min(beats, len(templates)))
        
        # Fill placeholders and add to script
        for template in selected:
            line = fill_placeholders(template, context)
            script_lines.append(line)
        
        # Add pacing pause between scenes
        if pacing == "slow":
            script_lines.append("[PAUSE 2s]")
        elif pacing == "very_slow":
            script_lines.append("[PAUSE 3s]")
        else:
            script_lines.append("[PAUSE 1s]")
        
        # Add voice note for this scene
        style_notes = VOICE_NOTES.get(voice_style, VOICE_NOTES["calm_parent"])
        if scene_type in style_notes:
            voice_notes.append({
                "scene": scene_type.replace("_", " ").title(),
                "note": style_notes[scene_type],
                "pacing": pacing
            })
        
        # Add SFX cues
        scene_sfx = SFX_CUES.get(scene_type, [])
        theme_sfx = SFX_CUES.get(theme, [])
        all_sfx = scene_sfx + theme_sfx
        
        if all_sfx:
            selected_sfx = random.choice(all_sfx)
            sfx_cues.append({
                "scene": scene_type.replace("_", " ").title(),
                "cue": selected_sfx
            })
    
    # Calculate approximate duration
    word_count = len(" ".join(script_lines).split())
    reading_time_mins = word_count / 130  # Average reading speed for children's stories
    
    return {
        "script": "\n\n".join(script_lines),
        "voice_notes": voice_notes,
        "sfx_cues": sfx_cues,
        "metadata": {
            "character": character,
            "place": place.replace("a ", "").replace("an ", ""),
            "word_count": word_count,
            "estimated_duration": f"{int(reading_time_mins)} min",
            "target_duration": f"{length} min"
        }
    }


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/config")
async def get_config():
    """Get configuration for the bedtime story builder"""
    await seed_bedtime_story_data()
    
    # Fetch themes and morals from DB
    themes = await db.story_themes.find({"active": True}, {"_id": 0}).to_list(length=50)
    morals = await db.story_morals.find({"active": True}, {"_id": 0}).to_list(length=50)
    
    return {
        "ageGroups": [
            {"id": "3-5", "name": "3-5 years", "description": "Toddlers & Preschool"},
            {"id": "6-8", "name": "6-8 years", "description": "Early Readers"},
            {"id": "9-12", "name": "9-12 years", "description": "Middle Grade"}
        ],
        "themes": [t["name"] for t in themes] if themes else DEFAULT_THEMES,
        "morals": [m["name"] for m in morals] if morals else DEFAULT_MORALS,
        "lengths": [
            {"id": "3", "name": "3 min (Short)", "description": "Quick bedtime story"},
            {"id": "5", "name": "5 min (Standard)", "description": "Perfect length", "default": True},
            {"id": "8", "name": "8 min (Long)", "description": "Extended adventure"}
        ],
        "voiceStyles": DEFAULT_VOICE_STYLES,
        "pricing": {
            "story": STORY_COST,
            "pdfExport": PDF_EXPORT_COST,
            "seriesPack": SERIES_PACK_COST
        }
    }


@router.post("/generate")
@limiter.limit("20/minute")
async def generate_story(
    request: Request,
    data: GenerateStoryRequest,
    user: dict = Depends(get_current_user)
):
    """Generate a bedtime story script"""
    
    # Validate inputs
    if data.age_group not in ["3-5", "6-8", "9-12"]:
        raise HTTPException(status_code=400, detail="Invalid age group")
    
    if data.length not in ["3", "5", "8"]:
        raise HTTPException(status_code=400, detail="Invalid length")
    
    # Check blocked content in optional child name
    if data.child_name and not check_blocked_content(data.child_name):
        raise HTTPException(
            status_code=400,
            detail="Copyrighted characters/brands are not allowed. Please use original names."
        )
    
    # Check credits
    user_id = user.get("id", user.get("_id", ""))
    user_credits = user.get("credits", 0)
    
    wallet = await db.wallets.find_one({"userId": str(user_id)})
    wallet_credits = wallet.get("balanceCredits", 0) if wallet else 0
    current_credits = max(user_credits, wallet_credits)
    
    if current_credits < STORY_COST:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {STORY_COST}, Available: {current_credits}"
        )
    
    # Deduct credits
    await db.wallets.update_one(
        {"userId": str(user_id)},
        {"$inc": {"balanceCredits": -STORY_COST, "availableCredits": -STORY_COST}},
        upsert=True
    )
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -STORY_COST}}
    )
    
    # Record transaction
    await db.credit_transactions.insert_one({
        "userId": str(user_id),
        "type": "debit",
        "amount": STORY_COST,
        "reason": "Bedtime Story Builder",
        "feature": "bedtime-story-builder",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    try:
        # Generate story
        result = generate_story_script(
            age_group=data.age_group,
            theme=data.theme,
            moral=data.moral,
            length=data.length,
            voice_style=data.voice_style,
            child_name=data.child_name
        )
        
        # Get updated balance
        updated_wallet = await db.wallets.find_one({"userId": str(user_id)})
        remaining = updated_wallet.get("balanceCredits", 0) if updated_wallet else max(0, current_credits - STORY_COST)
        
        # Log generation
        await db.story_generations.insert_one({
            "userId": str(user_id),
            "age_group": data.age_group,
            "theme": data.theme,
            "moral": data.moral,
            "length": data.length,
            "voice_style": data.voice_style,
            "credits_used": STORY_COST,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "story": result,
            "credits_used": STORY_COST,
            "remaining_credits": remaining
        }
        
    except Exception as e:
        # Refund on error
        await db.wallets.update_one(
            {"userId": str(user_id)},
            {"$inc": {"balanceCredits": STORY_COST, "availableCredits": STORY_COST}}
        )
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": STORY_COST}}
        )
        logger.error(f"Story generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed. Credits refunded.")


@router.post("/export")
async def export_story(
    story_content: Dict[str, Any],
    format: str = "txt",
    user: dict = Depends(get_current_user)
):
    """Export story as text or PDF"""
    
    if format == "pdf":
        # Check credits for PDF
        user_id = user.get("id", "")
        wallet = await db.wallets.find_one({"userId": str(user_id)})
        if not wallet or wallet.get("balanceCredits", 0) < PDF_EXPORT_COST:
            raise HTTPException(status_code=402, detail=f"PDF export requires {PDF_EXPORT_COST} credits")
        
        # Deduct credits
        await db.wallets.update_one(
            {"userId": str(user_id)},
            {"$inc": {"balanceCredits": -PDF_EXPORT_COST}}
        )
    
    # Format content
    script = story_content.get("script", "")
    voice_notes = story_content.get("voice_notes", [])
    sfx_cues = story_content.get("sfx_cues", [])
    metadata = story_content.get("metadata", {})
    
    content = "=" * 50 + "\n"
    content += "BEDTIME STORY AUDIO SCRIPT\n"
    content += "=" * 50 + "\n\n"
    
    content += f"Character: {metadata.get('character', 'Unknown')}\n"
    content += f"Setting: {metadata.get('place', 'Unknown')}\n"
    content += f"Duration: {metadata.get('target_duration', '5 min')}\n\n"
    
    content += "-" * 50 + "\n"
    content += "NARRATION SCRIPT\n"
    content += "-" * 50 + "\n\n"
    content += script + "\n\n"
    
    content += "-" * 50 + "\n"
    content += "VOICE PACING NOTES\n"
    content += "-" * 50 + "\n\n"
    for note in voice_notes:
        content += f"[{note['scene']}]\n"
        content += f"Pacing: {note['pacing']}\n"
        content += f"Notes: {note['note']}\n\n"
    
    content += "-" * 50 + "\n"
    content += "SOUND EFFECT CUES\n"
    content += "-" * 50 + "\n\n"
    for cue in sfx_cues:
        content += f"[{cue['scene']}] {cue['cue']}\n"
    
    content += "\n" + "=" * 50 + "\n"
    content += "Generated by CreatorStudio AI\n"
    content += "Sweet dreams!\n"
    
    return {
        "success": True,
        "content": content,
        "filename": f"bedtime_story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/themes")
async def get_admin_themes(admin: dict = Depends(get_admin_user)):
    """Get all themes"""
    themes = await db.story_themes.find({}, {"_id": 0}).to_list(length=100)
    return {"themes": themes}


@router.post("/admin/themes")
async def create_theme(name: str, admin: dict = Depends(get_admin_user)):
    """Create a new theme"""
    import uuid
    theme = {"id": str(uuid.uuid4()), "name": name, "active": True}
    await db.story_themes.insert_one(theme)
    return {"success": True, "theme": theme}


@router.delete("/admin/themes/{theme_id}")
async def delete_theme(theme_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a theme"""
    await db.story_themes.delete_one({"id": theme_id})
    return {"success": True}


@router.get("/admin/morals")
async def get_admin_morals(admin: dict = Depends(get_admin_user)):
    """Get all morals"""
    morals = await db.story_morals.find({}, {"_id": 0}).to_list(length=100)
    return {"morals": morals}


@router.post("/admin/morals")
async def create_moral(name: str, admin: dict = Depends(get_admin_user)):
    """Create a new moral"""
    import uuid
    moral = {"id": str(uuid.uuid4()), "name": name, "active": True}
    await db.story_morals.insert_one(moral)
    return {"success": True, "moral": moral}


@router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Get usage statistics"""
    total = await db.story_generations.count_documents({})
    themes = await db.story_themes.count_documents({})
    morals = await db.story_morals.count_documents({})
    
    return {
        "total_generations": total,
        "total_themes": themes,
        "total_morals": morals,
        "pricing": {
            "story": STORY_COST,
            "pdf_export": PDF_EXPORT_COST,
            "series_pack": SERIES_PACK_COST
        }
    }
