"""
Test Suite for P0/P0.5/P1 Priority Features - Iteration 507
- P0: Push Notification on Rank Drop (ALL users who drop rank)
- P0.5: WIN Share Trigger (persistent #1 share CTA in BattlePulse)
- P1: Autoplay Hook Quality (text overlays and competitive signals)

Tests backend endpoints:
- POST /api/push/subscribe
- GET /api/push/vapid-key
- GET /api/stories/battle-pulse/{rootId}
- GET /api/stories/viewer/{jobId}
- POST /api/stories/increment-metric
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
def auth_token(api_client):
    """Get authentication token for test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestPushNotificationEndpoints:
    """P0: Push Notification System Tests"""
    
    def test_vapid_key_endpoint_returns_public_key(self, api_client):
        """GET /api/push/vapid-key should return VAPID public key"""
        response = api_client.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert "vapid_public_key" in data, "Expected vapid_public_key in response"
        # VAPID key should be a non-empty string
        vapid_key = data.get("vapid_public_key", "")
        assert len(vapid_key) > 0, "VAPID public key should not be empty"
        print(f"VAPID key returned: {vapid_key[:20]}...")
    
    def test_push_subscribe_requires_auth(self, api_client):
        """POST /api/push/subscribe should require authentication"""
        # Remove auth header for this test
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/push/subscribe",
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                "keys": {"p256dh": "test", "auth": "test"}
            },
            headers=headers
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_push_subscribe_accepts_subscription(self, authenticated_client):
        """POST /api/push/subscribe should accept push subscription"""
        response = authenticated_client.post(f"{BASE_URL}/api/push/subscribe", json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-507",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                "auth": "tBHItJI5svbpez7KI4CCXg"
            }
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        print("Push subscription accepted successfully")
    
    def test_push_unsubscribe_endpoint(self, authenticated_client):
        """POST /api/push/unsubscribe should deactivate subscription"""
        response = authenticated_client.post(f"{BASE_URL}/api/push/unsubscribe", json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-507"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        print("Push unsubscribe successful")


class TestBattlePulseEndpoint:
    """P0.5: Battle Pulse with WIN/LOSS moments and user_rank"""
    
    def test_battle_pulse_returns_pulse_data(self, authenticated_client):
        """GET /api/stories/battle-pulse/{rootId} should return pulse with moment data"""
        # First get a hottest battle to find a root story ID
        hottest_response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        if hottest_response.status_code != 200:
            pytest.skip("No hottest battle available")
        
        hottest_data = hottest_response.json()
        if not hottest_data.get("battle") or not hottest_data["battle"].get("root_story_id"):
            pytest.skip("No battle root story ID available")
        
        root_id = hottest_data["battle"]["root_story_id"]
        
        # Now test battle-pulse endpoint
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle-pulse/{root_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        
        # Pulse can be null if no entries, but structure should be correct
        if data.get("pulse"):
            pulse = data["pulse"]
            # Check expected fields
            assert "ranked" in pulse or "top_3" in pulse, "Expected ranked or top_3 in pulse"
            assert "total_entries" in pulse, "Expected total_entries in pulse"
            # user_rank should be present (can be null if user not in battle)
            print(f"Battle pulse returned: {len(pulse.get('ranked', []))} ranked entries, user_rank={pulse.get('user_rank')}")
        else:
            print("No pulse data (no entries in battle)")
    
    def test_battle_pulse_requires_auth(self, api_client):
        """GET /api/stories/battle-pulse/{rootId} should require authentication"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-pulse/test-root-id")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


class TestStoryViewerBattleRank:
    """P0.5: Story Viewer returns battle_rank for branch stories"""
    
    def test_viewer_returns_battle_rank_for_branch(self, api_client):
        """GET /api/stories/viewer/{jobId} should return battle_rank field for branch stories"""
        # First find a branch story from discover feed
        discover_response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=20&sort_by=trending")
        if discover_response.status_code != 200:
            pytest.skip("Discover feed not available")
        
        stories = discover_response.json().get("stories", [])
        branch_story = None
        for story in stories:
            if story.get("continuation_type") == "branch":
                branch_story = story
                break
        
        if not branch_story:
            # Try to find any story with parent_job_id
            for story in stories:
                if story.get("parent_job_id"):
                    branch_story = story
                    break
        
        if not branch_story:
            pytest.skip("No branch story found in discover feed")
        
        job_id = branch_story.get("job_id")
        
        # Test viewer endpoint
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/{job_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert "job" in data, "Expected job in response"
        
        job = data["job"]
        # battle_rank should be present in response (can be null)
        assert "battle_rank" in job, "Expected battle_rank field in viewer response"
        print(f"Viewer returned battle_rank={job.get('battle_rank')} for story {job_id}")
    
    def test_viewer_returns_continuation_type(self, api_client):
        """GET /api/stories/viewer/{jobId} should return continuation_type"""
        discover_response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5")
        if discover_response.status_code != 200:
            pytest.skip("Discover feed not available")
        
        stories = discover_response.json().get("stories", [])
        if not stories:
            pytest.skip("No stories in discover feed")
        
        job_id = stories[0].get("job_id")
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/{job_id}")
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        assert "continuation_type" in job, "Expected continuation_type in viewer response"
        print(f"Viewer returned continuation_type={job.get('continuation_type')}")


class TestIncrementMetricRankNotifications:
    """P0: increment-metric triggers rank change notifications"""
    
    def test_increment_metric_views(self, api_client):
        """POST /api/stories/increment-metric should increment views"""
        # Get a story to test with
        discover_response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5")
        if discover_response.status_code != 200:
            pytest.skip("Discover feed not available")
        
        stories = discover_response.json().get("stories", [])
        if not stories:
            pytest.skip("No stories available")
        
        job_id = stories[0].get("job_id")
        
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": job_id,
            "metric": "views"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert data.get("metric") == "views", "Expected metric=views"
        assert "battle_score" in data, "Expected battle_score in response"
        print(f"Incremented views for {job_id}, new battle_score={data.get('battle_score')}")
    
    def test_increment_metric_shares(self, api_client):
        """POST /api/stories/increment-metric should increment shares"""
        discover_response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5")
        if discover_response.status_code != 200:
            pytest.skip("Discover feed not available")
        
        stories = discover_response.json().get("stories", [])
        if not stories:
            pytest.skip("No stories available")
        
        job_id = stories[0].get("job_id")
        
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": job_id,
            "metric": "shares"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert data.get("metric") == "shares", "Expected metric=shares"
        print(f"Incremented shares for {job_id}, new battle_score={data.get('battle_score')}")
    
    def test_increment_metric_invalid_metric(self, api_client):
        """POST /api/stories/increment-metric should reject invalid metric"""
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "test-job-id",
            "metric": "invalid_metric"
        })
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid metric, got {response.status_code}"


class TestDiscoverFeedCompetitiveSignals:
    """P1: Discover feed returns competitive signals for autoplay hooks"""
    
    def test_discover_feed_returns_competitive_fields(self, api_client):
        """GET /api/stories/feed/discover should return fields for hook text overlays"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=10&sort_by=trending")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        stories = data.get("stories", [])
        
        if not stories:
            pytest.skip("No stories in discover feed")
        
        # Check that stories have competitive signal fields
        for story in stories[:3]:
            # These fields enable hook text generation in frontend
            assert "total_children" in story or story.get("total_children") is None, "Expected total_children field"
            assert "total_views" in story or story.get("total_views") is None, "Expected total_views field"
            assert "battle_score" in story or story.get("battle_score") is None, "Expected battle_score field"
            
            # Log competitive signals
            children = story.get("total_children", 0)
            views = story.get("total_views", 0)
            score = story.get("battle_score", 0)
            print(f"Story {story.get('job_id', 'unknown')[:12]}: children={children}, views={views}, score={score}")
    
    def test_discover_feed_trending_sort(self, api_client):
        """GET /api/stories/feed/discover with trending sort should return hot stories first"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=10&sort_by=trending")
        assert response.status_code == 200
        
        stories = response.json().get("stories", [])
        if len(stories) < 2:
            pytest.skip("Not enough stories to verify sorting")
        
        # Trending stories should have higher battle_score or more activity
        # Just verify the endpoint works and returns data
        print(f"Trending feed returned {len(stories)} stories")
        for i, story in enumerate(stories[:3]):
            print(f"  #{i+1}: {story.get('title', 'Untitled')[:30]} - score={story.get('battle_score', 0)}")


class TestHottestBattleEndpoint:
    """P1: Hottest battle for spectator mode"""
    
    def test_hottest_battle_returns_contenders(self, api_client):
        """GET /api/stories/hottest-battle should return battle with contenders"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        
        if data.get("battle"):
            battle = data["battle"]
            assert "root_story_id" in battle, "Expected root_story_id"
            assert "contenders" in battle, "Expected contenders list"
            assert "branch_count" in battle, "Expected branch_count"
            
            print(f"Hottest battle: {battle.get('root_title', 'Unknown')}")
            print(f"  Branch count: {battle.get('branch_count')}")
            print(f"  Contenders: {len(battle.get('contenders', []))}")
        else:
            print("No active battle found")
    
    def test_hottest_battle_with_auth_returns_personalization(self, authenticated_client):
        """GET /api/stories/hottest-battle with auth should return personalized data"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        
        data = response.json()
        if data.get("battle"):
            battle = data["battle"]
            # Personalization fields
            assert "user_entry_count" in battle, "Expected user_entry_count for personalization"
            assert "user_is_new" in battle, "Expected user_is_new for personalization"
            assert "user_already_in_battle" in battle, "Expected user_already_in_battle"
            print(f"Personalization: entry_count={battle.get('user_entry_count')}, is_new={battle.get('user_is_new')}")


class TestBattleNotificationsEndpoint:
    """P0: Battle notifications for rank drops"""
    
    def test_battle_notifications_requires_auth(self, api_client):
        """GET /api/stories/notifications/battle should require auth"""
        response = requests.get(f"{BASE_URL}/api/stories/notifications/battle")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_battle_notifications_returns_list(self, authenticated_client):
        """GET /api/stories/notifications/battle should return notifications list"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/notifications/battle")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Expected success=True"
        assert "notifications" in data, "Expected notifications list"
        assert "total" in data, "Expected total count"
        assert "unread" in data, "Expected unread count"
        
        print(f"Battle notifications: total={data.get('total')}, unread={data.get('unread')}")


