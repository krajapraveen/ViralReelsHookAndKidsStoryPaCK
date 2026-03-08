"""
Watermark Service
Diagonal watermarks for ALL free outputs
Logo watermark - Transparent, Medium-Big, Diagonal
Only for FREE users (not for subscription or top-up users)
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import base64
import math
import os


# Path to logo file (if exists)
LOGO_PATH = "/app/backend/static/logo_watermark.png"


def add_diagonal_watermark(
    image_bytes: bytes, 
    text: str = "CREATORSTUDIO AI", 
    opacity: float = 0.15,
    font_size: int = 40,
    spacing: int = 200
) -> bytes:
    """
    Add diagonal watermark text across the entire image
    
    Args:
        image_bytes: Input image as bytes
        text: Watermark text
        opacity: Watermark opacity (0-1)
        font_size: Font size for watermark
        spacing: Spacing between watermark repetitions
    
    Returns:
        Watermarked image as bytes
    """
    # Open the image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size
    
    # Create a transparent layer for the watermark
    watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)
    
    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Calculate diagonal angle (45 degrees)
    angle = -30
    
    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate watermark color with opacity
    watermark_color = (128, 128, 128, int(255 * opacity))
    
    # Calculate the diagonal length to cover entire image
    diagonal = int(math.sqrt(width**2 + height**2))
    
    # Create a larger layer to rotate
    text_layer = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    
    # Draw repeated watermark text
    y = 0
    while y < diagonal * 2:
        x = 0
        while x < diagonal * 2:
            text_draw.text((x, y), text, font=font, fill=watermark_color)
            x += text_width + spacing
        y += text_height + spacing
    
    # Rotate the text layer
    text_layer = text_layer.rotate(angle, expand=False, resample=Image.BICUBIC)
    
    # Calculate position to center the rotated watermark
    offset_x = (text_layer.width - width) // 2
    offset_y = (text_layer.height - height) // 2
    
    # Crop to original image size
    text_layer = text_layer.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    
    # Composite the watermark onto the original image
    watermarked = Image.alpha_composite(img, text_layer)
    
    # Convert back to RGB and save
    watermarked = watermarked.convert("RGB")
    output = io.BytesIO()
    watermarked.save(output, format="PNG", quality=95)
    output.seek(0)
    
    return output.getvalue()


def add_logo_watermark(
    image_bytes: bytes,
    logo_bytes: bytes = None,
    opacity: float = 0.35,
    scale: float = 0.15,
    position: str = "diagonal"
) -> bytes:
    """
    Add logo watermark to image - diagonal, transparent, medium-big
    
    Args:
        image_bytes: Input image as bytes
        logo_bytes: Logo image as bytes (optional, uses text if not provided)
        opacity: Logo opacity (0-1) - higher = more visible
        scale: Logo size relative to image (0.1 = 10% of image size)
        position: "diagonal" for diagonal placement, "center" for single center
    
    Returns:
        Watermarked image as bytes
    """
    # Open the main image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size
    
    # Create watermark layer
    watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    
    # If no logo provided, create text-based logo
    if logo_bytes:
        logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    else:
        # Create a text-based logo watermark
        logo_size = int(min(width, height) * scale * 2)
        logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(logo)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(logo_size * 0.12))
        except:
            font = ImageFont.load_default()
        
        # Draw "CREATORSTUDIO AI" text in logo
        text = "CREATORSTUDIO AI"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (logo_size - text_w) // 2
        y = (logo_size - text_h) // 2
        
        # Draw with semi-transparent white
        draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))
    
    # Resize logo to medium-big size (15% of image width)
    logo_width = int(width * scale)
    logo_height = int(logo.height * (logo_width / logo.width))
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    
    # Apply opacity to logo
    if logo.mode == "RGBA":
        r, g, b, a = logo.split()
        a = ImageEnhance.Brightness(a).enhance(opacity)
        logo = Image.merge("RGBA", (r, g, b, a))
    
    if position == "diagonal":
        # Place logos diagonally across the image
        spacing_x = int(logo_width * 1.5)
        spacing_y = int(logo_height * 1.5)
        
        # Calculate diagonal
        diagonal = int(math.sqrt(width**2 + height**2))
        
        # Create a larger layer for rotation
        temp_layer = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
        
        # Tile logos
        y = 0
        while y < diagonal * 2:
            x = 0
            while x < diagonal * 2:
                temp_layer.paste(logo, (x, y), logo)
                x += spacing_x
            y += spacing_y
        
        # Rotate the layer by -30 degrees
        temp_layer = temp_layer.rotate(-30, expand=False, resample=Image.BICUBIC)
        
        # Crop to original image size
        offset_x = (temp_layer.width - width) // 2
        offset_y = (temp_layer.height - height) // 2
        watermark_layer = temp_layer.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    else:
        # Single center placement
        x = (width - logo_width) // 2
        y = (height - logo_height) // 2
        watermark_layer.paste(logo, (x, y), logo)
    
    # Composite
    watermarked = Image.alpha_composite(img, watermark_layer)
    
    # Convert and save
    watermarked = watermarked.convert("RGB")
    output = io.BytesIO()
    watermarked.save(output, format="PNG", quality=95)
    output.seek(0)
    
    return output.getvalue()


def add_watermark_to_base64(
    base64_image: str, 
    text: str = "CREATORSTUDIO AI",
    opacity: float = 0.15
) -> str:
    """
    Add watermark to a base64-encoded image
    
    Args:
        base64_image: Base64 encoded image string
        text: Watermark text
        opacity: Watermark opacity
    
    Returns:
        Watermarked image as base64 string
    """
    # Decode base64
    if "," in base64_image:
        base64_image = base64_image.split(",")[1]
    
    image_bytes = base64.b64decode(base64_image)
    
    # Add watermark
    watermarked_bytes = add_diagonal_watermark(image_bytes, text, opacity)
    
    # Encode back to base64
    return base64.b64encode(watermarked_bytes).decode("utf-8")


def should_apply_watermark(user: dict) -> bool:
    """
    Check if watermark should be applied based on user plan
    
    FREE users get watermarks
    Subscription users (weekly, monthly, quarterly, yearly) do NOT get watermarks
    Top-up users (starter, creator, pro purchasers) do NOT get watermarks
    """
    if not user:
        return True  # No user = apply watermark
    
    plan = str(user.get("plan", "")).lower()
    
    # Plans that DO NOT get watermarks (paid plans)
    paid_plans = [
        "weekly", "monthly", "quarterly", "yearly",  # Subscriptions
        "starter", "creator", "pro",  # Top-up plans
        "premium", "enterprise", "admin", "demo"  # Other paid/special plans
    ]
    
    # Check if user has a paid plan
    if plan in paid_plans:
        return False
    
    # Check if user has made any successful payment
    # (this will be checked at runtime via database)
    
    # Default: apply watermark for free/unknown plans
    free_plans = ["free", "trial", "", "none"]
    return plan in free_plans or not plan


# Watermark configurations for different content types
WATERMARK_CONFIGS = {
    "REEL": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.12,
        "font_size": 35,
        "spacing": 180
    },
    "COMIC": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.15,
        "font_size": 40,
        "spacing": 200
    },
    "GIF": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.12,
        "font_size": 30,
        "spacing": 150
    },
    "STORY": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.10,
        "font_size": 45,
        "spacing": 220
    },
    "COLORING_BOOK": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.15,
        "font_size": 40,
        "spacing": 200
    },
    "STORYBOOK": {
        "text": "CREATORSTUDIO AI",
        "opacity": 0.12,
        "font_size": 38,
        "spacing": 190
    }
}


def get_watermark_config(content_type: str) -> dict:
    """Get watermark configuration for a content type"""
    return WATERMARK_CONFIGS.get(content_type.upper(), WATERMARK_CONFIGS["COMIC"])
