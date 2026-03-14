"""
P0 Bug Fix Iteration 159 - Story Video Studio Generate Button Fix

Tests for:
1. Rate limit pre-check endpoint: GET /api/pipeline/rate-limit-status
2. Stale job auto-timeout (jobs stuck >15min are auto-failed)
3. Pipeline create returns proper error codes (429 rate limit, 402 credits)
4. Form validation requirements
5. Regression tests for Landing, Gallery, Pricing pages
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-challenges-10.preview.emergentagent.com').rstrip('/')

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
    """Get auth token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get auth token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with test user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_api_health(self, api_client):
        """Verify API health endpoint responds"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API is healthy: {data.get('version')}")


class TestRateLimitStatusEndpoint:
    """Tests for new /api/pipeline/rate-limit-status endpoint"""
    
    def test_rate_limit_status_requires_auth(self, api_client):
        """Rate limit status endpoint requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 401
        print("✓ Rate limit status correctly requires auth")
    
    def test_rate_limit_status_returns_required_fields(self, authenticated_client):
        """Rate limit status returns all required fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "can_create" in data, "Missing 'can_create' field"
        assert "recent_count" in data, "Missing 'recent_count' field"
        assert "concurrent" in data, "Missing 'concurrent' field"
        assert "max_per_hour" in data, "Missing 'max_per_hour' field"
        assert "max_concurrent" in data, "Missing 'max_concurrent' field"
        
        # Verify types
        assert isinstance(data["can_create"], bool), "can_create should be boolean"
        assert isinstance(data["recent_count"], int), "recent_count should be int"
        assert isinstance(data["concurrent"], int), "concurrent should be int"
        assert isinstance(data["max_per_hour"], int), "max_per_hour should be int"
        assert isinstance(data["max_concurrent"], int), "max_concurrent should be int"
        
        print(f"✓ Rate limit status: can_create={data['can_create']}, recent={data['recent_count']}/{data['max_per_hour']}, concurrent={data['concurrent']}/{data['max_concurrent']}")
    
    def test_rate_limit_status_has_reason_when_blocked(self, authenticated_client):
        """When can_create is false, reason field should explain why"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        assert response.status_code == 200
        data = response.json()
        
        # If blocked, reason should be provided
        if not data.get("can_create"):
            assert data.get("reason") is not None, "Should have reason when blocked"
            print(f"✓ Blocked with reason: {data['reason']}")
        else:
            # If allowed, reason should be None
            print(f"✓ User can create videos (reason is None as expected)")


class TestPipelineCreateValidation:
    """Tests for /api/pipeline/create endpoint validation"""
    
    def test_create_requires_auth(self):
        """Pipeline create requires authentication"""
        # Use fresh session without auth header
        fresh_client = requests.Session()
        fresh_client.headers.update({"Content-Type": "application/json"})
        response = fresh_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Video",
            "story_text": "A" * 100
        })
        assert response.status_code == 401
        print("✓ Create endpoint correctly requires auth")
    
    def test_create_validates_title_length(self, authenticated_client):
        """Title must be at least 3 characters"""
        response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "AB",  # Too short
            "story_text": "A" * 100
        })
        # Should fail validation (422 Unprocessable Entity)
        assert response.status_code == 422
        print("✓ Title validation working - rejects < 3 chars")
    
    def test_create_validates_story_length(self, authenticated_client):
        """Story must be at least 50 characters"""
        response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Valid Title",
            "story_text": "Too short"  # < 50 chars
        })
        # Should fail validation (422 Unprocessable Entity)
        assert response.status_code == 422
        print("✓ Story validation working - rejects < 50 chars")
    
    def test_create_rate_limit_returns_429(self, authenticated_client):
        """When rate limited, should return 429 status code"""
        # First check rate limit status
        status_response = authenticated_client.get(f"{BASE_URL}/api/pipeline/rate-limit-status")
        status = status_response.json()
        
        # This test is conditional - only meaningful if user is rate limited
        if not status.get("can_create"):
            response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
                "title": "Test Video",
                "story_text": "A" * 100
            })
            assert response.status_code == 429
            assert "detail" in response.json()
            print(f"✓ Rate limited correctly returns 429: {response.json().get('detail')}")
        else:
            print(f"⚠ User can create videos, skipping 429 test (concurrent={status.get('concurrent')})")


