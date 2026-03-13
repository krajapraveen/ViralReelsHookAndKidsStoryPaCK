"""
Test Phase 6-10 Features - Iteration 158
Tests: Gallery categories, sorting, leaderboard, OG meta tags, Performance monitoring

Categories:
1. Gallery Endpoints - categories, leaderboard, filtered queries
2. Performance Monitoring - queue, render_stats, failure_rate, workers
3. OpenGraph meta tags for social sharing
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = {"email": "test@visionary-suite.com", "password": "Test@2026#"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


@pytest.fixture(scope="module")
def api_session():
    """Create a reusable session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_session):
    """Get admin authentication token"""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code}")


@pytest.fixture(scope="module")
def test_user_token(api_session):
    """Get test user authentication token"""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json=TEST_USER)
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user login failed: {response.status_code}")


# ==================== Gallery Categories Endpoint ====================

class TestGalleryCategories:
    """Test GET /api/pipeline/gallery/categories - returns categories with counts"""
    
    def test_categories_endpoint_returns_success(self, api_session):
        """Categories endpoint should return 200 and categories list"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
    
    def test_categories_has_all_category(self, api_session):
        """Categories should include 'All' category with total count"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        data = response.json()
        
        categories = data.get("categories", [])
        all_cat = next((c for c in categories if c.get("id") == "all"), None)
        
        assert all_cat is not None, "Should have 'All' category"
        assert all_cat.get("name") == "All", "All category should have name 'All'"
        assert "count" in all_cat, "All category should have count"
    
    def test_categories_have_required_fields(self, api_session):
        """Each category should have id, name, and count"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        data = response.json()
        
        for cat in data.get("categories", []):
            assert "id" in cat, f"Category missing 'id': {cat}"
            assert "name" in cat, f"Category missing 'name': {cat}"
            assert "count" in cat, f"Category missing 'count': {cat}"
            print(f"  Category: {cat['name']} ({cat['count']} videos)")


# ==================== Gallery Leaderboard Endpoint ====================

class TestGalleryLeaderboard:
    """Test GET /api/pipeline/gallery/leaderboard - returns most remixed videos"""
    
    def test_leaderboard_endpoint_returns_success(self, api_session):
        """Leaderboard endpoint should return 200"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "leaderboard" in data, "Response should have 'leaderboard' key"
    
    def test_leaderboard_items_have_required_fields(self, api_session):
        """Leaderboard items should have remix_count and other fields"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/leaderboard")
        data = response.json()
        
        leaderboard = data.get("leaderboard", [])
        print(f"  Leaderboard has {len(leaderboard)} entries")
        
        # If there are items, verify fields
        for i, item in enumerate(leaderboard[:3]):
            assert "job_id" in item, f"Item {i} missing job_id"
            assert "remix_count" in item, f"Item {i} missing remix_count"
            print(f"  #{i+1}: {item.get('title', 'Untitled')} - {item.get('remix_count')} remixes")


# ==================== Gallery Filtered/Sorted Query ====================

class TestGalleryFiltering:
    """Test GET /api/pipeline/gallery with filters and sorting"""
    
    def test_gallery_default_returns_videos(self, api_session):
        """Gallery without filters should return videos"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        assert "videos" in data, "Should have 'videos' key"
        print(f"  Default gallery returned {len(data.get('videos', []))} videos")
    
    def test_gallery_sort_newest(self, api_session):
        """Gallery with sort=newest should work"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        print(f"  Sort=newest returned {len(videos)} videos")
    
    def test_gallery_sort_most_remixed(self, api_session):
        """Gallery with sort=most_remixed should work"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        assert response.status_code == 200
        
        data = response.json()
        videos = data.get("videos", [])
        print(f"  Sort=most_remixed returned {len(videos)} videos")
    
    def test_gallery_sort_trending(self, api_session):
        """Gallery with sort=trending should work"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery?sort=trending")
        assert response.status_code == 200
        
        data = response.json()
        print(f"  Sort=trending returned {len(data.get('videos', []))} videos")
    
    def test_gallery_category_filter(self, api_session):
        """Gallery with category filter should work"""
        # First get available categories
        cat_response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        categories = cat_response.json().get("categories", [])
        
        # Test with a non-'all' category if available
        test_cat = None
        for c in categories:
            if c.get("id") != "all" and c.get("count", 0) > 0:
                test_cat = c.get("id")
                break
        
        if test_cat:
            response = api_session.get(f"{BASE_URL}/api/pipeline/gallery?category={test_cat}")
            assert response.status_code == 200
            print(f"  Category filter '{test_cat}' returned {len(response.json().get('videos', []))} videos")
        else:
            print("  No category with videos to test filter")
    
    def test_gallery_combined_sort_and_category(self, api_session):
        """Gallery with both sort and category should work"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed&category=cartoon_2d")
        assert response.status_code == 200
        print(f"  Combined filter returned {len(response.json().get('videos', []))} videos")


