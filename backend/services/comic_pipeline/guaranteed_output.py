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


def _apply_comic_posterize(img: Image.Image, panel_index: int = 0) -> Image.Image:
    """Posterize + edge detection + contrast boost = comic look. Varies by panel index."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Per-panel color temperature variation
    color_temps = [
        (1.0, 1.0, 1.0),   # Neutral
        (1.1, 0.95, 0.9),  # Warm
        (0.9, 0.95, 1.1),  # Cool
        (1.05, 1.05, 0.9), # Golden
        (0.95, 1.0, 1.05), # Blue-tint
        (1.08, 0.92, 1.0), # Rose
    ]
    temp = color_temps[panel_index % len(color_temps)]
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * temp[0])))
    g = g.point(lambda x: min(255, int(x * temp[1])))
    b = b.point(lambda x: min(255, int(x * temp[2])))
    img = Image.merge("RGB", (r, g, b))

    # Step 1: Strong contrast boost
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Step 2: Saturate colors aggressively
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.8)

    # Step 3: Heavy posterize (fewer color levels = more comic-like)
    img = ImageOps.posterize(img, 3)

    # Step 4: Bold edge overlay
    edges = img.filter(ImageFilter.FIND_EDGES)
    edges_l = ImageOps.invert(edges.convert("L"))
    edges_l = edges_l.point(lambda x: 0 if x < 80 else 255)
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), edges_l)

    # Step 5: Sharpen for crispness
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    return img


def _apply_pop_art(img: Image.Image, panel_index: int) -> Image.Image:
    """High contrast pop art with bold color shifting per panel."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Stronger color shifts per panel for real visual variety
    shifts = [
        (0.7, 1.4, 1.6),   # Deep cyan/blue tint
        (1.6, 0.6, 1.3),   # Bold magenta
        (1.5, 1.3, 0.5),   # Hot yellow/warm
        (0.6, 1.5, 0.7),   # Vivid green
        (1.4, 0.5, 1.5),   # Purple/violet
        (1.6, 1.0, 0.4),   # Fiery orange
    ]
    shift = shifts[panel_index % len(shifts)]

    # Apply aggressive color shift
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * shift[0])))
    g = g.point(lambda x: min(255, int(x * shift[1])))
    b = b.point(lambda x: min(255, int(x * shift[2])))
    img = Image.merge("RGB", (r, g, b))

    # Extreme contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.5)

    # Heavy posterize for bold color blocks
    img = ImageOps.posterize(img, 2)

    # Bold edge detection overlay
    edges = img.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1,
        offset=0
    ))
    edges_l = edges.convert("L").point(lambda x: 0 if x < 25 else 255)
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), edges_l)

    # Extra sharpen
    img = img.filter(ImageFilter.SHARPEN)

    return img


