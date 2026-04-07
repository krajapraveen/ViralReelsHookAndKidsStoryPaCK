"""
Product Guidance System API Tests - Iteration 450
Tests for user progress tracking endpoints:
- GET /api/user/progress
- POST /api/user/progress/update
- POST /api/user/progress/dismiss-guide
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestUserProgressAPI:
    """Tests for user progress tracking endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        return None
    
    # ============================================
    # AUTH REQUIRED TESTS
    # ============================================
    
    def test_get_progress_requires_auth(self):
        """GET /api/user/progress returns 401 without token"""
        response = self.session.get(f"{BASE_URL}/api/user/progress")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET /api/user/progress returns 401 without auth")
    
    def test_update_progress_requires_auth(self):
        """POST /api/user/progress/update returns 401 without token"""
        response = self.session.post(f"{BASE_URL}/api/user/progress/update", json={
            "step": "create"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/user/progress/update returns 401 without auth")
    
    def test_dismiss_guide_requires_auth(self):
        """POST /api/user/progress/dismiss-guide returns 401 without token"""
        response = self.session.post(f"{BASE_URL}/api/user/progress/dismiss-guide")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/user/progress/dismiss-guide returns 401 without auth")
    
    # ============================================
    # GET PROGRESS TESTS
    # ============================================
    
    def test_get_progress_authenticated(self):
        """GET /api/user/progress returns progress object with correct fields"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/user/progress")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "data" in data, "Expected 'data' field in response"
        
        progress = data["data"]
        
        # Verify required fields exist
        required_fields = [
            "current_step", "completed_steps", "features_used", 
            "guide_dismissed", "total_generations", "total_shares"
        ]
        for field in required_fields:
            assert field in progress, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(progress["current_step"], str), "current_step should be string"
        assert isinstance(progress["completed_steps"], list), "completed_steps should be list"
        assert isinstance(progress["features_used"], list), "features_used should be list"
        assert isinstance(progress["guide_dismissed"], bool), "guide_dismissed should be bool"
        assert isinstance(progress["total_generations"], int), "total_generations should be int"
        assert isinstance(progress["total_shares"], int), "total_shares should be int"
        
        print(f"PASS: GET /api/user/progress returns valid progress object")
        print(f"  - current_step: {progress['current_step']}")
        print(f"  - completed_steps: {progress['completed_steps']}")
        print(f"  - guide_dismissed: {progress['guide_dismissed']}")
        print(f"  - total_generations: {progress['total_generations']}")
        print(f"  - total_shares: {progress['total_shares']}")
    
    # ============================================
    # UPDATE PROGRESS TESTS
    # ============================================
    
    def test_update_progress_step(self):
        """POST /api/user/progress/update updates current_step and completed_steps"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Update to 'create' step
        response = self.session.post(f"{BASE_URL}/api/user/progress/update", json={
            "step": "create"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert "data" in data, "Expected 'data' field in response"
        
        progress = data["data"]
        assert progress["current_step"] == "create", f"Expected current_step='create', got {progress['current_step']}"
        assert "create" in progress["completed_steps"], "Expected 'create' in completed_steps"
        
        print("PASS: POST /api/user/progress/update correctly updates step")
    
    def test_update_progress_with_feature(self):
        """POST /api/user/progress/update adds feature to features_used"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Update with feature
        response = self.session.post(f"{BASE_URL}/api/user/progress/update", json={
            "step": "generate",
            "feature": "story_video"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        progress = data["data"]
        
        assert "story_video" in progress["features_used"], "Expected 'story_video' in features_used"
        
        print("PASS: POST /api/user/progress/update correctly adds feature")
    
    def test_update_progress_generation_action(self):
        """POST /api/user/progress/update increments total_generations on generation_complete action"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current generations count
        response = self.session.get(f"{BASE_URL}/api/user/progress")
        initial_generations = response.json()["data"]["total_generations"]
        
        # Update with generation_complete action
        response = self.session.post(f"{BASE_URL}/api/user/progress/update", json={
            "step": "result",
            "action": "generation_complete"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        progress = data["data"]
        assert progress["total_generations"] == initial_generations + 1, \
            f"Expected total_generations to increment from {initial_generations} to {initial_generations + 1}"
        
        print(f"PASS: generation_complete action increments total_generations ({initial_generations} -> {progress['total_generations']})")
    
    def test_update_progress_share_action(self):
        """POST /api/user/progress/update increments total_shares on share_complete action"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get current shares count
        response = self.session.get(f"{BASE_URL}/api/user/progress")
        initial_shares = response.json()["data"]["total_shares"]
        
        # Update with share_complete action
        response = self.session.post(f"{BASE_URL}/api/user/progress/update", json={
            "step": "share",
            "action": "share_complete"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        progress = data["data"]
        assert progress["total_shares"] == initial_shares + 1, \
            f"Expected total_shares to increment from {initial_shares} to {initial_shares + 1}"
        
        print(f"PASS: share_complete action increments total_shares ({initial_shares} -> {progress['total_shares']})")
    
    # ============================================
    # DISMISS GUIDE TESTS
    # ============================================
    
    def test_dismiss_guide(self):
        """POST /api/user/progress/dismiss-guide sets guide_dismissed to true"""
        token = self.get_auth_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert token, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Dismiss guide
        response = self.session.post(f"{BASE_URL}/api/user/progress/dismiss-guide")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        
        # Verify guide is dismissed by fetching progress
        response = self.session.get(f"{BASE_URL}/api/user/progress")
        progress = response.json()["data"]
        
        assert progress["guide_dismissed"] == True, "Expected guide_dismissed=True after dismiss"
        
        print("PASS: POST /api/user/progress/dismiss-guide sets guide_dismissed=True")


class TestAdminGrowthDashboardRegression:
    """Regression tests for admin growth dashboard (from iteration 449)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Helper to get admin auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        return None
    
    def test_growth_dashboard_story_created_nonzero(self):
        """Regression: Growth dashboard shows Story Created > 0 with 30d period"""
        token = self.get_admin_token()
        assert token, "Failed to get admin auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Use 30d period (720 hours) as per iteration 449
        response = self.session.get(f"{BASE_URL}/api/admin/metrics/growth?hours=720")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check share_funnel.created exists and is > 0
        share_funnel = data.get("share_funnel", {})
        created = share_funnel.get("created", 0)
        
        assert created > 0, f"Expected share_funnel.created > 0, got {created}"
        
        print(f"PASS: Growth dashboard shows Story Created = {created} (30d period)")


class TestAuthFlowRegression:
    """Regression tests for auth flows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_login_test_user(self):
        """Test user login works correctly"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "token" in data, "Expected 'token' in response"
        assert len(data["token"]) > 0, "Expected non-empty token"
        
        print("PASS: Test user login works correctly")
    
    def test_login_admin_user(self):
        """Admin user login works correctly"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "token" in data, "Expected 'token' in response"
        assert len(data["token"]) > 0, "Expected non-empty token"
        
        print("PASS: Admin user login works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
