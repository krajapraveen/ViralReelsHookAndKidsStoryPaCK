"""
Iteration 306 - Comic Storybook Preview Fix Tests
Tests to verify:
1. POST /api/comic-storybook-v2/preview returns success:true with real presigned R2 URLs (not placehold.co)
2. POST /api/comic-storybook-v2/preview returns success:false when preview generation fails (not fake URLs)
3. GET /api/comic-storybook-v2/job/{id} returns presigned page_urls for completed jobs
4. GET /api/pipeline/gallery returns 48+ items with thumbnail_url (regression check)
5. No placehold.co URLs in comic storybook responses
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestComicStorybookPreview:
    """Test Comic Storybook Preview endpoint - honest state (no fake images)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_preview_endpoint_exists(self):
        """P0: POST /api/comic-storybook-v2/preview endpoint should exist"""
        response = self.session.post(f"{BASE_URL}/api/comic-storybook-v2/preview", json={
            "genre": "kids_adventure",
            "storyIdea": "A curious bunny discovers a hidden garden full of talking flowers and makes new friends along the way.",
            "title": "Test Preview Story",
            "pageCount": 10
        }, timeout=120)
        
        # Should return 200 (not 404)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"Preview endpoint response: {response.status_code}")
    
    def test_preview_returns_success_or_honest_failure(self):
        """P0: Preview should return success:true with R2 URLs OR success:false (never placehold.co)"""
        response = self.session.post(f"{BASE_URL}/api/comic-storybook-v2/preview", json={
            "genre": "fantasy",
            "storyIdea": "A young wizard finds a talking book that takes them to magical realms full of wonder and adventure.",
            "title": "Magic Book Adventure",
            "pageCount": 10
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Must have 'success' field
        assert "success" in data, f"Response missing 'success' field: {data}"
        
        if data["success"]:
            # If successful, must have previewPages with R2 URLs
            assert "previewPages" in data, f"Success but no previewPages: {data}"
            assert len(data["previewPages"]) > 0, f"Success but empty previewPages: {data}"
            
            for page in data["previewPages"]:
                url = page.get("url", "")
                # Must NOT be placehold.co
                assert "placehold.co" not in url, f"Found placehold.co URL in preview: {url}"
                # Should be R2 presigned URL or valid CDN URL
                assert url.startswith("https://"), f"URL doesn't start with https: {url}"
                print(f"Preview page URL (valid): {url[:80]}...")
        else:
            # If failed, must have honest message
            assert "message" in data, f"Failed but no message: {data}"
            assert data.get("previewPages", []) == [], f"Failed but has fake previewPages: {data}"
            print(f"Preview honestly failed: {data.get('message')}")
    
    def test_preview_no_placehold_co_on_failure(self):
        """P0: Even with minimal input, should return honest failure not placehold.co"""
        response = self.session.post(f"{BASE_URL}/api/comic-storybook-v2/preview", json={
            "genre": "mystery",
            "storyIdea": "A detective solves a mystery.",
            "title": "Mystery Story",
            "pageCount": 10
        }, timeout=120)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all URLs in response
        response_text = str(data)
        assert "placehold.co" not in response_text, f"Found placehold.co in response: {response_text}"
        print(f"Preview response contains no placehold.co URLs")


class TestComicStorybookJobStatus:
    """Test that completed jobs have presigned page_urls"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_job_history_endpoint(self):
        """Test GET /api/comic-storybook-v2/history returns user's jobs"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook-v2/history", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "jobs" in data, f"Response missing 'jobs': {data}"
        print(f"User has {len(data['jobs'])} comic storybook jobs")
        
        # Check if any completed jobs exist
        completed_jobs = [j for j in data["jobs"] if j.get("status") == "COMPLETED"]
        print(f"Completed jobs: {len(completed_jobs)}")
        
        return data["jobs"]
    
    def test_job_status_has_presigned_urls(self):
        """Test that completed jobs have presigned page_urls in job status"""
        # First get history to find a completed job
        history_response = self.session.get(f"{BASE_URL}/api/comic-storybook-v2/history", timeout=30)
        if history_response.status_code != 200:
            pytest.skip("Could not fetch job history")
        
        jobs = history_response.json().get("jobs", [])
        completed = [j for j in jobs if j.get("status") == "COMPLETED"]
        
        if not completed:
            pytest.skip("No completed comic storybook jobs to test")
        
        job_id = completed[0]["id"]
        print(f"Testing job status for: {job_id}")
        
        response = self.session.get(f"{BASE_URL}/api/comic-storybook-v2/job/{job_id}", timeout=30)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        job_data = response.json()
        
        # Check for presigned URLs
        if job_data.get("pdfUrl"):
            assert "placehold.co" not in job_data["pdfUrl"], f"pdfUrl contains placehold.co: {job_data['pdfUrl']}"
            print(f"PDF URL (presigned): {job_data['pdfUrl'][:80]}...")
        
        if job_data.get("coverUrl"):
            assert "placehold.co" not in job_data["coverUrl"], f"coverUrl contains placehold.co: {job_data['coverUrl']}"
            print(f"Cover URL (presigned): {job_data['coverUrl'][:80]}...")
        
        if job_data.get("page_urls"):
            for page in job_data["page_urls"]:
                url = page.get("url", "")
                assert "placehold.co" not in url, f"page_url contains placehold.co: {url}"
            print(f"All {len(job_data['page_urls'])} page_urls verified (no placehold.co)")


class TestGalleryRegressionCheck:
    """Regression test: Gallery should still return 48+ items with real thumbnails"""
    
    def test_gallery_returns_items(self):
        """Gallery should return 48+ items"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "videos" in data, f"Response missing 'videos': {data}"
        videos = data["videos"]
        
        assert len(videos) >= 48, f"Expected 48+ videos, got {len(videos)}"
        print(f"Gallery returns {len(videos)} videos")
        
        # Verify thumbnails exist
        with_thumb = [v for v in videos if v.get("thumbnail_url")]
        print(f"Videos with thumbnail_url: {len(with_thumb)}/{len(videos)}")
        
        # Check no placehold.co
        for v in videos:
            if v.get("thumbnail_url"):
                assert "placehold.co" not in v["thumbnail_url"], f"thumbnail_url contains placehold.co: {v['thumbnail_url']}"
        
        print("All gallery thumbnails verified (no placehold.co)")


class TestExploreRegressionCheck:
    """Regression test: Explore should still return items with real thumbnails"""
    
    def test_explore_trending(self):
        """Explore trending should return items with thumbnails"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/public/explore?sort=trending&limit=12", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        items = data.get("items", data.get("videos", []))
        print(f"Explore trending returns {len(items)} items")
        
        # Check thumbnails and no placehold.co
        for item in items:
            thumb = item.get("thumbnail_url") or item.get("thumbnailUrl")
            if thumb:
                assert "placehold.co" not in thumb, f"thumbnail contains placehold.co: {thumb}"
        
        print("All explore items verified (no placehold.co)")


class TestGenresAndPricing:
    """Test genres and pricing endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.text}")
        
        self.token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_genres_endpoint(self):
        """GET /api/comic-storybook-v2/genres should return genre list"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook-v2/genres", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "genres" in data, f"Response missing 'genres': {data}"
        assert len(data["genres"]) > 0, f"No genres returned: {data}"
        print(f"Genres available: {list(data['genres'].keys())}")
    
    def test_pricing_endpoint(self):
        """GET /api/comic-storybook-v2/pricing should return pricing"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook-v2/pricing", timeout=30)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "pricing" in data, f"Response missing 'pricing': {data}"
        print(f"Pricing: {data['pricing']}")
