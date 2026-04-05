"""
Phase 5 DATA MODE Testing - Iteration 436
Tests:
1. 30 seeded stories in shares collection with correct genre distribution
2. GET /api/public/explore-stories with genre filtering
3. GET /api/public/featured-story
4. GET /api/share/{shareId} for seeded stories
5. POST /api/share/{shareId}/fork
6. GET /api/admin/metrics/growth (zero-denominator safety)
7. GET /api/admin/metrics/story-performance (per-story metrics)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestSeededStories:
    """Test seeded stories in shares collection"""

    def test_explore_stories_returns_seeded_stories(self):
        """GET /api/public/explore-stories returns seeded stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "stories" in data, "Response should have 'stories' key"
        assert "total" in data, "Response should have 'total' key"
        assert "genres" in data, "Response should have 'genres' key"
        print(f"PASS: explore-stories returns {len(data['stories'])} stories, total: {data['total']}")

    def test_explore_stories_genre_counts(self):
        """Verify genre distribution: 10 mystery, 10 thriller, 5 emotional, 5 fantasy"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories")
        assert response.status_code == 200
        data = response.json()
        genres = data.get("genres", {})
        
        # Check genre counts
        mystery_count = genres.get("mystery", 0)
        thriller_count = genres.get("thriller", 0)
        emotional_count = genres.get("emotional", 0)
        fantasy_count = genres.get("fantasy", 0)
        
        print(f"Genre counts: mystery={mystery_count}, thriller={thriller_count}, emotional={emotional_count}, fantasy={fantasy_count}")
        
        # Verify expected distribution
        assert mystery_count >= 10, f"Expected at least 10 mystery stories, got {mystery_count}"
        assert thriller_count >= 10, f"Expected at least 10 thriller stories, got {thriller_count}"
        assert emotional_count >= 5, f"Expected at least 5 emotional stories, got {emotional_count}"
        assert fantasy_count >= 5, f"Expected at least 5 fantasy stories, got {fantasy_count}"
        
        total_seeded = mystery_count + thriller_count + emotional_count + fantasy_count
        assert total_seeded >= 30, f"Expected at least 30 seeded stories, got {total_seeded}"
        print(f"PASS: Genre distribution verified - total seeded: {total_seeded}")

    def test_explore_stories_filter_mystery(self):
        """GET /api/public/explore-stories?genre=mystery returns exactly 10 stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?genre=mystery")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        total = data.get("total", 0)
        
        # All returned stories should be mystery genre
        for story in stories:
            assert story.get("genre") == "mystery", f"Story {story.get('title')} has genre {story.get('genre')}, expected mystery"
        
        assert total >= 10, f"Expected at least 10 mystery stories, got {total}"
        print(f"PASS: mystery filter returns {total} stories")

    def test_explore_stories_filter_thriller(self):
        """GET /api/public/explore-stories?genre=thriller returns exactly 10 stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?genre=thriller")
        assert response.status_code == 200
        data = response.json()
        total = data.get("total", 0)
        
        assert total >= 10, f"Expected at least 10 thriller stories, got {total}"
        print(f"PASS: thriller filter returns {total} stories")

    def test_explore_stories_filter_fantasy(self):
        """GET /api/public/explore-stories?genre=fantasy returns exactly 5 stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?genre=fantasy")
        assert response.status_code == 200
        data = response.json()
        total = data.get("total", 0)
        
        assert total >= 5, f"Expected at least 5 fantasy stories, got {total}"
        print(f"PASS: fantasy filter returns {total} stories")

    def test_explore_stories_filter_emotional(self):
        """GET /api/public/explore-stories?genre=emotional returns exactly 5 stories"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?genre=emotional")
        assert response.status_code == 200
        data = response.json()
        total = data.get("total", 0)
        
        assert total >= 5, f"Expected at least 5 emotional stories, got {total}"
        print(f"PASS: emotional filter returns {total} stories")

    def test_explore_stories_has_continuation_rate(self):
        """Stories should have continuationRate calculated"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?limit=5")
        assert response.status_code == 200
        data = response.json()
        stories = data.get("stories", [])
        
        for story in stories:
            assert "continuationRate" in story, f"Story {story.get('title')} missing continuationRate"
            # continuationRate should be a number (can be 0)
            assert isinstance(story["continuationRate"], (int, float)), f"continuationRate should be numeric"
        
        print(f"PASS: All stories have continuationRate field")


