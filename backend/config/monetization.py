"""
Monetization Configuration - Centralized Pricing & Premium Features
Handles multi-output pricing, premium styles, upsells, and subscription tiers
"""
from typing import Dict, Any, List
from enum import Enum

# =============================================================================
# SUBSCRIPTION PLANS
# =============================================================================

SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "tier": "FREE",
        "duration_days": 0,
        "credits": 10,
        "price_inr": 0,
        "price_usd": 0,
        "monthly_credits": 0,
        "daily_generations": 3,
        "features": [
            "3 generations/day",
            "1 story series (3 episodes max)",
            "Basic styles only",
            "Watermarked outputs",
            "Standard queue"
        ],
        "limitations": {
            "premium_styles": False,
            "watermark_free": False,
            "hd_download": False,
            "priority_queue": False,
            "commercial_license": False,
            "max_series": 1,
            "max_episodes_per_series": 3,
            "daily_gen_limit": 3,
            "monthly_gen_limit": 0,
        }
    },
    "creator": {
        "id": "creator",
        "name": "Creator",
        "tier": "CREATOR",
        "duration_days": 30,
        "credits": 200,
        "price_inr": 499,
        "price_usd": 5.99,
        "monthly_credits": 200,
        "daily_generations": 999,
        "features": [
            "50 generations/month",
            "5 story series (15 episodes each)",
            "Watermark removal",
            "Full Story Series Engine",
            "Basic remix + continue loops",
            "Email support"
        ],
        "limitations": {
            "premium_styles": False,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": False,
            "commercial_license": False,
            "max_series": 5,
            "max_episodes_per_series": 15,
            "daily_gen_limit": 999,
            "monthly_gen_limit": 50,
        },
        "badge": "POPULAR"
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "tier": "PRO",
        "duration_days": 30,
        "credits": 500,
        "price_inr": 999,
        "price_usd": 11.99,
        "monthly_credits": 500,
        "daily_generations": 999,
        "features": [
            "150 generations/month",
            "Unlimited story series",
            "30+ episodes per series",
            "Priority queue",
            "Advanced styles (cinematic, anime)",
            "HD export",
            "Full remix + branching"
        ],
        "limitations": {
            "premium_styles": True,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": False,
            "commercial_license": True,
            "max_series": 999,
            "max_episodes_per_series": 30,
            "daily_gen_limit": 999,
            "monthly_gen_limit": 150,
        },
        "badge": "BEST VALUE",
        "savings": "40%"
    },
    "elite": {
        "id": "elite",
        "name": "Elite",
        "tier": "ELITE",
        "duration_days": 30,
        "credits": 1500,
        "price_inr": 1999,
        "price_usd": 23.99,
        "monthly_credits": 1500,
        "daily_generations": 999,
        "features": [
            "400 generations/month",
            "Unlimited everything",
            "Fastest queue",
            "Premium rendering",
            "Early access features",
            "No restrictions"
        ],
        "limitations": {
            "premium_styles": True,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": True,
            "commercial_license": True,
            "max_series": 999,
            "max_episodes_per_series": 999,
            "daily_gen_limit": 999,
            "monthly_gen_limit": 400,
        },
        "badge": "ELITE",
        "savings": "50%"
    }
}


# =============================================================================
# TOOL CREDIT COSTS
# =============================================================================

TOOL_CREDIT_COSTS = {
    "caption": 1,
    "text": 1,
    "bio": 1,
    "comment_reply": 1,
    "tone_switcher": 1,
    "gif": 2,
    "gif_maker": 2,
    "photo_to_comic": 3,
    "comix": 3,
    "coloring_book": 3,
    "comic_storybook": 5,
    "storybook": 5,
    "reel": 5,
    "story_video": 10,
    "story_series_episode": 10,
    "thumbnail": 2,
    "brand_story": 3,
    "challenge": 1,
    "daily_viral": 1,
}


