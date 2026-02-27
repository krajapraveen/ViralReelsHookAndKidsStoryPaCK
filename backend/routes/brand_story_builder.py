"""
Brand Story Builder
Template-based, no AI, <200ms response
Price: 18 credits
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import time
from datetime import datetime, timezone
from bson import ObjectId

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/brand-story-builder", tags=["Brand Story Builder"])

# ==================== COPYRIGHT PROTECTION ====================
BLOCKED_KEYWORDS = [
    "marvel", "disney", "pixar", "harry potter", "pokemon", "naruto", "spiderman", 
    "batman", "superman", "avengers", "frozen", "mickey", "star wars", "lord of the rings",
    "netflix", "amazon", "google", "apple", "microsoft", "facebook", "instagram",
    "tiktok", "youtube", "twitter", "coca cola", "pepsi", "mcdonalds", "nike", "adidas",
    "gucci", "louis vuitton", "rolex", "ferrari", "lamborghini", "tesla", "elon musk",
    "jeff bezos", "mark zuckerberg", "bill gates", "taylor swift", "beyonce", "drake"
]

def check_copyright(text: str) -> bool:
    text_lower = text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# ==================== TEMPLATES ====================
INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Education", "E-commerce", 
    "Real Estate", "Food & Beverage", "Fashion", "Consulting", "Marketing",
    "Fitness", "Travel", "Entertainment", "Manufacturing", "Non-profit"
]

TONES = ["professional", "bold", "luxury", "friendly"]

# Opening templates by industry and tone
OPENING_TEMPLATES = {
    "professional": [
        "At {business_name}, we believe in transforming {industry} through innovation and excellence.",
        "{business_name} was founded on a simple principle: deliver exceptional value in {industry}.",
        "Welcome to {business_name}, where {industry} meets precision and professionalism.",
    ],
    "bold": [
        "{business_name} isn't just another {industry} company. We're revolutionizing the game.",
        "Forget everything you know about {industry}. {business_name} is rewriting the rules.",
        "{business_name}: Because {industry} needed a wake-up call.",
    ],
    "luxury": [
        "{business_name} represents the pinnacle of {industry} excellence.",
        "Discover {business_name}: Where {industry} becomes an art form.",
        "Experience the epitome of {industry} sophistication with {business_name}.",
    ],
    "friendly": [
        "Hey there! {business_name} is here to make {industry} actually enjoyable.",
        "We're {business_name}, and we're passionate about making {industry} accessible to everyone.",
        "{business_name} started with a simple idea: {industry} should be fun and easy.",
    ]
}

# Value proposition templates
VALUE_TEMPLATES = [
    "Our mission, {mission}, drives every decision we make.",
    "We wake up every day committed to {mission}.",
    "What sets us apart? Our unwavering dedication to {mission}.",
    "At our core, we exist to {mission}.",
]

# Founder story templates
FOUNDER_TEMPLATES = [
    "The story of {business_name} begins with {founder_story}. This experience shaped our vision and purpose.",
    "Our founder's journey: {founder_story}. From this moment, {business_name} was born.",
    "{founder_story} - This is the spark that ignited {business_name}'s mission.",
    "Behind {business_name} is a story of determination: {founder_story}",
]

# Closing templates
CLOSING_TEMPLATES = {
    "professional": [
        "Join us in shaping the future of {industry}. Together, we'll achieve excellence.",
        "Partner with {business_name} and experience the difference that expertise makes.",
    ],
    "bold": [
        "Ready to disrupt {industry}? Let's make it happen together.",
        "Join the revolution. Join {business_name}.",
    ],
    "luxury": [
        "Elevate your {industry} experience. Welcome to {business_name}.",
        "Discover what exclusive {industry} truly means with {business_name}.",
    ],
    "friendly": [
        "We can't wait to work with you! Let's create something amazing together.",
        "Join the {business_name} family and let's make {industry} better, together!",
    ]
}

# Elevator pitch templates
PITCH_TEMPLATES = [
    "{business_name} helps {industry} professionals achieve {mission} through innovative solutions.",
    "We're {business_name}: making {mission} a reality for {industry}.",
    "{business_name} - Where {industry} meets {mission}. Simple. Effective. Transformative.",
]

# About section templates
ABOUT_TEMPLATES = [
    """About {business_name}

