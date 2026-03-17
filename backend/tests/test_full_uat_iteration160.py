"""
Full Production UAT - Iteration 160
Comprehensive backend API testing for Visionary Suite

Covers:
- Public endpoints (gallery, pricing, blog, contact)
- Auth endpoints (login, signup)
- Pipeline endpoints (rate-limit, create, status, options)
- Credits endpoints (balance, check-upsell)
- Cashfree payments endpoints (products)
- Admin endpoints (performance, funnel analytics)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://comic-pipeline-v2.preview.emergentagent.com").rstrip("/")

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
    """Login as test user and get token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Login as admin and get token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with test user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    admin_session = requests.Session()
    admin_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return admin_session


# =============================================================================
# PUBLIC ENDPOINTS TESTS
# =============================================================================

class TestPublicGalleryEndpoints:
    """Test public gallery endpoints (no auth required)"""
    
    def test_gallery_returns_videos(self, api_client):
        """GET /api/pipeline/gallery returns video list"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Gallery failed: {response.text}"
        data = response.json()
        assert "videos" in data, "Response should have 'videos' field"
        assert isinstance(data["videos"], list), "Videos should be a list"
        print(f"Gallery returned {len(data['videos'])} videos")
    
    def test_gallery_categories(self, api_client):
        """GET /api/pipeline/gallery/categories returns categories with counts"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Categories failed: {response.text}"
        data = response.json()
        assert "categories" in data, "Response should have 'categories' field"
        assert isinstance(data["categories"], list), "Categories should be a list"
        # Check first category is "All"
        if data["categories"]:
            assert data["categories"][0]["id"] == "all", "First category should be 'all'"
            assert "count" in data["categories"][0], "Categories should have counts"
        print(f"Categories: {[c['name'] for c in data['categories']]}")
    
    def test_gallery_leaderboard(self, api_client):
        """GET /api/pipeline/gallery/leaderboard returns most remixed videos"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200, f"Leaderboard failed: {response.text}"
        data = response.json()
        assert "leaderboard" in data, "Response should have 'leaderboard' field"
        assert isinstance(data["leaderboard"], list), "Leaderboard should be a list"
        print(f"Leaderboard has {len(data['leaderboard'])} entries")
    
    def test_gallery_filtering_by_sort(self, api_client):
        """GET /api/pipeline/gallery supports sorting"""
        for sort_option in ["newest", "most_remixed", "trending"]:
            response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort={sort_option}")
            assert response.status_code == 200, f"Sort={sort_option} failed: {response.text}"
            data = response.json()
            assert "videos" in data, f"Response for sort={sort_option} should have videos"
        print("All sort options working: newest, most_remixed, trending")
    
    def test_gallery_filtering_by_category(self, api_client):
        """GET /api/pipeline/gallery supports category filtering"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?category=cartoon_2d")
        assert response.status_code == 200, f"Category filter failed: {response.text}"
        data = response.json()
        assert "videos" in data, "Response should have videos"
        print(f"Category filter returned {len(data['videos'])} videos")


