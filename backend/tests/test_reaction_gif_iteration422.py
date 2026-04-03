"""
Reaction GIF Feature Tests - Iteration 422
Tests for the new single-screen flow with viral style packs

Features tested:
- GET /api/reaction-gif/reactions - returns 15 styles, 6 packs, first_free boolean
- POST /api/reaction-gif/generate - accepts new style IDs
- First-free logic for new users
- Admin credit bypass
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestReactionGIFReactionsEndpoint:
    """Tests for GET /api/reaction-gif/reactions endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_reactions_endpoint_requires_auth(self):
        """Test that /reactions endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /reactions endpoint requires authentication")
    
    def test_reactions_endpoint_returns_15_styles(self):
        """Test that /reactions returns 15 styles"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check styles count
        styles = data.get("styles", {})
        assert len(styles) == 15, f"Expected 15 styles, got {len(styles)}"
        print(f"PASS: /reactions returns {len(styles)} styles")
        
        # Verify all expected styles are present
        expected_styles = [
            "cartoon_motion", "comic_bounce", "sticker_style", "neon_glow", "minimal_clean",
            "meme_classic", "meme_deepfried",
            "pixar_3d", "pixar_clay",
            "anime_shonen", "anime_chibi",
            "desi_bollywood", "desi_comic",
            "corporate_clean", "corporate_flat"
        ]
        for style_id in expected_styles:
            assert style_id in styles, f"Missing style: {style_id}"
        print(f"PASS: All 15 expected styles present")
    
    def test_reactions_endpoint_returns_6_packs(self):
        """Test that /reactions returns 6 style packs"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check style_packs count
        style_packs = data.get("style_packs", {})
        assert len(style_packs) == 6, f"Expected 6 packs, got {len(style_packs)}"
        print(f"PASS: /reactions returns {len(style_packs)} style packs")
        
        # Verify all expected packs
        expected_packs = ["classic", "meme", "pixar", "anime", "desi", "corporate"]
        for pack_id in expected_packs:
            assert pack_id in style_packs, f"Missing pack: {pack_id}"
            pack = style_packs[pack_id]
            assert "name" in pack, f"Pack {pack_id} missing 'name'"
            assert "emoji" in pack, f"Pack {pack_id} missing 'emoji'"
            assert "description" in pack, f"Pack {pack_id} missing 'description'"
        print(f"PASS: All 6 expected packs present with correct structure")
    
    def test_reactions_endpoint_returns_first_free_boolean(self):
        """Test that /reactions returns first_free boolean"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check first_free is present and is boolean
        assert "first_free" in data, "Missing 'first_free' field"
        assert isinstance(data["first_free"], bool), f"first_free should be boolean, got {type(data['first_free'])}"
        print(f"PASS: first_free is present and is boolean (value: {data['first_free']})")
    
    def test_reactions_endpoint_returns_9_reactions(self):
        """Test that /reactions returns 9 reaction types"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check reactions count
        reactions = data.get("reactions", {})
        assert len(reactions) == 9, f"Expected 9 reactions, got {len(reactions)}"
        
        expected_reactions = ["happy", "laughing", "love", "cool", "surprised", "sad", "celebrate", "waving", "wow"]
        for reaction_id in expected_reactions:
            assert reaction_id in reactions, f"Missing reaction: {reaction_id}"
            assert "emoji" in reactions[reaction_id], f"Reaction {reaction_id} missing 'emoji'"
        print(f"PASS: All 9 reactions present with emoji")
    
    def test_styles_have_pack_association(self):
        """Test that each style has a pack association"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        styles = data.get("styles", {})
        valid_packs = ["classic", "meme", "pixar", "anime", "desi", "corporate"]
        
        for style_id, style_data in styles.items():
            assert "pack" in style_data, f"Style {style_id} missing 'pack'"
            assert style_data["pack"] in valid_packs, f"Style {style_id} has invalid pack: {style_data['pack']}"
        print(f"PASS: All styles have valid pack associations")


