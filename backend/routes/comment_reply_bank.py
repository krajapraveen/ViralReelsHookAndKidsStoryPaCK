"""
AI Comment Reply Bank
Template-based comment reply generator with zero AI dependencies.
"""

import random
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared import get_current_user, get_admin_user, db

logger = logging.getLogger("creatorstudio")
router = APIRouter(prefix="/comment-reply-bank", tags=["Comment Reply Bank"])
limiter = Limiter(key_func=get_remote_address)

# Pricing
SINGLE_REPLY_COST = 5
FULL_PACK_COST = 15
DOWNLOAD_COST = 1

# =============================================================================
# BLOCKED KEYWORDS (COPYRIGHT SAFETY)
# =============================================================================

BLOCKED_KEYWORDS = [
    "marvel", "disney", "nike", "apple", "tesla", "netflix",
    "spiderman", "spider-man", "batman", "superman", "harry potter",
    "pokemon", "pikachu", "mickey mouse", "coca-cola", "pepsi",
    "google", "facebook", "meta", "amazon", "microsoft",
    "taylor swift", "beyonce", "kardashian", "elon musk",
    "mcdonald", "starbucks", "gucci", "louis vuitton", "chanel",
    "avengers", "iron man", "hulk", "thor", "captain america",
    "naruto", "goku", "dragon ball", "one piece", "fortnite"
]

NEGATIVE_CONTENT = [
    "hate", "kill", "die", "death", "violence", "racist", "sexist",
    "explicit", "porn", "nude", "drugs", "weapon", "gun", "bomb"
]


def check_blocked_content(text: str) -> tuple[bool, str]:
    """Check for blocked/copyright content"""
    text_lower = text.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword in text_lower:
            return False, f"Brand-based or copyrighted content detected: '{keyword}'"
    
    for keyword in NEGATIVE_CONTENT:
        if keyword in text_lower:
            return False, f"Inappropriate content detected"
    
    return True, ""


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class GenerateRepliesRequest(BaseModel):
    comment: str = Field(..., max_length=500, description="The comment to reply to")
    mode: str = Field(..., description="single or full_pack")


class IntentKeywordModel(BaseModel):
    intent_type: str
    keyword: str


class ReplyTemplateModel(BaseModel):
    intent_type: str
    reply_type: str  # funny, smart, sales, short
    template_text: str


# =============================================================================
# DEFAULT DATA
# =============================================================================

DEFAULT_INTENT_KEYWORDS = [
    # Praise
    {"intent_type": "praise", "keyword": "amazing"},
    {"intent_type": "praise", "keyword": "awesome"},
    {"intent_type": "praise", "keyword": "love"},
    {"intent_type": "praise", "keyword": "great"},
    {"intent_type": "praise", "keyword": "fantastic"},
    {"intent_type": "praise", "keyword": "incredible"},
    {"intent_type": "praise", "keyword": "perfect"},
    {"intent_type": "praise", "keyword": "beautiful"},
    {"intent_type": "praise", "keyword": "inspiring"},
    {"intent_type": "praise", "keyword": "helpful"},
    {"intent_type": "praise", "keyword": "thank you"},
    {"intent_type": "praise", "keyword": "thanks"},
    {"intent_type": "praise", "keyword": "best"},
    {"intent_type": "praise", "keyword": "wow"},
    
    # Question
    {"intent_type": "question", "keyword": "how"},
    {"intent_type": "question", "keyword": "what"},
    {"intent_type": "question", "keyword": "when"},
    {"intent_type": "question", "keyword": "where"},
    {"intent_type": "question", "keyword": "why"},
    {"intent_type": "question", "keyword": "can you"},
    {"intent_type": "question", "keyword": "could you"},
    {"intent_type": "question", "keyword": "please explain"},
    {"intent_type": "question", "keyword": "tell me"},
    {"intent_type": "question", "keyword": "?"},
    
    # Objection
    {"intent_type": "objection", "keyword": "but"},
    {"intent_type": "objection", "keyword": "however"},
    {"intent_type": "objection", "keyword": "disagree"},
    {"intent_type": "objection", "keyword": "don't think"},
    {"intent_type": "objection", "keyword": "not sure"},
    {"intent_type": "objection", "keyword": "doubt"},
    {"intent_type": "objection", "keyword": "expensive"},
    {"intent_type": "objection", "keyword": "too much"},
    
    # Negative/Hate
    {"intent_type": "negative", "keyword": "hate"},
    {"intent_type": "negative", "keyword": "worst"},
    {"intent_type": "negative", "keyword": "terrible"},
    {"intent_type": "negative", "keyword": "awful"},
    {"intent_type": "negative", "keyword": "trash"},
    {"intent_type": "negative", "keyword": "waste"},
    {"intent_type": "negative", "keyword": "scam"},
    {"intent_type": "negative", "keyword": "fake"},
    
    # Pricing
    {"intent_type": "pricing", "keyword": "price"},
    {"intent_type": "pricing", "keyword": "cost"},
    {"intent_type": "pricing", "keyword": "how much"},
    {"intent_type": "pricing", "keyword": "discount"},
    {"intent_type": "pricing", "keyword": "offer"},
    {"intent_type": "pricing", "keyword": "deal"},
    {"intent_type": "pricing", "keyword": "free"},
    
    # Collaboration
    {"intent_type": "collaboration", "keyword": "collab"},
    {"intent_type": "collaboration", "keyword": "collaborate"},
    {"intent_type": "collaboration", "keyword": "partner"},
    {"intent_type": "collaboration", "keyword": "work together"},
    {"intent_type": "collaboration", "keyword": "dm me"},
    {"intent_type": "collaboration", "keyword": "let's connect"},
]

