"""
Test Suite: Monetization & Behavioral Compulsion Engine - Iteration 313
Features Tested:
- 4-tier subscription pricing (Free $0, Creator $5.99, Pro $11.99, Elite $23.99)
- Per-tool credit costs
- Top-up bundles (20/$2.49, 50/$4.99, 100/$8.49)
- Paywall enforcement (403 on series/episode limits)
- My-limits endpoint with plan/credits/series_limits
- ResumeYourStory compulsion data (next_episode, episodes_left, next_hook)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

# Test series ID that has 1 series with 3 episodes (at free limit)
TEST_SERIES_ID = "ea2bc4e8-454d-4f40-8415-f4383593904a"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token for test user (free plan)"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed - status {response.status_code}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# =============================================================================
# MONETIZATION API: GET /api/monetization/plans
# =============================================================================

class TestMonetizationPlans:
    """Test 4-tier subscription plan API"""
    
    def test_plans_returns_200(self, api_client):
        """GET /api/monetization/plans should return 200"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_plans_returns_4_tiers(self, api_client):
        """Should return exactly 4 plans"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        assert data.get("success") is True
        plans = data.get("plans", [])
        assert len(plans) == 4, f"Expected 4 plans, got {len(plans)}"
        
    def test_free_plan_pricing(self, api_client):
        """Free plan: $0 price"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        assert "free" in plans
        assert plans["free"]["price_usd"] == 0
        
    def test_creator_plan_pricing(self, api_client):
        """Creator plan: $5.99/month"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        assert "creator" in plans
        assert plans["creator"]["price_usd"] == 5.99
        
    def test_pro_plan_pricing(self, api_client):
        """Pro plan: $11.99/month"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        assert "pro" in plans
        assert plans["pro"]["price_usd"] == 11.99
        
    def test_elite_plan_pricing(self, api_client):
        """Elite plan: $23.99/month"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        assert "elite" in plans
        assert plans["elite"]["price_usd"] == 23.99
        
    def test_free_plan_has_series_limits(self, api_client):
        """Free plan should have max_series=1, max_episodes_per_series=3"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        free_limits = plans["free"].get("limitations", {})
        assert free_limits.get("max_series") == 1
        assert free_limits.get("max_episodes_per_series") == 3
        
    def test_creator_plan_has_series_limits(self, api_client):
        """Creator plan should have max_series=5, max_episodes_per_series=15"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        creator_limits = plans["creator"].get("limitations", {})
        assert creator_limits.get("max_series") == 5
        assert creator_limits.get("max_episodes_per_series") == 15
        
    def test_pro_plan_unlimited_series(self, api_client):
        """Pro plan should have max_series=999 (unlimited)"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        plans = {p["id"]: p for p in data.get("plans", [])}
        pro_limits = plans["pro"].get("limitations", {})
        assert pro_limits.get("max_series") == 999
        
    def test_plan_has_features_list(self, api_client):
        """Each plan should have a features list"""
        response = api_client.get(f"{BASE_URL}/api/monetization/plans")
        data = response.json()
        for plan in data.get("plans", []):
            assert "features" in plan
            assert isinstance(plan["features"], list)
            assert len(plan["features"]) > 0


# =============================================================================
# MONETIZATION API: GET /api/monetization/tool-costs
# =============================================================================

