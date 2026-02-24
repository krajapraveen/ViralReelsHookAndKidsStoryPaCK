"""
Convert Tools Routes - Content Conversion and Repurposing
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, Form, Query
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
    db, logger, get_current_user, deduct_credits, FILE_EXPIRY_MINUTES,
    LLM_AVAILABLE, EMERGENT_LLM_KEY
)

router = APIRouter(prefix="/convert", tags=["Convert Tools"])

# Conversion costs - Updated to 10 credits for main conversions
CONVERSION_COSTS = {
    "reel_to_carousel": 10,
    "reel_to_youtube": 10,
    "story_to_reel": 10,
    "story_to_quote": 0,  # FREE
    "text_to_story": 10,
    "text_to_reel": 15
}


@router.post("/reel-to-carousel")
async def convert_reel_to_carousel(
    generation_id: str = Query(None, description="Optional: specific reel ID"),
    use_recent: bool = Query(False, description="Use most recent reel"),
    user: dict = Depends(get_current_user)
):
    """Convert a reel script to carousel format (5 credits)"""
    
    # Find the reel to convert
    if use_recent or not generation_id:
        generation = await db.generations.find_one(
            {"userId": user["id"], "type": "REEL"},
            {"_id": 0},
            sort=[("createdAt", -1)]
        )
    else:
        generation = await db.generations.find_one(
            {"id": generation_id, "userId": user["id"], "type": "REEL"},
            {"_id": 0}
        )
    
    if not generation:
        raise HTTPException(status_code=404, detail="No reel found. Generate a reel first!")
    
    cost = CONVERSION_COSTS["reel_to_carousel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    reel_data = generation.get("outputJson", {})
    script = reel_data.get("script", {})
    topic = generation.get("topic", "Your Topic")
    
    # Create carousel with real content from the reel
    carousel = {
        "id": str(uuid.uuid4()),
        "sourceId": generation.get("id"),
        "type": "carousel",
        "topic": topic,
        "slides": []
    }
    
    # Cover slide using the best hook
    best_hook = reel_data.get("best_hook", reel_data.get("hooks", ["Swipe to learn more"])[0] if reel_data.get("hooks") else "Swipe to learn more")
    carousel["slides"].append({
        "slideNumber": 1,
        "type": "cover",
        "headline": best_hook,
        "subheadline": "Swipe for insights →",
        "designTip": "Use bold text, eye-catching colors"
    })
    
    # Content slides from scenes
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes[:7], start=2):
        on_screen = scene.get("on_screen_text", scene.get("text", ""))
        voiceover = scene.get("voiceover", scene.get("narration", ""))
        
        carousel["slides"].append({
            "slideNumber": i,
            "type": "content",
            "headline": f"Point {i-1}",
            "body": on_screen if on_screen else voiceover[:150] if voiceover else f"Key insight #{i-1}",
            "designTip": "Keep it visual with icons"
        })
    
    # CTA slide
    cta = script.get("cta", "Follow for more tips!")
    carousel["slides"].append({
        "slideNumber": len(carousel["slides"]) + 1,
        "type": "cta",
        "headline": "Want More?",
        "cta": cta,
        "designTip": "Include your handle prominently"
    })
    
    # Save the conversion
    await db.conversions.insert_one({
        "id": carousel["id"],
        "userId": user["id"],
        "type": "reel_to_carousel",
        "sourceId": generation.get("id"),
        "output": carousel,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await deduct_credits(user["id"], cost, "Reel to Carousel conversion")
    
    return {
        "success": True,
        "carousel": carousel,
        "creditsUsed": cost,
        "message": f"Converted reel '{topic}' to {len(carousel['slides'])}-slide carousel!"
    }


@router.post("/reel-to-youtube")
async def convert_reel_to_youtube(
    generation_id: str = Query(None, description="Optional: specific reel ID"),
    use_recent: bool = Query(False, description="Use most recent reel"),
    user: dict = Depends(get_current_user)
):
    """Expand a reel script to YouTube video format (2 credits)"""
    
    # Find the reel to convert
    if use_recent or not generation_id:
        generation = await db.generations.find_one(
            {"userId": user["id"], "type": "REEL"},
            {"_id": 0},
            sort=[("createdAt", -1)]
        )
    else:
        generation = await db.generations.find_one(
            {"id": generation_id, "userId": user["id"], "type": "REEL"},
            {"_id": 0}
        )
    
    if not generation:
        raise HTTPException(status_code=404, detail="No reel found. Generate a reel first!")
    
    cost = CONVERSION_COSTS["reel_to_youtube"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    reel_data = generation.get("outputJson", {})
    script = reel_data.get("script", {})
    topic = generation.get("topic", "Your Topic")
    niche = generation.get("niche", "General")
    
    # Expand to YouTube format
    youtube_script = {
        "id": str(uuid.uuid4()),
        "sourceId": generation.get("id"),
        "type": "youtube_video",
        "title": f"{topic} - Complete Guide",
        "description": f"In this video, we dive deep into {topic}. Perfect for anyone interested in {niche.lower()} content.",
        "estimatedLength": "8-10 minutes",
        "sections": [
            {
                "section": "Hook (0:00 - 0:30)",
                "content": reel_data.get("best_hook", "Welcome back to the channel!"),
                "tips": "Start strong with the hook from your reel"
            },
            {
                "section": "Introduction (0:30 - 1:30)",
                "content": f"Today we're going to explore {topic} in detail. By the end of this video, you'll have a complete understanding of everything you need to know.",
                "tips": "Tell viewers what they'll learn"
            }
        ],
        "mainContent": [],
        "outro": {
            "section": "Outro & CTA (8:00 - 10:00)",
            "content": script.get("cta", "Don't forget to like, subscribe, and hit the notification bell!"),
            "tips": "Remind viewers to subscribe and check out related videos"
        },
        "hashtags": reel_data.get("hashtags", ["#youtube", "#tutorial", f"#{niche.lower()}"]),
        "seoTags": [topic.lower(), niche.lower(), "tutorial", "guide", "tips"]
    }
    
    # Expand scenes to main content sections
    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes, start=1):
        expanded_section = {
            "section": f"Point {i} ({1 + i}:30 - {2 + i}:30)",
            "originalContent": scene.get("on_screen_text", scene.get("voiceover", "")),
            "expandedContent": f"Let's dive deeper into point {i}. {scene.get('voiceover', scene.get('on_screen_text', 'Here is the key insight...'))} This is important because it helps you understand the bigger picture.",
            "visualSuggestion": scene.get("visual_suggestion", "Show relevant B-roll or graphics")
        }
        youtube_script["mainContent"].append(expanded_section)
    
    # Save the conversion
    await db.conversions.insert_one({
        "id": youtube_script["id"],
        "userId": user["id"],
        "type": "reel_to_youtube",
        "sourceId": generation.get("id"),
        "output": youtube_script,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await deduct_credits(user["id"], cost, "Reel to YouTube conversion")
    
    return {
        "success": True,
        "youtubeScript": youtube_script,
        "creditsUsed": cost,
        "message": f"Expanded reel to ~10 minute YouTube script!"
    }


@router.post("/story-to-reel")
async def convert_story_to_reel(
    generation_id: str = Query(None, description="Optional: specific story ID"),
    use_recent: bool = Query(False, description="Use most recent story"),
    user: dict = Depends(get_current_user)
):
    """Convert a story to reel format (5 credits)"""
    
    # Find the story to convert
    if use_recent or not generation_id:
        generation = await db.generations.find_one(
            {"userId": user["id"], "type": "STORY"},
            {"_id": 0},
            sort=[("createdAt", -1)]
        )
    else:
        generation = await db.generations.find_one(
            {"id": generation_id, "userId": user["id"], "type": "STORY"},
            {"_id": 0}
        )
    
    if not generation:
        raise HTTPException(status_code=404, detail="No story found. Generate a story first!")
    
    cost = CONVERSION_COSTS["story_to_reel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    story_data = generation.get("outputJson", {})
    title = story_data.get("title", "Story")
    moral = story_data.get("moral", "Every story has a lesson")
    genre = story_data.get("genre", "Adventure")
    scenes = story_data.get("scenes", [])
    
    # Create engaging reel hooks based on the story
    hooks = [
        f"This story about {title.lower()} will change how you think!",
        f"3 life lessons hidden in '{title}'",
        f"What '{title}' teaches us about {moral.lower().split()[0]}",
        f"A {genre.lower()} story with a powerful message",
        f"Wait until you hear the ending of '{title}'!"
    ]
    
    # Convert to reel format
    reel = {
        "id": str(uuid.uuid4()),
        "sourceId": generation.get("id"),
        "type": "reel",
        "title": f"Story Time: {title}",
        "hooks": hooks,
        "best_hook": random.choice(hooks),
        "script": {
            "scenes": [],
            "cta": f"Follow for more {genre.lower()} stories and life lessons!"
        },
        "caption_short": f"The moral of '{title}' will surprise you!",
        "caption_long": f"Every great story has a lesson. '{title}' teaches us: {moral}. What story changed YOUR life? Comment below!",
        "hashtags": ["#storytime", "#kidsstory", "#lifelessons", "#storytelling", "#viral", "#parenting", f"#{genre.lower()}"],
        "posting_tips": [
            "Use calm, engaging voiceover",
            "Add gentle background music",
            "Show story visuals or text overlays",
            "End with the moral as text on screen"
        ]
    }
    
    # Convert story scenes to reel scenes
    total_duration = 60  # 60 second reel
    scene_duration = total_duration // min(len(scenes), 6)
    
    for i, scene in enumerate(scenes[:6]):
        start_time = i * scene_duration
        end_time = start_time + scene_duration
        
        narration = scene.get("narration", "")[:100] if scene.get("narration") else ""
        visual = scene.get("visualDescription", "Story visual")
        
        reel["script"]["scenes"].append({
            "sceneNumber": i + 1,
            "time": f"{start_time}-{end_time}s",
            "text": narration,
            "visual_suggestion": visual,
            "on_screen_text": scene.get("sceneTitle", f"Part {i+1}")
        })
    
    # Add moral as final scene if we have room
    if len(scenes) < 6:
        reel["script"]["scenes"].append({
            "sceneNumber": len(reel["script"]["scenes"]) + 1,
            "time": "50-60s",
            "text": moral,
            "visual_suggestion": "Text overlay with moral",
            "on_screen_text": f"The Lesson: {moral}"
        })
    
    # Save the conversion
    await db.conversions.insert_one({
        "id": reel["id"],
        "userId": user["id"],
        "type": "story_to_reel",
        "sourceId": generation.get("id"),
        "output": reel,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await deduct_credits(user["id"], cost, "Story to Reel conversion")
    
    return {
        "success": True,
        "reel": reel,
        "creditsUsed": cost,
        "message": f"Converted '{title}' to a 60-second reel!"
    }


@router.post("/story-to-quote")
async def convert_story_to_quote(
    generation_id: str = Query(None, description="Optional: specific story ID"),
    use_recent: bool = Query(False, description="Use most recent story"),
    user: dict = Depends(get_current_user)
):
    """Extract quotes from story - FREE"""
    
    # Find the story to convert
    if use_recent or not generation_id:
        generation = await db.generations.find_one(
            {"userId": user["id"], "type": "STORY"},
            {"_id": 0},
            sort=[("createdAt", -1)]
        )
    else:
        generation = await db.generations.find_one(
            {"id": generation_id, "userId": user["id"], "type": "STORY"},
            {"_id": 0}
        )
    
    if not generation:
        raise HTTPException(status_code=404, detail="No story found. Generate a story first!")
    
    story_data = generation.get("outputJson", {})
    title = story_data.get("title", "Story")
    moral = story_data.get("moral", "Every adventure begins with a single step")
    genre = story_data.get("genre", "Adventure")
    scenes = story_data.get("scenes", [])
    
    # Generate meaningful quotes
    quotes = [
        {
            "quote": f'"{moral}"',
            "source": f"— {title}",
            "type": "moral",
            "designSuggestion": "Use this as the main quote card"
        },
        {
            "quote": f'"In the world of {genre.lower()}, anything is possible when you believe."',
            "source": f"— Inspired by {title}",
            "type": "inspirational",
            "designSuggestion": "Perfect for Instagram stories"
        },
        {
            "quote": '"The greatest lessons come from the smallest moments."',
            "source": f"— {title}",
            "type": "wisdom",
            "designSuggestion": "Great for Pinterest"
        },
        {
            "quote": f'"Every ending is just a new beginning waiting to unfold."',
            "source": "— Story wisdom",
            "type": "philosophical",
            "designSuggestion": "Use with sunset/sunrise imagery"
        }
    ]
    
    # Extract quotes from scenes if available
    for scene in scenes[:3]:
        narration = scene.get("narration", "")
        if narration and len(narration) > 20:
            # Take a meaningful snippet
            sentences = narration.split('.')
            if sentences:
                snippet = sentences[0].strip()
                if len(snippet) > 15:
                    quotes.append({
                        "quote": f'"{snippet}."',
                        "source": f"— {title}",
                        "type": "narrative",
                        "designSuggestion": "Use as a carousel slide"
                    })
    
    result = {
        "id": str(uuid.uuid4()),
        "sourceId": generation.get("id"),
        "storyTitle": title,
        "quotes": quotes,
        "shareablePack": {
            "instagramStory": quotes[0] if quotes else None,
            "twitterPost": quotes[1] if len(quotes) > 1 else None,
            "pinterestPin": quotes[2] if len(quotes) > 2 else None
        },
        "hashtags": ["#quotes", "#wisdom", "#storytime", f"#{genre.lower()}", "#inspiration", "#motivation"]
    }
    
    # Save the conversion
    await db.conversions.insert_one({
        "id": result["id"],
        "userId": user["id"],
        "type": "story_to_quote",
        "sourceId": generation.get("id"),
        "output": result,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "result": result,
        "creditsUsed": 0,
        "message": f"Extracted {len(quotes)} quotes from '{title}'!"
    }


@router.post("/text-to-story")
async def convert_text_to_story(
    text: str = Form(...),
    genre: str = Form("Adventure"),
    age_group: str = Form("4-6"),
    user: dict = Depends(get_current_user)
):
    """Convert any text to a kids story (10 credits)"""
    cost = CONVERSION_COSTS["text_to_story"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text too short. Provide at least 10 characters.")
    
    # Create conversion job
    job_id = str(uuid.uuid4())
    
    # Extract key themes from text
    words = text.lower().split()
    theme_word = words[0] if words else "magic"
    
    # Generate story
    story_output = {
        "title": f"The {theme_word.title()} Adventure",
        "synopsis": f"A {genre.lower()} story inspired by: {text[:100]}",
        "genre": genre,
        "ageGroup": age_group,
        "moral": "Every adventure teaches us something new about ourselves",
        "scenes": [
            {
                "sceneNumber": 1,
                "sceneTitle": "The Beginning",
                "narration": f"Once upon a time, in a magical land, there was a curious soul who discovered something wonderful about {theme_word}...",
                "visualDescription": "A colorful scene setting the stage for adventure"
            },
            {
                "sceneNumber": 2,
                "sceneTitle": "The Discovery",
                "narration": f"As they explored further, they realized that {text[:50]}... was more than what it seemed.",
                "visualDescription": "A moment of wonder and discovery"
            },
            {
                "sceneNumber": 3,
                "sceneTitle": "The Challenge",
                "narration": "But every adventure has its challenges. They had to be brave and trust their heart.",
                "visualDescription": "A dramatic scene showing courage"
            },
            {
                "sceneNumber": 4,
                "sceneTitle": "The Triumph",
                "narration": "With courage and kindness, they overcame every obstacle in their path.",
                "visualDescription": "A triumphant moment of success"
            },
            {
                "sceneNumber": 5,
                "sceneTitle": "The Happy Ending",
                "narration": "And so, they learned that the greatest treasures are the lessons we learn along the way.",
                "visualDescription": "A warm, happy ending scene"
            }
        ]
    }
    
    # Save conversion
    await db.conversions.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_story",
        "input": {"text": text[:2000], "genre": genre, "ageGroup": age_group},
        "output": story_output,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await deduct_credits(user["id"], cost, "Text to Story conversion")
    
    return {
        "success": True,
        "jobId": job_id,
        "story": story_output,
        "creditsUsed": cost,
        "message": f"Created '{story_output['title']}' from your text!"
    }


@router.post("/text-to-reel")
async def convert_text_to_reel(
    text: str = Form(...),
    niche: str = Form("General"),
    tone: str = Form("Engaging"),
    user: dict = Depends(get_current_user)
):
    """Convert any text to a reel script (15 credits)"""
    cost = CONVERSION_COSTS["text_to_reel"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text too short. Provide at least 10 characters.")
    
    job_id = str(uuid.uuid4())
    
    # Extract key phrase
    key_phrase = text[:30].strip()
    
    # Generate reel
    reel_output = {
        "id": job_id,
        "hooks": [
            f"Stop scrolling! You NEED to know this about {key_phrase}...",
            f"This {niche.lower()} secret changed everything for me",
            f"3 things about {key_phrase} nobody tells you",
            f"POV: You just discovered the truth about {key_phrase}",
            f"Wait for it... this is game-changing"
        ],
        "best_hook": f"Stop scrolling! You NEED to know this about {key_phrase}...",
        "script": {
            "scenes": [
                {
                    "sceneNumber": 1,
                    "time": "0-5s",
                    "on_screen_text": "STOP SCROLLING",
                    "voiceover": f"If you're into {niche.lower()}, you need to hear this.",
                    "visual_suggestion": "Face to camera, energetic"
                },
                {
                    "sceneNumber": 2,
                    "time": "5-15s",
                    "on_screen_text": key_phrase[:40],
                    "voiceover": f"Here's the thing about {text[:50]}...",
                    "visual_suggestion": "Show text overlay or B-roll"
                },
                {
                    "sceneNumber": 3,
                    "time": "15-30s",
                    "on_screen_text": "THE SECRET",
                    "voiceover": f"{text[50:150] if len(text) > 50 else 'This insight will change how you think'}",
                    "visual_suggestion": "Demonstrate or show proof"
                },
                {
                    "sceneNumber": 4,
                    "time": "30-45s",
                    "on_screen_text": "ACTION STEP",
                    "voiceover": "Here's exactly what you should do next...",
                    "visual_suggestion": "Clear call-to-action visuals"
                },
                {
                    "sceneNumber": 5,
                    "time": "45-60s",
                    "on_screen_text": "FOLLOW FOR MORE",
                    "voiceover": f"Follow for more {niche.lower()} tips that actually work!",
                    "visual_suggestion": "Point to follow button"
                }
            ],
            "cta": f"Follow + Save this for later! More {niche.lower()} content coming soon."
        },
        "caption_short": f"{niche} tip that will change your life! #viral",
        "caption_long": f"This insight about {key_phrase} is something everyone needs to know. Save this and share with someone who needs to hear it! {text[:100]}...",
        "hashtags": [
            f"#{niche.lower().replace(' ', '')}",
            "#viral",
            "#trending",
            "#reels",
            "#tips",
            "#fyp",
            "#lifehacks",
            "#motivation"
        ],
        "posting_tips": [
            "Post between 6-9 PM for best engagement",
            "Use trending audio if available",
            "Reply to comments within first hour",
            f"Great for {tone.lower()} tone delivery"
        ]
    }
    
    # Save conversion
    await db.conversions.insert_one({
        "id": job_id,
        "userId": user["id"],
        "type": "text_to_reel",
        "input": {"text": text[:2000], "niche": niche, "tone": tone},
        "output": reel_output,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    await deduct_credits(user["id"], cost, "Text to Reel conversion")
    
    return {
        "success": True,
        "jobId": job_id,
        "reel": reel_output,
        "creditsUsed": cost,
        "message": "Created viral reel script from your text!"
    }


@router.get("/user-reels")
async def get_user_reels(
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    """Get user's recent reels for conversion"""
    reels = await db.generations.find(
        {"userId": user["id"], "type": "REEL"},
        {"_id": 0, "id": 1, "topic": 1, "createdAt": 1}
    ).sort("createdAt", -1).limit(limit).to_list(length=limit)
    
    return {"reels": reels, "count": len(reels)}


