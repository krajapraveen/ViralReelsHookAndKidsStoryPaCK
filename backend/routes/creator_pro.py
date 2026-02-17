"""
Creator Tools Pro - Template-Based Features (No AI Cost)
Includes: Hook Swipe File, Hook Analyzer, Bio Generator, Hashtag Matrix, etc.
"""
import re
import random
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# Router
creator_pro_router = APIRouter(prefix="/creator-pro", tags=["Creator Pro Tools"])

# =============================================================================
# VIRAL HOOK SWIPE FILE ENGINE - 500+ Categorized Hooks
# =============================================================================
HOOK_DATABASE = {
    "controversial": [
        "Nobody wants to hear this but...",
        "I'm going to get hate for this but...",
        "This is going to make people mad...",
        "Unpopular opinion but...",
        "I don't care what anyone says...",
        "Everyone's lying about this...",
        "The truth nobody tells you about...",
        "Stop doing this immediately...",
        "This is why you're failing at...",
        "The biggest lie in the industry is...",
        "I was wrong about everything...",
        "What they don't want you to know...",
        "This will change everything you believe about...",
        "The controversial truth about...",
        "I'm risking my reputation to tell you...",
        "Everyone is doing this wrong...",
        "Here's why experts are lying to you...",
        "The uncomfortable truth about...",
        "I've been keeping this secret...",
        "This advice ruined my life..."
    ],
    "emotional": [
        "This brought me to tears...",
        "I wasn't ready for this...",
        "My heart literally stopped when...",
        "I still can't believe this happened...",
        "This is the most beautiful thing I've seen...",
        "Warning: you might cry watching this...",
        "I've never felt more alive than...",
        "This moment changed my life forever...",
        "I didn't expect to feel this way...",
        "The moment that broke me...",
        "I'm not crying, you're crying...",
        "This hits different at 2am...",
        "The day my world fell apart...",
        "I've never told anyone this before...",
        "This is why I do what I do...",
        "The hardest goodbye I ever said...",
        "When everything finally made sense...",
        "The moment I knew things would never be the same...",
        "This gave me goosebumps...",
        "I wish someone told me this earlier..."
    ],
    "authority": [
        "After 10 years in this industry...",
        "As someone who's made $1M from this...",
        "I've helped 1000+ people with this...",
        "Here's what Harvard research shows...",
        "According to the latest studies...",
        "Expert tip most people miss...",
        "The secret top performers know...",
        "What CEOs do differently...",
        "The strategy billionaires use...",
        "After coaching 500+ clients...",
        "My mentor taught me this...",
        "What professionals never tell beginners...",
        "The framework that changed everything...",
        "Scientific proof that...",
        "Data from 10,000 users shows...",
        "The method used by industry leaders...",
        "After analyzing 1000+ successful...",
        "What separates amateurs from pros...",
        "The insider strategy for...",
        "Top 1% secret revealed..."
    ],
    "storytime": [
        "So this crazy thing happened...",
        "Story time: how I almost...",
        "You won't believe what happened next...",
        "Let me tell you about the time...",
        "This is the wildest story...",
        "I've never shared this publicly...",
        "The craziest thing that ever happened to me...",
        "Plot twist: it wasn't what I expected...",
        "Here's the full story of how...",
        "Day 1 of my journey to...",
        "It all started when I...",
        "The story of how I went from...",
        "This is how it all began...",
        "Three years ago, everything changed...",
        "The day I decided to change my life...",
        "Here's what actually happened...",
        "The behind-the-scenes story of...",
        "My biggest failure taught me...",
        "The moment that started everything...",
        "How I accidentally discovered..."
    ],
    "pov": [
        "POV: You finally figured it out...",
        "POV: You're about to change your life...",
        "POV: You're watching this at 3am...",
        "POV: You just discovered the secret...",
        "POV: You're about to level up...",
        "POV: Everyone doubted you but...",
        "POV: You took the leap and...",
        "POV: This is your sign to...",
        "POV: You're realizing everything was worth it...",
        "POV: You're the main character now...",
        "POV: You just unlocked a new level...",
        "POV: The universe is aligning...",
        "POV: You're about to have a breakthrough...",
        "POV: Everything is falling into place...",
        "POV: You're watching your dreams come true...",
        "POV: You finally chose yourself...",
        "POV: The plot twist in your favor...",
        "POV: You stopped playing small...",
        "POV: You're becoming who you're meant to be...",
        "POV: This is your moment..."
    ],
    "luxury": [
        "How I afford this lifestyle...",
        "A day in my life as a...",
        "What $10K/month looks like...",
        "The upgrade that changed everything...",
        "Living the dream, here's how...",
        "My morning routine as a...",
        "Inside my luxury apartment...",
        "Things I never thought I'd own...",
        "The life I manifested...",
        "What financial freedom feels like...",
        "My biggest purchase ever...",
        "Why I'll never go back to...",
        "The lifestyle business model...",
        "How I built this from nothing...",
        "Money tips rich people use...",
        "The investment that paid off...",
        "What my income streams look like...",
        "Passive income changed my life...",
        "The wealth mindset shift...",
        "From broke to this in 2 years..."
    ],
    "relationship": [
        "Green flags I ignored until...",
        "What healthy love actually looks like...",
        "The moment I knew they were the one...",
        "Red flags I wish I noticed sooner...",
        "Dating advice that actually works...",
        "How we met vs how it's going...",
        "Things I learned from my breakup...",
        "The relationship hack nobody talks about...",
        "Why I stopped settling for...",
        "What true partnership looks like...",
        "The conversation that changed everything...",
        "How we survived long distance...",
        "Things couples should discuss before...",
        "The secret to lasting love...",
        "Why this relationship is different...",
        "What I wish I knew about love...",
        "The boundary that saved my relationship...",
        "How to know when it's real...",
        "The moment everything clicked...",
        "Love lessons learned the hard way..."
    ],
    "health": [
        "The habit that changed my health...",
        "What happened when I tried this for 30 days...",
        "The food I cut out and noticed...",
        "My morning routine for energy...",
        "Simple changes, massive results...",
        "What nobody tells you about...",
        "The workout that actually works...",
        "My mental health non-negotiables...",
        "The supplement that changed everything...",
        "How I fixed my sleep...",
        "The 5-minute hack for...",
        "What I eat in a day for...",
        "The routine that cured my...",
        "Signs your body is telling you...",
        "The health test everyone should take...",
        "Why you're always tired...",
        "The gut health secret...",
        "What happens when you stop...",
        "The daily habit that transformed me...",
        "My body's transformation story..."
    ],
    "curiosity": [
        "Wait for it...",
        "You'll never guess what happens next...",
        "The ending will shock you...",
        "Watch until the end...",
        "I bet you didn't know this...",
        "Here's something you've never seen...",
        "This changes everything...",
        "The secret nobody knows...",
        "You're not going to believe this...",
        "What I found will blow your mind...",
        "This is actually insane...",
        "I can't unsee this now...",
        "The thing everyone's been looking for...",
        "Finally, the answer to...",
        "This explains so much...",
        "The missing piece you need...",
        "Why didn't I know this before...",
        "This is what they're hiding...",
        "The truth finally revealed...",
        "What happens when you try..."
    ],
    "fear": [
        "If you don't do this now...",
        "The biggest mistake you're making...",
        "You're losing money by not...",
        "Stop doing this immediately...",
        "Warning signs you're ignoring...",
        "The silent killer of success...",
        "Why most people fail at...",
        "The trap everyone falls into...",
        "You're sabotaging yourself by...",
        "The costly error most make...",
        "Time is running out for...",
        "Don't wait until it's too late...",
        "The hidden danger of...",
        "What happens if you ignore...",
        "The risk you don't see coming...",
        "Why waiting is costing you...",
        "The problem with doing nothing...",
        "What you're losing every day...",
        "The mistake that cost me everything...",
        "If I had known earlier..."
    ],
    "desire": [
        "What if you could...",
        "Imagine waking up to...",
        "The life you deserve starts with...",
        "You're one step away from...",
        "Everything you've ever wanted...",
        "The shortcut to your dreams...",
        "What your future self will thank you for...",
        "The path to everything you want...",
        "How to finally achieve...",
        "The blueprint for your dream...",
        "This is how winners do it...",
        "Your transformation starts here...",
        "The opportunity you've been waiting for...",
        "How to get there faster...",
        "The key to unlocking...",
        "What success really looks like...",
        "The secret to getting what you want...",
        "How to make it happen...",
        "Your best life is waiting...",
        "The formula for achieving..."
    ],
    "scarcity": [
        "Only a few people know this...",
        "This won't be available for long...",
        "Limited spots remaining for...",
        "Before everyone finds out about...",
        "The window is closing on...",
        "Exclusive access to...",
        "Not everyone can do this...",
        "This is rare and valuable...",
        "While supplies last...",
        "The last chance to...",
        "First come, first served...",
        "Join the exclusive few who...",
        "This opportunity won't come again...",
        "Only for serious people...",
        "The elite secret is...",
        "Before the algorithm buries this...",
        "Save this before it's gone...",
        "The inside track to...",
        "What 1% of people have access to...",
        "This information is priceless..."
    ]
}

