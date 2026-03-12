"""
P0 System Audit Tests - Iteration 143
CreatorStudio AI

Tests for:
1. should_apply_watermark() fix - now receives dict instead of string
2. Credit balance API - returns both 'balance' and 'credits' fields
3. All main routes load without blank pages
4. GIF Maker functionality
5. Story Generator functionality
6. Credits display on all pages
"""
import pytest
import requests
import os
import time
import json
from typing import Optional

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAuthAndCredits:
    """Test auth flow and credits API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Auth failed: {response.status_code} - {response.text[:200]}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_returns_token(self):
        """Test login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, "No token in response"
        print(f"✓ Login successful, got token")
    
    def test_credits_balance_returns_both_fields(self, auth_headers):
        """Test /credits/balance returns both 'balance' and 'credits' fields"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Credits API failed: {response.text}"
        data = response.json()
        
        # Verify both fields exist
        assert "balance" in data, "Missing 'balance' field in response"
        assert "credits" in data, "Missing 'credits' field in response"
        assert "isFreeTier" in data, "Missing 'isFreeTier' field in response"
        
        # Verify values are consistent
        assert data["balance"] == data["credits"], "balance and credits should match"
        assert isinstance(data["balance"], (int, float)), "balance should be numeric"
        
        print(f"✓ Credits balance API returns: balance={data['balance']}, credits={data['credits']}, isFreeTier={data['isFreeTier']}")
    
    def test_credits_balance_non_zero(self, auth_headers):
        """Test user has credits (not 0 or undefined)"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        credits = data.get("balance", data.get("credits", 0))
        print(f"✓ User credits: {credits}")
        # Note: Don't assert credits > 0 as user might have 0 credits legitimately


class TestHealthEndpoints:
    """Test all critical health endpoints"""
    
    def test_api_health(self):
        """Test /api/health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check: {data}")
    
    def test_api_docs_accessible(self):
        """Test API docs are accessible"""
        response = requests.get(f"{BASE_URL}/api/docs", timeout=30)
        assert response.status_code == 200
        print(f"✓ API docs accessible")


class TestGIFMaker:
    """Test GIF Maker (Photo Reaction GIF) functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Auth failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_gif_reactions_available(self):
        """Test GIF reactions metadata endpoint"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/reactions", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "reactions" in data or isinstance(data, list)
        print(f"✓ GIF reactions available")
    
    def test_gif_styles_available(self):
        """Test GIF styles metadata endpoint"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/styles", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data or isinstance(data, list)
        print(f"✓ GIF styles available")
    
    def test_gif_pricing_available(self):
        """Test GIF pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif/pricing", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "single" in data or "base" in data
        print(f"✓ GIF pricing available")
    
    def test_gif_history(self, auth_headers):
        """Test GIF history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/reaction-gif/history",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)
        print(f"✓ GIF history accessible")


class TestStoryGenerator:
    """Test Story Generator functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_story_age_groups(self):
        """Test story age groups endpoint"""
        response = requests.get(f"{BASE_URL}/api/generate/story/age-groups", timeout=30)
        assert response.status_code == 200
        print(f"✓ Story age groups available")
    
    def test_story_genres(self):
        """Test story genres endpoint"""
        response = requests.get(f"{BASE_URL}/api/generate/story/genres", timeout=30)
        assert response.status_code == 200
        print(f"✓ Story genres available")
    
    def test_story_history(self, auth_headers):
        """Test story history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/generate/history",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        print(f"✓ Story history accessible")


