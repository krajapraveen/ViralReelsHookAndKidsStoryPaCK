"""
Creator Tools Routes - Content Calendar, Carousel, Hashtags, Thumbnails, etc.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import random
import json

router = APIRouter(prefix="/creator-tools", tags=["Creator Tools"])

# Import auth and db from main server context (will be passed during include)
from server import get_current_user, get_admin_user, db

# =============================================================================
# DATA TEMPLATES - No AI Required
# =============================================================================

# Hashtag Banks by Niche
HASHTAG_BANKS = {
    "luxury": {
        "low_competition": ["#luxurylifestyleblogger", "#luxurydaily", "#luxuryvibes", "#luxurycontent", "#luxurymindset", "#highendlife", "#luxurygoals", "#luxelife", "#premiumcontent", "#elitelifestyle"],
        "medium_competition": ["#luxurylife", "#luxuryliving", "#luxuryhomes", "#luxurycars", "#billionairelifestyle", "#millionairemindset", "#wealthmindset", "#successmindset", "#richlife", "#abundancemindset"],
        "trending": ["#luxury", "#lifestyle", "#rich", "#success", "#motivation", "#wealth", "#entrepreneur", "#millionaire", "#goals", "#dream"]
    },
    "relationship": {
        "low_competition": ["#relationshipcoach", "#datingadvice", "#relationshipgoals101", "#couplegoalsaf", "#lovelessons", "#relationshiptips101", "#healthyrelationshiptips", "#datingtipsforwomen", "#relationshipwisdom", "#coupleadvice"],
        "medium_competition": ["#relationshipquotes", "#couplesofinstagram", "#loveadvice", "#datinglife", "#relationshipmatters", "#lovetips", "#romancegoals", "#partnerlove", "#relationshipbuilding", "#datingcoach"],
        "trending": ["#relationship", "#love", "#couple", "#dating", "#relationshipgoals", "#couplegoals", "#lovequotes", "#romance", "#together", "#soulmate"]
    },
    "health": {
        "low_competition": ["#healthcoachtips", "#wellnesswarrior", "#healthylifestyleblogger", "#fitnesstransformation", "#nutritionfacts101", "#healthjourney2024", "#wellnesstips101", "#holistichealthcoach", "#cleaneatinglifestyle", "#mindfulhealth"],
        "medium_competition": ["#healthylifestyle", "#fitnessmotivation", "#cleaneating", "#healthyliving", "#nutritioncoach", "#wellnessjourney", "#fitnessjourney", "#healthtips", "#workoutmotivation", "#mealprep"],
        "trending": ["#health", "#fitness", "#healthy", "#workout", "#nutrition", "#wellness", "#gym", "#fit", "#motivation", "#exercise"]
    },
    "motivation": {
        "low_competition": ["#motivationmondays", "#dailymotivational", "#successquotes101", "#motivationalspeaker", "#inspirationalquotes_", "#mindsetcoaching", "#positivevibesonly✨", "#motivateyourself", "#inspirationdaily_", "#growthmindsetquotes"],
        "medium_competition": ["#motivationalquotes", "#successmindset", "#inspirationalquotes", "#motivationspeaker", "#mindsetmatters", "#positivemindset", "#selfimprovement", "#personaldevelopment", "#goalgetter", "#dreambig"],
        "trending": ["#motivation", "#success", "#inspiration", "#mindset", "#goals", "#believe", "#dreams", "#hustle", "#grind", "#nevergiveup"]
    },
    "parenting": {
        "low_competition": ["#parentingtipsandtricks", "#momlifehacks", "#dadlifestyle", "#toddlermomlife", "#parentingwin", "#realparenting", "#momstruggles", "#parentinghacks101", "#dadgoals", "#raisingkids"],
        "medium_competition": ["#parentinglife", "#momlife", "#dadlife", "#parenthood", "#motherhood", "#fatherhood", "#familytime", "#kidsactivities", "#parentingtips", "#familyfirst"],
        "trending": ["#parenting", "#mom", "#dad", "#family", "#kids", "#children", "#baby", "#toddler", "#mommy", "#parent"]
    },
    "business": {
        "low_competition": ["#businesscoachtips", "#entrepreneurlifestyle", "#smallbusinessowner", "#startupfounder", "#businessgrowth101", "#sidehustleideas", "#onlinebusinesstips", "#digitalentrepreneur", "#businessstrategy101", "#freelancertips"],
        "medium_competition": ["#businessmindset", "#entrepreneurship", "#smallbusiness", "#startuplife", "#businessowner", "#onlinebusiness", "#digitalbusiness", "#businesstips", "#entrepreneurlife", "#businesscoach"],
        "trending": ["#business", "#entrepreneur", "#startup", "#money", "#success", "#marketing", "#branding", "#ceo", "#hustle", "#growth"]
    },
    "travel": {
        "low_competition": ["#travelcontentcreator", "#wanderlustlife", "#traveldiaries2024", "#solotraveler", "#travelphotography📷", "#budgettraveltips", "#travelreels", "#exploringtheworld", "#travelinspo2024", "#adventureseeker"],
        "medium_competition": ["#travelgram", "#travelblogger", "#travelphotography", "#traveltheworld", "#wanderlust", "#traveladdict", "#instatravel", "#travellife", "#traveler", "#adventure"],
        "trending": ["#travel", "#vacation", "#trip", "#explore", "#destination", "#holiday", "#tourism", "#journey", "#world", "#visiting"]
    },
    "food": {
        "low_competition": ["#foodbloggersofinstagram", "#homecooking101", "#foodphotographytips", "#recipeideas", "#healthyfoodrecipes", "#foodielife🍕", "#cookingreels", "#instafoodblogger", "#deliciousfood😋", "#foodstyling"],
        "medium_competition": ["#foodblogger", "#homecooking", "#foodphotography", "#recipeoftheday", "#healthyrecipes", "#foodlover", "#cookingathome", "#instafood", "#yummy", "#foodgasm"],
        "trending": ["#food", "#foodie", "#cooking", "#recipe", "#delicious", "#homemade", "#dinner", "#lunch", "#breakfast", "#tasty"]
    }
}

# Content Types for Calendar
CONTENT_TYPES = [
    "Storytime", "Myth-busting", "POV", "Luxury vibe", "Tutorial", 
    "Day in my life", "Get ready with me", "Behind the scenes", 
    "Before/After", "3 tips", "Unpopular opinion", "Hot take",
    "This vs That", "React to", "Duet style", "Voiceover story"
]

# Hook Templates by Niche
HOOK_TEMPLATES = {
    "luxury": [
        "This is what {price} gets you in {location}",
        "Rich people don't want you to know this",
        "I bought a {item} and here's what happened",
        "Living in a {price} apartment for a day",
        "The difference between rich and wealthy",
        "Why millionaires do this every morning",
        "Stop doing this if you want to be rich",
        "The luxury item that changed my life",
        "Inside a {price} {place}",
        "Rich habits that cost nothing"
    ],
    "relationship": [
        "If they do this, run",
        "Green flags you're ignoring",
        "This is why you're still single",
        "The truth about modern dating",
        "Stop texting them this",
        "Men secretly want this",
        "Women never tell you this",
        "The 3 second rule that works",
        "Why your ex keeps coming back",
        "If you've been hurt, watch this"
    ],
    "health": [
        "I lost {amount} in {time} doing this",
        "Stop eating this every morning",
        "The workout nobody talks about",
        "This changed my body in 30 days",
        "Doctors don't want you to know this",
        "The real reason you're not losing weight",
        "What I eat in a day to stay fit",
        "3 exercises that actually work",
        "The morning routine that transformed me",
        "Stop doing this at the gym"
    ],
    "motivation": [
        "This is your sign to start",
        "Remember why you started",
        "They laughed at me until...",
        "You're closer than you think",
        "Stop waiting for permission",
        "The mindset shift that changed everything",
        "You're not lazy, you're just...",
        "This is what discipline looks like",
        "Watch this when you want to give up",
        "Nobody is coming to save you"
    ],
    "parenting": [
        "Things I wish I knew before having kids",
        "What no one tells new parents",
        "My toddler taught me this",
        "Parenting hack that actually works",
        "Stop doing this with your kids",
        "The phrase that changed my parenting",
        "Gentle parenting in action",
        "When your kid says this, try this",
        "Morning routine with {number} kids",
        "How I get my kids to listen"
    ],
    "business": [
        "I made {amount} doing this",
        "The side hustle nobody talks about",
        "Stop trading time for money",
        "This business idea costs {amount} to start",
        "Why most businesses fail in year 1",
        "The email that got me {result}",
        "How I got my first client",
        "The pricing mistake killing your business",
        "What I'd do if I started over",
        "The tool that 10x'd my productivity"
    ],
    "general": [
        "Wait for it...",
        "I never knew this until now",
        "This changed everything",
        "Nobody is talking about this",
        "You need to see this",
        "I can't believe this works",
        "This is why you're stuck",
        "The truth no one tells you",
        "Watch until the end",
        "POV: You finally figure it out"
    ]
}

# CTA Templates
CTA_TEMPLATES = [
    "Follow for more {niche} tips",
    "Save this for later",
    "Share with someone who needs this",
    "Drop a 🔥 if you agree",
    "Comment '{word}' for the full guide",
    "Link in bio for more",
    "Follow for daily {niche} content",
    "Tag someone who needs to see this",
    "Double tap if this helped",
    "What should I post next?"
]

# Thumbnail Text Templates
THUMBNAIL_TEMPLATES = {
    "emotional": [
        "I CRIED 😢",
        "This BROKE me",
        "I can't believe...",
        "My heart 💔",
        "The TRUTH",
        "This HURT"
    ],
    "curiosity": [
        "Wait for it...",
        "You won't believe",
        "The SECRET",
        "Nobody knows this",
        "Hidden truth",
        "They hid this"
    ],
    "action": [
        "STOP doing this!",
        "Watch NOW",
        "TRY this today",
        "Don't miss this",
        "GAME CHANGER",
        "Life hack"
    ],
    "numbers": [
        "3 SECRETS",
        "5 mistakes",
        "10X your {topic}",
        "₹{amount} in {time}",
        "24 hours later",
        "Day {number}"
    ]
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/hashtags/{niche}")
async def get_hashtag_bank(niche: str, user: dict = Depends(get_current_user)):
    """Get curated hashtag bank for a specific niche"""
    niche_lower = niche.lower()
    
    if niche_lower not in HASHTAG_BANKS:
        # Return general/mixed hashtags
        all_hashtags = []
        for n in HASHTAG_BANKS.values():
            all_hashtags.extend(n.get("trending", [])[:3])
        return {
            "niche": niche,
            "hashtags": {
                "low_competition": all_hashtags[:10],
                "medium_competition": all_hashtags[10:20] if len(all_hashtags) > 10 else [],
                "trending": all_hashtags[:10]
            },
            "total": len(all_hashtags),
            "tip": f"No specific hashtags for '{niche}'. Try: luxury, relationship, health, motivation, parenting, business, travel, food"
        }
    
    bank = HASHTAG_BANKS[niche_lower]
    return {
        "niche": niche,
        "hashtags": bank,
        "total": sum(len(v) for v in bank.values()),
        "tip": f"Mix 3-5 hashtags from each category for best reach"
    }


@router.get("/hashtags")
async def get_all_niches(user: dict = Depends(get_current_user)):
    """Get list of available niches for hashtag banks"""
    return {
        "niches": list(HASHTAG_BANKS.keys()),
        "total_hashtags": sum(sum(len(v) for v in n.values()) for n in HASHTAG_BANKS.values())
    }


@router.post("/thumbnail-text")
async def generate_thumbnail_text(
    topic: str,
    style: str = "all",
    user: dict = Depends(get_current_user)
):
    """Generate thumbnail text options - No credits required"""
    results = {}
    
    if style == "all" or style == "emotional":
        results["emotional"] = [t.replace("{topic}", topic) for t in THUMBNAIL_TEMPLATES["emotional"]]
    
    if style == "all" or style == "curiosity":
        results["curiosity"] = [t.replace("{topic}", topic) for t in THUMBNAIL_TEMPLATES["curiosity"]]
    
    if style == "all" or style == "action":
        results["action"] = [t.replace("{topic}", topic) for t in THUMBNAIL_TEMPLATES["action"]]
    
    if style == "all" or style == "numbers":
        number_templates = []
        for t in THUMBNAIL_TEMPLATES["numbers"]:
            text = t.replace("{topic}", topic)
            text = text.replace("{amount}", str(random.choice([1000, 5000, 10000, 50000, 100000])))
            text = text.replace("{time}", random.choice(["24h", "7 days", "30 days", "1 month"]))
            text = text.replace("{number}", str(random.randint(1, 30)))
            number_templates.append(text)
        results["numbers"] = number_templates
    
    return {
        "topic": topic,
        "thumbnails": results,
        "tip": "Use CAPS for key words, add emojis for emotion"
    }


@router.post("/calendar/generate")
async def generate_content_calendar(
    niche: str,
    days: int = 30,
    include_full_scripts: bool = False,
    user: dict = Depends(get_current_user)
):
    """Generate 30-day content calendar - 10 credits (or 25 for full scripts)"""
    credits_needed = 25 if include_full_scripts else 10
    
    if user["credits"] < credits_needed:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient credits. Need {credits_needed} credits for {'full scripts' if include_full_scripts else 'calendar'}."
        )
    
    niche_lower = niche.lower()
    hooks = HOOK_TEMPLATES.get(niche_lower, HOOK_TEMPLATES["general"])
    
    calendar = []
    for day in range(1, min(days + 1, 31)):
        content_type = random.choice(CONTENT_TYPES)
        hook = random.choice(hooks)
        
        # Replace placeholders with random values
        hook = hook.replace("{price}", f"₹{random.choice([1000, 5000, 10000, 50000, 100000])}")
        hook = hook.replace("{location}", random.choice(["Dubai", "Mumbai", "New York", "Paris", "London"]))
        hook = hook.replace("{item}", random.choice(["watch", "car", "apartment", "bag", "phone"]))
        hook = hook.replace("{place}", random.choice(["hotel", "restaurant", "apartment", "villa", "penthouse"]))
        hook = hook.replace("{amount}", random.choice(["10kg", "15kg", "20kg", "5kg"]))
        hook = hook.replace("{time}", random.choice(["30 days", "2 months", "90 days", "6 weeks"]))
        hook = hook.replace("{number}", str(random.randint(2, 5)))
        hook = hook.replace("{result}", random.choice(["10 clients", "₹1 lakh", "my first sale", "1000 followers"]))
        hook = hook.replace("{word}", random.choice(["INFO", "GUIDE", "SECRET", "YES"]))
        
        cta = random.choice(CTA_TEMPLATES).replace("{niche}", niche).replace("{word}", "GUIDE")
        
        day_content = {
            "day": day,
            "content_type": content_type,
            "hook": hook,
            "cta": cta,
            "best_time": random.choice(["9 AM", "12 PM", "6 PM", "9 PM"]),
            "format": random.choice(["Reel", "Carousel", "Story"])
        }
        
        if include_full_scripts:
            day_content["full_script"] = {
                "intro": hook,
                "body": f"Here's the thing about {niche}... [Add your main content here based on the hook]",
                "outro": cta,
                "duration": random.choice(["15s", "30s", "60s", "90s"])
            }
        
        calendar.append(day_content)
    
    # Deduct credits
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -credits_needed}}
    )
    
    # Log transaction
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -credits_needed,
        "type": "USAGE",
        "description": f"30-Day Calendar: {niche}" + (" (with scripts)" if include_full_scripts else ""),
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save generation
    generation_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "CALENDAR",
        "status": "COMPLETED",
        "inputJson": {"niche": niche, "days": days, "include_full_scripts": include_full_scripts},
        "outputJson": {"calendar": calendar},
        "creditsUsed": credits_needed,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "generationId": generation_id,
        "calendar": calendar,
        "niche": niche,
        "days": len(calendar),
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }


@router.post("/carousel/generate")
async def generate_carousel(
    topic: str,
    niche: str = "general",
    slides: int = 7,
    user: dict = Depends(get_current_user)
):
    """Generate Instagram carousel content - 2 credits"""
    credits_needed = 2
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    if slides < 3 or slides > 10:
        slides = 7
    
    niche_lower = niche.lower()
    hooks = HOOK_TEMPLATES.get(niche_lower, HOOK_TEMPLATES["general"])
    
    carousel = {
        "topic": topic,
        "slides": []
    }
    
    # Slide 1: Big Hook
    carousel["slides"].append({
        "slide_number": 1,
        "type": "hook",
        "text": random.choice(hooks).replace("{price}", "").replace("{location}", "").strip(),
        "subtext": topic,
        "design_tip": "Bold text, contrasting colors, one powerful statement"
    })
    
    # Middle slides: Content
    content_points = [
        f"Point 1: The foundation of {topic}",
        f"Point 2: Common mistakes to avoid",
        f"Point 3: The strategy that works",
        f"Point 4: Real examples",
        f"Point 5: Quick wins you can apply today",
        f"Point 6: Advanced techniques",
        f"Point 7: The mindset shift needed",
        f"Point 8: Tools and resources"
    ]
    
    for i in range(2, slides):
        carousel["slides"].append({
            "slide_number": i,
            "type": "content",
            "text": content_points[i-2] if i-2 < len(content_points) else f"Key insight #{i-1}",
            "subtext": f"Supporting detail for slide {i}",
            "design_tip": "Keep text minimal, use icons or simple graphics"
        })
    
    # Final slide: CTA
    carousel["slides"].append({
        "slide_number": slides,
        "type": "cta",
        "text": "Found this helpful?",
        "subtext": random.choice(CTA_TEMPLATES).replace("{niche}", niche).replace("{word}", "YES"),
        "design_tip": "Clear call-to-action, your handle/logo"
    })
    
    # Generate caption and hashtags
    hashtag_bank = HASHTAG_BANKS.get(niche_lower, HASHTAG_BANKS.get("business", {}))
    selected_hashtags = []
    for category in ["trending", "medium_competition", "low_competition"]:
        if category in hashtag_bank:
            selected_hashtags.extend(random.sample(hashtag_bank[category], min(3, len(hashtag_bank[category]))))
    
    carousel["caption"] = {
        "short": f"Save this {topic} guide! 📌",
        "long": f"Everything you need to know about {topic} in one carousel.\n\nSwipe through to learn:\n→ The basics\n→ Common mistakes\n→ What actually works\n→ Quick wins\n\nSave this post and share with someone who needs it!\n\n" + " ".join(selected_hashtags[:15])
    }
    
    carousel["hashtags"] = selected_hashtags[:20]
    
    # Deduct credits
    await db.users.update_one(
        {"id": user["id"]},
        {"$inc": {"credits": -credits_needed}}
    )
    
    # Log transaction
    await db.credit_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "amount": -credits_needed,
        "type": "USAGE",
        "description": f"Carousel: {topic[:50]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save generation
    generation_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "CAROUSEL",
        "status": "COMPLETED",
        "inputJson": {"topic": topic, "niche": niche, "slides": slides},
        "outputJson": carousel,
        "creditsUsed": credits_needed,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "generationId": generation_id,
        "carousel": carousel,
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }
