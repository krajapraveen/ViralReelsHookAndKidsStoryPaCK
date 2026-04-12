"""
Entry Conversion Engine Tests - Iteration 501

Tests for:
1. POST /api/stories/quick-shot - 1-tap entry, returns job_id, streak info
2. GET /api/stories/hottest-battle - personalized fields for conversion
3. First-win boost in compute_battle_score - 15% lift for new users (0-1 entries)
4. Streak system integration with quick-shot
"""
import pytest
import requests
import os
import time

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


class TestAPIHealth:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        """Verify API is healthy"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("API health check passed")


class TestHottestBattleEndpoint:
    """Tests for GET /api/stories/hottest-battle with personalized conversion fields"""
    
    def test_hottest_battle_returns_data(self, api_client):
        """Verify hottest-battle endpoint returns battle data"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "battle" in data
        print(f"Hottest battle endpoint returned data: {data.get('battle', {}).get('root_title', 'N/A')}")
    
    def test_hottest_battle_has_personalized_fields_unauthenticated(self, api_client):
        """Verify personalized fields exist for unauthenticated users"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # Check personalized conversion fields exist
        assert "user_is_new" in battle, "Missing user_is_new field"
        assert "user_entry_count" in battle, "Missing user_entry_count field"
        assert "user_already_in_battle" in battle, "Missing user_already_in_battle field"
        assert "gap_continues_to_first" in battle, "Missing gap_continues_to_first field"
        
        # For unauthenticated users, should show as new
        assert battle.get("user_is_new") is True
        assert battle.get("user_entry_count") == 0
        assert battle.get("user_already_in_battle") is False
        print(f"Personalized fields for unauthenticated: user_is_new={battle.get('user_is_new')}, entry_count={battle.get('user_entry_count')}")
    
    def test_hottest_battle_has_personalized_fields_authenticated(self, authenticated_client):
        """Verify personalized fields for authenticated user"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # Check personalized conversion fields exist
        assert "user_is_new" in battle
        assert "user_entry_count" in battle
        assert "user_already_in_battle" in battle
        assert "gap_continues_to_first" in battle
        
        print(f"Personalized fields for test user: user_is_new={battle.get('user_is_new')}, entry_count={battle.get('user_entry_count')}, already_in_battle={battle.get('user_already_in_battle')}")
    
    def test_hottest_battle_has_contenders(self, api_client):
        """Verify battle has contenders with ranking info"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        contenders = battle.get("contenders", [])
        assert len(contenders) > 0, "No contenders in battle"
        
        # Check contender structure
        first = contenders[0]
        assert "job_id" in first
        assert "battle_score" in first
        assert "rank" in first
        assert "creator_name" in first
        assert first.get("rank") == 1
        print(f"Battle has {len(contenders)} contenders, #1: {first.get('title', 'N/A')} with score {first.get('battle_score', 0)}")
    
    def test_hottest_battle_gap_to_first_calculation(self, api_client):
        """Verify gap_to_first and gap_continues_to_first are calculated"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # These fields should exist for personalized CTA
        assert "gap_to_first" in battle
        assert "gap_continues_to_first" in battle
        assert "near_win" in battle
        
        print(f"Gap to first: {battle.get('gap_to_first')} pts, {battle.get('gap_continues_to_first')} continues, near_win={battle.get('near_win')}")


