"""
CreatorStudio AI - Auto-Scaling & Priority Lanes API Routes
============================================================
Admin endpoints for managing auto-scaling rules and priority lanes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, logger, get_admin_user, get_current_user
from services.priority_scaling_service import (
    priority_lane_manager,
    auto_scaling_engine,
    UserTier,
    TIER_CONFIG
)

router = APIRouter(prefix="/scaling", tags=["Auto-Scaling & Priority"])


# ============================================
# REQUEST MODELS
# ============================================

class ManualScaleRequest(BaseModel):
    target_workers: int = Field(..., ge=1, le=50, description="Target number of workers")
    reason: str = Field(default="manual", description="Reason for manual scaling")

class UpdateConfigRequest(BaseModel):
    min_workers: Optional[int] = Field(None, ge=1, le=20)
    max_workers: Optional[int] = Field(None, ge=1, le=50)

class ScalingRuleRequest(BaseModel):
    name: str
    metric: str = Field(..., description="queue_depth, error_rate, latency_p95, premium_queue_depth")
    operator: str = Field(..., description="gt, lt, gte, lte")
    threshold: float
    action: str = Field(..., description="scale_up or scale_down")
    scale_amount: int = Field(default=1, ge=1, le=10)
    cooldown_seconds: int = Field(default=60, ge=10, le=600)
    sustained_seconds: int = Field(default=30, ge=10, le=300)
    enabled: bool = Field(default=True)


# ============================================
# AUTO-SCALING ENDPOINTS
# ============================================

@router.get("/status")
async def get_scaling_status(current_user: dict = Depends(get_admin_user)):
    """
    Get current auto-scaling status including workers, metrics, and rules
    """
    status = auto_scaling_engine.get_status()
    
    # Add queue metrics
    pending_jobs = await db.jobs.count_documents({"state": "pending"})
    processing_jobs = await db.jobs.count_documents({"state": "in_progress"})
    
    status["queue_stats"] = {
        "pending": pending_jobs,
        "processing": processing_jobs,
        "total_active": pending_jobs + processing_jobs
    }
    
    return status


@router.post("/manual")
async def manual_scale(
    request: ManualScaleRequest,
    current_user: dict = Depends(get_admin_user)
):
    """
    Manually scale workers to a specific count
    """
    result = await auto_scaling_engine.manual_scale(
        request.target_workers,
        f"manual: {request.reason}"
    )
    
    # Log admin action
    await db.admin_actions.insert_one({
        "action": "manual_scale",
        "admin_id": str(current_user.get("id") or current_user.get("_id")),
        "details": {
            "target_workers": request.target_workers,
            "reason": request.reason,
            "result": result
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return result


@router.put("/config")
async def update_scaling_config(
    request: UpdateConfigRequest,
    current_user: dict = Depends(get_admin_user)
):
    """
    Update auto-scaling configuration (min/max workers)
    """
    result = await auto_scaling_engine.update_config(
        min_workers=request.min_workers,
        max_workers=request.max_workers
    )
    return result


@router.get("/rules")
async def get_scaling_rules(current_user: dict = Depends(get_admin_user)):
    """
    Get all configured scaling rules
    """
    rules = []
    for rule in auto_scaling_engine.config.rules:
        rules.append({
            "name": rule.name,
            "metric": rule.metric,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "action": rule.action,
            "scale_amount": rule.scale_amount,
            "cooldown_seconds": rule.cooldown_seconds,
            "sustained_seconds": rule.sustained_seconds,
            "enabled": rule.enabled
        })
    
    return {"rules": rules, "count": len(rules)}


@router.post("/rules")
async def add_scaling_rule(
    rule: ScalingRuleRequest,
    current_user: dict = Depends(get_admin_user)
):
    """
    Add a new scaling rule
    """
    from services.priority_scaling_service import ScalingRule
    
    new_rule = ScalingRule(
        name=rule.name,
        metric=rule.metric,
        operator=rule.operator,
        threshold=rule.threshold,
        action=rule.action,
        scale_amount=rule.scale_amount,
        cooldown_seconds=rule.cooldown_seconds,
        sustained_seconds=rule.sustained_seconds,
        enabled=rule.enabled
    )
    
    # Check for duplicate name
    for existing in auto_scaling_engine.config.rules:
        if existing.name == rule.name:
            raise HTTPException(400, "Rule with this name already exists")
    
    auto_scaling_engine.config.rules.append(new_rule)
    
    return {"success": True, "message": f"Rule '{rule.name}' added"}


@router.delete("/rules/{rule_name}")
async def delete_scaling_rule(
    rule_name: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Delete a scaling rule by name
    """
    original_count = len(auto_scaling_engine.config.rules)
    auto_scaling_engine.config.rules = [
        r for r in auto_scaling_engine.config.rules 
        if r.name != rule_name
    ]
    
    if len(auto_scaling_engine.config.rules) < original_count:
        return {"success": True, "message": f"Rule '{rule_name}' deleted"}
    
    raise HTTPException(404, f"Rule '{rule_name}' not found")


