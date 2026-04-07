"""
Test Growth Dashboard P0 Fix - Iteration 449
Tests the datetime/string type mismatch fix in MongoDB queries for pipeline_jobs.created_at

Key fixes tested:
1. Growth Dashboard shows non-zero 'Story Created' count (was 0, now should be 60)
2. Growth Dashboard 'Share Funnel Drop-off' table shows correct counts
3. Growth Dashboard 'Continuation Rate' is non-zero (around 20%)
4. Admin endpoint GET /api/admin/metrics/growth returns correct share_funnel.created > 0
5. Admin endpoint GET /api/admin/metrics/funnel-debug returns correct funnel_trace counts
6. Admin endpoint GET /api/admin/metrics/summary returns total_generations > 0
7. Admin endpoint GET /api/admin/metrics/story-performance returns deduplicated stories
8. Auth flows still work: login returns valid token
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Test user authentication failed - skipping user tests")


class TestAuthFlows:
    """Test authentication flows still work after the fix"""
    
    def test_admin_login_returns_valid_token(self):
        """Admin login should return valid token and correct credits"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "ADMIN"
        assert isinstance(data["user"]["credits"], int)
        assert len(data["token"]) > 0
    
    def test_test_user_login_returns_valid_token(self):
        """Test user login should return valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        assert data["user"]["email"] == TEST_USER_EMAIL


class TestGrowthMetricsEndpoint:
    """Test /api/admin/metrics/growth endpoint - the main fix"""
    
    def test_growth_endpoint_returns_200(self, admin_token):
        """Growth endpoint should return 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=720",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Growth endpoint failed: {response.text}"
    
    def test_growth_share_funnel_created_is_nonzero(self, admin_token):
        """share_funnel.created should be > 0 (was 0 before fix)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=720",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "share_funnel" in data, "Response should contain share_funnel"
        assert "created" in data["share_funnel"], "share_funnel should contain created"
        
        # THE KEY FIX: This was 0 before the datetime/string fix
        created_count = data["share_funnel"]["created"]
        assert created_count > 0, f"share_funnel.created should be > 0, got {created_count}"
        print(f"✓ share_funnel.created = {created_count} (was 0 before fix)")
    
    def test_growth_continuation_rate_is_nonzero(self, admin_token):
        """Continuation rate should be non-zero (around 20%)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=720",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "continuation_rate" in data, "Response should contain continuation_rate"
        
        cont_rate = data["continuation_rate"]
        assert "value" in cont_rate, "continuation_rate should have value"
        assert cont_rate["value"] > 0, f"Continuation rate should be > 0, got {cont_rate['value']}"
        print(f"✓ Continuation rate = {cont_rate['label']} ({cont_rate['interpretation']})")
    
    def test_growth_funnel_dropoff_has_all_stages(self, admin_token):
        """Funnel dropoff should have all 7 stages with correct counts"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=720",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "funnel_dropoff" in data, "Response should contain funnel_dropoff"
        
        funnel = data["funnel_dropoff"]
        expected_stages = [
            "Landing Visit", "CTA Click", "Story Created", 
            "Story Shared", "Share Opened", "Continued", "Re-shared"
        ]
        
        actual_stages = [step["stage"] for step in funnel]
        for stage in expected_stages:
            assert stage in actual_stages, f"Missing stage: {stage}"
        
        # Check Story Created count is non-zero
        story_created = next((s for s in funnel if s["stage"] == "Story Created"), None)
        assert story_created is not None, "Story Created stage not found"
        assert story_created["count"] > 0, f"Story Created count should be > 0, got {story_created['count']}"
        print(f"✓ Story Created count = {story_created['count']}")
    
    def test_growth_share_rate_is_nonzero(self, admin_token):
        """Share rate should be non-zero"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=720",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        share_rate = data.get("share_funnel", {}).get("rates", {}).get("share_rate", "0%")
        # Extract numeric value
        rate_value = float(share_rate.replace("%", ""))
        assert rate_value > 0, f"Share rate should be > 0, got {share_rate}"
        print(f"✓ Share rate = {share_rate}")


