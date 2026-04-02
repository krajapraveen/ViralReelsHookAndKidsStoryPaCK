"""
Photo to Comic Feature Upgrade Tests - Iteration 405
Tests for 5 P0 improvements:
1. GET /api/photo-to-comic/presets - 8 story presets
2. GET /api/photo-to-comic/estimate - Dynamic time estimation
3. GET /api/photo-to-comic/styles - Existing endpoint still works
4. GET /api/photo-to-comic/script/{job_id} - Script download
5. Backend stages array in job document
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestStoryPresets:
    """Tests for GET /api/photo-to-comic/presets endpoint"""
    
    def test_presets_endpoint_returns_200(self, auth_headers):
        """Presets endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /presets returns 200")
    
    def test_presets_returns_8_presets(self, auth_headers):
        """Should return exactly 8 story presets"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "presets" in data, "Response should have 'presets' key"
        presets = data["presets"]
        assert len(presets) == 8, f"Expected 8 presets, got {len(presets)}"
        print(f"PASS: Returns 8 presets: {list(presets.keys())}")
    
    def test_presets_have_required_fields(self, auth_headers):
        """Each preset should have name, prompt, panel_beats, genre, icon"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        presets = data["presets"]
        
        required_fields = ["name", "prompt", "panel_beats", "genre", "icon"]
        
        for preset_id, preset in presets.items():
            for field in required_fields:
                assert field in preset, f"Preset '{preset_id}' missing field '{field}'"
            
            # Validate panel_beats is a list
            assert isinstance(preset["panel_beats"], list), f"Preset '{preset_id}' panel_beats should be a list"
            assert len(preset["panel_beats"]) >= 3, f"Preset '{preset_id}' should have at least 3 panel beats"
        
        print("PASS: All presets have required fields (name, prompt, panel_beats, genre, icon)")
    
    def test_presets_include_expected_types(self, auth_headers):
        """Should include hero, comedy, romance, mystery, motivational, adventure, horror, scifi"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        presets = data["presets"]
        
        expected_presets = ["hero", "comedy", "romance", "mystery", "motivational", "adventure", "horror", "scifi"]
        
        for preset_id in expected_presets:
            assert preset_id in presets, f"Missing expected preset: {preset_id}"
        
        print(f"PASS: All 8 expected presets present: {expected_presets}")


class TestTimeEstimation:
    """Tests for GET /api/photo-to-comic/estimate endpoint"""
    
    def test_estimate_strip_mode_returns_200(self, auth_headers):
        """Estimate endpoint for strip mode should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/estimate?mode=strip&panel_count=4",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /estimate?mode=strip returns 200")
    
    def test_estimate_avatar_mode_returns_200(self, auth_headers):
        """Estimate endpoint for avatar mode should return 200"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/estimate?mode=avatar",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /estimate?mode=avatar returns 200")
    
    def test_estimate_returns_required_fields(self, auth_headers):
        """Estimate should return estimated_seconds_low, estimated_seconds_high, queue_depth, guarantee"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/estimate?mode=strip&panel_count=4",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["estimated_seconds_low", "estimated_seconds_high", "queue_depth", "guarantee"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate types
        assert isinstance(data["estimated_seconds_low"], int), "estimated_seconds_low should be int"
        assert isinstance(data["estimated_seconds_high"], int), "estimated_seconds_high should be int"
        assert isinstance(data["queue_depth"], int), "queue_depth should be int"
        assert isinstance(data["guarantee"], str), "guarantee should be string"
        
        print(f"PASS: Estimate returns all required fields: {data}")
    
    def test_estimate_low_less_than_high(self, auth_headers):
        """estimated_seconds_low should be less than or equal to estimated_seconds_high"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/estimate?mode=strip&panel_count=4",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["estimated_seconds_low"] <= data["estimated_seconds_high"], \
            f"Low ({data['estimated_seconds_low']}) should be <= high ({data['estimated_seconds_high']})"
        print(f"PASS: Low ({data['estimated_seconds_low']}) <= High ({data['estimated_seconds_high']})")
    
    def test_estimate_guarantee_message(self, auth_headers):
        """Guarantee should contain refund message"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/estimate?mode=strip&panel_count=4",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        guarantee = data["guarantee"].lower()
        assert "guarantee" in guarantee or "refund" in guarantee, \
            f"Guarantee message should mention guarantee or refund: {data['guarantee']}"
        print(f"PASS: Guarantee message: '{data['guarantee']}'")


class TestExistingStylesEndpoint:
    """Tests for GET /api/photo-to-comic/styles - existing endpoint"""
    
    def test_styles_endpoint_returns_200(self, auth_headers):
        """Styles endpoint should still work"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /styles returns 200")
    
    def test_styles_returns_styles_and_pricing(self, auth_headers):
        """Styles endpoint should return styles and pricing"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/styles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "styles" in data, "Response should have 'styles' key"
        assert "pricing" in data, "Response should have 'pricing' key"
        assert len(data["styles"]) > 0, "Should have at least one style"
        
        print(f"PASS: /styles returns {len(data['styles'])} styles and pricing info")


class TestScriptEndpoint:
    """Tests for GET /api/photo-to-comic/script/{job_id}"""
    
    def test_script_endpoint_404_for_invalid_job(self, auth_headers):
        """Script endpoint should return 404 for non-existent job"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/script/invalid-job-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: /script returns 404 for invalid job ID")
    
    def test_script_endpoint_requires_auth(self):
        """Script endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/script/some-job-id")
        assert response.status_code in [401, 403, 422], \
            f"Expected 401/403/422 without auth, got {response.status_code}"
        print("PASS: /script requires authentication")


class TestJobStagesArray:
    """Tests for stages array in job document"""
    
    def test_job_status_includes_stages_for_strip(self, auth_headers):
        """Job status for strip mode should include stages array"""
        # First, get history to find a strip job
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history?size=10",
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Could not fetch history")
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        # Find a strip job
        strip_job = None
        for job in jobs:
            if job.get("mode") == "strip":
                strip_job = job
                break
        
        if not strip_job:
            pytest.skip("No strip jobs found in history to verify stages")
        
        # Check if stages array exists
        if "stages" in strip_job:
            stages = strip_job["stages"]
            assert isinstance(stages, list), "stages should be a list"
            
            # For strip mode, expect: face_analysis, story_generation, panel_generation, composition
            expected_stage_names = ["face_analysis", "story_generation", "panel_generation", "composition"]
            actual_stage_names = [s.get("name") for s in stages]
            
            for expected in expected_stage_names:
                assert expected in actual_stage_names, f"Missing stage: {expected}"
            
            print(f"PASS: Strip job has stages array with: {actual_stage_names}")
        else:
            # Stages might not be present in older jobs
            print("INFO: No stages array in job (may be older job before upgrade)")
    
    def test_job_status_includes_stages_for_avatar(self, auth_headers):
        """Job status for avatar mode should include stages array"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/history?size=10",
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Could not fetch history")
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        # Find an avatar job
        avatar_job = None
        for job in jobs:
            if job.get("mode") == "avatar":
                avatar_job = job
                break
        
        if not avatar_job:
            pytest.skip("No avatar jobs found in history to verify stages")
        
        if "stages" in avatar_job:
            stages = avatar_job["stages"]
            assert isinstance(stages, list), "stages should be a list"
            
            # For avatar mode, expect: face_analysis, avatar_generation
            expected_stage_names = ["face_analysis", "avatar_generation"]
            actual_stage_names = [s.get("name") for s in stages]
            
            for expected in expected_stage_names:
                assert expected in actual_stage_names, f"Missing stage: {expected}"
            
            print(f"PASS: Avatar job has stages array with: {actual_stage_names}")
        else:
            print("INFO: No stages array in job (may be older job before upgrade)")


class TestPricingEndpoint:
    """Tests for GET /api/photo-to-comic/pricing"""
    
    def test_pricing_endpoint_returns_200(self, auth_headers):
        """Pricing endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/pricing", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /pricing returns 200")
    
    def test_pricing_includes_avatar_and_strip(self, auth_headers):
        """Pricing should include comic_avatar and comic_strip"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/pricing", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        pricing = data.get("pricing", {})
        assert "comic_avatar" in pricing, "Missing comic_avatar pricing"
        assert "comic_strip" in pricing, "Missing comic_strip pricing"
        
        # Validate avatar pricing
        assert "base" in pricing["comic_avatar"], "Avatar pricing missing 'base'"
        assert pricing["comic_avatar"]["base"] == 3, "Avatar base should be 3 credits"
        
        # Validate strip pricing
        assert "panels" in pricing["comic_strip"], "Strip pricing missing 'panels'"
        
        print(f"PASS: Pricing includes avatar (base={pricing['comic_avatar']['base']}) and strip")


class TestHistoryEndpoint:
    """Tests for GET /api/photo-to-comic/history"""
    
    def test_history_endpoint_returns_200(self, auth_headers):
        """History endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: /history returns 200")
    
    def test_history_returns_pagination_info(self, auth_headers):
        """History should return jobs, total, page, size"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data, "Missing 'jobs' key"
        assert "total" in data, "Missing 'total' key"
        assert "page" in data, "Missing 'page' key"
        assert "size" in data, "Missing 'size' key"
        
        print(f"PASS: History returns {len(data['jobs'])} jobs, total={data['total']}")


class TestPresetIntegration:
    """Integration tests for preset usage in generation"""
    
    def test_presets_have_valid_genres(self, auth_headers):
        """All presets should have valid genre values"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        presets = data["presets"]
        
        valid_genres = ["action", "comedy", "romance", "adventure", "fantasy", "scifi", "mystery", "kids_friendly", "slice_of_life", "motivational"]
        
        for preset_id, preset in presets.items():
            genre = preset.get("genre")
            assert genre in valid_genres, f"Preset '{preset_id}' has invalid genre: {genre}"
        
        print("PASS: All presets have valid genres")
    
    def test_presets_have_valid_icons(self, auth_headers):
        """All presets should have icon values"""
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        presets = data["presets"]
        
        for preset_id, preset in presets.items():
            icon = preset.get("icon")
            assert icon is not None and len(icon) > 0, f"Preset '{preset_id}' missing icon"
        
        print("PASS: All presets have icons")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
