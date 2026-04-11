"""
Test Suite: Story Visibility Model + Cross-User Access + Attribution
Phase 1: Visibility (public/unlisted/private) + cross-user access + attribution
Phase 2A: Core action integrity (ContinuationModal preset buttons)

Endpoints tested:
- GET /api/stories/feed/discover — ALL public stories from ALL users, paginated, sortable
- GET /api/stories/feed/continue-watching — stories user has viewed (cross-user), ordered by last_viewed_at
- GET /api/stories/feed/trending — only public/legacy visibility stories
- POST /api/stories/set-visibility — owner can set public/unlisted/private; non-owner blocked
- POST /api/stories/backfill-visibility — admin-only, sets all completed stories to public
- GET /api/stories/viewer/{id} — blocks private stories for non-owners, allows public for all
- POST /api/stories/continue-episode — enforces visibility (private story cannot be continued by non-owner)
- POST /api/stories/continue-branch — enforces visibility (private story cannot be branched by non-owner)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture(scope="module")
def test_user_client(test_user_token):
    """Session with test user auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_user_token}"
    })
    return session


@pytest.fixture(scope="module")
def public_client():
    """Session without auth (public access)"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestDiscoverFeed:
    """GET /api/stories/feed/discover — ALL public stories from ALL users"""
    
    def test_discover_feed_returns_success(self, public_client):
        """Discover feed should return success with stories array"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data
        assert isinstance(data["stories"], list)
        print(f"PASS: Discover feed returns {len(data['stories'])} stories")
    
    def test_discover_feed_pagination(self, public_client):
        """Discover feed should support limit and offset pagination"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "has_more" in data
        assert data["limit"] == 5
        assert data["offset"] == 0
        print(f"PASS: Discover feed pagination works - total={data['total']}, has_more={data['has_more']}")
    
    def test_discover_feed_sort_by_latest(self, public_client):
        """Discover feed should sort by latest (created_at descending)"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?sort_by=latest&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        stories = data.get("stories", [])
        if len(stories) >= 2:
            # Verify descending order by created_at
            for i in range(len(stories) - 1):
                if stories[i].get("created_at") and stories[i+1].get("created_at"):
                    assert stories[i]["created_at"] >= stories[i+1]["created_at"], "Stories not sorted by latest"
        print(f"PASS: Discover feed sorted by latest")
    
    def test_discover_feed_sort_by_trending(self, public_client):
        """Discover feed should sort by trending (battle_score descending)"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?sort_by=trending&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        stories = data.get("stories", [])
        if len(stories) >= 2:
            # Verify descending order by battle_score
            for i in range(len(stories) - 1):
                score_i = stories[i].get("battle_score", 0) or 0
                score_j = stories[i+1].get("battle_score", 0) or 0
                assert score_i >= score_j, "Stories not sorted by trending"
        print(f"PASS: Discover feed sorted by trending")
    
    def test_discover_feed_sort_by_most_continued(self, public_client):
        """Discover feed should sort by most_continued (total_children descending)"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?sort_by=most_continued&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        stories = data.get("stories", [])
        if len(stories) >= 2:
            # Verify descending order by total_children
            for i in range(len(stories) - 1):
                children_i = stories[i].get("total_children", 0) or 0
                children_j = stories[i+1].get("total_children", 0) or 0
                assert children_i >= children_j, "Stories not sorted by most_continued"
        print(f"PASS: Discover feed sorted by most_continued")
    
    def test_discover_feed_excludes_seed_content(self, public_client):
        """Discover feed should exclude is_seed_content=true stories"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=50")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        for story in stories:
            # is_seed_content should not be True
            assert story.get("is_seed_content") is not True, f"Seed content found in discover feed: {story.get('job_id')}"
        print(f"PASS: Discover feed excludes seed content")
    
    def test_discover_feed_includes_creator_name(self, public_client):
        """Discover feed stories should include creator_name"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=10")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        if stories:
            # At least some stories should have creator_name
            has_creator = any(s.get("creator_name") for s in stories)
            assert has_creator, "No stories have creator_name"
        print(f"PASS: Discover feed includes creator_name")


