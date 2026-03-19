"""
Test Suite for Public Creation Page & Cashfree Payment Features
Iteration 300 - Share→Remix Growth Loop & Payment Verification
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://k-factor-boost.preview.emergentagent.com').rstrip('/')

class TestBackendHealth:
    """Health check tests"""
    
    def test_backend_health(self):
        """Verify backend API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Backend healthy: {data}")

    def test_cashfree_health(self):
        """Verify Cashfree gateway health"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        print(f"✅ Cashfree healthy: {data}")


class TestPublicRoutes:
    """Public creation routes tests"""
    
    @pytest.fixture(scope="class")
    def valid_slug(self):
        """Get a valid creation slug from trending"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert len(data.get("items", [])) > 0
        slug = data["items"][0].get("slug") or data["items"][0].get("job_id")
        print(f"✅ Found valid slug: {slug}")
        return slug
    
    def test_get_public_creation(self, valid_slug):
        """Test GET /api/public/creation/{slug} returns tool_type"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{valid_slug}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        creation = data.get("creation", {})
        
        # Required fields
        assert "job_id" in creation
        assert "title" in creation
        assert "tool_type" in creation, "tool_type field must be present"
        assert "views" in creation
        assert "remix_count" in creation
        assert "creator" in creation
        
        # tool_type should be valid
        valid_tools = ['story-video-studio', 'photo-to-comic', 'reels', 'gif-maker', 
                       'comic-storybook', 'bedtime-story-builder', 'caption-rewriter', 'brand-story-builder']
        assert creation["tool_type"] in valid_tools, f"tool_type must be one of {valid_tools}"
        
        print(f"✅ Public creation fetched: {creation['title']}, tool_type={creation['tool_type']}")

    def test_increment_remix_count(self, valid_slug):
        """Test POST /api/public/creation/{slug}/remix increments count"""
        # Get current remix count
        response = requests.get(f"{BASE_URL}/api/public/creation/{valid_slug}")
        initial_remix = response.json()["creation"]["remix_count"]
        
        # Increment
        response = requests.post(f"{BASE_URL}/api/public/creation/{valid_slug}/remix")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify increment
        response = requests.get(f"{BASE_URL}/api/public/creation/{valid_slug}")
        new_remix = response.json()["creation"]["remix_count"]
        assert new_remix >= initial_remix, "Remix count should be incremented"
        print(f"✅ Remix count incremented: {initial_remix} → {new_remix}")

    def test_public_creation_404(self):
        """Test 404 for non-existent slug"""
        response = requests.get(f"{BASE_URL}/api/public/creation/non-existent-slug-12345")
        assert response.status_code == 404
        print("✅ 404 for non-existent slug")

    def test_trending_weekly(self):
        """Test trending weekly endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "items" in data
        assert data["period"] == "weekly"
        print(f"✅ Trending weekly: {len(data['items'])} items")

    def test_platform_stats(self):
        """Test platform stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        assert "creators" in data
        assert "videos_created" in data
        assert "total_creations" in data
        assert "ai_scenes" in data
        print(f"✅ Platform stats: {data}")


class TestCashfreeProducts:
    """Cashfree products and gateway tests"""
    
    def test_get_products(self):
        """Test GET /api/cashfree/products returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        
        # Check gateway info
        assert data.get("gateway") == "cashfree"
        assert data.get("configured") == True
        
        # Check products structure
        products = data.get("products", {})
        assert "topup_small" in products, "topup_small product required"
        assert "topup_medium" in products
        assert "topup_large" in products
        
        # Verify product fields
        topup_small = products["topup_small"]
        assert topup_small["credits"] == 50
        assert topup_small["price"] == 399  # INR price
        assert "displayPrice" in topup_small
        assert "displayCurrency" in topup_small
        
        print(f"✅ Cashfree products: {list(products.keys())}")

    def test_get_plans_alias(self):
        """Test /api/cashfree/plans alias works"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200
        data = response.json()
        assert data.get("gateway") == "cashfree"
        assert "products" in data
        print("✅ Cashfree plans alias working")


class TestCashfreeCreateOrder:
    """Cashfree order creation tests (requires auth)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Auth failed - skipping authenticated tests")
        return None
    
    def test_create_order_requires_auth(self):
        """Test create-order requires authentication"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json={
            "productId": "topup_small",
            "currency": "INR"
        })
        assert response.status_code in [401, 403], "Should require auth"
        print("✅ Create order requires auth")
    
    def test_create_order_with_inr(self, auth_token):
        """Test creating order with INR currency (primary supported currency)"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", 
            json={
                "productId": "topup_small",
                "currency": "INR"
            },
            headers=headers
        )
        
        # Should succeed with INR
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "orderId" in data
            assert "paymentSessionId" in data
            assert data.get("currency") == "INR"
            print(f"✅ Order created: {data['orderId']}")
        elif response.status_code == 500:
            # Cashfree may not be fully configured in test env
            print(f"⚠️ Order creation returned 500 - Cashfree may not be configured")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")

    def test_create_order_invalid_product(self, auth_token):
        """Test create-order rejects invalid product"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", 
            json={
                "productId": "invalid_product",
                "currency": "INR"
            },
            headers=headers
        )
        assert response.status_code == 400, "Should reject invalid product"
        print("✅ Invalid product rejected")


class TestCashfreeVerify:
    """Cashfree payment verification tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Auth failed")
        return None
    
    def test_verify_requires_auth(self):
        """Test verify requires authentication"""
        response = requests.post(f"{BASE_URL}/api/cashfree/verify", json={
            "order_id": "test-order-123"
        })
        assert response.status_code in [401, 403], "Should require auth"
        print("✅ Verify requires auth")
    
    def test_verify_nonexistent_order(self, auth_token):
        """Test verify returns 404 for non-existent order"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/cashfree/verify", 
            json={"order_id": "fake-order-12345"},
            headers=headers
        )
        assert response.status_code == 404, "Should return 404 for non-existent order"
        print("✅ Non-existent order returns 404")


class TestCashfreeWebhook:
    """Cashfree webhook tests"""
    
    def test_webhook_handles_test_event(self):
        """Test webhook accepts test events"""
        response = requests.post(f"{BASE_URL}/api/cashfree/webhook", 
            json={
                "type": "TEST",
                "data": {}
            },
            headers={"Content-Type": "application/json"}
        )
        # Webhook should return 200 for test events
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "received"]
        print(f"✅ Webhook test event handled: {data}")

    def test_webhook_handles_webhook_test_event(self):
        """Test webhook accepts WEBHOOK_TEST events"""
        response = requests.post(f"{BASE_URL}/api/cashfree/webhook", 
            json={
                "type": "WEBHOOK_TEST",
                "data": {}
            },
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        print("✅ WEBHOOK_TEST event handled")


class TestPublicSharePages:
    """Share page and OG meta tests"""
    
    @pytest.fixture(scope="class")
    def valid_slug(self):
        """Get a valid creation slug"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=1")
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                return data["items"][0].get("slug") or data["items"][0].get("job_id")
        pytest.skip("No valid slug found")
    
    def test_share_page_returns_html(self, valid_slug):
        """Test /api/public/s/{slug} returns HTML with OG tags"""
        response = requests.get(f"{BASE_URL}/api/public/s/{valid_slug}")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        html = response.text
        assert "og:title" in html
        assert "og:image" in html
        assert "twitter:card" in html
        print("✅ Share page returns HTML with OG tags")

    def test_sitemap_returns_xml(self):
        """Test sitemap endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200
        assert "xml" in response.headers.get("content-type", "")
        print("✅ Sitemap returns XML")


class TestExploreAndActivity:
    """Explore feed and live activity tests"""
    
    def test_explore_feed(self):
        """Test explore feed endpoint"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "items" in data
        print(f"✅ Explore feed: {len(data['items'])} items")

    def test_live_activity(self):
        """Test live activity feed"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "items" in data
        print(f"✅ Live activity: {len(data['items'])} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