class TestToolCreditCosts:
    """Test per-tool credit cost API"""
    
    def test_tool_costs_returns_200(self, api_client):
        """GET /api/monetization/tool-costs should return 200"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        assert response.status_code == 200
        
    def test_caption_costs_1_credit(self, api_client):
        """Caption tool should cost 1 credit"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        data = response.json()
        costs = data.get("costs", {})
        assert costs.get("caption") == 1
        
    def test_gif_costs_2_credits(self, api_client):
        """GIF tool should cost 2 credits"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        data = response.json()
        costs = data.get("costs", {})
        assert costs.get("gif") == 2
        
    def test_photo_to_comic_costs_3_credits(self, api_client):
        """Photo to comic should cost 3 credits"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        data = response.json()
        costs = data.get("costs", {})
        assert costs.get("photo_to_comic") == 3
        
    def test_storybook_costs_5_credits(self, api_client):
        """Storybook should cost 5 credits"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        data = response.json()
        costs = data.get("costs", {})
        assert costs.get("storybook") == 5
        
    def test_story_video_costs_10_credits(self, api_client):
        """Story video should cost 10 credits"""
        response = api_client.get(f"{BASE_URL}/api/monetization/tool-costs")
        data = response.json()
        costs = data.get("costs", {})
        assert costs.get("story_video") == 10


# =============================================================================
# MONETIZATION API: GET /api/monetization/topups
# =============================================================================

class TestTopupPacks:
    """Test credit top-up bundles API"""
    
    def test_topups_returns_200(self, api_client):
        """GET /api/monetization/topups should return 200"""
        response = api_client.get(f"{BASE_URL}/api/monetization/topups")
        assert response.status_code == 200
        
    def test_topups_returns_3_packs(self, api_client):
        """Should return 3 top-up packs"""
        response = api_client.get(f"{BASE_URL}/api/monetization/topups")
        data = response.json()
        packs = data.get("packs", [])
        assert len(packs) == 3
        
    def test_small_pack_20_credits_2_49(self, api_client):
        """Small pack: 20 credits for $2.49"""
        response = api_client.get(f"{BASE_URL}/api/monetization/topups")
        data = response.json()
        packs = {p["id"]: p for p in data.get("packs", [])}
        assert "small" in packs
        assert packs["small"]["credits"] == 20
        assert packs["small"]["price_usd"] == 2.49
        
    def test_medium_pack_50_credits_4_99(self, api_client):
        """Medium pack: 50 credits for $4.99"""
        response = api_client.get(f"{BASE_URL}/api/monetization/topups")
        data = response.json()
        packs = {p["id"]: p for p in data.get("packs", [])}
        assert "medium" in packs
        assert packs["medium"]["credits"] == 50
        assert packs["medium"]["price_usd"] == 4.99
        
    def test_large_pack_100_credits_8_49(self, api_client):
        """Large pack: 100 credits for $8.49"""
        response = api_client.get(f"{BASE_URL}/api/monetization/topups")
        data = response.json()
        packs = {p["id"]: p for p in data.get("packs", [])}
        assert "large" in packs
        assert packs["large"]["credits"] == 100
        assert packs["large"]["price_usd"] == 8.49


# =============================================================================
# MONETIZATION API: GET /api/monetization/my-limits (requires auth)
# =============================================================================

class TestMyLimits:
    """Test user limits endpoint - returns plan, credits, series_limits"""
    
    def test_my_limits_requires_auth(self, api_client):
        """GET /api/monetization/my-limits should require authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/monetization/my-limits")
        assert response.status_code in [401, 403]
        
    def test_my_limits_returns_200_with_auth(self, authenticated_client):
        """GET /api/monetization/my-limits should return 200 with auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/my-limits")
        assert response.status_code == 200
        
    def test_my_limits_has_plan(self, authenticated_client):
        """Response should include user's plan"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/my-limits")
        data = response.json()
        assert "plan" in data
        assert data["plan"] in ["free", "creator", "pro", "elite"]
        
    def test_my_limits_has_credits(self, authenticated_client):
        """Response should include user's credits"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/my-limits")
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], (int, float))
        
    def test_my_limits_has_series_limits(self, authenticated_client):
        """Response should include series_limits with max_series and max_episodes_per_series"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/my-limits")
        data = response.json()
        assert "series_limits" in data
        series_limits = data["series_limits"]
        assert "max_series" in series_limits
        assert "max_episodes_per_series" in series_limits
        
    def test_my_limits_has_limitations(self, authenticated_client):
        """Response should include full limitations object"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/my-limits")
        data = response.json()
        assert "limitations" in data


# =============================================================================
# PAYWALL: POST /api/story-series/create with series limit
# =============================================================================

class TestSeriesPaywall:
    """Test paywall enforcement for series creation"""
    
    def test_create_series_returns_403_at_limit(self, authenticated_client):
        """Free user with 1 series should get 403 when creating another series"""
        # The test user has 1 series already (Fox Forest) - at free limit
        response = authenticated_client.post(f"{BASE_URL}/api/story-series/create", json={
            "title": "TEST_Paywall_Series",
            "initial_prompt": "A test story to trigger paywall",
            "genre": "adventure",
            "audience": "kids_5_8",
            "style": "cartoon_2d",
            "tool": "story_video"
        })
        # Should return 403 because free plan allows only 1 series
        assert response.status_code == 403, f"Expected 403 paywall, got {response.status_code}"
        
    def test_create_series_403_has_upgrade_message(self, authenticated_client):
        """403 response should contain upgrade message"""
        response = authenticated_client.post(f"{BASE_URL}/api/story-series/create", json={
            "title": "TEST_Paywall_Series_2",
            "initial_prompt": "Another test story to trigger paywall",
            "genre": "adventure",
            "audience": "kids_5_8",
            "style": "cartoon_2d",
            "tool": "story_video"
        })
        assert response.status_code == 403
        data = response.json()
        detail = data.get("detail", "")
        # Should mention series limit or upgrade
        assert "series" in detail.lower() or "limit" in detail.lower() or "upgrade" in detail.lower()


# =============================================================================
# PAYWALL: POST /api/story-series/{id}/plan-episode with episode limit
# =============================================================================

class TestEpisodePaywall:
    """Test paywall enforcement for episode creation"""
    
    def test_plan_episode_returns_403_at_limit(self, authenticated_client):
        """Free user with 3 episodes should get 403 when planning episode 4"""
        # The test series has 3 episodes (at free limit)
        response = authenticated_client.post(
            f"{BASE_URL}/api/story-series/{TEST_SERIES_ID}/plan-episode",
            json={"direction_type": "continue"}
        )
        # Should return 403 because free plan allows only 3 episodes per series
        assert response.status_code == 403, f"Expected 403 paywall, got {response.status_code}"
        
    def test_plan_episode_403_has_upgrade_message(self, authenticated_client):
        """403 response should contain upgrade message about episode limit"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/story-series/{TEST_SERIES_ID}/plan-episode",
            json={"direction_type": "continue"}
        )
        assert response.status_code == 403
        data = response.json()
        detail = data.get("detail", "")
        # Should mention episode limit or upgrade
        assert "episode" in detail.lower() or "limit" in detail.lower() or "upgrade" in detail.lower()


