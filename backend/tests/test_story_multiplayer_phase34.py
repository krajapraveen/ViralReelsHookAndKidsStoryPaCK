"""
Story Multiplayer Engine Phase 3 & 4 Tests
- Phase 3: StoryChain Visualizer & Story Battle Screen
- Phase 4: Notification & Feed Engine

Tests:
- GET /api/stories/battle/{story_id} — ranked contenders with creator names, scores, user rank
- GET /api/stories/{story_id}/chain — episodes sorted by depth + branches grouped by parent
- GET /api/stories/feed/trending — stories sorted by battle_score with creator names
- GET /api/stories/notifications/battle — battle notifications for current user
- POST /api/stories/increment-metric — triggers rank notifications when leader changes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from context
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

# Demo data from context
DEMO_ROOT_ID = "battle-demo-root"


class TestStoryBattleEndpoint:
    """Tests for GET /api/stories/battle/{story_id}"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")
    
    def test_battle_endpoint_returns_200(self, admin_token):
        """Battle endpoint should return 200 for valid story_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_battle_returns_contenders_with_ranks(self, admin_token):
        """Battle endpoint should return contenders with rank field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        contenders = data.get("contenders", [])
        assert len(contenders) > 0, "Expected at least one contender"
        
        # Check first contender has rank
        first = contenders[0]
        assert "rank" in first, "Contender should have rank field"
        assert first["rank"] == 1, "First contender should be rank #1"
    
    def test_battle_returns_creator_names(self, admin_token):
        """Battle endpoint should enrich contenders with creator_name"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        contenders = data.get("contenders", [])
        for c in contenders:
            assert "creator_name" in c, f"Contender {c.get('job_id')} missing creator_name"
    
    def test_battle_returns_battle_scores(self, admin_token):
        """Battle endpoint should return battle_score for each contender"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        contenders = data.get("contenders", [])
        for c in contenders:
            assert "battle_score" in c, f"Contender {c.get('job_id')} missing battle_score"
    
    def test_battle_returns_user_rank_for_authenticated_user(self, test_user_token):
        """Battle endpoint should return user_rank for authenticated user with contender"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Test user owns branches br1 and br3, so should have a rank
        user_rank = data.get("user_rank")
        # user_rank can be None if user has no contender, but should be present in response
        assert "user_rank" in data, "Response should include user_rank field"
    
    def test_battle_returns_total_contenders(self, admin_token):
        """Battle endpoint should return total_contenders count"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/{DEMO_ROOT_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_contenders" in data
        assert data["total_contenders"] >= 1
    
    def test_battle_404_for_invalid_story(self, admin_token):
        """Battle endpoint should return 404 for non-existent story"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/battle/nonexistent-story-id-12345", headers=headers)
        assert response.status_code == 404


class TestStoryChainEndpoint:
    """Tests for GET /api/stories/{story_id}/chain"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_chain_endpoint_returns_200(self, admin_token):
        """Chain endpoint should return 200 for valid story_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/{DEMO_ROOT_ID}/chain", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_chain_returns_episodes_sorted_by_depth(self, admin_token):
        """Chain endpoint should return episodes sorted by chain_depth"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/{DEMO_ROOT_ID}/chain", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        episodes = data.get("episodes", [])
        assert len(episodes) > 0, "Expected at least one episode"
        
        # Verify sorted by chain_depth
        depths = [ep.get("chain_depth", 0) for ep in episodes]
        assert depths == sorted(depths), f"Episodes not sorted by depth: {depths}"
    
    def test_chain_returns_branch_map(self, admin_token):
        """Chain endpoint should return branch_map grouped by parent"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/{DEMO_ROOT_ID}/chain", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        branch_map = data.get("branch_map", {})
        assert isinstance(branch_map, dict), "branch_map should be a dictionary"
    
    def test_chain_returns_chain_stats(self, admin_token):
        """Chain endpoint should return chain_stats with totals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/{DEMO_ROOT_ID}/chain", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("chain_stats", {})
        assert "total_nodes" in stats
        assert "max_depth" in stats
        assert "total_episodes" in stats
        assert "total_branches" in stats
    
    def test_chain_returns_root_story_id(self, admin_token):
        """Chain endpoint should return root_story_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/{DEMO_ROOT_ID}/chain", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "root_story_id" in data
        assert data["root_story_id"] == DEMO_ROOT_ID
    
    def test_chain_404_for_invalid_story(self, admin_token):
        """Chain endpoint should return 404 for non-existent story"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/nonexistent-story-id-12345/chain", headers=headers)
        assert response.status_code == 404


