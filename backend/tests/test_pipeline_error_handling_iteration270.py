"""
Pipeline Error Handling Tests - Iteration 270
Tests for improved error handling in Story Video creation flow.
Focus: 402 for credits, 500 with detail, session expiry (401), and validation (422)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestPipelineAuthentication:
    """Test 401 authentication errors for pipeline endpoints"""
    
    def test_create_pipeline_without_auth_returns_401(self):
        """POST /api/pipeline/create without auth token returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Test Story",
                "story_text": "A long enough story text that meets the 50 character minimum requirement for validation.",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            headers={"Content-Type": "application/json"}
        )
        # Should be 401 Unauthorized without auth token
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data or "message" in data
    
    def test_create_pipeline_with_invalid_token_returns_401(self):
        """POST /api/pipeline/create with invalid token returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Test Story",
                "story_text": "A long enough story text that meets the 50 character minimum requirement for validation.",
                "animation_style": "cartoon_2d"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token_12345"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"


class TestPipelineValidation:
    """Test 422 validation errors for pipeline create endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        return response.json().get("token")
    
    def test_create_pipeline_short_title_returns_422(self, auth_token):
        """POST /api/pipeline/create with too-short title (2 chars) returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Ab",  # Only 2 chars, min is 3
                "story_text": "A long enough story text that meets the 50 character minimum requirement for validation.",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        assert response.status_code == 422, f"Expected 422 for short title, got {response.status_code}: {response.text}"
        data = response.json()
        # Pydantic validation errors have detail as array
        assert "detail" in data
        # Check that error mentions title or minimum length
        detail_str = str(data["detail"]).lower()
        assert "title" in detail_str or "min" in detail_str or "length" in detail_str or "character" in detail_str
    
    def test_create_pipeline_short_story_returns_422(self, auth_token):
        """POST /api/pipeline/create with too-short story (<50 chars) returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Valid Title",
                "story_text": "Short story",  # Only ~11 chars, min is 50
                "animation_style": "cartoon_2d"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        assert response.status_code == 422, f"Expected 422 for short story, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        detail_str = str(data["detail"]).lower()
        assert "story" in detail_str or "min" in detail_str or "50" in detail_str or "character" in detail_str
    
    def test_create_pipeline_missing_title_returns_422(self, auth_token):
        """POST /api/pipeline/create with missing title returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "story_text": "A long enough story text that meets the 50 character minimum requirement for validation.",
                "animation_style": "cartoon_2d"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        assert response.status_code == 422, f"Expected 422 for missing title, got {response.status_code}: {response.text}"
    
    def test_create_pipeline_missing_story_returns_422(self, auth_token):
        """POST /api/pipeline/create with missing story_text returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Valid Title",
                "animation_style": "cartoon_2d"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        assert response.status_code == 422, f"Expected 422 for missing story, got {response.status_code}: {response.text}"


class TestPipelineSuccessPath:
    """Test successful pipeline creation - happy path"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        return response.json().get("token")
    
    def test_create_pipeline_valid_input_succeeds(self, auth_token):
        """POST /api/pipeline/create with valid input returns success with job_id"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Test Story for Error Handling Verification",
                "story_text": """Once upon a time in a magical forest, there lived a little rabbit named 
                Whiskers. Every day, Whiskers would hop through the meadow looking for adventures. 
                One sunny morning, Whiskers found a mysterious golden key hidden under an old oak tree.
                The key sparkled in the sunlight, and Whiskers wondered what it could unlock.
                With the key safely tucked in his pocket, Whiskers set off to find the door it opened.""",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        # Test user is rate-limit-exempt, so should succeed
        assert response.status_code == 200, f"Expected 200 for valid input, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "job_id" in data
        assert "credits_charged" in data
        assert isinstance(data["job_id"], str)
        assert len(data["job_id"]) > 10  # UUID-like


class TestPipelineOptions:
    """Test pipeline options endpoint"""
    
    def test_get_pipeline_options_returns_all_options(self):
        """GET /api/pipeline/options returns animation styles, age groups, voices"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert len(data["animation_styles"]) > 0
        assert len(data["age_groups"]) > 0
        assert len(data["voice_presets"]) > 0


class TestRateLimitStatus:
    """Test rate limit status endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        return response.json().get("token")
    
    def test_rate_limit_status_for_exempt_user(self, auth_token):
        """GET /api/pipeline/rate-limit-status for exempt user shows can_create=True"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/rate-limit-status",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Test user is exempt from rate limiting
        assert data.get("can_create") is True
        assert data.get("exempt") is True or data.get("max_per_hour", 0) >= 999


class TestPipelineStatusAndUserJobs:
    """Test pipeline status and user jobs endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        return response.json().get("token")
    
    def test_user_jobs_returns_list(self, auth_token):
        """GET /api/pipeline/user-jobs returns jobs list"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
    
    def test_job_status_for_nonexistent_job_returns_404(self, auth_token):
        """GET /api/pipeline/status/{job_id} for non-existent job returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/status/nonexistent-job-id-12345",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestGalleryEndpoints:
    """Test public gallery endpoints"""
    
    def test_gallery_returns_videos(self):
        """GET /api/pipeline/gallery returns videos list"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_gallery_categories_returns_list(self):
        """GET /api/pipeline/gallery/categories returns categories"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)
    
    def test_gallery_leaderboard_returns_list(self):
        """GET /api/pipeline/gallery/leaderboard returns leaderboard"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)


class TestErrorResponseFormat:
    """Test that error responses have proper format"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        return response.json().get("token")
    
    def test_422_error_has_detail_with_field_info(self, auth_token):
        """422 validation errors include field-specific information"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "X",  # Too short
                "story_text": "Y"  # Also too short
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Pydantic returns array of validation errors
        if isinstance(data["detail"], list):
            # Check that we have field locations
            for err in data["detail"]:
                assert "loc" in err or "msg" in err
    
    def test_401_error_has_detail(self):
        """401 unauthorized errors include detail message"""
        response = requests.post(
            f"{BASE_URL}/api/pipeline/create",
            json={
                "title": "Test",
                "story_text": "A" * 60
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer expired_invalid_token"
            }
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
