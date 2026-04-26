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


def assign_variant_weighted(session_id: str, experiment_id: str, variants: list, weights: dict) -> int:
    """
    Deterministic weighted assignment.
    `weights` is {variant_id: float} (sum should be ~1.0). Falls back to uniform when missing.
    Same (session_id, experiment_id) always returns the same variant index.
    """
    if not weights:
        return assign_variant(session_id, experiment_id, len(variants))
    total = sum(max(0.0, float(weights.get(v["id"], 0.0))) for v in variants)
    if total <= 0:
        return assign_variant(session_id, experiment_id, len(variants))
    # Hash → bucket in [0, 1)
    key = f"{session_id}:{experiment_id}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    bucket = (h % 10_000) / 10_000.0  # 4 decimal precision
    cumulative = 0.0
    for idx, v in enumerate(variants):
        w = max(0.0, float(weights.get(v["id"], 0.0))) / total
        cumulative += w
        if bucket < cumulative:
            return idx
    return len(variants) - 1


# ─── POST /api/ab/assign ─────────────────────────────────────────────────────

@router.post("/assign")
async def ab_assign(data: AssignRequest):
    """Assign a variant to a session for an experiment. Deterministic and idempotent."""
    exp = await db.ab_experiments.find_one({"experiment_id": data.experiment_id, "active": True}, {"_id": 0})
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found or inactive")

    variants = exp["variants"]
    weights = exp.get("traffic_weights") or {}
    if weights:
        idx = assign_variant_weighted(data.session_id, data.experiment_id, variants, weights)
    else:
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
        weights = exp.get("traffic_weights") or {}
        if weights:
            idx = assign_variant_weighted(session_id, exp["experiment_id"], variants, weights)
        else:
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


# ─── GET /api/ab/segmentation ────────────────────────────────────────────────

MIN_SOURCE_SAMPLE = 100  # Minimum impressions per source/variant before declaring results reliable

@router.get("/segmentation")
async def ab_segmentation(experiment_id: str = Query("hero_headline")):
    """Traffic source segmentation for an A/B experiment.
    Shows per-source breakdown with impressions, CTR, confidence, and winner."""
    exp = await db.ab_experiments.find_one(
        {"experiment_id": experiment_id, "active": True}, {"_id": 0}
    )
    if not exp:
        return {"success": True, "sources": [], "message": "Experiment not found or inactive"}

    variant_ids = [v["id"] for v in exp["variants"]]
    variant_labels = {v["id"]: v.get("label", v["id"]) for v in exp["variants"]}

    # Get all distinct traffic sources
    sources_raw = await db.ab_events.distinct("traffic_source", {"experiment_id": experiment_id})
    sources = sorted([s for s in sources_raw if s], key=lambda s: s)

    source_data = []
    for source in sources:
        rows = []
        for vid in variant_ids:
            # Count impressions for this source+variant
            impressions = await db.ab_events.count_documents({
                "experiment_id": experiment_id,
                "traffic_source": source,
                "variant": vid,
                "action": "impression",
            })
            # Count clicks (cta_click action)
            clicks = await db.ab_events.count_documents({
                "experiment_id": experiment_id,
                "traffic_source": source,
                "variant": vid,
                "action": "cta_click",
            })
            ctr = round(clicks / impressions * 100, 2) if impressions > 0 else 0
            rows.append({
                "variant_id": vid,
                "label": variant_labels.get(vid, vid),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
            })

        total_impressions = sum(r["impressions"] for r in rows)
        sufficient = all(r["impressions"] >= MIN_SOURCE_SAMPLE for r in rows)

        # Confidence for this source
        if len(rows) == 2 and sufficient:
            conf = _calc_confidence([
                {"sessions": rows[0]["impressions"], "clicks": rows[0]["clicks"]},
                {"sessions": rows[1]["impressions"], "clicks": rows[1]["clicks"]},
            ])
        else:
            conf = 0

        # Winner for this source
        winner = None
        if sufficient and conf >= 95:
            best = max(rows, key=lambda r: r["ctr"])
            winner = best["variant_id"]

        source_data.append({
            "source": source,
            "total_impressions": total_impressions,
            "variants": rows,
            "sufficient_data": sufficient,
            "confidence": conf,
            "winner": winner,
        })

    # Sort by total traffic volume (highest first)
    source_data.sort(key=lambda s: s["total_impressions"], reverse=True)

    return {
        "success": True,
        "experiment_id": experiment_id,
        "min_source_sample": MIN_SOURCE_SAMPLE,
        "sources": source_data,
    }


# ─── GET /api/ab/smart-route ─────────────────────────────────────────────────

