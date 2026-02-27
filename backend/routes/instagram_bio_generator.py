"""
Instagram Niche Bio Generator
Template-based bio generation with zero AI dependencies.
"""

import os
import random
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from middleware.auth import get_current_user, get_admin_user
from database import db

logger = logging.getLogger("creatorstudio")
router = APIRouter(prefix="/instagram-bio-generator", tags=["Instagram Bio Generator"])
limiter = Limiter(key_func=get_remote_address)

# Credit cost
CREDIT_COST = 5
DOWNLOAD_CREDIT_COST = 1


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class GenerateBioRequest(BaseModel):
    niche: str = Field(..., description="Selected niche")
    tone: str = Field(..., description="Selected tone")
    goal: str = Field(..., description="Selected goal")


class GenerateBioResponse(BaseModel):
    success: bool
    bios: List[Dict[str, Any]]
    credits_used: int
    remaining_credits: int


class NicheModel(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    active: bool = True


class HeadlineTemplateModel(BaseModel):
    id: Optional[str] = None
    niche: str
    tone: str
    template: str
    active: bool = True


class ValueTemplateModel(BaseModel):
    id: Optional[str] = None
    niche: str
    template: str
    active: bool = True


class CTATemplateModel(BaseModel):
    id: Optional[str] = None
    goal: str
    template: str
    active: bool = True


class EmojiSetModel(BaseModel):
    id: Optional[str] = None
    tone: str
    emojis: List[str]
    active: bool = True


# =============================================================================
# COPYRIGHT BLOCKED KEYWORDS
# =============================================================================

BLOCKED_KEYWORDS = [
    "marvel", "disney", "nike", "apple", "tesla", "netflix",
    "spiderman", "spider-man", "batman", "superman", "harry potter",
    "pokemon", "pikachu", "mickey mouse", "coca-cola", "pepsi",
    "google", "facebook", "meta", "amazon", "microsoft",
    "taylor swift", "beyonce", "kardashian", "elon musk",
    "mcdonald", "starbucks", "gucci", "louis vuitton", "chanel"
]


def check_copyright(text: str) -> bool:
    """Check if text contains blocked keywords"""
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return False
    return True


# =============================================================================
# DEFAULT DATA (Seeded on first run)
# =============================================================================

DEFAULT_NICHES = [
    {"name": "Business Coach", "description": "Business and entrepreneurship coaching"},
    {"name": "Luxury Influencer", "description": "Luxury lifestyle and premium brands"},
    {"name": "Fitness Coach", "description": "Health, fitness, and wellness"},
    {"name": "Parenting", "description": "Parenting tips and family life"},
    {"name": "Relationship Advice", "description": "Dating and relationship guidance"},
    {"name": "Motivation", "description": "Motivational and inspirational content"},
    {"name": "Beauty / Fashion", "description": "Beauty, makeup, and fashion"},
    {"name": "Kids Creator", "description": "Content for children and families"},
    {"name": "Digital Marketing", "description": "Marketing strategies and tips"},
    {"name": "Personal Brand", "description": "Personal branding and self-promotion"}
]

DEFAULT_TONES = ["Professional", "Bold", "Luxury", "Friendly", "Funny", "Emotional", "Authority", "Minimal"]

DEFAULT_GOALS = [
    "Grow Followers",
    "Sell Products",
    "Book Calls",
    "Build Trust",
    "Drive Website Traffic",
    "Promote Course",
    "Build Community"
]

DEFAULT_HEADLINES = [
    # Business Coach
    {"niche": "Business Coach", "tone": "Professional", "template": "Helping {audience} build profitable businesses"},
    {"niche": "Business Coach", "tone": "Bold", "template": "Turning entrepreneurs into industry leaders"},
    {"niche": "Business Coach", "tone": "Authority", "template": "Business strategist | Scaling brands globally"},
    {"niche": "Business Coach", "tone": "Friendly", "template": "Your go-to business bestie"},
    {"niche": "Business Coach", "tone": "Minimal", "template": "Business. Strategy. Growth."},
    
    # Luxury Influencer
    {"niche": "Luxury Influencer", "tone": "Luxury", "template": "Living the elevated lifestyle"},
    {"niche": "Luxury Influencer", "tone": "Bold", "template": "Curating luxury for the discerning eye"},
    {"niche": "Luxury Influencer", "tone": "Minimal", "template": "Luxury. Travel. Lifestyle."},
    {"niche": "Luxury Influencer", "tone": "Professional", "template": "Premium lifestyle curator"},
    
    # Fitness Coach
    {"niche": "Fitness Coach", "tone": "Bold", "template": "Transforming bodies, changing lives"},
    {"niche": "Fitness Coach", "tone": "Friendly", "template": "Your fitness journey starts here"},
    {"niche": "Fitness Coach", "tone": "Professional", "template": "Certified trainer | Results-driven coaching"},
    {"niche": "Fitness Coach", "tone": "Emotional", "template": "From struggle to strength"},
    {"niche": "Fitness Coach", "tone": "Authority", "template": "Elite performance coach"},
    
    # Parenting
    {"niche": "Parenting", "tone": "Friendly", "template": "Mom of {count} | Sharing the real journey"},
    {"niche": "Parenting", "tone": "Funny", "template": "Surviving parenthood one coffee at a time"},
    {"niche": "Parenting", "tone": "Emotional", "template": "Raising tiny humans with big hearts"},
    {"niche": "Parenting", "tone": "Professional", "template": "Parenting educator | Child development expert"},
    
    # Relationship Advice
    {"niche": "Relationship Advice", "tone": "Professional", "template": "Relationship coach | Healing hearts"},
    {"niche": "Relationship Advice", "tone": "Friendly", "template": "Your love life cheerleader"},
    {"niche": "Relationship Advice", "tone": "Emotional", "template": "Helping you find lasting love"},
    {"niche": "Relationship Advice", "tone": "Bold", "template": "Breaking toxic patterns since {year}"},
    
    # Motivation
    {"niche": "Motivation", "tone": "Bold", "template": "Wake up. Grind. Repeat."},
    {"niche": "Motivation", "tone": "Emotional", "template": "Your daily dose of inspiration"},
    {"niche": "Motivation", "tone": "Authority", "template": "Mindset mentor | Success architect"},
    {"niche": "Motivation", "tone": "Friendly", "template": "Here to lift you up every day"},
    
    # Beauty / Fashion
    {"niche": "Beauty / Fashion", "tone": "Luxury", "template": "Elegance is an attitude"},
    {"niche": "Beauty / Fashion", "tone": "Friendly", "template": "Making beauty accessible for all"},
    {"niche": "Beauty / Fashion", "tone": "Bold", "template": "Redefining beauty standards"},
    {"niche": "Beauty / Fashion", "tone": "Minimal", "template": "Beauty. Style. Confidence."},
    
    # Kids Creator
    {"niche": "Kids Creator", "tone": "Friendly", "template": "Fun content for little ones"},
    {"niche": "Kids Creator", "tone": "Funny", "template": "Making kids (and parents) smile daily"},
    {"niche": "Kids Creator", "tone": "Emotional", "template": "Creating magical moments for families"},
    
    # Digital Marketing
    {"niche": "Digital Marketing", "tone": "Professional", "template": "Helping brands dominate online"},
    {"niche": "Digital Marketing", "tone": "Bold", "template": "Growth hacker | Revenue multiplier"},
    {"niche": "Digital Marketing", "tone": "Authority", "template": "Digital strategist | {number}M+ reach"},
    {"niche": "Digital Marketing", "tone": "Minimal", "template": "Marketing. Strategy. Growth."},
    
    # Personal Brand
    {"niche": "Personal Brand", "tone": "Professional", "template": "Building authentic personal brands"},
    {"niche": "Personal Brand", "tone": "Bold", "template": "Stand out. Get noticed. Succeed."},
    {"niche": "Personal Brand", "tone": "Friendly", "template": "Helping you become unforgettable"},
    {"niche": "Personal Brand", "tone": "Authority", "template": "Personal branding expert | Speaker"}
]

DEFAULT_VALUE_LINES = [
    # Business Coach
    {"niche": "Business Coach", "template": "Daily business growth strategies"},
    {"niche": "Business Coach", "template": "Proven frameworks for scaling"},
    {"niche": "Business Coach", "template": "Mindset + strategy = success"},
    {"niche": "Business Coach", "template": "Simplifying complex business concepts"},
    
    # Luxury Influencer
    {"niche": "Luxury Influencer", "template": "Discovering hidden luxury gems"},
    {"niche": "Luxury Influencer", "template": "Travel | Fashion | Fine dining"},
    {"niche": "Luxury Influencer", "template": "Curated recommendations for the elite"},
    
    # Fitness Coach
    {"niche": "Fitness Coach", "template": "Workout tips that actually work"},
    {"niche": "Fitness Coach", "template": "Nutrition made simple"},
    {"niche": "Fitness Coach", "template": "No shortcuts, just results"},
    {"niche": "Fitness Coach", "template": "Free workout guides in bio"},
    
    # Parenting
    {"niche": "Parenting", "template": "Real talk about motherhood"},
    {"niche": "Parenting", "template": "Tips for busy parents"},
    {"niche": "Parenting", "template": "Making parenting less overwhelming"},
    
    # Relationship Advice
    {"niche": "Relationship Advice", "template": "Daily relationship wisdom"},
    {"niche": "Relationship Advice", "template": "Communication tips that save relationships"},
    {"niche": "Relationship Advice", "template": "Building healthy connections"},
    
    # Motivation
    {"niche": "Motivation", "template": "Daily motivation for your feed"},
    {"niche": "Motivation", "template": "Mindset shifts for success"},
    {"niche": "Motivation", "template": "Your potential is unlimited"},
    
    # Beauty / Fashion
    {"niche": "Beauty / Fashion", "template": "Outfit inspo for every occasion"},
    {"niche": "Beauty / Fashion", "template": "Skincare routines that work"},
    {"niche": "Beauty / Fashion", "template": "Affordable luxury finds"},
    
    # Kids Creator
    {"niche": "Kids Creator", "template": "Educational + entertaining content"},
    {"niche": "Kids Creator", "template": "Screen time that parents approve"},
    {"niche": "Kids Creator", "template": "Fun activities for little ones"},
    
    # Digital Marketing
    {"niche": "Digital Marketing", "template": "Actionable marketing tips daily"},
    {"niche": "Digital Marketing", "template": "Social media growth secrets"},
    {"niche": "Digital Marketing", "template": "Content that converts"},
    
    # Personal Brand
    {"niche": "Personal Brand", "template": "Stand out in your industry"},
    {"niche": "Personal Brand", "template": "Building your unique voice"},
    {"niche": "Personal Brand", "template": "From invisible to influential"}
]

DEFAULT_CTAS = [
    {"goal": "Grow Followers", "template": "Follow for daily value"},
    {"goal": "Grow Followers", "template": "Hit follow for more"},
    {"goal": "Grow Followers", "template": "Join the community below"},
    {"goal": "Sell Products", "template": "Shop the collection below"},
    {"goal": "Sell Products", "template": "Link in bio to shop"},
    {"goal": "Sell Products", "template": "Tap link for exclusive deals"},
    {"goal": "Book Calls", "template": "Book your free call below"},
    {"goal": "Book Calls", "template": "DM 'READY' to get started"},
    {"goal": "Book Calls", "template": "Let's chat - link in bio"},
    {"goal": "Build Trust", "template": "Real results, real stories"},
    {"goal": "Build Trust", "template": "See client transformations below"},
    {"goal": "Build Trust", "template": "Trusted by thousands"},
    {"goal": "Drive Website Traffic", "template": "Read the full blog below"},
    {"goal": "Drive Website Traffic", "template": "Free resources in link"},
    {"goal": "Drive Website Traffic", "template": "Tap for more content"},
    {"goal": "Promote Course", "template": "Enroll now - link in bio"},
    {"goal": "Promote Course", "template": "Free masterclass below"},
    {"goal": "Promote Course", "template": "Start learning today"},
    {"goal": "Build Community", "template": "Join our tribe below"},
    {"goal": "Build Community", "template": "Be part of the movement"},
    {"goal": "Build Community", "template": "Connect with like-minded souls"}
]

DEFAULT_EMOJI_SETS = [
    {"tone": "Professional", "emojis": ["📈", "💼", "📊", "✅", "🎯", "💡"]},
    {"tone": "Bold", "emojis": ["🔥", "💪", "⚡", "🚀", "💯", "👊"]},
    {"tone": "Luxury", "emojis": ["✨", "🖤", "💎", "🥂", "👑", "🌟"]},
    {"tone": "Friendly", "emojis": ["💕", "🌈", "😊", "🙌", "💫", "🤗"]},
    {"tone": "Funny", "emojis": ["😂", "🤪", "🎭", "😜", "🤣", "💀"]},
    {"tone": "Emotional", "emojis": ["❤️", "🙏", "💖", "🌸", "✨", "🦋"]},
    {"tone": "Authority", "emojis": ["🏆", "📚", "🎓", "💼", "🌍", "⭐"]},
    {"tone": "Minimal", "emojis": ["•", "→", "—", "∙", "|", "/"]}
]


# =============================================================================
# DATABASE SEEDING
# =============================================================================

async def seed_bio_generator_data():
    """Seed default data if collections are empty"""
    
    # Seed niches
    if await db.bio_niches.count_documents({}) == 0:
        for niche in DEFAULT_NICHES:
            niche["id"] = niche["name"].lower().replace(" ", "_").replace("/", "_")
            niche["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.bio_niches.insert_many(DEFAULT_NICHES)
        logger.info(f"Seeded {len(DEFAULT_NICHES)} bio niches")
    
    # Seed headlines
    if await db.bio_headlines.count_documents({}) == 0:
        import uuid
        for headline in DEFAULT_HEADLINES:
            headline["id"] = str(uuid.uuid4())
            headline["active"] = True
            headline["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.bio_headlines.insert_many(DEFAULT_HEADLINES)
        logger.info(f"Seeded {len(DEFAULT_HEADLINES)} bio headlines")
    
    # Seed value lines
    if await db.bio_value_lines.count_documents({}) == 0:
        import uuid
        for value in DEFAULT_VALUE_LINES:
            value["id"] = str(uuid.uuid4())
            value["active"] = True
            value["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.bio_value_lines.insert_many(DEFAULT_VALUE_LINES)
        logger.info(f"Seeded {len(DEFAULT_VALUE_LINES)} bio value lines")
    
    # Seed CTAs
    if await db.bio_ctas.count_documents({}) == 0:
        import uuid
        for cta in DEFAULT_CTAS:
            cta["id"] = str(uuid.uuid4())
            cta["active"] = True
            cta["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.bio_ctas.insert_many(DEFAULT_CTAS)
        logger.info(f"Seeded {len(DEFAULT_CTAS)} bio CTAs")
    
    # Seed emoji sets
    if await db.bio_emoji_sets.count_documents({}) == 0:
        import uuid
        for emoji_set in DEFAULT_EMOJI_SETS:
            emoji_set["id"] = str(uuid.uuid4())
            emoji_set["active"] = True
            emoji_set["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.bio_emoji_sets.insert_many(DEFAULT_EMOJI_SETS)
        logger.info(f"Seeded {len(DEFAULT_EMOJI_SETS)} bio emoji sets")


# =============================================================================
# BIO GENERATION ENGINE
# =============================================================================

def interpolate_template(template: str) -> str:
    """Replace placeholder variables with random values"""
    replacements = {
        "{audience}": random.choice(["entrepreneurs", "creators", "coaches", "brands", "dreamers", "leaders"]),
        "{result}": random.choice(["success", "growth", "freedom", "results", "transformation", "impact"]),
        "{topic}": random.choice(["growth", "success", "lifestyle", "tips", "strategies", "insights"]),
        "{count}": random.choice(["2", "3", "4"]),
        "{year}": random.choice(["2020", "2021", "2022", "2023"]),
        "{number}": random.choice(["100K", "500K", "1", "5", "10"])
    }
    
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    
    return result


async def generate_single_bio(niche: str, tone: str, goal: str) -> Dict[str, Any]:
    """Generate a single bio from templates"""
    
    # Fetch headline
    headlines = await db.bio_headlines.find({
        "niche": niche,
        "tone": tone,
        "active": True
    }).to_list(length=100)
    
    if not headlines:
        # Fallback to any headline for this niche
        headlines = await db.bio_headlines.find({
            "niche": niche,
            "active": True
        }).to_list(length=100)
    
    if not headlines:
        # Ultimate fallback
        headlines = [{"template": f"Welcome to my {niche.lower()} journey"}]
    
    headline_template = random.choice(headlines)["template"]
    headline = interpolate_template(headline_template)
    
    # Fetch value lines
    value_lines = await db.bio_value_lines.find({
        "niche": niche,
        "active": True
    }).to_list(length=100)
    
    if not value_lines:
        value_lines = [{"template": "Sharing valuable content daily"}]
    
    # Pick 1-2 value lines
    selected_values = random.sample(value_lines, min(2, len(value_lines)))
    value1 = interpolate_template(selected_values[0]["template"])
    value2 = interpolate_template(selected_values[-1]["template"]) if len(selected_values) > 1 else ""
    
    # Fetch CTA
    ctas = await db.bio_ctas.find({
        "goal": goal,
        "active": True
    }).to_list(length=100)
    
    if not ctas:
        ctas = [{"template": "Link in bio for more"}]
    
    cta = interpolate_template(random.choice(ctas)["template"])
    
    # Fetch emojis
    emoji_sets = await db.bio_emoji_sets.find({
        "tone": tone,
        "active": True
    }).to_list(length=10)
    
    if not emoji_sets:
        emoji_sets = [{"emojis": ["✨", "📈", "🎯"]}]
    
    emojis = emoji_sets[0]["emojis"]
    selected_emojis = random.sample(emojis, min(3, len(emojis)))
    
    # Assemble bio
    bio_lines = []
    
    # Line 1: Emoji + Headline
    bio_lines.append(f"{selected_emojis[0]} {headline}")
    
    # Line 2: Emoji + Value 1
    if len(selected_emojis) > 1:
        bio_lines.append(f"{selected_emojis[1]} {value1}")
    else:
        bio_lines.append(f"• {value1}")
    
    # Line 3: Value 2 (if available)
    if value2 and value2 != value1:
        if len(selected_emojis) > 2:
            bio_lines.append(f"{selected_emojis[2]} {value2}")
        else:
            bio_lines.append(f"• {value2}")
    
    # Line 4: CTA with pointing emoji
    bio_lines.append(f"👇 {cta}")
    
    # Combine into full bio
    full_bio = "\n".join(bio_lines)
    
    return {
        "bio": full_bio,
        "headline": headline,
        "value_lines": [value1, value2] if value2 else [value1],
        "cta": cta,
        "emojis_used": selected_emojis,
        "character_count": len(full_bio)
    }


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/config")
async def get_bio_generator_config():
    """Get configuration options for the bio generator"""
    
    # Seed data if needed
    await seed_bio_generator_data()
    
    # Fetch niches
    niches = await db.bio_niches.find({"active": {"$ne": False}}, {"_id": 0}).to_list(length=100)
    
    return {
        "niches": [n["name"] for n in niches],
        "tones": DEFAULT_TONES,
        "goals": DEFAULT_GOALS,
        "creditCost": CREDIT_COST,
        "downloadCreditCost": DOWNLOAD_CREDIT_COST,
        "disclaimer": "This tool generates original generic bio templates. Do not use copyrighted brand names."
    }


@router.post("/generate")
@limiter.limit("20/minute")
async def generate_bios(
    request: Request,
    data: GenerateBioRequest,
    user: dict = Depends(get_current_user)
):
    """Generate 5 Instagram bios based on selected options"""
    
    # Validate inputs
    if not data.niche or not data.tone or not data.goal:
        raise HTTPException(status_code=400, detail="Niche, tone, and goal are required")
    
    # Check for blocked keywords
    if not check_copyright(data.niche):
        raise HTTPException(status_code=400, detail="Input contains blocked content")
    
    # Check credits
    wallet = await db.wallets.find_one({"userId": user["id"]})
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")
    
    current_credits = wallet.get("balanceCredits", wallet.get("availableCredits", 0))
    if current_credits < CREDIT_COST:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {CREDIT_COST}, Available: {current_credits}"
        )
    
    # Deduct credits BEFORE generation
    await db.wallets.update_one(
        {"userId": user["id"]},
        {
            "$inc": {"balanceCredits": -CREDIT_COST, "availableCredits": -CREDIT_COST},
            "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Record transaction
    await db.credit_transactions.insert_one({
        "userId": user["id"],
        "type": "debit",
        "amount": CREDIT_COST,
        "reason": "Instagram Bio Generator",
        "feature": "instagram-bio-generator",
        "metadata": {"niche": data.niche, "tone": data.tone, "goal": data.goal},
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    try:
        # Generate 5 unique bios
        bios = []
        attempts = 0
        max_attempts = 15  # Prevent infinite loop
        
        while len(bios) < 5 and attempts < max_attempts:
            attempts += 1
            bio = await generate_single_bio(data.niche, data.tone, data.goal)
            
            # Check for duplicates
            if not any(b["bio"] == bio["bio"] for b in bios):
                bios.append(bio)
        
        # Get updated balance
        updated_wallet = await db.wallets.find_one({"userId": user["id"]})
        remaining_credits = updated_wallet.get("balanceCredits", updated_wallet.get("availableCredits", 0))
        
        # Log generation
        await db.bio_generations.insert_one({
            "userId": user["id"],
            "niche": data.niche,
            "tone": data.tone,
            "goal": data.goal,
            "bios_generated": len(bios),
            "credits_used": CREDIT_COST,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"User {user['id']} generated {len(bios)} Instagram bios")
        
        return {
            "success": True,
            "bios": bios,
            "credits_used": CREDIT_COST,
            "remaining_credits": remaining_credits
        }
        
    except Exception as e:
        # Refund credits on error
        await db.wallets.update_one(
            {"userId": user["id"]},
            {"$inc": {"balanceCredits": CREDIT_COST, "availableCredits": CREDIT_COST}}
        )
        logger.error(f"Bio generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed. Credits refunded.")


@router.post("/download")
@limiter.limit("10/minute")
async def download_bios(
    request: Request,
    bios: List[str],
    user: dict = Depends(get_current_user)
):
    """Download bios as text (costs 1 credit)"""
    
    # Check credits
    wallet = await db.wallets.find_one({"userId": user["id"]})
    current_credits = wallet.get("balanceCredits", wallet.get("availableCredits", 0))
    
    if current_credits < DOWNLOAD_CREDIT_COST:
        raise HTTPException(status_code=402, detail="Insufficient credits for download")
    
    # Deduct credit
    await db.wallets.update_one(
        {"userId": user["id"]},
        {"$inc": {"balanceCredits": -DOWNLOAD_CREDIT_COST, "availableCredits": -DOWNLOAD_CREDIT_COST}}
    )
    
    # Format for download
    content = "Instagram Bio Generator - Your Bios\n"
    content += "=" * 40 + "\n\n"
    
    for i, bio in enumerate(bios, 1):
        content += f"Bio {i}:\n{bio}\n\n"
        content += "-" * 20 + "\n\n"
    
    content += "\nGenerated by CreatorStudio AI\n"
    content += "Remember: Do not use copyrighted brand names.\n"
    
    return {
        "success": True,
        "content": content,
        "filename": "instagram_bios.txt"
    }


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Get bio generator statistics"""
    
    total_generations = await db.bio_generations.count_documents({})
    total_niches = await db.bio_niches.count_documents({})
    total_headlines = await db.bio_headlines.count_documents({})
    total_values = await db.bio_value_lines.count_documents({})
    total_ctas = await db.bio_ctas.count_documents({})
    
    return {
        "total_generations": total_generations,
        "total_niches": total_niches,
        "total_headlines": total_headlines,
        "total_value_lines": total_values,
        "total_ctas": total_ctas,
        "credit_cost": CREDIT_COST
    }


@router.get("/admin/niches")
async def get_admin_niches(admin: dict = Depends(get_admin_user)):
    """Get all niches for admin"""
    niches = await db.bio_niches.find({}, {"_id": 0}).to_list(length=100)
    return {"niches": niches}


@router.post("/admin/niches")
async def create_niche(niche: NicheModel, admin: dict = Depends(get_admin_user)):
    """Create a new niche"""
    import uuid
    
    niche_data = niche.dict()
    niche_data["id"] = str(uuid.uuid4())
    niche_data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bio_niches.insert_one(niche_data)
    return {"success": True, "niche": niche_data}


@router.put("/admin/niches/{niche_id}")
async def update_niche(niche_id: str, niche: NicheModel, admin: dict = Depends(get_admin_user)):
    """Update a niche"""
    await db.bio_niches.update_one(
        {"id": niche_id},
        {"$set": {"name": niche.name, "description": niche.description, "active": niche.active}}
    )
    return {"success": True}


@router.delete("/admin/niches/{niche_id}")
async def delete_niche(niche_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a niche"""
    await db.bio_niches.delete_one({"id": niche_id})
    return {"success": True}


@router.get("/admin/headlines")
async def get_admin_headlines(admin: dict = Depends(get_admin_user)):
    """Get all headline templates"""
    headlines = await db.bio_headlines.find({}, {"_id": 0}).to_list(length=500)
    return {"headlines": headlines}


@router.post("/admin/headlines")
async def create_headline(headline: HeadlineTemplateModel, admin: dict = Depends(get_admin_user)):
    """Create a new headline template"""
    import uuid
    
    data = headline.dict()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bio_headlines.insert_one(data)
    return {"success": True, "headline": data}


@router.put("/admin/headlines/{headline_id}")
async def update_headline(headline_id: str, headline: HeadlineTemplateModel, admin: dict = Depends(get_admin_user)):
    """Update a headline template"""
    await db.bio_headlines.update_one(
        {"id": headline_id},
        {"$set": headline.dict(exclude={"id"})}
    )
    return {"success": True}


@router.delete("/admin/headlines/{headline_id}")
async def delete_headline(headline_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a headline template"""
    await db.bio_headlines.delete_one({"id": headline_id})
    return {"success": True}


@router.get("/admin/values")
async def get_admin_values(admin: dict = Depends(get_admin_user)):
    """Get all value line templates"""
    values = await db.bio_value_lines.find({}, {"_id": 0}).to_list(length=500)
    return {"values": values}


@router.post("/admin/values")
async def create_value(value: ValueTemplateModel, admin: dict = Depends(get_admin_user)):
    """Create a new value template"""
    import uuid
    
    data = value.dict()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bio_value_lines.insert_one(data)
    return {"success": True, "value": data}


@router.get("/admin/ctas")
async def get_admin_ctas(admin: dict = Depends(get_admin_user)):
    """Get all CTA templates"""
    ctas = await db.bio_ctas.find({}, {"_id": 0}).to_list(length=500)
    return {"ctas": ctas}


@router.post("/admin/ctas")
async def create_cta(cta: CTATemplateModel, admin: dict = Depends(get_admin_user)):
    """Create a new CTA template"""
    import uuid
    
    data = cta.dict()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bio_ctas.insert_one(data)
    return {"success": True, "cta": data}


@router.get("/admin/emojis")
async def get_admin_emojis(admin: dict = Depends(get_admin_user)):
    """Get all emoji sets"""
    emojis = await db.bio_emoji_sets.find({}, {"_id": 0}).to_list(length=100)
    return {"emoji_sets": emojis}


@router.post("/admin/emojis")
async def create_emoji_set(emoji_set: EmojiSetModel, admin: dict = Depends(get_admin_user)):
    """Create a new emoji set"""
    import uuid
    
    data = emoji_set.dict()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bio_emoji_sets.insert_one(data)
    return {"success": True, "emoji_set": data}


@router.put("/admin/pricing")
async def update_pricing(credit_cost: int, admin: dict = Depends(get_admin_user)):
    """Update credit pricing (requires code change for now)"""
    # This would require updating the constant - for now just return info
    return {
        "message": "Pricing update requires code change",
        "current_cost": CREDIT_COST,
        "requested_cost": credit_cost
    }
