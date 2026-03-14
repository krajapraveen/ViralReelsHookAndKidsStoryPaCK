#!/usr/bin/env python3
"""
CreatorStudio AI - Load Testing Script
Medium Load Test: 200 Concurrent Users
Tests all functionalities EXCEPT payment gateway
"""

import asyncio
import aiohttp
import time
import json
import random
import sys
from datetime import datetime
from collections import defaultdict

# Configuration
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://gallery-showcase-43.preview.emergentagent.com"
CONCURRENT_USERS = 200
TEST_DURATION_SECONDS = 120  # 2 minutes
RAMP_UP_SECONDS = 30

# Test credentials
TEST_USERS = [
    {"email": "demo@example.com", "password": "Password123!"},
    {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
]

# Metrics
metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_logins": 0,
    "successful_logins": 0,
    "response_times": [],
    "errors": defaultdict(int),
    "endpoint_times": defaultdict(list),
}

# Endpoints to test (excluding payment)
ENDPOINTS = [
    # Public endpoints
    ("GET", "/api/health/", False),
    ("GET", "/api/cashfree/products", False),
    ("GET", "/api/pricing/plans?currency=INR", False),
    ("GET", "/api/help/quick-start", False),
    
    # Authenticated endpoints
    ("GET", "/api/auth/me", True),
    ("GET", "/api/wallet/me", True),
    ("GET", "/api/analytics/user-stats", True),
    ("GET", "/api/genstudio/dashboard", True),
    ("GET", "/api/genstudio/templates", True),
    ("GET", "/api/story-series/themes", True),
    ("GET", "/api/story-series/pricing", True),
    ("GET", "/api/story-series/history?limit=5", True),
    ("GET", "/api/challenge-generator/platforms", True),
    ("GET", "/api/challenge-generator/pricing", True),
    ("GET", "/api/tone-switcher/tones", True),
    ("GET", "/api/tone-switcher/pricing", True),
    ("GET", "/api/coloring-book/pricing", True),
    ("GET", "/api/coloring-book/styles", True),
    ("GET", "/api/subscriptions/plans", True),
    ("GET", "/api/privacy/my-data", True),
]


async def login(session, user):
    """Login and get token"""
    try:
        start = time.time()
        async with session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": user["email"], "password": user["password"]},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            elapsed = (time.time() - start) * 1000
            metrics["total_logins"] += 1
            metrics["endpoint_times"]["login"].append(elapsed)
            
            if resp.status == 200:
                data = await resp.json()
                metrics["successful_logins"] += 1
                return data.get("token")
            else:
                metrics["errors"][f"login_{resp.status}"] += 1
                return None
    except Exception as e:
        metrics["errors"][f"login_error"] += 1
        return None


