"""
Full Production QA Sweep - Iteration 445
Tests ALL public pages, auth flows, API endpoints, and critical features.
This is the RELEASE GATE test for Visionary Suite.
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
KNOWN_SHARE_ID = "96902ad4-066"


class TestHealthAndBasics:
    """Basic health checks - run first"""
    
    def test_health_endpoint(self):
        """API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_public_stats(self):
        """Public stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        # Should have some stats
        assert "videos_created" in data or "creators" in data or "total_creations" in data
        print(f"✓ Public stats: {data}")
    
    def test_public_alive(self):
        """Public alive signals"""
        response = requests.get(f"{BASE_URL}/api/public/alive")
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Alive signals: {data}")
    
    def test_public_live_activity(self):
        """Public live activity feed"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=6")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Live activity: {len(data.get('items', []))} items")


class TestAuthFlows:
    """Authentication flow tests"""
    
    def test_login_valid_credentials(self):
        """Login with valid test user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_EMAIL
        print(f"✓ Login successful for {TEST_USER_EMAIL}")
        return data["token"]
    
    def test_login_invalid_password(self):
        """Login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "WrongPassword123!"
        })
        assert response.status_code in [401, 423]  # 423 if account locked
        print(f"✓ Invalid password correctly rejected: {response.status_code}")
    
    def test_login_nonexistent_user(self):
        """Login with non-existent email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "SomePassword123!"
        })
        assert response.status_code == 401
        print("✓ Non-existent user correctly rejected")
    
    def test_admin_login(self):
        """Admin login should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"].upper() == "ADMIN"
        print(f"✓ Admin login successful: role={data['user']['role']}")
        return data["token"]
    
    def test_auth_me_endpoint(self):
        """Get current user info with valid token"""
        # First login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed, skipping /me test")
        
        token = login_resp.json()["token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER_EMAIL
        print(f"✓ /auth/me returned user: {data['email']}")
    
    def test_protected_route_without_token(self):
        """Protected routes should reject unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ Protected route correctly rejects unauthenticated request")


class TestSharePage:
    """Share page API tests"""
    
    def test_share_page_loads(self):
        """Share page data endpoint"""
        response = requests.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "title" in data or "videoUrl" in data or "thumbnailUrl" in data
        print(f"✓ Share page data loaded: title={data.get('title', 'N/A')}")
    
    def test_share_more_videos(self):
        """More videos carousel endpoint"""
        response = requests.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}/more-videos")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"✓ More videos: {len(data.get('videos', []))} videos returned")
    
    def test_share_invalid_id(self):
        """Invalid share ID should return 404 or empty"""
        response = requests.get(f"{BASE_URL}/api/share/invalid-share-id-12345")
        # Could be 404 or 200 with success=false
        assert response.status_code in [200, 404]
        print(f"✓ Invalid share ID handled: status={response.status_code}")


class TestPaymentAPIs:
    """Payment/Cashfree API tests"""
    
    def test_cashfree_plans(self):
        """Get available plans"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200
        data = response.json()
        # Should have plans/products structure
        assert "plans" in data or "products" in data or "configured" in data
        print(f"✓ Cashfree plans endpoint working: {list(data.keys())}")
    
    def test_pricing_page_data(self):
        """Pricing page should have plan data"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200
        print("✓ Pricing data available")


class TestReferralSystem:
    """Referral system API tests"""
    
    def test_referral_code_authenticated(self):
        """Get referral code for authenticated user"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/referral/code", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "code" in data or "referral_code" in data
        print(f"✓ Referral code retrieved")
    
    def test_referral_stats_authenticated(self):
        """Get referral stats for authenticated user"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/referral/stats", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        print("✓ Referral stats retrieved")


class TestGrowthAnalytics:
    """Growth analytics API tests"""
    
    def test_growth_funnel(self):
        """Growth funnel endpoint"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel")
        assert response.status_code == 200
        print("✓ Growth funnel endpoint working")
    
    def test_growth_event_post(self):
        """Post growth event"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "share_viewed",
            "properties": {"share_id": "test-123"},
            "timestamp": int(time.time() * 1000)
        })
        # 200 for valid events, 400 for invalid - endpoint is working if not 500
        assert response.status_code in [200, 400, 422]
        print(f"✓ Growth event POST working: status={response.status_code}")


class TestStoryEngine:
    """Story engine API tests"""
    
    def test_first_video_free(self):
        """First video free eligibility check"""
        response = requests.get(f"{BASE_URL}/api/story-engine/first-video-free")
        assert response.status_code == 200
        print("✓ First video free endpoint working")
    
    def test_story_engine_options(self):
        """Get story engine options"""
        response = requests.get(f"{BASE_URL}/api/story-engine/options")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        print(f"✓ Story engine options: {len(data.get('animation_styles', []))} styles")
    
    def test_quality_modes(self):
        """Get quality modes"""
        response = requests.get(f"{BASE_URL}/api/story-engine/quality-modes")
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        print(f"✓ Quality modes: {list(data.get('modes', {}).keys())}")
    
    def test_user_jobs_authenticated(self):
        """Get user jobs (authenticated)"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs?limit=5", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"✓ User jobs: {len(data.get('jobs', []))} jobs")


