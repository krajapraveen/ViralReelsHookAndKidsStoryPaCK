"""
Regional Pricing Module
Geo-based pricing for India (INR) and USA (USD)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user

router = APIRouter(prefix="/pricing", tags=["Regional Pricing"])

# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

SUBSCRIPTION_PLANS = {
    "INR": {
        "currency": "INR",
        "symbol": "₹",
        "plans": {
            "weekly": {
                "price": 99,
                "credits": 30,
                "totalActions": 10,
                "features": ["10 total actions/week", "Basic support", "Standard processing"],
                "badge": None
            },
            "monthly": {
                "price": 299,
                "credits": 100,
                "totalActions": 60,
                "features": ["60 total actions/month", "Basic add-ons included", "Email support"],
                "badge": "BEST CONVERSION"
            },
            "quarterly": {
                "price": 699,
                "credits": 350,
                "totalActions": 220,
                "features": ["220 total actions/quarter", "Priority processing", "All add-ons included", "Priority support"],
                "badge": "BEST VALUE",
                "savings": "Save ₹198 vs monthly"
            }
        },
        "topups": [
            {"credits": 30, "price": 149, "popular": False},
            {"credits": 70, "price": 299, "popular": True},
            {"credits": 140, "price": 499, "popular": False}
        ]
    },
    "USD": {
        "currency": "USD",
        "symbol": "$",
        "plans": {
            "weekly": {
                "price": 4.99,
                "credits": 30,
                "totalActions": 10,
                "features": ["10 total actions/week", "Basic support", "Standard processing"],
                "badge": None
            },
            "monthly": {
                "price": 9.99,
                "credits": 100,
                "totalActions": 60,
                "features": ["60 total actions/month", "Basic add-ons included", "Email support"],
                "badge": "MOST POPULAR"
            },
            "quarterly": {
                "price": 24.99,
                "credits": 350,
                "totalActions": 220,
                "features": ["220 total actions/quarter", "Priority processing", "All add-ons included", "Priority support"],
                "badge": "BEST VALUE",
                "savings": "Save $4.98 vs monthly"
            }
        },
        "topups": [
            {"credits": 30, "price": 4.99, "popular": False},
            {"credits": 70, "price": 9.99, "popular": True},
            {"credits": 140, "price": 14.99, "popular": False}
        ]
    }
}

# Credit costs per feature (app-agnostic)
FEATURE_COSTS = {
    # Story Series
    "story_series_3_episodes": 8,
    "story_series_5_episodes": 12,
    "story_series_7_episodes": 18,
    "character_bible": 5,
    
    # Challenge Generator
    "challenge_7_day": 6,
    "challenge_30_day": 15,
    "caption_pack": 3,
    "hashtag_bundle": 2,
    
    # Tone Switcher
    "tone_single": 1,
    "tone_batch_5": 3,
    "tone_batch_10": 5,
    
    # Coloring Book
    "coloring_export_base": 5,
    "coloring_activity_pages": 2,
    "coloring_personalized_cover": 1,
    
    # GenStudio (existing)
    "text_to_image": 10,
    "text_to_video_base": 25,
    "text_to_video_per_second": 5,
    "image_to_video_base": 20,
    "image_to_video_per_second": 4,
    "story_generation": 10,
    "reel_generation": 10
}

# Country to currency mapping
COUNTRY_CURRENCY_MAP = {
    "IN": "INR",
    "US": "USD",
    "GB": "USD",
    "CA": "USD",
    "AU": "USD",
    # Add more countries as needed
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def detect_region_from_request(request: Request) -> str:
    """Detect user's region from request headers"""
    # Check CF-IPCountry header (Cloudflare)
    country = request.headers.get("cf-ipcountry", "").upper()
    
    # Check X-Country header (custom)
    if not country:
        country = request.headers.get("x-country", "").upper()
    
    # Check Accept-Language header as fallback
    if not country:
        accept_lang = request.headers.get("accept-language", "")
        if "hi" in accept_lang.lower():
            country = "IN"
        elif "en-US" in accept_lang or "en-us" in accept_lang:
            country = "US"
    
    # Default to USD
    if not country:
        country = "US"
    
    return COUNTRY_CURRENCY_MAP.get(country, "USD")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/plans")