class TestContinueWatchingFeed:
    """GET /api/stories/feed/continue-watching — stories user has viewed"""
    
    def test_continue_watching_requires_auth(self, public_client):
        """Continue watching feed should require authentication"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/continue-watching")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Continue watching requires auth")
    
    def test_continue_watching_returns_success(self, test_user_client):
        """Continue watching feed should return success for authenticated user"""
        response = test_user_client.get(f"{BASE_URL}/api/stories/feed/continue-watching")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data
        assert isinstance(data["stories"], list)
        print(f"PASS: Continue watching returns {len(data['stories'])} stories")
    
    def test_continue_watching_after_viewing_story(self, test_user_client):
        """After viewing a story via viewer endpoint, it should appear in continue-watching"""
        # First, get a public story from discover feed
        discover_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=1")
        if discover_res.status_code != 200 or not discover_res.json().get("stories"):
            pytest.skip("No stories available in discover feed")
        
        story_id = discover_res.json()["stories"][0]["job_id"]
        
        # View the story via viewer endpoint (this should track watch history)
        viewer_res = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        assert viewer_res.status_code == 200, f"Viewer failed: {viewer_res.text}"
        
        # Now check continue-watching feed
        cw_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/continue-watching")
        assert cw_res.status_code == 200
        data = cw_res.json()
        
        # The viewed story should be in the list
        story_ids = [s.get("job_id") for s in data.get("stories", [])]
        assert story_id in story_ids, f"Viewed story {story_id} not in continue-watching feed"
        print(f"PASS: Viewed story appears in continue-watching feed")


class TestTrendingFeed:
    """GET /api/stories/feed/trending — only public/legacy visibility stories"""
    
    def test_trending_feed_returns_success(self, public_client):
        """Trending feed should return success"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/trending")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data
        print(f"PASS: Trending feed returns {len(data['stories'])} stories")
    
    def test_trending_feed_sorted_by_battle_score(self, public_client):
        """Trending feed should be sorted by battle_score descending"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/trending?limit=20")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        if len(stories) >= 2:
            for i in range(len(stories) - 1):
                score_i = stories[i].get("battle_score", 0) or 0
                score_j = stories[i+1].get("battle_score", 0) or 0
                assert score_i >= score_j, "Trending not sorted by battle_score"
        print(f"PASS: Trending feed sorted by battle_score")
    
    def test_trending_feed_only_public_visibility(self, public_client):
        """Trending feed should only include public or legacy (null) visibility stories"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/trending?limit=50")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        for story in stories:
            vis = story.get("visibility")
            # Should be public, None, or not present (legacy)
            assert vis in [None, "public"], f"Non-public story in trending: {story.get('job_id')} has visibility={vis}"
        print(f"PASS: Trending feed only includes public/legacy stories")


class TestSetVisibility:
    """POST /api/stories/set-visibility — owner can set visibility"""
    
    def test_set_visibility_requires_auth(self, public_client):
        """Set visibility should require authentication"""
        response = public_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": "test-job-id",
            "visibility": "private"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"PASS: Set visibility requires auth")
    
    def test_set_visibility_owner_can_change(self, admin_client):
        """Owner should be able to change visibility of their story"""
        # Get an admin-owned story
        discover_res = admin_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=20")
        if discover_res.status_code != 200:
            pytest.skip("Cannot get discover feed")
        
        stories = discover_res.json().get("stories", [])
        # Find a story that might be owned by admin (we'll try battle-demo-root or similar)
        # For this test, we'll use a known story ID
        test_story_id = "battle-demo-ep2"  # Known admin story from context
        
        # Try to set visibility to private
        response = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if response.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        # Admin should be able to change (either as owner or admin role)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert data.get("visibility") == "private"
        print(f"PASS: Admin can set visibility to private")
        
        # Restore to public
        restore_res = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "public"
        })
        assert restore_res.status_code == 200
        print(f"PASS: Visibility restored to public")
    
    def test_set_visibility_non_owner_blocked(self, test_user_client, admin_client):
        """Non-owner should be blocked from changing visibility"""
        # Get an admin-owned story
        test_story_id = "battle-demo-root"  # Known admin story
        
        # Test user tries to change visibility
        response = test_user_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if response.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        # Should be forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"PASS: Non-owner blocked from changing visibility")
    
    def test_set_visibility_validates_values(self, admin_client):
        """Set visibility should validate visibility values"""
        response = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": "battle-demo-root",
            "visibility": "invalid_value"
        })
        # Should fail validation (422) or bad request (400)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"PASS: Invalid visibility value rejected")


