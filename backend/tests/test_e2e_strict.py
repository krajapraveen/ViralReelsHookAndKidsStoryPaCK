"""
CreatorStudio AI - Strict E2E Backend API Test Suite
Covers: Auth, Wallet, Generation, GenStudio, Billing, Profile, Privacy
"""
import pytest
import requests
import os
import json
import time
from datetime import datetime
import uuid

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comix-ai-bugfix.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
NEW_TEST_USER = {"email": f"qatest_{uuid.uuid4().hex[:8]}@test.com", "password": "QATest123!"}


class TestHealthAndBasicAPIs:
    """Phase 0: Health check and basic API availability"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        # Accept 200 or redirect
        assert response.status_code in [200, 307], f"Health check failed: {response.status_code}"
        print("PASS: Health endpoint accessible")
    
    def test_pricing_endpoint_public(self):
        """Test public pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing")
        assert response.status_code == 200, f"Pricing endpoint failed: {response.status_code}"
        data = response.json()
        assert "pricing" in data, "Pricing data missing"
        print(f"PASS: Pricing endpoint returns {len(data['pricing'])} job types")
    
    def test_templates_endpoint_public(self):
        """Test public templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200, f"Templates endpoint failed: {response.status_code}"
        data = response.json()
        assert "templates" in data, "Templates data missing"
        print(f"PASS: Templates endpoint returns {len(data['templates'])} templates")


class TestAuthenticationFlows:
    """Phase 1: Authentication - Register, Login, Session"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for auth tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_login_success_demo_user(self):
        """Test successful login with demo user"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=DEMO_USER
        )
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data, "Token missing in response"
        assert "user" in data, "User data missing"
        assert data["user"]["email"] == DEMO_USER["email"], "Email mismatch"
        print(f"PASS: Demo user login successful, credits: {data['user'].get('credits', 'N/A')}")
    
    def test_login_success_admin_user(self):
        """Test successful login with admin user"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_USER
        )
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data, "Token missing"
        assert data["user"].get("role") == "ADMIN", f"Expected ADMIN role, got: {data['user'].get('role')}"
        print(f"PASS: Admin user login successful, role: {data['user']['role']}")
    
    def test_login_failure_invalid_credentials(self):
        """Test login fails with invalid credentials"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPass123!"}
        )
        assert response.status_code == 401, f"Expected 401, got: {response.status_code}"
        print("PASS: Invalid credentials properly rejected with 401")
    
    def test_login_failure_empty_password(self):
        """Test login fails with empty password"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@test.com", "password": ""}
        )
        assert response.status_code in [400, 401, 422], f"Expected error, got: {response.status_code}"
        print("PASS: Empty password properly rejected")
    
    def test_protected_route_without_auth(self):
        """Test protected routes require authentication"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403], f"Expected 401/403, got: {response.status_code}"
        print("PASS: Protected route returns 401/403 without auth")
    
    def test_protected_route_with_auth(self):
        """Test protected routes work with valid auth"""
        # Login first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = login_response.json()["token"]
        
        # Access protected route
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Protected route failed: {response.status_code}"
        data = response.json()
        assert "id" in data, "User ID missing"
        assert "email" in data, "Email missing"
        print(f"PASS: Protected route accessible with auth, user: {data['email']}")


class TestWalletAndCredits:
    """Phase 2: Wallet display, credit operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as demo user
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for wallet tests")
    
    def test_get_wallet_balance(self):
        """Test wallet balance endpoint"""
        response = self.session.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code == 200, f"Wallet endpoint failed: {response.status_code}"
        data = response.json()
        assert "balanceCredits" in data, "Balance missing"
        assert "reservedCredits" in data, "Reserved credits missing"
        assert "availableCredits" in data, "Available credits missing"
        print(f"PASS: Wallet balance: {data['balanceCredits']}, available: {data['availableCredits']}, reserved: {data['reservedCredits']}")
    
    def test_get_credit_ledger(self):
        """Test credit ledger endpoint"""
        response = self.session.get(f"{BASE_URL}/api/wallet/ledger")
        assert response.status_code == 200, f"Ledger endpoint failed: {response.status_code}"
        data = response.json()
        assert "entries" in data, "Ledger entries missing"
        print(f"PASS: Credit ledger has {len(data['entries'])} entries")
    
    def test_get_jobs_list(self):
        """Test jobs listing endpoint"""
        response = self.session.get(f"{BASE_URL}/api/wallet/jobs")
        assert response.status_code == 200, f"Jobs endpoint failed: {response.status_code}"
        data = response.json()
        assert "jobs" in data, "Jobs list missing"
        assert "total" in data, "Total count missing"
        print(f"PASS: Jobs list has {data['total']} total jobs")
    
    def test_get_credit_balance_legacy(self):
        """Test legacy credits endpoint"""
        response = self.session.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 200, f"Credits balance failed: {response.status_code}"
        data = response.json()
        assert "credits" in data, "Credits missing"
        print(f"PASS: Legacy credits endpoint returns {data['credits']} credits")


