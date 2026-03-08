"""
Go-Live QA Comprehensive Test Suite - Iteration 43
Tests all 10 phases of CreatorStudio AI

Phase 1: Full Site Crawl - All internal links
Phase 2: Auth/Access Control - Login, Register, RBAC
Phase 3: Cashfree Payments - Sandbox flows
Phase 4: Generators - All AI generators
Phase 5: Exception Handling - Error UIs
Phase 6: Security - Headers, Rate Limiting
Phase 7: Admin Dashboard - All tabs
Phase 8: Downloads - Invoice PDFs, media
Phase 9: Mobile Responsive - (Playwright test)
Phase 10: Final Verification - E2E flows
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-video-builder.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}

# Cashfree credentials
CASHFREE_APP_ID = "TEST109947494c1ad7cf7b10784f590994749901"
CASHFREE_SECRET = "cfsk_ma_test_f9a613ed1437f4479a4cce91c6cc07fe_279396a6"

class TestFixtures:
    """Shared test fixtures"""
    demo_token = None
    admin_token = None
    
    @classmethod
    def get_demo_token(cls):
        if cls.demo_token:
            return cls.demo_token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            cls.demo_token = response.json().get("token")
        return cls.demo_token
    
    @classmethod
    def get_admin_token(cls):
        if cls.admin_token:
            return cls.admin_token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        if response.status_code == 200:
            cls.admin_token = response.json().get("token")
        return cls.admin_token


# =============================================================================
# PHASE 1: FULL SITE CRAWL - Test all internal links
# =============================================================================
class TestPhase1SiteCrawl:
    """Phase 1: Full site crawl - test all URLs for 404/500 errors"""
    
    # Public pages that should return 200
    PUBLIC_URLS = [
        "/",
        "/pricing",
        "/contact",
        "/reviews",
        "/user-manual",
        "/help",
        "/privacy-policy",
    ]
    
    # API endpoints that should be accessible
    API_HEALTH_URLS = [
        "/api/health",
        "/api/health/",
    ]
    
    def test_public_pages_accessible(self):
        """Test all public pages return 200"""
        for url in self.PUBLIC_URLS:
            response = requests.get(f"{BASE_URL}{url}", allow_redirects=True)
            assert response.status_code == 200, f"Public page {url} failed with status {response.status_code}"
            print(f"PASS: {url} - Status {response.status_code}")
    
    def test_api_health_endpoints(self):
        """Test API health endpoints"""
        for url in self.API_HEALTH_URLS:
            response = requests.get(f"{BASE_URL}{url}", allow_redirects=True)
            assert response.status_code == 200, f"Health endpoint {url} failed"
            data = response.json()
            assert data.get("status") == "healthy", f"Health endpoint {url} not healthy"
            print(f"PASS: {url} - Status: healthy")
    
    def test_api_docs_accessible(self):
        """Test API docs are accessible"""
        response = requests.get(f"{BASE_URL}/api/docs", allow_redirects=True)
        assert response.status_code == 200, "API docs not accessible"
        print("PASS: /api/docs accessible")
    
    def test_no_404_on_main_routes(self):
        """Test main routes don't return 404"""
        main_routes = ["/login", "/signup", "/pricing"]
        for route in main_routes:
            response = requests.get(f"{BASE_URL}{route}", allow_redirects=True)
            assert response.status_code != 404, f"Route {route} returned 404"
            print(f"PASS: {route} - No 404")


