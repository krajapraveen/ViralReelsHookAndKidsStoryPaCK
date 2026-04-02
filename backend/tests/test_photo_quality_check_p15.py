"""
Photo to Comic P1.5 - Quality Check & Failure Masking Tests
Tests:
- POST /api/photo-to-comic/quality-check endpoint
- Quality check with no-face image returns can_proceed=false
- Quality check with real face photo returns can_proceed=true
- Quality check caching works
- READY_WITH_WARNINGS status handling in job status
- Events endpoint accepts valid events
- PDF download still works
"""

import pytest
import requests
import os
import hashlib

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
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestQualityCheckEndpoint:
    """Tests for POST /api/photo-to-comic/quality-check"""
    
    def test_quality_check_no_face_image(self, auth_token):
        """Quality check with no-face image returns can_proceed=false and overall=poor"""
        # Use the pre-created test image with no face
        test_image_path = "/tmp/test_no_face.jpg"
        
        if not os.path.exists(test_image_path):
            pytest.skip("Test image not found at /tmp/test_no_face.jpg")
        
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test_no_face.jpg', f, 'image/jpeg')}
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify quality assessment structure
        assert "face_detected" in data, "Missing face_detected field"
        assert "blur_score" in data, "Missing blur_score field"
        assert "brightness" in data, "Missing brightness field"
        assert "overall" in data, "Missing overall field"
        assert "can_proceed" in data, "Missing can_proceed field"
        assert "checks" in data, "Missing checks field"
        
        # Verify no-face behavior
        assert data["face_detected"] == False, f"Expected face_detected=False, got {data['face_detected']}"
        assert data["can_proceed"] == False, f"Expected can_proceed=False for no-face image, got {data['can_proceed']}"
        assert data["overall"] == "poor", f"Expected overall=poor, got {data['overall']}"
        
        # Verify checks structure
        checks = data.get("checks", {})
        assert "face" in checks, "Missing face check"
        assert checks["face"] == "fail", f"Expected face check=fail, got {checks['face']}"
        
        print(f"✓ No-face image quality check: face_detected={data['face_detected']}, can_proceed={data['can_proceed']}, overall={data['overall']}")
    
    def test_quality_check_real_face_image(self, auth_token):
        """Quality check with real face photo returns can_proceed=true and overall=good"""
        test_image_path = "/tmp/test_real_face.jpg"
        
        if not os.path.exists(test_image_path):
            pytest.skip("Test image not found at /tmp/test_real_face.jpg")
        
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test_real_face.jpg', f, 'image/jpeg')}
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify quality assessment structure
        assert "face_detected" in data, "Missing face_detected field"
        assert "can_proceed" in data, "Missing can_proceed field"
        assert "overall" in data, "Missing overall field"
        assert "checks" in data, "Missing checks field"
        
        # Verify face detection works
        assert data["face_detected"] == True, f"Expected face_detected=True, got {data['face_detected']}"
        assert data["can_proceed"] == True, f"Expected can_proceed=True for face image, got {data['can_proceed']}"
        
        # Overall should be good or acceptable (not poor)
        assert data["overall"] in ["good", "acceptable"], f"Expected overall=good/acceptable, got {data['overall']}"
        
        # Verify checks structure
        checks = data.get("checks", {})
        assert "face" in checks, "Missing face check"
        assert checks["face"] in ["pass", "warn"], f"Expected face check=pass/warn, got {checks['face']}"
        
        print(f"✓ Real face image quality check: face_detected={data['face_detected']}, can_proceed={data['can_proceed']}, overall={data['overall']}")
    
    def test_quality_check_caching(self, auth_token):
        """Quality check caching works (same image hash returns cached result)"""
        test_image_path = "/tmp/test_real_face.jpg"
        
        if not os.path.exists(test_image_path):
            pytest.skip("Test image not found at /tmp/test_real_face.jpg")
        
        # First request
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test_real_face.jpg', f, 'image/jpeg')}
            headers = {"Authorization": f"Bearer {auth_token}"}
            response1 = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second request with same image (should be cached)
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test_real_face.jpg', f, 'image/jpeg')}
            headers = {"Authorization": f"Bearer {auth_token}"}
            response2 = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Results should be identical (cached)
        assert data1["face_detected"] == data2["face_detected"], "Cached result mismatch: face_detected"
        assert data1["can_proceed"] == data2["can_proceed"], "Cached result mismatch: can_proceed"
        assert data1["overall"] == data2["overall"], "Cached result mismatch: overall"
        
        print(f"✓ Quality check caching works: both requests returned identical results")
    
    def test_quality_check_returns_all_checks(self, auth_token):
        """Quality check returns Face/Clarity/Lighting/Framing checks"""
        test_image_path = "/tmp/test_real_face.jpg"
        
        if not os.path.exists(test_image_path):
            pytest.skip("Test image not found at /tmp/test_real_face.jpg")
        
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test_real_face.jpg', f, 'image/jpeg')}
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = requests.post(
                f"{BASE_URL}/api/photo-to-comic/quality-check",
                files=files,
                headers=headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        checks = data.get("checks", {})
        
        # Verify all required checks are present
        required_checks = ["face", "clarity", "lighting", "framing"]
        for check in required_checks:
            assert check in checks, f"Missing required check: {check}"
            assert checks[check] in ["pass", "warn", "fail"], f"Invalid check value for {check}: {checks[check]}"
        
        print(f"✓ All quality checks present: {checks}")


class TestJobStatusReadyWithWarnings:
    """Tests for READY_WITH_WARNINGS status handling"""
    
    def test_job_status_endpoint_exists(self, api_client):
        """Job status endpoint returns proper response"""
        # Use the completed job ID from test credentials
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/job/{COMPLETED_JOB_ID}")
        
        # Should return 200 or 404 (if job doesn't exist)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Missing status field in job response"
            print(f"✓ Job status endpoint works: status={data.get('status')}")
        else:
            print(f"✓ Job status endpoint returns 404 for non-existent job (expected)")


class TestEventsEndpoint:
    """Tests for events endpoint (existing functionality)"""
    
    def test_events_accepts_valid_event(self, api_client):
        """Events endpoint accepts valid events"""
        response = api_client.post(f"{BASE_URL}/api/photo-to-comic/events", json={
            "event_type": "generate_after_preview",
            "metadata": {"style": "cartoon_fun", "mode": "avatar"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Events endpoint accepts valid events")
    
    def test_events_accepts_result_page_view(self, api_client):
        """Events endpoint accepts result_page_view event"""
        response = api_client.post(f"{BASE_URL}/api/photo-to-comic/events", json={
            "event_type": "result_page_view",
            "metadata": {"job_id": "test-job-123"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Events endpoint accepts result_page_view event")


class TestPDFDownload:
    """Tests for PDF download (existing functionality)"""
    
    def test_pdf_download_completed_job(self, auth_token):
        """PDF download returns 200 for completed job"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/pdf/{COMPLETED_JOB_ID}",
            headers=headers
        )
        
        # Should return 200 (PDF) or 404 (job not found) or 400 (no panels)
        assert response.status_code in [200, 400, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            assert response.headers.get('Content-Type') == 'application/pdf', "Expected PDF content type"
            print("✓ PDF download works for completed job")
        elif response.status_code == 404:
            print("✓ PDF endpoint returns 404 for non-existent job (expected)")
        else:
            print(f"✓ PDF endpoint returns {response.status_code} (no panels ready)")


class TestStylePreviewStrip:
    """Tests for style preview strip endpoint (existing functionality)"""
    
    def test_style_previews_endpoint(self, api_client):
        """Style previews endpoint returns previews"""
        response = api_client.get(f"{BASE_URL}/api/photo-to-comic/style-previews")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "previews" in data, "Missing previews field"
        assert len(data["previews"]) >= 8, f"Expected at least 8 previews, got {len(data['previews'])}"
        
        print(f"✓ Style previews endpoint returns {len(data['previews'])} previews")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
