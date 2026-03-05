"""
Blog API - Content pages for SEO and user engagement
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging
import re

from shared import db, get_admin_user

logger = logging.getLogger("blog")
router = APIRouter(prefix="/blog", tags=["blog"])


class BlogPost(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    slug: Optional[str] = None
    excerpt: str = Field(..., min_length=10, max_length=500)
    content: str = Field(..., min_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    tags: List[str] = []
    featuredImage: Optional[str] = None
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    published: bool = False


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    featuredImage: Optional[str] = None
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    published: Optional[bool] = None


def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


@router.get("/posts")
async def get_blog_posts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 10,
    skip: int = 0
):
    """Get published blog posts"""
    try:
        query = {"published": True}
        
        if category:
            query["category"] = category
        if tag:
            query["tags"] = tag
        
        posts = await db.blog_posts.find(
            query,
            {"_id": 0, "content": 0}  # Exclude full content for listing
        ).sort("publishedAt", -1).skip(skip).limit(limit).to_list(limit)
        
        total = await db.blog_posts.count_documents(query)
        
        return {
            "success": True,
            "posts": posts,
            "total": total,
            "hasMore": skip + limit < total
        }
    except Exception as e:
        logger.error(f"Error fetching blog posts: {e}")
        return {"success": True, "posts": [], "total": 0, "hasMore": False}


@router.get("/posts/{slug}")
async def get_blog_post(slug: str):
    """Get a single blog post by slug"""
    try:
        post = await db.blog_posts.find_one(
            {"slug": slug, "published": True},
            {"_id": 0}
        )
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Increment view count
        await db.blog_posts.update_one(
            {"slug": slug},
            {"$inc": {"views": 1}}
        )
        
        return {"success": True, "post": post}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching blog post: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch post")


@router.get("/categories")
async def get_categories():
    """Get all blog categories with post counts"""
    try:
        pipeline = [
            {"$match": {"published": True}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        categories = await db.blog_posts.aggregate(pipeline).to_list(50)
        
        return {
            "success": True,
            "categories": [{"name": c["_id"], "count": c["count"]} for c in categories]
        }
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return {"success": True, "categories": []}


@router.get("/tags")
async def get_tags():
    """Get all blog tags with counts"""
    try:
        pipeline = [
            {"$match": {"published": True}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 30}
        ]
        
        tags = await db.blog_posts.aggregate(pipeline).to_list(30)
        
        return {
            "success": True,
            "tags": [{"name": t["_id"], "count": t["count"]} for t in tags]
        }
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        return {"success": True, "tags": []}


# Admin endpoints

@router.get("/admin/posts")
async def get_all_posts_admin(admin: dict = Depends(get_admin_user)):
    """Get all blog posts for admin management"""
    try:
        posts = await db.blog_posts.find(
            {},
            {"_id": 0}
        ).sort("createdAt", -1).to_list(500)
        
        return {"success": True, "posts": posts}
    except Exception as e:
        logger.error(f"Error fetching all posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch posts")


@router.post("/admin/posts")
async def create_blog_post(post: BlogPost, admin: dict = Depends(get_admin_user)):
    """Create a new blog post"""
    try:
        post_id = str(uuid.uuid4())
        slug = post.slug or generate_slug(post.title)
        
        # Check for duplicate slug
        existing = await db.blog_posts.find_one({"slug": slug})
        if existing:
            slug = f"{slug}-{post_id[:8]}"
        
        post_doc = {
            "id": post_id,
            "title": post.title,
            "slug": slug,
            "excerpt": post.excerpt,
            "content": post.content,
            "category": post.category,
            "tags": post.tags,
            "featuredImage": post.featuredImage,
            "metaTitle": post.metaTitle or post.title,
            "metaDescription": post.metaDescription or post.excerpt,
            "published": post.published,
            "publishedAt": datetime.now(timezone.utc).isoformat() if post.published else None,
            "author": admin.get("name", "Admin"),
            "authorId": admin.get("id"),
            "views": 0,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.blog_posts.insert_one(post_doc)
        
        logger.info(f"Blog post created: {post_id} by admin {admin.get('id')}")
        
        return {
            "success": True,
            "message": "Blog post created successfully",
            "postId": post_id,
            "slug": slug
        }
    except Exception as e:
        logger.error(f"Error creating blog post: {e}")
        raise HTTPException(status_code=500, detail="Failed to create post")


@router.put("/admin/posts/{post_id}")
async def update_blog_post(post_id: str, update: BlogUpdate, admin: dict = Depends(get_admin_user)):
    """Update a blog post"""
    try:
        update_data = {k: v for k, v in update.dict().items() if v is not None}
        update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
        
        # If publishing for the first time, set publishedAt
        if update.published:
            existing = await db.blog_posts.find_one({"id": post_id})
            if existing and not existing.get("publishedAt"):
                update_data["publishedAt"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.blog_posts.update_one(
            {"id": post_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        
        logger.info(f"Blog post updated: {post_id} by admin {admin.get('id')}")
        
        return {"success": True, "message": "Blog post updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating blog post: {e}")
        raise HTTPException(status_code=500, detail="Failed to update post")


@router.delete("/admin/posts/{post_id}")
async def delete_blog_post(post_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a blog post"""
    try:
        result = await db.blog_posts.delete_one({"id": post_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        
        logger.info(f"Blog post deleted: {post_id} by admin {admin.get('id')}")
        
        return {"success": True, "message": "Blog post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting blog post: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete post")


# Seed initial blog posts for SEO
SEED_POSTS = [
    {
        "title": "How to Create Viral Instagram Reels in 2026",
        "slug": "how-to-create-viral-instagram-reels-2026",
        "excerpt": "Learn the secrets behind viral Instagram Reels and how AI can help you create engaging content in seconds.",
        "content": """
# How to Create Viral Instagram Reels in 2026

Creating viral content isn't about luck—it's about understanding what works and having the right tools to execute quickly.

## The Anatomy of a Viral Reel

Every viral reel has these key components:
1. **A Hook that Stops the Scroll** - You have 0.5 seconds to capture attention
2. **Engaging Middle Content** - Keep viewers watching with valuable or entertaining content
3. **A Strong Call-to-Action** - Tell viewers what to do next

## How AI is Changing Content Creation

AI tools like CreatorStudio AI can generate:
- 5 different hook variations for your topic
- Complete scripts optimized for engagement
- Trending hashtags for maximum reach
- Captions that drive comments and shares

## Tips for Going Viral

1. **Post at the right time** - When your audience is most active
2. **Use trending audio** - The algorithm favors content with popular sounds
3. **Keep it short** - 7-15 seconds performs best for reels
4. **Add value** - Teach something, make people laugh, or inspire

## Start Creating Today

With 100 free credits, you can create dozens of reels and test what works for your audience. No credit card required!
        """,
        "category": "Instagram Tips",
        "tags": ["instagram", "reels", "viral content", "social media", "ai tools"],
        "metaTitle": "How to Create Viral Instagram Reels in 2026 | CreatorStudio AI",
        "metaDescription": "Learn the secrets behind viral Instagram Reels. Discover how AI can help you create engaging hooks, scripts, and captions in seconds.",
        "published": True
    },
    {
        "title": "The Ultimate Guide to Kids Story Videos for YouTube",
        "slug": "ultimate-guide-kids-story-videos-youtube",
        "excerpt": "Everything you need to know about creating engaging kids story videos that parents love and YouTube recommends.",
        "content": """
# The Ultimate Guide to Kids Story Videos for YouTube

Kids content is one of the most lucrative niches on YouTube, but creating quality content consistently is challenging. Here's how to succeed.

## Why Kids Content Works

- Parents are always looking for safe, educational content
- Kids watch videos repeatedly, boosting your watch time
- The niche has less competition than adult content
- Advertising rates are often higher for family-friendly content

## Essential Elements of Great Kids Stories

### 1. Age-Appropriate Themes
- Friendship and kindness
- Problem-solving adventures
- Learning through play
- Moral lessons wrapped in fun

### 2. Visual Appeal
- Bright, colorful imagery
- Simple, expressive characters
- Smooth animations or illustrations

### 3. Audio Quality
- Clear, engaging narration
- Pleasant background music
- Sound effects that enhance the story

## Creating Story Packs with AI

Our Kids Story Pack generator creates complete production packages including:
- Full story script with dialogue
- Scene-by-scene visual descriptions
- Character descriptions and expressions
- Music and sound effect suggestions
- AI-generated voiceover

## Monetization Strategies

1. YouTube AdSense (once eligible)
2. Sponsored content with child-safe brands
3. Merchandise (coloring books, activity sheets)
4. Premium content platforms

## Get Started Free

Try creating your first Kids Story Pack with 100 free credits. Generate complete video scripts with voiceover in under 90 seconds!
        """,
        "category": "YouTube Tips",
        "tags": ["youtube", "kids content", "story videos", "content creation", "monetization"],
        "metaTitle": "Ultimate Guide to Kids Story Videos for YouTube | CreatorStudio AI",
        "metaDescription": "Learn how to create engaging kids story videos for YouTube. Discover AI tools that generate complete story packs with scripts and visuals.",
        "published": True
    },
    {
        "title": "30-Day Content Calendar: Never Run Out of Ideas Again",
        "slug": "30-day-content-calendar-guide",
        "excerpt": "How to plan a month's worth of content in minutes using AI-powered content calendars.",
        "content": """
# 30-Day Content Calendar: Never Run Out of Ideas Again

Consistency is the key to social media success, but coming up with fresh ideas every day is exhausting. Here's the solution.

## The Content Calendar Advantage

Having a pre-planned content calendar helps you:
- Stay consistent with posting
- Maintain content quality
- Reduce daily stress and decision fatigue
- Align content with trends and events
- Track what performs best

## How to Build Your Calendar

### Step 1: Define Your Pillars
Choose 3-5 content themes that represent your brand:
- Educational tips
- Behind-the-scenes
- Product showcases
- User testimonials
- Trending topics

### Step 2: Map Your Month
- Weekly themes for cohesion
- Daily posting times based on analytics
- Space for reactive/trending content
- Balance of content types

### Step 3: Generate with AI
Our AI content calendar generator creates:
- 30 unique content ideas
- Hooks and captions for each day
- Hashtag suggestions
- Best posting times
- Content mix recommendations

## Sample Weekly Structure

**Monday**: Motivational/Educational
**Tuesday**: Tips & Tricks
**Wednesday**: Behind-the-Scenes
**Thursday**: Trending Topics
**Friday**: Fun/Entertainment
**Saturday**: Community Engagement
**Sunday**: Recap/Preview

## Tools to Stay Organized

1. AI Content Calendar (get 30 days planned in seconds)
2. Scheduling tools for automated posting
3. Analytics dashboards for performance tracking
4. Content libraries for evergreen posts

## Start Planning Today

Generate your first 30-day content calendar with our AI tool. Just enter your niche and let AI do the planning!
        """,
        "category": "Content Strategy",
        "tags": ["content calendar", "planning", "social media strategy", "productivity", "ai tools"],
        "metaTitle": "30-Day Content Calendar Guide | CreatorStudio AI",
        "metaDescription": "Learn how to plan a month's worth of content in minutes. AI-powered content calendars help you stay consistent and creative.",
        "published": True
    }
]


@router.post("/admin/seed")
async def seed_blog_posts(admin: dict = Depends(get_admin_user)):
    """Seed initial blog posts for SEO"""
    try:
        seeded = 0
        for post_data in SEED_POSTS:
            existing = await db.blog_posts.find_one({"slug": post_data["slug"]})
            if not existing:
                post_id = str(uuid.uuid4())
                post_doc = {
                    "id": post_id,
                    **post_data,
                    "author": "CreatorStudio Team",
                    "authorId": admin.get("id"),
                    "views": 0,
                    "publishedAt": datetime.now(timezone.utc).isoformat(),
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }
                await db.blog_posts.insert_one(post_doc)
                seeded += 1
        
        return {
            "success": True,
            "message": f"Seeded {seeded} blog posts",
            "seeded": seeded
        }
    except Exception as e:
        logger.error(f"Error seeding blog posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to seed posts")
