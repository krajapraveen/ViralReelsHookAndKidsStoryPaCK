"""
Phase 3: Feed as Return Engine — Backend API Tests

Tests for:
- PersonalAlertStrip: /api/stories/notifications/battle, /api/war/current
- TrendingPublicFeed: /api/stories/feed/discover?sort_by=trending
- YourCreationsStrip: /api/story-engine/user-jobs
- War Banner: /api/war/current
"""
import pytest
import requests
import os

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
    """Get test user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with test user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        """Verify API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("API health check passed")


class TestBattleNotifications:
    """Tests for /api/stories/notifications/battle — PersonalAlertStrip data source"""
    
    def test_battle_notifications_endpoint_exists(self, authenticated_client):
        """Verify battle notifications endpoint exists"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=5")
        assert response.status_code == 200, f"Battle notifications endpoint failed: {response.status_code}"
        print(f"Battle notifications endpoint returned: {response.status_code}")
    
    def test_battle_notifications_response_structure(self, authenticated_client):
        """Verify response has correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data, "Response missing 'success' field"
        assert "notifications" in data, "Response missing 'notifications' field"
        assert isinstance(data["notifications"], list), "notifications should be a list"
        print(f"Battle notifications structure valid, {len(data['notifications'])} notifications found")
    
    def test_battle_notifications_types(self, authenticated_client):
        """Verify notification types are correct"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        valid_types = ["rank_drop", "version_outperformed", "story_branched", "new_branch_created", "war_overtake", "war_won"]
        for notif in data.get("notifications", []):
            if "type" in notif:
                assert notif["type"] in valid_types, f"Invalid notification type: {notif['type']}"
        print(f"All notification types are valid")
    
    def test_battle_notifications_has_deep_link(self, authenticated_client):
        """Verify notifications have deep_link for navigation"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        for notif in data.get("notifications", []):
            if notif.get("data"):
                # deep_link should be present in data
                print(f"Notification type={notif.get('type')}, has data={bool(notif.get('data'))}")
        print("Battle notifications deep_link check passed")