# ==================== OpenGraph Meta Tags Endpoint ====================

class TestOpenGraphMetaTags:
    """Test GET /api/pipeline/gallery/{job_id}/og returns HTML with OG tags"""
    
    def test_og_endpoint_404_for_invalid_id(self, api_session):
        """OG endpoint should return 404 for non-existent job"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/invalid-job-id-12345/og")
        assert response.status_code == 404, f"Expected 404 for invalid job, got {response.status_code}"
    
    def test_og_endpoint_returns_html_for_valid_video(self, api_session):
        """OG endpoint should return HTML with meta tags for valid video"""
        # First get a valid video from gallery
        gallery_response = api_session.get(f"{BASE_URL}/api/pipeline/gallery")
        videos = gallery_response.json().get("videos", [])
        
        if not videos:
            pytest.skip("No videos in gallery to test OG endpoint")
        
        job_id = videos[0].get("job_id")
        response = api_session.get(f"{BASE_URL}/api/pipeline/gallery/{job_id}/og")
        
        assert response.status_code == 200, f"OG endpoint returned {response.status_code}"
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, f"Expected HTML, got {content_type}"
        
        html = response.text
        # Check for essential OG tags
        assert "og:title" in html, "HTML should have og:title"
        assert "og:video" in html, "HTML should have og:video"
        assert "og:type" in html, "HTML should have og:type"
        assert "twitter:card" in html, "HTML should have twitter:card"
        print(f"  OG endpoint for job {job_id} returns valid HTML with meta tags")


# ==================== Performance Monitoring Endpoint ====================

class TestPerformanceMonitoring:
    """Test GET /api/pipeline/performance (admin only)"""
    
    def test_performance_requires_auth(self, api_session):
        """Performance endpoint should require authentication"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/performance")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_performance_requires_admin(self, api_session, test_user_token):
        """Performance endpoint should require admin role"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_performance_returns_data_for_admin(self, api_session, admin_token):
        """Performance endpoint should return metrics for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        
        # Check required fields
        assert "queue" in data, "Should have queue stats"
        assert "render_stats" in data, "Should have render_stats"
        assert "failure_rate" in data, "Should have failure_rate"
        assert "workers" in data, "Should have workers"
        assert "timestamp" in data, "Should have timestamp"
        
        print(f"  Performance data:")
        print(f"    Queue: {data.get('queue')}")
        print(f"    Failure rate: {data.get('failure_rate')}%")
        print(f"    Workers: {data.get('workers')}")
    
    def test_performance_queue_has_required_fields(self, api_session, admin_token):
        """Queue stats should have queued and processing counts"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        
        data = response.json()
        queue = data.get("queue", {})
        
        assert "queued" in queue, "Queue should have 'queued' count"
        assert "processing" in queue, "Queue should have 'processing' count"
        assert isinstance(queue.get("queued"), int), "queued should be integer"
        assert isinstance(queue.get("processing"), int), "processing should be integer"
    
    def test_performance_render_stats_fields(self, api_session, admin_token):
        """Render stats should have timing metrics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/performance", headers=headers)
        
        data = response.json()
        render = data.get("render_stats", {})
        
        # These may be 0 or null if no recent renders
        assert "avg_total_ms" in render or render == {}, "Should have avg_total_ms or empty"
        assert "max_total_ms" in render or render == {}, "Should have max_total_ms or empty"
        print(f"    Avg render time: {render.get('avg_total_ms', 0)}ms")
        print(f"    Max render time: {render.get('max_total_ms', 0)}ms")


