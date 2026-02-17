"""
Creator Pro Tools - 15+ AI-Powered Features for Content Creators
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, Form
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import uuid
import json
import random
import re
import asyncio

# Import from shared module (absolute import for server.py compatibility)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared import db, logger, get_current_user, deduct_credits, log_exception, LLM_AVAILABLE, EMERGENT_LLM_KEY
except ImportError:
    from ..shared import db, logger, get_current_user, deduct_credits, log_exception, LLM_AVAILABLE, EMERGENT_LLM_KEY

# Import emergent integrations for AI
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    AI_AVAILABLE = bool(EMERGENT_LLM_KEY)
except ImportError:
    AI_AVAILABLE = False
    logger.warning("emergentintegrations not available - AI features will use templates")


async def generate_ai_content(prompt: str, system_message: str = "You are a viral content expert.") -> str:
    """Generate AI content using Gemini"""
    if not AI_AVAILABLE:
        return None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"creator_pro_{uuid.uuid4().hex[:8]}",
            system_message=system_message
        ).with_model("gemini", "gemini-3-flash-preview")
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return None

router = APIRouter(prefix="/creator-pro", tags=["Creator Pro"])

# =============================================================================
# CREDIT COSTS FOR PRO FEATURES
# =============================================================================
PRO_COSTS = {
    "hook_analyzer": 2,
    "swipe_file": 3,
    "bio_generator": 3,
    "content_repurpose": 5,
    "consistency_tracker": 1,
    "caption_generator": 2,
    "trend_predictor": 3,
    "engagement_optimizer": 2,
    "viral_score": 1,
    "headline_generator": 2,
    "thread_generator": 5,
    "poll_generator": 1,
    "story_template": 2,
    "collab_finder": 3,
    "posting_schedule": 2
}

# =============================================================================
# HOOK ANALYSIS DATA
# =============================================================================
POWER_WORDS = [
    "secret", "free", "new", "proven", "discover", "instant", "guaranteed",
    "exclusive", "limited", "powerful", "breakthrough", "revolutionary",
    "shocking", "incredible", "amazing", "ultimate", "essential", "urgent",
    "warning", "banned", "exposed", "revealed", "hidden", "truth", "lies"
]

EMOTIONAL_TRIGGERS = {
    "curiosity": ["why", "how", "what if", "secret", "hidden", "truth", "revealed"],
    "fear": ["warning", "danger", "mistake", "avoid", "stop", "never", "wrong"],
    "urgency": ["now", "today", "limited", "last chance", "hurry", "before"],
    "desire": ["want", "need", "must have", "dream", "wish", "imagine"],
    "social_proof": ["everyone", "millions", "viral", "trending", "famous"]
}

HOOK_FORMULAS = [
    {"name": "Problem-Solution", "pattern": "Struggling with X? Here's how to fix it"},
    {"name": "Controversy", "pattern": "Unpopular opinion: [hot take]"},
    {"name": "Story Loop", "pattern": "I did X and this happened..."},
    {"name": "Direct Challenge", "pattern": "Stop doing X right now"},
    {"name": "Curiosity Gap", "pattern": "The secret to X that nobody talks about"},
    {"name": "Social Proof", "pattern": "This is why millions are doing X"},
    {"name": "Before/After", "pattern": "X changed my life in Y days"},
    {"name": "Listicle", "pattern": "N things you need to know about X"},
    {"name": "Question Hook", "pattern": "What if I told you X?"},
    {"name": "Fear Appeal", "pattern": "Warning: X is ruining your Y"}
]

# =============================================================================
# VIRAL SWIPE FILE DATABASE
# =============================================================================
VIRAL_HOOKS_DATABASE = {
    "fitness": [
        {"hook": "I lost 30 pounds in 90 days doing this one thing", "views": "2.5M", "engagement": "18%"},
        {"hook": "The workout nobody talks about that actually works", "views": "1.8M", "engagement": "15%"},
        {"hook": "Stop doing crunches. Here's what actually burns belly fat", "views": "3.1M", "engagement": "22%"},
        {"hook": "I did 100 pushups a day for 30 days. Here's what happened", "views": "4.2M", "engagement": "19%"},
        {"hook": "The morning routine that transformed my body", "views": "1.5M", "engagement": "16%"}
    ],
    "business": [
        {"hook": "I made $10K in my first month doing this side hustle", "views": "5.2M", "engagement": "24%"},
        {"hook": "The email template that got me a $50K client", "views": "2.8M", "engagement": "21%"},
        {"hook": "Stop trading time for money. Here's how", "views": "3.5M", "engagement": "18%"},
        {"hook": "The pricing mistake that's killing your business", "views": "1.9M", "engagement": "17%"},
        {"hook": "What I'd do if I had to start over with $0", "views": "4.1M", "engagement": "23%"}
    ],
    "relationships": [
        {"hook": "If they do this, run. Biggest red flag", "views": "6.8M", "engagement": "28%"},
        {"hook": "The truth about modern dating nobody wants to hear", "views": "4.5M", "engagement": "25%"},
        {"hook": "Green flags you're probably ignoring", "views": "3.2M", "engagement": "20%"},
        {"hook": "This is why you're still single (harsh truth)", "views": "5.1M", "engagement": "26%"},
        {"hook": "The 3 second rule that changed my dating life", "views": "2.9M", "engagement": "19%"}
    ],
    "motivation": [
        {"hook": "This is your sign to finally start", "views": "7.2M", "engagement": "30%"},
        {"hook": "They laughed at me. Look at me now", "views": "5.8M", "engagement": "27%"},
        {"hook": "Nobody is coming to save you. Watch this", "views": "4.3M", "engagement": "24%"},
        {"hook": "The mindset shift that changed everything", "views": "3.6M", "engagement": "21%"},
        {"hook": "You're not lazy. You're just doing this wrong", "views": "4.9M", "engagement": "23%"}
    ],
    "lifestyle": [
        {"hook": "My morning routine that makes me unstoppable", "views": "3.4M", "engagement": "19%"},
        {"hook": "Life hacks I wish I knew sooner", "views": "4.7M", "engagement": "22%"},
        {"hook": "Things I stopped buying that changed my life", "views": "2.8M", "engagement": "18%"},
        {"hook": "The habit that 10x'd my productivity", "views": "3.9M", "engagement": "20%"},
        {"hook": "Minimalist living: What I got rid of", "views": "2.5M", "engagement": "17%"}
    ],
    "general": [
        {"hook": "Wait for it... you won't believe this", "views": "8.5M", "engagement": "32%"},
        {"hook": "Nobody is talking about this and it's crazy", "views": "5.6M", "engagement": "26%"},
        {"hook": "I finally figured it out after 10 years", "views": "4.2M", "engagement": "23%"},
        {"hook": "This changed my perspective completely", "views": "3.8M", "engagement": "21%"},
        {"hook": "The truth no one wants to tell you", "views": "6.1M", "engagement": "28%"}
    ]
}

BIO_TEMPLATES = {
    "professional": [
        "🎯 {profession} | Helping {audience} {outcome}",
        "💼 {profession} → {specialization} | {achievement}",
        "🚀 {profession} | {unique_value} | DM for collabs",
        "✨ {profession} sharing {content_type} | {cta}"
    ],
    "creative": [
        "🌟 {profession} by day, {hobby} by night | {vibe}",
        "✨ Making {content_type} that {benefit} | {cta}",
        "🎨 {profession} | {passion} enthusiast | {location}",
        "💫 {profession} + {side_interest} | {tagline}"
    ],
    "minimalist": [
        "{profession}. {one_line_value}.",
        "{what_you_do} → {result}",
        "{profession} | {location}",
        "Just a {profession} trying to {goal}"
    ],
    "bold": [
        "🔥 {profession} who {bold_claim}",
        "The {profession} your competitors follow",
        "Making {audience} {transformation} since {year}",
        "Not your average {profession} | {differentiator}"
    ]
}

# =============================================================================
# 1. HOOK ANALYZER
# =============================================================================
@router.post("/hook-analyzer")
async def analyze_hook(
    hook: str = Form(...),
    niche: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """Analyze a hook for virality factors - 2 credits"""
    cost = PRO_COSTS["hook_analyzer"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    hook_lower = hook.lower()
    
    # Analyze power words
    found_power_words = [w for w in POWER_WORDS if w in hook_lower]
    power_word_score = min(len(found_power_words) * 10, 30)
    
    # Analyze emotional triggers
    emotional_analysis = {}
    for emotion, triggers in EMOTIONAL_TRIGGERS.items():
        found = [t for t in triggers if t in hook_lower]
        if found:
            emotional_analysis[emotion] = found
    emotion_score = min(len(emotional_analysis) * 15, 30)
    
    # Length analysis
    word_count = len(hook.split())
    length_score = 20 if 5 <= word_count <= 12 else (10 if 3 <= word_count <= 15 else 5)
    
    # Structure analysis
    has_number = bool(re.search(r'\d+', hook))
    has_question = "?" in hook
    has_call_to_action = any(w in hook_lower for w in ["stop", "watch", "try", "learn", "discover"])
    structure_score = (10 if has_number else 0) + (5 if has_question else 0) + (5 if has_call_to_action else 0)
    
    # Total score
    total_score = power_word_score + emotion_score + length_score + structure_score
    
    # Determine rating
    if total_score >= 80:
        rating = "🔥 VIRAL POTENTIAL"
        color = "green"
    elif total_score >= 60:
        rating = "👍 STRONG"
        color = "blue"
    elif total_score >= 40:
        rating = "⚡ GOOD"
        color = "yellow"
    else:
        rating = "📈 NEEDS WORK"
        color = "orange"
    
    # Generate improvements
    improvements = []
    if not found_power_words:
        improvements.append("Add power words like 'secret', 'proven', 'instant'")
    if not emotional_analysis:
        improvements.append("Include emotional triggers (curiosity, urgency, desire)")
    if word_count > 15:
        improvements.append("Shorten your hook - aim for 5-12 words")
    if not has_number:
        improvements.append("Consider adding a specific number for credibility")
    if not has_call_to_action:
        improvements.append("Add an action word (stop, watch, try, discover)")
    
    # Find matching formula
    matched_formula = None
    for formula in HOOK_FORMULAS:
        if any(keyword in hook_lower for keyword in formula["pattern"].lower().split()):
            matched_formula = formula["name"]
            break
    
    # Generate AI-powered improved hooks if available
    ai_improvements = []
    if AI_AVAILABLE and total_score < 80:
        prompt = f"""Analyze this social media hook and provide 3 improved versions:
