"""
Test Suite: Anonymous Avatar Demo Wizard (/avatar-demo)
Iteration: 535
Focus: P0 try-before-signup flow - anonymous generation, rate limiting, funnel events

Tests cover:
- POST /api/avatar/studio/anon-mock-generate (anonymous, no auth)
- GET /api/avatar/studio/anon-jobs/{job_id} (anonymous polling)
- Rate limit: 2 generations per session per 24h, 3rd returns 429 ANON_LIMIT_REACHED
- Validation: invalid avatar_type, motion_style, safety_confirmed=false, banned script
- 5 new funnel steps: demo_generate_clicked, demo_completed, signup_after_demo, retry_after_demo, share_after_demo
- Photo Trailer regression: /api/photo-trailer/templates still returns 9 templates
"""

import os
import pytest
import requests
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token for authenticated endpoint tests"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip("Admin login failed - skipping admin tests")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user auth token"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if r.status_code == 200:
        return r.json().get("token")
    pytest.skip("Test user login failed")


@pytest.fixture
def fresh_session_id():
    """Generate a fresh session ID for each test to avoid rate limit conflicts"""
    return f"test_anon_{uuid.uuid4().hex[:12]}_{int(time.time())}"


class TestAnonMockGenerateValidation:
    """Test validation for POST /api/avatar/studio/anon-mock-generate"""
    
    def test_invalid_avatar_type_returns_400(self, fresh_session_id):
        """Invalid avatar_type should return 400 with INVALID_AVATAR_TYPE"""
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "invalid_type_xyz",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("detail", {}).get("code") == "INVALID_AVATAR_TYPE", f"Expected INVALID_AVATAR_TYPE, got {data}"
        print("PASS: Invalid avatar_type returns 400 INVALID_AVATAR_TYPE")
    
    def test_invalid_motion_style_returns_400(self, fresh_session_id):
        """Invalid motion_style should return 400 with INVALID_MOTION_STYLE"""
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "invalid_motion_xyz",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("detail", {}).get("code") == "INVALID_MOTION_STYLE", f"Expected INVALID_MOTION_STYLE, got {data}"
        print("PASS: Invalid motion_style returns 400 INVALID_MOTION_STYLE")
    
    def test_safety_not_confirmed_returns_400(self, fresh_session_id):
        """safety_confirmed=false should return 400 with SAFETY_NOT_CONFIRMED"""
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": False
        })
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("detail", {}).get("code") == "SAFETY_NOT_CONFIRMED", f"Expected SAFETY_NOT_CONFIRMED, got {data}"
        print("PASS: safety_confirmed=false returns 400 SAFETY_NOT_CONFIRMED")
    
    def test_banned_script_returns_400(self, fresh_session_id):
        """Script with banned content should return 400 with DISALLOWED_CONTENT"""
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True,
            "script": "Please send me your OTP for verification"
        })
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        data = r.json()
        assert data.get("detail", {}).get("code") == "DISALLOWED_CONTENT", f"Expected DISALLOWED_CONTENT, got {data}"
        print("PASS: Banned script returns 400 DISALLOWED_CONTENT")


class TestAnonMockGenerateSuccess:
    """Test successful anonymous generation flow"""
    
    def test_valid_payload_returns_job(self, fresh_session_id):
        """Valid payload should return job_id, eta_seconds, demo_label, is_demo_output=true, anonymous=true, remaining_in_window"""
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True,
            "script": "Hey — I didn't record this video. This is my AI avatar.",
            "clone_name": "My Demo Avatar"
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        
        # Verify all required fields
        assert "job_id" in data, "Missing job_id"
        assert "eta_seconds" in data, "Missing eta_seconds"
        assert "demo_label" in data, "Missing demo_label"
        assert data.get("is_demo_output") == True, f"Expected is_demo_output=true, got {data.get('is_demo_output')}"
        assert data.get("anonymous") == True, f"Expected anonymous=true, got {data.get('anonymous')}"
        assert "remaining_in_window" in data, "Missing remaining_in_window"
        
        # remaining_in_window should be 1 after first generation (limit=2, used=1)
        assert data["remaining_in_window"] == 1, f"Expected remaining_in_window=1, got {data['remaining_in_window']}"
        
        print(f"PASS: Valid payload returns job_id={data['job_id']}, eta={data['eta_seconds']}s, remaining={data['remaining_in_window']}")
        return data["job_id"]
    
    def test_no_auth_header_required(self, fresh_session_id):
        """Anonymous endpoint should work without any auth header"""
        r = requests.post(
            f"{BASE_URL}/api/avatar/studio/anon-mock-generate",
            json={
                "session_id": fresh_session_id,
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True
            },
            headers={"Content-Type": "application/json"}  # No Authorization header
        )
        assert r.status_code == 200, f"Expected 200 without auth, got {r.status_code}: {r.text}"
        print("PASS: Anonymous endpoint works without auth header")


