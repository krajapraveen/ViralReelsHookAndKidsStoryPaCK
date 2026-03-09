"""
Story → Video Studio - Video Templates, Social Sharing & Interactive Waiting Experience
- Pre-made story templates for quick video creation
- Social sharing to Facebook, Twitter, WhatsApp, LinkedIn
- Download functionality
- Mini-games, quizzes, and puzzles while waiting for video generation
"""

import os
import uuid
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from shared import db, get_current_user

router = APIRouter(prefix="/story-video-studio/templates", tags=["Story Video Templates & Sharing"])

# =============================================================================
# UNIVERSAL NEGATIVE PROMPTS (COMPREHENSIVE)
# =============================================================================

UNIVERSAL_NEGATIVE_PROMPTS = """
# COPYRIGHT & TRADEMARK PROTECTION
copyrighted character, trademarked character, brand logo, company logo, 
Disney character, Marvel character, DC Comics character, Nintendo character,
Pixar character, DreamWorks character, Warner Bros character,
Mickey Mouse, Spider-Man, Batman, Superman, Harry Potter, Pokemon,
celebrity face, real person, famous person, recognizable person,
movie scene, TV show scene, video game screenshot,

# LEGAL COMPLIANCE
nsfw, nudity, partial nudity, suggestive content, sexual content,
violence, gore, blood, injury, death, corpse, weapons, guns, knives,
drugs, alcohol, smoking, tobacco, vaping, drug paraphernalia,
hate symbols, nazi symbols, confederate flag, extremist symbols,
political propaganda, religious mockery, cultural insensitivity,

# CHILD SAFETY (CRITICAL)
realistic child in danger, child abuse, child exploitation,
scary content for children, nightmare fuel, horror elements,
creepy imagery, disturbing content, traumatic scenes,

# QUALITY CONTROL
blurry, low quality, pixelated, distorted, deformed,
bad anatomy, extra limbs, missing limbs, floating limbs,
bad hands, extra fingers, missing fingers, fused fingers,
cross-eyed, lazy eye, asymmetric eyes,
watermark, signature, text overlay, logo overlay,
cropped, out of frame, poorly drawn,

# STYLE CONSISTENCY
inconsistent style, mixed art styles, photorealistic in cartoon,
anime in realistic, mismatched lighting, wrong perspective
""".strip()

# Export for use in other modules
def get_universal_negative_prompts() -> str:
    """Get the universal negative prompts for image generation"""
    return UNIVERSAL_NEGATIVE_PROMPTS

# =============================================================================
# VIDEO TEMPLATES (PRE-MADE STORY STRUCTURES)
# =============================================================================

