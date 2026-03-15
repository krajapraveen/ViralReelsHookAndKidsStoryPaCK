"""
Comprehensive Dashboard Audit Tests - CreatorStudio AI
Tests all dashboard features, APIs, and integrations
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://progressive-pipeline.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"

class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Admin user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data["user"]["role"] == "ADMIN", f"Expected ADMIN role, got {data['user']['role']}"
        print(f"✓ Admin login successful - Role: {data['user']['role']}")

    def test_demo_user_login(self):
        """Demo user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        # Demo user might not exist
        if response.status_code == 401:
            pytest.skip("Demo user not registered")
        assert response.status_code == 200
        print("✓ Demo user login successful")

    def test_invalid_login(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Admin login failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestWalletAndCredits:
    """Wallet/Credits API tests"""
    
    def test_get_wallet_balance(self, admin_headers):
        """Get wallet balance returns credits"""
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=admin_headers)
        assert response.status_code == 200, f"Wallet API failed: {response.text}"
        data = response.json()
        assert "balanceCredits" in data or "balance" in data, "No balance in response"
        credits = data.get("balanceCredits") or data.get("balance", 0)
        print(f"✓ Wallet balance: {credits} credits")
        
    def test_get_wallet_pricing(self, admin_headers):
        """Get pricing data"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data, "No pricing data"
        print(f"✓ Pricing loaded: {len(data['pricing'])} items")


class TestGenStudio:
    """GenStudio AI endpoints"""
    
    def test_genstudio_templates(self, admin_headers):
        """GenStudio templates load"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=admin_headers)
        assert response.status_code == 200, f"Templates failed: {response.text}"
        data = response.json()
        assert "templates" in data or isinstance(data, list), "No templates"
        print("✓ GenStudio templates loaded")

    def test_genstudio_dashboard(self, admin_headers):
        """GenStudio dashboard data loads"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=admin_headers)
        assert response.status_code == 200
        print("✓ GenStudio dashboard data loaded")


class TestCreatorTools:
    """Creator Tools endpoints"""
    
    def test_hashtags_endpoint(self, admin_headers):
        """Get hashtags for niche"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/hashtags/business", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "hashtags" in data, "No hashtags returned"
        print("✓ Hashtag bank working")
        
    def test_thumbnail_text(self, admin_headers):
        """Generate thumbnail text"""
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/thumbnail-text?topic=productivity",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # API returns "ideas" instead of "thumbnails"
        assert "ideas" in data or "thumbnails" in data, "No thumbnail ideas returned"
        print("✓ Thumbnail text generation working")


class TestColoringBook:
    """Coloring Book endpoints"""
    
    def test_coloring_book_pricing(self, admin_headers):
        """Get coloring book pricing"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "creditPricing" in data or "pricing" in data
        print("✓ Coloring book pricing loaded")
        
    def test_coloring_book_stories(self, admin_headers):
        """Get available stories"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/stories", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stories" in data
        print(f"✓ Coloring book stories: {len(data['stories'])} available")


class TestStorySeries:
    """Story Series endpoints"""
    
    def test_story_series_pricing(self, admin_headers):
        """Get story series pricing"""
        response = requests.get(f"{BASE_URL}/api/story-series/pricing", headers=admin_headers)
        assert response.status_code == 200
        print("✓ Story series pricing loaded")

    def test_story_series_themes(self, admin_headers):
        """Get available themes"""
        response = requests.get(f"{BASE_URL}/api/story-series/themes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        print(f"✓ Story series themes: {len(data['themes'])} available")


class TestChallengeGenerator:
    """Challenge Generator endpoints"""
    
    def test_challenge_pricing(self, admin_headers):
        """Get challenge pricing"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/pricing", headers=admin_headers)
        assert response.status_code == 200
        print("✓ Challenge generator pricing loaded")

    def test_challenge_niches(self, admin_headers):
        """Get available niches"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/niches", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        print(f"✓ Challenge niches loaded")

    def test_challenge_platforms(self, admin_headers):
        """Get supported platforms"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/platforms", headers=admin_headers)
        assert response.status_code == 200
        print("✓ Challenge platforms loaded")

    def test_challenge_goals(self, admin_headers):
        """Get available goals"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/goals", headers=admin_headers)
        assert response.status_code == 200
        print("✓ Challenge goals loaded")


class TestToneSwitcher:
    """Tone Switcher endpoints"""
    
    def test_tone_pricing(self, admin_headers):
        """Get tone switcher pricing"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/pricing", headers=admin_headers)
        assert response.status_code == 200
        print("✓ Tone switcher pricing loaded")

    def test_tone_options(self, admin_headers):
        """Get available tones"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/tones", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tones" in data
        print(f"✓ Available tones: {list(data['tones'].keys())}")


class TestAdminDashboard:
    """Admin Dashboard endpoints"""
    
    def test_admin_stats(self, admin_headers):
        """Get admin dashboard stats"""
        # Try /api/admin/dashboard or /api/admin/stats
        response = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=admin_headers)
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers)
        # Admin endpoint might be at different path
        if response.status_code == 404:
            pytest.skip("Admin stats endpoint not found")
        assert response.status_code == 200
        print("✓ Admin stats loaded")

    def test_admin_users_list(self, admin_headers):
        """Get users list (admin only)"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"✓ Admin users list: {len(data['users'])} users")


class TestSubscriptions:
    """Subscription plans endpoints"""
    
    def test_get_plans(self, admin_headers):
        """Get subscription plans"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        print(f"✓ Subscription plans: {len(data['plans'])} available")


class TestProfileAndAuth:
    """Profile management endpoints"""
    
    def test_get_current_user(self, admin_headers):
        """Get current user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert data["email"] == ADMIN_EMAIL
        print(f"✓ Current user: {data['email']}")


class TestHealthAndInfrastructure:
    """Health checks and infrastructure"""
    
    def test_health_endpoint(self):
        """Health endpoint returns OK"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ Health endpoint OK")

    def test_cors_headers(self):
        """CORS headers present"""
        response = requests.options(f"{BASE_URL}/api/auth/login", headers={
            "Origin": "https://progressive-pipeline.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST"
        })
        # Should not be blocked
        assert response.status_code in [200, 204, 405]
        print("✓ CORS preflight handled")


class TestSecurityAccess:
    """Security and access control tests"""
    
    def test_protected_route_without_auth(self):
        """Protected routes require authentication"""
        response = requests.get(f"{BASE_URL}/api/wallet/me")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Protected routes require auth")

    def test_admin_route_with_non_admin(self):
        """Admin routes blocked for non-admin users"""
        # Try with demo user if available
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Demo user not available")
        
        token = login_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try /api/admin/users - should be blocked for non-admin
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        # If admin route returns 404, the endpoint may not exist - skip
        if response.status_code == 404:
            pytest.skip("Admin endpoint returns 404 - cannot test access control")
        assert response.status_code in [401, 403], f"Non-admin accessed admin route (got {response.status_code})"
        print("✓ Admin routes properly protected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
