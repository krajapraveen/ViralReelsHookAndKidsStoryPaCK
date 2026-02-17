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

# Import the Disney-style PDF generator
from pdf_generator import generate_pdf_simple, PAGE_THEMES

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
        
        # Generate Disney-style colorful PDF
        pdf_path = f"/tmp/printable_book_{book_id}.pdf"
        
        # Use the Disney-style PDF generator with HTML templates
        await generate_pdf_simple(story, pdf_path)
        
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