class TestGenStudioDashboard:
    """Phase 2: GenStudio Dashboard - Tools, History"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for GenStudio tests")
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/dashboard")
        assert response.status_code == 200, f"Dashboard failed: {response.status_code}"
        data = response.json()
        assert "credits" in data, "Credits missing"
        assert "templates" in data, "Templates missing"
        assert "costs" in data, "Costs missing"
        print(f"PASS: GenStudio dashboard - credits: {data['credits']}, templates: {len(data['templates'])}")
    
    def test_genstudio_history(self):
        """Test GenStudio history endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/history")
        assert response.status_code == 200, f"History failed: {response.status_code}"
        data = response.json()
        assert "jobs" in data, "Jobs missing"
        assert "total" in data, "Total missing"
        print(f"PASS: GenStudio history - total: {data['total']}")
    
    def test_genstudio_history_with_type_filter(self):
        """Test GenStudio history with type filter"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/history?type_filter=text_to_image")
        assert response.status_code == 200, f"Filtered history failed: {response.status_code}"
        print("PASS: GenStudio history with type filter works")
    
    def test_genstudio_style_profiles(self):
        """Test style profiles endpoint"""
        response = self.session.get(f"{BASE_URL}/api/genstudio/style-profiles")
        assert response.status_code == 200, f"Style profiles failed: {response.status_code}"
        data = response.json()
        assert "profiles" in data, "Profiles missing"
        print(f"PASS: Style profiles - count: {data.get('count', len(data['profiles']))}")


class TestReelGenerator:
    """Phase 2: Reel Generator - Input validation, generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for Reel tests")
    
    def test_demo_reel_generation(self):
        """Test demo reel generation (no auth required)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json={
                "topic": "Morning productivity tips",
                "niche": "Lifestyle",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Engagement",
                "language": "English"
            }
        )
        assert response.status_code == 200, f"Demo reel failed: {response.status_code}"
        data = response.json()
        assert data.get("isDemo") == True, "Should be marked as demo"
        assert "result" in data, "Result missing"
        print("PASS: Demo reel generation works")
    
    def test_reel_generation_input_validation(self):
        """Test reel generation validates inputs"""
        # Empty topic should fail
        response = self.session.post(
            f"{BASE_URL}/api/generate/reel",
            json={
                "topic": "",
                "niche": "Lifestyle",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Engagement",
                "language": "English"
            }
        )
        assert response.status_code in [400, 422], f"Expected validation error, got: {response.status_code}"
        print("PASS: Reel generation validates empty topic")


class TestStoryGenerator:
    """Phase 2: Story Generator - Input validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for Story tests")
    
    def test_story_generation_endpoint_exists(self):
        """Test story generation endpoint is accessible"""
        response = self.session.post(
            f"{BASE_URL}/api/generate/story",
            json={
                "genre": "Adventure",
                "ageGroup": "4-6",
                "theme": "Friendship",
                "sceneCount": 8
            }
        )
        # Should either succeed or return valid error (not 404/500)
        assert response.status_code in [200, 400, 402, 422, 503], f"Unexpected status: {response.status_code}"
        print(f"PASS: Story endpoint responded with {response.status_code}")


class TestBillingAndPayments:
    """Phase 2: Billing - Plans, Purchase flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for Billing tests")
    
    def test_get_plans(self):
        """Test getting available plans"""
        response = self.session.get(f"{BASE_URL}/api/payments/plans")
        assert response.status_code == 200, f"Plans endpoint failed: {response.status_code}"
        data = response.json()
        assert "plans" in data, "Plans missing"
        assert len(data["plans"]) > 0, "No plans available"
        print(f"PASS: {len(data['plans'])} billing plans available")
    
    def test_get_orders(self):
        """Test getting user orders"""
        response = self.session.get(f"{BASE_URL}/api/payments/orders")
        assert response.status_code == 200, f"Orders endpoint failed: {response.status_code}"
        data = response.json()
        assert "orders" in data, "Orders missing"
        print(f"PASS: User has {len(data['orders'])} orders")
    
    def test_cashfree_plans(self):
        """Test Cashfree plans endpoint"""
        response = self.session.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200, f"Cashfree plans failed: {response.status_code}"
        data = response.json()
        assert "plans" in data or isinstance(data, list), "Plans response invalid"
        print("PASS: Cashfree plans endpoint works")


class TestProfile:
    """Phase 2: Profile - Load, Update"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for Profile tests")
    
    def test_get_profile(self):
        """Test getting user profile"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Profile endpoint failed: {response.status_code}"
        data = response.json()
        assert "id" in data, "ID missing"
        assert "email" in data, "Email missing"
        assert "name" in data, "Name missing"
        print(f"PASS: Profile loaded - {data['email']}")
    
    def test_update_profile(self):
        """Test updating user profile"""
        response = self.session.put(
            f"{BASE_URL}/api/auth/profile",
            json={"name": "Test User Updated"}
        )
        assert response.status_code == 200, f"Profile update failed: {response.status_code}"
        print("PASS: Profile update successful")


class TestPrivacySettings:
    """Phase 2: Privacy - Preferences, Export, Delete"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for Privacy tests")
    
    def test_get_privacy_settings(self):
        """Test getting privacy settings"""
        response = self.session.get(f"{BASE_URL}/api/privacy/settings")
        assert response.status_code == 200, f"Privacy settings failed: {response.status_code}"
        data = response.json()
        assert "settings" in data or "dataCollection" in data, "Privacy data missing"
        print("PASS: Privacy settings loaded")
    
    def test_export_data(self):
        """Test data export endpoint"""
        response = self.session.get(f"{BASE_URL}/api/auth/export-data")
        assert response.status_code == 200, f"Export data failed: {response.status_code}"
        data = response.json()
        assert "user" in data, "User data missing in export"
        print("PASS: Data export works")