DEFAULT_REPLY_TEMPLATES = [
    # PRAISE - Funny
    {"intent_type": "praise", "reply_type": "funny", "template_text": "Stop it, you're making me blush! {emoji} Thanks for the love!"},
    {"intent_type": "praise", "reply_type": "funny", "template_text": "My ego just grew 3 sizes reading this {emoji} Thank you!"},
    {"intent_type": "praise", "reply_type": "funny", "template_text": "You just made my whole week! {emoji} Now I need to go celebrate!"},
    
    # PRAISE - Smart
    {"intent_type": "praise", "reply_type": "smart", "template_text": "Thank you so much! Your support means everything to this journey {emoji}"},
    {"intent_type": "praise", "reply_type": "smart", "template_text": "I appreciate you taking the time to share this! It motivates me to create more {emoji}"},
    {"intent_type": "praise", "reply_type": "smart", "template_text": "Comments like this fuel my creativity. Thank you for being here {emoji}"},
    
    # PRAISE - Sales
    {"intent_type": "praise", "reply_type": "sales", "template_text": "Thank you! {emoji} If you loved this, you'll love what's coming next! {cta}"},
    {"intent_type": "praise", "reply_type": "sales", "template_text": "So glad you enjoyed it! Check out the link in bio for more exclusive content {emoji}"},
    {"intent_type": "praise", "reply_type": "sales", "template_text": "You're amazing! Want more? Join our community - link in bio {emoji}"},
    
    # PRAISE - Short
    {"intent_type": "praise", "reply_type": "short", "template_text": "Thank you! {emoji}"},
    {"intent_type": "praise", "reply_type": "short", "template_text": "You're the best! {emoji}"},
    {"intent_type": "praise", "reply_type": "short", "template_text": "Appreciate you! {emoji}"},
    
    # QUESTION - Funny
    {"intent_type": "question", "reply_type": "funny", "template_text": "Great question! I'd tell you but then I'd have to... just kidding! {emoji} Here's the thing..."},
    {"intent_type": "question", "reply_type": "funny", "template_text": "You ask the real questions! {emoji} Let me spill the tea..."},
    {"intent_type": "question", "reply_type": "funny", "template_text": "Ah, someone's curious! I love it {emoji} Short answer: lots of coffee and determination!"},
    
    # QUESTION - Smart
    {"intent_type": "question", "reply_type": "smart", "template_text": "Great question! I'll be covering this in detail soon. Follow along! {emoji}"},
    {"intent_type": "question", "reply_type": "smart", "template_text": "Love this question! It's all about consistency and the right strategy {emoji}"},
    {"intent_type": "question", "reply_type": "smart", "template_text": "Thanks for asking! I share tips like this regularly - stay tuned {emoji}"},
    
    # QUESTION - Sales
    {"intent_type": "question", "reply_type": "sales", "template_text": "Amazing question! I actually cover this in my guide - check the link in bio {emoji}"},
    {"intent_type": "question", "reply_type": "sales", "template_text": "Great Q! DM me 'INFO' and I'll share my complete process with you {emoji}"},
    {"intent_type": "question", "reply_type": "sales", "template_text": "This is exactly what I help people with! Link in bio for more {emoji}"},
    
    # QUESTION - Short
    {"intent_type": "question", "reply_type": "short", "template_text": "Great question! DM me {emoji}"},
    {"intent_type": "question", "reply_type": "short", "template_text": "Check bio for details! {emoji}"},
    {"intent_type": "question", "reply_type": "short", "template_text": "Coming soon! {emoji}"},
    
    # OBJECTION - Funny
    {"intent_type": "objection", "reply_type": "funny", "template_text": "I hear you! Plot twist: give it a try and let's chat after {emoji}"},
    {"intent_type": "objection", "reply_type": "funny", "template_text": "Valid point! But here's the secret sauce... {emoji}"},
    {"intent_type": "objection", "reply_type": "funny", "template_text": "I was skeptical too once! Look at me now {emoji}"},
    
    # OBJECTION - Smart
    {"intent_type": "objection", "reply_type": "smart", "template_text": "I appreciate your perspective! Let me share another angle..."},
    {"intent_type": "objection", "reply_type": "smart", "template_text": "That's a fair point. Here's what I've found works..."},
    {"intent_type": "objection", "reply_type": "smart", "template_text": "I understand the concern! Many felt the same before trying it {emoji}"},
    
    # OBJECTION - Sales
    {"intent_type": "objection", "reply_type": "sales", "template_text": "I get it! That's exactly why I offer a guarantee. Check bio for details {emoji}"},
    {"intent_type": "objection", "reply_type": "sales", "template_text": "Fair point! DM me and I'll show you real results {emoji}"},
    {"intent_type": "objection", "reply_type": "sales", "template_text": "I hear you! Want me to share some success stories? DM me {emoji}"},
    
    # OBJECTION - Short
    {"intent_type": "objection", "reply_type": "short", "template_text": "Fair point! Let's chat {emoji}"},
    {"intent_type": "objection", "reply_type": "short", "template_text": "I hear you! DM me {emoji}"},
    {"intent_type": "objection", "reply_type": "short", "template_text": "Give it a try! {emoji}"},
    
    # NEGATIVE - Funny
    {"intent_type": "negative", "reply_type": "funny", "template_text": "Thanks for the feedback! Here's a virtual cookie while you wait for better content {emoji}"},
    {"intent_type": "negative", "reply_type": "funny", "template_text": "Noted! I'll add 'make this person smile' to my to-do list {emoji}"},
    {"intent_type": "negative", "reply_type": "funny", "template_text": "Ouch! But hey, at least you stopped by {emoji}"},
    
    # NEGATIVE - Smart
    {"intent_type": "negative", "reply_type": "smart", "template_text": "I appreciate the honest feedback. What would you like to see improved?"},
    {"intent_type": "negative", "reply_type": "smart", "template_text": "Thanks for sharing. I'm always looking to grow and improve {emoji}"},
    {"intent_type": "negative", "reply_type": "smart", "template_text": "I hear you. Not everything resonates with everyone, and that's okay {emoji}"},
    
    # NEGATIVE - Sales
    {"intent_type": "negative", "reply_type": "sales", "template_text": "Sorry to hear that! Give us another chance - something better coming soon {emoji}"},
    {"intent_type": "negative", "reply_type": "sales", "template_text": "I appreciate the feedback! Maybe check out my other content? {emoji}"},
    {"intent_type": "negative", "reply_type": "sales", "template_text": "Fair enough! Stick around - I think you'll like what's next {emoji}"},
    
    # NEGATIVE - Short
    {"intent_type": "negative", "reply_type": "short", "template_text": "Thanks for the feedback! {emoji}"},
    {"intent_type": "negative", "reply_type": "short", "template_text": "Noted! {emoji}"},
    {"intent_type": "negative", "reply_type": "short", "template_text": "I hear you! {emoji}"},
    
    # PRICING - Funny
    {"intent_type": "pricing", "reply_type": "funny", "template_text": "Ah, the million dollar question! {emoji} Check bio for all the deets!"},
    {"intent_type": "pricing", "reply_type": "funny", "template_text": "Less than a fancy coffee habit! {emoji} DM for details!"},
    {"intent_type": "pricing", "reply_type": "funny", "template_text": "Investment mode: ON {emoji} Link in bio for pricing!"},
    
    # PRICING - Smart
    {"intent_type": "pricing", "reply_type": "smart", "template_text": "Great question! All pricing details are in the link in bio {emoji}"},
    {"intent_type": "pricing", "reply_type": "smart", "template_text": "I have options for every budget! Check my bio for details {emoji}"},
    {"intent_type": "pricing", "reply_type": "smart", "template_text": "DM me and I'll send you the complete pricing guide {emoji}"},
    
    # PRICING - Sales
    {"intent_type": "pricing", "reply_type": "sales", "template_text": "Perfect timing! We have a special offer running. Check bio! {emoji}"},
    {"intent_type": "pricing", "reply_type": "sales", "template_text": "DM me 'PRICE' for exclusive pricing and bonus offers {emoji}"},
    {"intent_type": "pricing", "reply_type": "sales", "template_text": "Great timing to ask! Link in bio for current deals {emoji}"},
    
    # PRICING - Short
    {"intent_type": "pricing", "reply_type": "short", "template_text": "Check bio! {emoji}"},
    {"intent_type": "pricing", "reply_type": "short", "template_text": "DM for pricing! {emoji}"},
    {"intent_type": "pricing", "reply_type": "short", "template_text": "Link in bio! {emoji}"},
    
    # COLLABORATION - Funny
    {"intent_type": "collaboration", "reply_type": "funny", "template_text": "A collab? Say less! {emoji} Slide into my DMs!"},
    {"intent_type": "collaboration", "reply_type": "funny", "template_text": "You had me at collab! {emoji} Let's make magic!"},
    {"intent_type": "collaboration", "reply_type": "funny", "template_text": "Collab requests are my love language {emoji} DM me!"},
    
    # COLLABORATION - Smart
    {"intent_type": "collaboration", "reply_type": "smart", "template_text": "Love connecting with creators! DM me with your ideas {emoji}"},
    {"intent_type": "collaboration", "reply_type": "smart", "template_text": "Always open to collaborations that bring value! Let's chat {emoji}"},
    {"intent_type": "collaboration", "reply_type": "smart", "template_text": "Sounds interesting! Send me a DM with more details {emoji}"},
    
    # COLLABORATION - Sales
    {"intent_type": "collaboration", "reply_type": "sales", "template_text": "Love this! DM me your proposal and let's explore {emoji}"},
    {"intent_type": "collaboration", "reply_type": "sales", "template_text": "Exciting! Check my bio for collaboration inquiries {emoji}"},
    {"intent_type": "collaboration", "reply_type": "sales", "template_text": "Let's create something amazing! DM me your pitch {emoji}"},
    
    # COLLABORATION - Short
    {"intent_type": "collaboration", "reply_type": "short", "template_text": "Love it! DM me {emoji}"},
    {"intent_type": "collaboration", "reply_type": "short", "template_text": "Let's do it! {emoji}"},
    {"intent_type": "collaboration", "reply_type": "short", "template_text": "Slide into DMs! {emoji}"},
    
    # GENERIC - Funny
    {"intent_type": "generic", "reply_type": "funny", "template_text": "Thanks for stopping by! You're officially my favorite comment of the day {emoji}"},
    {"intent_type": "generic", "reply_type": "funny", "template_text": "Your presence is appreciated! {emoji} Thanks for being here!"},
    {"intent_type": "generic", "reply_type": "funny", "template_text": "This comment just made my notification worth checking {emoji}"},
    
    # GENERIC - Smart
    {"intent_type": "generic", "reply_type": "smart", "template_text": "Thanks for engaging! I love connecting with my community {emoji}"},
    {"intent_type": "generic", "reply_type": "smart", "template_text": "Appreciate you being here! More great content coming {emoji}"},
    {"intent_type": "generic", "reply_type": "smart", "template_text": "Thank you! Your support means everything {emoji}"},
    
    # GENERIC - Sales
    {"intent_type": "generic", "reply_type": "sales", "template_text": "Thanks! Want more content like this? Follow along! {emoji}"},
    {"intent_type": "generic", "reply_type": "sales", "template_text": "Glad you're here! Check bio for more goodies {emoji}"},
    {"intent_type": "generic", "reply_type": "sales", "template_text": "Thank you! Don't miss what's coming next - turn on notifications! {emoji}"},
    
    # GENERIC - Short
    {"intent_type": "generic", "reply_type": "short", "template_text": "Thank you! {emoji}"},
    {"intent_type": "generic", "reply_type": "short", "template_text": "Appreciate it! {emoji}"},
    {"intent_type": "generic", "reply_type": "short", "template_text": "{emoji}{emoji}{emoji}"},
]

