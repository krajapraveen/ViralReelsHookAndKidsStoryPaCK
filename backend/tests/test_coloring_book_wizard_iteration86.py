"""
Test Suite: Coloring Book Wizard - 5-Step Flow (Iteration 86)
Testing the new pricing structure and wizard flow:
- Story Mode: 5 pages=10cr, 10 pages=18cr, 20 pages=32cr (default), 30 pages=45cr
- Photo Mode: 1 image=5cr, 5 images=20cr, 10 images=35cr
- Add-ons: Activity Pages +3, Personalized Cover +4 (pre-selected), Dedication Page +2, 
           Premium Templates +5 (Pro only), HD Print +5, Commercial License +10
- Subscription discounts: Creator 20%, Pro 30%, Studio 40%
- Expected AOV: 39 credits (20 pages + cover + activity)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestColoringBookPricingAPI:
    """Test /api/coloring-book/pricing endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping tests")
    
    def test_pricing_endpoint_returns_success(self):
        """Test that pricing endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Response should have success=True"
        print("PASS: Pricing endpoint returns 200 OK")
    
    def test_pricing_has_story_mode(self):
        """Test that pricing includes story mode options with correct credits"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers
        )
        data = response.json()
        
        assert "storyMode" in data, "Missing storyMode in response"
        story_mode = data["storyMode"]
        
        # Verify exact pricing: 5 pages=10cr, 10 pages=18cr, 20 pages=32cr, 30 pages=45cr
        assert story_mode.get("5_pages", {}).get("credits") == 10, "5 pages should be 10 credits"
        assert story_mode.get("10_pages", {}).get("credits") == 18, "10 pages should be 18 credits"
        assert story_mode.get("20_pages", {}).get("credits") == 32, "20 pages should be 32 credits"
        assert story_mode.get("30_pages", {}).get("credits") == 45, "30 pages should be 45 credits"
        
        # Verify 20 pages is default
        assert story_mode.get("20_pages", {}).get("default") == True, "20 pages should be default"
        print("PASS: Story mode pricing is correct")
    
    def test_pricing_has_photo_mode(self):
        """Test that pricing includes photo mode options with correct credits"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers
        )
        data = response.json()
        
        assert "photoMode" in data, "Missing photoMode in response"
        photo_mode = data["photoMode"]
        
        # Verify exact pricing: 1 image=5cr, 5 images=20cr, 10 images=35cr
        assert photo_mode.get("1_image", {}).get("credits") == 5, "1 image should be 5 credits"
        assert photo_mode.get("5_images", {}).get("credits") == 20, "5 images should be 20 credits"
        assert photo_mode.get("10_images", {}).get("credits") == 35, "10 images should be 35 credits"
        print("PASS: Photo mode pricing is correct")
    
    def test_pricing_has_addons(self):
        """Test that pricing includes all add-ons with correct credits"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers
        )
        data = response.json()
        
        assert "addons" in data, "Missing addons in response"
        addons = data["addons"]
        
        # Verify add-on credits
        assert addons.get("activity_pages", {}).get("credits") == 3, "Activity pages should be 3 credits"
        assert addons.get("personalized_cover", {}).get("credits") == 4, "Personalized cover should be 4 credits"
        assert addons.get("dedication_page", {}).get("credits") == 2, "Dedication page should be 2 credits"
        assert addons.get("premium_templates", {}).get("credits") == 5, "Premium templates should be 5 credits"
        assert addons.get("hd_print", {}).get("credits") == 5, "HD print should be 5 credits"
        assert addons.get("commercial_license", {}).get("credits") == 10, "Commercial license should be 10 credits"
        print("PASS: Add-on pricing is correct")
    
    def test_pricing_has_defaults(self):
        """Test that pricing includes defaults for revenue optimization"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=self.headers
        )
        data = response.json()
        
        assert "defaults" in data, "Missing defaults in response"
        defaults = data["defaults"]
        
        assert defaults.get("storyPageOption") == "20_pages", "Default story option should be 20_pages"
        assert "personalized_cover" in defaults.get("preSelectedAddons", []), "personalized_cover should be pre-selected"
        print("PASS: Defaults are set correctly for revenue optimization")


class TestColoringBookCalculateAPI:
    """Test /api/coloring-book/calculate endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping tests")
    
    def test_calculate_20_pages_with_cover(self):
        """Test calculation: 20 pages + cover = 36 credits"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate?mode=story&option=20_pages&addons=personalized_cover",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        breakdown = data.get("breakdown", {})
        
        # 20 pages = 32 credits, cover = 4 credits, total = 36
        assert breakdown.get("base", {}).get("credits") == 32, "Base should be 32 credits"
        assert breakdown.get("total") == 36, "Total should be 36 credits (32 + 4)"
        print("PASS: 20 pages + cover = 36 credits")
    
    def test_calculate_expected_aov(self):
        """Test expected AOV calculation: 20 pages + cover + activity = 39 credits"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate?mode=story&option=20_pages&addons=personalized_cover&addons=activity_pages",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        # 20 pages = 32 credits, cover = 4 credits, activity = 3 credits, total = 39
        total = breakdown.get("total", 0)
        assert total == 39, f"Expected AOV should be 39 credits, got {total}"
        print("PASS: Expected AOV calculation correct: 39 credits")
    
    def test_calculate_photo_mode(self):
        """Test photo mode calculation"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate?mode=photo&option=5_images&addons=personalized_cover",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        # 5 images = 20 credits, cover = 4 credits, total = 24
        assert breakdown.get("base", {}).get("credits") == 20, "Base should be 20 credits"
        assert breakdown.get("total") == 24, "Total should be 24 credits"
        print("PASS: Photo mode calculation correct")
    
    def test_calculate_breakdown_structure(self):
        """Test that breakdown has correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/calculate?mode=story&option=20_pages&addons=personalized_cover&addons=activity_pages",
            headers=self.headers
        )
        
        data = response.json()
        breakdown = data.get("breakdown", {})
        
        # Verify structure
        assert "base" in breakdown, "Missing base in breakdown"
        assert "addons" in breakdown, "Missing addons list in breakdown"
        assert "subtotal" in breakdown, "Missing subtotal in breakdown"
        assert "discount" in breakdown, "Missing discount in breakdown"
        assert "total" in breakdown, "Missing total in breakdown"
        
        # Verify addon list
        addon_list = breakdown.get("addons", [])
        assert len(addon_list) == 2, f"Expected 2 addons, got {len(addon_list)}"
        
        addon_ids = [a.get("id") for a in addon_list]
        assert "personalized_cover" in addon_ids, "personalized_cover should be in addons"
        assert "activity_pages" in addon_ids, "activity_pages should be in addons"
        print("PASS: Breakdown structure is correct")


