#!/usr/bin/env python3
"""
CreatorStudio AI - Extended Load Testing (25-50 Concurrent Users)
Tests API endpoints under concurrent load to validate performance and stability.
"""

import asyncio
import aiohttp
import time
import json
import os
import statistics
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict

# Configuration
API_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://visionary-qa.preview.emergentagent.com")
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

@dataclass
class RequestResult:
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: Optional[str] = None

@dataclass
class LoadTestReport:
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    endpoints_tested: Dict[str, dict]
    timestamp: str

class LoadTester:
    def __init__(self, api_url: str, concurrent_users: int = 25):
        self.api_url = api_url.rstrip('/')
        self.concurrent_users = concurrent_users
        self.results: List[RequestResult] = []
        self.token: Optional[str] = None
        
    async def login(self, session: aiohttp.ClientSession) -> str:
        """Get authentication token"""
        async with session.post(
            f"{self.api_url}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ) as resp:
            data = await resp.json()
            return data.get("token", "")
    
    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        json_data: dict = None,
        auth: bool = True
    ) -> RequestResult:
        """Make a single request and record results"""
        url = f"{self.api_url}{endpoint}"
        headers = {}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        start_time = time.time()
        try:
            async with session.request(
                method,
                url,
                json=json_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                response_time = time.time() - start_time
                success = 200 <= resp.status < 400
                return RequestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=resp.status,
                    response_time=response_time,
                    success=success
                )
        except Exception as e:
            response_time = time.time() - start_time
            return RequestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def run_user_session(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        endpoints: List[dict]
    ):
        """Simulate a single user making requests"""
        for ep in endpoints:
            result = await self.make_request(
                session,
                ep.get("method", "GET"),
                ep["endpoint"],
                ep.get("json"),
                ep.get("auth", True)
            )
            self.results.append(result)
            # Small delay between requests
            await asyncio.sleep(0.1)
    
    async def run_load_test(self, endpoints: List[dict], duration_seconds: int = 30):
        """Run load test with concurrent users"""
        print(f"\n{'='*60}")
        print(f"Starting Load Test: {self.concurrent_users} concurrent users")
        print(f"Duration: {duration_seconds} seconds")
        print(f"API URL: {self.api_url}")
        print(f"{'='*60}\n")
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Get auth token
            self.token = await self.login(session)
            if not self.token:
                print("ERROR: Failed to get authentication token")
                return None
            
            print(f"Authentication successful")
            
            start_time = time.time()
            tasks = []
            user_id = 0
            
            # Run for specified duration
            while time.time() - start_time < duration_seconds:
                # Launch batch of concurrent users
                batch_tasks = []
                for _ in range(self.concurrent_users):
                    user_id += 1
                    task = asyncio.create_task(
                        self.run_user_session(session, user_id, endpoints)
                    )
                    batch_tasks.append(task)
                
                await asyncio.gather(*batch_tasks)
                
                elapsed = time.time() - start_time
                print(f"Progress: {elapsed:.1f}s / {duration_seconds}s - {len(self.results)} requests completed")
        
        return self.generate_report(duration_seconds)
    
    def generate_report(self, duration_seconds: int) -> LoadTestReport:
        """Generate comprehensive test report"""
        if not self.results:
            return None
        
        response_times = [r.response_time for r in self.results]
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        # Per-endpoint stats
        endpoint_stats = defaultdict(lambda: {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "response_times": [],
            "errors": []
        })
        
        for r in self.results:
            stats = endpoint_stats[r.endpoint]
            stats["requests"] += 1
            stats["response_times"].append(r.response_time)
            if r.success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
                if r.error:
                    stats["errors"].append(r.error)
        
        # Calculate per-endpoint metrics
        for endpoint, stats in endpoint_stats.items():
            times = stats["response_times"]
            stats["avg_response_time"] = statistics.mean(times) if times else 0
            stats["p95_response_time"] = sorted(times)[int(len(times) * 0.95)] if times else 0
            stats["success_rate"] = (stats["successes"] / stats["requests"] * 100) if stats["requests"] else 0
            del stats["response_times"]  # Remove raw data
        
        sorted_times = sorted(response_times)
        report = LoadTestReport(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time=statistics.mean(response_times),
            p95_response_time=sorted_times[int(len(sorted_times) * 0.95)],
            p99_response_time=sorted_times[int(len(sorted_times) * 0.99)],
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            requests_per_second=len(self.results) / duration_seconds,
            error_rate=(len(failed) / len(self.results) * 100) if self.results else 0,
            endpoints_tested=dict(endpoint_stats),
            timestamp=datetime.utcnow().isoformat()
        )
        
        return report


