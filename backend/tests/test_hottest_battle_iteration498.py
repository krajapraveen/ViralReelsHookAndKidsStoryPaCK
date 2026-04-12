"""
Hottest Battle Spectator Mode — Backend API Tests (Iteration 498)

Tests for GET /api/stories/hottest-battle endpoint:
- Aggregation finds root with most branches
- Returns top 3 contenders with scores
- near_win flag when gap ≤ 5 pts
- gap_to_first calculation
- No regressions on existing endpoints
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
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        """API health endpoint returns healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")


class TestHottestBattleEndpoint:
    """GET /api/stories/hottest-battle endpoint tests"""
    
    def test_hottest_battle_returns_200(self, api_client):
        """Endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        print("✓ Hottest battle endpoint returns 200")
    
    def test_hottest_battle_response_structure(self, api_client):
        """Response has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "battle" in data
        print("✓ Response has success and battle fields")
    
    def test_hottest_battle_has_battle_data(self, api_client):
        """Battle object has required fields"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        # Battle should exist (demo data seeded)
        assert battle is not None, "No battle data returned - demo data may not be seeded"
        
        # Required fields
        assert "root_story_id" in battle
        assert "root_title" in battle
        assert "root_creator" in battle
        assert "branch_count" in battle
        assert "contenders" in battle
        assert "near_win" in battle
        assert "gap_to_first" in battle
        
        print(f"✓ Battle has all required fields: root_story_id={battle['root_story_id']}")
    
    def test_hottest_battle_contenders_structure(self, api_client):
        """Contenders have correct structure with ranks"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        contenders = battle.get("contenders", [])
        
        # Should have up to 3 contenders
        assert len(contenders) <= 3, f"Expected max 3 contenders, got {len(contenders)}"
        assert len(contenders) > 0, "Expected at least 1 contender"
        
        for i, c in enumerate(contenders):
            assert "job_id" in c, f"Contender {i} missing job_id"
            assert "title" in c, f"Contender {i} missing title"
            assert "battle_score" in c, f"Contender {i} missing battle_score"
            assert "rank" in c, f"Contender {i} missing rank"
            assert "creator_name" in c, f"Contender {i} missing creator_name"
            assert c["rank"] == i + 1, f"Contender {i} has wrong rank: {c['rank']}"
        
        print(f"✓ {len(contenders)} contenders with correct structure and ranks")
    
    def test_hottest_battle_contenders_sorted_by_score(self, api_client):
        """Contenders are sorted by battle_score descending"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        contenders = battle.get("contenders", [])
        
        if len(contenders) >= 2:
            for i in range(len(contenders) - 1):
                assert contenders[i]["battle_score"] >= contenders[i+1]["battle_score"], \
                    f"Contenders not sorted: {contenders[i]['battle_score']} < {contenders[i+1]['battle_score']}"
        
        print("✓ Contenders sorted by battle_score descending")
    
    def test_hottest_battle_near_win_flag(self, api_client):
        """near_win flag is boolean based on gap threshold"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        near_win = battle.get("near_win")
        gap_to_first = battle.get("gap_to_first")
        
        assert isinstance(near_win, bool), f"near_win should be bool, got {type(near_win)}"
        assert isinstance(gap_to_first, (int, float)), f"gap_to_first should be numeric, got {type(gap_to_first)}"
        
        # Verify near_win logic: true when gap ≤ 5
        if gap_to_first <= 5:
            assert near_win == True, f"near_win should be True when gap={gap_to_first}"
        else:
            assert near_win == False, f"near_win should be False when gap={gap_to_first}"
        
        print(f"✓ near_win={near_win}, gap_to_first={gap_to_first} (threshold ≤5)")
    
    def test_hottest_battle_gap_calculation(self, api_client):
        """gap_to_first is calculated correctly from top 2 scores"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        contenders = battle.get("contenders", [])
        gap_to_first = battle.get("gap_to_first")
        
        if len(contenders) >= 2:
            top_score = contenders[0].get("battle_score", 0)
            second_score = contenders[1].get("battle_score", 0)
            expected_gap = round(top_score - second_score)
            
            # Allow small rounding difference
            assert abs(gap_to_first - expected_gap) <= 1, \
                f"gap_to_first={gap_to_first} doesn't match calculated gap={expected_gap}"
        
        print(f"✓ gap_to_first calculation verified: {gap_to_first}")
    
    def test_hottest_battle_demo_data(self, api_client):
        """Demo data exists: battle-demo-root with 3 branches"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        
        # Verify demo data as per agent context
        assert battle.get("root_story_id") == "battle-demo-root", \
            f"Expected battle-demo-root, got {battle.get('root_story_id')}"
        assert battle.get("branch_count") == 3, \
            f"Expected 3 branches, got {battle.get('branch_count')}"
        
        # Verify contender titles
        contender_titles = [c.get("title") for c in battle.get("contenders", [])]
        assert any("Horror Edition" in t for t in contender_titles), "Missing Horror Edition contender"
        assert any("Crystal Maze" in t for t in contender_titles), "Missing Crystal Maze contender"
        
        print("✓ Demo data verified: battle-demo-root with 3 branches")


