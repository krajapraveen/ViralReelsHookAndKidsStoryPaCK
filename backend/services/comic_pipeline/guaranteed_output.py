"""
Guaranteed Output Service — Deterministic comic-style output from source photo.

When ALL AI generation attempts fail, this service applies image processing
(Pillow-based comic filters) to the source photo to guarantee output.

This is NOT AI. This is deterministic image manipulation. It CANNOT fail
(barring corrupt source photo, which gets a color-block fallback).

STYLE-AWARE: Each style maps to a radically different visual treatment.
A human must be able to INSTANTLY tell the difference between styles.
"""
import io
import hashlib
import logging
from typing import List, Optional

from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont

logger = logging.getLogger("creatorstudio.comic_pipeline.guaranteed_output")

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


def _image_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=90)
    return buf.getvalue()


def _create_color_block_fallback(panel_index: int, scene: str, total_panels: int) -> bytes:
    """Absolute last resort — colored block with scene text."""
    colors = [
        (41, 128, 185), (142, 68, 173), (39, 174, 96),
        (211, 84, 0), (192, 57, 43), (44, 62, 80),
    ]
    color = colors[panel_index % len(colors)]
    img = Image.new("RGB", (PANEL_WIDTH, PANEL_HEIGHT), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
        small_font = font
    draw.text((PANEL_WIDTH // 2, PANEL_HEIGHT // 3), f"Panel {panel_index + 1}",
              fill=(255, 255, 255), font=font, anchor="mm")
    scene_text = scene[:80] + "..." if len(scene) > 80 else scene
    draw.text((PANEL_WIDTH // 2, PANEL_HEIGHT * 2 // 3), scene_text,
              fill=(255, 255, 255, 200), font=small_font, anchor="mm")
    draw.rectangle([(4, 4), (PANEL_WIDTH - 5, PANEL_HEIGHT - 5)],
                   outline=(255, 255, 255), width=3)
    return _image_to_bytes(img)


def _add_comic_border(img: Image.Image, panel_index: int) -> Image.Image:
    """Add comic-style border to panel."""
    draw = ImageDraw.Draw(img)
    border_colors = [
        (0, 0, 0), (30, 30, 30), (10, 10, 10),
        (20, 20, 40), (40, 10, 10), (10, 30, 10),
    ]
    color = border_colors[panel_index % len(border_colors)]
    draw.rectangle([(0, 0), (img.width - 1, img.height - 1)], outline=color, width=5)
    draw.rectangle([(5, 5), (img.width - 6, img.height - 6)], outline=(255, 255, 255), width=1)
    return img


def _enhance_source_photo(img: Image.Image) -> Image.Image:
    """Pre-process source photo for better filter results."""
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.1)
    return img


# ══════════════════════════════════════════════════════════════════════════════
# STYLE-SPECIFIC RENDERERS — Each produces a DRAMATICALLY different look
# ══════════════════════════════════════════════════════════════════════════════

def _render_bold_hero(img: Image.Image, panel_index: int) -> Image.Image:
    """BOLD HERO: High contrast, saturated, dramatic shadows, thick black outlines."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Strong contrast and saturation
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Color(img).enhance(2.0)
    img = ImageEnhance.Brightness(img).enhance(1.1)
    # Posterize for comic flat colors
    img = ImageOps.posterize(img, 3)
    # Edge detection for comic outlines
    edges = img.filter(ImageFilter.FIND_EDGES)
    edges_l = edges.convert("L")
    # Keep original where NO edge, show black where edge is strong
    edges_mask = edges_l.point(lambda x: 255 if x < 50 else 0)
    # Composite: original image + black outlines
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), edges_mask)
    # Per-panel color warmth
    shifts = [(1.05, 0.95, 0.9), (0.95, 1.0, 1.05), (1.0, 1.05, 0.95), (1.05, 1.0, 0.9)]
    s = shifts[panel_index % len(shifts)]
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * s[0])))
    g = g.point(lambda x: min(255, int(x * s[1])))
    b = b.point(lambda x: min(255, int(x * s[2])))
    img = Image.merge("RGB", (r, g, b))
    img = img.filter(ImageFilter.SHARPEN)
    return img


def _render_cartoon(img: Image.Image, panel_index: int) -> Image.Image:
    """CARTOON: Bright, flat colors, smooth surfaces, simplified with heavy posterize."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Smooth the image first (cartoon = simplified surfaces)
    img = img.filter(ImageFilter.GaussianBlur(3))
    img = img.filter(ImageFilter.GaussianBlur(2))
    # Bright and colorful
    img = ImageEnhance.Color(img).enhance(2.0)
    img = ImageEnhance.Brightness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.6)
    # Very heavy posterize — flat color blocks
    img = ImageOps.posterize(img, 2)
    # Gentle edge lines
    edges = img.filter(ImageFilter.FIND_EDGES).convert("L")
    edges = edges.point(lambda x: 0 if x < 40 else 255)
    # Black outlines on bright image
    outline_mask = ImageOps.invert(edges)
    img = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), outline_mask)
    # Color warmth per panel
    shifts = [(1.05, 1.0, 0.9), (1.0, 1.05, 0.95), (0.95, 1.0, 1.05), (1.05, 0.95, 1.0)]
    s = shifts[panel_index % len(shifts)]
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * s[0])))
    g = g.point(lambda x: min(255, int(x * s[1])))
    b = b.point(lambda x: min(255, int(x * s[2])))
    img = Image.merge("RGB", (r, g, b))
    return img