VIDEO_TEMPLATES = [
    {
        "template_id": "bedtime_adventure",
        "name": "Bedtime Adventure",
        "description": "A gentle adventure story perfect for bedtime",
        "age_group": "kids_5_8",
        "style": "watercolor",
        "duration_estimate": "2-3 minutes",
        "scene_count": 5,
        "structure": [
            {"scene": 1, "type": "introduction", "prompt": "Introduce the main character in their cozy home at sunset"},
            {"scene": 2, "type": "discovery", "prompt": "The character discovers something magical"},
            {"scene": 3, "type": "adventure", "prompt": "A gentle adventure begins"},
            {"scene": 4, "type": "resolution", "prompt": "The character overcomes a small challenge"},
            {"scene": 5, "type": "ending", "prompt": "The character returns home, ready for sleep"}
        ],
        "fill_in_blanks": {
            "character_name": "Luna",
            "character_type": "bunny",
            "magical_item": "glowing flower",
            "adventure_location": "enchanted forest"
        },
        "music_mood": "calm",
        "voice_preset": "narrator_warm"
    },
    {
        "template_id": "superhero_origin",
        "name": "My Superhero Story",
        "description": "Create your own superhero origin story",
        "age_group": "kids_9_12",
        "style": "comic",
        "duration_estimate": "3-4 minutes",
        "scene_count": 6,
        "structure": [
            {"scene": 1, "type": "ordinary_life", "prompt": "The hero living their normal life"},
            {"scene": 2, "type": "incident", "prompt": "Something extraordinary happens"},
            {"scene": 3, "type": "discovery", "prompt": "The hero discovers their powers"},
            {"scene": 4, "type": "training", "prompt": "Learning to control their abilities"},
            {"scene": 5, "type": "challenge", "prompt": "First challenge to overcome"},
            {"scene": 6, "type": "victory", "prompt": "The hero saves the day"}
        ],
        "fill_in_blanks": {
            "hero_name": "Captain Spark",
            "power": "lightning speed",
            "weakness": "water",
            "city_name": "Brightville"
        },
        "music_mood": "adventure",
        "voice_preset": "narrator_energetic"
    },
    {
        "template_id": "fairy_tale",
        "name": "Classic Fairy Tale",
        "description": "A magical fairy tale with a happy ending",
        "age_group": "kids_5_8",
        "style": "storybook",
        "duration_estimate": "3-4 minutes",
        "scene_count": 6,
        "structure": [
            {"scene": 1, "type": "once_upon", "prompt": "Once upon a time in a faraway kingdom"},
            {"scene": 2, "type": "problem", "prompt": "A problem arises in the kingdom"},
            {"scene": 3, "type": "journey", "prompt": "The hero sets out on a journey"},
            {"scene": 4, "type": "helper", "prompt": "A magical helper appears"},
            {"scene": 5, "type": "climax", "prompt": "The final challenge"},
            {"scene": 6, "type": "happily_ever", "prompt": "And they lived happily ever after"}
        ],
        "fill_in_blanks": {
            "hero_name": "Princess Lily",
            "kingdom_name": "Rosewood",
            "villain": "wicked witch",
            "magical_helper": "wise owl"
        },
        "music_mood": "magical",
        "voice_preset": "narrator_warm"
    },
    {
        "template_id": "space_explorer",
        "name": "Space Explorer",
        "description": "An exciting journey through the stars",
        "age_group": "kids_9_12",
        "style": "3d_cartoon",
        "duration_estimate": "3-4 minutes",
        "scene_count": 6,
        "structure": [
            {"scene": 1, "type": "launch", "prompt": "Launching into space from Earth"},
            {"scene": 2, "type": "travel", "prompt": "Flying through the solar system"},
            {"scene": 3, "type": "discovery", "prompt": "Discovering a new planet"},
            {"scene": 4, "type": "exploration", "prompt": "Exploring the alien world"},
            {"scene": 5, "type": "challenge", "prompt": "Overcoming a space challenge"},
            {"scene": 6, "type": "return", "prompt": "Returning home as a hero"}
        ],
        "fill_in_blanks": {
            "astronaut_name": "Captain Nova",
            "spaceship_name": "Star Voyager",
            "planet_name": "Zephyria",
            "alien_friend": "friendly alien creature"
        },
        "music_mood": "adventure",
        "voice_preset": "narrator_dramatic"
    },
    {
        "template_id": "friendship_story",
        "name": "Best Friends Forever",
        "description": "A heartwarming story about friendship",
        "age_group": "all_ages",
        "style": "anime",
        "duration_estimate": "2-3 minutes",
        "scene_count": 5,
        "structure": [
            {"scene": 1, "type": "meeting", "prompt": "Two characters meet for the first time"},
            {"scene": 2, "type": "bonding", "prompt": "They discover they have things in common"},
            {"scene": 3, "type": "conflict", "prompt": "A small misunderstanding happens"},
            {"scene": 4, "type": "resolution", "prompt": "They talk and make up"},
            {"scene": 5, "type": "celebration", "prompt": "Celebrating their friendship"}
        ],
        "fill_in_blanks": {
            "friend1_name": "Max",
            "friend1_type": "puppy",
            "friend2_name": "Whiskers",
            "friend2_type": "kitten"
        },
        "music_mood": "happy",
        "voice_preset": "narrator_friendly"
    },
    {
        "template_id": "educational_journey",
        "name": "Learning Adventure",
        "description": "Educational content wrapped in a fun story",
        "age_group": "kids_5_8",
        "style": "storybook",
        "duration_estimate": "2-3 minutes",
        "scene_count": 5,
        "structure": [
            {"scene": 1, "type": "question", "prompt": "The character has a question about the world"},
            {"scene": 2, "type": "exploration", "prompt": "Setting out to find the answer"},
            {"scene": 3, "type": "learning1", "prompt": "Learning the first fact"},
            {"scene": 4, "type": "learning2", "prompt": "Learning more interesting facts"},
            {"scene": 5, "type": "conclusion", "prompt": "Understanding and sharing knowledge"}
        ],
        "fill_in_blanks": {
            "learner_name": "Curious Charlie",
            "topic": "how rainbows form",
            "guide_character": "Professor Owl"
        },
        "music_mood": "happy",
        "voice_preset": "narrator_friendly"
    },
    {
        "template_id": "animal_adventure",
        "name": "Animal Kingdom Adventure",
        "description": "An adventure with animal characters",
        "age_group": "toddler",
        "style": "watercolor",
        "duration_estimate": "1-2 minutes",
        "scene_count": 4,
        "structure": [
            {"scene": 1, "type": "introduction", "prompt": "Meet the animal friends"},
            {"scene": 2, "type": "activity", "prompt": "The animals play together"},
            {"scene": 3, "type": "problem", "prompt": "A small problem to solve"},
            {"scene": 4, "type": "solution", "prompt": "Working together to solve it"}
        ],
        "fill_in_blanks": {
            "main_animal": "little elephant",
            "friend1": "giraffe",
            "friend2": "zebra",
            "location": "sunny savanna"
        },
        "music_mood": "happy",
        "voice_preset": "narrator_warm"
    },
    {
        "template_id": "mystery_detective",
        "name": "Junior Detective",
        "description": "A kid-friendly mystery to solve",
        "age_group": "kids_9_12",
        "style": "comic",
        "duration_estimate": "3-4 minutes",
        "scene_count": 6,
        "structure": [
            {"scene": 1, "type": "case", "prompt": "A mystery presents itself"},
            {"scene": 2, "type": "clue1", "prompt": "Finding the first clue"},
            {"scene": 3, "type": "clue2", "prompt": "Discovering another clue"},
            {"scene": 4, "type": "thinking", "prompt": "Putting the pieces together"},
            {"scene": 5, "type": "revelation", "prompt": "The mystery is solved"},
            {"scene": 6, "type": "celebration", "prompt": "Everyone celebrates the detective"}
        ],
        "fill_in_blanks": {
            "detective_name": "Detective Sam",
            "mystery": "missing cookies",
            "location": "neighborhood",
            "suspect": "mischievous squirrel"
        },
        "music_mood": "adventure",
        "voice_preset": "narrator_energetic"
    }
]

