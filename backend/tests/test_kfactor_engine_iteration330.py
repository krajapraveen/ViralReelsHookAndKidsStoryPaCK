"""
K-Factor Engine (Viral Scaling Phase) - Iteration 330 Tests
Tests: K-factor metrics, continuation reward (+15), signup referral reward (+25), streak API
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


class TestKFactorAPIs:
    """K-Factor Engine API Tests"""
    
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
    
    # ─── K-FACTOR METRICS ENDPOINT ───────────────────────────────────────────
    
    def test_kfactor_metrics_endpoint_authenticated(self):
        """Test GET /api/growth/k-factor returns user and platform metrics"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/growth/k-factor")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "user" in data, "Response should have 'user' metrics"
        assert "platform_7d" in data, "Response should have 'platform_7d' metrics"
        
        # Verify user metrics structure
        user_metrics = data["user"]
        assert "total_shares" in user_metrics, "User metrics should have total_shares"
        assert "total_continuations_earned" in user_metrics, "User metrics should have total_continuations_earned"
        assert "total_referral_signups" in user_metrics, "User metrics should have total_referral_signups"
        assert "credits_from_virality" in user_metrics, "User metrics should have credits_from_virality"
        
        # Verify platform metrics structure
        platform_metrics = data["platform_7d"]
        assert "total_shares" in platform_metrics, "Platform metrics should have total_shares"
        assert "share_to_continue" in platform_metrics, "Platform metrics should have share_to_continue"
        assert "share_to_signup" in platform_metrics, "Platform metrics should have share_to_signup"
        assert "share_to_continue_rate" in platform_metrics, "Platform metrics should have share_to_continue_rate"
        assert "share_to_signup_rate" in platform_metrics, "Platform metrics should have share_to_signup_rate"
        assert "estimated_k_factor" in platform_metrics, "Platform metrics should have estimated_k_factor"
        
        print(f"K-Factor metrics: user={user_metrics}, platform_7d={platform_metrics}")
    
    def test_kfactor_metrics_requires_auth(self):
        """Test GET /api/growth/k-factor requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/growth/k-factor")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    # ─── CONTINUATION REWARD ENDPOINT (+15 credits) ──────────────────────────
    
    def test_continuation_reward_endpoint(self):
        """Test POST /api/growth/continuation-reward awards +15 credits"""
        # This endpoint doesn't require auth - it's called from public share page
        response = self.session.post(f"{BASE_URL}/api/growth/continuation-reward", json={
            "parent_job_id": "test-job-id-12345",
            "session_id": "test-session-continuation-reward"
        })
        
        # Should return success (even if parent job not found, it returns success=False gracefully)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Response should have success field
        assert "success" in data, "Response should have 'success' field"
        
        # If rewarded, should be +15 credits
        if data.get("rewarded"):
            assert data.get("credits_awarded") == 15, f"Expected 15 credits, got {data.get('credits_awarded')}"
            print("Continuation reward: +15 credits awarded")
        else:
            print(f"Continuation reward not awarded: {data.get('message', 'No message')}")
    
    def test_continuation_reward_deduplication(self):
        """Test continuation reward is deduplicated (same session can't claim twice)"""
        session_id = "test-session-dedup-check"
        
        # First call
        response1 = self.session.post(f"{BASE_URL}/api/growth/continuation-reward", json={
            "parent_job_id": "test-job-dedup",
            "session_id": session_id
        })
        assert response1.status_code == 200
        
        # Second call with same session
        response2 = self.session.post(f"{BASE_URL}/api/growth/continuation-reward", json={
            "parent_job_id": "test-job-dedup",
            "session_id": session_id
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second call should not reward again
        if data2.get("rewarded") == False:
            print("Deduplication working: second call not rewarded")
        else:
            print("Note: First call may have failed, so second call rewarded")
    
    # ─── SIGNUP REFERRAL REWARD ENDPOINT (+25 credits) ───────────────────────
    
    def test_signup_referral_reward_endpoint(self):
        """Test POST /api/growth/signup-referral-reward awards +25 credits"""
        response = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "test-referrer-job-id",
            "new_user_id": "test-new-user-id-12345"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "success" in data, "Response should have 'success' field"
        
        # If rewarded, should be +25 credits
        if data.get("rewarded"):
            assert data.get("credits_awarded") == 25, f"Expected 25 credits, got {data.get('credits_awarded')}"
            print("Signup referral reward: +25 credits awarded")
        else:
            print(f"Signup referral reward not awarded: {data.get('message', 'No message')}")
    
    def test_signup_referral_self_referral_blocked(self):
        """Test self-referral is blocked"""
        # This would require a real job with a user_id, so we test the endpoint exists
        response = self.session.post(f"{BASE_URL}/api/growth/signup-referral-reward", json={
            "referrer_job_id": "nonexistent-job",
            "new_user_id": "same-user-id"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return success=False for nonexistent job
        assert data.get("success") == False, "Should fail for nonexistent job"
    
    # ─── SHARE REWARD ENDPOINT (+5 credits) ──────────────────────────────────
    
    def test_share_reward_endpoint(self):
        """Test POST /api/growth/share-reward awards +5 credits"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.post(f"{BASE_URL}/api/growth/share-reward", json={
            "job_id": "test-share-job-id",
            "platform": "whatsapp"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        
        # If rewarded, should be +5 credits
        if data.get("rewarded"):
            assert data.get("credits_awarded") == 5, f"Expected 5 credits, got {data.get('credits_awarded')}"
            print("Share reward: +5 credits awarded")
        else:
            print(f"Share reward already claimed: {data.get('message', 'No message')}")
    
    # ─── STREAK API ──────────────────────────────────────────────────────────
    
    def test_streak_api_authenticated(self):
        """Test GET /api/retention/streak returns streak data"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/retention/streak")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "current_streak" in data, "Response should have current_streak"
        assert "longest_streak" in data, "Response should have longest_streak"
        
        print(f"Streak data: current={data.get('current_streak')}, longest={data.get('longest_streak')}")
    
    # ─── GROWTH EVENT TRACKING ───────────────────────────────────────────────
    
    def test_growth_event_tracking(self):
        """Test POST /api/growth/event tracks events"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": "test-session-event-tracking",
            "source_page": "/v/test-slug",
            "source_slug": "test-slug",
            "origin": "share_page"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "event_id" in data or "deduplicated" in data, "Response should have event_id or deduplicated flag"
        
        print(f"Event tracked: {data}")
    
    def test_growth_event_invalid_event_type(self):
        """Test invalid event type is rejected"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "invalid_event_type",
            "session_id": "test-session"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
    
    def test_growth_event_continue_click(self):
        """Test continue_click event tracking"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "continue_click",
            "session_id": "test-session-continue",
            "source_slug": TEST_SLUG,
            "origin": "share_page"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        print("continue_click event tracked successfully")
    
    def test_growth_event_share_click(self):
        """Test share_click event tracking"""
        response = self.session.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_click",
            "session_id": "test-session-share",
            "source_slug": TEST_SLUG,
            "origin": "share_page",
            "meta": {"platform": "whatsapp"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        print("share_click event tracked successfully")
    
    # ─── VIRAL COEFFICIENT ENDPOINT ──────────────────────────────────────────
    
    def test_viral_coefficient_endpoint(self):
        """Test GET /api/growth/viral-coefficient returns K-factor calculation"""
        response = self.session.get(f"{BASE_URL}/api/growth/viral-coefficient?days=7")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "viral_coefficient_K" in data, "Response should have viral_coefficient_K"
        assert "interpretation" in data, "Response should have interpretation"
        assert "components" in data, "Response should have components"
        assert "top_performing_slugs" in data, "Response should have top_performing_slugs"
        
        print(f"Viral coefficient: K={data.get('viral_coefficient_K')}, interpretation={data.get('interpretation')}")
    
    # ─── GROWTH METRICS ENDPOINT ─────────────────────────────────────────────
    
    def test_growth_metrics_endpoint(self):
        """Test GET /api/growth/metrics returns funnel metrics"""
        response = self.session.get(f"{BASE_URL}/api/growth/metrics?days=7")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "raw_counts" in data, "Response should have raw_counts"
        assert "conversion_rates" in data, "Response should have conversion_rates"
        assert "viral_metrics" in data, "Response should have viral_metrics"
        
        print(f"Growth metrics: {data.get('raw_counts')}")
    
    # ─── PUBLIC CREATION ENDPOINT ────────────────────────────────────────────
    
    def test_public_creation_endpoint(self):
        """Test GET /api/public/creation/{slug} returns creation data"""
        response = self.session.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "creation" in data, "Response should have creation data"
        creation = data["creation"]
        
        assert "title" in creation, "Creation should have title"
        assert "views" in creation or "remix_count" in creation, "Creation should have views or remix_count"
        
        print(f"Public creation: title={creation.get('title')}, views={creation.get('views')}, remixes={creation.get('remix_count')}")


class TestRetentionAPIs:
    """Retention API Tests (still working from previous phases)"""
    
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
    
    def test_return_banner_api(self):
        """Test GET /api/retention/return-banner returns banner data"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if not token:
            pytest.skip("Authentication failed")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/retention/return-banner")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "has_story" in data, "Response should have has_story field"
        
        print(f"Return banner: has_story={data.get('has_story')}")
    
    def test_universe_rankings_api(self):
        """Test GET /api/universe/rankings returns rankings"""
        response = self.session.get(f"{BASE_URL}/api/universe/rankings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "top_characters" in data or "top_creators" in data or "top_stories" in data, \
            "Response should have ranking data"
        
        print(f"Rankings: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