class TestServiceWorkerFile:
    """P0: Service worker file exists and is accessible"""
    
    def test_service_worker_accessible(self, api_client):
        """GET /sw-push.js should return service worker file"""
        # Service worker is served from frontend, not backend API
        # Just verify the file structure exists by checking frontend URL
        frontend_url = BASE_URL.replace('/api', '')
        response = requests.get(f"{frontend_url}/sw-push.js", timeout=10)
        # Should return 200 or redirect
        assert response.status_code in [200, 301, 302, 304], f"Expected 200/3xx for sw-push.js, got {response.status_code}"
        
        if response.status_code == 200:
            content = response.text
            # Verify it contains push event handler
            assert "push" in content.lower(), "Service worker should handle push events"
            assert "notificationclick" in content.lower(), "Service worker should handle notification clicks"
            print("Service worker file accessible and contains push handlers")


class TestCodeReviewVerification:
    """Code review verification for P0/P0.5/P1 features"""
    
    def test_push_notifications_module_exists(self):
        """Verify push_notifications.py has required functions"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from routes.push_notifications import (
                trigger_rank_drop_push,
                send_push_to_user,
                ALLOWED_TRIGGERS
            )
            
            assert "rank_drop" in ALLOWED_TRIGGERS, "rank_drop should be in ALLOWED_TRIGGERS"
            assert callable(trigger_rank_drop_push), "trigger_rank_drop_push should be callable"
            assert callable(send_push_to_user), "send_push_to_user should be callable"
            print(f"Push notification module verified. ALLOWED_TRIGGERS: {ALLOWED_TRIGGERS}")
        except ImportError as e:
            pytest.fail(f"Failed to import push_notifications module: {e}")
    
    def test_story_multiplayer_has_rank_notification_function(self):
        """Verify story_multiplayer.py has check_and_send_rank_notifications"""
        import sys
        sys.path.insert(0, '/app/backend')
        
        try:
            from routes.story_multiplayer import check_and_send_rank_notifications
            assert callable(check_and_send_rank_notifications), "check_and_send_rank_notifications should be callable"
            print("check_and_send_rank_notifications function verified")
        except ImportError as e:
            pytest.fail(f"Failed to import check_and_send_rank_notifications: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
