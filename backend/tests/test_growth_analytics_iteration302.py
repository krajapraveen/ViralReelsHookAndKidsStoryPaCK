"""
Test Growth Analytics APIs - Iteration 302
Tests: /api/growth/* endpoints for Growth Intelligence Dashboard
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGrowthMetrics:
    """Tests for /api/growth/metrics endpoint - raw counts and conversion rates"""
    
    def test_metrics_default_7_days(self):
        """GET /api/growth/metrics returns raw_counts + conversion_rates for 7 days default"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert data["period_days"] == 7  # default
        assert "raw_counts" in data
        assert "conversion_rates" in data
        
        # Verify raw_counts structure
        raw = data["raw_counts"]
        assert "page_views" in raw
        assert "remix_clicks" in raw
        assert "signups_completed" in raw
        assert "creations_completed" in raw
        
        # Verify conversion_rates structure
        rates = data["conversion_rates"]
        assert "remix_click_rate" in rates
        assert "prefill_rate" in rates
        assert "generation_rate" in rates
        assert "signup_completion_rate" in rates
        assert "creation_rate" in rates
        assert "overall_conversion" in rates
    
    def test_metrics_14_days(self):
        """GET /api/growth/metrics?days=14 returns 14-day metrics"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days=14")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_days"] == 14
    
    def test_metrics_30_days(self):
        """GET /api/growth/metrics?days=30 returns 30-day metrics"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days=30")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_days"] == 30