# =============================================================================
# TOP-UP PACKS
# =============================================================================

TOPUP_PACKS = {
    "small": {
        "id": "small",
        "credits": 20,
        "price_inr": 199,
        "price_usd": 2.49,
        "label": "20 Credits",
    },
    "medium": {
        "id": "medium",
        "credits": 50,
        "price_inr": 399,
        "price_usd": 4.99,
        "label": "50 Credits",
        "badge": "POPULAR",
    },
    "large": {
        "id": "large",
        "credits": 100,
        "price_inr": 699,
        "price_usd": 8.49,
        "label": "100 Credits",
        "badge": "BEST VALUE",
        "savings": "15%",
    },
}


# =============================================================================
# SERIES-SPECIFIC LIMITS
# =============================================================================

def get_series_limits(user_plan: str) -> dict:
    plan = SUBSCRIPTION_PLANS.get(user_plan, SUBSCRIPTION_PLANS["free"])
    limits = plan.get("limitations", {})
    return {
        "max_series": limits.get("max_series", 1),
        "max_episodes_per_series": limits.get("max_episodes_per_series", 3),
    }


def check_series_limit(user_plan: str, current_series_count: int) -> dict:
    limits = get_series_limits(user_plan)
    can_create = current_series_count < limits["max_series"]
    return {
        "can_create": can_create,
        "current": current_series_count,
        "limit": limits["max_series"],
        "upgrade_needed": not can_create,
        "upgrade_message": f"You've reached your {limits['max_series']} series limit. Upgrade to create more." if not can_create else None,
    }


def check_episode_limit(user_plan: str, current_episode_count: int) -> dict:
    limits = get_series_limits(user_plan)
    can_create = current_episode_count < limits["max_episodes_per_series"]
    return {
        "can_create": can_create,
        "current": current_episode_count,
        "limit": limits["max_episodes_per_series"],
        "upgrade_needed": not can_create,
        "upgrade_message": f"You've reached Episode {limits['max_episodes_per_series']} limit. Upgrade to continue your story." if not can_create else None,
    }


# =============================================================================
# MULTI-OUTPUT PRICING (Batch Generation)
# =============================================================================

VARIATION_PRICING = {
    "single": {
        "count": 1,
        "multiplier": 1.0,
        "extra_credits": 0,
        "label": "1 Output"
    },
    "triple": {
        "count": 3,
        "multiplier": 1.5,
        "extra_credits": 5,
        "label": "3 Variations",
        "badge": "SAVE 50%"
    },
    "five": {
        "count": 5,
        "multiplier": 2.0,
        "extra_credits": 10,
        "label": "5 Variations",
        "badge": "POPULAR"
    },
    "ten": {
        "count": 10,
        "multiplier": 3.0,
        "extra_credits": 20,
        "label": "10 Variations",
        "badge": "BEST VALUE"
    }
}


# =============================================================================
# UPSELL OPTIONS (Post-Generation)
# =============================================================================

UPSELL_OPTIONS = {
    "hd_download": {
        "id": "hd_download",
        "name": "Download HD",
        "description": "Get high-resolution output (4K)",
        "credits": 5,
        "icon": "download",
        "available_for": ["comix", "storybook", "gif", "story"]
    },
    "remove_watermark": {
        "id": "remove_watermark",
        "name": "Remove Watermark",
        "description": "Clean output without branding",
        "credits": 3,
        "icon": "x-circle",
        "available_for": ["comix", "gif", "storybook"],
        "free_for_plans": ["creator", "pro", "elite"]
    },
    "commercial_license": {
        "id": "commercial_license",
        "name": "Commercial License",
        "description": "Use for commercial purposes",
        "credits": 10,
        "icon": "briefcase",
        "available_for": ["comix", "storybook", "gif", "story", "reel"],
        "free_for_plans": ["pro", "elite"]
    },
    "batch_download": {
        "id": "batch_download",
        "name": "Batch Download ZIP",
        "description": "Download all assets in one ZIP",
        "credits": 5,
        "icon": "archive",
        "available_for": ["comix", "storybook", "story"]
    }
}


