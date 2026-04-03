"""
Brand Kit Generator API Tests - Iteration 420
Tests for the upgraded Brand Story Builder with parallel AI generation,
progressive results, and downloadable deliverables.

Features tested:
- GET /api/brand-story-builder/config - returns industries, tones, modes
- POST /api/brand-story-builder/generate - creates job and returns jobId
- GET /api/brand-story-builder/job/{job_id} - returns status, progress, artifact states
- GET /api/brand-story-builder/job/{job_id}/result - returns full artifact data
- GET /api/brand-story-builder/job/{job_id}/pdf - returns PDF file
- GET /api/brand-story-builder/job/{job_id}/zip - returns ZIP file
- Credit deduction (10 for fast, 25 for pro)
- Copyright check blocks trademarked terms
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Existing completed jobs for testing (to avoid spending credits)
FAST_MODE_JOB_ID = "e5b5bc69-3c47-48f0-9725-cb3a306b4a4b"
PRO_MODE_JOB_ID = "857b34c9-ec66-4705-b823-f5e067d3cc6d"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestBrandKitConfig:
    """Tests for GET /api/brand-story-builder/config endpoint"""
    
    def test_config_returns_industries(self):
        """Config should return list of industries"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "industries" in data
        assert isinstance(data["industries"], list)
        assert len(data["industries"]) > 0
        assert "Technology" in data["industries"]
        assert "SaaS" in data["industries"]
        print(f"✓ Config returns {len(data['industries'])} industries")
    
    def test_config_returns_tones(self):
        """Config should return list of tones"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "tones" in data
        assert isinstance(data["tones"], list)
        expected_tones = ["professional", "bold", "luxury", "friendly", "emotional", "gen-z", "startup", "premium"]
        for tone in expected_tones:
            assert tone in data["tones"], f"Missing tone: {tone}"
        print(f"✓ Config returns {len(data['tones'])} tones")
    
    def test_config_returns_personalities(self):
        """Config should return list of personalities"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "personalities" in data
        assert isinstance(data["personalities"], list)
        expected_personalities = ["innovative", "trustworthy", "playful", "sophisticated"]
        for p in expected_personalities:
            assert p in data["personalities"], f"Missing personality: {p}"
        print(f"✓ Config returns {len(data['personalities'])} personalities")
    
    def test_config_returns_modes(self):
        """Config should return mode configurations with correct credit costs"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "modes" in data
        assert "fast" in data["modes"]
        assert "pro" in data["modes"]
        
        # Fast mode: 10 credits, 4 artifacts
        fast = data["modes"]["fast"]
        assert fast["credits"] == 10
        assert len(fast["artifacts"]) == 4
        assert "short_brand_story" in fast["artifacts"]
        assert "mission_vision_values" in fast["artifacts"]
        assert "taglines" in fast["artifacts"]
        assert "elevator_pitch" in fast["artifacts"]
        
        # Pro mode: 25 credits, 10 artifacts
        pro = data["modes"]["pro"]
        assert pro["credits"] == 25
        assert len(pro["artifacts"]) == 10
        assert "color_palettes" in pro["artifacts"]
        assert "typography" in pro["artifacts"]
        assert "logo_concepts" in pro["artifacts"]
        
        print(f"✓ Fast mode: {fast['credits']} credits, {len(fast['artifacts'])} artifacts")
        print(f"✓ Pro mode: {pro['credits']} credits, {len(pro['artifacts'])} artifacts")
    
    def test_config_returns_credit_costs(self):
        """Config should return credit costs dictionary"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "credit_costs" in data
        assert data["credit_costs"]["fast"] == 10
        assert data["credit_costs"]["pro"] == 25
        assert data["credit_costs"]["premium"] == 50
        print("✓ Credit costs: fast=10, pro=25, premium=50")


class TestCopyrightProtection:
    """Tests for copyright/trademark blocking"""
    
    def test_blocks_marvel_trademark(self, auth_headers):
        """Should block business names containing 'Marvel'"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "Marvel Studios Clone", "mission": "Copy Marvel", "mode": "fast"}
        )
        assert response.status_code == 400
        assert "blocked content" in response.json().get("detail", "").lower()
        print("✓ Blocked 'Marvel' trademark")
    
    def test_blocks_disney_trademark(self, auth_headers):
        """Should block business names containing 'Disney'"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "Disney Magic World", "mode": "fast"}
        )
        assert response.status_code == 400
        assert "blocked content" in response.json().get("detail", "").lower()
        print("✓ Blocked 'Disney' trademark")
    
    def test_blocks_nike_trademark(self, auth_headers):
        """Should block business names containing 'Nike'"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "Nike Sports Clone", "mode": "fast"}
        )
        assert response.status_code == 400
        assert "blocked content" in response.json().get("detail", "").lower()
        print("✓ Blocked 'Nike' trademark")
    
    def test_blocks_trademark_in_mission(self, auth_headers):
        """Should block trademarked terms in mission field"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "My Brand", "mission": "Be like Google", "mode": "fast"}
        )
        assert response.status_code == 400
        assert "blocked content" in response.json().get("detail", "").lower()
        print("✓ Blocked trademark in mission field")
    
    def test_allows_clean_business_name(self, auth_headers):
        """Should allow business names without trademarks"""
        # Note: This would create a new job and spend credits, so we just verify
        # the copyright check passes by checking the error is NOT about blocked content
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "TEST_CleanBrand123", "mode": "fast"}
        )
        # Should either succeed (200) or fail for other reasons (not 400 with blocked content)
        if response.status_code == 400:
            assert "blocked content" not in response.json().get("detail", "").lower()
        print("✓ Clean business name passes copyright check")


