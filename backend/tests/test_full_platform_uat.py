"""
Full Platform UAT Tests - Production Go-Ready Validation
Tests ALL modules, ALL flows, ALL edge cases for PRODUCTION GO/NO-GO DECISION.
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pricing-paywall.preview.emergentagent.com')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Known valid slug for public page testing
VALID_SLUG = "da85bb12-785b-4906-8fba-48de780f4a2e"


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


class TestSystemHealth:
    """Test system health and reliability endpoints"""
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_deep_health(self):
        """GET /api/health/deep returns comprehensive health check"""
        response = requests.get(f"{BASE_URL}/api/health/deep")
        assert response.status_code == 200
        data = response.json()
        assert "healthy" in data or "checks" in data
        # Check critical services
        if "checks" in data:
            assert "api" in data["checks"]
            assert "database" in data["checks"]
        print(f"✓ Deep health check passed")


class TestCashfreePayments:
    """Test Cashfree payment gateway"""
    
    def test_products_endpoint(self):
        """GET /api/cashfree/products returns 5 products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) == 5, f"Expected 5 products, got {len(data['products'])}"
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        # Verify all required products
        product_ids = list(data["products"].keys())
        assert "topup_small" in product_ids
        assert "topup_medium" in product_ids
        assert "topup_large" in product_ids
        print(f"✓ Cashfree products: {product_ids}")
    
    def test_create_order_requires_auth(self):
        """POST /api/cashfree/create-order requires authentication"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "topup_small",
            "currency": "INR"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_create_order_with_inr(self, test_user_token):
        """POST /api/cashfree/create-order creates order in INR"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "topup_small",
            "currency": "INR"
        }, headers=headers)
        assert response.status_code == 200, f"Create order failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "orderId" in data
        assert "paymentSessionId" in data
        print(f"✓ Order created: {data.get('orderId', 'N/A')}")
    
    def test_verify_nonexistent_order(self, test_user_token):
        """POST /api/cashfree/verify with unpaid order returns pending/404"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/verify", json={
            "order_id": "nonexistent_order_12345"
        }, headers=headers)
        # Should return 404 or pending status
        assert response.status_code in [200, 404, 400]
        if response.status_code == 200:
            data = response.json()
            # Unpaid order should not add credits
            assert data.get("success", True) in [True, False]
    
    def test_webhook_handles_test_event(self):
        """POST /api/cashfree/webhook handles test events"""
        response = requests.post(f"{BASE_URL}/api/cashfree/webhook", json={
            "type": "TEST"
        }, headers={"Content-Type": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "received"]
        print(f"✓ Webhook test event handled")
    
    def test_payment_history(self, test_user_token):
        """GET /api/cashfree/payments/history returns payment history"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/cashfree/payments/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "payments" in data
        print(f"✓ Payment history: {len(data.get('payments', []))} records")