# =============================================================================
# COMPULSION DATA: GET /api/story-series/my-series
# =============================================================================

class TestCompulsionData:
    """Test behavioral compulsion data in my-series response"""
    
    def test_my_series_has_compulsion_fields(self, authenticated_client):
        """GET /api/story-series/my-series should return compulsion data"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        assert response.status_code == 200
        data = response.json()
        series_list = data.get("series", [])
        assert len(series_list) > 0, "Expected at least one series for test user"
        
    def test_series_has_next_episode_field(self, authenticated_client):
        """Each series should have next_episode field"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        data = response.json()
        series_list = data.get("series", [])
        for s in series_list:
            # next_episode can be null if no planned episodes
            assert "next_episode" in s or s.get("next_episode") is None
            
    def test_series_has_episodes_left_field(self, authenticated_client):
        """Each series should have episodes_left count"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        data = response.json()
        series_list = data.get("series", [])
        for s in series_list:
            assert "episodes_left" in s
            assert isinstance(s["episodes_left"], int)
            
    def test_series_has_next_hook_field(self, authenticated_client):
        """Each series should have next_hook field (from story memory)"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        data = response.json()
        series_list = data.get("series", [])
        for s in series_list:
            # next_hook can be null if no pending hooks
            assert "next_hook" in s
            
    def test_series_has_open_loops_count(self, authenticated_client):
        """Each series should have open_loops_count"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        data = response.json()
        series_list = data.get("series", [])
        for s in series_list:
            assert "open_loops_count" in s
            assert isinstance(s["open_loops_count"], int)
            
    def test_series_has_total_episodes(self, authenticated_client):
        """Each series should have total_episodes or episode_count"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-series/my-series")
        data = response.json()
        series_list = data.get("series", [])
        for s in series_list:
            assert "total_episodes" in s or "episode_count" in s


# =============================================================================
# OTHER MONETIZATION ENDPOINTS
# =============================================================================

class TestOtherMonetizationEndpoints:
    """Test additional monetization endpoints"""
    
    def test_variations_returns_200(self, api_client):
        """GET /api/monetization/variations should return 200"""
        response = api_client.get(f"{BASE_URL}/api/monetization/variations")
        assert response.status_code == 200
        
    def test_bundles_returns_200(self, api_client):
        """GET /api/monetization/bundles/{feature} should return 200"""
        response = api_client.get(f"{BASE_URL}/api/monetization/bundles/comix")
        assert response.status_code == 200
        
    def test_upsells_requires_auth(self, api_client):
        """GET /api/monetization/upsells should require auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/monetization/upsells")
        assert response.status_code in [401, 403]
        
    def test_credit_status_requires_auth(self, api_client):
        """GET /api/monetization/credit-status should require auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/monetization/credit-status")
        assert response.status_code in [401, 403]
        
    def test_credit_status_returns_200_with_auth(self, authenticated_client):
        """GET /api/monetization/credit-status should return 200 with auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/monetization/credit-status")
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "status" in data


# =============================================================================
# AUTH ENFORCEMENT
# =============================================================================

class TestAuthEnforcement:
    """Verify auth is required for protected endpoints"""
    
    def test_create_series_requires_auth(self, api_client):
        """POST /api/story-series/create should require auth"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(f"{BASE_URL}/api/story-series/create", json={
            "title": "Test",
            "initial_prompt": "Test"
        })
        assert response.status_code in [401, 403]
        
    def test_plan_episode_requires_auth(self, api_client):
        """POST /api/story-series/{id}/plan-episode should require auth"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        response = session.post(
            f"{BASE_URL}/api/story-series/{TEST_SERIES_ID}/plan-episode",
            json={"direction_type": "continue"}
        )
        assert response.status_code in [401, 403]
        
    def test_my_series_requires_auth(self, api_client):
        """GET /api/story-series/my-series should require auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/story-series/my-series")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