def _apply_sketch(img: Image.Image, panel_index: int = 0) -> Image.Image:
    """Strong pencil sketch effect — fast and visually distinct. Varies tint by panel."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)

    # Per-panel tint variation
    tints = [
        (0.85, 0.88, 1.0),   # Blue-tint
        (0.92, 0.85, 0.80),  # Sepia-warm
        (0.80, 0.90, 0.85),  # Green-tint
        (0.90, 0.82, 0.95),  # Purple-tint
        (0.88, 0.88, 0.88),  # Neutral gray
        (0.82, 0.88, 0.92),  # Steel blue
    ]
    tint = tints[panel_index % len(tints)]

    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    blurred = inverted.filter(ImageFilter.GaussianBlur(21))

    from PIL import ImageChops
    sketch = ImageChops.screen(gray, blurred)

    enhancer = ImageEnhance.Contrast(sketch)
    sketch = enhancer.enhance(2.5)
    sketch = sketch.point(lambda x: 0 if x < 120 else min(255, int(x * 1.3)))

    tinted = Image.merge("RGB", (
        sketch.point(lambda x: int(x * tint[0])),
        sketch.point(lambda x: int(x * tint[1])),
        sketch.point(lambda x: int(x * tint[2])),
    ))

    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda x: 255 if x < 40 else 0)
    combined = Image.composite(
        Image.new("RGB", tinted.size, (20, 25, 40)),
        tinted,
        edges,
    )

    return combined


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


# ══════════════════════════════════════════════════════════════════════════════
# STYLE → FILTER MAPPING — Each style gets a distinct filter treatment
# ══════════════════════════════════════════════════════════════════════════════
STYLE_FILTER_MAP = {
    # Action styles → high contrast pop art
    "bold_superhero": ["pop_art", "comic_posterize", "pop_art"],
    "dark_vigilante": ["sketch", "pop_art", "sketch"],
    "retro_action": ["comic_posterize", "pop_art", "comic_posterize"],
    "dynamic_battle": ["pop_art", "pop_art", "comic_posterize"],
    # Fun styles → bright posterize
    "cartoon_fun": ["comic_posterize", "pop_art", "sketch"],
    "meme_expression": ["pop_art", "comic_posterize", "pop_art"],
    "comic_caricature": ["comic_posterize", "pop_art", "comic_posterize"],
    "exaggerated_reaction": ["pop_art", "comic_posterize", "pop_art"],
    # Soft styles → sketch and gentle filters
    "romance_comic": ["sketch", "comic_posterize", "sketch"],
    "dreamy_pastel": ["sketch", "sketch", "comic_posterize"],
    "soft_manga": ["sketch", "comic_posterize", "sketch"],
    "cute_chibi": ["comic_posterize", "sketch", "comic_posterize"],
    # Fantasy styles → mixed
    "magical_fantasy": ["comic_posterize", "pop_art", "sketch"],
    "medieval_adventure": ["comic_posterize", "sketch", "pop_art"],
    "scifi_neon": ["pop_art", "pop_art", "pop_art"],
    "cyberpunk_comic": ["pop_art", "pop_art", "comic_posterize"],
    # Kids → bright posterize
    "kids_storybook": ["comic_posterize", "pop_art", "comic_posterize"],
    "friendly_animal": ["comic_posterize", "sketch", "comic_posterize"],
    "classroom_comic": ["comic_posterize", "pop_art", "sketch"],
    "adventure_kids": ["pop_art", "comic_posterize", "pop_art"],
    # Minimal styles → sketch dominant
    "black_white_ink": ["sketch", "sketch", "sketch"],
    "sketch_outline": ["sketch", "sketch", "comic_posterize"],
    "noir_comic": ["sketch", "sketch", "pop_art"],
    "vintage_print": ["comic_posterize", "sketch", "comic_posterize"],
}

# Default rotation for unknown styles
DEFAULT_FILTER_ROTATION = ["comic_posterize", "pop_art", "sketch"]

FILTER_FUNCTIONS = {
    "comic_posterize": lambda img, idx: _apply_comic_posterize(img, idx),
    "pop_art": lambda img, idx: _apply_pop_art(img, idx),
    "sketch": lambda img, idx: _apply_sketch(img, idx),
}


def generate_guaranteed_panels(
    source_bytes: bytes,
    scenes: List[dict],
    panel_count: int,
    style_name: str = "comic",
) -> List[dict]:
    """
    Generate guaranteed comic panels from source photo using image processing.
    Style-aware: each style maps to distinct filter treatments.

    Returns list of panel dicts with:
      - panelNumber, scene, imageBytes, status, pipeline_status, guaranteed_output
    """
    panels = []
    source_img = _safe_open_image(source_bytes) if source_bytes else None

    if source_img:
        source_img = _enhance_source_photo(source_img)

    # Get style-specific filter rotation
    filter_rotation = STYLE_FILTER_MAP.get(style_name, DEFAULT_FILTER_ROTATION)

    for i in range(panel_count):
        scene_text = scenes[i].get("scene", f"Panel {i + 1}") if i < len(scenes) else f"Panel {i + 1}"

        if source_img is None:
            img_bytes = _create_color_block_fallback(i, scene_text, panel_count)
            filter_used = "color_block"
        else:
            # Style-aware filter selection
            filter_key = filter_rotation[i % len(filter_rotation)]
            filter_fn = FILTER_FUNCTIONS.get(filter_key, FILTER_FUNCTIONS["comic_posterize"])
            try:
                processed = filter_fn(source_img.copy(), i)
                filter_used = filter_key
                processed = _add_comic_border(processed, i)
                img_bytes = _image_to_bytes(processed)
            except Exception as e:
                logger.warning(f"Filter {filter_key} failed for panel {i}: {e}")
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
            "style_applied": style_name,
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
