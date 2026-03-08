"""
Story → Video Studio - Performance Monitoring & Analytics
Tracks generation times, success rates, and user metrics.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from shared import db, get_current_user, get_admin_user

router = APIRouter(prefix="/story-video-studio/analytics", tags=["Story Video Analytics"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class PerformanceMetric(BaseModel):
    metric_type: str  # "image_generation", "voice_generation", "video_assembly", "scene_generation"
    project_id: str
    user_id: str
    duration_ms: int
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MetricsSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_duration_ms: float
    p95_duration_ms: float
    success_rate: float

# =============================================================================
# METRIC RECORDING
# =============================================================================

async def record_metric(
    metric_type: str,
    project_id: str,
    user_id: str,
    duration_ms: int,
    success: bool,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Record a performance metric"""
    metric_doc = {
        "metric_type": metric_type,
        "project_id": project_id,
        "user_id": user_id,
        "duration_ms": duration_ms,
        "success": success,
        "error_message": error_message,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc)
    }
    await db.story_video_metrics.insert_one(metric_doc)

async def record_generation_start(project_id: str, generation_type: str):
    """Record when a generation starts"""
    await db.generation_tracking.insert_one({
        "project_id": project_id,
        "generation_type": generation_type,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "status": "IN_PROGRESS"
    })

async def record_generation_complete(project_id: str, generation_type: str, success: bool, duration_ms: int):
    """Record when a generation completes"""
    await db.generation_tracking.update_one(
        {"project_id": project_id, "generation_type": generation_type, "status": "IN_PROGRESS"},
        {
            "$set": {
                "completed_at": datetime.now(timezone.utc),
                "status": "COMPLETED" if success else "FAILED",
                "duration_ms": duration_ms
            }
        }
    )

# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(default=7, le=90),
    current_user: dict = Depends(get_admin_user)
):
    """Get analytics dashboard for admins"""
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get metrics by type
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$metric_type",
            "total": {"$sum": 1},
            "successful": {"$sum": {"$cond": ["$success", 1, 0]}},
            "failed": {"$sum": {"$cond": ["$success", 0, 1]}},
            "avg_duration": {"$avg": "$duration_ms"},
            "max_duration": {"$max": "$duration_ms"},
            "min_duration": {"$min": "$duration_ms"}
        }}
    ]
    
    metrics_by_type = await db.story_video_metrics.aggregate(pipeline).to_list(100)
    
    # Get daily trends
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "type": "$metric_type"
            },
            "count": {"$sum": 1},
            "success_count": {"$sum": {"$cond": ["$success", 1, 0]}}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    
    daily_trends = await db.story_video_metrics.aggregate(daily_pipeline).to_list(500)
    
    # Get top users
    user_pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$user_id",
            "total_generations": {"$sum": 1},
            "successful": {"$sum": {"$cond": ["$success", 1, 0]}}
        }},
        {"$sort": {"total_generations": -1}},
        {"$limit": 10}
    ]
    
    top_users = await db.story_video_metrics.aggregate(user_pipeline).to_list(10)
    
    # Calculate overall stats
    total_requests = sum(m.get("total", 0) for m in metrics_by_type)
    total_successful = sum(m.get("successful", 0) for m in metrics_by_type)
    overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "success": True,
        "period_days": days,
        "summary": {
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_requests - total_successful,
            "success_rate": round(overall_success_rate, 2)
        },
        "metrics_by_type": [
            {
                "type": m["_id"],
                "total": m["total"],
                "successful": m["successful"],
                "failed": m["failed"],
                "success_rate": round(m["successful"] / m["total"] * 100, 2) if m["total"] > 0 else 0,
                "avg_duration_ms": round(m["avg_duration"], 0),
                "max_duration_ms": m["max_duration"],
                "min_duration_ms": m["min_duration"]
            }
            for m in metrics_by_type
        ],
        "daily_trends": daily_trends,
        "top_users": top_users
    }

@router.get("/real-time")
async def get_real_time_metrics(current_user: dict = Depends(get_admin_user)):
    """Get real-time generation status"""
    
    # Get in-progress generations
    in_progress = await db.generation_tracking.find(
        {"status": "IN_PROGRESS"},
        {"_id": 0}
    ).to_list(100)
    
    # Get recent completions (last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = await db.story_video_metrics.find(
        {"created_at": {"$gte": one_hour_ago}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    # Calculate rates
    success_count = len([r for r in recent if r.get("success")])
    
    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "in_progress_count": len(in_progress),
        "in_progress": in_progress,
        "last_hour": {
            "total": len(recent),
            "successful": success_count,
            "failed": len(recent) - success_count,
            "success_rate": round(success_count / len(recent) * 100, 2) if recent else 0
        },
        "recent_completions": recent[:10]
    }

