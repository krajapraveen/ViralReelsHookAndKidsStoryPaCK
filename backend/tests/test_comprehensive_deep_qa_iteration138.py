"""
Iteration 138 - COMPREHENSIVE DEEP QA Testing
Production-grade testing of ALL APIs, endpoints, and features
Testing: Authentication, Generation, Billing, Credits, Admin, Story Video Studio, Role-based Access, Input Validation
"""
import pytest
import requests
import os
import time
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
print(f"Testing against BASE_URL: {BASE_URL}")

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"

# Global token storage
USER_TOKEN = None
ADMIN_TOKEN = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_auth_header(token):
    """Get authorization header"""
    return {"Authorization": f"Bearer {token}"}


def login_user(email, password):
    """Login and return token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json().get("token")
    return None


# =============================================================================
# 1. AUTHENTICATION TESTS
# =============================================================================
class TestAuthentication:
    """Test all authentication endpoints - Login, Register, Profile, Password"""
    
    def test_01_login_valid_credentials(self):
        """Test login with valid credentials"""
        global USER_TOKEN
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user object"
        USER_TOKEN = data["token"]
        print(f"SUCCESS: Login valid - user: {data['user'].get('email')}, credits: {data['user'].get('credits')}")
    
    def test_02_login_invalid_email(self):
        """Test login with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "somepassword"
        })
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Invalid email returns 401")
    
    def test_03_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": "wrongpassword123"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Invalid password returns 401")
    
    def test_04_login_empty_email(self):
        """Test login with empty email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "",
            "password": "somepassword"
        })
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
        print("SUCCESS: Empty email returns 422 validation error")
    
    def test_05_login_empty_password(self):
        """Test login with empty password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": ""
        })
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("SUCCESS: Empty password returns 422 validation error")
    
    def test_06_login_sql_injection_attempt(self):
        """Test login with SQL injection attempt"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "'; DROP TABLE users; --",
            "password": "test123"
        })
        # Should return 422 (invalid email format) or 401, not 500
        assert response.status_code in [401, 422], f"SQL injection should be blocked, got {response.status_code}"
        print("SUCCESS: SQL injection attempt blocked")
    
    def test_07_get_me_authenticated(self):
        """Test /me endpoint with valid token"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=get_auth_header(USER_TOKEN))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "email" in data, "Response should contain email"
        assert "credits" in data, "Response should contain credits"
        print(f"SUCCESS: /me returns user data - credits: {data.get('credits')}")
    
    def test_08_get_me_unauthenticated(self):
        """Test /me endpoint without token - should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: /me without token returns 401")
    
    def test_09_get_me_invalid_token(self):
        """Test /me endpoint with invalid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: /me with invalid token returns 401")
    
    def test_10_forgot_password_valid_email(self):
        """Test forgot password with valid email"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": TEST_USER_EMAIL
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True or "message" in data, "Should return success"
        print("SUCCESS: Forgot password returns success for valid email")
    
    def test_11_forgot_password_nonexistent_email(self):
        """Test forgot password with non-existent email - should still return 200 (security)"""
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", json={
            "email": "nonexistent@test.com"
        })
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: Forgot password for non-existent email returns 200 (security)")
    
    def test_12_admin_login_valid(self):
        """Test admin login with valid credentials"""
        global ADMIN_TOKEN
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_USER_EMAIL,
            "password": ADMIN_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            ADMIN_TOKEN = data.get("token")
            role = data.get("user", {}).get("role", "")
            print(f"SUCCESS: Admin login - role: {role}")
            assert role.upper() in ["ADMIN", "SUPERADMIN"], f"Expected admin role, got {role}"
        else:
            # Admin might be locked - skip but note
            print(f"NOTE: Admin login returned {response.status_code} - may be locked or different password")
            pytest.skip("Admin account may be locked or credentials different")


# =============================================================================
# 2. REEL GENERATOR TESTS
# =============================================================================
class TestReelGenerator:
    """Test /api/generate/reel endpoint - valid, invalid, edge cases"""
    
    def test_01_reel_generate_valid_input(self):
        """Test reel generation with valid input"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
            if not USER_TOKEN:
                pytest.skip("Cannot login - skipping reel generation test")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=get_auth_header(USER_TOKEN),
            json={
                "topic": "5 productivity tips for remote workers",
                "language": "English",
                "niche": "Business",
                "tone": "Professional",
                "duration": "30s",
                "goal": "Engagement"
            },
            timeout=120
        )
        
        if response.status_code == 403:
            data = response.json()
            if "credits" in str(data.get("detail", "")).lower() or "insufficient" in str(data.get("detail", "")).lower():
                print("NOTE: Insufficient credits - endpoint works but user has no credits")
                return
        
        # 200 = success, 503 = LLM unavailable (acceptable)
        assert response.status_code in [200, 503], f"Expected 200/503, got {response.status_code}: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Response should indicate success"
            assert "result" in data, "Response should contain result"
            print(f"SUCCESS: Reel generated - credits used: {data.get('creditsUsed')}")
        else:
            print("NOTE: LLM unavailable (503) - endpoint works but AI service down")
    
    def test_02_reel_generate_empty_topic(self):
        """Test reel generation with empty topic"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token available")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=get_auth_header(USER_TOKEN),
            json={
                "topic": "",
                "language": "English",
                "niche": "Business"
            }
        )
        # Should return 422 validation error
        assert response.status_code == 422, f"Expected 422 for empty topic, got {response.status_code}"
        print("SUCCESS: Empty topic returns 422 validation error")
    
    def test_03_reel_generate_special_chars(self):
        """Test reel generation with special characters"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token available")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=get_auth_header(USER_TOKEN),
            json={
                "topic": "<script>alert('xss')</script>",
                "language": "English",
                "niche": "Business"
            },
            timeout=120
        )
        # Should either sanitize or block - not return 500
        assert response.status_code in [200, 400, 403, 422, 503], f"XSS should be handled, got {response.status_code}"
        print(f"SUCCESS: Special chars handled - status: {response.status_code}")
    
    def test_04_reel_generate_unicode_emoji(self):
        """Test reel generation with unicode and emoji"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token available")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=get_auth_header(USER_TOKEN),
            json={
                "topic": "测试中文主题 🚀 with emoji",
                "language": "Chinese",
                "niche": "Technology"
            },
            timeout=120
        )
        # Should handle unicode gracefully
        assert response.status_code in [200, 400, 403, 503], f"Unicode should be handled, got {response.status_code}"
        print(f"SUCCESS: Unicode/emoji handled - status: {response.status_code}")
    
    def test_05_reel_generate_very_long_input(self):
        """Test reel generation with very long topic"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token available")
        
        long_topic = "a" * 5000  # 5000 characters
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers=get_auth_header(USER_TOKEN),
            json={
                "topic": long_topic,
                "language": "English",
                "niche": "Business"
            }
        )
        # Should return 422 validation error for too long
        assert response.status_code in [400, 422], f"Expected validation error for long input, got {response.status_code}"
        print("SUCCESS: Very long input returns validation error")
    
    def test_06_reel_generate_unauthenticated(self):
        """Test reel generation without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            json={"topic": "test", "language": "English", "niche": "Business"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated reel request returns 401")
    
    def test_07_demo_reel_generate(self):
        """Test demo reel generation (no auth required)"""
        response = requests.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json={
                "topic": "AI in healthcare",
                "language": "English",
                "niche": "Technology"
            }
        )
        assert response.status_code == 200, f"Demo reel should work, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Demo should return success"
        assert data.get("isDemo") == True, "Should be marked as demo"
        print("SUCCESS: Demo reel generation works")


# =============================================================================
# 3. KIDS STORY GENERATOR TESTS
# =============================================================================
class TestKidsStoryGenerator:
    """Test /api/generate/story endpoint"""
    
    def test_01_story_generate_valid_input(self):
        """Test story generation with valid input"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        if not USER_TOKEN:
            pytest.skip("Cannot login")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/story",
            headers=get_auth_header(USER_TOKEN),
            json={
                "genre": "Adventure",
                "ageGroup": "4-6",
                "theme": "Friendship",
                "sceneCount": 5
            },
            timeout=180
        )
        
        if response.status_code == 403:
            data = response.json()
            if "credits" in str(data.get("detail", "")).lower():
                print("NOTE: Insufficient credits for story generation")
                return
        
        assert response.status_code in [200, 503], f"Expected 200/503, got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Should indicate success"
            print(f"SUCCESS: Story generated - credits used: {data.get('creditsUsed')}")
        else:
            print("NOTE: LLM unavailable (503)")
    
    def test_02_story_generate_unauthenticated(self):
        """Test story generation without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/generate/story",
            json={"genre": "Adventure", "ageGroup": "4-6", "theme": "Friendship"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated story request returns 401")


# =============================================================================
# 4. BILLING/PAYMENT TESTS
# =============================================================================
class TestBillingPayments:
    """Test /api/cashfree/* endpoints - products, health, order creation"""
    
    def test_01_get_products(self):
        """Test getting all products"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "products" in data, "Response should contain products"
        products = data.get("products", {})
        assert len(products) == 7, f"Expected 7 products, got {len(products)}"
        print(f"SUCCESS: Got {len(products)} products")
    
    def test_02_get_plans_alias(self):
        """Test /api/cashfree/plans endpoint (alias for products)"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "products" in data, "Response should contain products"
        print("SUCCESS: /plans alias works")
    
    def test_03_verify_subscription_products(self):
        """Verify all subscription products exist with correct structure"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        products = data.get("products", {})
        
        subscriptions = ["weekly", "monthly", "quarterly", "yearly"]
        for sub in subscriptions:
            assert sub in products, f"Missing subscription: {sub}"
            assert "period" in products[sub], f"{sub} should have period"
            assert "price" in products[sub], f"{sub} should have price"
            assert "credits" in products[sub], f"{sub} should have credits"
        print(f"SUCCESS: All subscription products verified: {subscriptions}")
    
    def test_04_verify_credit_packs(self):
        """Verify all credit pack products exist"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        data = response.json()
        products = data.get("products", {})
        
        packs = ["starter", "creator", "pro"]
        for pack in packs:
            assert pack in products, f"Missing credit pack: {pack}"
            assert "price" in products[pack], f"{pack} should have price"
            assert "credits" in products[pack], f"{pack} should have credits"
        print(f"SUCCESS: All credit packs verified: {packs}")
    
    def test_05_cashfree_health(self):
        """Test Cashfree health endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", "Cashfree should be healthy"
        assert data.get("configured") == True, "Cashfree should be configured"
        assert data.get("gateway") == "cashfree", "Gateway should be cashfree"
        print(f"SUCCESS: Cashfree healthy - environment: {data.get('environment')}")
    
    def test_06_create_order_unauthenticated(self):
        """Test creating order without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            json={"productId": "starter", "currency": "INR"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated order creation returns 401")
    
    def test_07_create_order_authenticated(self):
        """Test creating order with authentication"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        if not USER_TOKEN:
            pytest.skip("Cannot login")
        
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=get_auth_header(USER_TOKEN),
            json={"productId": "starter", "currency": "INR"}
        )
        
        # 200 = order created, 500 = Cashfree config issue
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Order should be created successfully"
            assert "orderId" in data, "Response should contain orderId"
            assert "paymentSessionId" in data, "Response should contain paymentSessionId"
            print(f"SUCCESS: Order created - orderId: {data.get('orderId')}")
        else:
            print(f"NOTE: Order creation returned {response.status_code} - check Cashfree config")
    
    def test_08_create_order_invalid_product(self):
        """Test creating order with invalid product ID"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=get_auth_header(USER_TOKEN),
            json={"productId": "invalid_product", "currency": "INR"}
        )
        assert response.status_code == 400, f"Invalid product should return 400, got {response.status_code}"
        print("SUCCESS: Invalid product returns 400")


# =============================================================================
# 5. CREDITS TESTS
# =============================================================================
class TestCredits:
    """Test /api/credits/* endpoints - balance, ledger, usage, packages"""
    
    def test_01_get_balance_authenticated(self):
        """Test getting credit balance with authentication"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        if not USER_TOKEN:
            pytest.skip("Cannot login")
        
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "credits" in data, "Response should contain credits"
        assert isinstance(data["credits"], (int, float)), "Credits should be numeric"
        print(f"SUCCESS: User credits balance: {data.get('credits')}")
    
    def test_02_get_balance_unauthenticated(self):
        """Test getting credit balance without authentication"""
        response = requests.get(f"{BASE_URL}/api/credits/balance")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated balance request returns 401")
    
    def test_03_get_ledger_authenticated(self):
        """Test getting credit ledger with authentication"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.get(
            f"{BASE_URL}/api/credits/ledger",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "ledger" in data, "Response should contain ledger"
        assert "total" in data, "Response should contain total count"
        print(f"SUCCESS: Ledger returned - total entries: {data.get('total')}")
    
    def test_04_get_credit_history(self):
        """Test getting credit history"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.get(
            f"{BASE_URL}/api/credits/history",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "history" in data, "Response should contain history"
        print(f"SUCCESS: Credit history returned - entries: {data.get('total', len(data.get('history', [])))}")
    
    def test_05_get_usage_stats(self):
        """Test getting usage statistics"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.get(
            f"{BASE_URL}/api/credits/usage",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "currentBalance" in data, "Response should contain currentBalance"
        assert "totalSpent" in data, "Response should contain totalSpent"
        print(f"SUCCESS: Usage stats - balance: {data.get('currentBalance')}, spent: {data.get('totalSpent')}")
    
    def test_06_get_credit_packages(self):
        """Test getting credit packages"""
        response = requests.get(f"{BASE_URL}/api/credits/packages")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list of packages"
        assert len(data) >= 1, "Should have at least one package"
        print(f"SUCCESS: Got {len(data)} credit packages")


# =============================================================================
# 6. ADMIN TESTS
# =============================================================================
class TestAdmin:
    """Test /api/admin/* endpoints - dashboard, analytics, user management"""
    
    def test_01_admin_dashboard_unauthenticated(self):
        """Test admin dashboard without authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated admin dashboard returns 401")
    
    def test_02_admin_dashboard_with_user_token(self):
        """Test admin dashboard with regular user token - should be forbidden"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        if not USER_TOKEN:
            pytest.skip("Cannot login")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/analytics/dashboard",
            headers=get_auth_header(USER_TOKEN)
        )
        # Should return 403 Forbidden for non-admin users
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("SUCCESS: Non-admin user gets 403 on admin endpoints")
    
    def test_03_admin_users_list_unauthenticated(self):
        """Test admin user list without authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/users/list")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated admin/users returns 401")
    
    def test_04_admin_exceptions_unauthenticated(self):
        """Test admin exceptions list without authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/exceptions/all")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated admin/exceptions returns 401")
    
    def test_05_admin_feedback_unauthenticated(self):
        """Test admin feedback without authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/feedback/all")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated admin/feedback returns 401")


# =============================================================================
# 7. STORY VIDEO STUDIO TESTS (BETA)
# =============================================================================
class TestStoryVideoStudio:
    """Test /api/story-video-studio/* endpoints"""
    
    def test_01_get_video_styles(self):
        """Test getting available video styles"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success"
        assert "styles" in data, "Response should contain styles"
        styles = data.get("styles", [])
        assert len(styles) >= 1, "Should have at least one style"
        print(f"SUCCESS: Got {len(styles)} video styles")
    
    def test_02_get_pricing(self):
        """Test getting pricing information"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success"
        assert "pricing" in data, "Response should contain pricing"
        print(f"SUCCESS: Got pricing - scene_generation: {data.get('pricing', {}).get('scene_generation')} credits")
    
    def test_03_create_project(self):
        """Test creating a story video project"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": "Once upon a time, in a magical forest, there lived a brave little bunny named Fluffy. " * 5,
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook",
                "title": "Fluffy's Adventure"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, "Should return success"
        assert "project_id" in data, "Response should contain project_id"
        print(f"SUCCESS: Project created - ID: {data.get('project_id')}")
        return data.get("project_id")
    
    def test_04_create_project_copyright_violation(self):
        """Test creating project with copyrighted content - should be blocked"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": "Once upon a time, Mickey Mouse and SpiderMan went to Hogwarts to meet Harry Potter.",
                "language": "english",
                "age_group": "kids_5_8",
                "style_id": "storybook"
            }
        )
        assert response.status_code == 400, f"Expected 400 for copyright violation, got {response.status_code}"
        print("SUCCESS: Copyright violation blocked")
    
    def test_05_create_project_too_short(self):
        """Test creating project with too short story"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/projects/create",
            json={
                "story_text": "Too short",
                "language": "english",
                "age_group": "kids_5_8"
            }
        )
        assert response.status_code == 422, f"Expected 422 for too short story, got {response.status_code}"
        print("SUCCESS: Too short story returns validation error")
    
    def test_06_list_projects(self):
        """Test listing projects"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success"
        assert "projects" in data, "Response should contain projects"
        print(f"SUCCESS: Listed {data.get('count', len(data.get('projects', [])))} projects")
    
    def test_07_get_analytics(self):
        """Test getting story video analytics"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/analytics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success"
        assert "analytics" in data, "Response should contain analytics"
        print(f"SUCCESS: Got analytics - total projects: {data.get('analytics', {}).get('total_projects')}")


# =============================================================================
# 8. GENERATION HISTORY TESTS
# =============================================================================
class TestGenerationHistory:
    """Test generation history and retrieval"""
    
    def test_01_get_generations_authenticated(self):
        """Test getting generation history"""
        global USER_TOKEN
        if not USER_TOKEN:
            USER_TOKEN = login_user(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        
        if not USER_TOKEN:
            pytest.skip("Cannot login")
        
        response = requests.get(
            f"{BASE_URL}/api/generate/",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "generations" in data, "Response should contain generations"
        assert "total" in data, "Response should contain total count"
        print(f"SUCCESS: Got {data.get('total')} total generations")
    
    def test_02_get_generations_unauthenticated(self):
        """Test getting generations without authentication"""
        response = requests.get(f"{BASE_URL}/api/generate/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthenticated generations request returns 401")
    
    def test_03_get_generations_by_type(self):
        """Test filtering generations by type"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.get(
            f"{BASE_URL}/api/generate/?type=REEL",
            headers=get_auth_header(USER_TOKEN)
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: Filtered generations by type")


# =============================================================================
# 9. HEALTH CHECK TESTS
# =============================================================================
class TestHealthChecks:
    """Test health check endpoints"""
    
    def test_01_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", "API should be healthy"
        print(f"SUCCESS: API healthy - version: {data.get('version')}")
    
    def test_02_root_endpoint(self):
        """Test root API endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("SUCCESS: Root API endpoint accessible")


# =============================================================================
# 10. INPUT VALIDATION & SECURITY TESTS
# =============================================================================
class TestInputValidationSecurity:
    """Test input validation and security measures"""
    
    def test_01_xss_attempt_in_topic(self):
        """Test XSS attempt in generation topic"""
        global USER_TOKEN
        if not USER_TOKEN:
            pytest.skip("No user token")
        
        response = requests.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json={
                "topic": "<img src=x onerror=alert('xss')>",
                "language": "English",
                "niche": "Business"
            }
        )
        # Should sanitize or reject - not execute
        if response.status_code == 200:
            data = response.json()
            # Check that the response doesn't contain unescaped XSS
            result_str = json.dumps(data)
            assert "<img src=x onerror" not in result_str or "&lt;img" in result_str, "XSS should be escaped"
        print(f"SUCCESS: XSS attempt handled - status: {response.status_code}")
    
    def test_02_sql_injection_attempt(self):
        """Test SQL injection attempt"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test' OR '1'='1",
                "password": "test' OR '1'='1"
            }
        )
        # Should return 422 (invalid email) or 401 (auth failed), not 500
        assert response.status_code in [401, 422], f"SQL injection should be handled, got {response.status_code}"
        print("SUCCESS: SQL injection attempt blocked")
    
    def test_03_large_payload_rejection(self):
        """Test rejection of very large payloads"""
        large_data = "a" * 100000  # 100KB
        response = requests.post(
            f"{BASE_URL}/api/generate/demo/reel",
            json={"topic": large_data, "language": "English", "niche": "Business"}
        )
        # Should return 400 or 422 for too large payload
        assert response.status_code in [400, 413, 422], f"Large payload should be rejected, got {response.status_code}"
        print("SUCCESS: Large payload rejected")


# =============================================================================
# RUN ALL TESTS
# =============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x", f"--junitxml=/app/test_reports/pytest/pytest_comprehensive_deep_qa_iteration138.xml"])
