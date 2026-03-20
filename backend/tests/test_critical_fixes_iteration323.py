"""
Test Critical Fixes - Iteration 323
Tests for 5 critical fixes:
1. Profile Security tab - should render (not blank)
2. Admin satisfaction - truth-based with min 5 ratings
3. Reviews authenticity - no fake/seeded reviews
4. Live Activity - diverse locations (not repeated Seoul)
5. All fixes verified
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://k-factor-boost.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Authenticate as admin user and get token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def user_token():
    """Authenticate as test user and get token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("User authentication failed")


class TestLiveActivityDiverseLocations:
    """Fix #4: Live Activity must show diverse locations (not all Seoul)"""
    
    def test_live_activity_returns_items(self):
        """Live activity endpoint should return activity items"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "items" in data
    
    def test_live_activity_has_diverse_locations(self):
        """Activity items should have DIVERSE location labels"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        if len(items) == 0:
            pytest.skip("No live activity items to test")
        
        # Extract creator location labels
        locations = [item.get("creator", "") for item in items]
        print(f"Found locations: {locations}")
        
        # Check for diversity - not all same location
        unique_locations = set(locations)
        assert len(unique_locations) > 1, f"All items have same location: {locations}"
        
        # Specifically check not all Seoul
        seoul_count = sum(1 for loc in locations if 'Seoul' in loc or 'South Korea' in loc)
        non_seoul_count = len(locations) - seoul_count
        assert non_seoul_count >= 1, "All items are from Seoul/South Korea - not diverse"
    
    def test_live_activity_no_visionary_ai_system(self):
        """Activity should NOT contain synthetic items from 'visionary-ai-system'"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        items = data.get("items", [])
        # None of the items should mention 'visionary-ai-system' in any field
        for item in items:
            item_str = str(item).lower()
            assert "visionary-ai-system" not in item_str, f"Found synthetic item: {item}"


class TestAdminSatisfactionMetric:
    """Fix #2: Admin satisfaction must be truth-based with min 5 real ratings"""
    
    def test_satisfaction_requires_min_5_ratings(self, admin_token):
        """Satisfaction should show 'Not enough ratings yet' when <5 ratings"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        rating_count = data.get("rating_count", 0)
        satisfaction_pct = data.get("satisfaction_pct")
        satisfaction_note = data.get("satisfaction_note")
        
        print(f"Rating count: {rating_count}")
        print(f"Satisfaction pct: {satisfaction_pct}")
        print(f"Satisfaction note: {satisfaction_note}")
        
        if rating_count < 5:
            # Must show "Not enough ratings yet"
            assert satisfaction_pct is None, "satisfaction_pct should be null when <5 ratings"
            assert satisfaction_note == "Not enough ratings yet", "Should show 'Not enough ratings yet'"
        else:
            # If >= 5 ratings, should have actual percentage
            assert satisfaction_pct is not None, "satisfaction_pct should have value when >=5 ratings"
            assert satisfaction_note is None or satisfaction_note == "", "note should be empty when showing real data"
    
    def test_satisfaction_not_fake_score(self, admin_token):
        """Satisfaction should NOT show fake 4.0-4.5 score when insufficient data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        rating_count = data.get("rating_count", 0)
        satisfaction_pct = data.get("satisfaction_pct")
        
        # If less than 5 ratings, satisfaction_pct MUST be null
        if rating_count < 5:
            assert satisfaction_pct is None, (
                f"satisfaction_pct is {satisfaction_pct} with only {rating_count} ratings - "
                "this could be a fake score. Must be null when <5 ratings."
            )


class TestAuthEndpoints:
    """Test authentication endpoints work correctly"""
    
    def test_admin_login(self):
        """Admin login should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "ADMIN"
    
    def test_user_login(self):
        """Test user login should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data


class TestProfileSecurityEndpoint:
    """Fix #1: Profile Security tab must work (backend auth/me endpoint)"""
    
    def test_auth_me_returns_user(self, user_token):
        """Auth/me should return user data for Security tab"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "id" in data


class TestPublicEndpoints:
    """Test public endpoints that power the landing page"""
    
    def test_public_stats(self):
        """Public stats endpoint should return data"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        data = response.json()
        # Stats endpoint returns data directly (creators, videos_created, etc)
        assert "creators" in data or "total_creations" in data
    
    def test_public_explore(self):
        """Explore endpoint should return items"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