def _render_retro_pop(img: Image.Image, panel_index: int) -> Image.Image:
    """RETRO POP: Halftone dots simulation, limited palette, vintage paper tone."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Strong color shifts — each panel a different pop art color
    shifts = [
        (0.5, 1.5, 1.8),   # Deep cyan
        (1.8, 0.5, 1.3),   # Hot magenta
        (1.7, 1.4, 0.3),   # Bold yellow
        (0.4, 1.6, 0.5),   # Vivid green
    ]
    shift = shifts[panel_index % len(shifts)]
    r, g, b = img.split()
    r = r.point(lambda x: min(255, int(x * shift[0])))
    g = g.point(lambda x: min(255, int(x * shift[1])))
    b = b.point(lambda x: min(255, int(x * shift[2])))
    img = Image.merge("RGB", (r, g, b))
    # Extreme contrast
    img = ImageEnhance.Contrast(img).enhance(3.0)
    # Super heavy posterize — 2-bit color
    img = ImageOps.posterize(img, 2)
    # Simulate halftone by pixelating then scaling back
    small = img.resize((PANEL_WIDTH // 8, PANEL_HEIGHT // 8), Image.NEAREST)
    img = small.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.NEAREST)
    # Add vintage paper tint
    paper = Image.new("RGB", img.size, (245, 235, 210))
    img = Image.blend(img, paper, 0.1)
    return img


def _render_manga(img: Image.Image, panel_index: int) -> Image.Image:
    """MANGA: Black and white ink, screen tones, high contrast, minimal color."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Convert to grayscale
    gray = img.convert("L")
    # High contrast for manga look
    gray = ImageEnhance.Contrast(gray).enhance(2.5)
    # Create screen tone pattern (simulated)
    # Threshold at different levels for panel variation
    thresholds = [100, 110, 120, 130]
    thresh = thresholds[panel_index % len(thresholds)]
    # Multi-level threshold for manga shading
    toned = gray.point(lambda x: 0 if x < thresh * 0.5 else (128 if x < thresh else 255))
    # Find bold edges
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda x: 0 if x > 20 else 255)
    # Composite: tones + bold black edges
    result = Image.composite(
        toned.convert("RGB"),
        Image.new("RGB", img.size, (0, 0, 0)),
        edges,
    )
    # Add very slight blue tint for traditional manga feel
    r_ch, g_ch, b_ch = result.split()
    b_ch = b_ch.point(lambda x: min(255, int(x * 1.08)))
    result = Image.merge("RGB", (r_ch, g_ch, b_ch))
    return result


