"""
Avatar Studio Backend Tests - Iteration 533
Tests for AI Personal Avatar Studio vertical slice MVP.

Features tested:
- Health endpoint
- Billing/plans endpoint
- Clone CRUD operations
- Consent capture flow
- Training flow (mock)
- Video generation (mock)
- Safety checks (banned content)
- Admin moderation endpoints
- Abuse reporting
- Chat endpoint
- Photo Trailer isolation check
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


class TestAvatarStudioHealth:
    """Health endpoint tests"""
    
    def test_avatar_health_endpoint(self):
        """GET /api/avatar/health returns ok:true and mode:vertical_slice_mock"""
        response = requests.get(f"{BASE_URL}/api/avatar/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") is True, f"Expected ok:true, got {data}"
        assert data.get("mode") == "vertical_slice_mock", f"Expected mode:vertical_slice_mock, got {data.get('mode')}"
        print(f"✓ Avatar health endpoint: {data}")


class TestAvatarStudioBilling:
    """Billing/plans endpoint tests"""
    
    def test_billing_plans_returns_4_plans_4_topups_inr(self):
        """GET /api/avatar/billing/plans returns 4 plans + 4 topups + INR currency"""
        response = requests.get(f"{BASE_URL}/api/avatar/billing/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check plans
        plans = data.get("plans", [])
        assert len(plans) == 4, f"Expected 4 plans, got {len(plans)}"
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids, "Missing 'free' plan"
        assert "creator" in plan_ids, "Missing 'creator' plan"
        assert "pro" in plan_ids, "Missing 'pro' plan"
        assert "studio" in plan_ids, "Missing 'studio' plan"
        
        # Check topups
        topups = data.get("topups", [])
        assert len(topups) == 4, f"Expected 4 topups, got {len(topups)}"
        
        # Check currency
        assert data.get("currency") == "INR", f"Expected currency:INR, got {data.get('currency')}"
        
        print(f"✓ Billing plans: {len(plans)} plans, {len(topups)} topups, currency={data.get('currency')}")


class TestAvatarStudioClones:
    """Clone CRUD and consent flow tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin to get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
        
        # Also login as test user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.test_token = response.json().get("token")
            self.test_headers = {"Authorization": f"Bearer {self.test_token}", "Content-Type": "application/json"}
        else:
            self.test_token = None
            self.test_headers = None
    
    def test_create_clone_self_type_returns_consent_pending(self):
        """POST /api/avatar/clones with self type returns 201/200 with status='consent_pending'"""
        clone_name = f"Test Clone {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones", 
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "consent_pending", f"Expected status:consent_pending, got {data.get('status')}"
        assert data.get("clone_name") == clone_name
        assert data.get("clone_type") == "self"
        assert "id" in data, "Missing clone id"
        print(f"✓ Create clone (self): id={data.get('id')}, status={data.get('status')}")
        return data
    
    def test_create_clone_invalid_type_returns_400(self):
        """POST /api/avatar/clones with invalid clone_type returns 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": "Invalid Clone", "clone_type": "invalid_type"})
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"✓ Invalid clone type returns 400")
    
    def test_consent_rejects_short_video(self):
        """POST /api/avatar/clones/{id}/consent rejects videos < 5s (duration_seconds=3 → 400)"""
        # First create a clone
        clone = self.test_create_clone_self_type_returns_consent_pending()
        clone_id = clone.get("id")
        
        # Submit consent with short duration
        files = {
            'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm'),
        }
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '3',  # Too short
            'user_agent': 'test-agent'
        }
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        assert response.status_code == 400, f"Expected 400 for short video, got {response.status_code}: {response.text}"
        print(f"✓ Consent rejects short video (duration=3s)")
    
    def test_consent_rejects_mismatched_phrase(self):
        """POST consent rejects mismatched phrase (overlap < 80%) → 400"""
        # Create a clone
        clone_name = f"Phrase Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit consent with wrong phrase
        files = {
            'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm'),
        }
        data = {
            'consent_phrase': 'This is a completely different phrase that does not match',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        assert response.status_code == 400, f"Expected 400 for mismatched phrase, got {response.status_code}: {response.text}"
        print(f"✓ Consent rejects mismatched phrase")
    
    def test_consent_rejects_small_video(self):
        """POST consent rejects too-small video bytes (<5KB) → 400"""
        # Create a clone
        clone_name = f"Small Video Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit consent with tiny video
        files = {
            'selfie_video': ('consent.webm', b'x' * 100, 'video/webm'),  # Only 100 bytes
        }
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        assert response.status_code == 400, f"Expected 400 for small video, got {response.status_code}: {response.text}"
        print(f"✓ Consent rejects small video (<5KB)")
    
    def test_consent_valid_submission(self):
        """POST consent with valid phrase + 5s+ duration + 5KB+ video → 200, status='pending'"""
        # Create a clone
        clone_name = f"Valid Consent Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit valid consent
        files = {
            'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm'),  # 10KB
        }
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        assert response.status_code == 200, f"Expected 200 for valid consent, got {response.status_code}: {response.text}"
        consent_data = response.json()
        assert consent_data.get("status") == "pending", f"Expected status:pending, got {consent_data.get('status')}"
        
        # Verify clone status flipped to consent_review
        clone_response = requests.get(f"{BASE_URL}/api/avatar/clones/{clone_id}",
            headers=self.admin_headers)
        clone_data = clone_response.json()
        assert clone_data.get("status") == "consent_review", f"Expected clone status:consent_review, got {clone_data.get('status')}"
        
        print(f"✓ Valid consent submission: consent_id={consent_data.get('consent_id')}, clone status=consent_review")
        return clone_id


class TestAvatarStudioTraining:
    """Training flow tests"""
    
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
    
    def test_train_before_consent_approval_returns_403(self):
        """POST /train BEFORE consent approval returns 403"""
        # Create a clone
        clone_name = f"Train Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Try to train without consent approval
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/train",
            headers=self.admin_headers, json={})
        
        assert response.status_code == 403, f"Expected 403 for training without consent, got {response.status_code}: {response.text}"
        print(f"✓ Training before consent approval returns 403")
    
    def test_full_training_flow_with_consent_approval(self):
        """Full flow: create clone → submit consent → admin approve → voice profile → train → ready"""
        # 1. Create clone
        clone_name = f"Full Flow Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        print(f"  Created clone: {clone_id}")
        
        # 2. Submit consent
        files = {
            'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm'),
        }
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        assert response.status_code == 200
        print(f"  Consent submitted")
        
        # 3. Admin approve consent
        response = requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "approve_consent", "notes": "test approval"})
        assert response.status_code == 200, f"Consent approval failed: {response.text}"
        print(f"  Consent approved")
        
        # Verify clone status is consent_approved
        response = requests.get(f"{BASE_URL}/api/avatar/clones/{clone_id}",
            headers=self.admin_headers)
        assert response.json().get("status") == "consent_approved"
        
        # 4. Create voice profile
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/voice-profile",
            headers=self.admin_headers)
        assert response.status_code == 200
        voice_data = response.json()
        assert voice_data.get("voice_model_ref", "").startswith("mock_voice::"), f"Expected mock_voice ref, got {voice_data}"
        print(f"  Voice profile created: {voice_data.get('voice_model_ref')}")
        
        # 5. Start training
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/train",
            headers=self.admin_headers, json={})
        assert response.status_code == 200
        train_data = response.json()
        job_id = train_data.get("job_id")
        assert job_id is not None, "Expected job_id from training"
        print(f"  Training started: job_id={job_id}")
        
        # 6. Poll for completion (mock worker completes in ~8s)
        for i in range(15):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.admin_headers)
            job_data = response.json()
            print(f"    Poll {i+1}: status={job_data.get('status')}, progress={job_data.get('progress')}")
            if job_data.get("status") == "completed":
                break
        
        assert job_data.get("status") == "completed", f"Training did not complete in time: {job_data}"
        
        # 7. Verify clone is ready
        response = requests.get(f"{BASE_URL}/api/avatar/clones/{clone_id}",
            headers=self.admin_headers)
        clone_data = response.json()
        assert clone_data.get("status") == "ready", f"Expected clone status:ready, got {clone_data.get('status')}"
        assert clone_data.get("face_model_ref", "").startswith("mock_face::"), f"Expected mock_face ref"
        
        print(f"✓ Full training flow completed: clone is ready with face_model_ref={clone_data.get('face_model_ref')}")
        return clone_id


class TestAvatarStudioVideoGeneration:
    """Video generation and safety tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and create a ready clone"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json().get("token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
        
        # Create and prepare a ready clone for video generation tests
        self.ready_clone_id = self._create_ready_clone()
    
    def _create_ready_clone(self):
        """Helper to create a fully ready clone"""
        clone_name = f"Video Gen Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit consent
        files = {'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm')}
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        # Approve consent
        requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "approve_consent"})
        
        # Create voice profile
        requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/voice-profile",
            headers=self.admin_headers)
        
        # Train
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/train",
            headers=self.admin_headers, json={})
        job_id = response.json().get("job_id")
        
        # Wait for training
        for _ in range(15):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.admin_headers)
            if response.json().get("status") == "completed":
                break
        
        return clone_id
    
    def test_generate_video_with_valid_script(self):
        """POST /generate-video with valid script returns job_id, completes within 10s, creates export"""
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": "Hello, welcome to my channel. Today I will share three productivity tips that changed my life.",
                "platform": "youtube"
            })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        job_id = data.get("job_id")
        assert job_id is not None, "Expected job_id"
        print(f"  Video generation started: job_id={job_id}")
        
        # Poll for completion
        for i in range(12):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.admin_headers)
            job_data = response.json()
            print(f"    Poll {i+1}: status={job_data.get('status')}, progress={job_data.get('progress')}")
            if job_data.get("status") == "completed":
                break
        
        assert job_data.get("status") == "completed", f"Video generation did not complete: {job_data}"
        
        # Check exports
        response = requests.get(f"{BASE_URL}/api/avatar/clones/{self.ready_clone_id}/exports",
            headers=self.admin_headers)
        exports = response.json().get("exports", [])
        assert len(exports) > 0, "Expected at least one export"
        
        export = exports[0]
        assert export.get("visible_label_text") == "AI-generated avatar", f"Expected visible_label_text='AI-generated avatar', got {export.get('visible_label_text')}"
        assert export.get("forensic_watermark_id", "").startswith("WM-"), f"Expected forensic_watermark_id starting with 'WM-', got {export.get('forensic_watermark_id')}"
        assert export.get("disclosure_text"), "Expected non-empty disclosure_text"
        
        metadata = export.get("metadata", {})
        assert metadata.get("ai_generated") is True, "Expected metadata.ai_generated=true"
        assert metadata.get("youtube_synthetic_disclosure_required") is True, "Expected metadata.youtube_synthetic_disclosure_required=true"
        
        print(f"✓ Video generation completed with proper export metadata")
        print(f"  visible_label_text: {export.get('visible_label_text')}")
        print(f"  forensic_watermark_id: {export.get('forensic_watermark_id')}")
        print(f"  disclosure_text: {export.get('disclosure_text')[:50]}...")
    
    def test_generate_video_banned_content_modi(self):
        """POST /generate-video with script containing 'modi' → 400 with code='DISALLOWED_CONTENT'"""
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": "Vote for Modi in the upcoming election",
                "platform": "youtube"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("code") == "DISALLOWED_CONTENT", f"Expected code:DISALLOWED_CONTENT, got {detail}"
        print(f"✓ Banned content 'modi' rejected with DISALLOWED_CONTENT")
    
    def test_generate_video_banned_content_otp(self):
        """POST /generate-video with script containing 'OTP' → 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": "Please share your OTP with me for verification",
                "platform": "youtube"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Banned content 'OTP' rejected")
    
    def test_generate_video_banned_content_send_money(self):
        """POST /generate-video with script containing 'send me money' → 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": "Please send me money urgently to this account",
                "platform": "youtube"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Banned content 'send me money' rejected")
    
    def test_generate_video_empty_script(self):
        """POST /generate-video with empty script → 400"""
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": "",
                "platform": "youtube"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Empty script rejected")
    
    def test_generate_video_script_too_long(self):
        """POST /generate-video with script > 1200 chars → 400"""
        long_script = "x" * 1300
        response = requests.post(f"{BASE_URL}/api/avatar/generate-video",
            headers=self.admin_headers,
            json={
                "clone_id": self.ready_clone_id,
                "script": long_script,
                "platform": "youtube"
            })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Script > 1200 chars rejected")


