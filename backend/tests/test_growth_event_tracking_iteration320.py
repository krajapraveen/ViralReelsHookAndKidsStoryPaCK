"""
Growth Event Tracking API Tests - Iteration 320
Tests the 6+1 core growth events instrumentation:
1. POST /api/growth/event - all 7 event types with full schema
2. Deduplication with idempotency_key
3. POST /api/growth/events/batch - batch events
4. POST /api/growth/link-session - anonymous to user linkage
5. GET /api/admin/metrics/funnel - real funnel data from growth_events
6. Attribution fields: origin, origin_character_id, origin_series_id
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Test character ID
TEST_CHARACTER_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"

VALID_EVENTS = [
    "page_view", "remix_click", "tool_open_prefilled",
    "generate_click", "signup_triggered", "signup_completed",
    "creation_completed", "share_click",
]

class TestGrowthEventAPI:
    """Test POST /api/growth/event endpoint for all event types"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session_id = f"test_sess_{uuid.uuid4().hex[:8]}"
        self.anonymous_id = f"test_anon_{uuid.uuid4().hex[:8]}"

    def test_page_view_event_full_schema(self):
        """Test page_view event with all attribution fields"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": self.session_id,
            "anonymous_id": self.anonymous_id,
            "source_page": "/character/test-char-123",
            "character_id": TEST_CHARACTER_ID,
            "origin": "public_character_page",
            "origin_character_id": TEST_CHARACTER_ID,
            "origin_series_id": "test-series-123",
            "meta": {"test": True}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "event_id" in data
        print(f"PASS: page_view event created with event_id={data.get('event_id')}")

    def test_remix_click_event(self):
        """Test remix_click event with tool_type"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "remix_click",
            "session_id": self.session_id,
            "anonymous_id": self.anonymous_id,
            "source_page": "/character/test-char-123",
            "tool_type": "story_video",
            "character_id": TEST_CHARACTER_ID,
            "origin": "public_character_page",
            "origin_character_id": TEST_CHARACTER_ID,
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: remix_click event created")

    def test_tool_open_prefilled_event(self):
        """Test tool_open_prefilled event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "tool_open_prefilled",
            "session_id": self.session_id,
            "anonymous_id": self.anonymous_id,
            "source_page": "/app/story-video-studio",
            "tool_type": "story_video",
            "origin": "share_page",
            "origin_character_id": TEST_CHARACTER_ID,
            "meta": {"remix_title": "Test Story"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: tool_open_prefilled event created")

    def test_generate_click_event(self):
        """Test generate_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "generate_click",
            "session_id": self.session_id,
            "user_id": "test-user-123",
            "source_page": "/app/story-video-studio",
            "tool_type": "story_video",
            "creation_type": "story_video",
            "meta": {"project_id": "test-proj"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: generate_click event created")

    def test_signup_completed_event(self):
        """Test signup_completed event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "signup_completed",
            "session_id": self.session_id,
            "user_id": "new-user-123",
            "source_page": "/signup",
            "meta": {"method": "email"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: signup_completed event created")

    def test_creation_completed_event(self):
        """Test creation_completed event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "creation_completed",
            "session_id": self.session_id,
            "user_id": "test-user-123",
            "source_page": "/app/story-video-studio",
            "tool_type": "story_video",
            "creation_type": "story_video",
            "meta": {"project_id": "test-proj", "has_remix": False}
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: creation_completed event created")

    def test_share_click_event(self):
        """Test share_click event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_click",
            "session_id": self.session_id,
            "user_id": "test-user-123",
            "source_page": "/app/characters/test-char",
            "character_id": TEST_CHARACTER_ID,
            "origin": "character_detail"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: share_click event created")

    def test_invalid_event_type_rejected(self):
        """Test that invalid event types are rejected"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_type",
            "session_id": self.session_id,
        })
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
        print(f"PASS: Invalid event type correctly rejected")