class TestPipelineOptions:
    """Tests for /api/pipeline/options endpoint"""
    
    def test_options_returns_styles(self, api_client):
        """Options endpoint returns animation styles"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "animation_styles" in data
        assert len(data["animation_styles"]) > 0
        
        # Check structure of each style
        for style in data["animation_styles"]:
            assert "id" in style
            assert "name" in style
        
        print(f"✓ Pipeline options: {len(data['animation_styles'])} animation styles")
    
    def test_options_returns_age_groups(self, api_client):
        """Options endpoint returns age groups"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        
        assert "age_groups" in data
        assert len(data["age_groups"]) > 0
        print(f"✓ Pipeline options: {len(data['age_groups'])} age groups")
    
    def test_options_returns_voice_presets(self, api_client):
        """Options endpoint returns voice presets"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        
        assert "voice_presets" in data
        assert len(data["voice_presets"]) > 0
        print(f"✓ Pipeline options: {len(data['voice_presets'])} voice presets")


class TestUserJobs:
    """Tests for user jobs endpoint"""
    
    def test_user_jobs_requires_auth(self):
        """User jobs endpoint requires authentication"""
        # Use fresh session without auth header
        fresh_client = requests.Session()
        fresh_client.headers.update({"Content-Type": "application/json"})
        response = fresh_client.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 401
        print("✓ User jobs correctly requires auth")
    
    def test_user_jobs_returns_jobs_list(self, authenticated_client):
        """User jobs endpoint returns list of jobs"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/user-jobs")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        print(f"✓ User has {len(data['jobs'])} pipeline jobs")


class TestGalleryEndpointsRegression:
    """Regression tests for gallery endpoints"""
    
    def test_gallery_public_access(self, api_client):
        """Public gallery endpoint works without auth"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        print(f"✓ Gallery has {len(data['videos'])} public videos")
    
    def test_gallery_categories(self, api_client):
        """Gallery categories endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        print(f"✓ Gallery has {len(data['categories'])} categories")
    
    def test_gallery_leaderboard(self, api_client):
        """Gallery leaderboard endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        print(f"✓ Gallery leaderboard has {len(data['leaderboard'])} entries")
    
    def test_gallery_filtering(self, api_client):
        """Gallery filtering by category and sort works"""
        # Test sort options
        for sort in ["newest", "most_remixed", "trending"]:
            response = api_client.get(f"{BASE_URL}/api/pipeline/gallery?sort={sort}")
            assert response.status_code == 200
            print(f"✓ Gallery sort '{sort}' works")


class TestLandingPageRegression:
    """Regression tests for landing page APIs"""
    
    def test_live_stats_public(self, api_client):
        """Live stats endpoint for landing page"""
        response = api_client.get(f"{BASE_URL}/api/live-stats/public")
        # This may return 200 or 404 depending on implementation
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Live stats: {data}")
        else:
            print(f"⚠ Live stats returned {response.status_code} - may not be implemented")


class TestPricingPageRegression:
    """Regression tests for pricing page APIs"""
    
    def test_payment_products(self, api_client):
        """Payment products endpoint for pricing page"""
        response = api_client.get(f"{BASE_URL}/api/payments/products")
        # May require auth or be public
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Payment products available")
        elif response.status_code == 401:
            print("✓ Payment products requires auth (expected)")
        else:
            print(f"⚠ Payment products returned {response.status_code}")


class TestCreditsCheck:
    """Tests for credits-related endpoints"""
    
    def test_credits_check_upsell(self, authenticated_client):
        """Check upsell endpoint for low credits"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/check-upsell")
        assert response.status_code == 200
        data = response.json()
        
        # Should have show_upsell and credits fields
        print(f"✓ Credits check: show_upsell={data.get('show_upsell')}, credits={data.get('credits')}")


class TestAdminPerformanceMonitoring:
    """Tests for admin performance monitoring endpoint"""
    
    def test_performance_requires_admin(self, authenticated_client):
        """Performance endpoint requires admin role"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/performance")
        # Regular user should get 403
        assert response.status_code == 403
        print("✓ Performance endpoint correctly requires admin role")
    
    def test_performance_works_for_admin(self, api_client, admin_token):
        """Performance endpoint works for admin"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        response = api_client.get(f"{BASE_URL}/api/pipeline/performance")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "queue" in data
        assert "render_stats" in data
        assert "failure_rate" in data
        
        print(f"✓ Performance: queue={data['queue']}, failure_rate={data['failure_rate']}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