EMOJIS = {
    "praise": ["❤️", "🙏", "✨", "💕", "🥰", "💫"],
    "question": ["💡", "📚", "🎯", "✨", "👀", "🔥"],
    "objection": ["🤝", "💪", "✨", "🙏", "💡", "👊"],
    "negative": ["🙏", "💫", "✨", "🤍", "💭", "🌟"],
    "pricing": ["💰", "🔥", "✨", "💫", "🎯", "💎"],
    "collaboration": ["🤝", "✨", "🔥", "💫", "🚀", "💪"],
    "generic": ["❤️", "✨", "🙏", "💫", "🔥", "💕"]
}

CTAS = [
    "Follow for more!",
    "Link in bio!",
    "Stay tuned!",
    "Don't miss out!",
    "More coming soon!"
]


# =============================================================================
# DATABASE SEEDING
# =============================================================================

async def seed_comment_reply_data():
    """Seed default data if collections are empty"""
    
    # Seed intent keywords
    if await db.comment_intent_keywords.count_documents({}) == 0:
        import uuid
        for item in DEFAULT_INTENT_KEYWORDS:
            item["id"] = str(uuid.uuid4())
            item["active"] = True
            item["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.comment_intent_keywords.insert_many(DEFAULT_INTENT_KEYWORDS)
        logger.info(f"Seeded {len(DEFAULT_INTENT_KEYWORDS)} intent keywords")
    
    # Seed reply templates
    if await db.reply_templates.count_documents({}) == 0:
        import uuid
        for item in DEFAULT_REPLY_TEMPLATES:
            item["id"] = str(uuid.uuid4())
            item["active"] = True
            item["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.reply_templates.insert_many(DEFAULT_REPLY_TEMPLATES)
        logger.info(f"Seeded {len(DEFAULT_REPLY_TEMPLATES)} reply templates")


# =============================================================================
# INTENT DETECTION
# =============================================================================

async def detect_intent(comment: str) -> str:
    """Detect comment intent using keyword matching"""
    comment_lower = comment.lower()
    
    # Fetch keywords
    keywords = await db.comment_intent_keywords.find({"active": True}).to_list(length=500)
    
    # Priority order for matching
    intent_priority = ["pricing", "collaboration", "question", "negative", "objection", "praise"]
    
    intent_scores = {intent: 0 for intent in intent_priority}
    intent_scores["generic"] = 0
    
    for kw in keywords:
        if kw["keyword"].lower() in comment_lower:
            intent_scores[kw["intent_type"]] = intent_scores.get(kw["intent_type"], 0) + 1
    
    # Get highest scoring intent
    max_score = 0
    detected_intent = "generic"
    
    for intent in intent_priority:
        if intent_scores.get(intent, 0) > max_score:
            max_score = intent_scores[intent]
            detected_intent = intent
    
    return detected_intent


def fill_template(template: str, intent: str) -> str:
    """Fill template placeholders"""
    emoji = random.choice(EMOJIS.get(intent, EMOJIS["generic"]))
    cta = random.choice(CTAS)
    
    result = template.replace("{emoji}", emoji)
    result = result.replace("{cta}", cta)
    result = result.replace("{name}", "friend")
    
    return result


# =============================================================================
# GENERATION ENGINE
# =============================================================================

async def generate_replies(comment: str, mode: str) -> Dict[str, Any]:
    """Generate replies based on comment and mode"""
    
    # Detect intent
    intent = await detect_intent(comment)
    
    # Fetch templates for this intent
    templates = await db.reply_templates.find({
        "intent_type": intent,
        "active": True
    }).to_list(length=100)
    
    if not templates:
        # Fallback to generic
        templates = await db.reply_templates.find({
            "intent_type": "generic",
            "active": True
        }).to_list(length=100)
    
    # Group by reply_type
    by_type = {"funny": [], "smart": [], "sales": [], "short": []}
    for t in templates:
        reply_type = t.get("reply_type", "short")
        if reply_type in by_type:
            by_type[reply_type].append(t)
    
    replies = []
    
    if mode == "single":
        # 4 replies - one of each type
        for reply_type in ["funny", "smart", "sales", "short"]:
            type_templates = by_type.get(reply_type, [])
            if type_templates:
                template = random.choice(type_templates)
                reply_text = fill_template(template["template_text"], intent)
                replies.append({
                    "type": reply_type,
                    "reply": reply_text
                })
            else:
                # Fallback
                replies.append({
                    "type": reply_type,
                    "reply": fill_template("Thank you! {emoji}", intent)
                })
    
    else:  # full_pack
        # 12 replies - 3 of each type
        for reply_type in ["funny", "smart", "sales", "short"]:
            type_templates = by_type.get(reply_type, [])
            
            if len(type_templates) >= 3:
                selected = random.sample(type_templates, 3)
            else:
                selected = type_templates * 3  # Repeat if not enough
                selected = selected[:3]
            
            for template in selected:
                reply_text = fill_template(template["template_text"], intent)
                replies.append({
                    "type": reply_type,
                    "reply": reply_text
                })
    
    return {
        "intent": intent,
        "replies": replies
    }


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/config")
async def get_config():
    """Get configuration for the comment reply bank"""
    await seed_comment_reply_data()
    
    return {
        "modes": [
            {"id": "single", "name": "Single Reply Set", "credits": SINGLE_REPLY_COST, "replies": 4},
            {"id": "full_pack", "name": "Full Reply Pack", "credits": FULL_PACK_COST, "replies": 12}
        ],
        "replyTypes": ["funny", "smart", "sales", "short"],
        "maxCommentLength": 500,
        "downloadCost": DOWNLOAD_COST
    }


@router.post("/generate")
@limiter.limit("30/minute")
async def generate_comment_replies(
    request: Request,
    data: GenerateRepliesRequest,
    user: dict = Depends(get_current_user)
):
    """Generate replies for a comment"""
    
    # Validate comment
    if not data.comment or len(data.comment.strip()) < 3:
        raise HTTPException(status_code=400, detail="Comment is required (min 3 characters)")
    
    if len(data.comment) > 500:
        raise HTTPException(status_code=400, detail="Comment too long (max 500 characters)")
    
    # Check blocked content
    is_safe, error_msg = check_blocked_content(data.comment)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Validate mode
    if data.mode not in ["single", "full_pack"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'single' or 'full_pack'")
    
    # Determine cost
    cost = SINGLE_REPLY_COST if data.mode == "single" else FULL_PACK_COST
    
    # Check credits
    user_id = user.get("id", user.get("_id", ""))
    user_credits = user.get("credits", 0)
    
    wallet = await db.wallets.find_one({"userId": str(user_id)})
    wallet_credits = wallet.get("balanceCredits", 0) if wallet else 0
    current_credits = max(user_credits, wallet_credits)
    
    if current_credits < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {cost}, Available: {current_credits}"
        )
    
    # Deduct credits
    await db.wallets.update_one(
        {"userId": str(user_id)},
        {"$inc": {"balanceCredits": -cost, "availableCredits": -cost}},
        upsert=True
    )
    
    # Also update user credits
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"credits": -cost}}
    )
    
    # Record transaction
    await db.credit_transactions.insert_one({
        "userId": str(user_id),
        "type": "debit",
        "amount": cost,
        "reason": f"Comment Reply Bank ({data.mode})",
        "feature": "comment-reply-bank",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    try:
        # Generate replies
        result = await generate_replies(data.comment, data.mode)
        
        # Get updated balance
        updated_wallet = await db.wallets.find_one({"userId": str(user_id)})
        remaining = updated_wallet.get("balanceCredits", 0) if updated_wallet else max(0, current_credits - cost)
        
        # Log generation
        await db.reply_generations.insert_one({
            "userId": str(user_id),
            "comment": data.comment[:100],
            "mode": data.mode,
            "intent": result["intent"],
            "replies_count": len(result["replies"]),
            "credits_used": cost,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "intent_detected": result["intent"],
            "replies": result["replies"],
            "credits_used": cost,
            "remaining_credits": remaining
        }
        
    except Exception as e:
        # Refund on error
        await db.wallets.update_one(
            {"userId": str(user_id)},
            {"$inc": {"balanceCredits": cost, "availableCredits": cost}}
        )
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"credits": cost}}
        )
        logger.error(f"Reply generation error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed. Credits refunded.")


