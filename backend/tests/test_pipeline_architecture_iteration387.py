"""
Test Suite for Pipeline Architecture Overhaul (Iteration 387)

Tests the major pipeline refactor:
1. Stage orchestrator (execute_pipeline, process_next_stage)
2. Retry/Cancel endpoints
3. Per-stage failure states (FAILED_PLANNING, FAILED_IMAGES, FAILED_TTS, FAILED_RENDER)
4. Status response with retry_info, credits_refunded, error_code
5. State machine transitions
6. Cost guard (enforce_runtime_budget, BudgetExceededError)
7. Deterministic fallback for planning
8. Recovery daemon (check logs)
"""

import pytest
import requests
import os
import sys
from pathlib import Path

# Add backend to path for direct module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Could not authenticate test user: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Could not authenticate admin user: {response.status_code}")


class TestRetryEndpoint:
    """Test POST /api/story-engine/retry/{job_id}"""
    
    def test_retry_nonexistent_job_returns_404(self, test_user_token):
        """Retry endpoint returns 404 for nonexistent job"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(
            f"{BASE_URL}/api/story-engine/retry/nonexistent-job-id-12345",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "not found" in str(data).lower()
    
    def test_retry_without_auth_returns_401(self):
        """Retry endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/story-engine/retry/some-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestCancelEndpoint:
    """Test POST /api/story-engine/cancel/{job_id}"""
    
    def test_cancel_nonexistent_job_returns_404(self, test_user_token):
        """Cancel endpoint returns 404 for nonexistent job"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(
            f"{BASE_URL}/api/story-engine/cancel/nonexistent-job-id-12345",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "not found" in str(data).lower()
    
    def test_cancel_without_auth_returns_401(self):
        """Cancel endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/story-engine/cancel/some-job-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestStatusEndpointRetryInfo:
    """Test GET /api/story-engine/status/{job_id} returns retry_info"""
    
    def test_status_nonexistent_job_returns_404(self, test_user_token):
        """Status endpoint returns 404 for nonexistent job"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(
            f"{BASE_URL}/api/story-engine/status/nonexistent-job-id-12345",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_status_response_structure(self, test_user_token):
        """Status endpoint returns expected structure with retry_info fields"""
        # First get a real job from user-jobs
        headers = {"Authorization": f"Bearer {test_user_token}"}
        jobs_response = requests.get(f"{BASE_URL}/api/story-engine/user-jobs", headers=headers)
        
        if jobs_response.status_code != 200:
            pytest.skip("Could not fetch user jobs")
        
        jobs = jobs_response.json().get("jobs", [])
        # Filter for story_engine jobs (not legacy pipeline jobs)
        story_engine_jobs = [j for j in jobs if j.get("source") == "story_engine"]
        if not story_engine_jobs:
            pytest.skip("No story_engine jobs found for test user")
        
        # Get status of first story_engine job
        job_id = story_engine_jobs[0].get("job_id")
        response = requests.get(f"{BASE_URL}/api/story-engine/status/{job_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        
        job = data.get("job", {})
        
        # Check retry_info object exists
        retry_info = job.get("retry_info")
        assert retry_info is not None, "retry_info should be present in status response"
        
        # Check retry_info fields
        assert "can_retry" in retry_info, "retry_info should have can_retry field"
        assert "current_attempt" in retry_info, "retry_info should have current_attempt field"
        assert "heartbeat_detail" in retry_info, "retry_info should have heartbeat_detail field"
        
        # Check credits_refunded field
        assert "credits_refunded" in job, "credits_refunded should be in status response"
        
        # Check engine_state field (per-stage failure states)
        assert "engine_state" in job, "engine_state should be in status response"


class TestPerStageFailureStates:
    """Test that per-stage failure states are defined and used"""
    
    def test_failure_states_in_schemas(self):
        """Verify per-stage failure states exist in schemas"""
        from services.story_engine.schemas import JobState, PER_STAGE_FAILURE_STATES
        
        # Check all per-stage failure states exist
        assert hasattr(JobState, 'FAILED_PLANNING'), "FAILED_PLANNING state should exist"
        assert hasattr(JobState, 'FAILED_IMAGES'), "FAILED_IMAGES state should exist"
        assert hasattr(JobState, 'FAILED_TTS'), "FAILED_TTS state should exist"
        assert hasattr(JobState, 'FAILED_RENDER'), "FAILED_RENDER state should exist"
        
        # Check PER_STAGE_FAILURE_STATES set
        assert JobState.FAILED_PLANNING in PER_STAGE_FAILURE_STATES
        assert JobState.FAILED_IMAGES in PER_STAGE_FAILURE_STATES
        assert JobState.FAILED_TTS in PER_STAGE_FAILURE_STATES
        assert JobState.FAILED_RENDER in PER_STAGE_FAILURE_STATES
    
    def test_failure_states_in_terminal_states(self):
        """Verify per-stage failure states are terminal"""
        from services.story_engine.schemas import JobState, TERMINAL_STATES
        
        assert JobState.FAILED_PLANNING in TERMINAL_STATES
        assert JobState.FAILED_IMAGES in TERMINAL_STATES
        assert JobState.FAILED_TTS in TERMINAL_STATES
        assert JobState.FAILED_RENDER in TERMINAL_STATES


class TestStateMachineTransitions:
    """Test state machine validates transitions correctly"""
    
    def test_valid_transition_planning_to_building_character_context(self):
        """PLANNING -> BUILDING_CHARACTER_CONTEXT is valid"""
        from services.story_engine.state_machine import can_transition
        from services.story_engine.schemas import JobState
        
        result = can_transition(JobState.PLANNING, JobState.BUILDING_CHARACTER_CONTEXT)
        assert result == True, "PLANNING -> BUILDING_CHARACTER_CONTEXT should be valid"
    
    def test_invalid_transition_planning_to_ready(self):
        """PLANNING -> READY is invalid (must go through all stages)"""
        from services.story_engine.state_machine import can_transition
        from services.story_engine.schemas import JobState
        
        result = can_transition(JobState.PLANNING, JobState.READY)
        assert result == False, "PLANNING -> READY should be invalid"
    
    def test_valid_transition_planning_to_failed_planning(self):
        """PLANNING -> FAILED_PLANNING is valid"""
        from services.story_engine.state_machine import can_transition
        from services.story_engine.schemas import JobState
        
        result = can_transition(JobState.PLANNING, JobState.FAILED_PLANNING)
        assert result == True, "PLANNING -> FAILED_PLANNING should be valid"
    
    def test_valid_transition_failed_planning_to_planning(self):
        """FAILED_PLANNING -> PLANNING is valid (retry)"""
        from services.story_engine.state_machine import can_transition
        from services.story_engine.schemas import JobState
        
        result = can_transition(JobState.FAILED_PLANNING, JobState.PLANNING)
        assert result == True, "FAILED_PLANNING -> PLANNING should be valid (retry)"
    
    def test_stage_order_defined(self):
        """STAGE_ORDER is defined with correct sequence"""
        from services.story_engine.state_machine import STAGE_ORDER
        from services.story_engine.schemas import JobState
        
        assert len(STAGE_ORDER) >= 7, "STAGE_ORDER should have at least 7 stages"
        assert STAGE_ORDER[0] == JobState.PLANNING, "First stage should be PLANNING"
        assert JobState.VALIDATING in STAGE_ORDER, "VALIDATING should be in STAGE_ORDER"
    
    def test_failure_to_retry_mapping(self):
        """FAILURE_TO_RETRY maps failure states to retry stages"""
        from services.story_engine.state_machine import FAILURE_TO_RETRY
        from services.story_engine.schemas import JobState
        
        assert JobState.FAILED_PLANNING in FAILURE_TO_RETRY
        assert JobState.FAILED_IMAGES in FAILURE_TO_RETRY
        assert JobState.FAILED_TTS in FAILURE_TO_RETRY
        assert JobState.FAILED_RENDER in FAILURE_TO_RETRY
        
        # Check retry targets
        assert FAILURE_TO_RETRY[JobState.FAILED_PLANNING] == JobState.PLANNING
        assert FAILURE_TO_RETRY[JobState.FAILED_IMAGES] == JobState.GENERATING_KEYFRAMES
        assert FAILURE_TO_RETRY[JobState.FAILED_TTS] == JobState.GENERATING_AUDIO
        assert FAILURE_TO_RETRY[JobState.FAILED_RENDER] == JobState.ASSEMBLING_VIDEO


class TestCostGuard:
    """Test runtime budget guard"""
    
    def test_budget_exceeded_error_exists(self):
        """BudgetExceededError is defined"""
        from services.story_engine.cost_guard import BudgetExceededError
        
        error = BudgetExceededError("TEST_STAGE", 100, 50)
        assert error.stage == "TEST_STAGE"
        assert error.consumed == 100
        assert error.limit == 50
        assert "budget" in str(error).lower()
    
    def test_enforce_runtime_budget_within_budget(self):
        """enforce_runtime_budget passes when within budget"""
        from services.story_engine.cost_guard import enforce_runtime_budget, BudgetExceededError
        
        job = {
            "cost_estimate": {"total_credits_required": 21},
            "total_credits_consumed": 5
        }
        
        # Should not raise
        try:
            enforce_runtime_budget(job, "PLANNING")
        except BudgetExceededError:
            pytest.fail("Should not raise BudgetExceededError when within budget")
    
    def test_enforce_runtime_budget_exceeds_budget(self):
        """enforce_runtime_budget raises when over budget"""
        from services.story_engine.cost_guard import enforce_runtime_budget, BudgetExceededError
        
        job = {
            "cost_estimate": {"total_credits_required": 10},
            "total_credits_consumed": 50  # Way over budget
        }
        
        with pytest.raises(BudgetExceededError):
            enforce_runtime_budget(job, "GENERATING_SCENE_CLIPS")
    
    def test_pre_flight_check_sufficient_credits(self):
        """pre_flight_check returns sufficient=True when user has enough credits"""
        from services.story_engine.cost_guard import pre_flight_check
        
        result = pre_flight_check(user_credits=100, scene_count=5)
        assert result.sufficient == True
        assert result.shortfall == 0
    
    def test_pre_flight_check_insufficient_credits(self):
        """pre_flight_check returns sufficient=False when user lacks credits"""
        from services.story_engine.cost_guard import pre_flight_check
        
        result = pre_flight_check(user_credits=1, scene_count=5)
        assert result.sufficient == False
        assert result.shortfall > 0


class TestDeterministicFallback:
    """Test deterministic scene splitter fallback"""
    
    def test_deterministic_scene_splitter_produces_valid_plan(self):
        """_deterministic_scene_splitter produces valid plan structure"""
        from services.story_engine.adapters.planning_llm import _deterministic_scene_splitter
        
        sample_text = """
        Once upon a time, there was a brave knight named Sir Cedric. 
        He lived in a castle on a hill. One day, a dragon appeared in the kingdom.
        The dragon was causing trouble for the villagers. Sir Cedric decided to face the dragon.
        He rode his horse through the forest. The battle was fierce but Sir Cedric prevailed.
        The kingdom was saved and everyone celebrated.
        """
        
        plan = _deterministic_scene_splitter(sample_text, episode_number=1, style_id="cartoon_2d")
        
        assert plan is not None, "Deterministic splitter should produce a plan"
        assert "title" in plan, "Plan should have title"
        assert "scene_breakdown" in plan, "Plan should have scene_breakdown"
        assert "character_arcs" in plan, "Plan should have character_arcs"
        
        # Validate scene_breakdown
        scenes = plan.get("scene_breakdown", [])
        assert len(scenes) >= 3, "Should produce at least 3 scenes"
        assert len(scenes) <= 5, "Should produce at most 5 scenes"
        
        for scene in scenes:
            assert "scene_number" in scene
            assert "action_summary" in scene
            assert "emotional_beat" in scene
        
        # Validate character_arcs
        chars = plan.get("character_arcs", [])
        assert len(chars) >= 1, "Should have at least 1 character"
        
        for char in chars:
            assert "character_name" in char
            assert "role" in char
    
    def test_deterministic_scene_splitter_handles_empty_text(self):
        """_deterministic_scene_splitter returns None for empty text"""
        from services.story_engine.adapters.planning_llm import _deterministic_scene_splitter
        
        plan = _deterministic_scene_splitter("", episode_number=1)
        assert plan is None, "Should return None for empty text"
        
        plan = _deterministic_scene_splitter("   ", episode_number=1)
        assert plan is None, "Should return None for whitespace-only text"


class TestErrorCodes:
    """Test structured error codes"""
    
    def test_error_codes_defined(self):
        """ErrorCode enum has all expected codes"""
        from services.story_engine.schemas import ErrorCode
        
        expected_codes = [
            "BUDGET_EXCEEDED_PRECHECK",
            "BUDGET_EXCEEDED_RUNTIME",
            "MODEL_TIMEOUT",
            "MODEL_INVALID_RESPONSE",
            "SCENE_GENERATION_FAILED",
            "IMAGE_GENERATION_FAILED",
            "TTS_GENERATION_FAILED",
            "RENDER_FAILED",
            "JOB_HEARTBEAT_EXPIRED",
            "WORKER_CRASH",
            "UNKNOWN_STAGE_FAILURE",
            "CONTENT_VIOLATION",
            "INSUFFICIENT_CREDITS",
        ]
        
        for code in expected_codes:
            assert hasattr(ErrorCode, code), f"ErrorCode should have {code}"


class TestRecoveryDaemon:
    """Test recovery daemon is running"""
    
    def test_recovery_daemon_log_message(self):
        """Check backend logs for recovery daemon started message"""
        import subprocess
        
        result = subprocess.run(
            ["grep", "-r", "recovery daemon", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True
        )
        
        # Check if recovery daemon messages exist in logs
        # The daemon logs "[RECOVERY]" prefix
        result2 = subprocess.run(
            ["grep", "-c", "\\[RECOVERY\\]", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True
        )
        
        count = int(result2.stdout.strip()) if result2.stdout.strip().isdigit() else 0
        assert count > 0, "Recovery daemon should have logged messages with [RECOVERY] prefix"


class TestRateLimitFriendlyMessages:
    """Regression test: Rate limit warning shows friendly text"""
    
    def test_rate_limit_status_returns_friendly_message(self, test_user_token):
        """Rate limit status returns friendly 'All rendering slots are busy' text"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-engine/rate-limit-status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # If there's a reason (rate limited), it should be friendly
        reason = data.get("reason")
        if reason:
            assert "Rate limit:" not in reason, "Should not use harsh 'Rate limit:' prefix"
            # Should use friendly language
            assert any(word in reason.lower() for word in ["slots", "busy", "wait", "processing"]), \
                f"Reason should be friendly: {reason}"