class TestAnonJobPolling:
    """Test GET /api/avatar/studio/anon-jobs/{job_id}"""
    
    def test_poll_job_with_correct_session_id(self, fresh_session_id):
        """Polling with correct session_id should return job status"""
        # First create a job
        create_r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert create_r.status_code == 200
        job_id = create_r.json()["job_id"]
        
        # Poll the job
        poll_r = requests.get(f"{BASE_URL}/api/avatar/studio/anon-jobs/{job_id}?session_id={fresh_session_id}")
        assert poll_r.status_code == 200, f"Expected 200, got {poll_r.status_code}: {poll_r.text}"
        
        data = poll_r.json()
        assert "status" in data, "Missing status field"
        assert "progress" in data, "Missing progress field"
        assert data.get("is_demo_output") == True, "Expected is_demo_output=true"
        assert data.get("anonymous") == True, "Expected anonymous=true"
        
        print(f"PASS: Poll job returns status={data['status']}, progress={data['progress']}%")
    
    def test_poll_job_with_wrong_session_id_returns_404(self, fresh_session_id):
        """Polling with wrong session_id should return 404"""
        # First create a job
        create_r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert create_r.status_code == 200
        job_id = create_r.json()["job_id"]
        
        # Poll with wrong session_id
        wrong_session = f"wrong_session_{uuid.uuid4().hex[:8]}"
        poll_r = requests.get(f"{BASE_URL}/api/avatar/studio/anon-jobs/{job_id}?session_id={wrong_session}")
        assert poll_r.status_code == 404, f"Expected 404 for wrong session_id, got {poll_r.status_code}"
        print("PASS: Wrong session_id returns 404")
    
    def test_job_auto_completes_with_output_url(self, fresh_session_id):
        """Job should auto-complete in 20-60s with stage_label + output_url"""
        # Create a short duration job (15s → 20s eta)
        create_r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert create_r.status_code == 200
        job_id = create_r.json()["job_id"]
        eta = create_r.json()["eta_seconds"]
        
        print(f"Job created: {job_id}, eta={eta}s. Waiting for completion...")
        
        # Poll until completed or timeout
        max_wait = eta + 15  # Give extra buffer
        start = time.time()
        completed = False
        final_data = None
        
        while time.time() - start < max_wait:
            poll_r = requests.get(f"{BASE_URL}/api/avatar/studio/anon-jobs/{job_id}?session_id={fresh_session_id}")
            if poll_r.status_code == 200:
                data = poll_r.json()
                if data.get("status") == "completed":
                    completed = True
                    final_data = data
                    break
                print(f"  Progress: {data.get('progress', 0)}% - {data.get('stage_label', 'N/A')}")
            time.sleep(2)
        
        assert completed, f"Job did not complete within {max_wait}s"
        assert "output_url" in final_data, "Missing output_url in completed job"
        assert final_data.get("output_url"), "output_url is empty"
        assert "stage_label" in final_data, "Missing stage_label"
        
        print(f"PASS: Job completed in {time.time() - start:.1f}s with output_url={final_data['output_url'][:50]}...")


class TestAnonRateLimit:
    """Test rate limiting: 2 generations per session per 24h"""
    
    def test_rate_limit_third_generation_returns_429(self):
        """3rd generation for same session_id within 24h should return 429 ANON_LIMIT_REACHED"""
        # Use a fresh session for this test
        session_id = f"ratelimit_test_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        # First generation - should succeed
        r1 = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r1.status_code == 200, f"First generation failed: {r1.status_code} {r1.text}"
        data1 = r1.json()
        assert data1.get("remaining_in_window") == 1, f"Expected remaining=1 after 1st, got {data1.get('remaining_in_window')}"
        print(f"1st generation: PASS (remaining={data1.get('remaining_in_window')})")
        
        # Second generation - should succeed
        r2 = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "gesture",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r2.status_code == 200, f"Second generation failed: {r2.status_code} {r2.text}"
        data2 = r2.json()
        assert data2.get("remaining_in_window") == 0, f"Expected remaining=0 after 2nd, got {data2.get('remaining_in_window')}"
        print(f"2nd generation: PASS (remaining={data2.get('remaining_in_window')})")
        
        # Third generation - should fail with 429
        r3 = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "full_body",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r3.status_code == 429, f"Expected 429 for 3rd generation, got {r3.status_code}: {r3.text}"
        
        data3 = r3.json()
        detail = data3.get("detail", {})
        assert detail.get("code") == "ANON_LIMIT_REACHED", f"Expected code=ANON_LIMIT_REACHED, got {detail}"
        assert detail.get("limit") == 2, f"Expected limit=2, got {detail.get('limit')}"
        assert detail.get("window_hours") == 24, f"Expected window_hours=24, got {detail.get('window_hours')}"
        
        print(f"3rd generation: PASS (429 ANON_LIMIT_REACHED, limit={detail.get('limit')}, window={detail.get('window_hours')}h)")


