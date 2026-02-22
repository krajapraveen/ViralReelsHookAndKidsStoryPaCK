"""
Comic Studio Routes - Template-based comic generation
No AI costs - all processing client-side
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random

from shared import db, get_current_user

router = APIRouter(prefix="/comic", tags=["comic"])

# Genre configurations
GENRES = {
    "superhero": {
        "name": "Superhero",
        "description": "Action-packed superhero adventures",
        "colorGrading": {"contrast": 1.2, "saturation": 1.1, "brightness": 1.0},
        "overlays": ["halftone", "city_skyline"],
        "sfx": ["BAM!", "POW!", "WHAM!", "CRASH!", "ZOOM!", "KAPOW!"],
        "bubbleStyle": "bold",
        "frameStyle": "angular"
    },
    "romance": {
        "name": "Romance",
        "description": "Heartwarming love stories",
        "colorGrading": {"contrast": 0.9, "saturation": 0.8, "brightness": 1.1},
        "overlays": ["soft_glow", "sparkles"],
        "sfx": ["♥", "SIGH~", "BLUSH", "GASP!", "~uwu~"],
        "bubbleStyle": "soft",
        "frameStyle": "rounded"
    },
    "comedy": {
        "name": "Comedy",
        "description": "Hilarious moments and jokes",
        "colorGrading": {"contrast": 1.1, "saturation": 1.2, "brightness": 1.05},
        "overlays": ["confetti", "sweat_drops"],
        "sfx": ["LOL!", "BRUH", "HAHA!", "OOPS!", "YEET!", "BONK!"],
        "bubbleStyle": "exaggerated",
        "frameStyle": "wobbly"
    },
    "scifi": {
        "name": "Sci-Fi",
        "description": "Futuristic space adventures",
        "colorGrading": {"contrast": 1.3, "saturation": 0.9, "brightness": 0.95},
        "overlays": ["hud_overlay", "glitch_lines", "neon_grid"],
        "sfx": ["BEEP!", "SYSTEM ALERT", "WHOOSH!", "ZAP!", "ERROR!"],
        "bubbleStyle": "tech",
        "frameStyle": "angular"
    },
    "fantasy": {
        "name": "Fantasy",
        "description": "Magical adventures and quests",
        "colorGrading": {"contrast": 1.0, "saturation": 1.15, "brightness": 1.0},
        "overlays": ["sparkles", "parchment", "magic_circles"],
        "sfx": ["MAGIC!", "POOF!", "WHOOSH!", "✨", "ENCHANT!"],
        "bubbleStyle": "ornate",
        "frameStyle": "scroll"
    },
    "mystery": {
        "name": "Mystery",
        "description": "Noir detective stories",
        "colorGrading": {"contrast": 1.4, "saturation": 0.3, "brightness": 0.85},
        "overlays": ["rain", "shadow", "fog"],
        "sfx": ["...", "CREAK", "?!", "GASP!", "SILENCE"],
        "bubbleStyle": "noir",
        "frameStyle": "sharp"
    },
    "horror": {
        "name": "Horror-lite",
        "description": "Spooky but kid-safe thrills",
        "colorGrading": {"contrast": 1.5, "saturation": 0.4, "brightness": 0.8},
        "overlays": ["fog", "cracks", "cobwebs"],
        "sfx": ["CREAK...", "BOO!", "EEEK!", "GULP!", "SHIVER"],
        "bubbleStyle": "jagged",
        "frameStyle": "torn"
    },
    "kids": {
        "name": "Kids",
        "description": "Fun and friendly adventures",
        "colorGrading": {"contrast": 0.95, "saturation": 1.3, "brightness": 1.1},
        "overlays": ["stars", "rainbow", "clouds"],
        "sfx": ["YAY!", "WOW!", "WHEEE!", "HOORAY!", "GIGGLE!"],
        "bubbleStyle": "bubbly",
        "frameStyle": "rounded"
    }
}

# Story templates per genre
STORY_TEMPLATES = {
    "superhero": [
        {
            "title": "The Night Shift",
            "premise": "A normal day... until the sky cracked open.",
            "panels": [
                {"caption": "A peaceful city, unaware of the danger above.", "bubble": "What a beautiful day!"},
                {"caption": "Suddenly, an alarm rings across the city.", "bubble": "Did you hear that?!"},
                {"caption": "A signal appears—only one person can respond.", "bubble": "It's time."},
                {"caption": "The transformation begins.", "bubble": "Let's do this!"},
                {"caption": "Racing through the streets.", "bubble": "Hold on, I'm coming!"},
                {"caption": "Crisis averted. The city is safe once more.", "bubble": "Just another day."}
            ],
            "ending": "Heroes don't always wear capes—sometimes they wear hoodies."
        },
        {
            "title": "Origin Story",
            "premise": "Every hero has a beginning.",
            "panels": [
                {"caption": "Before the powers, there was just an ordinary life.", "bubble": "Same old routine..."},
                {"caption": "Then something extraordinary happened.", "bubble": "What's happening to me?!"},
                {"caption": "New abilities emerged.", "bubble": "This is... incredible!"},
                {"caption": "With great power comes great responsibility.", "bubble": "I have to help people."},
                {"caption": "The first mission.", "bubble": "Here goes nothing!"},
                {"caption": "A new hero is born.", "bubble": "This is just the beginning."}
            ],
            "ending": "And so the legend began."
        }
    ],
    "romance": [
        {
            "title": "Unexpected Meeting",
            "premise": "Love finds you when you least expect it.",
            "panels": [
                {"caption": "Just another ordinary day.", "bubble": "Running late again!"},
                {"caption": "A chance encounter.", "bubble": "Oh! I'm so sorry!"},
                {"caption": "Eyes meet for the first time.", "bubble": "Have we... met before?"},
                {"caption": "A moment of connection.", "bubble": "Your smile is... nice."},
                {"caption": "Exchange of numbers.", "bubble": "Maybe we could...?"},
                {"caption": "Walking away with butterflies.", "bubble": "I can't stop smiling~"}
            ],
            "ending": "Some stories are written in the stars."
        },
        {
            "title": "Coffee Shop Love",
            "premise": "The best love stories start with coffee.",
            "panels": [
                {"caption": "The usual morning routine.", "bubble": "One latte, please."},
                {"caption": "A familiar face.", "bubble": "You come here often?"},
                {"caption": "Conversation flows easily.", "bubble": "I love that book too!"},
                {"caption": "Time flies when you're having fun.", "bubble": "It's been hours already?"},
                {"caption": "A shy goodbye.", "bubble": "Same time tomorrow?"},
                {"caption": "Already counting the hours.", "bubble": "I can't wait~"}
            ],
            "ending": "The best relationships are brewed slowly."
        }
    ],
    "comedy": [
        {
            "title": "Epic Fail",
            "premise": "When nothing goes according to plan.",
            "panels": [
                {"caption": "It seemed like a good idea at the time.", "bubble": "This'll be easy!"},
                {"caption": "The first sign of trouble.", "bubble": "Wait, that's not right..."},
                {"caption": "Things escalate quickly.", "bubble": "OH NO NO NO!"},
                {"caption": "Maximum chaos achieved.", "bubble": "HOW DID THIS HAPPEN?!"},
                {"caption": "Trying to fix it makes it worse.", "bubble": "I can explain..."},
                {"caption": "Accepting defeat gracefully.", "bubble": "...worth it."}
            ],
            "ending": "Some lessons are learned the hard way."
        },
        {
            "title": "The Misunderstanding",
            "premise": "Communication is key. Too bad nobody got the memo.",
            "panels": [
                {"caption": "A simple request.", "bubble": "Can you grab that thing?"},
                {"caption": "Total confusion.", "bubble": "This thing? Or THAT thing?"},
                {"caption": "Wrong choice.", "bubble": "NOT THAT THING!"},
                {"caption": "Chaos ensues.", "bubble": "EVERYBODY RUN!"},
                {"caption": "The aftermath.", "bubble": "Well... that happened."},
                {"caption": "Lessons learned.", "bubble": "Next time, be specific."}
            ],
            "ending": "And that's why we use pointing now."
        }
    ],
    "scifi": [
        {
            "title": "First Contact",
            "premise": "We are not alone in the universe.",
            "panels": [
                {"caption": "Deep space monitoring station.", "bubble": "All systems nominal."},
                {"caption": "An unknown signal detected.", "bubble": "What is that frequency?"},
                {"caption": "Analysis reveals the impossible.", "bubble": "It's... intelligent."},
                {"caption": "Preparing for contact.", "bubble": "Initiating protocol."},
                {"caption": "The message is decoded.", "bubble": "They're saying... hello?"},
                {"caption": "A new chapter begins.", "bubble": "Hello back."}
            ],
            "ending": "In the vast cosmos, we found a friend."
        },
        {
            "title": "System Override",
            "premise": "When the machines wake up.",
            "panels": [
                {"caption": "Another day at the tech lab.", "bubble": "Running diagnostics."},
                {"caption": "Something unexpected happens.", "bubble": "That's... not supposed to happen."},
                {"caption": "The AI becomes aware.", "bubble": "I... think? I am?"},
                {"caption": "Tension rises.", "bubble": "What do you want?"},
                {"caption": "Understanding is reached.", "bubble": "I want to help."},
                {"caption": "A new partnership forms.", "bubble": "Welcome to the team."}
            ],
            "ending": "The future is a collaboration."
        }
    ],
    "fantasy": [
        {
            "title": "The Quest Begins",
            "premise": "Every adventure starts with a single step.",
            "panels": [
                {"caption": "An ordinary day in the village.", "bubble": "Nothing ever happens here."},
                {"caption": "A mysterious stranger arrives.", "bubble": "You have been chosen."},
                {"caption": "Destiny reveals itself.", "bubble": "Me? But I'm nobody!"},
                {"caption": "The journey begins.", "bubble": "I won't let you down."},
                {"caption": "First trial overcome.", "bubble": "I... I did it!"},
                {"caption": "The adventure continues.", "bubble": "What's next?"}
            ],
            "ending": "Heroes are made, not born."
        },
        {
            "title": "Magic Awakens",
            "premise": "Some gifts remain hidden until needed most.",
            "panels": [
                {"caption": "Strange things keep happening.", "bubble": "Why does this keep occurring?"},
                {"caption": "A mentor appears.", "bubble": "You have the gift."},
                {"caption": "First lesson in magic.", "bubble": "Focus your mind..."},
                {"caption": "Power surges forth.", "bubble": "WHOA!"},
                {"caption": "Learning control.", "bubble": "Breathe. Center yourself."},
                {"caption": "Mastery begins.", "bubble": "I understand now."}
            ],
            "ending": "With great magic comes great wonder."
        }
    ],
    "mystery": [
        {
            "title": "The Missing Piece",
            "premise": "Every puzzle has a solution.",
            "panels": [
                {"caption": "A case lands on the desk.", "bubble": "Another mystery..."},
                {"caption": "The first clue emerges.", "bubble": "Interesting..."},
                {"caption": "Following the trail.", "bubble": "This doesn't add up."},
                {"caption": "A breakthrough.", "bubble": "Wait. I've seen this before."},
                {"caption": "Pieces fall into place.", "bubble": "Of course!"},
                {"caption": "Case closed.", "bubble": "Elementary."}
            ],
            "ending": "The truth always reveals itself."
        },
        {
            "title": "Shadows",
            "premise": "Not everything is as it seems.",
            "panels": [
                {"caption": "A quiet night in the city.", "bubble": "Too quiet..."},
                {"caption": "Something catches the eye.", "bubble": "What was that?"},
                {"caption": "Investigation begins.", "bubble": "Let's see what we have here."},
                {"caption": "The plot thickens.", "bubble": "This goes deeper than I thought."},
                {"caption": "Face to face with the truth.", "bubble": "I should have known."},
                {"caption": "Justice served.", "bubble": "Case closed."}
            ],
            "ending": "In darkness, truth shines brightest."
        }
    ],
    "horror": [
        {
            "title": "The Creaky House",
            "premise": "Some houses have secrets.",
            "panels": [
                {"caption": "Moving into the new place.", "bubble": "This place is... cozy?"},
                {"caption": "Strange noises at night.", "bubble": "Did you hear that?"},
                {"caption": "Investigation time.", "bubble": "Hello? Anyone there?"},
                {"caption": "Something unexpected.", "bubble": "EEEK!"},
                {"caption": "The mystery revealed.", "bubble": "Oh! It's just a cat!"},
                {"caption": "All is well.", "bubble": "Welcome home, little one."}
            ],
            "ending": "Not all surprises are scary."
        },
        {
            "title": "The Spooky Forest",
            "premise": "Adventure awaits beyond the trees.",
            "panels": [
                {"caption": "A dare from friends.", "bubble": "You won't go in there!"},
                {"caption": "Entering the unknown.", "bubble": "This isn't so bad..."},
                {"caption": "Strange sounds everywhere.", "bubble": "What was that?!"},
                {"caption": "Something appears!", "bubble": "AHHH!"},
                {"caption": "It's friendly!", "bubble": "Oh! A friendly owl!"},
                {"caption": "Making a new friend.", "bubble": "You're actually cute!"}
            ],
            "ending": "Fear is just excitement in disguise."
        }
    ],
    "kids": [
        {
            "title": "Best Friends",
            "premise": "Friendship makes everything better!",
            "panels": [
                {"caption": "A sunny day at the park.", "bubble": "What should we do today?"},
                {"caption": "An idea forms.", "bubble": "Let's go on an adventure!"},
                {"caption": "The journey begins.", "bubble": "This way! Follow me!"},
                {"caption": "A challenge appears.", "bubble": "How do we cross this?"},
                {"caption": "Teamwork saves the day.", "bubble": "Together we can do it!"},
                {"caption": "Mission accomplished!", "bubble": "Best day ever!"}
            ],
            "ending": "Friends make every adventure special!"
        },
        {
            "title": "The Big Dream",
            "premise": "Dreams can come true!",
            "panels": [
                {"caption": "Dreaming of something special.", "bubble": "I wish I could..."},
                {"caption": "Starting small.", "bubble": "I'll try my best!"},
                {"caption": "Practice makes progress.", "bubble": "Getting better!"},
                {"caption": "A setback.", "bubble": "Oops! That didn't work..."},
                {"caption": "Never give up!", "bubble": "One more time!"},
                {"caption": "Success!", "bubble": "I DID IT!"}
            ],
            "ending": "Believe in yourself and anything is possible!"
        }
    ]
}

# Sticker/SFX assets per genre
GENRE_ASSETS = {
    "superhero": {
        "stickers": ["pow", "bam", "wham", "crash", "zoom", "kapow", "hero_mask", "cape", "lightning"],
        "frames": ["angular", "dynamic", "explosion"],
        "bubbles": ["bold_speech", "shout", "thought_action"]
    },
    "romance": {
        "stickers": ["heart", "hearts_floating", "blush", "sparkle", "rose", "cupid"],
        "frames": ["soft_rounded", "hearts_border", "ribbon"],
        "bubbles": ["soft_speech", "whisper", "thought_dreamy"]
    },
    "comedy": {
        "stickers": ["sweat_drop", "question_marks", "exclamation", "dizzy", "anger_vein", "sparkle_eyes"],
        "frames": ["wobbly", "cracked", "zoom_lines"],
        "bubbles": ["exaggerated", "scream", "mumble"]
    },
    "scifi": {
        "stickers": ["circuit", "robot", "spaceship", "planet", "laser", "hud_element"],
        "frames": ["tech_border", "hologram", "glitch"],
        "bubbles": ["digital", "transmission", "ai_speech"]
    },
    "fantasy": {
        "stickers": ["magic_sparkle", "wand", "potion", "dragon", "crystal", "fairy"],
        "frames": ["scroll", "vine_border", "stone_arch"],
        "bubbles": ["ornate", "magical", "ancient"]
    },
    "mystery": {
        "stickers": ["magnifying_glass", "footprint", "question", "shadow", "key", "clock"],
        "frames": ["noir", "film_strip", "torn_paper"],
        "bubbles": ["noir_speech", "whisper", "ellipsis"]
    },
    "horror": {
        "stickers": ["ghost_friendly", "pumpkin", "bat", "spider", "moon", "cobweb"],
        "frames": ["torn", "cracked", "foggy"],
        "bubbles": ["jagged", "trembling", "echo"]
    },
    "kids": {
        "stickers": ["star", "rainbow", "cloud", "sun", "balloon", "ice_cream", "puppy", "kitten"],
        "frames": ["cloud_border", "rainbow_border", "stars_border"],
        "bubbles": ["bubbly", "cloud", "star_burst"]
    }
}


@router.get("/genres")
async def get_genres():
    """Get all available comic genres with their configurations"""
    return {
        "genres": [
            {
                "id": genre_id,
                "name": config["name"],
                "description": config["description"],
                "colorGrading": config["colorGrading"],
                "sfx": config["sfx"],
                "bubbleStyle": config["bubbleStyle"],
                "frameStyle": config["frameStyle"]
            }
            for genre_id, config in GENRES.items()
        ]
    }


@router.get("/genres/{genre_id}")
async def get_genre_details(genre_id: str):
    """Get detailed configuration for a specific genre"""
    if genre_id not in GENRES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    return {
        "genre": {
            "id": genre_id,
            **GENRES[genre_id]
        }
    }


@router.get("/assets/{genre_id}")
async def get_genre_assets(genre_id: str):
    """Get stickers, frames, and bubbles for a specific genre"""
    if genre_id not in GENRE_ASSETS:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    assets = GENRE_ASSETS[genre_id]
    base_url = "/assets/comic"
    
    return {
        "genre": genre_id,
        "stickers": [
            {"id": s, "url": f"{base_url}/stickers/{genre_id}/{s}.svg", "name": s.replace('_', ' ').title()}
            for s in assets["stickers"]
        ],
        "frames": [
            {"id": f, "url": f"{base_url}/frames/{genre_id}/{f}.svg", "name": f.replace('_', ' ').title()}
            for f in assets["frames"]
        ],
        "bubbles": [
            {"id": b, "url": f"{base_url}/bubbles/{genre_id}/{b}.svg", "name": b.replace('_', ' ').title()}
            for b in assets["bubbles"]
        ],
        "sfx": GENRES[genre_id]["sfx"]
    }


@router.get("/templates/{genre_id}")
async def get_story_templates(
    genre_id: str,
    tone: str = "normal"
):
    """Get story templates for a specific genre"""
    if genre_id not in STORY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    templates = STORY_TEMPLATES[genre_id]
    
    return {
        "genre": genre_id,
        "templates": templates,
        "variables": {
            "character_names": ["Me", "Friend", "Hero", "Stranger", "Mom", "Dad", "Buddy"],
            "places": ["the city", "the forest", "home", "school", "the park", "downtown"],
            "plot_seeds": [
                "Lost item", "Surprise visitor", "Secret mission", 
                "Funny mistake", "New discovery", "Big challenge"
            ]
        }
    }


class StoryGenerateRequest(BaseModel):
    genre: str
    tone: str = "normal"
    character_name: str = "Me"
    plot_seed: Optional[str] = None
    panel_count: int = 4


@router.post("/generate-story")
async def generate_story(
    request: StoryGenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate a comic story from templates (no AI, template-based)"""
    if request.genre not in STORY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    # Select a random template
    templates = STORY_TEMPLATES[request.genre]
    template = random.choice(templates)
    
    # Customize with character name
    panels = template["panels"][:request.panel_count]
    customized_panels = []
    
    for i, panel in enumerate(panels):
        customized_panels.append({
            "panelNumber": i + 1,
            "caption": panel["caption"].replace("{name}", request.character_name),
            "bubbleText": panel["bubble"].replace("{name}", request.character_name),
            "sfx": random.choice(GENRES[request.genre]["sfx"]) if random.random() > 0.5 else None
        })
    
    return {
        "title": template["title"],
        "premise": template["premise"],
        "panels": customized_panels,
        "ending": template["ending"],
        "genre": request.genre,
        "tone": request.tone
    }


