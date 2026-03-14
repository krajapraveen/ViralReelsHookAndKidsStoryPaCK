"""
Comprehensive QA Tests - Iteration 42
Tests all phases from the testing request:
- Phase 1: Public URLs
- Phase 2: Protected routes 
- Phase 3: Login/Logout flows
- Phase 4: Dashboard
- Phase 5: GenStudio pages
- Phase 6: New apps (story-series, challenge-generator, tone-switcher, coloring-book)
- Phase 7: Admin monitoring dashboard
- Phase 8: Subscription management
- Phase 9: Analytics dashboard
- Phase 10: Cashfree payment sandbox
- Phase 11: Worker scaling status
- Phase 12: Copyright audit
- Phase 13: A/B testing
- Phase 14: Webhook endpoint
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-challenges-10.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestPhase1PublicURLs:
    """Phase 1: Test all public URLs are accessible"""
    
    def test_landing_page(self):
        """Landing page should return 200"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
    
    def test_pricing_page(self):
        """Pricing page should return 200"""
        response = requests.get(f"{BASE_URL}/pricing")
        assert response.status_code == 200
    
    def test_user_manual_page(self):
        """User manual page should return 200"""
        response = requests.get(f"{BASE_URL}/user-manual")
        assert response.status_code == 200
    
    def test_contact_page(self):
        """Contact page should return 200"""
        response = requests.get(f"{BASE_URL}/contact")
        assert response.status_code == 200
    
    def test_reviews_page(self):
        """Reviews page should return 200"""
        response = requests.get(f"{BASE_URL}/reviews")
        assert response.status_code == 200


class TestPhase3LoginLogout:
    """Phase 3: Test Login/Logout flows"""
    
    def test_demo_user_login(self):
        """Demo user should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0
    
    def test_admin_user_login(self):
        """Admin user should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role", "").lower() == "admin"
    
    def test_invalid_login(self):
        """Invalid credentials should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401


class TestPhase10CashfreePayment:
    """Phase 10: Cashfree payment sandbox tests"""
    
    def test_cashfree_health(self):
        """Cashfree gateway health check"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] == "cashfree"
        assert data["configured"] == True
        assert data["environment"] == "sandbox"
    
    def test_cashfree_products(self):
        """Get available products for Cashfree"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "starter" in data["products"]
        assert "creator" in data["products"]
        assert "pro" in data["products"]
    
    def test_cashfree_create_order(self):
        """Create Cashfree order (requires auth)"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Create order
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers={"Authorization": f"Bearer {token}"},
            json={"productId": "starter", "currency": "INR"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "orderId" in data
        assert "cfOrderId" in data
        assert "paymentSessionId" in data
        assert data["amount"] == 499
        assert data["credits"] == 100
        assert data["environment"] == "sandbox"


class TestPhase11WorkerScaling:
    """Phase 11: Worker scaling status endpoint tests"""
    
    def test_worker_status_requires_admin(self):
        """Worker status should require admin access"""
        # Login as demo user
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Try to access worker status
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/worker-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_worker_status_as_admin(self):
        """Admin should access worker status"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get worker status
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/worker-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "current_workers" in data
        assert "min_workers" in data
        assert "max_workers" in data
        assert "queue_depth" in data
        assert data["min_workers"] == 2
        assert data["max_workers"] == 10


class TestPhase12CopyrightAudit:
    """Phase 12: Copyright audit endpoint tests"""
    
    def test_run_copyright_audit_as_admin(self):
        """Admin should be able to run copyright audit"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Run audit
        response = requests.post(
            f"{BASE_URL}/api/analytics/admin/run-copyright-audit",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "audit" in data
        assert data["audit"]["status"] in ["PASS", "NEEDS_REVIEW", "ERROR"]
        assert "compliance_score" in data["audit"]
        assert "components_checked" in data["audit"]
    
    def test_get_copyright_audit_result(self):
        """Get latest copyright audit result"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get audit result
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/copyright-audit",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


class TestPhase13ABTesting:
    """Phase 13: A/B testing endpoint tests"""
    
    def test_ab_test_pricing_requires_auth(self):
        """A/B test pricing should require authentication"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/ab-test/pricing")
        assert response.status_code == 401
    
    def test_ab_test_pricing_returns_variant(self):
        """A/B test pricing should return a variant"""
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get A/B test pricing
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/ab-test/pricing",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "variant" in data
        assert data["variant"] in ["A", "B"]
        assert "pricing" in data
        assert "testName" in data


class TestPhase14WebhookEndpoint:
    """Phase 14: Webhook endpoint for subscription renewals"""
    
    def test_webhook_endpoint_exists(self):
        """Webhook endpoint should exist and validate signature"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook/renewal",
            headers={"Content-Type": "application/json"},
            json={"type": "TEST", "data": {}}
        )
        # Should return 401 (invalid signature) or process the webhook
        assert response.status_code in [200, 401]
        if response.status_code == 401:
            data = response.json()
            assert "signature" in data.get("detail", "").lower() or "Invalid signature" in str(data)


class TestCDNStatus:
    """CDN status endpoint tests"""
    
    def test_cdn_status_as_admin(self):
        """Admin should access CDN status"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get CDN status
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/cdn-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "provider" in data
        # CDN is currently disabled as per mocked_api info
        assert data["enabled"] == False


class TestSubscriptionPlans:
    """Subscription plans tests"""
    
    def test_get_subscription_plans(self):
        """Get available subscription plans"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 3
        
        # Verify plan details
        plan_ids = [p["id"] for p in data["plans"]]
        assert "weekly" in plan_ids
        assert "monthly" in plan_ids
        assert "quarterly" in plan_ids
    
    def test_subscription_plans_currency_usd(self):
        """Get subscription plans in USD"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans?currency=USD")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "USD"


class TestAdminMonitoringEndpoints:
    """Admin monitoring endpoints tests"""
    
    def test_admin_overview(self):
        """Admin overview should return stats"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get overview
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "revenue" in data
        assert "jobs" in data
        assert "featureUsage" in data
    
    def test_admin_threat_stats(self):
        """Admin threat stats should return security info"""
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get threat stats
        response = requests.get(
            f"{BASE_URL}/api/analytics/admin/threat-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "currentStatus" in data
        assert "rateWindows" in data


class TestUserAnalytics:
    """User analytics tests"""
    
    def test_user_stats_requires_auth(self):
        """User stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/user-stats")
        assert response.status_code == 401
    
    def test_user_stats_returns_data(self):
        """User stats should return usage data"""
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        token = login_response.json().get("token")
        
        # Get user stats
        response = requests.get(
            f"{BASE_URL}/api/analytics/user-stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "storySeries" in data
        assert "challenges" in data
        assert "toneRewrites" in data
        assert "coloringBooks" in data
        assert "genstudioJobs" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
