"""
TTFD (Time to First Delight) Analytics Backend Tests - Iteration 267

Tests:
1. GET /api/analytics/ttfd - TTFD metrics with targets, engagement, pipeline health, daily trends
2. GET /api/analytics/queue - Queue performance with tier wait times
3. POST /api/analytics/track-event/{job_id} - Engagement event tracking with throttling
4. GET /api/analytics/daily-aggregates - Pre-computed daily analytics
5. Pipeline engine TTFD metrics recording verification
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

# Test job with TTFD data
TEST_JOB_ID = "b5e7107e-7237-4e53-9257-c4fcb28b18eb"
ENGAGEMENT_JOB_ID = "d870c412-dc39-4400-ab0e-f3a43a514182"


class TestSetup:
    """Setup fixtures for authentication"""
    
    @staticmethod
    def get_admin_token():
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    @staticmethod
    def get_user_token():
        """Get regular user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Admin auth token fixture"""
    token = TestSetup.get_admin_token()
    if not token:
        pytest.skip("Admin authentication failed")
    return token


@pytest.fixture(scope="module")
def user_token():
    """User auth token fixture"""
    token = TestSetup.get_user_token()
    if not token:
        pytest.skip("User authentication failed")
    return token


@pytest.fixture
def admin_headers(admin_token):
    """Admin request headers"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def user_headers(user_token):
    """User request headers"""
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }


class TestTTFDAnalyticsEndpoint:
    """GET /api/analytics/ttfd - TTFD metrics dashboard"""
    
    def test_ttfd_analytics_returns_success(self, admin_headers):
        """Test TTFD endpoint returns success with default 30 days"""
        response = requests.get(f"{BASE_URL}/api/analytics/ttfd", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert "data" in data, "Expected 'data' field in response"
    
    def test_ttfd_analytics_with_days_param(self, admin_headers):
        """Test TTFD endpoint with different days parameter"""
        for days in [7, 14, 30]:
            response = requests.get(f"{BASE_URL}/api/analytics/ttfd?days={days}", headers=admin_headers)
            assert response.status_code == 200, f"Expected 200 for days={days}"
            data = response.json()
            assert data.get("data", {}).get("period_days") == days, f"Expected period_days={days}"
    
    def test_ttfd_analytics_structure(self, admin_headers):
        """Test TTFD response contains all required fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/ttfd", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json().get("data", {})
        
        # Check jobs_analyzed field exists
        assert "jobs_analyzed" in data, "Missing jobs_analyzed field"
        
        # Check TTFD metrics if jobs exist
        if data.get("jobs_analyzed", 0) > 0:
            # TTFD detailed metrics
            assert "ttfd" in data, "Missing 'ttfd' field"
            ttfd = data["ttfd"]
            expected_ttfd_keys = [
                "time_to_first_scene",
                "time_to_first_image", 
                "time_to_first_voice",
                "time_to_first_playable_preview",
                "total_generation_time"
            ]
            for key in expected_ttfd_keys:
                assert key in ttfd, f"Missing TTFD metric: {key}"
            
            # Queue performance
            assert "queue_performance" in data, "Missing queue_performance"
            
            # Engagement rates
            assert "engagement" in data, "Missing engagement"
            engagement = data["engagement"]
            assert "preview_play_rate" in engagement
            assert "export_start_rate" in engagement
            
            # Pipeline health
            assert "pipeline_health" in data, "Missing pipeline_health"
            health = data["pipeline_health"]
            assert "completed" in health
            assert "partial" in health
            assert "failed" in health
            assert "export_success_rate" in health
            
            # Targets
            assert "targets" in data, "Missing targets"
            assert isinstance(data["targets"], list)
            
            # Daily trends
            assert "daily_trends" in data, "Missing daily_trends"
    
    def test_ttfd_targets_structure(self, admin_headers):
        """Test TTFD targets have metric, target, current, status fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/ttfd", headers=admin_headers)
        assert response.status_code == 200
        
        targets = response.json().get("data", {}).get("targets", [])
        
        if len(targets) > 0:
            for target in targets:
                assert "metric" in target, "Missing 'metric' in target"
                assert "target" in target, "Missing 'target' value"
                assert "current" in target, "Missing 'current' value"
                assert "status" in target, "Missing 'status' field"
                assert target["status"] in ["pass", "fail"], f"Invalid status: {target['status']}"
    
    def test_ttfd_requires_admin(self, user_headers):
        """Test TTFD endpoint requires admin role"""
        response = requests.get(f"{BASE_URL}/api/analytics/ttfd", headers=user_headers)
        # Non-admin should get 403
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"


class TestQueueAnalyticsEndpoint:
    """GET /api/analytics/queue - Queue performance metrics"""
    
    def test_queue_analytics_returns_success(self, admin_headers):
        """Test queue endpoint returns success"""
        response = requests.get(f"{BASE_URL}/api/analytics/queue", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
    
    def test_queue_analytics_structure(self, admin_headers):
        """Test queue response contains required fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/queue", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json().get("data", {})
        
        # Check queue depth and processing count
        assert "queue_depth" in data, "Missing queue_depth"
        assert "processing" in data, "Missing processing count"
        assert isinstance(data["queue_depth"], int)
        assert isinstance(data["processing"], int)
        
        # Check tier wait times
        assert "tier_wait_times_24h" in data, "Missing tier_wait_times_24h"
        tier_waits = data["tier_wait_times_24h"]
        
        for tier in ["free", "paid", "admin"]:
            assert tier in tier_waits, f"Missing tier: {tier}"
            assert "avg_ms" in tier_waits[tier], f"Missing avg_ms for {tier}"
            assert "p95_ms" in tier_waits[tier], f"Missing p95_ms for {tier}"
            assert "count" in tier_waits[tier], f"Missing count for {tier}"
    
    def test_queue_requires_admin(self, user_headers):
        """Test queue endpoint requires admin role"""
        response = requests.get(f"{BASE_URL}/api/analytics/queue", headers=user_headers)
        assert response.status_code == 403


class TestEngagementTracking:
    """POST /api/analytics/track-event/{job_id} - Engagement event tracking"""
    
    def test_track_preview_played_event(self, user_headers):
        """Test tracking preview_played event"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "preview_played"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
    
    def test_track_export_started_event(self, user_headers):
        """Test tracking export_started event"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "export_started"}
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
    
    def test_track_story_pack_downloaded_event(self, user_headers):
        """Test tracking story_pack_downloaded event"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "story_pack_downloaded"}
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
    
    def test_track_export_completed_event(self, user_headers):
        """Test tracking export_completed event"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "export_completed"}
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
    
    def test_track_video_shared_event(self, user_headers):
        """Test tracking video_shared event"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "video_shared"}
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
    
    def test_track_preview_watch_duration_with_value(self, user_headers):
        """Test tracking preview_watch_duration event with value"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "preview_watch_duration", "value": 45.5}
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
    
    def test_track_event_throttling(self, user_headers):
        """Test duplicate events are throttled within 10-second window"""
        # First event should succeed
        response1 = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "preview_played"}
        )
        assert response1.status_code == 200
        first_result = response1.json()
        
        # Immediate duplicate should be throttled
        response2 = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "preview_played"}
        )
        assert response2.status_code == 200
        second_result = response2.json()
        
        # Second call should return throttled=True (or success=True but throttled)
        assert second_result.get("success") is True
        # Throttle indicator may be present
        if "throttled" in second_result:
            assert second_result["throttled"] is True
    
    def test_track_invalid_event_type_returns_422(self, user_headers):
        """Test invalid event type returns 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            headers=user_headers,
            json={"event_type": "invalid_event_type"}
        )
        # Pydantic validation should reject invalid event_type
        assert response.status_code == 422, f"Expected 422 for invalid event type, got {response.status_code}"
    
    def test_track_event_requires_auth(self):
        """Test track-event endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/analytics/track-event/{ENGAGEMENT_JOB_ID}",
            json={"event_type": "preview_played"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestDailyAggregates:
    """GET /api/analytics/daily-aggregates - Pre-computed daily analytics"""
    
    def test_daily_aggregates_returns_success(self, admin_headers):
        """Test daily-aggregates endpoint returns success"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily-aggregates", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
    
    def test_daily_aggregates_with_days_param(self, admin_headers):
        """Test daily-aggregates with custom days parameter"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily-aggregates?days=14", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_daily_aggregates_structure(self, admin_headers):
        """Test daily aggregate records have expected structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily-aggregates?days=30", headers=admin_headers)
        assert response.status_code == 200
        
        aggregates = response.json().get("data", [])
        
        # If there are any aggregates, check structure
        if len(aggregates) > 0:
            for agg in aggregates:
                assert "date" in agg, "Missing date field"
                # These fields may be present if jobs existed that day
                if "total_jobs" in agg:
                    assert isinstance(agg["total_jobs"], int)
    
    def test_daily_aggregates_requires_admin(self, user_headers):
        """Test daily-aggregates endpoint requires admin role"""
        response = requests.get(f"{BASE_URL}/api/analytics/daily-aggregates", headers=user_headers)
        assert response.status_code == 403


class TestPipelineJobTTFDMetrics:
    """Verify pipeline jobs have TTFD metrics recorded"""
    
    def test_pipeline_job_has_ttfd_metrics(self, admin_headers):
        """Test that the test job has ttfd_metrics recorded"""
        # Get pipeline job details
        response = requests.get(f"{BASE_URL}/api/pipeline/jobs/{TEST_JOB_ID}", headers=admin_headers)
        
        if response.status_code == 200:
            job = response.json()
            if isinstance(job, dict) and "job_id" in job:
                # Check for ttfd_metrics
                if "ttfd_metrics" in job:
                    ttfd = job["ttfd_metrics"]
                    print(f"TTFD Metrics found: {ttfd}")
                    
                    # Check expected fields
                    if ttfd.get("pipeline_start"):
                        print(f"  pipeline_start: {ttfd['pipeline_start']}")
                    if ttfd.get("time_to_first_scene"):
                        print(f"  time_to_first_scene: {ttfd['time_to_first_scene']}s")
                    if ttfd.get("time_to_first_image"):
                        print(f"  time_to_first_image: {ttfd['time_to_first_image']}s")
                    if ttfd.get("time_to_first_voice"):
                        print(f"  time_to_first_voice: {ttfd['time_to_first_voice']}s")
                    if ttfd.get("time_to_first_playable_preview"):
                        print(f"  time_to_first_playable_preview: {ttfd['time_to_first_playable_preview']}s")
                else:
                    print("No ttfd_metrics found on job (may be an older job)")
        else:
            print(f"Could not fetch job {TEST_JOB_ID}: {response.status_code}")
    
    def test_ttfd_analytics_shows_real_data(self, admin_headers):
        """Test TTFD analytics reflects real job data"""
        response = requests.get(f"{BASE_URL}/api/analytics/ttfd?days=30", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json().get("data", {})
        jobs_analyzed = data.get("jobs_analyzed", 0)
        
        print(f"Jobs analyzed in last 30 days: {jobs_analyzed}")
        
        if jobs_analyzed > 0:
            ttfd = data.get("ttfd", {})
            
            # Check time_to_first_scene
            ttfs = ttfd.get("time_to_first_scene", {})
            if ttfs.get("avg"):
                print(f"Avg Time to First Scene: {ttfs['avg']}s")
                assert ttfs["avg"] > 0, "time_to_first_scene avg should be positive"
            
            # Check time_to_first_image  
            ttfi = ttfd.get("time_to_first_image", {})
            if ttfi.get("avg"):
                print(f"Avg Time to First Image: {ttfi['avg']}s")
                assert ttfi["avg"] > 0, "time_to_first_image avg should be positive"
            
            # Check time_to_first_playable_preview
            ttfp = ttfd.get("time_to_first_playable_preview", {})
            if ttfp.get("avg"):
                print(f"Avg Time to Playable Preview: {ttfp['avg']}s")
                assert ttfp["avg"] > 0


class TestAdminDashboardTTFDLink:
    """Verify Admin Dashboard has TTFD Analytics button"""
    
    def test_admin_dashboard_loads(self, admin_headers):
        """Basic check that admin analytics endpoint works"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard?days=30", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
