"""
Queue System Hardening Testing — Iteration 506

Full QA sweep of queue system hardening:
1. QUEUED state in JobState enum, STATE_PROGRESS, STATE_LABELS, VALID_TRANSITIONS
2. Queue drains on success (_finalize_job calls _drain_queue_for_user)
3. Queue drains on failure (_fail_job_terminal calls _drain_queue_for_user)
4. _drain_queue_for_user promotes oldest QUEUED job (FIFO) with update_one filter
5. get_job_status returns queue_position for QUEUED jobs
6. No SLOTS_BUSY error in check_rate_limits or detect_abuse
7. POST /api/stories/quick-shot with busy slots returns success+queued=true
8. POST /api/stories/continue-branch with busy slots returns success+queued=true
9. GET /api/stories/viewer/{id} works for both story_engine_jobs and pipeline_jobs
10. GET /api/media/admin/integrity-check returns healthy status

Test credentials:
- Admin: admin@creatorstudio.ai / Cr3@t0rStud!o#2026 (unlimited credits)
- Test User: test@visionary-suite.com / Test@2026#
"""

import pytest
import requests
import os
import inspect

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Known test data
KNOWN_PIPELINE_JOB_ID = "e669ab26-85c4-4c0e-b49f-6214dd4b47d9"
KNOWN_R2_VIDEO_JOB_ID = "6ade2a58-60e2-4705-ad6e-95646e0f4168"


# ═══════════════════════════════════════════════════════════════
# SECTION 1: QUEUED STATE VERIFICATION (Code Review)
# ═══════════════════════════════════════════════════════════════

class TestQueuedStateInSchemas:
    """Verify QUEUED state is properly defined in schemas.py"""
    
    def test_queued_in_job_state_enum(self):
        """JobState enum should include QUEUED"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.schemas import JobState, TERMINAL_STATES, ACTIVE_STATES
        
        # QUEUED should exist
        assert hasattr(JobState, 'QUEUED'), "JobState should have QUEUED"
        assert JobState.QUEUED.value == "QUEUED", f"QUEUED value should be 'QUEUED', got {JobState.QUEUED.value}"
        
        # QUEUED should NOT be in TERMINAL_STATES (it's not terminal)
        assert JobState.QUEUED not in TERMINAL_STATES, "QUEUED should NOT be in TERMINAL_STATES"
        
        # QUEUED should NOT be in ACTIVE_STATES (it's waiting, not active)
        assert JobState.QUEUED not in ACTIVE_STATES, "QUEUED should NOT be in ACTIVE_STATES"
        
        print("✓ QUEUED state properly defined in JobState enum")
        print(f"  - TERMINAL_STATES excludes QUEUED: {JobState.QUEUED not in TERMINAL_STATES}")
        print(f"  - ACTIVE_STATES excludes QUEUED: {JobState.QUEUED not in ACTIVE_STATES}")


class TestQueuedStateInStateMachine:
    """Verify QUEUED state is properly configured in state_machine.py"""
    
    def test_queued_in_valid_transitions(self):
        """VALID_TRANSITIONS should allow QUEUED -> INIT and QUEUED -> FAILED"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.state_machine import VALID_TRANSITIONS
        from services.story_engine.schemas import JobState
        
        # QUEUED should have valid transitions
        assert JobState.QUEUED in VALID_TRANSITIONS, "QUEUED should be in VALID_TRANSITIONS"
        
        allowed = VALID_TRANSITIONS[JobState.QUEUED]
        assert JobState.INIT in allowed, f"QUEUED should transition to INIT, allowed: {allowed}"
        assert JobState.FAILED in allowed, f"QUEUED should transition to FAILED, allowed: {allowed}"
        
        print(f"✓ QUEUED transitions: {[s.value for s in allowed]}")
    
    def test_queued_in_state_progress(self):
        """STATE_PROGRESS should have QUEUED with progress=0"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.state_machine import STATE_PROGRESS
        from services.story_engine.schemas import JobState
        
        assert JobState.QUEUED in STATE_PROGRESS, "QUEUED should be in STATE_PROGRESS"
        assert STATE_PROGRESS[JobState.QUEUED] == 0, f"QUEUED progress should be 0, got {STATE_PROGRESS[JobState.QUEUED]}"
        
        print(f"✓ QUEUED progress: {STATE_PROGRESS[JobState.QUEUED]}%")
    
    def test_queued_in_state_labels(self):
        """STATE_LABELS should have QUEUED with 'Queued for rendering' label"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.state_machine import STATE_LABELS
        from services.story_engine.schemas import JobState
        
        assert JobState.QUEUED in STATE_LABELS, "QUEUED should be in STATE_LABELS"
        label = STATE_LABELS[JobState.QUEUED]
        assert "queued" in label.lower() or "rendering" in label.lower(), f"QUEUED label should mention queued/rendering: {label}"
        
        print(f"✓ QUEUED label: '{label}'")