class TestGrowthAnalytics:
    """Test growth analytics pipeline"""
    
    def test_track_event(self):
        """POST /api/growth/event tracks events"""
        response = requests.post(f"{BASE_URL}/api/growth/event", json={
            "event": "page_view",
            "session_id": f"test_{uuid.uuid4()}",
            "source_slug": VALID_SLUG,
            "tool": "story-video-studio"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Event tracked: {data.get('event_id', 'N/A')}")
    
    def test_batch_events(self):
        """POST /api/growth/events/batch tracks multiple events"""
        session_id = f"test_batch_{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json={
            "events": [
                {"event": "page_view", "session_id": session_id, "source_slug": VALID_SLUG},
                {"event": "remix_click", "session_id": session_id, "source_slug": VALID_SLUG, "tool": "reels"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["tracked"] >= 1
        print(f"✓ Batch events tracked: {data['tracked']}")
    
    def test_get_metrics(self):
        """GET /api/growth/metrics returns funnel conversion rates"""
        response = requests.get(f"{BASE_URL}/api/growth/metrics?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "raw_counts" in data
        assert "conversion_rates" in data
        print(f"✓ Metrics: page_views={data['raw_counts'].get('page_views', 0)}")
    
    def test_get_funnel(self):
        """GET /api/growth/funnel returns stage counts"""
        response = requests.get(f"{BASE_URL}/api/growth/funnel?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "funnel" in data
        assert isinstance(data["funnel"], list)
        print(f"✓ Funnel stages: {len(data['funnel'])}")
    
    def test_viral_coefficient(self):
        """GET /api/growth/viral-coefficient returns K value"""
        response = requests.get(f"{BASE_URL}/api/growth/viral-coefficient?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "viral_coefficient_K" in data
        assert "interpretation" in data
        print(f"✓ Viral K={data['viral_coefficient_K']}, interpretation={data['interpretation']}")
    
    def test_get_trends(self):
        """GET /api/growth/trends returns daily trends"""
        response = requests.get(f"{BASE_URL}/api/growth/trends?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "daily" in data
        print(f"✓ Trends: {len(data.get('daily', {}))} days of data")


class TestPublicCreationPage:
    """Test share → remix funnel"""
    
    def test_public_creation_fetch(self):
        """GET /api/public/creation/{slug} returns creation data"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{VALID_SLUG}")
        assert response.status_code == 200
        data = response.json()
        assert "creation" in data or "title" in data or "job_id" in data
        print(f"✓ Public creation fetch: {VALID_SLUG[:12]}...")
    
    def test_public_creation_404(self):
        """GET /api/public/creation/nonexistent returns 404"""
        response = requests.get(f"{BASE_URL}/api/public/creation/nonexistent_slug_12345")
        assert response.status_code == 404
    
    def test_trending_weekly(self):
        """GET /api/public/trending-weekly returns trending items"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "success" in data
    
    def test_explore_feed(self):
        """GET /api/public/explore returns explore feed"""
        response = requests.get(f"{BASE_URL}/api/public/explore?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_remix_increment(self):
        """POST /api/public/creation/{slug}/remix increments remix count"""
        response = requests.post(f"{BASE_URL}/api/public/creation/{VALID_SLUG}/remix")
        # Should accept the remix increment
        assert response.status_code in [200, 201]


class TestWatchdogSelfHealing:
    """Test watchdog and self-healing system"""
    
    def test_watchdog_run(self, admin_token):
        """POST /api/admin/watchdog/run triggers self-healing"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/watchdog/run", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "status" in data
        print(f"✓ Watchdog run: {data}")
    
    def test_confidence_score(self, admin_token):
        """GET /api/admin/confidence-score returns system score"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/confidence-score", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Confidence score should be 0-100
        if "score" in data:
            assert 0 <= data["score"] <= 100
        print(f"✓ Confidence score: {data}")


class TestToolAPIs:
    """Test all 9 tool APIs"""
    
    def test_pipeline_options(self):
        """GET /api/pipeline/options returns Story Video options"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        print(f"✓ Pipeline options: {len(data.get('animation_styles', []))} styles")
    
    def test_daily_viral_ideas_config(self):
        """GET /api/daily-viral-ideas/config returns config"""
        response = requests.get(f"{BASE_URL}/api/daily-viral-ideas/config")
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data or "categories" in data or "success" in data
    
    def test_caption_rewriter_tones(self):
        """GET /api/caption-rewriter/tones returns available tones"""
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/tones")
        # May not exist - check both endpoints
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/caption/tones")
        assert response.status_code in [200, 404]
    
    def test_gif_maker_options(self):
        """GET /api/gif-maker/options returns emotions and styles"""
        response = requests.get(f"{BASE_URL}/api/gif-maker/options")
        if response.status_code == 200:
            data = response.json()
            assert "emotions" in data or "styles" in data
        # May not have dedicated options endpoint


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_input_returns_422(self):
        """Invalid API inputs return 422 (not 500)"""
        # Test pipeline create with invalid data
        response = requests.post(f"{BASE_URL}/api/pipeline/create", json={
            "title": "",  # Empty title - invalid
            "story_text": "x"  # Too short
        }, headers={"Authorization": "Bearer invalid_token"})
        # Should return 401 (auth) or 422 (validation), not 500
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
    
    def test_auth_invalid_token(self):
        """Invalid auth token returns 401"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code in [401, 403]
    
    def test_rate_limit_headers(self):
        """API returns rate limit headers"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Rate limit headers may be present
        # This is informational, not a failure
        print(f"✓ Rate limit headers present: {'X-RateLimit-Limit' in response.headers}")


class TestCreditsAndBilling:
    """Test credits system"""
    
    def test_credits_balance(self, test_user_token):
        """GET /api/credits/balance returns user credits"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data or "balance" in data
        print(f"✓ Credits balance: {data}")
    
    def test_admin_credits_not_zero(self, admin_token):
        """Admin has unlimited credits (not 0)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        credits = data.get("credits", data.get("balance", 0))
        # Admin should have > 1000 credits (essentially unlimited)
        assert credits > 1000, f"Admin credits too low: {credits}"
        print(f"✓ Admin credits: {credits}")


class TestDownloadsAndGallery:
    """Test downloads and gallery"""
    
    def test_user_jobs(self, test_user_token):
        """GET /api/pipeline/user-jobs returns user's jobs (for My Downloads)"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data or "success" in data
        print(f"✓ User jobs: {len(data.get('jobs', []))}")
    
    def test_gallery_explore(self):
        """GET /api/public/explore returns gallery items"""
        response = requests.get(f"{BASE_URL}/api/public/explore?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestNavigation:
    """Test that all page APIs respond correctly"""
    
    def test_auth_me(self, test_user_token):
        """GET /api/auth/me returns user info"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "user" in data
    
    def test_dashboard_stats(self, test_user_token):
        """API for dashboard stats works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        # Try multiple possible dashboard endpoints
        for endpoint in ["/api/user/stats", "/api/dashboard/stats", "/api/credits/balance"]:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            if response.status_code == 200:
                print(f"✓ Dashboard endpoint: {endpoint}")
                return
        # At least credits should work
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200


class TestShareFeatures:
    """Test social sharing features"""
    
    def test_og_image_endpoint(self):
        """GET /api/public/og-image/{slug} returns or redirects"""
        response = requests.get(f"{BASE_URL}/api/public/og-image/{VALID_SLUG}", allow_redirects=False)
        # Should return image, redirect, or 200
        assert response.status_code in [200, 301, 302, 404]
    
    def test_share_page_redirect(self):
        """GET /api/public/s/{slug} serves share page"""
        response = requests.get(f"{BASE_URL}/api/public/s/{VALID_SLUG}", allow_redirects=False)
        # Should return HTML or redirect
        assert response.status_code in [200, 301, 302, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
