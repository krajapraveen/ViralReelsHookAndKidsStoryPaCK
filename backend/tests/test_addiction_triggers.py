"""
Test suite for Addiction Triggers feature in Story Engine.
Tests: Preview endpoint, Status endpoint, Episode plan schema, FFmpeg assembly function.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test job ID with existing story (The Painter of Stars)
TEST_JOB_ID = "261430a2-28f5-4c40-bac2-35f8d275fae7"

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPreviewEndpoint:
    """Tests for GET /api/story-engine/preview/{job_id} - addiction fields"""
    
    def test_preview_returns_cliffhanger(self, api_client):
        """Preview endpoint should return cliffhanger field."""
        response = api_client.get(f"{BASE_URL}/api/story-engine/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        preview = data.get("preview", {})
        
        # Cliffhanger should exist and be non-empty for this story
        assert "cliffhanger" in preview
        assert preview["cliffhanger"] is not None
        assert len(preview["cliffhanger"]) > 10
        print(f"✓ Cliffhanger: {preview['cliffhanger'][:80]}...")
    
    def test_preview_returns_trigger_text_field(self, api_client):
        """Preview endpoint should return trigger_text field (may be null for old stories)."""
        response = api_client.get(f"{BASE_URL}/api/story-engine/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        preview = data.get("preview", {})
        
        # trigger_text field should exist (may be null for stories before new prompt)
        assert "trigger_text" in preview
        print(f"✓ trigger_text field present: {preview['trigger_text']}")
    
    def test_preview_returns_tension_peak_field(self, api_client):
        """Preview endpoint should return tension_peak field (may be null for old stories)."""
        response = api_client.get(f"{BASE_URL}/api/story-engine/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        preview = data.get("preview", {})
        
        # tension_peak field should exist
        assert "tension_peak" in preview
        print(f"✓ tension_peak field present: {preview['tension_peak']}")
    
    def test_preview_returns_cut_mood_field(self, api_client):
        """Preview endpoint should return cut_mood field (may be null for old stories)."""
        response = api_client.get(f"{BASE_URL}/api/story-engine/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        preview = data.get("preview", {})
        
        # cut_mood field should exist
        assert "cut_mood" in preview
        print(f"✓ cut_mood field present: {preview['cut_mood']}")
    
    def test_preview_returns_final_video_url(self, api_client):
        """Preview endpoint should return final_video_url for completed stories."""
        response = api_client.get(f"{BASE_URL}/api/story-engine/preview/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        preview = data.get("preview", {})
        
        # final_video_url should exist for completed story
        assert "final_video_url" in preview
        assert preview["final_video_url"] is not None
        assert "mp4" in preview["final_video_url"].lower()
        print(f"✓ final_video_url present")


class TestStatusEndpoint:
    """Tests for GET /api/story-engine/status/{job_id} - addiction fields"""
    
    def test_status_returns_cliffhanger(self, authenticated_client):
        """Status endpoint should return cliffhanger field."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        job = data.get("job", {})
        
        # Cliffhanger should exist
        assert "cliffhanger" in job
        assert job["cliffhanger"] is not None
        print(f"✓ Status cliffhanger: {job['cliffhanger'][:80]}...")
    
    def test_status_returns_trigger_text_field(self, authenticated_client):
        """Status endpoint should return trigger_text field."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        job = data.get("job", {})
        
        # trigger_text field should exist
        assert "trigger_text" in job
        print(f"✓ Status trigger_text field present: {job['trigger_text']}")
    
    def test_status_returns_tension_peak_field(self, authenticated_client):
        """Status endpoint should return tension_peak field."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        job = data.get("job", {})
        
        # tension_peak field should exist
        assert "tension_peak" in job
        print(f"✓ Status tension_peak field present: {job['tension_peak']}")
    
    def test_status_returns_cut_mood_field(self, authenticated_client):
        """Status endpoint should return cut_mood field."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        job = data.get("job", {})
        
        # cut_mood field should exist
        assert "cut_mood" in job
        print(f"✓ Status cut_mood field present: {job['cut_mood']}")
    
    def test_status_job_completed(self, authenticated_client):
        """Status endpoint should show job as COMPLETED."""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/status/{TEST_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        job = data.get("job", {})
        
        assert job.get("status") == "COMPLETED"
        assert job.get("engine_state") == "READY"
        print(f"✓ Job status: {job['status']}, engine_state: {job['engine_state']}")


class TestEpisodePlanSchema:
    """Tests to verify episode plan prompt includes addiction fields."""
    
    def test_planning_llm_prompt_has_tension_peak(self):
        """Episode plan prompt should include tension_peak in schema."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters.planning_llm import EPISODE_PLAN_PROMPT
        
        assert "tension_peak" in EPISODE_PLAN_PROMPT
        assert '"tension_peak"' in EPISODE_PLAN_PROMPT
        print("✓ tension_peak in episode plan prompt")
    
    def test_planning_llm_prompt_has_trigger_text(self):
        """Episode plan prompt should include trigger_text in schema."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters.planning_llm import EPISODE_PLAN_PROMPT
        
        assert "trigger_text" in EPISODE_PLAN_PROMPT
        assert '"trigger_text"' in EPISODE_PLAN_PROMPT
        print("✓ trigger_text in episode plan prompt")
    
    def test_planning_llm_prompt_has_cut_mood(self):
        """Episode plan prompt should include cut_mood in schema."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters.planning_llm import EPISODE_PLAN_PROMPT
        
        assert "cut_mood" in EPISODE_PLAN_PROMPT
        assert '"cut_mood"' in EPISODE_PLAN_PROMPT
        print("✓ cut_mood in episode plan prompt")
    
    def test_planning_llm_prompt_has_cliffhanger(self):
        """Episode plan prompt should include cliffhanger in schema."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters.planning_llm import EPISODE_PLAN_PROMPT
        
        assert "cliffhanger" in EPISODE_PLAN_PROMPT
        assert '"cliffhanger"' in EPISODE_PLAN_PROMPT
        print("✓ cliffhanger in episode plan prompt")


class TestFFmpegAssembly:
    """Tests to verify apply_addiction_triggers function exists and is called."""
    
    def test_apply_addiction_triggers_function_exists(self):
        """apply_addiction_triggers function should exist in ffmpeg_assembly.py."""
        import sys
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters import ffmpeg_assembly
        
        assert hasattr(ffmpeg_assembly, 'apply_addiction_triggers')
        assert callable(ffmpeg_assembly.apply_addiction_triggers)
        print("✓ apply_addiction_triggers function exists")
    
    def test_apply_addiction_triggers_signature(self):
        """apply_addiction_triggers should have correct parameters."""
        import sys
        import inspect
        sys.path.insert(0, '/app/backend')
        from services.story_engine.adapters.ffmpeg_assembly import apply_addiction_triggers
        
        sig = inspect.signature(apply_addiction_triggers)
        params = list(sig.parameters.keys())
        
        assert 'video_path' in params
        assert 'output_path' in params
        assert 'trigger_text' in params
        assert 'cliffhanger_text' in params
        print(f"✓ apply_addiction_triggers signature: {params}")
    
    def test_pipeline_calls_apply_addiction_triggers(self):
        """Pipeline _stage_assembly should call apply_addiction_triggers."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read pipeline.py source to verify the call
        with open('/app/backend/services/story_engine/pipeline.py', 'r') as f:
            pipeline_source = f.read()
        
        assert 'apply_addiction_triggers' in pipeline_source
        assert 'ffmpeg_assembly.apply_addiction_triggers' in pipeline_source
        print("✓ Pipeline calls apply_addiction_triggers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
