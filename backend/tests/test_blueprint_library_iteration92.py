"""
Test Blueprint Library API - Iteration 92
Tests for Revenue Protection & Content Blueprint Library features

Features tested:
- Blueprint Library catalog endpoint (3 products with item counts)
- Hooks endpoint (sorted by engagement score)
- Frameworks endpoint (with categories)
- Story Ideas endpoint (with genres)
- Purchase endpoint (credit deduction and access granting)
- Content locking/unlocking based on purchases
- Admin seed database endpoint
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def demo_token(api_client):
    """Get demo user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Demo user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin user login failed: {response.status_code}")


@pytest.fixture
def demo_client(api_client, demo_token):
    """Session with demo user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {demo_token}"})
    return api_client


@pytest.fixture
def admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestBlueprintLibraryCatalog:
    """Test the /api/blueprint-library/catalog endpoint"""

    def test_catalog_returns_3_products(self, demo_client):
        """Catalog should return exactly 3 products"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "products" in data, "Response should contain 'products' key"
        assert len(data["products"]) == 3, f"Expected 3 products, got {len(data['products'])}"
        
    def test_catalog_products_have_correct_ids(self, demo_client):
        """Each product should have the correct id"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        product_ids = [p["id"] for p in data["products"]]
        expected_ids = ["viral_hook_bank", "reel_frameworks", "kids_story_ideas"]
        
        for expected_id in expected_ids:
            assert expected_id in product_ids, f"Product '{expected_id}' not found in catalog"

    def test_catalog_products_have_item_counts(self, demo_client):
        """Each product should have item_count > 0"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        for product in data["products"]:
            assert "item_count" in product, f"Product {product['id']} missing item_count"
            assert product["item_count"] > 0, f"Product {product['id']} has 0 items"
            print(f"Product {product['id']}: {product['item_count']} items")

    def test_catalog_returns_user_credits(self, demo_client):
        """Catalog should return user's credit balance"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        assert "user_credits" in data, "Response should contain 'user_credits'"
        assert isinstance(data["user_credits"], (int, float)), "user_credits should be a number"

    def test_catalog_products_have_pricing(self, demo_client):
        """Each product should have pricing information"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        for product in data["products"]:
            assert "pricing" in product, f"Product {product['id']} missing pricing"
            assert len(product["pricing"]) >= 3, f"Product {product['id']} should have at least 3 pricing tiers"


class TestBlueprintLibraryHooks:
    """Test the /api/blueprint-library/hooks endpoint"""

    def test_hooks_endpoint_returns_hooks(self, demo_client):
        """Hooks endpoint should return hooks array"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        assert response.status_code == 200
        
        data = response.json()
        assert "hooks" in data, "Response should contain 'hooks' key"
        assert len(data["hooks"]) > 0, "Should return at least 1 hook"

    def test_hooks_sorted_by_engagement_score(self, demo_client):
        """Hooks should be sorted by engagement_score descending"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        hooks = data["hooks"]
        scores = [h.get("engagement_score", 0) for h in hooks if h.get("engagement_score")]
        
        # Check if sorted in descending order
        assert scores == sorted(scores, reverse=True), "Hooks should be sorted by engagement_score descending"
        print(f"Engagement scores (first 5): {scores[:5]}")

    def test_hooks_have_niche_field(self, demo_client):
        """Each hook should have a niche field"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        for hook in data["hooks"][:5]:  # Check first 5
            assert "niche" in hook, "Hook should have 'niche' field"
            assert hook["niche"], "Niche should not be empty"

    def test_hooks_filter_by_niche(self, demo_client):
        """Hooks can be filtered by niche"""
        # First get available niches
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        if data.get("niches") and len(data["niches"]) > 0:
            test_niche = data["niches"][0]
            filtered_response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks?niche={test_niche}")
            filtered_data = filtered_response.json()
            
            for hook in filtered_data["hooks"]:
                assert hook["niche"] == test_niche, f"Hook niche should be {test_niche}"

    def test_hooks_have_lock_status(self, demo_client):
        """Each hook should have is_unlocked field"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        for hook in data["hooks"][:5]:
            assert "is_unlocked" in hook, "Hook should have 'is_unlocked' field"