@router.get("/user-stories")
async def get_user_stories(
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    """Get user's recent stories for conversion"""
    stories = await db.generations.find(
        {"userId": user["id"], "type": "STORY"},
        {"_id": 0, "id": 1, "outputJson.title": 1, "createdAt": 1}
    ).sort("createdAt", -1).limit(limit).to_list(length=limit)
    
    # Format response
    formatted = []
    for s in stories:
        formatted.append({
            "id": s.get("id"),
            "title": s.get("outputJson", {}).get("title", "Untitled Story"),
            "createdAt": s.get("createdAt")
        })
    
    return {"stories": formatted, "count": len(formatted)}


@router.get("/status/{job_id}")
async def get_conversion_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get conversion job status"""
    job = await db.conversions.find_one(
        {"id": job_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.get("/history")
async def get_conversion_history(
    page: int = 0,
    size: int = 20,
    type_filter: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get conversion history"""
    skip = page * size
    query = {"userId": user["id"]}
    if type_filter:
        query["type"] = type_filter
    
    jobs = await db.conversions.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.conversions.count_documents(query)
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/costs")
async def get_conversion_costs():
    """Get conversion costs"""
    return {
        "costs": CONVERSION_COSTS,
        "description": {
            "reel_to_carousel": "Convert reel script to carousel slides (5 credits)",
            "reel_to_youtube": "Expand reel to YouTube video script (2 credits)",
            "story_to_reel": "Convert story to parenting reel (5 credits)",
            "story_to_quote": "Extract quotes from story (FREE)",
            "text_to_story": "Transform any text into a kids story (10 credits)",
            "text_to_reel": "Transform any text into a reel script (15 credits)"
        }
    }
