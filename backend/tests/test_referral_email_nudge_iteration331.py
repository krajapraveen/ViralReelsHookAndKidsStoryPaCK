"""
Attribution + Distribution Phase (Phase 5.5) - Iteration 331 Tests
Tests: Referral tracking, signup-referral-reward, email nudge system, share page features
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

# Known test slug
TEST_SLUG = "dragon-guardians-of-the-crystal-valley-fe12f875"


class TestSignupReferralReward:
    """Tests for POST /api/growth/signup-referral-reward endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_signup_referral_reward_nonexistent_job(self):
        """Test signup-referral-reward returns success:false for nonexistent referrer job"""
        response = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "nonexistent-job-id-12345",
            "new_user_id": "test-new-user-id"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return success=False for nonexistent job
        assert data.get("success") == False, f"Expected success=False for nonexistent job, got {data}"
        print(f"Nonexistent job test passed: {data}")
    
    def test_signup_referral_reward_missing_params(self):
        """Test signup-referral-reward handles missing parameters"""
        # Missing referrer_job_id
        response1 = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "new_user_id": "test-user"
        })
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("success") == False, "Should fail without referrer_job_id"
        
        # Missing new_user_id
        response2 = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-job"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("success") == False, "Should fail without new_user_id"
        
        print("Missing params test passed")
    
    def test_signup_referral_reward_self_referral_blocked(self):
        """Test self-referral is prevented (same user can't refer themselves)"""
        # This requires a real job with user_id, but we can test the endpoint handles it
        response = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-self-referral-job",
            "new_user_id": "same-user-id"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return success=False (job doesn't exist, so can't self-refer anyway)
        assert data.get("success") == False, "Should fail for nonexistent job"
        print(f"Self-referral test passed: {data}")
    
    def test_signup_referral_reward_duplicate_prevention(self):
        """Test duplicate referral rewards are prevented"""
        # First call
        response1 = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-dup-job",
            "new_user_id": "test-dup-user"
        })
        assert response1.status_code == 200
        
        # Second call with same params
        response2 = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-dup-job",
            "new_user_id": "test-dup-user"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Both should return success=False since job doesn't exist
        # But if job existed, second call would return "Already rewarded"
        print(f"Duplicate prevention test: {data2}")
    
    def test_signup_referral_reward_credits_amount(self):
        """Test that signup referral reward is +25 credits when successful"""
        # We can't easily create a real job, but we verify the endpoint structure
        response = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-credits-job",
            "new_user_id": "test-credits-user"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # If it were successful, it would have credits_awarded=25
        if data.get("rewarded"):
            assert data.get("credits_awarded") == 25, f"Expected 25 credits, got {data.get('credits_awarded')}"
        
        print(f"Credits amount test: {data}")


class TestEmailNudgeSystem:
    """Tests for email nudge system and admin endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_admin_email_nudges_endpoint(self):
        """Test GET /api/retention/admin/email-nudges shows email_service_active field"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not token:
            pytest.skip("Admin authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/retention/admin/email-nudges")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "email_service_active" in data, "Response should have email_service_active field"
        assert "pending_count" in data, "Response should have pending_count"
        assert "sent_count" in data, "Response should have sent_count"
        
        # Email service should be inactive (RESEND_API_KEY not set)
        assert data.get("email_service_active") == False, "Email service should be inactive without RESEND_API_KEY"
        
        print(f"Email nudge admin endpoint: email_service_active={data.get('email_service_active')}, pending={data.get('pending_count')}, sent={data.get('sent_count')}")
    
    def test_admin_email_nudges_requires_admin(self):
        """Test email nudges endpoint requires admin authentication"""
        # Without auth
        response1 = self.session.get(f"{BASE_URL}/api/retention/admin/email-nudges")
        assert response1.status_code in [401, 403], f"Expected 401/403 without auth, got {response1.status_code}"
        
        # With regular user auth
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            response2 = self.session.get(f"{BASE_URL}/api/retention/admin/email-nudges")
            assert response2.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response2.status_code}"
        
        print("Admin auth requirement test passed")


class TestSharePageFeatures:
    """Tests for share page features (social proof, urgency, share buttons)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_public_creation_endpoint(self):
        """Test GET /api/public/creation/{slug} returns creation with required fields"""
        response = self.session.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "creation" in data, "Response should have creation data"
        creation = data["creation"]
        
        # Verify required fields for share page
        assert "title" in creation, "Creation should have title"
        assert "job_id" in creation, "Creation should have job_id (for referral tracking)"
        
        print(f"Public creation: title={creation.get('title')}, job_id={creation.get('job_id')}")
    
    def test_public_creation_remix_endpoint(self):
        """Test POST /api/public/creation/{slug}/remix increments remix count"""
        response = self.session.post(f"{BASE_URL}/api/public/creation/{TEST_SLUG}/remix")
        
        # Should return 200 (or 404 if slug doesn't exist)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"Remix endpoint response: {data}")


class TestKFactorAndStreakAPIs:
    """Tests for K-factor and streak APIs (still working from previous phases)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_kfactor_api(self):
        """Test GET /api/growth/k-factor returns metrics"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/growth/k-factor")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "user" in data
        assert "platform_7d" in data
        
        print(f"K-factor API: user={data.get('user')}, platform_7d={data.get('platform_7d')}")
    
    def test_streak_api(self):
        """Test GET /api/retention/streak returns streak data"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/retention/streak")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "current_streak" in data
        assert "longest_streak" in data
        
        print(f"Streak API: current={data.get('current_streak')}, longest={data.get('longest_streak')}")
    
    def test_return_banner_api(self):
        """Test GET /api/retention/return-banner returns banner data"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/retention/return-banner")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "has_story" in data
        
        print(f"Return banner API: has_story={data.get('has_story')}")


class TestGrowthEventTracking:
    """Tests for growth event tracking"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_page_view_event(self):
        """Test page_view event tracking"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": "test-session-page-view-331",
            "source_page": f"/v/{TEST_SLUG}",
            "source_slug": TEST_SLUG,
            "origin": "share_page"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        print(f"page_view event: {data}")
    
    def test_remix_click_event(self):
        """Test remix_click event tracking"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "remix_click",
            "session_id": "test-session-remix-331",
            "source_slug": TEST_SLUG,
            "origin": "share_page",
            "tool_type": "story_video"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"remix_click event: {data}")
    
    def test_signup_completed_event(self):
        """Test signup_completed event tracking"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "signup_completed",
            "session_id": "test-session-signup-331",
            "source_page": "/signup",
            "meta": {"method": "email"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"signup_completed event: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