class TestBackfillVisibility:
    """POST /api/stories/backfill-visibility — admin-only"""
    
    def test_backfill_visibility_requires_admin(self, test_user_client):
        """Backfill visibility should require admin role"""
        response = test_user_client.post(f"{BASE_URL}/api/stories/backfill-visibility")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"PASS: Backfill visibility requires admin")
    
    def test_backfill_visibility_admin_can_run(self, admin_client):
        """Admin should be able to run backfill visibility"""
        response = admin_client.post(f"{BASE_URL}/api/stories/backfill-visibility")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "updated" in data
        print(f"PASS: Admin ran backfill visibility, updated={data.get('updated')}")


class TestViewerVisibilityEnforcement:
    """GET /api/stories/viewer/{id} — visibility enforcement"""
    
    def test_viewer_allows_public_story_for_all(self, public_client, test_user_client):
        """Public stories should be viewable by anyone"""
        # Get a public story
        discover_res = public_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=1")
        if discover_res.status_code != 200 or not discover_res.json().get("stories"):
            pytest.skip("No public stories available")
        
        story_id = discover_res.json()["stories"][0]["job_id"]
        
        # Public client should be able to view
        response = public_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        # May require auth, but should not be 403 for visibility
        if response.status_code == 401:
            # Try with test user
            response = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: Public story viewable")
    
    def test_viewer_blocks_private_story_for_non_owner(self, admin_client, test_user_client):
        """Private stories should be blocked for non-owners"""
        test_story_id = "battle-demo-ep2"
        
        # Admin sets story to private
        set_res = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if set_res.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        if set_res.status_code != 200:
            pytest.skip(f"Could not set visibility: {set_res.text}")
        
        # Test user tries to view
        response = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{test_story_id}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"PASS: Private story blocked for non-owner")
        
        # Restore to public
        admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "public"
        })
    
    def test_viewer_allows_private_story_for_owner(self, admin_client):
        """Private stories should be viewable by owner"""
        test_story_id = "battle-demo-ep2"
        
        # Admin sets story to private
        set_res = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if set_res.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        if set_res.status_code != 200:
            pytest.skip(f"Could not set visibility: {set_res.text}")
        
        # Admin (owner) should still be able to view
        response = admin_client.get(f"{BASE_URL}/api/stories/viewer/{test_story_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: Private story viewable by owner")
        
        # Restore to public
        admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "public"
        })


class TestContinuationVisibilityEnforcement:
    """Continue-episode and continue-branch enforce visibility"""
    
    def test_continue_episode_blocks_private_story(self, admin_client, test_user_client):
        """Continue-episode should block private stories for non-owners"""
        test_story_id = "battle-demo-ep2"
        
        # Admin sets story to private
        set_res = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if set_res.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        if set_res.status_code != 200:
            pytest.skip(f"Could not set visibility: {set_res.text}")
        
        # Test user tries to continue episode
        response = test_user_client.post(f"{BASE_URL}/api/stories/continue-episode", json={
            "parent_job_id": test_story_id,
            "title": "Test Episode",
            "story_text": "This is a test story continuation that should be blocked because the parent is private. " * 3,
            "animation_style": "cartoon_2d",
            "age_group": "kids_5_8",
            "voice_preset": "narrator_warm"
        })
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"PASS: Continue-episode blocked for private story")
        
        # Restore to public
        admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "public"
        })
    
    def test_continue_branch_blocks_private_story(self, admin_client, test_user_client):
        """Continue-branch should block private stories for non-owners"""
        test_story_id = "battle-demo-ep2"
        
        # Admin sets story to private
        set_res = admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "private"
        })
        
        if set_res.status_code == 404:
            pytest.skip(f"Story {test_story_id} not found")
        
        if set_res.status_code != 200:
            pytest.skip(f"Could not set visibility: {set_res.text}")
        
        # Test user tries to branch
        response = test_user_client.post(f"{BASE_URL}/api/stories/continue-branch", json={
            "parent_job_id": test_story_id,
            "title": "Test Branch",
            "story_text": "This is a test story branch that should be blocked because the parent is private. " * 3,
            "animation_style": "cartoon_2d",
            "age_group": "kids_5_8",
            "voice_preset": "narrator_warm"
        })
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"PASS: Continue-branch blocked for private story")
        
        # Restore to public
        admin_client.post(f"{BASE_URL}/api/stories/set-visibility", json={
            "job_id": test_story_id,
            "visibility": "public"
        })


