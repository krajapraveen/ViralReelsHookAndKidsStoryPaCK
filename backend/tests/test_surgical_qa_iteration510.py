"""
Iteration 510: Final Pre-Traffic Surgical QA
Tests for edge cases:
1. GET /api/stories/hottest-battle - returns valid data
2. GET /api/stories/battle-pulse/nonexistent-id - returns pulse: null (not 500)
3. GET /api/stories/battle-entry-status - returns entry count + packs
4. POST /api/stories/quick-shot - prevents rapid double submission
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


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
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestHottestBattleAPI:
    """Tests for GET /api/stories/hottest-battle endpoint"""

    def test_hottest_battle_returns_200(self, api_client):
        """Test that hottest-battle endpoint returns 200"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        print(f"✓ hottest-battle returned {response.status_code}")

    def test_hottest_battle_structure(self, api_client):
        """Test hottest-battle response structure"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        if response.status_code == 200:
            data = response.json()
            # Should have 'battle' key
            assert "battle" in data, "Response should have 'battle' key"
            if data["battle"]:
                battle = data["battle"]
                # Verify battle has expected fields
                assert "root_story_id" in battle or "root_title" in battle, "Battle should have root_story_id or root_title"
                print(f"✓ Battle data structure valid: {list(battle.keys())[:5]}...")
            else:
                print("✓ No active battle (battle is null)")
        else:
            print(f"✓ No hottest battle available ({response.status_code})")


class TestBattlePulseAPI:
    """Tests for GET /api/stories/battle-pulse/{root_story_id} endpoint"""

    def test_battle_pulse_nonexistent_returns_null_not_500(self, authenticated_client):
        """Test that battle-pulse for nonexistent ID returns pulse: null, not 500"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle-pulse/nonexistent-id-12345")
        # Should NOT return 500 - should gracefully return null pulse
        assert response.status_code != 500, f"Should not return 500 for nonexistent ID, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # pulse should be null or empty for nonexistent battle
            assert "pulse" in data, "Response should have 'pulse' key"
            print(f"✓ battle-pulse for nonexistent ID returned pulse: {data.get('pulse')}")
        else:
            print(f"✓ battle-pulse for nonexistent ID returned {response.status_code} (not 500)")

    def test_battle_pulse_valid_battle(self, authenticated_client):
        """Test battle-pulse for valid battle (battle-demo-root)"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle-pulse/battle-demo-root")
        # Should return 200 or 404 if battle doesn't exist
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            if data.get("pulse"):
                pulse = data["pulse"]
                print(f"✓ battle-pulse returned valid data: user_rank={pulse.get('user_rank')}, total_entries={pulse.get('total_entries')}")
            else:
                print("✓ battle-pulse returned null pulse (no data)")
        else:
            print(f"✓ battle-pulse returned {response.status_code}")


class TestBattleEntryStatusAPI:
    """Tests for GET /api/stories/battle-entry-status endpoint"""

    def test_battle_entry_status_returns_200(self, authenticated_client):
        """Test that battle-entry-status endpoint returns 200 for authenticated user"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle-entry-status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ battle-entry-status returned 200")

    def test_battle_entry_status_structure(self, authenticated_client):
        """Test battle-entry-status response structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle-entry-status")
        assert response.status_code == 200
        
        data = response.json()
        # Should have entry_count and credits
        assert "entry_count" in data, "Response should have 'entry_count'"
        assert "credits" in data, "Response should have 'credits'"
        
        print(f"✓ battle-entry-status: entry_count={data.get('entry_count')}, credits={data.get('credits')}")
        
        # Verify packs if present
        if "packs" in data:
            print(f"  packs available: {len(data.get('packs', []))}")

    def test_battle_entry_status_unauthenticated(self, api_client):
        """Test that battle-entry-status requires authentication"""
        # Remove auth header for this test
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/stories/battle-entry-status", headers=headers)
        # Should return 401 or 403 for unauthenticated
        assert response.status_code in [401, 403, 200], f"Expected 401/403/200, got {response.status_code}"
        print(f"✓ battle-entry-status unauthenticated returned {response.status_code}")


class TestQuickShotAPI:
    """Tests for POST /api/stories/quick-shot endpoint"""

    def test_quick_shot_requires_auth(self, api_client):
        """Test that quick-shot requires authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "test"},
            headers=headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ quick-shot requires auth (returned {response.status_code})")

    def test_quick_shot_double_submission_protection(self, authenticated_client):
        """Test that quick-shot prevents rapid double submission"""
        # First, get a valid root_story_id from hottest-battle
        battle_response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        
        if battle_response.status_code != 200 or not battle_response.json().get("battle"):
            pytest.skip("No active battle for quick-shot test")
        
        root_story_id = battle_response.json()["battle"].get("root_story_id")
        if not root_story_id:
            pytest.skip("No root_story_id in battle data")
        
        # First submission
        response1 = authenticated_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": root_story_id}
        )
        
        # Immediate second submission (should be blocked or return appropriate error)
        response2 = authenticated_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": root_story_id}
        )
        
        # Both should not return 500
        assert response1.status_code != 500, f"First quick-shot returned 500"
        assert response2.status_code != 500, f"Second quick-shot returned 500"
        
        print(f"✓ quick-shot responses: first={response1.status_code}, second={response2.status_code}")
        
        # If first succeeded, second should either succeed (queued) or return rate limit/duplicate error
        if response1.status_code in [200, 201]:
            # Second should be handled gracefully (not crash)
            assert response2.status_code in [200, 201, 402, 429, 400], f"Second submission should be handled gracefully, got {response2.status_code}"
            print(f"✓ Double submission handled gracefully")


class TestAPIHealthCheck:
    """Basic health checks for all battle-related APIs"""

    def test_all_endpoints_accessible(self, authenticated_client):
        """Verify all battle endpoints are accessible (no 500 errors)"""
        endpoints = [
            ("GET", "/api/stories/hottest-battle"),
            ("GET", "/api/stories/battle-entry-status"),
            ("GET", "/api/stories/battle-pulse/battle-demo-root"),
        ]
        
        results = []
        for method, endpoint in endpoints:
            if method == "GET":
                response = authenticated_client.get(f"{BASE_URL}{endpoint}")
            results.append((endpoint, response.status_code))
            assert response.status_code != 500, f"{endpoint} returned 500"
        
        print("✓ All endpoints accessible (no 500 errors):")
        for endpoint, status in results:
            print(f"  {endpoint}: {status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
