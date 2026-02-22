"""
Feature Requests Routes - User Feature Suggestions and Voting
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import os
import sys

# Ensure backend directory is in path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/feature-requests", tags=["Feature Requests"])

# =============================================================================
# MODELS
# =============================================================================

class FeatureRequestCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: str = Field(default="OTHER")


class FeatureRequestVote(BaseModel):
    requestId: str


# =============================================================================
# CONSTANTS
# =============================================================================

CATEGORIES = [
    {"value": "NEW_FEATURE", "label": "New Feature"},
    {"value": "IMPROVEMENT", "label": "Improvement"},
    {"value": "BUG_FIX", "label": "Bug Fix"},
    {"value": "UI_UX", "label": "UI/UX"},
    {"value": "INTEGRATION", "label": "Integration"},
    {"value": "PERFORMANCE", "label": "Performance"},
    {"value": "OTHER", "label": "Other"},
]

STATUS_OPTIONS = ["PENDING", "UNDER_REVIEW", "PLANNED", "IN_PROGRESS", "COMPLETED", "DECLINED"]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("")
async def get_feature_requests(
    user: dict = Depends(get_current_user),
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get all feature requests with vote counts"""
    user_id = user["id"]
    
    # Build query
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    # Get feature requests
    requests_cursor = db.feature_requests.find(
        query,
        {"_id": 0}
    ).sort([("voteCount", -1), ("createdAt", -1)]).skip(skip).limit(limit)
    
    requests_list = await requests_cursor.to_list(limit)
    
    # Get user's votes
    user_votes = await db.feature_request_votes.find(
        {"userId": user_id},
        {"requestId": 1, "_id": 0}
    ).to_list(1000)
    
    voted_ids = {v["requestId"] for v in user_votes}
    
    # Enrich with user-specific data
    for req in requests_list:
        req["hasVoted"] = req["id"] in voted_ids
        req["isOwner"] = req.get("userId") == user_id
        # Get category label
        cat_info = next((c for c in CATEGORIES if c["value"] == req.get("category", "OTHER")), None)
        req["categoryLabel"] = cat_info["label"] if cat_info else "Other"
    
    total = await db.feature_requests.count_documents(query)
    
    return {
        "content": requests_list,
        "total": total
    }


@router.get("/categories")
async def get_categories():
    """Get available categories for feature requests"""
    return {"categories": CATEGORIES}


@router.post("")
@limiter.limit("5/minute")
async def create_feature_request(
    request: Request,
    data: FeatureRequestCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new feature request"""
    user_id = user["id"]
    
    # Check if similar request exists
    existing = await db.feature_requests.find_one({
        "title": {"$regex": data.title, "$options": "i"},
        "status": {"$nin": ["COMPLETED", "DECLINED"]}
    })
    
    if existing:
        return {
            "success": False,
            "error": "A similar feature request already exists. Please vote for it instead!",
            "existingId": existing["id"]
        }
    
    request_id = str(uuid.uuid4())
    
    feature_request = {
        "id": request_id,
        "userId": user_id,
        "authorName": user.get("name", "Anonymous"),
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "status": "PENDING",
        "voteCount": 1,  # Creator's vote included
        "adminResponse": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feature_requests.insert_one(feature_request)
    
    # Auto-vote by creator
    await db.feature_request_votes.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "requestId": request_id,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "requestId": request_id,
        "message": "Feature request submitted! Your vote has been added."
    }


@router.post("/{request_id}/vote")
async def vote_feature_request(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Vote for a feature request"""
    user_id = user["id"]
    
    # Check if request exists
    feature_request = await db.feature_requests.find_one({"id": request_id})
    if not feature_request:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Check if already voted
    existing_vote = await db.feature_request_votes.find_one({
        "userId": user_id,
        "requestId": request_id
    })
    
    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted for this request")
    
    # Add vote
    await db.feature_request_votes.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "requestId": request_id,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    # Increment vote count
    await db.feature_requests.update_one(
        {"id": request_id},
        {"$inc": {"voteCount": 1}, "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "message": "Vote added!"}


@router.delete("/{request_id}/vote")
async def remove_vote(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Remove vote from a feature request"""
    user_id = user["id"]
    
    # Check if vote exists
    existing_vote = await db.feature_request_votes.find_one({
        "userId": user_id,
        "requestId": request_id
    })
    
    if not existing_vote:
        raise HTTPException(status_code=400, detail="You haven't voted for this request")
    
    # Remove vote
    await db.feature_request_votes.delete_one({
        "userId": user_id,
        "requestId": request_id
    })
    
    # Decrement vote count
    await db.feature_requests.update_one(
        {"id": request_id},
        {"$inc": {"voteCount": -1}, "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "message": "Vote removed"}


@router.get("/{request_id}")
async def get_feature_request(
    request_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific feature request"""
    feature_request = await db.feature_requests.find_one(
        {"id": request_id},
        {"_id": 0}
    )
    
    if not feature_request:
        raise HTTPException(status_code=404, detail="Feature request not found")
    
    # Check if user has voted
    vote = await db.feature_request_votes.find_one({
        "userId": user["id"],
        "requestId": request_id
    })
    
    feature_request["hasVoted"] = vote is not None
    feature_request["isOwner"] = feature_request.get("userId") == user["id"]
    
    return feature_request
