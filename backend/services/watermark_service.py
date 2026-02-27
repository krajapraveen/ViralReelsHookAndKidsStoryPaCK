"""
Watermark Service
Diagonal watermarks for ALL free outputs
"""
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import math


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


def should_apply_watermark(user_plan: str) -> bool:
    """
    Check if watermark should be applied based on user plan
    
    Free users get watermarks, paid plans don't
    """
    free_plans = ["free", "trial", None, ""]
    return str(user_plan).lower() in free_plans


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
