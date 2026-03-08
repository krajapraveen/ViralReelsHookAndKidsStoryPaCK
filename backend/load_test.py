#!/usr/bin/env python3
"""
CreatorStudio AI - Load Testing & Stress Testing Suite
=======================================================
Simulates high-concurrency scenarios to measure platform stability.

Usage:
    python3 load_test.py --users 100 --duration 60
    python3 load_test.py --users 500 --duration 120 --ramp-up 30
"""
import os
import sys
import asyncio
import aiohttp
import argparse
import time
import json
import random
import statistics
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any
from collections import defaultdict

# Configuration
API_URL = os.environ.get("API_URL", "https://story-to-video-dev.preview.emergentagent.com")
TEST_USER_EMAIL = "demo@example.com"
TEST_USER_PASSWORD = "Password123!"


@dataclass
class RequestResult:
    """Result of a single request"""
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    success: bool
    error: str = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class LoadTestReport:
    """Comprehensive load test report"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0
    latencies: List[float] = field(default_factory=list)
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    results_by_endpoint: Dict[str, List[RequestResult]] = field(default_factory=lambda: defaultdict(list))
    start_time: str = None
    end_time: str = None
    
    def add_result(self, result: RequestResult):
        self.total_requests += 1
        self.latencies.append(result.latency_ms)
        self.total_latency_ms += result.latency_ms
        self.results_by_endpoint[result.endpoint].append(result)
        
        if result.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if result.error:
                self.errors_by_type[result.error] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"error": "No data collected"}
        
        sorted_latencies = sorted(self.latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)
        
        duration_seconds = 1
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            duration_seconds = max((end - start).total_seconds(), 1)
        
        error_rate = (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "summary": {
                "total_requests": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "error_rate_percent": round(error_rate, 2),
                "requests_per_second": round(self.total_requests / duration_seconds, 2),
                "duration_seconds": round(duration_seconds, 2)
            },
            "latency_ms": {
                "min": round(min(self.latencies), 2),
                "max": round(max(self.latencies), 2),
                "avg": round(statistics.mean(self.latencies), 2),
                "median_p50": round(sorted_latencies[p50_idx], 2),
                "p95": round(sorted_latencies[p95_idx], 2),
                "p99": round(sorted_latencies[p99_idx], 2)
            },
            "errors": dict(self.errors_by_type),
            "endpoints": {
                endpoint: {
                    "count": len(results),
                    "success_rate": round(sum(1 for r in results if r.success) / len(results) * 100, 2),
                    "avg_latency_ms": round(statistics.mean([r.latency_ms for r in results]), 2)
                }
                for endpoint, results in self.results_by_endpoint.items()
            },
            "test_config": {
                "api_url": API_URL,
                "start_time": self.start_time,
                "end_time": self.end_time
            },
            "verdict": self._get_verdict(error_rate, sorted_latencies[p95_idx])
        }
    
    def _get_verdict(self, error_rate: float, p95_latency: float) -> Dict[str, Any]:
        issues = []
        
        if error_rate > 5:
            issues.append(f"CRITICAL: Error rate {error_rate}% exceeds 5% threshold")
        elif error_rate > 1:
            issues.append(f"WARNING: Error rate {error_rate}% exceeds 1% threshold")
        
        if p95_latency > 10000:
            issues.append(f"CRITICAL: p95 latency {p95_latency}ms exceeds 10s threshold")
        elif p95_latency > 5000:
            issues.append(f"WARNING: p95 latency {p95_latency}ms exceeds 5s threshold")
        
        status = "PASS" if not issues else ("FAIL" if any("CRITICAL" in i for i in issues) else "WARN")
        
        return {
            "status": status,
            "production_ready": status == "PASS",
            "issues": issues
        }


class LoadTester:
    """Main load testing class"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.report = LoadTestReport()
        self.tokens: Dict[int, str] = {}  # user_id -> token
        self.semaphore = None
    
    async def login(self, session: aiohttp.ClientSession, user_id: int) -> str:
        """Login and get token for a simulated user"""
        if user_id in self.tokens:
            return self.tokens[user_id]
        
        try:
            async with session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data.get("token")
                    self.tokens[user_id] = token
                    return token
        except Exception as e:
            print(f"Login failed for user {user_id}: {e}")
        return None
    
    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        token: str = None,
        json_data: Dict = None,
        timeout: int = 60
    ) -> RequestResult:
        """Make a single request and record result"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        start_time = time.time()
        
        try:
            async with self.semaphore:
                if method == "GET":
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        latency_ms = (time.time() - start_time) * 1000
                        await response.text()  # Consume response
                        return RequestResult(
                            endpoint=endpoint,
                            method=method,
                            status_code=response.status,
                            latency_ms=latency_ms,
                            success=200 <= response.status < 400
                        )
                elif method == "POST":
                    async with session.post(url, headers=headers, json=json_data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        latency_ms = (time.time() - start_time) * 1000
                        await response.text()
                        return RequestResult(
                            endpoint=endpoint,
                            method=method,
                            status_code=response.status,
                            latency_ms=latency_ms,
                            success=200 <= response.status < 400
                        )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                latency_ms=latency_ms,
                success=False,
                error="timeout"
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                latency_ms=latency_ms,
                success=False,
                error=str(type(e).__name__)
            )
    
    async def simulate_user(self, session: aiohttp.ClientSession, user_id: int, duration: int):
        """Simulate a single user making requests"""
        token = await self.login(session, user_id)
        if not token:
            return
        
        end_time = time.time() + duration
        
        # Define user actions with weights
        actions = [
            ("GET", "/api/auth/me", None, 30),  # Profile check - most common
            ("GET", "/api/performance/health", None, 20),  # Health check
            ("GET", "/api/comic-storybook/styles", None, 15),  # Comic storybook styles
            ("GET", "/api/comix/styles", None, 10),  # Comix styles
            ("GET", "/api/gif-maker/emotions", None, 10),  # GIF emotions
            ("GET", "/api/comix/credits-info", None, 10),  # Credits info
            ("GET", "/api/performance/metrics", None, 5),  # Performance metrics
        ]
        
        while time.time() < end_time:
            # Pick weighted random action
            total_weight = sum(w for _, _, _, w in actions)
            r = random.randint(1, total_weight)
            cumulative = 0
            
            for method, endpoint, data, weight in actions:
                cumulative += weight
                if r <= cumulative:
                    result = await self.make_request(session, method, endpoint, token, data)
                    self.report.add_result(result)
                    break
            
            # Small delay between requests (simulate think time)
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def run_load_test(self, num_users: int, duration: int, ramp_up: int = 0, max_concurrent: int = 100):
        """Run the full load test"""
        print(f"\n{'='*60}")
        print(f"LOAD TEST: {num_users} users for {duration}s")
        print(f"API URL: {self.base_url}")
        print(f"{'='*60}\n")
        
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.report.start_time = datetime.now(timezone.utc).isoformat()
        
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm up - login all users first
            print("Warming up - logging in users...")
            login_tasks = [self.login(session, i) for i in range(num_users)]
            await asyncio.gather(*login_tasks, return_exceptions=True)
            print(f"Logged in {len(self.tokens)} users\n")
            
            # Start user simulations with optional ramp-up
            tasks = []
            if ramp_up > 0:
                users_per_second = num_users / ramp_up
                for i in range(num_users):
                    task = asyncio.create_task(self.simulate_user(session, i, duration))
                    tasks.append(task)
                    if (i + 1) % max(1, int(users_per_second)) == 0:
                        await asyncio.sleep(1)
                        print(f"Ramped up {i + 1}/{num_users} users...")
            else:
                tasks = [asyncio.create_task(self.simulate_user(session, i, duration)) for i in range(num_users)]
            
            print(f"Running load test with {num_users} concurrent users...")
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.report.end_time = datetime.now(timezone.utc).isoformat()
        return self.report.get_summary()


async def run_generation_stress_test(num_users: int = 10):
    """Stress test the generation endpoints (actually creates jobs)"""
    print(f"\n{'='*60}")
    print(f"GENERATION STRESS TEST: {num_users} concurrent generations")
    print(f"{'='*60}\n")
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(
            f"{API_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        ) as response:
            data = await response.json()
            token = data.get("token")
        
        if not token:
            print("Failed to login")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Submit multiple generation requests
        async def submit_generation(user_num: int):
            start_time = time.time()
            try:
                # Use Reel Generator as it's quick
                async with session.post(
                    f"{API_URL}/api/reel-generator/generate",
                    headers=headers,
                    json={
                        "topic": f"Test topic {user_num} - funny cat video",
                        "platform": "instagram",
                        "duration": "30sec",
                        "style": "humorous"
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    latency = (time.time() - start_time) * 1000
                    data = await response.json()
                    return {
                        "user": user_num,
                        "status": response.status,
                        "latency_ms": latency,
                        "success": response.status == 200,
                        "data": data
                    }
            except Exception as e:
                return {
                    "user": user_num,
                    "status": 0,
                    "latency_ms": (time.time() - start_time) * 1000,
                    "success": False,
                    "error": str(e)
                }
        
        print(f"Submitting {num_users} generation requests...")
        tasks = [submit_generation(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful = sum(1 for r in results if r["success"])
    failed = num_users - successful
    latencies = [r["latency_ms"] for r in results]
    
    print(f"\n{'='*60}")
    print("GENERATION STRESS TEST RESULTS")
    print(f"{'='*60}")
    print(f"Total: {num_users}")
    print(f"Successful: {successful} ({successful/num_users*100:.1f}%)")
    print(f"Failed: {failed} ({failed/num_users*100:.1f}%)")
    print(f"Avg Latency: {statistics.mean(latencies):.2f}ms")
    print(f"p95 Latency: {sorted(latencies)[int(len(latencies)*0.95)]:.2f}ms")
    
    if failed > 0:
        print("\nErrors:")
        for r in results:
            if not r["success"]:
                print(f"  User {r['user']}: {r.get('error', r.get('data', 'Unknown error'))}")
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="CreatorStudio Load Testing Suite")
    parser.add_argument("--users", type=int, default=50, help="Number of simulated users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--ramp-up", type=int, default=0, help="Ramp-up time in seconds")
    parser.add_argument("--max-concurrent", type=int, default=100, help="Max concurrent connections")
    parser.add_argument("--stress-gen", action="store_true", help="Run generation stress test")
    parser.add_argument("--gen-users", type=int, default=10, help="Users for generation stress test")
    
    args = parser.parse_args()
    
    if args.stress_gen:
        await run_generation_stress_test(args.gen_users)
    else:
        tester = LoadTester(API_URL)
        report = await tester.run_load_test(
            num_users=args.users,
            duration=args.duration,
            ramp_up=args.ramp_up,
            max_concurrent=args.max_concurrent
        )
        
        print("\n" + "="*60)
        print("LOAD TEST REPORT")
        print("="*60)
        print(json.dumps(report, indent=2))
        
        # Save report
        report_path = f"/app/test_reports/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