@router.post("/download")
async def download_replies(
    replies: List[Dict[str, str]],
    user: dict = Depends(get_current_user)
):
    """Download replies as text"""
    user_id = user.get("id", user.get("_id", ""))
    
    # Check credits
    user_credits = user.get("credits", 0)
    wallet = await db.wallets.find_one({"userId": str(user_id)})
    wallet_credits = wallet.get("balanceCredits", 0) if wallet else 0
    
    if max(user_credits, wallet_credits) < DOWNLOAD_COST:
        raise HTTPException(status_code=402, detail="Insufficient credits for download")
    
    # Deduct credit
    await db.wallets.update_one(
        {"userId": str(user_id)},
        {"$inc": {"balanceCredits": -DOWNLOAD_COST}}
    )
    
    # Format content
    content = "Comment Reply Bank - Your Replies\n"
    content += "=" * 40 + "\n\n"
    
    for i, reply in enumerate(replies, 1):
        content += f"{reply.get('type', 'Reply').upper()} REPLY:\n"
        content += f"{reply.get('reply', '')}\n\n"
    
    content += "\nGenerated by CreatorStudio AI\n"
    
    return {"success": True, "content": content, "filename": "comment_replies.txt"}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/keywords")
async def get_admin_keywords(admin: dict = Depends(get_admin_user)):
    """Get all intent keywords"""
    keywords = await db.comment_intent_keywords.find({}, {"_id": 0}).to_list(length=500)
    return {"keywords": keywords}