class TestColoringBookSessionAPI:
    """Test session tracking and analytics endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping tests")
    
    def test_session_start(self):
        """Test that session/start creates a new session"""
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/session/start",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "sessionId" in data, "Missing sessionId in response"
        assert len(data["sessionId"]) > 0, "Session ID should not be empty"
        print(f"PASS: Session started with ID: {data['sessionId']}")
    
    def test_analytics_track_mode_selection(self):
        """Test analytics tracking for mode selection"""
        # First start a session
        session_res = requests.post(
            f"{BASE_URL}/api/coloring-book/session/start",
            headers=self.headers
        )
        session_id = session_res.json().get("sessionId")
        
        # Track analytics
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/analytics/track",
            headers=self.headers,
            json={
                "sessionId": session_id,
                "step": 1,
                "action": "mode_selected",
                "data": {"mode": "story"}
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("success") == True
        print("PASS: Analytics tracking for mode selection works")
    
    def test_analytics_track_step_completion(self):
        """Test analytics tracking for step completion"""
        # First start a session
        session_res = requests.post(
            f"{BASE_URL}/api/coloring-book/session/start",
            headers=self.headers
        )
        session_id = session_res.json().get("sessionId")
        
        # Track step completion
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/analytics/track",
            headers=self.headers,
            json={
                "sessionId": session_id,
                "step": 2,
                "action": "step_completed",
                "data": {"next_step": 3}
            }
        )
        assert response.status_code == 200
        print("PASS: Analytics tracking for step completion works")


class TestColoringBookPreviewAPI:
    """Test preview generation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping tests")
    
    def test_preview_config(self):
        """Test preview configuration endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/preview-config",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "preview" in data, "Missing preview in response"
        
        preview = data["preview"]
        assert "pages" in preview, "Missing pages in preview config"
        assert "watermark" in preview, "Missing watermark in preview config"
        print(f"PASS: Preview config returned - pages: {preview['pages']}, watermark: {preview['watermark']}")


class TestColoringBookGenerationAPI:
    """Test generation endpoints (preview and full)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "Password123!"}
        )
        if login_response.status_code == 200:
            self.token = login_response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Auth failed - skipping tests")
    
    def test_preview_generation(self):
        """Test preview generation (FREE - no credits charged)"""
        # Start session first
        session_res = requests.post(
            f"{BASE_URL}/api/coloring-book/session/start",
            headers=self.headers
        )
        session_id = session_res.json().get("sessionId")
        
        response = requests.post(
            f"{BASE_URL}/api/coloring-book/generate/preview",
            headers=self.headers,
            json={
                "sessionId": session_id,
                "mode": "story",
                "storyData": {
                    "title": "Test Story",
                    "ageGroup": "4-6",
                    "description": "A test story for coloring book generation",
                    "illustrationStyle": "cartoon",
                    "pageCount": "20"
                },
                "customize": {
                    "mode": "story",
                    "pageOption": "20_pages",
                    "paperSize": "A4",
                    "addons": ["personalized_cover"]
                }
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True
        assert "preview" in data, "Missing preview in response"
        print("PASS: Preview generation works (FREE)")
    
    def test_history_endpoint(self):
        """Test generation history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/history",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        assert "generations" in data, "Missing generations in response"
        print(f"PASS: History endpoint works - {len(data['generations'])} generations found")


class TestColoringBookSubscriptionDiscounts:
    """Test subscription discount calculations"""
    
    def get_auth_header(self, email: str, password: str):
        """Helper to get auth header for a user"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        return None
    
    def test_free_user_no_discount(self):
        """Test that free users get 0% discount"""
        headers = self.get_auth_header("demo@example.com", "Password123!")
        if not headers:
            pytest.skip("Auth failed")
        
        response = requests.get(
            f"{BASE_URL}/api/coloring-book/pricing",
            headers=headers
        )
        data = response.json()
        
        subscription = data.get("subscription", {})
        benefits = subscription.get("benefits", {})
        
        # Free user should have 0% discount
        discount = benefits.get("discount", -1)
        assert discount == 0, f"Free user discount should be 0%, got {discount}%"
        print("PASS: Free user has 0% discount")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
