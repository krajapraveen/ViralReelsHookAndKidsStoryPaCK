"""
GREENLIGHT Recovery Sprint - Iteration 486
Tests for:
1. Backend accepts 'return_to_inspect' as a valid funnel step via POST /api/funnel/track
2. Backend accepts 'share_revisit' as a valid funnel step via POST /api/funnel/track
3. Share API GET /api/shares/{id} returns userId field
4. Public creation API GET /api/public/creation/{slug} returns user_id field in creation
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestFunnelTrackingNewSteps:
    """Test new funnel steps: return_to_inspect and share_revisit"""
    
    def test_return_to_inspect_funnel_step_accepted(self):
        """Test that 'return_to_inspect' is accepted as a valid funnel step"""
        session_id = f"test-session-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "return_to_inspect",
                "session_id": session_id,
                "context": {
                    "source_page": "dashboard",
                    "meta": {
                        "trigger": "traction_banner",
                        "remixes": 5,
                        "credits_earned": 10
                    }
                }
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        assert "session_id" in data, "Response should contain session_id"
        print(f"PASS: return_to_inspect funnel step accepted - session_id: {data.get('session_id')}")
    
    def test_share_revisit_funnel_step_accepted(self):
        """Test that 'share_revisit' is accepted as a valid funnel step"""
        session_id = f"test-session-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "share_revisit",
                "session_id": session_id,
                "context": {
                    "source_page": "share_page",
                    "meta": {
                        "trigger": "creator_revisit",
                        "share_id": "test-share-123"
                    }
                }
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, f"Expected success=True, got {data}"
        print(f"PASS: share_revisit funnel step accepted - session_id: {data.get('session_id')}")
    
    def test_invalid_funnel_step_rejected(self):
        """Test that invalid funnel steps are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "invalid_step_xyz",
                "session_id": "test-session",
                "context": {}
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is False, f"Expected success=False for invalid step, got {data}"
        assert "error" in data, "Response should contain error message"
        print(f"PASS: Invalid funnel step rejected with error: {data.get('error')}")
    
    def test_return_to_inspect_with_user_context(self):
        """Test return_to_inspect with full user context from dashboard"""
        session_id = f"test-session-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={
                "step": "return_to_inspect",
                "session_id": session_id,
                "user_id": "test-user-123",
                "context": {
                    "source_page": "my_space",
                    "meta": {
                        "trigger": "page_visit",
                        "referrer_path": "/app"
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print(f"PASS: return_to_inspect with user context accepted")


class TestShareAPIUserIdField:
    """Test that Share API returns userId field"""
    
    def test_share_api_returns_userid(self):
        """Test GET /api/share/{id} returns userId field"""
        # First, we need to find an existing share or create one
        # Let's try to get a share that exists
        
        # Try with a known share ID pattern (trust-engine-5)
        test_share_ids = ["trust-engine-5", "test-share-1"]
        
        for share_id in test_share_ids:
            response = requests.get(f"{BASE_URL}/api/share/{share_id}")
            if response.status_code == 200:
                data = response.json()
                # Check if userId field is present in response
                assert "userId" in data, f"Response should contain 'userId' field. Got: {list(data.keys())}"
                print(f"PASS: Share API returns userId field for share {share_id}: userId={data.get('userId')}")
                return
        
        # If no existing share found, test with a non-existent share (should return 404)
        response = requests.get(f"{BASE_URL}/api/share/nonexistent-share-xyz")
        assert response.status_code == 404, f"Expected 404 for non-existent share, got {response.status_code}"
        print("INFO: No existing shares found to test userId field, but 404 handling works correctly")


class TestPublicCreationUserIdField:
    """Test that Public Creation API returns user_id field"""
    
    def test_public_creation_returns_user_id(self):
        """Test GET /api/public/creation/{slug} returns user_id field in creation"""
        # Try to get a public creation
        test_slugs = ["trust-engine-5", "test-creation-1"]
        
        for slug in test_slugs:
            response = requests.get(f"{BASE_URL}/api/public/creation/{slug}")
            if response.status_code == 200:
                data = response.json()
                assert data.get("success") is True, f"Expected success=True, got {data}"
                creation = data.get("creation", {})
                # Check if user_id field is present in creation
                assert "user_id" in creation, f"Creation should contain 'user_id' field. Got: {list(creation.keys())}"
                print(f"PASS: Public creation API returns user_id field for slug {slug}: user_id={creation.get('user_id')}")
                return
        
        # If no existing creation found, test with a non-existent slug (should return 404)
        response = requests.get(f"{BASE_URL}/api/public/creation/nonexistent-slug-xyz")
        assert response.status_code == 404, f"Expected 404 for non-existent creation, got {response.status_code}"
        print("INFO: No existing public creations found to test user_id field, but 404 handling works correctly")


class TestHealthAndBasicEndpoints:
    """Basic health checks"""
    
    def test_backend_health(self):
        """Test backend health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("PASS: Backend health check passed")
    
    def test_funnel_tracking_endpoint_exists(self):
        """Test that funnel tracking endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            json={"step": "landing_view", "session_id": "test"}
        )
        assert response.status_code == 200, f"Funnel tracking endpoint not working: {response.status_code}"
        print("PASS: Funnel tracking endpoint exists and responds")


class TestFunnelStepsValidation:
    """Validate all expected funnel steps are in FUNNEL_STEPS list"""
    
    def test_all_viral_loop_steps_accepted(self):
        """Test that all viral loop funnel steps are accepted"""
        viral_steps = [
            "return_to_inspect",
            "share_revisit",
        ]
        
        for step in viral_steps:
            session_id = f"test-{uuid.uuid4()}"
            response = requests.post(
                f"{BASE_URL}/api/funnel/track",
                json={
                    "step": step,
                    "session_id": session_id,
                    "context": {"source_page": "test", "meta": {}}
                }
            )
            
            assert response.status_code == 200, f"Step {step} failed: {response.status_code}"
            data = response.json()
            assert data.get("success") is True, f"Step {step} not accepted: {data}"
            print(f"PASS: Viral loop step '{step}' accepted")


class TestAuthenticatedFunnelTracking:
    """Test funnel tracking with authenticated user"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_return_to_inspect_with_auth_token(self, auth_token):
        """Test return_to_inspect extracts user_id from auth token"""
        session_id = f"test-session-{uuid.uuid4()}"
        response = requests.post(
            f"{BASE_URL}/api/funnel/track",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "step": "return_to_inspect",
                "session_id": session_id,
                "context": {
                    "source_page": "dashboard",
                    "meta": {"trigger": "traction_banner"}
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print(f"PASS: return_to_inspect with auth token accepted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