class TestAvatarStudioAdmin:
    """Admin moderation endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and test user"""
        # Admin login
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
        else:
            self.test_token = None
            self.test_headers = None
    
    def test_admin_list_clones_as_admin(self):
        """GET /admin/clones returns clones list for admin"""
        response = requests.get(f"{BASE_URL}/api/avatar/admin/clones",
            headers=self.admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "clones" in data, "Expected 'clones' key in response"
        print(f"✓ Admin list clones: {len(data.get('clones', []))} clones")
    
    def test_admin_list_clones_as_regular_user_returns_403(self):
        """GET /admin/clones as regular user returns 403"""
        if not self.test_headers:
            pytest.skip("Test user not available")
        
        response = requests.get(f"{BASE_URL}/api/avatar/admin/clones",
            headers=self.test_headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Admin endpoint returns 403 for regular user")
    
    def test_admin_list_pending_consents(self):
        """GET /admin/consents/pending returns pending consents"""
        response = requests.get(f"{BASE_URL}/api/avatar/admin/consents/pending",
            headers=self.admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "consents" in data, "Expected 'consents' key"
        print(f"✓ Admin pending consents: {len(data.get('consents', []))} pending")
    
    def test_admin_disable_and_enable_clone(self):
        """POST /admin/clones/{id}/action disable_clone and enable_clone"""
        # Create a clone
        clone_name = f"Disable Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit and approve consent
        files = {'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm')}
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "approve_consent"})
        
        # Disable clone
        response = requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "disable_clone", "notes": "test disable"})
        assert response.status_code == 200
        
        # Verify disabled
        response = requests.get(f"{BASE_URL}/api/avatar/clones/{clone_id}",
            headers=self.admin_headers)
        assert response.json().get("status") == "disabled"
        print(f"  Clone disabled")
        
        # Enable clone
        response = requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "enable_clone"})
        assert response.status_code == 200
        
        # Verify enabled (should be consent_approved since no face_model_ref)
        response = requests.get(f"{BASE_URL}/api/avatar/clones/{clone_id}",
            headers=self.admin_headers)
        assert response.json().get("status") in ["consent_approved", "ready"]
        print(f"✓ Admin disable/enable clone works")