@router.post("/admin/keywords")
async def create_keyword(data: IntentKeywordModel, admin: dict = Depends(get_admin_user)):
    """Create a new intent keyword"""
    import uuid
    keyword_data = {
        "id": str(uuid.uuid4()),
        "intent_type": data.intent_type,
        "keyword": data.keyword.lower(),
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.comment_intent_keywords.insert_one(keyword_data)
    return {"success": True, "keyword": keyword_data}


@router.delete("/admin/keywords/{keyword_id}")
async def delete_keyword(keyword_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a keyword"""
    await db.comment_intent_keywords.delete_one({"id": keyword_id})
    return {"success": True}


@router.get("/admin/templates")
async def get_admin_templates(admin: dict = Depends(get_admin_user)):
    """Get all reply templates"""
    templates = await db.reply_templates.find({}, {"_id": 0}).to_list(length=500)
    return {"templates": templates}


@router.post("/admin/templates")
async def create_template(data: ReplyTemplateModel, admin: dict = Depends(get_admin_user)):
    """Create a new reply template"""
    import uuid
    template_data = {
        "id": str(uuid.uuid4()),
        "intent_type": data.intent_type,
        "reply_type": data.reply_type,
        "template_text": data.template_text,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.reply_templates.insert_one(template_data)
    return {"success": True, "template": template_data}


@router.delete("/admin/templates/{template_id}")
async def delete_template(template_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a template"""
    await db.reply_templates.delete_one({"id": template_id})
    return {"success": True}


@router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Get usage statistics"""
    total_generations = await db.reply_generations.count_documents({})
    total_keywords = await db.comment_intent_keywords.count_documents({})
    total_templates = await db.reply_templates.count_documents({})
    
    return {
        "total_generations": total_generations,
        "total_keywords": total_keywords,
        "total_templates": total_templates,
        "pricing": {
            "single": SINGLE_REPLY_COST,
            "full_pack": FULL_PACK_COST
        }
    }
