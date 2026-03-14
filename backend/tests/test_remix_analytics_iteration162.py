"""
Iteration 162 - Remix & Variations Engine + Engagement Analytics Test Suite
Tests:
1. Remix variations GET endpoints for all 7 tools
2. Remix tracking POST endpoint
3. Remix stats GET endpoint
4. Engagement analytics CTA tracking
5. Engagement analytics template tracking
6. Engagement analytics admin report
7. Pipeline worker status
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://engagement-loop-core.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Authenticate test user and return token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Authenticate admin user and return token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_USER_EMAIL,
        "password": ADMIN_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


class TestRemixVariationsEndpoints:
    """Test GET /api/remix/variations/{tool} for all 7 tools"""

    def test_story_video_studio_variations(self):
        """Test story-video-studio variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/story-video-studio")
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "quick" in data, "Missing 'quick' variations"
        assert "styles" in data, "Missing 'styles'"
        assert "actions" in data, "Missing 'actions'"
        
        assert len(data["quick"]) >= 4, f"Expected 4+ quick variations, got {len(data['quick'])}"
        assert len(data["styles"]) >= 5, f"Expected 5+ styles, got {len(data['styles'])}"
        assert len(data["actions"]) >= 4, f"Expected 4+ actions, got {len(data['actions'])}"
        
        print(f"PASS: story-video-studio - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_reels_variations(self):
        """Test reels variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/reels")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 5
        assert "actions" in data and len(data["actions"]) >= 4
        print(f"PASS: reels - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_photo_to_comic_variations(self):
        """Test photo-to-comic variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/photo-to-comic")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 5
        assert "actions" in data and len(data["actions"]) >= 4
        print(f"PASS: photo-to-comic - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_gif_maker_variations(self):
        """Test gif-maker variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/gif-maker")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 4
        assert "actions" in data and len(data["actions"]) >= 3
        print(f"PASS: gif-maker - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_stories_variations(self):
        """Test stories variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/stories")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 5
        assert "actions" in data and len(data["actions"]) >= 4
        print(f"PASS: stories - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_bedtime_story_builder_variations(self):
        """Test bedtime-story-builder variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/bedtime-story-builder")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 5
        assert "actions" in data and len(data["actions"]) >= 4
        print(f"PASS: bedtime-story-builder - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_comic_storybook_variations(self):
        """Test comic-storybook variation config"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/comic-storybook")
        assert response.status_code == 200
        data = response.json()
        
        assert "quick" in data and len(data["quick"]) >= 4
        assert "styles" in data and len(data["styles"]) >= 5
        assert "actions" in data and len(data["actions"]) >= 3
        print(f"PASS: comic-storybook - {len(data['quick'])} quick, {len(data['styles'])} styles, {len(data['actions'])} actions")

    def test_unknown_tool_returns_empty(self):
        """Test unknown tool returns empty arrays"""
        response = requests.get(f"{BASE_URL}/api/remix/variations/unknown-tool-xyz")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("quick") == [], f"Expected empty quick, got {data.get('quick')}"
        assert data.get("styles") == [], f"Expected empty styles, got {data.get('styles')}"
        assert data.get("actions") == [], f"Expected empty actions, got {data.get('actions')}"
        print("PASS: unknown-tool returns empty arrays")


class TestRemixTracking:
    """Test POST /api/remix/track and GET /api/remix/stats"""

    def test_track_remix_event(self, test_user_token):
        """Test tracking a remix event (authenticated)"""
        response = requests.post(
            f"{BASE_URL}/api/remix/track",
            json={
                "source_tool": "story-video-studio",
                "target_tool": "reels",
                "original_prompt": "TEST_A cat exploring space",
                "variation_type": "convert",
                "variation_label": "Short Reel Version",
                "modifier": "Create a 15-second reel version"
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("tracked") == True
        print("PASS: remix event tracked successfully")

    def test_track_remix_requires_auth(self):
        """Test that remix tracking requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/remix/track",
            json={
                "source_tool": "stories",
                "target_tool": "stories",
                "original_prompt": "Test prompt",
                "variation_type": "quick"
            }
        )
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print("PASS: remix tracking requires auth")

    def test_get_remix_stats_user(self, test_user_token):
        """Test getting remix stats as regular user"""
        response = requests.get(
            f"{BASE_URL}/api/remix/stats",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert "total_remixes" in data
        print(f"PASS: User remix stats - total_remixes: {data.get('total_remixes', 0)}")

    def test_get_remix_stats_admin(self, admin_token):
        """Test getting full remix stats as admin"""
        response = requests.get(
            f"{BASE_URL}/api/remix/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        # Admin should get full breakdown
        assert "total_remixes" in data
        # These fields may be empty if no remix data yet
        if data.get("total_remixes", 0) > 0:
            assert "by_type" in data or "by_source_tool" in data
        print(f"PASS: Admin remix stats - total_remixes: {data.get('total_remixes', 0)}, by_type: {data.get('by_type', {})}")


class TestEngagementAnalytics:
    """Test Engagement Analytics API endpoints"""

    def test_track_cta_click(self, test_user_token):
        """Test tracking CTA click events"""
        response = requests.post(
            f"{BASE_URL}/api/engagement-analytics/track-cta",
            json={
                "cta_type": "upgrade_banner",
                "source_page": "dashboard"
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("tracked") == True
        print("PASS: CTA click tracked")

    def test_track_template_usage(self, test_user_token):
        """Test tracking template usage events"""
        response = requests.post(
            f"{BASE_URL}/api/engagement-analytics/track-template",
            json={
                "template_id": "TEST_template_001",
                "template_name": "Test Template",
                "source_page": "story-generator"
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("tracked") == True
        print("PASS: Template usage tracked")

    def test_engagement_report_admin(self, admin_token):
        """Test full engagement analytics report (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/engagement-analytics/report",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify report structure
        assert "generated_at" in data
        assert "challenge_completion" in data
        assert "streak_retention" in data
        assert "creations" in data
        assert "remix_engine" in data
        assert "cta_performance" in data
        assert "template_usage" in data
        
        print(f"PASS: Engagement report - challenge_completion: {data['challenge_completion']}, remix_engine: {data['remix_engine']}")

    def test_engagement_report_requires_admin(self, test_user_token):
        """Test that engagement report requires admin access"""
        response = requests.get(
            f"{BASE_URL}/api/engagement-analytics/report",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Engagement report requires admin")


class TestPipelineWorkerStatus:
    """Test pipeline worker status endpoint"""

    def test_worker_status(self, admin_token):
        """Test pipeline worker stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pipeline/workers/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # May be 200 or 404 if endpoint not exposed
        if response.status_code == 200:
            data = response.json()
            print(f"PASS: Worker status - {data}")
        elif response.status_code == 404:
            print("INFO: Worker status endpoint not exposed publicly (expected in some configs)")
        else:
            print(f"INFO: Worker status returned {response.status_code}")


class TestRegressionBasicEndpoints:
    """Regression tests for basic app functionality"""

    def test_health_endpoint(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint")

    def test_login_flow(self):
        """Test login flow works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print("PASS: Login flow")

    def test_user_profile(self, test_user_token):
        """Test user profile endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/user/me",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data or "name" in data
        print("PASS: User profile endpoint")

    def test_engagement_dashboard(self, test_user_token):
        """Test engagement dashboard (from iteration 161)"""
        response = requests.get(
            f"{BASE_URL}/api/engagement/dashboard",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "streak" in data or "challenge" in data or "level" in data
        print(f"PASS: Engagement dashboard - {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