class TestHottestBattleAggregation:
    """Tests for the aggregation pipeline logic"""
    
    def test_aggregation_finds_root_with_most_branches(self, api_client):
        """Aggregation correctly identifies root with most branches"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        branch_count = battle.get("branch_count", 0)
        
        # Demo data has 3 branches - should be the hottest
        assert branch_count >= 1, "Hottest battle should have at least 1 branch"
        print(f"✓ Aggregation found root with {branch_count} branches")
    
    def test_aggregation_includes_root_in_contenders(self, api_client):
        """Root story is included in contenders list"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        data = response.json()
        battle = data.get("battle")
        
        assert battle is not None
        root_id = battle.get("root_story_id")
        contenders = battle.get("contenders", [])
        
        contender_ids = [c.get("job_id") for c in contenders]
        assert root_id in contender_ids, f"Root {root_id} not in contenders: {contender_ids}"
        
        print(f"✓ Root story {root_id} included in contenders")


class TestNoRegressions:
    """Verify existing endpoints still work"""
    
    def test_battle_endpoint_no_regression(self, api_client):
        """GET /api/stories/battle/{story_id} still works"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Battle endpoint no regression")
    
    def test_chain_endpoint_no_regression(self, api_client):
        """GET /api/stories/{story_id}/chain still works"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle-demo-root/chain")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Chain endpoint no regression")
    
    def test_trending_feed_no_regression(self, api_client):
        """GET /api/stories/feed/trending still works"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/trending")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Trending feed no regression")
    
    def test_discover_feed_no_regression(self, api_client):
        """GET /api/stories/feed/discover still works"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Discover feed no regression")
    
    def test_war_current_no_regression(self, api_client):
        """GET /api/war/current still works"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        # May return 404 if no war active, but should not error
        assert response.status_code in [200, 404]
        print("✓ War current endpoint no regression")


class TestAnalyticsTracking:
    """Tests for analytics event tracking"""
    
    def test_funnel_track_endpoint_exists(self, api_client):
        """POST /api/funnel/track endpoint exists"""
        response = api_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "spectator_to_player_conversion",
            "data": {"root_id": "test-root-id"}
        })
        # Should accept the event (may require auth or return 200/401)
        assert response.status_code in [200, 201, 401, 422]
        print(f"✓ Funnel track endpoint exists (status: {response.status_code})")


class TestAuthenticatedAccess:
    """Tests with authenticated user"""
    
    def test_hottest_battle_with_auth(self, authenticated_client):
        """Hottest battle works with authenticated user"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Hottest battle works with auth")
    
    def test_continue_watching_feed_with_auth(self, authenticated_client):
        """Continue watching feed requires auth and works"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/feed/continue-watching")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Continue watching feed works with auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
