"""
Protected Download Routes
Secure file access with signed URLs and watermarking
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
import io

from shared import db, get_current_user
from services.content_protection import (
    generate_signed_token,
    validate_signed_token,
    watermark_image_bytes,
    check_watermark_removal_eligibility,
    purchase_watermark_removal,
    WATERMARK_REMOVAL_COST
)
from services.audit_log import log_admin_action, AuditAction

router = APIRouter(prefix="/protected-download", tags=["Protected Downloads"])

class SignedUrlRequest(BaseModel):
    file_id: str
    file_type: str = "image"  # image, pdf, video

class WatermarkRemovalRequest(BaseModel):
    file_id: str

@router.post("/get-signed-url")
async def get_signed_url(
    request: SignedUrlRequest,
    user: dict = Depends(get_current_user)
):
    """Generate a signed URL for secure file download"""
    user_id = str(user.get("id") or user.get("_id"))
    
    # Verify user owns this file
    file_record = await db.user_files.find_one({
        "_id": ObjectId(request.file_id),
        "user_id": user_id
    })
    
    if not file_record:
        # Check generated content
        file_record = await db.generated_content.find_one({
            "_id": ObjectId(request.file_id),
            "user_id": user_id
        })
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    
    # Generate signed token (60 second expiry)
    token = generate_signed_token(user_id, request.file_id, expiry_seconds=60)
    
    # Log access
    await db.file_access_logs.insert_one({
        "user_id": user_id,
        "file_id": request.file_id,
        "action": "signed_url_generated",
        "timestamp": datetime.now(timezone.utc)
    })
    
    return {
        "signed_url": f"/api/protected-download/file/{token}",
        "expires_in": 60,
        "file_type": request.file_type
    }

@router.get("/file/{token}")
async def download_file(token: str):
    """Download file with signed token validation"""
    # Validate token
    token_data = validate_signed_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired download link")
    
    user_id = token_data["user_id"]
    file_id = token_data["file_id"]
    
    # Get file record
    file_record = await db.user_files.find_one({"_id": ObjectId(file_id)})
    if not file_record:
        file_record = await db.generated_content.find_one({"_id": ObjectId(file_id)})
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get user email for watermark
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    user_email = user.get("email", "user@visionary-suite.com") if user else "user@visionary-suite.com"
    
    # Check if watermark removal purchased
    removal = await db.watermark_removals.find_one({
        "user_id": user_id,
        "file_id": file_id
    })
    
    # Get file content
    file_content = file_record.get("content") or file_record.get("data")
    if isinstance(file_content, str):
        # If it's a base64 string or URL, we need to handle differently
        import base64
        try:
            file_content = base64.b64decode(file_content)
        except:
            file_content = file_content.encode()
    
    # Apply watermark if not removed
    if not removal and file_record.get("type", "").startswith("image"):
        file_content = watermark_image_bytes(
            file_content,
            user_email,
            include_subtle=True
        )
    
    # Log download
    await db.file_access_logs.insert_one({
        "user_id": user_id,
        "file_id": file_id,
        "action": "downloaded",
        "watermarked": not bool(removal),
        "timestamp": datetime.now(timezone.utc)
    })
    
    # Determine content type
    content_type = file_record.get("content_type", "application/octet-stream")
    filename = file_record.get("filename", f"download_{file_id}")
    
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/watermark-status/{file_id}")
async def check_watermark_status(
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Check watermark removal eligibility"""
    user_id = str(user.get("id") or user.get("_id"))
    status = await check_watermark_removal_eligibility(db, user_id, file_id)
    return status

@router.post("/remove-watermark")
async def remove_watermark(
    request: WatermarkRemovalRequest,
    user: dict = Depends(get_current_user)
):
    """Purchase watermark removal for a file"""
    user_id = str(user.get("id") or user.get("_id"))
    
    # Verify file exists and user owns it
    file_record = await db.user_files.find_one({
        "_id": ObjectId(request.file_id),
        "user_id": user_id
    })
    
    if not file_record:
        file_record = await db.generated_content.find_one({
            "_id": ObjectId(request.file_id),
            "user_id": user_id
        })
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found or access denied")
    
    result = await purchase_watermark_removal(db, user_id, request.file_id)
    
    if not result["success"]:
        raise HTTPException(status_code=402, detail=result["error"])
    
    return {
        "success": True,
        "message": "Watermark removal purchased. Your next download will be watermark-free.",
        "credits_used": result["credits_used"]
    }

@router.get("/config")
async def get_download_config():
    """Get download protection configuration"""
    return {
        "watermark_removal_cost": WATERMARK_REMOVAL_COST,
        "signed_url_expiry_seconds": 60,
        "watermark_enabled": True,
        "protection_features": [
            "Signed URLs with 60s expiry",
            "Ownership validation",
            "Dynamic watermarking",
            "Access logging"
        ]
    }
