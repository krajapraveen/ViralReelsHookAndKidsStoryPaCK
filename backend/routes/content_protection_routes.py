"""
Content Protection Routes
API endpoints for PDF flattening and video streaming protection
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import base64
import os
from pathlib import Path

from shared import logger, db, get_current_user
from services.content_protection_service import (
    get_pdf_protection_service,
    get_video_streaming_service
)

router = APIRouter(prefix="/content-protection", tags=["Content Protection"])


# Request/Response Models
class PDFProtectRequest(BaseModel):
    pdf_base64: str
    flatten: bool = True
    encrypt: bool = True
    add_watermark: bool = True


class VideoStreamRequest(BaseModel):
    video_id: str


class StreamTokenValidation(BaseModel):
    token: str
    video_id: str


# PDF Protection Endpoints
@router.post("/pdf/protect")
async def protect_pdf(
    request: PDFProtectRequest,
    user: dict = Depends(get_current_user)
):
    """
    Protect a PDF by flattening and encrypting it.
    - Flattening converts editable elements to static content
    - Encryption prevents copying/editing
    - Optional watermark with user email
    """
    try:
        # Decode PDF
        pdf_bytes = base64.b64decode(request.pdf_base64)
        
        # Get service
        service = get_pdf_protection_service()
        
        if not service.available:
            raise HTTPException(
                status_code=503,
                detail="PDF protection service not available. Install pypdf and reportlab."
            )
        
        # Protect PDF
        result = service.protect_pdf(
            pdf_bytes=pdf_bytes,
            user_email=user.get('email', 'user'),
            flatten=request.flatten,
            encrypt=request.encrypt,
            add_watermark=request.add_watermark
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Protection failed'))
        
        # Return protected PDF as base64
        protected_base64 = base64.b64encode(result['pdf_bytes']).decode('utf-8')
        
        return {
            'success': True,
            'protected_pdf_base64': protected_base64,
            'flattened': result['flattened'],
            'encrypted': result['encrypted'],
            'watermark_applied': result['watermark_applied'],
            'message': 'PDF protected successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF protection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf/status")
async def get_pdf_service_status():
    """Check if PDF protection service is available"""
    service = get_pdf_protection_service()
    return {
        'available': service.available,
        'features': {
            'flatten': service.available,
            'encrypt': service.available,
            'watermark': service.available
        }
    }


# Video Streaming Endpoints
@router.post("/video/stream-url")
async def get_video_stream_url(
    request: VideoStreamRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a protected stream URL for a video.
    Returns a time-limited token for accessing the stream.
    """
    try:
        service = get_video_streaming_service()
        
        # Get base URL from environment
        base_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        
        result = service.get_stream_url(
            video_id=request.video_id,
            user_id=user.get('id'),
            user_email=user.get('email', 'user'),
            base_url=base_url
        )
        
        return {
            'success': True,
            **result
        }
        
    except Exception as e:
        logger.error(f"Stream URL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/validate-token")
async def validate_stream_token(request: StreamTokenValidation):
    """Validate a video stream token"""
    service = get_video_streaming_service()
    result = service.validate_stream_token(request.token, request.video_id)
    
    if not result['valid']:
        raise HTTPException(status_code=401, detail=result.get('error', 'Invalid token'))
    
    return {
        'valid': True,
        'user_id': result['user_id'],
        'expires_at': result['expires_at']
    }


@router.get("/video/status")
async def get_video_service_status():
    """Check if video streaming service is available"""
    service = get_video_streaming_service()
    return {
        'available': service.available,
        'features': {
            'hls_streaming': service.available,
            'watermarking': service.available,
            'token_auth': True  # Always available
        }
    }


# Stream delivery endpoint (for HLS segments)
@router.get("/stream/{video_id}/playlist.m3u8")
async def get_hls_playlist(
    video_id: str,
    token: str = Query(..., description="Stream authentication token")
):
    """
    Get HLS playlist for video streaming.
    Requires valid stream token.
    """
    service = get_video_streaming_service()
    
    # Validate token
    validation = service.validate_stream_token(token, video_id)
    if not validation['valid']:
        raise HTTPException(status_code=401, detail=validation.get('error', 'Invalid token'))
    
    # Get playlist path
    playlist_path = service.storage_path / video_id / "playlist.m3u8"
    
    if not playlist_path.exists():
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return FileResponse(
        playlist_path,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/stream/{video_id}/{segment}")
async def get_hls_segment(
    video_id: str,
    segment: str,
    token: str = Query(..., description="Stream authentication token")
):
    """
    Get HLS segment for video streaming.
    Requires valid stream token.
    """
    service = get_video_streaming_service()
    
    # Validate token
    validation = service.validate_stream_token(token, video_id)
    if not validation['valid']:
        raise HTTPException(status_code=401, detail=validation.get('error', 'Invalid token'))
    
    # Get segment path
    segment_path = service.storage_path / video_id / segment
    
    if not segment_path.exists():
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return FileResponse(
        segment_path,
        media_type="video/mp2t",
        headers={
            "Cache-Control": "no-cache"
        }
    )


# Cleanup endpoint (admin only)
@router.post("/cleanup")
async def cleanup_expired_tokens(user: dict = Depends(get_current_user)):
    """Clean up expired stream tokens (admin only)"""
    if user.get('role') != 'ADMIN':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = get_video_streaming_service()
    cleaned = service.cleanup_expired_tokens()
    
    return {
        'success': True,
        'tokens_cleaned': cleaned
    }