Original hook: "{hook}"
Niche: {niche if niche else 'general'}
Current score: {total_score}/100

Issues identified:
{chr(10).join(['- ' + imp for imp in improvements]) if improvements else '- Generally good but can be better'}

Create 3 improved versions that:
1. Include power words (secret, proven, instant, shocking, etc.)
2. Add emotional triggers (curiosity, urgency, fear, desire)
3. Keep it 5-12 words
4. Use viral hook formulas

Return ONLY a JSON array of 3 improved hook strings:
["hook1", "hook2", "hook3"]"""
        
        ai_response = await generate_ai_content(
            prompt,
            "You are a viral content expert who creates hooks that get millions of views."
        )
        
        if ai_response:
            try:
                json_match = re.search(r'\[.*?\]', ai_response, re.DOTALL)
                if json_match:
                    ai_improvements = json.loads(json_match.group())
            except Exception as e:
                logger.warning(f"Failed to parse AI hook improvements: {e}")
    
    await deduct_credits(user["id"], cost, "Hook Analyzer")
    
    return {
        "success": True,
        "hook": hook,
        "analysis": {
            "totalScore": total_score,
            "rating": rating,
            "color": color,
            "breakdown": {
                "powerWords": {"score": power_word_score, "found": found_power_words},
                "emotionalTriggers": {"score": emotion_score, "analysis": emotional_analysis},
                "length": {"score": length_score, "wordCount": word_count, "optimal": "5-12 words"},
                "structure": {"score": structure_score, "hasNumber": has_number, "hasQuestion": has_question, "hasCTA": has_call_to_action}
            },
            "matchedFormula": matched_formula,
            "improvements": improvements,
            "aiImprovedHooks": ai_improvements if ai_improvements else None
        },
        "aiPowered": bool(AI_AVAILABLE),
        "creditsUsed": cost
    }


# =============================================================================
# 2. VIRAL SWIPE FILE ENGINE
# =============================================================================
@router.get("/swipe-file/{niche}")
async def get_swipe_file(
    niche: str,
    limit: int = 10,
    content_type: str = "reel",
    user: dict = Depends(get_current_user)
):
    """Get viral hooks from swipe file database - 3 credits"""
    cost = PRO_COSTS["swipe_file"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    niche_lower = niche.lower()
    hooks = VIRAL_HOOKS_DATABASE.get(niche_lower, VIRAL_HOOKS_DATABASE["general"])
    
    # Add adaptations
    adapted_hooks = []
    for h in hooks[:limit]:
        adapted_hooks.append({
            **h,
            "adaptations": [
                f"POV: {h['hook']}",
                f"Story time: {h['hook']}",
                f"I need to talk about {h['hook'].lower()}"
            ]
        })
    
    await deduct_credits(user["id"], cost, f"Swipe File: {niche}")
    
    return {
        "success": True,
        "niche": niche,
        "contentType": content_type,
        "hooks": adapted_hooks,
        "tips": [
            "Adapt these hooks to your unique voice",
            "Test multiple variations",
            "First 3 seconds are crucial",
            "Match hook energy with video energy"
        ],
        "creditsUsed": cost
    }


# =============================================================================
# 3. BIO GENERATOR (AI-POWERED)
# =============================================================================
@router.post("/bio-generator")
async def generate_bio(
    profession: str = Form(...),
    keywords: str = Form(""),  # comma-separated
    tone: str = Form("professional"),
    platform: str = Form("instagram"),
    user: dict = Depends(get_current_user)
):
    """Generate AI-powered social media bios - 3 credits"""
    cost = PRO_COSTS["bio_generator"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]
    char_limits = {"instagram": 150, "twitter": 160, "tiktok": 80, "linkedin": 220}
    limit = char_limits.get(platform, 150)
    
    # Try AI generation first
    ai_bios = []
    if AI_AVAILABLE:
        prompt = f"""Generate 5 unique social media bios for a {profession}.
