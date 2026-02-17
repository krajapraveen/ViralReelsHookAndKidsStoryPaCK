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

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, deduct_credits, FILE_EXPIRY_MINUTES

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
    """Generate printable book from story (5 credits)"""
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
    
    # Create printable book record
    book = {
        "id": str(uuid.uuid4()),
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
    
    # Deduct credits
    await deduct_credits(user["id"], cost, f"Printable book: {story.get('title', 'Story')[:30]}")
    
    # Mark as completed (PDF generation would happen asynchronously in production)
    await db.printable_books.update_one(
        {"id": book["id"]},
        {"$set": {"status": "completed"}}
    )
    
    return {
        "success": True,
        "bookId": book["id"],
        "creditsUsed": cost,
        "downloadUrl": f"/api/story-tools/download-book/{book['id']}",
        "expiresIn": f"{FILE_EXPIRY_MINUTES} minutes",
        "message": f"⚠️ Download within {FILE_EXPIRY_MINUTES} minutes - files are auto-deleted for security!"
    }


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