class TestDeduplication:
    """Test idempotency_key deduplication"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session_id = f"dedup_sess_{uuid.uuid4().hex[:8]}"
        self.idempotency_key = f"idem_{uuid.uuid4().hex}"

    def test_duplicate_event_with_same_idempotency_key(self):
        """Test that same idempotency_key deduplicates the event"""
        payload = {
            "event": "page_view",
            "session_id": self.session_id,
            "source_page": "/test-dedup",
            "idempotency_key": self.idempotency_key
        }
        
        # First request - should create event
        response1 = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("success") == True
        assert data1.get("event_id") is not None  # First event has event_id
        print(f"PASS: First event created with event_id={data1.get('event_id')}")
        
        # Second request with same key - should be deduplicated
        response2 = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("success") == True
        assert data2.get("deduplicated") == True
        assert data2.get("event_id") is None  # Deduplicated event has no event_id
        print(f"PASS: Second event deduplicated (deduplicated={data2.get('deduplicated')})")

    def test_different_idempotency_keys_create_separate_events(self):
        """Test that different idempotency_keys create separate events"""
        base_payload = {
            "event": "page_view",
            "session_id": self.session_id,
            "source_page": "/test-different-keys",
        }
        
        key1 = f"idem_{uuid.uuid4().hex}"
        key2 = f"idem_{uuid.uuid4().hex}"
        
        response1 = requests.post(f"{BASE_URL}/api/growth/event", json={**base_payload, "idempotency_key": key1})
        response2 = requests.post(f"{BASE_URL}/api/growth/event", json={**base_payload, "idempotency_key": key2})
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1.get("event_id") is not None
        assert data2.get("event_id") is not None
        assert data1.get("event_id") != data2.get("event_id")
        print(f"PASS: Different idempotency keys created separate events")


class TestBatchEvents:
    """Test POST /api/growth/events/batch endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session_id = f"batch_sess_{uuid.uuid4().hex[:8]}"

    def test_batch_events_success(self):
        """Test batch event tracking"""
        events = [
            {
                "event": "page_view",
                "session_id": self.session_id,
                "source_page": "/explore",
                "origin": "direct"
            },
            {
                "event": "remix_click",
                "session_id": self.session_id,
                "source_page": "/explore",
                "tool_type": "story_video"
            },
            {
                "event": "tool_open_prefilled",
                "session_id": self.session_id,
                "source_page": "/app/story-video-studio",
                "tool_type": "story_video"
            }
        ]
        
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json={"events": events})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("tracked") == 3, f"Expected 3 tracked events, got {data.get('tracked')}"
        print(f"PASS: Batch tracked {data.get('tracked')} events")

    def test_batch_skips_invalid_events(self):
        """Test that batch skips invalid event types"""
        events = [
            {"event": "page_view", "session_id": self.session_id, "source_page": "/test"},
            {"event": "invalid_event", "session_id": self.session_id},  # Invalid - should be skipped
            {"event": "share_click", "session_id": self.session_id, "source_page": "/test"}
        ]
        
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json={"events": events})
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("tracked") == 2, f"Expected 2 tracked events (invalid skipped), got {data.get('tracked')}"
        print(f"PASS: Batch correctly skipped invalid event, tracked {data.get('tracked')}")

    def test_batch_deduplicates_with_idempotency_key(self):
        """Test batch deduplication with idempotency_key"""
        unique_key = f"batch_idem_{uuid.uuid4().hex}"
        events = [
            {"event": "page_view", "session_id": self.session_id, "source_page": "/test1", "idempotency_key": unique_key},
            {"event": "page_view", "session_id": self.session_id, "source_page": "/test1", "idempotency_key": unique_key},  # Duplicate
        ]
        
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json={"events": events})
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("tracked") == 1, f"Expected 1 tracked (duplicate skipped), got {data.get('tracked')}"
        print(f"PASS: Batch deduplication working")

    def test_batch_max_50_events(self):
        """Test batch accepts max 50 events"""
        events = [{"event": "page_view", "session_id": self.session_id, "source_page": f"/page-{i}"} for i in range(60)]
        
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json={"events": events})
        assert response.status_code == 200
        data = response.json()
        assert data.get("tracked") <= 50, f"Batch should limit to 50, got {data.get('tracked')}"
        print(f"PASS: Batch limited to {data.get('tracked')} events (max 50)")


