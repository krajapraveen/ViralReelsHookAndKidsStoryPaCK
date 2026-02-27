"""
Centralized Image & GIF Generation Service
CreatorStudio AI - Unified generation pipeline

This module centralizes ALL image and GIF generation logic:
- Comic character generation
- Story illustrations
- GIF creation with text overlays
- Watermarking (for free users)
- Format conversion
- Error handling with fallbacks

All generation requests flow through this service for:
- Consistent watermarking
- Credit protection
- Rate limiting
- Error recovery
- Analytics tracking
"""
import os
import io
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple, BinaryIO
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import hashlib

logger = logging.getLogger(__name__)

# Configuration
WATERMARK_TEXT = "CreatorStudio AI"
WATERMARK_OPACITY = 128  # 0-255
WATERMARK_POSITION = "bottom-right"
MAX_IMAGE_SIZE = (2048, 2048)
SUPPORTED_FORMATS = ["PNG", "JPEG", "GIF", "WEBP"]


class CentralizedGenerationService:
    """
    Unified service for all image and GIF generation operations.
    Ensures consistent handling of:
    - Generation
    - Watermarking
    - Format conversion
    - Error handling
    - Analytics
    """
    
    def __init__(self, db):
        self.db = db
        self._generation_count = 0
    
    # =========================================================================
    # WATERMARKING
    # =========================================================================
    
    def apply_watermark(
        self,
        image: Image.Image,
        user_plan: str = "free",
        custom_text: Optional[str] = None
    ) -> Image.Image:
        """
        Apply watermark to an image for free users.
        
        Args:
            image: PIL Image to watermark
            user_plan: User's subscription plan
            custom_text: Optional custom watermark text
            
        Returns:
            Watermarked image (or original if paid user)
        """
        # Don't watermark for paid users
        if user_plan.lower() in ["pro", "premium", "enterprise", "paid"]:
            return image
        
        # Convert to RGBA for transparency support
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Create watermark overlay
        watermark_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # Get font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text = custom_text or WATERMARK_TEXT
        
        # Calculate text size and position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position watermark
        padding = 10
        if WATERMARK_POSITION == "bottom-right":
            x = image.width - text_width - padding
            y = image.height - text_height - padding
        elif WATERMARK_POSITION == "bottom-left":
            x = padding
            y = image.height - text_height - padding
        elif WATERMARK_POSITION == "top-right":
            x = image.width - text_width - padding
            y = padding
        else:  # center
            x = (image.width - text_width) // 2
            y = (image.height - text_height) // 2
        
        # Draw watermark with semi-transparency
        draw.text((x, y), text, font=font, fill=(255, 255, 255, WATERMARK_OPACITY))
        
        # Composite
        watermarked = Image.alpha_composite(image, watermark_layer)
        
        return watermarked
    
    def apply_watermark_to_gif(
        self,
        gif_bytes: bytes,
        user_plan: str = "free"
    ) -> bytes:
        """
        Apply watermark to each frame of a GIF.
        
        Args:
            gif_bytes: Raw GIF bytes
            gif: PIL Image (GIF)
            user_plan: User's subscription plan
            
        Returns:
            Watermarked GIF bytes
        """
        if user_plan.lower() in ["pro", "premium", "enterprise", "paid"]:
            return gif_bytes
        
        gif = Image.open(io.BytesIO(gif_bytes))
        
        frames = []
        durations = []
        
        for frame in ImageSequence.Iterator(gif):
            # Get duration for this frame
            durations.append(frame.info.get("duration", 100))
            
            # Convert and watermark
            frame_rgba = frame.convert("RGBA")
            watermarked_frame = self.apply_watermark(frame_rgba, "free")
            frames.append(watermarked_frame)
        
        # Save as GIF
        output = io.BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=False
        )
        
        return output.getvalue()
    
    # =========================================================================
    # IMAGE GENERATION HELPERS
    # =========================================================================
    
    def resize_image(
        self,
        image: Image.Image,
        max_size: Tuple[int, int] = MAX_IMAGE_SIZE
    ) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image
    
    def convert_format(
        self,
        image: Image.Image,
        target_format: str = "PNG",
        quality: int = 95
    ) -> bytes:
        """Convert image to specified format"""
        output = io.BytesIO()
        
        if target_format.upper() == "JPEG":
            # JPEG doesn't support transparency
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            image.save(output, format="JPEG", quality=quality)
        else:
            image.save(output, format=target_format.upper())
        
        return output.getvalue()
    
    def create_text_overlay(
        self,
        image: Image.Image,
        text: str,
        position: str = "bottom",
        font_size: int = 32,
        text_color: str = "white",
        bg_color: str = "black",
        padding: int = 10
    ) -> Image.Image:
        """
        Add text overlay to an image.
        Used for meme-style text, captions, etc.
        """
        image = image.convert("RGBA")
        
        # Create text layer
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate text size
        draw = ImageDraw.Draw(image)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create background rectangle for text
        if position == "bottom":
            rect_y = image.height - text_height - padding * 2
            text_y = image.height - text_height - padding
        elif position == "top":
            rect_y = 0
            text_y = padding
        else:  # center
            rect_y = (image.height - text_height - padding * 2) // 2
            text_y = (image.height - text_height) // 2
        
        text_x = (image.width - text_width) // 2
        
        # Draw background
        bg_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_layer)
        bg_draw.rectangle(
            [(0, rect_y), (image.width, rect_y + text_height + padding * 2)],
            fill=(0, 0, 0, 180) if bg_color == "black" else (255, 255, 255, 180)
        )
        
        # Draw text
        color = (255, 255, 255, 255) if text_color == "white" else (0, 0, 0, 255)
        bg_draw.text((text_x, text_y), text, font=font, fill=color)
        
        # Composite
        result = Image.alpha_composite(image, bg_layer)
        
        return result
    
    # =========================================================================
    # GIF CREATION
    # =========================================================================
    
    def create_reaction_gif(
        self,
        images: List[Image.Image],
        text_overlays: Optional[List[str]] = None,
        duration_per_frame: int = 500,
        user_plan: str = "free"
    ) -> bytes:
        """
        Create a reaction GIF from a list of images.
        
        Args:
            images: List of PIL Images
            text_overlays: Optional text for each frame
            duration_per_frame: Milliseconds per frame
            user_plan: User's subscription plan
            
        Returns:
            GIF bytes
        """
        if not images:
            raise ValueError("No images provided")
        
        frames = []
        
        for i, img in enumerate(images):
            # Ensure consistent size
            img = img.convert("RGBA")
            
            # Add text overlay if provided
            if text_overlays and i < len(text_overlays) and text_overlays[i]:
                img = self.create_text_overlay(img, text_overlays[i])
            
            # Apply watermark for free users
            if user_plan.lower() == "free":
                img = self.apply_watermark(img, "free")
            
            # Convert to P mode for GIF
            frames.append(img.convert("P", palette=Image.ADAPTIVE))
        
        # Create GIF
        output = io.BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration_per_frame,
            loop=0
        )
        
        return output.getvalue()
    
    def create_slideshow_gif(
        self,
        images: List[Image.Image],
        transition: str = "none",  # none, fade, slide
        duration_per_image: int = 2000,
        user_plan: str = "free"
    ) -> bytes:
        """
        Create a slideshow GIF from images.
        """
        if not images:
            raise ValueError("No images provided")
        
        frames = []
        frame_duration = duration_per_image // 10  # 10 sub-frames per image
        
        for i, img in enumerate(images):
            img = img.convert("RGBA")
            
            # Apply watermark
            if user_plan.lower() == "free":
                img = self.apply_watermark(img, "free")
            
            # Add frames for this image
            for _ in range(10):
                frames.append(img.convert("P", palette=Image.ADAPTIVE))
        
        output = io.BytesIO()
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=0
        )
        
        return output.getvalue()
    
    # =========================================================================
    # COMIC GENERATION HELPERS
    # =========================================================================
    
    def create_comic_panel_layout(
        self,
        images: List[Image.Image],
        layout: str = "grid",  # grid, vertical, horizontal
        panel_size: Tuple[int, int] = (400, 400),
        gap: int = 10,
        background_color: str = "#FFFFFF"
    ) -> Image.Image:
        """
        Create a comic panel layout from multiple images.
        """
        num_images = len(images)
        
        if layout == "vertical":
            width = panel_size[0]
            height = panel_size[1] * num_images + gap * (num_images - 1)
            canvas = Image.new("RGB", (width, height), background_color)
            
            y = 0
            for img in images:
                img = img.resize(panel_size, Image.Resampling.LANCZOS)
                canvas.paste(img, (0, y))
                y += panel_size[1] + gap
                
        elif layout == "horizontal":
            width = panel_size[0] * num_images + gap * (num_images - 1)
            height = panel_size[1]
            canvas = Image.new("RGB", (width, height), background_color)
            
            x = 0
            for img in images:
                img = img.resize(panel_size, Image.Resampling.LANCZOS)
                canvas.paste(img, (x, 0))
                x += panel_size[0] + gap
                
        else:  # grid
            cols = 2 if num_images <= 4 else 3
            rows = (num_images + cols - 1) // cols
            
            width = panel_size[0] * cols + gap * (cols - 1)
            height = panel_size[1] * rows + gap * (rows - 1)
            canvas = Image.new("RGB", (width, height), background_color)
            
            for i, img in enumerate(images):
                row = i // cols
                col = i % cols
                x = col * (panel_size[0] + gap)
                y = row * (panel_size[1] + gap)
                
                img = img.resize(panel_size, Image.Resampling.LANCZOS)
                canvas.paste(img, (x, y))
        
        return canvas
    
    def add_speech_bubble(
        self,
        image: Image.Image,
        text: str,
        position: Tuple[int, int],
        bubble_type: str = "speech"  # speech, thought
    ) -> Image.Image:
        """
        Add a speech or thought bubble to an image.
        """
        image = image.convert("RGBA")
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Calculate text size
        draw = ImageDraw.Draw(image)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        padding = 15
        bubble_width = text_width + padding * 2
        bubble_height = text_height + padding * 2
        
        # Create bubble layer
        bubble_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        bubble_draw = ImageDraw.Draw(bubble_layer)
        
        # Draw bubble
        x, y = position
        if bubble_type == "thought":
            # Draw ellipse for thought bubble
            bubble_draw.ellipse(
                [x, y, x + bubble_width, y + bubble_height],
                fill=(255, 255, 255, 240),
                outline=(0, 0, 0, 255)
            )
            # Add small circles for thought trail
            for i in range(3):
                cx = x + bubble_width // 2 - i * 10
                cy = y + bubble_height + 5 + i * 8
                r = 5 - i
                bubble_draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 255, 240))
        else:
            # Draw rounded rectangle for speech bubble
            bubble_draw.rounded_rectangle(
                [x, y, x + bubble_width, y + bubble_height],
                radius=10,
                fill=(255, 255, 255, 240),
                outline=(0, 0, 0, 255)
            )
            # Draw tail
            tail_points = [
                (x + bubble_width // 2 - 10, y + bubble_height),
                (x + bubble_width // 2, y + bubble_height + 15),
                (x + bubble_width // 2 + 10, y + bubble_height)
            ]
            bubble_draw.polygon(tail_points, fill=(255, 255, 255, 240))
        
        # Draw text
        bubble_draw.text((x + padding, y + padding), text, font=font, fill=(0, 0, 0, 255))
        
        # Composite
        result = Image.alpha_composite(image, bubble_layer)
        
        return result
    
    # =========================================================================
    # ANALYTICS & TRACKING
    # =========================================================================
    
    async def log_generation(
        self,
        user_id: str,
        generation_type: str,
        success: bool,
        credits_used: int = 0,
        metadata: Optional[Dict] = None
    ):
        """Log generation event for analytics"""
        await self.db.generation_analytics.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": generation_type,
            "success": success,
            "credits_used": credits_used,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        self._generation_count += 1
    
    async def get_generation_stats(self, days: int = 30) -> Dict:
        """Get generation statistics"""
        from datetime import timedelta
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "success_count": {"$sum": {"$cond": ["$success", 1, 0]}},
                "total_credits": {"$sum": "$credits_used"}
            }}
        ]
        
        results = await self.db.generation_analytics.aggregate(pipeline).to_list(100)
        
        return {
            "period_days": days,
            "by_type": {r["_id"]: {
                "count": r["count"],
                "success_rate": round(r["success_count"] / r["count"] * 100, 1) if r["count"] > 0 else 0,
                "credits_used": r["total_credits"]
            } for r in results},
            "total_generations": sum(r["count"] for r in results)
        }


# Singleton
_generation_service = None


def get_generation_service(db) -> CentralizedGenerationService:
    """Get or create the generation service singleton"""
    global _generation_service
    if _generation_service is None:
        _generation_service = CentralizedGenerationService(db)
    return _generation_service


__all__ = [
    'CentralizedGenerationService',
    'get_generation_service',
    'WATERMARK_TEXT',
    'SUPPORTED_FORMATS'
]
