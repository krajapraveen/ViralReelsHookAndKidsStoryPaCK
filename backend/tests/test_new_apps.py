"""
Test Suite for New Standalone Apps (Story Series, Challenge Generator, Tone Switcher)
and Regional Pricing Module
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}

class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.text}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# =============================================================================
# STORY SERIES API TESTS
# =============================================================================

class TestStorySeriesPricing(TestSetup):
    """Story Series pricing endpoint tests"""
    
    def test_pricing_returns_200(self):
        """GET /api/story-series/pricing returns 200"""
        response = requests.get(f"{BASE_URL}/api/story-series/pricing")
        assert response.status_code == 200
        data = response.json()
        
        # Validate pricing structure
        assert "pricing" in data
        assert "episodeBundles" in data
        assert "addOns" in data
        
        # Validate pricing values
        pricing = data["pricing"]
        assert pricing["3_EPISODES"] == 8
        assert pricing["5_EPISODES"] == 12
        assert pricing["7_EPISODES"] == 18
        assert pricing["CHARACTER_BIBLE"] == 5
        
    def test_pricing_episode_bundles(self):
        """Verify episode bundles structure"""
        response = requests.get(f"{BASE_URL}/api/story-series/pricing")
        bundles = response.json()["episodeBundles"]
        
        assert len(bundles) == 3
        assert bundles[0] == {"episodes": 3, "credits": 8}
        assert bundles[1] == {"episodes": 5, "credits": 12}
        assert bundles[2] == {"episodes": 7, "credits": 18}


class TestStorySeriesThemes(TestSetup):
    """Story Series themes endpoint tests"""
    
    def test_themes_returns_200(self):
        """GET /api/story-series/themes returns 200"""
        response = requests.get(f"{BASE_URL}/api/story-series/themes")
        assert response.status_code == 200
        data = response.json()
        
        # Validate themes
        assert "themes" in data
        assert "descriptions" in data
        assert len(data["themes"]) == 5
        
        expected_themes = ["Adventure", "Friendship", "Mystery", "Fantasy", "Comedy"]
        assert all(t in data["themes"] for t in expected_themes)
        
    def test_themes_have_descriptions(self):
        """Verify all themes have descriptions"""
        response = requests.get(f"{BASE_URL}/api/story-series/themes")
        data = response.json()
        
        for theme in data["themes"]:
            assert theme in data["descriptions"]
            assert len(data["descriptions"][theme]) > 0


class TestStorySeriesGenerate(TestSetup):
    """Story Series generation endpoint tests"""
    
    def test_generate_requires_auth(self):
        """POST /api/story-series/generate requires authentication"""
        response = requests.post(f"{BASE_URL}/api/story-series/generate", json={
            "storySummary": "Test story",
            "characterNames": ["Hero"],
            "theme": "Adventure",
            "episodeCount": 3
        })
        assert response.status_code == 401
        
    def test_generate_with_valid_auth(self, auth_headers):
        """POST /api/story-series/generate with valid auth"""
        response = requests.post(f"{BASE_URL}/api/story-series/generate", json={
            "storySummary": "TEST_A brave young explorer discovers a hidden treasure map",
            "characterNames": ["Luna", "Max"],
            "targetAgeGroup": "4-7",
            "theme": "Adventure",
            "episodeCount": 3
        }, headers=auth_headers)
        
        # Should return 200 (or 402 if insufficient credits)
        assert response.status_code in [200, 402]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "seriesId" in data
            assert data["episodeCount"] == 3
            assert "episodes" in data
            assert len(data["episodes"]) == 3
            
            # Verify episode structure
            for ep in data["episodes"]:
                assert "episodeNumber" in ep
                assert "title" in ep
                assert "arcStage" in ep
                assert "sceneBeats" in ep
                assert "cliffhanger" in ep


class TestStorySeriesHistory(TestSetup):
    """Story Series history endpoint tests"""
    
    def test_history_requires_auth(self):
        """GET /api/story-series/history requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-series/history")
        assert response.status_code == 401
        
    def test_history_with_auth(self, auth_headers):
        """GET /api/story-series/history returns user's series"""
        response = requests.get(f"{BASE_URL}/api/story-series/history?limit=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "series" in data
        assert "total" in data


# =============================================================================
# CHALLENGE GENERATOR API TESTS
# =============================================================================

class TestChallengeGeneratorPricing(TestSetup):
    """Challenge Generator pricing endpoint tests"""
    
    def test_pricing_returns_200(self):
        """GET /api/challenge-generator/pricing returns 200"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/pricing")
        assert response.status_code == 200
        data = response.json()
        
        # Validate pricing structure
        assert "pricing" in data
        assert "challengeTypes" in data
        assert "addOns" in data
        
        # Validate pricing values
        pricing = data["pricing"]
        assert pricing["7_DAY"] == 6
        assert pricing["30_DAY"] == 15
        assert pricing["CAPTION_PACK"] == 3
        assert pricing["HASHTAG_BUNDLE"] == 2


class TestChallengeGeneratorNiches(TestSetup):
    """Challenge Generator niches endpoint tests"""
    
    def test_niches_returns_200(self):
        """GET /api/challenge-generator/niches returns 200"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/niches")
        assert response.status_code == 200
        data = response.json()
        
        # Validate niches
        assert "niches" in data
        assert "descriptions" in data
        
        expected_niches = ["luxury", "fitness", "kids_stories", "motivation", "business"]
        assert all(n in data["niches"] for n in expected_niches)


