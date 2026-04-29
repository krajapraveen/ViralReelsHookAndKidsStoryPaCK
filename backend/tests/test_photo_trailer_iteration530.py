"""
Photo Trailer (YouStar / My Movie Trailer) P0 Backend Tests - Iteration 530
Tests all backend endpoints for the new photo trailer feature.
"""
import pytest
import requests
import os
import io
from PIL import Image

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Admin login failed: {r.status_code} - {r.text}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip(f"Test user login failed: {r.status_code} - {r.text}")


@pytest.fixture
def auth_headers(test_user_token):
    """Auth headers for test user"""
    return {"Authorization": f"Bearer {test_user_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    """Auth headers for admin"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


def create_test_jpeg(width=1024, height=1024):
    """Create a small test JPEG image"""
    img = Image.new('RGB', (width, height), color=(100, 150, 200))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer.getvalue()


class TestTemplatesEndpoint:
    """GET /api/photo-trailer/templates - returns 9 templates"""
    
    def test_templates_returns_9_templates(self):
        """Templates endpoint returns exactly 9 templates"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "templates" in data
        assert len(data["templates"]) == 9, f"Expected 9 templates, got {len(data['templates'])}"
    
    def test_templates_have_required_fields(self):
        """Each template has id/title/description/tone/narrator/music_mood/scene_count"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert r.status_code == 200
        data = r.json()
        required_fields = ["id", "title", "description", "tone", "narrator", "music_mood", "scene_count"]
        for tpl in data["templates"]:
            for field in required_fields:
                assert field in tpl, f"Template {tpl.get('id', 'unknown')} missing field: {field}"
    
    def test_templates_no_auth_required(self):
        """Templates endpoint is public (no auth required)"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert r.status_code == 200


class TestCreditEstimateEndpoint:
    """GET /api/photo-trailer/credit-estimate - returns credit cost for duration"""
    
    def test_credit_estimate_45s_returns_25(self, auth_headers):
        """45s duration returns 25 credits"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/credit-estimate?duration=45", headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["credits"] == 25, f"Expected 25 credits for 45s, got {data['credits']}"
        assert data["duration_seconds"] == 45
    
    def test_credit_estimate_15s_returns_5(self, auth_headers):
        """15s duration returns 5 credits"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/credit-estimate?duration=15", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["credits"] == 5, f"Expected 5 credits for 15s, got {data['credits']}"
    
    def test_credit_estimate_20s_returns_5(self, auth_headers):
        """20s duration returns 5 credits"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/credit-estimate?duration=20", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["credits"] == 5, f"Expected 5 credits for 20s, got {data['credits']}"
    
    def test_credit_estimate_60s_returns_35(self, auth_headers):
        """60s duration returns 35 credits"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/credit-estimate?duration=60", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["credits"] == 35, f"Expected 35 credits for 60s, got {data['credits']}"
    
    def test_credit_estimate_requires_auth(self):
        """Credit estimate requires authentication"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/credit-estimate?duration=45")
        assert r.status_code in [401, 403], f"Expected 401/403 without auth, got {r.status_code}"


class TestUploadInitEndpoint:
    """POST /api/photo-trailer/uploads/init - validates and creates upload session"""
    
    def test_upload_init_success(self, auth_headers):
        """Valid init request returns upload_session_id"""
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 3,
            "mime_types": ["image/jpeg", "image/png", "image/webp"],
            "file_sizes": [500000, 600000, 700000]
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "upload_session_id" in data
        assert data["max_photos"] == 10
        assert data["max_bytes"] == 10 * 1024 * 1024
    
    def test_upload_init_rejects_over_10_photos(self, auth_headers):
        """Rejects file_count > 10 with 400"""
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 11,
            "mime_types": ["image/jpeg"] * 11,
            "file_sizes": [500000] * 11
        })
        assert r.status_code == 400, f"Expected 400 for >10 photos, got {r.status_code}"
        assert "maximum of 10" in r.text.lower() or "10 photos" in r.text.lower()
    
    def test_upload_init_rejects_invalid_mime(self, auth_headers):
        """Rejects unsupported mime types"""
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/gif"],
            "file_sizes": [500000]
        })
        assert r.status_code == 400, f"Expected 400 for invalid mime, got {r.status_code}"
        assert "unsupported" in r.text.lower() or "jpg" in r.text.lower()
    
    def test_upload_init_rejects_oversized_file(self, auth_headers):
        """Rejects files over 10MB"""
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [15 * 1024 * 1024]  # 15MB
        })
        assert r.status_code == 400, f"Expected 400 for oversized file, got {r.status_code}"
        assert "10mb" in r.text.lower() or "smaller" in r.text.lower()
    
    def test_upload_init_requires_auth(self):
        """Upload init requires authentication"""
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [500000]
        })
        assert r.status_code in [401, 403], f"Expected 401/403 without auth, got {r.status_code}"


