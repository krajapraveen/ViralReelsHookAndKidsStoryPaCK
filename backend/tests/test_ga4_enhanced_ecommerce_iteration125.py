"""
Test GA4 Enhanced E-commerce and Blog SEO Features - Iteration 125
Tests:
1. Blog API endpoints (posts, categories, single post)
2. Enhanced e-commerce tracking verification (code review based)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBlogAPI:
    """Blog API endpoints for SEO content"""
    
    def test_get_blog_posts(self):
        """Test getting list of published blog posts"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?limit=20")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "posts" in data
        assert "total" in data
        # Should have 8 posts (3 original + 5 new)
        assert data["total"] >= 8, f"Expected at least 8 posts, got {data['total']}"
        
        # Verify post structure
        if data["posts"]:
            post = data["posts"][0]
            assert "id" in post
            assert "title" in post
            assert "slug" in post
            assert "excerpt" in post
            assert "category" in post
            assert "published" in post
    
    def test_get_blog_categories(self):
        """Test getting blog categories with counts"""
        response = requests.get(f"{BASE_URL}/api/blog/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "categories" in data
        
        # Should have categories
        assert len(data["categories"]) > 0, "Expected at least one category"
        
        # Verify category structure
        if data["categories"]:
            cat = data["categories"][0]
            assert "name" in cat
            assert "count" in cat
    
    def test_get_single_blog_post(self):
        """Test getting a single blog post by slug"""
        slug = "how-to-create-viral-instagram-reels-2026"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "post" in data
        
        post = data["post"]
        assert post["slug"] == slug
        assert "content" in post
        assert len(post["content"]) > 100, "Content should be substantial"
        assert "title" in post
        assert "author" in post
    
    def test_get_nonexistent_blog_post(self):
        """Test getting a post that doesn't exist"""
        slug = "nonexistent-post-slug-12345"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 404
    
    def test_blog_posts_filter_by_category(self):
        """Test filtering blog posts by category"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?category=Instagram%20Tips")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # All returned posts should be in the filtered category
        for post in data["posts"]:
            assert post["category"] == "Instagram Tips"
    
    def test_blog_posts_pagination(self):
        """Test blog posts pagination"""
        # Get first 3 posts
        response1 = requests.get(f"{BASE_URL}/api/blog/posts?limit=3&skip=0")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get next 3 posts
        response2 = requests.get(f"{BASE_URL}/api/blog/posts?limit=3&skip=3")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Posts should be different
        if data1["posts"] and data2["posts"]:
            ids1 = {p["id"] for p in data1["posts"]}
            ids2 = {p["id"] for p in data2["posts"]}
            assert ids1.isdisjoint(ids2), "Paginated posts should not overlap"
    
    def test_blog_tags_endpoint(self):
        """Test getting blog tags"""
        response = requests.get(f"{BASE_URL}/api/blog/tags")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "tags" in data


class TestNewBlogPosts:
    """Verify the 5 new SEO blog posts are present"""
    
    new_post_slugs = [
        "ai-gif-maker-create-animated-content",
        "comic-avatar-generator-photos-to-cartoons",
        "coloring-book-creator-generate-printable-pages",
        "social-media-hooks-templates-2026",
        "content-repurposing-one-idea-ten-pieces"
    ]
    
    def test_new_gif_maker_post(self):
        """Verify AI GIF Maker blog post exists"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/ai-gif-maker-create-animated-content")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "GIF" in data["post"]["title"]
    
    def test_new_comic_avatar_post(self):
        """Verify Comic Avatar Generator blog post exists"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/comic-avatar-generator-photos-to-cartoons")
        assert response.status_code == 200
        data = response.json()
        assert "Comic Avatar" in data["post"]["title"]
    
    def test_new_coloring_book_post(self):
        """Verify Coloring Book Creator blog post exists"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/coloring-book-creator-generate-printable-pages")
        assert response.status_code == 200
        data = response.json()
        assert "Coloring Book" in data["post"]["title"]
    
    def test_new_social_hooks_post(self):
        """Verify Social Media Hooks blog post exists"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/social-media-hooks-templates-2026")
        assert response.status_code == 200
        data = response.json()
        assert "Hooks" in data["post"]["title"]
    
    def test_new_content_repurposing_post(self):
        """Verify Content Repurposing blog post exists"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/content-repurposing-one-idea-ten-pieces")
        assert response.status_code == 200
        data = response.json()
        assert "Repurposing" in data["post"]["title"]


class TestHealthAndBasicAPI:
    """Basic API health checks"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
    
    def test_products_endpoint(self):
        """Test products endpoint for e-commerce tracking context"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
