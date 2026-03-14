"""
Iteration 161 - Dashboard Engagement System & Features Tests
Tests: Daily Challenge, Streak, Creator Level, AI Ideas, Trending, Universal Prompt, Hero Actions
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-challenges-10.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


class TestSetup:
    """Test setup and authentication"""
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_USER_EMAIL, "password": ADMIN_USER_PASSWORD},
            timeout=10
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]


class TestEngagementDashboardAPI(TestSetup):
    """Tests for /api/engagement/dashboard endpoint"""
    
    def test_dashboard_returns_all_engagement_data(self, test_user_token):
        """GET /api/engagement/dashboard returns challenge, streak, level, ideas"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Dashboard API failed: {response.text}"
        data = response.json()
        
        # Verify all required fields present
        assert "challenge" in data, "Missing 'challenge' field"
        assert "streak" in data, "Missing 'streak' field"
        assert "level" in data, "Missing 'level' field"
        assert "ideas" in data, "Missing 'ideas' field"
        
    def test_challenge_data_structure(self, test_user_token):
        """Verify daily challenge has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200
        challenge = response.json().get("challenge", {})
        
        assert "prompt" in challenge, "Challenge missing 'prompt'"
        assert "reward" in challenge, "Challenge missing 'reward'"
        assert "tool" in challenge, "Challenge missing 'tool'"
        assert "completed" in challenge, "Challenge missing 'completed'"
        assert "challenge_id" in challenge, "Challenge missing 'challenge_id'"
        assert "date" in challenge, "Challenge missing 'date'"
        
        # Verify date is today
        today = datetime.now().strftime("%Y-%m-%d")
        assert challenge["date"] == today, f"Challenge date {challenge['date']} != today {today}"
        
        # Verify reward is positive integer
        assert isinstance(challenge["reward"], int), "Reward should be integer"
        assert challenge["reward"] > 0, "Reward should be positive"
        
    def test_streak_data_structure(self, test_user_token):
        """Verify streak has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200
        streak = response.json().get("streak", {})
        
        assert "current" in streak, "Streak missing 'current'"
        assert "longest" in streak, "Streak missing 'longest'"
        assert isinstance(streak["current"], int), "Current streak should be integer"
        assert isinstance(streak["longest"], int), "Longest streak should be integer"
        assert streak["current"] >= 0, "Current streak should be non-negative"
        
    def test_creator_level_data_structure(self, test_user_token):
        """Verify creator level has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200
        level = response.json().get("level", {})
        
        assert "level" in level, "Level missing 'level' name"
        assert "creation_count" in level, "Level missing 'creation_count'"
        assert "next_level_at" in level, "Level missing 'next_level_at'"
        assert "progress" in level, "Level missing 'progress'"
        
        # Verify level is valid
        valid_levels = ["Beginner", "Creator", "Creator Pro", "AI Producer", "Visionary"]
        assert level["level"] in valid_levels, f"Invalid level: {level['level']}"
        
        # Verify progress is 0-100
        assert 0 <= level["progress"] <= 100, f"Progress {level['progress']} out of range"
        
    def test_ai_ideas_data_structure(self, test_user_token):
        """Verify AI ideas returns 4 personalized suggestions"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200
        ideas = response.json().get("ideas", [])
        
        assert len(ideas) == 4, f"Expected 4 ideas, got {len(ideas)}"
        
        for i, idea in enumerate(ideas):
            assert "text" in idea, f"Idea {i} missing 'text'"
            assert "tool" in idea, f"Idea {i} missing 'tool'"
            assert len(idea["text"]) > 0, f"Idea {i} has empty text"
            
    def test_dashboard_requires_auth(self):
        """Dashboard API should require authentication"""
        response = requests.get(f"{BASE_URL}/api/engagement/dashboard", timeout=10)
        assert response.status_code == 401, "Dashboard should require auth"


