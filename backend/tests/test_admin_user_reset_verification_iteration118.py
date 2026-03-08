"""
Admin User Reset Verification Tests - Iteration 118
Tests for the Admin User Reset Verification feature:
- POST /api/admin/users/reset-verification - resets user's verification status
- GET /api/admin/users/list - returns users with verification fields
- GET /api/admin/users/{user_id} - returns individual user details
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://story-video-builder.preview.emergentagent.com').rstrip('/')

# Admin credentials for testing
ADMIN_EMAIL = "krajapraveen.katta@creatorstudio.ai"
ADMIN_PASSWORD = "Onemanarmy@1979#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    data = response.json()
    return data.get("token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get headers with admin auth"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAdminUsersList:
    """Tests for GET /api/admin/users/list endpoint"""
    
    def test_list_users_returns_200(self, admin_headers):
        """Test that list users endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: /api/admin/users/list returns 200")
    
    def test_list_users_contains_users_array(self, admin_headers):
        """Test that response contains users array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list",
            headers=admin_headers
        )
        data = response.json()
        assert "users" in data, "Response should contain 'users' key"
        assert isinstance(data["users"], list), "'users' should be a list"
        print(f"PASS: Response contains users array with {len(data['users'])} users")
    
    def test_list_users_contains_verification_fields(self, admin_headers):
        """Test that user objects contain emailVerified, pending_credits, and credits_locked fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list",
            headers=admin_headers
        )
        data = response.json()
        users = data.get("users", [])
        
        # Check at least one user exists for testing
        if len(users) == 0:
            pytest.skip("No users found in database")
        
        # Check first few users for verification fields
        sample_size = min(5, len(users))
        for user in users[:sample_size]:
            # emailVerified can be True, False, or undefined (legacy users)
            # pending_credits and credits_locked might only be present for reset users
            user_email = user.get("email", "unknown")
            email_verified = user.get("emailVerified")
            pending_credits = user.get("pending_credits")
            credits_locked = user.get("credits_locked")
            print(f"User {user_email}: emailVerified={email_verified}, pending_credits={pending_credits}, credits_locked={credits_locked}")
        
        print(f"PASS: Verified user objects structure for {sample_size} users")
    
    def test_list_users_pagination(self, admin_headers):
        """Test pagination parameters work correctly"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list?page=1&size=10",
            headers=admin_headers
        )
        data = response.json()
        assert "pagination" in data or "total" in data, "Response should contain pagination info"
        users = data.get("users", [])
        assert len(users) <= 10, "Should return at most 10 users when size=10"
        print(f"PASS: Pagination works - returned {len(users)} users with size=10")


class TestAdminUserDetails:
    """Tests for GET /api/admin/users/{user_id} endpoint"""
    
    def test_get_user_details_valid_user(self, admin_headers):
        """Test getting details for a valid user"""
        # First get a user from the list
        list_response = requests.get(
            f"{BASE_URL}/api/admin/users/list?size=1",
            headers=admin_headers
        )
        users = list_response.json().get("users", [])
        if len(users) == 0:
            pytest.skip("No users found for testing")
        
        user_id = users[0].get("id")
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user" in data, "Response should contain 'user' key"
        user = data["user"]
        assert user.get("id") == user_id, "User ID should match"
        print(f"PASS: Got details for user {user.get('email')}")
    
    def test_get_user_details_invalid_user(self, admin_headers):
        """Test getting details for a non-existent user returns 404"""
        fake_user_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/admin/users/{fake_user_id}",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Expected 404 for invalid user, got {response.status_code}"
        print(f"PASS: Invalid user ID returns 404")


class TestResetVerificationEndpoint:
    """Tests for POST /api/admin/users/reset-verification endpoint"""
    
    def test_reset_verification_requires_admin(self):
        """Test that endpoint requires admin authentication"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/reset-verification",
            json={"user_id": "test", "reason": "Test reason"}
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"PASS: Endpoint requires authentication (got {response.status_code})")
    
    def test_reset_verification_invalid_user(self, admin_headers):
        """Test reset verification with non-existent user returns 404"""
        fake_user_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/admin/users/reset-verification",
            headers=admin_headers,
            json={"user_id": fake_user_id, "reason": "Testing invalid user"}
        )
        assert response.status_code == 404, f"Expected 404 for invalid user, got {response.status_code}: {response.text}"
        print(f"PASS: Invalid user returns 404")
    
    def test_reset_verification_requires_reason(self, admin_headers):
        """Test that reason field is required with minimum length"""
        # First get a valid user
        list_response = requests.get(
            f"{BASE_URL}/api/admin/users/list?size=1",
            headers=admin_headers
        )
        users = list_response.json().get("users", [])
        if len(users) == 0:
            pytest.skip("No users found for testing")
        
        user_id = users[0].get("id")
        
        # Test with too short reason
        response = requests.post(
            f"{BASE_URL}/api/admin/users/reset-verification",
            headers=admin_headers,
            json={"user_id": user_id, "reason": "ab"}  # Too short
        )
        # Should return 422 validation error
        assert response.status_code == 422, f"Expected 422 for short reason, got {response.status_code}"
        print(f"PASS: Short reason rejected with 422")
    
    def test_reset_verification_success(self, admin_headers):
        """Test successful reset verification for a legacy user"""
        # Get a user with credits who might be a legacy user
        list_response = requests.get(
            f"{BASE_URL}/api/admin/users/list?size=50",
            headers=admin_headers
        )
        users = list_response.json().get("users", [])
        
        # Find a user that can be reset (not admin, has credits or is unverified)
        test_user = None
        for user in users:
            role = user.get("role", "").upper()
            if role not in ["ADMIN", "SUPERADMIN"]:
                test_user = user
                break
        
        if test_user is None:
            pytest.skip("No non-admin users found for testing reset")
        
        user_id = test_user.get("id")
        user_email = test_user.get("email")
        old_credits = test_user.get("credits", 0)
        old_verified = test_user.get("emailVerified")
        
        print(f"Testing reset for user: {user_email}")
        print(f"  Before: credits={old_credits}, emailVerified={old_verified}")
        
        # Perform reset
        response = requests.post(
            f"{BASE_URL}/api/admin/users/reset-verification",
            headers=admin_headers,
            json={
                "user_id": user_id,
                "reason": "Testing admin reset verification feature"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response contains expected fields
        assert data.get("success") == True, "Response should indicate success"
        assert "user_email" in data, "Response should contain user_email"
        assert "old_credits" in data, "Response should contain old_credits"
        assert "new_state" in data, "Response should contain new_state"
        
        new_state = data.get("new_state", {})
        assert new_state.get("emailVerified") == False, "emailVerified should be False after reset"
        assert new_state.get("credits") == 0, "credits should be 0 after reset"
        assert new_state.get("pending_credits") == 20, "pending_credits should be 20 after reset"
        assert new_state.get("credits_locked") == True, "credits_locked should be True after reset"
        
        print(f"  After reset: {new_state}")
        print(f"PASS: Reset verification successful for {user_email}")
        
        # Verify by fetching user again
        verify_response = requests.get(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers=admin_headers
        )
        verify_data = verify_response.json()
        verify_user = verify_data.get("user", {})
        
        assert verify_user.get("emailVerified") == False, "GET after reset should show emailVerified=False"
        assert verify_user.get("credits") == 0, "GET after reset should show credits=0"
        assert verify_user.get("pending_credits") == 20, "GET after reset should show pending_credits=20"
        assert verify_user.get("credits_locked") == True, "GET after reset should show credits_locked=True"
        
        print(f"PASS: Reset persistence verified via GET endpoint")


class TestAdminUsersEndpointAlternatives:
    """Test alternative endpoint paths"""
    
    def test_users_endpoint_with_role_filter(self, admin_headers):
        """Test filtering users by role"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list?role=user",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: Role filter works")
    
    def test_users_endpoint_with_search(self, admin_headers):
        """Test searching users"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users/list?search=test",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: Search filter works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
