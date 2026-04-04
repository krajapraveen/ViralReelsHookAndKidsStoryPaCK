"""
Image Generation Service
Primary: GPT Image 1 via existing image_gen_direct
Fallback: Solid-color PNG with text overlay (Pillow)
"""
import os
import io
import logging

logger = logging.getLogger("viral.image_gen")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


async def generate_thumbnail(idea: str, niche: str) -> dict:
    """Returns {"image_bytes": bytes, "fallback_used": bool}"""
    # Level 1: GPT Image 1
    if EMERGENT_KEY:
        try:
            from services.image_gen_direct import generate_image_direct
            prompt = (
                f"Create a bold, eye-catching social media thumbnail for a viral video about: {idea}. "
                f"Niche: {niche}. Style: modern, bold typography, vibrant colors, professional. "
                f"No text on the image. Abstract or thematic background that conveys the topic."
            )
            images = await generate_image_direct(
                api_key=EMERGENT_KEY,
                prompt=prompt,
                model="gpt-image-1",
                quality="low",
                size="1024x1024",
                n=1,
            )
            if images and len(images) > 0:
                logger.info("[THUMBNAIL] Generated via GPT Image 1")
                return {"image_bytes": images[0], "fallback_used": False}
        except Exception as e:
            logger.warning(f"[THUMBNAIL] GPT Image 1 failed: {e}")

    # Level 2: Pillow fallback
    return {"image_bytes": _generate_fallback_thumbnail(idea, niche), "fallback_used": True}


def _generate_fallback_thumbnail(idea: str, niche: str) -> bytes:
    """Generate a simple gradient thumbnail with Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        COLORS = {
            "Tech": ((15, 23, 42), (56, 189, 248)), "Finance": ((15, 23, 42), (74, 222, 128)),
            "Fitness": ((26, 10, 10), (248, 113, 113)), "Food": ((26, 20, 0), (251, 191, 36)),
            "Travel": ((15, 7, 32), (192, 132, 252)), "Fashion": ((26, 10, 20), (251, 113, 133)),
            "Gaming": ((10, 10, 31), (129, 140, 248)), "Education": ((5, 20, 20), (45, 212, 191)),
            "Business": ((17, 17, 17), (148, 163, 184)), "Lifestyle": ((26, 20, 0), (251, 191, 36)),
            "Health": ((5, 26, 10), (74, 222, 128)), "Entertainment": ((26, 10, 26), (232, 121, 249)),
        }
        bg, accent = COLORS.get(niche, ((15, 23, 42), (249, 115, 22)))

        img = Image.new("RGB", (1080, 1080), bg)
        draw = ImageDraw.Draw(img)

        # Draw accent circle
        draw.ellipse([340, 340, 740, 740], fill=(*accent, 40) if len(accent) == 3 else accent)

        # Draw text
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = font_large

        # Niche label
        draw.text((540, 300), niche.upper(), fill=accent, font=font_small, anchor="mm")

        # Title (wrapped)
        title = idea[:80]
        words = title.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if len(test) > 25:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        y = 480
        for line in lines[:4]:
            draw.text((540, y), line, fill="white", font=font_large, anchor="mm")
            y += 65

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        logger.info("[THUMBNAIL] Generated fallback with Pillow")
        return buf.getvalue()

    except ImportError:
        # Ultra-fallback: 1x1 orange pixel PNG
        logger.warning("[THUMBNAIL] Pillow not available, using minimal fallback")
        import struct
        import zlib
        def _minimal_png():
            raw = b'\x00\xf9\x73\x16'
            data = zlib.compress(raw)
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            chunks = b''
            for ctype, cdata in [(b'IHDR', ihdr), (b'IDAT', data), (b'IEND', b'')]:
                chunks += struct.pack('>I', len(cdata)) + ctype + cdata + struct.pack('>I', zlib.crc32(ctype + cdata) & 0xffffffff)
            return b'\x89PNG\r\n\x1a\n' + chunks
        return _minimal_png()
