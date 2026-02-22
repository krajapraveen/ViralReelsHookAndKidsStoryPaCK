"""
A/B Testing Framework for Pricing and Features
Enables controlled experiments with different pricing, UI variants, and features
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_current_user, get_admin_user

router = APIRouter(prefix="/experiments", tags=["A/B Testing"])


# Experiment Configuration
EXPERIMENTS = {
    "pricing_v2": {
        "name": "Pricing Page V2",
        "description": "Test new pricing structure with emphasis on quarterly plan",
        "variants": {
            "control": {
                "name": "Original Pricing",
                "weight": 50,
                "config": {
                    "plans": [
                        {"id": "weekly", "name": "Weekly", "price": 199, "credits": 50, "highlight": False},
                        {"id": "monthly", "name": "Monthly", "price": 699, "credits": 200, "highlight": True},
                        {"id": "quarterly", "name": "Quarterly", "price": 1999, "credits": 500, "highlight": False},
                        {"id": "yearly", "name": "Yearly", "price": 5999, "credits": 2500, "highlight": False},
                    ],
                    "show_savings": True,
                    "cta_text": "Get Started"
                }
            },
            "treatment": {
                "name": "Quarterly Focus",
                "weight": 50,
                "config": {
                    "plans": [
                        {"id": "weekly", "name": "Weekly", "price": 199, "credits": 50, "highlight": False},
                        {"id": "monthly", "name": "Monthly", "price": 699, "credits": 200, "highlight": False},
                        {"id": "quarterly", "name": "Quarterly", "price": 1799, "credits": 600, "highlight": True, "badge": "BEST VALUE"},
                        {"id": "yearly", "name": "Yearly", "price": 4999, "credits": 3000, "highlight": False, "badge": "50% OFF"},
                    ],
                    "show_savings": True,
                    "show_comparison": True,
                    "cta_text": "Start Saving Now"
                }
            }
        },
        "metrics": ["conversion_rate", "avg_order_value", "plan_distribution"],
        "status": "active",
        "start_date": "2026-02-01",
        "end_date": "2026-03-01"
    },
    "dashboard_layout": {
        "name": "Dashboard Layout Test",
        "description": "Test compact vs expanded dashboard layout",
        "variants": {
            "control": {
                "name": "Current Layout",
                "weight": 50,
                "config": {
                    "layout": "grid",
                    "cards_per_row": 4,
                    "show_quick_actions": True
                }
            },
            "treatment": {
                "name": "Compact Layout",
                "weight": 50,
                "config": {
                    "layout": "compact",
                    "cards_per_row": 6,
                    "show_quick_actions": False,
                    "show_recent_first": True
                }
            }
        },
        "metrics": ["engagement", "feature_usage", "session_duration"],
        "status": "paused"
    },
    "onboarding_flow": {
        "name": "Onboarding Flow Test",
        "description": "Test guided vs self-serve onboarding",
        "variants": {
            "control": {
                "name": "Self-Serve",
                "weight": 50,
                "config": {
                    "show_tutorial": False,
                    "show_tips": True,
                    "free_credits": 100
                }
            },
            "treatment": {
                "name": "Guided Tour",
                "weight": 50,
                "config": {
                    "show_tutorial": True,
                    "tutorial_steps": 5,
                    "show_tips": True,
                    "free_credits": 50,
                    "bonus_on_completion": 75
                }
            }
        },
        "metrics": ["activation_rate", "first_generation", "retention_d7"],
        "status": "draft"
    }
}


def get_user_bucket(user_id: str, experiment_id: str) -> str:
    """Deterministically assign user to a variant based on user_id"""
    # Create a hash from user_id + experiment_id for consistent assignment
    hash_input = f"{user_id}:{experiment_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    
    experiment = EXPERIMENTS.get(experiment_id, {})
    variants = experiment.get("variants", {})
    
    if not variants:
        return "control"
    
    # Calculate cumulative weights
    total_weight = sum(v.get("weight", 0) for v in variants.values())
    bucket = hash_value % total_weight
    
    cumulative = 0
    for variant_id, variant in variants.items():
        cumulative += variant.get("weight", 0)
        if bucket < cumulative:
            return variant_id
    
    return "control"


class ExperimentEvent(BaseModel):
    experiment_id: str
    event_type: str = Field(..., description="view, click, convert, etc.")
    metadata: Optional[dict] = {}


@router.get("/active")
async def get_active_experiments(user: dict = Depends(get_current_user)):
    """Get active experiments and user's assigned variants"""
    user_id = user["id"]
    
    active_experiments = {}
    
    for exp_id, experiment in EXPERIMENTS.items():
        if experiment.get("status") == "active":
            variant_id = get_user_bucket(user_id, exp_id)
            variant = experiment["variants"].get(variant_id, {})
            
            active_experiments[exp_id] = {
                "name": experiment["name"],
                "variant": variant_id,
                "config": variant.get("config", {})
            }
    
    return {
        "experiments": active_experiments,
        "user_id": user_id
    }