Platform: {platform} (max {limit} characters each)
Tone: {tone}
Keywords to include: {', '.join(keywords_list) if keywords_list else 'none specified'}

Requirements:
- Each bio must be under {limit} characters
- Use emojis strategically
- Include a clear value proposition
- Match the {tone} tone
- Be creative and unique

Return ONLY a JSON array of 5 bio strings, no explanations:
["bio1", "bio2", "bio3", "bio4", "bio5"]"""
        
        ai_response = await generate_ai_content(
            prompt,
            "You are an expert social media copywriter who creates viral bios that convert."
        )
        
        if ai_response:
            try:
                # Parse JSON from response
                import re
                json_match = re.search(r'\[.*?\]', ai_response, re.DOTALL)
                if json_match:
                    ai_bios = json.loads(json_match.group())
            except Exception as e:
                logger.warning(f"Failed to parse AI bios: {e}")
    
    # Fallback to templates if AI fails
    if not ai_bios:
        templates = BIO_TEMPLATES.get(tone, BIO_TEMPLATES["professional"])
        for template in templates:
            bio = template.format(
                profession=profession,
                audience=keywords_list[0] if keywords_list else "people",
                outcome=keywords_list[1] if len(keywords_list) > 1 else "achieve their goals",
                specialization=keywords_list[0] if keywords_list else "expert tips",
                achievement="10K+ helped" if random.random() > 0.5 else "Featured creator",
                unique_value=f"Daily {profession.lower()} tips",
                content_type=f"{profession.lower()} content",
                cta="Link below ⬇️",
                hobby=keywords_list[-1] if keywords_list else "creator",
                vibe="Living the dream ✨",
                passion=keywords_list[0] if keywords_list else "growth",
                location="🌍 Global",
                side_interest="coffee addict ☕",
                tagline="Building something special",
                one_line_value=f"Making {profession.lower()} simple",
                what_you_do=f"I help with {profession.lower()}",
                result="results",
                goal="make an impact",
                bold_claim=f"actually delivers results",
                transformation="better",
                year="2024",
                differentiator="Results speak louder"
            )
            ai_bios.append(bio)
    
    await deduct_credits(user["id"], cost, f"Bio Generator: {platform}")
    
    return {
        "success": True,
        "profession": profession,
        "platform": platform,
        "tone": tone,
        "bios": [{"bio": b, "charCount": len(b), "withinLimit": len(b) <= limit} for b in ai_bios[:5]],
        "charLimit": limit,
        "aiPowered": bool(AI_AVAILABLE and ai_bios),
        "tips": [
            f"Keep under {limit} characters for {platform}",
            "Include a clear call-to-action",
            "Use emojis sparingly but strategically",
            "Update your bio regularly to reflect growth"
        ],
        "creditsUsed": cost
    }


# =============================================================================
# 4. CONTENT REPURPOSING ENGINE
# =============================================================================
@router.post("/content-repurpose")
async def repurpose_content(
    content: str = Form(...),
    source_format: str = Form(...),  # blog, tweet, caption, video_script
    target_formats: str = Form(...),  # comma-separated
    user: dict = Depends(get_current_user)
):
    """Repurpose content into multiple formats - 5 credits"""
    cost = PRO_COSTS["content_repurpose"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    targets = [t.strip() for t in target_formats.split(",")]
    
    repurposed = {}
    
    for target in targets:
        if target == "reel_script":
            # Convert to reel script
            sentences = content.split(".")[:3]
            repurposed["reel_script"] = {
                "hook": sentences[0].strip() if sentences else content[:50],
                "body": " ".join(sentences[1:3]) if len(sentences) > 1 else content[50:150],
                "cta": "Follow for more! Link in bio.",
                "duration": "15-30s"
            }
        elif target == "carousel":
            # Convert to carousel slides
            sentences = [s.strip() for s in content.split(".") if s.strip()]
            repurposed["carousel"] = {
                "slides": [
                    {"slide": 1, "type": "cover", "text": sentences[0] if sentences else "Main Point"},
                    *[{"slide": i+2, "type": "content", "text": s} for i, s in enumerate(sentences[1:6])],
                    {"slide": len(sentences[:6])+2, "type": "cta", "text": "Save this post!"}
                ]
            }
        elif target == "thread":
            # Convert to Twitter/X thread
            sentences = [s.strip() for s in content.split(".") if s.strip()]
            repurposed["thread"] = {
                "tweets": [
                    {"number": 1, "text": f"🧵 {sentences[0]}" if sentences else "Thread incoming..."},
                    *[{"number": i+2, "text": s} for i, s in enumerate(sentences[1:8])],
                    {"number": "last", "text": "If this was helpful, RT the first tweet! Follow for more."}
                ]
            }
        elif target == "linkedin_post":
            repurposed["linkedin_post"] = {
                "hook": content[:100] + "...",
                "body": content,
                "cta": "\n\n👉 What do you think? Share your thoughts below.\n\n#leadership #growth #insights"
            }
        elif target == "email":
            repurposed["email"] = {
                "subject": content[:50] + "...",
                "preview": content[50:100],
                "body": content,
                "cta": "Reply to this email with your thoughts!"
            }
        elif target == "quote_cards":
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20][:5]
            repurposed["quote_cards"] = [{"quote": s, "attribution": "- You"} for s in sentences]
    
    await deduct_credits(user["id"], cost, "Content Repurposing")
    
    return {
        "success": True,
        "sourceFormat": source_format,
        "targetFormats": targets,
        "repurposed": repurposed,
        "creditsUsed": cost
    }


# =============================================================================
# 5. CONSISTENCY TRACKER
# =============================================================================
@router.post("/consistency-track")
async def track_consistency(
    content_type: str = Form(...),
    platform: str = Form("instagram"),
    notes: str = Form(""),
    user: dict = Depends(get_current_user)
):
    """Track content posting consistency - 1 credit"""
    cost = PRO_COSTS["consistency_tracker"]
    
    # Save tracking entry
    entry = {
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "contentType": content_type,
        "platform": platform,
        "notes": notes,
        "postedAt": datetime.now(timezone.utc).isoformat()
    }
    await db.consistency_tracker.insert_one(entry)
    
    # Get stats
    user_entries = await db.consistency_tracker.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("postedAt", -1).to_list(100)
    
    # Calculate streak
    streak = 0
    today = datetime.now(timezone.utc).date()
    for i, e in enumerate(user_entries):
        entry_date = datetime.fromisoformat(e["postedAt"].replace('Z', '+00:00')).date()
        expected_date = today - timedelta(days=i)
        if entry_date == expected_date:
            streak += 1
        else:
            break
    
    # Calculate weekly stats
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    weekly_posts = len([e for e in user_entries if e.get("postedAt", "") >= week_ago])
    
    await deduct_credits(user["id"], cost, "Consistency Tracker")
    
    return {
        "success": True,
        "tracked": entry,
        "stats": {
            "currentStreak": streak,
            "weeklyPosts": weekly_posts,
            "totalPosts": len(user_entries),
            "bestStreak": max(streak, 1)  # Would need more logic for historical best
        },
        "motivation": "🔥 Keep going! Consistency beats perfection." if streak > 0 else "Start your streak today!",
        "creditsUsed": cost
    }


@router.get("/consistency-stats")
async def get_consistency_stats(user: dict = Depends(get_current_user)):
    """Get consistency statistics - FREE"""
    entries = await db.consistency_tracker.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("postedAt", -1).to_list(100)
    
    # Group by platform
    by_platform = {}
    for e in entries:
        platform = e.get("platform", "unknown")
        if platform not in by_platform:
            by_platform[platform] = 0
        by_platform[platform] += 1
    
    # Group by content type
    by_type = {}
    for e in entries:
        ct = e.get("contentType", "unknown")
        if ct not in by_type:
            by_type[ct] = 0
        by_type[ct] += 1
    
    return {
        "totalPosts": len(entries),
        "byPlatform": by_platform,
        "byContentType": by_type,
        "recentPosts": entries[:10]
    }


# =============================================================================
# 6. CAPTION GENERATOR (AI-POWERED)
# =============================================================================
@router.post("/caption-generator")
async def generate_caption(
    topic: str = Form(...),
    tone: str = Form("engaging"),
    include_cta: bool = Form(True),
    include_hashtags: bool = Form(True),
    platform: str = Form("instagram"),
    user: dict = Depends(get_current_user)
):
    """Generate AI-powered captions - 2 credits"""
    cost = PRO_COSTS["caption_generator"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    ai_captions = []
    
    # Try AI generation first
    if AI_AVAILABLE:
        prompt = f"""Generate 3 unique {tone} captions for {platform} about: {topic}

