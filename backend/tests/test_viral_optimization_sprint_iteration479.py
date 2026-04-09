"""
Viral Optimization Sprint Tests - Iteration 479
Tests for:
1. GET /api/viral/momentum-meter - returns stories with momentum levels
2. GET /api/viral/my-nudges - returns pending nudges for current user
3. POST /api/viral/generate-nudges - creates reshare + progress nudges respecting 24h caps
4. POST /api/viral/dismiss-nudge - dismisses all user nudges
5. Security: No Phase C hidden data leaks in public viral endpoints
"""
import pytest
import requests
import os
from datetime import datetime, timezone

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
def test_user_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with auth header for test user"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestMomentumMeter:
    """Tests for GET /api/viral/momentum-meter endpoint"""
    
    def test_momentum_meter_requires_auth(self, api_client):
        """Momentum meter should require authentication"""
        # Clear any existing auth
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/viral/momentum-meter", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Momentum meter requires authentication")
    
    def test_momentum_meter_returns_stories(self, authenticated_client):
        """Momentum meter should return stories with momentum levels"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/momentum-meter")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] == True, "Success should be True"
        assert "stories" in data, "Response should have 'stories' field"
        assert isinstance(data["stories"], list), "Stories should be a list"
        print(f"✓ Momentum meter returns {len(data['stories'])} stories")
        
        # If there are stories, verify structure
        if len(data["stories"]) > 0:
            story = data["stories"][0]
            expected_fields = ["job_id", "title", "momentum_level", "momentum_label", "momentum_icon"]
            for field in expected_fields:
                assert field in story, f"Story should have '{field}' field"
            
            # Verify momentum levels are valid
            valid_levels = ["rising_fast", "trending", "spreading_widely", "steady"]
            assert story["momentum_level"] in valid_levels, f"Invalid momentum level: {story['momentum_level']}"
            print(f"✓ Story has valid momentum level: {story['momentum_level']}")
    
    def test_momentum_meter_no_phase_c_data_leak(self, authenticated_client):
        """Momentum meter should not leak Phase C hidden data"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/momentum-meter")
        assert response.status_code == 200
        
        data = response.json()
        # Check that no Phase C specific fields are exposed
        phase_c_fields = ["phase_c_score", "gamification_rank", "hidden_rewards", "dark_launch"]
        for story in data.get("stories", []):
            for field in phase_c_fields:
                assert field not in story, f"Phase C field '{field}' should not be exposed"
        print("✓ No Phase C data leaks in momentum meter")


class TestMyNudges:
    """Tests for GET /api/viral/my-nudges endpoint"""
    
    def test_my_nudges_requires_auth(self, api_client):
        """My nudges should require authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/viral/my-nudges", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ My nudges requires authentication")
    
    def test_my_nudges_returns_nudges(self, authenticated_client):
        """My nudges should return pending nudges for current user"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/my-nudges")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] == True, "Success should be True"
        assert "nudges" in data, "Response should have 'nudges' field"
        assert isinstance(data["nudges"], list), "Nudges should be a list"
        print(f"✓ My nudges returns {len(data['nudges'])} nudges")
        
        # If there are nudges, verify structure
        if len(data["nudges"]) > 0:
            nudge = data["nudges"][0]
            expected_fields = ["type", "title", "copy_variant_id", "dismissed"]
            for field in expected_fields:
                assert field in nudge, f"Nudge should have '{field}' field"
            
            # Verify nudge types are valid
            valid_types = ["reshare", "progress"]
            assert nudge["type"] in valid_types, f"Invalid nudge type: {nudge['type']}"
            print(f"✓ Nudge has valid type: {nudge['type']}")


class TestGenerateNudges:
    """Tests for POST /api/viral/generate-nudges endpoint"""
    
    def test_generate_nudges_works(self, api_client):
        """Generate nudges should create reshare + progress nudges"""
        # This endpoint doesn't require auth (it's a batch job)
        response = api_client.post(f"{BASE_URL}/api/viral/generate-nudges")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] == True, "Success should be True"
        assert "nudges_created" in data, "Response should have 'nudges_created' field"
        assert isinstance(data["nudges_created"], int), "nudges_created should be an integer"
        print(f"✓ Generate nudges created {data['nudges_created']} nudges")
    
    def test_generate_nudges_respects_24h_cap(self, api_client):
        """Generate nudges should respect 24h cap (running twice should not double nudges)"""
        # First call
        response1 = api_client.post(f"{BASE_URL}/api/viral/generate-nudges")
        assert response1.status_code == 200
        count1 = response1.json().get("nudges_created", 0)
        
        # Second call immediately after - should create 0 or fewer due to 24h cap
        response2 = api_client.post(f"{BASE_URL}/api/viral/generate-nudges")
        assert response2.status_code == 200
        count2 = response2.json().get("nudges_created", 0)
        
        # Second call should create 0 nudges (24h cap)
        assert count2 == 0, f"Expected 0 nudges on second call (24h cap), got {count2}"
        print(f"✓ Generate nudges respects 24h cap (first: {count1}, second: {count2})")


