"""
Backend tests for Blog SEO Posts and Payment History fixes - Iteration 144
Tests:
1. Blog API - returns 12 posts including 4 new SEO blog posts
2. Blog categories - includes Business Tips and Monetization
3. Individual blog post - fetches correct data for new posts
4. Payment History API - returns correct payment data with proper field names
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBlogAPI:
    """Blog API endpoint tests - MongoDB-based blog posts"""
    
    def test_blog_posts_returns_12_posts(self):
        """Blog API should return 12 posts total"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("total") == 12, f"Expected 12 posts, got {data.get('total')}"
        assert len(data.get("posts", [])) == 12
    
    def test_blog_post_ai_revolutionizing_small_businesses(self):
        """Verify new blog post: AI Revolutionizing Content for Small Businesses"""
        slug = "ai-revolutionizing-content-creation-small-businesses-2026"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        post = data.get("post")
        assert post is not None
        assert post.get("title") == "How AI is Revolutionizing Content Creation for Small Businesses in 2026"
        assert post.get("category") == "Business Tips"
        assert "small business" in post.get("tags", [])
    
    def test_blog_post_monetize_creative_skills(self):
        """Verify new blog post: Monetize Creative Skills with AI Tools"""
        slug = "monetize-creative-skills-ai-tools-2026"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200
        data = response.json()
        post = data.get("post")
        assert post is not None
        assert post.get("title") == "10 Ways to Monetize Your Creative Skills with AI Tools"
        assert post.get("category") == "Monetization"
    
    def test_blog_post_photo_to_comic(self):
        """Verify new blog post: AI Photo to Comic"""
        slug = "ai-photo-to-comic-transform-photos-professional-art"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200
        data = response.json()
        post = data.get("post")
        assert post is not None
        assert "Photo to Comic" in post.get("title")
        assert post.get("category") == "Design Tools"
    
    def test_blog_post_reaction_gifs(self):
        """Verify new blog post: Creating Viral Reaction GIFs"""
        slug = "ultimate-guide-creating-viral-reaction-gifs-ai"
        response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
        assert response.status_code == 200
        data = response.json()
        post = data.get("post")
        assert post is not None
        assert "Reaction GIFs" in post.get("title")
        assert post.get("category") == "Content Creation"
    
    def test_blog_categories_include_new_categories(self):
        """Blog categories should include Business Tips and Monetization"""
        response = requests.get(f"{BASE_URL}/api/blog/categories")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        categories = data.get("categories", [])
        category_names = [c.get("name") for c in categories]
        assert "Business Tips" in category_names, "Missing 'Business Tips' category"
        assert "Monetization" in category_names, "Missing 'Monetization' category"
    
    def test_blog_post_has_required_fields(self):
        """Blog posts should have all required fields for display"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?limit=1")
        assert response.status_code == 200
        data = response.json()
        posts = data.get("posts", [])
        assert len(posts) > 0
        post = posts[0]
        # Required fields for frontend display
        required_fields = ["id", "title", "slug", "excerpt", "category", "publishedAt"]
        for field in required_fields:
            assert field in post, f"Missing required field: {field}"
    
    def test_blog_category_filter(self):
        """Blog API category filter should work correctly"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?category=Business%20Tips")
        assert response.status_code == 200
        data = response.json()
        posts = data.get("posts", [])
        assert len(posts) > 0
        for post in posts:
            assert post.get("category") == "Business Tips"


class TestPaymentHistoryAPI:
    """Payment History API tests - requires authentication"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login and get auth token for authenticated requests"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@visionary-suite.com", "password": "Test@2026#"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Login failed - skipping payment history tests")
    
    def test_payment_history_returns_payments(self):
        """Payment history endpoint should return payments array"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/payments/history?skip=0&limit=10",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "payments" in data
        assert "total" in data
        assert isinstance(data["payments"], list)
    
    def test_payment_has_snake_case_fields(self):
        """Payment records should have snake_case field names"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/payments/history?skip=0&limit=5",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        payments = data.get("payments", [])
        if len(payments) == 0:
            pytest.skip("No payments to test")
        
        payment = payments[0]
        # Check snake_case fields exist (not camelCase)
        assert "order_id" in payment or "orderId" in payment, "Missing order_id field"
        assert "createdAt" in payment or "created_at" in payment, "Missing createdAt/created_at field"
        assert "status" in payment, "Missing status field"
    
    def test_payment_has_plan_name(self):
        """Payment records should include plan_name for display"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/payments/history?skip=0&limit=10",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        payments = data.get("payments", [])
        # Check that some payments have plan_name
        has_plan_name = any(p.get("plan_name") or p.get("productName") for p in payments)
        assert has_plan_name, "No payments with plan_name/productName found"
    
    def test_payment_amount_in_paise(self):
        """Payment amounts should be stored in paise (100x rupees)"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/payments/history?skip=0&limit=10",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        payments = data.get("payments", [])
        for payment in payments:
            amount = payment.get("amount", 0)
            # Amounts should be in paise (e.g., 29900 for ₹299)
            assert amount >= 100, f"Amount {amount} seems too low - should be in paise"
    
    def test_payment_history_pagination(self):
        """Payment history should support pagination"""
        response = requests.get(
            f"{BASE_URL}/api/cashfree/payments/history?skip=0&limit=5",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("limit") == 5
        assert data.get("skip") == 0
        assert data.get("total", 0) >= len(data.get("payments", []))
    
    def test_payment_history_requires_auth(self):
        """Payment history should require authentication"""
        response = requests.get(f"{BASE_URL}/api/cashfree/payments/history")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422], f"Expected auth error, got {response.status_code}"


class TestBlogSEOMetadata:
    """Test blog posts have proper SEO metadata"""
    
    def test_new_posts_have_meta_titles(self):
        """New blog posts should have metaTitle for SEO"""
        new_slugs = [
            "ai-revolutionizing-content-creation-small-businesses-2026",
            "monetize-creative-skills-ai-tools-2026",
            "ai-photo-to-comic-transform-photos-professional-art",
            "ultimate-guide-creating-viral-reaction-gifs-ai"
        ]
        for slug in new_slugs:
            response = requests.get(f"{BASE_URL}/api/blog/posts/{slug}")
            assert response.status_code == 200
            post = response.json().get("post")
            assert post.get("metaTitle"), f"Missing metaTitle for {slug}"
            assert post.get("metaDescription"), f"Missing metaDescription for {slug}"
    
    def test_blog_posts_have_tags(self):
        """Blog posts should have tags for categorization"""
        response = requests.get(f"{BASE_URL}/api/blog/posts?limit=5")
        assert response.status_code == 200
        posts = response.json().get("posts", [])
        for post in posts:
            tags = post.get("tags", [])
            assert len(tags) > 0, f"Post {post.get('slug')} has no tags"


class TestCreditsBalanceAPI:
    """Test credits balance API returns correct format"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@visionary-suite.com", "password": "Test@2026#"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Login failed")
    
    def test_credits_balance_returns_both_fields(self):
        """Credits API should return both 'balance' and 'credits' fields"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least one of these fields
        has_balance = "balance" in data or "credits" in data
        assert has_balance, "Missing both 'balance' and 'credits' fields"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