# Add more hooks dynamically
for category in HOOK_DATABASE:
    base_hooks = HOOK_DATABASE[category].copy()
    variations = []
    for hook in base_hooks[:10]:
        variations.extend([
            hook.replace("...", " - here's what happened..."),
            "🔥 " + hook,
            hook.upper(),
        ])
    HOOK_DATABASE[category].extend(variations[:15])

class HookCategory(BaseModel):
    category: str
    hooks: List[str]
    count: int
    is_pro: bool = False

class HookRequest(BaseModel):
    category: Optional[str] = None
    count: int = Field(default=10, ge=1, le=50)
    emotion: Optional[str] = None

@creator_pro_router.get("/hooks/categories")
async def get_hook_categories():
    """Get all hook categories with counts"""
    categories = []
    for cat, hooks in HOOK_DATABASE.items():
        categories.append({
            "category": cat,
            "count": len(hooks),
            "preview": hooks[:3],
            "is_pro": cat in ["luxury", "authority", "scarcity"]
        })
    return {"categories": categories, "total_hooks": sum(len(h) for h in HOOK_DATABASE.values())}

@creator_pro_router.get("/hooks/{category}")
async def get_hooks_by_category(category: str, limit: int = 20):
    """Get hooks from a specific category"""
    if category not in HOOK_DATABASE:
        raise HTTPException(status_code=404, detail="Category not found")
    
    hooks = HOOK_DATABASE[category]
    return {
        "category": category,
        "hooks": hooks[:limit],
        "total": len(hooks),
        "is_pro": category in ["luxury", "authority", "scarcity"]
    }