class TestViewerAttribution:
    """Viewer endpoint returns attribution fields"""
    
    def test_viewer_returns_attribution_fields(self, test_user_client):
        """Viewer should return derivative_label, source_story_title, source_creator_name"""
        # Get a story from discover feed
        discover_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=20")
        if discover_res.status_code != 200:
            pytest.skip("Cannot get discover feed")
        
        stories = discover_res.json().get("stories", [])
        if not stories:
            pytest.skip("No stories in discover feed")
        
        # View the first story
        story_id = stories[0]["job_id"]
        response = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        job = data.get("job", {})
        
        # Attribution fields should be present (may be null for original stories)
        assert "derivative_label" in job, "derivative_label field missing"
        assert "source_story_id" in job, "source_story_id field missing"
        assert "source_story_title" in job, "source_story_title field missing"
        assert "source_creator_name" in job, "source_creator_name field missing"
        print(f"PASS: Viewer returns attribution fields")
    
    def test_viewer_returns_creator_name(self, test_user_client):
        """Viewer should return creator_name in response"""
        discover_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=1")
        if discover_res.status_code != 200 or not discover_res.json().get("stories"):
            pytest.skip("No stories available")
        
        story_id = discover_res.json()["stories"][0]["job_id"]
        response = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        assert response.status_code == 200
        
        data = response.json()
        job = data.get("job", {})
        
        assert "creator_name" in job, "creator_name field missing"
        print(f"PASS: Viewer returns creator_name: {job.get('creator_name')}")


class TestNewStoriesDefaultVisibility:
    """New stories should be created with visibility=public by default"""
    
    def test_discover_feed_stories_have_visibility(self, public_client):
        """Stories in discover feed should have visibility field"""
        response = public_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        stories = data.get("stories", [])
        
        # Check that stories have visibility (public or null for legacy)
        for story in stories:
            vis = story.get("visibility")
            # Should be public, None, or not present (legacy)
            assert vis in [None, "public", "unlisted"], f"Unexpected visibility: {vis}"
        
        print(f"PASS: Stories have valid visibility values")


class TestWatchHistoryTracking:
    """Viewer endpoint tracks watch history in watch_history collection"""
    
    def test_viewer_tracks_watch_history(self, test_user_client):
        """Viewing a story should add it to watch_history"""
        # Get a story
        discover_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5")
        if discover_res.status_code != 200 or not discover_res.json().get("stories"):
            pytest.skip("No stories available")
        
        stories = discover_res.json()["stories"]
        # Pick a story that might not be in watch history yet
        story_id = stories[-1]["job_id"] if len(stories) > 1 else stories[0]["job_id"]
        
        # View the story
        viewer_res = test_user_client.get(f"{BASE_URL}/api/stories/viewer/{story_id}")
        assert viewer_res.status_code == 200
        
        # Check continue-watching feed
        cw_res = test_user_client.get(f"{BASE_URL}/api/stories/feed/continue-watching")
        assert cw_res.status_code == 200
        
        data = cw_res.json()
        story_ids = [s.get("job_id") for s in data.get("stories", [])]
        
        # The viewed story should be in the list
        assert story_id in story_ids, f"Viewed story {story_id} not tracked in watch history"
        print(f"PASS: Watch history tracking works")


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self, public_client):
        """API should be healthy"""
        response = public_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print(f"PASS: API is healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
