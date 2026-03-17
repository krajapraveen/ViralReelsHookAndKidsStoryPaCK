"""
P0 Bug Fix Tests - Iteration 142
Tests for:
- Bug 1: Blank page navigation (WaitingWithGames links with target="_blank")
- Bug 2: Story generation (status COMPLETED, credits deduction)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comic-pipeline-v2.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestCreditsAPI:
    """Tests for credits balance API (Bug 2 fix: credits display)"""
    
    def test_credits_balance_returns_both_fields(self, api_client):
        """Verify /credits/balance returns both 'balance' and 'credits' fields"""
        response = api_client.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200
        
        data = response.json()
        
        # Bug 2 Fix: API must return BOTH fields for frontend compatibility
        assert "balance" in data, "Missing 'balance' field"
        assert "credits" in data, "Missing 'credits' field"
        assert data["balance"] == data["credits"], "balance and credits should match"
        
        # Verify isFreeTier field exists
        assert "isFreeTier" in data, "Missing 'isFreeTier' field"
        
        print(f"Credits balance: {data['balance']}, isFreeTier: {data['isFreeTier']}")
    
    def test_credits_balance_numeric(self, api_client):
        """Verify credits are returned as numbers (not undefined/null)"""
        response = api_client.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200
        
        data = response.json()
        
        # Frontend was showing 0/undefined because of missing field
        assert isinstance(data["balance"], (int, float)), "balance must be numeric"
        assert data["balance"] >= 0, "balance must be non-negative"


class TestStoryGeneration:
    """Tests for story generation API (Bug 2 fix: story generation)"""
    
    def test_story_generation_success(self, api_client):
        """Test story generation returns COMPLETED status"""
        # Get initial credits
        credits_before = api_client.get(f"{BASE_URL}/api/credits/balance").json()["balance"]
        
        # Generate story
        response = api_client.post(
            f"{BASE_URL}/api/generate/story",
            json={
                "ageGroup": "6-8",
                "genre": "Fantasy",
                "theme": "Friendship",
                "sceneCount": 8
            },
            timeout=180  # Story generation takes 30-90 seconds
        )
        
        assert response.status_code == 200, f"Story generation failed: {response.text}"
        
        data = response.json()
        
        # Bug 2 Fix: Verify COMPLETED status
        assert data.get("status") == "COMPLETED", f"Expected COMPLETED status, got: {data.get('status')}"
        assert data.get("success") == True, "Expected success=True"
        
        # Verify result structure
        result = data.get("result", {})
        assert "title" in result, "Missing story title"
        assert "scenes" in result, "Missing scenes"
        assert len(result["scenes"]) > 0, "Scenes array is empty"
        
        # Verify credits deduction
        credits_after = api_client.get(f"{BASE_URL}/api/credits/balance").json()["balance"]
        credits_used = credits_before - credits_after
        assert credits_used == 10, f"Expected 10 credits deducted, got {credits_used}"
        
        print(f"Story generated: '{result['title']}' with {len(result['scenes'])} scenes")
        print(f"Credits: {credits_before} -> {credits_after} (deducted: {credits_used})")
    
    def test_story_generation_with_different_age_groups(self, api_client):
        """Test story generation works with different age groups"""
        age_groups = ["4-6", "8-10"]
        
        for age_group in age_groups:
            response = api_client.post(
                f"{BASE_URL}/api/generate/story",
                json={
                    "ageGroup": age_group,
                    "genre": "Adventure",
                    "theme": "Courage",
                    "sceneCount": 8
                },
                timeout=180
            )
            
            assert response.status_code == 200, f"Story generation failed for age {age_group}"
            data = response.json()
            assert data.get("status") == "COMPLETED"
            assert data.get("result", {}).get("title") is not None
            
            print(f"Age group {age_group}: Story generated successfully")


class TestReelGeneration:
    """Tests for reel generation API"""
    
    def test_reel_generation_success(self, api_client):
        """Test reel generation works correctly"""
        response = api_client.post(
            f"{BASE_URL}/api/generate/reel",
            json={
                "topic": "Morning productivity tips",
                "niche": "Lifestyle",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers"
            },
            timeout=60
        )
        
        assert response.status_code == 200, f"Reel generation failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "result" in data
        assert "hooks" in data["result"] or "script" in data["result"]
        
        print(f"Reel generated successfully")


class TestHealthAndAuth:
    """Basic health and auth tests"""
    
    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_login_success(self):
        """Verify login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        assert "token" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
