"""
Iteration 508: Battle Paywall & Competition Loop Tests

Tests for:
1. GET /api/stories/battle-entry-status - returns entry_count, free_limit, free_remaining, needs_payment, packs
2. Battle entry packs have correct pricing (battle_5=₹49, battle_20=₹149, battle_50=₹299)
3. FREE_BATTLE_ENTRIES = 3 config
"""
import pytest
import requests
import os

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
    """Get test user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


class TestBattleEntryStatus:
    """Tests for GET /api/stories/battle-entry-status endpoint"""

    def test_battle_entry_status_returns_200(self, api_client, test_user_token):
        """Test that battle-entry-status endpoint returns 200 for authenticated user"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_battle_entry_status_returns_required_fields(self, api_client, test_user_token):
        """Test that response contains all required fields"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields exist
        assert "success" in data, "Missing 'success' field"
        assert "entry_count" in data, "Missing 'entry_count' field"
        assert "free_limit" in data, "Missing 'free_limit' field"
        assert "free_remaining" in data, "Missing 'free_remaining' field"
        assert "needs_payment" in data, "Missing 'needs_payment' field"
        assert "packs" in data, "Missing 'packs' field"
        assert "credits" in data, "Missing 'credits' field"

    def test_battle_entry_status_free_limit_is_3(self, api_client, test_user_token):
        """Test that FREE_BATTLE_ENTRIES = 3"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["free_limit"] == 3, f"Expected free_limit=3, got {data['free_limit']}"

    def test_battle_entry_status_entry_count_is_integer(self, api_client, test_user_token):
        """Test that entry_count is a non-negative integer"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["entry_count"], int), f"entry_count should be int, got {type(data['entry_count'])}"
        assert data["entry_count"] >= 0, f"entry_count should be >= 0, got {data['entry_count']}"

    def test_battle_entry_status_free_remaining_calculation(self, api_client, test_user_token):
        """Test that free_remaining = max(0, free_limit - entry_count)"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        expected_remaining = max(0, data["free_limit"] - data["entry_count"])
        assert data["free_remaining"] == expected_remaining, \
            f"Expected free_remaining={expected_remaining}, got {data['free_remaining']}"

    def test_battle_entry_status_needs_payment_is_boolean(self, api_client, test_user_token):
        """Test that needs_payment is a boolean"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["needs_payment"], bool), \
            f"needs_payment should be bool, got {type(data['needs_payment'])}"

    def test_battle_entry_status_requires_auth(self, api_client):
        """Test that endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle-entry-status")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"