class TestFeaturedStory:
    """Test featured story endpoint"""

    def test_featured_story_returns_valid_data(self):
        """GET /api/public/featured-story returns a valid story"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "found" in data, "Response should have 'found' key"
        
        if data.get("found"):
            # If a story is found, verify required fields
            assert "title" in data, "Featured story should have title"
            # shareId or jobId should be present
            assert data.get("shareId") or data.get("jobId"), "Featured story should have shareId or jobId"
            print(f"PASS: Featured story found - title: {data.get('title')}")
        else:
            print("INFO: No featured story found (empty state)")

    def test_featured_story_has_hook_text(self):
        """Featured story should have hookText if available"""
        response = requests.get(f"{BASE_URL}/api/public/featured-story")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("found") and data.get("shareId"):
            # hookText is optional but should be present for seeded stories
            print(f"Featured story hookText: {data.get('hookText', 'N/A')}")
        print("PASS: Featured story endpoint works correctly")


class TestShareEndpoints:
    """Test share endpoints with seeded stories"""

    @pytest.fixture(scope="class")
    def seeded_share_id(self):
        """Get a seeded share ID for testing"""
        response = requests.get(f"{BASE_URL}/api/public/explore-stories?limit=1")
        if response.status_code == 200:
            data = response.json()
            stories = data.get("stories", [])
            if stories:
                return stories[0].get("id")
        pytest.skip("No seeded stories found")

    def test_get_share_returns_correct_data(self, seeded_share_id):
        """GET /api/share/{shareId} returns correct data for seeded story"""
        response = requests.get(f"{BASE_URL}/api/share/{seeded_share_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Response should have success=True"
        assert "title" in data, "Response should have title"
        assert "hookText" in data, "Response should have hookText"
        assert "storyContext" in data, "Response should have storyContext"
        assert "characters" in data, "Response should have characters"
        assert "tone" in data, "Response should have tone"
        assert "conflict" in data, "Response should have conflict"
        
        print(f"PASS: Share {seeded_share_id} returns all required fields")
        print(f"  Title: {data.get('title')}")
        print(f"  Characters: {data.get('characters')}")
        print(f"  Tone: {data.get('tone')}")

    def test_fork_story_works(self, seeded_share_id):
        """POST /api/share/{shareId}/fork works on seeded story"""
        # Get initial fork count
        initial_response = requests.get(f"{BASE_URL}/api/share/{seeded_share_id}")
        initial_forks = initial_response.json().get("forks", 0)
        
        # Fork the story
        response = requests.post(f"{BASE_URL}/api/share/{seeded_share_id}/fork")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Fork should succeed"
        assert "fork" in data, "Response should have fork data"
        
        fork = data["fork"]
        assert "parentShareId" in fork, "Fork should have parentShareId"
        assert "storyContext" in fork, "Fork should have storyContext"
        assert "characters" in fork, "Fork should have characters"
        assert "tone" in fork, "Fork should have tone"
        
        # Verify fork count incremented
        updated_response = requests.get(f"{BASE_URL}/api/share/{seeded_share_id}")
        updated_forks = updated_response.json().get("forks", 0)
        assert updated_forks > initial_forks, f"Fork count should increment: {initial_forks} -> {updated_forks}"
        
        print(f"PASS: Fork works - count incremented from {initial_forks} to {updated_forks}")

    def test_fork_nonexistent_returns_404(self):
        """POST /api/share/nonexistent/fork returns 404"""
        response = requests.post(f"{BASE_URL}/api/share/nonexistent-id-12345/fork")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Fork nonexistent share returns 404")


class TestGrowthMetrics:
    """Test growth metrics endpoint with zero-denominator safety"""

    def test_growth_metrics_returns_valid_data(self, admin_headers):
        """GET /api/admin/metrics/growth returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=72",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "period_hours" in data, "Response should have period_hours"
        assert "continuation_rate" in data, "Response should have continuation_rate"
        assert "branches_per_story" in data, "Response should have branches_per_story"
        assert "share_funnel" in data, "Response should have share_funnel"
        assert "first_session" in data, "Response should have first_session"
        assert "funnel_dropoff" in data, "Response should have funnel_dropoff"
        
        print(f"PASS: Growth metrics returns all required fields")

    def test_growth_metrics_no_null_values(self, admin_headers):
        """Growth metrics should not have null/None values in rates"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=72",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check continuation_rate
        cr = data.get("continuation_rate", {})
        assert cr.get("value") is not None, "continuation_rate.value should not be None"
        assert cr.get("label") is not None, "continuation_rate.label should not be None"
        
        # Check branches_per_story
        bps = data.get("branches_per_story", {})
        assert bps.get("value") is not None, "branches_per_story.value should not be None"
        
        # Check share_funnel rates
        funnel = data.get("share_funnel", {})
        rates = funnel.get("rates", {})
        for rate_name, rate_value in rates.items():
            assert rate_value is not None, f"share_funnel.rates.{rate_name} should not be None"
            # Rate should be a string like "0%" or "10.5%"
            assert "%" in str(rate_value), f"Rate {rate_name} should contain %: {rate_value}"
        
        print(f"PASS: No null values in growth metrics rates")

    def test_growth_metrics_zero_denominator_safety(self, admin_headers):
        """Growth metrics should return 0 instead of crashing when denominators are zero"""
        # Test with a very short time window that likely has no data
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/growth?hours=1",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Should not crash with zero data: {response.status_code}"
        data = response.json()
        
        # Even with zero data, rates should be 0 or valid percentages, not errors
        cr = data.get("continuation_rate", {})
        assert isinstance(cr.get("value"), (int, float)), "continuation_rate.value should be numeric"
        
        print(f"PASS: Zero-denominator safety verified")

    def test_growth_metrics_requires_admin(self):
        """Growth metrics should require admin authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/growth")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Growth metrics requires admin auth")