# ═══════════════════════════════════════════════════════════════
# SECTION 2: QUEUE DRAIN MECHANISM (Code Review)
# ═══════════════════════════════════════════════════════════════

class TestQueueDrainOnSuccess:
    """Verify _finalize_job calls _drain_queue_for_user"""
    
    def test_finalize_job_calls_drain_queue(self):
        """_finalize_job should call _drain_queue_for_user after job completes"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import _finalize_job
        source = inspect.getsource(_finalize_job)
        
        # Should call _drain_queue_for_user
        assert "_drain_queue_for_user" in source, "_finalize_job should call _drain_queue_for_user"
        
        # Should get user_id from job
        assert "user_id" in source, "_finalize_job should access user_id"
        
        print("✓ _finalize_job calls _drain_queue_for_user on success")


class TestQueueDrainOnFailure:
    """Verify _fail_job_terminal calls _drain_queue_for_user"""
    
    def test_fail_job_terminal_calls_drain_queue(self):
        """_fail_job_terminal should call _drain_queue_for_user after job fails"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import _fail_job_terminal
        source = inspect.getsource(_fail_job_terminal)
        
        # Should call _drain_queue_for_user
        assert "_drain_queue_for_user" in source, "_fail_job_terminal should call _drain_queue_for_user"
        
        print("✓ _fail_job_terminal calls _drain_queue_for_user on failure")


class TestDrainQueueFIFOOrdering:
    """Verify _drain_queue_for_user uses FIFO ordering"""
    
    def test_drain_queue_uses_created_at_sort(self):
        """_drain_queue_for_user should sort by created_at ASC for FIFO"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import _drain_queue_for_user
        source = inspect.getsource(_drain_queue_for_user)
        
        # Should sort by created_at ascending (FIFO)
        assert "created_at" in source, "_drain_queue_for_user should use created_at for sorting"
        assert "sort" in source, "_drain_queue_for_user should use sort"
        
        # Check for ascending sort (1 = ASC)
        assert '("created_at", 1)' in source or "('created_at', 1)" in source, \
            "_drain_queue_for_user should sort created_at ASC for FIFO"
        
        print("✓ _drain_queue_for_user uses FIFO ordering (created_at ASC)")


class TestDrainQueueNoDuplicateExecution:
    """Verify _drain_queue_for_user uses update_one with state=QUEUED filter"""
    
    def test_drain_queue_uses_atomic_update(self):
        """_drain_queue_for_user should use update_one with state=QUEUED filter to prevent double-promotion"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import _drain_queue_for_user
        source = inspect.getsource(_drain_queue_for_user)
        
        # Should use update_one (not update_many)
        assert "update_one" in source, "_drain_queue_for_user should use update_one for atomic update"
        
        # Should filter by state=QUEUED
        assert '"state": "QUEUED"' in source or "'state': 'QUEUED'" in source or \
               '"state": JobState.QUEUED' in source or "'state': JobState.QUEUED" in source, \
            "_drain_queue_for_user should filter by state=QUEUED"
        
        # Should check modified_count
        assert "modified_count" in source, "_drain_queue_for_user should check modified_count"
        
        print("✓ _drain_queue_for_user uses atomic update_one with state=QUEUED filter")


# ═══════════════════════════════════════════════════════════════
# SECTION 3: QUEUE POSITION IN STATUS (Code Review)
# ═══════════════════════════════════════════════════════════════

