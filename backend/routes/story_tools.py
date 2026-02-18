"""
Story Tools Routes - Worksheets, Printable Books, Teen Content
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import uuid
import os
import sys
import asyncio

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, deduct_credits, FILE_EXPIRY_MINUTES

# ReportLab imports for PDF generation (production-safe)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Page themes for colorful PDFs
PAGE_THEMES = [
    {"name": "lavender", "primary": "#8B5CF6", "secondary": "#F3E8FF", "accent": "#5B21B6"},
    {"name": "mint", "primary": "#10B981", "secondary": "#D1FAE5", "accent": "#047857"},
    {"name": "peach", "primary": "#F97316", "secondary": "#FFEDD5", "accent": "#C2410C"},
    {"name": "sky", "primary": "#3B82F6", "secondary": "#DBEAFE", "accent": "#1D4ED8"},
    {"name": "rose", "primary": "#F43F5E", "secondary": "#FFE4E6", "accent": "#BE123C"},
]


def generate_colorful_pdf(story: Dict, output_path: str):
    """Generate a colorful Disney-style PDF using ReportLab (production-safe)"""
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=A4,
        rightMargin=0.75*inch, 
        leftMargin=0.75*inch,
        topMargin=0.75*inch, 
        bottomMargin=0.75*inch
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'StoryTitle',
        parent=styles['Title'],
        fontSize=32,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#5B21B6'),
        leading=40
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=HexColor('#6B7280')
    )
    
    chapter_style = ParagraphStyle(
        'Chapter',
        parent=styles['Heading1'],
        fontSize=20,
        spaceBefore=30,
        spaceAfter=15,
        alignment=TA_CENTER,
        textColor=HexColor('#3B82F6')
    )
    
    body_style = ParagraphStyle(
        'StoryBody',
        parent=styles['Normal'],
        fontSize=13,
        spaceAfter=15,
        alignment=TA_JUSTIFY,
        leading=22,
        textColor=HexColor('#374151')
    )
    
    dialogue_style = ParagraphStyle(
        'Dialogue',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10,
        leftIndent=20,
        rightIndent=20,
        textColor=HexColor('#7C3AED'),
        leading=18
    )
    
    moral_style = ParagraphStyle(
        'Moral',
        parent=styles['Normal'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=HexColor('#059669'),
        leading=24
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=HexColor('#9CA3AF')
    )
    
    watermark_style = ParagraphStyle(
        'Watermark',
        parent=styles['Normal'],
        fontSize=48,
        alignment=TA_CENTER,
        textColor=HexColor('#E5E7EB')
    )
    
    elements = []
    
    # ===== COVER PAGE =====
    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph("✨ 📚 ✨", title_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(story.get('title', 'My Story'), title_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("A CreatorStudio AI Story", subtitle_style))
    
    if story.get('synopsis'):
        elements.append(Spacer(1, 0.5*inch))
        synopsis_style = ParagraphStyle(
            'Synopsis',
            parent=styles['Italic'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=HexColor('#6B7280'),
            leading=18
        )
        elements.append(Paragraph(f"<i>{story['synopsis']}</i>", synopsis_style))
    
    # Characters if present
    if story.get('characters'):
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("🌟 Characters 🌟", subtitle_style))
        for char in story.get('characters', [])[:5]:
            if isinstance(char, dict):
                char_text = f"<b>{char.get('name', 'Character')}</b> - {char.get('description', '')}"
            else:
                char_text = f"• {char}"
            elements.append(Paragraph(char_text, body_style))
    
    elements.append(PageBreak())
    
    # ===== STORY PAGES =====
    scenes = story.get('scenes', [])
    for i, scene in enumerate(scenes, 1):
        theme = PAGE_THEMES[i % len(PAGE_THEMES)]
        
        # Scene title
        if isinstance(scene, dict):
            scene_title = scene.get('title', f'Chapter {i}')
            narration = scene.get('narration', scene.get('description', ''))
            dialogue = scene.get('dialogue', [])
        else:
            scene_title = f'Chapter {i}'
            narration = str(scene)
            dialogue = []
        
        # Chapter heading with theme color
        chapter_colored = ParagraphStyle(
            f'Chapter{i}',
            parent=chapter_style,
            textColor=HexColor(theme['primary'])
        )
        elements.append(Paragraph(f"Chapter {i}", chapter_colored))
        elements.append(Paragraph(scene_title, subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Narration
        if narration:
            paragraphs = narration.split('\n') if '\n' in narration else [narration]
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), body_style))
        
        # Dialogue
        if dialogue:
            elements.append(Spacer(1, 0.2*inch))
            for d in dialogue[:3]:
                if isinstance(d, dict):
                    speaker = d.get('speaker', 'Character')
                    text = d.get('text') or d.get('line', '')
                    if text:
                        elements.append(Paragraph(f'<b>{speaker}:</b> "{text}"', dialogue_style))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Page break after every 2 scenes
        if i < len(scenes):
            if i % 2 == 0:
                elements.append(PageBreak())
    
    elements.append(PageBreak())
    
    # ===== MORAL PAGE =====
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("💫 The Lesson 💫", chapter_style))
    elements.append(Spacer(1, 0.5*inch))
    moral = story.get('moral', 'Every adventure teaches us something wonderful!')
    elements.append(Paragraph(f'"{moral}"', moral_style))
    elements.append(PageBreak())
    
    # ===== ENDING PAGE =====
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("✨ The End ✨", title_style))
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("Thank you for reading!", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Created with CreatorStudio AI", footer_style))
    elements.append(Paragraph(f"© {datetime.now().year} - All rights reserved", footer_style))
    
    # Build PDF
    doc.build(elements)
    return output_path


router = APIRouter(prefix="/story-tools", tags=["Story Tools"])


@router.post("/worksheet/{generation_id}")
async def generate_worksheet(generation_id: str, user: dict = Depends(get_current_user)):
    """Generate educational worksheet from story (1 credit)"""
    # Get the story generation
    generation = await db.generations.find_one(
        {"id": generation_id, "userId": user["id"], "type": "STORY"},
        {"_id": 0}
    )
    
    if not generation:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check credits
    if user.get("credits", 0) < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    story = generation.get("outputJson", {})
    
    # Generate worksheet content
    worksheet = {
        "id": str(uuid.uuid4()),
        "generationId": generation_id,
        "userId": user["id"],
        "title": f"Worksheet: {story.get('title', 'Story')}",
        "activities": [
            {
                "type": "vocabulary",
                "title": "New Words",
                "words": story.get("keywords", [])[:5],
                "instructions": "Match each word with its meaning"
            },
            {
                "type": "comprehension",
                "title": "Reading Questions",
                "questions": [
                    f"What is the main character's name?",
                    f"What lesson did the story teach?",
                    f"How did the story end?",
                    f"What was your favorite part?"
                ]
            },
            {
                "type": "creative",
                "title": "Draw Your Favorite Scene",
                "instructions": "Draw a picture of your favorite moment from the story"
            },
            {
                "type": "sequencing",
                "title": "Put in Order",
                "instructions": "Number these events in the order they happened"
            }
        ],
        "ageGroup": story.get("ageGroup", "4-6"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
    }
    
    await db.worksheets.insert_one(worksheet)
    
    # Deduct credit
    await deduct_credits(user["id"], 1, "Worksheet generation")
    
    return {
        "success": True,
        "worksheet": worksheet,
        "creditsUsed": 1,
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes"
    }


@router.post("/printable-book/{generation_id}")
async def generate_printable_book(
    generation_id: str,
    include_activities: bool = True,
    personalization: Optional[Dict[str, Any]] = None,
    user: dict = Depends(get_current_user)
):
    """Generate Disney-style colorful printable book from story (5 credits)"""
    try:
        # Get the story generation
        generation = await db.generations.find_one(
            {"id": generation_id, "userId": user["id"], "type": "STORY"},
            {"_id": 0}
        )
        
        if not generation:
            raise HTTPException(status_code=404, detail="Story not found")
        
        cost = 5
        if user.get("credits", 0) < cost:
            raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
        
        story = generation.get("outputJson", {})
        book_id = str(uuid.uuid4())
        
        # Create printable book record with story data for PDF generation
        book = {
            "id": book_id,
            "generationId": generation_id,
            "userId": user["id"],
            "title": story.get("title", "My Story"),
            "synopsis": story.get("synopsis", ""),
            "scenes": story.get("scenes", []),
            "characters": story.get("characters", []),
            "moral": story.get("moral", "Every adventure teaches us something new!"),
            "genre": story.get("genre", "Adventure"),
            "ageGroup": story.get("ageGroup", "3-8"),
            "includeActivities": include_activities,
            "personalization": personalization or {},
            "status": "processing",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
        }
        
        await db.printable_books.insert_one(book)
        
        # Generate colorful PDF using ReportLab (production-safe)
        pdf_path = f"/tmp/printable_book_{book_id}.pdf"
        
        # Use the ReportLab-based PDF generator (no Playwright dependency)
        generate_colorful_pdf(story, pdf_path)
        
        # Verify PDF was created
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
        # Deduct credits
        new_balance = await deduct_credits(user["id"], cost, f"Printable book: {story.get('title', 'Story')[:30]}")
        
        # Mark as completed
        await db.printable_books.update_one(
            {"id": book_id},
            {"$set": {"status": "completed", "pdfPath": pdf_path}}
        )
        
        logger.info(f"Disney-style PDF generated successfully: {pdf_path}")
        
        return {
            "success": True,
            "bookId": book_id,
            "creditsUsed": cost,
            "remainingCredits": new_balance,
            "downloadUrl": f"/api/story-tools/download-book/{book_id}",
            "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
            "message": f"⚠️ Download within {FILE_EXPIRY_MINUTES} minutes - files are auto-deleted for security!"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Printable book generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/download-book/{book_id}")
async def download_printable_book_pdf(book_id: str, user: dict = Depends(get_current_user)):
    """Download Disney-style printable book PDF"""
    try:
        book = await db.printable_books.find_one(
            {"id": book_id, "userId": user["id"]},
            {"_id": 0}
        )
        
        if not book:
            raise HTTPException(status_code=404, detail="Book not found or access denied")
        
        # Check expiry
        expiry_str = book.get("expiresAt")
        if expiry_str:
            try:
                expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expiry_time:
                    raise HTTPException(status_code=410, detail="Download link expired. Files are available for 3 minutes only.")
            except ValueError:
                pass  # Skip expiry check if parsing fails
        
        # Check for PDF file
        pdf_path = f"/tmp/printable_book_{book_id}.pdf"
        
        if not os.path.exists(pdf_path):
            # Regenerate Disney-style PDF if missing
            logger.info(f"Regenerating Disney-style PDF for book {book_id}")
            await generate_pdf_simple(book, pdf_path)
        
        if os.path.exists(pdf_path):
            # Sanitize filename
            safe_title = "".join(c for c in book.get('title', 'story') if c.isalnum() or c in ' -_').strip()[:50]
            return FileResponse(
                pdf_path,
                filename=f"{safe_title}_printable.pdf",
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_title}_printable.pdf"'
                }
            )
        
        raise HTTPException(status_code=500, detail="PDF file could not be generated")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/worksheets")
async def get_user_worksheets(user: dict = Depends(get_current_user)):
    """Get user's worksheets"""
    worksheets = await db.worksheets.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(50).to_list(length=50)
    
    return {"worksheets": worksheets}


@router.get("/printable-books")
async def get_user_printable_books(user: dict = Depends(get_current_user)):
    """Get user's printable books"""
    books = await db.printable_books.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(50).to_list(length=50)
    
    return {"books": books}
