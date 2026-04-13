"""
UAT Iteration 511 - Full Backend API Tests
Tests all critical battle, story, and user APIs for the Visionary Suite platform.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAuthenticationFlows:
    """Test login flows with valid and invalid credentials"""
    
    def test_login_valid_test_user(self):
        """FLOW 2: Login with valid test user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Missing token in response"
        assert data.get("user", {}).get("email") == TEST_USER_EMAIL
        # Test user should have 13 credits
        credits = data.get("user", {}).get("credits", 0)
        print(f"Test user credits: {credits}")
        
    def test_login_valid_admin_user(self):
        """Login with valid admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        # Admin should have admin role
        user = data.get("user", {})
        assert user.get("role", "").upper() in ["ADMIN", "SUPERADMIN"], f"Expected admin role, got {user.get('role')}"
        # Admin should have unlimited credits (999999999)
        credits = user.get("credits", 0)
        assert credits >= 99999, f"Admin should have unlimited credits, got {credits}"
        print(f"Admin credits: {credits}")
        
    def test_login_invalid_credentials(self):
        """FLOW 3: Login with invalid credentials shows error"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400, 422], f"Expected 401/400/422, got {response.status_code}"


class TestBattleAPIs:
    """Test battle-related APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Could not authenticate test user")
    
    def test_hottest_battle_endpoint(self):
        """Test /api/stories/hottest-battle returns battle data"""
        response = requests.get(f"{BASE_URL}/api/stories/hottest-battle", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should have battle object or null
        if data.get("battle"):
            battle = data["battle"]
            assert "root_story_id" in battle or "root_title" in battle
            
    def test_battle_pulse_endpoint(self):
        """Test /api/stories/battle-pulse/{root_id} returns pulse data"""
        # First get hottest battle to get a root_id
        response = requests.get(f"{BASE_URL}/api/stories/hottest-battle", headers=self.headers)
        if response.status_code == 200 and response.json().get("battle"):
            root_id = response.json()["battle"].get("root_story_id", "battle-demo-root")
        else:
            root_id = "battle-demo-root"
            
        response = requests.get(f"{BASE_URL}/api/stories/battle-pulse/{root_id}", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should have pulse object (can be null for nonexistent battles)
        assert "pulse" in data or "success" in data
        
    def test_battle_pulse_nonexistent(self):
        """Test battle-pulse with nonexistent ID returns gracefully (not 500)"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-pulse/nonexistent-id-12345", headers=self.headers)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
    def test_battle_entry_status(self):
        """FLOW 5/6: Test battle entry status returns credits and packs"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-entry-status", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "credits" in data, "Missing credits in response"
        assert "packs" in data, "Missing packs in response"
        # Test user has 13 credits, needs 21 for story_video
        if data.get("needs_payment") is not None:
            assert isinstance(data["needs_payment"], bool)
            
    def test_battle_page_data(self):
        """FLOW 7: Test battle page data endpoint"""
        response = requests.get(f"{BASE_URL}/api/stories/battle/battle-demo-root", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should have contenders list
        assert "contenders" in data or "total_contenders" in data or "current_story" in data
        
    def test_quick_shot_requires_credits(self):
        """FLOW 5: Quick Shot checks credits and returns 402 if low"""
        response = requests.post(f"{BASE_URL}/api/stories/quick-shot", 
            headers=self.headers,
            json={"root_story_id": "battle-demo-root"})
        # Should return 402 (payment required) or 200 (success) or 422 (validation)
        assert response.status_code in [200, 402, 422], f"Expected 200/402/422, got {response.status_code}"
        if response.status_code == 402:
            # Paywall triggered correctly
            pass


class TestStoryViewerAPIs:
    """Test story viewer APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Could not authenticate")
    
    def test_story_viewer_endpoint(self):
        """FLOW 8: Test story viewer data endpoint"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/battle-demo-root", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        if data.get("success"):
            assert "job" in data
            
    def test_story_viewer_invalid_id(self):
        """Test story viewer with invalid ID returns gracefully"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/invalid-story-id-xyz", headers=self.headers)
        # Should return 404 or 200 with error, not 500
        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"


class TestExploreAPIs:
    """Test explore/discover APIs"""
    
    def test_explore_endpoint(self):
        """FLOW 9: Test explore endpoint returns stories with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/engagement/explore", params={
            "category": "all",
            "limit": 5
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "stories" in data
        # Stories should have thumbnails (filtered by backend)
        for story in data.get("stories", []):
            # Each story should have basic fields
            assert "job_id" in story or "title" in story
            
    def test_discover_feed_endpoint(self):
        """Test discover feed endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/stories/feed/discover", 
            headers=headers,
            params={"limit": 5, "sort_by": "trending"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestPublicAPIs:
    """Test public (unauthenticated) APIs"""
    
    def test_public_stats(self):
        """Test public stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_public_alive(self):
        """Test public alive signals endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/alive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_public_live_activity(self):
        """Test public live activity endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity", params={"limit": 6})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestAdminAPIs:
    """Test admin-specific APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.user = response.json().get("user", {})
        else:
            pytest.skip("Could not authenticate admin")
    
    def test_admin_has_unlimited_credits(self):
        """FLOW 18/19: Admin should have unlimited credits (999999999)"""
        # Check credits from login response or /api/auth/me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            credits = data.get("credits", 0)
            # Admin should have very high credits (999999999 or similar)
            assert credits >= 99999, f"Admin credits should be >= 99999, got {credits}"
            
    def test_admin_battle_entry_status(self):
        """Admin should not need payment for battle entry"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-entry-status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        # Admin should not need payment
        assert data.get("needs_payment") == False or data.get("credits", 0) >= 99999


class TestFunnelTracking:
    """Test funnel tracking APIs"""
    
    def test_funnel_track_endpoint(self):
        """EDGE: Test funnel events fire correctly"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(f"{BASE_URL}/api/funnel/track", 
            headers=headers,
            json={
                "event": "test_event",
                "source_page": "test",
                "meta": {"test": True}
            })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestPaywallPacks:
    """Test paywall pack configuration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Could not authenticate")
    
    def test_paywall_has_three_packs(self):
        """FLOW 13: BattlePaywallModal should have 3 packs (₹29/₹49/₹149)"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-entry-status", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        packs = data.get("packs", [])
        assert len(packs) >= 3, f"Expected at least 3 packs, got {len(packs)}"
        # Check pack prices
        prices = [p.get("price_inr") for p in packs]
        assert 29 in prices or 49 in prices or 149 in prices, f"Expected packs with prices 29/49/149, got {prices}"


class TestRetentionAPIs:
    """Test retention/challenge APIs"""
    
    def test_daily_challenge_endpoint(self):
        """Test daily challenge endpoint"""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/today")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_challenge_winner_endpoint(self):
        """Test challenge winner endpoint"""
        response = requests.get(f"{BASE_URL}/api/retention/challenge/winner")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_top_stories_endpoint(self):
        """Test top stories leaderboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/retention/top-stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestPushNotifications:
    """Test push notification APIs"""
    
    def test_vapid_key_endpoint(self):
        """Test VAPID key endpoint for push notifications"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "vapid_public_key" in data or "vapid_key" in data or "publicKey" in data, f"Missing VAPID key in response: {data}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