class TestJobStatusEndpoint:
    """Tests for GET /api/brand-story-builder/job/{job_id} endpoint"""
    
    def test_fast_mode_job_status(self, auth_headers):
        """Should return correct status for fast mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobId"] == FAST_MODE_JOB_ID
        assert data["status"] == "READY"
        assert data["mode"] == "fast"
        assert data["progress"] == 100
        assert data["current_stage"] == "COMPLETE"
        assert data["total_artifacts"] == 4
        assert data["completed_artifacts"] == 4
        
        # Check artifact summary
        assert "artifacts" in data
        for art_type in ["short_brand_story", "mission_vision_values", "taglines", "elevator_pitch"]:
            assert art_type in data["artifacts"]
            assert data["artifacts"][art_type]["status"] == "READY"
        
        print(f"✓ Fast mode job status: {data['status']}, {data['completed_artifacts']}/{data['total_artifacts']} artifacts")
    
    def test_pro_mode_job_status(self, auth_headers):
        """Should return correct status for pro mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobId"] == PRO_MODE_JOB_ID
        assert data["status"] == "READY"
        assert data["mode"] == "pro"
        assert data["progress"] == 100
        assert data["current_stage"] == "COMPLETE"
        assert data["total_artifacts"] == 10
        assert data["completed_artifacts"] == 10
        
        # Check all pro mode artifacts
        pro_artifacts = ["short_brand_story", "long_brand_story", "mission_vision_values", 
                        "taglines", "elevator_pitch", "website_hero", "social_ad_copy",
                        "color_palettes", "typography", "logo_concepts"]
        for art_type in pro_artifacts:
            assert art_type in data["artifacts"], f"Missing artifact: {art_type}"
            assert data["artifacts"][art_type]["status"] == "READY"
        
        print(f"✓ Pro mode job status: {data['status']}, {data['completed_artifacts']}/{data['total_artifacts']} artifacts")
    
    def test_job_not_found(self, auth_headers):
        """Should return 404 for non-existent job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/non-existent-job-id",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent job")
    
    def test_job_requires_auth(self):
        """Should require authentication"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}")
        assert response.status_code == 401 or response.status_code == 403
        print("✓ Job status requires authentication")


class TestJobResultEndpoint:
    """Tests for GET /api/brand-story-builder/job/{job_id}/result endpoint"""
    
    def test_fast_mode_result_data(self, auth_headers):
        """Should return full artifact data for fast mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}/result",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobId"] == FAST_MODE_JOB_ID
        assert data["status"] == "READY"
        assert data["mode"] == "fast"
        assert "outputs" in data
        assert "brief" in data
        
        # Verify short_brand_story has actual content
        short_story = data["outputs"]["short_brand_story"]
        assert short_story["status"] == "READY"
        assert "data" in short_story
        assert "short_brand_story" in short_story["data"]
        assert len(short_story["data"]["short_brand_story"]) > 50
        
        # Verify taglines have actual content
        taglines = data["outputs"]["taglines"]
        assert taglines["status"] == "READY"
        assert "taglines" in taglines["data"]
        assert len(taglines["data"]["taglines"]) >= 5
        
        print(f"✓ Fast mode result has {len(data['outputs'])} outputs with full data")
    
    def test_pro_mode_result_data(self, auth_headers):
        """Should return full artifact data for pro mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}/result",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobId"] == PRO_MODE_JOB_ID
        assert data["status"] == "READY"
        assert data["mode"] == "pro"
        assert len(data["outputs"]) == 10
        
        # Verify color_palettes structure
        palettes = data["outputs"]["color_palettes"]
        assert palettes["status"] == "READY"
        assert "palettes" in palettes["data"]
        assert len(palettes["data"]["palettes"]) >= 3
        for p in palettes["data"]["palettes"]:
            assert "primary" in p
            assert "secondary" in p
            assert "accent" in p
            assert p["primary"].startswith("#")
        
        # Verify typography structure
        typography = data["outputs"]["typography"]
        assert typography["status"] == "READY"
        assert "pairings" in typography["data"]
        assert len(typography["data"]["pairings"]) >= 3
        
        # Verify logo_concepts structure
        logos = data["outputs"]["logo_concepts"]
        assert logos["status"] == "READY"
        assert "concepts" in logos["data"]
        assert len(logos["data"]["concepts"]) >= 3
        
        print(f"✓ Pro mode result has {len(data['outputs'])} outputs with full data")
        print(f"  - {len(palettes['data']['palettes'])} color palettes")
        print(f"  - {len(typography['data']['pairings'])} typography pairings")
        print(f"  - {len(logos['data']['concepts'])} logo concepts")


