"""
Creator Tools Routes - Hashtag Bank, Thumbnails, Calendar, Carousel
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import json
import os
import sys
import random

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    db, logger, get_current_user, deduct_credits,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/creator-tools", tags=["Creator Tools"])

# Hashtag bank data
HASHTAG_BANK = {
    "fitness": ["#fitness", "#gym", "#workout", "#health", "#fitfam", "#training", "#bodybuilding", "#motivation", "#fitlife", "#exercise", "#fitnessmotivation", "#gymlife", "#fit", "#healthylifestyle", "#muscle"],
    "business": ["#business", "#entrepreneur", "#success", "#motivation", "#marketing", "#startup", "#money", "#hustle", "#leadership", "#growth", "#entrepreneurship", "#smallbusiness", "#businessowner", "#mindset", "#goals"],
    "travel": ["#travel", "#wanderlust", "#adventure", "#explore", "#vacation", "#travelphotography", "#instatravel", "#travelgram", "#nature", "#tourism", "#travelling", "#travelblogger", "#trip", "#holiday", "#beautiful"],
    "food": ["#food", "#foodie", "#foodporn", "#yummy", "#delicious", "#cooking", "#recipe", "#foodphotography", "#homemade", "#foodlover", "#instafood", "#foodstagram", "#healthy", "#dinner", "#lunch"],
    "fashion": ["#fashion", "#style", "#ootd", "#outfit", "#fashionblogger", "#streetstyle", "#fashionista", "#instafashion", "#trendy", "#lookoftheday", "#fashionstyle", "#model", "#beauty", "#shopping", "#dress"],
    "tech": ["#technology", "#tech", "#innovation", "#ai", "#coding", "#programming", "#software", "#digital", "#startup", "#developer", "#artificialintelligence", "#python", "#javascript", "#machinelearning", "#data"],
    "beauty": ["#beauty", "#makeup", "#skincare", "#cosmetics", "#beautyblogger", "#makeupartist", "#selfcare", "#glam", "#beautytips", "#skincareroutine", "#beautiful", "#mua", "#lipstick", "#eyeshadow", "#nails"],
    "lifestyle": ["#lifestyle", "#life", "#happy", "#love", "#instagood", "#photooftheday", "#motivation", "#inspiration", "#daily", "#positivevibes", "#mindfulness", "#selfimprovement", "#wellness", "#goals", "#success"],
    "luxury": ["#luxury", "#luxurylifestyle", "#millionaire", "#billionaire", "#wealth", "#success", "#lifestyle", "#rich", "#motivation", "#luxurylife", "#entrepreneur", "#moneymaker", "#highlife", "#premium", "#exclusive"],
    "relationship": ["#relationship", "#love", "#couple", "#relationshipgoals", "#dating", "#marriage", "#romance", "#together", "#couplegoals", "#lovestory", "#family", "#partnership", "#trust", "#communication", "#happiness"],
    "health": ["#health", "#healthy", "#wellness", "#fitness", "#nutrition", "#healthylifestyle", "#selfcare", "#mentalhealth", "#healthcare", "#healthyfood", "#wellbeing", "#yoga", "#meditation", "#mindfulness", "#vitality"],
    "motivation": ["#motivation", "#success", "#inspiration", "#goals", "#mindset", "#grind", "#hustle", "#discipline", "#focus", "#determination", "#nevergiveup", "#believe", "#winner", "#champion", "#growth"],
    "parenting": ["#parenting", "#mom", "#dad", "#family", "#kids", "#momlife", "#dadlife", "#children", "#parenthood", "#motherhood", "#fatherhood", "#baby", "#toddler", "#familytime", "#parentingtips"],
    "general": ["#viral", "#trending", "#fyp", "#explore", "#reels", "#instagram", "#content", "#creator", "#socialmedia", "#influencer", "#trending2026", "#foryou", "#foryoupage", "#viral2026", "#explorepage"]
}

NICHES = list(HASHTAG_BANK.keys())

# Inspirational tips bank
INSPIRATIONAL_TIPS = [
    "Start each morning with gratitude - name 3 things you're thankful for",
    "Your only limit is your mind. Break through it today",
    "Small steps every day lead to massive results",
    "Embrace failure as your greatest teacher",
    "The best time to start was yesterday. The next best time is NOW",
    "Your energy introduces you before you even speak",
    "Don't wait for opportunity. Create it",
    "Progress, not perfection, is what matters",
    "Be so good they can't ignore you",
    "Your comfort zone is where dreams go to die",
    "Action beats intention every single time",
    "Fall seven times, stand up eight",
    "The pain you feel today is the strength you feel tomorrow",
    "Success is not final, failure is not fatal",
    "Dream big, start small, act now",
    "Your future self will thank you for starting today",
    "Consistency beats talent when talent doesn't work hard",
    "Make today count - it's the only one you've got",
    "Turn your can'ts into cans and your dreams into plans",
    "Be the energy you want to attract",
    "Growth happens outside your comfort zone",
    "Your mindset determines your success",
    "Excellence is not an act, but a habit",
    "The only way to do great work is to love what you do",
    "Believe you can and you're halfway there",
    "Success is walking from failure to failure with no loss of enthusiasm",
    "The harder you work, the luckier you get",
    "Don't count the days, make the days count",
    "Your attitude determines your direction",
    "Champions keep playing until they get it right",
    "The secret of getting ahead is getting started",
    "Be stronger than your excuses",
    "Success usually comes to those who are too busy to be looking for it",
    "Don't stop when you're tired. Stop when you're done",
    "Your potential is endless - go explore it",
    "Every expert was once a beginner",
    "Difficult roads often lead to beautiful destinations",
    "What you do today can improve all your tomorrows",
    "Be fearless in the pursuit of what sets your soul on fire",
    "The only impossible journey is the one you never begin"
]

# Carousel content templates
CAROUSEL_CONTENT = {
    "productivity": {
        "covers": [
            "Master Your Morning Routine",
            "10X Your Productivity Today",
            "The Secret to Getting More Done",
            "Stop Wasting Time - Start Winning",
            "Productivity Hacks That Actually Work"
        ],
        "points": [
            "Wake up 1 hour earlier than usual - use this time for deep work before distractions hit",
            "Apply the 2-minute rule - if it takes less than 2 minutes, do it immediately",
            "Use time-blocking to schedule specific tasks in dedicated time slots",
            "Eliminate decision fatigue by planning your day the night before",
            "Take strategic breaks every 90 minutes to maintain peak performance",
            "Batch similar tasks together to maximize efficiency and flow",
            "Turn off all notifications during deep work sessions",
            "Start with your most challenging task when energy is highest"
        ],
        "ctas": [
            "Save this for later and share with a friend who needs it!",
            "Which tip will you try first? Comment below!",
            "Follow for daily productivity tips that transform your life!",
            "Double-tap if you found this helpful!"
        ]
    },
    "success": {
        "covers": [
            "Habits of Highly Successful People",
            "The Millionaire Morning Routine",
            "What Winners Do Differently",
            "Success Secrets Nobody Tells You",
            "Build Your Empire Starting Today"
        ],
        "points": [
            "Wake up with purpose - successful people never hit snooze",
            "Read at least 30 minutes daily - knowledge compounds over time",
            "Network strategically - your network is your net worth",
            "Invest in yourself before investing in anything else",
            "Set clear goals and review them every single day",
            "Take calculated risks - no risk means no reward",
            "Learn from failures - they're just lessons in disguise",
            "Stay consistent even when motivation fades"
        ],
        "ctas": [
            "Ready to transform? Follow for more success tips!",
            "Tag someone who needs to see this!",
            "Save this carousel and revisit it weekly!",
            "Comment your favorite tip below!"
        ]
    },
    "health": {
        "covers": [
            "Transform Your Health in 30 Days",
            "Wellness Habits That Change Lives",
            "The Ultimate Health Guide",
            "Healthy Living Made Simple",
            "Boost Your Energy Naturally"
        ],
        "points": [
            "Drink a full glass of water first thing every morning",
            "Get 7-9 hours of quality sleep - your body heals during rest",
            "Move your body for at least 30 minutes daily",
            "Eat whole foods and minimize processed junk",
            "Practice mindfulness or meditation for mental clarity",
            "Limit screen time, especially before bed",
            "Connect with loved ones - social health matters too",
            "Take regular breaks from sitting - your spine will thank you"
        ],
        "ctas": [
            "Save this for your health journey!",
            "Which habit will you start today? Comment below!",
            "Follow for daily wellness inspiration!",
            "Share with someone who's on their health journey!"
        ]
    },
    "general": {
        "covers": [
            "Transform Your Life Today",
            "Secrets to Living Your Best Life",
            "The Ultimate Guide to Success",
            "Change Your Life in 30 Days",
            "Unlock Your Full Potential"
        ],
        "points": [
            "Start your day with intention and gratitude",
            "Focus on progress, not perfection",
            "Invest time in relationships that matter",
            "Learn something new every single day",
            "Take action, even when you're scared",
            "Celebrate small wins along the way",
            "Stay curious and never stop growing",
            "Be consistent - that's where the magic happens"
        ],
        "ctas": [
            "Ready for more? Follow and stay inspired!",
            "Save this and share with your community!",
            "Comment which tip resonates with you most!",
            "Double-tap if this spoke to you!"
        ]
    }
}


@router.get("/hashtags/{niche}")
async def get_hashtag_bank(niche: str, user: dict = Depends(get_current_user)):
    """Get hashtags for a specific niche - FREE"""
    niche_lower = niche.lower()
    hashtags = HASHTAG_BANK.get(niche_lower, HASHTAG_BANK["general"])
    
    # Shuffle to provide variety
    shuffled = list(hashtags)
    random.shuffle(shuffled)
    
    return {
        "niche": niche,
        "hashtags": shuffled[:15],  # Return 15 random hashtags
        "count": len(shuffled[:15]),
        "tip": "Mix 3-5 popular hashtags with 5-7 niche-specific ones for best reach"
    }


@router.get("/niches")
async def get_all_niches(user: dict = Depends(get_current_user)):
    """Get all available niches"""
    return {"niches": NICHES}


@router.post("/thumbnail-text")
async def generate_thumbnail_text(
    topic: str,
    style: str = "all",
    user: dict = Depends(get_current_user)
):
    """Generate thumbnail text ideas - FREE"""
    
    # Generate thumbnail text ideas with variety
    base_ideas = {
        "clickbait": [
            f"You Won't Believe {topic}!",
            f"The {topic} Secret Nobody Tells You",
            f"I Tried {topic} and THIS Happened",
            f"Stop! Watch This Before {topic}",
            f"Why {topic} Changed Everything",
            f"The TRUTH About {topic}",
            f"Don't Do {topic} Until You See This"
        ],
        "informative": [
            f"How to Master {topic}",
            f"{topic}: Complete Guide",
            f"Everything About {topic}",
            f"{topic} Tips & Tricks",
            f"Learn {topic} in 5 Minutes",
            f"{topic} For Beginners",
            f"The Ultimate {topic} Guide"
        ],
        "emotional": [
            f"The Truth About {topic}",
            f"Why I Love {topic}",
            f"{topic} Will Make You Cry",
            f"The {topic} Journey",
            f"How {topic} Changed My Life",
            f"My {topic} Story",
            f"What {topic} Taught Me"
        ],
        "curiosity": [
            f"What Nobody Tells You About {topic}",
            f"The Hidden Side of {topic}",
            f"Is {topic} Worth It?",
            f"{topic}: Fact or Fiction?",
            f"The Real Story Behind {topic}"
        ],
        "action": [
            f"Start {topic} TODAY",
            f"Try This {topic} Hack NOW",
            f"Stop Scrolling, Learn {topic}",
            f"Take Your {topic} to the Next Level",
            f"Master {topic} in 24 Hours"
        ]
    }
    
    # Randomly select from each category
    result = {}
    for category, texts in base_ideas.items():
        random.shuffle(texts)
        result[category] = texts[:5]
    
    if style != "all" and style in result:
        result = {style: result[style]}
    
    return {
        "topic": topic,
        "thumbnails": result,
        "creditsUsed": 0
    }


@router.post("/content-calendar")
async def generate_content_calendar(
    niche: str,
    days: int = 30,
    include_full_scripts: bool = False,
    user: dict = Depends(get_current_user)
):
    """Generate a content calendar (10 credits, 25 with scripts)"""
    cost = 25 if include_full_scripts else 10
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Content type pool with inspirational themes
    content_types = [
        ("Motivation/Inspiration", "motivational"),
        ("Tutorial/Educational", "educational"),
        ("Tips & tricks", "tips"),
        ("Behind the scenes", "bts"),
        ("Day in my life", "lifestyle"),
        ("Q&A", "engagement"),
        ("Story time", "storytelling"),
        ("Review", "review"),
        ("Transformation", "transformation"),
        ("How I started", "origin"),
        ("Mistakes to avoid", "lessons"),
        ("Trending topic", "trending"),
        ("Challenge", "challenge"),
        ("Quick wins", "quickwins"),
        ("Mindset shift", "mindset")
    ]
    
    # Generate calendar
    calendar = []
    from datetime import date
    start_date = date.today()
    
    # Shuffle inspirational tips to provide variety
    tips_copy = INSPIRATIONAL_TIPS.copy()
    random.shuffle(tips_copy)
    
    for i in range(min(days, 30)):
        current_date = start_date + timedelta(days=i)
        day_name = current_date.strftime("%A")
        
        # Select content type based on day
        if day_name in ["Saturday", "Sunday"]:
            content_type, theme = random.choice([("Story/Behind the scenes", "bts"), ("Day in my life", "lifestyle"), ("Q&A", "engagement")])
        elif day_name == "Monday":
            content_type, theme = "Motivation/Inspiration", "motivational"
        elif day_name == "Wednesday":
            content_type, theme = "Tutorial/Educational", "educational"
        elif day_name == "Friday":
            content_type, theme = random.choice([("Tips & tricks", "tips"), ("Quick wins", "quickwins")])
        else:
            content_type, theme = random.choice(content_types)
        
        # Get inspirational tip for the day
        tip_index = i % len(tips_copy)
        daily_tip = tips_copy[tip_index]
        
        entry = {
            "date": current_date.isoformat(),
            "dayOfWeek": day_name,
            "contentType": content_type,
            "niche": niche,
            "suggestedTopic": f"{niche.title()} - {content_type}",
            "bestPostingTime": "6:00 PM - 9:00 PM" if day_name in ["Saturday", "Sunday"] else "12:00 PM - 1:00 PM",
            "inspirationalTip": daily_tip
        }
        
        if include_full_scripts:
            entry["scriptOutline"] = {
                "hook": f"Stop scrolling! Here's {content_type.lower()} you need...",
                "body": f"Today's focus: {daily_tip}",
                "cta": "Follow for more!"
            }
        
        calendar.append(entry)
    
    await deduct_credits(user["id"], cost, f"Content calendar: {niche} ({days} days)")
    
    return {
        "niche": niche,
        "days": days,
        "calendar": calendar,
        "creditsUsed": cost
    }


@router.post("/carousel")
async def generate_carousel(
    topic: str,
    niche: str = "general",
    slides: int = 7,
    user: dict = Depends(get_current_user)
):
    """Generate carousel content (3 credits)"""
    cost = 3
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    slides = min(max(slides, 3), 10)  # 3-10 slides
    
    # Get content based on niche or general
    niche_key = niche.lower() if niche.lower() in CAROUSEL_CONTENT else "general"
    content = CAROUSEL_CONTENT[niche_key]
    
    # Select random cover, points, and CTA
    cover_title = random.choice(content["covers"])
    points = content["points"].copy()
    random.shuffle(points)
    selected_points = points[:slides - 2]  # Reserve 2 for cover and CTA
    cta_text = random.choice(content["ctas"])
    
    # Generate carousel
    carousel = {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "niche": niche,
        "slides": []
    }
    
    # Cover slide
    carousel["slides"].append({
        "slideNumber": 1,
        "type": "cover",
        "headline": cover_title,
        "subheadline": f"Swipe to learn about {topic} →",
        "designTip": "Use bold, contrasting colors and make the headline POP"
    })
    
    # Content slides with real content
    for i, point in enumerate(selected_points, start=2):
        carousel["slides"].append({
            "slideNumber": i,
            "type": "content",
            "headline": f"Tip #{i-1}",
            "body": point,
            "designTip": "Keep text minimal, use icons and white space"
        })
    
    # CTA slide
    carousel["slides"].append({
        "slideNumber": slides,
        "type": "cta",
        "headline": "Want More?",
        "cta": cta_text,
        "designTip": "Include your handle/logo and a clear action"
    })
    
    await deduct_credits(user["id"], cost, f"Carousel: {topic[:30]}")
    
    return {
        "success": True,
        "carousel": carousel,
        "creditsUsed": cost,
        "tips": [
            "First slide is key - make it scroll-stopping",
            "Keep each slide focused on ONE point",
            "Use consistent branding throughout",
            "End with a clear call-to-action"
        ]
    }


# =============================================================================
# TRENDING TOPICS - Enhanced with randomization
# =============================================================================
@router.get("/trending")
async def get_trending_topics(
    niche: str = "general",
    limit: int = 8,
    user: dict = Depends(get_current_user)
):
    """Get weekly trending topics for content creation - FREE"""
    
    # Extended trending topics data by niche
    TRENDING_DATA = {
        "fitness": [
            {"topic": "Morning Workout Routines", "hook": "5 AM club secrets that actually work", "engagement": "High"},
            {"topic": "Protein Myths Debunked", "hook": "Stop believing these protein lies", "engagement": "Very High"},
            {"topic": "Home Gym Essentials", "hook": "Build a killer gym for under $500", "engagement": "High"},
            {"topic": "Recovery Days", "hook": "Why rest days make you stronger", "engagement": "Medium"},
            {"topic": "Meal Prep Hacks", "hook": "Prep a week of meals in 2 hours", "engagement": "Very High"},
            {"topic": "Cardio vs Weights", "hook": "The truth nobody tells you", "engagement": "High"},
            {"topic": "Sleep & Gains", "hook": "How sleep affects your muscles", "engagement": "Medium"},
            {"topic": "Beginner Mistakes", "hook": "Avoid these gym newbie errors", "engagement": "Very High"},
            {"topic": "HIIT Training Benefits", "hook": "Burn fat 3x faster with this method", "engagement": "Very High"},
            {"topic": "Stretching Routines", "hook": "Flexibility secrets for injury prevention", "engagement": "High"},
            {"topic": "Supplements Guide", "hook": "Which supplements actually work", "engagement": "High"},
            {"topic": "Body Transformation", "hook": "My 90-day journey revealed", "engagement": "Very High"}
        ],
        "business": [
            {"topic": "AI Tools for Entrepreneurs", "hook": "10 AI tools that 10x productivity", "engagement": "Very High"},
            {"topic": "Side Hustle Ideas 2026", "hook": "Start earning $5K/month from home", "engagement": "Very High"},
            {"topic": "Personal Branding", "hook": "Build a brand that attracts clients", "engagement": "High"},
            {"topic": "Remote Team Management", "hook": "Lead teams across timezones", "engagement": "Medium"},
            {"topic": "Pricing Strategies", "hook": "Stop undercharging for your work", "engagement": "High"},
            {"topic": "Email Marketing Secrets", "hook": "Get 50% open rates consistently", "engagement": "High"},
            {"topic": "Content Repurposing", "hook": "1 piece of content → 10 posts", "engagement": "Very High"},
            {"topic": "Networking Tips", "hook": "Connect with anyone on LinkedIn", "engagement": "Medium"},
            {"topic": "Sales Funnel Mastery", "hook": "Convert strangers to customers", "engagement": "Very High"},
            {"topic": "Time Management", "hook": "Get 8 hours of work done in 4", "engagement": "High"},
            {"topic": "Client Retention", "hook": "Keep customers coming back forever", "engagement": "High"},
            {"topic": "Passive Income Streams", "hook": "Make money while you sleep", "engagement": "Very High"}
        ],
        "travel": [
            {"topic": "Budget Travel Hacks", "hook": "Travel Europe for $50/day", "engagement": "Very High"},
            {"topic": "Hidden Gems 2026", "hook": "Places tourists haven't discovered", "engagement": "High"},
            {"topic": "Solo Travel Safety", "hook": "Stay safe while exploring alone", "engagement": "High"},
            {"topic": "Travel Photography", "hook": "Phone photos that look professional", "engagement": "Medium"},
            {"topic": "Packing Light", "hook": "2 weeks in a carry-on bag", "engagement": "High"},
            {"topic": "Flight Deals", "hook": "Find $200 international flights", "engagement": "Very High"},
            {"topic": "Digital Nomad Life", "hook": "Work from anywhere guide", "engagement": "High"},
            {"topic": "Local Experiences", "hook": "Skip tourist traps, live like locals", "engagement": "Medium"},
            {"topic": "Luxury Travel Hacks", "hook": "5-star experience on a 2-star budget", "engagement": "Very High"},
            {"topic": "Adventure Destinations", "hook": "Bucket list places for thrill-seekers", "engagement": "High"},
            {"topic": "Travel Apps", "hook": "Must-have apps for every traveler", "engagement": "High"},
            {"topic": "Airport Tips", "hook": "Breeze through airports like a pro", "engagement": "Medium"}
        ],
        "food": [
            {"topic": "5-Minute Meals", "hook": "Healthy dinners faster than delivery", "engagement": "Very High"},
            {"topic": "Meal Prep Sunday", "hook": "Prep your entire week in 2 hours", "engagement": "High"},
            {"topic": "Air Fryer Recipes", "hook": "Crispy everything without the oil", "engagement": "Very High"},
            {"topic": "Budget Cooking", "hook": "Feed a family for $50/week", "engagement": "High"},
            {"topic": "Viral TikTok Recipes", "hook": "Recipes that actually work", "engagement": "High"},
            {"topic": "Healthy Snacks", "hook": "Guilt-free snacks you'll love", "engagement": "Medium"},
            {"topic": "One-Pot Wonders", "hook": "Less dishes, more flavor", "engagement": "High"},
            {"topic": "Food Photography", "hook": "Make your food look Instagram-worthy", "engagement": "Medium"},
            {"topic": "Freezer Meals", "hook": "Make-ahead meals that taste fresh", "engagement": "High"},
            {"topic": "Restaurant Hacks", "hook": "Recreate famous dishes at home", "engagement": "Very High"},
            {"topic": "Plant-Based Cooking", "hook": "Delicious vegan meals anyone can make", "engagement": "High"},
            {"topic": "Kitchen Organization", "hook": "Pro chef secrets for your home kitchen", "engagement": "Medium"}
        ],
        "tech": [
            {"topic": "AI Tools Revolution", "hook": "Tools that are replacing jobs", "engagement": "Very High"},
            {"topic": "Coding in 2026", "hook": "Languages worth learning now", "engagement": "High"},
            {"topic": "Cybersecurity Basics", "hook": "Protect yourself online", "engagement": "High"},
            {"topic": "No-Code Apps", "hook": "Build apps without coding", "engagement": "Very High"},
            {"topic": "Tech Career Tips", "hook": "Land your dream tech job", "engagement": "High"},
            {"topic": "Productivity Apps", "hook": "Apps that save 10 hours/week", "engagement": "High"},
            {"topic": "Web3 Explained", "hook": "Blockchain made simple", "engagement": "Medium"},
            {"topic": "Automation Hacks", "hook": "Automate your boring tasks", "engagement": "Very High"},
            {"topic": "AI Image Generation", "hook": "Create stunning visuals with AI", "engagement": "Very High"},
            {"topic": "Cloud Computing", "hook": "Why every business needs the cloud", "engagement": "High"},
            {"topic": "Smart Home Setup", "hook": "Automate your entire home", "engagement": "High"},
            {"topic": "Tech Gadgets 2026", "hook": "Gadgets that will change your life", "engagement": "Medium"}
        ],
        "general": [
            {"topic": "Productivity Hacks", "hook": "Do more in less time", "engagement": "Very High"},
            {"topic": "Morning Routines", "hook": "How successful people start their day", "engagement": "High"},
            {"topic": "Money Saving Tips", "hook": "Save $500/month with these tricks", "engagement": "Very High"},
            {"topic": "Self Improvement", "hook": "Small changes, big results", "engagement": "High"},
            {"topic": "Mental Health", "hook": "Daily habits for better mental health", "engagement": "High"},
            {"topic": "Life Hacks", "hook": "Simple tricks that change everything", "engagement": "Very High"},
            {"topic": "Goal Setting", "hook": "Actually achieve your goals this year", "engagement": "Medium"},
            {"topic": "Time Management", "hook": "Master your calendar", "engagement": "High"},
            {"topic": "Mindset Shifts", "hook": "Think like a millionaire", "engagement": "Very High"},
            {"topic": "Communication Skills", "hook": "Talk your way to success", "engagement": "High"},
            {"topic": "Work-Life Balance", "hook": "Stop burning out, start thriving", "engagement": "High"},
            {"topic": "Networking Secrets", "hook": "Build connections that open doors", "engagement": "Medium"}
        ]
    }
    
    # Get topics for the requested niche (default to general if not found)
    all_topics = TRENDING_DATA.get(niche.lower(), TRENDING_DATA["general"])
    
    # Shuffle to provide different results on each refresh
    shuffled_topics = all_topics.copy()
    random.shuffle(shuffled_topics)
    
    # Select limited number
    selected_topics = shuffled_topics[:limit]
    
    return {
        "success": True,
        "niche": niche,
        "weekOf": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topics": selected_topics,
        "tips": [
            "Jump on trending topics within 24-48 hours for maximum reach",
            "Add your unique perspective to stand out",
            "Use the hook as your opening line",
            "High engagement topics = more algorithm boost"
        ]
    }
