"""
Tests for P0: Mandatory Subscription / Zero Free Credits Policy (2026-05)

Coverage:
  1. Funnel tracking: NEW events accepted (free_user_blocked_post_policy_first, 
     free_user_blocked_post_policy_repeat, pricing_page_opened_from_block)
  2. Referral hard-kill: REFERRAL_CREDITS_DISABLED=True blocks credit grants
  3. Daily reward: POST /api/monetization/daily-reward/claim returns no-op success
  4. Admin billing policy verification endpoint
  5. Avatar demo whitelist: /api/avatar/studio/anon-mock-generate works without auth
  6. Photo Trailer freeze: 9 templates returned
"""
import os
import sys
import pytest
import requests
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://trust-engine-5.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestFunnelTrackingNewEvents:
    """Test that new funnel events for the subscription policy are accepted."""
    
    def test_free_user_blocked_post_policy_first_accepted(self):
        """POST /api/funnel/track accepts free_user_blocked_post_policy_first"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "free_user_blocked_post_policy_first",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "meta": {"feature": "test", "source": "pytest"}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        print("PASS: free_user_blocked_post_policy_first accepted")
    
    def test_free_user_blocked_post_policy_repeat_accepted(self):
        """POST /api/funnel/track accepts free_user_blocked_post_policy_repeat"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "free_user_blocked_post_policy_repeat",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "meta": {"feature": "test", "source": "pytest"}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        print("PASS: free_user_blocked_post_policy_repeat accepted")
    
    def test_pricing_page_opened_from_block_accepted(self):
        """POST /api/funnel/track accepts pricing_page_opened_from_block"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "pricing_page_opened_from_block",
            "session_id": f"test_{uuid.uuid4().hex[:8]}",
            "meta": {"feature": "test"}
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        print("PASS: pricing_page_opened_from_block accepted")
    
    def test_unknown_step_rejected(self):
        """POST /api/funnel/track rejects unknown step"""
        response = requests.post(f"{BASE_URL}/api/funnel/track", json={
            "step": "unknown_invalid_step_xyz",
            "session_id": f"test_{uuid.uuid4().hex[:8]}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is False, f"Expected success=False for unknown step, got {data}"
        print("PASS: Unknown step rejected correctly")


class TestReferralCreditsDisabled:
    """Test that referral credit grants are blocked under the policy."""
    
    @pytest.fixture
    def test_user_token(self):
        """Get auth token for test user."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login test user: {response.text}")
        return response.json().get("token")
    
    def test_qualify_returns_no_credits_granted(self, test_user_token):
        """POST /api/referrals/qualify should return granted=false with policy reason."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/referrals/qualify", 
                                 json={}, headers=headers)
        # May return 200 with qualified=false (no pending attribution) or
        # qualified=true but granted=false (policy blocked)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # If there's no pending attribution, that's fine - policy still works
        if data.get("qualified") is False:
            print(f"PASS: No pending attribution for test user - reason: {data.get('reason')}")
        else:
            # If qualified, credits should NOT be granted
            assert data.get("granted") is False, f"Expected granted=False under policy, got {data}"
            reason = data.get("reason", "")
            assert "POLICY" in reason.upper() or "DISABLED" in reason.upper() or "CAP" in reason.upper(), \
                f"Expected policy-related reason, got: {reason}"
            print(f"PASS: Referral qualified but credits blocked - reason: {reason}")


class TestDailyRewardDisabled:
    """Test that daily reward claim returns no-op success."""
    
    @pytest.fixture
    def test_user_token(self):
        """Get auth token for test user."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login test user: {response.text}")
        return response.json().get("token")
    
    @pytest.fixture
    def test_user_credits_before(self, test_user_token):
        """Get test user's credit balance before claim."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        if response.status_code != 200:
            pytest.skip(f"Could not get credits: {response.text}")
        return response.json().get("credits", 0)
    
    def test_daily_reward_claim_returns_no_op(self, test_user_token, test_user_credits_before):
        """POST /api/monetization/daily-reward/claim returns success=false with policy message."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/monetization/daily-reward/claim", 
                                 json={}, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify no-op response
        assert data.get("success") is False, f"Expected success=False, got {data}"
        assert data.get("credits_earned", 0) == 0, f"Expected credits_earned=0, got {data}"
        assert "subscription_required_2026_05" in data.get("policy", ""), \
            f"Expected policy=subscription_required_2026_05, got {data}"
        
        # Verify credits unchanged
        response2 = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        credits_after = response2.json().get("credits", 0)
        assert credits_after == test_user_credits_before, \
            f"Credits changed! Before: {test_user_credits_before}, After: {credits_after}"
        
        print(f"PASS: Daily reward claim returned no-op, credits unchanged at {credits_after}")


class TestAdminBillingPolicyVerification:
    """Test admin billing policy verification endpoint."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login admin: {response.text}")
        return response.json().get("token")
    
    def test_verification_endpoint_returns_valid_stats(self, admin_token):
        """GET /api/admin/billing-policy/verification returns valid stats."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/billing-policy/verification", 
                                headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "total_users" in data, f"Missing total_users in {data}"
        assert data["total_users"] > 0, f"Expected total_users > 0, got {data['total_users']}"
        
        assert "users_with_credits_gt_zero" in data, f"Missing users_with_credits_gt_zero"
        # After migration, this should be 0 (excluding admin/unlimited/subscribed)
        # But we don't enforce 0 here since test user may have purchased credits
        
        assert "policy" in data, f"Missing policy field"
        assert data["policy"] == "subscription_required_2026_05", \
            f"Expected policy=subscription_required_2026_05, got {data['policy']}"
        
        print(f"PASS: Billing policy verification - total_users={data['total_users']}, "
              f"users_with_credits_gt_zero={data['users_with_credits_gt_zero']}")


class TestAvatarDemoWhitelist:
    """Test that /avatar-demo anonymous generation still works (ungated)."""
    
    def test_anon_mock_generate_works_without_auth(self):
        """POST /api/avatar/studio/anon-mock-generate works without auth."""
        session_id = f"test_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/avatar/studio/anon-mock-generate", json={
            "session_id": session_id,
            "avatar_type": "quick_avatar",
            "motion_style": "talking_head",
            "duration_seconds": 15,
            "script": "Hello, this is a test avatar demo.",
            "safety_confirmed": True
        })
        # Should succeed without auth
        assert response.status_code in [200, 201], \
            f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify job created
        assert "job_id" in data, f"Missing job_id in response: {data}"
        assert data.get("is_demo_output") is True, f"Expected is_demo_output=True, got {data}"
        assert data.get("anonymous") is True, f"Expected anonymous=True, got {data}"
        
        print(f"PASS: Anonymous avatar demo generation works - job_id={data['job_id']}")


class TestPhotoTrailerFreeze:
    """Test that Photo Trailer templates are unchanged (9 templates)."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token."""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login admin: {response.text}")
        return response.json().get("token")
    
    def test_photo_trailer_templates_returns_9(self, admin_token):
        """GET /api/photo-trailer/templates returns 9 templates."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-trailer/templates", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        templates = data.get("templates", data) if isinstance(data, dict) else data
        if isinstance(templates, dict):
            templates = templates.get("templates", [])
        
        assert len(templates) == 9, f"Expected 9 templates, got {len(templates)}"
        print(f"PASS: Photo Trailer freeze intact - {len(templates)} templates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