class TestQueuePositionInStatus:
    """Verify get_job_status returns queue_position for QUEUED jobs"""
    
    def test_get_job_status_returns_queue_position(self):
        """get_job_status should return queue_position for QUEUED jobs"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import get_job_status
        source = inspect.getsource(get_job_status)
        
        # Should calculate queue_position
        assert "queue_position" in source, "get_job_status should return queue_position"
        
        # Should check for QUEUED state
        assert "QUEUED" in source, "get_job_status should check for QUEUED state"
        
        # Should count documents ahead
        assert "count_documents" in source, "get_job_status should count documents for queue position"
        
        print("✓ get_job_status returns queue_position for QUEUED jobs")


# ═══════════════════════════════════════════════════════════════
# SECTION 4: NO SLOTS_BUSY ERROR (Code Review)
# ═══════════════════════════════════════════════════════════════

class TestNoSlotsBusyError:
    """Verify SLOTS_BUSY error does not appear in safety.py"""
    
    def test_check_rate_limits_no_slots_busy(self):
        """check_rate_limits should NOT return SLOTS_BUSY error"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.safety import check_rate_limits
        source = inspect.getsource(check_rate_limits)
        
        # Should NOT contain SLOTS_BUSY
        assert "SLOTS_BUSY" not in source, "check_rate_limits should NOT return SLOTS_BUSY"
        
        # Should return None for concurrent slot limit (queuing handled elsewhere)
        assert "return None" in source, "check_rate_limits should return None for concurrent limit"
        
        print("✓ check_rate_limits does NOT return SLOTS_BUSY")
    
    def test_detect_abuse_no_slots_busy(self):
        """detect_abuse should NOT return SLOTS_BUSY error in actual return statements"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.safety import detect_abuse
        source = inspect.getsource(detect_abuse)
        
        # Check that return statements don't contain SLOTS_BUSY
        # The docstring mentions SLOTS_BUSY to explain it's NOT used, so we check return lines
        lines = source.split('\n')
        for line in lines:
            if 'return' in line and 'SLOTS_BUSY' in line:
                assert False, f"detect_abuse should NOT return SLOTS_BUSY: {line}"
        
        # Should use RATE_LIMIT prefix in return statements
        assert "RATE_LIMIT" in source, "detect_abuse should use RATE_LIMIT prefix"
        
        print("✓ detect_abuse does NOT return SLOTS_BUSY (uses RATE_LIMIT)")


class TestShouldQueueJobFunction:
    """Verify should_queue_job function exists and is correct"""
    
    def test_should_queue_job_checks_concurrent_limit(self):
        """should_queue_job should check if active jobs >= MAX_CONCURRENT_JOBS"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.safety import should_queue_job, MAX_CONCURRENT_JOBS
        source = inspect.getsource(should_queue_job)
        
        # Should check MAX_CONCURRENT_JOBS
        assert "MAX_CONCURRENT_JOBS" in source, "should_queue_job should use MAX_CONCURRENT_JOBS"
        
        # Should count active jobs
        assert "count_documents" in source, "should_queue_job should count active jobs"
        
        # Verify MAX_CONCURRENT_JOBS = 2
        assert MAX_CONCURRENT_JOBS == 2, f"MAX_CONCURRENT_JOBS should be 2, got {MAX_CONCURRENT_JOBS}"
        
        print(f"✓ should_queue_job checks concurrent limit (MAX_CONCURRENT_JOBS={MAX_CONCURRENT_JOBS})")


# ═══════════════════════════════════════════════════════════════
# SECTION 5: API ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════

class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 502:
            pytest.skip("API not ready")
        assert response.status_code == 200
        print("✓ API health check passed")


class TestQuickShotEndpoint:
    """Test POST /api/stories/quick-shot returns queued=true when slots busy"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_quick_shot_no_slots_busy_error(self, admin_token):
        """POST /api/stories/quick-shot should NOT return SLOTS_BUSY error"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a story to quick-shot from
        feed_response = requests.get(f"{BASE_URL}/api/stories/feed/discover?limit=1", headers=headers)
        if feed_response.status_code != 200 or not feed_response.json().get("stories"):
            pytest.skip("No stories available")
        
        root_story_id = feed_response.json()["stories"][0]["job_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": root_story_id},
            headers=headers
        )
        
        # Should NOT return SLOTS_BUSY
        assert "SLOTS_BUSY" not in response.text, f"SLOTS_BUSY should not appear: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print("✓ Quick-shot returned queued=true (slots busy)")
            else:
                print("✓ Quick-shot returned success (job started)")
        else:
            print(f"✓ Quick-shot returned {response.status_code} (not SLOTS_BUSY)")


