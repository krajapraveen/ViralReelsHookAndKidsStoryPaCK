"""
Convert Tools Routes - Convert content between formats
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid
import random

router = APIRouter(prefix="/convert", tags=["Convert Tools"])

# Import from main server
from server import get_current_user, db

# =============================================================================
# CONVERSION TEMPLATES
# =============================================================================

CAROUSEL_TEMPLATE = {
    "slides": 7,
    "structure": ["Hook", "Problem", "Solution 1", "Solution 2", "Solution 3", "Example", "CTA"]
}

YOUTUBE_SCRIPT_TEMPLATE = {
    "sections": [
        {"name": "Hook", "duration": "0-15s", "description": "Grab attention immediately"},
        {"name": "Intro", "duration": "15-30s", "description": "Introduce yourself and topic"},
        {"name": "Main Content", "duration": "30s-8min", "description": "Deliver value"},
        {"name": "Recap", "duration": "Last 30s", "description": "Summarize key points"},
        {"name": "CTA", "duration": "Final 15s", "description": "Like, subscribe, comment"}
    ]
}

MORAL_QUOTE_TEMPLATES = [
    "'{moral}' - A lesson from {title}",
    "What {character} taught us: {moral}",
    "The wisdom from '{title}': {moral}",
    "Remember: {moral} ✨",
    "Life lesson from {title}: {moral}"
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/reel-to-carousel")
async def convert_reel_to_carousel(
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """Convert a reel script to carousel format - 1 credit"""
    credits_needed = 1
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credit.")
    
    # Get the reel generation
    reel_gen = await db.generations.find_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "REEL"
    }, {"_id": 0})
    
    if not reel_gen:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    reel = reel_gen.get("outputJson", {})
    
    # Convert to carousel format
    carousel = {
        "original_reel_id": generation_id,
        "slides": [],
        "caption": reel.get("caption_long", ""),
        "hashtags": reel.get("hashtags", [])
    }
    
    # Slide 1: Hook
    carousel["slides"].append({
        "slide_number": 1,
        "type": "hook",
        "text": reel.get("best_hook", ""),
        "design_tip": "Bold text, eye-catching colors"
    })
    
    # Middle slides: Extract from script scenes
    script = reel.get("script", {})
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes[:5], 2):
        carousel["slides"].append({
            "slide_number": i,
            "type": "content",
            "text": scene.get("on_screen_text", "") or scene.get("voiceover", "")[:100],
            "visual_notes": ", ".join(scene.get("broll", [])[:2]) if scene.get("broll") else ""
        })
    
    # Final slide: CTA
    carousel["slides"].append({
        "slide_number": len(carousel["slides"]) + 1,
        "type": "cta",
        "text": script.get("cta", "Follow for more!"),
        "design_tip": "Clear call-to-action with your handle"
    })
    
    # Deduct credit
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
        "description": "Convert: Reel to Carousel",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save conversion
    conversion_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": conversion_id,
        "userId": user["id"],
        "type": "CAROUSEL",
        "status": "COMPLETED",
        "inputJson": {"source_type": "REEL", "source_id": generation_id},
        "outputJson": carousel,
        "creditsUsed": credits_needed,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "generationId": conversion_id,
        "carousel": carousel,
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }


@router.post("/reel-to-youtube")
async def convert_reel_to_youtube(
    generation_id: str,
    target_duration: str = "5-10min",
    user: dict = Depends(get_current_user)
):
    """Convert a reel script to YouTube script - 2 credits"""
    credits_needed = 2
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    # Get the reel generation
    reel_gen = await db.generations.find_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "REEL"
    }, {"_id": 0})
    
    if not reel_gen:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    reel = reel_gen.get("outputJson", {})
    script = reel.get("script", {})
    
    # Convert to YouTube format
    youtube_script = {
        "original_reel_id": generation_id,
        "target_duration": target_duration,
        "title_options": [
            reel.get("best_hook", ""),
            f"The Truth About {reel.get('best_hook', '')[:30]}...",
            f"You Won't Believe What I Found Out About {reel.get('best_hook', '')[:20]}"
        ],
        "thumbnail_texts": [
            reel.get("best_hook", "")[:20].upper() + "!",
            "SHOCKING" if "secret" in reel.get("best_hook", "").lower() else "MUST WATCH",
            "I WAS WRONG"
        ],
        "sections": []
    }
    
    # Hook section (expanded from reel hook)
    youtube_script["sections"].append({
        "name": "Hook",
        "timestamp": "0:00 - 0:30",
        "content": f"Open with: {reel.get('best_hook', '')}\n\nExpand on why this matters to the viewer. Create urgency.",
        "b_roll": "Quick cuts, text overlays, dramatic music"
    })
    
    # Intro section
    youtube_script["sections"].append({
        "name": "Introduction",
        "timestamp": "0:30 - 1:30",
        "content": f"Introduce yourself.\nPromise what viewers will learn.\nTeaser of the main points.",
        "b_roll": "Face cam, branded intro animation"
    })
    
    # Main content (expanded from reel scenes)
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes[:4], 1):
        youtube_script["sections"].append({
            "name": f"Main Point {i}",
            "timestamp": f"{i+1}:30 - {i+3}:00",
            "content": f"Expand on: {scene.get('voiceover', scene.get('on_screen_text', ''))}\n\nAdd examples, stories, data to support this point.",
            "b_roll": ", ".join(scene.get("broll", ["Relevant footage"])) if scene.get("broll") else "Supporting visuals"
        })
    
    # Recap
    youtube_script["sections"].append({
        "name": "Recap",
        "timestamp": f"{len(scenes)+3}:00 - {len(scenes)+4}:00",
        "content": "Summarize the key takeaways:\n" + "\n".join([f"- Point {i+1}" for i in range(min(4, len(scenes)))]),
        "b_roll": "Text overlay with bullet points"
    })
    
    # CTA
    youtube_script["sections"].append({
        "name": "Call to Action",
        "timestamp": "Final minute",
        "content": f"Original CTA: {script.get('cta', '')}\n\nExpanded: Ask viewers to like, subscribe, comment their experience. Tease next video.",
        "b_roll": "Subscribe animation, end screen with video suggestions"
    })
    
    # Description template
    youtube_script["description_template"] = f"""
{reel.get('caption_long', '')}