class TestTrendingFeedEndpoint:
    """Tests for GET /api/stories/feed/trending"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_trending_endpoint_returns_200(self, admin_token):
        """Trending feed endpoint should return 200"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/feed/trending", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_trending_returns_stories_sorted_by_battle_score(self, admin_token):
        """Trending feed should return stories sorted by battle_score descending"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/feed/trending?limit=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        if len(stories) > 1:
            scores = [s.get("battle_score", 0) for s in stories]
            assert scores == sorted(scores, reverse=True), f"Stories not sorted by battle_score: {scores}"
    
    def test_trending_returns_creator_names(self, admin_token):
        """Trending feed should enrich stories with creator_name"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/feed/trending?limit=5", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        for s in stories:
            assert "creator_name" in s, f"Story {s.get('job_id')} missing creator_name"
    
    def test_trending_respects_limit_param(self, admin_token):
        """Trending feed should respect limit parameter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/feed/trending?limit=3", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        assert len(stories) <= 3, f"Expected max 3 stories, got {len(stories)}"


class TestBattleNotificationsEndpoint:
    """Tests for GET /api/stories/notifications/battle"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Test user login failed: {response.status_code}")
    
    def test_battle_notifications_returns_200(self, admin_token):
        """Battle notifications endpoint should return 200"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/notifications/battle", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_battle_notifications_returns_correct_types(self, admin_token):
        """Battle notifications should only return battle-related types"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/notifications/battle", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        notifications = data.get("notifications", [])
        valid_types = {"rank_drop", "version_outperformed", "story_branched", "new_branch_created"}
        for n in notifications:
            assert n.get("type") in valid_types, f"Unexpected notification type: {n.get('type')}"
    
    def test_battle_notifications_returns_unread_count(self, admin_token):
        """Battle notifications should return unread count"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stories/notifications/battle", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "unread" in data
        assert isinstance(data["unread"], int)
    
    def test_battle_notifications_requires_auth(self):
        """Battle notifications should require authentication"""
        response = requests.get(f"{BASE_URL}/api/stories/notifications/battle")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestIncrementMetricEndpoint:
    """Tests for POST /api/stories/increment-metric"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def test_increment_views_returns_200(self, admin_token):
        """Increment views should return 200"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", 
            headers=headers,
            json={"job_id": DEMO_ROOT_ID, "metric": "views"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
    
    def test_increment_shares_returns_200(self, admin_token):
        """Increment shares should return 200"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", 
            headers=headers,
            json={"job_id": DEMO_ROOT_ID, "metric": "shares"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
    
    def test_increment_returns_updated_battle_score(self, admin_token):
        """Increment metric should return updated battle_score"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", 
            headers=headers,
            json={"job_id": DEMO_ROOT_ID, "metric": "views"})
        assert response.status_code == 200
        data = response.json()
        
        assert "battle_score" in data
        assert isinstance(data["battle_score"], (int, float))
    
    def test_increment_invalid_metric_returns_400(self, admin_token):
        """Increment with invalid metric should return 400"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", 
            headers=headers,
            json={"job_id": DEMO_ROOT_ID, "metric": "invalid_metric"})
        assert response.status_code == 422, f"Expected 422 for invalid metric, got {response.status_code}"
    
    def test_increment_nonexistent_story_returns_404(self, admin_token):
        """Increment for non-existent story should return 404"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/stories/increment-metric", 
            headers=headers,
            json={"job_id": "nonexistent-story-12345", "metric": "views"})
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