def _render_noir(img: Image.Image, panel_index: int) -> Image.Image:
    """NOIR: Deep black shadows, high contrast B&W, dramatic lighting."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Convert to grayscale
    gray = img.convert("L")
    # Extreme contrast for noir
    gray = ImageEnhance.Contrast(gray).enhance(3.5)
    gray = ImageEnhance.Brightness(gray).enhance(0.7)
    # Hard black/white threshold for dramatic shadows
    threshold = 100 + (panel_index * 10) % 40
    bw = gray.point(lambda x: 0 if x < threshold else 255)
    # Slight blur for ink bleed effect
    bw = bw.filter(ImageFilter.GaussianBlur(0.5))
    # Convert back to RGB with slight warm paper tone
    result = Image.merge("RGB", (
        bw.point(lambda x: int(x * 1.0)),
        bw.point(lambda x: int(x * 0.95)),
        bw.point(lambda x: int(x * 0.85)),
    ))
    return result


def _render_sketch(img: Image.Image, panel_index: int) -> Image.Image:
    """SKETCH: Pencil drawing effect, fine lines, minimal fill."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    gray = img.convert("L")
    inverted = ImageOps.invert(gray)
    blurred = inverted.filter(ImageFilter.GaussianBlur(21))
    from PIL import ImageChops
    sketch = ImageChops.screen(gray, blurred)
    sketch = ImageEnhance.Contrast(sketch).enhance(2.5)
    sketch = sketch.point(lambda x: 0 if x < 120 else min(255, int(x * 1.3)))
    # Per-panel tint
    tints = [
        (0.85, 0.88, 1.0),   # Blue-tint
        (0.92, 0.85, 0.80),  # Sepia
        (0.80, 0.90, 0.85),  # Green
        (0.90, 0.82, 0.95),  # Purple
    ]
    tint = tints[panel_index % len(tints)]
    result = Image.merge("RGB", (
        sketch.point(lambda x: int(x * tint[0])),
        sketch.point(lambda x: int(x * tint[1])),
        sketch.point(lambda x: int(x * tint[2])),
    ))
    # Add edge lines
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    edges_mask = edges.point(lambda x: 255 if x < 40 else 0)
    result = Image.composite(
        Image.new("RGB", result.size, (20, 25, 40)),
        result,
        edges_mask,
    )
    return result