📌 TIMESTAMPS:
0:00 - Hook
0:30 - Introduction
1:30 - Main Content
[Add more timestamps]

🔔 Don't forget to SUBSCRIBE and hit the notification bell!

📱 Follow me on Instagram: @yourhandle

#shorts #youtube #{' #'.join(reel.get('hashtags', ['viral'])[:5])}
"""
    
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
        "description": "Convert: Reel to YouTube Script",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save conversion
    conversion_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": conversion_id,
        "userId": user["id"],
        "type": "YOUTUBE_SCRIPT",
        "status": "COMPLETED",
        "inputJson": {"source_type": "REEL", "source_id": generation_id, "target_duration": target_duration},
        "outputJson": youtube_script,
        "creditsUsed": credits_needed,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "generationId": conversion_id,
        "youtube_script": youtube_script,
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }


@router.post("/story-to-reel")
async def convert_story_to_reel(
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """Convert a kids story to short reel format - 1 credit"""
    credits_needed = 1
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credit.")
    
    # Get the story generation
    story_gen = await db.generations.find_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "STORY"
    }, {"_id": 0})
    
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    
    # Convert to reel format (30-60 second summary)
    reel_script = {
        "original_story_id": generation_id,
        "duration": "30-60s",
        "hooks": [
            f"This story will make your kids {random.choice(['smile', 'think', 'laugh', 'dream'])}",
            f"The magical tale of {story.get('title', 'adventure')}",
            f"A beautiful lesson about {story.get('moral', 'life')[:30]}",
            "Storytime with the kids! 📚",
            f"Why every child should hear the story of {story.get('title', '')[:20]}"
        ],
        "best_hook": f"This story will change how your kids see {story.get('moral', 'the world')[:20]}",
        "script": {
            "scenes": [
                {
                    "time": "0-5s",
                    "on_screen_text": story.get("title", "Story Time"),
                    "voiceover": f"Let me tell you the story of {story.get('title', 'a magical adventure')}",
                    "visual": "Book opening animation or title card"
                },
                {
                    "time": "5-15s",
                    "on_screen_text": "The Beginning",
                    "voiceover": story.get("synopsis", "Once upon a time...")[:150],
                    "visual": "Scene 1 illustration or animated characters"
                },
                {
                    "time": "15-25s",
                    "on_screen_text": "The Adventure",
                    "voiceover": f"Our hero faced challenges but learned something important...",
                    "visual": "Key story moments montage"
                },
                {
                    "time": "25-30s",
                    "on_screen_text": story.get("moral", "The Lesson"),
                    "voiceover": f"The moral: {story.get('moral', 'Be kind to everyone')}",
                    "visual": "Beautiful ending scene"
                }
            ],
            "cta": "Follow for more bedtime stories! 📖✨"
        },
        "caption_short": f"📚 {story.get('title', 'Story Time')} - A story about {story.get('moral', 'life')[:30]}",
        "caption_long": f"""📚 {story.get('title', 'Story Time')}

{story.get('synopsis', '')}

Moral: {story.get('moral', '')}

Save this for bedtime! ❤️

#kidsstory #bedtimestory #parenting #storytime #moralstory #childrensbook #familytime""",
        "hashtags": ["kidsstory", "bedtimestory", "parenting", "storytime", "moralstory", "childrensbook", "familytime", "momlife", "dadlife", "toddlermom", "preschool", "reading", "education", "learning", "kids"]
    }
    
    # Deduct credit
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
        "description": f"Convert: Story to Reel - {story.get('title', '')[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save conversion
    conversion_id = str(uuid.uuid4())
    await db.generations.insert_one({
        "id": conversion_id,
        "userId": user["id"],
        "type": "REEL",
        "status": "COMPLETED",
        "inputJson": {"source_type": "STORY", "source_id": generation_id},
        "outputJson": reel_script,
        "creditsUsed": credits_needed,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "generationId": conversion_id,
        "reel_script": reel_script,
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }


@router.post("/story-to-quote")
async def convert_story_to_moral_quote(
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """Convert a story's moral to shareable quotes - Free"""
    # Get the story generation
    story_gen = await db.generations.find_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "STORY"
    }, {"_id": 0})
    
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    title = story.get("title", "Story")
    moral = story.get("moral", "Be kind to everyone")
    characters = story.get("characters", [])
    main_char = characters[0].get("name", "the hero") if characters else "the hero"
    
    # Generate quote variations
    quotes = []
    for template in MORAL_QUOTE_TEMPLATES:
        quote = template.replace("{moral}", moral)
        quote = quote.replace("{title}", title)
        quote = quote.replace("{character}", main_char)
        quotes.append(quote)
    
    # Add some creative variations
    quotes.extend([
        f"🌟 {moral}",
        f"Today's lesson: {moral}",
        f"From the story '{title}':\n\n\"{moral}\"",
        f"What {main_char} learned: {moral} ✨"
    ])
    
    return {
        "success": True,
        "story_title": title,
        "moral": moral,
        "quotes": quotes,
        "hashtags": ["morals", "lifelessons", "wisdom", "kidswisdom", "parenting", "teachingkids", "values", "inspiration"],
        "tip": "Use these quotes for Instagram stories, Pinterest pins, or as standalone posts!"
    }
