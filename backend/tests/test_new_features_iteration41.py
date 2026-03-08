"""
Test Suite for Iteration 41 - New Features Testing
Tests:
1. User Manual API endpoints
2. Admin Monitoring Dashboard APIs
3. Subscription Management APIs
4. User Analytics Dashboard APIs
5. Cashfree Payment Gateway (sandbox)
6. Protected Routes and Admin Routes
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://review-blog-chat.preview.emergentagent.com')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestUserManualAPI:
    """Test User Manual / Help endpoints"""
    
    def test_get_full_manual(self):
        """Test full manual retrieval"""
        response = requests.get(f"{BASE_URL}/api/help/manual")
        assert response.status_code == 200
        data = response.json()
        
        # Verify manual structure
        assert "overview" in data
        assert "features" in data
        assert "account" in data
        assert "troubleshooting" in data
        
        # Verify overview content
        assert "title" in data["overview"]
        assert "quickStart" in data["overview"]
        print(f"SUCCESS: Full manual has {len(data['features'])} feature guides")
    
    def test_get_manual_section(self):
        """Test getting specific manual section"""
        response = requests.get(f"{BASE_URL}/api/help/manual/features")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        print(f"SUCCESS: Features section has {len(data['features'])} items")
    
    def test_get_manual_section_not_found(self):
        """Test 404 for invalid section"""
        response = requests.get(f"{BASE_URL}/api/help/manual/nonexistent")
        assert response.status_code == 404
        print("SUCCESS: Returns 404 for invalid section")
    
    def test_get_feature_guide(self):
        """Test getting specific feature guide"""
        response = requests.get(f"{BASE_URL}/api/help/feature/genstudio")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "description" in data
        print(f"SUCCESS: GenStudio guide: {data.get('title')}")
    
    def test_get_subfeature_guide(self):
        """Test getting subfeature guide"""
        response = requests.get(f"{BASE_URL}/api/help/feature/text_to_image")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "howToUse" in data
        print(f"SUCCESS: Text-to-Image guide has {len(data.get('howToUse', []))} steps")
    
    def test_search_manual(self):
        """Test manual search"""
        response = requests.get(f"{BASE_URL}/api/help/search?q=credits")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "credits"
        print(f"SUCCESS: Search for 'credits' returned {len(data['results'])} results")
    
    def test_quick_start_guide(self):
        """Test quick start endpoint"""
        response = requests.get(f"{BASE_URL}/api/help/quick-start")
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert "popularFeatures" in data
        assert len(data["steps"]) >= 4
        print(f"SUCCESS: Quick start has {len(data['steps'])} steps")


class TestAuthenticationFlow:
    """Test authentication and token management"""
    
    def test_demo_user_login(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print("SUCCESS: Demo user login works")
    
    def test_admin_user_login(self):
        """Test admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        
        # Verify admin role
        token = data["token"]
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        user = me_response.json()
        assert user.get("role") == "ADMIN"
        print("SUCCESS: Admin user login and role verified")
    
    def test_protected_route_without_auth(self):
        """Test protected routes return 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 401
        print("SUCCESS: Protected routes require auth")


class TestSubscriptionManagementAPI:
    """Test Subscription Management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Login as demo user
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_subscription_plans(self):
        """Test getting available subscription plans"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) >= 3  # Weekly, Monthly, Quarterly
        
        # Verify plan structure
        plan = data["plans"][0]
        assert "id" in plan
        assert "name" in plan
        assert "credits" in plan
        assert "price" in plan
        assert "durationDays" in plan
        print(f"SUCCESS: Found {len(data['plans'])} subscription plans")
    
    def test_get_subscription_plans_currency(self):
        """Test plans with different currencies"""
        # INR
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans?currency=INR")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "INR"
        
        # USD
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans?currency=USD")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"
        print("SUCCESS: Plans support INR and USD currencies")
    
    def test_get_current_subscription(self):
        """Test getting current subscription"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/current", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "subscription" in data
        print(f"SUCCESS: Current subscription: {data['subscription'] or 'None'}")
    
    def test_get_subscription_history(self):
        """Test getting subscription history"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/history", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        print(f"SUCCESS: Subscription history has {len(data['subscriptions'])} records")


class TestUserAnalyticsAPI:
    """Test User Analytics Dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_user_stats(self):
        """Test getting user statistics"""
        response = requests.get(f"{BASE_URL}/api/analytics/user-stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats structure
        expected_keys = ["storySeries", "challenges", "toneRewrites", "coloringBooks", 
                         "genstudioJobs", "totalGenerations", "creditsUsedThisMonth", "currentBalance"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
        
        print(f"SUCCESS: User stats - Balance: {data['currentBalance']}, This month credits used: {data['creditsUsedThisMonth']}")
    
    def test_user_stats_requires_auth(self):
        """Test user stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/user-stats")
        assert response.status_code == 401
        print("SUCCESS: User stats endpoint requires auth")


class TestAdminMonitoringAPI:
    """Test Admin Monitoring Dashboard endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        self.admin_token = response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Login as demo user
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        self.demo_token = response.json().get("token")
        self.demo_headers = {"Authorization": f"Bearer {self.demo_token}"}
    
    def test_admin_overview_with_admin_user(self):
        """Test admin overview with admin credentials"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=self.admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "users" in data
        assert "revenue" in data
        assert "jobs" in data
        assert "featureUsage" in data
        
        print(f"SUCCESS: Admin overview - Total users: {data['users']['total']}, Active today: {data['users']['activeToday']}")
    
    def test_admin_overview_denied_for_non_admin(self):
        """Test admin overview denied for non-admin users"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=self.demo_headers)
        assert response.status_code == 403
        print("SUCCESS: Admin overview denied for non-admin user")
    
    def test_admin_threat_stats(self):
        """Test admin threat detection stats"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/threat-stats", headers=self.admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "currentStatus" in data
        assert "rateWindows" in data
        print(f"SUCCESS: Threat stats - Blocked IPs: {data['currentStatus'].get('blocked_ips_count', 0)}")
    
    def test_admin_app_usage(self):
        """Test admin app usage statistics"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/app-usage?days=30", headers=self.admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "dailyStats" in data
        assert "featureTotals" in data
        assert "period" in data
        print(f"SUCCESS: App usage - Period: {data['period']}, Days: {len(data['dailyStats'])}")
    
    def test_admin_performance_metrics(self):
        """Test admin performance metrics"""
        response = requests.get(f"{BASE_URL}/api/analytics/admin/performance", headers=self.admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "dbCollections" in data
        print(f"SUCCESS: Performance - DB collections: {data['dbCollections']}")


class TestCashfreePaymentAPI:
    """Test Cashfree Payment Gateway endpoints"""
    
    def get_auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.get_auth_token()}"}
    
    def test_cashfree_health(self):
        """Test Cashfree gateway health"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        print(f"SUCCESS: Cashfree health - Environment: {data.get('environment')}")
    
    def test_get_cashfree_products(self):
        """Test getting Cashfree products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        
        assert "products" in data
        assert data["gateway"] == "cashfree"
        
        # Verify products
        products = data["products"]
        assert "starter" in products
        assert "creator" in products
        assert "pro" in products
        print(f"SUCCESS: Found {len(products)} Cashfree products")
    
    def test_get_cashfree_plans_alias(self):
        """Test /plans alias endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print("SUCCESS: /plans alias works")
    
    def test_create_cashfree_order_sandbox(self):
        """Test creating Cashfree order in sandbox mode"""
        order_data = {
            "productId": "starter",
            "currency": "INR"
        }
        headers = self.get_headers()
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", 
                                 json=order_data, 
                                 headers=headers)
        
        # Should succeed in sandbox
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "orderId" in data
        assert "paymentSessionId" in data
        assert data["environment"] == "sandbox"
        print(f"SUCCESS: Sandbox order created - Order ID: {data['orderId']}")
    
    def test_create_order_requires_auth(self):
        """Test order creation requires auth"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", 
                                 json={"productId": "starter"})
        assert response.status_code == 401
        print("SUCCESS: Order creation requires auth")


class TestDashboardRoutes:
    """Test Dashboard links and navigation"""
    
    def test_credits_balance_with_fresh_token(self):
        """Test credit balance endpoint"""
        # Login and get token directly
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        print(f"SUCCESS: Credit balance: {data['credits']}")
        
        # Also test recent generations with same token
        response2 = requests.get(f"{BASE_URL}/api/generate/", headers=headers)
        assert response2.status_code == 200
        data2 = response2.json()
        assert "generations" in data2
        print(f"SUCCESS: Recent generations: {len(data2['generations'])}")


class TestGenStudioTextToImage:
    """Test GenStudio endpoints"""
    
    def get_auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.get_auth_token()}"}
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard listing"""
        headers = self.get_headers()
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "recentJobs" in data
        print(f"SUCCESS: GenStudio dashboard - Credits: {data['credits']}, Jobs: {len(data['recentJobs'])}")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates"""
        headers = self.get_headers()
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"SUCCESS: GenStudio templates: {len(data['templates'])}")


