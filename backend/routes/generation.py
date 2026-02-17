"""Content generation routes"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from datetime import datetime, timezone
from typing import Optional
import uuid
import json
import copy
import random
import logging
import os

from ..utils.auth import get_current_user
from ..utils.database import db
from ..models.schemas import GenerateReelRequest, GenerateStoryRequest

# LLM Integration
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# PDF Generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    import tempfile
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate", tags=["Generation"])

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# AI Generation Prompts
REEL_SYSTEM_PROMPT = """You are an elite social media scriptwriter. Output must be structured JSON only."""

REEL_USER_PROMPT_TEMPLATE = """Generate a UNIQUE and ORIGINAL high-retention Instagram Reel package.

**Input Parameters:**
- Language: {language}
- Niche: {niche}
- Tone: {tone}
- Duration: {duration}
- Goal: {goal}
- Topic: {topic}
- Unique Request ID: {uniqueId}

Output ONLY this JSON format:
{{
  "hooks": ["5 unique, attention-grabbing hooks under 12 words each"],
  "best_hook": "The most powerful hook from above",
  "script": {{
    "scenes": [
      {{"time": "0-2s", "on_screen_text": "...", "voiceover": "...", "broll": ["visual suggestions"]}}
    ],
    "cta": "Compelling call to action"
  }},
  "caption_short": "Short engaging caption",
  "caption_long": "Detailed caption with value",
  "hashtags": ["20 relevant trending hashtags"],
  "posting_tips": ["5 specific tips for this content"]
}}

