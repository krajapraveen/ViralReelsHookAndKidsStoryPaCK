"""
Test Suite for Production Scale Readiness - Iteration 457
Tests:
- System Health API endpoints (admin-only)
- Worker Queue architecture (8 queue types)
- Database indexes for funnel_events, asset_access_log, abuse_events
- k6 load test infrastructure
- Regression tests for funnel tracking and streaks APIs
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASS = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASS = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASS
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def user_token(api_client):
    """Get regular user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASS
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("User authentication failed - skipping user tests")


def auth_headers(token):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }


class TestSystemHealthOverview:
    """Tests for GET /api/admin/system-health/overview"""
    
    def test_overview_returns_full_health_data(self, api_client, admin_token):
        """Admin can access full system health overview"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields are present
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "queues" in data
        assert "workers" in data
        assert "completion_times" in data
        assert "errors" in data
        assert "dead_letter" in data
        assert "database" in data
        assert "request_latency" in data
        assert "asset_access" in data
        
        # Verify queue structure
        queues = data["queues"]
        assert "total_queued" in queues
        assert "depth_by_type" in queues
        
        # Verify workers structure
        workers = data["workers"]
        assert "total_processing" in workers
        assert "busy_by_queue" in workers
        assert "stuck_jobs" in workers
        
        # Verify errors structure
        errors = data["errors"]
        assert "failed_24h" in errors
        assert "completed_24h" in errors
        assert "error_rate_pct" in errors
        
        # Verify dead_letter structure
        dead_letter = data["dead_letter"]
        assert "total" in dead_letter
        assert "last_24h" in dead_letter
        
        # Verify database health structure
        db_health = data["database"]
        assert "status" in db_health
        assert "ping_ms" in db_health
        
        # Verify request latency structure (p50/p95/p99)
        req_latency = data["request_latency"]
        assert "total_requests" in req_latency
        assert "p50_ms" in req_latency
        assert "p95_ms" in req_latency
        assert "p99_ms" in req_latency
        
        # Verify asset access structure
        asset_access = data["asset_access"]
        assert "accesses_last_hour" in asset_access
        assert "abuse_events_last_hour" in asset_access
        
        print(f"✓ System health overview returned all required fields")
        print(f"  - Uptime: {data['uptime_seconds']}s")
        print(f"  - DB status: {db_health['status']}, ping: {db_health['ping_ms']}ms")
        print(f"  - Total queued: {queues['total_queued']}")
        print(f"  - Dead letter total: {dead_letter['total']}")
    
    def test_overview_rejects_non_admin(self, api_client, user_token):
        """Non-admin users should get 403"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected with 403")
    
    def test_overview_rejects_unauthenticated(self, api_client):
        """Unauthenticated requests should get 401"""
        response = api_client.get(f"{BASE_URL}/api/admin/system-health/overview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestSystemHealthQueues:
    """Tests for GET /api/admin/system-health/queues"""
    
    def test_queues_returns_all_8_queue_types(self, api_client, admin_token):
        """Queue detail endpoint returns all 8 queue types"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/queues",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "timestamp" in data
        assert "queues" in data
        
        queues = data["queues"]
        expected_queue_types = ["text", "image", "video", "audio", "export", "webhook", "analytics", "batch"]
        
        for qt in expected_queue_types:
            assert qt in queues, f"Missing queue type: {qt}"
            queue_info = queues[qt]
            assert "queued" in queue_info
            assert "processing" in queue_info
            assert "max_wait_seconds" in queue_info
            assert "failed_last_hour" in queue_info
        
        print(f"✓ All 8 queue types present: {expected_queue_types}")
        for qt in expected_queue_types:
            q = queues[qt]
            print(f"  - {qt}: queued={q['queued']}, processing={q['processing']}, wait={q['max_wait_seconds']}s")
    
    def test_queues_rejects_non_admin(self, api_client, user_token):
        """Non-admin users should get 403"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/queues",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected with 403")


class TestSystemHealthDeadLetter:
    """Tests for GET /api/admin/system-health/dead-letter"""
    
    def test_dead_letter_returns_contents(self, api_client, admin_token):
        """Dead letter endpoint returns queue contents"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/dead-letter",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        print(f"✓ Dead letter queue: {data['total']} total jobs")
    
    def test_dead_letter_accepts_limit_param(self, api_client, admin_token):
        """Dead letter endpoint accepts limit parameter"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/dead-letter?limit=5",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) <= 5
        print("✓ Dead letter limit parameter works")
    
    def test_dead_letter_rejects_non_admin(self, api_client, user_token):
        """Non-admin users should get 403"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/dead-letter",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 403
        print("✓ Non-admin correctly rejected with 403")


class TestSystemHealthStuckJobs:
    """Tests for GET /api/admin/system-health/stuck-jobs"""
    
    def test_stuck_jobs_returns_processing_jobs(self, api_client, admin_token):
        """Stuck jobs endpoint returns jobs stuck in PROCESSING"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/stuck-jobs",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        # If there are stuck jobs, verify structure
        if data["jobs"]:
            job = data["jobs"][0]
            assert "id" in job or "jobType" in job
        
        print(f"✓ Stuck jobs endpoint: {data['count']} stuck jobs found")
    
    def test_stuck_jobs_rejects_non_admin(self, api_client, user_token):
        """Non-admin users should get 403"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/stuck-jobs",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 403
        print("✓ Non-admin correctly rejected with 403")


class TestDatabaseHealth:
    """Tests for database health check in overview"""
    
    def test_database_health_returns_status_and_ping(self, api_client, admin_token):
        """Database health check returns status=UP with ping_ms"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        
        data = response.json()
        db_health = data["database"]
        
        assert db_health["status"] in ["UP", "DEGRADED", "DOWN"]
        assert "ping_ms" in db_health
        assert isinstance(db_health["ping_ms"], (int, float))
        
        # DB should be UP in normal operation
        assert db_health["status"] == "UP", f"DB status is {db_health['status']}, expected UP"
        
        print(f"✓ Database health: status={db_health['status']}, ping={db_health['ping_ms']}ms")


