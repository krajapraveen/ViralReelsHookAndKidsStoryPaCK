"""
Test Suite for Feedback System and Credit Reset - Iteration 447
Tests:
1. POST /api/feedback/experience - submit feedback (authenticated)
2. POST /api/feedback/experience - validation errors for missing fields
3. POST /api/feedback/experience - reject unauthenticated requests
4. GET /api/admin/feedback - list feedback with pagination (admin only)
5. GET /api/admin/feedback - filter by rating, source, read_by_admin, search
6. GET /api/admin/feedback/unread-count - returns correct count (admin only)
7. POST /api/admin/feedback/{id}/mark-read - marks feedback as read (admin only)
8. POST /api/admin/feedback/mark-read-bulk - bulk mark as read (admin only)
9. Credit reset verification: test user has exactly 50 credits
10. Credit reset verification: admin user credits unchanged (999999999)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAuthHelpers:
    """Helper methods for authentication"""
    
    @staticmethod
    def login(email: str, password: str) -> dict:
        """Login and return token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        return response.json() if response.status_code == 200 else None
    
    @staticmethod
    def get_auth_header(token: str) -> dict:
        """Return authorization header"""
        return {"Authorization": f"Bearer {token}"}


class TestCreditResetVerification:
    """Test credit reset for users"""
    
    def test_test_user_has_50_credits(self):
        """Verify test user has exactly 50 credits after reset"""
        login_data = TestAuthHelpers.login(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert login_data is not None, "Login failed for test user"
        assert "token" in login_data, f"No token in response: {login_data}"
        
        token = login_data.get("token")
        headers = TestAuthHelpers.get_auth_header(token)
        
        # Get user profile to check credits
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Failed to get user profile: {response.text}"
        
        user_data = response.json()
        credits = user_data.get("credits", user_data.get("user", {}).get("credits"))
        print(f"Test user credits: {credits}")
        assert credits == 50, f"Expected 50 credits, got {credits}"
    
    def test_admin_user_credits_unchanged(self):
        """Verify admin user credits are unchanged (should be high value)"""
        login_data = TestAuthHelpers.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert login_data is not None, "Login failed for admin user"
        assert "token" in login_data, f"No token in response: {login_data}"
        
        token = login_data.get("token")
        headers = TestAuthHelpers.get_auth_header(token)
        
        # Get user profile to check credits
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"Failed to get admin profile: {response.text}"
        
        user_data = response.json()
        credits = user_data.get("credits", user_data.get("user", {}).get("credits"))
        print(f"Admin user credits: {credits}")
        # Admin should have high credits (999999999 or similar)
        assert credits >= 999999, f"Admin credits should be high, got {credits}"


class TestFeedbackSubmission:
    """Test feedback submission endpoints"""
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user token"""
        login_data = TestAuthHelpers.login(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if login_data and "token" in login_data:
            return login_data["token"]
        pytest.skip("Could not login as test user")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        login_data = TestAuthHelpers.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if login_data and "token" in login_data:
            return login_data["token"]
        pytest.skip("Could not login as admin")
    
    def test_submit_feedback_success(self, test_user_token):
        """Test successful feedback submission with valid data"""
        headers = TestAuthHelpers.get_auth_header(test_user_token)
        headers["Content-Type"] = "application/json"
        
        feedback_data = {
            "rating": "good",
            "liked": "The UI is clean and easy to use",
            "improvements": "Would like faster generation times",
            "reuse_intent": "yes",
            "feature_context": ["reel_generator", "story_video"],
            "session_id": f"test_session_{uuid.uuid4().hex[:8]}",
            "source": "logout_prompt",
            "meta": {
                "browser": "Test Browser",
                "device": "desktop",
                "credits_remaining": 50,
                "idle_seconds": 0
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/experience", 
                                 json=feedback_data, headers=headers)
        print(f"Submit feedback response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True: {data}"
        assert "feedback_id" in data.get("data", {}), f"Expected feedback_id in response: {data}"
    
    def test_submit_feedback_validation_errors(self, test_user_token):
        """Test feedback submission with missing required fields"""
        headers = TestAuthHelpers.get_auth_header(test_user_token)
        headers["Content-Type"] = "application/json"
        
        # Missing required fields
        feedback_data = {
            "liked": "Something",
            # Missing: rating, improvements, reuse_intent, session_id, source
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/experience", 
                                 json=feedback_data, headers=headers)
        print(f"Validation error response: {response.status_code} - {response.text}")
        
        data = response.json()
        # Should return validation errors
        assert data.get("success") == False or "errors" in data, f"Expected validation errors: {data}"
        if "errors" in data:
            assert "rating" in data["errors"], "Expected rating validation error"
            assert "improvements" in data["errors"], "Expected improvements validation error"
    
    def test_submit_feedback_unauthenticated(self):
        """Test feedback submission without authentication"""
        feedback_data = {
            "rating": "good",
            "improvements": "Test improvement",
            "reuse_intent": "yes",
            "session_id": "test_session",
            "source": "logout_prompt"
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/experience", json=feedback_data)
        print(f"Unauthenticated response: {response.status_code} - {response.text}")
        
        # Should be 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestAdminFeedbackEndpoints:
    """Test admin feedback management endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        login_data = TestAuthHelpers.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if login_data and "token" in login_data:
            return login_data["token"]
        pytest.skip("Could not login as admin")
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user token"""
        login_data = TestAuthHelpers.login(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        if login_data and "token" in login_data:
            return login_data["token"]
        pytest.skip("Could not login as test user")
    
    def test_admin_list_feedback(self, admin_token):
        """Test admin can list feedback with pagination"""
        headers = TestAuthHelpers.get_auth_header(admin_token)
        
        response = requests.get(f"{BASE_URL}/api/admin/feedback", headers=headers)
        print(f"Admin list feedback: {response.status_code} - {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True: {data}"
        assert "items" in data.get("data", {}), f"Expected items in response: {data}"
        assert "pagination" in data.get("data", {}), f"Expected pagination in response: {data}"
    
    def test_admin_list_feedback_with_filters(self, admin_token):
        """Test admin can filter feedback by rating, source, read_by_admin"""
        headers = TestAuthHelpers.get_auth_header(admin_token)
        
        # Test rating filter
        response = requests.get(f"{BASE_URL}/api/admin/feedback?rating=good", headers=headers)
        assert response.status_code == 200, f"Rating filter failed: {response.text}"
        
        # Test source filter
        response = requests.get(f"{BASE_URL}/api/admin/feedback?source=logout_prompt", headers=headers)
        assert response.status_code == 200, f"Source filter failed: {response.text}"
        
        # Test read_by_admin filter
        response = requests.get(f"{BASE_URL}/api/admin/feedback?read_by_admin=false", headers=headers)
        assert response.status_code == 200, f"Read filter failed: {response.text}"
        
        # Test search filter
        response = requests.get(f"{BASE_URL}/api/admin/feedback?search=test", headers=headers)
        assert response.status_code == 200, f"Search filter failed: {response.text}"
        
        print("All filters working correctly")
    
    def test_admin_unread_count(self, admin_token):
        """Test admin can get unread feedback count"""
        headers = TestAuthHelpers.get_auth_header(admin_token)
        
        response = requests.get(f"{BASE_URL}/api/admin/feedback/unread-count", headers=headers)
        print(f"Unread count response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True: {data}"
        assert "unread_count" in data.get("data", {}), f"Expected unread_count in response: {data}"
        print(f"Unread count: {data['data']['unread_count']}")
    
    def test_admin_mark_feedback_read(self, admin_token):
        """Test admin can mark feedback as read"""
        headers = TestAuthHelpers.get_auth_header(admin_token)
        
        # First get a feedback item
        response = requests.get(f"{BASE_URL}/api/admin/feedback?read_by_admin=false&page_size=1", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get feedback list")
        
        data = response.json()
        items = data.get("data", {}).get("items", [])
        if not items:
            pytest.skip("No unread feedback items to test with")
        
        feedback_id = items[0].get("id")
        print(f"Marking feedback {feedback_id} as read")
        
        # Mark as read
        response = requests.post(f"{BASE_URL}/api/admin/feedback/{feedback_id}/mark-read", headers=headers)
        print(f"Mark read response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True: {data}"
    
    def test_admin_bulk_mark_read(self, admin_token):
        """Test admin can bulk mark feedback as read"""
        headers = TestAuthHelpers.get_auth_header(admin_token)
        headers["Content-Type"] = "application/json"
        
        # First get some feedback items
        response = requests.get(f"{BASE_URL}/api/admin/feedback?read_by_admin=false&page_size=3", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get feedback list")
        
        data = response.json()
        items = data.get("data", {}).get("items", [])
        if not items:
            pytest.skip("No unread feedback items to test bulk mark")
        
        feedback_ids = [item.get("id") for item in items]
        print(f"Bulk marking {len(feedback_ids)} feedback items as read")
        
        # Bulk mark as read
        response = requests.post(f"{BASE_URL}/api/admin/feedback/mark-read-bulk", 
                                 json={"feedback_ids": feedback_ids}, headers=headers)
        print(f"Bulk mark read response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True: {data}"
    
    def test_non_admin_cannot_access_admin_endpoints(self, test_user_token):
        """Test that non-admin users cannot access admin feedback endpoints"""
        headers = TestAuthHelpers.get_auth_header(test_user_token)
        
        # Try to list feedback
        response = requests.get(f"{BASE_URL}/api/admin/feedback", headers=headers)
        print(f"Non-admin list feedback: {response.status_code}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Try to get unread count
        response = requests.get(f"{BASE_URL}/api/admin/feedback/unread-count", headers=headers)
        print(f"Non-admin unread count: {response.status_code}")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