@creator_pro_router.post("/hooks/random")
async def get_random_hooks(data: HookRequest):
    """Get random hooks, optionally filtered"""
    all_hooks = []
    
    if data.category:
        if data.category not in HOOK_DATABASE:
            raise HTTPException(status_code=404, detail="Category not found")
        all_hooks = HOOK_DATABASE[data.category]
    else:
        for hooks in HOOK_DATABASE.values():
            all_hooks.extend(hooks)
    
    random.shuffle(all_hooks)
    return {"hooks": all_hooks[:data.count], "total_available": len(all_hooks)}

# =============================================================================
# HOOK ANALYZER - Rule-Based Scoring (No AI)
# =============================================================================
POWER_WORDS = [
    "secret", "exclusive", "limited", "free", "new", "proven", "guaranteed",
    "instant", "easy", "simple", "fast", "powerful", "ultimate", "essential",
    "shocking", "incredible", "amazing", "unbelievable", "revolutionary",
    "breakthrough", "discover", "unlock", "transform", "boost", "skyrocket",
    "massive", "huge", "critical", "urgent", "warning", "alert", "finally"
]

EMOTIONAL_TRIGGERS = [
    "love", "hate", "fear", "joy", "anger", "surprise", "sad", "happy",
    "excited", "worried", "anxious", "proud", "ashamed", "guilty", "grateful",
    "frustrated", "overwhelmed", "inspired", "motivated", "determined"
]

CURIOSITY_GAPS = [
    "...", "?", "secret", "hidden", "revealed", "truth", "discover",
    "find out", "learn", "uncover", "expose", "what happens", "why",
    "how", "the reason", "nobody knows", "you won't believe"
]

class HookAnalysisRequest(BaseModel):
    hook: str = Field(..., min_length=3, max_length=500)

class HookAnalysisResult(BaseModel):
    score: int
    breakdown: dict
    suggestions: List[str]
    grade: str

