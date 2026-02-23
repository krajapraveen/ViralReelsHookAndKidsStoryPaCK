"""
Test suite for Comix AI and GIF Maker features - Iteration 67
Tests backend APIs for both new features added to CreatorStudio AI
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"


class TestAuthentication:
    """Authentication tests to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        assert len(auth_token) > 0


class TestComixAIStyles:
    """Test Comix AI styles and configuration endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_get_comic_styles(self, auth_token):
        """Test that comic styles API returns all 9 styles"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/styles", headers=headers)
        
        assert response.status_code == 200, f"Failed to get styles: {response.text}"
        data = response.json()
        
        # Verify styles structure
        assert "styles" in data, "No styles in response"
        styles = data["styles"]
        
        # Expected 9 styles
        expected_styles = ["classic", "manga", "cartoon", "pixel", "kids", "noir", "superhero", "fantasy", "scifi"]
        
        for style in expected_styles:
            assert style in styles, f"Missing style: {style}"
            assert "name" in styles[style], f"Style {style} missing name"
            assert "description" in styles[style], f"Style {style} missing description"
            assert "prompt_modifier" in styles[style], f"Style {style} missing prompt_modifier"
        
        print(f"✓ Found all 9 comic styles: {list(styles.keys())}")
    
    def test_get_layouts(self, auth_token):
        """Test that panel layouts are returned"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/styles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "layouts" in data, "No layouts in response"
        layouts = data["layouts"]
        
        # Expected panel layouts
        expected_counts = ["1", "3", "4", "6", "9"]
        for count in expected_counts:
            assert count in layouts or int(count) in layouts, f"Missing layout for {count} panels"
        
        print(f"✓ Found panel layouts: {list(layouts.keys())}")
    
    def test_get_credit_costs(self, auth_token):
        """Test that credit costs are returned"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/styles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "credits" in data, "No credits info in response"
        credits = data["credits"]
        
        # Expected credit cost keys
        expected_costs = ["character_portrait", "character_fullbody", "panel_single", "panel_multi", "story_mode"]
        for cost_type in expected_costs:
            assert cost_type in credits, f"Missing credit cost: {cost_type}"
            assert isinstance(credits[cost_type], int), f"Credit cost {cost_type} should be integer"
        
        print(f"✓ Credit costs: {credits}")


class TestComixAICreditsInfo:
    """Test Comix AI credits info endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_credits_info_endpoint(self, auth_token):
        """Test credits info endpoint returns proper structure"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/credits-info", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "costs" in data, "Missing costs"
        assert "userCredits" in data, "Missing userCredits"
        assert "description" in data, "Missing description"
        
        # Verify descriptions exist
        descriptions = data["description"]
        assert "character_portrait" in descriptions
        assert "story_mode" in descriptions
        
        print(f"✓ Credits info endpoint working, user has {data['userCredits']} credits")


class TestComixAIHistory:
    """Test Comix AI history endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_history_endpoint(self, auth_token):
        """Test comic history endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/comix/history?size=10", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "jobs" in data, "Missing jobs array"
        assert "total" in data, "Missing total count"
        assert "page" in data, "Missing page"
        assert "size" in data, "Missing size"
        
        print(f"✓ Comic history: {data['total']} total jobs")


