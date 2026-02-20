"""
Tone Switcher Module - AI-Free Emotional Tone Rewriter
Template-based text transformation without LLM costs
Route: /app/tone-switcher
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import random
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/tone-switcher", tags=["Tone Switcher"])

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================
TONE_PRICING = {
    "SINGLE_REWRITE": 1,
    "BATCH_5": 3,  # 5 variations for price of 3
    "BATCH_10": 5,  # 10 variations for price of 5
}

# =============================================================================
# TONE TRANSFORMATION DATA (Original - No AI Cost)
# =============================================================================

TONE_CONFIGS = {
    "funny": {
        "name": "Funny",
        "description": "Add humor and lighthearted vibes",
        "emoji_set": ["😂", "🤣", "😆", "😜", "🎉", "✨", "💯", "🔥"],
        "intensifiers": ["literally", "seriously", "honestly", "like,", "you guys,"],
        "exclamation_ratio": 0.4,  # 40% of sentences end with !
        "transformations": {
            "good": ["amazing", "incredible", "chef's kiss"],
            "bad": ["a total disaster", "chaos mode", "yikes-worthy"],
            "important": ["super duper important", "mega crucial", "do-not-miss"],
            "easy": ["piece of cake", "child's play", "too easy"],
            "hard": ["brain-melting", "next level challenge", "big brain time"],
            "start": ["let's gooo", "buckle up", "here we go"],
            "end": ["mic drop", "and that's the tea", "you're welcome"]
        },
        "sentence_starters": [
            "Plot twist:",
            "Hot take:",
            "Not gonna lie,",
            "Here's the thing -",
            "Spoiler alert:"
        ],
        "sentence_enders": [
            "...just saying!",
            "- you'll thank me later!",
            "(trust me on this one)",
            "...and I mean it!",
            "- works every time!"
        ]
    },
    "aggressive": {
        "name": "Aggressive/Bold",
        "description": "Confident, direct, no-nonsense tone",
        "emoji_set": ["💪", "🔥", "⚡", "🎯", "💥", "🚀"],
        "intensifiers": ["absolutely", "definitely", "without question", "100%"],
        "exclamation_ratio": 0.6,
        "transformations": {
            "good": ["powerful", "dominant", "unstoppable"],
            "bad": ["unacceptable", "weak", "failing"],
            "important": ["critical", "non-negotiable", "essential"],
            "should": ["MUST", "need to", "have to"],
            "could": ["WILL", "are going to", "better"],
            "maybe": ["definitely", "absolutely", "without doubt"],
            "try": ["commit", "execute", "dominate"]
        },
        "sentence_starters": [
            "Listen up:",
            "Here's the truth:",
            "No excuses -",
            "Wake up call:",
            "Reality check:"
        ],
        "sentence_enders": [
            ". Period.",
            ". No arguments.",
            ". Make it happen.",
            ". That's final.",
            ". Do it now."
        ]
    },
    "calm": {
        "name": "Calm & Peaceful",
        "description": "Gentle, soothing, mindful tone",
        "emoji_set": ["🌿", "✨", "💫", "🌸", "☁️", "🧘", "💭"],
        "intensifiers": ["gently", "softly", "peacefully", "mindfully"],
        "exclamation_ratio": 0.1,
        "transformations": {
            "must": ["might consider", "could explore", "may find it helpful to"],
            "should": ["could", "might", "you're invited to"],
            "have to": ["are encouraged to", "can choose to", "may want to"],
            "important": ["meaningful", "worth considering", "valuable"],
            "quick": ["in your own time", "at your pace", "gently"],
            "now": ["when you're ready", "in this moment", "as feels right"]
        },
        "sentence_starters": [
            "Take a moment to consider...",
            "Gently notice...",
            "When you're ready...",
            "Allow yourself to...",
            "Breathe and..."
        ],
        "sentence_enders": [
            "...in your own time.",
            "...with kindness.",
            "...and that's perfectly okay.",
            "...at your own pace.",
            "...and breathe."
        ]
    },
    "luxury": {
        "name": "Luxury/Premium",
        "description": "Sophisticated, elegant, exclusive tone",
        "emoji_set": ["✨", "💎", "🥂", "🌟", "👑", "🎭"],
        "intensifiers": ["exquisitely", "exceptionally", "remarkably", "distinctively"],
        "exclamation_ratio": 0.2,
        "transformations": {
            "good": ["exceptional", "exquisite", "distinguished"],
            "best": ["finest", "most coveted", "premier"],
            "buy": ["acquire", "invest in", "curate"],
            "cheap": ["accessible", "attainable", "value-conscious"],
            "expensive": ["premium", "exclusive", "investment-worthy"],
            "product": ["offering", "creation", "masterpiece"],
            "deal": ["opportunity", "invitation", "exclusive access"]
        },
        "sentence_starters": [
            "For the discerning...",
            "Experience the extraordinary...",
            "Elevate your...",
            "Discover refined...",
            "Indulge in..."
        ],
        "sentence_enders": [
            "...crafted for excellence.",
            "...for those who appreciate the finer things.",
            "...an experience unlike any other.",
            "...where quality meets elegance.",
            "...beyond the ordinary."
        ]
    },
    "motivational": {
        "name": "Motivational",
        "description": "Inspiring, empowering, uplifting tone",
        "emoji_set": ["🌟", "💪", "🚀", "✨", "🎯", "💫", "🔥", "⭐"],
        "intensifiers": ["absolutely", "truly", "genuinely", "remarkably"],
        "exclamation_ratio": 0.5,
        "transformations": {
            "can't": ["CAN", "will", "are capable of"],
            "hard": ["challenging but achievable", "growth opportunity", "your next breakthrough"],
            "fail": ["learn", "grow", "discover what works"],
            "problem": ["opportunity", "challenge to overcome", "stepping stone"],
            "impossible": ["not yet achieved", "waiting for you", "your next goal"],
            "weak": ["getting stronger", "in progress", "building up"]
        },
        "sentence_starters": [
            "You've got this!",
            "Believe in yourself:",
            "Your potential is limitless!",
            "Champions know:",
            "Rise up!"
        ],
        "sentence_enders": [
            "...you're stronger than you know!",
            "...greatness awaits!",
            "...your time is NOW!",
            "...make it happen!",
            "...believe and achieve!"
        ]
    }
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    targetTone: str = Field(default="funny")
    intensity: int = Field(default=50, ge=0, le=100)  # 0-100 slider
    keepLength: str = Field(default="same")  # "same", "shorter", "longer"
    variationCount: int = Field(default=1, ge=1, le=10)


# =============================================================================
# TRANSFORMATION FUNCTIONS
# =============================================================================

def apply_word_transformations(text: str, transformations: dict, intensity: float) -> str:
    """Apply word-level transformations based on tone"""
    result = text
    
    for original, replacements in transformations.items():
        if isinstance(replacements, list):
            replacement = random.choice(replacements)
        else:
            replacement = replacements
        
        # Apply based on intensity
        if random.random() < intensity:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(original), re.IGNORECASE)
            result = pattern.sub(replacement, result, count=1)
    
    return result


def adjust_punctuation(text: str, exclamation_ratio: float, intensity: float) -> str:
    """Adjust sentence-ending punctuation based on tone"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result_sentences = []
    
    for sentence in sentences:
        if sentence.strip():
            # Determine if should add exclamation
            should_exclaim = random.random() < (exclamation_ratio * intensity)
            
            # Replace ending punctuation
            if should_exclaim and sentence.rstrip()[-1] in '.!':
                sentence = sentence.rstrip()[:-1] + '!'
            
            result_sentences.append(sentence)
    
    return ' '.join(result_sentences)


