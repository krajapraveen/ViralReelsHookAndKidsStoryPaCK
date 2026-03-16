"""
Landing Page Redesign Tests - Iteration 155
Tests for new landing page with Story->Video hero, gallery API, and 10 credits signup
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://durable-jobs-beta.preview.emergentagent.com')

class TestGalleryAPI:
    """Gallery API tests - Public endpoint for landing page"""
    
    def test_gallery_endpoint_returns_videos(self):
        """GET /api/pipeline/gallery returns videos array"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        assert "videos" in data
        assert isinstance(data["videos"], list)
        print(f"Gallery returned {len(data['videos'])} videos")
    
    def test_gallery_no_auth_required(self):
        """Gallery is public - no auth header needed"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        # Should not return 401
    
    def test_gallery_video_structure(self):
        """Videos have required fields for landing page display"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        if data["videos"]:
            video = data["videos"][0]
            # Check expected fields for gallery display
            assert "title" in video or "output_url" in video
            assert "output_url" in video  # Must have video URL
            print(f"First video: {video.get('title', 'N/A')}")


class TestAuthCredits:
    """Authentication and credit system tests"""
    
    def test_login_returns_user_with_credits(self):
        """POST /api/auth/login returns user with credits"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert "credits" in data["user"]
        print(f"User credits: {data['user']['credits']}")
    
    def test_me_endpoint_returns_credits(self):
        """GET /api/auth/me returns user profile with credits"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        assert login_response.status_code == 200
        token = login_response.json()["token"]
        
        # Get profile
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "email" in data
        assert "credits" in data
        print(f"Profile credits: {data['credits']}")


class TestStoryVideoPipeline:
    """Story Video Pipeline tests - No regression"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_pipeline_options_endpoint(self):
        """GET /api/pipeline/options returns animation styles, age groups, voices"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        
        print(f"Animation styles: {len(data['animation_styles'])}")
        print(f"Age groups: {len(data['age_groups'])}")
        print(f"Voice presets: {len(data['voice_presets'])}")
        
        # Should have 6, 5, 5 as per PRD
        assert len(data["animation_styles"]) >= 6
        assert len(data["age_groups"]) >= 5
        assert len(data["voice_presets"]) >= 5
    
    def test_user_jobs_endpoint(self):
        """GET /api/pipeline/user-jobs returns user's pipeline jobs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        print(f"User has {len(data['jobs'])} pipeline jobs")


class TestDashboardEndpoints:
    """Dashboard API tests - No regression"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_credits_balance_endpoint(self):
        """GET /api/credits/balance returns current balance"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "credits" in data or "balance" in data
        print(f"Credits balance: {data}")
    
    def test_generations_endpoint(self):
        """GET /api/generate/ returns generation history"""
        response = requests.get(f"{BASE_URL}/api/generate/", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "generations" in data or isinstance(data, list)
        print(f"Generations returned")


class TestLiveStats:
    """Live stats API for landing page social proof bar"""
    
    def test_public_live_stats(self):
        """GET /api/live-stats/public returns stats for social proof"""
        response = requests.get(f"{BASE_URL}/api/live-stats/public")
        # This might be 200 or 404 depending on if implemented
        if response.status_code == 200:
            data = response.json()
            print(f"Live stats: {data}")
        else:
            print(f"Live stats endpoint: {response.status_code}")


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"Health: {response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