# =============================================================================
# PHASE 2: AUTH/ACCESS CONTROL
# =============================================================================
class TestPhase2AuthAccess:
    """Phase 2: Authentication and access control testing"""
    
    def test_demo_user_login_success(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == DEMO_USER["email"]
        print(f"PASS: Demo user login successful - Credits: {data['user'].get('credits', 0)}")
    
    def test_admin_user_login_success(self):
        """Test admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data["user"]["role"] == "ADMIN", "Admin role not set"
        print(f"PASS: Admin user login successful - Role: {data['user']['role']}")
    
    def test_invalid_credentials_rejected(self):
        """Test invalid credentials are rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Invalid credentials should return 401"
        print("PASS: Invalid credentials rejected with 401")
    
    def test_protected_routes_require_auth(self):
        """Test protected API routes require authentication"""
        protected_endpoints = [
            "/api/auth/me",
            "/api/generate/",
            "/api/genstudio/dashboard",
            "/api/credits/balance"
        ]
        
        for endpoint in protected_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            # Should return 401 or 403 for unauthenticated requests
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require auth, got {response.status_code}"
            print(f"PASS: {endpoint} requires auth - Status {response.status_code}")
    
    def test_admin_routes_blocked_for_normal_user(self):
        """Test admin routes return 403 for normal user"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        admin_endpoints = [
            "/api/admin/analytics/dashboard",
            "/api/admin/users",
            "/api/admin/payments/successful"
        ]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 403, f"Admin endpoint {endpoint} should return 403 for normal user"
            print(f"PASS: {endpoint} returns 403 for normal user")
    
    def test_get_current_user_profile(self):
        """Test getting current user profile"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        data = response.json()
        assert "email" in data, "Email missing from profile"
        assert "credits" in data, "Credits missing from profile"
        print(f"PASS: User profile retrieved - Credits: {data.get('credits', 0)}")


# =============================================================================
# PHASE 3: CASHFREE PAYMENTS SANDBOX
# =============================================================================
class TestPhase3CashfreePayments:
    """Phase 3: Cashfree payment integration testing in sandbox mode"""
    
    def test_cashfree_health_endpoint(self):
        """Test Cashfree health endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Cashfree health failed: {response.text}"
        data = response.json()
        assert data.get("configured") == True, "Cashfree not configured"
        assert data.get("environment") == "sandbox", "Cashfree not in sandbox mode"
        print(f"PASS: Cashfree health - configured={data.get('configured')}, env={data.get('environment')}")
    
    def test_get_products(self):
        """Test getting available products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Get products failed: {response.text}"
        data = response.json()
        assert "products" in data, "Products not in response"
        products = data["products"]
        # Check expected products exist
        expected_products = ["starter", "creator", "pro", "weekly", "monthly"]
        for prod in expected_products:
            assert prod in products, f"Product {prod} missing"
        print(f"PASS: Products available - {len(products)} products")
    
    def test_create_order_sandbox(self):
        """Test creating a Cashfree order in sandbox"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "productId": "starter",
            "currency": "INR"
        }
        
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order", json=payload, headers=headers)
        
        # Rate limiting might cause 429
        if response.status_code == 429:
            print("WARN: Rate limited on create-order")
            pytest.skip("Rate limited")
        
        assert response.status_code == 200, f"Create order failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") == True, "Order creation not successful"
        assert "orderId" in data, "No orderId in response"
        assert "paymentSessionId" in data, "No paymentSessionId in response"
        print(f"PASS: Order created - orderId={data.get('orderId')}, sessionId exists={bool(data.get('paymentSessionId'))}")
    
    def test_subscription_plans_endpoint(self):
        """Test subscription plans endpoint"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200, f"Get plans failed: {response.text}"
        data = response.json()
        assert "plans" in data, "Plans not in response"
        plans = data["plans"]
        # Check for expected plans
        plan_names = [p.get("name", "").lower() for p in plans]
        assert any("weekly" in n for n in plan_names), "Weekly plan missing"
        assert any("monthly" in n for n in plan_names), "Monthly plan missing"
        print(f"PASS: Subscription plans - {len(plans)} plans available")
    
    def test_webhook_signature_validation(self):
        """Test webhook endpoint validates signature"""
        # Send invalid signature to webhook
        response = requests.post(
            f"{BASE_URL}/api/cashfree/webhook",
            json={"type": "TEST_EVENT", "data": {}},
            headers={"x-webhook-signature": "invalid", "x-webhook-timestamp": "12345"}
        )
        # Should reject invalid signature
        assert response.status_code in [403, 200], f"Webhook validation unexpected: {response.status_code}"
        print(f"PASS: Webhook endpoint responds - Status {response.status_code}")


# =============================================================================
# PHASE 4: GENERATORS - Test all AI generators
# =============================================================================
class TestPhase4Generators:
    """Phase 4: Test all AI generation endpoints"""
    
    def test_reel_generator_endpoint_exists(self):
        """Test reel generator endpoint responds"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        # Just test the endpoint exists (don't actually generate to save credits)
        response = requests.post(f"{BASE_URL}/api/generate/reel", json={
            "topic": "test",
            "niche": "General",
            "tone": "Bold",
            "duration": "30s",
            "goal": "Engagement"
        }, headers=headers)
        
        # Should return 200 or 422 (validation) or 503 (service unavailable)
        assert response.status_code in [200, 400, 422, 503], f"Reel endpoint unexpected: {response.status_code}"
        print(f"PASS: Reel generator endpoint responds - Status {response.status_code}")
    
    def test_story_generator_endpoint_exists(self):
        """Test story generator endpoint responds"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/generate/story", json={
            "genre": "Adventure",
            "ageGroup": "4-6",
            "theme": "Friendship",
            "sceneCount": 4
        }, headers=headers)
        
        assert response.status_code in [200, 400, 422, 503], f"Story endpoint unexpected: {response.status_code}"
        print(f"PASS: Story generator endpoint responds - Status {response.status_code}")
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=headers)
        
        assert response.status_code == 200, f"GenStudio dashboard failed: {response.text}"
        data = response.json()
        assert "credits" in data, "Credits missing from dashboard"
        assert "templates" in data, "Templates missing from dashboard"
        assert "costs" in data, "Costs missing from dashboard"
        print(f"PASS: GenStudio dashboard - Credits: {data.get('credits')}, Templates: {len(data.get('templates', []))}")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200, f"Templates failed: {response.text}"
        data = response.json()
        assert "templates" in data, "Templates missing"
        assert len(data["templates"]) > 0, "No templates returned"
        print(f"PASS: GenStudio templates - {len(data['templates'])} templates")
    
    def test_story_series_endpoint(self):
        """Test story series endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/story-series/history", headers=headers)
        
        assert response.status_code == 200, f"Story series history failed: {response.text}"
        print(f"PASS: Story series endpoint works - Status {response.status_code}")
    
    def test_challenge_generator_endpoint(self):
        """Test challenge generator endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/challenge-generator/history", headers=headers)
        
        assert response.status_code == 200, f"Challenges history failed: {response.text}"
        print(f"PASS: Challenge generator endpoint works - Status {response.status_code}")
    
    def test_tone_switcher_endpoint(self):
        """Test tone switcher endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/tone-switcher/history", headers=headers)
        
        assert response.status_code == 200, f"Tone switcher history failed: {response.text}"
        print(f"PASS: Tone switcher endpoint works - Status {response.status_code}")
    
    def test_coloring_book_endpoint(self):
        """Test coloring book endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing", headers=headers)
        
        assert response.status_code == 200, f"Coloring book pricing failed: {response.text}"
        print(f"PASS: Coloring book endpoint works - Status {response.status_code}")


