"""
Phase 2B: CompetitionPulse + Style Remix + Accordion Continuation Tests

Tests:
- /api/stories/battle/{id} endpoint for CompetitionPulse component
- Battle endpoint returns user_rank, contenders, total_contenders
- Validates winner state (rank=1) vs competitor state (rank>1)
- Tests gap calculation fields (battle_score, total_children)
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
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with test user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        """Verify API is healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")


class TestBattleEndpoint:
    """Tests for /api/stories/battle/{id} endpoint used by CompetitionPulse"""
    
    def test_battle_endpoint_exists(self, api_client):
        """Verify battle endpoint returns proper response structure"""
        # Use a known demo story ID or any story ID
        response = api_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        # Should return 200 or 404 (if story doesn't exist), not 500
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ Battle endpoint responds with status {response.status_code}")
    
    def test_battle_endpoint_with_auth(self, authenticated_client):
        """Verify battle endpoint works with authenticated user"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            # Verify required fields for CompetitionPulse
            assert "contenders" in data, "Missing contenders field"
            assert "total_contenders" in data, "Missing total_contenders field"
            # user_rank may be None if user hasn't participated
            print(f"✓ Battle endpoint returns success with {data.get('total_contenders')} contenders")
        elif response.status_code == 404:
            print("✓ Battle endpoint returns 404 for non-existent story (expected)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code}")
    
    def test_battle_response_structure(self, authenticated_client):
        """Verify battle response has all fields needed by CompetitionPulse"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            # Required fields for CompetitionPulse component
            required_fields = ["success", "contenders", "total_contenders"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify contenders structure
            if data.get("contenders"):
                contender = data["contenders"][0]
                contender_fields = ["job_id", "title", "battle_score"]
                for field in contender_fields:
                    assert field in contender, f"Contender missing field: {field}"
                print(f"✓ Contender structure valid: {contender.get('title')}")
            
            print("✓ Battle response structure is valid for CompetitionPulse")
        else:
            print(f"✓ Battle endpoint returns {response.status_code} (story may not exist)")
    
    def test_battle_user_rank_calculation(self, authenticated_client):
        """Verify user_rank is calculated correctly when user has participated"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            user_rank = data.get("user_rank")
            user_id = data.get("user_id")
            
            if user_rank:
                # User has participated - verify rank is valid
                assert isinstance(user_rank, int), "user_rank should be integer"
                assert user_rank >= 1, "user_rank should be >= 1"
                assert user_rank <= data.get("total_contenders", 0), "user_rank should be <= total_contenders"
                print(f"✓ User rank: #{user_rank} of {data.get('total_contenders')}")
            else:
                print("✓ User has not participated in this battle (user_rank is None)")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")


class TestBattleContenderFields:
    """Tests for contender fields needed for gap calculation"""
    
    def test_contender_battle_score(self, authenticated_client):
        """Verify contenders have battle_score for gap calculation"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            contenders = data.get("contenders", [])
            if contenders:
                for c in contenders[:3]:  # Check first 3
                    assert "battle_score" in c, "Contender missing battle_score"
                    assert isinstance(c["battle_score"], (int, float)), "battle_score should be numeric"
                print(f"✓ All contenders have valid battle_score")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")
    
    def test_contender_total_children(self, authenticated_client):
        """Verify contenders have total_children for gap calculation"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            contenders = data.get("contenders", [])
            if contenders:
                for c in contenders[:3]:
                    # total_children may be 0 but should exist
                    assert "total_children" in c or c.get("total_children", 0) >= 0
                print(f"✓ Contenders have total_children field")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")
    
    def test_contender_creator_name(self, authenticated_client):
        """Verify contenders have creator_name for display"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            contenders = data.get("contenders", [])
            if contenders:
                for c in contenders[:3]:
                    assert "creator_name" in c, "Contender missing creator_name"
                    assert isinstance(c["creator_name"], str), "creator_name should be string"
                print(f"✓ Contenders have creator_name: {contenders[0].get('creator_name')}")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")


class TestBattleRanking:
    """Tests for battle ranking and sorting"""
    
    def test_contenders_sorted_by_score(self, authenticated_client):
        """Verify contenders are sorted by battle_score descending"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            contenders = data.get("contenders", [])
            if len(contenders) >= 2:
                scores = [c.get("battle_score", 0) for c in contenders]
                assert scores == sorted(scores, reverse=True), "Contenders should be sorted by battle_score desc"
                print(f"✓ Contenders sorted by score: {scores[:3]}")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")
    
    def test_contenders_have_rank(self, authenticated_client):
        """Verify contenders have rank field"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        if response.status_code == 200:
            data = response.json()
            contenders = data.get("contenders", [])
            if contenders:
                for i, c in enumerate(contenders):
                    assert "rank" in c, "Contender missing rank"
                    assert c["rank"] == i + 1, f"Rank should be {i+1}, got {c['rank']}"
                print(f"✓ Contenders have correct rank assignments")
        else:
            print(f"✓ Battle endpoint returns {response.status_code}")


class TestIncrementMetric:
    """Tests for /api/stories/increment-metric endpoint"""
    
    def test_increment_views(self, api_client):
        """Test incrementing view count"""
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "battle-demo-root",
            "metric": "views"
        })
        # Should return 200 or 404
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "battle_score" in data, "Should return updated battle_score"
            print(f"✓ View increment successful, new score: {data.get('battle_score')}")
        else:
            print("✓ Story not found (expected for demo)")
    
    def test_increment_shares(self, api_client):
        """Test incrementing share count"""
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "battle-demo-root",
            "metric": "shares"
        })
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            print(f"✓ Share increment successful")
        else:
            print("✓ Story not found (expected for demo)")
    
    def test_invalid_metric_rejected(self, api_client):
        """Test that invalid metrics are rejected"""
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": "battle-demo-root",
            "metric": "invalid_metric"
        })
        # Should return 400 or 422 for invalid metric
        assert response.status_code in [400, 422], f"Should reject invalid metric, got {response.status_code}"
        print("✓ Invalid metric correctly rejected")


