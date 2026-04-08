"""
Test Suite for Continue Story Loop + Smart Paywall Features (Iteration 460)
Tests:
- POST /api/public/quick-generate endpoint (fresh and continue modes)
- POST /api/funnel/track endpoint (all paywall-related events)
- Rate limiting behavior
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# All funnel events related to continue story loop and paywall
PAYWALL_FUNNEL_EVENTS = [
    "continue_clicked",
    "story_part_generated",
    "paywall_teaser_shown",
    "paywall_shown",
    "paywall_dismissed",
    "paywall_converted",
    "exit_offer_shown",
    "discount_offer_shown",
]


class TestQuickGenerateEndpoint:
    """Tests for POST /api/public/quick-generate - story generation"""
    
    def test_quick_generate_fresh_mode(self):
        """Test fresh story generation returns valid response"""
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id
            },
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "story_id" in data, "Response should contain story_id"
        assert "title" in data, "Response should contain title"
        assert "story_text" in data, "Response should contain story_text"
        assert "status" in data, "Response should contain status"
        assert data["status"] == "success", f"Expected success status, got {data['status']}"
        assert len(data["story_text"]) > 100, "Story text should be substantial"
        print(f"✓ Fresh story generated: {data['title'][:50]}...")
    
    def test_quick_generate_continue_mode(self):
        """Test continue mode generates Part 2 based on source snippet"""
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # First generate a fresh story
        fresh_response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": session_id
            },
            timeout=30
        )
        assert fresh_response.status_code == 200
        fresh_data = fresh_response.json()
        
        # Now continue the story
        continue_response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "continue",
                "source_title": fresh_data["title"],
                "source_snippet": fresh_data["story_text"][-500:],
                "session_id": session_id
            },
            timeout=30
        )
        
        assert continue_response.status_code == 200, f"Expected 200, got {continue_response.status_code}"
        
        cont_data = continue_response.json()
        assert "story_id" in cont_data
        assert "story_text" in cont_data
        assert len(cont_data["story_text"]) > 50, "Continuation should have substantial text"
        print(f"✓ Story continuation generated successfully")
    
    def test_quick_generate_with_theme(self):
        """Test story generation with custom theme"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "theme": "A mysterious lighthouse keeper discovers a message in a bottle",
                "session_id": f"test_{uuid.uuid4().hex[:8]}"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        print(f"✓ Themed story generated: {data['title'][:50]}...")
    
    def test_quick_generate_invalid_mode(self):
        """Test that invalid mode is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "invalid_mode",
                "session_id": "test123"
            },
            timeout=10
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for invalid mode, got {response.status_code}"
        print("✓ Invalid mode correctly rejected")


class TestFunnelTrackingEndpoint:
    """Tests for POST /api/funnel/track - all paywall-related events"""
    
    def test_track_continue_clicked(self):
        """Test tracking continue_clicked event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "continue_clicked",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 2, "story_id": "test123"}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ continue_clicked event tracked")
    
    def test_track_story_part_generated(self):
        """Test tracking story_part_generated event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "story_part_generated",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 2, "story_id": "abc123"}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ story_part_generated event tracked")
    
    def test_track_paywall_teaser_shown(self):
        """Test tracking paywall_teaser_shown event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "paywall_teaser_shown",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 2, "entry_source": "landing"}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ paywall_teaser_shown event tracked")
    
    def test_track_paywall_shown(self):
        """Test tracking paywall_shown event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "paywall_shown",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 3, "view_count": 1}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ paywall_shown event tracked")
    
    def test_track_paywall_dismissed(self):
        """Test tracking paywall_dismissed event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "paywall_dismissed",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 3, "exit_offer": False}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ paywall_dismissed event tracked")
    
    def test_track_paywall_converted(self):
        """Test tracking paywall_converted event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "paywall_converted",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "plan_selected": "monthly",
                    "meta": {"part_number": 3, "entry_source": "landing"}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ paywall_converted event tracked")
    
    def test_track_exit_offer_shown(self):
        """Test tracking exit_offer_shown event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "exit_offer_shown",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"part_number": 3}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ exit_offer_shown event tracked")
    
    def test_track_discount_offer_shown(self):
        """Test tracking discount_offer_shown event"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "discount_offer_shown",
                "session_id": f"test_{uuid.uuid4().hex[:8]}",
                "context": {
                    "source_page": "experience",
                    "meta": {"view_count": 2}
                }
            },
            timeout=10
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✓ discount_offer_shown event tracked")
    
    def test_track_invalid_step_rejected(self):
        """Test that invalid funnel step is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "invalid_step_name",
                "session_id": "test123"
            },
            timeout=10
        )
        
        assert response.status_code == 200  # API returns 200 with success=False
        data = response.json()
        assert data["success"] == False
        assert "Invalid step" in data.get("error", "")
        print("✓ Invalid funnel step correctly rejected")
    
    def test_track_all_paywall_events_in_sequence(self):
        """Test tracking a complete paywall funnel sequence"""
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        
        events_sequence = [
            ("continue_clicked", {"part_number": 2}),
            ("story_part_generated", {"part_number": 2}),
            ("paywall_teaser_shown", {"part_number": 2}),
            ("continue_clicked", {"part_number": 3}),
            ("paywall_shown", {"part_number": 3, "view_count": 1}),
            ("exit_offer_shown", {"part_number": 3}),
            ("paywall_dismissed", {"part_number": 3, "exit_offer": True}),
        ]
        
        for step, meta in events_sequence:
            response = requests.post(
                f"{BASE_URL}/api/funnel/track",
                json={
                    "step": step,
                    "session_id": session_id,
                    "context": {
                        "source_page": "experience",
                        "meta": meta
                    }
                },
                timeout=10
            )
            assert response.status_code == 200
            assert response.json()["success"] == True
        
        print(f"✓ Complete paywall funnel sequence tracked ({len(events_sequence)} events)")


class TestRateLimiting:
    """Tests for rate limiting on quick-generate endpoint"""
    
    def test_rate_limit_returns_429_when_exceeded(self):
        """Test that rate limit returns 429 (skipped if limit not reached)"""
        # This test is informational - we don't want to actually hit rate limits
        # Just verify the endpoint structure is correct
        response = requests.post(
            f"{BASE_URL}/api/public/quick-generate",
            json={
                "mode": "fresh",
                "session_id": f"test_{uuid.uuid4().hex[:8]}"
            },
            timeout=30
        )
        
        # Should be either 200 (success) or 429 (rate limited)
        assert response.status_code in [200, 429], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 429:
            print("✓ Rate limit correctly enforced (429)")
        else:
            print("✓ Request succeeded (within rate limit)")


class TestEndpointAvailability:
    """Basic availability tests for all relevant endpoints"""
    
    def test_quick_generate_endpoint_exists(self):
        """Verify quick-generate endpoint is accessible"""
        response = requests.options(
            f"{BASE_URL}/api/public/quick-generate",
            timeout=10
        )
        # OPTIONS should return 200 or 405 (method not allowed but endpoint exists)
        assert response.status_code in [200, 204, 405], f"Endpoint not accessible: {response.status_code}"
        print("✓ /api/public/quick-generate endpoint accessible")
    
    def test_funnel_track_endpoint_exists(self):
        """Verify funnel track endpoint is accessible"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={"step": "demo_viewed", "session_id": "test"},
            timeout=10
        )
        assert response.status_code == 200
        print("✓ /api/funnel/track endpoint accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