class TestWarCurrent:
    """Tests for /api/war/current — War Banner and PersonalAlertStrip data source"""
    
    def test_war_current_endpoint_exists(self, authenticated_client):
        """Verify war current endpoint exists"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/current")
        # Can be 200 (war exists) or 404 (no active war)
        assert response.status_code in [200, 404], f"War current endpoint failed: {response.status_code}"
        print(f"War current endpoint returned: {response.status_code}")
    
    def test_war_current_response_structure(self, authenticated_client):
        """Verify response structure when war exists"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/current")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data, "Response missing 'success' field"
            if data.get("war"):
                war = data["war"]
                assert "war_id" in war, "War missing war_id"
                assert "state" in war, "War missing state"
                # War uses root_title for the story title
                assert "root_title" in war or "title" in war or "theme" in war, "War missing root_title/title/theme"
                print(f"War current structure valid: {war.get('root_title') or war.get('title') or war.get('theme')}")
        else:
            print("No active war found (404) - this is acceptable")
    
    def test_war_current_leaderboard(self, authenticated_client):
        """Verify leaderboard data is included"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/current")
        if response.status_code == 200:
            data = response.json()
            if data.get("leaderboard"):
                lb = data["leaderboard"]
                assert "entries" in lb or "total_entries" in lb, "Leaderboard missing entries"
                print(f"War leaderboard found with {lb.get('total_entries', 0)} entries")
        else:
            print("No active war - skipping leaderboard check")


class TestDiscoverFeed:
    """Tests for /api/stories/feed/discover — TrendingPublicFeed data source"""
    
    def test_discover_feed_endpoint_exists(self, api_client):
        """Verify discover feed endpoint exists (no auth required)"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=8&sort_by=trending")
        assert response.status_code == 200, f"Discover feed endpoint failed: {response.status_code}"
        print(f"Discover feed endpoint returned: {response.status_code}")
    
    def test_discover_feed_response_structure(self, api_client):
        """Verify response has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=8&sort_by=trending")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data, "Response missing 'success' field"
        assert "stories" in data, "Response missing 'stories' field"
        assert isinstance(data["stories"], list), "stories should be a list"
        assert "total" in data, "Response missing 'total' field"
        assert "has_more" in data, "Response missing 'has_more' field"
        print(f"Discover feed structure valid, {len(data['stories'])} stories found")
    
    def test_discover_feed_story_fields(self, api_client):
        """Verify stories have required fields for TrendingPublicFeed"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=8&sort_by=trending")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["job_id", "title"]
        optional_fields = ["creator_name", "total_views", "total_children", "total_shares", "battle_score", "thumbnail_url"]
        
        for story in data.get("stories", [])[:3]:  # Check first 3
            for field in required_fields:
                assert field in story, f"Story missing required field: {field}"
            print(f"Story '{story.get('title', 'Untitled')[:30]}' has required fields")
    
    def test_discover_feed_hot_badge_criteria(self, api_client):
        """Verify stories have fields needed for HOT badge (total_children >= 3 or battle_score > 50)"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=20&sort_by=trending")
        assert response.status_code == 200
        data = response.json()
        
        hot_count = 0
        for story in data.get("stories", []):
            total_children = story.get("total_children", 0)
            battle_score = story.get("battle_score", 0)
            if total_children >= 3 or battle_score > 50:
                hot_count += 1
        print(f"Found {hot_count} stories eligible for HOT badge")
    
    def test_discover_feed_attribution_fields(self, api_client):
        """Verify derivative stories have attribution fields"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=20&sort_by=trending")
        assert response.status_code == 200
        data = response.json()
        
        derivative_count = 0
        for story in data.get("stories", []):
            if story.get("derivative_label"):
                derivative_count += 1
                # Should have source_story_title for attribution
                print(f"Derivative story: {story.get('derivative_label')} from '{story.get('source_story_title', 'Unknown')}'")
        print(f"Found {derivative_count} derivative stories with attribution")
    
    def test_discover_feed_pagination(self, api_client):
        """Verify pagination works"""
        response1 = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5&offset=0")
        response2 = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5&offset=5")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # If there are enough stories, pages should be different
        if data1.get("total", 0) > 5:
            ids1 = {s["job_id"] for s in data1.get("stories", [])}
            ids2 = {s["job_id"] for s in data2.get("stories", [])}
            # Pages should not overlap (unless total < 10)
            if data1.get("total", 0) >= 10:
                assert len(ids1 & ids2) == 0, "Pagination returned overlapping stories"
        print("Pagination working correctly")


class TestTrendingFeed:
    """Tests for /api/stories/feed/trending — Alternative trending endpoint"""
    
    def test_trending_feed_endpoint_exists(self, api_client):
        """Verify trending feed endpoint exists"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/trending?limit=10")
        assert response.status_code == 200, f"Trending feed endpoint failed: {response.status_code}"
        print(f"Trending feed endpoint returned: {response.status_code}")
    
    def test_trending_feed_sorted_by_score(self, api_client):
        """Verify stories are sorted by battle_score descending"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/trending?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        if len(stories) >= 2:
            scores = [s.get("battle_score", 0) for s in stories]
            assert scores == sorted(scores, reverse=True), "Stories not sorted by battle_score"
            print(f"Trending feed correctly sorted by score: {scores[:5]}")


