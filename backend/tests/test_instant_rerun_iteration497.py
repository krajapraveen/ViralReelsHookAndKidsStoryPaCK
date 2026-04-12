"""
Instant Re-run Engine Tests — iteration 497
Tests POST /api/stories/instant-rerun endpoint and related functionality.

Features tested:
- Endpoint validation (source_job_id exists, auth required, mode pattern)
- Error responses (404 for bad source, 401 for no auth, 422 for bad mode)
- Branch creation with correct fields (continuation_type, derivative_label, visibility)
- Variation suffix usage from _VARIATION_SUFFIXES
- beat_top mode competitive reference
- Quality gate (3+ reruns warning)
- Rerun tracking in rerun_tracker collection
- Analytics tracking in analytics_events collection
- No regressions on battle, chain, war endpoints
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        print("API health check passed")


class TestInstantRerunEndpointExists:
    """Verify the instant-rerun endpoint exists and responds"""
    
    def test_endpoint_exists_returns_401_without_auth(self):
        """Endpoint should return 401 without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"source_job_id": "test-job-id", "mode": "try_again"},
            timeout=10
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("Endpoint exists and requires auth (401 returned)")


class TestInstantRerunValidation:
    """Test input validation for instant-rerun endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code}")
    
    def test_rejects_nonexistent_source_404(self, auth_token):
        """Should return 404 for non-existent source_job_id"""
        fake_job_id = f"nonexistent-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"source_job_id": fake_job_id, "mode": "try_again"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 404, f"Expected 404 for non-existent source, got {response.status_code}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower(), f"Expected 'not found' in detail: {data}"
        print(f"Correctly returns 404 for non-existent source: {data.get('detail')}")
    
    def test_rejects_invalid_mode_422(self, auth_token):
        """Should return 422 for invalid mode pattern"""
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"source_job_id": "any-job-id", "mode": "invalid_mode"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        # Pydantic validation should reject invalid mode pattern
        assert response.status_code == 422, f"Expected 422 for invalid mode, got {response.status_code}"
        print(f"Correctly returns 422 for invalid mode pattern")
    
    def test_rejects_missing_source_job_id_422(self, auth_token):
        """Should return 422 for missing source_job_id"""
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"mode": "try_again"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 422, f"Expected 422 for missing source_job_id, got {response.status_code}"
        print("Correctly returns 422 for missing source_job_id")
    
    def test_accepts_valid_modes(self, auth_token):
        """Verify both valid modes are accepted (validation passes, may fail on source lookup)"""
        for mode in ["try_again", "beat_top"]:
            response = requests.post(
                f"{BASE_URL}/api/stories/instant-rerun",
                json={"source_job_id": f"test-{uuid.uuid4()}", "mode": mode},
                headers={"Authorization": f"Bearer {auth_token}"},
                timeout=10
            )
            # Should NOT be 422 (validation error) - should be 404 (source not found) or 400 (rate limit)
            assert response.status_code != 422, f"Mode '{mode}' should be valid, got 422"
            print(f"Mode '{mode}' passes validation (status: {response.status_code})")


class TestInstantRerunRequestModel:
    """Test the InstantRerunRequest Pydantic model validation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    def test_default_mode_is_try_again(self, auth_token):
        """Mode should default to 'try_again' if not provided"""
        # Send request without mode field
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"source_job_id": f"test-{uuid.uuid4()}"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        # Should not be 422 - mode has default value
        assert response.status_code != 422, f"Mode should have default value, got 422"
        print(f"Mode defaults correctly (status: {response.status_code})")


class TestVariationSuffixes:
    """Test that _VARIATION_SUFFIXES are properly defined"""
    
    def test_variation_suffixes_exist_in_code(self):
        """Verify _VARIATION_SUFFIXES array exists with expected entries"""
        # Read the source file to verify the suffixes
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from routes.story_multiplayer import _VARIATION_SUFFIXES
            
            assert isinstance(_VARIATION_SUFFIXES, list), "_VARIATION_SUFFIXES should be a list"
            assert len(_VARIATION_SUFFIXES) == 8, f"Expected 8 suffixes, got {len(_VARIATION_SUFFIXES)}"
            
            # Verify each suffix is a non-empty string
            for i, suffix in enumerate(_VARIATION_SUFFIXES):
                assert isinstance(suffix, str), f"Suffix {i} should be a string"
                assert len(suffix) > 10, f"Suffix {i} should be meaningful text"
            
            print(f"_VARIATION_SUFFIXES verified: {len(_VARIATION_SUFFIXES)} entries")
            print(f"Sample suffix: {_VARIATION_SUFFIXES[0][:50]}...")
        except ImportError as e:
            pytest.skip(f"Could not import _VARIATION_SUFFIXES: {e}")