# Endpoints to test
ENDPOINTS_TO_TEST = [
    {"endpoint": "/api/health/", "method": "GET", "auth": False},
    {"endpoint": "/api/cashfree/products", "method": "GET", "auth": False},
    {"endpoint": "/api/coloring-book/styles", "method": "GET", "auth": False},
    {"endpoint": "/api/gif-maker/templates", "method": "GET", "auth": False},
    {"endpoint": "/api/story-episode-creator/config", "method": "GET", "auth": True},
    {"endpoint": "/api/content-challenge-planner/config", "method": "GET", "auth": True},
    {"endpoint": "/api/caption-rewriter-pro/config", "method": "GET", "auth": True},
    {"endpoint": "/api/photo-to-comic/styles", "method": "GET", "auth": True},
    {"endpoint": "/api/reaction-gif/reactions", "method": "GET", "auth": True},
    {"endpoint": "/api/comic-storybook-v2/config", "method": "GET", "auth": True},
    {"endpoint": "/api/wallet/me", "method": "GET", "auth": True},
    {"endpoint": "/api/blueprint-library/catalog", "method": "GET", "auth": True},
]


async def run_tests():
    """Run load tests with increasing user counts"""
    results = {}
    
    for user_count in [25, 50]:
        print(f"\n{'#'*60}")
        print(f"LOAD TEST: {user_count} CONCURRENT USERS")
        print(f"{'#'*60}")
        
        tester = LoadTester(API_URL, concurrent_users=user_count)
        report = await tester.run_load_test(ENDPOINTS_TO_TEST, duration_seconds=30)
        
        if report:
            results[f"{user_count}_users"] = {
                "total_requests": report.total_requests,
                "successful_requests": report.successful_requests,
                "failed_requests": report.failed_requests,
                "success_rate": f"{100 - report.error_rate:.2f}%",
                "avg_response_time": f"{report.avg_response_time:.3f}s",
                "p95_response_time": f"{report.p95_response_time:.3f}s",
                "p99_response_time": f"{report.p99_response_time:.3f}s",
                "requests_per_second": f"{report.requests_per_second:.2f}",
                "endpoints": report.endpoints_tested
            }
            
            print(f"\n{'='*60}")
            print(f"RESULTS: {user_count} Concurrent Users")
            print(f"{'='*60}")
            print(f"Total Requests: {report.total_requests}")
            print(f"Successful: {report.successful_requests}")
            print(f"Failed: {report.failed_requests}")
            print(f"Success Rate: {100 - report.error_rate:.2f}%")
            print(f"Avg Response Time: {report.avg_response_time:.3f}s")
            print(f"P95 Response Time: {report.p95_response_time:.3f}s")
            print(f"P99 Response Time: {report.p99_response_time:.3f}s")
            print(f"Requests/Second: {report.requests_per_second:.2f}")
    
    # Save results
    report_path = "/app/test_reports/load_test_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "test_type": "Extended Load Test (25-50 Concurrent Users)",
            "timestamp": datetime.utcnow().isoformat(),
            "api_url": API_URL,
            "results": results
        }, f, indent=2)
    
    print(f"\n\nReport saved to: {report_path}")
    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