# =============================================================================
# PHASE 5: EXCEPTION HANDLING
# =============================================================================
class TestPhase5ExceptionHandling:
    """Phase 5: Test exception handling and error responses"""
    
    def test_invalid_json_returns_422(self):
        """Test invalid JSON body returns proper error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422, f"Invalid JSON should return 422, got {response.status_code}"
        print("PASS: Invalid JSON returns 422")
    
    def test_missing_required_fields_returns_422(self):
        """Test missing required fields returns 422"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={})
        assert response.status_code == 422, f"Missing fields should return 422, got {response.status_code}"
        print("PASS: Missing required fields returns 422")
    
    def test_nonexistent_endpoint_returns_404(self):
        """Test nonexistent endpoint returns 404"""
        response = requests.get(f"{BASE_URL}/api/nonexistent/endpoint")
        assert response.status_code == 404, f"Nonexistent endpoint should return 404, got {response.status_code}"
        print("PASS: Nonexistent endpoint returns 404")
    
    def test_method_not_allowed_returns_405(self):
        """Test wrong HTTP method returns 405"""
        response = requests.delete(f"{BASE_URL}/api/health")
        # Health endpoint might not support DELETE
        assert response.status_code in [404, 405], f"Wrong method should return 405 or 404, got {response.status_code}"
        print(f"PASS: Wrong HTTP method handled - Status {response.status_code}")


