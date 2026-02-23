"""
Iteration 72 - Mobile Responsive UI & Admin User Management Tests
Tests:
1. Mobile Login at 320px, 375px, 414px - no horizontal scroll, inputs full width
2. Mobile Dashboard at 375px - single column cards, credits visible  
3. Admin Users Management page - /app/admin/users
4. Admin reset credits API - /api/admin/users/reset-credits
5. Admin create user API - /api/admin/users/create
6. QA user login - qa@creatorstudio.ai
7. Autofill styles verification
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAdminAuthentication:
    """Test admin authentication and access"""
    
    def test_admin_login(self):
        """Test admin login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, "No token in response"
        return data.get("access_token") or data.get("token")
    
    def test_qa_user_login(self):
        """Test QA user login - qa@creatorstudio.ai"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "qa@creatorstudio.ai",
            "password": "QATester@2026!"
        })
        # QA user might not exist yet, test will verify
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data or "token" in data, "QA user login successful but no token"
            print(f"QA user login successful: {data.get('user', {}).get('email')}")
            return True
        else:
            print(f"QA user not found (status {response.status_code}), will be created via admin API")
            return False

    def test_demo_user_login(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"


class TestAdminUsersManagement:
    """Test admin user management endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, "Admin login failed"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_list_users(self, admin_token):
        """Test /api/admin/users/list endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list", headers=headers)
        assert response.status_code == 200, f"List users failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "users" in data, "No users field in response"
        assert "pagination" in data, "No pagination field in response"
        print(f"Found {data['pagination'].get('total', 0)} users")
    
    def test_list_users_with_search(self, admin_token):
        """Test user search functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list?search=admin", headers=headers)
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        assert "users" in data
        print(f"Search for 'admin' found {len(data['users'])} users")
    
    def test_list_users_with_role_filter(self, admin_token):
        """Test role filter functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list?role=admin", headers=headers)
        assert response.status_code == 200, f"Role filter failed: {response.text}"
        data = response.json()
        assert "users" in data
        # Verify all returned users have admin role
        for user in data["users"]:
            assert user.get("role") == "admin", f"User {user.get('email')} has role {user.get('role')}, expected admin"
        print(f"Admin role filter found {len(data['users'])} admin users")


class TestAdminResetCredits:
    """Test admin reset credits endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture
    def demo_user_id(self, admin_token):
        """Get demo user ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list?search=demo@example.com", headers=headers)
        if response.status_code == 200:
            users = response.json().get("users", [])
            if users:
                return users[0].get("id")
        return None
    
    def test_reset_credits_success(self, admin_token, demo_user_id):
        """Test successful credit reset"""
        if not demo_user_id:
            pytest.skip("Demo user not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
            "user_id": demo_user_id,
            "credits": 500,
            "reason": "Testing credit reset functionality"
        }, headers=headers)
        
        assert response.status_code == 200, f"Reset credits failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") == True, "Reset was not successful"
        assert data.get("new_credits") == 500, f"Expected 500 credits, got {data.get('new_credits')}"
        print(f"Credits reset: {data.get('old_credits')} -> {data.get('new_credits')}")
    
    def test_reset_credits_invalid_user(self, admin_token):
        """Test reset credits with invalid user ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
            "user_id": "invalid-user-id-12345",
            "credits": 100,
            "reason": "Testing invalid user"
        }, headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_reset_credits_missing_reason(self, admin_token, demo_user_id):
        """Test reset credits without required reason"""
        if not demo_user_id:
            pytest.skip("Demo user not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
            "user_id": demo_user_id,
            "credits": 100,
            "reason": "ab"  # Too short, min 5 chars
        }, headers=headers)
        
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"
    
    def test_reset_credits_unlimited(self, admin_token, demo_user_id):
        """Test setting unlimited credits (999999999)"""
        if not demo_user_id:
            pytest.skip("Demo user not found")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
            "user_id": demo_user_id,
            "credits": 999999999,
            "reason": "Setting unlimited credits for testing"
        }, headers=headers)
        
        assert response.status_code == 200, f"Unlimited credits failed: {response.text}"
        data = response.json()
        assert data.get("new_credits") == 999999999, "Credits not set to unlimited"
        print("Unlimited credits set successfully")
        
        # Reset back to normal
        response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
            "user_id": demo_user_id,
            "credits": 100,
            "reason": "Resetting to normal after test"
        }, headers=headers)


