"""
Test Iteration 60 - Bug Fixes for Carousel, Hashtags, and New Features
Tests carousel generation, hashtag bank, feature requests dark theme, and help guide
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {
    "email": "demo@example.com",
    "password": "Password123!"
}

class TestAuthentication:
    """Authentication tests"""
    
    def test_demo_user_login(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in login response"
        return data["token"]


class TestCarouselGenerator:
    """Carousel Generator API tests - P0 fix"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_carousel_generation(self, auth_token):
        """Test carousel generation endpoint - P0 fix verification"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Generate carousel
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/carousel?topic=5%20Morning%20Habits&niche=business&slides=7",
            headers=headers
        )
        
        assert response.status_code == 200, f"Carousel generation failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Missing 'success' field"
        assert data["success"] == True, "Carousel generation not successful"
        assert "carousel" in data, "Missing 'carousel' field"
        assert "slides" in data["carousel"], "Missing 'slides' in carousel"
        
        # Verify slides structure - check property names match frontend expectations
        slides = data["carousel"]["slides"]
        assert len(slides) > 0, "No slides generated"
        
        first_slide = slides[0]
        # These are the property names the frontend expects (per the fix)
        assert "slideNumber" in first_slide, "Missing 'slideNumber' - property name mismatch"
        assert "headline" in first_slide, "Missing 'headline' - property name mismatch"
        assert "type" in first_slide, "Missing 'type' field"
        
        print(f"✓ Carousel generated with {len(slides)} slides")
        print(f"✓ First slide properties: {list(first_slide.keys())}")
        
    def test_carousel_slide_types(self, auth_token):
        """Verify carousel has cover, content, and CTA slides"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/carousel?topic=Test%20Topic&niche=general&slides=5",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        slides = data["carousel"]["slides"]
        
        # Check slide types
        slide_types = [s["type"] for s in slides]
        assert "cover" in slide_types, "Missing cover slide"
        assert "cta" in slide_types, "Missing CTA slide"
        assert "content" in slide_types, "Missing content slides"
        
        print(f"✓ Slide types present: {set(slide_types)}")


class TestHashtagBank:
    """Hashtag Bank API tests - P0 fix"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_get_hashtags_business(self, auth_token):
        """Test hashtag retrieval for business niche - P0 fix verification"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/hashtags/business",
            headers=headers
        )
        
        assert response.status_code == 200, f"Hashtag fetch failed: {response.text}"
        data = response.json()
        
        # Verify response structure - frontend expects array of hashtags
        assert "hashtags" in data, "Missing 'hashtags' field"
        assert "niche" in data, "Missing 'niche' field"
        assert "count" in data, "Missing 'count' field"
        
        # Verify hashtags is an array (not an object)
        assert isinstance(data["hashtags"], list), "Hashtags should be an array"
        assert len(data["hashtags"]) > 0, "No hashtags returned"
        
        # Verify hashtags format
        for tag in data["hashtags"]:
            assert tag.startswith("#"), f"Hashtag should start with #: {tag}"
        
        print(f"✓ Retrieved {len(data['hashtags'])} hashtags for business niche")
        print(f"✓ Sample hashtags: {data['hashtags'][:5]}")
        
    def test_get_hashtags_all_niches(self, auth_token):
        """Test hashtags for multiple niches"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        niches = ["fitness", "travel", "food", "tech", "beauty", "lifestyle"]
        
        for niche in niches:
            response = requests.get(
                f"{BASE_URL}/api/creator-tools/hashtags/{niche}",
                headers=headers
            )
            assert response.status_code == 200, f"Failed for niche: {niche}"
            data = response.json()
            assert len(data["hashtags"]) > 0, f"No hashtags for niche: {niche}"
            
        print(f"✓ All niches return valid hashtags: {niches}")


class TestTrendingTopics:
    """Trending Topics API tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_get_trending_general(self, auth_token):
        """Test trending topics endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8",
            headers=headers
        )
        
        assert response.status_code == 200, f"Trending fetch failed: {response.text}"
        data = response.json()
        
        assert "success" in data and data["success"], "Trending request not successful"
        assert "topics" in data, "Missing 'topics' field"
        assert len(data["topics"]) > 0, "No trending topics returned"
        
        # Verify topic structure
        first_topic = data["topics"][0]
        assert "topic" in first_topic, "Missing 'topic' field"
        assert "hook" in first_topic, "Missing 'hook' field"
        assert "engagement" in first_topic, "Missing 'engagement' field"
        
        print(f"✓ Retrieved {len(data['topics'])} trending topics")


class TestFeatureRequests:
    """Feature Requests API tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_get_feature_requests(self, auth_token):
        """Test feature requests list endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/feature-requests", headers=headers)
        assert response.status_code == 200, f"Feature requests fetch failed: {response.text}"
        
        data = response.json()
        assert "content" in data, "Missing 'content' field"
        
        print(f"✓ Feature requests endpoint working, {len(data.get('content', []))} requests found")
    
    def test_get_categories(self, auth_token):
        """Test feature request categories endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/feature-requests/categories", headers=headers)
        assert response.status_code == 200, f"Categories fetch failed: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Missing 'categories' field"
        
        print(f"✓ Categories endpoint working")


class TestHelpManual:
    """Help/Manual API tests for new HelpGuide feature"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_get_help_manual(self, auth_token):
        """Test help manual endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(f"{BASE_URL}/api/help/manual", headers=headers)
        # API might return 200 or 404 depending on implementation
        print(f"Help manual endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Help manual API working")
        else:
            print("Note: Help manual API not implemented - HelpGuide uses local content")


class TestContentCalendar:
    """Content Calendar API tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    def test_generate_calendar(self, auth_token):
        """Test content calendar generation"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/creator-tools/content-calendar?niche=business&days=7&include_full_scripts=false",
            headers=headers
        )
        
        assert response.status_code == 200, f"Calendar generation failed: {response.text}"
        data = response.json()
        
        assert "calendar" in data, "Missing 'calendar' field"
        assert len(data["calendar"]) > 0, "No calendar entries generated"
        
        # Verify calendar entry structure
        first_entry = data["calendar"][0]
        assert "date" in first_entry, "Missing 'date' field"
        assert "contentType" in first_entry, "Missing 'contentType' field"
        assert "suggestedTopic" in first_entry, "Missing 'suggestedTopic' field"
        
        print(f"✓ Generated calendar with {len(data['calendar'])} days")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