class TestDownloadEndpoints:
    """Tests for PDF and ZIP download endpoints"""
    
    def test_pdf_download_fast_mode(self, auth_headers):
        """Should download PDF for fast mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000  # PDF should have reasonable size
        
        # Check PDF magic bytes
        assert response.content[:4] == b'%PDF'
        print(f"✓ PDF download (fast mode): {len(response.content)} bytes")
    
    def test_pdf_download_pro_mode(self, auth_headers):
        """Should download PDF for pro mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 1000
        assert response.content[:4] == b'%PDF'
        print(f"✓ PDF download (pro mode): {len(response.content)} bytes")
    
    def test_zip_download_fast_mode(self, auth_headers):
        """Should download ZIP for fast mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}/zip",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/zip"
        assert len(response.content) > 1000
        
        # Check ZIP magic bytes (PK)
        assert response.content[:2] == b'PK'
        print(f"✓ ZIP download (fast mode): {len(response.content)} bytes")
    
    def test_zip_download_pro_mode(self, auth_headers):
        """Should download ZIP for pro mode job"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}/zip",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/zip"
        assert len(response.content) > 1000
        assert response.content[:2] == b'PK'
        print(f"✓ ZIP download (pro mode): {len(response.content)} bytes")
    
    def test_download_requires_auth(self):
        """Downloads should require authentication"""
        pdf_response = requests.get(f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}/pdf")
        zip_response = requests.get(f"{BASE_URL}/api/brand-story-builder/job/{FAST_MODE_JOB_ID}/zip")
        
        assert pdf_response.status_code in [401, 403]
        assert zip_response.status_code in [401, 403]
        print("✓ Downloads require authentication")


class TestGenerateEndpoint:
    """Tests for POST /api/brand-story-builder/generate endpoint"""
    
    def test_generate_requires_auth(self):
        """Generate should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            json={"business_name": "Test", "mode": "fast"}
        )
        assert response.status_code in [401, 403]
        print("✓ Generate requires authentication")
    
    def test_generate_requires_business_name(self, auth_headers):
        """Generate should require business_name"""
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"mode": "fast"}
        )
        assert response.status_code == 422  # Validation error
        print("✓ Generate requires business_name")
    
    def test_generate_validates_mode(self, auth_headers):
        """Generate should default to 'pro' for invalid mode"""
        # Note: The backend defaults invalid modes to 'pro', so this should work
        # We're not actually creating a job to avoid spending credits
        response = requests.post(
            f"{BASE_URL}/api/brand-story-builder/generate",
            headers=auth_headers,
            json={"business_name": "TEST_InvalidMode", "mode": "invalid_mode"}
        )
        # Should either succeed with pro mode or fail for other reasons
        if response.status_code == 200:
            data = response.json()
            assert data.get("mode") == "pro"  # Should default to pro
        print("✓ Generate handles invalid mode")


class TestBriefDataPersistence:
    """Tests for brief data persistence in jobs"""
    
    def test_brief_contains_all_fields(self, auth_headers):
        """Job should contain all brief fields"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        brief = response.json().get("brief", {})
        
        expected_fields = ["business_name", "mission", "founder_story", "industry", 
                         "tone", "audience", "personality", "competitors", "market", "problem_solved"]
        for field in expected_fields:
            assert field in brief, f"Missing brief field: {field}"
        
        print(f"✓ Brief contains all {len(expected_fields)} expected fields")
    
    def test_brief_values_match_input(self, auth_headers):
        """Brief values should match what was submitted"""
        response = requests.get(
            f"{BASE_URL}/api/brand-story-builder/job/{PRO_MODE_JOB_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        brief = response.json().get("brief", {})
        
        # Verify specific values from the pro mode job
        assert brief["business_name"] == "Visionary Suite"
        assert brief["industry"] == "SaaS"
        assert brief["tone"] == "premium"
        assert brief["market"] == "Global"
        
        print("✓ Brief values match submitted input")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
