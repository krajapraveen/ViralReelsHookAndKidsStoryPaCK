"""
AI Cloning Studio 5-Step Wizard Tests - Iteration 534
Tests for the new Phase 1 MOCKED wizard flow.

Features tested:
- GET /api/avatar/studio/templates: 6 templates + 4 motion_styles + 4 avatar_types
- POST /api/avatar/studio/mock-generate: validation + job creation + auto-complete
- GET /api/avatar/jobs/{id}: polling + staged progress + demo output
- Photo Trailer regression: /api/photo-trailer/templates still returns 9 templates
- Existing funnel endpoints: /api/avatar/funnel/track, /api/avatar/referral/attribute, /api/avatar/admin/funnel-table
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestStudioTemplates:
    """GET /api/avatar/studio/templates tests"""
    
    def test_studio_templates_returns_6_templates(self):
        """GET /api/avatar/studio/templates returns 6 templates"""
        response = requests.get(f"{BASE_URL}/api/avatar/studio/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        templates = data.get("templates", [])
        assert len(templates) == 6, f"Expected 6 templates, got {len(templates)}"
        
        template_ids = [t["id"] for t in templates]
        expected_ids = ["intro_reel", "course_welcome", "product_demo", "founder_update", "testimonial", "wellness_tip"]
        for tid in expected_ids:
            assert tid in template_ids, f"Missing template: {tid}"
        
        print(f"✓ Studio templates: {len(templates)} templates returned")
    
    def test_studio_templates_returns_4_motion_styles(self):
        """GET /api/avatar/studio/templates returns 4 motion_styles"""
        response = requests.get(f"{BASE_URL}/api/avatar/studio/templates")
        data = response.json()
        
        motion_styles = data.get("motion_styles", [])
        assert len(motion_styles) == 4, f"Expected 4 motion_styles, got {len(motion_styles)}"
        
        expected_styles = ["talking_head", "gesture", "full_body", "static"]
        for style in expected_styles:
            assert style in motion_styles, f"Missing motion_style: {style}"
        
        print(f"✓ Studio templates: 4 motion_styles returned")
    
    def test_studio_templates_returns_4_avatar_types(self):
        """GET /api/avatar/studio/templates returns 4 avatar_types"""
        response = requests.get(f"{BASE_URL}/api/avatar/studio/templates")
        data = response.json()
        
        avatar_types = data.get("avatar_types", [])
        assert len(avatar_types) == 4, f"Expected 4 avatar_types, got {len(avatar_types)}"
        
        expected_types = ["quick_avatar", "voice_matched", "motion", "template"]
        for atype in expected_types:
            assert atype in avatar_types, f"Missing avatar_type: {atype}"
        
        print(f"✓ Studio templates: 4 avatar_types returned")


class TestMockGenerate:
    """POST /api/avatar/studio/mock-generate tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_mock_generate_invalid_avatar_type_returns_400(self):
        """POST /api/avatar/studio/mock-generate with invalid avatar_type returns 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "invalid_type",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("code") == "INVALID_AVATAR_TYPE", f"Expected INVALID_AVATAR_TYPE, got {detail}"
        print(f"✓ Invalid avatar_type returns 400 with INVALID_AVATAR_TYPE")
    
    def test_mock_generate_invalid_motion_style_returns_400(self):
        """POST /api/avatar/studio/mock-generate with invalid motion_style returns 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "invalid_motion",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("code") == "INVALID_MOTION_STYLE", f"Expected INVALID_MOTION_STYLE, got {detail}"
        print(f"✓ Invalid motion_style returns 400 with INVALID_MOTION_STYLE")
    
    def test_mock_generate_safety_not_confirmed_returns_400(self):
        """POST /api/avatar/studio/mock-generate with safety_confirmed=false returns 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": False
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("code") == "SAFETY_NOT_CONFIRMED", f"Expected SAFETY_NOT_CONFIRMED, got {detail}"
        print(f"✓ safety_confirmed=false returns 400 with SAFETY_NOT_CONFIRMED")
    
    def test_mock_generate_banned_script_returns_400(self):
        """POST /api/avatar/studio/mock-generate with banned script terms returns 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True,
                "script": "Vote for Modi in the election"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("code") == "DISALLOWED_CONTENT", f"Expected DISALLOWED_CONTENT, got {detail}"
        print(f"✓ Banned script terms return 400 with DISALLOWED_CONTENT")
    
    def test_mock_generate_valid_payload_returns_job(self):
        """POST /api/avatar/studio/mock-generate with valid payload returns job_id, eta_seconds, demo_label, is_demo_output"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True,
                "clone_name": "Test Avatar",
                "script": "Hello, welcome to my channel!"
            })
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "job_id" in data, f"Missing job_id: {data}"
        assert "eta_seconds" in data, f"Missing eta_seconds: {data}"
        assert data.get("demo_label") == "Demo / simulated output", f"Expected demo_label='Demo / simulated output', got {data.get('demo_label')}"
        assert data.get("is_demo_output") is True, f"Expected is_demo_output=true, got {data.get('is_demo_output')}"
        
        print(f"✓ Valid payload returns job_id={data.get('job_id')}, eta_seconds={data.get('eta_seconds')}, is_demo_output=true")
        return data


class TestJobPollingAndCompletion:
    """Job polling and auto-completion tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_short_duration_job_completes_in_about_20s(self):
        """15s duration job auto-completes in ~20s ETA"""
        # Create job with 15s duration
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True,
                "clone_name": "Short Test"
            })
        
        assert response.status_code in [200, 201]
        data = response.json()
        job_id = data.get("job_id")
        eta = data.get("eta_seconds")
        
        assert eta == 20, f"Expected eta_seconds=20 for 15s duration, got {eta}"
        print(f"  Job created: job_id={job_id}, eta={eta}s")
        
        # Poll until completion (max 30s)
        start_time = time.time()
        job_data = None
        for i in range(30):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.headers)
            job_data = response.json()
            print(f"    Poll {i+1}: status={job_data.get('status')}, progress={job_data.get('progress')}, stage={job_data.get('stage_label')}")
            if job_data.get("status") == "completed":
                break
        
        elapsed = time.time() - start_time
        assert job_data.get("status") == "completed", f"Job did not complete: {job_data}"
        assert job_data.get("is_demo_output") is True, f"Expected is_demo_output=true"
        assert job_data.get("output_url") is not None, f"Expected output_url"
        
        print(f"✓ 15s duration job completed in {elapsed:.1f}s (eta was {eta}s)")
    
    def test_long_duration_job_completes_in_about_55s(self):
        """60s duration job auto-completes in ~55s ETA"""
        # Create job with 60s duration
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "motion",
                "motion_style": "full_body",
                "duration_seconds": 60,
                "safety_confirmed": True,
                "clone_name": "Long Test"
            })
        
        assert response.status_code in [200, 201]
        data = response.json()
        job_id = data.get("job_id")
        eta = data.get("eta_seconds")
        
        assert eta == 55, f"Expected eta_seconds=55 for 60s duration, got {eta}"
        print(f"  Job created: job_id={job_id}, eta={eta}s")
        
        # Poll until completion (max 70s)
        start_time = time.time()
        job_data = None
        for i in range(70):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.headers)
            job_data = response.json()
            if i % 5 == 0:  # Print every 5 seconds
                print(f"    Poll {i+1}: status={job_data.get('status')}, progress={job_data.get('progress')}, stage={job_data.get('stage_label')}")
            if job_data.get("status") == "completed":
                break
        
        elapsed = time.time() - start_time
        assert job_data.get("status") == "completed", f"Job did not complete: {job_data}"
        assert job_data.get("is_demo_output") is True
        assert job_data.get("output_url") is not None
        
        print(f"✓ 60s duration job completed in {elapsed:.1f}s (eta was {eta}s)")
    
    def test_completed_job_has_required_fields(self):
        """Completed job has is_demo_output=true, stage_label, output_url"""
        # Create and wait for job
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "static",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        
        job_id = response.json().get("job_id")
        
        # Wait for completion
        for _ in range(30):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.headers)
            job_data = response.json()
            if job_data.get("status") == "completed":
                break
        
        assert job_data.get("status") == "completed"
        assert job_data.get("is_demo_output") is True, f"Missing is_demo_output=true"
        assert job_data.get("stage_label") is not None, f"Missing stage_label"
        assert job_data.get("output_url") is not None, f"Missing output_url"
        assert job_data.get("output_export_id") is not None, f"Missing output_export_id"
        
        print(f"✓ Completed job has all required fields: is_demo_output=true, stage_label={job_data.get('stage_label')}, output_url present")