@creator_pro_router.post("/hooks/analyze")
async def analyze_hook(data: HookAnalysisRequest):
    """Analyze a hook and return score with suggestions (No AI - Rule Based)"""
    hook = data.hook.lower()
    hook_words = hook.split()
    
    score = 0
    breakdown = {}
    suggestions = []
    
    # Length check (ideal 6-12 words)
    word_count = len(hook_words)
    if 6 <= word_count <= 12:
        score += 20
        breakdown["length"] = {"score": 20, "status": "optimal", "value": word_count}
    elif word_count < 6:
        score += 10
        breakdown["length"] = {"score": 10, "status": "too_short", "value": word_count}
        suggestions.append("Add more words to create intrigue (aim for 6-12 words)")
    else:
        score += 10
        breakdown["length"] = {"score": 10, "status": "too_long", "value": word_count}
        suggestions.append("Shorten your hook for better impact (aim for 6-12 words)")
    
    # Power words check
    power_word_count = sum(1 for word in POWER_WORDS if word in hook)
    if power_word_count >= 2:
        score += 20
        breakdown["power_words"] = {"score": 20, "status": "excellent", "found": power_word_count}
    elif power_word_count == 1:
        score += 15
        breakdown["power_words"] = {"score": 15, "status": "good", "found": power_word_count}
        suggestions.append(f"Add more power words like: {', '.join(random.sample(POWER_WORDS, 3))}")
    else:
        score += 0
        breakdown["power_words"] = {"score": 0, "status": "missing", "found": 0}
        suggestions.append(f"Add power words like: {', '.join(random.sample(POWER_WORDS, 5))}")
    
    # Curiosity gap check
    has_curiosity = any(gap in hook for gap in CURIOSITY_GAPS)
    if has_curiosity:
        score += 20
        breakdown["curiosity_gap"] = {"score": 20, "status": "present"}
    else:
        score += 0
        breakdown["curiosity_gap"] = {"score": 0, "status": "missing"}
        suggestions.append("Add a curiosity gap with '...' or a question")
    
    # Emotional trigger check
    emotional_count = sum(1 for trigger in EMOTIONAL_TRIGGERS if trigger in hook)
    if emotional_count >= 1:
        score += 15
        breakdown["emotional_trigger"] = {"score": 15, "status": "present", "found": emotional_count}
    else:
        score += 0
        breakdown["emotional_trigger"] = {"score": 0, "status": "missing"}
        suggestions.append(f"Add emotional triggers like: {', '.join(random.sample(EMOTIONAL_TRIGGERS, 3))}")
    
    # Number check
    has_number = bool(re.search(r'\d+', hook))
    if has_number:
        score += 15
        breakdown["number"] = {"score": 15, "status": "present"}
    else:
        score += 5
        breakdown["number"] = {"score": 5, "status": "optional"}
        suggestions.append("Consider adding a specific number for credibility (e.g., '7 secrets', '$10K')")
    
    # First word impact check
    strong_starters = ["stop", "warning", "secret", "nobody", "the", "why", "how", "this", "what", "i"]
    first_word = hook_words[0] if hook_words else ""
    if first_word in strong_starters:
        score += 10
        breakdown["opening"] = {"score": 10, "status": "strong", "word": first_word}
    else:
        score += 5
        breakdown["opening"] = {"score": 5, "status": "average", "word": first_word}
        suggestions.append(f"Start with impact words like: {', '.join(random.sample(strong_starters, 4))}")
    
    # Determine grade
    if score >= 85:
        grade = "A+"
    elif score >= 75:
        grade = "A"
    elif score >= 65:
        grade = "B+"
    elif score >= 55:
        grade = "B"
    elif score >= 45:
        grade = "C"
    else:
        grade = "D"
    
    return {
        "original_hook": data.hook,
        "score": min(score, 100),
        "grade": grade,
        "breakdown": breakdown,
        "suggestions": suggestions[:5],
        "improved_version": generate_improved_hook(data.hook, suggestions)
    }

def generate_improved_hook(original: str, suggestions: List[str]) -> str:
    """Generate an improved version of the hook"""
    improved = original
    if "..." not in original:
        improved = improved.rstrip(".!?") + "..."
    if not any(word in original.lower() for word in POWER_WORDS[:5]):
        improved = random.choice(["🔥 ", "⚠️ ", "💡 "]) + improved
    return improved

