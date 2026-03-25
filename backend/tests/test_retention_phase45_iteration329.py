"""
Phase 4.5 Retention Engine - Behavioral Tightening Tests
Tests: Forced decision modal, emotional streak messaging, auto-next trigger,
       email nudge system, hook-based content seeding, reward celebration
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


class TestRetentionPhase45:
    """Phase 4.5 Behavioral Tightening Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_test_user_token(self):
        """Get auth token for test user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_admin_token(self):
        """Get auth token for admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # STREAK API TESTS - Emotional messaging support
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_streak_api_returns_valid_data(self):
        """GET /api/retention/streak returns streak data with milestone info"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert "current_streak" in data
        assert "longest_streak" in data
        assert "milestones_claimed" in data
        # next_milestone should be 3 or 7 (or None if all claimed)
        if data.get("next_milestone"):
            assert data["next_milestone"] in [3, 7]
        # next_reward should be 10 or 25 (or None)
        if data.get("next_reward"):
            assert data["next_reward"] in [10, 25]
        
        print(f"✓ Streak API: current={data['current_streak']}, longest={data['longest_streak']}, next_milestone={data.get('next_milestone')}")

    def test_streak_api_requires_auth(self):
        """GET /api/retention/streak requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/retention/streak")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Streak API requires authentication")

    # ═══════════════════════════════════════════════════════════════════════════
    # RETURN BANNER API TESTS - Cliffhanger + character name
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_return_banner_api_returns_story_data(self):
        """GET /api/retention/return-banner returns story + cliffhanger for forced decision modal"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/return-banner",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert "has_story" in data
        
        if data.get("has_story"):
            assert "story" in data
            assert "cliffhanger" in data
            # character_name may be None if no characters extracted
            print(f"✓ Return banner: has_story=True, cliffhanger='{data.get('cliffhanger', '')[:50]}...'")
        else:
            print("✓ Return banner: has_story=False (user has no completed stories)")

    def test_return_banner_requires_auth(self):
        """GET /api/retention/return-banner requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/retention/return-banner")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Return banner API requires authentication")

    # ═══════════════════════════════════════════════════════════════════════════
    # EMAIL NUDGE SYSTEM TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_admin_email_nudge_queue_endpoint(self):
        """GET /api/retention/admin/email-nudges returns pending/sent counts"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/admin/email-nudges",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert "pending_count" in data
        assert "sent_count" in data
        assert "recent_pending" in data
        assert "note" in data  # Should mention email service integration
        
        print(f"✓ Email nudge queue: pending={data['pending_count']}, sent={data['sent_count']}")

    def test_admin_email_nudge_requires_admin(self):
        """GET /api/retention/admin/email-nudges requires admin role"""
        # Test with regular user token
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/admin/email-nudges",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("✓ Email nudge queue requires admin role")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTENT SEEDING TESTS - Hook-based themes
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_admin_seed_content_endpoint(self):
        """POST /api/retention/admin/seed-content works for admin with hook-based themes"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.post(
            f"{BASE_URL}/api/retention/admin/seed-content",
            headers={"Authorization": f"Bearer {token}"},
            json={"count": 1}  # Just test with 1 to avoid creating too many
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert "job_ids" in data
        assert "message" in data
        
        print(f"✓ Seed content: created {len(data.get('job_ids', []))} job(s)")

    def test_admin_seed_content_requires_admin(self):
        """POST /api/retention/admin/seed-content requires admin role"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.post(
            f"{BASE_URL}/api/retention/admin/seed-content",
            headers={"Authorization": f"Bearer {token}"},
            json={"count": 1}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("✓ Seed content requires admin role")

    def test_admin_seed_status_endpoint(self):
        """GET /api/retention/admin/seed-status returns seed content stats"""
        token = self.get_admin_token()
        assert token, "Failed to get admin token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/admin/seed-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        assert "total" in data
        assert "completed" in data
        assert "failed" in data
        assert "queued" in data
        
        print(f"✓ Seed status: total={data['total']}, completed={data['completed']}, queued={data['queued']}")

    # ═══════════════════════════════════════════════════════════════════════════
    # UNIVERSE/RANKINGS API TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_universe_rankings_api(self):
        """GET /api/universe/rankings returns character rankings"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/universe/rankings",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True
        # API returns top_characters, top_creators, top_stories
        assert "top_characters" in data or "top_creators" in data or "top_stories" in data
        
        print(f"✓ Universe rankings API working")

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Health endpoint working")


class TestEmotionalStreakMessaging:
    """Tests for emotional streak messaging logic (frontend-driven, API provides data)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_test_user_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_streak_data_supports_emotional_messaging(self):
        """Verify streak API returns data needed for emotional messaging"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Frontend uses current_streak to determine emotional message:
        # 0: "Create a story today to start your streak"
        # 1: "Great start! Come back tomorrow to build momentum"
        # <3: "Don't break it — your story streak is growing"
        # <7: "You're on fire! Keep the momentum going"
        # 7+: "Legendary streak! You're a storytelling machine"
        
        current_streak = data.get("current_streak", 0)
        assert isinstance(current_streak, int)
        
        # Verify milestone data for "Continue today to keep your streak alive" text
        if data.get("next_milestone"):
            assert data["next_milestone"] in [3, 7]
            assert data.get("next_reward") in [10, 25]
        
        print(f"✓ Streak data supports emotional messaging: streak={current_streak}")


class TestForcedDecisionModal:
    """Tests for forced decision modal data (3-sec modal on Dashboard)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_test_user_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_return_banner_provides_modal_data(self):
        """Return banner API provides data for forced decision modal"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/return-banner",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Modal needs: headline ("Your story is waiting"), cliffhanger text
        # Continue Now button, Later button
        if data.get("has_story"):
            assert "cliffhanger" in data
            assert "story" in data
            # character_name used for personalized headline
            print(f"✓ Modal data available: cliffhanger='{data.get('cliffhanger', '')[:40]}...'")
        else:
            print("✓ No story for modal (user has no completed stories)")


class TestPostGenerationTrigger:
    """Tests for post-generation auto-next trigger data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_test_user_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def test_streak_api_for_reward_celebration(self):
        """Streak API provides data for reward celebration toast"""
        token = self.get_test_user_token()
        assert token, "Failed to get test user token"
        
        response = self.session.get(
            f"{BASE_URL}/api/retention/streak",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # PostGenPhase checks streak on READY state for celebration
        # Needs: current_streak, milestones_claimed
        assert "current_streak" in data
        assert "milestones_claimed" in data
        
        print(f"✓ Streak data for celebration: streak={data['current_streak']}, claimed={data.get('milestones_claimed', [])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