Return ONLY valid JSON, no markdown or explanation."""


async def generate_reel_content_inline(data: dict) -> dict:
    """Generate reel content using LLM directly"""
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        raise Exception("LLM integration not available")
    
    import time
    unique_id = f"reel_{uuid.uuid4().hex[:12]}_{int(time.time())}"
    
    prompt = REEL_USER_PROMPT_TEMPLATE.format(
        language=data.get("language", "English"),
        niche=data.get("niche", "Business"),
        tone=data.get("tone", "Professional"),
        duration=data.get("duration", "30s"),
        goal=data.get("goal", "Engagement"),
        topic=data.get("topic", ""),
        uniqueId=unique_id
    )
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        model="gemini-2.0-flash",
        system_message=REEL_SYSTEM_PROMPT,
        temperature=0.9
    )
    
    response = await chat.send_message_async(UserMessage(content=prompt))
    
    # Parse JSON from response
    text = response.content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    
    return json.loads(text)


@router.post("/reel")
async def generate_reel(data: GenerateReelRequest, user: dict = Depends(get_current_user)):
    """Generate an Instagram reel script"""
    credits_needed = 3
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credits_needed} credits.")
    
    generation_id = str(uuid.uuid4())
    
    try:
        result = await generate_reel_content_inline(data.model_dump())
        
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
            "description": f"Reel generation: {data.niche} - {data.topic[:50] if data.topic else 'No topic'}",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Save generation
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "REEL",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": credits_needed,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "status": "COMPLETED",
            "result": result,
            "creditsUsed": credits_needed,
            "remainingCredits": user["credits"] - credits_needed
        }
        
    except Exception as e:
        logger.error(f"Reel generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/story")
async def generate_story(data: GenerateStoryRequest, user: dict = Depends(get_current_user)):
    """Generate a kids story pack from templates"""
    credits_needed = min(max(data.sceneCount, 6), 10)
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. You need {credits_needed} credits.")
    
    generation_id = str(uuid.uuid4())
    
    try:
        result = None
        
        # TEMPLATE-BASED GENERATION - Find matching template
        template = await db.story_templates.find_one({
            "ageGroup": data.ageGroup,
            "genre": data.genre if data.genre != "Custom" else {"$exists": True}
        }, {"_id": 0})
        
        if template:
            # Random character names for uniqueness
            hero_names = ["Max", "Luna", "Leo", "Maya", "Sam", "Zoe", "Jack", "Lily", "Finn", "Emma"]
            friend_names = ["Pip", "Sparkle", "Buddy", "Twinkle", "Fuzzy", "Whiskers", "Bubbles", "Patches"]
            mentor_names = ["Grandma Rose", "Old Wizard Oak", "Wise Owl", "Elder Willow", "Magic Fox"]
            
            hero_name = random.choice(hero_names)
            friend_name = random.choice(friend_names)
            mentor_name = random.choice(mentor_names)
            
            # Deep copy and replace placeholders
            result = copy.deepcopy(template)
            
            # Remove template-specific fields
            result.pop("templateNumber", None)
            result.pop("usageCount", None)
            result.pop("createdAt", None)
            
            # Replace placeholders
            result_str = json.dumps(result)
            result_str = result_str.replace("{{HERO_NAME}}", hero_name)
            result_str = result_str.replace("{{FRIEND_NAME}}", friend_name)
            result_str = result_str.replace("{{MENTOR_NAME}}", mentor_name)
            result = json.loads(result_str)
            
            # Update template usage count
            await db.story_templates.update_one(
                {"id": template["id"]},
                {"$inc": {"usageCount": 1}}
            )
            
            logger.info(f"Used template story: {template['title']} for user {user['email']}")
        
        if result is None:
            raise HTTPException(status_code=503, detail="No matching story template found. Please try different options.")
        
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
            "description": f"Story pack generation: {data.genre} ({data.sceneCount} scenes)",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Save generation
        generation = {
            "id": generation_id,
            "userId": user["id"],
            "type": "STORY",
            "status": "COMPLETED",
            "inputJson": data.model_dump(),
            "outputJson": result,
            "creditsUsed": credits_needed,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.generations.insert_one(generation)
        
        return {
            "success": True,
            "generationId": generation_id,
            "status": "COMPLETED",
            "result": result,
            "creditsUsed": credits_needed,
            "remainingCredits": user["credits"] - credits_needed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")


@router.get("/generations/{generation_id}")
async def get_generation(generation_id: str, user: dict = Depends(get_current_user)):
    """Get a specific generation by ID"""
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return generation


@router.get("/generations/{generation_id}/pdf")
async def download_generation_pdf(generation_id: str, user: dict = Depends(get_current_user)):
    """Generate and download a PDF for a story"""
    if not PDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF generation not available")
    
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    result = generation.get("outputJson", {})
    
    # Create PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=12)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, spaceAfter=8)
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, spaceAfter=6)
        
        story = []
        
        # Title
        story.append(Paragraph(result.get('title', 'Story Pack'), title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Synopsis
        if result.get('synopsis'):
            story.append(Paragraph('<b>Synopsis:</b>', heading_style))
            story.append(Paragraph(result.get('synopsis', ''), body_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Metadata
        story.append(Paragraph(f"<b>Genre:</b> {result.get('genre', 'N/A')} | <b>Age Group:</b> {result.get('ageGroup', 'N/A')}", body_style))
        if result.get('moral'):
            story.append(Paragraph(f"<b>Moral:</b> {result.get('moral', '')}", body_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Characters
        if result.get('characters'):
            story.append(Paragraph('Characters', heading_style))
            for char in result['characters']:
                story.append(Paragraph(f"<b>{char.get('name', 'Unknown')}</b> ({char.get('role', 'character')}): {char.get('description', '')}", body_style))
            story.append(Spacer(1, 0.3*inch))
        
        # Scenes
        if result.get('scenes'):
            story.append(Paragraph('Scenes', heading_style))
            scene_title_style = ParagraphStyle('SceneTitle', parent=styles['Normal'], fontSize=12, textColor='purple')
            
            for scene in result['scenes']:
                story.append(Paragraph(f"Scene {scene.get('scene_number', '?')}: {scene.get('title', 'Untitled')}", scene_title_style))
                if scene.get('setting'):
                    story.append(Paragraph(f"<i>Setting: {scene.get('setting')}</i>", body_style))
                if scene.get('narration'):
                    story.append(Paragraph(f"<b>Narration:</b> {scene.get('narration')}", body_style))
                if scene.get('visual_description'):
                    story.append(Paragraph(f"<b>Visual:</b> {scene.get('visual_description')}", body_style))
                if scene.get('dialogue'):
                    for d in scene['dialogue']:
                        story.append(Paragraph(f"<b>{d.get('speaker', 'Speaker')}:</b> \"{d.get('line', '')}\"", body_style))
                story.append(Spacer(1, 0.15*inch))
        
        doc.build(story)
        
        # Read and return PDF
        with open(tmp_file.name, 'rb') as f:
            pdf_content = f.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=story-{generation_id}.pdf"}
        )


@router.get("/generations")
async def get_generations(type: Optional[str] = None, page: int = 0, size: int = 20, user: dict = Depends(get_current_user)):
    """Get user's generation history"""
    query = {"userId": user["id"]}
    if type:
        query["type"] = type.upper()
    
    skip = page * size
    
    generations = await db.generations.find(
        query,
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(length=size)
    
    total = await db.generations.count_documents(query)
    
    return {
        "generations": generations,
        "total": total,
        "page": page,
        "size": size
    }


@router.post("/demo-reel")
async def demo_reel(data: GenerateReelRequest):
    """Demo reel generation (no auth required, limited)"""
    # Return sample data for demo
    return {
        "success": True,
        "generationId": "demo-" + str(uuid.uuid4())[:8],
        "status": "COMPLETED",
        "result": {
            "hooks": [
                "Stop scrolling, this changed everything",
                "The secret nobody talks about",
                "I wish I knew this sooner",
                "This is why you're stuck",
                "Game changer alert"
            ],
            "best_hook": "Stop scrolling, this changed everything",
            "script": {
                "scenes": [
                    {"time": "0-3s", "on_screen_text": "Hook", "voiceover": "Stop scrolling, this changed everything for me", "broll": ["Person looking surprised at phone"]},
                    {"time": "3-15s", "on_screen_text": "The Problem", "voiceover": "I used to struggle with this exact same thing", "broll": ["Frustrated person at desk"]},
                    {"time": "15-25s", "on_screen_text": "The Solution", "voiceover": "Until I discovered this simple trick", "broll": ["Lightbulb moment"]},
                    {"time": "25-30s", "on_screen_text": "CTA", "voiceover": "Follow for more tips like this", "broll": ["Follow button animation"]}
                ],
                "cta": "Follow for more tips!"
            },
            "caption_short": "This changed everything!",
            "caption_long": "I spent months trying to figure this out. Here's what actually worked...",
            "hashtags": ["#tips", "#viral", "#trending", "#fyp", "#foryou"],
            "posting_tips": ["Post between 9-11 AM", "Engage with comments quickly", "Use trending audio"]
        },
        "demo": True
    }
