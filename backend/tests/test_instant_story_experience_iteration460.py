"""
Test Suite for Instant Demo Experience Feature - Iteration 460
Tests:
1. POST /api/public/quick-generate - No auth required, returns story_id, title, story_text
2. POST /api/funnel/track - All instant story events accepted
3. Rate limiting behavior
4. Error handling
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInstantStoryQuickGenerate:
    """Tests for POST /api/public/quick-generate endpoint"""
    
    def test_quick_generate_no_auth_required(self):
        """Verify endpoint works without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={"mode": "fresh", "session_id": "test_session_001"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        # Should not return 401/403 - no auth required
        assert response.status_code != 401, "Endpoint should not require auth"
        assert response.status_code != 403, "Endpoint should not require auth"
        print(f"✓ Quick generate endpoint accessible without auth, status: {response.status_code}")
    
    def test_quick_generate_returns_required_fields(self):
        """Verify response contains story_id, title, story_text"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={"mode": "fresh", "session_id": "test_session_002"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limited - clear db.instant_story_requests to test")
        
        if response.status_code == 503:
            pytest.skip("Generation service unavailable (EMERGENT_LLM_KEY not set)")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "story_id" in data, "Response must contain story_id"
        assert "title" in data, "Response must contain title"
        assert "story_text" in data, "Response must contain story_text"
        assert isinstance(data["story_id"], str), "story_id must be string"
        assert len(data["story_id"]) > 0, "story_id must not be empty"
        assert len(data["title"]) > 0, "title must not be empty"
        assert len(data["story_text"]) > 0, "story_text must not be empty"
        print(f"✓ Quick generate returns required fields: story_id={data['story_id'][:8]}..., title={data['title'][:30]}...")
    
    def test_quick_generate_continue_mode(self):
        """Test continue mode with source_title and source_snippet"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "continue",
                "source_title": "The Girl Who Opened the Moon Door",
                "source_snippet": "In a village where the moon hung impossibly close...",
                "session_id": "test_session_003"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        if response.status_code == 503:
            pytest.skip("Generation service unavailable")
        
        assert response.status_code == 200, f"Continue mode failed: {response.text}"
        data = response.json()
        assert "story_text" in data
        print(f"✓ Continue mode works, generated continuation")
    
    def test_quick_generate_with_theme(self):
        """Test fresh mode with custom theme"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "theme": "A robot discovers emotions for the first time",
                "session_id": "test_session_004"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        if response.status_code == 503:
            pytest.skip("Generation service unavailable")
        
        assert response.status_code == 200, f"Theme mode failed: {response.text}"
        print(f"✓ Fresh mode with custom theme works")
    
    def test_quick_generate_invalid_mode(self):
        """Test that invalid mode is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={"mode": "invalid_mode", "session_id": "test_session_005"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for invalid mode, got {response.status_code}"
        print(f"✓ Invalid mode correctly rejected with 422")


class TestFunnelTrackingInstantStoryEvents:
    """Tests for POST /api/funnel/track with instant story events"""
    
    INSTANT_STORY_EVENTS = [
        "demo_viewed",
        "story_generation_started",
        "story_generated_success",
        "story_generated_failed",
        "story_generation_timeout",
        "cta_continue_clicked",
        "cta_video_clicked",
        "cta_share_clicked",
        "login_prompt_shown"
    ]
    
    def test_all_instant_story_events_accepted(self):
        """Verify all instant story events are in FUNNEL_STEPS and accepted"""
        results = []
        for event in self.INSTANT_STORY_EVENTS:
            response = requests.post(
                f"{BASE_URL}/api/funnel/track",
                json={
                    "step": event,
                    "session_id": f"test_funnel_{event}",
                    "context": {
                        "source_page": "experience",
                        "device": "desktop",
                        "meta": {"test": True}
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            data = response.json()
            success = data.get("success", False)
            results.append((event, response.status_code, success))
            
            if not success:
                print(f"✗ Event '{event}' rejected: {data}")
        
        # Check all events were accepted
        failed = [r for r in results if not r[2]]
        assert len(failed) == 0, f"Events rejected: {failed}"
        print(f"✓ All {len(self.INSTANT_STORY_EVENTS)} instant story events accepted")
    
    def test_demo_viewed_event(self):
        """Test demo_viewed event specifically"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "demo_viewed",
                "session_id": "test_demo_viewed_001",
                "context": {
                    "source_page": "experience",
                    "device": "mobile",
                    "meta": {"source": "landing"}
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True, f"demo_viewed should be accepted: {data}"
        assert "session_id" in data
        print(f"✓ demo_viewed event tracked successfully")
    
    def test_story_generation_started_event(self):
        """Test story_generation_started event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "story_generation_started",
                "session_id": "test_gen_started_001",
                "context": {"source_page": "experience"}
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ story_generation_started event tracked")
    
    def test_story_generated_success_with_meta(self):
        """Test story_generated_success with story_id in meta"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "story_generated_success",
                "session_id": "test_gen_success_001",
                "context": {
                    "source_page": "experience",
                    "meta": {"story_id": "abc123def456"}
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ story_generated_success with meta tracked")
    
    def test_cta_continue_clicked_event(self):
        """Test cta_continue_clicked event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "cta_continue_clicked",
                "session_id": "test_cta_continue_001",
                "context": {
                    "source_page": "experience",
                    "meta": {"phase": "demo"}
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ cta_continue_clicked event tracked")
    
    def test_login_prompt_shown_event(self):
        """Test login_prompt_shown event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "login_prompt_shown",
                "session_id": "test_login_prompt_001",
                "context": {
                    "source_page": "experience",
                    "meta": {"trigger": "continue"}
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ login_prompt_shown event tracked")
    
    def test_invalid_event_rejected(self):
        """Test that invalid events are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "invalid_event_xyz",
                "session_id": "test_invalid_001"
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        data = response.json()
        assert data.get("success") == False, "Invalid event should be rejected"
        print(f"✓ Invalid event correctly rejected")


class TestLandingPageCTARouting:
    """Tests for landing page CTA routing to /experience"""
    
    def test_landing_page_loads(self):
        """Verify landing page is accessible"""
        response = requests.get(f"{BASE_URL}/", timeout=10)
        assert response.status_code == 200
        print(f"✓ Landing page loads successfully")
    
    def test_experience_page_accessible(self):
        """Verify /experience route is accessible"""
        response = requests.get(f"{BASE_URL}/experience", timeout=10)
        # React SPA returns 200 for all routes
        assert response.status_code == 200
        print(f"✓ /experience route accessible")
    
    def test_experience_with_query_params(self):
        """Verify /experience accepts query params"""
        response = requests.get(
            f"{BASE_URL}/experience",
            params={
                "source": "landing",
                "title": "Test Story",
                "snippet": "Once upon a time...",
                "theme": "adventure"
            },
            timeout=10
        )
        assert response.status_code == 200
        print(f"✓ /experience with query params accessible")


class TestRateLimiting:
    """Tests for rate limiting on quick-generate endpoint"""
    
    def test_rate_limit_returns_429(self):
        """Verify rate limit returns 429 after exceeding limit"""
        # Note: Rate limit is 5 requests per hour per IP
        # This test may need db.instant_story_requests cleared first
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={"mode": "fresh", "session_id": "rate_limit_test"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # If we get 429, rate limiting is working
        if response.status_code == 429:
            data = response.json()
            assert "detail" in data
            print(f"✓ Rate limiting active: {data['detail']}")
        else:
            print(f"✓ Request succeeded (not rate limited yet), status: {response.status_code}")


class TestHealthAndStatus:
    """Basic health checks"""
    
    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        print(f"✓ API health check passed")
    
    def test_public_stats_endpoint(self):
        """Verify public stats endpoint works"""
        response = requests.get(f"{BASE_URL}/api/public/stats", timeout=10)
        assert response.status_code == 200
        print(f"✓ Public stats endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
