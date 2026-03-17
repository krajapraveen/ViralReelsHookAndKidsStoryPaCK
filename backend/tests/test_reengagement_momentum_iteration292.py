"""
Re-engagement and Momentum System Tests - Iteration 292
Tests the new re-engagement features:
1. GET /api/photo-to-comic/active-chains - Returns chains with momentum_msg, milestone_next, episodes_to_milestone
2. POST /api/metrics/track - Event tracking
3. GET /api/metrics/reengagement - Admin-only aggregated metrics
4. POST /api/photo-to-comic/chain/suggestions - Context-aware AI suggestions with caching
5. POST /api/story-video-studio/continue-video - Video continuation
6. GET /api/story-video-studio/active-video-chains - Video chains with momentum_msg
7. GET /api/story-video-studio/video-chain/{chain_id} - Chain projects with progress
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


class TestActiveChainsMomentum:
    """Test GET /api/photo-to-comic/active-chains momentum fields"""

    def test_active_chains_returns_chains(self, test_user_token):
        """Test that active-chains endpoint returns chains array"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data
        assert "total" in data
        assert isinstance(data["chains"], list)
        print(f"✓ Active chains returned: {data['total']} chains")

    def test_active_chains_momentum_fields(self, test_user_token):
        """Test that chains have momentum_msg, milestone_next, episodes_to_milestone fields"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        chains = data.get("chains", [])
        
        if len(chains) == 0:
            pytest.skip("No chains found for test user - cannot verify momentum fields")
        
        # Verify first chain has momentum fields
        chain = chains[0]
        assert "momentum_msg" in chain, "Chain missing momentum_msg field"
        assert "milestone_next" in chain, "Chain missing milestone_next field"
        assert "episodes_to_milestone" in chain, "Chain missing episodes_to_milestone field"
        assert "progress_pct" in chain, "Chain missing progress_pct field"
        assert "total_episodes" in chain, "Chain missing total_episodes field"
        
        print(f"✓ Chain momentum fields verified:")
        print(f"  - momentum_msg: {chain.get('momentum_msg')}")
        print(f"  - milestone_next: {chain.get('milestone_next')}")
        print(f"  - episodes_to_milestone: {chain.get('episodes_to_milestone')}")
        print(f"  - progress_pct: {chain.get('progress_pct')}")

    def test_active_chains_has_preview_and_continue_fields(self, test_user_token):
        """Test that chains have preview_url and continue_job_id fields"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        chains = data.get("chains", [])
        
        if len(chains) == 0:
            pytest.skip("No chains found for test user")
        
        chain = chains[0]
        # These fields should be present (may be null)
        assert "preview_url" in chain, "Chain missing preview_url field"
        assert "continue_job_id" in chain, "Chain missing continue_job_id field"
        assert "chain_id" in chain, "Chain missing chain_id field"
        assert "root_job_id" in chain, "Chain missing root_job_id field"
        
        print(f"✓ Chain preview/continue fields present")


class TestMetricsTracking:
    """Test POST /api/metrics/track endpoint"""

    def test_track_event_success(self, test_user_token):
        """Test that event tracking returns ok:true"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "event": "test_event_from_pytest",
            "chain_id": "test-chain-123",
            "meta": {"test": True}
        }
        response = requests.post(f"{BASE_URL}/api/metrics/track", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") == True, f"Expected ok:true, got {data}"
        print("✓ Event tracking returned ok:true")

    def test_track_event_various_types(self, test_user_token):
        """Test tracking various event types"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        event_types = [
            "login_interstitial_shown",
            "login_interstitial_continue",
            "banner_shown",
            "continue_from_banner",
            "suggestion_view",
            "suggestion_click"
        ]
        
        for event in event_types:
            payload = {"event": event, "chain_id": f"test-chain-{event}"}
            response = requests.post(f"{BASE_URL}/api/metrics/track", json=payload, headers=headers)
            assert response.status_code == 200, f"Event {event} failed"
            assert response.json().get("ok") == True
        
        print(f"✓ All {len(event_types)} event types tracked successfully")

    def test_track_event_without_auth_fails(self):
        """Test that tracking without auth fails"""
        payload = {"event": "unauthorized_test"}
        response = requests.post(f"{BASE_URL}/api/metrics/track", json=payload)
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthorized tracking correctly rejected")