class TestPhotoTrailerRegression:
    """Photo Trailer regression check - must still return 9 templates"""
    
    def test_photo_trailer_templates_returns_9_templates(self):
        """GET /api/photo-trailer/templates still returns 9 templates (freeze held)"""
        response = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert response.status_code == 200, f"Photo Trailer templates failed: {response.status_code}"
        data = response.json()
        
        templates = data.get("templates", [])
        assert len(templates) == 9, f"Expected 9 Photo Trailer templates, got {len(templates)}"
        
        print(f"✓ Photo Trailer regression: {len(templates)} templates (freeze held)")


class TestExistingFunnelEndpoints:
    """Existing avatar funnel endpoints must still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
        
        # Test user login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.test_token = response.json().get("token")
            self.test_headers = {"Authorization": f"Bearer {self.test_token}", "Content-Type": "application/json"}
    
    def test_funnel_track_endpoint_works(self):
        """POST /api/avatar/funnel/track accepts valid step"""
        response = requests.post(f"{BASE_URL}/api/avatar/funnel/track",
            json={
                "step": "avatar_landing_view",
                "session_id": f"test-session-{uuid.uuid4().hex[:8]}",
                "meta": {"test": True}
            })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") is True
        print(f"✓ Funnel track endpoint works")
    
    def test_funnel_track_rejects_unknown_step(self):
        """POST /api/avatar/funnel/track rejects unknown step"""
        response = requests.post(f"{BASE_URL}/api/avatar/funnel/track",
            json={
                "step": "unknown_step",
                "session_id": "test"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Funnel track rejects unknown step")
    
    def test_referral_attribute_endpoint_works(self):
        """POST /api/avatar/referral/attribute works for authenticated user"""
        response = requests.post(f"{BASE_URL}/api/avatar/referral/attribute",
            headers=self.test_headers,
            json={
                "utm_source": "test",
                "utm_campaign": "iteration534",
                "landing_path": "/avatar-demo"
            })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") is True
        print(f"✓ Referral attribute endpoint works: attributed={data.get('attributed')}")
    
    def test_admin_funnel_table_endpoint_works(self):
        """GET /api/avatar/admin/funnel-table works for admin"""
        response = requests.get(f"{BASE_URL}/api/avatar/admin/funnel-table?days=7",
            headers=self.admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "rows" in data, f"Missing 'rows' in response"
        assert "last7_totals" in data, f"Missing 'last7_totals' in response"
        assert "day7_gate" in data, f"Missing 'day7_gate' in response"
        
        print(f"✓ Admin funnel table works: {len(data.get('rows', []))} rows, gate passes={data.get('day7_gate', {}).get('passes_gate')}")


class TestAllAvatarTypes:
    """Test all 4 avatar types work with mock-generate"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_quick_avatar_type(self):
        """quick_avatar type works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201], f"quick_avatar failed: {response.text}"
        print(f"✓ quick_avatar type works")
    
    def test_voice_matched_type(self):
        """voice_matched type works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "voice_matched",
                "motion_style": "talking_head",
                "duration_seconds": 30,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201], f"voice_matched failed: {response.text}"
        print(f"✓ voice_matched type works")
    
    def test_motion_type(self):
        """motion type works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "motion",
                "motion_style": "full_body",
                "duration_seconds": 45,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201], f"motion failed: {response.text}"
        print(f"✓ motion type works")
    
    def test_template_type(self):
        """template type works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "template",
                "motion_style": "gesture",
                "duration_seconds": 30,
                "safety_confirmed": True,
                "template_id": "intro_reel"
            })
        assert response.status_code in [200, 201], f"template failed: {response.text}"
        print(f"✓ template type works")


