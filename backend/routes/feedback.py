"""Feedback routes"""
from fastapi import APIRouter, Request
from datetime import datetime, timezone
import uuid
from ..utils.database import db
from ..models.schemas import FeedbackSuggestion, ContactMessage

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/suggestion")
async def submit_suggestion(data: FeedbackSuggestion):
    """Submit user feedback/suggestion"""
    feedback = {
        "id": str(uuid.uuid4()),
        "rating": data.rating,
        "category": data.category,
        "suggestion": data.suggestion,
        "email": data.email,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback)
    
    return {"message": "Thank you for your feedback!", "id": feedback["id"]}