# =============================================================================
# TRENDING FORMATS LIBRARY
# =============================================================================
TRENDING_FORMATS = {
    "pov": {
        "name": "POV Format",
        "description": "First-person perspective that makes viewers feel like they're living the experience",
        "template": "POV: You [action/situation]\n[Visual: Show the outcome/reaction]\n[Text overlay with relatable detail]",
        "examples": [
            "POV: You finally quit your 9-5 and this is day 1",
            "POV: You're watching this instead of doing what you should",
            "POV: The gym is empty at 5am and you own it"
        ],
        "best_for": ["lifestyle", "motivation", "comedy", "relatable"]
    },
    "storytime": {
        "name": "Storytime Format",
        "description": "Personal narrative that hooks viewers with drama and keeps them watching",
        "template": "Hook: [Dramatic statement]\nSetup: [Context - 5 sec]\nTension: [The problem/conflict]\nResolution: [What happened]\nLesson: [Takeaway]",
        "examples": [
            "Story time: The day I got fired changed everything",
            "So this thing happened at the airport...",
            "I've never told anyone this but..."
        ],
        "best_for": ["personal brand", "entertainment", "education"]
    },
    "three_mistakes": {
        "name": "3 Mistakes Format",
        "description": "List format highlighting common errors - educational and engaging",
        "template": "Hook: '3 mistakes that are [ruining/killing/destroying] your [topic]'\nMistake 1: [Most common]\nMistake 2: [Surprising one]\nMistake 3: [The one they didn't expect]\nBonus: [What to do instead]",
        "examples": [
            "3 mistakes killing your engagement",
            "3 mistakes that make you look poor",
            "3 mistakes in your morning routine"
        ],
        "best_for": ["education", "niche expertise", "tips"]
    },
    "unpopular_opinion": {
        "name": "Unpopular Opinion Format",
        "description": "Controversial take that drives engagement through debate",
        "template": "Hook: 'Unpopular opinion: [controversial statement]'\nReason 1: [Your logic]\nReason 2: [Supporting evidence]\nDefense: [Preempt criticism]\nCTA: [Invite discussion]",
        "examples": [
            "Unpopular opinion: College is a waste of time",
            "Unpopular opinion: Morning routines are overrated",
            "Unpopular opinion: Most advice is terrible"
        ],
        "best_for": ["thought leadership", "debate", "viral"]
    },
    "before_after": {
        "name": "Before/After Format",
        "description": "Transformation content showing clear contrast",
        "template": "Before: [The problem state - visual]\nThe process: [Quick montage/explanation]\nAfter: [The result - satisfying reveal]\nHow: [Brief explanation or CTA]",
        "examples": [
            "My room before vs after minimalism",
            "My income before vs after this side hustle",
            "My skin before vs after this routine"
        ],
        "best_for": ["transformation", "tutorials", "motivation"]
    },
    "day_in_life": {
        "name": "Day In Life Format",
        "description": "Behind-the-scenes content showing your daily routine",
        "template": "Morning: [Wake up routine - aspirational]\nWork: [What you actually do]\nBreak: [Lifestyle moment]\nEvening: [Wind down + productivity]\nEnd: [Reflection or motivation]",
        "examples": [
            "Day in my life as a 6-figure creator",
            "Realistic day in my life working from home",
            "Day in my life at 25 living alone"
        ],
        "best_for": ["lifestyle", "personal brand", "aspirational"]
    },
    "this_vs_that": {
        "name": "This vs That Format",
        "description": "Comparison content that helps viewers make decisions",
        "template": "Option A: [First choice]\nOption B: [Second choice]\nComparison: [Key differences]\nVerdict: [Your recommendation]\nWhy: [Brief reasoning]",
        "examples": [
            "iPhone vs Android in 2024",
            "Gym vs Home workouts",
            "$50 product vs $500 product"
        ],
        "best_for": ["reviews", "education", "decision-making"]
    },
    "ranking": {
        "name": "Ranking Format",
        "description": "List-based content ranking things from worst to best",
        "template": "Hook: 'Ranking [items] from worst to best'\n5th: [Worst - explain why]\n4th-2nd: [Quick progression]\n1st: [Best - detailed reason]\nHonorable mention: [Surprise pick]",
        "examples": [
            "Ranking fast food chains from worst to best",
            "Ranking side hustles by profit",
            "Ranking cities to live in your 20s"
        ],
        "best_for": ["entertainment", "reviews", "opinions"]
    }
}

@creator_pro_router.get("/formats")
async def get_trending_formats():
    """Get all trending content formats"""
    formats_list = []
    for key, data in TRENDING_FORMATS.items():
        formats_list.append({
            "id": key,
            "name": data["name"],
            "description": data["description"],
            "best_for": data["best_for"],
            "example_count": len(data["examples"])
        })
    return {"formats": formats_list, "total": len(formats_list)}

@creator_pro_router.get("/formats/{format_id}")
async def get_format_detail(format_id: str):
    """Get detailed format template and examples"""
    if format_id not in TRENDING_FORMATS:
        raise HTTPException(status_code=404, detail="Format not found")
    
    return TRENDING_FORMATS[format_id]

# =============================================================================
# VIRAL TITLE GENERATOR FOR YOUTUBE SHORTS
# =============================================================================
TITLE_TEMPLATES = {
    "curiosity": [
        "Nobody Talks About This...",
        "The Truth About {topic}...",
        "What They Don't Tell You About {topic}",
        "The Secret Behind {topic}",
        "Why {topic} Is Actually {twist}",
        "The Real Reason {topic} {action}",
        "What Happens When You {action}",
        "I Finally Discovered Why {topic}",
        "This Changes Everything About {topic}",
        "The Hidden Truth About {topic}"
    ],
    "transformation": [
        "I Tried {topic} For 30 Days...",
        "What Happened After {timeframe} Of {topic}",
        "From {before} To {after} In {timeframe}",
        "{topic} Changed My Life In {timeframe}",
        "My {topic} Transformation",
        "Before vs After {topic}",
        "The {topic} That Changed Everything",
        "How I Went From {before} To {after}",
        "{timeframe} Of {topic} Results",
        "My {timeframe} {topic} Journey"
    ],
    "listicle": [
        "{number} {topic} That Will {benefit}",
        "{number} Reasons Why {topic}",
        "{number} {topic} You Need To Try",
        "Top {number} {topic} In {year}",
        "{number} {topic} Mistakes To Avoid",
        "{number} {topic} Secrets Revealed",
        "{number} {topic} That Actually Work",
        "The {number} Best {topic}",
        "{number} {topic} For Beginners",
        "{number} {topic} Pros Don't Tell You"
    ],
    "shock": [
        "I Can't Believe This {topic}",
        "This {topic} Shocked Me",
        "You Won't Believe This {topic}",
        "The Most {adjective} {topic} Ever",
        "This {topic} Is Insane",
        "Wait For The {topic}...",
        "I Wasn't Expecting This {topic}",
        "The {topic} That Broke The Internet",
        "Everyone Is Wrong About {topic}",
        "This {topic} Will Blow Your Mind"
    ],
    "how_to": [
        "How To {action} In {timeframe}",
        "The Easiest Way To {action}",
        "How I {action} (Step By Step)",
        "The Simple Trick To {action}",
        "How To {action} Without {obstacle}",
        "The Best Way To {action}",
        "How To Actually {action}",
        "Quick Guide To {action}",
        "How To {action} Like A Pro",
        "{action} Made Simple"
    ]
}

class TitleGeneratorRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=100)
    style: Optional[str] = None
    count: int = Field(default=10, ge=1, le=20)

@creator_pro_router.post("/titles/generate")
async def generate_viral_titles(data: TitleGeneratorRequest):
    """Generate viral YouTube Shorts titles (Template-based, No AI)"""
    generated_titles = []
    
    styles = [data.style] if data.style and data.style in TITLE_TEMPLATES else list(TITLE_TEMPLATES.keys())
    
    for style in styles:
        templates = TITLE_TEMPLATES[style]
        for template in random.sample(templates, min(3, len(templates))):
            title = template.format(
                topic=data.topic,
                action=f"master {data.topic}",
                benefit=f"change your {data.topic.split()[0]} game",
                before="nothing",
                after="success",
                timeframe="30 days",
                number=random.choice(["3", "5", "7", "10"]),
                year="2024",
                adjective=random.choice(["insane", "incredible", "amazing", "shocking"]),
                obstacle="spending money",
                twist="a game changer"
            )
            generated_titles.append({
                "title": title,
                "style": style,
                "character_count": len(title)
            })
    
    random.shuffle(generated_titles)
    return {
        "titles": generated_titles[:data.count],
        "topic": data.topic,
        "tip": "Keep titles under 50 characters for best mobile display"
    }

# =============================================================================
# PERSONAL BRANDING BIO GENERATOR
# =============================================================================
BIO_TEMPLATES = {
    "instagram": {
        "professional": [
            "{title} | {niche} Expert\n💼 Helping {audience} {benefit}\n📍 {location}\n🔗 {cta}",
            "{emoji} {title} in {niche}\n{achievement}\n{cta_emoji} {cta}",
            "{niche} {title} | {personality}\n{tagline}\n{cta}"
        ],
        "personal": [
            "{personality} {title} 🌟\n{hobby} enthusiast | {niche} lover\n{cta}",
            "Just a {personality} {title} doing {niche} things ✨\n{tagline}",
            "{name} | {age}s | {location}\n{niche} journey 📈\n{cta}"
        ],
        "creator": [
            "Creating {content_type} about {niche} 🎬\n{followers}+ community\n{cta}",
            "{niche} Creator | {posting_schedule}\n{tagline}\n{cta}",
            "📱 {niche} content daily\n🎯 {mission}\n👇 {cta}"
        ]
    },
    "youtube": {
        "professional": [
            "Welcome to {channel_name}! 🎬\n\nI create {content_type} about {niche} to help you {benefit}.\n\n📅 New videos every {schedule}\n🔔 Subscribe for {promise}\n\n{cta}",
            "{channel_name} - Your go-to channel for {niche}!\n\nHere you'll find: {content_list}\n\n{achievement}\n\nSubscribe to join {followers}+ {audience}!"
        ]
    },
    "linkedin": {
        "professional": [
            "{title} | {company} | {niche} Expert\n\nI help {audience} {benefit} through {method}.\n\n{achievement}",
            "{title} specializing in {niche}\n{years}+ years of {expertise}\nPassionate about {passion}",
            "{niche} Professional | {title} at {company}\n\nAreas of expertise:\n• {skill1}\n• {skill2}\n• {skill3}"
        ]
    },
    "twitter": {
        "professional": [
            "{title} | {niche}\n{tagline}\n{cta}",
            "Building {project} | {niche} thoughts | {hobby}",
            "{emoji} {niche} {title}\n{achievement}\nDMs open for {offer}"
        ]
    },
    "tiktok": {
        "creator": [
            "{niche} creator 🎬\n{posting_schedule}\n{cta}",
            "Making {content_type} about {niche} ✨\n{tagline}",
            "{emoji} {personality} {title}\n{niche} content daily\n{cta}"
        ]
    }
}

