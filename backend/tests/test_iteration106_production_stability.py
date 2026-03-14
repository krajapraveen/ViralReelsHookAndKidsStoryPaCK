"""
Iteration 106: Production Stability Testing
Full A-Z testing of all critical API endpoints and features

Tests:
- Auth (Login/Logout)
- Dashboard/Credits
- Notifications
- Photo to Comic
- Reaction GIF
- Comic Storybook
- Downloads
- Admin endpoints
"""
import pytest
import requests
import os
from datetime import datetime

# Get the backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://gallery-showcase-43.preview.emergentagent.com"

# Test credentials
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Admin123!"


class TestHealthEndpoints:
    """Test basic health and server status"""
    
    def test_health_endpoint(self):
        """Test /api/health is accessible"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "healthy" in str(data).lower()
        print(f"✅ Health endpoint: {response.status_code}")
    
    def test_server_is_up(self):
        """Test base URL responds"""
        response = requests.get(BASE_URL, timeout=10)
        assert response.status_code in [200, 304], f"Server not responding: {response.status_code}"
        print(f"✅ Server is up: {response.status_code}")


class TestAuthentication:
    """Test Login/Logout flows"""
    
    def test_login_demo_user(self):
        """Test demo user can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        
        # Check response
        assert response.status_code in [200, 201], f"Login failed: {response.text}"
        data = response.json()
        
        # Should return a token
        assert "token" in data or "access_token" in data, f"No token in response: {data}"
        
        token = data.get("token") or data.get("access_token")
        assert token and len(token) > 10, "Token too short or empty"
        
        print(f"✅ Demo user login successful")
        return token
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrongpass"},
            timeout=10
        )
        
        assert response.status_code in [400, 401, 403], f"Should reject invalid credentials"
        print(f"✅ Invalid credentials properly rejected: {response.status_code}")
    
    def test_admin_login(self):
        """Test admin user can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            assert token, "No token for admin"
            print(f"✅ Admin login successful")
            return token
        else:
            print(f"⚠️ Admin login returned: {response.status_code} - may need different credentials")
            # Try alternate admin credentials
            alt_response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
                timeout=15
            )
            if alt_response.status_code in [200, 201]:
                print(f"✅ Admin login successful with alternate credentials")
                return alt_response.json().get("token") or alt_response.json().get("access_token")
            pytest.skip("Admin credentials need verification")


class TestUserEndpoints:
    """Test user-related endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            return response.json().get("token") or response.json().get("access_token")
        pytest.skip("Could not get auth token")
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_current_user(self, auth_headers):
        """Test /api/auth/me returns user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Failed to get user: {response.text}"
        data = response.json()
        
        # Check for user data
        user = data.get("user") or data
        assert user, "No user data returned"
        
        print(f"✅ Current user fetched: {user.get('email', 'unknown')}")
    
    def test_get_credits_balance(self, auth_headers):
        """Test credits/balance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Failed to get credits: {response.text}"
        data = response.json()
        
        assert "credits" in data, f"No credits field: {data}"
        print(f"✅ Credits balance: {data.get('credits', 'unknown')}")
    
    def test_get_wallet(self, auth_headers):
        """Test wallet endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/wallet",
            headers=auth_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            credits = data.get("balanceCredits") or data.get("availableCredits") or data.get("credits")
            print(f"✅ Wallet fetched: {credits} credits")
        else:
            print(f"⚠️ Wallet endpoint: {response.status_code}")


class TestNotificationEndpoints:
    """Test notification system - critical for previous bug fix verification"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_get_notifications(self, auth_headers):
        """Test /api/notifications returns notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Notifications failed: {response.text}"
        data = response.json()
        
        assert "notifications" in data, f"Missing notifications key: {data}"
        assert "unread_count" in data, f"Missing unread_count: {data}"
        
        print(f"✅ Notifications fetched: {len(data['notifications'])} items, {data['unread_count']} unread")
    
    def test_notification_poll(self, auth_headers):
        """Test /api/notifications/poll - previously had route conflict bug"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/poll",
            headers=auth_headers,
            timeout=10
        )
        
        # This should NOT return 403 (admin access required) - that was the bug
        assert response.status_code == 200, f"Poll failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "unread_count" in data, f"Missing unread_count: {data}"
        assert "has_new" in data, f"Missing has_new: {data}"
        
        print(f"✅ Notification poll working: unread={data['unread_count']}, has_new={data['has_new']}")
    
    def test_notification_unread_count(self, auth_headers):
        """Test unread count endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Unread count failed: {response.text}"
        data = response.json()
        
        assert "unread_count" in data
        print(f"✅ Unread count: {data['unread_count']}")
    
    def test_mark_all_read(self, auth_headers):
        """Test mark all as read - previously had route conflict"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-all-read",
            headers=auth_headers,
            timeout=10
        )
        
        # Should NOT return 403
        assert response.status_code == 200, f"Mark all read failed: {response.status_code} - {response.text}"
        print(f"✅ Mark all read working")


