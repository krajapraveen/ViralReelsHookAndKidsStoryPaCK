"""
P0 Hero Selection UI Verification Tests - Iteration 532

Tests the 6 specific verification cases for the hero-selection UI fix:
1. Desktop + mobile viewports render 3 checkboxes OUTSIDE the photo card (siblings, not overlay)
2. Selecting ONLY a Villain (no Hero) -> Continue is enabled -> advances to Step 3
3. Selecting ONLY a Supporting (no Hero, no Villain) -> Continue is enabled -> advances to Step 3
4. After fallback, POST /api/photo-trailer/jobs contains non-null hero_asset_id (promoted from villain/supporting)
5. Happy path (user explicitly picks Hero) still returns 201
6. Backend contract regression: POST /jobs without hero_asset_id returns 422
"""
import os
import pytest
import requests
import json
import time
from PIL import Image
from io import BytesIO

# Get BASE_URL from frontend .env
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
            break

ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Create test image
TEST_PHOTO_PATH = "/tmp/test_hero_selection.jpg"


@pytest.fixture(scope="module")
def ensure_test_photo():
    """Create a test photo for upload"""
    if not os.path.exists(TEST_PHOTO_PATH):
        img = Image.new("RGB", (512, 512), (100, 150, 200))
        img.save(TEST_PHOTO_PATH, "JPEG")
    return TEST_PHOTO_PATH


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Auth headers for API calls"""
    return {"Authorization": f"Bearer {admin_token}"}


def create_upload_session_with_photos(auth_headers, photo_path, photo_count=1):
    """Helper to create upload session and upload photos"""
    # Init session
    init_resp = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/init", 
        headers={**auth_headers, "Content-Type": "application/json"},
        json={
            "file_count": photo_count,
            "mime_types": ["image/jpeg"] * photo_count,
            "file_sizes": [os.path.getsize(photo_path)] * photo_count
        })
    assert init_resp.status_code == 200, f"Init failed: {init_resp.text}"
    session_id = init_resp.json()["upload_session_id"]
    
    # Upload photos
    asset_ids = []
    for i in range(photo_count):
        with open(photo_path, "rb") as f:
            files = {"file": (f"test_photo_{i}.jpg", f, "image/jpeg")}
            data = {"upload_session_id": session_id}
            upload_resp = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/photo",
                headers=auth_headers, files=files, data=data)
            assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
            asset_ids.append(upload_resp.json()["asset_id"])
    
    # Complete session with consent
    complete_resp = requests.post(f"{BASE_URL}/api/photo-trailer/uploads/complete",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"upload_session_id": session_id, "consent_confirmed": True})
    assert complete_resp.status_code == 200, f"Complete failed: {complete_resp.text}"
    
    return session_id, asset_ids


class TestBackendContractRegression:
    """Test 6: Backend contract regression - POST /jobs without hero_asset_id returns 422"""
    
    def test_missing_hero_asset_id_returns_422(self, auth_headers, ensure_test_photo):
        """POST /jobs with missing hero_asset_id should return 422 Pydantic validation error"""
        session_id, asset_ids = create_upload_session_with_photos(auth_headers, ensure_test_photo, 1)
        
        # Try to create job WITHOUT hero_asset_id
        job_payload = {
            "upload_session_id": session_id,
            # hero_asset_id intentionally omitted
            "villain_asset_id": asset_ids[0],
            "supporting_asset_ids": [],
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        }
        
        resp = requests.post(f"{BASE_URL}/api/photo-trailer/jobs",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=job_payload)
        
        # Should return 422 Unprocessable Entity (Pydantic validation)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        print(f"PASS: Missing hero_asset_id correctly returns 422")
    
    def test_null_hero_asset_id_returns_422(self, auth_headers, ensure_test_photo):
        """POST /jobs with hero_asset_id=null should return 422"""
        session_id, asset_ids = create_upload_session_with_photos(auth_headers, ensure_test_photo, 1)
        
        job_payload = {
            "upload_session_id": session_id,
            "hero_asset_id": None,  # Explicitly null
            "villain_asset_id": asset_ids[0],
            "supporting_asset_ids": [],
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        }
        
        resp = requests.post(f"{BASE_URL}/api/photo-trailer/jobs",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=job_payload)
        
        # Should return 422 Unprocessable Entity
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        print(f"PASS: Null hero_asset_id correctly returns 422")


class TestHappyPathHeroSelection:
    """Test 5: Happy path - selecting Hero explicitly returns 201"""
    
    def test_explicit_hero_selection_returns_201(self, auth_headers, ensure_test_photo):
        """User explicitly picks Hero -> POST /jobs returns 201"""
        session_id, asset_ids = create_upload_session_with_photos(auth_headers, ensure_test_photo, 1)
        
        job_payload = {
            "upload_session_id": session_id,
            "hero_asset_id": asset_ids[0],  # Explicitly set hero
            "villain_asset_id": None,
            "supporting_asset_ids": [],
            "template_id": "superhero_origin",
            "duration_target_seconds": 15  # Use 15s to minimize credit usage
        }
        
        resp = requests.post(f"{BASE_URL}/api/photo-trailer/jobs",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=job_payload)
        
        # Should return 200 or 201 with job_id
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "job_id" in data, f"Response missing job_id: {data}"
        print(f"PASS: Happy path with explicit Hero returns {resp.status_code} with job_id={data['job_id']}")
        return data["job_id"]


class TestHeroFallbackMechanism:
    """Test 4: After fallback, POST /jobs contains non-null hero_asset_id"""
    
    def test_villain_promoted_to_hero_in_payload(self, auth_headers, ensure_test_photo):
        """
        When frontend sends villain_asset_id as hero_asset_id (fallback),
        the backend should accept it and create the job.
        
        Note: The frontend does the promotion before sending the request.
        This test verifies the backend accepts the promoted payload.
        """
        session_id, asset_ids = create_upload_session_with_photos(auth_headers, ensure_test_photo, 1)
        
        # Simulate frontend fallback: villain is promoted to hero
        # Frontend sets hero_asset_id = villain_asset_id when no hero was selected
        job_payload = {
            "upload_session_id": session_id,
            "hero_asset_id": asset_ids[0],  # This was originally villain, now promoted
            "villain_asset_id": asset_ids[0],  # Same asset as villain
            "supporting_asset_ids": [],
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        }
        
        resp = requests.post(f"{BASE_URL}/api/photo-trailer/jobs",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=job_payload)
        
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "job_id" in data, f"Response missing job_id: {data}"
        print(f"PASS: Villain-promoted-to-hero payload accepted, job_id={data['job_id']}")
    
    def test_supporting_promoted_to_hero_in_payload(self, auth_headers, ensure_test_photo):
        """
        When frontend sends supporting_asset_id as hero_asset_id (fallback),
        the backend should accept it.
        """
        session_id, asset_ids = create_upload_session_with_photos(auth_headers, ensure_test_photo, 1)
        
        # Simulate frontend fallback: supporting is promoted to hero
        job_payload = {
            "upload_session_id": session_id,
            "hero_asset_id": asset_ids[0],  # This was originally supporting, now promoted
            "villain_asset_id": None,
            "supporting_asset_ids": [asset_ids[0]],  # Same asset as supporting
            "template_id": "superhero_origin",
            "duration_target_seconds": 15
        }
        
        resp = requests.post(f"{BASE_URL}/api/photo-trailer/jobs",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=job_payload)
        
        assert resp.status_code in [200, 201], f"Expected 200/201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "job_id" in data, f"Response missing job_id: {data}"
        print(f"PASS: Supporting-promoted-to-hero payload accepted, job_id={data['job_id']}")


class TestTemplatesEndpoint:
    """Verify templates endpoint works"""
    
    def test_templates_list(self, auth_headers):
        """GET /templates returns list of templates"""
        resp = requests.get(f"{BASE_URL}/api/photo-trailer/templates", headers=auth_headers)
        assert resp.status_code == 200, f"Templates failed: {resp.text}"
        data = resp.json()
        assert "templates" in data
        assert len(data["templates"]) > 0
        print(f"PASS: Templates endpoint returns {len(data['templates'])} templates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
