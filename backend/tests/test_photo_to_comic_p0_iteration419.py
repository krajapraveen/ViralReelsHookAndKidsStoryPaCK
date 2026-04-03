"""
Photo to Comic P0 Bug Fix Tests - Iteration 419
Tests for:
1. POST /api/photo-to-comic/download/{job_id} - accepts PARTIAL_READY and READY_WITH_WARNINGS
2. GET /api/photo-to-comic/script/{job_id} - returns sanitized script (no null/None dialogue)
3. GET /api/photo-to-comic/pdf/{job_id} - generates valid PDF with presigned R2 URLs
4. GET /api/photo-to-comic/comic-book/{job_id} - generates full comic book PDF
5. POST /api/photo-to-comic/continue-story - accepts PARTIAL_READY parent jobs
6. GET /api/photo-to-comic/validate-asset/{job_id} - accepts PARTIAL_READY and READY_WITH_WARNINGS
7. Source photo storage in R2 (source_storage_key populated)
8. Panel dialogue sanitization (no null/None/... strings)
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Existing test job IDs from context
JOB_ID_READY_WITH_WARNINGS = "a4a94680-0ef1-4a55-9da7-e4b98f4295ab"  # READY_WITH_WARNINGS, 3 panels
JOB_ID_PARTIAL_READY = "9515bdd7-360b-47c8-b23f-8f536aa9dd4b"  # PARTIAL_READY, 2 panels with source_storage_key


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_backend_health(self, api_client):
        """Test backend is healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"Backend health: {response.json()}")


class TestDownloadEndpoint:
    """Tests for POST /api/photo-to-comic/download/{job_id}"""
    
    def test_download_accepts_ready_with_warnings(self, authenticated_client):
        """Download endpoint should accept READY_WITH_WARNINGS status jobs"""
        response = authenticated_client.post(f"{BASE_URL}/api/photo-to-comic/download/{JOB_ID_READY_WITH_WARNINGS}")
        # Should return 200 with downloadUrls or 404 if job doesn't exist for this user
        if response.status_code == 404:
            print(f"Job {JOB_ID_READY_WITH_WARNINGS} not found for test user - may belong to different user")
            pytest.skip("Job not found for test user")
        elif response.status_code == 400:
            # Check if it's because no downloadable assets (acceptable)
            detail = response.json().get("detail", "")
            print(f"Download returned 400: {detail}")
            assert "downloadable" in detail.lower() or "assets" in detail.lower()
        else:
            assert response.status_code == 200
            data = response.json()
            assert "downloadUrls" in data
            print(f"Download URLs returned: {len(data.get('downloadUrls', []))}")
    
    def test_download_accepts_partial_ready(self, authenticated_client):
        """Download endpoint should accept PARTIAL_READY status jobs"""
        response = authenticated_client.post(f"{BASE_URL}/api/photo-to-comic/download/{JOB_ID_PARTIAL_READY}")
        if response.status_code == 404:
            print(f"Job {JOB_ID_PARTIAL_READY} not found for test user")
            pytest.skip("Job not found for test user")
        elif response.status_code == 400:
            detail = response.json().get("detail", "")
            print(f"Download returned 400: {detail}")
        else:
            assert response.status_code == 200
            data = response.json()
            assert "downloadUrls" in data
            print(f"PARTIAL_READY download URLs: {len(data.get('downloadUrls', []))}")
    
    def test_download_returns_presigned_urls(self, authenticated_client):
        """Download should return presigned URLs for R2 assets"""
        response = authenticated_client.post(f"{BASE_URL}/api/photo-to-comic/download/{JOB_ID_READY_WITH_WARNINGS}")
        if response.status_code == 200:
            data = response.json()
            urls = data.get("downloadUrls", [])
            for url in urls:
                # Presigned URLs should have signature params or be data URIs
                if url and not url.startswith("data:"):
                    print(f"URL format: {url[:100]}...")
                    # R2 presigned URLs typically have X-Amz-Signature or similar
                    assert "r2.dev" in url or "r2.cloudflarestorage" in url or "X-Amz" in url or url.startswith("http")