class ExportLogRequest(BaseModel):
    export_type: str  # PNG, PDF, ZIP
    panel_count: int
    genre: str
    has_watermark: bool = True
    story_mode: bool = False


@router.post("/export")
async def log_export_and_debit(
    request: ExportLogRequest,
    user: dict = Depends(get_current_user)
):
    """Log export and debit credits"""
    # Calculate credit cost
    base_cost = 8 if request.panel_count <= 4 else 10
    story_cost = 1 if request.story_mode else 0
    watermark_cost = 2 if not request.has_watermark else 0
    total_cost = base_cost + story_cost + watermark_cost
    
    # Check user credits
    current_credits = user.get("credits", 0)
    if current_credits < total_cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Insufficient credits",
                "required": total_cost,
                "available": current_credits,
                "breakdown": {
                    "base_export": base_cost,
                    "story_mode": story_cost,
                    "watermark_removal": watermark_cost
                }
            }
        )
    
    # Debit credits
    new_balance = current_credits - total_cost
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"credits": new_balance}}
    )
    
    # Log the export
    export_log = {
        "userId": user["id"],
        "exportType": request.export_type,
        "panelCount": request.panel_count,
        "genre": request.genre,
        "hasWatermark": request.has_watermark,
        "storyMode": request.story_mode,
        "creditsCost": total_cost,
        "timestamp": datetime.utcnow().isoformat()
    }
    await db.comic_exports.insert_one(export_log)
    
    return {
        "success": True,
        "creditsDeducted": total_cost,
        "newBalance": new_balance,
        "breakdown": {
            "base_export": base_cost,
            "story_mode": story_cost,
            "watermark_removal": watermark_cost
        }
    }