class BioGeneratorRequest(BaseModel):
    platform: str = Field(..., description="instagram, youtube, linkedin, twitter, tiktok")
    style: str = Field(default="professional", description="professional, personal, creator")
    niche: str = Field(..., min_length=2, max_length=50)
    personality: Optional[str] = Field(default="passionate")
    name: Optional[str] = None
    title: Optional[str] = None
    achievement: Optional[str] = None
    cta: Optional[str] = "Link in bio"

@creator_pro_router.post("/bio/generate")
async def generate_bio(data: BioGeneratorRequest):
    """Generate platform-specific bios (Template-based)"""
    platform = data.platform.lower()
    style = data.style.lower()
    
    if platform not in BIO_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Platform not supported. Choose from: {list(BIO_TEMPLATES.keys())}")
    
    platform_templates = BIO_TEMPLATES[platform]
    if style not in platform_templates:
        style = list(platform_templates.keys())[0]
    
    templates = platform_templates[style]
    generated_bios = []
    
    for template in templates:
        bio = template.format(
            niche=data.niche,
            personality=data.personality or "passionate",
            title=data.title or f"{data.niche} Expert",
            name=data.name or "Creator",
            achievement=data.achievement or f"Sharing {data.niche} tips",
            cta=data.cta or "Link in bio",
            audience=f"{data.niche} enthusiasts",
            benefit=f"level up their {data.niche}",
            tagline=f"Making {data.niche} simple",
            location="Worldwide",
            emoji=random.choice(["🚀", "💡", "⭐", "🔥", "✨"]),
            cta_emoji=random.choice(["👇", "🔗", "📩", "💬"]),
            content_type="content",
            followers="10K",
            posting_schedule="New content daily",
            channel_name=f"{data.niche} Hub",
            schedule="week",
            promise=f"{data.niche} mastery",
            content_list=f"tips, tutorials, and {data.niche} insights",
            company="Self-employed",
            method="proven strategies",
            years="5",
            expertise=f"{data.niche} consulting",
            passion=f"helping others succeed in {data.niche}",
            skill1=f"{data.niche} Strategy",
            skill2="Content Creation",
            skill3="Community Building",
            project=f"the future of {data.niche}",
            hobby="coffee lover",
            offer="collaborations",
            age="20"
        )
        generated_bios.append({
            "bio": bio,
            "character_count": len(bio),
            "platform": platform,
            "style": style
        })
    
    return {
        "bios": generated_bios,
        "platform": platform,
        "tip": get_platform_tip(platform)
    }

def get_platform_tip(platform: str) -> str:
    tips = {
        "instagram": "Keep under 150 characters. Use line breaks and emojis strategically.",
        "youtube": "Include keywords for SEO. Mention upload schedule.",
        "linkedin": "Be professional. Include measurable achievements.",
        "twitter": "Max 160 characters. Be memorable and clear.",
        "tiktok": "Keep it fun and relatable. Emojis work well."
    }
    return tips.get(platform, "Be authentic and clear about your value proposition.")