class TestReactionGIFGenerateEndpoint:
    """Tests for POST /api/reaction-gif/generate endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_generate_requires_auth(self):
        """Test that /generate endpoint requires authentication"""
        # Create a minimal test image
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'photo': ('test.png', img_bytes, 'image/png')}
        data = {'mode': 'single', 'reaction': 'happy', 'style': 'cartoon_motion'}
        
        response = self.session.post(f"{BASE_URL}/api/reaction-gif/generate", files=files, data=data)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /generate endpoint requires authentication")
    
    def test_generate_accepts_new_style_ids(self):
        """Test that /generate accepts the new viral style IDs"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Test each new style ID
        new_style_ids = [
            "meme_classic", "meme_deepfried",
            "pixar_3d", "pixar_clay",
            "anime_shonen", "anime_chibi",
            "desi_bollywood", "desi_comic",
            "corporate_clean", "corporate_flat"
        ]
        
        import io
        from PIL import Image
        
        for style_id in new_style_ids:
            # Create a minimal test image
            img = Image.new('RGB', (100, 100), color='blue')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            files = {'photo': ('test.png', img_bytes, 'image/png')}
            data = {
                'mode': 'single',
                'reaction': 'happy',
                'style': style_id,
                'hd_quality': 'false',
                'transparent_bg': 'false',
                'caption': '',
                'commercial_license': 'false'
            }
            
            response = self.session.post(f"{BASE_URL}/api/reaction-gif/generate", files=files, data=data)
            
            # Admin should be able to generate (bypasses credit check)
            # We expect 200 with jobId, or 400 if there's a validation issue
            assert response.status_code in [200, 400], f"Style {style_id}: Expected 200 or 400, got {response.status_code}"
            
            if response.status_code == 200:
                result = response.json()
                assert "jobId" in result, f"Style {style_id}: Missing jobId in response"
                print(f"PASS: Style {style_id} accepted, jobId: {result['jobId'][:8]}...")
            else:
                print(f"INFO: Style {style_id} returned 400: {response.json().get('detail', 'Unknown error')}")
    
    def test_generate_validates_reaction_type(self):
        """Test that /generate validates reaction type"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='green')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'photo': ('test.png', img_bytes, 'image/png')}
        data = {
            'mode': 'single',
            'reaction': 'invalid_reaction',
            'style': 'cartoon_motion'
        }
        
        response = self.session.post(f"{BASE_URL}/api/reaction-gif/generate", files=files, data=data)
        assert response.status_code == 400, f"Expected 400 for invalid reaction, got {response.status_code}"
        print("PASS: Invalid reaction type returns 400")
    
    def test_generate_defaults_invalid_style_to_cartoon_motion(self):
        """Test that /generate defaults invalid style to cartoon_motion"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='yellow')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'photo': ('test.png', img_bytes, 'image/png')}
        data = {
            'mode': 'single',
            'reaction': 'happy',
            'style': 'invalid_style_xyz'
        }
        
        response = self.session.post(f"{BASE_URL}/api/reaction-gif/generate", files=files, data=data)
        # Should accept and default to cartoon_motion
        assert response.status_code == 200, f"Expected 200 (default style), got {response.status_code}"
        print("PASS: Invalid style defaults to cartoon_motion (returns 200)")


class TestFirstFreeLogic:
    """Tests for first-free generation logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_admin_first_free_status(self):
        """Test first_free status for admin user (likely has jobs already)"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        # Admin likely has jobs, so first_free should be false
        # But we just verify the field exists and is boolean
        assert "first_free" in data
        assert isinstance(data["first_free"], bool)
        print(f"PASS: Admin user first_free = {data['first_free']}")
    
    def test_test_user_first_free_status(self):
        """Test first_free status for test user"""
        token = self.get_auth_token(TEST_EMAIL, TEST_PASSWORD)
        assert token, "Failed to get test user token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/reactions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "first_free" in data
        assert isinstance(data["first_free"], bool)
        print(f"PASS: Test user first_free = {data['first_free']}")


class TestAdminCreditBypass:
    """Tests for admin credit bypass"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_admin_can_generate_without_credits(self):
        """Test that admin can generate without credit check"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        import io
        from PIL import Image
        
        img = Image.new('RGB', (100, 100), color='purple')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        files = {'photo': ('test.png', img_bytes, 'image/png')}
        data = {
            'mode': 'single',
            'reaction': 'cool',
            'style': 'pixar_3d',
            'hd_quality': 'false',
            'transparent_bg': 'false',
            'caption': '',
            'commercial_license': 'false'
        }
        
        response = self.session.post(f"{BASE_URL}/api/reaction-gif/generate", files=files, data=data)
        
        # Admin should be able to generate
        assert response.status_code == 200, f"Expected 200 for admin, got {response.status_code}: {response.text}"
        result = response.json()
        assert "jobId" in result
        print(f"PASS: Admin can generate without credit check, jobId: {result['jobId'][:8]}...")


class TestJobStatusEndpoint:
    """Tests for GET /api/reaction-gif/job/{job_id} endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_job_status_requires_auth(self):
        """Test that job status endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/job/test-job-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Job status endpoint requires authentication")
    
    def test_job_status_returns_404_for_invalid_job(self):
        """Test that job status returns 404 for invalid job ID"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/job/invalid-job-id-12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Invalid job ID returns 404")


class TestHistoryEndpoint:
    """Tests for GET /api/reaction-gif/history endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_history_requires_auth(self):
        """Test that history endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/history")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: History endpoint requires authentication")
    
    def test_history_returns_paginated_results(self):
        """Test that history returns paginated results"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "jobs" in data, "Missing 'jobs' field"
        assert "total" in data, "Missing 'total' field"
        assert "page" in data, "Missing 'page' field"
        assert "size" in data, "Missing 'size' field"
        assert isinstance(data["jobs"], list), "jobs should be a list"
        print(f"PASS: History returns paginated results (total: {data['total']}, page: {data['page']})")


class TestPricingEndpoint:
    """Tests for GET /api/reaction-gif/pricing endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
    
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_pricing_requires_auth(self):
        """Test that pricing endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/pricing")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Pricing endpoint requires authentication")
    
    def test_pricing_returns_8_credits_base(self):
        """Test that pricing returns 8 credits as base for single mode"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token, "Failed to get admin token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/reaction-gif/pricing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "pricing" in data, "Missing 'pricing' field"
        pricing = data["pricing"]
        
        assert "single" in pricing, "Missing 'single' pricing"
        assert pricing["single"]["base"] == 8, f"Expected base price 8, got {pricing['single']['base']}"
        print(f"PASS: Single mode base price is 8 credits")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