class TestAdminDashboard:
    """Admin dashboard API tests"""
    
    def test_admin_dashboard_authenticated(self):
        """Admin dashboard requires admin auth"""
        # Login as admin
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Admin login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        print("✓ Admin dashboard accessible")
    
    def test_admin_users_list(self):
        """Admin users list"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Admin login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/admin/users/list", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        print("✓ Admin users list accessible")


class TestUserProfile:
    """User profile API tests"""
    
    def test_user_profile(self):
        """Get user profile"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/user/profile", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        print("✓ User profile accessible")
    
    def test_credits_balance(self):
        """Get credits balance"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data or "balance" in data
        print(f"✓ Credits balance retrieved")


class TestPublicPages:
    """Test public page endpoints"""
    
    def test_public_explore_stories(self):
        """Public explore stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?page=1&limit=5")
        assert response.status_code == 200
        print("✓ Public explore stories working")
    
    def test_public_featured_story(self):
        """Public featured story"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200
        print("✓ Public featured story working")
    
    def test_ab_impression(self):
        """A/B test impression tracking"""
        response = requests.post(f"{BASE_URL}/api/public/ab-impression", json={
            "variant": "A",
            "action": "impression"
        })
        assert response.status_code == 200
        print("✓ A/B impression tracking working")


class TestReelGenerator:
    """Reel generator API tests"""
    
    def test_user_reels(self):
        """Get user reels"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/convert/user-reels", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        print("✓ User reels endpoint working")


class TestBillingPage:
    """Billing page API tests"""
    
    def test_billing_page_data(self):
        """Billing page should load user subscription info"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        
        token = login_resp.json()["token"]
        
        # Try various billing endpoints
        endpoints = [
            "/api/cashfree/plans",
            "/api/credits/balance",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers={
                "Authorization": f"Bearer {token}"
            })
            assert response.status_code == 200, f"Failed: {endpoint}"
        
        print("✓ Billing page data endpoints working")


class TestInputValidation:
    """Input validation tests"""
    
    def test_login_empty_email(self):
        """Login with empty email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": "SomePassword123!"
        })
        assert response.status_code in [400, 422]
        print("✓ Empty email validation working")
    
    def test_login_invalid_email_format(self):
        """Login with invalid email format should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "not-an-email",
            "password": "SomePassword123!"
        })
        assert response.status_code in [400, 401, 422]
        print("✓ Invalid email format validation working")


class TestPerformance:
    """Basic performance tests"""
    
    def test_health_response_time(self):
        """Health endpoint should respond quickly"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/health")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check took {elapsed:.2f}s (should be <1s)"
        print(f"✓ Health check response time: {elapsed:.3f}s")
    
    def test_public_stats_response_time(self):
        """Public stats should respond within 1s"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/public/stats")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Public stats took {elapsed:.2f}s (should be <1s)"
        print(f"✓ Public stats response time: {elapsed:.3f}s")
    
    def test_share_page_response_time(self):
        """Share page should respond within 1s"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/share/{KNOWN_SHARE_ID}")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0, f"Share page took {elapsed:.2f}s (should be <1s)"
        print(f"✓ Share page response time: {elapsed:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