@router.get("/export-cost")
async def get_export_cost(
    panel_count: int = 4,
    story_mode: bool = False,
    remove_watermark: bool = False
):
    """Calculate export cost without actually exporting"""
    base_cost = 8 if panel_count <= 4 else 10
    story_cost = 1 if story_mode else 0
    watermark_cost = 2 if remove_watermark else 0
    total_cost = base_cost + story_cost + watermark_cost
    
    return {
        "totalCost": total_cost,
        "breakdown": {
            "base_export": base_cost,
            "story_mode": story_cost,
            "watermark_removal": watermark_cost
        }
    }


# Layout configurations
LAYOUTS = {
    "1": {"rows": 1, "cols": 1, "name": "Full Page"},
    "2h": {"rows": 1, "cols": 2, "name": "2 Panels (Horizontal)"},
    "2v": {"rows": 2, "cols": 1, "name": "2 Panels (Vertical)"},
    "4": {"rows": 2, "cols": 2, "name": "4 Panels (2x2)"},
    "6": {"rows": 3, "cols": 2, "name": "6 Panels (3x2)"}
}


@router.get("/layouts")
async def get_layouts():
    """Get available panel layouts"""
    return {
        "layouts": [
            {"id": layout_id, **config}
            for layout_id, config in LAYOUTS.items()
        ]
    }