class TestAdminCreateUser:
    """Test admin create user endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_create_user_success(self, admin_token):
        """Test successful user creation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        test_email = f"test_user_{int(__import__('time').time())}@example.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users/create", json={
            "name": "Test User",
            "email": test_email,
            "password": "TestPassword123!",
            "credits": 500,
            "role": "user"
        }, headers=headers)
        
        assert response.status_code == 200, f"Create user failed: {response.status_code} - {response.text}"
        data = response.json()
        assert data.get("success") == True, "User creation not successful"
        assert data.get("user", {}).get("email") == test_email.lower()
        assert data.get("user", {}).get("credits") == 500
        print(f"Created user: {test_email} with 500 credits")
    
    def test_create_qa_user_with_unlimited_credits(self, admin_token):
        """Test creating QA user with unlimited credits"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First check if QA user already exists
        response = requests.get(f"{BASE_URL}/api/admin/users/list?search=qa@creatorstudio.ai", headers=headers)
        if response.status_code == 200:
            users = response.json().get("users", [])
            if users:
                print("QA user already exists, skipping creation")
                # Set unlimited credits
                user_id = users[0].get("id")
                response = requests.post(f"{BASE_URL}/api/admin/users/reset-credits", json={
                    "user_id": user_id,
                    "credits": 999999999,
                    "reason": "Setting unlimited credits for QA user"
                }, headers=headers)
                assert response.status_code == 200
                return
        
        # Create QA user
        response = requests.post(f"{BASE_URL}/api/admin/users/create", json={
            "name": "QA Tester",
            "email": "qa@creatorstudio.ai",
            "password": "QATester@2026!",
            "credits": 999999999,  # Unlimited
            "role": "qa"
        }, headers=headers)
        
        if response.status_code == 400 and "already registered" in response.text.lower():
            print("QA user already exists")
            return
        
        assert response.status_code == 200, f"Create QA user failed: {response.text}"
        data = response.json()
        assert data.get("user", {}).get("role") == "qa"
        print("QA user created with unlimited credits")
    
    def test_create_user_duplicate_email(self, admin_token):
        """Test creating user with existing email"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/users/create", json={
            "name": "Duplicate Admin",
            "email": "admin@creatorstudio.ai",
            "password": "Password123!",
            "credits": 100,
            "role": "user"
        }, headers=headers)
        
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
    
    def test_create_user_invalid_password(self, admin_token):
        """Test creating user with short password"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/users/create", json={
            "name": "Test",
            "email": "shortpwd@example.com",
            "password": "abc",  # Too short, min 8 chars
            "credits": 100,
            "role": "user"
        }, headers=headers)
        
        assert response.status_code == 422, f"Expected 422 validation error, got {response.status_code}"


class TestAdminUsersPageAccess:
    """Test Admin Users Management page access"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_admin_users_page_api_access(self, admin_token):
        """Test that admin users list API is accessible"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list", headers=headers)
        assert response.status_code == 200, f"Admin users list not accessible: {response.text}"
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated access is denied"""
        response = requests.get(f"{BASE_URL}/api/admin/users/list")
        assert response.status_code == 401 or response.status_code == 403, "Should require authentication"
    
    def test_non_admin_access_denied(self):
        """Test that non-admin users cannot access"""
        # Login as demo user
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if login_response.status_code != 200:
            pytest.skip("Demo user login failed")
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/users/list", headers=headers)
        # Should return 403 Forbidden for non-admin
        assert response.status_code == 403, f"Non-admin should get 403, got {response.status_code}"


class TestAPIHealthAndAuth:
    """Basic API health and auth tests"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
    
    def test_login_endpoint_exists(self):
        """Test login endpoint is available"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@test.com",
            "password": "test"
        })
        # Should get 401 or similar, not 404
        assert response.status_code != 404, "Login endpoint not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