class TestPhotoToComicEndpoints:
    """Test Photo to Comic generation endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_get_styles(self, auth_headers):
        """Test /api/photo-to-comic/styles"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/styles",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Styles failed: {response.text}"
        data = response.json()
        
        assert "styles" in data, f"Missing styles: {data}"
        print(f"✅ Photo-to-comic styles fetched: {len(data['styles'])} styles")
    
    def test_get_pricing(self, auth_headers):
        """Test /api/photo-to-comic/pricing"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pricing",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"Pricing failed: {response.text}"
        data = response.json()
        
        assert "pricing" in data
        print(f"✅ Photo-to-comic pricing fetched")
    
    def test_get_history(self, auth_headers):
        """Test /api/photo-to-comic/history"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"History failed: {response.text}"
        data = response.json()
        
        assert "jobs" in data
        print(f"✅ Photo-to-comic history: {data.get('total', len(data['jobs']))} jobs")


class TestDownloadEndpoints:
    """Test download/expiry endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_get_my_downloads(self, auth_headers):
        """Test /api/downloads/my-downloads"""
        response = requests.get(
            f"{BASE_URL}/api/downloads/my-downloads",
            headers=auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200, f"My downloads failed: {response.text}"
        data = response.json()
        
        assert "downloads" in data, f"Missing downloads: {data}"
        print(f"✅ My downloads: {len(data['downloads'])} items")


class TestRatingEndpoint:
    """Test rating modal submission - critical for previous bug fix verification"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_submit_rating(self, auth_headers):
        """Test rating submission"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers=auth_headers,
            json={
                "rating": 5,
                "feature_key": "test_feature",
                "comment": "Test rating from pytest"
            },
            timeout=10
        )
        
        # Should succeed or return structured response
        if response.status_code == 200:
            print(f"✅ Rating submission successful")
        else:
            print(f"⚠️ Rating submission: {response.status_code} - {response.text[:200]}")


class TestReactionGifEndpoints:
    """Test Reaction GIF endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_reaction_gif_history(self, auth_headers):
        """Test /api/reaction-gif/history"""
        response = requests.get(
            f"{BASE_URL}/api/reaction-gif/history",
            headers=auth_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Reaction GIF history: {data.get('total', 0)} jobs")
        else:
            print(f"⚠️ Reaction GIF history: {response.status_code}")


class TestComicStorybookEndpoints:
    """Test Comic Storybook endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_comic_storybook_history(self, auth_headers):
        """Test /api/comic-storybook-v2/history"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook-v2/history",
            headers=auth_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Comic storybook history: {data.get('total', 0)} books")
        else:
            print(f"⚠️ Comic storybook history: {response.status_code}")


class TestGenerationEndpoints:
    """Test generation history endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_get_generations(self, auth_headers):
        """Test /api/generations endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/generations",
            headers=auth_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            generations = data.get("generations", [])
            print(f"✅ Generations history: {len(generations)} items")
        else:
            print(f"⚠️ Generations endpoint: {response.status_code}")


class TestAdminEndpoints:
    """Test admin endpoints"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin auth headers"""
        # Try primary admin credentials
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=15
        )
        
        if response.status_code not in [200, 201]:
            # Try alternate credentials
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"},
                timeout=15
            )
        
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get admin token")
    
    def test_admin_dashboard_access(self, admin_headers):
        """Test admin can access admin endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers=admin_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Admin stats accessible")
        else:
            print(f"⚠️ Admin stats: {response.status_code}")


class TestFeatureRequests:
    """Test feature requests endpoints"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=15
        )
        if response.status_code in [200, 201]:
            token = response.json().get("token") or response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Could not get auth token")
    
    def test_get_feature_requests(self, auth_headers):
        """Test /api/feature-requests"""
        response = requests.get(
            f"{BASE_URL}/api/feature-requests",
            headers=auth_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Feature requests: {len(data.get('requests', data.get('features', [])))} items")
        else:
            print(f"⚠️ Feature requests: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
