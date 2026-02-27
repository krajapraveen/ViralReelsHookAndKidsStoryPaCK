"""
Content Protection Service
- Signed URL generation with expiry
- Ownership validation
- Watermark generation
- Access logging
"""
import hashlib
import hmac
import time
import base64
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from bson import ObjectId

# Configuration
SIGNED_URL_SECRET = "content-protection-secret-key-2026-secure"
URL_EXPIRY_SECONDS = 60
WATERMARK_OPACITY = 0.4  # 40% for visible watermark
SUBTLE_WATERMARK_OPACITY = 0.10  # 10% for repeating background

def generate_signed_token(user_id: str, file_id: str, expiry_seconds: int = URL_EXPIRY_SECONDS) -> str:
    """Generate a signed token for secure file access"""
    expiry_time = int(time.time()) + expiry_seconds
    message = f"{user_id}:{file_id}:{expiry_time}"
    signature = hmac.new(
        SIGNED_URL_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    token = base64.urlsafe_b64encode(f"{message}:{signature}".encode()).decode()
    return token

def validate_signed_token(token: str) -> Optional[Dict[str, str]]:
    """Validate a signed token and return user_id, file_id if valid"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.split(":")
        if len(parts) != 4:
            return None
        
        user_id, file_id, expiry_str, signature = parts
        expiry_time = int(expiry_str)
        
        # Check expiry
        if time.time() > expiry_time:
            return None
        
        # Verify signature
        message = f"{user_id}:{file_id}:{expiry_time}"
        expected_signature = hmac.new(
            SIGNED_URL_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        return {"user_id": user_id, "file_id": file_id}
    except Exception:
        return None

def add_visible_watermark(
    image: Image.Image,
    user_email: str,
    site_domain: str = "visionary-suite.com",
    position: str = "bottom-right"
) -> Image.Image:
    """Add visible watermark to bottom-right corner"""
    # Convert to RGBA if needed
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create watermark overlay
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Watermark text
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    watermark_text = f"Generated for {user_email}\n{site_domain}\n{date_str}"
    
    # Try to use a font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    # Get text size using textbbox
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position
    padding = 10
    if position == "bottom-right":
        x = image.width - text_width - padding
        y = image.height - text_height - padding
    elif position == "bottom-left":
        x = padding
        y = image.height - text_height - padding
    elif position == "top-right":
        x = image.width - text_width - padding
        y = padding
    else:
        x = padding
        y = padding
    
    # Draw semi-transparent background
    bg_padding = 5
    draw.rectangle(
        [x - bg_padding, y - bg_padding, x + text_width + bg_padding, y + text_height + bg_padding],
        fill=(0, 0, 0, int(255 * 0.5))
    )
    
    # Draw text
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, int(255 * WATERMARK_OPACITY)))
    
    # Composite
    return Image.alpha_composite(image, overlay)

def add_diagonal_watermark(
    image: Image.Image,
    text: str = "visionary-suite.com",
    opacity: float = SUBTLE_WATERMARK_OPACITY
) -> Image.Image:
    """Add subtle repeating diagonal watermark pattern"""
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create watermark pattern
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Calculate text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Draw diagonal pattern
    spacing_x = text_width + 100
    spacing_y = text_height + 80
    
    color = (128, 128, 128, int(255 * opacity))
    
    for y in range(-image.height, image.height * 2, spacing_y):
        for x in range(-image.width, image.width * 2, spacing_x):
            # Offset every other row
            offset = (y // spacing_y % 2) * (spacing_x // 2)
            draw.text(
                (x + offset, y),
                text,
                font=font,
                fill=color
            )
    
    # Rotate overlay for diagonal effect
    overlay = overlay.rotate(45, expand=False, fillcolor=(0, 0, 0, 0))
    
    # Crop to original size
    overlay = overlay.crop((
        (overlay.width - image.width) // 2,
        (overlay.height - image.height) // 2,
        (overlay.width + image.width) // 2,
        (overlay.height + image.height) // 2
    ))
    
    if overlay.size != image.size:
        overlay = overlay.resize(image.size)
    
    return Image.alpha_composite(image, overlay)

def apply_full_watermark(
    image: Image.Image,
    user_email: str,
    include_subtle: bool = True
) -> Image.Image:
    """Apply both visible and subtle watermarks"""
    result = image
    
    if include_subtle:
        result = add_diagonal_watermark(result)
    
    result = add_visible_watermark(result, user_email)
    
    return result

def watermark_image_bytes(
    image_bytes: bytes,
    user_email: str,
    include_subtle: bool = True,
    output_format: str = "PNG"
) -> bytes:
    """Apply watermark to image bytes and return watermarked bytes"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        watermarked = apply_full_watermark(image, user_email, include_subtle)
        
        output = io.BytesIO()
        if output_format.upper() == "JPEG":
            watermarked = watermarked.convert("RGB")
        watermarked.save(output, format=output_format)
        return output.getvalue()
    except Exception as e:
        print(f"Watermark error: {e}")
        return image_bytes

# Watermark removal pricing
WATERMARK_REMOVAL_COST = 5  # credits

async def check_watermark_removal_eligibility(db, user_id: str, file_id: str) -> Dict[str, Any]:
    """Check if user can remove watermark (requires payment)"""
    # Check if already purchased
    purchase = await db.watermark_removals.find_one({
        "user_id": user_id,
        "file_id": file_id
    })
    
    if purchase:
        return {"eligible": True, "already_purchased": True, "cost": 0}
    
    return {"eligible": True, "already_purchased": False, "cost": WATERMARK_REMOVAL_COST}

async def purchase_watermark_removal(db, user_id: str, file_id: str) -> Dict[str, Any]:
    """Process watermark removal purchase"""
    # Check user credits
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return {"success": False, "error": "User not found"}
    
    if user.get("credits", 0) < WATERMARK_REMOVAL_COST:
        return {"success": False, "error": f"Insufficient credits. {WATERMARK_REMOVAL_COST} credits required."}
    
    # Deduct credits
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"credits": -WATERMARK_REMOVAL_COST}}
    )
    
    # Record purchase
    await db.watermark_removals.insert_one({
        "user_id": user_id,
        "file_id": file_id,
        "cost": WATERMARK_REMOVAL_COST,
        "purchased_at": datetime.now(timezone.utc)
    })
    
    return {"success": True, "credits_used": WATERMARK_REMOVAL_COST}
