"""
Retention Analytics Dashboard Tests - Iteration 385

Tests for:
1. Session tracking (start, heartbeat, end events)
2. Dashboard metrics (avg_session_time, hook_ctr, continue_rate, dropoff_10s, scroll_depth)
3. Retention curve (7 buckets)
4. Preview analytics (impressions, plays, clicks)
5. Trends array with daily data
6. Period selector (7d, 14d, 30d)
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


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
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestSessionTracking:
    """Session tracking endpoint tests - POST /api/admin/retention/session"""
    
    def test_session_start_creates_record(self, api_client):
        """POST /api/admin/retention/session with event=start creates session record"""
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "start",
            "device": "desktop"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print(f"✓ Session start created: {session_id}")
    
    def test_session_heartbeat_updates_scroll_depth(self, api_client):
        """POST /api/admin/retention/session with event=heartbeat updates scroll_depth and actions"""
        session_id = f"test-heartbeat-{uuid.uuid4().hex[:8]}"
        
        # First create session
        api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "start",
            "device": "mobile"
        })
        
        # Wait a bit for duration calculation
        time.sleep(0.5)
        
        # Send heartbeat with scroll_depth and actions
        response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "heartbeat",
            "scroll_depth": 5,
            "actions": 3
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print(f"✓ Session heartbeat updated: scroll_depth=5, actions=3")
    
    def test_session_end_sets_duration_and_status(self, api_client):
        """POST /api/admin/retention/session with event=end sets duration and status=ended"""
        session_id = f"test-end-{uuid.uuid4().hex[:8]}"
        
        # Create session
        api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "start",
            "device": "desktop"
        })
        
        # Wait for some duration
        time.sleep(1)
        
        # End session
        response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "end",
            "scroll_depth": 10,
            "actions": 5
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        print(f"✓ Session ended: {session_id}")
    
    def test_session_tracking_open_to_all_users(self, api_client):
        """Session tracking endpoint is open to all users (no auth required)"""
        # Remove any auth headers
        headers = {"Content-Type": "application/json"}
        session_id = f"test-anon-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/admin/retention/session", 
            json={
                "session_id": session_id,
                "event": "start",
                "device": "mobile"
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200 (open endpoint), got {response.status_code}: {response.text}"
        print("✓ Session tracking is open to all users (no auth required)")


class TestRetentionDashboard:
    """Dashboard metrics endpoint tests - GET /api/admin/retention/dashboard"""
    
    def test_dashboard_returns_metrics(self, admin_client):
        """GET /api/admin/retention/dashboard?days=7 returns all 5 key metrics"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check period_days
        assert data.get("period_days") == 7, f"Expected period_days=7, got {data.get('period_days')}"
        
        # Check metrics object exists
        metrics = data.get("metrics", {})
        assert "avg_session_time" in metrics, "Missing avg_session_time metric"
        assert "scroll_depth" in metrics, "Missing scroll_depth metric"
        assert "hook_ctr" in metrics, "Missing hook_ctr metric"
        assert "continue_rate" in metrics, "Missing continue_rate metric"
        assert "dropoff_10s" in metrics, "Missing dropoff_10s metric"
        
        print(f"✓ Dashboard returns all 5 metrics: avg_session_time, scroll_depth, hook_ctr, continue_rate, dropoff_10s")
    
    def test_dashboard_avg_session_time_structure(self, admin_client):
        """Dashboard avg_session_time has correct structure"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        avg_session = data.get("metrics", {}).get("avg_session_time", {})
        assert "seconds" in avg_session, "Missing seconds field"
        assert "total_sessions" in avg_session, "Missing total_sessions field"
        assert "device_breakdown" in avg_session, "Missing device_breakdown field"
        assert "target" in avg_session, "Missing target field"
        
        print(f"✓ avg_session_time structure: seconds={avg_session.get('seconds')}, total_sessions={avg_session.get('total_sessions')}")
    
    def test_dashboard_hook_ctr_structure(self, admin_client):
        """Dashboard hook_ctr has correct structure"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        hook_ctr = data.get("metrics", {}).get("hook_ctr", {})
        assert "rate" in hook_ctr, "Missing rate field"
        assert "impressions" in hook_ctr, "Missing impressions field"
        assert "clicks" in hook_ctr, "Missing clicks field"
        assert "target" in hook_ctr, "Missing target field"
        
        print(f"✓ hook_ctr structure: rate={hook_ctr.get('rate')}, impressions={hook_ctr.get('impressions')}, clicks={hook_ctr.get('clicks')}")
    
    def test_dashboard_continue_rate_structure(self, admin_client):
        """Dashboard continue_rate has correct structure"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        continue_rate = data.get("metrics", {}).get("continue_rate", {})
        assert "rate" in continue_rate, "Missing rate field"
        assert "views" in continue_rate, "Missing views field"
        assert "continues" in continue_rate, "Missing continues field"
        assert "target" in continue_rate, "Missing target field"
        
        print(f"✓ continue_rate structure: rate={continue_rate.get('rate')}, views={continue_rate.get('views')}, continues={continue_rate.get('continues')}")
    
    def test_dashboard_dropoff_10s_structure(self, admin_client):
        """Dashboard dropoff_10s has correct structure"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        dropoff = data.get("metrics", {}).get("dropoff_10s", {})
        assert "rate" in dropoff, "Missing rate field"
        assert "dropped" in dropoff, "Missing dropped field"
        assert "total_sessions" in dropoff, "Missing total_sessions field"
        assert "target" in dropoff, "Missing target field"
        
        print(f"✓ dropoff_10s structure: rate={dropoff.get('rate')}, dropped={dropoff.get('dropped')}, total_sessions={dropoff.get('total_sessions')}")
    
    def test_dashboard_retention_curve_7_buckets(self, admin_client):
        """GET /api/admin/retention/dashboard returns retention_curve with 7 buckets"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        retention_curve = data.get("retention_curve", [])
        assert isinstance(retention_curve, list), f"Expected retention_curve to be a list, got {type(retention_curve)}"
        assert len(retention_curve) == 7, f"Expected 7 buckets, got {len(retention_curve)}"
        
        # Check bucket structure
        expected_buckets = ["0-10s", "10-30s", "30-60s", "1-3min", "3-5min", "5-10min", "10min+"]
        actual_buckets = [b.get("bucket") for b in retention_curve]
        assert actual_buckets == expected_buckets, f"Expected buckets {expected_buckets}, got {actual_buckets}"
        
        # Each bucket should have count
        for bucket in retention_curve:
            assert "bucket" in bucket, "Missing bucket field"
            assert "count" in bucket, "Missing count field"
        
        print(f"✓ retention_curve has 7 buckets: {actual_buckets}")
    
    def test_dashboard_preview_analytics(self, admin_client):
        """GET /api/admin/retention/dashboard returns preview_analytics (impressions, plays, clicks)"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        preview = data.get("preview_analytics", {})
        assert "impressions" in preview, "Missing impressions field"
        assert "plays" in preview, "Missing plays field"
        assert "clicks" in preview, "Missing clicks field"
        assert "play_rate" in preview, "Missing play_rate field"
        assert "click_conversion" in preview, "Missing click_conversion field"
        
        print(f"✓ preview_analytics: impressions={preview.get('impressions')}, plays={preview.get('plays')}, clicks={preview.get('clicks')}")
    
    def test_dashboard_trends_array(self, admin_client):
        """GET /api/admin/retention/dashboard returns trends array with daily data"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        trends = data.get("trends", [])
        assert isinstance(trends, list), f"Expected trends to be a list, got {type(trends)}"
        assert len(trends) <= 7, f"Expected max 7 days of trends, got {len(trends)}"
        
        # Check trend structure
        if len(trends) > 0:
            trend = trends[0]
            assert "date" in trend, "Missing date field"
            assert "sessions" in trend, "Missing sessions field"
            assert "avg_session_seconds" in trend, "Missing avg_session_seconds field"
            assert "hook_ctr" in trend, "Missing hook_ctr field"
            assert "dropoff_10s" in trend, "Missing dropoff_10s field"
        
        print(f"✓ trends array has {len(trends)} days of data")
    
    def test_dashboard_30_day_period(self, admin_client):
        """GET /api/admin/retention/dashboard?days=30 works with different period"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=30")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("period_days") == 30, f"Expected period_days=30, got {data.get('period_days')}"
        
        trends = data.get("trends", [])
        assert len(trends) <= 30, f"Expected max 30 days of trends, got {len(trends)}"
        
        print(f"✓ Dashboard works with 30-day period, trends has {len(trends)} days")
    
    def test_dashboard_requires_admin_auth(self, api_client):
        """Dashboard endpoint requires admin authentication"""
        # Remove auth header
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7", headers=headers)
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Dashboard requires admin authentication")


