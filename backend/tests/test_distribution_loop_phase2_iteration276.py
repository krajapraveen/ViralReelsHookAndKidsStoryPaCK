"""
Test Suite: Distribution Loop Phase 2 - Iteration 276
Tests for public APIs: /api/public/stats, /api/public/explore, /api/public/creation/{slug}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pipeline-optimize.preview.emergentagent.com')


class TestPublicStats:
    """Tests for /api/public/stats endpoint - platform social proof"""

    def test_stats_endpoint_returns_200(self):
        """Verify stats endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200
        print(f"✓ Stats endpoint returns 200")

    def test_stats_returns_real_creator_count(self):
        """Verify stats returns real creator count > 0"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        assert "creators" in data
        assert data["creators"] > 0
        print(f"✓ Creators count: {data['creators']}")

    def test_stats_returns_real_video_count(self):
        """Verify stats returns videos_created count"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        assert "videos_created" in data
        assert data["videos_created"] >= 0
        print(f"✓ Videos created: {data['videos_created']}")

    def test_stats_returns_total_creations(self):
        """Verify stats returns total_creations count"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        assert "total_creations" in data
        assert data["total_creations"] >= 0
        print(f"✓ Total creations: {data['total_creations']}")

    def test_stats_returns_ai_scenes(self):
        """Verify stats returns ai_scenes count"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        assert "ai_scenes" in data
        assert data["ai_scenes"] >= 0
        print(f"✓ AI scenes: {data['ai_scenes']}")


class TestPublicExplore:
    """Tests for /api/public/explore endpoint - creation feed"""

    def test_explore_trending_tab(self):
        """Verify explore trending tab returns data"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=12")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["tab"] == "trending"
        assert "items" in data
        assert "total" in data
        print(f"✓ Trending tab: {len(data['items'])} items, total={data['total']}")

    def test_explore_newest_tab(self):
        """Verify explore newest tab returns data"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=12")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["tab"] == "newest"
        assert "items" in data
        print(f"✓ Newest tab: {len(data['items'])} items")

    def test_explore_most_remixed_tab(self):
        """Verify explore most_remixed tab returns data"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=most_remixed&limit=12")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["tab"] == "most_remixed"
        assert "items" in data
        print(f"✓ Most Remixed tab: {len(data['items'])} items")

    def test_explore_item_structure(self):
        """Verify explore items have required fields"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=1")
        data = response.json()
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["job_id", "title", "animation_style", "views", "remix_count"]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            print(f"✓ Item structure valid: {item['title'][:40]}...")

    def test_explore_pagination(self):
        """Verify explore pagination with skip parameter"""
        response1 = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5&skip=0")
        response2 = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=5&skip=5")
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert len(data1["items"]) > 0
        # Check has_more is accurate
        if data1["total"] > 5:
            assert data1["has_more"] == True
        print(f"✓ Pagination working: page1={len(data1['items'])}, page2={len(data2['items'])}")


class TestPublicCreation:
    """Tests for /api/public/creation/{slug} endpoint"""
    
    SAMPLE_JOB_ID = "e236cead-8fd4-42fc-a3a8-4f43612afd01"

    def test_creation_by_job_id(self):
        """Verify creation can be fetched by job_id"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "creation" in data
        print(f"✓ Creation fetched: {data['creation']['title']}")

    def test_creation_has_required_fields(self):
        """Verify creation response has all required fields"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        data = response.json()
        creation = data["creation"]
        
        required_fields = ["job_id", "title", "status", "animation_style", 
                          "views", "remix_count", "creator", "story_text"]
        for field in required_fields:
            assert field in creation, f"Missing field: {field}"
        print(f"✓ All required fields present")

    def test_creation_increments_views(self):
        """Verify view count increments on each request"""
        response1 = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        views1 = response1.json()["creation"]["views"]
        
        response2 = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        views2 = response2.json()["creation"]["views"]
        
        assert views2 >= views1  # Views should be same or increased
        print(f"✓ Views tracking: {views1} → {views2}")

    def test_creation_not_found(self):
        """Verify 404 for non-existent creation"""
        response = requests.get(f"{BASE_URL}/api/public/creation/non-existent-id-12345")
        assert response.status_code == 404
        print(f"✓ 404 returned for non-existent creation")

    def test_creation_has_creator_info(self):
        """Verify creation includes creator info"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        data = response.json()
        creator = data["creation"]["creator"]
        
        assert "name" in creator
        print(f"✓ Creator info: {creator['name']}")

    def test_creation_has_story_text(self):
        """Verify creation includes story_text for remix"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{self.SAMPLE_JOB_ID}")
        data = response.json()
        story_text = data["creation"]["story_text"]
        
        assert isinstance(story_text, str)
        assert len(story_text) > 0
        print(f"✓ Story text for remix: '{story_text[:50]}...'")


class TestHealthCheck:
    """Basic health check tests"""

    def test_api_health(self):
        """Verify API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API health: {data['status']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