class TestChallengeGeneratorPlatforms(TestSetup):
    """Challenge Generator platforms endpoint tests"""
    
    def test_platforms_returns_200(self):
        """GET /api/challenge-generator/platforms returns 200"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/platforms")
        assert response.status_code == 200
        data = response.json()
        
        assert "platforms" in data
        assert "instagram" in data["platforms"]
        assert "youtube" in data["platforms"]
        assert "tiktok" in data["platforms"]


class TestChallengeGeneratorGoals(TestSetup):
    """Challenge Generator goals endpoint tests"""
    
    def test_goals_returns_200(self):
        """GET /api/challenge-generator/goals returns 200"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/goals")
        assert response.status_code == 200
        data = response.json()
        
        assert "goals" in data
        expected_goals = ["followers", "leads", "sales", "engagement"]
        assert all(g in data["goals"] for g in expected_goals)


class TestChallengeGeneratorGenerate(TestSetup):
    """Challenge Generator generation endpoint tests"""
    
    def test_generate_requires_auth(self):
        """POST /api/challenge-generator/generate requires authentication"""
        response = requests.post(f"{BASE_URL}/api/challenge-generator/generate", json={
            "challengeType": "7_day",
            "niche": "motivation",
            "platform": "instagram",
            "goal": "followers",
            "timePerDay": 10
        })
        assert response.status_code == 401
        
    def test_generate_with_valid_auth(self, auth_headers):
        """POST /api/challenge-generator/generate with valid auth"""
        response = requests.post(f"{BASE_URL}/api/challenge-generator/generate", json={
            "challengeType": "7_day",
            "niche": "motivation",
            "platform": "instagram",
            "goal": "followers",
            "timePerDay": 10
        }, headers=auth_headers)
        
        # Should return 200 (or 402 if insufficient credits)
        assert response.status_code in [200, 402]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "challengeId" in data
            assert data["days"] == 7
            assert "dailyPlans" in data
            assert len(data["dailyPlans"]) == 7
            
            # Verify daily plan structure
            for plan in data["dailyPlans"]:
                assert "day" in plan
                assert "theme" in plan
                assert "contentType" in plan
                assert "hook" in plan
                assert "callToAction" in plan
                assert "hashtags" in plan
                assert "postingTime" in plan


# =============================================================================
# TONE SWITCHER API TESTS
# =============================================================================

class TestToneSwitcherTones(TestSetup):
    """Tone Switcher tones endpoint tests"""
    
    def test_tones_returns_200(self):
        """GET /api/tone-switcher/tones returns 200"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/tones")
        assert response.status_code == 200
        data = response.json()
        
        assert "tones" in data
        expected_tones = ["funny", "aggressive", "calm", "luxury", "motivational"]
        assert all(t in data["tones"] for t in expected_tones)
        
        # Verify tone structure
        for tone_key, tone_info in data["tones"].items():
            assert "name" in tone_info
            assert "description" in tone_info
            assert "sampleEmojis" in tone_info


class TestToneSwitcherPricing(TestSetup):
    """Tone Switcher pricing endpoint tests"""
    
    def test_pricing_returns_200(self):
        """GET /api/tone-switcher/pricing returns 200"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/pricing")
        assert response.status_code == 200
        data = response.json()
        
        assert "pricing" in data
        assert "options" in data
        
        pricing = data["pricing"]
        assert pricing["SINGLE_REWRITE"] == 1
        assert pricing["BATCH_5"] == 3
        assert pricing["BATCH_10"] == 5


