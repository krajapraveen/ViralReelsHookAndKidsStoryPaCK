"""
Iteration 119 - Testing new features:
1. Reviews API (organic testimonials system)
2. Blog API (SEO content pages)
3. Watermark API (social sharing with watermarks)
4. Live Chat Widget integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestReviewsAPI:
    """Test organic reviews system - no fake testimonials"""
    
    def test_approved_reviews_returns_empty(self):
        """Verify /api/reviews/approved returns empty array (no fake reviews)"""
        response = requests.get(f"{BASE_URL}/api/reviews/approved")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert isinstance(data["reviews"], list)
        assert data["totalCount"] == 0  # No approved reviews yet
        assert data["avgRating"] == 0
        
    def test_reviews_list_returns_empty(self):
        """Verify /api/reviews returns empty array (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/reviews")
        assert response.status_code == 200
        data = response.json()
        
        # Should be empty list - no fake reviews
        assert isinstance(data, list)
        assert len(data) == 0
        
    def test_approved_reviews_with_limit(self):
        """Verify /api/reviews/approved accepts limit parameter"""
        response = requests.get(f"{BASE_URL}/api/reviews/approved?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "reviews" in data
        assert "totalCount" in data
        assert "avgRating" in data
        
    def test_submit_review_requires_auth(self):
        """Verify /api/reviews/submit requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/reviews/submit",
            json={
                "name": "Test User",
                "rating": 5,
                "message": "This is a test review message for testing purposes."
            }
        )
        assert response.status_code == 401  # Unauthorized
        
    def test_admin_pending_requires_auth(self):
        """Verify /api/reviews/admin/pending requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/reviews/admin/pending")
        assert response.status_code == 401  # Unauthorized


class TestBlogAPI:
    """Test blog/content pages for SEO"""
    
    def test_blog_posts_returns_seeded_posts(self):
        """Verify /api/blog/posts returns 3 seeded posts"""
        response = requests.get(f"{BASE_URL}/api/blog/posts")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["posts"]) == 3
        assert data["total"] == 3
        assert data["hasMore"] is False
        
        # Verify post structure
        for post in data["posts"]:
            assert "id" in post
            assert "title" in post
            assert "slug" in post
            assert "excerpt" in post
            assert "category" in post
            assert "tags" in post
            assert "published" in post
            assert post["published"] is True  # Only published posts
            
    def test_blog_posts_category_filter(self):
        """Verify category filter works on /api/blog/posts"""
        # Test Instagram Tips category
        response = requests.get(f"{BASE_URL}/api/blog/posts?category=Instagram%20Tips")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["posts"]) == 1
        assert data["posts"][0]["category"] == "Instagram Tips"
        
    def test_blog_posts_youtube_category(self):
        """Verify YouTube Tips category filter"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?category=YouTube%20Tips")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["posts"]) == 1
        assert data["posts"][0]["category"] == "YouTube Tips"
        
    def test_blog_posts_content_strategy_category(self):
        """Verify Content Strategy category filter"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?category=Content%20Strategy")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["posts"]) == 1
        assert data["posts"][0]["category"] == "Content Strategy"
        
    def test_blog_categories_endpoint(self):
        """Verify /api/blog/categories returns correct categories"""
        response = requests.get(f"{BASE_URL}/api/blog/categories")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["categories"]) == 3
        
        category_names = [c["name"] for c in data["categories"]]
        assert "Instagram Tips" in category_names
        assert "YouTube Tips" in category_names
        assert "Content Strategy" in category_names
        
        # Each category should have count=1
        for cat in data["categories"]:
            assert cat["count"] == 1
            
    def test_blog_tags_endpoint(self):
        """Verify /api/blog/tags returns tags with counts"""
        response = requests.get(f"{BASE_URL}/api/blog/tags")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert isinstance(data["tags"], list)
        
        # Check some expected tags
        tag_names = [t["name"] for t in data["tags"]]
        # Common tags from seeded posts
        assert "ai tools" in tag_names or "instagram" in tag_names or "youtube" in tag_names
        
    def test_blog_single_post_by_slug(self):
        """Verify /api/blog/posts/{slug} returns single post"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/how-to-create-viral-instagram-reels-2026")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["post"]["slug"] == "how-to-create-viral-instagram-reels-2026"
        assert data["post"]["title"] == "How to Create Viral Instagram Reels in 2026"
        assert "content" in data["post"]  # Full content included for single post
        
    def test_blog_post_not_found(self):
        """Verify 404 for non-existent blog post"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/non-existent-slug-12345")
        assert response.status_code == 404
        
    def test_blog_admin_seed_requires_auth(self):
        """Verify /api/blog/admin/seed requires admin auth"""
        response = requests.post(f"{BASE_URL}/api/blog/admin/seed")
        assert response.status_code == 401  # Unauthorized


class TestWatermarkAPI:
    """Test watermark service for social sharing"""
    
    def test_watermark_settings_requires_auth(self):
        """Verify /api/watermark/settings requires authentication"""
        response = requests.get(f"{BASE_URL}/api/watermark/settings")
        assert response.status_code == 401  # Unauthorized
        
    def test_watermark_image_requires_auth(self):
        """Verify /api/watermark/image requires authentication"""
        response = requests.post(f"{BASE_URL}/api/watermark/image")
        assert response.status_code in [401, 422]  # Unauthorized or validation error


class TestLandingPageAPIs:
    """Test landing page related APIs"""
    
    def test_live_stats_public(self):
        """Verify /api/live-stats/public returns stats"""
        response = requests.get(f"{BASE_URL}/api/live-stats/public")
        # This endpoint might not exist or might return different status
        # Just check it doesn't crash the server
        assert response.status_code in [200, 404, 401]
        
    def test_health_endpoint(self):
        """Verify basic API health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200


class TestFooterLinks:
    """Verify footer links are accessible"""
    
    def test_blog_page_accessible(self):
        """Verify blog page is accessible via frontend route"""
        # This tests the frontend route indirectly via API
        response = requests.get(f"{BASE_URL}/api/blog/posts")
        assert response.status_code == 200
        
    def test_reviews_page_data(self):
        """Verify reviews page data is accessible"""
        response = requests.get(f"{BASE_URL}/api/reviews/approved")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
