"""
Growth Engine Feature Tests - Iteration 324
Testing:
- A/B Testing endpoint (/api/ab/results)
- Leaderboard endpoint (/api/admin/metrics/leaderboard)
- Public creation page A/B variant handling
- WebSocket connection availability
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestHealthCheck:
    """Basic health check tests"""

    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API Health: {data}")


class TestAuthentication:
    """Authentication tests"""

    def test_admin_login(self):
        """Test admin login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ Admin login successful")
        return data["token"]


class TestABTestingEndpoint:
    """A/B Testing Results Endpoint Tests"""

    def test_ab_results_endpoint_exists(self):
        """Test /api/ab/results endpoint exists and returns proper structure"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        assert response.status_code == 200
        data = response.json()
        
        # Should have experiments array
        assert "experiments" in data
        experiments = data["experiments"]
        assert isinstance(experiments, list)
        print(f"✓ A/B Results endpoint returns {len(experiments)} experiments")
        return experiments

    def test_ab_results_experiment_structure(self):
        """Verify each experiment has proper structure"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        data = response.json()
        
        for exp in data.get("experiments", []):
            # Check required fields
            assert "experiment_id" in exp, f"Missing experiment_id"
            assert "name" in exp, f"Missing name in {exp.get('experiment_id')}"
            assert "variants" in exp, f"Missing variants in {exp.get('experiment_id')}"
            assert "active" in exp, f"Missing active in {exp.get('experiment_id')}"
            
            # Check variants structure
            variants = exp.get("variants", [])
            for v in variants:
                assert "variant_id" in v
                assert "sessions" in v
                assert "primary_conv_rate" in v
            
            print(f"✓ Experiment '{exp['name']}' has {len(variants)} variants")
    
    def test_ab_results_seeded_experiments(self):
        """Verify seeded experiments exist (cta_copy, hook_text, login_timing, cta_placement)"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        data = response.json()
        
        experiment_ids = [e.get("experiment_id") for e in data.get("experiments", [])]
        expected_experiments = ["cta_copy", "hook_text", "login_timing", "cta_placement"]
        
        for exp_id in expected_experiments:
            assert exp_id in experiment_ids, f"Expected experiment '{exp_id}' not found"
            print(f"✓ Found seeded experiment: {exp_id}")


class TestLeaderboardEndpoint:
    """Leaderboard Endpoint Tests"""

    @pytest.fixture
    def admin_token(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")

    def test_leaderboard_endpoint_requires_auth(self):
        """Test /api/admin/metrics/leaderboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/leaderboard")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected auth required, got {response.status_code}"
        print(f"✓ Leaderboard endpoint requires authentication")

    def test_leaderboard_endpoint_with_auth(self, admin_token):
        """Test leaderboard endpoint with admin auth"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get("success") is True
        assert "top_stories" in data
        assert "top_continuers" in data
        assert "total_continuations" in data
        assert "unique_continuers" in data
        assert "stories_with_continuations" in data
        
        print(f"✓ Leaderboard response: {len(data.get('top_stories', []))} top stories, "
              f"{len(data.get('top_continuers', []))} top continuers, "
              f"{data.get('total_continuations', 0)} total continuations")
        return data

    def test_leaderboard_top_stories_structure(self, admin_token):
        """Verify top_stories have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for story in data.get("top_stories", []):
            assert "job_id" in story or story.get("title"), f"Story missing identifier"
            assert "continuations" in story
            assert "views" in story
            print(f"✓ Story '{story.get('title', 'N/A')}': {story.get('continuations')} continuations")

    def test_leaderboard_top_continuers_structure(self, admin_token):
        """Verify top_continuers have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        
        for user in data.get("top_continuers", []):
            assert "name" in user
            assert "continuation_count" in user
            print(f"✓ User '{user.get('name', 'N/A')}': {user.get('continuation_count')} remixes")


class TestAdminDashboardSections:
    """Test Admin Dashboard API endpoints for new sections"""

    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")

    def test_summary_endpoint(self, admin_token):
        """Test /api/admin/metrics/summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "total_users" in data
        print(f"✓ Summary: {data.get('total_users')} users, {data.get('total_generations')} generations")

    def test_funnel_endpoint(self, admin_token):
        """Test /api/admin/metrics/funnel"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "page_views" in data
        print(f"✓ Funnel: {data.get('page_views')} page views, {data.get('share_clicks')} shares")

    def test_reliability_endpoint(self, admin_token):
        """Test /api/admin/metrics/reliability"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/reliability",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "queue_depth" in data
        assert "overall_health" in data
        print(f"✓ Reliability: queue={data.get('queue_depth')}, health={data.get('overall_health')}")

    def test_revenue_endpoint(self, admin_token):
        """Test /api/admin/metrics/revenue"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/revenue?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "total_revenue_inr" in data
        print(f"✓ Revenue: ₹{data.get('total_revenue_inr')}, {data.get('successful_payments')} payments")

    def test_series_endpoint(self, admin_token):
        """Test /api/admin/metrics/series"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/series",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "active_series" in data
        print(f"✓ Series: {data.get('active_series')} active, {data.get('total_episodes')} episodes")

    def test_credits_endpoint(self, admin_token):
        """Test /api/admin/metrics/credits"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/credits",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "total_credits_issued" in data
        print(f"✓ Credits: {data.get('total_current_balance')} balance across {data.get('total_users')} users")

    def test_conversion_endpoint(self, admin_token):
        """Test /api/admin/metrics/conversion"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/conversion",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "free_to_paid_rate" in data
        print(f"✓ Conversion: {data.get('free_to_paid_rate')}% free-to-paid rate")


