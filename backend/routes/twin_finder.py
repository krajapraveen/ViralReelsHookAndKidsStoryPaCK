"""
TwinFinder - Face Lookalike Finder
Find your celebrity lookalike using AI face embeddings
Uses free-tier face analysis APIs
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import base64
import os
import json
import httpx
import traceback
import math
import sys

# Import from shared module (absolute import for server.py compatibility)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared import db, logger, get_current_user, deduct_credits, log_exception, LLM_AVAILABLE, EMERGENT_LLM_KEY, FILE_EXPIRY_MINUTES
except ImportError:
    from ..shared import db, logger, get_current_user, deduct_credits, log_exception, LLM_AVAILABLE, EMERGENT_LLM_KEY, FILE_EXPIRY_MINUTES

router = APIRouter(prefix="/twinfinder", tags=["TwinFinder"])

# Credit costs
TWINFINDER_COSTS = {
    "analyze_face": 5,
    "find_match": 10,
    "celebrity_match": 15,
    "share_result": 0
}

# Celebrity database (mock - in production, use actual embeddings)
CELEBRITY_DATABASE = [
    {"id": "cel_001", "name": "Chris Hemsworth", "category": "actor", "traits": ["blonde", "blue_eyes", "strong_jaw", "athletic"]},
    {"id": "cel_002", "name": "Scarlett Johansson", "category": "actress", "traits": ["blonde", "green_eyes", "oval_face", "full_lips"]},
    {"id": "cel_003", "name": "Brad Pitt", "category": "actor", "traits": ["blonde", "blue_eyes", "square_jaw", "dimples"]},
    {"id": "cel_004", "name": "Angelina Jolie", "category": "actress", "traits": ["brunette", "green_eyes", "high_cheekbones", "full_lips"]},
    {"id": "cel_005", "name": "Leonardo DiCaprio", "category": "actor", "traits": ["blonde", "blue_eyes", "round_face", "boyish"]},
    {"id": "cel_006", "name": "Jennifer Lawrence", "category": "actress", "traits": ["blonde", "blue_eyes", "round_face", "natural"]},
    {"id": "cel_007", "name": "Ryan Gosling", "category": "actor", "traits": ["blonde", "blue_eyes", "strong_nose", "intense"]},
    {"id": "cel_008", "name": "Emma Stone", "category": "actress", "traits": ["red", "green_eyes", "round_eyes", "porcelain"]},
    {"id": "cel_009", "name": "Tom Hardy", "category": "actor", "traits": ["brunette", "blue_eyes", "full_lips", "rugged"]},
    {"id": "cel_010", "name": "Margot Robbie", "category": "actress", "traits": ["blonde", "blue_eyes", "high_cheekbones", "elegant"]},
    {"id": "cel_011", "name": "Idris Elba", "category": "actor", "traits": ["black", "brown_eyes", "strong_jaw", "distinguished"]},
    {"id": "cel_012", "name": "Zendaya", "category": "actress", "traits": ["brunette", "brown_eyes", "oval_face", "youthful"]},
    {"id": "cel_013", "name": "Jason Momoa", "category": "actor", "traits": ["black", "brown_eyes", "strong_jaw", "rugged"]},
    {"id": "cel_014", "name": "Lupita Nyong'o", "category": "actress", "traits": ["black", "brown_eyes", "oval_face", "radiant"]},
    {"id": "cel_015", "name": "Henry Cavill", "category": "actor", "traits": ["brunette", "blue_eyes", "square_jaw", "classic"]},
    {"id": "cel_016", "name": "Gal Gadot", "category": "actress", "traits": ["brunette", "brown_eyes", "strong_features", "athletic"]},
    {"id": "cel_017", "name": "Chris Evans", "category": "actor", "traits": ["brunette", "blue_eyes", "strong_jaw", "all_american"]},
    {"id": "cel_018", "name": "Anne Hathaway", "category": "actress", "traits": ["brunette", "brown_eyes", "large_eyes", "elegant"]},
    {"id": "cel_019", "name": "Keanu Reeves", "category": "actor", "traits": ["black", "brown_eyes", "angular_face", "timeless"]},
    {"id": "cel_020", "name": "Natalie Portman", "category": "actress", "traits": ["brunette", "brown_eyes", "heart_face", "classic"]},
]


async def analyze_face_with_ai(image_base64: str) -> dict:
    """Analyze face features using Gemini Vision"""
    if not LLM_AVAILABLE or not EMERGENT_LLM_KEY:
        # Return mock analysis if AI not available
        return {
            "success": True,
            "traits": ["oval_face", "brown_eyes", "brunette"],
            "confidence": 0.75,
            "mock": True
        }
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            model="gemini",
            model_name="gemini-2.0-flash",
            system_message="""You are a face analysis AI. Analyze the face in the image and return a JSON object with these fields:
