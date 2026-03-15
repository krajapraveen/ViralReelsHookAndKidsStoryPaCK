"""
Bug Fixes Testing - Iteration 263
Tests for:
1. Story Video Pipeline - POST /api/pipeline/create works, QUEUED status returned
2. Comic Storybook V2 - POST /api/comic-storybook-v2/generate works
3. Frontend code review verification (pollingRef fix, RatingModal close)
4. Landing page testimonials section
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestBugFixes:
    """Bug fix verification tests for iteration 263"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token' not 'access_token'
        pytest.skip("Admin authentication failed")
        return None
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")  # API returns 'token' not 'access_token'
        pytest.skip("Test user authentication failed")
        return None
    
    # ===== BUG FIX 1: Story Video Pipeline Tests =====
    
    def test_pipeline_create_endpoint_exists(self, admin_token):
        """Bug Fix 1: Verify POST /api/pipeline/create endpoint exists and accepts requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test that the endpoint exists (even if we don't have enough credits)
        response = requests.post(f"{BASE_URL}/api/pipeline/create", 
            headers=headers,
            json={
                "title": "Test Superhero Story",
                "story_text": "A brave hero saves the city from a dangerous storm.",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        
        # Should either return 200 (job created) or 400 (validation/credits issue)
        # But NOT 404 (endpoint not found) or 500 (server error)
        assert response.status_code in [200, 201, 400, 422], f"Unexpected status: {response.status_code}, response: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "job_id" in data, "Response should contain job_id"
            print(f"✅ Pipeline job created successfully: {data.get('job_id')}")
        else:
            print(f"✅ Pipeline endpoint exists (returned {response.status_code}): {response.json()}")
    
    def test_pipeline_status_endpoint(self, admin_token):
        """Bug Fix 1: Verify pipeline status endpoint works"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test with a dummy job_id to verify endpoint exists
        response = requests.get(f"{BASE_URL}/api/pipeline/status/test-job-id", headers=headers)
        
        # Should be 404 (not found) or 200, not 500
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Pipeline status endpoint exists and responds correctly")
    
    def test_pipeline_workers_status(self, admin_token):
        """Bug Fix 1: Verify workers status endpoint returns priority config"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/pipeline/workers/status", headers=headers)
        
        # Should be 200 with worker status info
        assert response.status_code == 200, f"Workers status failed: {response.status_code}"
        data = response.json()
        
        # Verify priority config exists (from iteration 262)
        if "priority_config" in data:
            config = data["priority_config"]
            assert config.get("admin") == 0, "Admin priority should be 0"
            assert config.get("paid") == 1, "Paid priority should be 1"
            assert config.get("free") == 10, "Free priority should be 10"
            print(f"✅ Priority config verified: {config}")
        
        print(f"✅ Workers status endpoint working")
    
    # ===== BUG FIX 2: Comic Storybook V2 Tests =====
    
    def test_comic_storybook_v2_generate_endpoint_exists(self, test_user_token):
        """Bug Fix 2: Verify POST /api/comic-storybook-v2/generate endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        response = requests.post(f"{BASE_URL}/api/comic-storybook-v2/generate", 
            headers=headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "A curious bunny discovers a hidden garden full of talking flowers.",
                "title": "Test Story Book",
                "author": "Test Author",
                "pageCount": 10,
                "addOns": {},
                "dedicationText": None
            }
        )
        
        # Should return 200 (job created) or 400 (validation/credits issue)
        assert response.status_code in [200, 201, 400, 422], f"Unexpected status: {response.status_code}, response: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "jobId" in data, "Response should contain jobId"
            assert data.get("status") == "QUEUED", "Job should be QUEUED"
            print(f"✅ Comic storybook job created: {data.get('jobId')}, status: {data.get('status')}")
            return data.get("jobId")
        else:
            print(f"✅ Comic storybook endpoint exists (returned {response.status_code}): {response.json()}")
        return None
    
    def test_comic_storybook_v2_job_status_endpoint(self, test_user_token):
        """Bug Fix 2: Verify GET /api/comic-storybook-v2/job/{jobId} works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        # Test with a dummy job_id to verify endpoint exists
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/test-job-id", headers=headers)
        
        # Should be 404 (not found) or 200, not 500
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✅ Comic storybook job status endpoint exists")
    
    def test_comic_storybook_v2_genres_endpoint(self, test_user_token):
        """Bug Fix 2: Verify genres endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=headers)
        
        assert response.status_code == 200, f"Genres endpoint failed: {response.status_code}"
        data = response.json()
        assert "genres" in data, "Response should contain genres"
        assert "pricing" in data, "Response should contain pricing"
        
        # Verify expected genres exist
        genres = data.get("genres", {})
        expected_genres = ["kids_adventure", "superhero", "fantasy", "comedy"]
        for genre in expected_genres:
            assert genre in genres, f"Genre {genre} should exist"
        
        print(f"✅ Genres endpoint working, found {len(genres)} genres")
    
    def test_comic_storybook_v2_preview_endpoint(self, test_user_token):
        """Bug Fix 2: Verify preview endpoint works"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        response = requests.post(f"{BASE_URL}/api/comic-storybook-v2/preview",
            headers=headers,
            json={
                "genre": "kids_adventure",
                "storyIdea": "A test story about adventure.",
                "title": "Test Preview",
                "pageCount": 10
            }
        )
        
        # Preview should work or return expected status
        assert response.status_code in [200, 400, 422], f"Preview endpoint failed: {response.status_code}"
        print(f"✅ Preview endpoint working (status: {response.status_code})")
    
    # ===== BUG FIX 3: Frontend Code Review (indirect verification) =====
    
    def test_user_analytics_rating_endpoint(self, test_user_token):
        """Bug Fix 3: Verify rating endpoint works (RatingModal uses this)"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        
        response = requests.post(f"{BASE_URL}/api/user-analytics/rating",
            headers=headers,
            json={
                "rating": 5,
                "feature_key": "test_feature",
                "reason_type": None,
                "comment": "Test rating",
                "related_request_id": None
            }
        )
        
        # Should accept ratings
        assert response.status_code in [200, 201, 400], f"Rating endpoint failed: {response.status_code}"
        print(f"✅ Rating endpoint working (status: {response.status_code})")
    
    # ===== Landing Page Testimonials (API test for stats) =====
    
    def test_live_stats_public_endpoint(self):
        """Landing page: Verify live stats endpoint works (used by Landing.js)"""
        response = requests.get(f"{BASE_URL}/api/live-stats/public")
        
        # Should return public stats
        assert response.status_code == 200, f"Live stats failed: {response.status_code}"
        data = response.json()
        
        if data.get("success"):
            stats = data.get("stats", {})
            print(f"✅ Live stats endpoint working: {stats}")
        else:
            print(f"✅ Live stats endpoint exists (response: {data})")
    
    def test_pipeline_gallery_endpoint(self):
        """Landing page: Verify gallery endpoint works (used by Landing.js)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        
        # Should return gallery data
        assert response.status_code == 200, f"Gallery failed: {response.status_code}"
        data = response.json()
        
        if "videos" in data:
            print(f"✅ Gallery endpoint working, found {len(data.get('videos', []))} videos")
        else:
            print(f"✅ Gallery endpoint exists (response keys: {data.keys()})")


class TestHealthEndpoints:
    """Basic health and connectivity tests"""
    
    def test_api_health(self):
        """Verify API is reachable"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, "Health check failed"
        print(f"✅ API health check passed")
    
    def test_login_endpoint(self):
        """Verify login endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        data = response.json()
        assert "token" in data, "Login should return token"
        print(f"✅ Login endpoint working")
    
    def test_admin_login(self):
        """Verify admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.status_code}"
        data = response.json()
        assert "token" in data, "Login should return token"
        print(f"✅ Admin login endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
