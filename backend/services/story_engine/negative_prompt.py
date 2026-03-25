"""
Universal Negative Prompt — System-level, non-removable.
Applied to ALL image generation, keyframe generation, and video generation.
"""

# This prompt is injected into every visual generation call.
# It cannot be overridden by user input.
UNIVERSAL_NEGATIVE_PROMPT = (
    "blurry, out of focus, low resolution, pixelated, noisy, grainy, "
    "distorted, warped, stretched, squished, "
    "extra limbs, extra fingers, extra arms, extra legs, missing limbs, fused limbs, "
    "deformed hands, deformed face, deformed body, anatomical errors, "
    "inconsistent character design, style drift, clothing change mid-scene, "
    "text, watermark, logo, signature, caption, subtitles, UI overlay, "
    "copyrighted character, trademarked character, Disney, Marvel, DC Comics, "
    "celebrity face, real person resemblance, photorealistic celebrity, "
    "static image, slideshow feel, frozen pose, no motion, still frame, "
    "uncanny valley, plastic skin, mannequin, doll-like, "
    "NSFW, nudity, violence, gore, blood, weapons, "
    "duplicate characters in same frame unless scripted, "
    "inconsistent lighting between cuts, shadow direction mismatch"
)

# Per-category additional negatives
CATEGORY_NEGATIVES = {
    "kids": (
        "scary, frightening, dark themes, violence, blood, weapons, "
        "horror elements, jump scare, death, injury, adult themes"
    ),
    "horror": (
        "cute, bright colors, cartoon style unless specified, cheerful"
    ),
}


def get_negative_prompt(category: str = "", user_negatives: str = "") -> str:
    """
    Build the full negative prompt. Universal negatives are ALWAYS included.
    Category-specific and user negatives are appended.
    """
    parts = [UNIVERSAL_NEGATIVE_PROMPT]

    cat_neg = CATEGORY_NEGATIVES.get(category, "")
    if cat_neg:
        parts.append(cat_neg)

    if user_negatives and user_negatives.strip():
        parts.append(user_negatives.strip())

    return ", ".join(parts)


def get_style_positive_prompt(style_id: str) -> str:
    """Get positive style prompt for a given animation style."""
    STYLE_PROMPTS = {
        "cartoon_2d": "vibrant 2D cartoon animation style, clean lines, bold colors, expressive characters, fluid motion",
        "anime": "anime art style, detailed eyes, dynamic poses, Japanese animation quality, cel-shaded",
        "watercolor": "watercolor painting style, soft edges, flowing colors, gentle gradients, painterly texture",
        "realistic": "photorealistic style, cinematic lighting, detailed textures, natural shadows, film grain",
        "noir": "film noir style, high contrast, deep shadows, black and white with selective color, dramatic lighting",
        "pixel_art": "retro pixel art style, 16-bit aesthetic, clean pixels, limited palette, nostalgic",
    }
    return STYLE_PROMPTS.get(style_id, STYLE_PROMPTS["cartoon_2d"])