class TestBlueprintLibraryFrameworks:
    """Test the /api/blueprint-library/frameworks endpoint"""

    def test_frameworks_endpoint_returns_frameworks(self, demo_client):
        """Frameworks endpoint should return frameworks array"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/frameworks")
        assert response.status_code == 200
        
        data = response.json()
        assert "frameworks" in data, "Response should contain 'frameworks' key"
        assert len(data["frameworks"]) > 0, "Should return at least 1 framework"

    def test_frameworks_have_category_field(self, demo_client):
        """Each framework should have a category field"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/frameworks")
        data = response.json()
        
        for framework in data["frameworks"]:
            assert "category" in framework, "Framework should have 'category' field"
            assert framework["category"], "Category should not be empty"

    def test_frameworks_have_title_and_description(self, demo_client):
        """Each framework should have title and description"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/frameworks")
        data = response.json()
        
        for framework in data["frameworks"]:
            assert "title" in framework, "Framework should have 'title' field"
            assert "description" in framework, "Framework should have 'description' field"

    def test_frameworks_categories_returned(self, demo_client):
        """Endpoint should return available categories"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/frameworks")
        data = response.json()
        
        assert "categories" in data, "Response should contain 'categories' key"
        assert len(data["categories"]) > 0, "Should have at least 1 category"
        print(f"Framework categories: {data['categories']}")


class TestBlueprintLibraryStoryIdeas:
    """Test the /api/blueprint-library/story-ideas endpoint"""

    def test_story_ideas_endpoint_returns_ideas(self, demo_client):
        """Story ideas endpoint should return ideas array"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/story-ideas")
        assert response.status_code == 200
        
        data = response.json()
        assert "ideas" in data, "Response should contain 'ideas' key"
        assert len(data["ideas"]) > 0, "Should return at least 1 story idea"

    def test_story_ideas_have_genre_field(self, demo_client):
        """Each story idea should have a genre field"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/story-ideas")
        data = response.json()
        
        for idea in data["ideas"]:
            assert "genre" in idea, "Story idea should have 'genre' field"
            assert idea["genre"], "Genre should not be empty"

    def test_story_ideas_have_age_group(self, demo_client):
        """Each story idea should have age_group"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/story-ideas")
        data = response.json()
        
        for idea in data["ideas"]:
            assert "age_group" in idea, "Story idea should have 'age_group' field"

    def test_story_ideas_genres_returned(self, demo_client):
        """Endpoint should return available genres"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/story-ideas")
        data = response.json()
        
        assert "genres" in data, "Response should contain 'genres' key"
        assert len(data["genres"]) > 0, "Should have at least 1 genre"
        print(f"Story genres: {data['genres']}")


class TestBlueprintLibraryPurchase:
    """Test the /api/blueprint-library/purchase endpoint"""

    def test_purchase_validation_requires_product_type(self, demo_client):
        """Purchase should validate product_type"""
        response = demo_client.post(f"{BASE_URL}/api/blueprint-library/purchase", json={
            "product_type": "invalid_type",
            "purchase_tier": "single"
        })
        assert response.status_code == 400, "Should reject invalid product_type"

    def test_purchase_validation_requires_item_id_for_single(self, demo_client):
        """Single purchase should require item_id"""
        response = demo_client.post(f"{BASE_URL}/api/blueprint-library/purchase", json={
            "product_type": "viral_hook_bank",
            "purchase_tier": "single"
        })
        assert response.status_code == 400, "Should require item_id for single purchase"
        assert "item_id" in response.json().get("detail", "").lower() or "Item ID" in response.json().get("detail", "")

    def test_purchase_validation_requires_category_for_pack(self, demo_client):
        """Pack purchase should require category"""
        response = demo_client.post(f"{BASE_URL}/api/blueprint-library/purchase", json={
            "product_type": "viral_hook_bank",
            "purchase_tier": "pack"
        })
        assert response.status_code == 400, "Should require category for pack purchase"

    def test_purchase_single_hook_success(self, demo_client):
        """Purchase single hook should succeed and deduct credits"""
        # Get a hook ID first
        hooks_response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        hooks_data = hooks_response.json()
        
        if not hooks_data.get("hooks"):
            pytest.skip("No hooks available to purchase")
        
        # Find an unlocked hook to purchase (one we don't own yet)
        hook_to_buy = None
        for hook in hooks_data["hooks"]:
            if not hook.get("is_unlocked"):
                hook_to_buy = hook
                break
        
        if not hook_to_buy:
            # All hooks are already unlocked, skip test
            pytest.skip("All hooks already purchased or unlocked")
        
        # Get current credits
        catalog_response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        initial_credits = catalog_response.json().get("user_credits", 0)
        
        # Make the purchase
        response = demo_client.post(f"{BASE_URL}/api/blueprint-library/purchase", json={
            "product_type": "viral_hook_bank",
            "purchase_tier": "single",
            "item_id": hook_to_buy["id"]
        })
        
        assert response.status_code == 200, f"Purchase should succeed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "credits_spent" in data, "Response should include credits_spent"
        assert data["credits_spent"] == 1, "Single hook should cost 1 credit"
        assert data["new_balance"] == initial_credits - 1, "Credits should be deducted"
        
        print(f"Successfully purchased hook: credits {initial_credits} -> {data['new_balance']}")