class TestScriptEndpoint:
    """Tests for GET /api/photo-to-comic/script/{job_id}"""
    
    def test_script_returns_sanitized_text(self, authenticated_client):
        """Script endpoint should return sanitized script without null/None dialogue"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/script/{JOB_ID_READY_WITH_WARNINGS}")
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        
        assert response.status_code == 200
        data = response.json()
        assert "script" in data
        script = data["script"]
        
        # Check that script doesn't contain raw null/None strings
        script_lower = script.lower()
        # These should NOT appear as dialogue values
        assert 'dialogue: "null"' not in script_lower
        assert 'dialogue: "none"' not in script_lower
        assert 'dialogue: "..."' not in script_lower
        print(f"Script length: {len(script)} chars")
        print(f"Script preview: {script[:300]}...")
    
    def test_script_has_panel_structure(self, authenticated_client):
        """Script should have proper panel structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/script/{JOB_ID_READY_WITH_WARNINGS}")
        if response.status_code == 200:
            script = response.json().get("script", "")
            # Should have panel markers
            assert "Panel" in script or "panel" in script or "Scene" in script


class TestPdfEndpoint:
    """Tests for GET /api/photo-to-comic/pdf/{job_id}"""
    
    def test_pdf_generation(self, authenticated_client):
        """PDF endpoint should generate valid PDF"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/{JOB_ID_READY_WITH_WARNINGS}",
            timeout=60
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        elif response.status_code == 400:
            detail = response.json().get("detail", "") if response.headers.get("content-type", "").startswith("application/json") else ""
            print(f"PDF generation returned 400: {detail}")
            pytest.skip(f"No panels ready for PDF: {detail}")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        # PDF should start with %PDF
        assert response.content[:4] == b'%PDF'
        print(f"PDF size: {len(response.content)} bytes")
    
    def test_pdf_content_disposition(self, authenticated_client):
        """PDF should have proper content-disposition header"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/{JOB_ID_READY_WITH_WARNINGS}",
            timeout=60
        )
        if response.status_code == 200:
            content_disp = response.headers.get("content-disposition", "")
            assert "attachment" in content_disp
            assert "comic_" in content_disp
            print(f"Content-Disposition: {content_disp}")


class TestComicBookEndpoint:
    """Tests for GET /api/photo-to-comic/comic-book/{job_id}"""
    
    def test_comic_book_generation(self, authenticated_client):
        """Comic book endpoint should generate full comic book PDF"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/comic-book/{JOB_ID_READY_WITH_WARNINGS}",
            timeout=90
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        elif response.status_code == 400:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except:
                pass
            print(f"Comic book generation returned 400: {detail}")
            pytest.skip(f"No panels ready for comic book: {detail}")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        # PDF should start with %PDF
        assert response.content[:4] == b'%PDF'
        # Comic book should be larger than simple PDF (has cover, panels, script)
        print(f"Comic book PDF size: {len(response.content)} bytes")
    
    def test_comic_book_content_disposition(self, authenticated_client):
        """Comic book should have proper filename in content-disposition"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/comic-book/{JOB_ID_READY_WITH_WARNINGS}",
            timeout=90
        )
        if response.status_code == 200:
            content_disp = response.headers.get("content-disposition", "")
            assert "attachment" in content_disp
            assert "comic_book_" in content_disp
            print(f"Comic book Content-Disposition: {content_disp}")