class TestFunnelDebugEndpoint:
    """Test /api/admin/metrics/funnel-debug endpoint"""
    
    def test_funnel_debug_returns_200(self, admin_token):
        """Funnel debug endpoint should return 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel-debug?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Funnel debug endpoint failed: {response.text}"
    
    def test_funnel_debug_stories_created_is_nonzero(self, admin_token):
        """funnel_trace.4_stories_created should be > 0"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel-debug?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "funnel_trace" in data, "Response should contain funnel_trace"
        
        stories_created = data["funnel_trace"].get("4_stories_created", {})
        assert "count" in stories_created, "4_stories_created should have count"
        assert stories_created["count"] > 0, f"Stories created should be > 0, got {stories_created['count']}"
        print(f"✓ funnel_trace.4_stories_created = {stories_created['count']}")
    
    def test_funnel_debug_has_data_quality_section(self, admin_token):
        """Funnel debug should have data_quality section with duplicates_found"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel-debug?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "data_quality" in data, "Response should contain data_quality"
        assert "duplicates_found" in data["data_quality"], "data_quality should have duplicates_found"
        print(f"✓ data_quality.duplicates_found = {data['data_quality']['duplicates_found']}")
    
    def test_funnel_debug_has_growth_events_cross_check(self, admin_token):
        """Funnel debug should have growth_events_cross_check section"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/funnel-debug?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "growth_events_cross_check" in data, "Response should contain growth_events_cross_check"
        
        ge = data["growth_events_cross_check"]
        assert "creation_completed" in ge, "Should have creation_completed"
        print(f"✓ growth_events.creation_completed = {ge['creation_completed']}")


class TestSummaryEndpoint:
    """Test /api/admin/metrics/summary endpoint"""
    
    def test_summary_returns_200(self, admin_token):
        """Summary endpoint should return 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Summary endpoint failed: {response.text}"
    
    def test_summary_total_generations_is_nonzero(self, admin_token):
        """total_generations should be > 0"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_generations" in data, "Response should contain total_generations"
        assert data["total_generations"] > 0, f"total_generations should be > 0, got {data['total_generations']}"
        print(f"✓ total_generations = {data['total_generations']}")
    
    def test_summary_completed_generations_is_nonzero(self, admin_token):
        """completed_generations should be > 0"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/summary?days=90",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "completed_generations" in data, "Response should contain completed_generations"
        assert data["completed_generations"] > 0, f"completed_generations should be > 0, got {data['completed_generations']}"
        print(f"✓ completed_generations = {data['completed_generations']}")


class TestStoryPerformanceEndpoint:
    """Test /api/admin/metrics/story-performance endpoint"""
    
    def test_story_performance_returns_200(self, admin_token):
        """Story performance endpoint should return 200 OK"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Story performance endpoint failed: {response.text}"
    
    def test_story_performance_has_deduplicated_stories(self, admin_token):
        """Stories should be deduplicated (no duplicate titles)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "stories" in data, "Response should contain stories"
        
        stories = data["stories"]
        titles = [s.get("title") for s in stories if s.get("title")]
        unique_titles = set(titles)
        
        # Check for duplicates
        assert len(titles) == len(unique_titles), f"Found duplicate titles: {[t for t in titles if titles.count(t) > 1]}"
        print(f"✓ {len(stories)} stories, all unique titles")
    
    def test_story_performance_has_summary(self, admin_token):
        """Story performance should have summary section"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data, "Response should contain summary"
        
        summary = data["summary"]
        assert "total_stories" in summary, "Summary should have total_stories"
        assert "total_views" in summary, "Summary should have total_views"
        assert "total_forks" in summary, "Summary should have total_forks"
        assert "avg_continuation_rate" in summary, "Summary should have avg_continuation_rate"
        print(f"✓ Summary: {summary['total_stories']} stories, {summary['total_views']} views, {summary['avg_continuation_rate']}% avg rate")


class TestHealthEndpoint:
    """Test basic health endpoint"""
    
    def test_health_returns_200(self):
        """Health endpoint should return 200 OK"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health endpoint failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Health status should be healthy, got {data.get('status')}"
        print(f"✓ Health status: {data.get('status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