class TestToneSwitcherPreview(TestSetup):
    """Tone Switcher preview endpoint tests"""
    
    def test_preview_requires_auth(self):
        """POST /api/tone-switcher/preview requires authentication"""
        response = requests.post(f"{BASE_URL}/api/tone-switcher/preview", json={
            "text": "Hello world",
            "targetTone": "funny",
            "intensity": 50
        })
        assert response.status_code == 401
        
    def test_preview_with_auth(self, auth_headers):
        """POST /api/tone-switcher/preview returns preview without charging"""
        response = requests.post(f"{BASE_URL}/api/tone-switcher/preview", json={
            "text": "This is a test message for tone transformation",
            "targetTone": "funny",
            "intensity": 70,
            "keepLength": "same",
            "variationCount": 1
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "preview" in data
        assert data["isPreview"] == True
        assert "note" in data


class TestToneSwitcherRewrite(TestSetup):
    """Tone Switcher rewrite endpoint tests"""
    
    def test_rewrite_requires_auth(self):
        """POST /api/tone-switcher/rewrite requires authentication"""
        response = requests.post(f"{BASE_URL}/api/tone-switcher/rewrite", json={
            "text": "Hello world",
            "targetTone": "funny",
            "intensity": 50
        })
        assert response.status_code == 401
        
    def test_rewrite_with_valid_auth(self, auth_headers):
        """POST /api/tone-switcher/rewrite with valid auth"""
        response = requests.post(f"{BASE_URL}/api/tone-switcher/rewrite", json={
            "text": "TEST_This is important information that you should know about",
            "targetTone": "funny",
            "intensity": 50,
            "keepLength": "same",
            "variationCount": 1
        }, headers=auth_headers)
        
        # Should return 200 (or 402 if insufficient credits)
        assert response.status_code in [200, 402]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "rewriteId" in data
            assert "variations" in data
            assert len(data["variations"]) == 1
            
            # Verify variation structure
            for v in data["variations"]:
                assert "index" in v
                assert "text" in v
                assert "intensity" in v


# =============================================================================
# REGIONAL PRICING API TESTS
# =============================================================================

class TestRegionalPricingPlans(TestSetup):
    """Regional pricing plans endpoint tests"""
    
    def test_plans_returns_200(self):
        """GET /api/pricing/plans returns 200"""
        response = requests.get(f"{BASE_URL}/api/pricing/plans")
        assert response.status_code == 200
        data = response.json()
        
        assert "currency" in data
        assert "symbol" in data
        assert "plans" in data
        assert "topups" in data
        
        # Verify plan structure
        plans = data["plans"]
        assert "weekly" in plans
        assert "monthly" in plans
        assert "quarterly" in plans
        
    def test_plans_with_usd_currency(self):
        """GET /api/pricing/plans?currency=USD returns USD prices"""
        response = requests.get(f"{BASE_URL}/api/pricing/plans?currency=USD")
        assert response.status_code == 200
        data = response.json()
        
        assert data["currency"] == "USD"
        assert data["symbol"] == "$"
        assert data["plans"]["weekly"]["price"] == 4.99
        assert data["plans"]["monthly"]["price"] == 9.99
        assert data["plans"]["quarterly"]["price"] == 24.99
        
    def test_plans_with_inr_currency(self):
        """GET /api/pricing/plans?currency=INR returns INR prices"""
        response = requests.get(f"{BASE_URL}/api/pricing/plans?currency=INR")
        assert response.status_code == 200
        data = response.json()
        
        assert data["currency"] == "INR"
        assert data["symbol"] == "₹"
        assert data["plans"]["weekly"]["price"] == 99
        assert data["plans"]["monthly"]["price"] == 299
        assert data["plans"]["quarterly"]["price"] == 699


class TestRegionalPricingTopups(TestSetup):
    """Regional pricing topups endpoint tests"""
    
    def test_topups_returns_200(self):
        """GET /api/pricing/topups returns 200"""
        response = requests.get(f"{BASE_URL}/api/pricing/topups")
        assert response.status_code == 200
        data = response.json()
        
        assert "currency" in data
        assert "topups" in data
        assert len(data["topups"]) == 3


class TestRegionalPricingFeatureCosts(TestSetup):
    """Feature costs endpoint tests"""
    
    def test_feature_costs_returns_200(self):
        """GET /api/pricing/feature-costs returns 200"""
        response = requests.get(f"{BASE_URL}/api/pricing/feature-costs")
        assert response.status_code == 200
        data = response.json()
        
        assert "costs" in data
        assert "categories" in data
        
        # Verify Story Series costs
        costs = data["costs"]
        assert costs["story_series_3_episodes"] == 8
        assert costs["story_series_5_episodes"] == 12
        assert costs["story_series_7_episodes"] == 18
        
        # Verify Challenge Generator costs
        assert costs["challenge_7_day"] == 6
        assert costs["challenge_30_day"] == 15
        
        # Verify Tone Switcher costs
        assert costs["tone_single"] == 1
        assert costs["tone_batch_5"] == 3
        assert costs["tone_batch_10"] == 5
        
    def test_feature_costs_categories(self):
        """Verify all categories are present"""
        response = requests.get(f"{BASE_URL}/api/pricing/feature-costs")
        categories = response.json()["categories"]
        
        expected_categories = ["Story Series", "Challenge Generator", "Tone Switcher", "Coloring Book", "GenStudio"]
        assert all(c in categories for c in expected_categories)


# =============================================================================
# DASHBOARD APP CARDS TEST (requires auth)
# =============================================================================

class TestDashboardApps(TestSetup):
    """Dashboard apps visibility tests"""
    
    def test_auth_me_returns_user(self, auth_headers):
        """GET /api/auth/me returns user data"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "user" in data
        assert "id" in data["user"]
        assert "email" in data["user"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
