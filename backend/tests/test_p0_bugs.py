"""
Test P0 Bugs:
1. Feedback submission - Submit feedback via widget and verify it appears on Admin Dashboard
2. Browser back button - Login as user, verify back button behavior (handled in frontend)

Also tests Admin Dashboard tabs functionality
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFeedbackSubmission:
    """P0 Bug 1: Test feedback submission and retrieval on Admin Dashboard"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]
    
    def test_submit_feedback_via_suggestion_endpoint(self):
        """Test POST /api/feedback/suggestion - the endpoint used by FeedbackWidget"""
        unique_id = str(uuid.uuid4())[:8]
        feedback_data = {
            "rating": 4,
            "category": "feature",
            "suggestion": f"TEST_FEEDBACK_{unique_id}: This is a test feature request",
            "email": f"test_{unique_id}@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/suggestion", json=feedback_data)
        
        # Status assertion
        assert response.status_code == 200, f"Feedback submission failed: {response.text}"
        
        # Data assertion
        data = response.json()
        assert data.get("success") == True
        assert "message" in data
        print(f"✓ Feedback submitted successfully: {data['message']}")
        
        return unique_id
    
    def test_feedback_appears_on_admin_dashboard(self, admin_token):
        """Test GET /api/admin/feedback/all - verify submitted feedback appears"""
        # First submit a unique feedback
        unique_id = str(uuid.uuid4())[:8]
        feedback_data = {
            "rating": 5,
            "category": "improvement",
            "suggestion": f"TEST_ADMIN_FEEDBACK_{unique_id}: Testing admin dashboard visibility",
            "email": f"admin_test_{unique_id}@example.com"
        }
        
        # Submit feedback
        submit_response = requests.post(f"{BASE_URL}/api/feedback/suggestion", json=feedback_data)
        assert submit_response.status_code == 200, f"Feedback submission failed: {submit_response.text}"
        
        # Now fetch all feedback as admin
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/feedback/all", headers=headers)
        
        # Status assertion
        assert response.status_code == 200, f"Admin feedback fetch failed: {response.text}"
        
        # Data assertion
        data = response.json()
        assert data.get("success") == True
        assert "feedback" in data
        assert "stats" in data
        
        # Verify our feedback is in the list
        feedback_list = data["feedback"]
        assert isinstance(feedback_list, list)
        
        # Find our submitted feedback
        found = False
        for fb in feedback_list:
            if f"TEST_ADMIN_FEEDBACK_{unique_id}" in fb.get("message", ""):
                found = True
                print(f"✓ Found submitted feedback in admin dashboard: {fb['message'][:50]}...")
                break
        
        assert found, f"Submitted feedback with ID {unique_id} not found in admin dashboard"
        
        # Verify stats
        stats = data["stats"]
        assert "total" in stats
        assert stats["total"] > 0
        print(f"✓ Admin dashboard shows {stats['total']} total feedback items")
    
    def test_feedback_stats_calculation(self, admin_token):
        """Test that feedback stats are calculated correctly"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/feedback/all", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        stats = data["stats"]
        assert "total" in stats
        assert "averageRating" in stats
        assert "byCategory" in stats
        
        print(f"✓ Feedback stats: total={stats['total']}, avgRating={stats['averageRating']}")
        print(f"✓ Categories: {stats['byCategory']}")


class TestAdminDashboardTabs:
    """Test all Admin Dashboard tabs work correctly"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    def test_admin_analytics_dashboard(self, admin_token):
        """Test GET /api/admin/analytics/dashboard - Overview tab data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard?days=30", headers=headers)
        
        assert response.status_code == 200, f"Admin analytics failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        
        analytics = data["data"]
        
        # Verify all expected sections exist
        expected_sections = ["overview", "visitors", "featureUsage", "payments", "satisfaction", "generations", "recentActivity"]
        for section in expected_sections:
            assert section in analytics, f"Missing section: {section}"
        
        # Verify overview data
        overview = analytics["overview"]
        assert "totalUsers" in overview
        assert "newUsers" in overview
        assert "totalGenerations" in overview
        assert "totalRevenue" in overview
        
        print(f"✓ Admin dashboard analytics loaded successfully")
        print(f"  - Total Users: {overview['totalUsers']}")
        print(f"  - Total Generations: {overview['totalGenerations']}")
        print(f"  - Total Revenue: ₹{overview['totalRevenue']}")
    
    def test_feature_requests_analytics(self, admin_token):
        """Test GET /api/feature-requests/analytics - Feature Requests tab"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/feature-requests/analytics", headers=headers)
        
        assert response.status_code == 200, f"Feature requests analytics failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        
        print(f"✓ Feature requests analytics loaded successfully")
    
    def test_admin_requires_authentication(self):
        """Test that admin endpoints require authentication"""
        # Without token
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Admin endpoints correctly require authentication")
    
    def test_admin_requires_admin_role(self, demo_token):
        """Test that admin endpoints require ADMIN role"""
        # With demo user token (not admin)
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("✓ Admin endpoints correctly require ADMIN role")
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]


class TestUserLoginFlow:
    """Test user login flow for back button bug verification"""
    
    def test_admin_login(self):
        """Test admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Admin@123"
        })
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "ADMIN"
        assert data["user"]["email"] == "admin@creatorstudio.ai"
        
        print(f"✓ Admin login successful: {data['user']['name']}")
    
    def test_demo_user_login(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "USER"
        assert data["user"]["email"] == "demo@example.com"
        
        print(f"✓ Demo user login successful: {data['user']['name']}")
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_auth_me_endpoint(self):
        """Test GET /api/auth/me returns user info"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        token = login_response.json()["token"]
        
        # Then get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        
        data = response.json()
        assert data["email"] == "demo@example.com"
        assert "credits" in data
        
        print(f"✓ Auth me endpoint working: {data['name']} with {data['credits']} credits")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