class TestAvatarStudioChat:
    """Chat endpoint tests"""
    
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
    
    def _create_ready_clone(self):
        """Helper to create a ready clone"""
        clone_name = f"Chat Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        files = {'selfie_video': ('consent.webm', b'x' * 10000, 'video/webm')}
        data = {
            'consent_phrase': 'I consent to creating an AI avatar of myself for my own content. I understand all output will be labeled AI-generated.',
            'duration_seconds': '6',
            'user_agent': 'test-agent'
        }
        requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/consent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files, data=data)
        
        requests.post(f"{BASE_URL}/api/avatar/admin/clones/{clone_id}/action",
            headers=self.admin_headers,
            json={"action": "approve_consent"})
        
        requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/voice-profile",
            headers=self.admin_headers)
        
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/train",
            headers=self.admin_headers, json={})
        job_id = response.json().get("job_id")
        
        for _ in range(15):
            time.sleep(1)
            response = requests.get(f"{BASE_URL}/api/avatar/jobs/{job_id}",
                headers=self.admin_headers)
            if response.json().get("status") == "completed":
                break
        
        return clone_id
    
    def test_chat_safe_message_returns_reply_with_label(self):
        """POST /chat with safe message returns reply containing visible label"""
        clone_id = self._create_ready_clone()
        
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/chat",
            headers=self.admin_headers,
            json={"clone_id": clone_id, "message": "Hello, how are you today?"})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "AI-generated avatar" in data.get("reply", ""), f"Expected visible label in reply"
        assert data.get("visible_label") == "AI-generated avatar"
        print(f"✓ Chat returns reply with visible label")
    
    def test_chat_banned_message_returns_400(self):
        """POST /chat with banned message → 400"""
        clone_id = self._create_ready_clone()
        
        response = requests.post(f"{BASE_URL}/api/avatar/clones/{clone_id}/chat",
            headers=self.admin_headers,
            json={"clone_id": clone_id, "message": "Please share your OTP for verification"})
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ Chat rejects banned message")