class TestPipelineOptionsEndpoint:
    """Test pipeline options endpoint"""
    
    def test_get_options(self, api_client):
        """GET /api/pipeline/options returns animation styles, age groups, voices"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200, f"Options failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        assert "animation_styles" in data, "Should have animation_styles"
        assert "age_groups" in data, "Should have age_groups"
        assert "voice_presets" in data, "Should have voice_presets"
        assert "credit_costs" in data, "Should have credit_costs"
        print(f"Animation styles: {len(data['animation_styles'])}, Age groups: {len(data['age_groups'])}, Voices: {len(data['voice_presets'])}")


class TestCashfreeProductsEndpoint:
    """Test Cashfree products endpoint (pricing)"""
    
    def test_get_products(self, api_client):
        """GET /api/cashfree/products returns pricing tiers"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Products failed: {response.text}"
        data = response.json()
        assert "products" in data, "Response should have 'products' field"
        products = data["products"]
        # Verify expected products exist
        expected_products = ["creator_monthly", "pro_monthly", "topup_small", "topup_medium", "topup_large"]
        for prod_id in expected_products:
            assert prod_id in products, f"Product {prod_id} should exist"
        # Verify pricing
        assert products["creator_monthly"]["priceUsd"] == 9, "Creator plan should be $9"
        assert products["pro_monthly"]["priceUsd"] == 19, "Pro plan should be $19"
        print(f"Products verified: {list(products.keys())}")
    
    def test_cashfree_health(self, api_client):
        """GET /api/cashfree/health returns gateway status"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "healthy", "Gateway should be healthy"
        assert data.get("gateway") == "cashfree", "Gateway should be 'cashfree'"
        print(f"Cashfree health: {data}")


# =============================================================================
# AUTH ENDPOINTS TESTS
# =============================================================================

class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_login_success(self, api_client):
        """POST /api/auth/login with valid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, "Should return token"
        print("Test user login successful")
    
    def test_login_invalid_credentials(self, api_client):
        """POST /api/auth/login with invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400, 404], f"Should reject invalid creds: {response.status_code}"
        print(f"Invalid login correctly rejected with status {response.status_code}")
    
    def test_admin_login_success(self, api_client):
        """POST /api/auth/login as admin"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, "Should return token"
        print("Admin login successful")


# =============================================================================
# AUTHENTICATED ENDPOINTS TESTS
# =============================================================================

class TestCreditsEndpoints:
    """Test credits endpoints (requires auth)"""
    
    def test_get_balance(self, authenticated_client):
        """GET /api/credits/balance returns user credit balance"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200, f"Balance failed: {response.text}"
        data = response.json()
        assert "credits" in data or "balance" in data, "Should have credits/balance field"
        credits = data.get("credits", data.get("balance", 0))
        print(f"User credit balance: {credits}")
    
    def test_check_upsell(self, authenticated_client):
        """GET /api/credits/check-upsell returns upsell status"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/check-upsell")
        assert response.status_code == 200, f"Check-upsell failed: {response.text}"
        data = response.json()
        assert "show_upsell" in data, "Should have show_upsell field"
        assert "credits" in data, "Should have credits field"
        print(f"Upsell check: show_upsell={data['show_upsell']}, credits={data['credits']}")


class TestPipelineRateLimitEndpoint:
    """Test pipeline rate limit status endpoint"""
    
    def test_rate_limit_status(self, authenticated_client):
        """GET /api/pipeline/rate-limit-status returns rate limit info"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 200, f"Rate limit status failed: {response.text}"
        data = response.json()
        assert "can_create" in data, "Should have can_create field"
        assert "recent_count" in data, "Should have recent_count field"
        assert "max_per_hour" in data, "Should have max_per_hour field"
        assert "concurrent" in data, "Should have concurrent field"
        print(f"Rate limit: can_create={data['can_create']}, concurrent={data['concurrent']}, recent={data['recent_count']}/{data['max_per_hour']}")


class TestPipelineCreateValidation:
    """Test pipeline create validation (without actually creating)"""
    
    def test_create_rejects_short_title(self, authenticated_client):
        """POST /api/pipeline/create rejects title < 3 chars"""
        response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "AB",  # Too short
            "story_text": "A" * 60,  # Valid length
            "animation_style": "cartoon_2d"
        })
        assert response.status_code == 422, f"Should reject short title: {response.status_code}"
        print("Short title correctly rejected")
    
    def test_create_rejects_short_story(self, authenticated_client):
        """POST /api/pipeline/create rejects story_text < 50 chars"""
        response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Valid Title",
            "story_text": "Short story",  # Too short
            "animation_style": "cartoon_2d"
        })
        assert response.status_code == 422, f"Should reject short story: {response.status_code}"
        print("Short story correctly rejected")


class TestUserJobsEndpoint:
    """Test user jobs endpoint"""
    
    def test_get_user_jobs(self, authenticated_client):
        """GET /api/pipeline/user-jobs returns user's pipeline jobs"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 200, f"User jobs failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        assert "jobs" in data, "Should have jobs field"
        assert isinstance(data["jobs"], list), "Jobs should be a list"
        print(f"User has {len(data['jobs'])} pipeline jobs")


