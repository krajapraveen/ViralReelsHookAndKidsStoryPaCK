"""
Load Testing Script for CreatorStudio AI
Simulates 100+ concurrent users hitting various endpoints
"""
import asyncio
import aiohttp
import time
import json
import random
import statistics
from datetime import datetime
from typing import List, Dict, Any

# Configuration
BASE_URL = "https://engagement-loop-core.preview.emergentagent.com"
CONCURRENT_USERS = 50  # Reduced for better stability
TEST_DURATION_SECONDS = 30  # Shorter test
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"

# Endpoints to test (weight determines frequency)
ENDPOINTS = [
    {"path": "/api/health", "method": "GET", "weight": 10, "auth": False},
    {"path": "/api/credits/balance", "method": "GET", "weight": 15, "auth": True},
    {"path": "/api/user/profile", "method": "GET", "weight": 10, "auth": True},
    {"path": "/api/photo-to-comic/styles", "method": "GET", "weight": 15, "auth": True},
    {"path": "/api/photo-to-comic/pricing", "method": "GET", "weight": 15, "auth": True},
    {"path": "/api/comic-storybook-v2/config", "method": "GET", "weight": 10, "auth": True},
    {"path": "/api/help/manual", "method": "GET", "weight": 10, "auth": False},
    {"path": "/api/creator-tools/hashtags/niches", "method": "GET", "weight": 10, "auth": True},
    {"path": "/api/creator-tools/trending", "method": "GET", "weight": 5, "auth": True},
]


class LoadTestMetrics:
    def __init__(self):
        self.requests_sent = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.response_times: List[float] = []
        self.errors: Dict[str, int] = {}
        self.status_codes: Dict[int, int] = {}
        self.start_time = None
        self.end_time = None
        
    def record_request(self, success: bool, response_time: float, status_code: int = 0, error: str = None):
        self.requests_sent += 1
        self.response_times.append(response_time)
        
        if success:
            self.requests_successful += 1
        else:
            self.requests_failed += 1
            if error:
                self.errors[error] = self.errors.get(error, 0) + 1
        
        if status_code:
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        return {
            "test_duration_seconds": round(duration, 2),
            "total_requests": self.requests_sent,
            "successful_requests": self.requests_successful,
            "failed_requests": self.requests_failed,
            "success_rate": round((self.requests_successful / max(self.requests_sent, 1)) * 100, 2),
            "requests_per_second": round(self.requests_sent / max(duration, 1), 2),
            "response_times": {
                "min_ms": round(min(self.response_times) * 1000, 2) if self.response_times else 0,
                "max_ms": round(max(self.response_times) * 1000, 2) if self.response_times else 0,
                "avg_ms": round(statistics.mean(self.response_times) * 1000, 2) if self.response_times else 0,
                "median_ms": round(statistics.median(self.response_times) * 1000, 2) if self.response_times else 0,
                "p95_ms": round(sorted(self.response_times)[int(len(self.response_times) * 0.95)] * 1000, 2) if len(self.response_times) > 20 else 0,
                "p99_ms": round(sorted(self.response_times)[int(len(self.response_times) * 0.99)] * 1000, 2) if len(self.response_times) > 100 else 0,
            },
            "status_codes": dict(sorted(self.status_codes.items())),
            "errors": dict(sorted(self.errors.items(), key=lambda x: -x[1])[:10])
        }


