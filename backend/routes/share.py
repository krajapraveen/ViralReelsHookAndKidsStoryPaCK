"""
Share Your Creation - Backend Routes
Shareable links with social media preview cards (Open Graph)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_current_user_optional

router = APIRouter(prefix="/share", tags=["Share"])


# =============================================================================
# MODELS
# =============================================================================

class CreateShareRequest(BaseModel):
    generationId: str
    type: str
    title: Optional[str] = None
    preview: Optional[str] = None
    thumbnailUrl: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_og_html(share_data: dict, base_url: str) -> str:
    """Generate HTML with Open Graph meta tags for social sharing"""
    title = share_data.get('title', 'AI Creation')
    description = share_data.get('preview', 'Created with CreatorStudio AI')[:160]
    type_name = share_data.get('type', 'creation')
    share_id = share_data.get('id', '')
    thumbnail = share_data.get('thumbnailUrl', f'{base_url}/og-default.png')
    
    type_emojis = {
        'REEL': '🎬',
        'STORY': '📖',
        'COMIC': '💥',
        'GIF': '✨',
        'COLORING_BOOK': '🎨',
        'STORYBOOK': '📚'
    }
    emoji = type_emojis.get(type_name, '✨')
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{emoji} {title} - CreatorStudio AI</title>
    
    <!-- Primary Meta Tags -->
    <meta name="title" content="{emoji} {title} - CreatorStudio AI">
    <meta name="description" content="{description}">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{base_url}/share/{share_id}">
    <meta property="og:title" content="{emoji} {title} - CreatorStudio AI">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{thumbnail}">
    <meta property="og:site_name" content="CreatorStudio AI">
    
    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{base_url}/share/{share_id}">
    <meta property="twitter:title" content="{emoji} {title} - CreatorStudio AI">
    <meta property="twitter:description" content="{description}">
    <meta property="twitter:image" content="{thumbnail}">
    
    <!-- WhatsApp / LinkedIn -->
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    
    <!-- Redirect to React app -->
    <meta http-equiv="refresh" content="0;url={base_url}/share/{share_id}">
    <script>window.location.href = "{base_url}/share/{share_id}";</script>
</head>
<body>
    <p>Redirecting to <a href="{base_url}/share/{share_id}">CreatorStudio AI</a>...</p>
</body>
</html>"""


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/create")
async def create_share_link(
    request: CreateShareRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a shareable link for a generation
    Links are valid for 30 days
    """
    share_id = str(uuid.uuid4())[:12]  # Short ID for nicer URLs
    
    share_doc = {
        "id": share_id,
        "generationId": request.generationId,
        "userId": user["id"],
        "type": request.type,
        "title": request.title,
        "preview": request.preview,
        "thumbnailUrl": request.thumbnailUrl,
        "views": 0,
        "shares": 0,
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.shares.insert_one(share_doc)
    
    # Get base URL from environment or use default
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "https://creatorstudio.ai")
    
    logger.info(f"Created share link {share_id} for generation {request.generationId}")
    
    return {
        "success": True,
        "shareId": share_id,
        "shareUrl": f"{base_url}/share/{share_id}",
        "expiresAt": share_doc["expiresAt"]
    }


@router.get("/{share_id}")
async def get_share_data(share_id: str, request: Request):
    """
    Get share data for displaying shared content
    Increments view count
    """
    share = await db.shares.find_one({"id": share_id}, {"_id": 0})
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    # Check expiration
    expires_at = datetime.fromisoformat(share["expiresAt"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=404, detail="Share link has expired")
    
    # Increment view count
    await db.shares.update_one(
        {"id": share_id},
        {"$inc": {"views": 1}}
    )
    
    return {
        "success": True,
        "id": share["id"],
        "type": share["type"],
        "title": share["title"],
        "preview": share["preview"],
        "thumbnailUrl": share.get("thumbnailUrl"),
        "views": share["views"] + 1,
        "createdAt": share["createdAt"]
    }


@router.get("/{share_id}/og", response_class=HTMLResponse)
async def get_share_og_page(share_id: str, request: Request):
    """
    Return HTML page with Open Graph meta tags for social media crawlers
    This endpoint is called when social platforms fetch preview data
    """
    share = await db.shares.find_one({"id": share_id}, {"_id": 0})
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    # Get base URL
    base_url = os.environ.get("REACT_APP_BACKEND_URL", str(request.base_url).rstrip('/'))
    
    # Increment share count (indicates social preview was loaded)
    await db.shares.update_one(
        {"id": share_id},
        {"$inc": {"shares": 1}}
    )
    
    return HTMLResponse(content=generate_og_html(share, base_url))


@router.get("/{share_id}/stats")
async def get_share_stats(
    share_id: str,
    user: dict = Depends(get_current_user)
):
    """Get statistics for a shared link (owner only)"""
    share = await db.shares.find_one(
        {"id": share_id, "userId": user["id"]},
        {"_id": 0}
    )
    
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    return {
        "success": True,
        "stats": {
            "views": share["views"],
            "shares": share["shares"],
            "createdAt": share["createdAt"],
            "expiresAt": share["expiresAt"]
        }
    }


@router.delete("/{share_id}")
async def delete_share_link(
    share_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a share link (owner only)"""
    result = await db.shares.delete_one({"id": share_id, "userId": user["id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    return {"success": True, "message": "Share link deleted"}


@router.get("/user/all")
async def get_user_shares(user: dict = Depends(get_current_user)):
    """Get all share links created by the user"""
    shares = await db.shares.find(
        {"userId": user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).limit(50).to_list(50)
    
    return {
        "success": True,
        "shares": shares
    }