Requirements:
- Tone: {tone}
- Platform: {platform}
- Include CTA: {include_cta}
- Include hashtags: {include_hashtags}
- Each caption should be engaging and optimized for the platform
- Use emojis appropriately
- Make each caption distinct in style

Return ONLY a JSON array of 3 caption strings:
["caption1", "caption2", "caption3"]"""
        
        ai_response = await generate_ai_content(
            prompt,
            "You are a viral social media copywriter who creates captions that drive engagement."
        )
        
        if ai_response:
            try:
                import re
                json_match = re.search(r'\[.*?\]', ai_response, re.DOTALL)
                if json_match:
                    ai_captions = json.loads(json_match.group())
            except Exception as e:
                logger.warning(f"Failed to parse AI captions: {e}")
    
    # Fallback to templates if AI fails
    if not ai_captions:
        captions_templates = {
            "engaging": [
                f"Here's something about {topic} that changed my perspective...",
                f"Can we talk about {topic}? Because this is important.",
                f"I've been thinking a lot about {topic} lately. Here's why..."
            ],
            "educational": [
                f"3 things you need to know about {topic}:",
                f"The truth about {topic} that nobody talks about:",
                f"Everything you've been told about {topic} is wrong. Here's why:"
            ],
            "storytelling": [
                f"Story time: How {topic} changed everything for me...",
                f"I never thought I'd be talking about {topic}, but here we are...",
                f"The {topic} journey that taught me the biggest lesson..."
            ],
            "promotional": [
                f"Excited to share something about {topic} with you!",
                f"This is why {topic} matters more than ever...",
                f"If you've been struggling with {topic}, this is for you."
            ]
        }
        
        ai_captions = captions_templates.get(tone, captions_templates["engaging"])
        
        # Add CTA
        ctas = [
            "\n\n👉 Save this for later!",
            "\n\n💬 Drop a comment if you agree!",
            "\n\n🔔 Follow for more!",
            "\n\n❤️ Double tap if this resonates!"
        ]
        
        # Add hashtags
        hashtags = f"\n\n#{topic.replace(' ', '').lower()} #content #viral #trending #fyp"
        
        enhanced_captions = []
        for cap in ai_captions:
            final = cap
            if include_cta:
                final += random.choice(ctas)
            if include_hashtags:
                final += hashtags
            enhanced_captions.append(final)
        ai_captions = enhanced_captions
    
    await deduct_credits(user["id"], cost, "Caption Generator")
    
    return {
        "success": True,
        "topic": topic,
        "tone": tone,
        "captions": [{"caption": cap, "charCount": len(cap)} for cap in ai_captions[:3]],
        "aiPowered": bool(AI_AVAILABLE),
        "creditsUsed": cost
    }


# =============================================================================
# 7. VIRAL SCORE CALCULATOR
# =============================================================================
@router.post("/viral-score")
async def calculate_viral_score(
    hook: str = Form(...),
    caption: str = Form(""),
    hashtags: str = Form(""),
    user: dict = Depends(get_current_user)
):
    """Calculate virality potential score - 1 credit"""
    cost = PRO_COSTS["viral_score"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    scores = {}
    
    # Hook score (40% weight)
    hook_words = len(hook.split())
    power_count = sum(1 for w in POWER_WORDS if w in hook.lower())
    hook_score = min(100, (power_count * 15) + (20 if 5 <= hook_words <= 12 else 10))
    scores["hook"] = {"score": hook_score, "weight": 40}
    
    # Caption score (30% weight)
    caption_length = len(caption)
    has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F]', caption))
    has_cta = any(w in caption.lower() for w in ["follow", "save", "share", "comment", "like"])
    caption_score = min(100, (30 if 100 <= caption_length <= 500 else 15) + (20 if has_emoji else 0) + (30 if has_cta else 0))
    scores["caption"] = {"score": caption_score, "weight": 30}
    
    # Hashtag score (30% weight)
    hashtag_count = len([h for h in hashtags.split() if h.startswith("#")])
    hashtag_score = 100 if 5 <= hashtag_count <= 15 else (70 if 3 <= hashtag_count <= 20 else 40)
    scores["hashtags"] = {"score": hashtag_score, "weight": 30}
    
    # Calculate weighted total
    total_score = sum(s["score"] * s["weight"] / 100 for s in scores.values())
    
    # Determine tier
    if total_score >= 85:
        tier = "🚀 VIRAL READY"
    elif total_score >= 70:
        tier = "🔥 HIGH POTENTIAL"
    elif total_score >= 50:
        tier = "⚡ MODERATE"
    else:
        tier = "📈 NEEDS IMPROVEMENT"
    
    await deduct_credits(user["id"], cost, "Viral Score Calculator")
    
    return {
        "success": True,
        "totalScore": round(total_score, 1),
        "tier": tier,
        "breakdown": scores,
        "recommendations": [
            "Add more power words to your hook" if hook_score < 70 else None,
            "Include a clear CTA in your caption" if not has_cta else None,
            "Add emojis to increase engagement" if not has_emoji else None,
            f"Use {15 - hashtag_count} more hashtags" if hashtag_count < 5 else None
        ],
        "creditsUsed": cost
    }


# =============================================================================
# 8. HEADLINE GENERATOR
# =============================================================================
@router.post("/headline-generator")
async def generate_headlines(
    topic: str = Form(...),
    style: str = Form("all"),  # clickbait, informative, emotional, numbers
    count: int = Form(5),
    user: dict = Depends(get_current_user)
):
    """Generate attention-grabbing headlines - 2 credits"""
    cost = PRO_COSTS["headline_generator"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    headlines = {
        "clickbait": [
            f"You Won't Believe What Happens When You Try {topic}",
            f"The Shocking Truth About {topic} Nobody Tells You",
            f"I Tried {topic} For 30 Days And This Happened",
            f"Stop Everything: {topic} Just Changed The Game",
            f"Why Everyone Is Talking About {topic} Right Now"
        ],
        "informative": [
            f"The Complete Guide to {topic} in 2024",
            f"Everything You Need to Know About {topic}",
            f"How to Master {topic}: A Step-by-Step Guide",
            f"{topic} Explained: What Beginners Need to Know",
            f"The Science Behind {topic}: What Research Shows"
        ],
        "emotional": [
            f"How {topic} Changed My Life Forever",
            f"The {topic} Journey That Made Me Cry",
            f"Why {topic} Means Everything to Me",
            f"The Heartbreaking Truth About {topic}",
            f"What {topic} Taught Me About Life"
        ],
        "numbers": [
            f"7 Secrets About {topic} That Will Blow Your Mind",
            f"10 {topic} Mistakes You're Probably Making",
            f"5 Ways {topic} Will Transform Your Life",
            f"3 Things I Wish I Knew About {topic} Sooner",
            f"12 {topic} Hacks That Actually Work"
        ]
    }
    
    if style == "all":
        result = {k: v[:count] for k, v in headlines.items()}
    else:
        result = {style: headlines.get(style, headlines["informative"])[:count]}
    
    await deduct_credits(user["id"], cost, "Headline Generator")
    
    return {
        "success": True,
        "topic": topic,
        "style": style,
        "headlines": result,
        "creditsUsed": cost
    }


# =============================================================================
# 9. THREAD GENERATOR
# =============================================================================
@router.post("/thread-generator")
async def generate_thread(
    topic: str = Form(...),
    points: int = Form(7),
    platform: str = Form("twitter"),
    user: dict = Depends(get_current_user)
):
    """Generate a viral thread structure - 5 credits"""
    cost = PRO_COSTS["thread_generator"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    points = min(max(points, 3), 15)
    
    thread = {
        "topic": topic,
        "platform": platform,
        "tweets": [
            {"number": 1, "type": "hook", "template": f"🧵 Everything you need to know about {topic}.\n\nThread 👇"},
            *[{"number": i+2, "type": "point", "template": f"{i}. [Key point about {topic}]\n\n[Explanation or example]"} for i in range(1, points)],
            {"number": points+1, "type": "summary", "template": f"To summarize {topic}:\n\n• Point 1\n• Point 2\n• Point 3"},
            {"number": points+2, "type": "cta", "template": "If you found this helpful:\n\n1. RT the first tweet\n2. Follow me for more\n3. Drop a 🔥 below"}
        ],
        "tips": [
            "First tweet is crucial - make it irresistible",
            "Each tweet should stand alone but connect",
            "Use line breaks for readability",
            "End with a clear CTA"
        ]
    }
    
    await deduct_credits(user["id"], cost, "Thread Generator")
    
    return {
        "success": True,
        "thread": thread,
        "creditsUsed": cost
    }


# =============================================================================
# 10. POLL GENERATOR
# =============================================================================
@router.post("/poll-generator")
async def generate_poll(
    topic: str = Form(...),
    poll_type: str = Form("opinion"),  # opinion, quiz, this_or_that
    user: dict = Depends(get_current_user)
):
    """Generate engaging poll ideas - 1 credit"""
    cost = PRO_COSTS["poll_generator"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    polls = {
        "opinion": [
            {
                "question": f"What's your biggest challenge with {topic}?",
                "options": ["Time", "Knowledge", "Resources", "Motivation"]
            },
            {
                "question": f"Hot take: {topic} is overrated. Agree?",
                "options": ["Strongly Agree", "Somewhat Agree", "Disagree", "Strongly Disagree"]
            }
        ],
        "quiz": [
            {
                "question": f"How well do you know {topic}?",
                "options": ["Expert", "Intermediate", "Beginner", "What's that?"]
            },
            {
                "question": f"Can you guess the right answer about {topic}?",
                "options": ["Option A", "Option B", "Option C", "Option D"]
            }
        ],
        "this_or_that": [
            {
                "question": f"When it comes to {topic}, which do you prefer?",
                "options": ["Option A", "Option B"]
            },
            {
                "question": f"For {topic}, what matters more?",
                "options": ["Quality", "Speed", "Both equally", "Neither"]
            }
        ]
    }
    
    selected_polls = polls.get(poll_type, polls["opinion"])
    
    await deduct_credits(user["id"], cost, "Poll Generator")
    
    return {
        "success": True,
        "topic": topic,
        "pollType": poll_type,
        "polls": selected_polls,
        "tips": [
            "Polls boost engagement significantly",
            "Ask questions your audience cares about",
            "Share results and insights after"
        ],
        "creditsUsed": cost
    }


# =============================================================================
# 11. STORY TEMPLATE GENERATOR
# =============================================================================
@router.post("/story-templates")
async def generate_story_templates(
    niche: str = Form(...),
    story_type: str = Form("engagement"),  # engagement, promo, behind_scenes
    user: dict = Depends(get_current_user)
):
    """Generate Instagram/TikTok story templates - 2 credits"""
    cost = PRO_COSTS["story_template"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    templates = {
        "engagement": [
            {"slide": 1, "type": "question", "text": f"Quick question about {niche}...", "sticker": "Question Box"},
            {"slide": 2, "type": "poll", "text": "Which do you prefer?", "sticker": "Poll"},
            {"slide": 3, "type": "slider", "text": f"Rate your {niche} knowledge", "sticker": "Emoji Slider"},
            {"slide": 4, "type": "quiz", "text": f"Pop quiz: {niche} edition", "sticker": "Quiz"},
            {"slide": 5, "type": "cta", "text": "DM me your answer!", "sticker": "Link/DM Button"}
        ],
        "promo": [
            {"slide": 1, "type": "hook", "text": "Wait... have you seen this?", "sticker": None},
            {"slide": 2, "type": "problem", "text": f"Struggling with {niche}?", "sticker": None},
            {"slide": 3, "type": "solution", "text": "Here's how I can help...", "sticker": None},
            {"slide": 4, "type": "proof", "text": "Results from my clients", "sticker": None},
            {"slide": 5, "type": "cta", "text": "Link in bio!", "sticker": "Link"}
        ],
        "behind_scenes": [
            {"slide": 1, "type": "intro", "text": "Day in my life as a...", "sticker": None},
            {"slide": 2, "type": "process", "text": "Working on something big", "sticker": None},
            {"slide": 3, "type": "insight", "text": "Here's what most people don't see", "sticker": None},
            {"slide": 4, "type": "value", "text": "Quick tip for you", "sticker": None},
            {"slide": 5, "type": "question", "text": "Want to see more BTS?", "sticker": "Poll"}
        ]
    }
    
    selected = templates.get(story_type, templates["engagement"])
    
    await deduct_credits(user["id"], cost, "Story Templates")
    
    return {
        "success": True,
        "niche": niche,
        "storyType": story_type,
        "templates": selected,
        "tips": [
            "Post stories consistently (at least daily)",
            "Use stickers to boost engagement",
            "Save best stories to Highlights"
        ],
        "creditsUsed": cost
    }


# =============================================================================
# 12. POSTING SCHEDULE OPTIMIZER
# =============================================================================
@router.post("/posting-schedule")
async def optimize_posting_schedule(
    platform: str = Form(...),
    timezone_str: str = Form("UTC"),
    content_frequency: str = Form("daily"),  # daily, 3x_week, weekly
    user: dict = Depends(get_current_user)
):
    """Generate optimized posting schedule - 2 credits"""
    cost = PRO_COSTS["posting_schedule"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Optimal times by platform (in local time)
    optimal_times = {
        "instagram": {
            "weekday": ["6:00 AM", "12:00 PM", "7:00 PM", "9:00 PM"],
            "weekend": ["9:00 AM", "11:00 AM", "7:00 PM", "8:00 PM"],
            "best_days": ["Tuesday", "Wednesday", "Friday"]
        },
        "tiktok": {
            "weekday": ["7:00 AM", "12:00 PM", "3:00 PM", "7:00 PM"],
            "weekend": ["9:00 AM", "12:00 PM", "7:00 PM"],
            "best_days": ["Tuesday", "Thursday", "Friday"]
        },
        "twitter": {
            "weekday": ["8:00 AM", "12:00 PM", "5:00 PM", "9:00 PM"],
            "weekend": ["9:00 AM", "12:00 PM"],
            "best_days": ["Wednesday", "Thursday"]
        },
        "linkedin": {
            "weekday": ["7:30 AM", "12:00 PM", "5:00 PM"],
            "weekend": ["Not recommended"],
            "best_days": ["Tuesday", "Wednesday", "Thursday"]
        },
        "youtube": {
            "weekday": ["2:00 PM", "4:00 PM", "9:00 PM"],
            "weekend": ["9:00 AM", "12:00 PM"],
            "best_days": ["Thursday", "Friday", "Saturday"]
        }
    }
    
    platform_data = optimal_times.get(platform.lower(), optimal_times["instagram"])
    
    # Generate weekly schedule
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    schedule = []
    
    if content_frequency == "daily":
        for day in days:
            is_weekend = day in ["Saturday", "Sunday"]
            times = platform_data["weekend"] if is_weekend else platform_data["weekday"]
            schedule.append({
                "day": day,
                "postTime": times[0] if times and times[0] != "Not recommended" else None,
                "isOptimalDay": day in platform_data["best_days"]
            })
    elif content_frequency == "3x_week":
        for day in platform_data["best_days"][:3]:
            times = platform_data["weekday"]
            schedule.append({
                "day": day,
                "postTime": times[0],
                "isOptimalDay": True
            })
    else:  # weekly
        best_day = platform_data["best_days"][0]
        times = platform_data["weekday"]
        schedule.append({
            "day": best_day,
            "postTime": times[0],
            "isOptimalDay": True
        })
    
    await deduct_credits(user["id"], cost, f"Posting Schedule: {platform}")
    
    return {
        "success": True,
        "platform": platform,
        "timezone": timezone_str,
        "frequency": content_frequency,
        "schedule": schedule,
        "optimalTimes": platform_data,
        "tips": [
            "Consistency matters more than perfect timing",
            "Test and adjust based on your audience",
            "Use scheduling tools to stay consistent"
        ],
        "creditsUsed": cost
    }


# =============================================================================
# FEATURE COSTS ENDPOINT
# =============================================================================
@router.get("/costs")
async def get_pro_costs():
    """Get all Creator Pro feature costs"""
    return {
        "costs": PRO_COSTS,
        "features": {
            "hook_analyzer": "Analyze hooks for virality factors",
            "swipe_file": "Access viral hook database",
            "bio_generator": "Generate optimized social bios",
            "content_repurpose": "Convert content to multiple formats",
            "consistency_tracker": "Track posting consistency",
            "caption_generator": "Generate engaging captions",
            "viral_score": "Calculate content virality score",
            "headline_generator": "Create attention-grabbing headlines",
            "thread_generator": "Structure viral threads",
            "poll_generator": "Create engaging polls",
            "story_template": "Get story templates",
            "posting_schedule": "Optimize posting times"
        }
    }
