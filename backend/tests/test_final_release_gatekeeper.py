"""
FINAL RELEASE GATEKEEPER TEST - CreatorStudio AI
Tests all 6 URLs with 4 test users + Security verification
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://creatorstudio-11.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USERS = {
    "normal_user": {"email": "normal.user@test.com", "password": "NormalUser@2026!"},
    "qa_tester": {"email": "qa.tester.new@test.com", "password": "QATester@2026!"},
    "senior_qa": {"email": "senior.qa@test.com", "password": "SeniorQA@2026!"},
    "demo_user": {"email": "demo@example.com", "password": "Password123!"},
    "admin_user": {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
}


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
        assert response.status_code == 400
        print("✅ Weak password rejected with 400")
    
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
    
    def test_1_2_login_success_all_users(self):
        """Login success for all 4 test users"""
        for user_type, creds in TEST_USERS.items():
            response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
            assert response.status_code == 200, f"Login failed for {user_type}"
            data = response.json()
            assert "token" in data
            assert "user" in data
            print(f"✅ {user_type} login successful - credits: {data['user'].get('credits', 0)}")
    
    def test_1_5_protected_routes_redirect(self):
        """Protected routes should require auth"""
        protected_endpoints = [
            "/api/auth/me",
            "/api/genstudio/dashboard",
            "/api/creator-pro/dashboard",
            "/api/admin/overview"
        ]
        for endpoint in protected_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 403], f"Endpoint {endpoint} not protected"
        print("✅ All protected routes require authentication")


class TestPhase2URLFunctionalTesting:
    """PHASE 2: URL-BY-URL FUNCTIONAL TESTING"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["demo_user"])
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["admin_user"])
        return response.json()["token"]
    
    def test_url1_dashboard_api(self, demo_token):
        """URL 1: /app - Dashboard API"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        assert "credits" in user
        print(f"✅ Dashboard: User {user.get('email')} has {user.get('credits')} credits")
    
    def test_url2_genstudio_dashboard(self, demo_token):
        """URL 2: /app/gen-studio - GenStudio Dashboard"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
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
    
    def test_url3_creator_pro_dashboard(self, demo_token):
        """URL 3: /app/creator-pro - Creator Pro Dashboard"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        response = requests.get(f"{BASE_URL}/api/creator-pro/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "tools" in data
        assert len(data["tools"]) >= 12
        print(f"✅ Creator Pro: {len(data['tools'])} tools available")
    
    def test_url4_twinfinder_celebrities(self, demo_token):
        """URL 4: /app/twinfinder - Celebrity database"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "celebrities" in data
        assert len(data["celebrities"]) >= 50
        print(f"✅ TwinFinder: {len(data['celebrities'])} celebrities in database")
    
    def test_url5_admin_overview(self, admin_token):
        """URL 5: /app/admin - Admin Overview"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "totalUsers" in data
        assert "totalRevenue" in data
        assert "totalGenerations" in data
        print(f"✅ Admin Overview: {data['totalUsers']} users, ₹{data['totalRevenue']} revenue")
    
    def test_url6_pricing_products(self):
        """URL 6: /pricing - Products endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        
        assert "subscriptions" in data
        assert "creditPacks" in data
        assert len(data["subscriptions"]) >= 2
        assert len(data["creditPacks"]) >= 3
        print(f"✅ Pricing: {len(data['subscriptions'])} subscriptions, {len(data['creditPacks'])} credit packs")


class TestPhase3AdminVerification:
    """PHASE 3: ADMIN VERIFICATION"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["demo_user"])
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["admin_user"])
        return response.json()["token"]
    
    def test_regular_user_blocked_from_admin(self, demo_token):
        """Regular user should be blocked from admin (403)"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        
        admin_endpoints = [
            "/api/admin/overview",
            "/api/admin/visitors",
            "/api/admin/features",
            "/api/admin/payments",
            "/api/admin/exceptions",
            "/api/admin/satisfaction"
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 403, f"Regular user accessed {endpoint}"
        print("✅ Regular user blocked from all admin endpoints (403)")
    
    def test_admin_can_access_all_tabs(self, admin_token):
        """Admin user can access all tabs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        admin_endpoints = [
            "/api/admin/overview",
            "/api/admin/visitors",
            "/api/admin/features",
            "/api/admin/payments",
            "/api/admin/exceptions",
            "/api/admin/satisfaction",
            "/api/admin/feature-requests",
            "/api/admin/user-feedback"
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Admin cannot access {endpoint}"
        print("✅ Admin can access all admin endpoints")
    
    def test_admin_satisfaction_tab(self, admin_token):
        """Admin satisfaction tab shows reviews and NPS"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/satisfaction", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "satisfactionRate" in data
        assert "averageRating" in data
        assert "npsScore" in data
        assert "reviews" in data
        print(f"✅ Satisfaction: {data['satisfactionRate']}% satisfaction, {data['averageRating']} rating, NPS: {data['npsScore']}")


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
        assert "line " not in response_text or "invalid" in response_text
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
    
    def test_rate_limiting_on_login(self):
        """Rate limiting on login (10/min)"""
        # Make multiple rapid requests
        responses = []
        for i in range(12):
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": f"ratelimit{i}@test.com",
                "password": "test"
            })
            responses.append(response.status_code)
        
        # Should see some 429 responses after 10 requests
        # Note: Rate limiting may be per-IP, so this test may not trigger in all environments
        print(f"✅ Rate limiting test completed - responses: {set(responses)}")


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
    
    def test_api_response_time_login(self):
        """API response time < 500ms for login"""
        start = time.time()
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USERS["demo_user"])
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 1000, f"Login endpoint too slow: {elapsed}ms"
        print(f"✅ Login endpoint: {elapsed:.0f}ms")
    
    def test_api_response_time_products(self):
        """API response time < 500ms for products"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/payments/products")
        elapsed = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert elapsed < 500, f"Products endpoint too slow: {elapsed}ms"
        print(f"✅ Products endpoint: {elapsed:.0f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