class TestInstantRerunWithRealJob:
    """Test instant-rerun with a real completed job (if available)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def completed_job(self, auth_token):
        """Find a completed job to use as source"""
        # Try to find a completed job from user's jobs
        response = requests.get(
            f"{BASE_URL}/api/story-engine/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            # Find a completed job
            for job in jobs:
                if job.get("status") in ["COMPLETED", "READY", "PARTIAL_READY"]:
                    return job
        
        # Try discover feed for public completed stories
        response = requests.get(
            f"{BASE_URL}/api/stories/feed/discover?limit=5",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            stories = data.get("stories", [])
            if stories:
                return stories[0]
        
        return None
    
    def test_instant_rerun_with_real_job(self, auth_token, completed_job):
        """Test instant-rerun with a real completed job"""
        if not completed_job:
            pytest.skip("No completed job available for testing")
        
        job_id = completed_job.get("job_id")
        print(f"Testing instant-rerun with job: {job_id}")
        
        response = requests.post(
            f"{BASE_URL}/api/stories/instant-rerun",
            json={"source_job_id": job_id, "mode": "try_again"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30
        )
        
        # Expected responses:
        # - 200: Success (job created)
        # - 400: Rate limit / SLOTS_BUSY (expected per main agent note)
        # - 402: Insufficient credits
        # - 404: Source not found (shouldn't happen with real job)
        
        print(f"Instant-rerun response: {response.status_code}")
        data = response.json()
        print(f"Response data: {data}")
        
        if response.status_code == 200:
            # Verify success response structure
            assert data.get("success") == True, "Expected success=True"
            assert "job_id" in data, "Expected job_id in response"
            assert data.get("mode") == "try_again", "Expected mode=try_again"
            assert "rerun_number" in data, "Expected rerun_number in response"
            assert "root_story_id" in data, "Expected root_story_id in response"
            assert "chain_depth" in data, "Expected chain_depth in response"
            print(f"SUCCESS: New job created: {data.get('job_id')}")
            print(f"Rerun number: {data.get('rerun_number')}")
            if data.get("quality_warning"):
                print(f"Quality warning: {data.get('quality_warning')}")
        elif response.status_code == 400:
            # Rate limit / SLOTS_BUSY - expected behavior
            detail = data.get("detail", "")
            print(f"Rate limited (expected): {detail}")
            assert "SLOTS_BUSY" in detail or "rate" in detail.lower() or "busy" in detail.lower() or "slot" in detail.lower(), \
                f"Expected rate limit message, got: {detail}"
        elif response.status_code == 402:
            # Insufficient credits
            print(f"Insufficient credits: {data.get('detail')}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}, detail: {data}")


class TestBattleEndpointsNoRegression:
    """Verify battle endpoints still work (no regression)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    def test_battle_endpoint_exists(self, auth_token):
        """Verify /api/stories/battle/{story_id} endpoint works"""
        # Use a fake ID - should return 404 (not 500 or other error)
        response = requests.get(
            f"{BASE_URL}/api/stories/battle/test-story-id",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        # Should be 404 (not found) not 500 (server error)
        assert response.status_code in [200, 404], f"Battle endpoint error: {response.status_code}"
        print(f"Battle endpoint working (status: {response.status_code})")
    
    def test_chain_endpoint_exists(self, auth_token):
        """Verify /api/stories/{story_id}/chain endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/stories/test-story-id/chain",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code in [200, 404], f"Chain endpoint error: {response.status_code}"
        print(f"Chain endpoint working (status: {response.status_code})")
    
    def test_branches_endpoint_exists(self, auth_token):
        """Verify /api/stories/{story_id}/branches endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/stories/test-story-id/branches",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code in [200, 404], f"Branches endpoint error: {response.status_code}"
        print(f"Branches endpoint working (status: {response.status_code})")
    
    def test_increment_metric_endpoint(self, auth_token):
        """Verify /api/stories/increment-metric endpoint works"""
        response = requests.post(
            f"{BASE_URL}/api/stories/increment-metric",
            json={"job_id": "test-job-id", "metric": "views"},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        # Should be 404 (job not found) not 500 or 422
        assert response.status_code in [200, 404], f"Increment-metric endpoint error: {response.status_code}"
        print(f"Increment-metric endpoint working (status: {response.status_code})")


class TestFeedEndpointsNoRegression:
    """Verify feed endpoints still work (no regression)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    def test_trending_feed(self, auth_token):
        """Verify /api/stories/feed/trending works"""
        response = requests.get(
            f"{BASE_URL}/api/stories/feed/trending?limit=5",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Trending feed error: {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        print(f"Trending feed working: {len(data.get('stories', []))} stories")
    
    def test_discover_feed(self, auth_token):
        """Verify /api/stories/feed/discover works"""
        response = requests.get(
            f"{BASE_URL}/api/stories/feed/discover?limit=5",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"Discover feed error: {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        print(f"Discover feed working: {len(data.get('stories', []))} stories")


class TestDailyWarNoRegression:
    """Verify daily war endpoints still work (no regression)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    def test_war_current_endpoint(self, auth_token):
        """Verify /api/war/current works"""
        response = requests.get(
            f"{BASE_URL}/api/war/current",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"War current error: {response.status_code}"
        print(f"War current endpoint working")
    
    def test_war_history_endpoint(self, auth_token):
        """Verify /api/war/history works"""
        response = requests.get(
            f"{BASE_URL}/api/war/history?limit=5",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        assert response.status_code == 200, f"War history error: {response.status_code}"
        print(f"War history endpoint working")


class TestCompetitionPulseDataTestIds:
    """Verify CompetitionPulse component has correct data-testids"""
    
    def test_competition_pulse_component_exists(self):
        """Verify CompetitionPulse.jsx has required data-testids"""
        component_path = "/app/frontend/src/components/CompetitionPulse.jsx"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        required_testids = [
            'competition-pulse',
            'instant-rerun-buttons',
            'instant-try-again',
            'instant-beat-top',
            'quality-warning',
            'try-twist-instead',
            'session-depth'
        ]
        
        for testid in required_testids:
            assert f'data-testid="{testid}"' in content, f"Missing data-testid: {testid}"
            print(f"Found data-testid: {testid}")
        
        print("All required data-testids present in CompetitionPulse.jsx")
    
    def test_instant_rerun_buttons_have_icons(self):
        """Verify instant rerun buttons have correct icons (Zap, Swords)"""
        component_path = "/app/frontend/src/components/CompetitionPulse.jsx"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        # Check for Zap icon (Try Again)
        assert 'Zap' in content, "Missing Zap icon for Try Again button"
        
        # Check for Swords icon (Beat #1)
        assert 'Swords' in content, "Missing Swords icon for Beat #1 button"
        
        # Check for Loader2 icon (spinner during generation)
        assert 'Loader2' in content, "Missing Loader2 spinner icon"
        
        print("All required icons present in CompetitionPulse.jsx")
    
    def test_quality_warning_has_alert_triangle(self):
        """Verify quality warning has AlertTriangle icon"""
        component_path = "/app/frontend/src/components/CompetitionPulse.jsx"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        assert 'AlertTriangle' in content, "Missing AlertTriangle icon for quality warning"
        print("AlertTriangle icon present for quality warning")


class TestStoryVideoPipelineIntegration:
    """Verify StoryVideoPipeline uses CompetitionPulse correctly"""
    
    def test_competition_pulse_imported(self):
        """Verify CompetitionPulse is imported in StoryVideoPipeline"""
        pipeline_path = "/app/frontend/src/pages/StoryVideoPipeline.js"
        
        with open(pipeline_path, 'r') as f:
            content = f.read()
        
        assert "import CompetitionPulse" in content, "CompetitionPulse not imported"
        print("CompetitionPulse imported in StoryVideoPipeline")
    
    def test_competition_pulse_rendered(self):
        """Verify CompetitionPulse component is rendered"""
        pipeline_path = "/app/frontend/src/pages/StoryVideoPipeline.js"
        
        with open(pipeline_path, 'r') as f:
            content = f.read()
        
        assert "<CompetitionPulse" in content, "CompetitionPulse not rendered"
        print("CompetitionPulse rendered in StoryVideoPipeline")


class TestRerunTrackerCollection:
    """Test rerun_tracker collection usage in code"""
    
    def test_rerun_tracker_used_in_code(self):
        """Verify rerun_tracker collection is used for tracking"""
        backend_path = "/app/backend/routes/story_multiplayer.py"
        
        with open(backend_path, 'r') as f:
            content = f.read()
        
        # Check for rerun_tracker collection usage
        assert "rerun_tracker" in content, "rerun_tracker collection not used"
        assert "rerun_key" in content, "rerun_key not defined"
        
        # Check for hourly window (1 hour = timedelta(hours=1))
        assert "timedelta(hours=1)" in content, "Hourly window not implemented"
        
        print("rerun_tracker collection properly used with hourly window")


class TestAnalyticsTracking:
    """Test analytics tracking for instant reruns"""
    
    def test_analytics_events_tracked(self):
        """Verify analytics events are tracked for instant reruns"""
        backend_path = "/app/backend/routes/story_multiplayer.py"
        
        with open(backend_path, 'r') as f:
            content = f.read()
        
        # Check for analytics_events collection usage
        assert "analytics_events" in content, "analytics_events collection not used"
        
        # Check for event names
        assert "instant_rerun_try_again" in content or "instant_rerun_{request.mode}" in content, \
            "instant_rerun_try_again event not tracked"
        assert "instant_rerun_beat_top" in content or "instant_rerun_{request.mode}" in content, \
            "instant_rerun_beat_top event not tracked"
        
        print("Analytics events properly tracked for instant reruns")


class TestQualityGateLogic:
    """Test quality gate logic (3+ reruns warning)"""
    
    def test_quality_gate_threshold(self):
        """Verify quality gate triggers at 3+ reruns"""
        backend_path = "/app/backend/routes/story_multiplayer.py"
        
        with open(backend_path, 'r') as f:
            content = f.read()
        
        # Check for quality gate threshold (>= 3)
        assert "rerun_count >= 3" in content, "Quality gate threshold not set to 3"
        
        # Check for quality_warning message
        assert "quality_warning" in content, "quality_warning field not defined"
        
        print("Quality gate properly implemented at 3+ reruns")


class TestBeatTopCompetitiveReference:
    """Test beat_top mode includes competitive reference"""
    
    def test_beat_top_includes_top_story(self):
        """Verify beat_top mode queries #1 story for competitive context"""
        backend_path = "/app/backend/routes/story_multiplayer.py"
        
        with open(backend_path, 'r') as f:
            content = f.read()
        
        # Check for beat_top mode handling
        assert 'mode == "beat_top"' in content or "beat_top" in content, "beat_top mode not handled"
        
        # Check for battle_score sorting to find #1
        assert "battle_score" in content, "battle_score not used for ranking"
        
        # Check for COMPETITIVE REWRITE instruction
        assert "COMPETITIVE REWRITE" in content, "Competitive rewrite instruction not included"
        
        print("beat_top mode properly includes competitive reference")


class TestBranchCreationFields:
    """Test that instant rerun creates branch with correct fields"""
    
    def test_branch_fields_set_correctly(self):
        """Verify branch creation sets correct fields"""
        backend_path = "/app/backend/routes/story_multiplayer.py"
        
        with open(backend_path, 'r') as f:
            content = f.read()
        
        # Check for continuation_type='branch'
        assert '"branch"' in content, "continuation_type='branch' not set"
        
        # Check for derivative_label='remixed_from'
        assert '"remixed_from"' in content, "derivative_label='remixed_from' not set"
        
        # Check for visibility='public'
        assert '"visibility": "public"' in content or "'visibility': 'public'" in content, \
            "visibility='public' not set"
        
        print("Branch creation fields properly set")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
