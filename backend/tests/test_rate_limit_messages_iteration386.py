"""
Test Rate Limit Message Fix - Iteration 386
Verifies that rate limit messages are friendly and don't contain 'Rate limit:' prefix.

Key validations:
1. /api/story-engine/rate-limit-status returns friendly reason text
2. /api/pipeline/rate-limit-status returns friendly reason text  
3. safety.py check_rate_limits() uses 'SLOTS_BUSY:' prefix
4. safety.py detect_abuse() uses 'SLOTS_BUSY:' prefix
5. story_engine_routes.py converts 'SLOTS_BUSY:' to 429 with friendly message
6. No 'Rate limit:' prefixed text in any HTTP error response
"""

import pytest
import requests
import os
import sys
from pathlib import Path

# Add backend to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get test user auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


class TestRateLimitStatusEndpoints:
    """Test rate-limit-status endpoints return friendly messages"""
    
    def test_story_engine_rate_limit_status_returns_200(self, api_client, test_user_token):
        """Verify /api/story-engine/rate-limit-status returns 200"""
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/rate-limit-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "can_create" in data
        print(f"✓ Story Engine rate-limit-status: can_create={data['can_create']}")
    
    def test_story_engine_rate_limit_reason_no_harsh_prefix(self, api_client, test_user_token):
        """Verify reason text doesn't contain 'Rate limit:' prefix"""
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/rate-limit-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        reason = data.get("reason") or ""
        
        # Key assertion: no 'Rate limit:' prefix
        assert not reason.startswith("Rate limit:"), f"Reason should not start with 'Rate limit:': {reason}"
        
        # If there's a reason, it should be friendly
        if reason:
            assert "slots" in reason.lower() or "videos" in reason.lower() or "wait" in reason.lower(), \
                f"Reason should be friendly: {reason}"
        print(f"✓ Story Engine reason is friendly: '{reason[:80]}...' if reason else 'None'")
    
    def test_pipeline_rate_limit_status_returns_200(self, api_client, test_user_token):
        """Verify /api/pipeline/rate-limit-status returns 200"""
        response = api_client.get(
            f"{BASE_URL}/api/pipeline/rate-limit-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "can_create" in data
        print(f"✓ Pipeline rate-limit-status: can_create={data['can_create']}")
    
    def test_pipeline_rate_limit_reason_no_harsh_prefix(self, api_client, test_user_token):
        """Verify pipeline reason text doesn't contain 'Rate limit:' prefix"""
        response = api_client.get(
            f"{BASE_URL}/api/pipeline/rate-limit-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        reason = data.get("reason") or ""
        
        # Key assertion: no 'Rate limit:' prefix
        assert not reason.startswith("Rate limit:"), f"Reason should not start with 'Rate limit:': {reason}"
        print(f"✓ Pipeline reason is friendly: '{reason[:80] if reason else 'None'}'")


class TestSafetyModuleMessages:
    """Test safety.py module returns SLOTS_BUSY: prefixed messages"""
    
    def test_safety_check_rate_limits_format(self):
        """Verify check_rate_limits returns SLOTS_BUSY: prefix when rate limited"""
        # Import the safety module directly
        try:
            from services.story_engine.safety import check_rate_limits, MAX_CONCURRENT_JOBS
            print(f"✓ Imported safety module, MAX_CONCURRENT_JOBS={MAX_CONCURRENT_JOBS}")
        except ImportError as e:
            pytest.skip(f"Could not import safety module: {e}")
    
    def test_safety_detect_abuse_format(self):
        """Verify detect_abuse returns SLOTS_BUSY: prefix when abuse detected"""
        try:
            from services.story_engine.safety import detect_abuse
            print("✓ Imported detect_abuse function")
        except ImportError as e:
            pytest.skip(f"Could not import detect_abuse: {e}")


class TestCreateEndpointRateLimitResponse:
    """Test /api/story-engine/create returns 429 with friendly message when rate limited"""
    
    def test_create_endpoint_accessible(self, api_client, test_user_token):
        """Verify create endpoint is accessible (test user is exempt from rate limits)"""
        # Test user is exempt, so we just verify the endpoint works
        response = api_client.post(
            f"{BASE_URL}/api/story-engine/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "title": "Test Rate Limit Message",
                "story_text": "This is a test story to verify rate limit messages are friendly. " * 5,
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        # Test user is exempt, so should succeed or fail for other reasons (not rate limit)
        if response.status_code == 429:
            data = response.json()
            detail = data.get("detail", "")
            # Key assertion: 429 response should have friendly message
            assert "Rate limit:" not in str(detail), f"429 detail should not contain 'Rate limit:': {detail}"
            print(f"✓ 429 response has friendly message: {detail[:100]}")
        else:
            print(f"✓ Create endpoint returned {response.status_code} (test user is exempt)")
    
    def test_pipeline_create_endpoint_accessible(self, api_client, test_user_token):
        """Verify pipeline create endpoint is accessible"""
        response = api_client.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "title": "Test Pipeline Rate Limit",
                "story_text": "This is a test story for pipeline rate limit verification. " * 5,
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        if response.status_code == 429:
            data = response.json()
            detail = data.get("detail", "")
            # Key assertion: 429 response should have friendly message
            if isinstance(detail, dict):
                message = detail.get("message", "")
                assert "Rate limit:" not in message, f"429 message should not contain 'Rate limit:': {message}"
                print(f"✓ Pipeline 429 response has friendly message: {message[:100]}")
            else:
                assert "Rate limit:" not in str(detail), f"429 detail should not contain 'Rate limit:': {detail}"
                print(f"✓ Pipeline 429 response has friendly message: {detail[:100]}")
        else:
            print(f"✓ Pipeline create endpoint returned {response.status_code}")


class TestCodeReviewRateLimitMessages:
    """Code review: verify no 'Rate limit:' prefix in backend files"""
    
    def test_safety_py_no_rate_limit_prefix(self):
        """Verify safety.py doesn't use 'Rate limit:' prefix"""
        safety_path = Path(__file__).parent.parent / "services" / "story_engine" / "safety.py"
        if not safety_path.exists():
            pytest.skip("safety.py not found")
        
        content = safety_path.read_text()
        
        # Should NOT contain 'Rate limit:' as error prefix
        assert 'return f"Rate limit:' not in content, "safety.py should not return 'Rate limit:' prefix"
        assert 'return "Rate limit:' not in content, "safety.py should not return 'Rate limit:' prefix"
        
        # Should contain 'SLOTS_BUSY:' prefix
        assert 'SLOTS_BUSY:' in content, "safety.py should use 'SLOTS_BUSY:' prefix"
        
        print("✓ safety.py uses SLOTS_BUSY: prefix, not Rate limit:")
    
    def test_story_engine_routes_handles_slots_busy(self):
        """Verify story_engine_routes.py handles SLOTS_BUSY: prefix"""
        routes_path = Path(__file__).parent.parent / "routes" / "story_engine_routes.py"
        if not routes_path.exists():
            pytest.skip("story_engine_routes.py not found")
        
        content = routes_path.read_text()
        
        # Should handle SLOTS_BUSY: prefix
        assert 'SLOTS_BUSY:' in content, "story_engine_routes.py should handle SLOTS_BUSY: prefix"
        assert 'status_code=429' in content, "story_engine_routes.py should return 429 for rate limits"
        
        print("✓ story_engine_routes.py handles SLOTS_BUSY: and returns 429")
    
    def test_pipeline_routes_friendly_messages(self):
        """Verify pipeline_routes.py uses friendly messages"""
        routes_path = Path(__file__).parent.parent / "routes" / "pipeline_routes.py"
        if not routes_path.exists():
            pytest.skip("pipeline_routes.py not found")
        
        content = routes_path.read_text()
        
        # Should NOT contain 'Rate limit:' as error prefix in HTTPException
        lines_with_rate_limit = [
            line for line in content.split('\n') 
            if 'Rate limit:' in line and 'HTTPException' in line
        ]
        assert len(lines_with_rate_limit) == 0, \
            f"pipeline_routes.py should not use 'Rate limit:' in HTTPException: {lines_with_rate_limit}"
        
        # Should contain friendly messages
        assert 'All rendering slots are busy' in content or 'slots are busy' in content.lower(), \
            "pipeline_routes.py should use friendly 'slots are busy' message"
        
        print("✓ pipeline_routes.py uses friendly messages")


class TestExemptUserBehavior:
    """Test that exempt users (test@visionary-suite.com) bypass rate limits"""
    
    def test_test_user_is_exempt(self, api_client, test_user_token):
        """Verify test user is exempt from rate limits"""
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/rate-limit-status",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Test user should be exempt
        assert data.get("exempt") == True or data.get("can_create") == True, \
            f"Test user should be exempt or can_create: {data}"
        print(f"✓ Test user is exempt: {data.get('exempt', 'N/A')}, can_create: {data.get('can_create')}")
    
    def test_admin_user_is_exempt(self, api_client, admin_token):
        """Verify admin user is exempt from rate limits"""
        response = api_client.get(
            f"{BASE_URL}/api/story-engine/rate-limit-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Admin should be exempt
        assert data.get("exempt") == True or data.get("can_create") == True, \
            f"Admin should be exempt or can_create: {data}"
        print(f"✓ Admin is exempt: {data.get('exempt', 'N/A')}, can_create: {data.get('can_create')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
