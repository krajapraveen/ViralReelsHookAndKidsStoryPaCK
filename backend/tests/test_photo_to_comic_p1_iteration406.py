"""
Photo to Comic P1 Frontend Upgrades - Backend API Tests
Tests for: StylePreviewStrip, ComicDownloads, Event tracking, PDF endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"
COMPLETED_JOB_ID = "dd41b71f-5711-413b-aac3-dc11349e8e04"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestStylePreviewsEndpoint:
    """Tests for /api/photo-to-comic/style-previews endpoint"""
    
    def test_style_previews_returns_8_previews(self, auth_headers):
        """Style previews endpoint should return exactly 8 style previews"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/style-previews", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "previews" in data, "Response should contain 'previews' key"
        
        previews = data["previews"]
        assert len(previews) == 8, f"Expected 8 previews, got {len(previews)}"
    
    def test_style_previews_structure(self, auth_headers):
        """Each preview should have id, name, badge, desc fields"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/style-previews", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        previews = data["previews"]
        
        required_fields = ["id", "name", "badge", "desc"]
        for preview in previews:
            for field in required_fields:
                assert field in preview, f"Preview missing '{field}' field: {preview}"
    
    def test_style_previews_expected_styles(self, auth_headers):
        """Verify expected style IDs are present"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/style-previews", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        style_ids = [p["id"] for p in data["previews"]]
        
        expected_ids = ["cartoon", "manga", "chibi", "storybook", "bold_hero", "retro_pop", "noir", "cyberpunk"]
        for expected_id in expected_ids:
            assert expected_id in style_ids, f"Missing style ID: {expected_id}"
    
    def test_style_previews_requires_auth(self):
        """Style previews endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/style-previews")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestEventsEndpoint:
    """Tests for /api/photo-to-comic/events endpoint"""
    
    def test_events_accepts_valid_event_types(self, auth_headers):
        """Events endpoint should accept valid event types"""
        valid_events = [
            "preview_strip_style_click",
            "pdf_download_click",
            "pdf_download_success",
            "pdf_download_fail",
            "png_download_click",
            "script_download_click",
            "result_page_view",
            "generate_after_preview"
        ]
        
        for event_type in valid_events:
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/events",
                headers=auth_headers,
                json={"event_type": event_type, "metadata": {"test": True}}
            )
            assert response.status_code == 200, f"Event '{event_type}' failed: {response.status_code}"
            data = response.json()
            assert data.get("ok") == True, f"Event '{event_type}' response not ok"
    
    def test_events_rejects_unknown_event_type(self, auth_headers):
        """Events endpoint should reject unknown event types"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/events",
            headers=auth_headers,
            json={"event_type": "unknown_event_type", "metadata": {}}
        )
        assert response.status_code == 400, f"Expected 400 for unknown event, got {response.status_code}"
    
    def test_events_requires_auth(self):
        """Events endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/events",
            json={"event_type": "pdf_download_click", "metadata": {}}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_events_with_metadata(self, auth_headers):
        """Events endpoint should accept metadata"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/events",
            headers=auth_headers,
            json={
                "event_type": "preview_strip_style_click",
                "metadata": {"style": "cartoon_fun", "source": "preview_strip"}
            }
        )
        assert response.status_code == 200
        assert response.json().get("ok") == True


class TestPDFEndpoint:
    """Tests for /api/photo-to-comic/pdf/{job_id} endpoint"""
    
    def test_pdf_endpoint_returns_pdf_for_completed_job(self, auth_headers):
        """PDF endpoint should return valid PDF for completed job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/{COMPLETED_JOB_ID}",
            headers=auth_headers,
            timeout=60
        )
        
        # Should return 200 with PDF content or 404 if job not found
        if response.status_code == 200:
            assert response.headers.get("content-type") == "application/pdf", \
                f"Expected application/pdf, got {response.headers.get('content-type')}"
            
            # Check PDF magic bytes
            assert response.content[:4] == b'%PDF', "Response should start with PDF magic bytes"
            
            # Check reasonable size (should be > 10KB for a real PDF)
            assert len(response.content) > 10000, f"PDF too small: {len(response.content)} bytes"
            
            print(f"PDF size: {len(response.content)} bytes (~{len(response.content)//1024}KB)")
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found - may need different test job")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text[:200]}")
    
    def test_pdf_endpoint_returns_404_for_invalid_job(self, auth_headers):
        """PDF endpoint should return 404 for non-existent job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/invalid-job-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_pdf_endpoint_requires_auth(self):
        """PDF endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/pdf/{COMPLETED_JOB_ID}")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestJobStatusForDownloads:
    """Tests for job status endpoint related to download readiness"""
    
    def test_job_status_returns_status_field(self, auth_headers):
        """Job status should include status field for download readiness"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Job response should include 'status' field"
            assert data["status"] in ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL_READY", "FAILED"], \
                f"Unexpected status: {data['status']}"
            print(f"Job status: {data['status']}")
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")
    
    def test_completed_job_has_result_url(self, auth_headers):
        """Completed job should have resultUrl or panels"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/job/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "COMPLETED":
                has_result = data.get("resultUrl") or data.get("resultUrls") or data.get("panels")
                assert has_result, "Completed job should have resultUrl, resultUrls, or panels"
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found")


class TestValidateAssetEndpoint:
    """Tests for /api/photo-to-comic/validate-asset/{job_id} endpoint"""
    
    def test_validate_asset_returns_readiness_fields(self, auth_headers):
        """Validate asset should return download_ready and preview_ready"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "download_ready" in data, "Response should include 'download_ready'"
            assert "preview_ready" in data, "Response should include 'preview_ready'"
            print(f"Asset validation: download_ready={data['download_ready']}, preview_ready={data['preview_ready']}")
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found")
    
    def test_validate_asset_requires_auth(self):
        """Validate asset endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/validate-asset/{COMPLETED_JOB_ID}")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestDownloadEndpoint:
    """Tests for /api/photo-to-comic/download/{job_id} endpoint"""
    
    def test_download_returns_urls_for_completed_job(self, auth_headers):
        """Download endpoint should return downloadUrls for completed job"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/download/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True, "Download should return success=True"
            assert "downloadUrls" in data, "Download should return downloadUrls"
            print(f"Download URLs count: {len(data.get('downloadUrls', []))}")
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found")
        elif response.status_code == 400:
            # Job not ready
            print(f"Job not ready for download: {response.text}")


class TestScriptEndpoint:
    """Tests for /api/photo-to-comic/script/{job_id} endpoint"""
    
    def test_script_returns_script_text(self, auth_headers):
        """Script endpoint should return script text for completed job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/script/{COMPLETED_JOB_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "script" in data, "Response should include 'script' field"
            print(f"Script length: {len(data.get('script', ''))} chars")
        elif response.status_code == 404:
            pytest.skip(f"Job {COMPLETED_JOB_ID} not found or no script")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
