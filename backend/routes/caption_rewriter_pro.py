"""
Caption Rewriter Pro - Rebuilt from Tone Switcher
"Rewrite your content in viral tones instantly."

3-Step Guided Wizard:
- Step 1: Paste Text
- Step 2: Choose Tone (6 options only)
- Step 3: Generate Rewrite (3 variations)

Zero AI Cost - Uses smart templates
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

router = APIRouter(prefix="/caption-rewriter-pro", tags=["Caption Rewriter Pro"])

# =============================================================================
# COPYRIGHT PROTECTION - BLOCKED KEYWORDS
# =============================================================================
BLOCKED_KEYWORDS = [
    "mickey", "disney", "marvel", "avengers", "pokemon", "pikachu", "naruto",
    "goku", "harry potter", "batman", "superman", "spiderman", "spider-man",
    "taylor swift", "beyonce", "drake", "elon musk", "trump", "biden",
    "nike", "adidas", "apple", "google", "amazon", "coca cola"
]

def check_copyright_violation(text: str) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return keyword
    return None

def sanitize_xss(text: str) -> str:
    """Remove potential XSS payloads from text"""
    if not text:
        return text
    # Remove script tags
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<script[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</script>', '', text, flags=re.IGNORECASE)
    # Remove event handlers
    text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*on\w+\s*=\s*\S+', '', text, flags=re.IGNORECASE)
    # Remove javascript: URLs
    text = re.sub(r'javascript\s*:', '', text, flags=re.IGNORECASE)
    # Remove img/svg/iframe with onerror
    text = re.sub(r'<(img|svg|iframe)[^>]*>', '', text, flags=re.IGNORECASE)
    return text

# =============================================================================
# PRICING - SIMPLIFIED (Only 3 options)
# =============================================================================
PRICING = {
    "single_tone": 5,      # 3 variations in 1 tone
    "three_tones": 12,     # 3 variations in 3 tones (9 total)
    "all_tones": 20,       # 3 variations in all 6 tones (18 total)
    "commercial_use": 10   # Commercial license add-on
}

# =============================================================================
# 6 TONES ONLY (Simplified from original)
# =============================================================================
TONES = {
    "funny": {
        "name": "Funny",
        "emoji": "😂",
        "description": "Add humor and make people laugh",
        "transformations": {
            "good": ["amazing", "incredible", "chef's kiss worthy"],
            "bad": ["a total disaster", "chaos mode activated", "yikes"],
            "important": ["super important", "mega crucial", "do-not-miss"],
            "love": ["absolutely obsessed with", "can't live without", "dying for"]
        },
        "starters": ["Plot twist:", "Not gonna lie,", "Here's the thing:", "Hot take:"],
        "enders": ["...just saying!", "- you're welcome!", "(trust me)", "- mic drop!"],
        "emoji_set": ["😂", "🤣", "😆", "💀", "🔥", "✨"]
    },
    "luxury": {
        "name": "Luxury",
        "emoji": "✨",
        "description": "Sophisticated and premium feel",
        "transformations": {
            "good": ["exceptional", "exquisite", "unparalleled"],
            "buy": ["invest in", "acquire", "curate"],
            "nice": ["refined", "elegant", "distinguished"],
            "product": ["masterpiece", "creation", "offering"]
        },
        "starters": ["For the discerning:", "Experience luxury:", "Elevate your:"],
        "enders": ["...crafted for excellence.", "...beyond ordinary.", "...for the refined."],
        "emoji_set": ["✨", "💎", "🥂", "👑", "🌟", "🎭"]
    },
    "bold": {
        "name": "Bold",
        "emoji": "💪",
        "description": "Confident, direct, no-nonsense",
        "transformations": {
            "should": ["MUST", "need to", "have to"],
            "maybe": ["definitely", "absolutely", "without doubt"],
            "try": ["commit to", "execute", "dominate"],
            "can": ["WILL", "are going to", "shall"]
        },
        "starters": ["Listen up:", "Here's the truth:", "No excuses:"],
        "enders": [". Period.", ". Make it happen.", ". Do it now."],
        "emoji_set": ["💪", "🔥", "⚡", "🎯", "💥", "🚀"]
    },
    "emotional": {
        "name": "Emotional",
        "emoji": "❤️",
        "description": "Heartfelt and touching",
        "transformations": {
            "happy": ["overjoyed", "blessed", "grateful beyond words"],
            "sad": ["heartbroken", "devastated", "moved to tears"],
            "love": ["cherish", "treasure", "hold dear"],
            "important": ["meaningful", "precious", "close to my heart"]
        },
        "starters": ["From the heart:", "I have to share:", "This means everything:"],
        "enders": ["...and I'm so grateful.", "...tears of joy.", "...blessed beyond measure."],
        "emoji_set": ["❤️", "🥹", "💕", "🙏", "✨", "💫"]
    },
    "motivational": {
        "name": "Motivational",
        "emoji": "🚀",
        "description": "Inspiring and empowering",
        "transformations": {
            "can't": ["CAN", "will", "are capable of"],
            "hard": ["challenging but achievable", "growth opportunity"],
            "fail": ["learn", "grow", "discover"],
            "problem": ["opportunity", "stepping stone", "breakthrough"]
        },
        "starters": ["You've got this!", "Rise up:", "Your time is NOW:"],
        "enders": ["...greatness awaits!", "...believe and achieve!", "...make it happen!"],
        "emoji_set": ["🚀", "💪", "🌟", "✨", "🎯", "⭐"]
    },
    "storytelling": {
        "name": "Storytelling",
        "emoji": "📖",
        "description": "Narrative and engaging",
        "transformations": {
            "then": ["and then something happened", "when suddenly"],
            "but": ["but here's the twist", "until one day"],
            "so": ["which led to", "and that's how"],
            "because": ["the reason was simple", "it all started when"]
        },
        "starters": ["Picture this:", "Let me tell you a story:", "It all started when:"],
        "enders": ["...and that changed everything.", "...the rest is history.", "...and I never looked back."],
        "emoji_set": ["📖", "✨", "🎬", "💫", "🌟", "🔮"]
    }
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000, description="Text to rewrite")
    tone: str = Field(..., description="funny, luxury, bold, emotional, motivational, storytelling")
    pack_type: str = Field(default="single_tone", description="single_tone, three_tones, all_tones")
    add_ons: List[str] = Field(default_factory=list, description="commercial_use")

# =============================================================================
# TRANSFORMATION FUNCTIONS
# =============================================================================
def apply_transformations(text: str, transformations: dict) -> str:
    """Apply word transformations"""
    result = text
    for original, replacements in transformations.items():
        if isinstance(replacements, list):
            replacement = random.choice(replacements)
        else:
            replacement = replacements
        # Case-insensitive replacement (only first occurrence)
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(replacement, result, count=1)
    return result

def add_tone_elements(text: str, tone_config: dict, variation: int) -> str:
    """Add starters, enders, and emojis based on tone"""
    result = text
    
    # Add starter (50% chance for variation)
    if variation == 0 or random.random() > 0.5:
        starter = random.choice(tone_config["starters"])
        # Lowercase first letter of original text if adding starter
        if result and result[0].isupper():
            result = result[0].lower() + result[1:]
        result = f"{starter} {result}"
    
    # Add ender (50% chance for variation)
    if variation == 0 or random.random() > 0.5:
        ender = random.choice(tone_config["enders"])
        result = result.rstrip('.!?') + ender
    
    # Add emojis
    emoji_count = random.randint(1, 3)
    emojis = random.sample(tone_config["emoji_set"], emoji_count)
    result = f"{result} {' '.join(emojis)}"
    
    return result

def generate_variation(text: str, tone: str, variation_num: int) -> str:
    """Generate a single variation"""
    tone_config = TONES.get(tone, TONES["funny"])
    
    # Apply transformations
    result = apply_transformations(text, tone_config["transformations"])
    
    # Add tone elements
    result = add_tone_elements(result, tone_config, variation_num)
    
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
# SAMPLE PREVIEW DATA (Try Before You Buy)
# =============================================================================
SAMPLE_PREVIEW = {
    "original_text": "Check out our new product! It's really good and you should buy it.",
    "selected_tone": "funny",
    "results": {
        "funny": {
            "tone_name": "Funny",
            "emoji": "😂",
            "variations": [
                {"variation": 1, "text": "Hot take: check out our new product! It's incredible and you should totally invest in it...just saying! 😂 🔥 ✨"},
                {"variation": 2, "text": "Plot twist: our new product is chef's kiss worthy and you absolutely need it - you're welcome! 🤣 😆 💀"},
                {"variation": 3, "text": "Not gonna lie, this product is amazing and you should definitely get it (trust me) 😂 ✨ 🔥"}
            ]
        },
        "luxury": {
            "tone_name": "Luxury",
            "emoji": "✨",
            "variations": [
                {"variation": 1, "text": "For the discerning: discover our exceptional new creation...crafted for excellence. ✨ 💎 🥂"},
                {"variation": 2, "text": "Experience luxury: our exquisite new masterpiece awaits...beyond ordinary. 👑 🌟 🎭"},
                {"variation": 3, "text": "Elevate your: acquire our unparalleled new offering...for the refined. ✨ 💎 👑"}
            ]
        },
        "bold": {
            "tone_name": "Bold",
            "emoji": "💪",
            "variations": [
                {"variation": 1, "text": "Listen up: check out our new product! It's AMAZING and you MUST get it. Period. 💪 🔥 ⚡"},
                {"variation": 2, "text": "Here's the truth: our product is incredible and you definitely need to commit to it. Make it happen. 🎯 💥 🚀"},
                {"variation": 3, "text": "No excuses: this product is GREAT and you absolutely WILL love it. Do it now. 💪 ⚡ 🔥"}
            ]
        }
    },
    "total_variations": 9,
    "is_preview": True,
    "preview_message": "This is a FREE preview showing 3 tones. Generate your own rewrites!"
}

# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/config")
async def get_config():
    """Get feature configuration"""
    return {
        "tones": {k: {"name": v["name"], "emoji": v["emoji"], "description": v["description"]} 
                  for k, v in TONES.items()},
        "pricing": {
            "single_tone": {"credits": PRICING["single_tone"], "label": "Single Tone", "variations": 3},
            "three_tones": {"credits": PRICING["three_tones"], "label": "3 Tones Pack", "variations": 9},
            "all_tones": {"credits": PRICING["all_tones"], "label": "All Tones Pack", "variations": 18}
        },
        "add_ons": {
            "commercial_use": {"credits": PRICING["commercial_use"], "label": "Commercial Use"}
        },
        "steps": [
            {"step": 1, "title": "Paste Text", "description": "Enter the text you want to rewrite"},
            {"step": 2, "title": "Choose Tone", "description": "Select from 6 viral tones"},
            {"step": 3, "title": "Generate", "description": "Get 3 variations instantly"}
        ]
    }

@router.get("/preview")
async def get_preview():
    """Get a FREE sample preview - Try Before You Buy"""
    return SAMPLE_PREVIEW

@router.post("/rewrite")
@limiter.limit("20/minute")
async def rewrite_caption(
    request: Request,
    data: RewriteRequest,
    user: dict = Depends(get_current_user)
):
    """Rewrite caption in selected tone - 3-step wizard endpoint"""
    user_id = user["id"]
    user_plan = user.get("plan", "free")
    
    # Validate tone
    if data.tone not in TONES:
        raise HTTPException(status_code=400, detail=f"Invalid tone. Choose from: {list(TONES.keys())}")
    
    # Validate pack type
    if data.pack_type not in ["single_tone", "three_tones", "all_tones"]:
        raise HTTPException(status_code=400, detail="Invalid pack type")
    
    # COPYRIGHT CHECK
    violation = check_copyright_violation(data.text)
    if violation:
        raise HTTPException(
            status_code=400,
            detail=f"Branded or copyrighted content is not allowed. Detected: '{violation}'"
        )
    
    # Calculate cost
    base_cost = PRICING[data.pack_type]
    addon_cost = sum(PRICING.get(addon, 0) for addon in data.add_ons)
    total_cost = base_cost + addon_cost
    
    # Generate rewrite ID
    rewrite_id = str(uuid.uuid4())
    
    # Deduct credits
    await deduct_credits(user_id, total_cost, "CAPTION_REWRITER", rewrite_id)
    
    # Determine which tones to use
    if data.pack_type == "single_tone":
        tones_to_use = [data.tone]
    elif data.pack_type == "three_tones":
        # Use selected tone + 2 random others
        other_tones = [t for t in TONES.keys() if t != data.tone]
        tones_to_use = [data.tone] + random.sample(other_tones, 2)
    else:  # all_tones
        tones_to_use = list(TONES.keys())
    
    # Generate variations
    results = {}
    for tone in tones_to_use:
        variations = []
        for i in range(3):  # Always 3 variations per tone
            variation = generate_variation(data.text, tone, i)
            variations.append({
                "variation": i + 1,
                "text": variation
            })
        results[tone] = {
            "tone_name": TONES[tone]["name"],
            "emoji": TONES[tone]["emoji"],
            "variations": variations
        }
    
    # Determine watermark status
    has_watermark = user_plan == "free" and "commercial_use" not in data.add_ons
    
    # Store rewrite
    rewrite_doc = {
        "id": rewrite_id,
        "userId": user_id,
        "original_text": data.text,
        "selected_tone": data.tone,
        "pack_type": data.pack_type,
        "results": results,
        "add_ons": data.add_ons,
        "credits_used": total_cost,
        "has_watermark": has_watermark,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.caption_rewrites.insert_one(rewrite_doc)
    
    # Calculate total variations
    total_variations = len(tones_to_use) * 3
    
    return {
        "success": True,
        "rewrite_id": rewrite_id,
        "original_text": data.text,
        "selected_tone": data.tone,
        "results": results,
        "total_variations": total_variations,
        "credits_used": total_cost,
        "has_watermark": has_watermark,
        "message": f"{total_variations} variations generated!"
    }

@router.get("/rewrite/{rewrite_id}")
async def get_rewrite(rewrite_id: str, user: dict = Depends(get_current_user)):
    """Get rewrite details"""
    rewrite = await db.caption_rewrites.find_one(
        {"id": rewrite_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not rewrite:
        raise HTTPException(status_code=404, detail="Rewrite not found")
    
    return rewrite

@router.get("/history")
async def get_history(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get user's rewrite history"""
    rewrites = await db.caption_rewrites.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(limit).to_list(limit)
    
    return {"rewrites": rewrites}
