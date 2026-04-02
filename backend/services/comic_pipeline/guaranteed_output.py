"""
Guaranteed Output Service — Deterministic comic-style output from source photo.

When ALL AI generation attempts fail, this service applies image processing
(Pillow-based comic filters) to the source photo to guarantee output.

This is NOT AI. This is deterministic image manipulation. It CANNOT fail
(barring corrupt source photo, which gets a color-block fallback).

Tiers:
  - COMIC_POSTERIZE: Posterize + edge detection + halftone effect
  - COMIC_POP_ART: High contrast pop art with bold color blocks
  - COMIC_SKETCH: Pencil sketch effect with comic overlay
"""
import io
import base64
import logging
from typing import List, Optional, Tuple

from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont

logger = logging.getLogger("creatorstudio.comic_pipeline.guaranteed_output")

# Min panel dimensions
PANEL_WIDTH = 768
PANEL_HEIGHT = 768


def _safe_open_image(source_bytes: bytes) -> Optional[Image.Image]:
    """Open image from bytes, return None on failure."""
    try:
        img = Image.open(io.BytesIO(source_bytes))
        img = img.convert("RGB")
        return img
    except Exception as e:
        logger.warning(f"Failed to open source image: {e}")
        return None


def _create_color_block_fallback(panel_index: int, scene: str, total_panels: int) -> bytes:
    """Absolute last resort — colored block with scene text."""
    colors = [
        (41, 128, 185), (142, 68, 173), (39, 174, 96),
        (211, 84, 0), (192, 57, 43), (44, 62, 80),
    ]
    color = colors[panel_index % len(colors)]

    img = Image.new("RGB", (PANEL_WIDTH, PANEL_HEIGHT), color)
    draw = ImageDraw.Draw(img)

    # Add panel number
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Panel number badge
    draw.text((PANEL_WIDTH // 2, PANEL_HEIGHT // 3), f"Panel {panel_index + 1}",
              fill=(255, 255, 255), font=font, anchor="mm")

    # Scene text (truncated)
    scene_text = scene[:80] + "..." if len(scene) > 80 else scene
    draw.text((PANEL_WIDTH // 2, PANEL_HEIGHT * 2 // 3), scene_text,
              fill=(255, 255, 255, 200), font=small_font, anchor="mm")

    # Comic border
    draw.rectangle([(4, 4), (PANEL_WIDTH - 5, PANEL_HEIGHT - 5)],
                   outline=(255, 255, 255), width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=90)
    return buf.getvalue()


def _apply_comic_posterize(img: Image.Image) -> Image.Image:
    """Posterize + edge detection + contrast boost = comic look."""
    # Resize to standard
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Step 1: Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.6)

    # Step 2: Enhance color saturation
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.4)

    # Step 3: Posterize (reduce color levels for comic look)
    img = ImageOps.posterize(img, 4)

    # Step 4: Find edges and overlay
    edges = img.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.invert(edges.convert("L"))
    edges = edges.point(lambda x: 0 if x < 100 else 255)

    # Darken edges on the comic
    img_with_edges = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)),
                                      edges.convert("L"))

    # Step 5: Slight sharpen for crispness
    img_with_edges = img_with_edges.filter(ImageFilter.SHARPEN)

    return img_with_edges


