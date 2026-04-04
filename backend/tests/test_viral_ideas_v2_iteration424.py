"""
Daily Viral Idea Drop V2 - Backend API Tests
Tests all endpoints for the queue-driven content pack generator.
Iteration 424 - Full E2E testing of viral ideas feature.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestViralIdeasAuth:
    """Test authentication for viral ideas endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    def test_login_success(self):
        """Test that test user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("email") == TEST_EMAIL


class TestDailyFeed:
    """Test GET /api/viral-ideas/daily-feed endpoint"""
    
    def test_daily_feed_returns_ideas(self):
        """Test that daily feed returns ideas with niches"""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/daily-feed")
        assert response.status_code == 200, f"Daily feed failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Response should have success=True"
        assert "ideas" in data, "Response should have ideas array"
        assert "niches" in data, "Response should have niches array"
        assert "date" in data, "Response should have date"
        
        # Verify ideas structure
        ideas = data["ideas"]
        assert isinstance(ideas, list), "Ideas should be a list"
        assert len(ideas) > 0, "Should have at least one idea"
        
        # Check first idea structure
        first_idea = ideas[0]
        assert "idea" in first_idea, "Idea should have 'idea' field"
        assert "niche" in first_idea, "Idea should have 'niche' field"
        
        # Verify niches
        niches = data["niches"]
        assert isinstance(niches, list), "Niches should be a list"
        assert len(niches) > 0, "Should have at least one niche"
    
    def test_daily_feed_filter_by_niche(self):
        """Test filtering daily feed by niche"""
        # First get available niches
        response = requests.get(f"{BASE_URL}/api/viral-ideas/daily-feed")
        assert response.status_code == 200
        niches = response.json().get("niches", [])
        
        if niches:
            test_niche = niches[0]
            response = requests.get(f"{BASE_URL}/api/viral-ideas/daily-feed?niche={test_niche}")
            assert response.status_code == 200, f"Filtered feed failed: {response.text}"
            
            data = response.json()
            ideas = data.get("ideas", [])
            # All returned ideas should match the niche
            for idea in ideas:
                assert idea.get("niche") == test_niche, f"Idea niche mismatch: expected {test_niche}, got {idea.get('niche')}"


class TestGenerateBundle:
    """Test POST /api/viral-ideas/generate-bundle endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_generate_bundle_requires_auth(self):
        """Test that generate-bundle requires authentication"""
        response = requests.post(f"{BASE_URL}/api/viral-ideas/generate-bundle", json={
            "idea": "Test idea",
            "niche": "Tech"
        })
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
    
    def test_generate_bundle_returns_job_id(self, auth_token):
        """Test that generate-bundle returns job_id immediately"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/viral-ideas/generate-bundle", 
            json={
                "idea": "5 AI tools that will change how you work in 2026",
                "niche": "Tech"
            },
            headers=headers
        )
        
        assert response.status_code == 200, f"Generate bundle failed: {response.text}"
        
        data = response.json()
        assert "job_id" in data, "Response should have job_id"
        assert "status" in data, "Response should have status"
        assert "message" in data, "Response should have message"
        
        # Status should be pending (immediate return)
        assert data["status"] == "pending", f"Status should be pending, got {data['status']}"
        
        # Store job_id for subsequent tests
        TestGenerateBundle.created_job_id = data["job_id"]
        print(f"Created job_id: {data['job_id']}")


class TestJobStatus:
    """Test GET /api/viral-ideas/jobs/{job_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def job_id(self, auth_token):
        """Create a job and return its ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/viral-ideas/generate-bundle",
            json={
                "idea": "How to build a personal brand on social media",
                "niche": "Business"
            },
            headers=headers
        )
        if response.status_code == 200:
            return response.json().get("job_id")
        pytest.skip("Failed to create job for testing")
    
    def test_job_status_requires_auth(self, job_id):
        """Test that job status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{job_id}")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
    
    def test_job_status_returns_progress(self, auth_token, job_id):
        """Test that job status returns progressive status with tasks"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200, f"Job status failed: {response.text}"
        
        data = response.json()
        assert "job_id" in data, "Response should have job_id"
        assert "status" in data, "Response should have status"
        assert "progress" in data, "Response should have progress"
        assert "tasks" in data, "Response should have tasks"
        
        # Verify progress structure
        progress = data["progress"]
        assert "current_phase" in progress, "Progress should have current_phase"
        assert "percentage" in progress, "Progress should have percentage"
        assert "message" in progress, "Progress should have message"
        
        # Verify tasks structure
        tasks = data["tasks"]
        assert isinstance(tasks, list), "Tasks should be a list"
    
    def test_job_not_found(self, auth_token):
        """Test 404 for non-existent job"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/non-existent-job-id", headers=headers)
        assert response.status_code == 404, f"Should return 404, got {response.status_code}"


class TestJobAssets:
    """Test GET /api/viral-ideas/jobs/{job_id}/assets endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_assets_requires_auth(self):
        """Test that assets endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/some-job-id/assets")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"


