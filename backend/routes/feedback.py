"""
Feedback Routes - Suggestions, Reviews, Contact
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
import uuid
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_optional_user, log_exception
from models.schemas import FeedbackSuggestion, ContactMessage, ChatMessage

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
        # Verify reCAPTCHA v3
        from routes.auth import CAPTCHA_ENABLED, verify_recaptcha
        captcha_token = request.headers.get('X-Captcha-Token', '')
        if CAPTCHA_ENABLED and not await verify_recaptcha(captcha_token, expected_action="contact"):
            raise HTTPException(status_code=400, detail="CAPTCHA verification failed. Please try again.")

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
        
    except HTTPException:
        raise
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
    """Handle chatbot messages with AI"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Common questions and quick responses
        quick_responses = {
            "pricing": "You can check our pricing at /pricing page. We offer flexible credit packs starting from ₹499!",
            "features": "CreatorStudio AI offers: Viral Reel Generator, Kids Story Pack Creator, GenStudio AI tools, Creator Pro features, and TwinFinder!",
            "help": "I can help you with: 1) Creating viral reels 2) Generating kids stories 3) Using AI tools 4) Understanding pricing",
            "contact": "You can reach us at support@creatorstudio.ai or use the Contact page.",
        }
        
        # Check for quick responses
        message_lower = data.message.lower()
        for keyword, response in quick_responses.items():
            if keyword in message_lower:
                return {"success": True, "response": response, "sessionId": data.sessionId}
        
        # Use AI for complex queries
        chat = LlmChat().with_model("gemini-2.0-flash")
        prompt = f"""You are a helpful assistant for CreatorStudio AI, a platform for creating viral reels and kids story videos.
        
Answer this user question concisely (2-3 sentences max): {data.message}

Key features: Reel Generator, Story Generator, GenStudio (Text-to-Image, Text-to-Video), Creator Pro Tools, TwinFinder.
Pricing starts at ₹499 for credit packs."""
        
        result = await chat.send_message(UserMessage(text=prompt))
        return {"success": True, "response": result.text, "sessionId": data.sessionId}
        
    except Exception as e:
        return {
            "success": True,
            "response": "Thanks for your message! Our team will review it. For immediate assistance, check our FAQ or contact support@creatorstudio.ai",
            "sessionId": data.sessionId
        }
