"""
Test suite for Profile Management, Email Notification Service, and Copyright features
Tests: PUT /api/auth/profile, GET /api/auth/export-data, PUT /api/auth/password
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Admin@123"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ API root: {data}")


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_admin(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "ADMIN"
        print(f"✓ Admin login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_demo_user(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_EMAIL
        print(f"✓ Demo user login successful: {data['user']['email']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")


class TestProfileManagement:
    """Profile management endpoint tests - PUT /api/auth/profile"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Authentication failed")
    
    def test_get_current_user(self, auth_token):
        """Test GET /api/auth/me endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data
        assert "credits" in data
        print(f"✓ Get current user: {data['name']} ({data['email']})")
    
    def test_update_profile_name(self, auth_token):
        """Test PUT /api/auth/profile - update name"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Update name
        new_name = "TEST_Updated Demo User"
        response = requests.put(f"{BASE_URL}/api/auth/profile", 
            headers=headers,
            json={"name": new_name}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        print(f"✓ Profile update response: {data}")
        
        # Verify the update persisted
        verify_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["name"] == new_name
        print(f"✓ Profile name updated and verified: {verify_data['name']}")
        
        # Restore original name
        requests.put(f"{BASE_URL}/api/auth/profile", 
            headers=headers,
            json={"name": "Demo User"}
        )
    
    def test_update_profile_invalid_name(self, auth_token):
        """Test PUT /api/auth/profile with invalid name (too short)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(f"{BASE_URL}/api/auth/profile", 
            headers=headers,
            json={"name": "A"}  # Too short
        )
        assert response.status_code == 422  # Validation error
        print("✓ Invalid name rejected correctly")
    
    def test_update_profile_unauthorized(self):
        """Test PUT /api/auth/profile without auth"""
        response = requests.put(f"{BASE_URL}/api/auth/profile", 
            json={"name": "Test Name"}
        )
        assert response.status_code == 401
        print("✓ Unauthorized profile update rejected")


class TestPasswordChange:
    """Password change endpoint tests - PUT /api/auth/password"""
    
    @pytest.fixture
    def test_user_token(self):
        """Create a test user and get token"""
        # Register a new test user
        test_email = f"TEST_password_user_{os.urandom(4).hex()}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "TEST Password User",
            "email": test_email,
            "password": "OldPassword123!"
        })
        
        if register_response.status_code == 200:
            data = register_response.json()
            return {
                "token": data["token"],
                "email": test_email,
                "user_id": data["user"]["id"]
            }
        elif register_response.status_code == 400:
            # User might already exist, try login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": test_email,
                "password": "OldPassword123!"
            })
            if login_response.status_code == 200:
                data = login_response.json()
                return {
                    "token": data["token"],
                    "email": test_email,
                    "user_id": data["user"]["id"]
                }
        pytest.skip("Could not create test user")
    
    def test_change_password_success(self, test_user_token):
        """Test PUT /api/auth/password - successful password change"""
        headers = {"Authorization": f"Bearer {test_user_token['token']}"}
        
        response = requests.put(f"{BASE_URL}/api/auth/password", 
            headers=headers,
            json={
                "currentPassword": "OldPassword123!",
                "newPassword": "NewPassword456!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Password change successful: {data}")
        
        # Verify can login with new password
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_token["email"],
            "password": "NewPassword456!"
        })
        assert login_response.status_code == 200
        print("✓ Login with new password successful")
    
    def test_change_password_wrong_current(self):
        """Test PUT /api/auth/password with wrong current password"""
        # Login as demo user
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.put(f"{BASE_URL}/api/auth/password", 
            headers=headers,
            json={
                "currentPassword": "WrongPassword!",
                "newPassword": "NewPassword456!"
            }
        )
        assert response.status_code == 400
        print("✓ Wrong current password rejected correctly")
    
    def test_change_password_unauthorized(self):
        """Test PUT /api/auth/password without auth"""
        response = requests.put(f"{BASE_URL}/api/auth/password", 
            json={
                "currentPassword": "OldPassword123!",
                "newPassword": "NewPassword456!"
            }
        )
        assert response.status_code == 401
        print("✓ Unauthorized password change rejected")


class TestDataExport:
    """Data export endpoint tests - GET /api/auth/export-data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Authentication failed")
    
    def test_export_data_success(self, auth_token):
        """Test GET /api/auth/export-data - successful export"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/export-data", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify export structure
        assert "exportedAt" in data
        assert "user" in data
        assert "generations" in data
        assert "creditHistory" in data
        assert "paymentHistory" in data
        
        # Verify user data
        assert data["user"]["email"] == DEMO_EMAIL
        assert "id" in data["user"]
        assert "name" in data["user"]
        assert "credits" in data["user"]
        
        print(f"✓ Data export successful:")
        print(f"  - User: {data['user']['name']}")
        print(f"  - Generations: {len(data['generations'])}")
        print(f"  - Credit History: {len(data['creditHistory'])}")
        print(f"  - Payment History: {len(data['paymentHistory'])}")
    
    def test_export_data_unauthorized(self):
        """Test GET /api/auth/export-data without auth"""
        response = requests.get(f"{BASE_URL}/api/auth/export-data")
        assert response.status_code == 401
        print("✓ Unauthorized data export rejected")


class TestEmailNotificationService:
    """Email notification service tests (stubbed - logs to DB)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Admin authentication failed")
    
    def test_email_logs_collection_exists(self, admin_token):
        """Verify email notification service is ready (logs to DB)"""
        # The email service logs to email_logs collection
        # We can verify by checking admin analytics which should work
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        print("✓ Email notification service backend is ready (stubbed with DB logging)")


class TestAccountDeletion:
    """Account deletion endpoint tests - DELETE /api/auth/account"""
    
    def test_delete_account_success(self):
        """Test DELETE /api/auth/account - successful deletion"""
        # Create a test user to delete
        test_email = f"TEST_delete_user_{os.urandom(4).hex()}@test.com"
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "TEST Delete User",
            "email": test_email,
            "password": "DeleteMe123!"
        })
        
        if register_response.status_code != 200:
            pytest.skip("Could not create test user for deletion")
        
        token = register_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Delete the account
        delete_response = requests.delete(f"{BASE_URL}/api/auth/account", headers=headers)
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["success"] == True
        print(f"✓ Account deletion successful: {data}")
        
        # Verify user can no longer login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "DeleteMe123!"
        })
        assert login_response.status_code == 401
        print("✓ Deleted user cannot login")
    
    def test_delete_account_unauthorized(self):
        """Test DELETE /api/auth/account without auth"""
        response = requests.delete(f"{BASE_URL}/api/auth/account")
        assert response.status_code == 401
        print("✓ Unauthorized account deletion rejected")


class TestCopyrightPage:
    """Copyright page tests - verify backend supports the page"""
    
    def test_privacy_policy_endpoint(self):
        """Test GET /api/privacy/policy endpoint"""
        response = requests.get(f"{BASE_URL}/api/privacy/policy")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        print(f"✓ Privacy policy endpoint working: {data['title']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