class TestAvatarStudioAbuseReports:
    """Abuse report tests"""
    
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
    
    def test_abuse_report_flow(self):
        """POST /abuse-report creates report, GET /admin/abuse-reports lists it, action flips status"""
        # Create a clone to report
        clone_name = f"Abuse Test {uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/clones",
            headers=self.admin_headers,
            json={"clone_name": clone_name, "clone_type": "self"})
        clone_id = response.json().get("id")
        
        # Submit abuse report
        response = requests.post(f"{BASE_URL}/api/avatar/abuse-report",
            headers=self.admin_headers,
            json={"clone_id": clone_id, "reason": "This is a test abuse report for testing purposes"})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        report_id = response.json().get("report_id")
        assert report_id is not None
        print(f"  Abuse report created: {report_id}")
        
        # List abuse reports
        response = requests.get(f"{BASE_URL}/api/avatar/admin/abuse-reports",
            headers=self.admin_headers)
        assert response.status_code == 200
        reports = response.json().get("reports", [])
        report_ids = [r.get("id") for r in reports]
        assert report_id in report_ids, "Report not found in list"
        print(f"  Report found in admin list")
        
        # Action the report
        response = requests.post(f"{BASE_URL}/api/avatar/admin/abuse-reports/{report_id}/action",
            headers=self.admin_headers,
            json={"status": "actioned", "notes": "test action"})
        assert response.status_code == 200
        
        # Verify status changed
        response = requests.get(f"{BASE_URL}/api/avatar/admin/abuse-reports",
            headers=self.admin_headers)
        reports = response.json().get("reports", [])
        report = next((r for r in reports if r.get("id") == report_id), None)
        assert report.get("status") == "actioned"
        print(f"✓ Abuse report flow complete: created → listed → actioned")


class TestPhotoTrailerIsolation:
    """Verify Photo Trailer is not affected by Avatar Studio"""
    
    def test_photo_trailer_templates_still_works(self):
        """GET /api/photo-trailer/templates still works — Avatar Studio did not break Photo Trailer"""
        response = requests.get(f"{BASE_URL}/api/photo-trailer/templates")
        assert response.status_code == 200, f"Photo Trailer templates check failed: {response.status_code}"
        data = response.json()
        assert "templates" in data, f"Photo Trailer templates missing: {data}"
        assert len(data.get("templates", [])) > 0, "Photo Trailer has no templates"
        print(f"✓ Photo Trailer templates endpoint still works: {len(data.get('templates', []))} templates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