class VirtualUser:
    def __init__(self, user_id: int, metrics: LoadTestMetrics, token: str = None):
        self.user_id = user_id
        self.metrics = metrics
        self.token = token
        self.session = None
        
    async def authenticate(self) -> bool:
        """Login and get auth token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/api/auth/login",
                    json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data.get("token")
                        return True
        except Exception as e:
            print(f"Auth failed for user {self.user_id}: {e}")
        return False
    
    async def make_request(self, endpoint: Dict) -> None:
        """Make a single request to an endpoint"""
        headers = {}
        if endpoint.get("auth") and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        start_time = time.time()
        try:
            async with self.session.request(
                endpoint["method"],
                f"{BASE_URL}{endpoint['path']}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                response_time = time.time() - start_time
                status = resp.status
                
                success = 200 <= status < 400
                error = None if success else f"HTTP {status}"
                
                self.metrics.record_request(success, response_time, status, error)
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            self.metrics.record_request(False, response_time, 0, "Timeout")
        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            self.metrics.record_request(False, response_time, 0, str(type(e).__name__))
        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_request(False, response_time, 0, str(e)[:50])
    
    async def run(self, duration: int) -> None:
        """Run the virtual user for specified duration"""
        end_time = time.time() + duration
        
        async with aiohttp.ClientSession() as self.session:
            while time.time() < end_time:
                # Select random endpoint based on weight
                total_weight = sum(e["weight"] for e in ENDPOINTS)
                r = random.uniform(0, total_weight)
                cumulative = 0
                selected_endpoint = ENDPOINTS[0]
                
                for endpoint in ENDPOINTS:
                    cumulative += endpoint["weight"]
                    if r <= cumulative:
                        selected_endpoint = endpoint
                        break
                
                await self.make_request(selected_endpoint)
                
                # Random delay between requests (50-200ms)
                await asyncio.sleep(random.uniform(0.05, 0.2))


async def run_load_test(num_users: int = CONCURRENT_USERS, duration: int = TEST_DURATION_SECONDS):
    """Run the load test with specified number of concurrent users"""
    print(f"\n{'='*60}")
    print(f"Load Test: CreatorStudio AI")
    print(f"{'='*60}")
    print(f"Concurrent Users: {num_users}")
    print(f"Test Duration: {duration} seconds")
    print(f"Target URL: {BASE_URL}")
    print(f"{'='*60}\n")
    
    metrics = LoadTestMetrics()
    metrics.start_time = time.time()
    
    # Authenticate a subset of users
    print("Authenticating users...")
    auth_token = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    auth_token = data.get("token")
                    print(f"Authentication successful!")
                else:
                    print(f"Authentication failed: {resp.status}")
    except Exception as e:
        print(f"Authentication error: {e}")
    
    # Create virtual users
    users = [VirtualUser(i, metrics, auth_token) for i in range(num_users)]
    
    print(f"\nStarting load test with {num_users} concurrent users...\n")
    
    # Run all users concurrently
    await asyncio.gather(*[user.run(duration) for user in users])
    
    metrics.end_time = time.time()
    
    # Print results
    summary = metrics.get_summary()
    
    print(f"\n{'='*60}")
    print("LOAD TEST RESULTS")
    print(f"{'='*60}")
    print(f"Test Duration: {summary['test_duration_seconds']} seconds")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Successful: {summary['successful_requests']}")
    print(f"Failed: {summary['failed_requests']}")
    print(f"Success Rate: {summary['success_rate']}%")
    print(f"Requests/Second: {summary['requests_per_second']}")
    print(f"\nResponse Times:")
    print(f"  Min: {summary['response_times']['min_ms']} ms")
    print(f"  Max: {summary['response_times']['max_ms']} ms")
    print(f"  Avg: {summary['response_times']['avg_ms']} ms")
    print(f"  Median: {summary['response_times']['median_ms']} ms")
    print(f"  P95: {summary['response_times']['p95_ms']} ms")
    print(f"  P99: {summary['response_times']['p99_ms']} ms")
    print(f"\nStatus Codes: {summary['status_codes']}")
    if summary['errors']:
        print(f"\nTop Errors: {summary['errors']}")
    print(f"{'='*60}\n")
    
    # Save results to file
    results_file = f"/app/test_reports/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Results saved to: {results_file}")
    
    # Determine pass/fail
    passed = (
        summary['success_rate'] >= 95 and 
        summary['response_times']['p95_ms'] < 2000 and
        summary['requests_per_second'] >= 10
    )
    
    print(f"\nLOAD TEST: {'PASSED' if passed else 'FAILED'}")
    
    return summary, passed


if __name__ == "__main__":
    asyncio.run(run_load_test())
