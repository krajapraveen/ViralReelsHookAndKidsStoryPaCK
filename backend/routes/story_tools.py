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
import io

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, deduct_credits, FILE_EXPIRY_MINUTES

# PDF Generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

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


def generate_story_pdf(book: dict, pdf_path: str):
    """Generate a beautifully formatted PDF storybook"""
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#2D3748')
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=HexColor('#718096')
    )
    
    heading_style = ParagraphStyle(
        'SceneHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=HexColor('#4A5568')
    )
    
    body_style = ParagraphStyle(
        'StoryBody',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leading=18,
        textColor=HexColor('#2D3748')
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=HexColor('#A0AEC0')
    )
    
    story = []
    
    # Cover Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph(book.get('title', 'My Story'), title_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("A CreatorStudio AI Story", subtitle_style))
    story.append(Spacer(1, 1*inch))
    
    if book.get('synopsis'):
        synopsis_style = ParagraphStyle(
            'Synopsis',
            parent=styles['Italic'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=HexColor('#4A5568')
        )
        story.append(Paragraph(f"<i>{book['synopsis']}</i>", synopsis_style))
    
    story.append(PageBreak())
    
    # Characters Page
    if book.get('characters'):
        story.append(Paragraph("Meet the Characters", heading_style))
        story.append(Spacer(1, 0.25*inch))
        for char in book.get('characters', []):
            if isinstance(char, dict):
                char_text = f"<b>{char.get('name', 'Character')}</b>: {char.get('description', '')}"
            else:
                char_text = f"• {char}"
            story.append(Paragraph(char_text, body_style))
        story.append(PageBreak())
    
    # Story Scenes
    scenes = book.get('scenes', [])
    for i, scene in enumerate(scenes, 1):
        if isinstance(scene, dict):
            scene_title = scene.get('title', f'Scene {i}')
            narration = scene.get('narration', scene.get('description', ''))
        else:
            scene_title = f'Scene {i}'
            narration = str(scene)
        
        story.append(Paragraph(f"Chapter {i}: {scene_title}", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Split long narration into paragraphs
        paragraphs = narration.split('\n') if '\n' in narration else [narration]
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Add page break every 2 scenes for readability
        if i < len(scenes) and i % 2 == 0:
            story.append(PageBreak())
    
    # Activities Page
    if book.get('includeActivities', True):
        story.append(PageBreak())
        story.append(Paragraph("Activities", heading_style))
        story.append(Spacer(1, 0.25*inch))
        
        activities = [
            "🎨 Draw your favorite scene from the story",
            "📝 Write what you would do if you were the main character",
            "🤔 What was the lesson you learned from this story?",
            "✏️ Create a new ending for the story",
            "🗣️ Retell the story to a friend or family member"
        ]
        
        for activity in activities:
            story.append(Paragraph(f"• {activity}", body_style))
            story.append(Spacer(1, 0.5*inch))  # Space for writing
    
    # Footer
    story.append(PageBreak())
    story.append(Spacer(1, 3*inch))
    story.append(Paragraph("The End", title_style))
    story.append(Spacer(1, 1*inch))
    story.append(Paragraph("Created with CreatorStudio AI", footer_style))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", footer_style))
    
    # Build PDF
    doc.build(story)
    return pdf_path


@router.post("/printable-book/{generation_id}")
async def generate_printable_book(
    generation_id: str,
    include_activities: bool = True,
    personalization: Optional[Dict[str, Any]] = None,
    user: dict = Depends(get_current_user)
):
    """Generate printable book from story (5 credits)"""
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
        
        # Create printable book record
        book = {
            "id": book_id,
            "generationId": generation_id,
            "userId": user["id"],
            "title": story.get("title", "My Story"),
            "synopsis": story.get("synopsis", ""),
            "scenes": story.get("scenes", []),
            "characters": story.get("characters", []),
            "includeActivities": include_activities,
            "personalization": personalization or {},
            "status": "processing",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=FILE_EXPIRY_MINUTES)).isoformat()
        }
        
        await db.printable_books.insert_one(book)
        
        # Generate actual PDF file
        pdf_path = f"/tmp/printable_book_{book_id}.pdf"
        generate_story_pdf(book, pdf_path)
        
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
        
        logger.info(f"PDF generated successfully: {pdf_path}")
        
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
    """Download printable book PDF"""
    book = await db.printable_books.find_one(
        {"id": book_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found or expired")
    
    # Check expiry
    expiry_str = book.get("expiresAt")
    if expiry_str:
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry_time:
            raise HTTPException(status_code=410, detail="Download link expired. Files are available for 3 minutes only.")
    
    # Check for PDF file
    pdf_path = f"/tmp/printable_book_{book_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            filename=f"{book.get('title', 'story')}_printable.pdf",
            media_type="application/pdf"
        )
    
    # Return book data for client-side PDF generation
    return {
        "book": book,
        "message": "PDF not available. Use book data for client-side generation."
    }


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