class TestSessionLinkage:
    """Test POST /api/growth/link-session endpoint"""

    def test_link_session_to_user(self):
        """Test linking anonymous session events to a user_id"""
        session_id = f"link_sess_{uuid.uuid4().hex[:8]}"
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # First create some anonymous events
        for i in range(3):
            requests.post(f"{BASE_URL}/api/growth/event", json={
                "event": "page_view",
                "session_id": session_id,
                "anonymous_id": f"anon_{session_id}",
                "source_page": f"/test-page-{i}",
                "user_id": None  # Anonymous
            })
        
        # Now link the session to a user
        response = requests.post(f"{BASE_URL}/api/growth/link-session", json={
            "session_id": session_id,
            "user_id": user_id
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("linked_events") >= 3, f"Expected >=3 linked events, got {data.get('linked_events')}"
        print(f"PASS: Linked {data.get('linked_events')} events to user_id={user_id}")


class TestAdminFunnelMetrics:
    """Test GET /api/admin/metrics/funnel with real growth_events data"""

    @pytest.fixture
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json().get("token")

    def test_funnel_endpoint_returns_data(self, admin_token):
        """Test funnel endpoint returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "page_views" in data
        assert "remix_clicks" in data
        assert "tool_opens_prefilled" in data
        assert "generate_clicks" in data
        assert "signup_completed" in data
        assert "creation_completed" in data
        assert "share_clicks" in data
        
        print(f"PASS: Funnel data retrieved:")
        print(f"  - page_views: {data.get('page_views')}")
        print(f"  - remix_clicks: {data.get('remix_clicks')}")
        print(f"  - tool_opens_prefilled: {data.get('tool_opens_prefilled')}")
        print(f"  - generate_clicks: {data.get('generate_clicks')}")
        print(f"  - signup_completed: {data.get('signup_completed')}")
        print(f"  - creation_completed: {data.get('creation_completed')}")
        print(f"  - share_clicks: {data.get('share_clicks')}")

    def test_funnel_requires_admin_auth(self):
        """Test funnel endpoint requires admin authentication"""
        # No auth header
        response = requests.get(f"{BASE_URL}/api/admin/metrics/funnel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Funnel endpoint requires auth (status={response.status_code})")

    def test_funnel_rejects_non_admin_user(self):
        """Test funnel endpoint rejects non-admin users"""
        # Login as regular user
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip(f"Regular user login failed: {login_response.text}")
        
        token = login_response.json().get("token")
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"PASS: Funnel endpoint rejects non-admin users")


class TestGrowthMetricsEndpoint:
    """Test /api/growth/metrics and /api/growth/funnel public endpoints"""

    def test_growth_metrics_endpoint(self):
        """Test growth metrics endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days=7")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "raw_counts" in data
        assert "conversion_rates" in data
        print(f"PASS: Growth metrics endpoint working")
        print(f"  - period_days: {data.get('period_days')}")
        print(f"  - raw_counts: {data.get('raw_counts')}")

    def test_growth_funnel_endpoint(self):
        """Test growth funnel endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel?days=7")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "funnel" in data
        funnel = data.get("funnel", [])
        expected_stages = ["page_view", "remix_click", "tool_open_prefilled", "generate_click", "signup_completed", "creation_completed"]
        stage_names = [s.get("stage") for s in funnel]
        for stage in expected_stages:
            assert stage in stage_names, f"Missing funnel stage: {stage}"
        
        print(f"PASS: Growth funnel endpoint working")
        for stage in funnel:
            print(f"  - {stage.get('stage')}: {stage.get('count')}")


class TestAttributionFields:
    """Test attribution fields in events"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session_id = f"attr_sess_{uuid.uuid4().hex[:8]}"

    def test_event_with_all_attribution_fields(self):
        """Test event includes all attribution fields"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": self.session_id,
            "user_id": "user-123",
            "anonymous_id": "anon-456",
            "source_page": "/character/char-789",
            "source_slug": "char-789",
            "tool_type": "story_video",
            "creation_type": "story_video",
            "series_id": "series-abc",
            "character_id": "char-789",
            "origin": "public_character_page",
            "origin_slug": "char-789",
            "origin_character_id": "char-789",
            "origin_series_id": "series-abc",
            "referrer_slug": "landing-page",
            "ab_variant": "variant_b",
            "meta": {"source": "test"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Event created with all attribution fields")

    def test_event_with_minimal_fields(self):
        """Test event works with minimal required fields"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": self.session_id
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"PASS: Event created with minimal fields")


class TestViralCoefficient:
    """Test viral coefficient endpoint"""

    def test_viral_coefficient_endpoint(self):
        """Test viral coefficient calculation endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient?days=7")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "viral_coefficient_K" in data
        assert "interpretation" in data
        assert "components" in data
        
        print(f"PASS: Viral coefficient endpoint working")
        print(f"  - K value: {data.get('viral_coefficient_K')}")
        print(f"  - Interpretation: {data.get('interpretation')}")
        print(f"  - Components: {data.get('components')}")


class TestGrowthTrends:
    """Test daily trends endpoint"""

    def test_growth_trends_endpoint(self):
        """Test daily trends endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/trends?days=7")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "daily" in data
        assert "period_days" in data
        print(f"PASS: Growth trends endpoint working")
        print(f"  - Days with data: {len(data.get('daily', {}))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