class TestStorySeries:
    """Test Story Series API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_story_series_pricing(self):
        """Test story series pricing"""
        response = requests.get(f"{BASE_URL}/api/story-series/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"SUCCESS: Story series pricing: {data['pricing']}")
    
    def test_story_series_themes(self):
        """Test story series themes"""
        response = requests.get(f"{BASE_URL}/api/story-series/themes")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        assert len(data["themes"]) >= 5
        print(f"SUCCESS: Story series themes: {len(data['themes'])}")


class TestChallengeGenerator:
    """Test Challenge Generator API endpoints"""
    
    def test_challenge_pricing(self):
        """Test challenge generator pricing"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"SUCCESS: Challenge pricing: {data['pricing']}")
    
    def test_challenge_niches(self):
        """Test challenge niches"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/niches")
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        print(f"SUCCESS: Challenge niches: {len(data['niches'])}")


class TestToneSwitcher:
    """Test Tone Switcher API endpoints"""
    
    def test_tone_switcher_pricing(self):
        """Test tone switcher pricing"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"SUCCESS: Tone switcher pricing: {data['pricing']}")
    
    def test_tone_switcher_tones(self):
        """Test available tones"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/tones")
        assert response.status_code == 200
        data = response.json()
        assert "tones" in data
        assert len(data["tones"]) >= 5
        print(f"SUCCESS: Available tones: {len(data['tones'])}")
    
    def test_tone_switcher_preview_with_fresh_token(self):
        """Test free preview feature (requires auth)"""
        # Login and get fresh token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(f"{BASE_URL}/api/tone-switcher/preview", 
                                 json={"text": "Hello world", "targetTone": "funny", "intensity": 50},
                                 headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data
        print("SUCCESS: Free preview works")


class TestColoringBook:
    """Test Coloring Book API endpoints"""
    
    def test_coloring_book_pricing(self):
        """Test coloring book pricing"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing")
        assert response.status_code == 200
        data = response.json()
        # Response has creditPricing instead of pricing
        assert "creditPricing" in data or "pricing" in data
        print(f"SUCCESS: Coloring book pricing retrieved")
    
    def test_coloring_book_export_history_with_fresh_token(self):
        """Test coloring book export history"""
        # Login and get fresh token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/coloring-book/export-history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "exports" in data
        print(f"SUCCESS: Coloring book exports: {len(data['exports'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