class TestChallengeComplete(TestSetup):
    """Tests for /api/engagement/challenge/complete endpoint"""
    
    def test_challenge_complete_requires_auth(self):
        """POST /api/engagement/challenge/complete requires authentication"""
        response = requests.post(f"{BASE_URL}/api/engagement/challenge/complete", timeout=10)
        assert response.status_code == 401, "Challenge complete should require auth"
        
    def test_challenge_complete_or_already_completed(self, test_user_token):
        """POST /api/engagement/challenge/complete returns success or already completed"""
        response = requests.post(
            f"{BASE_URL}/api/engagement/challenge/complete",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        # Either 200 (success) or 400 (already completed today) is valid
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Missing 'success' field"
            assert "reward" in data, "Missing 'reward' field"
            assert "new_balance" in data, "Missing 'new_balance' field"
            assert data["success"] is True, "Success should be True"
            assert isinstance(data["reward"], int), "Reward should be integer"
        else:
            data = response.json()
            # Should indicate already completed
            assert "detail" in data or "message" in data, "Should have error detail"


class TestStreakUpdate(TestSetup):
    """Tests for /api/engagement/streak/update endpoint"""
    
    def test_streak_update_requires_auth(self):
        """POST /api/engagement/streak/update requires authentication"""
        response = requests.post(f"{BASE_URL}/api/engagement/streak/update", timeout=10)
        assert response.status_code == 401, "Streak update should require auth"
        
    def test_streak_update_returns_streak_info(self, test_user_token):
        """POST /api/engagement/streak/update returns streak information"""
        response = requests.post(
            f"{BASE_URL}/api/engagement/streak/update",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Streak update failed: {response.text}"
        data = response.json()
        
        assert "success" in data, "Missing 'success' field"
        assert "streak" in data, "Missing 'streak' field"
        assert "milestone_reward" in data, "Missing 'milestone_reward' field"
        assert data["success"] is True, "Success should be True"
        assert isinstance(data["streak"], int), "Streak should be integer"


class TestTrending(TestSetup):
    """Tests for /api/engagement/trending endpoint"""
    
    def test_trending_returns_gallery_items(self):
        """GET /api/engagement/trending returns trending creations"""
        response = requests.get(f"{BASE_URL}/api/engagement/trending", timeout=10)
        assert response.status_code == 200, f"Trending API failed: {response.text}"
        data = response.json()
        
        assert "trending" in data, "Missing 'trending' field"
        assert isinstance(data["trending"], list), "Trending should be a list"
        
        # If there are trending items, verify structure
        for item in data["trending"][:3]:  # Check up to 3 items
            if "title" in item:
                assert "job_id" in item, "Trending item missing 'job_id'"


class TestWalletAPI(TestSetup):
    """Tests for wallet/credits API"""
    
    def test_wallet_returns_credits(self, test_user_token):
        """GET /api/wallet/ returns credit balance"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Wallet API failed: {response.text}"
        data = response.json()
        
        # Check for credits field
        has_credits = "balanceCredits" in data or "availableCredits" in data or "credits" in data
        assert has_credits, f"No credits field in wallet response: {data.keys()}"
        

class TestUserProfile(TestSetup):
    """Tests for user profile/current user API"""
    
    def test_current_user_returns_user_data(self, test_user_token):
        """GET /api/auth/me returns user information"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Auth/me API failed: {response.text}"
        data = response.json()
        
        # Verify user data structure
        user = data.get("user") or data
        assert "email" in user, "Missing 'email' field"
        assert user["email"] == TEST_USER_EMAIL, f"Email mismatch: {user['email']}"


class TestGenerationHistory(TestSetup):
    """Tests for generation history API"""
    
    def test_generations_returns_list(self, test_user_token):
        """GET /api/generations returns user's generation history"""
        response = requests.get(
            f"{BASE_URL}/api/generations?limit=5",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Generations API failed: {response.text}"
        data = response.json()
        
        # Should have generations list
        assert "generations" in data, f"Missing 'generations' field: {data.keys()}"
        assert isinstance(data["generations"], list), "Generations should be a list"


class TestHeroCardRoutes(TestSetup):
    """Tests to verify hero action card routes exist"""
    
    def test_story_video_studio_page_exists(self, test_user_token):
        """Verify /app/story-video-studio route loads (check API options)"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/options",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Pipeline options failed: {response.text}"
        data = response.json()
        assert "animation_styles" in data, "Missing animation styles"
        
    def test_reels_page_exists(self, test_user_token):
        """Verify reel generator API exists"""
        response = requests.get(
            f"{BASE_URL}/api/generations?type=REEL&limit=1",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        # Should return 200 even if empty
        assert response.status_code == 200


class TestAdminAccess(TestSetup):
    """Tests for admin user access"""
    
    def test_admin_user_has_admin_role(self, admin_token):
        """Verify admin user has ADMIN role"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        user = data.get("user") or data
        assert user.get("role") in ["ADMIN", "admin"], f"Admin role mismatch: {user.get('role')}"
        
    def test_admin_dashboard_accessible(self, admin_token):
        """Verify admin can access admin endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        # Admin stats should be accessible
        assert response.status_code == 200, f"Admin stats failed: {response.text}"


class TestQuickLinks(TestSetup):
    """Tests for quick link API endpoints"""
    
    def test_referral_page_api_exists(self, test_user_token):
        """Verify referral API exists"""
        response = requests.get(
            f"{BASE_URL}/api/referral/stats",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        # Should return 200 or 404 if no referrals
        assert response.status_code in [200, 404]
        
    def test_analytics_api_exists(self, test_user_token):
        """Verify analytics API exists"""
        response = requests.get(
            f"{BASE_URL}/api/user/analytics",
            headers={"Authorization": f"Bearer {test_user_token}"},
            timeout=10
        )
        # Analytics should be accessible
        assert response.status_code == 200


class TestGalleryPage(TestSetup):
    """Tests for Gallery page regression"""
    
    def test_gallery_loads(self):
        """Verify gallery/public items endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/gallery?limit=10",
            timeout=10
        )
        # Gallery should be publicly accessible
        assert response.status_code == 200, f"Gallery API failed: {response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
