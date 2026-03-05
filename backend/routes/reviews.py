"""
Reviews API - Organic User Reviews System
Allows users to submit reviews and admins to approve them for display
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger("reviews")
router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewSubmission(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    role: Optional[str] = Field(None, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=10, max_length=1000)


class ReviewApproval(BaseModel):
    approved: bool


@router.get("/approved")
async def get_approved_reviews(limit: int = 10, skip: int = 0):
    """Get all approved reviews for public display"""
    try:
        reviews = await db.user_reviews.find(
            {"approved": True},
            {"_id": 0}
        ).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
        
        # Get stats
        total_count = await db.user_reviews.count_documents({"approved": True})
        
        # Calculate average rating
        pipeline = [
            {"$match": {"approved": True}},
            {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}}}
        ]
        avg_result = await db.user_reviews.aggregate(pipeline).to_list(1)
        avg_rating = avg_result[0]["avgRating"] if avg_result else 0
        
        return {
            "success": True,
            "reviews": reviews,
            "totalCount": total_count,
            "avgRating": round(avg_rating, 1) if avg_rating else 0
        }
    except Exception as e:
        logger.error(f"Error fetching approved reviews: {e}")
        return {"success": True, "reviews": [], "totalCount": 0, "avgRating": 0}


@router.get("/")
async def get_all_reviews():
    """Get all reviews (returns approved reviews for public)"""
    try:
        reviews = await db.user_reviews.find(
            {"approved": True},
            {"_id": 0}
        ).sort("createdAt", -1).limit(20).to_list(20)
        
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        return []


@router.post("/submit")
async def submit_review(review: ReviewSubmission, user: dict = Depends(get_current_user)):
    """Submit a new review (requires authentication)"""
    try:
        review_id = str(uuid.uuid4())
        
        review_doc = {
            "id": review_id,
            "userId": user.get("id"),
            "name": review.name,
            "email": review.email or user.get("email"),
            "role": review.role,
            "rating": review.rating,
            "message": review.message,
            "approved": False,  # Requires admin approval
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.user_reviews.insert_one(review_doc)
        
        logger.info(f"New review submitted by user {user.get('id')}: {review_id}")
        
        return {
            "success": True,
            "message": "Thank you for your review! It will be visible after approval.",
            "reviewId": review_id
        }
    except Exception as e:
        logger.error(f"Error submitting review: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")


@router.get("/admin/pending")
async def get_pending_reviews(admin: dict = Depends(get_admin_user)):
    """Get all pending reviews for admin approval"""
    try:
        reviews = await db.user_reviews.find(
            {"approved": False},
            {"_id": 0}
        ).sort("createdAt", -1).to_list(100)
        
        return {"success": True, "reviews": reviews}
    except Exception as e:
        logger.error(f"Error fetching pending reviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending reviews")


@router.get("/admin/all")
async def get_all_reviews_admin(admin: dict = Depends(get_admin_user)):
    """Get all reviews for admin management"""
    try:
        reviews = await db.user_reviews.find(
            {},
            {"_id": 0}
        ).sort("createdAt", -1).to_list(500)
        
        return {"success": True, "reviews": reviews}
    except Exception as e:
        logger.error(f"Error fetching all reviews: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reviews")


@router.post("/admin/{review_id}/approve")
async def approve_review(review_id: str, approval: ReviewApproval, admin: dict = Depends(get_admin_user)):
    """Approve or reject a review"""
    try:
        result = await db.user_reviews.update_one(
            {"id": review_id},
            {
                "$set": {
                    "approved": approval.approved,
                    "approvedBy": admin.get("id"),
                    "approvedAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        action = "approved" if approval.approved else "rejected"
        logger.info(f"Review {review_id} {action} by admin {admin.get('id')}")
        
        return {
            "success": True,
            "message": f"Review {action} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving review: {e}")
        raise HTTPException(status_code=500, detail="Failed to update review")


@router.delete("/admin/{review_id}")
async def delete_review(review_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a review"""
    try:
        result = await db.user_reviews.delete_one({"id": review_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        logger.info(f"Review {review_id} deleted by admin {admin.get('id')}")
        
        return {"success": True, "message": "Review deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete review")