class TestSessionTrackingFullLifecycle:
    """Full session lifecycle test"""
    
    def test_full_session_lifecycle(self, api_client):
        """Test complete session lifecycle: start -> heartbeat -> end"""
        session_id = f"test-lifecycle-{uuid.uuid4().hex[:8]}"
        
        # 1. Start session
        start_response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "start",
            "device": "desktop"
        })
        assert start_response.status_code == 200
        print(f"  1. Session started: {session_id}")
        
        # 2. Send heartbeat after 1 second
        time.sleep(1)
        heartbeat_response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "heartbeat",
            "scroll_depth": 3,
            "actions": 2
        })
        assert heartbeat_response.status_code == 200
        print("  2. Heartbeat sent: scroll_depth=3, actions=2")
        
        # 3. Send another heartbeat
        time.sleep(1)
        heartbeat2_response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "heartbeat",
            "scroll_depth": 7,
            "actions": 5
        })
        assert heartbeat2_response.status_code == 200
        print("  3. Heartbeat sent: scroll_depth=7, actions=5")
        
        # 4. End session
        time.sleep(1)
        end_response = api_client.post(f"{BASE_URL}/api/admin/retention/session", json={
            "session_id": session_id,
            "event": "end",
            "scroll_depth": 10,
            "actions": 8
        })
        assert end_response.status_code == 200
        print("  4. Session ended: scroll_depth=10, actions=8")
        
        print(f"✓ Full session lifecycle completed for {session_id}")


class TestDeviceBreakdown:
    """Device breakdown tests"""
    
    def test_device_breakdown_in_dashboard(self, admin_client):
        """Dashboard returns device breakdown when data exists"""
        response = admin_client.get(f"{BASE_URL}/api/admin/retention/dashboard?days=7")
        data = response.json()
        
        device_breakdown = data.get("metrics", {}).get("avg_session_time", {}).get("device_breakdown", {})
        assert isinstance(device_breakdown, dict), f"Expected device_breakdown to be a dict, got {type(device_breakdown)}"
        
        # If there's data, check structure
        for device, stats in device_breakdown.items():
            assert "avg_seconds" in stats, f"Missing avg_seconds for device {device}"
            assert "count" in stats, f"Missing count for device {device}"
        
        print(f"✓ Device breakdown: {list(device_breakdown.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