@router.get("/project/{project_id}")
async def get_project_metrics(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get metrics for a specific project"""
    
    metrics = await db.story_video_metrics.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    # Calculate totals
    total_duration = sum(m.get("duration_ms", 0) for m in metrics)
    success_count = len([m for m in metrics if m.get("success")])
    
    return {
        "success": True,
        "project_id": project_id,
        "total_operations": len(metrics),
        "successful_operations": success_count,
        "total_duration_ms": total_duration,
        "total_duration_seconds": round(total_duration / 1000, 2),
        "metrics": metrics
    }

@router.post("/record")
async def record_performance_metric(
    metric: PerformanceMetric,
    current_user: dict = Depends(get_current_user)
):
    """Record a performance metric (internal use)"""
    
    await record_metric(
        metric_type=metric.metric_type,
        project_id=metric.project_id,
        user_id=metric.user_id,
        duration_ms=metric.duration_ms,
        success=metric.success,
        error_message=metric.error_message,
        metadata=metric.metadata
    )
    
    return {"success": True, "message": "Metric recorded"}

# =============================================================================
# USER TESTING ENDPOINTS
# =============================================================================

@router.get("/test-flow")
async def get_test_flow_guide():
    """Get user testing flow guide"""
    return {
        "success": True,
        "test_flow": {
            "name": "Story → Video Studio Complete Flow Test",
            "estimated_time": "2-3 minutes",
            "steps": [
                {
                    "step": 1,
                    "name": "Create Project",
                    "endpoint": "POST /api/story-video-studio/projects/create",
                    "description": "Create a new story project with title and story text",
                    "test_data": {
                        "title": "Test Story",
                        "story_text": "Once upon a time, in a magical forest, lived a brave little rabbit named Luna...",
                        "language": "english",
                        "age_group": "kids_5_8",
                        "style_id": "cartoon_2d"
                    }
                },
                {
                    "step": 2,
                    "name": "Generate Scenes",
                    "endpoint": "POST /api/story-video-studio/projects/{project_id}/generate-scenes",
                    "description": "AI generates scenes from story",
                    "expected_time": "5-10 seconds"
                },
                {
                    "step": 3,
                    "name": "Preview Mode (Optional)",
                    "endpoint": "POST /api/story-video-studio/generation/preview",
                    "description": "Generate low-res preview images quickly",
                    "expected_time": "15-30 seconds for all scenes"
                },
                {
                    "step": 4,
                    "name": "Generate Full Quality Images",
                    "endpoint": "POST /api/story-video-studio/generation/images",
                    "description": "Generate HD images for all scenes",
                    "expected_time": "30-60 seconds"
                },
                {
                    "step": 5,
                    "name": "Generate Voices",
                    "endpoint": "POST /api/story-video-studio/generation/voices",
                    "description": "Generate voice narration",
                    "expected_time": "10-20 seconds"
                },
                {
                    "step": 6,
                    "name": "Assemble Video",
                    "endpoint": "POST /api/story-video-studio/generation/video/assemble",
                    "description": "Combine images, voices, and music",
                    "expected_time": "20-40 seconds"
                },
                {
                    "step": 7,
                    "name": "Download Video",
                    "endpoint": "GET /api/story-video-studio/generation/video/download/{job_id}",
                    "description": "Download the final MP4 video"
                }
            ],
            "total_credits_estimate": {
                "preview_mode": "20-30 credits",
                "full_quality": "80-120 credits"
            }
        }
    }

@router.post("/test-run")
async def create_test_run(
    current_user: dict = Depends(get_current_user)
):
    """Create a test run to track user testing"""
    import uuid
    
    user_id = current_user.get("id") or str(current_user.get("_id"))
    test_run_id = str(uuid.uuid4())
    
    test_run_doc = {
        "test_run_id": test_run_id,
        "user_id": user_id,
        "status": "STARTED",
        "steps_completed": [],
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "feedback": None
    }
    
    await db.test_runs.insert_one(test_run_doc)
    
    return {
        "success": True,
        "test_run_id": test_run_id,
        "message": "Test run started. Complete all steps and submit feedback."
    }

@router.post("/test-run/{test_run_id}/step")
async def record_test_step(
    test_run_id: str,
    step_number: int,
    success: bool,
    duration_ms: int,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Record a test step completion"""
    
    step_data = {
        "step": step_number,
        "success": success,
        "duration_ms": duration_ms,
        "notes": notes,
        "completed_at": datetime.now(timezone.utc)
    }
    
    await db.test_runs.update_one(
        {"test_run_id": test_run_id},
        {"$push": {"steps_completed": step_data}}
    )
    
    return {"success": True, "message": f"Step {step_number} recorded"}

@router.post("/test-run/{test_run_id}/feedback")
async def submit_test_feedback(
    test_run_id: str,
    rating: int,
    feedback_text: str,
    issues_found: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback for a test run"""
    
    await db.test_runs.update_one(
        {"test_run_id": test_run_id},
        {
            "$set": {
                "status": "COMPLETED",
                "completed_at": datetime.now(timezone.utc),
                "feedback": {
                    "rating": rating,
                    "text": feedback_text,
                    "issues_found": issues_found or []
                }
            }
        }
    )
    
    return {"success": True, "message": "Thank you for your feedback!"}