{business_name} is a leading {industry} company dedicated to {mission}. Founded with passion and driven by purpose, we serve clients who demand excellence.

What We Do:
• Transform {industry} through innovation
• Deliver measurable results
• Build lasting partnerships

Our Promise:
Every interaction with {business_name} reflects our commitment to quality, integrity, and your success.""",
]

# ==================== MODELS ====================
class GenerateRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=100)
    mission: str = Field(..., min_length=10, max_length=300)
    founder_story: str = Field(..., min_length=20, max_length=500)
    industry: str
    tone: str = Field(default="professional")

class GenerateResponse(BaseModel):
    success: bool
    brand_story: str
    elevator_pitch: str
    about_section: str
    credits_used: int
    generation_time_ms: int

# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    return {
        "industries": INDUSTRIES,
        "tones": TONES,
        "credit_cost": 18,
        "max_mission_length": 300,
        "max_founder_story_length": 500
    }

@router.post("/generate", response_model=GenerateResponse)
async def generate_brand_story(request: GenerateRequest, user: dict = Depends(get_current_user)):
    start_time = time.time()
    
    # Copyright check
    all_text = f"{request.business_name} {request.mission} {request.founder_story}"
    if check_copyright(all_text):
        raise HTTPException(status_code=400, detail="Input contains blocked content. Please avoid copyrighted or trademarked terms.")
    
    # Check credits
    if user.get("credits", 0) < 18:
        raise HTTPException(status_code=402, detail="Insufficient credits. 18 credits required.")
    
    # Deduct credits BEFORE generation
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -18}}
    )
    
    try:
        tone = request.tone if request.tone in TONES else "professional"
        
        # Build brand story
        opening = random.choice(OPENING_TEMPLATES.get(tone, OPENING_TEMPLATES["professional"]))
        opening = opening.format(business_name=request.business_name, industry=request.industry)
        
        value = random.choice(VALUE_TEMPLATES)
        value = value.format(mission=request.mission)
        
        founder = random.choice(FOUNDER_TEMPLATES)
        founder = founder.format(business_name=request.business_name, founder_story=request.founder_story)
        
        closing = random.choice(CLOSING_TEMPLATES.get(tone, CLOSING_TEMPLATES["professional"]))
        closing = closing.format(business_name=request.business_name, industry=request.industry)
        
        brand_story = f"{opening}\n\n{value}\n\n{founder}\n\n{closing}"
        
        # Build elevator pitch
        pitch = random.choice(PITCH_TEMPLATES)
        pitch = pitch.format(business_name=request.business_name, industry=request.industry, mission=request.mission)
        
        # Build about section
        about = random.choice(ABOUT_TEMPLATES)
        about = about.format(business_name=request.business_name, industry=request.industry, mission=request.mission)
        
        # Track analytics
        await db.template_analytics.insert_one({
            "feature": "brand_story_builder",
            "user_id": str(user["id"]),
            "industry": request.industry,
            "tone": tone,
            "created_at": datetime.now(timezone.utc)
        })
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return GenerateResponse(
            success=True,
            brand_story=brand_story,
            elevator_pitch=pitch,
            about_section=about,
            credits_used=18,
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        # Refund on error
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"credits": 18}}
        )
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/templates")
async def get_templates(admin: dict = Depends(get_admin_user)):
    templates = await db.brand_story_templates.find({}).to_list(100)
    for t in templates:
        t["id"] = str(t.pop("_id"))
    return {"templates": templates}

@router.post("/admin/templates")
async def create_template(data: dict, admin: dict = Depends(get_admin_user)):
    template = {
        "type": data.get("type", "opening"),
        "tone": data.get("tone", "professional"),
        "template": data.get("template"),
        "active": True,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.brand_story_templates.insert_one(template)
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/admin/templates/{template_id}")
async def delete_template(template_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.brand_story_templates.delete_one({"_id": ObjectId(template_id)})
    return {"success": result.deleted_count > 0}
