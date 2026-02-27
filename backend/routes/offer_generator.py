"""
Offer Generator (Money Tool)
Template-based, no AI, <200ms response
Price: 20 credits
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import time
from datetime import datetime, timezone
from bson import ObjectId

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/offer-generator", tags=["Offer Generator"])

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
TONES = ["bold", "premium", "direct"]

# Offer name templates
OFFER_NAME_TEMPLATES = [
    "The Ultimate {product} Blueprint",
    "{product} Mastery System",
    "The {product} Accelerator",
    "{product} Success Formula",
    "The Complete {product} Bundle",
    "{product} Pro Package",
    "The {product} Transformation Kit",
    "{product} Elite Program",
    "The Definitive {product} Guide",
    "{product} Fast-Track System"
]

# Hook templates by tone
HOOK_TEMPLATES = {
    "bold": [
        "Finally solve {problem} without the BS.",
        "Stop struggling with {problem}. This actually works.",
        "What if {problem} wasn't your fault?",
        "The {problem} solution nobody talks about.",
        "Discover how {audience} are beating {problem}.",
    ],
    "premium": [
        "An exclusive solution for {audience} ready to overcome {problem}.",
        "For discerning {audience} who refuse to settle on {problem}.",
        "The sophisticated approach to solving {problem}.",
        "Elevate beyond {problem} with proven methodology.",
        "Where {audience} excellence meets {problem} solutions.",
    ],
    "direct": [
        "Solve {problem} in weeks, not years.",
        "Here's exactly how to fix {problem}.",
        "{audience}: End {problem} today.",
        "The fastest path from {problem} to results.",
        "No fluff. Just {problem} solutions that work.",
    ]
}

# Bonus templates
BONUS_TEMPLATES = [
    {"name": "Quick-Start Checklist", "value": "$47", "desc": "Step-by-step action plan to get started immediately"},
    {"name": "Swipe File Collection", "value": "$97", "desc": "Proven templates and examples you can customize"},
    {"name": "Case Study Bundle", "value": "$67", "desc": "Real success stories with detailed breakdowns"},
    {"name": "Resource Toolkit", "value": "$37", "desc": "Essential tools and resources for implementation"},
    {"name": "Implementation Guide", "value": "$57", "desc": "Detailed walkthrough for best results"},
    {"name": "FAQ & Troubleshooting", "value": "$27", "desc": "Common questions answered + problem solutions"},
    {"name": "Community Access", "value": "$97/mo", "desc": "Connect with others on the same journey"},
    {"name": "Monthly Updates", "value": "$47/mo", "desc": "Fresh content and strategies delivered monthly"},
]

# Guarantee templates
GUARANTEE_TEMPLATES = [
    "100% Money-Back Guarantee: If you don't see results in 30 days, get a full refund. No questions asked.",
    "Risk-Free Promise: Try it for 60 days. Love it or your money back.",
    "Double-Down Guarantee: If this doesn't work for you, we'll refund you AND give you $50 for your time.",
    "Results Guarantee: Follow the system, see results, or get your investment back.",
    "No-Risk Trial: Test-drive for 14 days. Not for you? Full refund, zero hassle.",
]

# Pricing angle templates
PRICING_ANGLE_TEMPLATES = {
    "value_stack": [
        "Total Value: ${total_value}\nYour Investment Today: Just ${price}\n(That's {savings}% OFF)",
        "Everything above is worth ${total_value}.\nBut you won't pay that. Not even close.\nToday: ${price}",
    ],
    "comparison": [
        "Others charge ${expensive} for less. You get more for ${price}.",
        "Skip the ${expensive} alternatives. Get better results for ${price}.",
    ],
    "roi": [
        "For less than ${daily} per day, solve {problem} forever.",
        "One investment of ${price}. Lifetime of results.",
    ]
}

# ==================== MODELS ====================
class GenerateRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=100)
    target_audience: str = Field(..., min_length=1, max_length=100)
    main_problem: str = Field(..., min_length=1, max_length=200)
    price_range: Optional[str] = None
    tone: str = Field(default="bold")

class Bonus(BaseModel):
    name: str
    value: str
    description: str

class GenerateResponse(BaseModel):
    success: bool
    offer_name: str
    offer_hook: str
    bonuses: List[Bonus]
    guarantee: str
    pricing_angle: str
    credits_used: int
    generation_time_ms: int

# ==================== ENDPOINTS ====================
@router.get("/config")
async def get_config():
    return {
        "tones": TONES,
        "credit_cost": 20,
        "bonus_count": 3,
        "max_product_length": 100,
        "max_problem_length": 200
    }

@router.post("/generate", response_model=GenerateResponse)
async def generate_offer(request: GenerateRequest, user: dict = Depends(get_current_user)):
    start_time = time.time()
    
    # Copyright check
    all_text = f"{request.product_name} {request.target_audience} {request.main_problem}"
    if check_copyright(all_text):
        raise HTTPException(status_code=400, detail="Input contains blocked content. Please avoid copyrighted or trademarked terms.")
    
    # Check credits
    if user.get("credits", 0) < 20:
        raise HTTPException(status_code=402, detail="Insufficient credits. 20 credits required.")
    
    # Deduct credits BEFORE generation
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$inc": {"credits": -20}}
    )
    
    try:
        tone = request.tone if request.tone in TONES else "bold"
        
        # Generate offer name
        offer_name = random.choice(OFFER_NAME_TEMPLATES)
        offer_name = offer_name.format(product=request.product_name)
        
        # Generate hook
        hook = random.choice(HOOK_TEMPLATES.get(tone, HOOK_TEMPLATES["bold"]))
        hook = hook.format(
            problem=request.main_problem,
            audience=request.target_audience,
            product=request.product_name
        )
        
        # Generate 3 bonuses
        selected_bonuses = random.sample(BONUS_TEMPLATES, 3)
        bonuses = [
            Bonus(name=b["name"], value=b["value"], description=b["desc"])
            for b in selected_bonuses
        ]
        
        # Generate guarantee
        guarantee = random.choice(GUARANTEE_TEMPLATES)
        
        # Generate pricing angle
        price = request.price_range or "97"
        try:
            price_num = int(''.join(filter(str.isdigit, price))) or 97
        except:
            price_num = 97
            
        total_value = price_num * 5
        daily = round(price_num / 365, 2)
        savings = 80
        
        pricing_type = random.choice(["value_stack", "comparison", "roi"])
        pricing_angle = random.choice(PRICING_ANGLE_TEMPLATES[pricing_type])
        pricing_angle = pricing_angle.format(
            total_value=total_value,
            price=price_num,
            savings=savings,
            expensive=total_value,
            daily=daily,
            problem=request.main_problem
        )
        
        # Track analytics
        await db.template_analytics.insert_one({
            "feature": "offer_generator",
            "user_id": str(user["_id"]),
            "tone": tone,
            "created_at": datetime.now(timezone.utc)
        })
        
        generation_time = int((time.time() - start_time) * 1000)
        
        return GenerateResponse(
            success=True,
            offer_name=offer_name,
            offer_hook=hook,
            bonuses=bonuses,
            guarantee=guarantee,
            pricing_angle=pricing_angle,
            credits_used=20,
            generation_time_ms=generation_time
        )
        
    except Exception as e:
        # Refund on error
        await db.users.update_one(
            {"_id": ObjectId(user["_id"])},
            {"$inc": {"credits": 20}}
        )
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# ==================== ADMIN ENDPOINTS ====================
@router.get("/admin/templates")
async def get_templates(admin: dict = Depends(get_admin_user)):
    templates = await db.offer_templates.find({}).to_list(100)
    for t in templates:
        t["id"] = str(t.pop("_id"))
    return {"templates": templates}

@router.post("/admin/templates")
async def create_template(data: dict, admin: dict = Depends(get_admin_user)):
    template = {
        "type": data.get("type", "offer_name"),
        "tone": data.get("tone"),
        "template": data.get("template"),
        "active": True,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.offer_templates.insert_one(template)
    return {"success": True, "id": str(result.inserted_id)}

@router.delete("/admin/templates/{template_id}")
async def delete_template(template_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.offer_templates.delete_one({"_id": ObjectId(template_id)})
    return {"success": result.deleted_count > 0}