class TestRequestLatencyMetrics:
    """Tests for request latency tracking (p50/p95/p99)"""
    
    def test_request_latency_returns_percentiles(self, api_client, admin_token):
        """Request latency tracking returns p50/p95/p99 metrics"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        
        data = response.json()
        req_latency = data["request_latency"]
        
        assert "p50_ms" in req_latency
        assert "p95_ms" in req_latency
        assert "p99_ms" in req_latency
        assert "total_requests" in req_latency
        assert "total_errors" in req_latency
        assert "error_rate_pct" in req_latency
        assert "sample_size" in req_latency
        
        print(f"✓ Request latency metrics:")
        print(f"  - p50: {req_latency['p50_ms']}ms")
        print(f"  - p95: {req_latency['p95_ms']}ms")
        print(f"  - p99: {req_latency['p99_ms']}ms")
        print(f"  - Total requests: {req_latency['total_requests']}")
        print(f"  - Error rate: {req_latency['error_rate_pct']}%")


class TestWorkerQueueConfiguration:
    """Tests for worker queue configuration (8 queue types)"""
    
    def test_queue_config_has_8_types(self):
        """QUEUE_CONFIG has all 8 queue types with proper config"""
        # Import the module to verify configuration
        import sys
        sys.path.insert(0, '/app/backend')
        from services.worker_queues import QUEUE_CONFIG, QueueType
        
        expected_types = [
            QueueType.TEXT, QueueType.IMAGE, QueueType.VIDEO, QueueType.AUDIO,
            QueueType.EXPORT, QueueType.WEBHOOK, QueueType.ANALYTICS, QueueType.BATCH
        ]
        
        assert len(QUEUE_CONFIG) == 8, f"Expected 8 queue types, got {len(QUEUE_CONFIG)}"
        
        for qt in expected_types:
            assert qt in QUEUE_CONFIG, f"Missing queue type: {qt}"
            config = QUEUE_CONFIG[qt]
            
            # Verify required config fields
            assert "max_concurrent" in config
            assert "timeout_seconds" in config
            assert "retry_limit" in config
            assert "retry_delays" in config
            assert "job_types" in config
            
            print(f"✓ {qt.value}: max_concurrent={config['max_concurrent']}, timeout={config['timeout_seconds']}s, retries={config['retry_limit']}")
    
    def test_worker_queue_has_cancel_method(self):
        """WorkerQueue class has cancel_job method"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.worker_queues import WorkerQueue
        
        assert hasattr(WorkerQueue, 'cancel_job'), "WorkerQueue missing cancel_job method"
        print("✓ WorkerQueue has cancel_job method")
    
    def test_worker_queue_tracks_per_user_fairness(self):
        """WorkerQueue tracks per-user fairness via MAX_JOBS_PER_USER"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.worker_queues import MAX_JOBS_PER_USER, WorkerQueue, QueueType
        
        assert MAX_JOBS_PER_USER > 0, "MAX_JOBS_PER_USER should be positive"
        
        # Create instance to verify _active_user_map is initialized
        class MockDB:
            def __getitem__(self, key):
                return self
        
        async def mock_processor(job):
            pass
        
        queue = WorkerQueue(QueueType.TEXT, MockDB(), mock_processor)
        assert hasattr(queue, '_active_user_map'), "WorkerQueue instance missing _active_user_map for fairness tracking"
        print(f"✓ Per-user fairness: MAX_JOBS_PER_USER={MAX_JOBS_PER_USER}")
    
    def test_worker_queue_records_metrics(self):
        """WorkerQueue records dead_lettered, cancelled, p95, p99 metrics"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.worker_queues import WorkerQueue, QueueType
        
        # Create a mock queue to check metrics structure
        class MockDB:
            def __getitem__(self, key):
                return self
        
        async def mock_processor(job):
            pass
        
        queue = WorkerQueue(QueueType.TEXT, MockDB(), mock_processor)
        
        # Verify metrics structure
        assert "dead_lettered" in queue.metrics
        assert "cancelled" in queue.metrics
        assert "p95_processing_time" in queue.metrics
        assert "p99_processing_time" in queue.metrics
        assert "processing_times" in queue.metrics
        
        print("✓ WorkerQueue tracks dead_lettered, cancelled, p95, p99 metrics")