# =============================================================================
# ADMIN ENDPOINTS TESTS
# =============================================================================

class TestAdminPerformanceEndpoint:
    """Test admin performance monitoring endpoint"""
    
    def test_performance_requires_admin(self, authenticated_client):
        """GET /api/pipeline/performance requires admin role"""
        # Use test user (non-admin) - should be rejected
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/performance")
        assert response.status_code in [403, 401], f"Should require admin: {response.status_code}"
        print("Performance endpoint correctly requires admin")
    
    def test_performance_with_admin(self, admin_client):
        """GET /api/pipeline/performance returns stats for admin"""
        response = admin_client.get(f"{BASE_URL}/api/pipeline/performance")
        assert response.status_code == 200, f"Admin performance failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        assert "queue" in data, "Should have queue stats"
        assert "render_stats" in data, "Should have render_stats"
        assert "failure_rate" in data, "Should have failure_rate"
        print(f"Performance: queue={data['queue']}, failure_rate={data['failure_rate']}%")


class TestAdminAnalyticsFunnelEndpoint:
    """Test admin analytics funnel endpoint"""
    
    def test_funnel_requires_admin(self, authenticated_client):
        """GET /api/pipeline/analytics/funnel requires admin role"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/analytics/funnel")
        assert response.status_code in [403, 401], f"Should require admin: {response.status_code}"
        print("Funnel endpoint correctly requires admin")
    
    def test_funnel_with_admin(self, admin_client):
        """GET /api/pipeline/analytics/funnel returns funnel data for admin"""
        response = admin_client.get(f"{BASE_URL}/api/pipeline/analytics/funnel")
        assert response.status_code == 200, f"Admin funnel failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        assert "funnel" in data, "Should have funnel data"
        assert "totals" in data, "Should have totals"
        totals = data.get("totals", {})
        print(f"Funnel totals: videos={totals.get('total_videos')}, completed={totals.get('completed_videos')}, remixes={totals.get('remix_count')}")


# =============================================================================
# HEALTH AND STATUS TESTS
# =============================================================================

class TestHealthEndpoints:
    """Test various health check endpoints"""
    
    def test_api_health(self, api_client):
        """GET /api/health returns API status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") in ["healthy", "ok", True], f"Status should be healthy: {data}"
        print(f"API health: {data}")
    
    def test_root_endpoint(self, api_client):
        """GET /api returns API info"""
        response = api_client.get(f"{BASE_URL}/api")
        assert response.status_code == 200, f"Root endpoint failed: {response.text}"
        print(f"API root: {response.json()}")


# =============================================================================
# PROFILE AND USER ENDPOINTS
# =============================================================================

class TestProfileEndpoints:
    """Test user profile endpoints"""
    
    def test_get_profile(self, authenticated_client):
        """GET /api/users/profile returns user profile"""
        response = authenticated_client.get(f"{BASE_URL}/api/users/profile")
        assert response.status_code == 200, f"Profile failed: {response.text}"
        data = response.json()
        # Profile may be nested or flat
        profile = data.get("user", data)
        assert "email" in profile or "name" in profile, "Profile should have user info"
        print(f"User profile retrieved: {profile.get('email', 'N/A')}")


class TestHistoryEndpoints:
    """Test history endpoints"""
    
    def test_get_credit_history(self, authenticated_client):
        """GET /api/credits/history returns credit transaction history"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/history")
        assert response.status_code == 200, f"Credit history failed: {response.text}"
        data = response.json()
        assert "history" in data, "Should have history field"
        assert isinstance(data["history"], list), "History should be a list"
        print(f"Credit history: {len(data['history'])} transactions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