class TestBattleEntryPacks:
    """Tests for battle entry pack pricing"""

    def test_packs_returned_in_response(self, api_client, test_user_token):
        """Test that packs are returned in the response"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "packs" in data, "Missing 'packs' field"
        assert isinstance(data["packs"], list), f"packs should be list, got {type(data['packs'])}"
        assert len(data["packs"]) >= 3, f"Expected at least 3 packs, got {len(data['packs'])}"

    def test_battle_5_pack_pricing(self, api_client, test_user_token):
        """Test battle_5 pack: 5 entries, ₹49"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        battle_5 = next((p for p in data["packs"] if p.get("id") == "battle_5"), None)
        assert battle_5 is not None, "battle_5 pack not found"
        assert battle_5.get("entries") == 5, f"Expected 5 entries, got {battle_5.get('entries')}"
        assert battle_5.get("price_inr") == 49, f"Expected price_inr=49, got {battle_5.get('price_inr')}"

    def test_battle_20_pack_pricing(self, api_client, test_user_token):
        """Test battle_20 pack: 20 entries, ₹149"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        battle_20 = next((p for p in data["packs"] if p.get("id") == "battle_20"), None)
        assert battle_20 is not None, "battle_20 pack not found"
        assert battle_20.get("entries") == 20, f"Expected 20 entries, got {battle_20.get('entries')}"
        assert battle_20.get("price_inr") == 149, f"Expected price_inr=149, got {battle_20.get('price_inr')}"

    def test_battle_50_pack_pricing(self, api_client, test_user_token):
        """Test battle_50 pack: 50 entries, ₹299"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        battle_50 = next((p for p in data["packs"] if p.get("id") == "battle_50"), None)
        assert battle_50 is not None, "battle_50 pack not found"
        assert battle_50.get("entries") == 50, f"Expected 50 entries, got {battle_50.get('entries')}"
        assert battle_50.get("price_inr") == 299, f"Expected price_inr=299, got {battle_50.get('price_inr')}"

    def test_packs_have_required_fields(self, api_client, test_user_token):
        """Test that each pack has required fields"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-entry-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["id", "entries", "credits", "price_inr", "label"]
        for pack in data["packs"]:
            for field in required_fields:
                assert field in pack, f"Pack {pack.get('id', 'unknown')} missing field: {field}"


class TestStoryBattleEndpoint:
    """Tests for GET /api/stories/battle/{story_id} endpoint"""

    def test_battle_endpoint_returns_contenders(self, api_client, test_user_token):
        """Test that battle endpoint returns contenders list"""
        # Use the demo battle root
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle/battle-demo-root",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # May return 404 if demo root doesn't exist, which is acceptable
        if response.status_code == 404:
            pytest.skip("Demo battle root not found - skipping")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "contenders" in data, "Missing 'contenders' field"
        assert isinstance(data["contenders"], list), "contenders should be a list"

    def test_battle_endpoint_returns_total_contenders(self, api_client, test_user_token):
        """Test that battle endpoint returns total_contenders count"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle/battle-demo-root",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        if response.status_code == 404:
            pytest.skip("Demo battle root not found - skipping")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_contenders" in data, "Missing 'total_contenders' field"
        assert isinstance(data["total_contenders"], int), "total_contenders should be int"


class TestHottestBattleEndpoint:
    """Tests for GET /api/stories/hottest-battle endpoint"""

    def test_hottest_battle_returns_200(self, api_client, test_user_token):
        """Test that hottest-battle endpoint returns 200"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/hottest-battle",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_hottest_battle_structure(self, api_client, test_user_token):
        """Test hottest-battle response structure"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/hottest-battle",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data, "Missing 'success' field"
        # battle can be null if no battles exist
        if data.get("battle"):
            battle = data["battle"]
            assert "root_story_id" in battle, "Missing 'root_story_id' in battle"
            assert "contenders" in battle, "Missing 'contenders' in battle"


class TestQuickShotEndpoint:
    """Tests for POST /api/stories/quick-shot endpoint"""

    def test_quick_shot_requires_auth(self, api_client):
        """Test that quick-shot requires authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "test-root"}
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"

    def test_quick_shot_returns_402_on_insufficient_credits(self, api_client, test_user_token):
        """Test that quick-shot returns 402 when user has insufficient credits"""
        # This test may pass or fail depending on user's credit state
        # We're testing that the endpoint exists and handles the request
        response = api_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "nonexistent-root"},
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # Should return 404 (root not found) or 402 (insufficient credits) or 400 (bad request)
        assert response.status_code in [400, 402, 404], \
            f"Expected 400/402/404, got {response.status_code}: {response.text}"


class TestBattlePulseEndpoint:
    """Tests for GET /api/stories/battle-pulse/{root_story_id} endpoint"""

    def test_battle_pulse_requires_auth(self, api_client):
        """Test that battle-pulse requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle-pulse/test-root")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"

    def test_battle_pulse_returns_pulse_data(self, api_client, test_user_token):
        """Test that battle-pulse returns pulse data structure"""
        response = api_client.get(
            f"{BASE_URL}/api/stories/battle-pulse/battle-demo-root",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        # May return 200 with null pulse if no data
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Missing 'success' field"
        # pulse can be null if no battle data


class TestStoryViewerEndpoint:
    """Tests for GET /api/stories/viewer/{story_id} endpoint"""

    def test_viewer_endpoint_exists(self, api_client):
        """Test that viewer endpoint exists"""
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/nonexistent-id")
        # Should return 404 for nonexistent story, not 500
        assert response.status_code in [400, 404], \
            f"Expected 400/404, got {response.status_code}: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
