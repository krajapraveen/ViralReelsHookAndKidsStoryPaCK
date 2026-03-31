"""
P1.1 Continue/Remix Optimization — Dependency-aware checkpoint reuse tests.
Tests the analyze-reuse endpoint and create endpoint with parent_video_id.

Features tested:
1. GET /api/story-engine/analyze-reuse endpoint
2. Style Remix analysis (animation_style change)
3. Voice Remix analysis (voice_preset change)
4. No-change analysis (full_reuse mode)
5. POST /api/story-engine/create with parent_video_id returns reuse info
6. GET /api/story-engine/status/{job_id} returns reuse_info field
7. analyze-reuse rejects non-existent parent_job_id with 404
8. State machine allows INIT to transition to any active state
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Known job_id from DB for testing (state=READY, style_id=cartoon_2d)
KNOWN_JOB_ID = "99f9cd11-a1d8-4909-9ed7-04a0320a2820"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Admin authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestAnalyzeReuseEndpoint:
    """Tests for GET /api/story-engine/analyze-reuse endpoint."""

    def test_analyze_reuse_endpoint_exists(self, api_client):
        """Test that analyze-reuse endpoint exists and returns proper structure."""
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={"parent_job_id": KNOWN_JOB_ID}
        )
        # Should return 200 or 404 (if job not found), not 405 (method not allowed)
        assert response.status_code in [200, 403, 404], f"Unexpected status: {response.status_code}"
        print(f"analyze-reuse endpoint response: {response.status_code}")

    def test_analyze_reuse_returns_required_fields(self, admin_client):
        """Test that analyze-reuse returns reuse_mode, reusable_stages, invalidated_stages, estimated_time_saved_percent."""
        response = admin_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={"parent_job_id": KNOWN_JOB_ID}
        )
        
        if response.status_code == 404:
            pytest.skip(f"Known job {KNOWN_JOB_ID} not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] == True, f"Request failed: {data}"
        assert "reuse_mode" in data, "Response missing 'reuse_mode' field"
        assert "reusable_stages" in data, "Response missing 'reusable_stages' field"
        assert "invalidated_stages" in data, "Response missing 'invalidated_stages' field"
        assert "estimated_time_saved_percent" in data, "Response missing 'estimated_time_saved_percent' field"
        
        print(f"analyze-reuse response: reuse_mode={data['reuse_mode']}, "
              f"reusable_stages={len(data['reusable_stages'])}, "
              f"invalidated_stages={len(data['invalidated_stages'])}, "
              f"estimated_time_saved={data['estimated_time_saved_percent']}%")

    def test_analyze_reuse_style_remix(self, admin_client):
        """Test Style Remix: changing animation_style identifies correct reusable/invalidated stages."""
        response = admin_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={
                "parent_job_id": KNOWN_JOB_ID,
                "animation_style": "anime_style"  # Different from parent's cartoon_2d
            }
        )
        
        if response.status_code == 404:
            pytest.skip(f"Known job {KNOWN_JOB_ID} not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # For style remix: PLANNING, CHARACTER, MOTION, AUDIO should be reusable
        # KEYFRAMES, CLIPS, ASSEMBLY should be invalidated
        reusable_ids = [s.get("id") for s in data.get("reusable_stages", [])]
        invalidated_ids = [s.get("id") for s in data.get("invalidated_stages", [])]
        
        print(f"Style Remix - Reusable: {reusable_ids}")
        print(f"Style Remix - Invalidated: {invalidated_ids}")
        
        # Verify reuse mode is style_remix or partial_remix
        assert data["reuse_mode"] in ["style_remix", "partial_remix"], \
            f"Expected style_remix or partial_remix, got {data['reuse_mode']}"
        
        # PLANNING should be reusable (story didn't change)
        assert "PLANNING" in reusable_ids, "PLANNING should be reusable for style remix"
        
        # GENERATING_KEYFRAMES should be invalidated (style changed)
        assert "GENERATING_KEYFRAMES" in invalidated_ids, "GENERATING_KEYFRAMES should be invalidated for style remix"

    def test_analyze_reuse_voice_remix(self, admin_client):
        """Test Voice Remix: changing voice_preset identifies correct reusable/invalidated stages."""
        response = admin_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={
                "parent_job_id": KNOWN_JOB_ID,
                "voice_preset": "narrator_dramatic"  # Different voice
            }
        )
        
        if response.status_code == 404:
            pytest.skip(f"Known job {KNOWN_JOB_ID} not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        reusable_ids = [s.get("id") for s in data.get("reusable_stages", [])]
        invalidated_ids = [s.get("id") for s in data.get("invalidated_stages", [])]
        
        print(f"Voice Remix - Reusable: {reusable_ids}")
        print(f"Voice Remix - Invalidated: {invalidated_ids}")
        
        # For voice remix: PLANNING, CHARACTER, MOTION, KEYFRAMES, CLIPS should be reusable
        # AUDIO, ASSEMBLY should be invalidated
        assert data["reuse_mode"] in ["voice_remix", "partial_remix"], \
            f"Expected voice_remix or partial_remix, got {data['reuse_mode']}"
        
        # Visual stages should be reusable
        assert "GENERATING_KEYFRAMES" in reusable_ids or "GENERATING_SCENE_CLIPS" in reusable_ids, \
            "Visual stages should be reusable for voice remix"
        
        # GENERATING_AUDIO should be invalidated
        assert "GENERATING_AUDIO" in invalidated_ids, "GENERATING_AUDIO should be invalidated for voice remix"

    def test_analyze_reuse_no_change_full_reuse(self, admin_client):
        """Test No-change analysis: returns full_reuse mode with all 7 stages reusable."""
        response = admin_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={"parent_job_id": KNOWN_JOB_ID}
            # No animation_style or voice_preset changes
        )
        
        if response.status_code == 404:
            pytest.skip(f"Known job {KNOWN_JOB_ID} not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        print(f"No-change - reuse_mode: {data['reuse_mode']}")
        print(f"No-change - Reusable stages: {len(data.get('reusable_stages', []))}")
        print(f"No-change - Invalidated stages: {len(data.get('invalidated_stages', []))}")
        
        # With no changes, should be full_reuse
        assert data["reuse_mode"] == "full_reuse", \
            f"Expected full_reuse for no changes, got {data['reuse_mode']}"
        
        # All 7 stages should be reusable
        assert len(data.get("reusable_stages", [])) == 7, \
            f"Expected 7 reusable stages for full_reuse, got {len(data.get('reusable_stages', []))}"
        
        # No stages should be invalidated
        assert len(data.get("invalidated_stages", [])) == 0, \
            f"Expected 0 invalidated stages for full_reuse, got {len(data.get('invalidated_stages', []))}"
        
        # Time saved should be 100%
        assert data["estimated_time_saved_percent"] == 100, \
            f"Expected 100% time saved for full_reuse, got {data['estimated_time_saved_percent']}%"

    def test_analyze_reuse_nonexistent_parent_404(self, api_client):
        """Test that analyze-reuse rejects non-existent parent_job_id with 404."""
        fake_job_id = "00000000-0000-0000-0000-000000000000"
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/analyze-reuse",
            params={"parent_job_id": fake_job_id}
        )
        
        assert response.status_code == 404, \
            f"Expected 404 for non-existent job, got {response.status_code}: {response.text}"
        print(f"Non-existent parent correctly returns 404")


class TestCreateWithParentVideoId:
    """Tests for POST /api/story-engine/create with parent_video_id."""

    def test_create_endpoint_accepts_parent_video_id(self, admin_client):
        """Test that create endpoint accepts parent_video_id parameter."""
        # Note: We won't actually create a job (requires credits), just verify the endpoint accepts the param
        # by checking the validation error message doesn't mention parent_video_id as invalid
        response = admin_client.post(
            f"{BASE_URL}/api/story-engine/create",
            json={
                "title": "Test Remix Video",
                "story_text": "A" * 50,  # Minimum 50 chars
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm",
                "parent_video_id": KNOWN_JOB_ID
            }
        )
        
        # We expect either success (201/200), rate limit (429), or credit error (402)
        # NOT a validation error about parent_video_id being invalid
        assert response.status_code in [200, 201, 402, 429], \
            f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Verify reuse info is returned
            assert "reuse_mode" in data, "Response should include reuse_mode"
            assert "stages_reused" in data, "Response should include stages_reused"
            assert "stages_to_generate" in data, "Response should include stages_to_generate"
            print(f"Create with parent_video_id - reuse_mode: {data.get('reuse_mode')}")
            print(f"Create with parent_video_id - stages_reused: {data.get('stages_reused')}")
        else:
            print(f"Create blocked by rate limit or credits (expected): {response.status_code}")


class TestStatusEndpointReuseInfo:
    """Tests for GET /api/story-engine/status/{job_id} reuse_info field."""

    def test_status_returns_reuse_info_field(self, admin_client):
        """Test that status endpoint returns reuse_info field when applicable."""
        response = admin_client.get(f"{BASE_URL}/api/story-engine/status/{KNOWN_JOB_ID}")
        
        if response.status_code == 404:
            pytest.skip(f"Known job {KNOWN_JOB_ID} not found in database")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "job" in data, "Response missing 'job' field"
        job = data["job"]
        
        # reuse_info should be present (may be null if not a remix job)
        assert "reuse_info" in job, "Job response missing 'reuse_info' field"
        
        print(f"Status endpoint reuse_info: {job.get('reuse_info')}")
        
        # If reuse_info is not null, verify its structure
        if job.get("reuse_info"):
            reuse_info = job["reuse_info"]
            assert "parent_job_id" in reuse_info, "reuse_info missing parent_job_id"
            assert "reuse_mode" in reuse_info, "reuse_info missing reuse_mode"
            assert "reused_stages" in reuse_info, "reuse_info missing reused_stages"


class TestStateMachineTransitions:
    """Tests for state machine allowing INIT to transition to any active state."""

    def test_valid_transitions_include_init_to_active_states(self):
        """Verify state machine code allows INIT to transition to any active state."""
        # This is a code review test - we verify the state_machine.py has correct transitions
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.story_engine.state_machine import VALID_TRANSITIONS
            from services.story_engine.schemas import JobState
            
            init_transitions = VALID_TRANSITIONS.get(JobState.INIT, [])
            
            # INIT should be able to transition to all active states for checkpoint skip
            expected_active_states = [
                JobState.PLANNING,
                JobState.BUILDING_CHARACTER_CONTEXT,
                JobState.PLANNING_SCENE_MOTION,
                JobState.GENERATING_KEYFRAMES,
                JobState.GENERATING_SCENE_CLIPS,
                JobState.GENERATING_AUDIO,
                JobState.ASSEMBLING_VIDEO,
            ]
            
            for state in expected_active_states:
                assert state in init_transitions, \
                    f"INIT should be able to transition to {state.value} for checkpoint reuse"
            
            print(f"INIT can transition to: {[s.value for s in init_transitions]}")
            print("State machine correctly allows INIT to any active state for checkpoint skip")
            
        except ImportError as e:
            pytest.skip(f"Could not import state_machine module: {e}")


class TestFrontendReuseComponents:
    """Tests verifying frontend components have reuse-related data-testid attributes."""

    def test_progressive_generation_has_reuse_badge_testid(self):
        """Verify ProgressiveGeneration.js has data-testid='reuse-badge'."""
        import os
        
        component_path = "/app/frontend/src/components/ProgressiveGeneration.js"
        assert os.path.exists(component_path), f"Component file not found: {component_path}"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid="reuse-badge"' in content, \
            "ProgressiveGeneration.js missing data-testid='reuse-badge'"
        print("Found data-testid='reuse-badge' in ProgressiveGeneration.js")

    def test_progressive_generation_has_stage_reused_testids(self):
        """Verify ProgressiveGeneration.js has data-testid='stage-reused-*' labels."""
        import os
        
        component_path = "/app/frontend/src/components/ProgressiveGeneration.js"
        assert os.path.exists(component_path), f"Component file not found: {component_path}"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        assert 'data-testid={`stage-reused-' in content, \
            "ProgressiveGeneration.js missing data-testid='stage-reused-*' labels"
        print("Found data-testid='stage-reused-*' pattern in ProgressiveGeneration.js")

    def test_story_video_pipeline_passes_reuse_info_prop(self):
        """Verify StoryVideoPipeline.js passes reuseInfo prop to ProgressiveGeneration."""
        import os
        
        component_path = "/app/frontend/src/pages/StoryVideoPipeline.js"
        assert os.path.exists(component_path), f"Component file not found: {component_path}"
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        # Check for reuseInfo state
        assert 'reuseInfo' in content, "StoryVideoPipeline.js missing reuseInfo state"
        
        # Check for passing reuseInfo to ProgressiveGeneration
        assert 'reuseInfo={reuseInfo}' in content or 'reuseInfo=' in content, \
            "StoryVideoPipeline.js should pass reuseInfo prop to ProgressiveGeneration"
        print("Found reuseInfo prop passing in StoryVideoPipeline.js")


class TestPipelineReuseLogic:
    """Tests for pipeline.py analyze_reuse and apply_reuse_checkpoints functions."""

    def test_analyze_reuse_function_exists(self):
        """Verify analyze_reuse function exists in pipeline.py."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.story_engine.pipeline import analyze_reuse
            assert callable(analyze_reuse), "analyze_reuse should be a callable function"
            print("analyze_reuse function exists and is callable")
        except ImportError as e:
            pytest.fail(f"Could not import analyze_reuse: {e}")

    def test_apply_reuse_checkpoints_function_exists(self):
        """Verify apply_reuse_checkpoints function exists in pipeline.py."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.story_engine.pipeline import apply_reuse_checkpoints
            assert callable(apply_reuse_checkpoints), "apply_reuse_checkpoints should be a callable function"
            print("apply_reuse_checkpoints function exists and is callable")
        except ImportError as e:
            pytest.fail(f"Could not import apply_reuse_checkpoints: {e}")

    def test_stage_outputs_mapping_exists(self):
        """Verify STAGE_OUTPUTS mapping exists for dependency tracking."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.story_engine.pipeline import STAGE_OUTPUTS
            
            expected_stages = [
                "PLANNING", "BUILDING_CHARACTER_CONTEXT", "PLANNING_SCENE_MOTION",
                "GENERATING_KEYFRAMES", "GENERATING_SCENE_CLIPS",
                "GENERATING_AUDIO", "ASSEMBLING_VIDEO"
            ]
            
            for stage in expected_stages:
                assert stage in STAGE_OUTPUTS, f"STAGE_OUTPUTS missing {stage}"
            
            print(f"STAGE_OUTPUTS contains all {len(expected_stages)} expected stages")
        except ImportError as e:
            pytest.fail(f"Could not import STAGE_OUTPUTS: {e}")

    def test_invalidation_map_exists(self):
        """Verify INVALIDATION_MAP exists for determining which stages to rerun."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from services.story_engine.pipeline import INVALIDATION_MAP
            
            # Check key invalidation triggers
            assert "story_text" in INVALIDATION_MAP, "INVALIDATION_MAP missing story_text"
            assert "style_id" in INVALIDATION_MAP, "INVALIDATION_MAP missing style_id"
            assert "voice_preset" in INVALIDATION_MAP, "INVALIDATION_MAP missing voice_preset"
            
            print(f"INVALIDATION_MAP contains triggers: {list(INVALIDATION_MAP.keys())}")
        except ImportError as e:
            pytest.fail(f"Could not import INVALIDATION_MAP: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