class TestBlueprintLibraryContentLocking:
    """Test content locking/unlocking based on purchases"""

    def test_locked_hook_shows_truncated_content(self, demo_client):
        """Locked hooks should show truncated hook text"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        locked_hooks = [h for h in data["hooks"] if not h.get("is_unlocked")]
        
        for hook in locked_hooks[:3]:  # Check first 3 locked hooks
            # Locked hooks should have truncated text or full if short
            hook_text = hook.get("hook_text", "")
            # Hooks should either be short or truncated with "..."
            if len(hook_text) > 30:
                assert "..." in hook_text, "Long locked hook should be truncated"

    def test_unlocked_hook_shows_full_content(self, demo_client):
        """Unlocked hooks should show full content"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/hooks")
        data = response.json()
        
        unlocked_hooks = [h for h in data["hooks"] if h.get("is_unlocked")]
        
        if unlocked_hooks:
            for hook in unlocked_hooks[:3]:
                # Unlocked hooks may have variations field
                assert "hook_text" in hook, "Unlocked hook should have hook_text"


class TestBlueprintLibraryMyPurchases:
    """Test the /api/blueprint-library/my-purchases endpoint"""

    def test_my_purchases_returns_purchase_history(self, demo_client):
        """My purchases should return user's purchase history"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/my-purchases")
        assert response.status_code == 200
        
        data = response.json()
        assert "purchases" in data, "Response should contain 'purchases' key"
        assert "by_product" in data, "Response should contain 'by_product' grouping"
        assert "total_spent" in data, "Response should contain 'total_spent'"


class TestBlueprintLibraryAdminSeed:
    """Test admin seed database endpoint"""

    def test_seed_endpoint_requires_admin(self, demo_client):
        """Seed endpoint should require admin authentication"""
        # Demo user is not admin
        response = demo_client.post(f"{BASE_URL}/api/blueprint-library/admin/seed-database")
        assert response.status_code in [401, 403], "Should reject non-admin users"

    def test_seed_endpoint_works_for_admin(self, admin_client):
        """Seed endpoint should work for admin (returns already seeded if data exists)"""
        response = admin_client.post(f"{BASE_URL}/api/blueprint-library/admin/seed-database")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "seeded" in data
        print(f"Seed result: {data['seeded']}")


class TestBlueprintLibraryItemCounts:
    """Verify item counts match expected values"""

    def test_hooks_count_is_25(self, demo_client):
        """Viral Hook Bank should have 25 items"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        hook_product = next((p for p in data["products"] if p["id"] == "viral_hook_bank"), None)
        assert hook_product is not None, "Should have viral_hook_bank product"
        assert hook_product["item_count"] == 25, f"Expected 25 hooks, got {hook_product['item_count']}"

    def test_frameworks_count_is_6(self, demo_client):
        """Reel Framework Packs should have 6 items"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        framework_product = next((p for p in data["products"] if p["id"] == "reel_frameworks"), None)
        assert framework_product is not None, "Should have reel_frameworks product"
        assert framework_product["item_count"] == 6, f"Expected 6 frameworks, got {framework_product['item_count']}"

    def test_story_ideas_count_is_8(self, demo_client):
        """Kids Story Idea Bank should have 8 items"""
        response = demo_client.get(f"{BASE_URL}/api/blueprint-library/catalog")
        data = response.json()
        
        story_product = next((p for p in data["products"] if p["id"] == "kids_story_ideas"), None)
        assert story_product is not None, "Should have kids_story_ideas product"
        assert story_product["item_count"] == 8, f"Expected 8 story ideas, got {story_product['item_count']}"


class TestAuditLogService:
    """Test audit log related endpoints"""

    def test_audit_logs_requires_admin(self, demo_client):
        """Audit logs should require admin"""
        response = demo_client.get(f"{BASE_URL}/api/admin/audit/logs")
        assert response.status_code in [401, 403], "Should reject non-admin users"

    def test_audit_logs_works_for_admin(self, admin_client):
        """Admin should be able to access audit logs"""
        response = admin_client.get(f"{BASE_URL}/api/admin/audit/logs")
        assert response.status_code == 200
        
        data = response.json()
        assert "logs" in data or "pagination" in data, "Should return logs data"

    def test_security_summary_works_for_admin(self, admin_client):
        """Admin should be able to access security summary"""
        response = admin_client.get(f"{BASE_URL}/api/admin/audit/security-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data, "Should return period_days"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
