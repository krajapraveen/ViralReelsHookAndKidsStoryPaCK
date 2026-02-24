"""
Content Vault - Viral hooks, captions, hashtags library
CreatorStudio AI
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import Optional
import uuid
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user
from security import limiter

router = APIRouter(prefix="/content", tags=["Content Vault"])

# Sample content vault data
SAMPLE_HOOKS = [
    {"id": "1", "text": "Wait for it...", "niche": "general", "likes": 15000},
    {"id": "2", "text": "Nobody talks about this but...", "niche": "business", "likes": 22000},
    {"id": "3", "text": "POV: You finally discovered...", "niche": "lifestyle", "likes": 18500},
    {"id": "4", "text": "This changed everything for me", "niche": "motivation", "likes": 25000},
    {"id": "5", "text": "I can't believe this actually works", "niche": "tech", "likes": 12000},
    {"id": "6", "text": "Stop scrolling if you want to learn...", "niche": "education", "likes": 30000},
    {"id": "7", "text": "The secret nobody tells you about...", "niche": "business", "likes": 28000},
    {"id": "8", "text": "Day 1 of trying...", "niche": "lifestyle", "likes": 16000},
    {"id": "9", "text": "Watch until the end!", "niche": "general", "likes": 35000},
    {"id": "10", "text": "Here's why you're doing it wrong", "niche": "education", "likes": 21000},
]

SAMPLE_CAPTIONS = [
    {"id": "1", "text": "Double tap if you agree!", "niche": "general", "engagement": "high"},
    {"id": "2", "text": "Save this for later!", "niche": "education", "engagement": "high"},
    {"id": "3", "text": "Tag someone who needs to see this", "niche": "motivation", "engagement": "high"},
    {"id": "4", "text": "Comment your thoughts below", "niche": "general", "engagement": "medium"},
    {"id": "5", "text": "Share this with your friends!", "niche": "lifestyle", "engagement": "high"},
]

SAMPLE_HASHTAGS = {
    "general": ["#fyp", "#viral", "#trending", "#foryou", "#explore"],
    "business": ["#entrepreneur", "#business", "#success", "#hustle", "#growth"],
    "lifestyle": ["#lifestyle", "#life", "#daily", "#aesthetic", "#vibes"],
    "tech": ["#tech", "#technology", "#gadgets", "#innovation", "#ai"],
    "education": ["#learn", "#tips", "#howto", "#tutorial", "#knowledge"],
}


@router.get("/vault")
@limiter.limit("60/minute")
async def get_content_vault(
    request: Request,
    niche: Optional[str] = Query(None, description="Filter by niche"),
    user: dict = Depends(get_current_user)
):
    """Get content vault with viral hooks, captions, and hashtags"""
    try:
        # Filter by niche if provided
        hooks = SAMPLE_HOOKS
        if niche and niche != 'all':
            hooks = [h for h in SAMPLE_HOOKS if h.get('niche') == niche]
        
        captions = SAMPLE_CAPTIONS
        if niche and niche != 'all':
            captions = [c for c in SAMPLE_CAPTIONS if c.get('niche') == niche]
        
        hashtags = SAMPLE_HASHTAGS.get(niche, SAMPLE_HASHTAGS['general']) if niche and niche != 'all' else []
        for n, tags in SAMPLE_HASHTAGS.items():
            hashtags = list(set(hashtags + tags))
        
        return {
            "success": True,
            "plan": "premium",
            "hooks": hooks,
            "captions": captions,
            "hashtags": hashtags[:20],
            "total_hooks": len(SAMPLE_HOOKS),
            "total_captions": len(SAMPLE_CAPTIONS),
            "access_level": {
                "hooks": len(hooks),
                "captions": len(captions),
                "hashtags": len(hashtags[:20])
            }
        }
        
    except Exception as e:
        logger.error(f"Content vault error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load content vault")


@router.get("/hooks")
@limiter.limit("60/minute")
async def get_viral_hooks(
    request: Request,
    niche: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user)
):
    """Get viral hooks"""
    hooks = SAMPLE_HOOKS
    if niche and niche != 'all':
        hooks = [h for h in SAMPLE_HOOKS if h.get('niche') == niche]
    
    return {"hooks": hooks[:limit], "total": len(SAMPLE_HOOKS)}


@router.get("/captions")
@limiter.limit("60/minute")
async def get_captions(
    request: Request,
    niche: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get viral captions"""
    captions = SAMPLE_CAPTIONS
    if niche and niche != 'all':
        captions = [c for c in SAMPLE_CAPTIONS if c.get('niche') == niche]
    
    return {"captions": captions, "total": len(SAMPLE_CAPTIONS)}


@router.get("/hashtags/{niche}")
@limiter.limit("60/minute")
async def get_hashtags(
    request: Request,
    niche: str,
    user: dict = Depends(get_current_user)
):
    """Get hashtags by niche"""
    hashtags = SAMPLE_HASHTAGS.get(niche, SAMPLE_HASHTAGS['general'])
    return {"hashtags": hashtags, "niche": niche}