# =============================================================================
# BUNDLE PRICING (Panel/Page Based)
# =============================================================================

BUNDLE_PRICING = {
    "comix": {
        "1_panel": {"panels": 1, "credits": 10, "label": "1 Panel"},
        "3_panels": {"panels": 3, "credits": 25, "label": "3 Panels", "savings": "17%"},
        "6_panels": {"panels": 6, "credits": 45, "label": "6 Panels", "savings": "25%", "badge": "POPULAR"},
    },
    "storybook": {
        "4_pages": {"pages": 4, "credits": 30, "label": "4 Pages"},
        "8_pages": {"pages": 8, "credits": 55, "label": "8 Pages", "savings": "15%"},
        "12_pages": {"pages": 12, "credits": 75, "label": "12 Pages", "savings": "25%", "badge": "POPULAR"},
        "20_pages": {"pages": 20, "credits": 120, "label": "20 Pages", "savings": "30%", "badge": "BEST VALUE"},
    },
    "gif": {
        "1_gif": {"count": 1, "credits": 8, "label": "1 GIF"},
        "3_gifs": {"count": 3, "credits": 20, "label": "3 GIFs", "savings": "17%"},
        "5_gifs": {"count": 5, "credits": 30, "label": "5 GIFs", "savings": "25%", "badge": "POPULAR"},
    }
}


# =============================================================================
# PREMIUM STYLES (50% locked for Free/Creator users)
# =============================================================================

PREMIUM_STYLES = {
    "comix": {
        "free_styles": [
            {"id": "cartoon", "name": "Classic Cartoon", "premium": False},
            {"id": "comic", "name": "Comic Book", "premium": False},
            {"id": "anime_basic", "name": "Anime Basic", "premium": False},
            {"id": "sketch", "name": "Pencil Sketch", "premium": False},
        ],
        "premium_styles": [
            {"id": "manga", "name": "Manga Pro", "premium": True},
            {"id": "disney", "name": "Disney Style", "premium": True},
            {"id": "pixar", "name": "Pixar 3D", "premium": True},
            {"id": "watercolor", "name": "Watercolor Art", "premium": True},
            {"id": "noir", "name": "Film Noir", "premium": True},
            {"id": "retro", "name": "Retro Comics", "premium": True},
        ]
    },
    "gif": {
        "free_styles": [
            {"id": "bounce", "name": "Bouncy", "premium": False},
            {"id": "spin", "name": "Spin", "premium": False},
            {"id": "fade", "name": "Fade In/Out", "premium": False},
            {"id": "slide", "name": "Slide", "premium": False},
        ],
        "premium_styles": [
            {"id": "glitch", "name": "Glitch Effect", "premium": True},
            {"id": "neon", "name": "Neon Glow", "premium": True},
            {"id": "particle", "name": "Particle Burst", "premium": True},
            {"id": "morph", "name": "3D Morph", "premium": True},
        ]
    },
    "storybook": {
        "free_styles": [
            {"id": "children", "name": "Children's Book", "premium": False},
            {"id": "fairytale", "name": "Fairy Tale", "premium": False},
            {"id": "adventure", "name": "Adventure", "premium": False},
        ],
        "premium_styles": [
            {"id": "fantasy", "name": "Fantasy Epic", "premium": True},
            {"id": "scifi", "name": "Sci-Fi", "premium": True},
            {"id": "educational", "name": "Educational", "premium": True},
            {"id": "popup", "name": "Pop-up Style", "premium": True},
        ]
    },
    "reel": {
        "free_styles": [
            {"id": "viral", "name": "Viral Hook", "premium": False},
            {"id": "educational", "name": "Educational", "premium": False},
            {"id": "storytelling", "name": "Storytelling", "premium": False},
        ],
        "premium_styles": [
            {"id": "cinematic", "name": "Cinematic", "premium": True},
            {"id": "trending", "name": "Trending Format", "premium": True},
            {"id": "brand", "name": "Brand Story", "premium": True},
        ]
    }
}