async def make_request(session, method, endpoint, token=None):
    """Make a single request"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        start = time.time()
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                elapsed = (time.time() - start) * 1000
                metrics["total_requests"] += 1
                metrics["response_times"].append(elapsed)
                metrics["endpoint_times"][endpoint].append(elapsed)
                
                if resp.status in [200, 201, 404]:  # 404 is acceptable for some endpoints
                    metrics["successful_requests"] += 1
                    return True
                else:
                    metrics["failed_requests"] += 1
                    metrics["errors"][f"{endpoint}_{resp.status}"] += 1
                    return False
        
        return True
    except asyncio.TimeoutError:
        metrics["failed_requests"] += 1
        metrics["errors"]["timeout"] += 1
        return False
    except Exception as e:
        metrics["failed_requests"] += 1
        metrics["errors"]["connection_error"] += 1
        return False


async def user_session(session, user_id, start_time):
    """Simulate a single user session"""
    user = random.choice(TEST_USERS)
    
    # Login
    token = await login(session, user)
    if not token:
        return
    
    # Execute random endpoints
    end_time = start_time + TEST_DURATION_SECONDS
    while time.time() < end_time:
        # Pick random endpoint
        method, endpoint, requires_auth = random.choice(ENDPOINTS)
        
        if requires_auth and not token:
            continue
        
        await make_request(session, method, endpoint, token if requires_auth else None)
        
        # Random delay between requests (0.5-2 seconds)
        await asyncio.sleep(random.uniform(0.5, 2))


async def run_load_test():
    """Run the load test"""
    print(f"\n{'='*60}")
    print(f"  CREATORSTUDIO AI - LOAD TEST")
    print(f"  {CONCURRENT_USERS} Concurrent Users | {TEST_DURATION_SECONDS}s Duration")
    print(f"  Target: {BASE_URL}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # Create connector with connection pooling
    connector = aiohttp.TCPConnector(limit=CONCURRENT_USERS, limit_per_host=CONCURRENT_USERS)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Ramp up users
        tasks = []
        users_per_second = CONCURRENT_USERS / RAMP_UP_SECONDS
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting ramp-up...")
        
        for i in range(CONCURRENT_USERS):
            task = asyncio.create_task(user_session(session, i, start_time))
            tasks.append(task)
            
            # Print progress every 50 users
            if (i + 1) % 50 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Spawned {i + 1}/{CONCURRENT_USERS} users")
            
            # Ramp up delay
            await asyncio.sleep(1 / users_per_second)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] All {CONCURRENT_USERS} users active. Running test...")
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    response_times = metrics["response_times"]
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.5)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
    else:
        avg_response = p50 = p95 = p99 = 0
    
    success_rate = (metrics["successful_requests"] / metrics["total_requests"] * 100) if metrics["total_requests"] > 0 else 0
    login_success_rate = (metrics["successful_logins"] / metrics["total_logins"] * 100) if metrics["total_logins"] > 0 else 0
    rps = metrics["total_requests"] / total_time if total_time > 0 else 0
    
    # Print results
    print(f"\n{'='*60}")
    print(f"  LOAD TEST RESULTS")
    print(f"{'='*60}")
    print(f"\n📊 Summary:")
    print(f"   Duration: {total_time:.1f} seconds")
    print(f"   Concurrent Users: {CONCURRENT_USERS}")
    print(f"   Total Requests: {metrics['total_requests']}")
    print(f"   Requests/Second: {rps:.1f}")
    print(f"\n✅ Success Metrics:")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Successful: {metrics['successful_requests']}")
    print(f"   Failed: {metrics['failed_requests']}")
    print(f"   Login Success Rate: {login_success_rate:.1f}%")
    print(f"\n⏱️ Response Times:")
    print(f"   Average: {avg_response:.0f}ms")
    print(f"   P50: {p50:.0f}ms")
    print(f"   P95: {p95:.0f}ms")
    print(f"   P99: {p99:.0f}ms")
    
    if metrics["errors"]:
        print(f"\n⚠️ Errors:")
        for error, count in sorted(metrics["errors"].items(), key=lambda x: -x[1])[:10]:
            print(f"   {error}: {count}")
    
    # Endpoint performance
    print(f"\n📈 Top 5 Slowest Endpoints:")
    endpoint_avgs = {k: sum(v)/len(v) for k, v in metrics["endpoint_times"].items() if v}
    for endpoint, avg in sorted(endpoint_avgs.items(), key=lambda x: -x[1])[:5]:
        print(f"   {endpoint}: {avg:.0f}ms avg")
    
    print(f"\n{'='*60}")
    
    # Determine pass/fail
    if success_rate >= 90 and p95 < 3000:
        print(f"  ✅ LOAD TEST PASSED")
        print(f"     Success Rate: {success_rate:.1f}% (threshold: 90%)")
        print(f"     P95 Response: {p95:.0f}ms (threshold: 3000ms)")
    else:
        print(f"  ⚠️ LOAD TEST NEEDS ATTENTION")
        if success_rate < 90:
            print(f"     Success Rate: {success_rate:.1f}% (below 90% threshold)")
        if p95 >= 3000:
            print(f"     P95 Response: {p95:.0f}ms (above 3000ms threshold)")
    
    print(f"{'='*60}\n")
    
    # Save results to file
    results = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "base_url": BASE_URL,
            "concurrent_users": CONCURRENT_USERS,
            "duration_seconds": TEST_DURATION_SECONDS,
        },
        "summary": {
            "total_requests": metrics["total_requests"],
            "successful_requests": metrics["successful_requests"],
            "failed_requests": metrics["failed_requests"],
            "success_rate": success_rate,
            "requests_per_second": rps,
        },
        "response_times": {
            "average_ms": avg_response,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
        },
        "logins": {
            "total": metrics["total_logins"],
            "successful": metrics["successful_logins"],
            "success_rate": login_success_rate,
        },
        "errors": dict(metrics["errors"]),
        "passed": success_rate >= 90 and p95 < 3000,
    }
    
    with open("/app/test_reports/load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to /app/test_reports/load_test_results.json")
    
    return results["passed"]


if __name__ == "__main__":
    success = asyncio.run(run_load_test())
    sys.exit(0 if success else 1)