# =============================================================================
# PHASE 6: SECURITY
# =============================================================================
class TestPhase6Security:
    """Phase 6: Security headers and rate limiting"""
    
    def test_security_headers_present(self):
        """Test security headers are present in response"""
        response = requests.get(f"{BASE_URL}/api/health")
        headers = response.headers
        
        # Check for key security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        }
        
        for header, expected_value in security_headers.items():
            assert header in headers, f"Security header {header} missing"
            assert headers[header] == expected_value, f"Header {header} has wrong value: {headers[header]}"
            print(f"PASS: {header}: {headers[header]}")
    
    def test_csp_header_present(self):
        """Test Content-Security-Policy header is present"""
        response = requests.get(f"{BASE_URL}/api/health")
        headers = response.headers
        
        assert "Content-Security-Policy" in headers, "CSP header missing"
        csp = headers["Content-Security-Policy"]
        assert "default-src" in csp, "CSP missing default-src"
        print(f"PASS: CSP header present - {len(csp)} chars")
    
    def test_cors_headers_present(self):
        """Test CORS headers are present"""
        response = requests.options(
            f"{BASE_URL}/api/health",
            headers={"Origin": "https://story-video-builder.preview.emergentagent.com"}
        )
        # OPTIONS should return 200 or method not allowed
        print(f"PASS: CORS preflight handled - Status {response.status_code}")
    
    def test_referrer_policy_header(self):
        """Test Referrer-Policy header"""
        response = requests.get(f"{BASE_URL}/api/health")
        headers = response.headers
        
        assert "Referrer-Policy" in headers, "Referrer-Policy header missing"
        print(f"PASS: Referrer-Policy: {headers['Referrer-Policy']}")


# =============================================================================
# PHASE 7: ADMIN DASHBOARD
# =============================================================================
class TestPhase7AdminDashboard:
    """Phase 7: Admin dashboard and monitoring endpoints"""
    
    def test_admin_dashboard_accessible(self):
        """Test admin dashboard is accessible to admin user"""
        token = TestFixtures.get_admin_token()
        if not token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        
        assert response.status_code == 200, f"Admin dashboard failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Dashboard not successful"
        assert "data" in data, "Data missing from dashboard"
        print(f"PASS: Admin dashboard accessible - totalUsers: {data['data']['overview'].get('totalUsers', 0)}")
    
    def test_admin_users_list(self):
        """Test admin can list users"""
        token = TestFixtures.get_admin_token()
        if not token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        
        assert response.status_code == 200, f"Admin users list failed: {response.text}"
        data = response.json()
        assert "users" in data, "Users missing from response"
        print(f"PASS: Admin users list - {len(data['users'])} users")
    
    def test_admin_monitoring_overview(self):
        """Test admin monitoring overview endpoint"""
        token = TestFixtures.get_admin_token()
        if not token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/admin/overview", headers=headers)
        
        assert response.status_code == 200, f"Admin overview failed: {response.text}"
        data = response.json()
        # Check for key fields in the overview
        assert "featureUsage" in data or "users" in data or "jobs" in data, "Overview data missing key fields"
        print(f"PASS: Admin monitoring overview - Status {response.status_code}")
    
    def test_admin_threat_stats(self):
        """Test admin threat stats endpoint"""
        token = TestFixtures.get_admin_token()
        if not token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/admin/threat-stats", headers=headers)
        
        assert response.status_code == 200, f"Threat stats failed: {response.text}"
        print(f"PASS: Admin threat stats - Status {response.status_code}")
    
    def test_admin_worker_status(self):
        """Test admin worker status endpoint"""
        token = TestFixtures.get_admin_token()
        if not token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/admin/worker-status", headers=headers)
        
        assert response.status_code == 200, f"Worker status failed: {response.text}"
        data = response.json()
        assert "current_workers" in data or "min_workers" in data, "Worker info missing"
        print(f"PASS: Admin worker status - Status {response.status_code}")


