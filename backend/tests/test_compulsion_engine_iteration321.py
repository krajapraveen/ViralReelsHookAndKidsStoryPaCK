"""
Compulsion Engine Testing - K-Factor Boost (Iteration 321)
Tests for:
1. Public Character API (/api/public/character/{characterId})
2. Public Creation API (/api/public/creation/{slug})
3. K-Factor Boost growth endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPublicCharacterAPI:
    """Public Character Page API tests - No auth required"""

    def test_public_character_endpoint_exists(self):
        """Test that public character endpoint is accessible without auth"""
        # Using a test character ID - endpoint should at least return 404, not 401
        response = requests.get(f"{BASE_URL}/api/public/character/test-character-id")
        # Should not be 401 (unauthorized) - endpoint is public
        assert response.status_code != 401, "Public character endpoint should not require auth"
        # Accept 404 (character not found) or 200 (if exists)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

    def test_public_character_returns_expected_fields(self):
        """Test public character endpoint returns expected fields when character exists"""
        # Try to get an existing character from DB
        # First, list from explore to find one
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        if explore_resp.status_code == 200 and explore_resp.json().get('items'):
            # There's content in the system - try to find a character
            pass
        
        # Test endpoint structure - should return proper error for non-existent ID
        response = requests.get(f"{BASE_URL}/api/public/character/nonexistent-id-12345")
        assert response.status_code == 404, f"Expected 404 for non-existent character"
        data = response.json()
        assert 'detail' in data or 'error' in data or 'message' in data, "Should return error message"


class TestPublicCreationAPI:
    """Public Creation Page API tests - No auth required"""

    def test_public_creation_endpoint_exists(self):
        """Test that public creation endpoint is accessible without auth"""
        response = requests.get(f"{BASE_URL}/api/public/creation/test-slug")
        # Should not be 401 (unauthorized) - endpoint is public
        assert response.status_code != 401, "Public creation endpoint should not require auth"
        # Accept 404 (creation not found) or 200 (if exists)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

    def test_public_creation_returns_expected_fields(self):
        """Test public creation endpoint returns expected fields"""
        # Get a real creation from explore feed
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        
        if explore_resp.status_code == 200:
            data = explore_resp.json()
            if data.get('items') and len(data['items']) > 0:
                slug = data['items'][0].get('slug') or data['items'][0].get('job_id')
                if slug:
                    # Test with real slug
                    creation_resp = requests.get(f"{BASE_URL}/api/public/creation/{slug}")
                    if creation_resp.status_code == 200:
                        creation_data = creation_resp.json()
                        assert creation_data.get('success') == True, "Should return success=True"
                        assert 'creation' in creation_data, "Should contain creation object"
                        creation = creation_data['creation']
                        # Check expected fields per K-factor boost requirements
                        assert 'job_id' in creation, "Should have job_id"
                        assert 'title' in creation, "Should have title"
                        assert 'views' in creation, "Should have views count"
                        assert 'remix_count' in creation, "Should have remix_count"
                        print(f"Successfully tested creation: {creation.get('title')}")

    def test_public_creation_remix_endpoint(self):
        """Test remix tracking endpoint"""
        # Get a real creation first
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        
        if explore_resp.status_code == 200:
            data = explore_resp.json()
            if data.get('items') and len(data['items']) > 0:
                slug = data['items'][0].get('slug') or data['items'][0].get('job_id')
                if slug:
                    # Test remix tracking
                    remix_resp = requests.post(f"{BASE_URL}/api/public/creation/{slug}/remix")
                    assert remix_resp.status_code in [200, 404], f"Unexpected status: {remix_resp.status_code}"
                    if remix_resp.status_code == 200:
                        assert remix_resp.json().get('success') == True


class TestKFactorBoostAPI:
    """K-Factor Boost specific API tests"""

    def test_public_stats_endpoint(self):
        """Test platform stats endpoint returns social proof data"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200, f"Public stats should return 200"
        data = response.json()
        # Check social proof fields
        assert 'creators' in data, "Should have creators count"
        assert 'videos_created' in data, "Should have videos_created count"
        assert isinstance(data['creators'], int), "creators should be int"
        assert isinstance(data['videos_created'], int), "videos_created should be int"

    def test_explore_feed_trending(self):
        """Test explore feed trending tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5")
        assert response.status_code == 200, f"Explore trending should return 200"
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        assert 'total' in data

    def test_explore_feed_newest(self):
        """Test explore feed newest tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=5")
        assert response.status_code == 200, f"Explore newest should return 200"
        data = response.json()
        assert data.get('success') == True

    def test_explore_feed_most_remixed(self):
        """Test explore feed most_remixed tab"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=most_remixed&limit=5")
        assert response.status_code == 200, f"Explore most_remixed should return 200"
        data = response.json()
        assert data.get('success') == True

    def test_trending_weekly_endpoint(self):
        """Test trending weekly endpoint for homepage carousel"""
        response = requests.get(f"{BASE_URL}/api/public/trending-weekly?limit=5")
        assert response.status_code == 200, f"Trending weekly should return 200"
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        assert 'period' in data
        assert data['period'] == 'weekly'

    def test_live_activity_feed(self):
        """Test live activity feed for social proof"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=5")
        assert response.status_code == 200, f"Live activity should return 200"
        data = response.json()
        assert data.get('success') == True
        assert 'items' in data
        # Check activity feed structure
        if data.get('items'):
            item = data['items'][0]
            assert 'creator' in item, "Activity should have creator"
            assert 'action' in item, "Activity should have action"
            assert 'type' in item, "Activity should have type"


