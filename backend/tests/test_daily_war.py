"""
Daily Story War API Tests
Tests for: /api/war/* endpoints
Features: war lifecycle, leaderboard, scoring, notifications
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


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
    pytest.skip("Test user authentication failed")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


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


class TestWarCurrentEndpoint:
    """Tests for GET /api/war/current"""
    
    def test_current_war_returns_200(self, api_client):
        """GET /api/war/current returns 200"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        assert response.status_code == 200
        print(f"✓ GET /api/war/current returns 200")
    
    def test_current_war_returns_success_flag(self, api_client):
        """Response includes success flag"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Response includes success=True")
    
    def test_current_war_returns_war_object(self, api_client):
        """Response includes war object with required fields"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        assert war is not None, "War object should be present"
        assert "war_id" in war
        assert "state" in war
        assert "root_story_id" in war
        assert "root_title" in war
        assert "start_time" in war
        assert "end_time" in war
        assert "time_left_seconds" in war
        assert "total_entries" in war
        print(f"✓ War object has all required fields: {war.get('war_id')}")
    
    def test_current_war_state_is_valid(self, api_client):
        """War state is one of valid states"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        valid_states = ["scheduled", "active", "ended", "winner_declared"]
        assert war.get("state") in valid_states, f"State {war.get('state')} not in {valid_states}"
        print(f"✓ War state is valid: {war.get('state')}")
    
    def test_current_war_returns_leaderboard(self, api_client):
        """Response includes leaderboard object"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        leaderboard = data.get("leaderboard")
        
        assert leaderboard is not None
        assert "entries" in leaderboard
        assert "total_entries" in leaderboard
        assert isinstance(leaderboard["entries"], list)
        print(f"✓ Leaderboard returned with {leaderboard['total_entries']} entries")
    
    def test_current_war_time_left_is_positive_for_active(self, api_client):
        """Active war has positive time_left_seconds"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        if war.get("state") == "active":
            assert war.get("time_left_seconds", 0) > 0, "Active war should have positive time left"
            print(f"✓ Active war has {war.get('time_left_seconds')} seconds left")
        else:
            print(f"⊘ War is not active (state={war.get('state')}), skipping time check")
    
    def test_authenticated_user_gets_user_rank(self, authenticated_client):
        """Authenticated user gets user_rank in leaderboard"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        leaderboard = data.get("leaderboard")
        
        # user_rank can be None if user hasn't entered
        assert "user_rank" in leaderboard
        assert "user_entry" in leaderboard
        print(f"✓ Authenticated response includes user_rank: {leaderboard.get('user_rank')}")


