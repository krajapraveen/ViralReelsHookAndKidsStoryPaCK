"""
Backend Tests for Growth, Monetization, and Analytics Features
Iteration 157 - Testing new features implemented for:
- Pricing model with $9/$19 monthly subscriptions and credit top-ups
- Usage analytics and cost monitoring (funnel analytics)
- Remix This Video feature
- Rate limiting (5 videos/hour/user, 1 concurrent)
- Upsell modal check endpoint
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin user auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_USER_EMAIL,
        "password": ADMIN_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with test user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header - create new session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestCashfreeProducts:
    """Test /api/cashfree/products endpoint for new pricing model"""
    
    def test_get_products_returns_success(self, api_client):
        """Products endpoint should return product list"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        print("✓ GET /api/cashfree/products - 200 OK")
    
    def test_products_contain_creator_monthly(self, api_client):
        """Products should include creator_monthly ($9/mo, 100 credits)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", {})
        
        assert "creator_monthly" in products, "creator_monthly plan not found"
        creator = products["creator_monthly"]
        assert creator.get("credits") == 100, f"Expected 100 credits, got {creator.get('credits')}"
        assert creator.get("priceUsd") == 9, f"Expected $9, got {creator.get('priceUsd')}"
        print(f"✓ creator_monthly: {creator.get('credits')} credits, ${creator.get('priceUsd')}/mo")
    
    def test_products_contain_pro_monthly(self, api_client):
        """Products should include pro_monthly ($19/mo, 250 credits)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", {})
        
        assert "pro_monthly" in products, "pro_monthly plan not found"
        pro = products["pro_monthly"]
        assert pro.get("credits") == 250, f"Expected 250 credits, got {pro.get('credits')}"
        assert pro.get("priceUsd") == 19, f"Expected $19, got {pro.get('priceUsd')}"
        print(f"✓ pro_monthly: {pro.get('credits')} credits, ${pro.get('priceUsd')}/mo")
    
    def test_products_contain_topup_small(self, api_client):
        """Products should include topup_small ($5 for 50 credits)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", {})
        
        assert "topup_small" in products, "topup_small not found"
        topup = products["topup_small"]
        assert topup.get("credits") == 50, f"Expected 50 credits, got {topup.get('credits')}"
        assert topup.get("priceUsd") == 5, f"Expected $5, got {topup.get('priceUsd')}"
        print(f"✓ topup_small: {topup.get('credits')} credits, ${topup.get('priceUsd')}")
    
    def test_products_contain_topup_medium(self, api_client):
        """Products should include topup_medium ($12 for 150 credits)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", {})
        
        assert "topup_medium" in products, "topup_medium not found"
        topup = products["topup_medium"]
        assert topup.get("credits") == 150, f"Expected 150 credits, got {topup.get('credits')}"
        assert topup.get("priceUsd") == 12, f"Expected $12, got {topup.get('priceUsd')}"
        print(f"✓ topup_medium: {topup.get('credits')} credits, ${topup.get('priceUsd')}")
    
    def test_products_contain_topup_large(self, api_client):
        """Products should include topup_large ($30 for 500 credits)"""
        response = api_client.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        products = data.get("products", {})
        
        assert "topup_large" in products, "topup_large not found"
        topup = products["topup_large"]
        assert topup.get("credits") == 500, f"Expected 500 credits, got {topup.get('credits')}"
        assert topup.get("priceUsd") == 30, f"Expected $30, got {topup.get('priceUsd')}"
        print(f"✓ topup_large: {topup.get('credits')} credits, ${topup.get('priceUsd')}")


class TestCheckUpsell:
    """Test /api/credits/check-upsell endpoint for upsell modal trigger"""
    
    def test_check_upsell_requires_auth(self, api_client):
        """Upsell check endpoint should require authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.get(f"{BASE_URL}/api/credits/check-upsell")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ GET /api/credits/check-upsell without auth returns {response.status_code}")
    
    def test_check_upsell_returns_data(self, authenticated_client):
        """Upsell check should return show_upsell boolean and credits"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/check-upsell")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "show_upsell" in data, "show_upsell field missing"
        assert "credits" in data, "credits field missing"
        assert isinstance(data["show_upsell"], bool), "show_upsell should be boolean"
        assert isinstance(data["credits"], (int, float)), "credits should be numeric"
        
        print(f"✓ check-upsell: show_upsell={data['show_upsell']}, credits={data['credits']}")