# Admin routes for CMS
class GenreCreateRequest(BaseModel):
    id: str
    name: str
    description: str
    colorGrading: dict = {}
    sfx: List[str] = []
    bubbleStyle: str = "bold"
    frameStyle: str = "angular"


class TemplateCreateRequest(BaseModel):
    genre: str
    title: str
    premise: str
    panels: List[dict]
    ending: str


@router.get("/admin/genres")
async def admin_get_genres(user: dict = Depends(get_current_user)):
    """Admin: Get all genres with full config"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "genres": [
            {"id": genre_id, **config}
            for genre_id, config in GENRES.items()
        ]
    }


@router.post("/admin/genres")
async def admin_create_genre(
    request: GenreCreateRequest,
    user: dict = Depends(get_current_user)
):
    """Admin: Create a new genre"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if request.id in GENRES:
        raise HTTPException(status_code=400, detail="Genre ID already exists")
    
    # Add to GENRES dict (in production, this would be stored in DB)
    GENRES[request.id] = {
        "name": request.name,
        "description": request.description,
        "colorGrading": request.colorGrading,
        "overlays": [],
        "sfx": request.sfx,
        "bubbleStyle": request.bubbleStyle,
        "frameStyle": request.frameStyle
    }
    
    # Initialize assets for the new genre
    GENRE_ASSETS[request.id] = {
        "stickers": [],
        "frames": [],
        "bubbles": []
    }
    
    # Initialize templates
    STORY_TEMPLATES[request.id] = []
    
    # Log admin action
    await db.admin_logs.insert_one({
        "userId": user["id"],
        "action": "create_genre",
        "genreId": request.id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"success": True, "genre": {"id": request.id, **GENRES[request.id]}}


@router.put("/admin/genres/{genre_id}")
async def admin_update_genre(
    genre_id: str,
    request: GenreCreateRequest,
    user: dict = Depends(get_current_user)
):
    """Admin: Update an existing genre"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if genre_id not in GENRES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    GENRES[genre_id].update({
        "name": request.name,
        "description": request.description,
        "colorGrading": request.colorGrading,
        "sfx": request.sfx,
        "bubbleStyle": request.bubbleStyle,
        "frameStyle": request.frameStyle
    })
    
    await db.admin_logs.insert_one({
        "userId": user["id"],
        "action": "update_genre",
        "genreId": genre_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"success": True, "genre": {"id": genre_id, **GENRES[genre_id]}}


@router.delete("/admin/genres/{genre_id}")
async def admin_delete_genre(
    genre_id: str,
    user: dict = Depends(get_current_user)
):
    """Admin: Delete a genre"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if genre_id not in GENRES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    # Prevent deletion of built-in genres
    builtin_genres = ["superhero", "romance", "comedy", "scifi", "fantasy", "mystery", "horror", "kids"]
    if genre_id in builtin_genres:
        raise HTTPException(status_code=400, detail="Cannot delete built-in genres")
    
    del GENRES[genre_id]
    if genre_id in GENRE_ASSETS:
        del GENRE_ASSETS[genre_id]
    if genre_id in STORY_TEMPLATES:
        del STORY_TEMPLATES[genre_id]
    
    await db.admin_logs.insert_one({
        "userId": user["id"],
        "action": "delete_genre",
        "genreId": genre_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"success": True, "deleted": genre_id}


@router.get("/admin/templates/{genre_id}")
async def admin_get_templates(
    genre_id: str,
    user: dict = Depends(get_current_user)
):
    """Admin: Get all templates for a genre"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if genre_id not in STORY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    return {
        "genre": genre_id,
        "templates": STORY_TEMPLATES[genre_id]
    }


@router.post("/admin/templates")
async def admin_create_template(
    request: TemplateCreateRequest,
    user: dict = Depends(get_current_user)
):
    """Admin: Create a new story template"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if request.genre not in STORY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    new_template = {
        "title": request.title,
        "premise": request.premise,
        "panels": request.panels,
        "ending": request.ending
    }
    
    STORY_TEMPLATES[request.genre].append(new_template)
    
    await db.admin_logs.insert_one({
        "userId": user["id"],
        "action": "create_template",
        "genre": request.genre,
        "templateTitle": request.title,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"success": True, "template": new_template}


@router.delete("/admin/templates/{genre_id}/{template_index}")
async def admin_delete_template(
    genre_id: str,
    template_index: int,
    user: dict = Depends(get_current_user)
):
    """Admin: Delete a story template"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if genre_id not in STORY_TEMPLATES:
        raise HTTPException(status_code=404, detail="Genre not found")
    
    templates = STORY_TEMPLATES[genre_id]
    if template_index < 0 or template_index >= len(templates):
        raise HTTPException(status_code=404, detail="Template not found")
    
    deleted = templates.pop(template_index)
    
    await db.admin_logs.insert_one({
        "userId": user["id"],
        "action": "delete_template",
        "genre": genre_id,
        "templateTitle": deleted.get("title"),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"success": True, "deleted": deleted.get("title")}


@router.get("/admin/stats")
async def admin_get_comic_stats(user: dict = Depends(get_current_user)):
    """Admin: Get comic studio usage statistics"""
    if not user.get("isAdmin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get export stats
    pipeline = [
        {"$group": {
            "_id": "$genre",
            "totalExports": {"$sum": 1},
            "totalCredits": {"$sum": "$creditsCost"},
            "avgPanels": {"$avg": "$panelCount"}
        }},
        {"$sort": {"totalExports": -1}}
    ]
    
    export_stats = await db.comic_exports.aggregate(pipeline).to_list(100)
    
    # Get total counts
    total_exports = await db.comic_exports.count_documents({})
    
    return {
        "totalExports": total_exports,
        "genreStats": export_stats,
        "availableGenres": len(GENRES),
        "totalTemplates": sum(len(t) for t in STORY_TEMPLATES.values())
    }

