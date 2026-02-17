"""
Story Tools Routes - Worksheets, Printable Books, Personalization
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from datetime import datetime, timezone
from typing import Optional
import uuid
import random
import json
import tempfile

router = APIRouter(prefix="/story-tools", tags=["Story Tools"])

# Import from main server
from server import get_current_user, db

# PDF Generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch, cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# =============================================================================
# WORKSHEET TEMPLATES
# =============================================================================

COMPREHENSION_TEMPLATES = [
    "What is the main character's name in this story?",
    "Where does the story take place?",
    "What problem did {character} face in the story?",
    "How did {character} solve the problem?",
    "What lesson did you learn from this story?",
    "Who helped {character} in the story?",
    "What happened at the beginning of the story?",
    "What happened at the end of the story?",
    "Why do you think {character} felt {emotion}?",
    "What would you do if you were {character}?"
]

FILL_BLANKS_TEMPLATES = [
    "The story is about a {adjective} {character_type} named _______.",
    "{character} went to the _______ to find {item}.",
    "The moral of the story is _______.",
    "{character} felt _______ when {event} happened.",
    "At the end, {character} learned that _______."
]

VOCABULARY_WORDS = {
    "Adventure": ["brave", "journey", "explore", "discover", "treasure", "quest", "courage", "mysterious"],
    "Fantasy": ["magical", "enchanted", "spell", "wizard", "fairy", "kingdom", "mythical", "wonder"],
    "Friendship": ["kind", "trust", "share", "help", "together", "loyal", "caring", "support"],
    "Animal": ["habitat", "wild", "nature", "forest", "creature", "species", "gentle", "fierce"],
    "Educational": ["learn", "curious", "knowledge", "discover", "experiment", "question", "answer", "understand"]
}

COLORING_PROMPTS = [
    "Draw {character} in their favorite place",
    "Color the magical {setting} from the story",
    "Draw what happens when {character} meets {friend}",
    "Create your own ending scene",
    "Draw {character} learning the moral of the story",
    "Color the most exciting moment in the story"
]

# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/worksheet/generate")
async def generate_worksheet(
    generation_id: str,
    user: dict = Depends(get_current_user)
):
    """Generate educational worksheet for a story - 3 credits"""
    credits_needed = 3
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
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
    characters = story.get("characters", [])
    main_char = characters[0].get("name", "the hero") if characters else "the hero"
    genre = story.get("genre", "Adventure")
    moral = story.get("moral", "Be kind to others")
    
    # Generate worksheet content
    worksheet = {
        "story_title": title,
        "story_id": generation_id,
        
        # Comprehension Questions
        "comprehension_questions": [],
        
        # Fill in the blanks
        "fill_blanks": [],
        
        # Vocabulary
        "vocabulary": [],
        
        # Moral reflection
        "moral_reflection": {
            "moral": moral,
            "question": f"The moral of this story is: '{moral}'. Write about a time when you learned a similar lesson."
        },
        
        # Coloring prompt
        "coloring_prompt": random.choice(COLORING_PROMPTS).replace("{character}", main_char).replace("{setting}", "scene").replace("{friend}", "a friend")
    }
    
    # Generate 5 comprehension questions
    selected_questions = random.sample(COMPREHENSION_TEMPLATES, 5)
    for i, q in enumerate(selected_questions, 1):
        worksheet["comprehension_questions"].append({
            "number": i,
            "question": q.replace("{character}", main_char).replace("{emotion}", "happy"),
            "lines": 2
        })
    
    # Generate 5 fill in the blanks
    for i, template in enumerate(FILL_BLANKS_TEMPLATES, 1):
        text = template.replace("{character}", main_char)
        text = text.replace("{adjective}", random.choice(["brave", "kind", "curious", "clever"]))
        text = text.replace("{character_type}", random.choice(["child", "animal", "creature"]))
        text = text.replace("{item}", random.choice(["treasure", "friend", "answer", "key"]))
        text = text.replace("{event}", "something exciting")
        worksheet["fill_blanks"].append({
            "number": i,
            "sentence": text
        })
    
    # Add vocabulary words
    vocab_list = VOCABULARY_WORDS.get(genre, VOCABULARY_WORDS["Adventure"])
    selected_vocab = random.sample(vocab_list, min(5, len(vocab_list)))
    for word in selected_vocab:
        worksheet["vocabulary"].append({
            "word": word,
            "definition_prompt": f"What do you think '{word}' means? Use it in a sentence."
        })
    
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
        "description": f"Worksheet: {title[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save worksheet
    worksheet_id = str(uuid.uuid4())
    await db.worksheets.insert_one({
        "id": worksheet_id,
        "userId": user["id"],
        "storyId": generation_id,
        "content": worksheet,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "worksheetId": worksheet_id,
        "worksheet": worksheet,
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed
    }


@router.get("/worksheet/{worksheet_id}/pdf")
async def download_worksheet_pdf(worksheet_id: str, user: dict = Depends(get_current_user)):
    """Download worksheet as PDF"""
    if not PDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF generation not available")
    
    worksheet_doc = await db.worksheets.find_one({
        "id": worksheet_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not worksheet_doc:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    
    worksheet = worksheet_doc.get("content", {})
    
    # Create PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, alignment=TA_CENTER, spaceAfter=20)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, spaceAfter=10, spaceBefore=15)
        question_style = ParagraphStyle('Question', parent=styles['Normal'], fontSize=12, spaceAfter=8)
        line_style = ParagraphStyle('Line', parent=styles['Normal'], fontSize=12, spaceAfter=4)
        
        elements = []
        
        # Title
        elements.append(Paragraph(f"📚 Story Worksheet: {worksheet.get('story_title', 'Story')}", title_style))
        elements.append(Paragraph("Name: _________________ Date: _________________", line_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Comprehension Questions
        elements.append(Paragraph("📝 Comprehension Questions", heading_style))
        for q in worksheet.get("comprehension_questions", []):
            elements.append(Paragraph(f"{q['number']}. {q['question']}", question_style))
            for _ in range(q.get('lines', 2)):
                elements.append(Paragraph("_" * 70, line_style))
            elements.append(Spacer(1, 0.1*inch))
        
        # Fill in the Blanks
        elements.append(Paragraph("✏️ Fill in the Blanks", heading_style))
        for fb in worksheet.get("fill_blanks", []):
            elements.append(Paragraph(f"{fb['number']}. {fb['sentence']}", question_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Vocabulary
        elements.append(Paragraph("📖 Vocabulary Challenge", heading_style))
        for vocab in worksheet.get("vocabulary", []):
            elements.append(Paragraph(f"• <b>{vocab['word']}</b>: {vocab['definition_prompt']}", question_style))
            elements.append(Paragraph("_" * 70, line_style))
        
        # Moral Reflection
        elements.append(Paragraph("💭 Moral Reflection", heading_style))
        moral_data = worksheet.get("moral_reflection", {})
        elements.append(Paragraph(moral_data.get("question", ""), question_style))
        for _ in range(4):
            elements.append(Paragraph("_" * 70, line_style))
        
        # Coloring Prompt
        elements.append(PageBreak())
        elements.append(Paragraph("🎨 Drawing Activity", heading_style))
        elements.append(Paragraph(worksheet.get("coloring_prompt", "Draw your favorite scene"), question_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("[Drawing Space]", ParagraphStyle('Center', alignment=TA_CENTER, fontSize=14, textColor=HexColor('#999999'))))
        
        doc.build(elements)
        
        with open(tmp_file.name, 'rb') as f:
            pdf_content = f.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=worksheet-{worksheet_id}.pdf"}
        )


@router.post("/printable-book/generate")
async def generate_printable_book(
    generation_id: str,
    include_activities: bool = True,
    personalization: Optional[dict] = None,
    user: dict = Depends(get_current_user)
):
    """Generate printable story book PDF - 4-6 credits"""
    credits_needed = 6 if include_activities else 4
    
    if user["credits"] < credits_needed:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {credits_needed} credits.")
    
    # Get the story
    story_gen = await db.generations.find_one({
        "id": generation_id,
        "userId": user["id"],
        "type": "STORY"
    }, {"_id": 0})
    
    if not story_gen:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story = story_gen.get("outputJson", {})
    
    # Apply personalization if provided
    if personalization:
        story_str = json.dumps(story)
        if personalization.get("child_name"):
            # Replace hero name with child's name
            characters = story.get("characters", [])
            if characters:
                old_name = characters[0].get("name", "")
                if old_name:
                    story_str = story_str.replace(old_name, personalization["child_name"])
        story = json.loads(story_str)
        
        if personalization.get("dedication"):
            story["dedication"] = personalization["dedication"]
        if personalization.get("birthday_message"):
            story["birthday_message"] = personalization["birthday_message"]
    
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
        "description": f"Printable Book: {story.get('title', 'Story')[:30]}",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Save book generation
    book_id = str(uuid.uuid4())
    await db.printable_books.insert_one({
        "id": book_id,
        "userId": user["id"],
        "storyId": generation_id,
        "story": story,
        "include_activities": include_activities,
        "personalization": personalization,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "bookId": book_id,
        "title": story.get("title"),
        "pages": len(story.get("scenes", [])) + 4,  # Cover + dedication + story pages + moral + activity
        "creditsUsed": credits_needed,
        "remainingCredits": user["credits"] - credits_needed,
        "downloadUrl": f"/api/story-tools/printable-book/{book_id}/pdf"
    }


@router.get("/printable-book/{book_id}/pdf")
async def download_printable_book_pdf(book_id: str, user: dict = Depends(get_current_user)):
    """Download printable book as PDF"""
    if not PDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF generation not available")
    
    book_doc = await db.printable_books.find_one({
        "id": book_id,
        "userId": user["id"]
    }, {"_id": 0})
    
    if not book_doc:
        raise HTTPException(status_code=404, detail="Book not found")
    
    story = book_doc.get("story", {})
    include_activities = book_doc.get("include_activities", True)
    
    # Create PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('BookTitle', parent=styles['Heading1'], fontSize=36, alignment=TA_CENTER, spaceAfter=30, textColor=HexColor('#6B21A8'))
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, spaceAfter=10)
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=18, spaceAfter=12, textColor=HexColor('#7C3AED'))
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=12, spaceAfter=8, leading=18)
        scene_title_style = ParagraphStyle('SceneTitle', parent=styles['Heading3'], fontSize=14, textColor=HexColor('#9333EA'))
        moral_style = ParagraphStyle('Moral', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, textColor=HexColor('#059669'))
        
        elements = []
        
        # === COVER PAGE ===
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(f"📖 {story.get('title', 'My Story')}", title_style))
        elements.append(Paragraph(story.get('synopsis', ''), subtitle_style))
        elements.append(Spacer(1, 1*inch))
        elements.append(Paragraph(f"Genre: {story.get('genre', 'Adventure')} | Ages: {story.get('ageGroup', 'All')}", subtitle_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Made with CreatorStudio AI", ParagraphStyle('Footer', alignment=TA_CENTER, fontSize=10, textColor=HexColor('#9CA3AF'))))
        elements.append(PageBreak())
        
        # === DEDICATION PAGE (if personalized) ===
        if story.get("dedication") or story.get("birthday_message"):
            elements.append(Spacer(1, 2*inch))
            if story.get("dedication"):
                elements.append(Paragraph(f"<i>{story.get('dedication')}</i>", ParagraphStyle('Dedication', alignment=TA_CENTER, fontSize=16, textColor=HexColor('#6B7280'))))
            if story.get("birthday_message"):
                elements.append(Spacer(1, 0.5*inch))
                elements.append(Paragraph(f"🎂 {story.get('birthday_message')}", ParagraphStyle('Birthday', alignment=TA_CENTER, fontSize=14)))
            elements.append(PageBreak())
        
        # === CHARACTERS PAGE ===
        elements.append(Paragraph("Meet the Characters", heading_style))
        elements.append(Spacer(1, 0.2*inch))
        for char in story.get("characters", []):
            elements.append(Paragraph(f"<b>{char.get('name', 'Character')}</b> - {char.get('role', 'character')}", body_style))
            elements.append(Paragraph(char.get('description', ''), body_style))
            elements.append(Spacer(1, 0.1*inch))
        elements.append(PageBreak())
        
        # === STORY PAGES ===
        for scene in story.get("scenes", []):
            elements.append(Paragraph(f"Chapter {scene.get('scene_number', '?')}: {scene.get('title', 'Scene')}", scene_title_style))
            if scene.get('setting'):
                elements.append(Paragraph(f"<i>📍 {scene.get('setting')}</i>", body_style))
            elements.append(Spacer(1, 0.1*inch))
            
            if scene.get('narration'):
                elements.append(Paragraph(scene.get('narration'), body_style))
            
            if scene.get('dialogue'):
                elements.append(Spacer(1, 0.1*inch))
                for d in scene.get('dialogue', []):
                    elements.append(Paragraph(f"<b>{d.get('speaker', 'Speaker')}:</b> \"{d.get('line', '')}\"", body_style))
            
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("[Illustration Space]", ParagraphStyle('ImagePlaceholder', alignment=TA_CENTER, fontSize=12, textColor=HexColor('#D1D5DB'))))
            elements.append(Spacer(1, 1*inch))
            elements.append(PageBreak())
        
        # === MORAL PAGE ===
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("The Moral of the Story", heading_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"✨ {story.get('moral', 'Every story has a lesson.')}", moral_style))
        elements.append(PageBreak())
        
        # === ACTIVITY PAGE (if included) ===
        if include_activities:
            elements.append(Paragraph("🎨 Activity Page", heading_style))
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("Draw your favorite scene from the story:", body_style))
            elements.append(Spacer(1, 3*inch))
            elements.append(Paragraph("What did you learn from this story?", body_style))
            elements.append(Paragraph("_" * 60, body_style))
            elements.append(Paragraph("_" * 60, body_style))
            elements.append(Paragraph("_" * 60, body_style))
        
        # === THE END ===
        elements.append(PageBreak())
        elements.append(Spacer(1, 3*inch))
        elements.append(Paragraph("~ The End ~", ParagraphStyle('End', alignment=TA_CENTER, fontSize=24, textColor=HexColor('#6B21A8'))))
        
        doc.build(elements)
        
        with open(tmp_file.name, 'rb') as f:
            pdf_content = f.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=storybook-{book_id}.pdf"}
        )
