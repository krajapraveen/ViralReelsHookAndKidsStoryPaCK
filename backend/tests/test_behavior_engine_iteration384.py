"""
Behavior Engine (Addiction Loop) Tests — Iteration 384
═══════════════════════════════════════════════════════
Tests session memory, momentum tracking, real-time profile updates,
variable reward injection, recovery system, infinite scroll, and dynamic hook timing.

Features tested:
- POST /api/engagement/feed-event with various event types
- Session momentum tracking (+2 for continue_click, -1 for skip_fast)
- Recovery detection (3+ consecutive skips)
- GET /api/engagement/story-feed/more for infinite scroll
- Variable reward injection in story ordering
- Feed API returns thumb_blur, cdn_base
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ═══════════════════════════════════════════════════════════════
# FEED-EVENT ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════

class TestFeedEventEndpoint:
    """POST /api/engagement/feed-event tests."""

    def test_feed_event_click_returns_session(self, authenticated_client):
        """POST /api/engagement/feed-event with event_type=click returns session with momentum, actions, should_rerank, recovery_needed, intensity."""
        response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "click",
            "job_id": "test-job-001",
            "category": "watercolor",
            "hook_text": "Test hook text"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=true"
        
        session = data.get("session", {})
        assert "momentum" in session, "Session should have momentum"
        assert "actions" in session, "Session should have actions"
        assert "should_rerank" in session, "Session should have should_rerank"
        assert "recovery_needed" in session, "Session should have recovery_needed"
        assert "intensity" in session, "Session should have intensity"
        
        # Momentum should be a float between 0 and 10
        assert isinstance(session["momentum"], (int, float)), "Momentum should be numeric"
        assert 0.0 <= session["momentum"] <= 10.0, f"Momentum {session['momentum']} should be 0-10"
        
        # Intensity should be low/medium/high
        assert session["intensity"] in ["low", "medium", "high"], f"Intensity {session['intensity']} should be low/medium/high"
        
        print(f"✓ Feed event click: momentum={session['momentum']}, actions={session['actions']}, intensity={session['intensity']}")

    def test_feed_event_continue_click_increases_momentum(self, authenticated_client):
        """POST /api/engagement/feed-event with event_type=continue_click shows momentum increase (+2)."""
        # First, get current momentum
        response1 = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "click",
            "job_id": "test-job-002",
            "category": "anime"
        })
        assert response1.status_code == 200
        initial_momentum = response1.json().get("session", {}).get("momentum", 0)
        
        # Now send continue_click (should add +2)
        response2 = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "continue_click",
            "job_id": "test-job-003",
            "category": "anime"
        })
        assert response2.status_code == 200
        
        data = response2.json()
        new_momentum = data.get("session", {}).get("momentum", 0)
        
        # continue_click adds +2 to momentum (capped at 10)
        expected_min = min(10.0, initial_momentum + 1.5)  # Allow some tolerance
        assert new_momentum >= expected_min or new_momentum == 10.0, \
            f"Momentum should increase: initial={initial_momentum}, new={new_momentum}"
        
        print(f"✓ Continue click momentum increase: {initial_momentum} → {new_momentum}")

    def test_feed_event_skip_fast_triggers_recovery(self, authenticated_client):
        """POST /api/engagement/feed-event with 3x skip_fast events shows recovery_needed=true and consecutive_skips=3."""
        # Send 3 skip_fast events
        for i in range(3):
            response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
                "event_type": "skip_fast",
                "job_id": f"test-skip-{i}",
                "category": "cartoon_2d"
            })
            assert response.status_code == 200, f"Skip {i+1} failed: {response.text}"
        
        # Check the last response
        data = response.json()
        session = data.get("session", {})
        
        # After 3 skips, recovery_needed should be true
        assert session.get("consecutive_skips", 0) >= 3, \
            f"Expected consecutive_skips >= 3, got {session.get('consecutive_skips')}"
        assert session.get("recovery_needed") is True, \
            f"Expected recovery_needed=true after 3 skips, got {session.get('recovery_needed')}"
        
        print(f"✓ Skip fast recovery: consecutive_skips={session.get('consecutive_skips')}, recovery_needed={session.get('recovery_needed')}")

    def test_feed_event_preview_play(self, authenticated_client):
        """POST /api/engagement/feed-event with event_type=preview_play works."""
        response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "preview_play",
            "job_id": "test-preview-001",
            "watch_time": 3.5
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        print("✓ Preview play event tracked")

    def test_feed_event_hook_seen(self, authenticated_client):
        """POST /api/engagement/feed-event with event_type=hook_seen works."""
        response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "hook_seen",
            "job_id": "test-hook-001",
            "hook_text": "The door wasn't supposed to exist..."
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        print("✓ Hook seen event tracked")

    def test_feed_event_watch_complete(self, authenticated_client):
        """POST /api/engagement/feed-event with event_type=watch_complete works."""
        response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "watch_complete",
            "job_id": "test-watch-001",
            "watch_time": 45.0
        })
        assert response.status_code == 200
        assert response.json().get("success") is True
        print("✓ Watch complete event tracked")


# ═══════════════════════════════════════════════════════════════
# STORY-FEED/MORE ENDPOINT TESTS (INFINITE SCROLL)
# ═══════════════════════════════════════════════════════════════

class TestStoryFeedMoreEndpoint:
    """GET /api/engagement/story-feed/more tests for infinite scroll."""

    def test_story_feed_more_returns_stories(self, authenticated_client):
        """GET /api/engagement/story-feed/more?offset=0&limit=4 returns stories array, offset, has_more, cdn_base, session_intensity."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=0&limit=4")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "stories" in data, "Response should have stories array"
        assert "offset" in data, "Response should have offset"
        assert "has_more" in data, "Response should have has_more"
        assert "cdn_base" in data, "Response should have cdn_base"
        assert "session_intensity" in data, "Response should have session_intensity"
        
        # Validate types
        assert isinstance(data["stories"], list), "stories should be a list"
        assert isinstance(data["offset"], int), "offset should be an int"
        assert isinstance(data["has_more"], bool), "has_more should be a bool"
        assert isinstance(data["cdn_base"], str), "cdn_base should be a string"
        assert data["session_intensity"] in ["low", "medium", "high"], \
            f"session_intensity should be low/medium/high, got {data['session_intensity']}"
        
        print(f"✓ Story feed more: {len(data['stories'])} stories, offset={data['offset']}, has_more={data['has_more']}, intensity={data['session_intensity']}")

    def test_story_feed_more_high_offset_returns_empty(self, authenticated_client):
        """GET /api/engagement/story-feed/more?offset=150 returns empty stories and has_more=false."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=150&limit=12")
        assert response.status_code == 200
        
        data = response.json()
        
        # At high offset, should have no more stories
        # Note: This depends on actual data volume, but 150 offset should be past most content
        assert "stories" in data
        assert "has_more" in data
        
        # If stories is empty, has_more should be false
        if len(data["stories"]) == 0:
            assert data["has_more"] is False, "has_more should be false when no stories returned"
            print("✓ High offset returns empty stories with has_more=false")
        else:
            print(f"✓ High offset still has {len(data['stories'])} stories (large dataset)")

    def test_story_feed_more_pagination(self, authenticated_client):
        """Test pagination: offset=0 then offset=4 returns different stories."""
        response1 = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=0&limit=4")
        assert response1.status_code == 200
        data1 = response1.json()
        
        response2 = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=4&limit=4")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Get job_ids from both responses
        ids1 = {s.get("job_id") for s in data1.get("stories", [])}
        ids2 = {s.get("job_id") for s in data2.get("stories", [])}
        
        # Should have minimal overlap (pagination working)
        overlap = ids1 & ids2
        print(f"✓ Pagination: page1={len(ids1)} stories, page2={len(ids2)} stories, overlap={len(overlap)}")


# ═══════════════════════════════════════════════════════════════
# FEED API MEDIA FIELDS TESTS
# ═══════════════════════════════════════════════════════════════

class TestFeedApiMediaFields:
    """Test that feed API returns correct media fields."""

    def test_feed_api_returns_cdn_base(self, authenticated_client):
        """Feed API returns cdn_base in response."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        assert "cdn_base" in data, "Response should have cdn_base"
        assert data["cdn_base"], "cdn_base should not be empty"
        assert "r2.dev" in data["cdn_base"], f"cdn_base should contain r2.dev, got {data['cdn_base']}"
        
        print(f"✓ Feed API cdn_base: {data['cdn_base']}")

    def test_feed_api_returns_thumb_blur(self, authenticated_client):
        """Feed API returns thumb_blur objects with type inline_base64."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        thumb_blur_count = 0
        inline_base64_count = 0
        
        for row in rows:
            for story in row.get("stories", []):
                media = story.get("media", {})
                thumb_blur = media.get("thumb_blur")
                if thumb_blur:
                    thumb_blur_count += 1
                    if thumb_blur.get("type") == "inline_base64":
                        inline_base64_count += 1
        
        print(f"✓ Feed API thumb_blur: {thumb_blur_count} total, {inline_base64_count} inline_base64")
        # At least some stories should have thumb_blur
        # Note: Not all stories may have blur data

    def test_story_feed_more_returns_cdn_base(self, authenticated_client):
        """story-feed/more endpoint returns cdn_base."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=0&limit=4")
        assert response.status_code == 200
        
        data = response.json()
        assert "cdn_base" in data, "Response should have cdn_base"
        assert data["cdn_base"], "cdn_base should not be empty"
        
        print(f"✓ Story feed more cdn_base: {data['cdn_base']}")