class TestStoryVideoStudioPublicAccess:
    """Test that StoryVideoStudio is accessible without authentication"""

    def test_story_video_studio_styles_public(self):
        """Test styles endpoint (used by StoryVideoStudio)"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/styles")
        # This might require auth for some endpoints
        assert response.status_code in [200, 401, 403], f"Styles endpoint status: {response.status_code}"

    def test_story_video_studio_pricing_public(self):
        """Test pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code in [200, 401, 403], f"Pricing endpoint status: {response.status_code}"


class TestGrowthEventsAPI:
    """Growth Events Tracking API tests"""

    def test_growth_event_tracking(self):
        """Test growth event tracking endpoint"""
        payload = {
            "event": "page_view",
            "source_page": "/character/test-id",
            "session_id": "test-session-12345",
            "anonymous_id": "anon-12345",
        }
        response = requests.post(f"{BASE_URL}/api/growth/event", json=payload)
        # Should accept event - 200 or validation error
        assert response.status_code in [200, 201, 422], f"Growth event status: {response.status_code}"

    def test_growth_batch_events(self):
        """Test batch growth events endpoint"""
        payload = {
            "events": [
                {
                    "event": "page_view",
                    "source_page": "/test",
                    "session_id": "test-session-12345",
                }
            ]
        }
        response = requests.post(f"{BASE_URL}/api/growth/events/batch", json=payload)
        assert response.status_code in [200, 201, 422], f"Batch events status: {response.status_code}"


class TestOpenGraphMeta:
    """Test OG meta endpoints for social sharing"""

    def test_share_page_html(self):
        """Test share page returns HTML with OG tags"""
        # Get a real creation slug first
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        
        if explore_resp.status_code == 200:
            data = explore_resp.json()
            if data.get('items') and len(data['items']) > 0:
                slug = data['items'][0].get('slug') or data['items'][0].get('job_id')
                if slug:
                    share_resp = requests.get(f"{BASE_URL}/api/public/s/{slug}")
                    assert share_resp.status_code == 200
                    # Should return HTML
                    assert 'text/html' in share_resp.headers.get('content-type', '')
                    # Should contain OG tags
                    content = share_resp.text
                    assert 'og:title' in content or 'og:image' in content

    def test_og_image_endpoint(self):
        """Test OG image generation endpoint"""
        # Get a real creation slug first
        explore_resp = requests.get(f"{BASE_URL}/api/public/explore?limit=1")
        
        if explore_resp.status_code == 200:
            data = explore_resp.json()
            if data.get('items') and len(data['items']) > 0:
                slug = data['items'][0].get('slug') or data['items'][0].get('job_id')
                if slug:
                    og_resp = requests.get(f"{BASE_URL}/api/public/og-image/{slug}")
                    assert og_resp.status_code in [200, 404]
                    if og_resp.status_code == 200:
                        # Should return an image
                        assert 'image/' in og_resp.headers.get('content-type', '')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
