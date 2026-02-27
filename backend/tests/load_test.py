"""
Load Testing Script for CreatorStudio AI
==========================================
Tests concurrent user access and API performance.

Usage:
    python load_test.py --users 100 --duration 60 --target all

Requirements:
    pip install aiohttp asyncio
"""
import asyncio
import aiohttp
import time
import argparse
import json
import random
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TestResult:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str = ""


@dataclass
class LoadTestReport:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0
    requests_per_second: float = 0
    endpoints_tested: Dict[str, Dict] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class LoadTester:
    """Concurrent load tester for API endpoints"""
    
    def __init__(self, base_url: str, num_users: int = 100, duration_seconds: int = 60):
        self.base_url = base_url.rstrip('/')
        self.num_users = num_users
        self.duration = duration_seconds
        self.results: List[TestResult] = []
        self.token = None
        self.admin_token = None
        
        # Test endpoints configuration
        self.public_endpoints = [
            ("GET", "/api/health"),
            ("GET", "/api/public/products"),
            ("GET", "/api/pdf-protection/config"),
            ("GET", "/api/video-stream/config"),
        ]
        
        self.auth_endpoints = [
            ("GET", "/api/wallet/me"),
            ("GET", "/api/dashboard/stats"),
            ("GET", "/api/instagram-bio/config"),
            ("GET", "/api/comment-reply/config"),
            ("GET", "/api/yt-thumbnail-text/config"),
            ("GET", "/api/brand-story/config"),
            ("GET", "/api/offer-generator/config"),
            ("GET", "/api/story-hooks/config"),
            ("GET", "/api/daily-viral-ideas/config"),
            ("GET", "/api/bedtime-stories/config"),
        ]
        
        self.admin_endpoints = [
            ("GET", "/api/admin/users"),
            ("GET", "/api/admin/dashboard"),
            ("GET", "/api/system-resilience/dashboard"),
        ]
    
    async def authenticate(self, session: aiohttp.ClientSession) -> tuple:
        """Get authentication tokens"""
        # Demo user login
        try:
            async with session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": "demo@example.com", "password": "Password123!"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get("token")
        except Exception as e:
            print(f"Demo auth failed: {e}")
        
        # Admin user login
        try:
            async with session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.admin_token = data.get("token")
        except Exception as e:
            print(f"Admin auth failed: {e}")
        
        return self.token, self.admin_token
    
    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        token: str = None
    ) -> TestResult:
        """Make a single API request and record results"""
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        start_time = time.time()
        
        try:
            async with session.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                response_time = (time.time() - start_time) * 1000
                success = resp.status in [200, 201, 204]
                
                return TestResult(
                    endpoint=endpoint,
                    method=method,
                    status_code=resp.status,
                    response_time_ms=response_time,
                    success=success
                )
        except asyncio.TimeoutError:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    async def user_simulation(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        target: str
    ):
        """Simulate a single user's requests"""
        endpoints = []
        
        if target in ["all", "public"]:
            endpoints.extend([(e, None) for e in self.public_endpoints])
        
        if target in ["all", "auth"] and self.token:
            endpoints.extend([(e, self.token) for e in self.auth_endpoints])
        
        if target in ["all", "admin"] and self.admin_token:
            endpoints.extend([(e, self.admin_token) for e in self.admin_endpoints])
        
        # Shuffle to simulate realistic usage
        random.shuffle(endpoints)
        
        for (method, endpoint), token in endpoints:
            result = await self.make_request(session, method, endpoint, token)
            self.results.append(result)
            
            # Small delay between requests (100-500ms)
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def run_load_test(self, target: str = "all") -> LoadTestReport:
        """Run the load test with specified number of concurrent users"""
        print(f"\n{'='*60}")
        print(f"Load Test Configuration")
        print(f"{'='*60}")
        print(f"Base URL: {self.base_url}")
        print(f"Concurrent Users: {self.num_users}")
        print(f"Duration: {self.duration} seconds")
        print(f"Target: {target}")
        print(f"{'='*60}\n")
        
        connector = aiohttp.TCPConnector(limit=self.num_users * 2)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Authenticate first
            print("Authenticating test users...")
            await self.authenticate(session)
            
            if not self.token:
                print("Warning: Demo user authentication failed")
            if not self.admin_token:
                print("Warning: Admin authentication failed")
            
            print(f"\nStarting load test with {self.num_users} concurrent users...")
            start_time = time.time()
            
            # Create user tasks
            tasks = [
                self.user_simulation(session, i, target)
                for i in range(self.num_users)
            ]
            
            # Run all users concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
        
        # Generate report
        return self._generate_report(total_time)
    
    def _generate_report(self, total_time: float) -> LoadTestReport:
        """Generate test report from results"""
        report = LoadTestReport()
        
        if not self.results:
            return report
        
        report.total_requests = len(self.results)
        report.successful_requests = sum(1 for r in self.results if r.success)
        report.failed_requests = report.total_requests - report.successful_requests
        
        response_times = [r.response_time_ms for r in self.results]
        report.avg_response_time_ms = sum(response_times) / len(response_times)
        report.min_response_time_ms = min(response_times)
        report.max_response_time_ms = max(response_times)
        report.requests_per_second = report.total_requests / total_time
        
        # Group by endpoint
        endpoint_stats = defaultdict(lambda: {"count": 0, "success": 0, "times": []})
        for result in self.results:
            key = f"{result.method} {result.endpoint}"
            endpoint_stats[key]["count"] += 1
            endpoint_stats[key]["success"] += 1 if result.success else 0
            endpoint_stats[key]["times"].append(result.response_time_ms)
            
            if result.error:
                report.errors.append(f"{key}: {result.error}")
        
        for endpoint, stats in endpoint_stats.items():
            report.endpoints_tested[endpoint] = {
                "total": stats["count"],
                "successful": stats["success"],
                "success_rate": round(stats["success"] / stats["count"] * 100, 1),
                "avg_time_ms": round(sum(stats["times"]) / len(stats["times"]), 1),
                "min_time_ms": round(min(stats["times"]), 1),
                "max_time_ms": round(max(stats["times"]), 1)
            }
        
        return report
    
    def print_report(self, report: LoadTestReport):
        """Print formatted test report"""
        print(f"\n{'='*60}")
        print(f"LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Requests: {report.total_requests}")
        print(f"Successful: {report.successful_requests}")
        print(f"Failed: {report.failed_requests}")
        print(f"Success Rate: {report.successful_requests/report.total_requests*100:.1f}%")
        print(f"\nPerformance:")
        print(f"  Requests/Second: {report.requests_per_second:.2f}")
        print(f"  Avg Response Time: {report.avg_response_time_ms:.1f}ms")
        print(f"  Min Response Time: {report.min_response_time_ms:.1f}ms")
        print(f"  Max Response Time: {report.max_response_time_ms:.1f}ms")
        
        print(f"\n{'='*60}")
        print("ENDPOINT BREAKDOWN")
        print(f"{'='*60}")
        for endpoint, stats in sorted(report.endpoints_tested.items()):
            print(f"\n{endpoint}")
            print(f"  Requests: {stats['total']} | Success Rate: {stats['success_rate']}%")
            print(f"  Response Time: {stats['avg_time_ms']}ms avg | {stats['min_time_ms']}ms min | {stats['max_time_ms']}ms max")
        
        if report.errors:
            print(f"\n{'='*60}")
            print("ERRORS (first 10)")
            print(f"{'='*60}")
            for error in report.errors[:10]:
                print(f"  - {error}")
        
        print(f"\n{'='*60}")
        
        # Overall assessment
        success_rate = report.successful_requests / report.total_requests * 100 if report.total_requests > 0 else 0
        avg_time = report.avg_response_time_ms
        
        print("\nPRODUCTION READINESS ASSESSMENT:")
        
        issues = []
        if success_rate < 95:
            issues.append(f"Success rate ({success_rate:.1f}%) below 95% threshold")
        if avg_time > 500:
            issues.append(f"Average response time ({avg_time:.1f}ms) above 500ms threshold")
        if report.failed_requests > report.total_requests * 0.05:
            issues.append(f"Error rate too high ({report.failed_requests} failures)")
        
        if not issues:
            print("  READY FOR PRODUCTION")
            print("  All metrics within acceptable thresholds")
        else:
            print("  NEEDS ATTENTION:")
            for issue in issues:
                print(f"    - {issue}")
        
        print(f"{'='*60}\n")
        
        return success_rate >= 95 and avg_time <= 500


