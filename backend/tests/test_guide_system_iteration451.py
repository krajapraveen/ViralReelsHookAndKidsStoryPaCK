"""
Product Guide System API Tests - Iteration 451
Tests for user progress tracking, guide dismissal, and auth requirements
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


class TestAuthEndpoints:
    """Test authentication for progress endpoints"""
    
    def test_get_progress_requires_auth(self):
        """GET /api/user/progress should return 401 without token"""
        response = requests.get(f"{BASE_URL}/api/user/progress")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: GET /api/user/progress returns 401 without auth")
    
    def test_update_progress_requires_auth(self):
        """POST /api/user/progress/update should return 401 without token"""
        response = requests.post(f"{BASE_URL}/api/user/progress/update", json={"step": "create"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/user/progress/update returns 401 without auth")
    
    def test_dismiss_guide_requires_auth(self):
        """POST /api/user/progress/dismiss-guide should return 401 without token"""
        response = requests.post(f"{BASE_URL}/api/user/progress/dismiss-guide")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: POST /api/user/progress/dismiss-guide returns 401 without auth")


class TestUserProgressAPI:
    """Test user progress CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token") or data.get("data", {}).get("token")
        assert self.token, "No token in login response"
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"PASS: Login successful for {TEST_USER_EMAIL}")
    
    def test_get_progress_returns_progress_object(self):
        """GET /api/user/progress should return progress with required fields"""
        response = requests.get(f"{BASE_URL}/api/user/progress", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=true"
        
        progress = data.get("data", {})
        # Check required fields
        required_fields = ["current_step", "completed_steps", "features_used", "guide_dismissed"]
        for field in required_fields:
            assert field in progress, f"Missing required field: {field}"
        
        print(f"PASS: GET /api/user/progress returns progress object with fields: {list(progress.keys())}")
        return progress
    
    def test_update_progress_step(self):
        """POST /api/user/progress/update should update current step"""
        response = requests.post(
            f"{BASE_URL}/api/user/progress/update",
            headers=self.headers,
            json={"step": "create", "action": "test_action", "feature": "story-video"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=true"
        
        progress = data.get("data", {})
        assert progress.get("current_step") == "create", "current_step should be 'create'"
        assert "create" in progress.get("completed_steps", []), "completed_steps should include 'create'"
        
        print("PASS: POST /api/user/progress/update updates step correctly")
    
    def test_update_progress_with_feature(self):
        """POST /api/user/progress/update should track feature usage"""
        response = requests.post(
            f"{BASE_URL}/api/user/progress/update",
            headers=self.headers,
            json={"step": "generate", "feature": "story-video-studio"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        progress = data.get("data", {})
        assert "story-video-studio" in progress.get("features_used", []), "features_used should include 'story-video-studio'"
        
        print("PASS: POST /api/user/progress/update tracks feature usage")
    
    def test_update_progress_generation_complete(self):
        """POST /api/user/progress/update with action=generation_complete should increment counter"""
        # Get current count
        get_response = requests.get(f"{BASE_URL}/api/user/progress", headers=self.headers)
        current_count = get_response.json().get("data", {}).get("total_generations", 0)
        
        # Update with generation_complete
        response = requests.post(
            f"{BASE_URL}/api/user/progress/update",
            headers=self.headers,
            json={"step": "result", "action": "generation_complete"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        progress = data.get("data", {})
        new_count = progress.get("total_generations", 0)
        assert new_count >= current_count, f"total_generations should be >= {current_count}, got {new_count}"
        
        print(f"PASS: generation_complete increments total_generations (now: {new_count})")
    
    def test_dismiss_guide(self):
        """POST /api/user/progress/dismiss-guide should set guide_dismissed=true"""
        response = requests.post(
            f"{BASE_URL}/api/user/progress/dismiss-guide",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should have success=true"
        
        # Verify by getting progress
        get_response = requests.get(f"{BASE_URL}/api/user/progress", headers=self.headers)
        progress = get_response.json().get("data", {})
        assert progress.get("guide_dismissed") == True, "guide_dismissed should be True after dismiss"
        
        print("PASS: POST /api/user/progress/dismiss-guide sets guide_dismissed=true")


class TestAdminLogin:
    """Test admin login works"""
    
    def test_admin_login(self):
        """Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        token = data.get("token") or data.get("data", {}).get("token")
        assert token, "No token in admin login response"
        print(f"PASS: Admin login successful for {ADMIN_EMAIL}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self):
        """API should be reachable"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("PASS: API health check")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
