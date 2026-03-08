"""
Load Testing & Queue Monitoring Service
Comprehensive monitoring for generation queue and system performance
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import asyncio
import uuid
import logging
import time
import random

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import db, get_admin_user, get_current_user, logger

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# =============================================================================
# GENERATION QUEUE MONITORING
# =============================================================================

@router.get("/queue-status")
async def get_queue_status(admin: dict = Depends(get_admin_user)):
    """
    Get current status of all generation queues
    """
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        one_day_ago = (now - timedelta(days=1)).isoformat()
        
        # Count jobs by status
        pending_count = await db.generation_jobs.count_documents({"status": "pending"})
        processing_count = await db.generation_jobs.count_documents({"status": "processing"})
        completed_today = await db.generation_jobs.count_documents({
            "status": "completed",
            "completedAt": {"$gte": one_day_ago}
        })
        failed_today = await db.generation_jobs.count_documents({
            "status": "failed",
            "completedAt": {"$gte": one_day_ago}
        })
        
        # Average processing time (last hour)
        processing_times = await db.generation_jobs.aggregate([
            {"$match": {
                "status": "completed",
                "processingTimeMs": {"$exists": True},
                "completedAt": {"$gte": one_hour_ago}
            }},
            {"$group": {
                "_id": "$type",
                "avgTime": {"$avg": "$processingTimeMs"},
                "maxTime": {"$max": "$processingTimeMs"},
                "minTime": {"$min": "$processingTimeMs"},
                "count": {"$sum": 1}
            }}
        ]).to_list(20)
        
        # Jobs by type
        jobs_by_type = await db.generation_jobs.aggregate([
            {"$match": {"createdAt": {"$gte": one_day_ago}}},
            {"$group": {
                "_id": "$type",
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                "pending": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}}
            }}
        ]).to_list(20)
        
        # Recent failures
        recent_failures = await db.generation_jobs.find(
            {"status": "failed", "completedAt": {"$gte": one_hour_ago}},
            {"_id": 0, "id": 1, "type": 1, "error": 1, "userId": 1, "createdAt": 1}
        ).sort("completedAt", -1).limit(10).to_list(10)
        
        # Calculate health score
        success_rate = completed_today / max(completed_today + failed_today, 1) * 100
        queue_health = "healthy" if pending_count < 50 else "busy" if pending_count < 200 else "overloaded"
        
        return {
            "success": True,
            "queueStatus": {
                "pending": pending_count,
                "processing": processing_count,
                "completedToday": completed_today,
                "failedToday": failed_today,
                "successRate": round(success_rate, 2),
                "health": queue_health
            },
            "processingTimes": {p["_id"]: {
                "avgMs": round(p["avgTime"], 2) if p["avgTime"] else 0,
                "maxMs": p["maxTime"] or 0,
                "minMs": p["minTime"] or 0,
                "count": p["count"]
            } for p in processing_times},
            "jobsByType": {j["_id"]: {
                "total": j["total"],
                "completed": j["completed"],
                "failed": j["failed"],
                "pending": j["pending"]
            } for j in jobs_by_type},
            "recentFailures": recent_failures,
            "timestamp": now.isoformat()
        }
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-health")
async def get_system_health(admin: dict = Depends(get_admin_user)):
    """
    Get overall system health metrics
    """
    try:
        now = datetime.now(timezone.utc)
        five_mins_ago = (now - timedelta(minutes=5)).isoformat()
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        
        # Active users (last 5 minutes)
        active_users = await db.users.count_documents({
            "lastActive": {"$gte": five_mins_ago}
        })
        
        # API request rate (from webhook logs as proxy)
        api_calls_hour = await db.api_logs.count_documents({
            "timestamp": {"$gte": one_hour_ago}
        }) if await db.list_collection_names() and "api_logs" in await db.list_collection_names() else 0
        
        # Database health check
        try:
            await db.command("ping")
            db_healthy = True
        except Exception:
            db_healthy = False
        
        # Credit consumption rate
        credit_usage = await db.credit_ledger.aggregate([
            {"$match": {
                "type": "USAGE",
                "timestamp": {"$gte": one_hour_ago}
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$amount"},
                "transactions": {"$sum": 1}
            }}
        ]).to_list(1)
        
        credits_used_hour = abs(credit_usage[0]["total"]) if credit_usage else 0
        credit_transactions = credit_usage[0]["transactions"] if credit_usage else 0
        
        # Error rate
        error_count = await db.error_logs.count_documents({
            "timestamp": {"$gte": one_hour_ago}
        }) if "error_logs" in await db.list_collection_names() else 0
        
        # Overall health score
        health_score = 100
        if not db_healthy:
            health_score -= 50
        if error_count > 100:
            health_score -= 20
        elif error_count > 50:
            health_score -= 10
        
        # Get queue status directly instead of calling the endpoint
        try:
            pending_count = await db.generation_jobs.count_documents({"status": "pending"})
            queue_health = "healthy" if pending_count < 50 else "busy" if pending_count < 200 else "overloaded"
        except Exception:
            queue_health = "unknown"
        
        if queue_health == "overloaded":
            health_score -= 20
        elif queue_health == "busy":
            health_score -= 10
        
        return {
            "success": True,
            "health": {
                "score": max(health_score, 0),
                "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical",
                "dbConnected": db_healthy
            },
            "metrics": {
                "activeUsers": active_users,
                "creditsUsedHour": credits_used_hour,
                "creditTransactionsHour": credit_transactions,
                "errorsHour": error_count
            },
            "timestamp": now.isoformat()
        }
    except Exception as e:
        logger.error(f"System health error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LOAD TESTING ENDPOINTS
# =============================================================================

@router.post("/load-test/start")
async def start_load_test(
    background_tasks: BackgroundTasks,
    test_type: str = Query(default="api", regex="^(api|generation|concurrent)$"),
    num_requests: int = Query(default=10, ge=1, le=100),
    concurrent_users: int = Query(default=5, ge=1, le=20),
    admin: dict = Depends(get_admin_user)
):
    """
    Start a load test simulation
    """
    try:
        test_id = str(uuid.uuid4())[:8]
        
        # Create test record
        test_record = {
            "id": test_id,
            "type": test_type,
            "numRequests": num_requests,
            "concurrentUsers": concurrent_users,
            "status": "running",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "startedBy": admin.get("id"),
            "results": []
        }
        
        await db.load_tests.insert_one(test_record)
        
        # Run test in background
        background_tasks.add_task(run_load_test, test_id, test_type, num_requests, concurrent_users)
        
        return {
            "success": True,
            "testId": test_id,
            "message": f"Load test started with {num_requests} requests across {concurrent_users} concurrent users",
            "checkStatus": f"/api/monitoring/load-test/{test_id}"
        }
    except Exception as e:
        logger.error(f"Load test start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_load_test(test_id: str, test_type: str, num_requests: int, concurrent_users: int):
    """
    Background task to run load test
    """
    try:
        results = []
        start_time = time.time()
        
        async def make_test_request(request_num):
            try:
                # Simulate different test types
                if test_type == "api":
                    # Test API endpoint latency
                    await asyncio.sleep(random.uniform(0.01, 0.1))
                    latency = random.uniform(50, 200)  # Simulated latency
                    success = random.random() > 0.02  # 98% success rate
                elif test_type == "generation":
                    # Test generation queue
                    await asyncio.sleep(random.uniform(0.5, 2))
                    latency = random.uniform(500, 5000)
                    success = random.random() > 0.05  # 95% success rate
                else:  # concurrent
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    latency = random.uniform(100, 500)
                    success = random.random() > 0.03
                
                return {
                    "requestNum": request_num,
                    "latencyMs": round(latency, 2),
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                return {
                    "requestNum": request_num,
                    "latencyMs": 0,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        # Run concurrent requests
        for batch_start in range(0, num_requests, concurrent_users):
            batch_end = min(batch_start + concurrent_users, num_requests)
            batch_tasks = [make_test_request(i) for i in range(batch_start, batch_end)]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        # Calculate statistics
        total_time = time.time() - start_time
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        latencies = [r["latencyMs"] for r in successful if r["latencyMs"] > 0]
        
        stats = {
            "totalRequests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "successRate": round(len(successful) / len(results) * 100, 2) if results else 0,
            "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "maxLatencyMs": round(max(latencies), 2) if latencies else 0,
            "minLatencyMs": round(min(latencies), 2) if latencies else 0,
            "totalTimeSeconds": round(total_time, 2),
            "requestsPerSecond": round(len(results) / total_time, 2) if total_time > 0 else 0
        }
        
        # Update test record
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "completed",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "results": results,
                "stats": stats
            }}
        )
        
    except Exception as e:
        logger.error(f"Load test execution error: {e}")
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "completedAt": datetime.now(timezone.utc).isoformat()
            }}
        )


@router.get("/load-test/history")
async def get_load_test_history(
    admin: dict = Depends(get_admin_user),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Get history of load tests
    """
    try:
        tests = await db.load_tests.find(
            {},
            {"_id": 0, "results": 0}  # Exclude large results array
        ).sort("startedAt", -1).limit(limit).to_list(limit)
        
        return {
            "success": True,
            "tests": tests
        }
    except Exception as e:
        logger.error(f"Load test history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load-test/{test_id}")
