"""
Story Series Module - Kids Story Series Mode
Creates episode series from stories with consistency rules
Route: /app/story-series
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, log_exception
from security import limiter

router = APIRouter(prefix="/story-series", tags=["Story Series"])

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================
SERIES_PRICING = {
    "3_EPISODES": 8,
    "5_EPISODES": 12,
    "7_EPISODES": 18,
    "CHARACTER_BIBLE": 5,
}

# =============================================================================
# TEMPLATE-BASED GENERATION (No paid AI)
# =============================================================================

# Episode structure templates
EPISODE_TEMPLATES = {
    "Adventure": {
        "arc_structure": ["Discovery", "Challenge", "Growth", "Triumph", "Reflection"],
        "hooks": [
            "But little did {character} know, a bigger adventure awaited...",
            "As the sun set, {character} noticed something strange...",
            "The next morning brought an unexpected visitor...",
            "A mysterious message arrived from far away...",
            "Something was different about the {location} today..."
        ],
        "cliffhangers": [
            "And just then, {character} heard a sound that changed everything...",
            "But before they could celebrate, a shadow appeared...",
            "The {item} began to glow with an unusual light...",
            "A new friend—or was it a foe?—stepped into view...",
            "The ground beneath them started to shake..."
        ]
    },
    "Friendship": {
        "arc_structure": ["Meeting", "Bonding", "Conflict", "Resolution", "Celebration"],
        "hooks": [
            "{character} wondered if their new friend felt the same way...",
            "Tomorrow would bring a chance to prove their friendship...",
            "But would {character}'s friend understand?",
            "The test of true friendship was about to begin...",
            "A special surprise was waiting just around the corner..."
        ],
        "cliffhangers": [
            "And that's when {character} realized they weren't alone...",
            "A misunderstanding threatened to tear them apart...",
            "But their friend was nowhere to be found...",
            "The words hung in the air between them...",
            "Would their friendship survive this challenge?"
        ]
    },
    "Mystery": {
        "arc_structure": ["Discovery", "Investigation", "Clue", "Revelation", "Solution"],
        "hooks": [
            "The mystery deepened as {character} found another clue...",
            "Someone knew more than they were telling...",
            "The answer was closer than {character} thought...",
            "A hidden message revealed a shocking truth...",
            "The final piece of the puzzle was almost within reach..."
        ],
        "cliffhangers": [
            "But the biggest mystery was yet to be solved...",
            "A new clue changed everything they thought they knew...",
            "Someone had been watching {character} all along...",
            "The {item} held a secret no one expected...",
            "And then the lights went out..."
        ]
    },
    "Fantasy": {
        "arc_structure": ["Portal", "Wonder", "Quest", "Magic", "Return"],
        "hooks": [
            "The magical world revealed another wonder...",
            "{character}'s magical abilities were growing stronger...",
            "A prophecy spoke of a hero who would save them all...",
            "The ancient magic stirred once more...",
            "Beyond the enchanted forest, destiny awaited..."
        ],
        "cliffhangers": [
            "But the magic came with a price...",
            "A dark force was awakening in the enchanted realm...",
            "The spell had unexpected consequences...",
            "{character}'s true power was finally revealed...",
            "The portal between worlds was closing..."
        ]
    },
    "Comedy": {
        "arc_structure": ["Setup", "Mishap", "Chaos", "Realization", "Laughter"],
        "hooks": [
            "And you won't believe what happened next...",
            "{character} had one more trick up their sleeve...",
            "But the funniest part was yet to come...",
            "Everyone thought the chaos was over. They were wrong...",
            "A simple plan was about to go wonderfully wrong..."
        ],
        "cliffhangers": [
            "And that's when everything got even sillier...",
            "The hiccups just wouldn't stop...",
            "Oh no, not again!",
            "{character} realized they'd made a tiny mistake...",
            "Things were about to get delightfully chaotic..."
        ]
    }
}

# Scene beat templates
SCENE_BEAT_TEMPLATES = {
    "opening": [
        "{character} wakes up to find {discovery}",
        "The day begins with {event} in {location}",
        "A letter arrives with news about {plot_point}",
        "{character} is preparing for {activity} when {interruption} happens"
    ],
    "rising_action": [
        "{character} discovers {secret} hidden in {location}",
        "An obstacle appears: {challenge}",
        "{character} meets {new_character} who reveals {information}",
        "The journey to {destination} is harder than expected"
    ],
    "climax": [
        "{character} faces their biggest fear: {fear}",
        "The moment of truth arrives at {location}",
        "Everything depends on {character}'s next decision",
        "{character} must choose between {choice_a} and {choice_b}"
    ],
    "falling_action": [
        "The solution comes from an unexpected source",
        "{character} realizes the true meaning of {theme}",
        "Friends come together to help {character}",
        "The {item} reveals its true purpose"
    ],
    "resolution": [
        "{character} returns home changed by the adventure",
        "A celebration honors {character}'s bravery",
        "The lesson learned will never be forgotten",
        "And so, {location} was peaceful once more"
    ]
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SeriesRequest(BaseModel):
    storyId: Optional[str] = None
    storySummary: Optional[str] = Field(default=None, max_length=1000)
    characterNames: List[str] = Field(default_factory=list, max_items=5)
    targetAgeGroup: str = Field(default="4-7")
    theme: str = Field(default="Adventure")
    episodeCount: int = Field(default=5, ge=3, le=7)


class CharacterBibleRequest(BaseModel):
    seriesId: str
    characterNames: List[str]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_episode_outline(
    episode_num: int,
    total_episodes: int,
    theme: str,
    characters: List[str],
    base_story: dict
) -> dict:
    """Generate episode outline using templates (no AI cost)"""
    import random
    
    template = EPISODE_TEMPLATES.get(theme, EPISODE_TEMPLATES["Adventure"])
    arc_position = min(episode_num - 1, len(template["arc_structure"]) - 1)
    arc_stage = template["arc_structure"][arc_position]
    
    # Generate episode title
    title_templates = [
        f"Episode {episode_num}: The {arc_stage} Begins",
        f"Episode {episode_num}: {characters[0] if characters else 'Hero'}'s {arc_stage}",
        f"Episode {episode_num}: A {arc_stage} to Remember",
        f"Episode {episode_num}: The Great {arc_stage}"
    ]
    title = random.choice(title_templates)
    
    # Generate scene beats
    main_char = characters[0] if characters else "the hero"
    location = base_story.get("setting", "the magical land")
    
    beat_count = random.randint(5, 8)
    scene_beats = []
    
    beat_types = ["opening", "rising_action", "rising_action", "climax", "falling_action", "resolution"]
    for i in range(beat_count):
        beat_type = beat_types[min(i, len(beat_types) - 1)]
        beat_templates = SCENE_BEAT_TEMPLATES.get(beat_type, SCENE_BEAT_TEMPLATES["rising_action"])
        beat = random.choice(beat_templates)
        
        # Fill in placeholders
        beat = beat.replace("{character}", main_char)
        beat = beat.replace("{location}", location)
        beat = beat.replace("{discovery}", "something unexpected")
        beat = beat.replace("{event}", "an exciting event")
        beat = beat.replace("{plot_point}", "the quest")
        beat = beat.replace("{activity}", "their adventure")
        beat = beat.replace("{interruption}", "something mysterious")
        beat = beat.replace("{secret}", "a hidden truth")
        beat = beat.replace("{new_character}", "a mysterious stranger")
        beat = beat.replace("{information}", "important news")
        beat = beat.replace("{destination}", "their goal")
        beat = beat.replace("{challenge}", "a difficult obstacle")
        beat = beat.replace("{fear}", "their greatest challenge")
        beat = beat.replace("{choice_a}", "one path")
        beat = beat.replace("{choice_b}", "another path")
        beat = beat.replace("{theme}", theme.lower())
        beat = beat.replace("{item}", "the magical object")
        
        scene_beats.append(beat)
    
    # Generate hook and cliffhanger
    hook = random.choice(template["hooks"]).replace("{character}", main_char).replace("{location}", location).replace("{item}", "artifact")
    cliffhanger = random.choice(template["cliffhangers"]).replace("{character}", main_char).replace("{item}", "treasure")
    
    return {
        "episodeNumber": episode_num,
        "title": title,
        "arcStage": arc_stage,
        "sceneBeats": scene_beats,
        "cliffhanger": cliffhanger if episode_num < total_episodes else "And they lived happily ever after!",
        "nextEpisodeHook": hook if episode_num < total_episodes else None
    }


def generate_character_bible(characters: List[str], theme: str) -> List[dict]:
    """Generate character traits and catchphrases (template-based)"""
    import random
    
    trait_options = {
        "positive": ["brave", "kind", "curious", "clever", "loyal", "funny", "creative", "patient"],
        "quirk": ["always hums when thinking", "collects shiny objects", "talks to animals", 
                  "loves telling stories", "never gives up", "sees the good in everyone"],
        "fear": ["the dark", "being alone", "letting friends down", "loud noises", "new places"],
        "strength": ["problem-solving", "making friends", "staying calm", "cheering others up"]
    }
    
    catchphrase_templates = [
        "Let's go on an adventure!",
        "Friends stick together!",
        "I've got an idea!",
        "Never give up!",
        "We can do this together!",
        "Time for some fun!",
        "That's what friends are for!",
        "Believe in yourself!"
    ]
    
    bible = []
    for char in characters:
        bible.append({
            "name": char,
            "traits": random.sample(trait_options["positive"], 3),
            "quirk": random.choice(trait_options["quirk"]),
            "fear": random.choice(trait_options["fear"]),
            "strength": random.choice(trait_options["strength"]),
            "catchphrase": random.choice(catchphrase_templates),
            "role": "Main Character" if bible == [] else "Supporting Character"
        })
    
    return bible


async def deduct_credits(user_id: str, amount: int, ref_type: str, ref_id: str) -> bool:
    """Atomically deduct credits"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or user.get("credits", 0) < amount:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {amount}")
    
    result = await db.users.update_one(
        {"id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=402, detail="Failed to deduct credits")
    
    # Log to ledger
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
    
    return True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_series_pricing():
    """Get pricing for story series features"""
    return {
        "pricing": SERIES_PRICING,
        "episodeBundles": [
            {"episodes": 3, "credits": SERIES_PRICING["3_EPISODES"]},
            {"episodes": 5, "credits": SERIES_PRICING["5_EPISODES"]},
            {"episodes": 7, "credits": SERIES_PRICING["7_EPISODES"]}
        ],
        "addOns": [
            {"name": "Character Bible", "credits": SERIES_PRICING["CHARACTER_BIBLE"]}
        ]
    }


@router.get("/themes")
async def get_available_themes():
    """Get available story themes"""
    return {
        "themes": list(EPISODE_TEMPLATES.keys()),
        "descriptions": {
            "Adventure": "Exciting journeys and discoveries",
            "Friendship": "Stories about bonds and togetherness",
            "Mystery": "Puzzles and secrets to uncover",
            "Fantasy": "Magical worlds and enchantments",
            "Comedy": "Fun and laughter-filled tales"
        }
    }


@router.get("/user-stories")
async def get_user_stories_for_series(user: dict = Depends(get_current_user)):
    """Get user's stories that can be expanded into series"""
    user_id = user["id"]
    
    stories = await db.generations.find(
        {"userId": user_id, "type": "story"},
        {"_id": 0}
    ).sort("createdAt", -1).limit(20).to_list(20)
    
    formatted = []
    for s in stories:
        result = s.get("result", {})
        formatted.append({
            "id": s.get("id"),
            "title": result.get("title", "Untitled"),
            "synopsis": result.get("synopsis", "")[:200],
            "characters": result.get("characters", []),
            "theme": result.get("genre", "Adventure"),
            "createdAt": s.get("createdAt")
        })
    
    return {"stories": formatted}


@router.post("/generate")
@limiter.limit("5/minute")
async def generate_series(
    request: Request,
    data: SeriesRequest,
    user: dict = Depends(get_current_user)
):
    """Generate episode series from story"""
    user_id = user["id"]
    
    # Determine pricing
    pricing_key = f"{data.episodeCount}_EPISODES"
    cost = SERIES_PRICING.get(pricing_key, SERIES_PRICING["5_EPISODES"])
    
    # Generate series ID
    series_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, cost, "STORY_SERIES", series_id)
    
    # Get base story if storyId provided
    base_story = {}
    if data.storyId:
        story_doc = await db.generations.find_one(
            {"id": data.storyId, "userId": user_id},
            {"_id": 0}
        )
        if story_doc:
            base_story = story_doc.get("result", {})
    
    # Generate episodes using templates
    episodes = []
    for i in range(1, data.episodeCount + 1):
        episode = generate_episode_outline(
            episode_num=i,
            total_episodes=data.episodeCount,
            theme=data.theme,
            characters=data.characterNames or base_story.get("characters", ["Hero"]),
            base_story=base_story
        )
        episodes.append(episode)
    
    # Store series
    series_doc = {
        "id": series_id,
        "userId": user_id,
        "baseStoryId": data.storyId,
        "storySummary": data.storySummary or base_story.get("synopsis", ""),
        "characterNames": data.characterNames or base_story.get("characters", []),
        "targetAgeGroup": data.targetAgeGroup,
        "theme": data.theme,
        "episodeCount": data.episodeCount,
        "episodes": episodes,
        "creditsUsed": cost,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.story_series.insert_one(series_doc)
    
    return {
        "success": True,
        "seriesId": series_id,
        "episodeCount": data.episodeCount,
        "creditsUsed": cost,
        "episodes": episodes,
        "disclaimer": "Generated content is template-based and should be reviewed before use."
    }


@router.post("/character-bible")
async def generate_character_bible_endpoint(
    data: CharacterBibleRequest,
    user: dict = Depends(get_current_user)
):
    """Generate character bible for series"""
    user_id = user["id"]
    cost = SERIES_PRICING["CHARACTER_BIBLE"]
    
    # Verify series belongs to user
    series = await db.story_series.find_one(
        {"id": data.seriesId, "userId": user_id},
        {"_id": 0}
    )
    
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    # Deduct credits
    bible_id = str(uuid.uuid4())
    await deduct_credits(user_id, cost, "CHARACTER_BIBLE", bible_id)
    
    # Generate bible
    characters = data.characterNames or series.get("characterNames", ["Hero"])
    theme = series.get("theme", "Adventure")
    bible = generate_character_bible(characters, theme)
    
    # Update series with bible
    await db.story_series.update_one(
        {"id": data.seriesId},
        {"$set": {"characterBible": bible, "bibleGeneratedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "success": True,
        "seriesId": data.seriesId,
        "characterBible": bible,
        "creditsUsed": cost
    }


@router.get("/series/{series_id}")
async def get_series(series_id: str, user: dict = Depends(get_current_user)):
    """Get series details"""
    series = await db.story_series.find_one(
        {"id": series_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    return series


@router.get("/history")
async def get_series_history(
    user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's series generation history"""
    user_id = user["id"]
    
    series_list = await db.story_series.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.story_series.count_documents({"userId": user_id})
    
    return {
        "series": series_list,
        "total": total
    }
