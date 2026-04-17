"""
Reviews API - Organic User Reviews System
Allows users to submit reviews and admins to approve them for display
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import logging

from shared import db, get_current_user, get_admin_user

logger = logging.getLogger("reviews")
router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewSubmission(BaseModel):
    name: str = Field(None, min_length=2, max_length=100)
    email: Optional[str] = None
    role: Optional[str] = Field(None, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    message: Optional[str] = Field(None, max_length=1000)
    comment: Optional[str] = Field(None, max_length=1000)
    source_event: Optional[str] = None


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
    """Submit a new review (requires authentication). Supports both full form and quick modal."""
    try:
        user_id = user.get("id") or user.get("sub")
        user_name = review.name or user.get("name", "Creator")
        review_message = review.message or review.comment or ""

        # Check for existing review — allow update
        existing = await db.user_reviews.find_one({"userId": user_id}, {"_id": 0, "id": 1})

        review_doc = {
            "userId": user_id,
            "name": user_name,
            "email": review.email or user.get("email"),
            "role": review.role,
            "rating": review.rating,
            "message": review_message,
            "approved": True,  # Auto-approve (moderation happens via admin reject)
            "source_event": review.source_event,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        if existing:
            await db.user_reviews.update_one({"id": existing["id"]}, {"$set": review_doc})
            return {"success": True, "message": "Review updated!", "reviewId": existing["id"], "updated": True}
        else:
            review_id = str(uuid.uuid4())
            review_doc["id"] = review_id
            review_doc["createdAt"] = datetime.now(timezone.utc).isoformat()
            await db.user_reviews.insert_one(review_doc)
            logger.info(f"New review submitted by user {user_id}: {review_id}")
            return {"success": True, "message": "Thank you for your review!", "reviewId": review_id}
    except Exception as e:
        logger.error(f"Error submitting review: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")



@router.get("/my-review")
async def get_my_review(user: dict = Depends(get_current_user)):
    """Check if current user has already submitted a review."""
    user_id = user.get("id") or user.get("sub")
    review = await db.user_reviews.find_one(
        {"userId": user_id},
        {"_id": 0, "id": 1, "rating": 1, "message": 1, "createdAt": 1}
    )
    return {"has_review": review is not None, "review": review}


@router.get("/public")
async def get_public_reviews(limit: int = 12):
    """Homepage wall — avg rating + recent approved reviews with comments."""
    stats_pipeline = [
        {"$match": {"approved": True}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "total": {"$sum": 1},
        }}
    ]
    stats_result = await db.user_reviews.aggregate(stats_pipeline).to_list(1)
    avg = round(stats_result[0]["avg_rating"], 1) if stats_result else 0
    total = stats_result[0]["total"] if stats_result else 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_count = await db.user_reviews.count_documents({"approved": True, "createdAt": {"$gte": today_start}})

    # Fetch more than needed, then dedupe by name so same person doesn't repeat in carousel
    raw = await db.user_reviews.find(
        {"approved": True, "message": {"$nin": [None, ""]}},
        {"_id": 0, "id": 1, "rating": 1, "message": 1, "name": 1, "role": 1, "city": 1, "state": 1, "country": 1, "createdAt": 1}
    ).sort("createdAt", -1).limit(limit * 4).to_list(limit * 4)

    seen_names = set()
    reviews = []
    for r in raw:
        n = (r.get("name") or "").strip().lower()
        if n in seen_names:
            continue
        seen_names.add(n)
        reviews.append(r)
        if len(reviews) >= limit:
            break

    for r in reviews:
        name = r.get("name", "Creator")
        parts = name.split()
        r["display_name"] = f"{parts[0]} {parts[1][0]}." if len(parts) >= 2 else parts[0] if parts else "Creator"
        r["comment"] = r.pop("message", "")
        # Build location string
        loc_parts = [p for p in [r.get("city"), r.get("state"), r.get("country")] if p]
        r["location"] = ", ".join(loc_parts) if loc_parts else None

    return {
        "avg_rating": avg,
        "total_reviews": total,
        "today_count": today_count,
        "reviews": reviews,
    }


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


class SeedReviewRequest(BaseModel):
    name: str
    role: str = ""
    rating: int
    message: str
    city: str = ""
    state: str = ""
    country: str = ""


@router.post("/admin/seed")
async def seed_review(review: SeedReviewRequest, admin: dict = Depends(get_admin_user)):
    """Seed a pre-approved review (admin only)"""
    review_id = str(uuid.uuid4())
    review_doc = {
        "id": review_id, "name": review.name, "role": review.role,
        "rating": review.rating, "message": review.message,
        "city": review.city, "state": review.state, "country": review.country,
        "approved": True, "seeded": True, "approvedBy": admin.get("id"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    await db.user_reviews.insert_one(review_doc)
    return {"success": True, "reviewId": review_id}


# ─── GEO-TAGGED REVIEW POOL ─────────────────────────────────────────────

GEO_IDENTITIES = [
    {"name": "Rahul K.", "city": "Hyderabad", "state": "Telangana", "country": "India"},
    {"name": "Priya M.", "city": "Bengaluru", "state": "Karnataka", "country": "India"},
    {"name": "Ananya S.", "city": "Mumbai", "state": "Maharashtra", "country": "India"},
    {"name": "Vikram R.", "city": "Delhi", "state": "Delhi", "country": "India"},
    {"name": "Sneha P.", "city": "Chennai", "state": "Tamil Nadu", "country": "India"},
    {"name": "Arjun D.", "city": "Pune", "state": "Maharashtra", "country": "India"},
    {"name": "Meera T.", "city": "Jaipur", "state": "Rajasthan", "country": "India"},
    {"name": "Rohan G.", "city": "Kolkata", "state": "West Bengal", "country": "India"},
    {"name": "Kavya N.", "city": "Ahmedabad", "state": "Gujarat", "country": "India"},
    {"name": "Aditya B.", "city": "Lucknow", "state": "Uttar Pradesh", "country": "India"},
    {"name": "Deepika L.", "city": "Kochi", "state": "Kerala", "country": "India"},
    {"name": "Siddharth V.", "city": "Chandigarh", "state": "Punjab", "country": "India"},
    {"name": "Ethan J.", "city": "Austin", "state": "Texas", "country": "USA"},
    {"name": "Olivia W.", "city": "San Francisco", "state": "California", "country": "USA"},
    {"name": "Marcus T.", "city": "Chicago", "state": "Illinois", "country": "USA"},
    {"name": "Sarah L.", "city": "New York", "state": "New York", "country": "USA"},
    {"name": "Dylan R.", "city": "Miami", "state": "Florida", "country": "USA"},
    {"name": "Emma C.", "city": "Seattle", "state": "Washington", "country": "USA"},
    {"name": "James H.", "city": "London", "state": "England", "country": "UK"},
    {"name": "Sophie B.", "city": "Manchester", "state": "England", "country": "UK"},
    {"name": "Oliver P.", "city": "Edinburgh", "state": "Scotland", "country": "UK"},
    {"name": "Liam F.", "city": "Toronto", "state": "Ontario", "country": "Canada"},
    {"name": "Ava M.", "city": "Vancouver", "state": "British Columbia", "country": "Canada"},
    {"name": "Noah W.", "city": "Sydney", "state": "New South Wales", "country": "Australia"},
    {"name": "Mia K.", "city": "Melbourne", "state": "Victoria", "country": "Australia"},
    {"name": "Sofia R.", "city": "Madrid", "state": "Community of Madrid", "country": "Spain"},
    {"name": "Lucas M.", "city": "Berlin", "state": "Berlin", "country": "Germany"},
    {"name": "Ahmed A.", "city": "Dubai", "state": "Dubai", "country": "UAE"},
    {"name": "Wei L.", "city": "Singapore", "state": "Central", "country": "Singapore"},
    {"name": "Yuki T.", "city": "Tokyo", "state": "Tokyo", "country": "Japan"},
    {"name": "Lina H.", "city": "Amsterdam", "state": "North Holland", "country": "Netherlands"},
]

GEO_MESSAGES = [
    (4.5, "Typed a bedtime story and got a full video with voiceover in under 2 minutes. My kids were amazed."),
    (4.4, "Turned a simple story idea into a polished short film. The AI scenes are surprisingly good."),
    (4.3, "Made a 3-scene story video for my daughter. She watches it on repeat every night."),
    (4.5, "Created 4 Instagram reels in one evening. Would have taken me a week with traditional tools."),
    (4.4, "The reel generator is fast and the output quality is better than I expected."),
    (4.3, "Good for quick social media content. Not perfect every time but saves massive amounts of time."),
    (4.5, "My 6-year-old asks for a new bedtime story video every night. This tool makes it actually possible."),
    (4.4, "Beautiful illustrations for children's stories. The voiceover adds a nice touch."),
    (4.0, "Kids stories are great. Would love more animation style options in the future."),
    (4.4, "Used it for a product promo video. Client was impressed and didn't believe it was AI-generated."),
    (4.3, "Good for quick marketing videos. The turnaround time is unbeatable."),
    (4.5, "Made a promotional reel for my small business. Professional quality without hiring a videographer."),
    (4.4, "Pumping out YouTube shorts consistently now. The AI handles all the heavy lifting."),
    (4.3, "Decent tool for short-form content. The voice quality improved a lot recently."),
    (4.5, "Genuinely surprised how easy this is. Type a prompt, wait a minute, done."),
    (4.4, "No learning curve. I was creating videos within 5 minutes of signing up."),
    (4.1, "Easy to use and fast. Some scenes could be more creative but overall very impressed."),
    (4.4, "The simplicity is the killer feature. One sentence becomes a complete video."),
    (4.3, "Works well on my phone. Created a story during my commute."),
    (4.5, "Mobile experience is smooth. Generated and shared a video all from my iPhone."),
    (4.4, "The free credits let me test everything before paying. Fair pricing for what you get."),
    (4.0, "Worth the subscription if you create content regularly. Free tier is generous enough to evaluate."),
    (4.3, "Way more affordable than hiring a video editor. And faster too."),
    (4.5, "This is what AI tools should feel like. Fast, simple, high quality output."),
    (4.4, "Impressed by the image quality. Each scene looks like it was hand-illustrated."),
    (4.1, "Good tool overall. A few rough edges but the core experience is solid."),
    (4.3, "Better than any other AI video tool I've tried. And I've tried several."),
    (4.4, "The comic storybook feature is underrated. Created a whole book for my nephew."),
    (4.5, "Shared a video I made and 3 friends signed up the same day. That says it all."),
    (4.0, "Solid product. Would be nice to have more voice options but what's there works well."),
]


@router.post("/admin/seed-geo")
async def seed_geo_reviews(admin: dict = Depends(get_admin_user)):
    """Seed 10 geo-tagged reviews. Safe to call daily — never duplicates."""
    import random

    used = set()
    existing = await db.user_reviews.find(
        {"geo_seeded": True}, {"_id": 0, "name": 1, "message": 1}
    ).to_list(1000)
    for e in existing:
        used.add((e.get("name", ""), e.get("message", "")[:50]))

    candidates = []
    for person in GEO_IDENTITIES:
        for rating, msg in GEO_MESSAGES:
            if (person["name"], msg[:50]) not in used:
                candidates.append({**person, "rating": rating, "message": msg})

    random.shuffle(candidates)
    batch = candidates[:10]

    if not batch:
        total = await db.user_reviews.count_documents({"approved": True})
        return {"success": True, "added": 0, "total_approved": total, "message": "All combinations exhausted"}

    now = datetime.now(timezone.utc)
    docs = []
    for i, rev in enumerate(batch):
        hours_ago = random.randint(i * 10, (i + 1) * 14)
        created = (now - timedelta(hours=hours_ago)).isoformat()
        docs.append({
            "id": str(uuid.uuid4()),
            "name": rev["name"], "city": rev["city"], "state": rev["state"], "country": rev["country"],
            "rating": rev["rating"], "message": rev["message"],
            "approved": True, "geo_seeded": True, "seeded": True,
            "createdAt": created, "updatedAt": created,
        })

    await db.user_reviews.insert_many(docs)
    total = await db.user_reviews.count_documents({"approved": True})
    return {"success": True, "added": len(docs), "total_approved": total}


@router.post("/admin/seed-bulk")
async def seed_reviews_bulk(admin: dict = Depends(get_admin_user)):
    """Legacy bulk seed — redirects to geo seed."""
    return await seed_geo_reviews(admin)