class TestUploadPhotoEndpoint:
    """POST /api/photo-trailer/uploads/photo - uploads a photo to R2"""
    
    def test_upload_photo_success(self, auth_headers):
        """Upload a valid JPEG returns asset_id and storage_url"""
        # First create a session
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        assert init_r.status_code == 200
        session_id = init_r.json()["upload_session_id"]
        
        # Upload a photo
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        result = r.json()
        assert "asset_id" in result
        assert "storage_url" in result
        assert result["width"] == 1024
        assert result["height"] == 1024


class TestUploadCompleteEndpoint:
    """POST /api/photo-trailer/uploads/complete - finalizes upload with consent"""
    
    def test_upload_complete_rejects_no_consent(self, auth_headers):
        """Rejects consent_confirmed=false with 400"""
        # Create session and upload a photo first
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        assert init_r.status_code == 200
        session_id = init_r.json()["upload_session_id"]
        
        # Upload a photo
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        
        # Try to complete without consent
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=auth_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": False
        })
        assert r.status_code == 400, f"Expected 400 for no consent, got {r.status_code}"
        assert "confirm" in r.text.lower() or "consent" in r.text.lower()
    
    def test_upload_complete_success_with_consent(self, auth_headers):
        """Succeeds with consent_confirmed=true and >=1 photo"""
        # Create session and upload a photo
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        assert init_r.status_code == 200
        session_id = init_r.json()["upload_session_id"]
        
        # Upload a photo
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        
        # Complete with consent
        r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=auth_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": True
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("success") == True


class TestJobCreationEndpoint:
    """POST /api/photo-trailer/jobs - creates a trailer generation job"""
    
    def test_job_creation_rejects_invalid_template(self, auth_headers):
        """Rejects unknown template_id with 400"""
        # Create and complete a session first
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        session_id = init_r.json()["upload_session_id"]
        
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        upload_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        asset_id = upload_r.json()["asset_id"]
        
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=auth_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": True
        })
        
        # Try to create job with invalid template
        r = requests.post(f"{BASE_URL}/api/photo-trailer/jobs", headers=auth_headers, json={
            "upload_session_id": session_id,
            "hero_asset_id": asset_id,
            "template_id": "invalid_template_xyz",
            "duration_target_seconds": 15
        })
        assert r.status_code == 400, f"Expected 400 for invalid template, got {r.status_code}"
        assert "invalid" in r.text.lower() or "template" in r.text.lower()
    
    def test_job_creation_rejects_hero_not_in_session(self, auth_headers):
        """Rejects hero_asset_id not in upload session"""
        # Create and complete a session
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        session_id = init_r.json()["upload_session_id"]
        
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=auth_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": True
        })
        
        # Try to create job with fake hero_asset_id
        r = requests.post(f"{BASE_URL}/api/photo-trailer/jobs", headers=auth_headers, json={
            "upload_session_id": session_id,
            "hero_asset_id": "fake-asset-id-12345",
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        })
        assert r.status_code == 400, f"Expected 400 for invalid hero, got {r.status_code}"
        assert "hero" in r.text.lower() or "uploaded" in r.text.lower()
    
    def test_job_creation_rejects_incomplete_session(self, auth_headers):
        """Rejects job creation if session not COMPLETED"""
        # Create session but don't complete it
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=auth_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        session_id = init_r.json()["upload_session_id"]
        
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": auth_headers["Authorization"]}
        upload_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        asset_id = upload_r.json()["asset_id"]
        
        # Try to create job without completing session
        r = requests.post(f"{BASE_URL}/api/photo-trailer/jobs", headers=auth_headers, json={
            "upload_session_id": session_id,
            "hero_asset_id": asset_id,
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        })
        assert r.status_code == 400, f"Expected 400 for incomplete session, got {r.status_code}"
        assert "consent" in r.text.lower() or "finalised" in r.text.lower() or "completed" in r.text.lower()