async def get_pricing_plans(request: Request, currency: Optional[str] = None):
    """Get subscription plans with regional pricing"""
    # Detect or use provided currency
    region_currency = currency or detect_region_from_request(request)
    
    if region_currency not in SUBSCRIPTION_PLANS:
        region_currency = "USD"
    
    pricing_data = SUBSCRIPTION_PLANS[region_currency]
    
    return {
        "currency": pricing_data["currency"],
        "symbol": pricing_data["symbol"],
        "plans": pricing_data["plans"],
        "topups": pricing_data["topups"],
        "detectedRegion": region_currency
    }


@router.get("/topups")
async def get_topup_options(request: Request, currency: Optional[str] = None):
    """Get credit top-up options"""
    region_currency = currency or detect_region_from_request(request)
    
    if region_currency not in SUBSCRIPTION_PLANS:
        region_currency = "USD"
    
    pricing_data = SUBSCRIPTION_PLANS[region_currency]
    
    return {
        "currency": pricing_data["currency"],
        "symbol": pricing_data["symbol"],
        "topups": pricing_data["topups"]
    }


@router.get("/feature-costs")
async def get_feature_costs():
    """Get credit costs for all features"""
    return {
        "costs": FEATURE_COSTS,
        "categories": {
            "Story Series": {
                "3 Episodes Bundle": FEATURE_COSTS["story_series_3_episodes"],
                "5 Episodes Bundle": FEATURE_COSTS["story_series_5_episodes"],
                "7 Episodes Bundle": FEATURE_COSTS["story_series_7_episodes"],
                "Character Bible Add-on": FEATURE_COSTS["character_bible"]
            },
            "Challenge Generator": {
                "7-Day Challenge": FEATURE_COSTS["challenge_7_day"],
                "30-Day Challenge": FEATURE_COSTS["challenge_30_day"],
                "Caption Pack": FEATURE_COSTS["caption_pack"],
                "Hashtag Bundle": FEATURE_COSTS["hashtag_bundle"]
            },
            "Tone Switcher": {
                "Single Rewrite": FEATURE_COSTS["tone_single"],
                "5 Variations Pack": FEATURE_COSTS["tone_batch_5"],
                "10 Variations Pack": FEATURE_COSTS["tone_batch_10"]
            },
            "Coloring Book": {
                "Export (Base)": FEATURE_COSTS["coloring_export_base"],
                "Activity Pages": FEATURE_COSTS["coloring_activity_pages"],
                "Personalized Cover": FEATURE_COSTS["coloring_personalized_cover"]
            },
            "GenStudio": {
                "Text to Image": FEATURE_COSTS["text_to_image"],
                "Text to Video (base)": FEATURE_COSTS["text_to_video_base"],
                "Image to Video (base)": FEATURE_COSTS["image_to_video_base"],
                "Story Generation": FEATURE_COSTS["story_generation"],
                "Reel Generation": FEATURE_COSTS["reel_generation"]
            }
        }
    }


@router.get("/compare")
async def compare_plans(request: Request):
    """Compare subscription plans across regions"""
    return {
        "comparison": {
            region: {
                "currency": data["currency"],
                "symbol": data["symbol"],
                "weekly": data["plans"]["weekly"]["price"],
                "monthly": data["plans"]["monthly"]["price"],
                "quarterly": data["plans"]["quarterly"]["price"]
            }
            for region, data in SUBSCRIPTION_PLANS.items()
        },
        "note": "Prices are region-specific and include all taxes where applicable."
    }


@router.get("/user-region")
async def get_user_region(request: Request):
    """Get detected user region"""
    detected = detect_region_from_request(request)
    
    return {
        "detectedCurrency": detected,
        "symbol": SUBSCRIPTION_PLANS.get(detected, SUBSCRIPTION_PLANS["USD"])["symbol"],
        "isSupported": detected in SUBSCRIPTION_PLANS
    }
