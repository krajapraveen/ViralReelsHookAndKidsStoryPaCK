"""
Watermark Service - Add branding watermarks to downloaded content
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging
import io
import os
from PIL import Image, ImageDraw, ImageFont

from shared import db, get_current_user

logger = logging.getLogger("watermark")
router = APIRouter(prefix="/watermark", tags=["watermark"])

# Watermark settings
WATERMARK_TEXT = "Made with visionary-suite.com"
WATERMARK_OPACITY = 128  # 0-255


class WatermarkSettings(BaseModel):
    text: Optional[str] = WATERMARK_TEXT
    position: str = "bottom-right"  # bottom-right, bottom-left, top-right, top-left, center
    opacity: int = 50  # 0-100
    fontSize: int = 24


def add_watermark_to_image(image_bytes: bytes, settings: WatermarkSettings) -> bytes:
    """Add watermark to an image"""
    try:
        # Open the image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create a transparent layer for the watermark
        txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Try to use a nice font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", settings.fontSize)
        except Exception:
            font = ImageFont.load_default()
        
        # Get text size
        text = settings.text or WATERMARK_TEXT
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate position
        padding = 20
        if settings.position == "bottom-right":
            x = img.width - text_width - padding
            y = img.height - text_height - padding
        elif settings.position == "bottom-left":
            x = padding
            y = img.height - text_height - padding
        elif settings.position == "top-right":
            x = img.width - text_width - padding
            y = padding
        elif settings.position == "top-left":
            x = padding
            y = padding
        else:  # center
            x = (img.width - text_width) // 2
            y = (img.height - text_height) // 2
        
        # Calculate opacity (0-255 from 0-100 percent)
        opacity = int((settings.opacity / 100) * 255)
        
        # Draw shadow for better visibility
        shadow_color = (0, 0, 0, opacity // 2)
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
        
        # Draw watermark text
        text_color = (255, 255, 255, opacity)
        draw.text((x, y), text, font=font, fill=text_color)
        
        # Composite the watermark layer onto the image
        watermarked = Image.alpha_composite(img, txt_layer)
        
        # Convert back to RGB for JPEG compatibility
        if watermarked.mode == 'RGBA':
            background = Image.new('RGB', watermarked.size, (255, 255, 255))
            background.paste(watermarked, mask=watermarked.split()[-1])
            watermarked = background
        
        # Save to bytes
        output = io.BytesIO()
        watermarked.save(output, format='PNG', quality=95)
        output.seek(0)
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        raise


@router.post("/image")
async def watermark_image(
    file: UploadFile = File(...),
    position: str = "bottom-right",
    opacity: int = 50,
    fontSize: int = 24,
    user: dict = Depends(get_current_user)
):
    """Add watermark to an uploaded image"""
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Apply watermark
        settings = WatermarkSettings(
            position=position,
            opacity=opacity,
            fontSize=fontSize
        )
        
        watermarked = add_watermark_to_image(contents, settings)
        
        # Log the action
        await db.watermark_logs.insert_one({
            "id": str(uuid.uuid4()),
            "userId": user.get("id"),
            "originalFilename": file.filename,
            "settings": settings.dict(),
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        # Return the watermarked image
        return StreamingResponse(
            io.BytesIO(watermarked),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=watermarked_{file.filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error watermarking image: {e}")
        raise HTTPException(status_code=500, detail="Failed to add watermark")


@router.get("/settings")
async def get_watermark_settings(user: dict = Depends(get_current_user)):
    """Get user's watermark preferences"""
    try:
        settings = await db.user_settings.find_one(
            {"userId": user.get("id")},
            {"_id": 0, "watermark": 1}
        )
        
        return {
            "success": True,
            "settings": settings.get("watermark") if settings else {
                "enabled": True,
                "text": WATERMARK_TEXT,
                "position": "bottom-right",
                "opacity": 50
            }
        }
    except Exception as e:
        logger.error(f"Error getting watermark settings: {e}")
        return {
            "success": True,
            "settings": {
                "enabled": True,
                "text": WATERMARK_TEXT,
                "position": "bottom-right",
                "opacity": 50
            }
        }


@router.post("/settings")
async def save_watermark_settings(settings: WatermarkSettings, user: dict = Depends(get_current_user)):
    """Save user's watermark preferences"""
    try:
        await db.user_settings.update_one(
            {"userId": user.get("id")},
            {
                "$set": {
                    "userId": user.get("id"),
                    "watermark": settings.dict(),
                    "updatedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        return {"success": True, "message": "Watermark settings saved"}
    except Exception as e:
        logger.error(f"Error saving watermark settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")