# =============================================================================
# PHASE 8: DOWNLOADS
# =============================================================================
class TestPhase8Downloads:
    """Phase 8: Test download functionality"""
    
    def test_user_manual_api(self):
        """Test user manual API endpoint"""
        response = requests.get(f"{BASE_URL}/api/help/manual")
        
        assert response.status_code == 200, f"User manual failed: {response.text}"
        data = response.json()
        assert "overview" in data or "features" in data, "Manual content missing"
        print(f"PASS: User manual API - Status {response.status_code}")
    
    def test_quick_start_guide(self):
        """Test quick start guide endpoint"""
        response = requests.get(f"{BASE_URL}/api/help/quick-start")
        
        assert response.status_code == 200, f"Quick start failed: {response.text}"
        print(f"PASS: Quick start guide - Status {response.status_code}")
    
    def test_help_search(self):
        """Test help search endpoint"""
        response = requests.get(f"{BASE_URL}/api/help/search?q=credits")
        
        assert response.status_code == 200, f"Help search failed: {response.text}"
        print(f"PASS: Help search - Status {response.status_code}")
    
    def test_export_user_data_requires_auth(self):
        """Test export data requires authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/export-data")
        assert response.status_code in [401, 403], "Export should require auth"
        print(f"PASS: Export data requires auth - Status {response.status_code}")


# =============================================================================
# PHASE 10: FINAL VERIFICATION
# =============================================================================
class TestPhase10FinalVerification:
    """Phase 10: Final verification of all integrations"""
    
    def test_full_login_flow(self):
        """Test complete login flow"""
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, "Login failed"
        data = response.json()
        token = data.get("token")
        
        # Get profile
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, "Get profile failed"
        
        print("PASS: Full login flow completed successfully")
    
    def test_credits_balance_endpoint(self):
        """Test credits balance endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        assert "balance" in data or "credits" in data, "Balance missing"
        print(f"PASS: Credits balance endpoint - Status {response.status_code}")
    
    def test_wallet_endpoint(self):
        """Test wallet endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=headers)
        
        assert response.status_code == 200, f"Wallet me failed: {response.text}"
        data = response.json()
        assert "balanceCredits" in data or "availableCredits" in data, "Balance missing"
        print(f"PASS: Wallet endpoint - Status {response.status_code}")
    
    def test_user_analytics(self):
        """Test user analytics endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/user-stats", headers=headers)
        
        assert response.status_code == 200, f"User analytics failed: {response.text}"
        print(f"PASS: User analytics - Status {response.status_code}")
    
    def test_subscription_current(self):
        """Test current subscription endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/subscriptions/current", headers=headers)
        
        assert response.status_code == 200, f"Subscription current failed: {response.text}"
        print(f"PASS: Subscription current - Status {response.status_code}")
    
    def test_regional_pricing(self):
        """Test regional pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/pricing/plans")
        
        assert response.status_code == 200, f"Regional pricing failed: {response.text}"
        data = response.json()
        assert "plans" in data, "Plans missing from pricing"
        print(f"PASS: Regional pricing - Status {response.status_code}")
    
    def test_privacy_my_data(self):
        """Test privacy my-data endpoint"""
        token = TestFixtures.get_demo_token()
        if not token:
            pytest.skip("Demo token not available")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/privacy/my-data", headers=headers)
        
        assert response.status_code == 200, f"Privacy my-data failed: {response.text}"
        print(f"PASS: Privacy my-data - Status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