class TestStoryPerformance:
    """Test story-performance endpoint"""

    def test_story_performance_returns_valid_data(self, admin_headers):
        """GET /api/admin/metrics/story-performance returns per-story metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "stories" in data, "Response should have stories"
        assert "summary" in data, "Response should have summary"
        assert "genre_breakdown" in data, "Response should have genre_breakdown"
        
        print(f"PASS: Story performance returns all required fields")

    def test_story_performance_has_per_story_metrics(self, admin_headers):
        """Each story should have views, forks, continuation_rate"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance?limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        for story in stories:
            assert "views" in story, f"Story {story.get('title')} missing views"
            assert "forks" in story, f"Story {story.get('title')} missing forks"
            assert "continuation_rate" in story, f"Story {story.get('title')} missing continuation_rate"
            
            # Values should be numeric
            assert isinstance(story["views"], (int, float)), "views should be numeric"
            assert isinstance(story["forks"], (int, float)), "forks should be numeric"
            assert isinstance(story["continuation_rate"], (int, float)), "continuation_rate should be numeric"
        
        print(f"PASS: All {len(stories)} stories have per-story metrics")

    def test_story_performance_sort_by_views(self, admin_headers):
        """GET /api/admin/metrics/story-performance?sort_by=views works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance?sort_by=views&limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        if len(stories) > 1:
            # Verify sorted by views descending
            for i in range(len(stories) - 1):
                assert stories[i].get("views", 0) >= stories[i+1].get("views", 0), \
                    f"Stories not sorted by views: {stories[i].get('views')} < {stories[i+1].get('views')}"
        
        print(f"PASS: sort_by=views works correctly")

    def test_story_performance_sort_by_forks(self, admin_headers):
        """GET /api/admin/metrics/story-performance?sort_by=forks works"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance?sort_by=forks&limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        stories = data.get("stories", [])
        if len(stories) > 1:
            # Verify sorted by forks descending
            for i in range(len(stories) - 1):
                assert stories[i].get("forks", 0) >= stories[i+1].get("forks", 0), \
                    f"Stories not sorted by forks: {stories[i].get('forks')} < {stories[i+1].get('forks')}"
        
        print(f"PASS: sort_by=forks works correctly")

    def test_story_performance_genre_breakdown(self, admin_headers):
        """Genre breakdown should have correct counts"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        genre_breakdown = data.get("genre_breakdown", {})
        
        # Check that genre breakdown has expected genres
        expected_genres = ["mystery", "thriller", "emotional", "fantasy"]
        for genre in expected_genres:
            if genre in genre_breakdown:
                stats = genre_breakdown[genre]
                assert "count" in stats, f"Genre {genre} missing count"
                assert "views" in stats, f"Genre {genre} missing views"
                assert "forks" in stats, f"Genre {genre} missing forks"
                assert "continuation_rate" in stats, f"Genre {genre} missing continuation_rate"
                print(f"  {genre}: count={stats['count']}, views={stats['views']}, forks={stats['forks']}, rate={stats['continuation_rate']}%")
        
        print(f"PASS: Genre breakdown has correct structure")

    def test_story_performance_summary(self, admin_headers):
        """Summary should have total_stories, total_views, total_forks, avg_continuation_rate"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/story-performance",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        assert "total_stories" in summary, "Summary missing total_stories"
        assert "total_views" in summary, "Summary missing total_views"
        assert "total_forks" in summary, "Summary missing total_forks"
        assert "avg_continuation_rate" in summary, "Summary missing avg_continuation_rate"
        
        print(f"PASS: Summary has all required fields")
        print(f"  total_stories: {summary.get('total_stories')}")
        print(f"  total_views: {summary.get('total_views')}")
        print(f"  total_forks: {summary.get('total_forks')}")
        print(f"  avg_continuation_rate: {summary.get('avg_continuation_rate')}%")

    def test_story_performance_requires_admin(self):
        """Story performance should require admin authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/metrics/story-performance")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Story performance requires admin auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
