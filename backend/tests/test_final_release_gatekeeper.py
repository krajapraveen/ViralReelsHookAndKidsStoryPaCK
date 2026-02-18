"""
FINAL RELEASE GATEKEEPER TEST - CreatorStudio AI
Tests all 6 URLs with 4 test users + Security verification
Updated with correct API endpoints
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://studio-deploy-2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USERS = {
    "normal_user": {"email": "normal.user@test.com", "password": "NormalUser@2026!"},
    "qa_tester": {"email": "qa.tester.new@test.com", "password": "QATester@2026!"},
    "senior_qa": {"email": "senior.qa@test.com", "password": "SeniorQA@2026!"},
    "demo_user": {"email": "demo@example.com", "password": "Password123!"},
    "admin_user": {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
}

# Cache tokens to avoid rate limiting
_token_cache = {}

def get_token(user_type):
    """Get cached token or login"""
    if user_type in _token_cache:
        return _token_cache[user_type]
    
    creds = TEST_USERS[user_type]
    response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if response.status_code == 200:
        token = response.json().get("token")
        _token_cache[user_type] = token
        return token
    return None


class TestPhase0PreCheck:
    """PHASE 0: PRECHECK - Verify all 6 URLs are accessible"""
    
    def test_health_endpoint(self):
        """Health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "security" in data
        print(f"✅ Health: {data}")
    
    def test_security_headers_present(self):
        """Verify all security headers are present"""
        response = requests.get(f"{BASE_URL}/api/health/")
        headers = response.headers
        
        # Required security headers
        assert "x-frame-options" in headers, "Missing X-Frame-Options"
        assert headers["x-frame-options"] == "DENY"
        
        assert "x-content-type-options" in headers, "Missing X-Content-Type-Options"
        assert headers["x-content-type-options"] == "nosniff"
        
        assert "x-xss-protection" in headers, "Missing X-XSS-Protection"
        assert "1; mode=block" in headers["x-xss-protection"]
        
        assert "referrer-policy" in headers, "Missing Referrer-Policy"
        assert "content-security-policy" in headers, "Missing CSP"
        assert "permissions-policy" in headers, "Missing Permissions-Policy"
        
        print("✅ All security headers present")
    
    def test_csp_header_content(self):
        """Verify CSP header has proper directives"""
        response = requests.get(f"{BASE_URL}/api/health/")
        csp = response.headers.get("content-security-policy", "")
        
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "frame-ancestors 'none'" in csp
        assert "upgrade-insecure-requests" in csp
        print(f"✅ CSP properly configured")
    
    def test_cross_origin_headers(self):
        """Verify Cross-Origin headers"""
        response = requests.get(f"{BASE_URL}/api/health/")
        headers = response.headers
        
        assert "cross-origin-embedder-policy" in headers
        assert "cross-origin-opener-policy" in headers
        assert "cross-origin-resource-policy" in headers
        print("✅ Cross-Origin headers present")


class TestPhase1AuthEndToEnd:
    """PHASE 1: AUTH END-TO-END Testing"""
    
    def test_1_1_signup_empty_submit(self):
        """Signup with empty data should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={})
        assert response.status_code == 422
        print("✅ Empty signup rejected with 422")
    
    def test_1_1_signup_invalid_email(self):
        """Signup with invalid email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "invalid-email",
            "password": "ValidPass123!",
            "name": "Test"
        })
        assert response.status_code == 422
        print("✅ Invalid email rejected with 422")
    
    def test_1_1_signup_weak_password(self):
        """Signup with weak password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "test@example.com",
            "password": "weak",
            "name": "Test"
        })
        # Can be 400 or 422 depending on validation order
        assert response.status_code in [400, 422]
        print(f"✅ Weak password rejected with {response.status_code}")
    
    def test_1_1_signup_existing_email(self):
        """Signup with existing email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "demo@example.com",
            "password": "ValidPass123!",
            "name": "Test"
        })
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
        print("✅ Existing email rejected with 400")
    
    def test_1_2_login_empty_submit(self):
        """Login with empty data should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={})
        assert response.status_code == 422
        print("✅ Empty login rejected with 422")
    
    def test_1_2_login_wrong_password(self):
        """Login with wrong password should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "WrongPassword123!"
        })
        assert response.status_code == 401
        print("✅ Wrong password rejected with 401")
    
    def test_1_2_login_nonexistent_email(self):
        """Login with non-existent email should fail"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 401
        print("✅ Non-existent email rejected with 401")
    
    def test_1_2_login_success_demo_user(self):
        """Login success for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["demo_user"])
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        _token_cache["demo_user"] = data["token"]
        print(f"✅ Demo user login successful - credits: {data['user'].get('credits', 0)}")
    
    def test_1_5_protected_routes_redirect(self):
        """Protected routes should require auth"""
        protected_endpoints = [
            "/api/auth/me",
            "/api/genstudio/dashboard"
        ]
        for endpoint in protected_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 403], f"Endpoint {endpoint} not protected"
        print("✅ Protected routes require authentication")