class TestStageOrchestrator:
    """Test stage orchestrator functions exist and are callable"""
    
    def test_execute_pipeline_exists(self):
        """execute_pipeline function exists"""
        from services.story_engine.pipeline import execute_pipeline
        assert callable(execute_pipeline)
    
    def test_process_next_stage_exists(self):
        """process_next_stage function exists"""
        from services.story_engine.pipeline import process_next_stage
        assert callable(process_next_stage)
    
    def test_refund_credits_exists(self):
        """_refund_credits function exists"""
        from services.story_engine.pipeline import _refund_credits
        assert callable(_refund_credits)
    
    def test_stage_functions_registered(self):
        """STAGE_FUNCTIONS dict has all stages"""
        from services.story_engine.pipeline import STAGE_FUNCTIONS
        from services.story_engine.schemas import JobState
        
        expected_stages = [
            JobState.PLANNING,
            JobState.BUILDING_CHARACTER_CONTEXT,
            JobState.PLANNING_SCENE_MOTION,
            JobState.GENERATING_KEYFRAMES,
            JobState.GENERATING_SCENE_CLIPS,
            JobState.GENERATING_AUDIO,
            JobState.ASSEMBLING_VIDEO,
            JobState.VALIDATING,
        ]
        
        for stage in expected_stages:
            assert stage in STAGE_FUNCTIONS, f"STAGE_FUNCTIONS should have {stage}"
            assert callable(STAGE_FUNCTIONS[stage]), f"Stage function for {stage} should be callable"


class TestHeartbeatFunctions:
    """Test heartbeat functions exist"""
    
    def test_update_heartbeat_exists(self):
        """update_heartbeat function exists"""
        from services.story_engine.state_machine import update_heartbeat
        assert callable(update_heartbeat)
    
    def test_heartbeat_thresholds_defined(self):
        """HEARTBEAT_THRESHOLDS dict is defined"""
        from services.story_engine.state_machine import HEARTBEAT_THRESHOLDS
        
        assert "PLANNING" in HEARTBEAT_THRESHOLDS
        assert "GENERATING_KEYFRAMES" in HEARTBEAT_THRESHOLDS
        assert "GENERATING_SCENE_CLIPS" in HEARTBEAT_THRESHOLDS
        
        # Thresholds should be reasonable (30s - 10min)
        for stage, threshold in HEARTBEAT_THRESHOLDS.items():
            assert 30 <= threshold <= 600, f"Threshold for {stage} should be 30-600s, got {threshold}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
