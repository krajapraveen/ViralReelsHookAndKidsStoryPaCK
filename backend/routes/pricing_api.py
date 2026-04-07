"""
Pricing API — Exposes pricing config for the Smart Paywall UI.
Frontend fetches plans from here instead of hardcoding.
"""
from fastapi import APIRouter
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.pricing import SUBSCRIPTION_PLANS, TOPUP_PACKS

router = APIRouter(prefix="/pricing-catalog", tags=["Pricing"])


@router.get("/plans")
async def get_plans():
    """Return all subscription plans and top-up packs from the single source of truth."""
    plans = []
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        plans.append({
            "id": plan["id"],
            "name": plan["name"],
            "period": plan["period"],
            "duration_days": plan["duration_days"],
            "price_inr": plan["price_inr"],
            "credits": plan["credits"],
            "features": plan["features"],
            "badge": plan.get("badge"),
        })

    topups = []
    for pack_id, pack in TOPUP_PACKS.items():
        topups.append({
            "id": pack["id"],
            "name": pack["name"],
            "credits": pack["credits"],
            "price_inr": pack["price_inr"],
            "popular": pack.get("popular", False),
        })

    return {
        "success": True,
        "plans": plans,
        "topups": topups,
    }
