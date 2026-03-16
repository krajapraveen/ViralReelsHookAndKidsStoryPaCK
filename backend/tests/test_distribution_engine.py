"""
P0 Distribution Engine API Tests
Tests for OG meta tags, share pages, sitemap, creator profiles, and growth metrics.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSeedStatus:
    """Content seeding verification - should have 40+ seeded videos"""
    
    def test_seed_status_returns_40_plus(self):
        response = requests.get(f"{BASE_URL}/api/public/seed-status")
        assert response.status_code == 200
        data = response.json()
        assert "seeded_count" in data
        assert data["seeded_count"] >= 40, f"Expected 40+ seeded videos, got {data['seeded_count']}"


class TestExploreAPI:
    """Explore feed API - should return 134+ creations with thumbnails and metrics"""
    
    def test_explore_returns_total_count(self):
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=12")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] >= 40, f"Expected 40+ total creations, got {data['total']}"
    
    def test_explore_items_have_thumbnails(self):
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=20")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        assert len(items) > 0, "No items returned"
        
        items_with_thumbnails = [i for i in items if i.get("thumbnail_url")]
        assert len(items_with_thumbnails) > 0, "No items have thumbnails"
    
    def test_explore_items_have_engagement_metrics(self):
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=trending&limit=10")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            assert "views" in item, f"Item {item.get('job_id')} missing views"
            assert "remix_count" in item, f"Item {item.get('job_id')} missing remix_count"


class TestPublicCreation:
    """Public creation page API - should return prompt, category, tags"""
    
    @pytest.fixture(scope="class")
    def sample_slug(self):
        """Get a sample slug from explore feed"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=1")
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                return items[0].get("slug") or items[0].get("job_id")
        return None
    
    def test_public_creation_returns_prompt(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/creation/{sample_slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        creation = data.get("creation", {})
        
        # Prompt should be present (from story_text)
        prompt = creation.get("prompt")
        assert prompt is not None, "prompt field missing from response"
        assert len(prompt) > 0, "prompt field is empty"
    
    def test_public_creation_returns_category(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/creation/{sample_slug}")
        assert response.status_code == 200
        data = response.json()
        creation = data.get("creation", {})
        
        # Category should be present
        assert "category" in creation, "category field missing from response"
    
    def test_public_creation_returns_tags(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/creation/{sample_slug}")
        assert response.status_code == 200
        data = response.json()
        creation = data.get("creation", {})
        
        # Tags should be a list
        assert "tags" in creation, "tags field missing from response"
        assert isinstance(creation.get("tags"), list), "tags should be a list"


class TestSharePage:
    """Backend share page - should return HTML with OG meta tags"""
    
    @pytest.fixture(scope="class")
    def sample_slug(self):
        """Get a sample slug from explore feed"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=1")
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                return items[0].get("slug") or items[0].get("job_id")
        return None
    
    def test_share_page_returns_html(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/s/{sample_slug}")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("Content-Type", "")
    
    def test_share_page_has_og_title(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/s/{sample_slug}")
        assert response.status_code == 200
        html = response.text
        assert 'og:title' in html, "og:title meta tag missing"
    
    def test_share_page_has_og_description(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/s/{sample_slug}")
        assert response.status_code == 200
        html = response.text
        assert 'og:description' in html, "og:description meta tag missing"
    
    def test_share_page_has_og_image(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/s/{sample_slug}")
        assert response.status_code == 200
        html = response.text
        assert 'og:image' in html, "og:image meta tag missing"
    
    def test_share_page_has_redirect(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/s/{sample_slug}")
        assert response.status_code == 200
        html = response.text
        assert f'/v/{sample_slug}' in html, "Redirect to /v/{slug} missing"


class TestOGImage:
    """OG image endpoint - should return a PNG image"""
    
    @pytest.fixture(scope="class")
    def sample_slug(self):
        """Get a sample slug from explore feed"""
        response = requests.get(f"{BASE_URL}/api/public/explore?tab=newest&limit=1")
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                return items[0].get("slug") or items[0].get("job_id")
        return None
    
    def test_og_image_returns_200(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/og-image/{sample_slug}")
        assert response.status_code == 200
    
    def test_og_image_is_png(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/og-image/{sample_slug}")
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "image/png" in content_type, f"Expected image/png, got {content_type}"
    
    def test_og_image_has_content(self, sample_slug):
        if not sample_slug:
            pytest.skip("No sample slug available")
        
        response = requests.get(f"{BASE_URL}/api/public/og-image/{sample_slug}")
        assert response.status_code == 200
        # Should have reasonable image size (at least 10KB for a 1200x630 PNG)
        assert len(response.content) > 10000, f"Image too small: {len(response.content)} bytes"


class TestSitemap:
    """Sitemap endpoint - should return valid XML with creation URLs"""
    
    def test_sitemap_returns_xml(self):
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "application/xml" in content_type or "text/xml" in content_type
    
    def test_sitemap_has_urlset(self):
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200
        assert '<?xml' in response.text
        assert '<urlset' in response.text
    
    def test_sitemap_has_creation_urls(self):
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200
        # Should have /v/ creation URLs
        assert '/v/' in response.text, "No creation URLs (/v/) in sitemap"
    
    def test_sitemap_has_static_pages(self):
        response = requests.get(f"{BASE_URL}/api/public/sitemap.xml")
        assert response.status_code == 200
        assert '/explore' in response.text, "/explore missing from sitemap"


class TestCreatorProfile:
    """Creator profile endpoint - should return visionary-ai creator with 40 creations"""
    
    def test_creator_visionary_ai_exists(self):
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_creator_visionary_ai_has_40_creations(self):
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        assert response.status_code == 200
        data = response.json()
        creator = data.get("creator", {})
        assert creator.get("total_creations") >= 40, f"Expected 40+ creations, got {creator.get('total_creations')}"
    
    def test_creator_profile_has_name(self):
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        assert response.status_code == 200
        data = response.json()
        creator = data.get("creator", {})
        assert creator.get("name") == "Visionary AI", f"Expected 'Visionary AI', got {creator.get('name')}"
    
    def test_creator_profile_has_stats(self):
        response = requests.get(f"{BASE_URL}/api/public/creator/visionary-ai")
        assert response.status_code == 200
        data = response.json()
        creator = data.get("creator", {})
        assert "total_views" in creator
        assert "total_remixes" in creator


class TestGrowthMetrics:
    """Growth dashboard metrics - should return daily_creations, remix_rate, creator_activation"""
    
    def test_growth_metrics_returns_success(self):
        response = requests.get(f"{BASE_URL}/api/public/growth-metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_growth_metrics_has_daily_creations(self):
        response = requests.get(f"{BASE_URL}/api/public/growth-metrics")
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        assert "daily_creations" in metrics
        dc = metrics["daily_creations"]
        assert "today" in dc
        assert "yesterday" in dc
        assert "avg_7d" in dc
    
    def test_growth_metrics_has_remix_rate(self):
        response = requests.get(f"{BASE_URL}/api/public/growth-metrics")
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        assert "remix_rate" in metrics
        assert isinstance(metrics["remix_rate"], (int, float))
    
    def test_growth_metrics_has_creator_activation(self):
        response = requests.get(f"{BASE_URL}/api/public/growth-metrics")
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        assert "creator_activation" in metrics
        ca = metrics["creator_activation"]
        assert "total_users" in ca
        assert "active_creators" in ca
        assert "rate" in ca
    
    def test_growth_metrics_has_total_creations(self):
        response = requests.get(f"{BASE_URL}/api/public/growth-metrics")
        assert response.status_code == 200
        data = response.json()
        metrics = data.get("metrics", {})
        assert "total_creations" in metrics
        assert metrics["total_creations"] >= 40