class TestViralCoefficient:
    """Tests for /api/growth/viral-coefficient endpoint - K value and interpretation"""
    
    def test_viral_coefficient_returns_k(self):
        """GET /api/growth/viral-coefficient returns K value with interpretation"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        assert "viral_coefficient_K" in data
        assert "interpretation" in data
        assert isinstance(data["viral_coefficient_K"], (int, float))
        
        # Interpretation should be one of the expected values
        valid_interpretations = ["exponential growth", "growing", "needs optimization", "no data"]
        assert data["interpretation"] in valid_interpretations
    
    def test_viral_coefficient_components(self):
        """GET /api/growth/viral-coefficient returns calculation components"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        assert "components" in data
        
        components = data["components"]
        assert "avg_shares_per_user" in components
        assert "conversion_rate_per_share" in components
        assert "unique_sharers" in components
        assert "total_shares" in components
        assert "page_views" in components
        assert "signups_from_shares" in components
    
    def test_viral_coefficient_top_slugs(self):
        """GET /api/growth/viral-coefficient returns top performing slugs"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient")
        assert response.status_code == 200
        
        data = response.json()
        assert "top_performing_slugs" in data
        assert isinstance(data["top_performing_slugs"], list)
        
        # If there are slugs, verify their structure
        if data["top_performing_slugs"]:
            slug = data["top_performing_slugs"][0]
            assert "slug" in slug
            assert "views" in slug
            assert "remix_clicks" in slug
            assert "remix_rate" in slug


class TestFunnel:
    """Tests for /api/growth/funnel endpoint - funnel stage visualization data"""
    
    def test_funnel_returns_all_stages(self):
        """GET /api/growth/funnel returns all 6 funnel stages"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "funnel" in data
        
        funnel = data["funnel"]
        assert len(funnel) == 6  # All 6 stages
        
        expected_stages = ["page_view", "remix_click", "tool_open_prefilled", 
                         "generate_click", "signup_completed", "creation_completed"]
        actual_stages = [s["stage"] for s in funnel]
        assert actual_stages == expected_stages
    
    def test_funnel_stage_structure(self):
        """Each funnel stage has stage name and count"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel")
        assert response.status_code == 200
        
        data = response.json()
        for stage in data["funnel"]:
            assert "stage" in stage
            assert "count" in stage
            assert isinstance(stage["count"], int)


class TestTrends:
    """Tests for /api/growth/trends endpoint - daily event breakdown"""
    
    def test_trends_returns_daily(self):
        """GET /api/growth/trends returns daily event breakdown"""
        response = requests.get(f"{BASE_URL}/api/growth/trends")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "daily" in data
        assert isinstance(data["daily"], dict)
    
    def test_trends_daily_structure(self):
        """Daily trends contain date keys with event counts"""
        response = requests.get(f"{BASE_URL}/api/growth/trends?days=7")
        assert response.status_code == 200
        
        data = response.json()
        daily = data["daily"]
        
        # If there's data, verify structure
        if daily:
            for date, events in daily.items():
                # Date should be in YYYY-MM-DD format
                assert len(date) == 10
                assert "-" in date
                assert isinstance(events, dict)


class TestEventTracking:
    """Tests for POST /api/growth/event - single event tracking"""
    
    def test_track_page_view_event(self):
        """POST /api/growth/event tracks page_view successfully"""
        session_id = f"pytest_session_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "page_view",
            "session_id": session_id,
            "source_slug": "pytest-test-slug"
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "event_id" in data
    
    def test_track_remix_click_event(self):
        """POST /api/growth/event tracks remix_click successfully"""
        session_id = f"pytest_session_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "remix_click",
            "session_id": session_id,
            "source_slug": "pytest-remix-slug",
            "tool": "story-video-studio"
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
    
    def test_track_signup_completed_event(self):
        """POST /api/growth/event tracks signup_completed successfully"""
        session_id = f"pytest_session_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": "signup_completed",
            "session_id": session_id,
            "user_id": "pytest_user_302"
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
    
    def test_track_invalid_event_returns_400(self):
        """POST /api/growth/event with invalid event type returns 400"""
        payload = {
            "event": "invalid_event_type_xyz",
            "session_id": "test_session"
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert "Invalid event" in data["detail"]


class TestBatchEventTracking:
    """Tests for POST /api/growth/events/batch - batch event tracking"""
    
    def test_batch_track_multiple_events(self):
        """POST /api/growth/events/batch tracks multiple events"""
        session_id = f"pytest_batch_{uuid.uuid4().hex[:8]}"
        payload = {
            "events": [
                {"event": "page_view", "session_id": session_id, "source_slug": "batch-test"},
                {"event": "remix_click", "session_id": session_id, "source_slug": "batch-test"},
                {"event": "tool_open_prefilled", "session_id": session_id, "tool": "reels"}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["tracked"] == 3
    
    def test_batch_ignores_invalid_events(self):
        """POST /api/growth/events/batch ignores invalid event types in batch"""
        session_id = f"pytest_batch_{uuid.uuid4().hex[:8]}"
        payload = {
            "events": [
                {"event": "page_view", "session_id": session_id},
                {"event": "invalid_xyz", "session_id": session_id},  # Should be ignored
                {"event": "remix_click", "session_id": session_id}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["tracked"] == 2  # Only 2 valid events tracked


class TestAllValidEventTypes:
    """Tests for all valid event types defined in backend"""
    
    @pytest.mark.parametrize("event_type", [
        "page_view",
        "remix_click",
        "tool_open_prefilled",
        "generate_click",
        "signup_triggered",
        "signup_completed",
        "creation_completed",
        "share_click"
    ])
    def test_all_valid_event_types(self, event_type):
        """All valid event types should be trackable"""
        session_id = f"pytest_event_{uuid.uuid4().hex[:8]}"
        payload = {
            "event": event_type,
            "session_id": session_id
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response.status_code == 200
        assert response.json()["success"] == True


class TestPeriodFiltering:
    """Tests for period filtering across all endpoints"""
    
    @pytest.mark.parametrize("days", [7, 14, 30])
    def test_metrics_period_filter(self, days):
        """Metrics endpoint respects days parameter"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days={days}")
        assert response.status_code == 200
        assert response.json()["period_days"] == days
    
    @pytest.mark.parametrize("days", [7, 14, 30])
    def test_viral_coefficient_period_filter(self, days):
        """Viral coefficient endpoint respects days parameter"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient?days={days}")
        assert response.status_code == 200
        assert response.json()["period_days"] == days
    
    @pytest.mark.parametrize("days", [7, 14, 30])
    def test_funnel_period_filter(self, days):
        """Funnel endpoint respects days parameter"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel?days={days}")
        assert response.status_code == 200
        assert response.json()["period_days"] == days
    
    @pytest.mark.parametrize("days", [7, 14, 30])
    def test_trends_period_filter(self, days):
        """Trends endpoint respects days parameter"""
        response = requests.get(f"{BASE_URL}/api/growth/trends?days={days}")
        assert response.status_code == 200
        assert response.json()["period_days"] == days