@router.get("/{experiment_id}")
async def get_experiment_config(experiment_id: str, user: dict = Depends(get_current_user)):
    """Get specific experiment configuration for user"""
    experiment = EXPERIMENTS.get(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    if experiment.get("status") != "active":
        # Return control variant for inactive experiments
        variant_id = "control"
    else:
        variant_id = get_user_bucket(user["id"], experiment_id)
    
    variant = experiment["variants"].get(variant_id, {})
    
    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment["name"],
        "variant": variant_id,
        "variant_name": variant.get("name", ""),
        "config": variant.get("config", {})
    }


@router.post("/track")
async def track_experiment_event(event: ExperimentEvent, user: dict = Depends(get_current_user)):
    """Track an experiment event"""
    experiment = EXPERIMENTS.get(event.experiment_id)
    
    if not experiment:
        return {"success": False, "message": "Experiment not found"}
    
    variant_id = get_user_bucket(user["id"], event.experiment_id)
    
    # Store event
    await db.experiment_events.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user["id"],
        "experimentId": event.experiment_id,
        "variant": variant_id,
        "eventType": event.event_type,
        "metadata": event.metadata,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True}


# Admin Endpoints

@router.get("/admin/list")
async def list_all_experiments(admin: dict = Depends(get_admin_user)):
    """List all experiments with status"""
    experiments_list = []
    
    for exp_id, experiment in EXPERIMENTS.items():
        experiments_list.append({
            "id": exp_id,
            "name": experiment["name"],
            "description": experiment["description"],
            "status": experiment.get("status", "draft"),
            "variants": list(experiment["variants"].keys()),
            "metrics": experiment.get("metrics", [])
        })
    
    return {"experiments": experiments_list}


@router.get("/admin/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    days: int = 30,
    admin: dict = Depends(get_admin_user)
):
    """Get experiment results and metrics"""
    experiment = EXPERIMENTS.get(experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get events grouped by variant
    pipeline = [
        {"$match": {
            "experimentId": experiment_id,
            "timestamp": {"$gte": start_date.isoformat()}
        }},
        {"$group": {
            "_id": {
                "variant": "$variant",
                "eventType": "$eventType"
            },
            "count": {"$sum": 1},
            "uniqueUsers": {"$addToSet": "$userId"}
        }}
    ]
    
    results = await db.experiment_events.aggregate(pipeline).to_list(100)
    
    # Process results
    variant_stats = {}
    for variant_id in experiment["variants"].keys():
        variant_stats[variant_id] = {
            "views": 0,
            "clicks": 0,
            "conversions": 0,
            "unique_users": set()
        }
    
    for result in results:
        variant = result["_id"]["variant"]
        event_type = result["_id"]["eventType"]
        
        if variant in variant_stats:
            if event_type == "view":
                variant_stats[variant]["views"] = result["count"]
            elif event_type == "click":
                variant_stats[variant]["clicks"] = result["count"]
            elif event_type == "convert":
                variant_stats[variant]["conversions"] = result["count"]
            
            variant_stats[variant]["unique_users"].update(result["uniqueUsers"])
    
    # Calculate conversion rates
    final_stats = {}
    for variant_id, stats in variant_stats.items():
        views = stats["views"] or 1
        final_stats[variant_id] = {
            "views": stats["views"],
            "clicks": stats["clicks"],
            "conversions": stats["conversions"],
            "unique_users": len(stats["unique_users"]),
            "click_rate": round((stats["clicks"] / views) * 100, 2),
            "conversion_rate": round((stats["conversions"] / views) * 100, 2)
        }
    
    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment["name"],
        "period_days": days,
        "variant_results": final_stats,
        "status": experiment.get("status", "unknown")
    }


@router.post("/admin/{experiment_id}/status")
async def update_experiment_status(
    experiment_id: str,
    status: str,
    admin: dict = Depends(get_admin_user)
):
    """Update experiment status (active, paused, ended)"""
    if experiment_id not in EXPERIMENTS:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    valid_statuses = ["draft", "active", "paused", "ended"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    # In production, this would update a database
    # For now, we log the change
    await db.experiment_changes.insert_one({
        "id": str(uuid.uuid4()),
        "experimentId": experiment_id,
        "previousStatus": EXPERIMENTS[experiment_id].get("status"),
        "newStatus": status,
        "changedBy": admin["id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "experiment_id": experiment_id,
        "new_status": status,
        "note": "Status change logged. Restart required to apply changes in demo mode."
    }