@router.put("/rules/{rule_name}/toggle")
async def toggle_scaling_rule(
    rule_name: str,
    enabled: bool = Query(...),
    current_user: dict = Depends(get_admin_user)
):
    """
    Enable or disable a scaling rule
    """
    for rule in auto_scaling_engine.config.rules:
        if rule.name == rule_name:
            rule.enabled = enabled
            return {
                "success": True,
                "rule": rule_name,
                "enabled": enabled
            }
    
    raise HTTPException(404, f"Rule '{rule_name}' not found")


@router.get("/history")
async def get_scaling_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_admin_user)
):
    """
    Get recent scaling events history
    """
    events = auto_scaling_engine.scaling_history[-limit:]
    events.reverse()  # Most recent first
    
    return {
        "events": events,
        "count": len(events)
    }


@router.get("/metrics")
async def get_scaling_metrics(current_user: dict = Depends(get_admin_user)):
    """
    Get detailed scaling metrics history
    """
    metrics = {}
    
    for metric_name, values in auto_scaling_engine.metric_history.items():
        if values:
            recent_values = [v["value"] for v in values[-30:]]
            metrics[metric_name] = {
                "current": values[-1]["value"] if values else None,
                "avg_30s": sum(recent_values) / len(recent_values) if recent_values else None,
                "min": min(recent_values) if recent_values else None,
                "max": max(recent_values) if recent_values else None,
                "history": values[-60:]
            }
    
    return {"metrics": metrics}


# ============================================
# PRIORITY LANES ENDPOINTS
# ============================================

@router.get("/priority/lanes")
async def get_priority_lanes(current_user: dict = Depends(get_admin_user)):
    """
    Get all priority lanes with their current statistics
    """
    stats = await priority_lane_manager.get_lane_stats()
    
    # Add tier configuration
    lane_info = {}
    for tier in UserTier:
        config = TIER_CONFIG[tier]
        lane_info[tier.value] = {
            **stats.get(tier.value, {}),
            "config": {
                "priority": config["priority"],
                "max_concurrent_jobs": config["max_concurrent_jobs"],
                "max_queue_size": config["max_queue_size"],
                "sla_seconds": config["guaranteed_sla_seconds"],
                "timeout_multiplier": config["timeout_multiplier"],
                "dedicated_worker_percent": config["dedicated_worker_percent"]
            }
        }
    
    return {"lanes": lane_info}


@router.get("/priority/user/{user_id}")
async def get_user_priority_info(
    user_id: str,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get priority information for a specific user
    """
    tier = await priority_lane_manager.get_user_tier(user_id)
    config = priority_lane_manager.get_tier_config(tier)
    
    # Get user's current jobs
    active_jobs = await db.jobs.count_documents({
        "user_id": user_id,
        "state": {"$in": ["pending", "in_progress", "retrying"]}
    })
    
    return {
        "user_id": user_id,
        "tier": tier.value,
        "priority": config["priority"],
        "active_jobs": active_jobs,
        "max_concurrent": config["max_concurrent_jobs"],
        "can_submit": active_jobs < config["max_concurrent_jobs"],
        "sla_seconds": config["guaranteed_sla_seconds"],
        "config": config
    }


@router.get("/priority/job/{job_id}")
async def get_job_queue_position(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a job's position in the priority queue (available to job owner)
    """
    user_id = str(current_user.get("id") or current_user.get("_id"))
    
    # Verify ownership or admin
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0, "user_id": 1})
    if not job:
        raise HTTPException(404, "Job not found")
    
    is_admin = current_user.get("role") == "admin"
    if job.get("user_id") != user_id and not is_admin:
        raise HTTPException(403, "Not authorized to view this job")
    
    position = await priority_lane_manager.get_queue_position(job_id, job.get("user_id"))
    return position


@router.post("/priority/check")
async def check_job_submission(
    job_type: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if user can submit a new job (enforces priority lane limits)
    """
    user_id = str(current_user.get("id") or current_user.get("_id"))
    result = await priority_lane_manager.assign_priority(user_id, job_type)
    return result


# ============================================
# COMBINED DASHBOARD ENDPOINT
# ============================================

@router.get("/dashboard")
async def get_scaling_dashboard(current_user: dict = Depends(get_admin_user)):
    """
    Get complete auto-scaling and priority dashboard data
    """
    # Get scaling status
    scaling_status = auto_scaling_engine.get_status()
    
    # Get priority lane stats
    lane_stats = await priority_lane_manager.get_lane_stats()
    
    # Get queue breakdown by tier
    tier_queues = {}
    for tier in UserTier:
        tier_queues[tier.value] = await db.jobs.count_documents({
            "state": "pending",
            "tier": tier.value
        })
    
    # Get recent scaling events from DB
    recent_events = await db.scaling_events.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(10).to_list(10)
    
    return {
        "scaling": {
            "current_workers": scaling_status["current_workers"],
            "min_workers": scaling_status["min_workers"],
            "max_workers": scaling_status["max_workers"],
            "running": scaling_status["running"],
            "metrics": scaling_status["metrics"]
        },
        "priority_lanes": lane_stats,
        "queue_by_tier": tier_queues,
        "recent_scaling_events": recent_events,
        "active_rules_count": len([r for r in auto_scaling_engine.config.rules if r.enabled]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
