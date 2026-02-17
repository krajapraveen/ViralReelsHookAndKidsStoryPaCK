"""
Feedback Routes - Suggestions, Reviews, Contact
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
import uuid

from ..shared import db, logger, get_optional_user, log_exception
from ..models.schemas import FeedbackSuggestion, ContactMessage, ChatMessage

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/suggestion")
async def submit_suggestion(request: Request, data: FeedbackSuggestion):
    """Submit a suggestion or feature request"""
    try:
        user = await get_optional_user(request)
        
        feedback = {
            "id": str(uuid.uuid4()),
            "type": "suggestion",
            "rating": data.rating,
            "category": data.category,
            "suggestion": data.suggestion,
            "email": data.email,
            "userId": user["id"] if user else None,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.feedback.insert_one(feedback)
        
        return {"success": True, "message": "Thank you for your feedback!"}
        
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.post("/")
async def submit_feedback_legacy(request: Request):
    """Legacy feedback endpoint for backwards compatibility"""
    try:
        body = await request.json()
        user = await get_optional_user(request)
        
        feedback = {
            "id": str(uuid.uuid4()),
            "type": body.get("type", "general"),
            "rating": body.get("rating", 0),
            "category": body.get("category", "general"),
            "message": body.get("message", body.get("suggestion", "")),
            "email": body.get("email"),
            "userId": user["id"] if user else None,
            "metadata": body.get("metadata", {}),
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.feedback.insert_one(feedback)
        
        return {"success": True, "message": "Feedback received!"}
        
    except Exception as e:
        logger.error(f"Legacy feedback error: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get("/reviews")
async def get_reviews():
    """Get public reviews/testimonials"""
    reviews = await db.feedback.find(
        {"type": "review", "public": True},
        {"_id": 0, "email": 0, "userId": 0}
    ).sort("rating", -1).limit(20).to_list(length=20)
    
    return {"reviews": reviews}


@router.post("/contact")
async def submit_contact(request: Request, data: ContactMessage):
    """Submit a contact message"""
    try:
        contact = {
            "id": str(uuid.uuid4()),
            "name": data.name,
            "email": data.email,
            "subject": data.subject,
            "message": data.message,
            "status": "new",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.contact_messages.insert_one(contact)
        
        logger.info(f"Contact message received from {data.email}")
        
        return {"success": True, "message": "Your message has been sent. We'll get back to you soon!"}
        
    except Exception as e:
        await log_exception(
            functionality="contact_form",
            error_type="CONTACT_SUBMISSION_ERROR",
            error_message=str(e),
            user_email=data.email,
            severity="WARNING"
        )
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/chatbot")
async def chatbot_message(data: ChatMessage):
    """Handle chatbot messages (placeholder)"""
    return {
        "response": "Thanks for your message! Our team will review it. For immediate assistance, please check our FAQ or contact support.",
        "sessionId": data.sessionId
    }