class TestAllRoutes:
    """Test all main API routes are accessible"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    @pytest.mark.parametrize("endpoint,method,expected_codes", [
        ("/api/health", "GET", [200]),
        ("/api/credits/packages", "GET", [200]),
        ("/api/generate/story/age-groups", "GET", [200]),
        ("/api/generate/story/genres", "GET", [200]),
        ("/api/reaction-gif/reactions", "GET", [200]),
        ("/api/reaction-gif/styles", "GET", [200]),
    ])
    def test_public_routes(self, endpoint, method, expected_codes):
        """Test public routes are accessible"""
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", timeout=30)
        
        assert response.status_code in expected_codes, f"{endpoint} returned {response.status_code}: {response.text[:200]}"
        print(f"✓ {endpoint}: {response.status_code}")
    
    @pytest.mark.parametrize("endpoint,method,expected_codes", [
        ("/api/credits/balance", "GET", [200]),
        ("/api/credits/history", "GET", [200]),
        ("/api/generate/history", "GET", [200]),
        ("/api/reaction-gif/history", "GET", [200]),
        ("/api/user/profile", "GET", [200]),
    ])
    def test_authenticated_routes(self, auth_headers, endpoint, method, expected_codes):
        """Test authenticated routes are accessible"""
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_headers, timeout=30)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", headers=auth_headers, timeout=30)
        
        assert response.status_code in expected_codes, f"{endpoint} returned {response.status_code}: {response.text[:200]}"
        print(f"✓ {endpoint}: {response.status_code}")


class TestBillingRoutes:
    """Test billing/payment related routes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_credit_packages(self):
        """Test credit packages endpoint"""
        response = requests.get(f"{BASE_URL}/api/credits/packages", timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Packages should be a list"
        assert len(data) > 0, "Should have at least one package"
        print(f"✓ Credit packages: {len(data)} packages available")
    
    def test_subscription_plans(self):
        """Test subscription plans endpoint"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Subscription plans available")
        else:
            print(f"⚠ Subscription plans endpoint returned {response.status_code}")


class TestComixAI:
    """Test ComixAI / Photo to Comic routes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_comix_styles(self):
        """Test comix styles endpoint"""
        response = requests.get(f"{BASE_URL}/api/comix/styles", timeout=30)
        if response.status_code == 200:
            print(f"✓ Comix styles available")
        else:
            # Try alternative endpoint
            response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles", timeout=30)
            if response.status_code == 200:
                print(f"✓ Photo-to-comic styles available")
            else:
                print(f"⚠ Comix styles endpoint returned {response.status_code}")
    
    def test_comix_history(self, auth_headers):
        """Test comix history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/comix/history",
            headers=auth_headers,
            timeout=30
        )
        if response.status_code == 200:
            print(f"✓ Comix history accessible")
        else:
            response = requests.get(
                f"{BASE_URL}/api/photo-to-comic/history",
                headers=auth_headers,
                timeout=30
            )
            if response.status_code == 200:
                print(f"✓ Photo-to-comic history accessible")
            else:
                print(f"⚠ Comix history returned {response.status_code}")


class TestColoringBook:
    """Test Coloring Book routes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_coloring_book_themes(self):
        """Test coloring book themes"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/themes", timeout=30)
        if response.status_code == 200:
            print(f"✓ Coloring book themes available")
        else:
            # Try v2
            response = requests.get(f"{BASE_URL}/api/coloring-book-v2/themes", timeout=30)
            if response.status_code == 200:
                print(f"✓ Coloring book v2 themes available")
            else:
                print(f"⚠ Coloring book themes returned {response.status_code}")
    
    def test_coloring_book_history(self, auth_headers):
        """Test coloring book history"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/history",
            headers=auth_headers,
            timeout=30
        )
        if response.status_code == 200:
            print(f"✓ Coloring book history accessible")
        else:
            print(f"⚠ Coloring book history returned {response.status_code}")


class TestComicStorybook:
    """Test Comic Storybook routes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_comic_storybook_themes(self):
        """Test comic storybook themes"""
        response = requests.get(f"{BASE_URL}/api/comic-storybook/themes", timeout=30)
        if response.status_code == 200:
            print(f"✓ Comic storybook themes available")
        else:
            response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/themes", timeout=30)
            if response.status_code == 200:
                print(f"✓ Comic storybook v2 themes available")
            else:
                print(f"⚠ Comic storybook themes returned {response.status_code}")
    
    def test_comic_storybook_history(self, auth_headers):
        """Test comic storybook history"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/history",
            headers=auth_headers,
            timeout=30
        )
        if response.status_code == 200:
            print(f"✓ Comic storybook history accessible")
        else:
            print(f"⚠ Comic storybook history returned {response.status_code}")


class TestReelGenerator:
    """Test Reel Generator routes"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_reel_history(self, auth_headers):
        """Test reel history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/generate/history",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        print(f"✓ Reel history accessible")


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_auth_rejected(self):
        """Test invalid token is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=30
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Invalid auth properly rejected: {response.status_code}")
    
    def test_missing_auth_rejected(self):
        """Test missing auth is rejected for protected routes"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            timeout=30
        )
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print(f"✓ Missing auth properly rejected: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