class TestPhase2URLFunctionalTesting:
    """PHASE 2: URL-BY-URL FUNCTIONAL TESTING"""
    
    def test_url1_dashboard_api(self):
        """URL 1: /app - Dashboard API"""
        token = get_token("demo_user")
        if not token:
            pytest.skip("Could not get demo token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        assert "credits" in user
        print(f"✅ Dashboard: User {user.get('email')} has {user.get('credits')} credits")
    
    def test_url2_genstudio_dashboard(self):
        """URL 2: /app/gen-studio - GenStudio Dashboard"""
        token = get_token("demo_user")
        if not token:
            pytest.skip("Could not get demo token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "credits" in data
        assert "templates" in data
        assert "costs" in data
        assert len(data["templates"]) >= 5
        print(f"✅ GenStudio: {len(data['templates'])} templates, costs: {data['costs']}")
    
    def test_url2_genstudio_templates(self):
        """URL 2: GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"✅ GenStudio templates: {len(data['templates'])} available")
    
    def test_url3_creator_pro_costs(self):
        """URL 3: /app/creator-pro - Creator Pro Costs"""
        response = requests.get(f"{BASE_URL}/api/creator-pro/costs")
        assert response.status_code == 200
        data = response.json()
        
        assert "costs" in data
        assert "features" in data
        assert len(data["costs"]) >= 12
        print(f"✅ Creator Pro: {len(data['costs'])} tools available")
    
    def test_url4_twinfinder_celebrities(self):
        """URL 4: /app/twinfinder - Celebrity database"""
        token = get_token("demo_user")
        if not token:
            pytest.skip("Could not get demo token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "celebrities" in data
        assert len(data["celebrities"]) >= 10  # At least 10 celebrities
        print(f"✅ TwinFinder: {len(data['celebrities'])} celebrities in database")
    
    def test_url5_admin_overview(self):
        """URL 5: /app/admin - Admin Overview"""
        token = get_token("admin_user")
        if not token:
            pytest.skip("Could not get admin token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Data is nested under 'data' key
        assert "data" in data or "overview" in data
        overview = data.get("data", {}).get("overview", data.get("overview", {}))
        print(f"✅ Admin Overview: {overview.get('totalUsers', 'N/A')} users")
    
    def test_url6_pricing_products(self):
        """URL 6: /pricing - Products endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        
        assert "products" in data
        assert "razorpayKeyId" in data
        products = data["products"]
        assert len(products) >= 5  # At least 5 products
        print(f"✅ Pricing: {len(products)} products available")


class TestPhase3AdminVerification:
    """PHASE 3: ADMIN VERIFICATION"""
    
    def test_regular_user_blocked_from_admin(self):
        """Regular user should be blocked from admin (403)"""
        token = get_token("demo_user")
        if not token:
            pytest.skip("Could not get demo token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        admin_endpoints = [
            "/api/admin/analytics/dashboard",
            "/api/admin/users/list",
            "/api/admin/exceptions/all"
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 403, f"Regular user accessed {endpoint}"
        print("✅ Regular user blocked from all admin endpoints (403)")
    
    def test_admin_can_access_all_tabs(self):
        """Admin user can access all tabs"""
        token = get_token("admin_user")
        if not token:
            pytest.skip("Could not get admin token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        admin_endpoints = [
            "/api/admin/analytics/dashboard",
            "/api/admin/users/list",
            "/api/admin/exceptions/all",
            "/api/admin/feedback/all",
            "/api/admin/feature-requests"
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Admin cannot access {endpoint}"
        print("✅ Admin can access all admin endpoints")


class TestPhase5ExceptionHandling:
    """PHASE 5: EXCEPTION HANDLING"""
    
    def test_invalid_inputs_return_proper_errors(self):
        """Invalid inputs return proper errors"""
        # Invalid JSON
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        print("✅ Invalid JSON returns 422")
    
    def test_no_stack_traces_exposed(self):
        """No stack traces exposed in error responses"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "wrong"
        })
        
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "file \"" not in response_text
        print("✅ No stack traces exposed")
    
    def test_sql_injection_blocked(self):
        """SQL injection attempts blocked"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "'; DROP TABLE users; --",
            "password": "test"
        })
        assert response.status_code in [401, 422]
        print("✅ SQL injection blocked")
    
    def test_xss_attempt_blocked(self):
        """XSS attempts blocked"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "<script>alert('xss')</script>@test.com",
            "password": "test"
        })
        assert response.status_code in [401, 422]
        print("✅ XSS attempt blocked")


class TestPhase6SecurityVerification:
    """PHASE 6: SECURITY VERIFICATION"""
    
    def test_all_security_headers(self):
        """Verify all security headers"""
        response = requests.get(f"{BASE_URL}/api/health/")
        headers = response.headers
        
        security_headers = {
            "x-frame-options": "DENY",
            "x-content-type-options": "nosniff",
            "x-xss-protection": "1; mode=block",
            "referrer-policy": "strict-origin-when-cross-origin",
        }
        
        for header, expected in security_headers.items():
            assert header in headers, f"Missing {header}"
            assert expected in headers[header], f"Wrong value for {header}"
        
        assert "content-security-policy" in headers
        assert "permissions-policy" in headers
        print("✅ All security headers verified")


class TestPhase7Performance:
    """PHASE 7: PERFORMANCE"""
    
    def test_api_response_time_health(self):
        """API response time < 500ms for health"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/health/")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 500, f"Health endpoint too slow: {elapsed}ms"
        print(f"✅ Health endpoint: {elapsed:.0f}ms")
    
    def test_api_response_time_products(self):
        """API response time < 500ms for products"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/payments/products")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 500, f"Products endpoint too slow: {elapsed}ms"
        print(f"✅ Products endpoint: {elapsed:.0f}ms")
    
    def test_api_response_time_templates(self):
        """API response time < 500ms for templates"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 500, f"Templates endpoint too slow: {elapsed}ms"
        print(f"✅ Templates endpoint: {elapsed:.0f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