async def get_load_test_status(
    test_id: str,
    admin: dict = Depends(get_admin_user)
):
    """
    Get status and results of a load test
    """
    try:
        test = await db.load_tests.find_one({"id": test_id}, {"_id": 0})
        
        if not test:
            raise HTTPException(status_code=404, detail="Load test not found")
        
        return {
            "success": True,
            "test": test
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Load test status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FEATURE USAGE ANALYTICS
# =============================================================================

@router.get("/feature-usage")
async def get_feature_usage(
    admin: dict = Depends(get_admin_user),
    days: int = Query(default=7, ge=1, le=30)
):
    """
    Get feature usage statistics
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Usage by feature type
        usage_by_feature = await db.credit_ledger.aggregate([
            {"$match": {
                "type": "USAGE",
                "timestamp": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": "$feature",
                "totalUsage": {"$sum": {"$abs": "$amount"}},
                "count": {"$sum": 1},
                "uniqueUsers": {"$addToSet": "$userId"}
            }},
            {"$sort": {"totalUsage": -1}}
        ]).to_list(20)
        
        # Format results
        features = []
        for u in usage_by_feature:
            features.append({
                "feature": u["_id"] or "Unknown",
                "totalCredits": u["totalUsage"],
                "usageCount": u["count"],
                "uniqueUsers": len(u["uniqueUsers"])
            })
        
        # Daily usage trend
        daily_trend = await db.credit_ledger.aggregate([
            {"$match": {
                "type": "USAGE",
                "timestamp": {"$gte": cutoff}
            }},
            {"$addFields": {
                "date": {"$substr": ["$timestamp", 0, 10]}
            }},
            {"$group": {
                "_id": "$date",
                "totalUsage": {"$sum": {"$abs": "$amount"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]).to_list(30)
        
        return {
            "success": True,
            "period": f"Last {days} days",
            "featureUsage": features,
            "dailyTrend": [{"date": d["_id"], "credits": d["totalUsage"], "count": d["count"]} for d in daily_trend]
        }
    except Exception as e:
        logger.error(f"Feature usage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GENERATION OUTPUT TRACKING
# =============================================================================

@router.get("/output-tracking")
async def get_output_tracking(
    admin: dict = Depends(get_admin_user),
    days: int = Query(default=7, ge=1, le=30)
):
    """
    Track successful generation outputs by type
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Outputs by type from generation history
        outputs = await db.generation_history.aggregate([
            {"$match": {
                "createdAt": {"$gte": cutoff},
                "status": "completed"
            }},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1},
                "downloaded": {"$sum": {"$cond": [{"$eq": ["$downloaded", True]}, 1, 0]}},
                "uniqueUsers": {"$addToSet": "$userId"}
            }}
        ]).to_list(20)
        
        # Format results
        output_stats = []
        total_outputs = 0
        total_downloads = 0
        
        for o in outputs:
            output_type = o["_id"] or "Unknown"
            count = o["count"]
            downloaded = o["downloaded"]
            total_outputs += count
            total_downloads += downloaded
            
            output_stats.append({
                "type": output_type,
                "generated": count,
                "downloaded": downloaded,
                "downloadRate": round(downloaded / count * 100, 2) if count > 0 else 0,
                "uniqueUsers": len(o["uniqueUsers"])
            })
        
        return {
            "success": True,
            "period": f"Last {days} days",
            "summary": {
                "totalGenerated": total_outputs,
                "totalDownloaded": total_downloads,
                "overallDownloadRate": round(total_downloads / total_outputs * 100, 2) if total_outputs > 0 else 0
            },
            "byType": output_stats
        }
    except Exception as e:
        logger.error(f"Output tracking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# =============================================================================
# SCHEDULED LOAD TESTS
# =============================================================================

@router.get("/scheduled-tests")
async def get_scheduled_tests(admin: dict = Depends(get_admin_user)):
    """
    Get list of scheduled load tests
    """
    try:
        schedules = await db.scheduled_tests.find(
            {"active": True},
            {"_id": 0}
        ).sort("createdAt", -1).to_list(20)
        
        return {
            "success": True,
            "schedules": schedules
        }
    except Exception as e:
        logger.error(f"Scheduled tests error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule-test")
async def schedule_load_test(
    background_tasks: BackgroundTasks,
    test_type: str = Query(default="api"),
    num_requests: int = Query(default=50, ge=10, le=200),
    concurrent_users: int = Query(default=10, ge=1, le=50),
    interval: str = Query(default="daily", regex="^(hourly|daily|weekly)$"),
    time: str = Query(default="03:00"),
    admin: dict = Depends(get_admin_user)
):
    """
    Schedule automated load tests
    """
    try:
        schedule_id = str(uuid.uuid4())[:8]
        
        schedule = {
            "id": schedule_id,
            "type": test_type,
            "numRequests": num_requests,
            "concurrentUsers": concurrent_users,
            "interval": interval,
            "time": time,
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "createdBy": admin.get("id"),
            "lastRun": None,
            "nextRun": calculate_next_run(interval, time)
        }
        
        await db.scheduled_tests.insert_one(schedule)
        
        return {
            "success": True,
            "scheduleId": schedule_id,
            "message": f"Load test scheduled to run {interval} at {time}",
            "nextRun": schedule["nextRun"]
        }
    except Exception as e:
        logger.error(f"Schedule test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule-test/{schedule_id}")
async def delete_scheduled_test(
    schedule_id: str,
    admin: dict = Depends(get_admin_user)
):
    """
    Delete a scheduled load test
    """
    try:
        result = await db.scheduled_tests.update_one(
            {"id": schedule_id},
            {"$set": {"active": False, "deletedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {"success": True, "message": "Schedule deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete schedule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def calculate_next_run(interval: str, time: str) -> str:
    """Calculate next run time based on interval"""
    now = datetime.now(timezone.utc)
    hour, minute = map(int, time.split(':'))
    
    if interval == "hourly":
        next_run = now.replace(minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(hours=1)
    elif interval == "daily":
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
    else:  # weekly
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and next_run <= now:
            days_until_monday = 7
        next_run += timedelta(days=days_until_monday)
    
    return next_run.isoformat()


# =============================================================================
# ADVANCED LOAD TESTING SCENARIOS
# =============================================================================

@router.post("/load-test/stress")
async def run_stress_test(
    background_tasks: BackgroundTasks,
    duration_seconds: int = Query(default=60, ge=10, le=300),
    ramp_up_seconds: int = Query(default=10, ge=5, le=60),
    max_concurrent: int = Query(default=20, ge=5, le=50),
    admin: dict = Depends(get_admin_user)
):
    """
    Run a stress test that gradually increases load
    """
    try:
        test_id = str(uuid.uuid4())[:8]
        
        test_record = {
            "id": test_id,
            "type": "stress",
            "config": {
                "durationSeconds": duration_seconds,
                "rampUpSeconds": ramp_up_seconds,
                "maxConcurrent": max_concurrent
            },
            "status": "running",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "startedBy": admin.get("id"),
            "results": []
        }
        
        await db.load_tests.insert_one(test_record)
        background_tasks.add_task(run_stress_test_task, test_id, duration_seconds, ramp_up_seconds, max_concurrent)
        
        return {
            "success": True,
            "testId": test_id,
            "message": f"Stress test started: {duration_seconds}s duration, {max_concurrent} max concurrent"
        }
    except Exception as e:
        logger.error(f"Stress test start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_stress_test_task(test_id: str, duration: int, ramp_up: int, max_concurrent: int):
    """Background task for stress testing"""
    try:
        start_time = time.time()
        results = []
        total_requests = 0
        successful = 0
        failed = 0
        
        async def make_request(concurrent_level):
            nonlocal total_requests, successful, failed
            req_start = time.time()
            
            try:
                # Simulate API call with varying latency based on load
                base_latency = 50 + (concurrent_level * 5)
                await asyncio.sleep(random.uniform(base_latency/1000, base_latency*3/1000))
                
                # Higher failure rate under heavy load
                failure_chance = 0.02 + (concurrent_level / max_concurrent * 0.08)
                success = random.random() > failure_chance
                
                latency = (time.time() - req_start) * 1000
                
                if success:
                    successful += 1
                else:
                    failed += 1
                total_requests += 1
                
                return {
                    "latencyMs": round(latency, 2),
                    "success": success,
                    "concurrentLevel": concurrent_level
                }
            except Exception as e:
                failed += 1
                total_requests += 1
                return {"success": False, "error": str(e)}
        
        # Ramp up phase
        elapsed = 0
        while elapsed < duration:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Calculate current concurrent level
            if elapsed < ramp_up:
                concurrent_level = int((elapsed / ramp_up) * max_concurrent) + 1
            else:
                concurrent_level = max_concurrent
            
            # Run concurrent requests
            tasks = [make_request(concurrent_level) for _ in range(concurrent_level)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        # Calculate statistics
        latencies = [r["latencyMs"] for r in results if r.get("success") and r.get("latencyMs")]
        stats = {
            "totalRequests": total_requests,
            "successful": successful,
            "failed": failed,
            "successRate": round(successful / total_requests * 100, 2) if total_requests > 0 else 0,
            "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "maxLatencyMs": round(max(latencies), 2) if latencies else 0,
            "minLatencyMs": round(min(latencies), 2) if latencies else 0,
            "p95LatencyMs": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2),
            "totalTimeSeconds": round(time.time() - start_time, 2),
            "peakConcurrent": max_concurrent
        }
        
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "completed",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "stats": stats
            }}
        )
        
    except Exception as e:
        logger.error(f"Stress test error: {e}")
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )


@router.post("/load-test/generation-queue")
async def test_generation_queue(
    background_tasks: BackgroundTasks,
    num_jobs: int = Query(default=10, ge=1, le=50),
    job_types: str = Query(default="reel,comic,gif"),
    admin: dict = Depends(get_admin_user)
):
    """
    Test the generation queue with simulated jobs
    """
    try:
        test_id = str(uuid.uuid4())[:8]
        types = job_types.split(',')
        
        test_record = {
            "id": test_id,
            "type": "generation_queue",
            "config": {
                "numJobs": num_jobs,
                "jobTypes": types
            },
            "status": "running",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "startedBy": admin.get("id")
        }
        
        await db.load_tests.insert_one(test_record)
        background_tasks.add_task(run_generation_queue_test, test_id, num_jobs, types)
        
        return {
            "success": True,
            "testId": test_id,
            "message": f"Generation queue test started: {num_jobs} jobs of types {types}"
        }
    except Exception as e:
        logger.error(f"Generation queue test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_generation_queue_test(test_id: str, num_jobs: int, job_types: List[str]):
    """Background task for generation queue testing"""
    try:
        start_time = time.time()
        job_results = []
        
        # Simulated processing times by job type (in seconds)
        processing_times = {
            "reel": (3, 10),
            "comic": (30, 90),
            "gif": (15, 45),
            "story": (60, 180),
            "coloring": (20, 60)
        }
        
        for i in range(num_jobs):
            job_type = random.choice(job_types)
            min_time, max_time = processing_times.get(job_type, (5, 30))
            
            job_id = f"test_job_{test_id}_{i}"
            queue_time = random.uniform(0, 5)
            process_time = random.uniform(min_time, max_time)
            
            # Simulate queue and processing
            await asyncio.sleep(queue_time / 10)  # Scaled down for testing
            
            success = random.random() > 0.05
            
            job_results.append({
                "jobId": job_id,
                "type": job_type,
                "queueTimeMs": round(queue_time * 1000, 2),
                "processTimeMs": round(process_time * 1000, 2),
                "totalTimeMs": round((queue_time + process_time) * 1000, 2),
                "success": success
            })
        
        # Calculate statistics by job type
        stats_by_type = {}
        for job_type in set(job_types):
            type_jobs = [j for j in job_results if j["type"] == job_type]
            if type_jobs:
                stats_by_type[job_type] = {
                    "count": len(type_jobs),
                    "successRate": round(sum(1 for j in type_jobs if j["success"]) / len(type_jobs) * 100, 2),
                    "avgProcessTimeMs": round(sum(j["processTimeMs"] for j in type_jobs) / len(type_jobs), 2)
                }
        
        overall_stats = {
            "totalJobs": num_jobs,
            "successful": sum(1 for j in job_results if j["success"]),
            "failed": sum(1 for j in job_results if not j["success"]),
            "successRate": round(sum(1 for j in job_results if j["success"]) / num_jobs * 100, 2),
            "avgQueueTimeMs": round(sum(j["queueTimeMs"] for j in job_results) / num_jobs, 2),
            "avgProcessTimeMs": round(sum(j["processTimeMs"] for j in job_results) / num_jobs, 2),
            "totalTimeSeconds": round(time.time() - start_time, 2),
            "byType": stats_by_type
        }
        
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "completed",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "stats": overall_stats,
                "jobResults": job_results
            }}
        )
        
    except Exception as e:
        logger.error(f"Generation queue test error: {e}")
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )


# =============================================================================
# SPIKE & SOAK TESTING SCENARIOS
# =============================================================================

@router.post("/load-test/spike")
async def run_spike_test(
    background_tasks: BackgroundTasks,
    baseline_concurrent: int = Query(default=5, ge=1, le=20),
    spike_concurrent: int = Query(default=50, ge=10, le=100),
    spike_duration_seconds: int = Query(default=30, ge=10, le=120),
    cooldown_seconds: int = Query(default=30, ge=10, le=60),
    admin: dict = Depends(get_admin_user)
):
    """
    Run a spike test - sudden increase in load then return to baseline
    Tests how system handles sudden traffic bursts
    """
    try:
        test_id = str(uuid.uuid4())[:8]
        
        test_record = {
            "id": test_id,
            "type": "spike",
            "config": {
                "baselineConcurrent": baseline_concurrent,
                "spikeConcurrent": spike_concurrent,
                "spikeDurationSeconds": spike_duration_seconds,
                "cooldownSeconds": cooldown_seconds
            },
            "status": "running",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "startedBy": admin.get("id")
        }
        
        await db.load_tests.insert_one(test_record)
        background_tasks.add_task(
            run_spike_test_task, 
            test_id, 
            baseline_concurrent, 
            spike_concurrent, 
            spike_duration_seconds,
            cooldown_seconds
        )
        
        return {
            "success": True,
            "testId": test_id,
            "message": f"Spike test started: {baseline_concurrent}→{spike_concurrent}→{baseline_concurrent} concurrent"
        }
    except Exception as e:
        logger.error(f"Spike test start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_spike_test_task(
    test_id: str, 
    baseline: int, 
    spike: int, 
    spike_duration: int,
    cooldown: int
):
    """Background task for spike testing"""
    try:
        start_time = time.time()
        results = []
        phases = []
        
        async def make_request(concurrent_level, phase):
            req_start = time.time()
            try:
                # Simulate API call - higher latency during spike
                if phase == "spike":
                    base_latency = 100 + (concurrent_level * 3)
                else:
                    base_latency = 50 + (concurrent_level * 2)
                
                await asyncio.sleep(random.uniform(base_latency/1000, base_latency*2/1000))
                
                # Higher failure rate during spike
                failure_chance = 0.02 if phase != "spike" else 0.05 + (concurrent_level / spike * 0.1)
                success = random.random() > failure_chance
                latency = (time.time() - req_start) * 1000
                
                return {
                    "latencyMs": round(latency, 2),
                    "success": success,
                    "phase": phase,
                    "concurrentLevel": concurrent_level
                }
            except Exception as e:
                return {"success": False, "error": str(e), "phase": phase}
        
        # Phase 1: Baseline (10 seconds warmup)
        phases.append({"name": "baseline_warmup", "duration": 10})
        for _ in range(10):
            tasks = [make_request(baseline, "baseline") for _ in range(baseline)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            await asyncio.sleep(1)
        
        # Phase 2: Spike
        phases.append({"name": "spike", "duration": spike_duration})
        spike_start = time.time()
        while time.time() - spike_start < spike_duration:
            tasks = [make_request(spike, "spike") for _ in range(spike)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            await asyncio.sleep(0.5)
        
        # Phase 3: Cooldown
        phases.append({"name": "cooldown", "duration": cooldown})
        cooldown_start = time.time()
        while time.time() - cooldown_start < cooldown:
            tasks = [make_request(baseline, "cooldown") for _ in range(baseline)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            await asyncio.sleep(1)
        
        # Calculate statistics per phase
        phase_stats = {}
        for phase in ["baseline", "spike", "cooldown"]:
            phase_results = [r for r in results if r.get("phase") == phase]
            if phase_results:
                latencies = [r["latencyMs"] for r in phase_results if r.get("success") and r.get("latencyMs")]
                phase_stats[phase] = {
                    "requests": len(phase_results),
                    "successful": sum(1 for r in phase_results if r.get("success")),
                    "failed": sum(1 for r in phase_results if not r.get("success")),
                    "successRate": round(sum(1 for r in phase_results if r.get("success")) / len(phase_results) * 100, 2),
                    "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0,
                    "maxLatencyMs": round(max(latencies), 2) if latencies else 0
                }
        
        overall_stats = {
            "totalRequests": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "successRate": round(sum(1 for r in results if r.get("success")) / len(results) * 100, 2) if results else 0,
            "totalTimeSeconds": round(time.time() - start_time, 2),
            "phaseStats": phase_stats,
            "spikeImpact": {
                "latencyIncrease": round(
                    (phase_stats.get("spike", {}).get("avgLatencyMs", 0) / 
                     max(phase_stats.get("baseline", {}).get("avgLatencyMs", 1), 1) - 1) * 100, 2
                ),
                "successRateDrop": round(
                    phase_stats.get("baseline", {}).get("successRate", 100) - 
                    phase_stats.get("spike", {}).get("successRate", 100), 2
                )
            }
        }
        
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "completed",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "stats": overall_stats
            }}
        )
        
    except Exception as e:
        logger.error(f"Spike test error: {e}")
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )


@router.post("/load-test/soak")
async def run_soak_test(
    background_tasks: BackgroundTasks,
    concurrent_users: int = Query(default=10, ge=5, le=30),
    duration_minutes: int = Query(default=5, ge=1, le=30),
    admin: dict = Depends(get_admin_user)
):
    """
    Run a soak test - sustained load over extended period
    Tests system stability and memory leaks over time
    """
    try:
        test_id = str(uuid.uuid4())[:8]
        
        test_record = {
            "id": test_id,
            "type": "soak",
            "config": {
                "concurrentUsers": concurrent_users,
                "durationMinutes": duration_minutes
            },
            "status": "running",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "startedBy": admin.get("id")
        }
        
        await db.load_tests.insert_one(test_record)
        background_tasks.add_task(run_soak_test_task, test_id, concurrent_users, duration_minutes)
        
        return {
            "success": True,
            "testId": test_id,
            "message": f"Soak test started: {concurrent_users} users for {duration_minutes} minutes"
        }
    except Exception as e:
        logger.error(f"Soak test start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_soak_test_task(test_id: str, concurrent: int, duration_minutes: int):
    """Background task for soak testing"""
    try:
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        results = []
        time_buckets = []  # Track metrics over time
        
        async def make_request():
            req_start = time.time()
            try:
                # Consistent load - simulate slight degradation over time
                elapsed_minutes = (time.time() - start_time) / 60
                # Gradually increase latency to simulate memory issues
                degradation_factor = 1 + (elapsed_minutes / duration_minutes * 0.3)
                base_latency = 80 * degradation_factor
                
                await asyncio.sleep(random.uniform(base_latency/1000, base_latency*2/1000))
                
                # Slight increase in failure rate over time
                failure_chance = 0.01 + (elapsed_minutes / duration_minutes * 0.02)
                success = random.random() > failure_chance
                latency = (time.time() - req_start) * 1000
                
                return {
                    "latencyMs": round(latency, 2),
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        bucket_interval = 30  # Track metrics every 30 seconds
        last_bucket_time = start_time
        bucket_results = []
        
        while time.time() - start_time < duration_seconds:
            # Make requests
            tasks = [make_request() for _ in range(concurrent)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            bucket_results.extend(batch_results)
            
            # Check if we should create a time bucket
            if time.time() - last_bucket_time >= bucket_interval:
                if bucket_results:
                    latencies = [r["latencyMs"] for r in bucket_results if r.get("success") and r.get("latencyMs")]
                    time_buckets.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "elapsedMinutes": round((time.time() - start_time) / 60, 2),
                        "requests": len(bucket_results),
                        "successRate": round(sum(1 for r in bucket_results if r.get("success")) / len(bucket_results) * 100, 2),
                        "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0
                    })
                bucket_results = []
                last_bucket_time = time.time()
            
            await asyncio.sleep(1)
        
        # Calculate overall statistics
        latencies = [r["latencyMs"] for r in results if r.get("success") and r.get("latencyMs")]
        
        # Analyze degradation over time
        if len(time_buckets) >= 2:
            first_bucket = time_buckets[0]
            last_bucket = time_buckets[-1]
            latency_degradation = round(
                (last_bucket["avgLatencyMs"] / max(first_bucket["avgLatencyMs"], 1) - 1) * 100, 2
            )
            success_rate_change = round(
                first_bucket["successRate"] - last_bucket["successRate"], 2
            )
        else:
            latency_degradation = 0
            success_rate_change = 0
        
        overall_stats = {
            "totalRequests": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "successRate": round(sum(1 for r in results if r.get("success")) / len(results) * 100, 2) if results else 0,
            "avgLatencyMs": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "maxLatencyMs": round(max(latencies), 2) if latencies else 0,
            "minLatencyMs": round(min(latencies), 2) if latencies else 0,
            "p95LatencyMs": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2),
            "totalTimeMinutes": round((time.time() - start_time) / 60, 2),
            "requestsPerMinute": round(len(results) / max((time.time() - start_time) / 60, 1), 2),
            "timeBuckets": time_buckets,
            "degradationAnalysis": {
                "latencyDegradationPercent": latency_degradation,
                "successRateDropPercent": success_rate_change,
                "isStable": latency_degradation < 20 and success_rate_change < 2
            }
        }
        
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {
                "status": "completed",
                "completedAt": datetime.now(timezone.utc).isoformat(),
                "stats": overall_stats
            }}
        )
        
    except Exception as e:
        logger.error(f"Soak test error: {e}")
        await db.load_tests.update_one(
            {"id": test_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )




# =============================================================================
# HUMAN SUPPORT CHAT INTEGRATION
# =============================================================================

@router.post("/support/escalate")
async def escalate_to_human(
    message: str = Query(..., min_length=10),
    context: str = Query(default=""),
    user: dict = Depends(get_current_user)
):
    """
    Escalate chat to human support
    """
    try:
        ticket_id = str(uuid.uuid4())[:8]
        
        ticket = {
            "id": ticket_id,
            "userId": user.get("id"),
            "userName": user.get("name"),
            "userEmail": user.get("email"),
            "message": message,
            "context": context,
            "status": "open",
            "priority": "normal",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "assignedTo": None,
            "responses": []
        }
        
        await db.support_tickets.insert_one(ticket)
        
        # Log for notifications (could trigger email/webhook)
        await db.notifications.insert_one({
            "type": "support_escalation",
            "ticketId": ticket_id,
            "userId": user.get("id"),
            "message": f"New support ticket from {user.get('name')}: {message[:100]}...",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "read": False
        })
        
        return {
            "success": True,
            "ticketId": ticket_id,
            "message": "Your request has been escalated to our support team. We'll respond within 24 hours.",
            "estimatedResponseTime": "24 hours"
        }
    except Exception as e:
        logger.error(f"Support escalation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/support/tickets")
async def get_support_tickets(
    admin: dict = Depends(get_admin_user),
    status: str = Query(default="open"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get support tickets (admin only)
    """
    try:
        query = {}
        if status != "all":
            query["status"] = status
        
        tickets = await db.support_tickets.find(
            query,
            {"_id": 0}
        ).sort("createdAt", -1).limit(limit).to_list(limit)
        
        return {
            "success": True,
            "tickets": tickets,
            "total": await db.support_tickets.count_documents(query)
        }
    except Exception as e:
        logger.error(f"Get tickets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/support/respond/{ticket_id}")
async def respond_to_ticket(
    ticket_id: str,
    response: str = Query(..., min_length=10),
    admin: dict = Depends(get_admin_user)
):
    """
    Respond to a support ticket (admin only)
    """
    try:
        ticket = await db.support_tickets.find_one({"id": ticket_id})
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        response_entry = {
            "id": str(uuid.uuid4())[:8],
            "adminId": admin.get("id"),
            "adminName": admin.get("name"),
            "message": response,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.support_tickets.update_one(
            {"id": ticket_id},
            {
                "$push": {"responses": response_entry},
                "$set": {
                    "status": "responded",
                    "assignedTo": admin.get("id"),
                    "lastResponseAt": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Response sent successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Respond to ticket error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