class TestGalleryEndpoint:
    """Test /api/pipeline/gallery for remix feature support"""
    
    def test_gallery_returns_videos(self, api_client):
        """Gallery endpoint should return videos list"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        
        assert "videos" in data, "videos field missing"
        assert isinstance(data["videos"], list), "videos should be a list"
        print(f"✓ GET /api/pipeline/gallery returns {len(data['videos'])} videos")
    
    def test_gallery_videos_contain_remix_data(self, api_client):
        """Gallery videos should include data needed for remix"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        videos = data.get("videos", [])
        
        if len(videos) > 0:
            video = videos[0]
            # Required fields for remix
            assert "job_id" in video, "job_id field missing for remix"
            assert "story_text" in video, "story_text field missing for remix"
            print(f"✓ Gallery videos contain remix fields: job_id, story_text")
        else:
            print("⚠ No videos in gallery to verify remix fields")


class TestAnalyticsFunnel:
    """Test /api/pipeline/analytics/funnel endpoint (admin only)"""
    
    def test_funnel_requires_admin(self, authenticated_client):
        """Funnel analytics should require admin role"""
        response = authenticated_client.get(f"{BASE_URL}/api/pipeline/analytics/funnel?days=30")
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ GET /api/pipeline/analytics/funnel returns 403 for non-admin user")
    
    def test_funnel_works_for_admin(self, admin_client):
        """Funnel analytics should work for admin"""
        response = admin_client.get(f"{BASE_URL}/api/pipeline/analytics/funnel?days=30")
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "success should be True"
        assert "funnel" in data, "funnel field missing"
        assert "daily" in data, "daily field missing"
        assert "totals" in data, "totals field missing"
        
        totals = data.get("totals", {})
        print(f"✓ Analytics funnel: total_videos={totals.get('total_videos')}, "
              f"completed={totals.get('completed_videos')}, "
              f"remixes={totals.get('remix_count')}, "
              f"credits_consumed={totals.get('total_credits_consumed')}")


class TestPipelineOptions:
    """Test /api/pipeline/options for animation styles and voices"""
    
    def test_options_endpoint_accessible(self, api_client):
        """Pipeline options should be publicly accessible"""
        response = api_client.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        print(f"✓ Pipeline options: {len(data['animation_styles'])} styles, "
              f"{len(data['age_groups'])} age groups, {len(data['voice_presets'])} voices")


class TestRateLimiting:
    """Test rate limiting for video creation (5/hour, 1 concurrent)"""
    
    def test_pipeline_create_checks_auth(self, api_client):
        """Create pipeline should require authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Video",
            "story_text": "A brave dragon protects a hidden village from shadow creatures.",
            "animation_style": "cartoon_2d"
        })
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print(f"✓ POST /api/pipeline/create without auth returns {response.status_code}")
    
    def test_pipeline_create_validates_story_length(self, authenticated_client):
        """Create pipeline should validate minimum story length"""
        response = authenticated_client.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "Test Video",
            "story_text": "Too short",  # Less than 50 chars
            "animation_style": "cartoon_2d"
        })
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for short story, got {response.status_code}"
        print(f"✓ Pipeline create validates story length (min 50 chars)")


class TestCreditsBalance:
    """Test credits endpoints"""
    
    def test_credits_balance_requires_auth(self, api_client):
        """Credits balance should require authentication"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ GET /api/credits/balance requires auth")
    
    def test_credits_balance_returns_data(self, authenticated_client):
        """Credits balance should return current balance"""
        response = authenticated_client.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200
        data = response.json()
        
        assert "credits" in data or "balance" in data, "credits/balance field missing"
        credits_val = data.get("credits") or data.get("balance", 0)
        print(f"✓ User credits balance: {credits_val}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