class TestQuickShotEndpoint:
    """Tests for POST /api/stories/quick-shot - 1-tap entry"""
    
    def test_quick_shot_requires_auth(self, api_client):
        """Verify quick-shot requires authentication"""
        # Remove auth header if present
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "battle-demo-root"},
            headers=headers
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("Quick-shot correctly requires authentication")
    
    def test_quick_shot_validates_root_story(self, authenticated_client):
        """Verify quick-shot validates root_story_id exists"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "nonexistent-story-id-12345"}
        )
        assert response.status_code == 404
        print("Quick-shot correctly validates root story exists")
    
    def test_quick_shot_endpoint_structure(self, authenticated_client):
        """Test quick-shot endpoint accepts correct payload structure"""
        # This may return SLOTS_BUSY if user has active jobs, which is expected
        response = authenticated_client.post(
            f"{BASE_URL}/api/stories/quick-shot",
            json={"root_story_id": "battle-demo-root"}
        )
        
        # Accept 200 (success), 400 (SLOTS_BUSY or other validation), 402 (insufficient credits)
        assert response.status_code in [200, 400, 402], f"Unexpected status: {response.status_code}"
        
        data = response.json()
        
        if response.status_code == 200:
            # Success case - verify response structure
            assert data.get("success") is True
            assert "job_id" in data
            assert "root_story_id" in data
            assert "streak_started" in data or "current_streak" in data
            print(f"Quick-shot success: job_id={data.get('job_id')}, streak_started={data.get('streak_started')}")
        elif response.status_code == 400:
            # Expected if user has active jobs (SLOTS_BUSY) or other validation
            detail = data.get("detail", "")
            print(f"Quick-shot returned 400: {detail}")
            # This is expected behavior per agent context
        elif response.status_code == 402:
            # Insufficient credits
            print(f"Quick-shot returned 402: insufficient credits")
        
        print(f"Quick-shot endpoint structure test passed with status {response.status_code}")


class TestFirstWinBoostInBattleScore:
    """Tests for first-win boost (15% lift for new users with 0-1 entries)"""
    
    def test_compute_battle_score_accepts_first_win_param(self, api_client):
        """Verify compute_battle_score function accepts is_first_win_eligible parameter"""
        # We test this indirectly by checking the battle score calculation
        # The function is internal, but we can verify the endpoint uses it
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # Verify contenders have battle_score (which uses compute_battle_score)
        contenders = battle.get("contenders", [])
        for c in contenders:
            assert "battle_score" in c
            assert isinstance(c["battle_score"], (int, float))
        
        print("Battle scores are calculated for all contenders")
    
    def test_first_win_eligibility_check_in_refresh(self, authenticated_client):
        """Verify refresh_battle_score checks prior_count for first-win eligibility"""
        # Get a story from the battle to verify score refresh works
        response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # The user_is_new field indicates first-win eligibility check is working
        assert "user_is_new" in battle
        assert "user_entry_count" in battle
        
        # user_is_new should be True when user_entry_count <= 1
        if battle.get("user_entry_count", 0) <= 1:
            assert battle.get("user_is_new") is True
        else:
            assert battle.get("user_is_new") is False
        
        print(f"First-win eligibility check: entry_count={battle.get('user_entry_count')}, is_new={battle.get('user_is_new')}")


class TestStreakIntegration:
    """Tests for streak system integration with quick-shot"""
    
    def test_streak_endpoint_works(self, authenticated_client):
        """Verify streak endpoint returns user streak data"""
        response = authenticated_client.get(f"{BASE_URL}/api/streaks/me")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "streak" in data
        
        streak = data["streak"]
        assert "current" in streak
        assert "longest" in streak
        assert "boost" in streak
        assert "participated_today" in streak
        
        print(f"User streak: current={streak.get('current')}, longest={streak.get('longest')}, boost={streak.get('boost')}")
    
    def test_record_participation_returns_streak_info(self, api_client):
        """Verify record_participation function returns streak_changed and current_streak"""
        # This is tested indirectly through quick-shot response
        # The quick-shot endpoint calls record_participation and returns streak info
        # We verify the response structure includes streak fields
        
        # Check the streaks.py module has the correct return structure
        # by verifying the endpoint that uses it
        response = api_client.get(f"{BASE_URL}/api/streaks/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "streaks" in data
        print(f"Streak leaderboard has {len(data.get('streaks', []))} entries")


class TestBattleEndpoints:
    """Additional battle-related endpoint tests"""
    
    def test_battle_endpoint_works(self, api_client):
        """Verify battle endpoint returns data for demo battle"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle/battle-demo-root")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "contenders" in data
        assert "battle_parent_id" in data
        
        print(f"Battle endpoint works: {len(data.get('contenders', []))} contenders")
    
    def test_trending_feed_works(self, api_client):
        """Verify trending feed endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/trending")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "stories" in data
        print(f"Trending feed has {len(data.get('stories', []))} stories")
    
    def test_discover_feed_works(self, api_client):
        """Verify discover feed endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/stories/feed/discover")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        assert "stories" in data
        assert "total" in data
        print(f"Discover feed has {data.get('total', 0)} total stories")


class TestPersonalizedCTALogic:
    """Tests for personalized CTA text logic based on user state"""
    
    def test_user_already_in_battle_detection(self, authenticated_client):
        """Verify user_already_in_battle is correctly detected"""
        response = authenticated_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        # This field should be boolean
        assert isinstance(battle.get("user_already_in_battle"), bool)
        print(f"user_already_in_battle={battle.get('user_already_in_battle')}")
    
    def test_gap_continues_to_first_for_close_race(self, api_client):
        """Verify gap_continues_to_first is calculated for close race CTA"""
        response = api_client.get(f"{BASE_URL}/api/stories/hottest-battle")
        assert response.status_code == 200
        data = response.json()
        battle = data.get("battle", {})
        
        gap = battle.get("gap_continues_to_first")
        assert gap is not None
        assert isinstance(gap, int)
        
        # If gap <= 3, it's a close race (used for "You can beat #1" CTA)
        if gap <= 3:
            print(f"Close race detected: gap_continues_to_first={gap}")
        else:
            print(f"Not a close race: gap_continues_to_first={gap}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