@router.get("/smart-route")
async def smart_headline_route(
    experiment_id: str = Query("hero_headline"),
    traffic_source: str = Query("direct"),
):
    """Smart Headline Router — returns the best variant for a given traffic source.
    Falls back to control variant if confidence is insufficient."""
    exp = await db.ab_experiments.find_one(
        {"experiment_id": experiment_id, "active": True}, {"_id": 0}
    )
    if not exp:
        return {"variant_id": None, "reason": "no_experiment"}

    control_id = next((v["id"] for v in exp["variants"] if v.get("is_control")), exp["variants"][0]["id"])
    weights = exp.get("traffic_weights") or {}

    # When traffic_weights are configured, the weighted variant beats the bare
    # control for the "no confident winner" fallback. This honors the founder's
    # 90/10 directive without abandoning the experiment.
    weighted_fallback = None
    if weights:
        weighted_fallback = max(weights.items(), key=lambda kv: kv[1])[0]

    # Check source-specific data
    variant_ids = [v["id"] for v in exp["variants"]]
    rows = []
    for vid in variant_ids:
        impressions = await db.ab_events.count_documents({
            "experiment_id": experiment_id,
            "traffic_source": traffic_source,
            "variant": vid,
            "action": "impression",
        })
        clicks = await db.ab_events.count_documents({
            "experiment_id": experiment_id,
            "traffic_source": traffic_source,
            "variant": vid,
            "action": "cta_click",
        })
        rows.append({"variant_id": vid, "sessions": impressions, "clicks": clicks})

    sufficient = all(r["sessions"] >= MIN_SOURCE_SAMPLE for r in rows)

    if not sufficient or len(rows) != 2:
        return {
            "variant_id": weighted_fallback or control_id,
            "reason": "weighted_rollout" if weighted_fallback else "insufficient_data",
            "source": traffic_source,
            "data_available": sum(r["sessions"] for r in rows),
        }

    conf = _calc_confidence(rows)
    if conf < 95:
        return {
            "variant_id": weighted_fallback or control_id,
            "reason": "weighted_rollout" if weighted_fallback else "low_confidence",
            "confidence": conf,
            "source": traffic_source,
        }

    # Confident winner for this source
    best = max(rows, key=lambda r: r["clicks"] / r["sessions"] if r["sessions"] > 0 else 0)
    return {
        "variant_id": best["variant_id"],
        "reason": "source_winner",
        "confidence": conf,
        "source": traffic_source,
    }


# ─── SEED EXPERIMENTS ────────────────────────────────────────────────────────

INITIAL_EXPERIMENTS = [
    {
        "experiment_id": "hero_headline",
        "name": "Hero Headline — Round 2 (A vs B vs C)",
        "primary_event": "experience_click",
        "secondary_event": "paywall_shown",
        "active": True,
        "min_sessions": 500,
        # 🎯 P0 Apr 2026 — 90/10 winner rollout. headline_b leads at 16.2% conversion.
        # Assignment honors these weights deterministically; smart-route source-winner
        # logic still overrides for confident source-specific winners.
        "traffic_weights": {
            "headline_b": 0.90,
            "headline_a": 0.05,
            "headline_c": 0.05,
        },
        "variants": [
            {
                "id": "headline_a",
                "label": "Direct Value (Control)",
                "is_control": True,
                "data": {
                    "heading": ["Turn Any Story Into a", "Stunning AI Video"],
                    "badge": "No editing. No experience needed.",
                    "subtitle": "Type a sentence. AI creates scenes, voiceover, and music. Download or share instantly.",
                    "cta": "Create Free Video Now",
                },
            },
            {
                "id": "headline_b",
                "label": "Zero Friction (Challenger 1)",
                "is_control": False,
                "data": {
                    "heading": ["Create Viral AI Videos", "in 60 Seconds"],
                    "badge": "Free first video — no signup needed",
                    "subtitle": "Kids stories, reels, and animations — just type your idea. AI does everything else.",
                    "cta": "Try It Free — No Signup",
                },
            },
            {
                "id": "headline_c",
                "label": "Social Proof (Challenger 2)",
                "is_control": False,
                "data": {
                    "heading": ["Kids Stories, Reels &", "Viral Videos — Instantly"],
                    "badge": "Used by 800+ creators this month",
                    "subtitle": "Type one sentence. Get a complete video with scenes, voice, and music. Share anywhere.",
                    "cta": "Make My First Video",
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
    """Seed or update initial experiments. Updates existing experiments with latest variant configs."""
    seeded = []
    updated = []
    for exp in INITIAL_EXPERIMENTS:
        existing = await db.ab_experiments.find_one({"experiment_id": exp["experiment_id"]})
        if not existing:
            await db.ab_experiments.insert_one(exp)
            seeded.append(exp["experiment_id"])
        else:
            # Update variants if changed (e.g., adding variant C)
            existing_variant_ids = {v["id"] for v in existing.get("variants", [])}
            new_variant_ids = {v["id"] for v in exp.get("variants", [])}
            if existing_variant_ids != new_variant_ids:
                await db.ab_experiments.update_one(
                    {"experiment_id": exp["experiment_id"]},
                    {"$set": {"variants": exp["variants"], "name": exp["name"]}}
                )
                updated.append(exp["experiment_id"])
    return {"seeded": seeded, "updated": updated, "total_experiments": len(INITIAL_EXPERIMENTS)}


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