# =============================================================================
# HASHTAG MATRIX (Curated Banks)
# =============================================================================
HASHTAG_BANKS = {
    "fitness": {
        "high_competition": ["fitness", "gym", "workout", "fitnessmotivation", "fit"],
        "medium_competition": ["fitfam", "gymmotivation", "workoutmotivation", "fitnessjourney", "fitlife"],
        "low_competition": ["fitnesstips2024", "homegymworkout", "beginnerfitness", "fitnessover30", "fitnessmindset"],
        "engagement": ["fitcheck", "gymbro", "liftingtiktok", "fitnessreels", "workouttok"]
    },
    "business": {
        "high_competition": ["business", "entrepreneur", "success", "motivation", "money"],
        "medium_competition": ["businessowner", "entrepreneurlife", "smallbusiness", "startuplife", "businesstips"],
        "low_competition": ["businessmindset2024", "solopreneurlife", "businesscoaching", "sidehustletips", "passiveincome2024"],
        "engagement": ["businesstok", "moneytok", "corporatetiktok", "9to5escape", "hustleculture"]
    },
    "beauty": {
        "high_competition": ["beauty", "makeup", "skincare", "beautytips", "makeupartist"],
        "medium_competition": ["beautyblogger", "makeuptutorial", "skincareroutine", "beautyhacks", "makeuplover"],
        "low_competition": ["cleanbeauty2024", "affordablemakeup", "drugstoremakeup", "skincareover30", "acnejourney"],
        "engagement": ["beautytok", "makeuptok", "grwm", "skincaretok", "beautycommunity"]
    },
    "food": {
        "high_competition": ["food", "foodie", "cooking", "recipe", "foodporn"],
        "medium_competition": ["foodblogger", "homecooking", "easyrecipes", "foodlover", "instafood"],
        "low_competition": ["mealprep2024", "budgetmeals", "healthyeating", "quickdinners", "airfryerrecipes"],
        "engagement": ["foodtok", "cookingtiktok", "recipetok", "foodasmr", "whatieatinaday"]
    },
    "travel": {
        "high_competition": ["travel", "wanderlust", "vacation", "travelgram", "adventure"],
        "medium_competition": ["travelblogger", "travellife", "exploremore", "travelphotography", "bucketlist"],
        "low_competition": ["budgettravel2024", "solotravel", "hiddengems", "traveltips2024", "digitalnomad"],
        "engagement": ["traveltok", "travelreels", "packingtips", "airportlife", "hotelreview"]
    },
    "parenting": {
        "high_competition": ["parenting", "mom", "momlife", "motherhood", "kids"],
        "medium_competition": ["parentingtips", "toddlermom", "boymom", "girlmom", "parenthood"],
        "low_competition": ["gentleparenting", "momhacks2024", "toddleractivities", "momof3", "parentingwin"],
        "engagement": ["momtok", "parentingtiktok", "momsoftiktok", "dadtok", "familyvlog"]
    },
    "motivation": {
        "high_competition": ["motivation", "success", "mindset", "goals", "inspiration"],
        "medium_competition": ["motivationalquotes", "successmindset", "growthmindset", "selfimprovement", "positivity"],
        "low_competition": ["morningmotivation", "motivationdaily", "mindsetcoach", "goalsetting2024", "levelup"],
        "engagement": ["motivationtok", "selfhelptok", "growthtok", "mindsetcheck", "dailymotivation"]
    }
}

class HashtagRequest(BaseModel):
    niche: str
    count: int = Field(default=30, ge=10, le=50)
    include_engagement: bool = True
    location: Optional[str] = None

@creator_pro_router.post("/hashtags/generate")
async def generate_hashtags(data: HashtagRequest):
    """Generate optimized hashtag mix from curated banks"""
    niche = data.niche.lower().replace(" ", "")
    
    # Find closest matching niche
    available_niches = list(HASHTAG_BANKS.keys())
    matched_niche = None
    for n in available_niches:
        if n in niche or niche in n:
            matched_niche = n
            break
    
    if not matched_niche:
        matched_niche = random.choice(available_niches)
    
    bank = HASHTAG_BANKS[matched_niche]
    
    # Build optimized mix (30/30/30/10 strategy)
    hashtags = []
    
    # 30% high competition (reach)
    high = random.sample(bank["high_competition"], min(int(data.count * 0.3), len(bank["high_competition"])))
    hashtags.extend([{"tag": f"#{h}", "competition": "high"} for h in high])
    
    # 30% medium competition (balance)
    medium = random.sample(bank["medium_competition"], min(int(data.count * 0.3), len(bank["medium_competition"])))
    hashtags.extend([{"tag": f"#{h}", "competition": "medium"} for h in medium])
    
    # 30% low competition (discovery)
    low = random.sample(bank["low_competition"], min(int(data.count * 0.3), len(bank["low_competition"])))
    hashtags.extend([{"tag": f"#{h}", "competition": "low"} for h in low])
    
    # 10% engagement tags
    if data.include_engagement:
        engagement = random.sample(bank["engagement"], min(int(data.count * 0.1) + 1, len(bank["engagement"])))
        hashtags.extend([{"tag": f"#{h}", "competition": "engagement"} for h in engagement])
    
    # Add location tags if specified
    if data.location:
        location_tags = [
            f"#{data.location.lower().replace(' ', '')}",
            f"#{data.location.lower().replace(' ', '')}life",
            f"#{data.location.lower().replace(' ', '')}creator"
        ]
        hashtags.extend([{"tag": t, "competition": "location"} for t in location_tags[:2]])
    
    return {
        "hashtags": hashtags[:data.count],
        "total": len(hashtags),
        "niche_matched": matched_niche,
        "copy_text": " ".join([h["tag"] for h in hashtags[:data.count]]),
        "strategy": "30% high (reach) + 30% medium (balance) + 30% low (discovery) + 10% engagement"
    }

@creator_pro_router.get("/hashtags/niches")
async def get_available_hashtag_niches():
    """Get all available hashtag niches"""
    return {
        "niches": list(HASHTAG_BANKS.keys()),
        "total": len(HASHTAG_BANKS)
    }

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = ['creator_pro_router']