# ==================== Pricing Page (Verify $9/$19 Plans) ====================

class TestPricingPlans:
    """Verify pricing products are correct"""
    
    def test_cashfree_products_returns_plans(self, api_session, test_user_token):
        """Products endpoint should return Creator and Pro plans with correct credits"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_session.get(f"{BASE_URL}/api/cashfree/products", headers=headers)
        
        # May need auth
        if response.status_code == 401:
            pytest.skip("Products endpoint requires different auth")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        products = data.get("products", {})
        
        # Check Creator plan (100 credits) - price may be in INR
        creator = products.get("creator_monthly")
        if creator:
            assert creator.get("credits") == 100, "Creator should have 100 credits"
            print(f"  Creator plan: {creator.get('price')} / {creator.get('credits')} credits")
        
        # Check Pro plan (250 credits)
        pro = products.get("pro_monthly")
        if pro:
            assert pro.get("credits") == 250, "Pro should have 250 credits"
            print(f"  Pro plan: {pro.get('price')} / {pro.get('credits')} credits")
        
        # Check top-ups exist
        topup_small = products.get("topup_small")
        if topup_small:
            assert topup_small.get("credits") == 50, "Small topup should have 50 credits"
            print(f"  Small topup: {topup_small.get('price')} / {topup_small.get('credits')} credits")


# ==================== Analytics Funnel (Admin) ====================

class TestAnalyticsFunnel:
    """Test analytics funnel endpoint for admin"""
    
    def test_funnel_requires_admin(self, api_session, test_user_token):
        """Funnel endpoint should require admin role"""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/analytics/funnel?days=30", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
    
    def test_funnel_returns_data_for_admin(self, api_session, admin_token):
        """Funnel endpoint should return funnel data for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = api_session.get(f"{BASE_URL}/api/pipeline/analytics/funnel?days=30", headers=headers)
        
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Should have success=true"
        assert "funnel" in data, "Should have funnel data"
        assert "totals" in data, "Should have totals"
        
        totals = data.get("totals", {})
        print(f"  Funnel totals (last 30 days):")
        print(f"    Total videos: {totals.get('total_videos', 0)}")
        print(f"    Completed: {totals.get('completed_videos', 0)}")
        print(f"    Remixes: {totals.get('remix_count', 0)}")


# ==================== Pipeline Options ====================

class TestPipelineOptions:
    """Test pipeline options endpoint returns all configuration"""
    
    def test_options_returns_all_configs(self, api_session):
        """Options endpoint should return animation styles, age groups, voices, costs"""
        response = api_session.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
        # Check animation styles
        styles = data.get("animation_styles", [])
        assert len(styles) >= 6, f"Should have at least 6 animation styles, got {len(styles)}"
        
        style_ids = [s.get("id") for s in styles]
        # Actual style IDs from the backend
        expected_styles = ["cartoon_2d", "anime_style", "3d_pixar", "watercolor", "comic_book", "claymation"]
        for expected in expected_styles:
            assert expected in style_ids, f"Missing animation style: {expected}"
        
        print(f"  Animation styles: {len(styles)}")
        print(f"  Age groups: {len(data.get('age_groups', []))}")
        print(f"  Voice presets: {len(data.get('voice_presets', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