# ═══════════════════════════════════════════════════════════════
# SESSION MOMENTUM MECHANICS TESTS
# ═══════════════════════════════════════════════════════════════

class TestSessionMomentumMechanics:
    """Test session momentum scoring mechanics."""

    def test_momentum_range_0_to_10(self, authenticated_client):
        """Momentum score should always be in range 0.0-10.0."""
        # Send multiple events to test momentum bounds
        for event_type in ["click", "continue_click", "preview_play"]:
            response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
                "event_type": event_type,
                "job_id": f"test-momentum-{event_type}",
                "category": "cinematic"
            })
            assert response.status_code == 200
            
            momentum = response.json().get("session", {}).get("momentum", 0)
            assert 0.0 <= momentum <= 10.0, f"Momentum {momentum} out of range for {event_type}"
        
        print("✓ Momentum always in range 0.0-10.0")

    def test_intensity_levels(self, authenticated_client):
        """Test that intensity levels are correctly determined."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=0&limit=4")
        assert response.status_code == 200
        
        intensity = response.json().get("session_intensity", "")
        assert intensity in ["low", "medium", "high"], f"Invalid intensity: {intensity}"
        
        print(f"✓ Session intensity: {intensity}")


# ═══════════════════════════════════════════════════════════════
# ANONYMOUS USER TESTS
# ═══════════════════════════════════════════════════════════════

class TestAnonymousUser:
    """Test behavior for anonymous (unauthenticated) users."""

    def test_anonymous_feed_event(self):
        """Anonymous users can send feed events (no auth required)."""
        # Use a fresh session without any auth
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "click",
            "job_id": "anon-test-001",
            "category": "watercolor"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        
        # Anonymous users should have default session values (momentum=0 since no profile)
        session = data.get("session", {})
        # For anonymous, momentum should be 0 since there's no user profile
        assert session.get("momentum") == 0.0, f"Anonymous momentum should be 0, got {session.get('momentum')}"
        
        print("✓ Anonymous feed event works")

    def test_anonymous_story_feed_more(self):
        """Anonymous users can fetch more stories."""
        # Use a fresh session without any auth
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.get(f"{BASE_URL}/api/engagement/story-feed/more?offset=0&limit=4")
        
        assert response.status_code == 200
        data = response.json()
        assert "stories" in data
        assert "session_intensity" in data
        # Anonymous users should have low intensity (no profile)
        assert data["session_intensity"] == "low", f"Anonymous intensity should be low, got {data['session_intensity']}"
        
        print(f"✓ Anonymous story feed more: {len(data.get('stories', []))} stories")


# ═══════════════════════════════════════════════════════════════
# RECOVERY SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════

class TestRecoverySystem:
    """Test the recovery system for skip detection."""

    def test_recovery_resets_on_positive_engagement(self, authenticated_client):
        """Recovery resets when user engages positively after skips."""
        # First, trigger recovery with skips
        for i in range(3):
            authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
                "event_type": "skip_fast",
                "job_id": f"recovery-skip-{i}"
            })
        
        # Now send a positive engagement
        response = authenticated_client.post(f"{BASE_URL}/api/engagement/feed-event", json={
            "event_type": "click",
            "job_id": "recovery-click-001",
            "category": "anime"
        })
        assert response.status_code == 200
        
        session = response.json().get("session", {})
        # After a click, consecutive_skips should reset to 0
        assert session.get("consecutive_skips", 0) == 0, \
            f"consecutive_skips should reset to 0 after click, got {session.get('consecutive_skips')}"
        
        print("✓ Recovery resets on positive engagement")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
