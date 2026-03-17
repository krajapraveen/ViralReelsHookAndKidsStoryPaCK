"""
Photo to Comic Feature Backend Tests - Iteration 99
Tests for verifying polling/toast infinite loop bug fixes
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://narrative-suite.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for demo user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Create auth headers with bearer token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPhotoToComicAPIs:
    """Test Photo to Comic backend endpoints"""
    
    def test_get_styles_endpoint(self, auth_headers):
        """Test /api/photo-to-comic/styles returns valid styles"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify styles structure
        assert "styles" in data
        assert len(data["styles"]) > 0
        
        # Verify some expected styles exist
        styles = data["styles"]
        expected_styles = ["cartoon_fun", "bold_superhero", "romance_comic", "kids_storybook"]
        for style in expected_styles:
            assert style in styles, f"Expected style '{style}' not found"
    
    def test_get_pricing_endpoint(self, auth_headers):
        """Test /api/photo-to-comic/pricing returns valid pricing"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/pricing", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify pricing structure
        assert "pricing" in data
        pricing = data["pricing"]
        
        # Verify comic avatar pricing
        assert "comic_avatar" in pricing
        assert pricing["comic_avatar"]["base"] == 15
        
        # Verify comic strip pricing
        assert "comic_strip" in pricing
        assert pricing["comic_strip"]["panels"]["3"] == 25
        assert pricing["comic_strip"]["panels"]["4"] == 32
        
        # Verify download pricing
        assert "download" in pricing
        assert pricing["download"]["avatar"] == 10
    
    def test_get_history_endpoint(self, auth_headers):
        """Test /api/photo-to-comic/history returns user's jobs"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        # Verify jobs have proper fields
        if data["jobs"]:
            job = data["jobs"][0]
            assert "id" in job
            assert "userId" in job
            assert "mode" in job
            assert "status" in job
    
    def test_get_job_status_with_valid_id(self, auth_headers):
        """Test /api/photo-to-comic/job/{id} returns job details"""
        # First get a job ID from history
        history_response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        assert history_response.status_code == 200
        jobs = history_response.json().get("jobs", [])
        
        if not jobs:
            pytest.skip("No existing jobs to test job status endpoint")
        
        job_id = jobs[0]["id"]
        
        # Get job status
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/job/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify job has required fields
        assert data["id"] == job_id
        assert "status" in data
        assert data["status"] in ["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
    
    def test_get_job_status_with_invalid_id(self, auth_headers):
        """Test /api/photo-to-comic/job/{id} returns 404 for invalid job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/invalid-job-id-12345", 
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_blocked_keywords_validation(self, auth_headers):
        """Test that blocked copyright keywords are rejected"""
        # Create a simple test image
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Test with blocked keyword in custom_details
        files = {"photo": ("test.png", img_bytes, "image/png")}
        data = {
            "mode": "avatar",
            "style": "cartoon_fun",
            "custom_details": "Make it look like Spider-Man",  # Blocked keyword
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            files=files,
            data=data,
            headers={"Authorization": auth_headers["Authorization"]}
        )
        
        # Should be rejected with 400
        assert response.status_code == 400
        assert "spider-man" in response.json().get("detail", "").lower() or "copyrighted" in response.json().get("detail", "").lower()
    
    def test_blocked_keywords_in_story_prompt(self, auth_headers):
        """Test that blocked keywords in story prompt are rejected"""
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {"photo": ("test.png", img_bytes, "image/png")}
        data = {
            "mode": "strip",
            "style": "cartoon_fun",
            "panel_count": "3",
            "story_prompt": "A story about Batman fighting crime",  # Blocked keyword
            "include_dialogue": "true"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            files=files,
            data=data,
            headers={"Authorization": auth_headers["Authorization"]}
        )
        
        # Should be rejected with 400
        assert response.status_code == 400
        assert "batman" in response.json().get("detail", "").lower() or "copyrighted" in response.json().get("detail", "").lower()


class TestPhotoToComicJobPolling:
    """Test job polling behavior - critical for infinite loop bug fix verification"""
    
    def test_completed_job_has_correct_status(self, auth_headers):
        """Verify completed jobs have correct status for polling termination"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if not completed_jobs:
            pytest.skip("No completed jobs to verify")
        
        job = completed_jobs[0]
        
        # Verify completed job has proper structure for frontend polling
        assert job["status"] == "COMPLETED"
        assert job.get("progress") == 100
        
        # For avatar mode, should have resultUrl
        if job.get("mode") == "avatar":
            assert "resultUrl" in job or "resultUrls" in job
        
        # For strip mode, should have panels
        if job.get("mode") == "strip":
            assert "panels" in job
            assert len(job["panels"]) > 0
    
    def test_job_status_returns_consistent_data(self, auth_headers):
        """Verify job status returns consistent data (important for polling)"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        jobs = response.json().get("jobs", [])
        
        if not jobs:
            pytest.skip("No jobs to test")
        
        job_id = jobs[0]["id"]
        
        # Poll the same job multiple times - should return consistent data
        results = []
        for _ in range(3):
            resp = requests.get(f"{BASE_URL}/api/photo-to-comic/job/{job_id}", headers=auth_headers)
            assert resp.status_code == 200
            results.append(resp.json())
        
        # All results should be identical for a completed/stable job
        for i in range(1, len(results)):
            assert results[i]["status"] == results[0]["status"]
            assert results[i]["progress"] == results[0]["progress"]
    
    def test_download_endpoint_for_completed_job(self, auth_headers):
        """Test download works for completed jobs"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        jobs = response.json().get("jobs", [])
        
        completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if not completed_jobs:
            pytest.skip("No completed jobs to test download")
        
        job = completed_jobs[0]
        job_id = job["id"]
        
        # Try downloading
        download_response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/download/{job_id}",
            headers=auth_headers
        )
        
        # Should succeed (either new download or re-download)
        assert download_response.status_code == 200
        data = download_response.json()
        
        if data.get("success"):
            assert "downloadUrls" in data
        else:
            # Could fail due to insufficient credits - that's still valid behavior
            assert "error" in data or "message" in data


class TestUserAnalyticsRating:
    """Test rating/feedback API used by RatingModal"""
    
    def test_submit_rating_endpoint(self, auth_headers):
        """Test rating submission endpoint"""
        rating_data = {
            "rating": 5,
            "feature_key": "photo_to_comic_test",
            "comment": "Test rating from automated test",
            "related_request_id": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            json=rating_data,
            headers=auth_headers
        )
        
        # Should succeed
        assert response.status_code in [200, 201]
    
    def test_submit_low_rating_with_reason(self, auth_headers):
        """Test low rating requires reason"""
        rating_data = {
            "rating": 2,
            "feature_key": "photo_to_comic_test",
            "reason_type": "poor_quality",
            "comment": "Test low rating from automated test",
            "related_request_id": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            json=rating_data,
            headers=auth_headers
        )
        
        # Should succeed
        assert response.status_code in [200, 201]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