class TestAllMotionStyles:
    """Test all 4 motion styles work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_talking_head_motion(self):
        """talking_head motion works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        print(f"✓ talking_head motion works")
    
    def test_gesture_motion(self):
        """gesture motion works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "gesture",
                "duration_seconds": 30,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        print(f"✓ gesture motion works")
    
    def test_full_body_motion(self):
        """full_body motion works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "full_body",
                "duration_seconds": 45,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        print(f"✓ full_body motion works")
    
    def test_static_motion(self):
        """static motion works"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "static",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        print(f"✓ static motion works")


class TestAllDurations:
    """Test all 5 duration options work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
    
    def test_15s_duration(self):
        """15s duration works, eta=20s"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 15,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        assert response.json().get("eta_seconds") == 20
        print(f"✓ 15s duration works, eta=20s")
    
    def test_30s_duration(self):
        """30s duration works, eta=35s"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 30,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        assert response.json().get("eta_seconds") == 35
        print(f"✓ 30s duration works, eta=35s")
    
    def test_45s_duration(self):
        """45s duration works, eta=35s"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 45,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        assert response.json().get("eta_seconds") == 35
        print(f"✓ 45s duration works, eta=35s")
    
    def test_60s_duration(self):
        """60s duration works, eta=55s"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 60,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        assert response.json().get("eta_seconds") == 55
        print(f"✓ 60s duration works, eta=55s")
    
    def test_90s_duration(self):
        """90s duration works, eta=55s"""
        response = requests.post(f"{BASE_URL}/api/avatar/studio/mock-generate",
            headers=self.headers,
            json={
                "avatar_type": "quick_avatar",
                "motion_style": "talking_head",
                "duration_seconds": 90,
                "safety_confirmed": True
            })
        assert response.status_code in [200, 201]
        assert response.json().get("eta_seconds") == 55
        print(f"✓ 90s duration works, eta=55s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