class TestDatabaseIndexes:
    """Tests for database indexes on funnel_events, asset_access_log, abuse_events"""
    
    def test_index_definitions_exist(self):
        """INDEX_DEFINITIONS includes funnel_events, asset_access_log, abuse_events"""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.database_indexes import INDEX_DEFINITIONS
        
        required_collections = ["funnel_events", "asset_access_log", "abuse_events"]
        
        for collection in required_collections:
            assert collection in INDEX_DEFINITIONS, f"Missing index definitions for {collection}"
            indexes = INDEX_DEFINITIONS[collection]
            assert len(indexes) > 0, f"No indexes defined for {collection}"
            print(f"✓ {collection}: {len(indexes)} indexes defined")
        
        # Verify specific indexes
        funnel_indexes = [idx["options"]["name"] for idx in INDEX_DEFINITIONS["funnel_events"]]
        assert "idx_funnel_session" in funnel_indexes
        assert "idx_funnel_timestamp" in funnel_indexes
        
        access_indexes = [idx["options"]["name"] for idx in INDEX_DEFINITIONS["asset_access_log"]]
        assert "idx_access_user_asset_time" in access_indexes
        assert "idx_access_timestamp" in access_indexes
        
        abuse_indexes = [idx["options"]["name"] for idx in INDEX_DEFINITIONS["abuse_events"]]
        assert "idx_abuse_user" in abuse_indexes
        assert "idx_abuse_timestamp" in abuse_indexes
        
        print("✓ All required indexes defined for funnel_events, asset_access_log, abuse_events")