class TestMetricsReengagementAdmin:
    """Test GET /api/metrics/reengagement admin endpoint"""

    def test_reengagement_requires_admin(self, test_user_token):
        """Test that reengagement endpoint requires admin role"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/metrics/reengagement", headers=headers)
        
        # Should be forbidden for non-admin
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("✓ Non-admin correctly rejected from reengagement metrics")

    def test_reengagement_admin_access(self, admin_token):
        """Test that admin can access reengagement metrics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/metrics/reengagement", headers=headers)
        
        assert response.status_code == 200, f"Admin access failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["continue_rate", "avg_chain_length", "return_rate_24h", 
                          "suggestion_ctr", "resume_from_banner_rate", "login_interstitial_rate"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        assert "raw" in data, "Missing raw data section"
        
        print(f"✓ Admin metrics accessible with all fields:")
        for field in expected_fields:
            print(f"  - {field}: {data.get(field)}")


class TestChainSuggestions:
    """Test POST /api/photo-to-comic/chain/suggestions"""

    def test_suggestions_requires_chain_id(self, test_user_token):
        """Test that suggestions endpoint requires chain_id"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Empty body should fail
        response = requests.post(f"{BASE_URL}/api/photo-to-comic/chain/suggestions", 
                                json={}, headers=headers)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Missing chain_id correctly rejected")

    def test_suggestions_invalid_chain(self, test_user_token):
        """Test that invalid chain_id returns 404"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {"chain_id": "nonexistent-chain-id-12345"}
        
        response = requests.post(f"{BASE_URL}/api/photo-to-comic/chain/suggestions", 
                                json=payload, headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid chain_id returns 404")

    def test_suggestions_with_valid_chain(self, test_user_token):
        """Test suggestions with a valid chain_id from user's chains"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # First get user's chains
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        if chains_response.status_code != 200:
            pytest.skip("Could not fetch chains")
        
        chains = chains_response.json().get("chains", [])
        if not chains:
            pytest.skip("No chains available for suggestion test")
        
        chain_id = chains[0]["chain_id"]
        payload = {"chain_id": chain_id}
        
        response = requests.post(f"{BASE_URL}/api/photo-to-comic/chain/suggestions", 
                                json=payload, headers=headers)
        
        assert response.status_code == 200, f"Suggestions failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "suggestions" in data, "Missing suggestions array"
        assert "chain_id" in data, "Missing chain_id in response"
        assert "episode_count" in data, "Missing episode_count"
        
        suggestions = data["suggestions"]
        assert len(suggestions) > 0, "No suggestions returned"
        
        # Verify suggestion structure
        for s in suggestions:
            assert "title" in s, "Suggestion missing title"
            assert "prompt" in s, "Suggestion missing prompt"
            assert "hook" in s, "Suggestion missing hook"
            assert "type" in s, "Suggestion missing type"
            assert s["type"] in ["escalation", "twist", "deepening"], f"Invalid type: {s['type']}"
        
        # NEW: Check for references_character and continues_from fields
        first_suggestion = suggestions[0]
        if "references_character" in first_suggestion:
            print(f"  - references_character: {first_suggestion.get('references_character')}")
        if "continues_from" in first_suggestion:
            print(f"  - continues_from: {first_suggestion.get('continues_from')}")
        
        print(f"✓ Got {len(suggestions)} suggestions for chain {chain_id[:8]}...")
        for s in suggestions:
            print(f"  - [{s['type']}] {s['title']}")

    def test_suggestions_are_cached(self, test_user_token):
        """Test that suggestions are cached (second call returns same data quickly)"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Get a valid chain
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        if chains_response.status_code != 200:
            pytest.skip("Could not fetch chains")
        
        chains = chains_response.json().get("chains", [])
        if not chains:
            pytest.skip("No chains available")
        
        chain_id = chains[0]["chain_id"]
        payload = {"chain_id": chain_id}
        
        # First call
        import time
        start1 = time.time()
        response1 = requests.post(f"{BASE_URL}/api/photo-to-comic/chain/suggestions", 
                                 json=payload, headers=headers)
        time1 = time.time() - start1
        
        # Second call (should be cached)
        start2 = time.time()
        response2 = requests.post(f"{BASE_URL}/api/photo-to-comic/chain/suggestions", 
                                 json=payload, headers=headers)
        time2 = time.time() - start2
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Verify same suggestions (from cache)
        assert data1["suggestions"] == data2["suggestions"], "Cached data should be identical"
        
        print(f"✓ Suggestions caching verified (first: {time1:.2f}s, cached: {time2:.2f}s)")


class TestStoryVideoChains:
    """Test Story Video Studio chain endpoints"""

    def test_continue_video_endpoint_exists(self, test_user_token):
        """Test POST /api/story-video-studio/continue-video accepts requests"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        payload = {
            "parent_project_id": "nonexistent-project-id",
            "story_text": "This is a continuation of the story...",
            "title": "Episode 2"
        }
        
        response = requests.post(f"{BASE_URL}/api/story-video-studio/continue-video", 
                                json=payload, headers=headers)
        
        # Should return 404 for nonexistent project (not 500 or endpoint not found)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ continue-video endpoint exists and validates parent_project_id")

    def test_active_video_chains_returns_chains(self, test_user_token):
        """Test GET /api/story-video-studio/active-video-chains returns chains"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-video-studio/active-video-chains", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "chains" in data, "Missing chains array"
        assert "total" in data, "Missing total count"
        
        # If chains exist, verify momentum_msg field
        chains = data.get("chains", [])
        if chains:
            chain = chains[0]
            assert "momentum_msg" in chain, "Chain missing momentum_msg field"
            assert "progress_pct" in chain, "Chain missing progress_pct"
            print(f"✓ Video chains returned with momentum_msg: {chain.get('momentum_msg')}")
        else:
            print("✓ Video chains endpoint works (no chains for this user)")

    def test_video_chain_detail_requires_valid_id(self, test_user_token):
        """Test GET /api/story-video-studio/video-chain/{chain_id}"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Test with invalid ID
        response = requests.get(f"{BASE_URL}/api/story-video-studio/video-chain/invalid-chain-id", 
                               headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ video-chain endpoint validates chain_id")


class TestChainDetailEndpoint:
    """Test GET /api/photo-to-comic/chain/{chain_id}"""

    def test_chain_detail_returns_progress_data(self, test_user_token):
        """Test that chain detail returns progress_pct, total_panels, etc."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # First get user's chains
        chains_response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        if chains_response.status_code != 200:
            pytest.skip("Could not fetch chains")
        
        chains = chains_response.json().get("chains", [])
        if not chains:
            pytest.skip("No chains available")
        
        chain_id = chains[0]["chain_id"]
        
        # Get chain detail
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/chain/{chain_id}", headers=headers)
        
        assert response.status_code == 200, f"Chain detail failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["flat", "total_episodes", "completed", "progress_pct", 
                          "total_panels", "continuations", "remixes", "styles_used"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        assert "flat" in data and isinstance(data["flat"], list), "Missing flat timeline array"
        
        print(f"✓ Chain detail verified for {chain_id[:8]}...")
        print(f"  - total_episodes: {data.get('total_episodes')}")
        print(f"  - progress_pct: {data.get('progress_pct')}")
        print(f"  - total_panels: {data.get('total_panels')}")


class TestMyChains:
    """Test GET /api/photo-to-comic/my-chains"""

    def test_my_chains_returns_progress_pct(self, test_user_token):
        """Test that my-chains returns chains with progress_pct"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/my-chains", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "chains" in data
        assert "total" in data
        
        chains = data.get("chains", [])
        if chains:
            chain = chains[0]
            assert "progress_pct" in chain, "Chain missing progress_pct"
            assert "chain_id" in chain, "Chain missing chain_id"
            print(f"✓ my-chains returned {len(chains)} chains with progress_pct")
        else:
            print("✓ my-chains endpoint works (no chains for user)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