def add_intensifiers(text: str, intensifiers: list, intensity: float) -> str:
    """Add intensifiers to sentences"""
    if random.random() > intensity:
        return text
    
    sentences = text.split('. ')
    result = []
    
    for i, sentence in enumerate(sentences):
        if i > 0 and random.random() < intensity * 0.3:
            intensifier = random.choice(intensifiers)
            sentence = f"{intensifier.capitalize()} {sentence.lower()}" if sentence else sentence
        result.append(sentence)
    
    return '. '.join(result)


def add_emojis(text: str, emoji_set: list, intensity: float) -> str:
    """Add relevant emojis based on intensity"""
    if intensity < 0.3:
        return text
    
    # Add emojis at end of text
    emoji_count = max(1, int(intensity * 3))
    selected_emojis = random.sample(emoji_set, min(emoji_count, len(emoji_set)))
    
    return f"{text} {' '.join(selected_emojis)}"


def apply_sentence_wrappers(text: str, starters: list, enders: list, intensity: float) -> str:
    """Add tone-specific sentence starters and enders"""
    sentences = text.split('. ')
    
    # Maybe add starter
    if sentences and random.random() < intensity * 0.5:
        starter = random.choice(starters)
        sentences[0] = f"{starter} {sentences[0].lower()}"
    
    # Maybe add ender
    if sentences and random.random() < intensity * 0.3:
        ender = random.choice(enders)
        sentences[-1] = sentences[-1].rstrip('.!?') + ender
    
    return '. '.join(sentences)