class TestK6LoadTestInfrastructure:
    """Tests for k6 load test scripts existence"""
    
    def test_mixed_workload_script_exists(self):
        """k6 mixed-workload.js exists at /app/load-tests/"""
        assert os.path.exists("/app/load-tests/mixed-workload.js"), "mixed-workload.js not found"
        
        with open("/app/load-tests/mixed-workload.js", "r") as f:
            content = f.read()
        
        # Verify key components
        assert "k6/http" in content, "Missing k6/http import"
        assert "landingBrowseFlow" in content, "Missing landingBrowseFlow function"
        assert "authFlow" in content, "Missing authFlow function"
        assert "generationFlow" in content, "Missing generationFlow function"
        assert "adminFlow" in content, "Missing adminFlow function"
        assert "system-health/overview" in content, "Missing system-health endpoint test"
        
        print("✓ mixed-workload.js exists with all required flows")
    
    def test_scenarios_config_exists(self):
        """scenarios.json exists with smoke/ramp/spike/soak profiles"""
        assert os.path.exists("/app/load-tests/scenarios.json"), "scenarios.json not found"
        
        with open("/app/load-tests/scenarios.json", "r") as f:
            content = f.read()
        
        # Verify key scenarios (JSON with comments, so check as text)
        assert "smoke_100" in content, "Missing smoke_100 scenario"
        assert "ramp_500" in content, "Missing ramp_500 scenario"
        assert "ramp_1k" in content, "Missing ramp_1k scenario"
        assert "ramp_10k" in content, "Missing ramp_10k scenario"
        assert "spike" in content, "Missing spike scenario"
        assert "soak_1h" in content, "Missing soak_1h scenario"
        
        print("✓ scenarios.json exists with smoke/ramp/spike/soak profiles")
    
    def test_runbook_exists(self):
        """RUNBOOK.md exists at /app/load-tests/"""
        assert os.path.exists("/app/load-tests/RUNBOOK.md"), "RUNBOOK.md not found"
        
        with open("/app/load-tests/RUNBOOK.md", "r") as f:
            content = f.read()
        
        # Verify key sections
        assert "Prerequisites" in content, "Missing Prerequisites section"
        assert "Test Execution" in content, "Missing Test Execution section"
        assert "Success Criteria" in content, "Missing Success Criteria section"
        assert "10,000" in content or "10000" in content, "Missing 10K user reference"
        
        print("✓ RUNBOOK.md exists with required sections")


class TestRegressionFunnelTracking:
    """Regression tests for funnel tracking API"""
    
    def test_funnel_track_accepts_events(self, api_client):
        """POST /api/funnel/track accepts funnel events"""
        response = api_client.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "test_landing_view",
                "session_id": "test-session-457",
                "context": {"source_page": "landing", "device": "desktop"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Funnel tracking accepts events")
    
    def test_funnel_metrics_requires_admin(self, api_client, user_token, admin_token):
        """GET /api/funnel/metrics requires admin"""
        # Non-admin should get 403
        response = api_client.get(
            f"{BASE_URL}/api/funnel/metrics?days=7",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        
        # Admin should get 200
        response = api_client.get(
            f"{BASE_URL}/api/funnel/metrics?days=7",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        print("✓ Funnel metrics requires admin (regression passed)")


class TestRegressionStreaksAPI:
    """Regression tests for streaks API"""
    
    def test_streaks_my_requires_auth(self, api_client, user_token):
        """GET /api/streaks/my requires authentication"""
        # Unauthenticated should fail
        response = api_client.get(f"{BASE_URL}/api/streaks/my")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Authenticated should work
        response = api_client.get(
            f"{BASE_URL}/api/streaks/my",
            headers=auth_headers(user_token)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify streak data structure (API returns streak_days)
        assert "streak_days" in data or "current_streak" in data or "streak" in data or "days" in data
        print(f"✓ Streaks /my endpoint works (regression passed) - streak_days={data.get('streak_days', 'N/A')}")
    
    def test_streaks_social_proof_is_public(self, api_client):
        """GET /api/streaks/social-proof is public"""
        response = api_client.get(f"{BASE_URL}/api/streaks/social-proof")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Streaks social-proof is public (regression passed)")


class TestLatencyTrackingMiddleware:
    """Tests for LatencyTrackingMiddleware in server.py"""
    
    def test_middleware_records_requests(self, api_client, admin_token):
        """LatencyTrackingMiddleware records request latencies"""
        # Make a few requests to populate latency data
        for _ in range(5):
            api_client.get(f"{BASE_URL}/api/health/")
        
        # Check that latency data is being recorded
        response = api_client.get(
            f"{BASE_URL}/api/admin/system-health/overview",
            headers=auth_headers(admin_token)
        )
        assert response.status_code == 200
        
        data = response.json()
        req_latency = data["request_latency"]
        
        # Should have recorded some requests
        assert req_latency["total_requests"] > 0, "No requests recorded"
        assert req_latency["sample_size"] > 0, "No latency samples"
        
        print(f"✓ LatencyTrackingMiddleware recording: {req_latency['total_requests']} requests, {req_latency['sample_size']} samples")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