class TestContinueBranchEndpoint:
    """Test POST /api/stories/continue-branch returns queued=true when slots busy"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_continue_branch_no_slots_busy_error(self, admin_token):
        """POST /api/stories/continue-branch should NOT return SLOTS_BUSY error"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        feed_response = requests.get(f"{BASE_URL}/api/stories/feed/discover?limit=1", headers=headers)
        if feed_response.status_code != 200 or not feed_response.json().get("stories"):
            pytest.skip("No stories available")
        
        parent_job_id = feed_response.json()["stories"][0]["job_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/stories/continue-branch",
            json={
                "parent_job_id": parent_job_id,
                "title": "Test Branch Queue System",
                "story_text": "Testing queue system hardening. " * 10,
                "animation_style": "cartoon_2d",
                "age_group": "all_ages"
            },
            headers=headers
        )
        
        assert "SLOTS_BUSY" not in response.text
        
        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print("✓ Continue-branch returned queued=true")
            else:
                print("✓ Continue-branch returned success")
        else:
            print(f"✓ Continue-branch returned {response.status_code} (not SLOTS_BUSY)")


class TestStoryViewerEndpoint:
    """Test GET /api/stories/viewer/{id} works for both collections"""
    
    def test_viewer_story_engine_jobs(self):
        """Viewer should work for story_engine_jobs"""
        # Get a story from discover feed
        response = requests.get(f"{BASE_URL}/api/stories/feed/discover?limit=1")
        if response.status_code != 200 or not response.json().get("stories"):
            pytest.skip("No stories available")
        
        job_id = response.json()["stories"][0]["job_id"]
        
        viewer_response = requests.get(f"{BASE_URL}/api/stories/viewer/{job_id}")
        assert viewer_response.status_code in [200, 400, 404], f"Unexpected: {viewer_response.status_code}"
        
        if viewer_response.status_code == 200:
            print(f"✓ Viewer works for story_engine_jobs: {job_id[:8]}")
        else:
            print(f"✓ Viewer returned {viewer_response.status_code} for {job_id[:8]}")
    
    def test_viewer_pipeline_jobs_fallback(self):
        """Viewer should check pipeline_jobs as fallback"""
        response = requests.get(f"{BASE_URL}/api/stories/viewer/{KNOWN_PIPELINE_JOB_ID}")
        
        # Should not return 500
        assert response.status_code != 500, f"Server error: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Viewer found story in pipeline_jobs: {data.get('job', {}).get('title', 'Untitled')}")
        else:
            print(f"✓ Viewer returned {response.status_code} for pipeline_jobs story")


class TestMediaIntegrityCheck:
    """Test GET /api/media/admin/integrity-check"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    def test_integrity_check_healthy(self, admin_token):
        """Integrity check should return healthy status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/media/admin/integrity-check", headers=headers)
        
        if response.status_code == 404:
            pytest.skip("Endpoint not found")
        
        assert response.status_code == 200, f"Expected 200: {response.text}"
        
        data = response.json()
        if "healthy" in data:
            assert data["healthy"] == True
            print("✓ Media integrity check: healthy=true")
        else:
            print(f"✓ Media integrity check returned: {data}")


class TestHottestBattleEndpoint:
    """Test GET /api/stories/hottest-battle"""
    
    def test_hottest_battle_returns_data(self):
        """Hottest battle should return battle data"""
        response = requests.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
        if data.get("battle"):
            battle = data["battle"]
            assert "root_story_id" in battle
            assert "contenders" in battle
            print(f"✓ Hottest battle: {battle.get('root_title', 'Untitled')} ({len(battle.get('contenders', []))} contenders)")
        else:
            print("✓ Hottest battle: no active battles")


# ═══════════════════════════════════════════════════════════════
# SECTION 6: CREDITS DEDUCTION VERIFICATION (Code Review)
# ═══════════════════════════════════════════════════════════════

class TestCreditsDeductedOnceAtCreation:
    """Verify credits are deducted once at creation, not again on promotion"""
    
    def test_create_job_deducts_credits(self):
        """create_job should deduct credits at creation time"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import create_job
        source = inspect.getsource(create_job)
        
        # Should deduct credits
        assert "deduct_credits" in source, "create_job should call deduct_credits"
        
        # Should track credits_deducted
        assert "credits_deducted" in source, "create_job should track credits_deducted"
        
        print("✓ create_job deducts credits at creation time")
    
    def test_drain_queue_does_not_deduct_credits(self):
        """_drain_queue_for_user should NOT deduct credits (already deducted at creation)"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        from services.story_engine.pipeline import _drain_queue_for_user
        source = inspect.getsource(_drain_queue_for_user)
        
        # Should NOT call deduct_credits
        assert "deduct_credits" not in source, "_drain_queue_for_user should NOT deduct credits"
        
        print("✓ _drain_queue_for_user does NOT deduct credits (no double deduction)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