class TestWarYesterdayEndpoint:
    """Tests for GET /api/war/yesterday"""
    
    def test_yesterday_requires_auth(self, api_client):
        """GET /api/war/yesterday requires authentication"""
        # Remove auth header for this test
        headers = {"Content-Type": "application/json"}
        response = requests.get(f"{BASE_URL}/api/war/yesterday", headers=headers)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ /api/war/yesterday requires authentication")
    
    def test_yesterday_returns_200_for_authenticated(self, authenticated_client):
        """GET /api/war/yesterday returns 200 for authenticated user"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/yesterday")
        assert response.status_code == 200
        print(f"✓ GET /api/war/yesterday returns 200")
    
    def test_yesterday_returns_war_results(self, authenticated_client):
        """Response includes yesterday_war with results"""
        response = authenticated_client.get(f"{BASE_URL}/api/war/yesterday")
        data = response.json()
        
        assert data.get("success") == True
        yesterday_war = data.get("yesterday_war")
        
        if yesterday_war:
            assert "war_id" in yesterday_war
            assert "root_title" in yesterday_war
            assert "winner_title" in yesterday_war
            assert "total_entries" in yesterday_war
            assert "your_rank" in yesterday_war
            assert "you_participated" in yesterday_war
            print(f"✓ Yesterday war results: {yesterday_war.get('root_title')}, user rank: {yesterday_war.get('your_rank')}")
        else:
            print(f"⊘ No yesterday war found (expected if no previous wars)")


class TestWarHistoryEndpoint:
    """Tests for GET /api/war/history"""
    
    def test_history_returns_200(self, api_client):
        """GET /api/war/history returns 200"""
        response = api_client.get(f"{BASE_URL}/api/war/history")
        assert response.status_code == 200
        print(f"✓ GET /api/war/history returns 200")
    
    def test_history_returns_wars_list(self, api_client):
        """Response includes wars list"""
        response = api_client.get(f"{BASE_URL}/api/war/history")
        data = response.json()
        
        assert data.get("success") == True
        assert "wars" in data
        assert isinstance(data["wars"], list)
        print(f"✓ History returned {len(data['wars'])} past wars")
    
    def test_history_respects_limit(self, api_client):
        """History respects limit parameter"""
        response = api_client.get(f"{BASE_URL}/api/war/history?limit=2")
        data = response.json()
        
        assert len(data.get("wars", [])) <= 2
        print(f"✓ History respects limit=2, returned {len(data.get('wars', []))} wars")
    
    def test_history_wars_have_required_fields(self, api_client):
        """Past wars have required fields"""
        response = api_client.get(f"{BASE_URL}/api/war/history")
        data = response.json()
        wars = data.get("wars", [])
        
        if wars:
            war = wars[0]
            assert "war_id" in war
            assert "root_title" in war
            assert "start_time" in war
            assert "end_time" in war
            assert "total_entries" in war
            print(f"✓ Past war has required fields: {war.get('war_id')}")
        else:
            print(f"⊘ No past wars to validate")


class TestWarEnterEndpoint:
    """Tests for POST /api/war/enter"""
    
    def test_enter_requires_auth(self, api_client):
        """POST /api/war/enter requires authentication"""
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/api/war/enter", headers=headers, json={
            "title": "Test Entry",
            "story_text": "A" * 100,
            "animation_style": "cartoon_2d"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ /api/war/enter requires authentication")
    
    def test_enter_validates_title_length(self, authenticated_client):
        """Entry title must be at least 3 characters"""
        response = authenticated_client.post(f"{BASE_URL}/api/war/enter", json={
            "title": "AB",  # Too short
            "story_text": "A" * 100,
            "animation_style": "cartoon_2d"
        })
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for short title, got {response.status_code}"
        print(f"✓ Entry title validation works (min 3 chars)")
    
    def test_enter_validates_story_text_length(self, authenticated_client):
        """Entry story_text must be at least 50 characters"""
        response = authenticated_client.post(f"{BASE_URL}/api/war/enter", json={
            "title": "Valid Title",
            "story_text": "Too short",  # Less than 50 chars
            "animation_style": "cartoon_2d"
        })
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422 for short story, got {response.status_code}"
        print(f"✓ Entry story_text validation works (min 50 chars)")


class TestWarIncrementMetricEndpoint:
    """Tests for POST /api/war/increment-metric"""
    
    def test_increment_metric_validates_job_id(self, api_client):
        """Increment metric requires valid job_id"""
        response = api_client.post(f"{BASE_URL}/api/war/increment-metric", json={
            "job_id": "nonexistent-job-id",
            "metric": "views"
        })
        assert response.status_code == 404, f"Expected 404 for invalid job_id, got {response.status_code}"
        print(f"✓ Increment metric validates job_id (404 for invalid)")
    
    def test_increment_metric_validates_metric_type(self, api_client):
        """Increment metric validates metric type"""
        response = api_client.post(f"{BASE_URL}/api/war/increment-metric", json={
            "job_id": "some-job-id",
            "metric": "invalid_metric"
        })
        # Should fail validation (422) or not found (404)
        assert response.status_code in [400, 404, 422], f"Expected 400/404/422, got {response.status_code}"
        print(f"✓ Increment metric validates metric type")


class TestWarAdminEndpoints:
    """Tests for admin war endpoints"""
    
    def test_admin_seed_requires_admin(self, authenticated_client):
        """POST /api/war/admin/seed requires admin role"""
        response = authenticated_client.post(f"{BASE_URL}/api/war/admin/seed", json={
            "title": "Test War",
            "story_text": "A" * 100,
            "animation_style": "cartoon_2d",
            "start_delay_minutes": 0
        })
        # Regular user should get 403
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print(f"✓ /api/war/admin/seed requires admin role")
    
    def test_admin_end_requires_admin(self, authenticated_client):
        """POST /api/war/admin/end requires admin role"""
        response = authenticated_client.post(f"{BASE_URL}/api/war/admin/end")
        # Regular user should get 403
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print(f"✓ /api/war/admin/end requires admin role")


class TestWarScoringLogic:
    """Tests for war scoring and ranking logic"""
    
    def test_leaderboard_entries_have_war_score(self, api_client):
        """Leaderboard entries include war_score"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        entries = data.get("leaderboard", {}).get("entries", [])
        
        if entries:
            entry = entries[0]
            assert "war_score" in entry
            assert "war_views" in entry
            assert "war_shares" in entry
            assert "war_continues" in entry
            assert "war_rank" in entry
            print(f"✓ Leaderboard entries have war scoring fields")
        else:
            print(f"⊘ No entries to validate scoring fields")
    
    def test_leaderboard_entries_have_gap_to_first(self, api_client):
        """Leaderboard entries include gap_score (gap to #1)"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        entries = data.get("leaderboard", {}).get("entries", [])
        
        if entries:
            entry = entries[0]
            assert "gap_score" in entry
            assert "gap_continues" in entry
            print(f"✓ Leaderboard entries have gap-to-#1 fields")
        else:
            print(f"⊘ No entries to validate gap fields")
    
    def test_leaderboard_entries_have_creator_name(self, api_client):
        """Leaderboard entries include creator_name"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        entries = data.get("leaderboard", {}).get("entries", [])
        
        if entries:
            entry = entries[0]
            assert "creator_name" in entry
            print(f"✓ Leaderboard entries have creator_name")
        else:
            print(f"⊘ No entries to validate creator_name")
    
    def test_leaderboard_entries_have_eligibility(self, api_client):
        """Leaderboard entries include eligible flag"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        entries = data.get("leaderboard", {}).get("entries", [])
        
        if entries:
            entry = entries[0]
            assert "eligible" in entry
            print(f"✓ Leaderboard entries have eligible flag")
        else:
            print(f"⊘ No entries to validate eligibility")


class TestWarDataIntegrity:
    """Tests for data integrity and consistency"""
    
    def test_war_id_format(self, api_client):
        """War ID follows expected format"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        if war:
            war_id = war.get("war_id", "")
            assert war_id.startswith("war-"), f"War ID should start with 'war-': {war_id}"
            print(f"✓ War ID format is valid: {war_id}")
        else:
            print(f"⊘ No war to validate ID format")
    
    def test_root_story_id_format(self, api_client):
        """Root story ID follows expected format"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        if war:
            root_id = war.get("root_story_id", "")
            assert root_id.startswith("war-root-"), f"Root story ID should start with 'war-root-': {root_id}"
            print(f"✓ Root story ID format is valid: {root_id}")
        else:
            print(f"⊘ No war to validate root story ID")
    
    def test_time_fields_are_iso_format(self, api_client):
        """Time fields are in ISO format"""
        response = api_client.get(f"{BASE_URL}/api/war/current")
        data = response.json()
        war = data.get("war")
        
        if war:
            start_time = war.get("start_time", "")
            end_time = war.get("end_time", "")
            
            # Try parsing as ISO format
            try:
                datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                print(f"✓ Time fields are valid ISO format")
            except ValueError as e:
                pytest.fail(f"Time fields not in ISO format: {e}")
        else:
            print(f"⊘ No war to validate time fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
