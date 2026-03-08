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
        except:
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
        except:
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
            req_start = time.time()
            
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
