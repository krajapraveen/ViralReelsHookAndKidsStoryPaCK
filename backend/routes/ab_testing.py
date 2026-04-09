"""
Lean A/B Testing — Assign, Convert, Results
Deterministic session-based variant assignment. No statistical theater.
Winner heuristic: 20%+ uplift after ~200 sessions per variant.
"""

import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from shared import db

logger = logging.getLogger("ab_testing")
router = APIRouter(prefix="/ab", tags=["ab-testing"])

# ─── MODELS ──────────────────────────────────────────────────────────────────

class AssignRequest(BaseModel):
    session_id: str
    experiment_id: str

class ConvertRequest(BaseModel):
    session_id: str
    experiment_id: str
    event: str  # remix_click, generate_click, signup_completed

VALID_CONVERSION_EVENTS = {"remix_click", "generate_click", "signup_completed", "share_click", "impression", "continue_click", "click", "experience_click", "paywall_shown"}

# ─── DETERMINISTIC ASSIGNMENT ────────────────────────────────────────────────

def assign_variant(session_id: str, experiment_id: str, num_variants: int) -> int:
    """Hash session_id + experiment_id to deterministically pick a variant index."""
    key = f"{session_id}:{experiment_id}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return h % num_variants


# ─── POST /api/ab/assign ─────────────────────────────────────────────────────

