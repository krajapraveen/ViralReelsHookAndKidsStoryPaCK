"""
Story Hook Generator for Fiction Writers
Template-based, no AI, <200ms response
Price: 8 credits
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import time
from datetime import datetime, timezone
from bson import ObjectId

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/story-hook-generator", tags=["Story Hook Generator"])

# ==================== COPYRIGHT PROTECTION ====================
BLOCKED_KEYWORDS = [
    "marvel", "disney", "pixar", "harry potter", "pokemon", "naruto", "spiderman", 
    "batman", "superman", "avengers", "frozen", "mickey", "star wars", "lord of the rings",
    "game of thrones", "stranger things", "hobbit", "gandalf", "frodo", "voldemort",
    "hogwarts", "darth vader", "luke skywalker", "iron man", "captain america", "thor",
    "hulk", "black widow", "thanos", "joker", "gotham", "sherlock", "james bond",
    "twilight", "hunger games", "katniss", "divergent", "maze runner"
]

def check_copyright(text: str) -> bool:
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# ==================== TEMPLATES ====================
GENRES = ["Fantasy", "Romance", "Thriller", "Sci-Fi", "Mystery", "Horror", "Historical", "Adventure"]
TONES = ["dark", "emotional", "suspenseful", "whimsical", "intense"]
CHARACTER_TYPES = ["hero", "anti-hero", "villain", "reluctant_hero", "ordinary_person", "outsider"]
SETTINGS = ["urban", "rural", "fantasy_realm", "space", "historical", "post_apocalyptic", "underwater", "underground"]

# Hook templates by genre
HOOK_TEMPLATES = {
    "Fantasy": [
        "The {character} had always known about the prophecy. They just never believed they'd be the one to break it.",
        "When {character} discovered the ancient {setting} beneath the city, they found something that should have stayed buried.",
        "The last dragon was dying, and only {character} knew the price of saving it.",
        "Magic had been forbidden for centuries. But {character} was born with it flowing through their veins.",
        "The {character} made a deal with a creature from the {setting}. The cost? Their own reflection.",
        "Three kingdoms. One throne. And {character} held the secret that could destroy them all.",
        "The map led to a {setting} that didn't exist on any other. {character} was about to find out why.",
        "When the moon turned red, {character} felt the change begin. There was no going back.",
        "{character} was chosen by the sword. The problem was, the sword chose someone new every sunrise.",
        "The ancient library held every story ever written. Except one. The one {character} needed to survive.",
    ],
    "Romance": [
        "{character} swore they'd never fall in love. Then they met someone who made them want to break every promise.",
        "It started with a wrong number. It ended with {character} questioning everything they thought they wanted.",
        "They were supposed to hate each other. The {setting} had other plans.",
        "{character} had 30 days to fall out of love. The problem? Every day, they fell deeper.",
        "The letter was 10 years late. But {character}'s heart still recognized the handwriting.",
        "In a {setting} full of strangers, {character} found the one person who felt like home.",
        "They agreed: no feelings, no complications. They were both terrible at keeping promises.",
        "{character} came to the {setting} to forget. Instead, they found someone unforgettable.",
        "The wedding was perfect. Until {character} realized they were marrying the wrong person.",
        "Second chances weren't supposed to hurt this much. {character} wasn't prepared for what came back.",
    ],
    "Thriller": [
        "{character} received a photo of themselves sleeping. It was timestamped three minutes ago.",
        "The {setting} was empty when {character} entered. But someone had already written their name on the wall.",
        "Everyone in the {setting} received the same message: '{character} knows what you did.'",
        "The last thing {character} remembered was falling asleep at home. They woke up in a {setting} they'd never seen.",
        "{character} had 12 hours to find the truth. After that, they'd become the next victim.",
        "The stranger knew {character}'s name, their address, and the secret they'd buried 10 years ago.",
        "Someone was watching. {character} found the camera hidden in their {setting}. It had been there for months.",
        "The detective said the case was closed. {character} had proof it was just beginning.",
        "Every night at 3 AM, {character} received a call. The voice on the other end was their own.",
        "The witness was lying. {character} knew because they were there that night too.",
    ],
    "Sci-Fi": [
        "The {character} was the only one who remembered Earth. Everyone else had their memories erased.",
        "Time travel was supposed to be impossible. {character} had just done it by accident.",
        "The AI wasn't supposed to have feelings. But it fell in love with {character} anyway.",
        "Humanity's first contact with aliens went perfectly. Until {character} discovered what they really wanted.",
        "In the {setting}, oxygen was currency. {character} was running out of both money and breath.",
        "The simulation was flawless. {character} was the only glitch in the system.",
        "{character} signed up for immortality. They didn't read the fine print about watching everyone die.",
        "The colony ship had been traveling for 200 years. {character} was the first to wake up and discover the lie.",
        "Every human had a digital twin. {character}'s had just murdered someone.",
        "The cure worked. But the side effects turned {character} into something no longer human.",
    ],
    "Mystery": [
        "The victim left one clue before dying: {character}'s name written in blood.",
        "Everyone in the {setting} had a motive. {character} had to find the one person with the opportunity.",
        "The case had been cold for 20 years. {character} just found fresh evidence in their own basement.",
        "The perfect crime had one witness: {character}. But they couldn't remember a thing.",
        "Three suspects. Three alibis. {character} knew two of them were lying.",
        "The murder weapon was impossible. It hadn't been invented yet when the victim died.",
        "{character} solved the case. But the real killer was someone they could never arrest.",
        "The missing person was found. The problem? They didn't want to be saved.",
        "Every clue pointed to {character}. But they knew they were being framed.",
        "The secret room in the {setting} held the truth. {character} wished they'd never opened that door.",
    ],
    "Horror": [
        "{character} realized the scratching wasn't coming from outside the {setting}. It was coming from inside the walls.",
        "The mirror reflected everything perfectly. Except {character} wasn't standing alone in it.",
        "The {setting} was abandoned for a reason. {character} was about to find out why.",
        "Children weren't supposed to have imaginary friends like that. {character}'s therapist should have listened.",
        "The dead don't stay dead in the {setting}. {character} learned this the hard way.",
        "{character} stopped believing in monsters when they were eight. At thirty, they became one.",
        "The voice in {character}'s head wasn't their own. And it was getting louder.",
        "Every night, {character} died in their dreams. Every morning, they woke with a new scar.",
        "The old photographs showed something standing behind {character}. Something that was still there.",
        "The {setting} had been built on sacred ground. The ground wanted it back.",
    ],
    "Historical": [
        "The secret {character} carried could rewrite history. If they lived long enough to tell it.",
        "In a {setting} where speaking the truth meant death, {character} chose to whisper it anyway.",
        "The revolution needed a hero. {character} was just trying to survive.",
        "History remembered them as a villain. {character} knew the real story.",
        "The letter changed everything. {character} had been living a lie their entire life.",
        "In the {setting}, war was coming. {character} was the only one who saw it.",
        "They called it progress. {character} called it the death of everything they loved.",
        "The crown wasn't supposed to fall to {character}. But everyone ahead of them was dead.",
        "In a {setting} divided by class, {character} was the bridge. And bridges get burned.",
        "The artifact had been hidden for centuries. {character} just dug it up.",
    ],
    "Adventure": [
        "The map was a fake. But the treasure {character} found was very, very real.",
        "{character} had three days to cross the {setting}. The journey was supposed to take three weeks.",
        "The expedition went silent six months ago. {character} was sent to find out why.",
        "Every explorer who entered the {setting} came back changed. {character} was about to discover how.",
        "The reward was enough to change {character}'s life. The risk was losing it entirely.",
        "{character} made a promise to return. They didn't know the {setting} would try to keep them.",
        "The race had begun. {character} was already three days behind.",
        "No one had ever reached the heart of the {setting}. {character} was determined to be the first.",
        "The journey was supposed to be simple. Then {character} found the body.",
        "Adventure called. {character} answered. They should have let it go to voicemail.",
    ]
}

# Cliffhanger templates
CLIFFHANGER_TEMPLATES = [
    "And then {character} realized the door behind them had never been there at all.",
    "'I should have told you sooner,' they whispered. 'We're not alone in here.'",
    "The ground beneath {character} began to crack. There was nowhere to run.",
    "As the lights flickered out, {character} heard breathing that wasn't their own.",
    "'You don't understand,' they said. 'That wasn't the test. This is.'",
    "The truth hit {character} like a wave. They had been the enemy all along.",
    "'Look up,' someone whispered. {character} wished they hadn't.",
    "The message was clear: {character} had until midnight. The clock struck eleven.",
    "When {character} turned around, they were standing face to face with themselves.",
    "'Run,' was all they managed to say before the world went dark.",
]

# Plot twist templates
TWIST_TEMPLATES = [
    "The mentor {character} trusted had been orchestrating everything from the beginning.",
    "The villain wasn't evil. They were trying to prevent something far worse.",
    "The entire {setting} was a prison. {character} was both prisoner and warden.",
    "The prophecy was real. But {character} wasn't the hero—they were the sacrifice.",
    "Everything {character} remembered was a lie. Their real memories had been stolen.",
    "The 'rescue' was actually an abduction. {character} had just become the hostage.",
    "The cure and the poison were the same thing. {character} had to choose who lived.",
    "The ally who saved {character}'s life was also the one who put them in danger.",
    "The mystery wasn't about finding the truth. It was about deciding which lie to believe.",
    "The war was over. {character} had won. But victory looked exactly like defeat.",
]

# ==================== MODELS ====================
class GenerateRequest(BaseModel):
    genre: str = Field(..., description="Story genre")
    tone: str = Field(default="suspenseful")
    character_type: str = Field(default="hero")
    setting: str = Field(default="urban")

class GenerateResponse(BaseModel):
    success: bool
    hooks: List[str]
    cliffhangers: List[str]
    plot_twists: List[str]
    credits_used: int
    generation_time_ms: int

# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    return {
        "genres": GENRES,
        "tones": TONES,
        "character_types": CHARACTER_TYPES,
        "settings": SETTINGS,
        "credit_cost": 8,
        "hooks_count": 10,
        "cliffhangers_count": 5,
        "twists_count": 3
    }

@router.post("/generate", response_model=GenerateResponse)
async def generate_hooks(request: GenerateRequest, user: dict = Depends(get_current_user)):
    start_time = time.time()
    
    # Copyright check on inputs
    all_text = f"{request.genre} {request.character_type} {request.setting}"
    if check_copyright(all_text):
        raise HTTPException(status_code=400, detail="Input contains blocked content. Please avoid copyrighted or trademarked terms.")
    
    # Check credits
    if user.get("credits", 0) < 8:
        raise HTTPException(status_code=402, detail="Insufficient credits. 8 credits required.")
    
    # Deduct credits BEFORE generation
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -8}}
    )
    
    try:
        genre = request.genre if request.genre in GENRES else "Fantasy"
        
        # Character naming based on type
        character_names = {
            "hero": "the chosen one",
            "anti-hero": "the outcast",
            "villain": "the dark one",
            "reluctant_hero": "the reluctant savior",
            "ordinary_person": "the ordinary soul",
            "outsider": "the stranger"
        }
        character = character_names.get(request.character_type, "the hero")
        
        # Setting descriptions
        setting_names = {
            "urban": "city",
            "rural": "village",
            "fantasy_realm": "enchanted realm",
            "space": "void of space",
            "historical": "ancient halls",
            "post_apocalyptic": "wasteland",
            "underwater": "depths",
            "underground": "caverns"
        }
        setting = setting_names.get(request.setting, "world")
        
        # Get genre-specific hooks
        genre_hooks = HOOK_TEMPLATES.get(genre, HOOK_TEMPLATES["Fantasy"])
        selected_hooks = random.sample(genre_hooks, min(10, len(genre_hooks)))
        
        # Format hooks
        hooks = []
        for hook in selected_hooks:
            formatted = hook.format(character=character, setting=setting)
            hooks.append(formatted)
        
        # Generate cliffhangers
        selected_cliffhangers = random.sample(CLIFFHANGER_TEMPLATES, 5)
        cliffhangers = [c.format(character=character, setting=setting) for c in selected_cliffhangers]
        
        # Generate plot twists
        selected_twists = random.sample(TWIST_TEMPLATES, 3)
        plot_twists = [t.format(character=character, setting=setting) for t in selected_twists]
        
        # Track analytics
        await db.template_analytics.insert_one({
            "feature": "story_hook_generator",
            "user_id": str(user["id"]),
            "genre": genre,
            "tone": request.tone,
            "created_at": datetime.now(timezone.utc)
        })
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return GenerateResponse(
            success=True,
            hooks=hooks,
            cliffhangers=cliffhangers,
            plot_twists=plot_twists,
            credits_used=8,
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        # Refund on error
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": 8}}
        )
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/hooks")
async def get_hooks(admin: dict = Depends(get_admin_user)):
    hooks = await db.fiction_hooks.find({}).to_list(200)
    for h in hooks:
        h["id"] = str(h.pop("_id"))
    return {"hooks": hooks}

@router.post("/admin/hooks")
async def create_hook(data: dict, admin: dict = Depends(get_admin_user)):
    hook = {
        "genre": data.get("genre", "Fantasy"),
        "template": data.get("template"),
        "type": data.get("type", "hook"),
        "active": True,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.fiction_hooks.insert_one(hook)
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/admin/hooks/{hook_id}")
async def delete_hook(hook_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.fiction_hooks.delete_one({"_id": ObjectId(hook_id)})
    return {"success": result.deleted_count > 0}