# =============================================================================
# MINI-GAMES & PUZZLES (While Waiting)
# =============================================================================

STORY_TRIVIA = [
    {"question": "Who wrote 'The Cat in the Hat'?", "options": ["Dr. Seuss", "Roald Dahl", "Eric Carle", "Maurice Sendak"], "answer": 0},
    {"question": "What color is the Very Hungry Caterpillar?", "options": ["Blue", "Green", "Red", "Yellow"], "answer": 1},
    {"question": "Who lives in a pineapple under the sea?", "options": ["Patrick", "SpongeBob", "Squidward", "Mr. Krabs"], "answer": 1},
    {"question": "What does Cinderella lose at midnight?", "options": ["Her crown", "Her dress", "Her glass slipper", "Her carriage"], "answer": 2},
    {"question": "What animal is Dumbo?", "options": ["Mouse", "Elephant", "Lion", "Bear"], "answer": 1},
    {"question": "Who is Simba's father?", "options": ["Scar", "Mufasa", "Zazu", "Timon"], "answer": 1},
    {"question": "What color is Elsa's dress in Frozen?", "options": ["Pink", "Blue", "Green", "White"], "answer": 1},
    {"question": "How many dwarfs does Snow White live with?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"question": "What is the name of Shrek's wife?", "options": ["Fiona", "Rapunzel", "Belle", "Aurora"], "answer": 0},
    {"question": "What type of fish is Nemo?", "options": ["Goldfish", "Clownfish", "Betta", "Angelfish"], "answer": 1},
]

WORD_PUZZLES = [
    {"scrambled": "YROST", "answer": "STORY", "hint": "What we're creating!"},
    {"scrambled": "OEDIV", "answer": "VIDEO", "hint": "Moving pictures"},
    {"scrambled": "EORH", "answer": "HERO", "hint": "The main character"},
    {"scrambled": "CIAGM", "answer": "MAGIC", "hint": "Something enchanting"},
    {"scrambled": "TARCS", "answer": "STARS", "hint": "Twinkle in the sky"},
    {"scrambled": "DAVENTURE", "answer": "ADVENTURE", "hint": "An exciting journey"},
    {"scrambled": "PRINECSS", "answer": "PRINCESS", "hint": "Royal daughter"},
    {"scrambled": "DRAGNO", "answer": "DRAGON", "hint": "Fire-breathing creature"},
    {"scrambled": "CASLTE", "answer": "CASTLE", "hint": "Where royalty lives"},
    {"scrambled": "FORSET", "answer": "FOREST", "hint": "Full of trees"},
]

RIDDLES = [
    {"riddle": "I have a head and a tail but no body. What am I?", "answer": "A coin"},
    {"riddle": "What has hands but can't clap?", "answer": "A clock"},
    {"riddle": "What can you catch but not throw?", "answer": "A cold"},
    {"riddle": "What has a face and two hands but no arms or legs?", "answer": "A clock"},
    {"riddle": "What gets wetter the more it dries?", "answer": "A towel"},
    {"riddle": "What can travel around the world while staying in a corner?", "answer": "A stamp"},
    {"riddle": "What has ears but cannot hear?", "answer": "Corn"},
    {"riddle": "What has a neck but no head?", "answer": "A bottle"},
    {"riddle": "What can you break without touching?", "answer": "A promise"},
    {"riddle": "What goes up but never comes down?", "answer": "Your age"},
]

SIMPLE_GAMES = [
    {
        "game_id": "emoji_story",
        "name": "Emoji Story Builder",
        "description": "Create a mini story using only emojis!",
        "type": "creative"
    },
    {
        "game_id": "character_match",
        "name": "Character Match",
        "description": "Match characters to their stories",
        "type": "memory"
    },
    {
        "game_id": "story_chain",
        "name": "Story Chain",
        "description": "Add one sentence to continue the story",
        "type": "creative"
    },
    {
        "game_id": "color_picker",
        "name": "Color Your Character",
        "description": "Choose colors for your video characters",
        "type": "creative"
    },
    {
        "game_id": "name_generator",
        "name": "Character Name Generator",
        "description": "Generate fun names for your characters",
        "type": "tool"
    }
]

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TemplateCustomization(BaseModel):
    template_id: str
    customizations: Dict[str, str]  # fill_in_blanks overrides
    additional_details: Optional[str] = None

class SocialShareRequest(BaseModel):
    video_id: str
    platform: str  # facebook, twitter, whatsapp, linkedin, email
    custom_message: Optional[str] = None

class GameScoreSubmission(BaseModel):
    game_type: str
    score: int
    job_id: str  # Link to video generation job

# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@router.get("/list")
async def get_video_templates(
    age_group: Optional[str] = None,
    style: Optional[str] = None
):
    """Get all available video templates"""
    templates = VIDEO_TEMPLATES.copy()
    
    if age_group:
        templates = [t for t in templates if t["age_group"] == age_group]
    
    if style:
        templates = [t for t in templates if t["style"] == style]
    
    return {
        "success": True,
        "templates": templates,
        "total": len(templates),
        "age_groups": ["toddler", "kids_5_8", "kids_9_12", "teen", "all_ages"],
        "styles": ["watercolor", "storybook", "3d_cartoon", "comic", "anime", "cinematic"]
    }

# =============================================================================
# WAITING GAMES ENDPOINTS (Must be before dynamic {template_id} route)
# =============================================================================

@router.get("/waiting-games")
async def get_waiting_games():
    """Get available games to play while waiting"""
    return {
        "success": True,
        "games": SIMPLE_GAMES,
        "trivia_count": len(STORY_TRIVIA),
        "puzzles_count": len(WORD_PUZZLES),
        "riddles_count": len(RIDDLES),
        "message": "Play games while your video is being created!"
    }

@router.get("/waiting-games/trivia")
async def get_trivia_questions(count: int = Query(default=5, le=10)):
    """Get random trivia questions"""
    questions = random.sample(STORY_TRIVIA, min(count, len(STORY_TRIVIA)))
    # Don't include answers in response
    return {
        "success": True,
        "questions": [
            {
                "id": i,
                "question": q["question"],
                "options": q["options"]
            }
            for i, q in enumerate(questions)
        ]
    }

@router.post("/waiting-games/trivia/check")
async def check_trivia_answer(question_id: int, answer_index: int):
    """Check trivia answer"""
    if question_id < 0 or question_id >= len(STORY_TRIVIA):
        raise HTTPException(status_code=400, detail="Invalid question")
    
    correct = STORY_TRIVIA[question_id]["answer"] == answer_index
    
    return {
        "success": True,
        "correct": correct,
        "correct_answer": STORY_TRIVIA[question_id]["options"][STORY_TRIVIA[question_id]["answer"]] if not correct else None
    }

@router.get("/waiting-games/word-puzzle")
async def get_word_puzzle():
    """Get a random word puzzle"""
    puzzle = random.choice(WORD_PUZZLES)
    return {
        "success": True,
        "scrambled": puzzle["scrambled"],
        "hint": puzzle["hint"],
        "length": len(puzzle["answer"])
    }

@router.post("/waiting-games/word-puzzle/check")
async def check_word_puzzle(scrambled: str, guess: str):
    """Check word puzzle answer"""
    puzzle = next((p for p in WORD_PUZZLES if p["scrambled"] == scrambled), None)
    
    if not puzzle:
        raise HTTPException(status_code=400, detail="Invalid puzzle")
    
    correct = guess.upper() == puzzle["answer"]
    
    return {
        "success": True,
        "correct": correct,
        "answer": puzzle["answer"] if not correct else None
    }

@router.get("/waiting-games/riddle")
async def get_riddle():
    """Get a random riddle"""
    riddle = random.choice(RIDDLES)
    return {
        "success": True,
        "riddle": riddle["riddle"]
    }

@router.post("/waiting-games/riddle/check")
async def check_riddle(riddle_text: str, guess: str):
    """Check riddle answer"""
    riddle = next((r for r in RIDDLES if r["riddle"] == riddle_text), None)
    
    if not riddle:
        raise HTTPException(status_code=400, detail="Invalid riddle")
    
    # Fuzzy match - check if the answer contains the key word
    correct = riddle["answer"].lower() in guess.lower() or guess.lower() in riddle["answer"].lower()
    
    return {
        "success": True,
        "correct": correct,
        "answer": riddle["answer"] if not correct else None
    }

@router.post("/waiting-games/score")
async def submit_game_score(
    submission: GameScoreSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Submit game score while waiting"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    score_doc = {
        "user_id": user_id,
        "job_id": submission.job_id,
        "game_type": submission.game_type,
        "score": submission.score,
        "submitted_at": datetime.now(timezone.utc)
    }
    
    await db.waiting_game_scores.insert_one(score_doc)
    
    return {
        "success": True,
        "message": "Score saved!",
        "score": submission.score
    }

# =============================================================================
# USER VIDEO LIBRARY (Profile Integration) - Must be before dynamic /{template_id} route
# =============================================================================

@router.get("/my-videos")
async def get_user_videos(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, le=50),
    offset: int = 0
):
    """Get all videos for the current user (for profile page)"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Get from render_jobs
    render_videos = await db.render_jobs.find(
        {"user_id": user_id, "status": "COMPLETED"},
        {"_id": 0}
    ).sort("completed_at", -1).to_list(limit)
    
    # Get from fast_video_jobs
    fast_videos = await db.fast_video_jobs.find(
        {"user_id": user_id, "status": "COMPLETED"},
        {"_id": 0}
    ).sort("completed_at", -1).to_list(limit)
    
    # Combine and sort
    all_videos = []
    
    for v in render_videos:
        all_videos.append({
            "video_id": v.get("job_id"),
            "title": v.get("title", "Story Video"),
            "project_id": v.get("project_id"),
            "output_url": v.get("output_url"),
            "created_at": v.get("completed_at"),
            "type": "standard",
            "credits_spent": v.get("credits_spent", 0)
        })
    
    for v in fast_videos:
        all_videos.append({
            "video_id": v.get("job_id"),
            "title": v.get("title", "Fast Video"),
            "output_url": v.get("output_url"),
            "created_at": v.get("completed_at"),
            "type": "fast",
            "credits_spent": v.get("credits_charged", 0)
        })
    
    # Sort by created_at
    all_videos.sort(key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    return {
        "success": True,
        "videos": all_videos[offset:offset + limit],
        "total": len(all_videos),
        "limit": limit,
        "offset": offset
    }

@router.get("/video-ready/{job_id}")
async def check_video_ready(job_id: str):
    """Check if video is ready and get redirect info"""
    
    # Check both job types
    video = await db.render_jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not video:
        video = await db.fast_video_jobs.find_one({"job_id": job_id}, {"_id": 0})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video job not found")
    
    is_ready = video.get("status") == "COMPLETED"
    
    return {
        "success": True,
        "job_id": job_id,
        "is_ready": is_ready,
        "status": video.get("status"),
        "progress": video.get("progress", 0),
        "output_url": video.get("output_url") if is_ready else None,
        "redirect_to": "/app/profile/videos" if is_ready else None,
        "message": "Your video is ready! View it in your profile." if is_ready else "Still generating..."
    }

# =============================================================================
# TEMPLATE DETAIL ENDPOINT (Dynamic route must come after specific routes)
# =============================================================================

@router.get("/{template_id}")
async def get_template_details(template_id: str):
    """Get detailed template information"""
    template = next((t for t in VIDEO_TEMPLATES if t["template_id"] == template_id), None)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "success": True,
        "template": template
    }

@router.post("/generate-from-template")
async def generate_from_template(
    request: TemplateCustomization,
    current_user: dict = Depends(get_current_user)
):
    """Generate a video from a template with customizations"""
    
    template = next((t for t in VIDEO_TEMPLATES if t["template_id"] == request.template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Merge customizations with defaults
    fill_ins = {**template["fill_in_blanks"], **request.customizations}
    
    # Generate story text from template
    story_parts = []
    for scene in template["structure"]:
        scene_text = scene["prompt"]
        # Replace placeholders
        for key, value in fill_ins.items():
            scene_text = scene_text.replace(f"{{{key}}}", value)
            scene_text = scene_text.replace(key, value)
        story_parts.append(scene_text)
    
    generated_story = ". ".join(story_parts)
    if request.additional_details:
        generated_story += f" {request.additional_details}"
    
    return {
        "success": True,
        "template_id": request.template_id,
        "generated_story": generated_story,
        "fill_ins_used": fill_ins,
        "recommended_settings": {
            "style": template["style"],
            "age_group": template["age_group"],
            "music_mood": template["music_mood"],
            "voice_preset": template["voice_preset"],
            "scene_count": template["scene_count"]
        },
        "next_step": "Use this story with POST /api/story-video-studio/projects/create"
    }

# =============================================================================
# SOCIAL SHARING ENDPOINTS
# =============================================================================

@router.post("/share")
async def share_video(
    request: SocialShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate share links for social platforms"""
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    
    # Get video info
    video = await db.render_jobs.find_one({"job_id": request.video_id})
    if not video:
        # Check fast video jobs
        video = await db.fast_video_jobs.find_one({"job_id": request.video_id})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Video is not ready for sharing")
    
    # Generate share URL (would be the actual video URL in production)
    video_url = video.get("output_url", "")
    base_url = os.getenv("FRONTEND_URL", "https://www.visionary-suite.com")
    share_url = f"{base_url}/shared/video/{request.video_id}"
    
    title = video.get("title", "My AI-Generated Video")
    default_message = f"Check out my AI-generated video: {title}"
    message = request.custom_message or default_message
    
    # Generate platform-specific share URLs
    share_links = {}
    encoded_message = message.replace(" ", "%20")
    encoded_url = share_url.replace(":", "%3A").replace("/", "%2F")
    
    if request.platform == "facebook" or request.platform == "all":
        share_links["facebook"] = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}&quote={encoded_message}"
    
    if request.platform == "twitter" or request.platform == "all":
        share_links["twitter"] = f"https://twitter.com/intent/tweet?text={encoded_message}&url={encoded_url}"
    
    if request.platform == "whatsapp" or request.platform == "all":
        share_links["whatsapp"] = f"https://api.whatsapp.com/send?text={encoded_message}%20{encoded_url}"
    
    if request.platform == "linkedin" or request.platform == "all":
        share_links["linkedin"] = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
    
    if request.platform == "email" or request.platform == "all":
        share_links["email"] = f"mailto:?subject={encoded_message}&body=Watch%20my%20video%3A%20{encoded_url}"
    
    # Record share action
    await db.video_shares.insert_one({
        "video_id": request.video_id,
        "user_id": user_id,
        "platform": request.platform,
        "shared_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "video_id": request.video_id,
        "share_url": share_url,
        "share_links": share_links,
        "message": message
    }

@router.get("/download/{video_id}")
async def get_download_info(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get video download information"""
    
    # Check render jobs
    video = await db.render_jobs.find_one({"job_id": video_id})
    if not video:
        video = await db.fast_video_jobs.find_one({"job_id": video_id})
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail="Video is not ready for download")
    
    output_url = video.get("output_url", "")
    
    return {
        "success": True,
        "video_id": video_id,
        "title": video.get("title", "Story Video"),
        "download_url": f"/api/story-video-studio/generation/video/download/{video_id}",
        "output_url": output_url,
        "file_size_estimate": "5-15 MB",
        "format": "MP4",
        "share_options": {
            "facebook": f"/api/story-video-studio/templates/share",
            "twitter": f"/api/story-video-studio/templates/share",
            "whatsapp": f"/api/story-video-studio/templates/share",
            "linkedin": f"/api/story-video-studio/templates/share"
        }
    }

# =============================================================================
# BETA TESTER ENDPOINTS
# =============================================================================

class BetaInviteRequest(BaseModel):
    emails: List[str]

@router.post("/beta-testers/invite")
async def invite_beta_testers(
    request: BetaInviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invite beta testers (admin only)"""
    
    # Check both is_admin flag and role
    is_admin = current_user.get("is_admin") or current_user.get("role") == "ADMIN"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    test_flow_url = "/api/story-video-studio/analytics/test-flow"
    
    invitations = []
    for email in request.emails:
        invite_doc = {
            "email": email,
            "invite_code": str(uuid.uuid4())[:8],
            "test_flow_url": test_flow_url,
            "invited_at": datetime.now(timezone.utc),
            "status": "PENDING"
        }
        await db.beta_invitations.insert_one(invite_doc)
        invitations.append({
            "email": email,
            "invite_code": invite_doc["invite_code"]
        })
    
    return {
        "success": True,
        "invitations_sent": len(invitations),
        "invitations": invitations,
        "test_flow_guide": {
            "url": test_flow_url,
            "steps": 7,
            "estimated_time": "2-3 minutes"
        }
    }

@router.get("/beta-testers/test-guide")
async def get_beta_test_guide():
    """Get the complete beta testing guide"""
    return {
        "success": True,
        "guide": {
            "title": "Story → Video Studio Beta Testing Guide",
            "version": "1.0",
            "estimated_time": "5-10 minutes",
            "credits_needed": "50-100 (preview mode uses less)",
            "steps": [
                {
                    "step": 1,
                    "name": "Access the Feature",
                    "url": "/app/story-video-studio",
                    "action": "Navigate to Story Video Studio from the dashboard"
                },
                {
                    "step": 2,
                    "name": "Choose a Template OR Write Story",
                    "url": "/api/story-video-studio/templates/list",
                    "action": "Select a template or write your own 500+ character story"
                },
                {
                    "step": 3,
                    "name": "Generate Scenes",
                    "action": "Click 'Generate Scenes' and wait for AI processing"
                },
                {
                    "step": 4,
                    "name": "Try Preview Mode",
                    "action": "Generate preview images (3 credits vs 10 for full quality)",
                    "url": "/api/story-video-studio/preview/generate"
                },
                {
                    "step": 5,
                    "name": "Play Waiting Games",
                    "action": "While waiting, try the trivia, puzzles, or riddles",
                    "url": "/api/story-video-studio/templates/waiting-games"
                },
                {
                    "step": 6,
                    "name": "Generate Full Video",
                    "action": "Approve preview and generate full quality video"
                },
                {
                    "step": 7,
                    "name": "Download & Share",
                    "action": "Download your video and share on social media",
                    "url": "/api/story-video-studio/templates/share"
                },
                {
                    "step": 8,
                    "name": "Submit Feedback",
                    "url": "/api/story-video-studio/analytics/test-run/{id}/feedback",
                    "action": "Rate your experience and report any issues"
                }
            ],
            "feedback_questions": [
                "How easy was it to create a video? (1-5)",
                "How satisfied are you with the video quality? (1-5)",
                "How likely are you to use this feature again? (1-5)",
                "What features would you like to see added?",
                "Did you encounter any bugs or issues?"
            ],
            "contact": "support@visionary-suite.com"
        }
    }