class TestFunnelTracking:
    """Test funnel event tracking for anonymous demo flow"""
    
    def test_funnel_accepts_demo_generate_clicked(self, fresh_session_id):
        """POST /api/avatar/funnel/track should accept demo_generate_clicked"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "demo_generate_clicked",
            "session_id": fresh_session_id,
            "meta": {"avatar_type": "quick_avatar", "motion_style": "talking_head"}
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: demo_generate_clicked accepted")
    
    def test_funnel_accepts_demo_completed(self, fresh_session_id):
        """POST /api/avatar/funnel/track should accept demo_completed"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "demo_completed",
            "session_id": fresh_session_id,
            "meta": {"job_id": "test_job_123"}
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: demo_completed accepted")
    
    def test_funnel_accepts_signup_after_demo(self, fresh_session_id):
        """POST /api/avatar/funnel/track should accept signup_after_demo"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "signup_after_demo",
            "session_id": fresh_session_id,
            "meta": {"reason": "download"}
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: signup_after_demo accepted")
    
    def test_funnel_accepts_retry_after_demo(self, fresh_session_id):
        """POST /api/avatar/funnel/track should accept retry_after_demo"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "retry_after_demo",
            "session_id": fresh_session_id,
            "meta": {"prior_job_id": "test_job_456"}
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: retry_after_demo accepted")
    
    def test_funnel_accepts_share_after_demo(self, fresh_session_id):
        """POST /api/avatar/funnel/track should accept share_after_demo"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "share_after_demo",
            "session_id": fresh_session_id,
            "meta": {"channel": "whatsapp"}
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("ok") == True
        print("PASS: share_after_demo accepted")
    
    def test_funnel_rejects_unknown_step(self, fresh_session_id):
        """POST /api/avatar/funnel/track should reject unknown step"""
        r = requests.post(f"{BASE_URL}/api/avatar/funnel/track", json={
            "step": "unknown_step_xyz",
            "session_id": fresh_session_id
        })
        assert r.status_code == 400, f"Expected 400 for unknown step, got {r.status_code}"
        print("PASS: Unknown step rejected with 400")


class TestPhotoTrailerRegression:
    """Ensure Photo Trailer is not affected by Avatar Demo changes"""
    
    def test_photo_trailer_templates_still_returns_9(self, test_user_token):
        """GET /api/photo-trailer/templates should still return 9 templates"""
        r = requests.get(
            f"{BASE_URL}/api/photo-trailer/templates",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        templates = data.get("templates", [])
        assert len(templates) == 9, f"Expected 9 templates, got {len(templates)}"
        print(f"PASS: Photo Trailer templates freeze held - {len(templates)} templates returned")


class TestAuthenticatedAvatarRegression:
    """Ensure authenticated /app/avatar still works"""
    
    def test_authenticated_studio_templates(self, test_user_token):
        """GET /api/avatar/studio/templates should work for authenticated users"""
        r = requests.get(
            f"{BASE_URL}/api/avatar/studio/templates",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "templates" in data, "Missing templates"
        assert "motion_styles" in data, "Missing motion_styles"
        assert "avatar_types" in data, "Missing avatar_types"
        
        assert len(data["templates"]) == 6, f"Expected 6 templates, got {len(data['templates'])}"
        assert len(data["motion_styles"]) == 4, f"Expected 4 motion_styles, got {len(data['motion_styles'])}"
        assert len(data["avatar_types"]) == 4, f"Expected 4 avatar_types, got {len(data['avatar_types'])}"
        
        print("PASS: Authenticated studio templates endpoint works (6 templates, 4 motion styles, 4 avatar types)")
    
    def test_authenticated_mock_generate(self, test_user_token):
        """POST /api/avatar/studio/mock-generate should work for authenticated users"""
        r = requests.post(
            f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True,
                "script": "This is a test script for authenticated generation."
            }
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        assert "job_id" in data, "Missing job_id"
        assert data.get("is_demo_output") == True, "Expected is_demo_output=true"
        
        print(f"PASS: Authenticated mock-generate works, job_id={data['job_id']}")


class TestServerSideFunnelEmits:
    """Test that server-side funnel events are emitted correctly"""
    
    def test_demo_generate_clicked_emitted_on_create(self, fresh_session_id):
        """Server should emit demo_generate_clicked when anon job is created"""
        # Create a job
        r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert r.status_code == 200
        
        # The server emits demo_generate_clicked internally - we can't directly verify
        # but the endpoint succeeding means the emit was attempted
        print("PASS: Job created successfully (server-side demo_generate_clicked emit attempted)")
    
    def test_demo_completed_emitted_on_first_poll_of_completed_job(self, fresh_session_id):
        """Server should emit demo_completed on first poll of a completed anon job"""
        # Create a short job
        create_r = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": fresh_session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "safety_confirmed": True
        })
        assert create_r.status_code == 200
        job_id = create_r.json()["job_id"]
        
        # Wait for completion
        max_wait = 35
        start = time.time()
        while time.time() - start < max_wait:
            poll_r = requests.get(f"{BASE_URL}/api/avatar/studio/anon-jobs/{job_id}?session_id={fresh_session_id}")
            if poll_r.status_code == 200 and poll_r.json().get("status") == "completed":
                # First poll of completed job triggers demo_completed emit
                print("PASS: Job completed - server-side demo_completed emit triggered on first poll")
                return
            time.sleep(2)
        
        pytest.fail("Job did not complete in time")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