# =============================================================================
# CREDIT PSYCHOLOGY CONFIG
# =============================================================================

CREDIT_PSYCHOLOGY = {
    "low_balance_threshold": 20,
    "critical_balance_threshold": 5,
    "daily_login_reward": 3,
    "trending_badge_threshold": 50,
    "urgency_messages": {
        "low": "Only {credits} credits left! Top up to keep creating.",
        "critical": "Running low! Your story is getting interesting...",
        "series_limit": "You've reached Episode {limit} limit. Upgrade to continue.",
        "daily_limit": "You've hit today's limit. Upgrade for unlimited daily use.",
    },
    "compulsion_messages": {
        "unfinished_series": "{count} episode{s} left to finish your arc",
        "cliffhanger": "A twist is waiting...",
        "unresolved": "{count} unresolved plot point{s}",
        "continue_cta": "Continue Episode {next_ep}",
        "character_waiting": "{name} is still waiting for resolution",
    }
}


# =============================================================================
# DASHBOARD PRIORITY ORDER
# =============================================================================

DASHBOARD_PRIORITY = [
    {"id": "comix", "name": "Comix AI", "credits": 10, "trending": True, "priority": 1},
    {"id": "storybook", "name": "Comic Storybook", "credits": 30, "trending": True, "priority": 2},
    {"id": "reel", "name": "Reel Generator", "credits": 10, "trending": False, "priority": 3},
    {"id": "story", "name": "Story Pack", "credits": 10, "trending": False, "priority": 4},
]

CREATOR_BOOST_PACK = [
    {"id": "coloring_book", "name": "Coloring Book", "credits": 15},
    {"id": "gif_maker", "name": "GIF Maker", "credits": 8},
    {"id": "tone_switcher", "name": "Tone Switcher", "credits": 5},
    {"id": "challenge", "name": "Challenge Generator", "credits": 5},
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_variation_cost(base_cost: int, variation_type: str) -> int:
    variation = VARIATION_PRICING.get(variation_type, VARIATION_PRICING["single"])
    return base_cost + variation["extra_credits"]


def is_style_premium(feature: str, style_id: str) -> bool:
    styles = PREMIUM_STYLES.get(feature, {})
    premium_list = styles.get("premium_styles", [])
    return any(s["id"] == style_id for s in premium_list)


def can_access_style(user_plan: str, feature: str, style_id: str) -> bool:
    if not is_style_premium(feature, style_id):
        return True
    plan = SUBSCRIPTION_PLANS.get(user_plan, SUBSCRIPTION_PLANS["free"])
    return plan.get("limitations", {}).get("premium_styles", False)


def get_upsell_cost(upsell_id: str, user_plan: str) -> int:
    upsell = UPSELL_OPTIONS.get(upsell_id)
    if not upsell:
        return 0
    free_for = upsell.get("free_for_plans", [])
    if user_plan in free_for:
        return 0
    return upsell.get("credits", 0)


def get_bundle_cost(feature: str, bundle_id: str) -> int:
    bundles = BUNDLE_PRICING.get(feature, {})
    bundle = bundles.get(bundle_id, {})
    return bundle.get("credits", 0)


def get_all_styles(feature: str) -> List[Dict[str, Any]]:
    styles = PREMIUM_STYLES.get(feature, {})
    all_styles = []
    for style in styles.get("free_styles", []):
        all_styles.append({**style, "locked": False})
    for style in styles.get("premium_styles", []):
        all_styles.append({**style, "locked": True})
    return all_styles


def get_tool_credit_cost(tool: str) -> int:
    return TOOL_CREDIT_COSTS.get(tool, 5)