- hair_color: blonde, brunette, black, red, gray
- eye_color: blue, green, brown, hazel, gray
- face_shape: oval, round, square, heart, oblong
- notable_features: list of 3-5 distinctive features (e.g., high_cheekbones, full_lips, strong_jaw, dimples, etc.)
- estimated_age_range: e.g., "25-35"
- gender_presentation: male, female

Return ONLY valid JSON, no explanation.""",
            session_id=f"twinfinder-{uuid.uuid4().hex[:8]}"
        )
        
        message = UserMessage(
            text="Analyze this face and return the analysis as JSON.",
            images=[ImageContent(image_base64=image_base64, media_type="image/jpeg")]
        )
        
        response = await chat.send_message_async(message)
        
        # Parse response
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        analysis = json.loads(response_text.strip())
        
        # Convert to traits format
        traits = [
            analysis.get("hair_color", "brunette"),
            analysis.get("eye_color", "brown") + "_eyes",
            analysis.get("face_shape", "oval") + "_face"
        ]
        traits.extend(analysis.get("notable_features", [])[:3])
        
        return {
            "success": True,
            "traits": traits,
            "fullAnalysis": analysis,
            "confidence": 0.85
        }
        
    except Exception as e:
        logger.error(f"Face analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "traits": ["oval_face", "brown_eyes", "brunette"],
            "confidence": 0.5
        }


def calculate_similarity(traits1: List[str], traits2: List[str]) -> float:
    """Calculate similarity score between two trait lists"""
    if not traits1 or not traits2:
        return 0.0
    
    traits1_lower = [t.lower() for t in traits1]
    traits2_lower = [t.lower() for t in traits2]
    
    matches = len(set(traits1_lower) & set(traits2_lower))
    total = len(set(traits1_lower) | set(traits2_lower))
    
    return round((matches / total) * 100, 1) if total > 0 else 0.0


def find_celebrity_matches(user_traits: List[str], limit: int = 5) -> List[dict]:
    """Find celebrity matches based on traits"""
    matches = []
    
    for celeb in CELEBRITY_DATABASE:
        similarity = calculate_similarity(user_traits, celeb["traits"])
        matches.append({
            "celebrity": celeb["name"],
            "category": celeb["category"],
            "similarity": similarity,
            "matchingTraits": list(set([t.lower() for t in user_traits]) & set([t.lower() for t in celeb["traits"]]))
        })
    
    # Sort by similarity
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    
    return matches[:limit]


# =============================================================================
# TWINFINDER ENDPOINTS
# =============================================================================

@router.get("/dashboard")
async def twinfinder_dashboard(user: dict = Depends(get_current_user)):
    """Get TwinFinder dashboard data"""
    # Get user's previous analyses
    analyses = await db.twinfinder_analyses.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(10).to_list(10)
    
    # Get leaderboard (most shared)
    leaderboard = await db.twinfinder_shares.aggregate([
        {"$group": {"_id": "$celebrity", "shares": {"$sum": 1}}},
        {"$sort": {"shares": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    return {
        "credits": user.get("credits", 0),
        "recentAnalyses": analyses,
        "leaderboard": [{"celebrity": l["_id"], "shares": l["shares"]} for l in leaderboard],
        "costs": TWINFINDER_COSTS,
        "celebrities": len(CELEBRITY_DATABASE)
    }


@router.post("/analyze")
async def analyze_face(
    file: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    user: dict = Depends(get_current_user)
):
    """Analyze uploaded face image - 5 credits"""
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Please confirm consent to analyze your image")
    
    cost = TWINFINDER_COSTS["analyze_face"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Validate file
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    # Convert to base64
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    # Analyze face
    analysis_result = await analyze_face_with_ai(image_base64)
    
    if not analysis_result.get("success"):
        raise HTTPException(status_code=500, detail="Face analysis failed")
    
    # Save analysis
    analysis_id = str(uuid.uuid4())
    analysis = {
        "id": analysis_id,
        "userId": user["id"],
        "traits": analysis_result.get("traits", []),
        "fullAnalysis": analysis_result.get("fullAnalysis"),
        "confidence": analysis_result.get("confidence", 0.5),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    }
    await db.twinfinder_analyses.insert_one(analysis)
    
    # Deduct credits
    new_balance = await deduct_credits(user["id"], cost, "TwinFinder: Face Analysis")
    
    return {
        "success": True,
        "analysisId": analysis_id,
        "traits": analysis_result.get("traits", []),
        "fullAnalysis": analysis_result.get("fullAnalysis"),
        "confidence": analysis_result.get("confidence", 0.5),
        "creditsUsed": cost,
        "remainingCredits": new_balance,
        "message": "Face analyzed! Now use /find-match to find your celebrity lookalike."
    }


@router.post("/find-match/{analysis_id}")
async def find_celebrity_match(
    analysis_id: str,
    limit: int = 5,
    user: dict = Depends(get_current_user)
):
    """Find celebrity matches for an analyzed face - 10 credits"""
    cost = TWINFINDER_COSTS["celebrity_match"]
    if user.get("credits", 0) < cost:
        raise HTTPException(status_code=400, detail=f"Insufficient credits. Need {cost} credits.")
    
    # Get analysis
    analysis = await db.twinfinder_analyses.find_one(
        {"id": analysis_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Find matches
    matches = find_celebrity_matches(analysis.get("traits", []), limit)
    
    # Save match result
    match_id = str(uuid.uuid4())
    match_result = {
        "id": match_id,
        "userId": user["id"],
        "analysisId": analysis_id,
        "matches": matches,
        "topMatch": matches[0] if matches else None,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.twinfinder_matches.insert_one(match_result)
    
    # Update analysis with match
    await db.twinfinder_analyses.update_one(
        {"id": analysis_id},
        {"$set": {"matchId": match_id, "topMatch": matches[0] if matches else None}}
    )
    
    # Deduct credits
    new_balance = await deduct_credits(user["id"], cost, f"TwinFinder: Celebrity Match")
    
    return {
        "success": True,
        "matchId": match_id,
        "matches": matches,
        "topMatch": matches[0] if matches else None,
        "shareUrl": f"/twinfinder/share/{match_id}",
        "creditsUsed": cost,
        "remainingCredits": new_balance
    }


@router.get("/result/{match_id}")
async def get_match_result(match_id: str, user: dict = Depends(get_current_user)):
    """Get a match result by ID"""
    match = await db.twinfinder_matches.find_one(
        {"id": match_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")
    
    return match


@router.post("/share/{match_id}")
async def share_result(match_id: str, platform: str = "twitter", user: dict = Depends(get_current_user)):
    """Generate shareable content for result - FREE"""
    match = await db.twinfinder_matches.find_one(
        {"id": match_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")
    
    top_match = match.get("topMatch", {})
    celebrity = top_match.get("celebrity", "Unknown")
    similarity = top_match.get("similarity", 0)
    
    # Generate share content
    share_messages = {
        "twitter": f"🌟 I just found out I look {similarity}% like {celebrity}! Find your celebrity twin at CreatorStudio AI #TwinFinder #CelebrityLookalike",
        "instagram": f"🌟 My celebrity lookalike is {celebrity}! ({similarity}% match)\n\nFind your twin at CreatorStudio AI ✨\n\n#TwinFinder #CelebrityLookalike #AI",
        "facebook": f"I just discovered my celebrity lookalike is {celebrity} with a {similarity}% match! 🌟 Try it yourself at CreatorStudio AI!",
        "whatsapp": f"OMG! I look {similarity}% like {celebrity}! 🌟 Find your celebrity twin: [link]"
    }
    
    # Log share
    await db.twinfinder_shares.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "matchId": match_id,
        "celebrity": celebrity,
        "platform": platform,
        "sharedAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "shareText": share_messages.get(platform, share_messages["twitter"]),
        "celebrity": celebrity,
        "similarity": similarity,
        "platform": platform
    }


@router.get("/history")
async def get_twinfinder_history(
    page: int = 0,
    size: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get user's TwinFinder history"""
    skip = page * size
    
    matches = await db.twinfinder_matches.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).skip(skip).limit(size).to_list(size)
    
    total = await db.twinfinder_matches.count_documents({"userId": user["id"]})
    
    return {
        "matches": matches,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/celebrities")
async def get_celebrity_list(category: Optional[str] = None):
    """Get list of celebrities in database"""
    celebs = CELEBRITY_DATABASE
    
    if category:
        celebs = [c for c in celebs if c["category"].lower() == category.lower()]
    
    return {
        "celebrities": [{"name": c["name"], "category": c["category"]} for c in celebs],
        "total": len(celebs),
        "categories": list(set(c["category"] for c in CELEBRITY_DATABASE))
    }


@router.get("/costs")
async def get_twinfinder_costs():
    """Get TwinFinder feature costs"""
    return {
        "costs": TWINFINDER_COSTS,
        "features": {
            "analyze_face": "AI-powered face analysis",
            "celebrity_match": "Find your celebrity lookalike",
            "share_result": "Share your result (FREE)"
        }
    }