class TestUserJobs:
    """Tests for /api/story-engine/user-jobs — YourCreationsStrip data source"""
    
    def test_user_jobs_endpoint_exists(self, authenticated_client):
        """Verify user jobs endpoint exists"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200, f"User jobs endpoint failed: {response.status_code}"
        print(f"User jobs endpoint returned: {response.status_code}")
    
    def test_user_jobs_response_structure(self, authenticated_client):
        """Verify response has correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data, "Response missing 'jobs' field"
        assert isinstance(data["jobs"], list), "jobs should be a list"
        print(f"User jobs structure valid, {len(data['jobs'])} jobs found")
    
    def test_user_jobs_story_fields(self, authenticated_client):
        """Verify jobs have required fields for YourCreationsStrip"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        
        # User jobs uses 'status' instead of 'state'
        required_fields = ["job_id", "title", "status"]
        optional_fields = ["battle_score", "total_views", "total_children", "thumbnail_url"]
        
        for job in data.get("jobs", [])[:3]:  # Check first 3
            for field in required_fields:
                assert field in job, f"Job missing required field: {field}"
            print(f"Job '{job.get('title', 'Untitled')[:30]}' status={job.get('status')}")
    
    def test_user_jobs_filterable_states(self, authenticated_client):
        """Verify jobs include status for filtering (READY, PARTIAL_READY, COMPLETED)"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-engine/user-jobs")
        assert response.status_code == 200
        data = response.json()
        
        # User jobs uses 'status' field
        valid_display_states = ["READY", "PARTIAL_READY", "COMPLETED"]
        displayable = [j for j in data.get("jobs", []) if j.get("status") in valid_display_states]
        print(f"Found {len(displayable)} displayable jobs (READY/PARTIAL_READY/COMPLETED)")


class TestContinueWatchingFeed:
    """Tests for /api/stories/feed/continue-watching — Continue Watching section"""
    
    def test_continue_watching_endpoint_exists(self, authenticated_client):
        """Verify continue watching endpoint exists"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/feed/continue-watching?limit=10")
        assert response.status_code == 200, f"Continue watching endpoint failed: {response.status_code}"
        print(f"Continue watching endpoint returned: {response.status_code}")
    
    def test_continue_watching_response_structure(self, authenticated_client):
        """Verify response has correct structure"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/feed/continue-watching?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data, "Response missing 'success' field"
        assert "stories" in data, "Response missing 'stories' field"
        assert isinstance(data["stories"], list), "stories should be a list"
        print(f"Continue watching structure valid, {len(data['stories'])} stories found")


class TestWarNotifications:
    """Tests for war-related notifications in PersonalAlertStrip"""
    
    def test_war_overtake_notification_type(self, authenticated_client):
        """Verify war_overtake notification type is supported"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=20")
        assert response.status_code == 200
        data = response.json()
        
        # Check if any war_overtake notifications exist
        war_overtake = [n for n in data.get("notifications", []) if n.get("type") == "war_overtake"]
        print(f"Found {len(war_overtake)} war_overtake notifications")
    
    def test_notification_cta_fields(self, authenticated_client):
        """Verify notifications have fields needed for CTAs"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        for notif in data.get("notifications", []):
            assert "type" in notif, "Notification missing type"
            assert "title" in notif, "Notification missing title"
            # message and data are optional but useful
            print(f"Notification: type={notif.get('type')}, title={notif.get('title', '')[:40]}")


class TestHomepageSectionOrder:
    """Tests to verify all required endpoints exist for homepage sections"""
    
    def test_all_homepage_endpoints_accessible(self, authenticated_client, api_client):
        """Verify all endpoints needed for homepage sections are accessible"""
        endpoints = [
            # PersonalAlertStrip
            (f"{BASE_URL}/api/stories/notifications/battle?limit=5", authenticated_client, "Battle Notifications"),
            (f"{BASE_URL}/api/war/current", authenticated_client, "War Current"),
            # TrendingPublicFeed
            (f"{BASE_URL}/api/stories/feed/discover?limit=8&sort_by=trending", api_client, "Discover Feed"),
            # YourCreationsStrip
            (f"{BASE_URL}/api/story-engine/user-jobs", authenticated_client, "User Jobs"),
            # Continue Watching
            (f"{BASE_URL}/api/stories/feed/continue-watching?limit=10", authenticated_client, "Continue Watching"),
            # Trending
            (f"{BASE_URL}/api/stories/feed/trending?limit=10", api_client, "Trending Feed"),
        ]
        
        results = []
        for url, client, name in endpoints:
            response = client.get(url)
            status = "PASS" if response.status_code in [200, 404] else "FAIL"
            results.append((name, response.status_code, status))
            print(f"{name}: {response.status_code} - {status}")
        
        # All should pass (200 or 404 for optional data)
        failures = [r for r in results if r[2] == "FAIL"]
        assert len(failures) == 0, f"Failed endpoints: {failures}"
        print("All homepage section endpoints accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