def main():
    parser = argparse.ArgumentParser(description="Load Test CreatorStudio AI")
    parser.add_argument("--url", default="https://studio-audit.preview.emergentagent.com", help="Base URL")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--target", choices=["all", "public", "auth", "admin"], default="all", help="Endpoints to test")
    parser.add_argument("--output", help="Output file for JSON report")
    
    args = parser.parse_args()
    
    tester = LoadTester(args.url, args.users, args.duration)
    
    # Run test
    report = asyncio.run(tester.run_load_test(args.target))
    
    # Print results
    production_ready = tester.print_report(report)
    
    # Save JSON report if requested
    if args.output:
        report_dict = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "url": args.url,
                "users": args.users,
                "duration": args.duration,
                "target": args.target
            },
            "results": {
                "total_requests": report.total_requests,
                "successful_requests": report.successful_requests,
                "failed_requests": report.failed_requests,
                "success_rate": report.successful_requests / report.total_requests * 100 if report.total_requests else 0,
                "requests_per_second": report.requests_per_second,
                "avg_response_time_ms": report.avg_response_time_ms,
                "min_response_time_ms": report.min_response_time_ms,
                "max_response_time_ms": report.max_response_time_ms
            },
            "endpoints": report.endpoints_tested,
            "errors": report.errors[:50],
            "production_ready": production_ready
        }
        
        with open(args.output, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"Report saved to {args.output}")
    
    return 0 if production_ready else 1


if __name__ == "__main__":
    exit(main())