class TestJobCreationWithAdmin:
    """Job creation tests using admin account (unlimited credits)"""
    
    def test_job_creation_success_returns_queued(self, admin_headers):
        """Valid job creation returns job_id and status QUEUED"""
        # Create and complete a session
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=admin_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        assert init_r.status_code == 200
        session_id = init_r.json()["upload_session_id"]
        
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": admin_headers["Authorization"]}
        upload_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        assert upload_r.status_code == 200
        asset_id = upload_r.json()["asset_id"]
        
        complete_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=admin_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": True
        })
        assert complete_r.status_code == 200
        
        # Create job
        r = requests.post(f"{BASE_URL}/api/photo-trailer/jobs", headers=admin_headers, json={
            "upload_session_id": session_id,
            "hero_asset_id": asset_id,
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "QUEUED"
        assert data["estimated_credits"] == 5  # 15s = 5 credits


class TestGetJobEndpoint:
    """GET /api/photo-trailer/jobs/{job_id} - returns job status"""
    
    def test_get_job_returns_job_without_id(self, admin_headers):
        """Job response excludes _id field"""
        # Create a job first
        init_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", headers=admin_headers, json={
            "file_count": 1,
            "mime_types": ["image/jpeg"],
            "file_sizes": [50000]
        })
        session_id = init_r.json()["upload_session_id"]
        
        jpeg_data = create_test_jpeg()
        files = {"file": ("test_photo.jpg", jpeg_data, "image/jpeg")}
        data = {"upload_session_id": session_id}
        upload_headers = {"Authorization": admin_headers["Authorization"]}
        upload_r = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo", headers=upload_headers, files=files, data=data)
        asset_id = upload_r.json()["asset_id"]
        
        requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete", headers=admin_headers, json={
            "upload_session_id": session_id,
            "consent_confirmed": True
        })
        
        job_r = requests.post(f"{BASE_URL}/api/photo-trailer/jobs", headers=admin_headers, json={
            "upload_session_id": session_id,
            "hero_asset_id": asset_id,
            "template_id": "birthday_movie",
            "duration_target_seconds": 15
        })
        job_id = job_r.json()["job_id"]
        
        # Get job status
        r = requests.get(f"{BASE_URL}/api/photo-trailer/jobs/{job_id}", headers=admin_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "_id" not in data, "Response should not contain _id"
        assert "current_stage" in data
        assert "progress_percent" in data
        assert "status" in data


class TestMyTrailersEndpoint:
    """GET /api/photo-trailer/my-trailers - returns user's trailers"""
    
    def test_my_trailers_returns_list(self, auth_headers):
        """Returns trailers list without crash"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/my-trailers", headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "trailers" in data
        assert isinstance(data["trailers"], list)


class TestAdminOverviewEndpoint:
    """GET /api/photo-trailer/admin/overview - admin-only metrics"""
    
    def test_admin_overview_returns_metrics(self, admin_headers):
        """Admin overview returns expected metrics structure"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/admin/overview", headers=admin_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        expected_fields = [
            "total_uploads", "total_jobs", "completed", "failed",
            "completion_pct", "by_template", "failure_stage_breakdown", "avg_credits_charged"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_admin_overview_rejects_non_admin(self, auth_headers):
        """Non-admin users get 403"""
        r = requests.get(f"{BASE_URL}/api/photo-trailer/admin/overview", headers=auth_headers)
        assert r.status_code == 403, f"Expected 403 for non-admin, got {r.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
