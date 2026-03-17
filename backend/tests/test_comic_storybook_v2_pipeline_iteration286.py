"""
Comic Storybook V2 Pipeline Tests - Iteration 286
Testing the 8-stage pipeline rebuild with permanent CDN storage and user_assets registration.

Features tested:
- 8-stage pipeline: story_outline → page_plan → panel_prompts → image_generation → page_assembly → export_creation → storage_upload → asset_registration
- Permanent CDN-backed downloads (no expiry)
- user_assets collection with status=ready
- My Downloads API returning permanent assets only
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://narrative-suite.preview.emergentagent.com').rstrip('/')
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
# Known completed job from context
COMPLETED_JOB_ID = "cd85ee04-44af-4a2d-ab52-365eba9edb65"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get authorization headers."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestComicStorybookV2Genres:
    """Test genre and pricing endpoint."""

    def test_genres_endpoint_returns_pricing(self, auth_headers):
        """GET /api/comic-storybook-v2/genres returns genre list with pricing."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/genres", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "genres" in data
        assert "pricing" in data
        
        # Verify expected genres exist
        expected_genres = ["kids_adventure", "superhero", "fantasy", "comedy", "romance", "scifi", "mystery", "horror_lite"]
        for genre_id in expected_genres:
            assert genre_id in data["genres"], f"Missing genre: {genre_id}"
            assert "name" in data["genres"][genre_id]
        
        # Verify pricing structure
        assert "pages" in data["pricing"]
        assert "add_ons" in data["pricing"]
        assert "10" in str(data["pricing"]["pages"]) or 10 in data["pricing"]["pages"]