def _render_neon(img: Image.Image, panel_index: int) -> Image.Image:
    """NEON/CYBERPUNK: Dark background, glowing neon edges, high saturation colors."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Darken the base significantly
    img = ImageEnhance.Brightness(img).enhance(0.4)
    img = ImageEnhance.Color(img).enhance(2.5)
    # Find edges — these will "glow"
    edges = img.filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Brightness(edges).enhance(3.0)
    edges = ImageEnhance.Color(edges).enhance(3.0)
    # Neon color per panel
    neon_colors = [
        (0, 255, 255),   # Cyan
        (255, 0, 255),   # Magenta
        (0, 255, 100),   # Green
        (255, 100, 0),   # Orange
    ]
    neon = neon_colors[panel_index % len(neon_colors)]
    neon_layer = Image.new("RGB", img.size, neon)
    # Blend neon color with edges
    edges_l = edges.convert("L").point(lambda x: min(255, x * 3))
    glowing_edges = Image.composite(neon_layer, Image.new("RGB", img.size, (0, 0, 0)), edges_l)
    # Composite: dark base + glowing edges
    result = Image.blend(img, glowing_edges, 0.7)
    # Add glow blur
    glow = glowing_edges.filter(ImageFilter.GaussianBlur(4))
    result = Image.blend(result, glow, 0.3)
    return result


def _render_pastel(img: Image.Image, panel_index: int) -> Image.Image:
    """PASTEL/DREAMY: Soft, muted colors, light washes, gentle contrast."""
    img = img.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.LANCZOS)
    # Soften
    img = img.filter(ImageFilter.GaussianBlur(2))
    # Reduce contrast significantly
    img = ImageEnhance.Contrast(img).enhance(0.6)
    # Boost brightness
    img = ImageEnhance.Brightness(img).enhance(1.3)
    # Desaturate partially
    img = ImageEnhance.Color(img).enhance(0.5)
    # Posterize gently
    img = ImageOps.posterize(img, 4)
    # Add pastel color wash per panel
    washes = [
        (255, 220, 230),  # Pink
        (220, 240, 255),  # Baby blue
        (240, 255, 220),  # Mint
        (255, 240, 210),  # Peach
    ]
    wash = washes[panel_index % len(washes)]
    wash_layer = Image.new("RGB", img.size, wash)
    img = Image.blend(img, wash_layer, 0.25)
    # Soft vignette
    img = img.filter(ImageFilter.SMOOTH)
    return img


# ══════════════════════════════════════════════════════════════════════════════
# STYLE → RENDERER MAPPING
# ══════════════════════════════════════════════════════════════════════════════

STYLE_RENDERER_MAP = {
    # Action styles → Bold Hero treatment
    "bold_superhero": _render_bold_hero,
    "dark_vigilante": _render_noir,
    "retro_action": _render_retro_pop,
    "dynamic_battle": _render_bold_hero,
    # Fun styles → Cartoon treatment
    "cartoon_fun": _render_cartoon,
    "meme_expression": _render_retro_pop,
    "comic_caricature": _render_cartoon,
    "exaggerated_reaction": _render_cartoon,
    # Soft styles → Sketch/Pastel treatment
    "romance_comic": _render_pastel,
    "dreamy_pastel": _render_pastel,
    "soft_manga": _render_manga,
    "cute_chibi": _render_cartoon,
    # Fantasy styles → Mixed
    "magical_fantasy": _render_pastel,
    "medieval_adventure": _render_bold_hero,
    "scifi_neon": _render_neon,
    "cyberpunk_comic": _render_neon,
    # Kids → Cartoon
    "kids_storybook": _render_cartoon,
    "friendly_animal": _render_cartoon,
    "classroom_comic": _render_cartoon,
    "adventure_kids": _render_bold_hero,
    # Minimal → Sketch/Noir
    "black_white_ink": _render_noir,
    "sketch_outline": _render_sketch,
    "noir_comic": _render_noir,
    "vintage_print": _render_retro_pop,
}

DEFAULT_RENDERER = _render_cartoon


def generate_guaranteed_panels(
    source_bytes: bytes,
    scenes: List[dict],
    panel_count: int,
    style_name: str = "comic",
) -> List[dict]:
    """
    Generate guaranteed comic panels from source photo using image processing.
    Style-aware: each style maps to a completely different visual renderer.

    Returns list of panel dicts with:
      - panelNumber, scene, imageBytes, status, pipeline_status, guaranteed_output
    """
    panels = []
    source_img = _safe_open_image(source_bytes) if source_bytes else None

    if source_img:
        source_img = _enhance_source_photo(source_img)

    # Get style-specific renderer
    renderer = STYLE_RENDERER_MAP.get(style_name, DEFAULT_RENDERER)
    renderer_name = renderer.__name__

    logger.info(
        f"[GUARANTEED_OUTPUT] style_name={style_name} renderer={renderer_name} "
        f"panel_count={panel_count} has_source={source_img is not None}"
    )

    for i in range(panel_count):
        scene_text = scenes[i].get("scene", f"Panel {i + 1}") if i < len(scenes) else f"Panel {i + 1}"
        dialogue = scenes[i].get("dialogue") if i < len(scenes) else None

        if source_img is None:
            img_bytes = _create_color_block_fallback(i, scene_text, panel_count)
            filter_used = "color_block"
        else:
            try:
                processed = renderer(source_img.copy(), i)
                processed = _add_comic_border(processed, i)
                img_bytes = _image_to_bytes(processed)
                filter_used = renderer_name

                # Log output hash for debugging
                output_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                logger.info(
                    f"[GUARANTEED_OUTPUT] panel={i + 1} filter={filter_used} "
                    f"output_hash={output_hash}"
                )
            except Exception as e:
                logger.warning(f"Renderer {renderer_name} failed for panel {i}: {e}")
                img_bytes = _create_color_block_fallback(i, scene_text, panel_count)
                filter_used = "color_block_fallback"

        panels.append({
            "panelNumber": i + 1,
            "scene": scene_text,
            "dialogue": dialogue,
            "imageBytes": img_bytes,
            "status": "READY",
            "pipeline_status": "PASSED_GUARANTEED",
            "guaranteed_output": True,
            "filter_used": filter_used,
            "style_applied": style_name,
        })

    return panels


def enhance_source_for_ai(source_bytes: bytes) -> Optional[bytes]:
    """Enhance source photo before sending to AI for better comic conversion."""
    if not source_bytes:
        return None
    try:
        img = _safe_open_image(source_bytes)
        if img is None:
            return None
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.15)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        return _image_to_bytes(img)
    except Exception as e:
        logger.warning(f"Source enhancement failed: {e}")
        return None