class TestDismissNudge:
    """Tests for POST /api/viral/dismiss-nudge endpoint"""
    
    def test_dismiss_nudge_requires_auth(self, api_client):
        """Dismiss nudge should require authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/api/viral/dismiss-nudge", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Dismiss nudge requires authentication")
    
    def test_dismiss_nudge_works(self, authenticated_client):
        """Dismiss nudge should dismiss all user nudges"""
        response = authenticated_client.post(f"{BASE_URL}/api/viral/dismiss-nudge")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should have 'success' field"
        assert data["success"] == True, "Success should be True"
        print("✓ Dismiss nudge works correctly")
    
    def test_dismiss_nudge_clears_nudges(self, authenticated_client):
        """After dismissing, my-nudges should return empty or dismissed nudges"""
        # First dismiss
        authenticated_client.post(f"{BASE_URL}/api/viral/dismiss-nudge")
        
        # Then check my-nudges
        response = authenticated_client.get(f"{BASE_URL}/api/viral/my-nudges")
        assert response.status_code == 200
        
        data = response.json()
        # All nudges should be dismissed (not returned in my-nudges)
        nudges = data.get("nudges", [])
        for nudge in nudges:
            # If nudges are returned, they should be dismissed
            if "dismissed" in nudge:
                assert nudge["dismissed"] == True, "Returned nudges should be dismissed"
        print(f"✓ After dismiss, my-nudges returns {len(nudges)} nudges (all dismissed)")


class TestViralEndpointsSecurity:
    """Security tests for viral endpoints - no Phase C data leaks"""
    
    def test_chain_stats_no_phase_c_leak(self, authenticated_client):
        """Chain stats should not leak Phase C data"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/chain-stats")
        assert response.status_code == 200
        
        data = response.json()
        # Check for Phase C fields that should not be exposed
        phase_c_fields = ["phase_c_enabled", "gamification_score", "hidden_achievements", "dark_mode_data"]
        for field in phase_c_fields:
            assert field not in data, f"Phase C field '{field}' should not be exposed in chain-stats"
        print("✓ No Phase C data leaks in chain-stats")
    
    def test_milestones_no_phase_c_leak(self, authenticated_client):
        """Milestones should not leak Phase C data"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/milestones")
        assert response.status_code == 200
        
        data = response.json()
        # Check for Phase C fields
        phase_c_fields = ["phase_c_badges", "hidden_rewards", "gamification_tier"]
        for field in phase_c_fields:
            assert field not in data, f"Phase C field '{field}' should not be exposed in milestones"
        print("✓ No Phase C data leaks in milestones")
    
    def test_rewards_status_no_phase_c_leak(self, authenticated_client):
        """Rewards status should not leak Phase C data"""
        response = authenticated_client.get(f"{BASE_URL}/api/viral/rewards/status")
        assert response.status_code == 200
        
        data = response.json()
        # Check for Phase C fields
        phase_c_fields = ["phase_c_rewards", "hidden_credits", "dark_launch_bonus"]
        for field in phase_c_fields:
            assert field not in data, f"Phase C field '{field}' should not be exposed in rewards/status"
        print("✓ No Phase C data leaks in rewards/status")


class TestMomentumLevelLogic:
    """Tests for momentum level calculation logic"""
    
    def test_momentum_levels_documented(self, authenticated_client):
        """Verify momentum levels match documented thresholds"""
        # According to spec:
        # - rising_fast: 1+ remixes in 7d
        # - trending: 1+ in 24h OR 5+ in 7d
        # - spreading_widely: 3+ in 24h
        
        response = authenticated_client.get(f"{BASE_URL}/api/viral/momentum-meter")
        assert response.status_code == 200
        
        data = response.json()
        for story in data.get("stories", []):
            level = story.get("momentum_level")
            remixes_24h = story.get("remixes_24h", 0)
            remixes_7d = story.get("remixes_7d", 0)
            
            # Verify level matches thresholds
            if level == "spreading_widely":
                assert remixes_24h >= 3, f"spreading_widely requires 3+ remixes in 24h, got {remixes_24h}"
            elif level == "trending":
                assert remixes_24h >= 1 or remixes_7d >= 5, f"trending requires 1+ in 24h or 5+ in 7d"
            elif level == "rising_fast":
                assert remixes_7d >= 1, f"rising_fast requires 1+ remixes in 7d, got {remixes_7d}"
        
        print("✓ Momentum levels match documented thresholds")


class TestNudgeCopyVariants:
    """Tests for nudge copy variant tagging"""
    
    def test_nudges_have_copy_variant_id(self, authenticated_client):
        """All nudges should have copy_variant_id for A/B tracking"""
        # First generate some nudges
        requests.post(f"{BASE_URL}/api/viral/generate-nudges")
        
        # Then check my-nudges
        response = authenticated_client.get(f"{BASE_URL}/api/viral/my-nudges")
        assert response.status_code == 200
        
        data = response.json()
        for nudge in data.get("nudges", []):
            assert "copy_variant_id" in nudge, "Nudge should have copy_variant_id"
            assert nudge["copy_variant_id"], "copy_variant_id should not be empty"
            # Verify it matches expected format
            assert "_v" in nudge["copy_variant_id"], f"copy_variant_id should contain version: {nudge['copy_variant_id']}"
        
        print("✓ All nudges have copy_variant_id for A/B tracking")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