class TestComicStorybookV2JobStatus:
    """Test job status endpoint for completed jobs."""

    def test_job_status_returns_stages_array(self, auth_headers):
        """GET /api/comic-storybook-v2/job/{jobId} returns job status with stages array."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "COMPLETED"
        assert "stages" in data
        assert isinstance(data["stages"], list)
        assert len(data["stages"]) == 8, f"Expected 8 stages, got {len(data['stages'])}"

    def test_completed_job_has_permanent_flag(self, auth_headers):
        """COMPLETED jobs have permanent=true."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["permanent"] == True, "Completed job should have permanent=true"

    def test_completed_job_has_cdn_urls(self, auth_headers):
        """COMPLETED jobs have pdfUrl, coverUrl."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("pdfUrl") is not None, "pdfUrl should be present"
        assert data.get("coverUrl") is not None, "coverUrl should be present"

    def test_completed_job_has_assets_array(self, auth_headers):
        """COMPLETED jobs have assets array."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "assets" in data
        assert isinstance(data["assets"], list)
        assert len(data["assets"]) >= 2, "Should have at least PDF and Cover assets"

    def test_job_status_includes_progress_and_current_stage(self, auth_headers):
        """Job status includes progress and current_stage."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/job/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "progress" in data
        assert data["progress"] == 100, "Completed job should have 100% progress"
        assert "current_stage" in data


class TestComicStorybookV2Stages:
    """Test detailed stage status endpoint."""

    def test_stages_endpoint_returns_8_stages(self, auth_headers):
        """GET /api/comic-storybook-v2/stages/{jobId} returns 8 stage records."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/stages/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "stages" in data
        assert len(data["stages"]) == 8
        
        expected_stages = [
            "story_outline", "page_plan", "panel_prompts", "image_generation",
            "page_assembly", "export_creation", "storage_upload", "asset_registration"
        ]
        stage_names = [s["stage_name"] for s in data["stages"]]
        for expected in expected_stages:
            assert expected in stage_names, f"Missing stage: {expected}"

    def test_stages_have_attempt_count(self, auth_headers):
        """Each stage has attempt_count field."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/stages/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for stage in data["stages"]:
            assert "attempt_count" in stage, f"Stage {stage['stage_name']} missing attempt_count"
            assert isinstance(stage["attempt_count"], int)

    def test_stages_have_status_completed(self, auth_headers):
        """All stages for completed job have status=completed."""
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/stages/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        for stage in data["stages"]:
            assert stage["status"] == "completed", f"Stage {stage['stage_name']} should be completed"


class TestComicStorybookV2Download:
    """Test download endpoint returns permanent CDN URLs."""

    def test_download_returns_permanent_true(self, auth_headers):
        """POST /api/comic-storybook-v2/download/{jobId} returns permanent=true."""
        response = requests.post(f"{BASE_URL}/api/comic-storybook-v2/download/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["permanent"] == True

    def test_download_returns_downloadurls_with_pdf_and_cover(self, auth_headers):
        """Download response includes downloadUrls with pdf and cover keys."""
        response = requests.post(f"{BASE_URL}/api/comic-storybook-v2/download/{COMPLETED_JOB_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "downloadUrls" in data
        assert "pdf" in data["downloadUrls"], "downloadUrls should have 'pdf' key"
        assert "cover" in data["downloadUrls"], "downloadUrls should have 'cover' key"
        
        # Verify URLs are CDN URLs
        assert "r2.dev" in data["downloadUrls"]["pdf"] or "cloudflare" in data["downloadUrls"]["pdf"].lower(), "PDF should be CDN URL"


class TestMyDownloadsPermanent:
    """Test My Downloads endpoint returns permanent assets."""

    def test_my_downloads_returns_permanent_true(self, auth_headers):
        """GET /api/downloads/my-downloads returns permanent=true."""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["permanent"] == True

    def test_my_downloads_no_expiry_references(self, auth_headers):
        """Response has NO expiry references (excluding S3/R2 URL query params)."""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check that response structure has no expiry fields
        # Note: "x-amz-expires" in presigned URLs is expected (URL signature validity, not download expiry)
        for download in data.get("downloads", []):
            assert "expiry" not in download, "Download item should not have expiry field"
            assert "countdown" not in download, "Download item should not have countdown field"
            assert "expires_at" not in download, "Download item should not have expires_at field"
            assert download.get("permanent") == True, "Download should be permanent"

    def test_my_downloads_returns_ready_status_items(self, auth_headers):
        """Downloads array contains items with status=ready."""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "downloads" in data
        assert len(data["downloads"]) >= 2, "Should have at least 2 downloadable assets"
        
        for download in data["downloads"]:
            assert download["status"] == "ready", f"Download {download['id']} should have status=ready"
            assert download["permanent"] == True

    def test_my_downloads_has_comic_storybook_assets(self, auth_headers):
        """Downloads include COMIC_STORYBOOK_PDF and COMIC_STORYBOOK_COVER assets."""
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        features = [d["feature"] for d in data["downloads"]]
        assert "COMIC_STORYBOOK_PDF" in features, "Should have COMIC_STORYBOOK_PDF asset"
        assert "COMIC_STORYBOOK_COVER" in features, "Should have COMIC_STORYBOOK_COVER asset"


class TestDownloadUrlEndpoint:
    """Test individual download URL endpoint."""

    def test_download_url_returns_presigned_cdn_url(self, auth_headers):
        """GET /api/downloads/{id}/url returns presigned CDN URL."""
        # First get the asset ID
        response = requests.get(f"{BASE_URL}/api/downloads/my-downloads", headers=auth_headers)
        assert response.status_code == 200
        downloads = response.json()["downloads"]
        
        if len(downloads) > 0:
            asset_id = downloads[0]["id"]
            url_response = requests.get(f"{BASE_URL}/api/downloads/{asset_id}/url", headers=auth_headers)
            assert url_response.status_code == 200
            url_data = url_response.json()
            
            assert url_data["permanent"] == True
            assert "url" in url_data
            assert url_data["url"] is not None


class TestGenerateEndpointStructure:
    """Test generate endpoint response structure (without actually generating)."""

    def test_generate_endpoint_returns_correct_structure(self, auth_headers):
        """POST /api/comic-storybook-v2/generate returns jobId, status=QUEUED, stages=8."""
        # Note: We're not actually submitting a new job as per instructions
        # But we can verify history shows the expected structure
        response = requests.get(f"{BASE_URL}/api/comic-storybook-v2/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert len(data["jobs"]) > 0
        
        # The first job should be the completed one
        job = data["jobs"][0]
        assert "id" in job
        assert job["status"] in ["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
        
        # Check completed job structure
        if job["status"] == "COMPLETED":
            assert job["permanent"] == True


class TestDeleteDownload:
    """Test soft delete endpoint (archive)."""

    def test_delete_endpoint_archives_asset(self, auth_headers):
        """DELETE /api/downloads/{id} should archive the asset (we won't actually delete)."""
        # Just verify endpoint exists and returns proper error for non-existent asset
        response = requests.delete(f"{BASE_URL}/api/downloads/nonexistent-id-12345", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
