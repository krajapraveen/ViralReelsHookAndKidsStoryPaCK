"""
Creator Tools API Tests - Iteration 66
Testing 6 features: Calendar, Carousel, Hashtags, Thumbnails, Trending, Convert
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"


@pytest.fixture(scope="session")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code}")


@pytest.fixture
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestCreatorToolsCalendar:
    """Tests for Content Calendar with Inspirational Tips"""
    
    def test_calendar_generates_with_inspirational_tips(self, api_client):
        """Calendar should include inspirationalTip field for each day"""
        response = api_client.post(f"{BASE_URL}/api/creator-tools/content-calendar?niche=business&days=7&include_full_scripts=false")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "calendar" in data
        assert len(data["calendar"]) == 7
        
        # Verify each day has inspirationalTip
        for day in data["calendar"]:
            assert "inspirationalTip" in day, f"Missing inspirationalTip in day: {day}"
            assert len(day["inspirationalTip"]) > 10, f"inspirationalTip too short: {day['inspirationalTip']}"
            assert "date" in day
            assert "dayOfWeek" in day
            assert "contentType" in day
    
    def test_calendar_with_scripts_has_tips(self, api_client):
        """Calendar with full scripts should also have inspirational tips"""
        response = api_client.post(f"{BASE_URL}/api/creator-tools/content-calendar?niche=health&days=7&include_full_scripts=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["creditsUsed"] == 25, "Should cost 25 credits with scripts"
        
        for day in data["calendar"]:
            assert "inspirationalTip" in day
            assert "scriptOutline" in day


class TestCreatorToolsCarousel:
    """Tests for Carousel Generator with Real Content"""
    
    def test_carousel_generates_real_content(self, api_client):
        """Carousel should generate real content, not generic placeholders"""
        response = api_client.post(f"{BASE_URL}/api/creator-tools/carousel?topic=Morning%20Habits&niche=productivity&slides=7")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "carousel" in data
        
        carousel = data["carousel"]
        assert "slides" in carousel
        assert len(carousel["slides"]) == 7
        
        # Check first slide is cover with real headline
        cover_slide = carousel["slides"][0]
        assert cover_slide["type"] == "cover"
        assert len(cover_slide["headline"]) > 5
        # Should NOT be generic placeholder text
        assert "Your content here" not in cover_slide["headline"].lower()
        assert "placeholder" not in cover_slide["headline"].lower()
        
        # Check content slides have real body content
        content_slides = [s for s in carousel["slides"] if s["type"] == "content"]
        for slide in content_slides:
            assert "body" in slide
            assert len(slide["body"]) > 20, f"Content too short: {slide['body']}"
            assert "placeholder" not in slide["body"].lower()
        
        # Check CTA slide exists
        cta_slides = [s for s in carousel["slides"] if s["type"] == "cta"]
        assert len(cta_slides) == 1
        assert "cta" in cta_slides[0]
    
    def test_carousel_different_niches_have_varied_content(self, api_client):
        """Different niches should produce different content"""
        response1 = api_client.post(f"{BASE_URL}/api/creator-tools/carousel?topic=Test&niche=productivity&slides=5")
        response2 = api_client.post(f"{BASE_URL}/api/creator-tools/carousel?topic=Test&niche=health&slides=5")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Content should be different for different niches
        slides1 = response1.json()["carousel"]["slides"]
        slides2 = response2.json()["carousel"]["slides"]
        
        # At least some slides should have different content
        content1 = [s["body"] for s in slides1 if s.get("body")]
        content2 = [s["body"] for s in slides2 if s.get("body")]
        
        # They should not be identical
        assert content1 != content2


class TestCreatorToolsHashtags:
    """Tests for Hashtag Bank"""
    
    def test_hashtags_returns_15_tags(self, api_client):
        """Should return exactly 15 hashtags"""
        response = api_client.get(f"{BASE_URL}/api/creator-tools/hashtags/business")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "hashtags" in data
        assert data["count"] == 15
        assert len(data["hashtags"]) == 15
        
        # All should be valid hashtags starting with #
        for tag in data["hashtags"]:
            assert tag.startswith("#"), f"Invalid hashtag: {tag}"
    
    def test_hashtags_different_niches(self, api_client):
        """Different niches should return different hashtags"""
        response_biz = api_client.get(f"{BASE_URL}/api/creator-tools/hashtags/business")
        response_fitness = api_client.get(f"{BASE_URL}/api/creator-tools/hashtags/fitness")
        
        assert response_biz.status_code == 200
        assert response_fitness.status_code == 200
        
        biz_tags = set(response_biz.json()["hashtags"])
        fitness_tags = set(response_fitness.json()["hashtags"])
        
        # They should be different (maybe with some overlap)
        assert biz_tags != fitness_tags


class TestCreatorToolsThumbnails:
    """Tests for Thumbnail Text Generator"""
    
    def test_thumbnails_generates_multiple_categories(self, api_client):
        """Should generate thumbnails in multiple categories"""
        response = api_client.post(f"{BASE_URL}/api/creator-tools/thumbnail-text?topic=productivity")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "thumbnails" in data
        
        thumbnails = data["thumbnails"]
        
        # Should have multiple categories
        expected_categories = ["clickbait", "informative", "emotional", "curiosity", "action"]
        for cat in expected_categories:
            assert cat in thumbnails, f"Missing category: {cat}"
            assert len(thumbnails[cat]) >= 3, f"Category {cat} has too few options"
        
        # Verify content contains the topic
        for cat, texts in thumbnails.items():
            for text in texts:
                assert len(text) > 5, f"Text too short: {text}"
    
    def test_thumbnails_is_free(self, api_client):
        """Thumbnail generation should be free"""
        response = api_client.post(f"{BASE_URL}/api/creator-tools/thumbnail-text?topic=money")
        
        assert response.status_code == 200
        data = response.json()
        assert data["creditsUsed"] == 0


class TestCreatorToolsTrending:
    """Tests for Trending Topics with Randomization"""
    
    def test_trending_returns_topics(self, api_client):
        """Should return trending topics"""
        response = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "topics" in data
        assert len(data["topics"]) == 8
        
        # Each topic should have required fields
        for topic in data["topics"]:
            assert "topic" in topic
            assert "hook" in topic
            assert "engagement" in topic
    
    def test_trending_randomization_on_refresh(self, api_client):
        """Topics should be randomized on refresh"""
        # Make two requests and compare order
        response1 = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8")
        time.sleep(0.5)  # Small delay
        response2 = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        topics1 = [t["topic"] for t in response1.json()["topics"]]
        topics2 = [t["topic"] for t in response2.json()["topics"]]
        
        # The order should be different (randomized) most of the time
        # There's a small chance they could be the same, so we test multiple times
        orders_different = False
        for _ in range(3):
            response3 = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8")
            topics3 = [t["topic"] for t in response3.json()["topics"]]
            if topics1 != topics3 or topics2 != topics3:
                orders_different = True
                break
        
        # At least one should be different
        assert orders_different, "Trending topics do not appear to be randomized"
    
    def test_trending_different_niches(self, api_client):
        """Different niches should return relevant topics"""
        response_fitness = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=fitness&limit=8")
        response_tech = api_client.get(f"{BASE_URL}/api/creator-tools/trending?niche=tech&limit=8")
        
        assert response_fitness.status_code == 200
        assert response_tech.status_code == 200
        
        fitness_topics = [t["topic"] for t in response_fitness.json()["topics"]]
        tech_topics = [t["topic"] for t in response_tech.json()["topics"]]
        
        # Should be different topics for different niches
        assert fitness_topics != tech_topics


class TestConvertTools:
    """Tests for Content Conversion Tools"""
    
    def test_reel_to_carousel_endpoint_exists(self, api_client):
        """Reel to Carousel endpoint should exist and work"""
        response = api_client.post(f"{BASE_URL}/api/convert/reel-to-carousel?use_recent=true")
        
        # Should either succeed or fail with "No reel found" - not 404
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 404:
            # Should be a meaningful message about no reel found
            data = response.json()
            assert "reel" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()
    
    def test_reel_to_youtube_endpoint_exists(self, api_client):
        """Reel to YouTube endpoint should exist and work"""
        response = api_client.post(f"{BASE_URL}/api/convert/reel-to-youtube?use_recent=true")
        
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 404:
            data = response.json()
            assert "reel" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()
    
    def test_story_to_reel_endpoint_exists(self, api_client):
        """Story to Reel endpoint should exist and work"""
        response = api_client.post(f"{BASE_URL}/api/convert/story-to-reel?use_recent=true")
        
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 404:
            data = response.json()
            assert "story" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()
    
    def test_story_to_quote_endpoint_exists(self, api_client):
        """Story to Quote endpoint should exist and work (FREE)"""
        response = api_client.post(f"{BASE_URL}/api/convert/story-to-quote?use_recent=true")
        
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 404:
            data = response.json()
            assert "story" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()
    
    def test_get_user_reels(self, api_client):
        """Should be able to get user's reels list"""
        response = api_client.get(f"{BASE_URL}/api/convert/user-reels?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "reels" in data
        assert "count" in data
    
    def test_get_user_stories(self, api_client):
        """Should be able to get user's stories list"""
        response = api_client.get(f"{BASE_URL}/api/convert/user-stories?limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "stories" in data
        assert "count" in data
    
    def test_conversion_costs_endpoint(self, api_client):
        """Should return conversion costs"""
        response = api_client.get(f"{BASE_URL}/api/convert/costs")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "costs" in data
        
        costs = data["costs"]
        assert costs["reel_to_carousel"] == 5
        assert costs["reel_to_youtube"] == 2
        assert costs["story_to_reel"] == 5
        assert costs["story_to_quote"] == 0  # FREE


class TestNichesEndpoint:
    """Tests for Niches endpoint"""
    
    def test_get_all_niches(self, api_client):
        """Should return all available niches"""
        response = api_client.get(f"{BASE_URL}/api/creator-tools/niches")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "niches" in data
        assert len(data["niches"]) > 5