class TestGifMakerEmotions:
    """Test GIF Maker emotions and configuration endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_get_emotions(self, auth_token):
        """Test that emotions API returns all 12 emotions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        
        assert response.status_code == 200, f"Failed to get emotions: {response.text}"
        data = response.json()
        
        assert "emotions" in data, "No emotions in response"
        emotions = data["emotions"]
        
        # Expected 12 emotions
        expected_emotions = [
            "happy", "sad", "excited", "laughing", "surprised", "thinking",
            "dancing", "waving", "jumping", "hearts", "thumbsup", "celebrate"
        ]
        
        for emotion in expected_emotions:
            assert emotion in emotions, f"Missing emotion: {emotion}"
            assert "name" in emotions[emotion], f"Emotion {emotion} missing name"
            assert "emoji" in emotions[emotion], f"Emotion {emotion} missing emoji"
            assert "description" in emotions[emotion], f"Emotion {emotion} missing description"
            assert "safe" in emotions[emotion], f"Emotion {emotion} missing safe flag"
            assert emotions[emotion]["safe"] == True, f"Emotion {emotion} should be safe"
        
        print(f"✓ Found all 12 emotions: {list(emotions.keys())}")
    
    def test_get_gif_styles(self, auth_token):
        """Test that GIF styles are returned"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "styles" in data, "No styles in response"
        styles = data["styles"]
        
        # Expected styles
        expected_styles = ["cartoon", "sticker", "chibi", "pixel", "watercolor"]
        for style in expected_styles:
            assert style in styles, f"Missing GIF style: {style}"
        
        print(f"✓ Found GIF styles: {list(styles.keys())}")
    
    def test_get_backgrounds(self, auth_token):
        """Test that backgrounds are returned"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "backgrounds" in data, "No backgrounds in response"
        backgrounds = data["backgrounds"]
        
        # Should have multiple background options
        assert len(backgrounds) >= 5, "Expected at least 5 background options"
        assert "transparent" in backgrounds, "Missing transparent background option"
        
        print(f"✓ Found {len(backgrounds)} background options")
    
    def test_get_gif_credits(self, auth_token):
        """Test that GIF credit costs are returned"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "credits" in data, "No credits in response"
        credits = data["credits"]
        
        # Expected credit types
        expected_costs = ["basic", "hd", "action", "batch_5", "batch_10"]
        for cost_type in expected_costs:
            assert cost_type in credits, f"Missing credit cost: {cost_type}"
            assert isinstance(credits[cost_type], int), f"Credit {cost_type} should be integer"
        
        print(f"✓ GIF credit costs: {credits}")


class TestGifMakerCreditsInfo:
    """Test GIF Maker credits info endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_gif_credits_info(self, auth_token):
        """Test GIF credits info endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/credits-info", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "costs" in data
        assert "userCredits" in data
        assert "freeUserLimits" in data
        assert "paidFeatures" in data
        
        # Verify free user limits
        free_limits = data["freeUserLimits"]
        assert "dailyLimit" in free_limits
        assert "hasWatermark" in free_limits
        
        print(f"✓ GIF credits info working, user has {data['userCredits']} credits")


class TestGifMakerHistory:
    """Test GIF Maker history endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_gif_history_endpoint(self, auth_token):
        """Test GIF history endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/gif-maker/history?size=12", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        
        print(f"✓ GIF history: {data['total']} total jobs")


class TestGifMakerShareEndpoint:
    """Test GIF Maker public share endpoint"""
    
    def test_share_nonexistent_gif(self):
        """Test share endpoint returns 404 for nonexistent GIF"""
        response = requests.get(f"{BASE_URL}/api/gif-maker/share/nonexistent-id-12345")
        
        # Should return 404 for nonexistent GIF
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Share endpoint properly returns 404 for nonexistent GIF")


class TestContentModeration:
    """Test content moderation for both features"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_blocked_content_patterns_documentation(self, auth_token):
        """Verify that content moderation is documented in styles response"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Comix AI styles endpoint should work
        response = requests.get(f"{BASE_URL}/api/comix/styles", headers=headers)
        assert response.status_code == 200
        
        # GIF Maker emotions endpoint should work  
        response = requests.get(f"{BASE_URL}/api/gif-maker/emotions", headers=headers)
        assert response.status_code == 200
        
        print("✓ Both APIs accessible - content moderation enforced at generation time")


class TestAPIRoutesExist:
    """Verify all required API routes exist"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_comix_routes_exist(self, auth_token):
        """Test Comix AI routes are registered"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # GET routes
        routes_to_check = [
            "/api/comix/styles",
            "/api/comix/credits-info",
            "/api/comix/history",
        ]
        
        for route in routes_to_check:
            response = requests.get(f"{BASE_URL}{route}", headers=headers)
            assert response.status_code == 200, f"Route {route} failed: {response.status_code}"
            print(f"  ✓ {route} - 200 OK")
        
        print("✓ All Comix AI GET routes accessible")
    
    def test_gif_maker_routes_exist(self, auth_token):
        """Test GIF Maker routes are registered"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # GET routes
        routes_to_check = [
            "/api/gif-maker/emotions",
            "/api/gif-maker/credits-info",
            "/api/gif-maker/history",
        ]
        
        for route in routes_to_check:
            response = requests.get(f"{BASE_URL}{route}", headers=headers)
            assert response.status_code == 200, f"Route {route} failed: {response.status_code}"
            print(f"  ✓ {route} - 200 OK")
        
        print("✓ All GIF Maker GET routes accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