def adjust_length(text: str, target: str) -> str:
    """Adjust text length based on preference"""
    if target == "shorter":
        # Remove filler words and simplify
        filler_words = ["very", "really", "just", "actually", "basically", "literally"]
        for filler in filler_words:
            text = re.sub(rf'\b{filler}\b\s*', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    elif target == "longer":
        # Add connecting phrases
        connectors = [
            " - and here's the thing - ",
            ", which is interesting because ",
            ". What's more, ",
            ". Additionally, "
        ]
        sentences = text.split('. ')
        if len(sentences) > 1:
            insert_point = len(sentences) // 2
            connector = random.choice(connectors)
            sentences[insert_point] = sentences[insert_point] + connector
        return '. '.join(sentences)
    
    return text


def transform_text(text: str, tone: str, intensity: int, keep_length: str) -> str:
    """Main transformation function"""
    config = TONE_CONFIGS.get(tone, TONE_CONFIGS["funny"])
    intensity_float = intensity / 100.0
    
    # Apply transformations in order
    result = text
    
    # 1. Word transformations
    result = apply_word_transformations(result, config["transformations"], intensity_float)
    
    # 2. Add intensifiers
    result = add_intensifiers(result, config["intensifiers"], intensity_float)
    
    # 3. Adjust punctuation
    result = adjust_punctuation(result, config["exclamation_ratio"], intensity_float)
    
    # 4. Add sentence wrappers
    result = apply_sentence_wrappers(
        result, 
        config["sentence_starters"], 
        config["sentence_enders"], 
        intensity_float
    )
    
    # 5. Add emojis
    result = add_emojis(result, config["emoji_set"], intensity_float)
    
    # 6. Adjust length
    result = adjust_length(result, keep_length)
    
    # Clean up
    result = re.sub(r'\s+', ' ', result).strip()
    result = re.sub(r'\s+([.!?,])', r'\1', result)
    
    return result


async def deduct_credits(user_id: str, amount: int, ref_type: str, ref_id: str):
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
# ENDPOINTS
# =============================================================================

@router.get("/pricing")
async def get_tone_pricing():
    """Get pricing for tone switcher"""
    return {
        "pricing": TONE_PRICING,
        "options": [
            {"type": "SINGLE_REWRITE", "name": "Single Variation", "credits": TONE_PRICING["SINGLE_REWRITE"]},
            {"type": "BATCH_5", "name": "5 Variations", "credits": TONE_PRICING["BATCH_5"]},
            {"type": "BATCH_10", "name": "10 Variations", "credits": TONE_PRICING["BATCH_10"]}
        ]
    }


@router.get("/tones")
async def get_available_tones():
    """Get available tones"""
    tones = {}
    for key, config in TONE_CONFIGS.items():
        tones[key] = {
            "name": config["name"],
            "description": config["description"],
            "sampleEmojis": config["emoji_set"][:3]
        }
    return {"tones": tones}


@router.post("/rewrite")
@limiter.limit("20/minute")
async def rewrite_text(
    request: Request,
    data: RewriteRequest,
    user: dict = Depends(get_current_user)
):
    """Rewrite text with selected tone"""
    user_id = user["id"]
    
    # Validate tone
    if data.targetTone not in TONE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Invalid tone. Available: {list(TONE_CONFIGS.keys())}")
    
    # Determine pricing
    if data.variationCount <= 1:
        cost = TONE_PRICING["SINGLE_REWRITE"]
    elif data.variationCount <= 5:
        cost = TONE_PRICING["BATCH_5"]
    else:
        cost = TONE_PRICING["BATCH_10"]
    
    rewrite_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, cost, "TONE_REWRITE", rewrite_id)
    
    # Generate variations
    variations = []
    for i in range(data.variationCount):
        # Slightly vary intensity for each variation
        varied_intensity = max(0, min(100, data.intensity + random.randint(-10, 10)))
        
        transformed = transform_text(
            text=data.text,
            tone=data.targetTone,
            intensity=varied_intensity,
            keep_length=data.keepLength
        )
        variations.append({
            "index": i + 1,
            "text": transformed,
            "intensity": varied_intensity
        })
    
    # Store rewrite
    rewrite_doc = {
        "id": rewrite_id,
        "userId": user_id,
        "originalText": data.text,
        "targetTone": data.targetTone,
        "intensity": data.intensity,
        "keepLength": data.keepLength,
        "variationCount": data.variationCount,
        "variations": variations,
        "creditsUsed": cost,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tone_rewrites.insert_one(rewrite_doc)
    
    return {
        "success": True,
        "rewriteId": rewrite_id,
        "originalText": data.text,
        "targetTone": data.targetTone,
        "variations": variations,
        "creditsUsed": cost,
        "toneInfo": {
            "name": TONE_CONFIGS[data.targetTone]["name"],
            "description": TONE_CONFIGS[data.targetTone]["description"]
        },
        "disclaimer": "Generated content is template-based and should be reviewed before posting."
    }


@router.post("/preview")
async def preview_rewrite(data: RewriteRequest, user: dict = Depends(get_current_user)):
    """Preview a single rewrite without charging credits"""
    if data.targetTone not in TONE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Invalid tone")
    
    # Generate single preview
    preview = transform_text(
        text=data.text[:500],  # Limit preview length
        tone=data.targetTone,
        intensity=data.intensity,
        keep_length=data.keepLength
    )
    
    return {
        "preview": preview,
        "isPreview": True,
        "note": "This is a preview. Full rewrites and variations require credits."
    }


@router.get("/history")
async def get_rewrite_history(
    user: dict = Depends(get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's rewrite history"""
    user_id = user["id"]
    
    rewrites = await db.tone_rewrites.find(
        {"userId": user_id},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.tone_rewrites.count_documents({"userId": user_id})
    
    return {
        "rewrites": rewrites,
        "total": total
    }


@router.get("/rewrite/{rewrite_id}")
async def get_rewrite(rewrite_id: str, user: dict = Depends(get_current_user)):
    """Get specific rewrite details"""
    rewrite = await db.tone_rewrites.find_one(
        {"id": rewrite_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not rewrite:
        raise HTTPException(status_code=404, detail="Rewrite not found")
    
    return rewrite