class TestMyJobs:
    """Test GET /api/viral-ideas/my-jobs endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_my_jobs_requires_auth(self):
        """Test that my-jobs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/viral-ideas/my-jobs")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
    
    def test_my_jobs_returns_user_jobs(self, auth_token):
        """Test that my-jobs returns user's recent jobs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/viral-ideas/my-jobs", headers=headers)
        
        assert response.status_code == 200, f"My jobs failed: {response.text}"
        
        data = response.json()
        assert "jobs" in data, "Response should have jobs array"
        
        jobs = data["jobs"]
        assert isinstance(jobs, list), "Jobs should be a list"
        
        # If there are jobs, verify structure
        if jobs:
            first_job = jobs[0]
            assert "job_id" in first_job, "Job should have job_id"
            assert "idea" in first_job, "Job should have idea"
            assert "niche" in first_job, "Job should have niche"
            assert "status" in first_job, "Job should have status"
            assert "progress" in first_job, "Job should have progress"


class TestFullGenerationPipeline:
    """Test full generation pipeline: create job, poll until complete, verify assets"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_full_pipeline_completion(self, auth_token):
        """Test that full pipeline completes with all assets"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Step 1: Create job
        create_response = requests.post(f"{BASE_URL}/api/viral-ideas/generate-bundle",
            json={
                "idea": "The morning routine that 10x'd my productivity",
                "niche": "Lifestyle"
            },
            headers=headers
        )
        
        assert create_response.status_code == 200, f"Create job failed: {create_response.text}"
        job_id = create_response.json().get("job_id")
        assert job_id, "No job_id returned"
        print(f"Created job: {job_id}")
        
        # Step 2: Poll until complete (max 60 seconds)
        max_wait = 60
        poll_interval = 2
        elapsed = 0
        final_status = None
        
        while elapsed < max_wait:
            status_response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{job_id}", headers=headers)
            assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
            
            status_data = status_response.json()
            current_status = status_data.get("status")
            progress = status_data.get("progress", {})
            
            print(f"[{elapsed}s] Status: {current_status}, Phase: {progress.get('current_phase')}, Progress: {progress.get('percentage')}%")
            
            if current_status in ["completed", "completed_with_fallbacks"]:
                final_status = current_status
                break
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        assert final_status in ["completed", "completed_with_fallbacks"], f"Job did not complete within {max_wait}s. Final status: {final_status}"
        
        # Step 3: Verify assets
        assets_response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{job_id}/assets", headers=headers)
        assert assets_response.status_code == 200, f"Assets fetch failed: {assets_response.text}"
        
        assets_data = assets_response.json()
        assets = assets_data.get("assets", [])
        
        # Verify we have all expected asset types
        asset_types = [a.get("asset_type") for a in assets]
        print(f"Asset types: {asset_types}")
        
        assert "hooks" in asset_types, "Missing hooks asset"
        assert "script" in asset_types, "Missing script asset"
        assert "captions" in asset_types, "Missing captions asset"
        assert "thumbnail" in asset_types, "Missing thumbnail asset"
        
        # Verify hooks content
        hooks_asset = next((a for a in assets if a["asset_type"] == "hooks"), None)
        assert hooks_asset, "Hooks asset not found"
        assert hooks_asset.get("content"), "Hooks should have content"
        
        # Verify script content
        script_asset = next((a for a in assets if a["asset_type"] == "script"), None)
        assert script_asset, "Script asset not found"
        assert script_asset.get("content"), "Script should have content"
        
        # Verify captions content
        captions_asset = next((a for a in assets if a["asset_type"] == "captions"), None)
        assert captions_asset, "Captions asset not found"
        assert captions_asset.get("content"), "Captions should have content"
        
        # Verify thumbnail has file_url
        thumbnail_asset = next((a for a in assets if a["asset_type"] == "thumbnail"), None)
        assert thumbnail_asset, "Thumbnail asset not found"
        assert thumbnail_asset.get("file_url"), "Thumbnail should have file_url"
        assert thumbnail_asset["file_url"].startswith("/api/static/"), f"Thumbnail URL should start with /api/static/, got {thumbnail_asset['file_url']}"
        
        # Check for ZIP bundle (may or may not be present)
        zip_assets = [a for a in assets if a["asset_type"] == "zip_bundle"]
        if zip_assets:
            # Should only have ONE zip_bundle (race condition fix)
            assert len(zip_assets) == 1, f"Should have exactly 1 zip_bundle, found {len(zip_assets)}"
            zip_asset = zip_assets[0]
            assert zip_asset.get("file_url"), "ZIP bundle should have file_url"
            assert zip_asset["file_url"].startswith("/api/static/"), f"ZIP URL should start with /api/static/, got {zip_asset['file_url']}"
            print(f"ZIP bundle URL: {zip_asset['file_url']}")
        
        print(f"Full pipeline test PASSED for job {job_id}")


class TestStaticFileAccess:
    """Test that static files (thumbnails, ZIPs) are accessible"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_thumbnail_accessible(self, auth_token):
        """Test that thumbnail files are accessible via static URL"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get user's jobs to find a completed one
        jobs_response = requests.get(f"{BASE_URL}/api/viral-ideas/my-jobs", headers=headers)
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        completed_jobs = [j for j in jobs if j.get("status") in ["completed", "completed_with_fallbacks"]]
        
        if not completed_jobs:
            pytest.skip("No completed jobs to test static file access")
        
        job_id = completed_jobs[0]["job_id"]
        
        # Get assets
        assets_response = requests.get(f"{BASE_URL}/api/viral-ideas/jobs/{job_id}/assets", headers=headers)
        if assets_response.status_code != 200:
            pytest.skip("Could not fetch assets")
        
        assets = assets_response.json().get("assets", [])
        thumbnail = next((a for a in assets if a["asset_type"] == "thumbnail"), None)
        
        if not thumbnail or not thumbnail.get("file_url"):
            pytest.skip("No thumbnail URL to test")
        
        # Test thumbnail access
        thumb_url = f"{BASE_URL}{thumbnail['file_url']}"
        thumb_response = requests.get(thumb_url)
        assert thumb_response.status_code == 200, f"Thumbnail not accessible: {thumb_response.status_code}"
        assert "image" in thumb_response.headers.get("content-type", ""), "Thumbnail should be an image"
        print(f"Thumbnail accessible at: {thumb_url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