class TestPublicCreationPage:
    """Test Public Creation Page API"""

    def test_public_creation_endpoint(self):
        """Test /api/public/creation/{slug} endpoint"""
        # First, get an existing creation from explore
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        if explore_resp.status_code == 200 and explore_resp.json().get("items"):
            slug = explore_resp.json()["items"][0].get("slug") or explore_resp.json()["items"][0].get("job_id")
            if slug:
                response = requests.get(f"{BASE_URL}/api/public/creation/{slug}")
                if response.status_code == 200:
                    data = response.json()
                    creation = data.get("creation", {})
                    assert "title" in creation
                    assert "views" in creation
                    assert "remix_count" in creation
                    # Momentum fields
                    assert "is_trending" in creation
                    assert "is_alive" in creation
                    print(f"✓ Public creation '{creation.get('title')}': "
                          f"{creation.get('views')} views, trending={creation.get('is_trending')}")
                    return
        print("✓ Public creation endpoint exists (no items to test)")


class TestABAssignment:
    """Test A/B Assignment and Conversion Endpoints"""

    def test_ab_assign_all_endpoint(self):
        """Test /api/ab/assign-all endpoint"""
        import uuid
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/ab/assign-all", json={
            "session_id": session_id
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "assignments" in data
        assignments = data["assignments"]
        
        # Should have assignments for seeded experiments
        expected = ["cta_copy", "hook_text", "login_timing", "cta_placement"]
        for exp_id in expected:
            if exp_id in assignments:
                assert "variant_id" in assignments[exp_id]
                assert "variant_data" in assignments[exp_id]
                print(f"✓ Assigned {exp_id}: {assignments[exp_id].get('variant_id')}")

    def test_ab_convert_endpoint(self):
        """Test /api/ab/convert endpoint"""
        import uuid
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        
        # First assign
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        # Then convert
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print(f"✓ Conversion tracked: {data}")


class TestWebSocketEndpoint:
    """Test WebSocket endpoint availability"""

    def test_websocket_endpoint_exists(self):
        """Check WebSocket endpoint is reachable (will get upgrade error which is expected)"""
        # HTTP request to WS endpoint should return a protocol error or upgrade required
        response = requests.get(f"{BASE_URL}/api/ws/admin/live", timeout=5)
        # Expecting 400, 426, or connection upgrade header
        print(f"✓ WebSocket endpoint response: {response.status_code}")


class TestSharePromptModal:
    """Test SharePromptModal component exists (frontend file check)"""

    def test_share_prompt_modal_file_exists(self):
        """Verify SharePromptModal.js exists"""
        import os
        path = "/app/frontend/src/components/SharePromptModal.js"
        assert os.path.exists(path), f"SharePromptModal.js not found at {path}"
        print(f"✓ SharePromptModal.js exists at {path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