@router.post("/assign")
async def ab_assign(data: AssignRequest):
    """Assign a variant to a session for an experiment. Deterministic and idempotent."""
    exp = await db.ab_experiments.find_one({"experiment_id": data.experiment_id, "active": True}, {"_id": 0})
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found or inactive")

    variants = exp["variants"]
    idx = assign_variant(data.session_id, data.experiment_id, len(variants))
    variant = variants[idx]

    # Upsert assignment (idempotent)
    await db.ab_assignments.update_one(
        {"session_id": data.session_id, "experiment_id": data.experiment_id},
        {"$setOnInsert": {
            "session_id": data.session_id,
            "experiment_id": data.experiment_id,
            "variant_id": variant["id"],
            "variant_idx": idx,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    return {
        "experiment_id": data.experiment_id,
        "variant_id": variant["id"],
        "variant_idx": idx,
        "variant_data": variant.get("data", {}),
    }


# ─── POST /api/ab/assign-all ─────────────────────────────────────────────────

@router.post("/assign-all")
async def ab_assign_all(data: dict):
    """Assign variants for ALL active experiments at once. Returns map of experiment_id -> variant."""
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    experiments = []
    async for exp in db.ab_experiments.find({"active": True}, {"_id": 0}):
        experiments.append(exp)

    results = {}
    for exp in experiments:
        variants = exp["variants"]
        idx = assign_variant(session_id, exp["experiment_id"], len(variants))
        variant = variants[idx]

        await db.ab_assignments.update_one(
            {"session_id": session_id, "experiment_id": exp["experiment_id"]},
            {"$setOnInsert": {
                "session_id": session_id,
                "experiment_id": exp["experiment_id"],
                "variant_id": variant["id"],
                "variant_idx": idx,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

        results[exp["experiment_id"]] = {
            "variant_id": variant["id"],
            "variant_idx": idx,
            "variant_data": variant.get("data", {}),
        }

    return {"session_id": session_id, "assignments": results}


# ─── POST /api/ab/convert ────────────────────────────────────────────────────

@router.post("/convert")
async def ab_convert(data: ConvertRequest):
    """Track a conversion event for a session's assigned variant."""
    if data.event not in VALID_CONVERSION_EVENTS:
        raise HTTPException(status_code=400, detail=f"Invalid event: {data.event}")

    # Find the assignment
    assignment = await db.ab_assignments.find_one(
        {"session_id": data.session_id, "experiment_id": data.experiment_id},
        {"_id": 0},
    )
    if not assignment:
        return {"success": False, "reason": "no_assignment"}

    # Dedupe: one conversion per session per experiment per event
    existing = await db.ab_conversions.find_one({
        "session_id": data.session_id,
        "experiment_id": data.experiment_id,
        "event": data.event,
    })
    if existing:
        return {"success": True, "dedupe": True}

    await db.ab_conversions.insert_one({
        "session_id": data.session_id,
        "experiment_id": data.experiment_id,
        "variant_id": assignment["variant_id"],
        "event": data.event,
        "converted_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"success": True}


# ─── GET /api/ab/results ─────────────────────────────────────────────────────

@router.get("/results")
async def ab_results(experiment_id: Optional[str] = Query(None)):
    """Get results for one or all experiments. Statistical confidence + winner heuristic."""
    query = {}
    if experiment_id:
        query["experiment_id"] = experiment_id

    experiments = []
    async for exp in db.ab_experiments.find(query, {"_id": 0}):
        experiments.append(exp)

    results = []
    for exp in experiments:
        eid = exp["experiment_id"]
        min_sessions = exp.get("min_sessions", 500)
        variant_results = []

        for variant in exp["variants"]:
            vid = variant["id"]
            sessions = await db.ab_assignments.count_documents({"experiment_id": eid, "variant_id": vid})

            conversions = {}
            for event in VALID_CONVERSION_EVENTS | {"experience_click", "paywall_shown"}:
                count = await db.ab_conversions.count_documents({
                    "experiment_id": eid,
                    "variant_id": vid,
                    "event": event,
                })
                conversions[event] = count

            primary_event = exp.get("primary_event", "experience_click")
            secondary_event = exp.get("secondary_event", "paywall_shown")
            primary_conversions = conversions.get(primary_event, 0)
            secondary_conversions = conversions.get(secondary_event, 0)
            ctr = round(primary_conversions / sessions * 100, 2) if sessions > 0 else 0
            paywall_rate = round(secondary_conversions / sessions * 100, 2) if sessions > 0 else 0

            variant_results.append({
                "variant_id": vid,
                "label": variant.get("label", vid),
                "is_control": variant.get("is_control", False),
                "sessions": sessions,
                "impressions": sessions,
                "clicks": primary_conversions,
                "ctr": ctr,
                "paywall_conversions": secondary_conversions,
                "paywall_rate": paywall_rate,
                "conversions": conversions,
            })

        # Statistical confidence via z-test for proportions
        confidence = _calc_confidence(variant_results) if len(variant_results) == 2 else 0

        # Winner heuristic: min_sessions per variant + 95% confidence
        winner = None
        if all(v["sessions"] >= min_sessions for v in variant_results) and confidence >= 95:
            best = max(variant_results, key=lambda v: v["ctr"])
            winner = best["variant_id"]

        results.append({
            "experiment_id": eid,
            "name": exp.get("name", eid),
            "primary_event": exp.get("primary_event", "experience_click"),
            "secondary_event": exp.get("secondary_event", ""),
            "active": exp.get("active", True),
            "variants": variant_results,
            "tentative_winner": winner,
            "confidence": confidence,
            "min_sessions_per_variant": min_sessions,
        })

    return {"success": True, "experiments": results}


def _calc_confidence(variant_results):
    """Z-test for two proportions. Returns confidence percentage (0-99.9)."""
    import math
    if len(variant_results) != 2:
        return 0
    n1, c1 = variant_results[0]["sessions"], variant_results[0]["clicks"]
    n2, c2 = variant_results[1]["sessions"], variant_results[1]["clicks"]
    if n1 < 30 or n2 < 30:
        return 0
    p1 = c1 / n1 if n1 > 0 else 0
    p2 = c2 / n2 if n2 > 0 else 0
    p_pool = (c1 + c2) / (n1 + n2) if (n1 + n2) > 0 else 0
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2)) if p_pool > 0 and p_pool < 1 else 0
    if se == 0:
        return 0
    z = abs(p1 - p2) / se
    # Approximate confidence from z-score
    if z >= 2.576:
        return 99
    elif z >= 1.96:
        return 95
    elif z >= 1.645:
        return 90
    elif z >= 1.28:
        return 80
    elif z >= 1.0:
        return 68
    else:
        return round(min(z / 1.96 * 95, 60), 1)


# ─── SEED EXPERIMENTS ────────────────────────────────────────────────────────

INITIAL_EXPERIMENTS = [
    {
        "experiment_id": "hero_headline",
        "name": "Hero Headline — Week 1 (A vs B)",
        "primary_event": "experience_click",
        "secondary_event": "paywall_shown",
        "active": True,
        "min_sessions": 500,
        "variants": [
            {
                "id": "headline_a",
                "label": "Emotional (Control)",
                "is_control": True,
                "data": {
                    "heading": ["Create stories kids will", "remember forever"],
                    "badge": "Stories that stay with them",
                    "subtitle": "Create cinematic videos, reels, and stories with AI — no editing, no experience needed. Free to start.",
                },
            },
            {
                "id": "headline_b",
                "label": "Prestige (Challenger)",
                "is_control": False,
                "data": {
                    "heading": ["Create award-worthy", "AI stories in minutes"],
                    "badge": "No editing. No experience needed.",
                    "subtitle": "Type a sentence. AI creates scenes, voiceover, and music. Download or share instantly.",
                },
            },
        ],
    },
    {
        "experiment_id": "cta_copy",
        "name": "CTA Copy Test",
        "primary_event": "remix_click",
        "active": True,
        "variants": [
            {"id": "cta_a", "label": "Create This in 1 Click", "data": {"cta_text": "Create This in 1 Click"}},
            {"id": "cta_b", "label": "Make Your Own Now", "data": {"cta_text": "Make Your Own Now"}},
            {"id": "cta_c", "label": "Generate This in Seconds", "data": {"cta_text": "Generate This in Seconds"}},
        ],
    },
    {
        "experiment_id": "hook_text",
        "name": "Hook Text Test",
        "primary_event": "remix_click",
        "active": True,
        "variants": [
            {"id": "hook_a", "label": "Made in 30 seconds", "data": {"hook_text": "Made in 30 seconds. No skills needed."}},
            {"id": "hook_b", "label": "Created with AI", "data": {"hook_text": "This video was created with AI \u2014 try it yourself."}},
            {"id": "hook_c", "label": "Anyone can make this", "data": {"hook_text": "Anyone can make this. Click and see."}},
        ],
    },
    {
        "experiment_id": "login_timing",
        "name": "Login Gate Timing",
        "primary_event": "signup_completed",
        "active": True,
        "variants": [
            {"id": "gate_before", "label": "Before Generate", "data": {"gate_timing": "before_generate"}},
            {"id": "gate_after", "label": "After Generate", "data": {"gate_timing": "after_generate"}},
            {"id": "gate_preview", "label": "After Preview", "data": {"gate_timing": "after_preview"}},
        ],
    },
    {
        "experiment_id": "cta_placement",
        "name": "CTA Placement Test",
        "primary_event": "generate_click",
        "active": True,
        "variants": [
            {"id": "cta_top", "label": "Top of Card", "data": {"cta_position": "top"}},
            {"id": "cta_bottom", "label": "Bottom of Card", "data": {"cta_position": "bottom"}},
            {"id": "cta_floating", "label": "Floating Sticky", "data": {"cta_position": "floating"}},
        ],
    },
    {
        "experiment_id": "story_hook",
        "name": "Story Hook Style",
        "primary_event": "continue_click",
        "active": True,
        "variants": [
            {
                "id": "hook_mystery",
                "label": "Mystery",
                "data": {
                    "style": "mystery",
                    "section_label": "The Cliffhanger",
                    "hook_suffix": "Something is hiding just beyond what you can see\u2026",
                    "cta_text": "Uncover What\u2019s Hidden",
                    "urgency": "This mystery won\u2019t solve itself",
                    "accent": "amber",
                },
            },
            {
                "id": "hook_emotional",
                "label": "Emotional",
                "data": {
                    "style": "emotional",
                    "section_label": "Where the heart breaks\u2026",
                    "hook_suffix": "Some stories need someone brave enough to finish them\u2026",
                    "cta_text": "Feel What Happens Next",
                    "urgency": "This story needs you",
                    "accent": "rose",
                },
            },
            {
                "id": "hook_shock",
                "label": "Shock",
                "data": {
                    "style": "shock",
                    "section_label": "Plot Twist Incoming",
                    "hook_suffix": "Everything changes after this moment\u2026",
                    "cta_text": "You Won\u2019t Believe What Happens",
                    "urgency": "No one saw this coming",
                    "accent": "red",
                },
            },
            {
                "id": "hook_curiosity",
                "label": "Curiosity",
                "data": {
                    "style": "curiosity",
                    "section_label": "Wait\u2026 there\u2019s more",
                    "hook_suffix": "Only one way to find out\u2026",
                    "cta_text": "What Happens Next?",
                    "urgency": "The next part changes everything",
                    "accent": "cyan",
                },
            },
        ],
    },
]


@router.post("/seed")
async def seed_experiments():
    """Seed initial experiments. Idempotent — skips existing."""
    seeded = []
    for exp in INITIAL_EXPERIMENTS:
        existing = await db.ab_experiments.find_one({"experiment_id": exp["experiment_id"]})
        if not existing:
            await db.ab_experiments.insert_one(exp)
            seeded.append(exp["experiment_id"])
    return {"seeded": seeded, "total_experiments": len(INITIAL_EXPERIMENTS)}


# ─── HOOK ANALYTICS (Admin) ──────────────────────────────────────────────────

HOOK_EVENTS = ["impression", "click", "continue_click", "share_click"]
MIN_SAMPLE = 50  # Minimum impressions before showing rates


@router.get("/hook-analytics")
async def hook_analytics():
    """
    Detailed analytics for the story_hook experiment.
    Returns per-variant: impressions, clicks, CTR, continues, continue rate,
    shares, share rate, and a confidence warning when sample is too small.
    """
    exp = await db.ab_experiments.find_one(
        {"experiment_id": "story_hook", "active": True}, {"_id": 0}
    )
    if not exp:
        return {"success": True, "experiment": None, "message": "story_hook experiment not found or inactive"}

    variants_data = []
    for variant in exp["variants"]:
        vid = variant["id"]

        # Count assignments (impressions proxy) and each event type
        sessions = await db.ab_assignments.count_documents(
            {"experiment_id": "story_hook", "variant_id": vid}
        )
        counts = {}
        for evt in HOOK_EVENTS:
            counts[evt] = await db.ab_conversions.count_documents(
                {"experiment_id": "story_hook", "variant_id": vid, "event": evt}
            )

        impressions = counts.get("impression", 0)
        clicks = counts.get("click", 0)
        continues = counts.get("continue_click", 0)
        shares = counts.get("share_click", 0)

        sufficient = impressions >= MIN_SAMPLE

        variants_data.append({
            "variant_id": vid,
            "label": variant.get("label", vid),
            "style": variant.get("data", {}).get("style", ""),
            "sessions": sessions,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            "continues": continues,
            "continue_rate": round(continues / impressions * 100, 2) if impressions > 0 else 0,
            "shares": shares,
            "share_rate": round(shares / impressions * 100, 2) if impressions > 0 else 0,
            "sufficient_data": sufficient,
            "data_warning": None if sufficient else f"Need {MIN_SAMPLE - impressions} more impressions for reliable rates",
        })

    # Rank by continue_rate (primary metric) when data is sufficient
    ranked = sorted(variants_data, key=lambda v: v["continue_rate"] if v["sufficient_data"] else -1, reverse=True)

    return {
        "success": True,
        "experiment_id": "story_hook",
        "name": exp.get("name", "Story Hook Style"),
        "min_sample_size": MIN_SAMPLE,
        "variants": ranked,
        "top_performer": ranked[0]["variant_id"] if ranked and ranked[0]["sufficient_data"] else None,
        "bottom_performer": ranked[-1]["variant_id"] if ranked and ranked[-1]["sufficient_data"] else None,
    }
