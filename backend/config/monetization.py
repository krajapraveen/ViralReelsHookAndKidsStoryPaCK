"""
Monetization Configuration - Centralized Pricing & Premium Features
Handles multi-output pricing, premium styles, upsells, and subscription tiers
"""
from typing import Dict, Any, List
from enum import Enum

# =============================================================================
# SUBSCRIPTION PLANS (Updated for Revenue Optimization)
# =============================================================================

SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name": "Free Trial",
        "tier": "FREE",
        "duration_days": 0,
        "credits": 10,
        "price_inr": 0,
        "price_usd": 0,
        "monthly_credits": 0,
        "features": [
            "10 trial credits",
            "Basic styles only",
            "Watermarked outputs",
            "Standard queue"
        ],
        "limitations": {
            "premium_styles": False,
            "watermark_free": False,
            "hd_download": False,
            "priority_queue": False,
            "commercial_license": False
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
        "features": [
            "200 credits/month",
            "Basic styles",
            "Watermark removal",
            "Standard queue",
            "Email support"
        ],
        "limitations": {
            "premium_styles": False,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": False,
            "commercial_license": False
        },
        "badge": "STARTER"
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "tier": "PRO",
        "duration_days": 30,
        "credits": 800,
        "price_inr": 1499,
        "price_usd": 17.99,
        "monthly_credits": 800,
        "features": [
            "800 credits/month",
            "🔓 All premium styles",
            "Watermark-free outputs",
            "HD downloads included",
            "Priority support"
        ],
        "limitations": {
            "premium_styles": True,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": False,
            "commercial_license": True
        },
        "badge": "POPULAR",
        "savings": "40%"
    },
    "studio": {
        "id": "studio",
        "name": "Studio",
        "tier": "STUDIO",
        "duration_days": 30,
        "credits": 3000,
        "price_inr": 3999,
        "price_usd": 47.99,
        "monthly_credits": 3000,
        "features": [
            "3000 credits/month",
            "🔓 All premium styles",
            "Watermark-free outputs",
            "HD downloads included",
            "⚡ Priority queue",
            "Commercial license",
            "Dedicated support"
        ],
        "limitations": {
            "premium_styles": True,
            "watermark_free": True,
            "hd_download": True,
            "priority_queue": True,
            "commercial_license": True
        },
        "badge": "BEST VALUE",
        "savings": "50%"
    }
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
        "multiplier": 1.5,  # 50% discount vs 3 singles
        "extra_credits": 5,
        "label": "3 Variations",
        "badge": "SAVE 50%"
    },
    "five": {
        "count": 5,
        "multiplier": 2.0,  # 60% discount vs 5 singles
        "extra_credits": 10,
        "label": "5 Variations",
        "badge": "POPULAR"
    },
    "ten": {
        "count": 10,
        "multiplier": 3.0,  # 70% discount vs 10 singles
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
        "free_for_plans": ["creator", "pro", "studio"]
    },
    "commercial_license": {
        "id": "commercial_license",
        "name": "Commercial License",
        "description": "Use for commercial purposes",
        "credits": 10,
        "icon": "briefcase",
        "available_for": ["comix", "storybook", "gif", "story", "reel"],
        "free_for_plans": ["pro", "studio"]
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
    "trending_badge_threshold": 50,  # Show trending badge for tools with >50 uses/day
    "urgency_messages": [
        "Only {credits} credits left!",
        "Running low on credits",
        "Top up to keep creating",
        "🔥 Limited credits remaining"
    ]
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
    """Calculate cost for batch variations"""
    variation = VARIATION_PRICING.get(variation_type, VARIATION_PRICING["single"])
    return base_cost + variation["extra_credits"]


def is_style_premium(feature: str, style_id: str) -> bool:
    """Check if a style is premium"""
    styles = PREMIUM_STYLES.get(feature, {})
    premium_list = styles.get("premium_styles", [])
    return any(s["id"] == style_id for s in premium_list)


def can_access_style(user_plan: str, feature: str, style_id: str) -> bool:
    """Check if user can access a style based on their plan"""
    if not is_style_premium(feature, style_id):
        return True
    
    plan = SUBSCRIPTION_PLANS.get(user_plan, SUBSCRIPTION_PLANS["free"])
    return plan.get("limitations", {}).get("premium_styles", False)


def get_upsell_cost(upsell_id: str, user_plan: str) -> int:
    """Get upsell cost, considering plan benefits"""
    upsell = UPSELL_OPTIONS.get(upsell_id)
    if not upsell:
        return 0
    
    # Check if free for user's plan
    free_for = upsell.get("free_for_plans", [])
    if user_plan in free_for:
        return 0
    
    return upsell.get("credits", 0)


def get_bundle_cost(feature: str, bundle_id: str) -> int:
    """Get bundle cost"""
    bundles = BUNDLE_PRICING.get(feature, {})
    bundle = bundles.get(bundle_id, {})
    return bundle.get("credits", 0)


def get_all_styles(feature: str) -> List[Dict[str, Any]]:
    """Get all styles for a feature with premium status"""
    styles = PREMIUM_STYLES.get(feature, {})
    all_styles = []
    
    for style in styles.get("free_styles", []):
        all_styles.append({**style, "locked": False})
    
    for style in styles.get("premium_styles", []):
        all_styles.append({**style, "locked": True})
    
    return all_styles