def _apply_pop_art(img: Image.Image, panel_index: int) -> Image.Image:
    """High contrast pop art with color shifting per panel."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Color shift per panel for variety
    shifts = [
        (1.0, 1.2, 0.8),  # Blue-green tint
        (1.2, 0.8, 1.0),  # Magenta tint
        (0.8, 1.0, 1.2),  # Cyan tint
        (1.2, 1.0, 0.8),  # Warm tint
        (0.9, 1.1, 1.1),  # Cool tint
        (1.1, 0.9, 1.0),  # Rose tint
    ]
    shift = shifts[panel_index % len(shifts)]

    # Apply color shift
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * shift[0])))
    g = g.point(lambda x: min(255, int(x * shift[1])))
    b = b.point(lambda x: min(255, int(x * shift[2])))
    img = Image.merge("RGB", (r, g, b))

    # Extreme contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Posterize heavily
    img = ImageOps.posterize(img, 3)

    # Bold edges
    edges = img.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1,
        offset=0
    ))
    edges_l = edges.convert("L").point(lambda x: 0 if x < 30 else 255)
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), edges_l)

    return img


def _apply_sketch(img: Image.Image) -> Image.Image:
    """Pencil sketch effect with comic overlay."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Convert to grayscale
    gray = img.convert("L")

    # Invert
    inverted = ImageOps.invert(gray)

    # Blur the inverted
    blurred = inverted.filter(ImageFilter.GaussianBlur(21))

    # Dodge blend: gray / (255 - blur) * 255
    sketch = Image.new("L", img.size)
    for x in range(img.width):
        for y in range(img.height):
            g_val = gray.getpixel((x, y))
            b_val = blurred.getpixel((x, y))
            if b_val == 255:
                sketch.putpixel((x, y), g_val)
            else:
                val = min(255, int(g_val * 256 / (256 - b_val)))
                sketch.putpixel((x, y), val)

    # Add slight blue tint for comic feel
    tinted = Image.merge("RGB", (
        sketch.point(lambda x: int(x * 0.9)),
        sketch.point(lambda x: int(x * 0.92)),
        sketch,
    ))

    return tinted


def _add_comic_border(img: Image.Image, panel_index: int) -> Image.Image:
    """Add a comic-style border and panel number."""
    draw = ImageDraw.Draw(img)

    # Thick black border
    w, h = img.size
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline=(0, 0, 0), width=4)
    draw.rectangle([(4, 4), (w - 5, h - 5)], outline=(255, 255, 255), width=2)

    return img


def _enhance_source_photo(img: Image.Image) -> Image.Image:
    """Pre-processing: auto-enhance brightness, contrast, sharpness."""
    # Auto-contrast
    img = ImageOps.autocontrast(img, cutoff=1)

    # Brighten slightly
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    return img


def _image_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=90)
    return buf.getvalue()


def generate_guaranteed_panels(
    source_bytes: bytes,
    scenes: List[dict],
    panel_count: int,
    style_name: str = "comic",
) -> List[dict]:
    """
    Generate guaranteed comic panels from source photo using image processing.

    Returns list of panel dicts with:
      - panelNumber, scene, imageBytes, status, pipeline_status, guaranteed_output
    """
    panels = []
    source_img = _safe_open_image(source_bytes) if source_bytes else None

    if source_img:
        source_img = _enhance_source_photo(source_img)

    for i in range(panel_count):
        scene_text = scenes[i].get("scene", f"Panel {i + 1}") if i < len(scenes) else f"Panel {i + 1}"

        if source_img is None:
            # Absolute last resort — color block with text
            img_bytes = _create_color_block_fallback(i, scene_text, panel_count)
            filter_used = "color_block"
        else:
            # Cycle through filter styles for visual variety
            filter_cycle = i % 3
            try:
                if filter_cycle == 0:
                    processed = _apply_comic_posterize(source_img.copy())
                    filter_used = "comic_posterize"
                elif filter_cycle == 1:
                    processed = _apply_pop_art(source_img.copy(), i)
                    filter_used = "pop_art"
                else:
                    processed = _apply_comic_posterize(source_img.copy())
                    filter_used = "comic_posterize_alt"

                processed = _add_comic_border(processed, i)
                img_bytes = _image_to_bytes(processed)
            except Exception as e:
                logger.warning(f"Filter {filter_cycle} failed for panel {i}: {e}")
                img_bytes = _create_color_block_fallback(i, scene_text, panel_count)
                filter_used = "color_block_fallback"

        panels.append({
            "panelNumber": i + 1,
            "scene": scene_text,
            "dialogue": scenes[i].get("dialogue") if i < len(scenes) else None,
            "imageBytes": img_bytes,
            "status": "READY",
            "pipeline_status": "PASSED_GUARANTEED",
            "guaranteed_output": True,
            "filter_used": filter_used,
        })

    return panels


def enhance_source_for_ai(source_bytes: bytes) -> Optional[bytes]:
    """
    Pre-process source photo for better AI generation results.
    Auto-enhance brightness, contrast, face sharpening.
    Returns enhanced bytes or None if processing fails.
    """
    img = _safe_open_image(source_bytes)
    if img is None:
        return None

    try:
        img = _enhance_source_photo(img)
        return _image_to_bytes(img)
    except Exception as e:
        logger.warning(f"Source enhancement failed: {e}")
        return None