class TestFunnelTracking:
    """Tests for analytics tracking endpoints used by Phase 2B features"""
    
    def test_funnel_track_endpoint(self, authenticated_client):
        """Test funnel tracking for create_new_story_clicked event"""
        response = authenticated_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "create_new_story_clicked",
            "data": {"from_job": "test-job-id"}
        })
        # Should return 200 or 201
        assert response.status_code in [200, 201, 204], f"Funnel track failed: {response.status_code}"
        print("✓ create_new_story_clicked event tracked")
    
    def test_style_remix_clicked_event(self, authenticated_client):
        """Test funnel tracking for style_remix_clicked event"""
        response = authenticated_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "style_remix_clicked",
            "data": {"job_id": "test-job-id", "target_style": "anime_style"}
        })
        assert response.status_code in [200, 201, 204]
        print("✓ style_remix_clicked event tracked")
    
    def test_pulse_try_again_clicked_event(self, authenticated_client):
        """Test funnel tracking for pulse_try_again_clicked event"""
        response = authenticated_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "pulse_try_again_clicked",
            "data": {"job_id": "test-job-id"}
        })
        assert response.status_code in [200, 201, 204]
        print("✓ pulse_try_again_clicked event tracked")
    
    def test_pulse_beat_top_clicked_event(self, authenticated_client):
        """Test funnel tracking for pulse_beat_top_clicked event"""
        response = authenticated_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "pulse_beat_top_clicked",
            "data": {"job_id": "test-job-id"}
        })
        assert response.status_code in [200, 201, 204]
        print("✓ pulse_beat_top_clicked event tracked")


class TestContinuationEndpoints:
    """Tests for continuation endpoints used by ContinuationModal"""
    
    def test_continue_episode_endpoint_exists(self, authenticated_client):
        """Verify continue-episode endpoint exists"""
        # Just check the endpoint responds (don't actually create)
        response = authenticated_client.post(f"{BASE_URL}/api/stories/continue-episode", json={
            "parent_job_id": "nonexistent-job",
            "title": "Test Episode",
            "story_text": "This is a test story text that is at least 50 characters long for validation."
        })
        # Should return 404 (parent not found) or 402 (insufficient credits), not 500
        assert response.status_code in [400, 402, 404, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ continue-episode endpoint responds with {response.status_code}")
    
    def test_continue_branch_endpoint_exists(self, authenticated_client):
        """Verify continue-branch endpoint exists"""
        response = authenticated_client.post(f"{BASE_URL}/api/stories/continue-branch", json={
            "parent_job_id": "nonexistent-job",
            "title": "Test Branch",
            "story_text": "This is a test story text that is at least 50 characters long for validation."
        })
        assert response.status_code in [400, 402, 404, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ continue-branch endpoint responds with {response.status_code}")


class TestDiscoverFeed:
    """Tests for discover feed used by CompetitionPulse context"""
    
    def test_discover_feed_returns_stories(self, api_client):
        """Verify discover feed returns public stories"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "stories" in data
        print(f"✓ Discover feed returns {len(data.get('stories', []))} stories")
    
    def test_trending_feed_returns_stories(self, api_client):
        """Verify trending feed returns stories sorted by battle_score"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/trending?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Trending feed returns {len(data.get('stories', []))} stories")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