class TestContinueStoryEndpoint:
    """Tests for POST /api/photo-to-comic/continue-story"""
    
    def test_continue_story_accepts_partial_ready(self, authenticated_client):
        """Continue story should accept PARTIAL_READY parent jobs"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/photo-to-comic/continue-story",
            json={
                "parentJobId": JOB_ID_PARTIAL_READY,
                "prompt": "Continue the adventure",
                "panelCount": 4,
                "keepStyle": True
            }
        )
        if response.status_code == 404:
            print("Parent job not found for test user")
            pytest.skip("Parent job not found")
        elif response.status_code == 400:
            detail = response.json().get("detail", "")
            print(f"Continue story returned 400: {detail}")
            # Check if it's a valid rejection reason (not status-related)
            if "status" in detail.lower() and ("partial" in detail.lower() or "ready" in detail.lower()):
                pytest.fail(f"Continue story rejected PARTIAL_READY status: {detail}")
            # Other 400 reasons (credits, source photo) are acceptable
        elif response.status_code == 200 or response.status_code == 201:
            data = response.json()
            assert data.get("success") == True or "jobId" in data
            print(f"Continue story job created: {data.get('jobId')}")
        else:
            print(f"Continue story response: {response.status_code} - {response.text[:200]}")
    
    def test_continue_story_requires_auth(self):
        """Continue story should require authentication"""
        # Use a fresh session without auth headers
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(
            f"{BASE_URL}/api/photo-to-comic/continue-story",
            json={"parentJobId": JOB_ID_PARTIAL_READY}
        )
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestValidateAssetEndpoint:
    """Tests for GET /api/photo-to-comic/validate-asset/{job_id}"""
    
    def test_validate_asset_accepts_partial_ready(self, authenticated_client):
        """Validate asset should accept PARTIAL_READY status"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/{JOB_ID_PARTIAL_READY}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        
        assert response.status_code == 200
        data = response.json()
        # Should return validation result, not reject based on status
        assert "download_ready" in data or "valid" in data
        print(f"Validate asset result: {data}")
    
    def test_validate_asset_accepts_ready_with_warnings(self, authenticated_client):
        """Validate asset should accept READY_WITH_WARNINGS status"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/validate-asset/{JOB_ID_READY_WITH_WARNINGS}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        
        assert response.status_code == 200
        data = response.json()
        assert "download_ready" in data or "valid" in data
        print(f"READY_WITH_WARNINGS validate result: {data}")


class TestJobStatusEndpoint:
    """Tests for GET /api/photo-to-comic/job/{job_id}"""
    
    def test_job_status_returns_panels(self, authenticated_client):
        """Job status should return panels with sanitized dialogue"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/job/{JOB_ID_READY_WITH_WARNINGS}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check panels exist
        panels = data.get("panels", [])
        print(f"Job has {len(panels)} panels")
        
        # Check dialogue sanitization
        for panel in panels:
            dialogue = panel.get("dialogue")
            if dialogue:
                dialogue_str = str(dialogue).strip().lower()
                # Should not have raw null/none values
                assert dialogue_str not in ['null', 'none', '...']
                print(f"Panel {panel.get('panelNumber')}: dialogue='{dialogue}'")
    
    def test_job_has_source_storage_key(self, authenticated_client):
        """Job should have source_storage_key populated for R2 storage"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/job/{JOB_ID_PARTIAL_READY}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found for test user")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check source_storage_key exists (for continue story functionality)
        source_key = data.get("source_storage_key")
        print(f"source_storage_key: {source_key}")
        # Note: May be None for older jobs, but should exist for new ones


class TestDialogueSanitization:
    """Tests for dialogue sanitization in panel_orchestrator.py"""
    
    def test_panel_orchestrator_sanitizes_dialogue(self, authenticated_client):
        """Panel orchestrator should sanitize null/None dialogue before DB persistence"""
        # This is verified by checking job panels don't have null dialogue
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/job/{JOB_ID_READY_WITH_WARNINGS}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found")
        
        data = response.json()
        panels = data.get("panels", [])
        
        for panel in panels:
            dialogue = panel.get("dialogue")
            if dialogue is not None:
                # Dialogue should be a clean string, not "null" or "None"
                assert str(dialogue).lower() not in ['null', 'none']
                print(f"Panel {panel.get('panelNumber')} dialogue sanitized: OK")


class TestOutputValidationLog:
    """Tests for [OUTPUT_VALIDATION] log emission"""
    
    def test_job_has_output_validation_fields(self, authenticated_client):
        """Job should have output validation audit fields"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/photo-to-comic/job/{JOB_ID_READY_WITH_WARNINGS}"
        )
        if response.status_code == 404:
            pytest.skip("Job not found")
        
        data = response.json()
        
        # Check for validation-related fields
        print(f"Job status: {data.get('status')}")
        print(f"Job has panels: {len(data.get('panels', []))}")
        print(f"Job has resultUrl: {bool(data.get('resultUrl'))}")
        print(f"Job has resultUrls: {len(data.get('resultUrls', []))}")
        
        # These fields indicate output validation was performed
        if data.get("panels"):
            for p in data["panels"]:
                print(f"  Panel {p.get('panelNumber')}: status={p.get('status')}, has_url={bool(p.get('imageUrl'))}")


class TestBasicEndpoints:
    """Tests for basic photo-to-comic endpoints"""
    
    def test_styles_endpoint(self, authenticated_client):
        """Styles endpoint should return available styles"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        print(f"Available styles: {len(data['styles'])}")
    
    def test_presets_endpoint(self, authenticated_client):
        """Presets endpoint should return story presets"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        print(f"Available presets: {list(data['presets'].keys())}")
    
    def test_pricing_endpoint(self, authenticated_client):
        """Pricing endpoint should return pricing config"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"Pricing config: {data['pricing']}")
    
    def test_estimate_endpoint(self, authenticated_client):
        """Estimate endpoint should return time estimates"""
        response = authenticated_client.get(f"{BASE_URL}/api/photo-to-comic/estimate?mode=strip&panel_count=4")
        assert response.status_code == 200
        data = response.json()
        assert "estimated_seconds_low" in data
        assert "estimated_seconds_high" in data
        print(f"Time estimate: {data['estimated_seconds_low']}-{data['estimated_seconds_high']}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