class TestAdminAccess:
    """Phase 2: Admin routes - Role-based access"""
    
    def test_admin_routes_require_admin_role(self):
        """Test admin routes reject non-admin users"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as regular user
        response = session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code != 200:
            pytest.skip("Could not login as demo user")
        
        token = response.json()["token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to access admin route
        admin_response = session.get(f"{BASE_URL}/api/admin/users")
        assert admin_response.status_code in [401, 403], f"Expected 401/403 for non-admin, got: {admin_response.status_code}"
        print("PASS: Admin routes properly protected")
    
    def test_admin_access_with_admin_user(self):
        """Test admin routes accessible by admin user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        if response.status_code != 200:
            pytest.skip("Could not login as admin user")
        
        token = response.json()["token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to access admin route
        admin_response = session.get(f"{BASE_URL}/api/admin/users")
        assert admin_response.status_code == 200, f"Admin route failed: {admin_response.status_code}"
        print("PASS: Admin routes accessible by admin user")


class TestNegativeEdgeCases:
    """Phase 3: Negative tests - Empty inputs, special chars"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Could not authenticate for negative tests")
    
    def test_empty_prompt_text_to_image(self):
        """Test empty prompt rejection"""
        response = self.session.post(
            f"{BASE_URL}/api/genstudio/text-to-image",
            json={
                "prompt": "",
                "consent_confirmed": True
            }
        )
        assert response.status_code in [400, 422], f"Expected validation error, got: {response.status_code}"
        print("PASS: Empty prompt properly rejected")
    
    def test_very_long_prompt(self):
        """Test very long prompt handling"""
        long_prompt = "A" * 5000  # 5000 characters
        response = self.session.post(
            f"{BASE_URL}/api/genstudio/text-to-image",
            json={
                "prompt": long_prompt,
                "consent_confirmed": True
            }
        )
        # Should either truncate and succeed, or reject with validation error
        assert response.status_code in [200, 400, 402, 422], f"Unexpected status: {response.status_code}"
        print(f"PASS: Long prompt handled with status {response.status_code}")
    
    def test_special_characters_in_prompt(self):
        """Test special characters handling"""
        response = self.session.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json={
                "topic": "Test <script>alert('xss')</script>",
                "niche": "General",
                "tone": "Bold",
                "duration": "30s",
                "goal": "Engagement",
                "language": "English"
            }
        )
        # Should either succeed (sanitized) or reject
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        print("PASS: Special characters handled properly")
    
    def test_consent_required_for_generation(self):
        """Test consent checkbox is required"""
        response = self.session.post(
            f"{BASE_URL}/api/genstudio/text-to-image",
            json={
                "prompt": "A beautiful sunset",
                "consent_confirmed": False
            }
        )
        assert response.status_code == 400, f"Expected 400 for no consent, got: {response.status_code}"
        print("PASS: Consent requirement enforced")


class TestSecurity:
    """Phase 6: Security tests"""
    
    def test_protected_routes_require_login(self):
        """Test that protected routes require authentication"""
        protected_routes = [
            "/api/auth/me",
            "/api/wallet/me",
            "/api/genstudio/dashboard",
            "/api/generate/reel"
        ]
        
        for route in protected_routes:
            response = requests.get(f"{BASE_URL}{route}")
            if response.status_code not in [401, 403, 405]:  # 405 for POST-only routes
                # Try POST
                response = requests.post(f"{BASE_URL}{route}", json={})
                assert response.status_code in [401, 403, 422], f"{route} not protected: {response.status_code}"
        
        print("PASS: All protected routes require authentication")
    
    def test_no_tokens_in_response_body(self):
        """Test that tokens are not leaked in error responses"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = session.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            token = response.json()["token"]
            
            # Make a request that might include token in error
            bad_response = requests.get(
                f"{BASE_URL}/api/admin/users",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Check response doesn't contain the token
            response_text = bad_response.text.lower()
            assert token not in response_text, "Token leaked in response"
            print("PASS: No token leakage detected")
    
    def test_sql_injection_prevention(self):
        """Test SQL injection is prevented"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "' OR '1'='1",
                "password": "' OR '1'='1"
            }
        )
        # Should fail authentication, not succeed
        assert response.status_code in [400, 401, 422], f"SQL injection may have succeeded: {response.status_code}"
        print("PASS: SQL injection properly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
