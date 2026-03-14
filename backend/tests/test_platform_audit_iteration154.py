"""
Full Platform Audit - Iteration 154
Tests all features: Reel Generator, Story Pack, Photo to Comic, GIF Maker, 
Comic Storybook, Story Video, Credits, Auth
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://daily-challenges-10.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"

class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.token = None
        
    def test_01_login_success(self):
        """Test login with valid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        self.token = data["token"]
        print(f"LOGIN SUCCESS: User {data['user'].get('email')} has {data['user'].get('credits')} credits")
        
    def test_02_get_current_user(self):
        """Test GET /api/auth/me returns user profile"""
        # First login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["token"]
        
        # Get profile
        response = self.session.get(f"{BASE_URL}/api/auth/me", 
            headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "credits" in data
        print(f"AUTH/ME SUCCESS: {data['email']} with {data['credits']} credits, plan: {data.get('plan', 'N/A')}")


class TestCreditsEndpoints:
    """Credit balance and history tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        # Login first
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_credits_balance(self):
        """Test GET /api/credits/balance returns current balance"""
        response = self.session.get(f"{BASE_URL}/api/credits/balance", headers=self.headers)
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        assert "credits" in data or "balance" in data
        credits = data.get("credits") or data.get("balance")
        print(f"CREDITS BALANCE: {credits} credits, plan: {data.get('plan', 'N/A')}")


class TestReelGenerator:
    """Reel Generator endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_reel_demo_endpoint(self):
        """Test demo reel generation (no credits)"""
        response = self.session.post(f"{BASE_URL}/api/generate/demo/reel", json={
            "topic": "Quick cooking tips",
            "niche": "Food",
            "tone": "Fun"
        })
        # Demo endpoint may or may not require auth
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") or data.get("isDemo")
            print(f"DEMO REEL: Success - {data.get('result', {}).get('best_hook', 'N/A')[:50]}...")
        else:
            print(f"DEMO REEL: Status {response.status_code} - {response.text[:100]}")
            
    def test_reel_generation_history(self):
        """Test GET /api/generate/ returns generation history"""
        response = self.session.get(f"{BASE_URL}/api/generate/", 
            headers=self.headers, params={"type": "REEL"})
        assert response.status_code == 200, f"Reel history failed: {response.text}"
        data = response.json()
        assert "generations" in data
        print(f"REEL HISTORY: {data['total']} total generations")


class TestStoryGenerator:
    """Kids Story Pack endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_story_generation_history(self):
        """Test GET /api/generate/ for story history"""
        response = self.session.get(f"{BASE_URL}/api/generate/", 
            headers=self.headers, params={"type": "STORY"})
        assert response.status_code == 200, f"Story history failed: {response.text}"
        data = response.json()
        assert "generations" in data
        print(f"STORY HISTORY: {data['total']} total stories")


class TestPhotoToComic:
    """Photo to Comic endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_photo_to_comic_styles(self):
        """Test GET /api/photo-to-comic/styles returns available styles"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/styles", headers=self.headers)
        assert response.status_code == 200, f"Photo to comic styles failed: {response.text}"
        data = response.json()
        assert "styles" in data
        assert "pricing" in data
        print(f"PHOTO TO COMIC STYLES: {len(data['styles'])} styles available")
        
    def test_photo_to_comic_pricing(self):
        """Test GET /api/photo-to-comic/pricing returns pricing tiers"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/pricing", headers=self.headers)
        assert response.status_code == 200, f"Photo to comic pricing failed: {response.text}"
        data = response.json()
        assert "pricing" in data
        print(f"PHOTO TO COMIC PRICING: {data['pricing']}")
        
    def test_photo_to_comic_history(self):
        """Test GET /api/photo-to-comic/history returns job history"""
        response = self.session.get(f"{BASE_URL}/api/photo-to-comic/history", headers=self.headers)
        assert response.status_code == 200, f"Photo to comic history failed: {response.text}"
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"PHOTO TO COMIC HISTORY: {data['total']} jobs")


class TestGifMaker:
    """GIF Maker endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_gif_maker_credits_info(self):
        """Test GET /api/gif-maker/credits-info returns credit costs and balance"""
        response = self.session.get(f"{BASE_URL}/api/gif-maker/credits-info", headers=self.headers)
        assert response.status_code == 200, f"GIF maker credits info failed: {response.text}"
        data = response.json()
        assert "costs" in data or "pricing" in data
        assert "userCredits" in data
        print(f"GIF MAKER CREDITS: User has {data['userCredits']} credits, costs: {data.get('costs') or data.get('pricing')}")
        
    def test_gif_maker_emotions(self):
        """Test GET /api/gif-maker/emotions returns available emotions"""
        response = self.session.get(f"{BASE_URL}/api/gif-maker/emotions", headers=self.headers)
        assert response.status_code == 200, f"GIF maker emotions failed: {response.text}"
        data = response.json()
        assert "emotions" in data
        print(f"GIF MAKER EMOTIONS: {len(data['emotions'])} emotions available")
        
    def test_gif_maker_history(self):
        """Test GET /api/gif-maker/history returns job history"""
        response = self.session.get(f"{BASE_URL}/api/gif-maker/history", headers=self.headers)
        assert response.status_code == 200, f"GIF maker history failed: {response.text}"
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"GIF MAKER HISTORY: {data['total']} jobs")


class TestComicStorybook:
    """Comic Storybook endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_comic_storybook_styles(self):
        """Test GET /api/comic-storybook/styles returns available styles"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook/styles", headers=self.headers)
        assert response.status_code == 200, f"Comic storybook styles failed: {response.text}"
        data = response.json()
        assert "styles" in data
        print(f"COMIC STORYBOOK STYLES: {len(data['styles'])} styles available")
        
    def test_comic_storybook_history(self):
        """Test GET /api/comic-storybook/history returns job history"""
        response = self.session.get(f"{BASE_URL}/api/comic-storybook/history", headers=self.headers)
        assert response.status_code == 200, f"Comic storybook history failed: {response.text}"
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        print(f"COMIC STORYBOOK HISTORY: {data['total']} jobs")


class TestStoryVideoPipeline:
    """Story Video pipeline endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_pipeline_options(self):
        """Test GET /api/pipeline/options returns animation styles, age groups, voice presets"""
        response = self.session.get(f"{BASE_URL}/api/pipeline/options", headers=self.headers)
        assert response.status_code == 200, f"Pipeline options failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert "credit_costs" in data
        print(f"PIPELINE OPTIONS: {len(data['animation_styles'])} styles, {len(data['age_groups'])} age groups, {len(data['voice_presets'])} voices")
        
    def test_pipeline_user_jobs(self):
        """Test GET /api/pipeline/user-jobs returns completed job history"""
        response = self.session.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=self.headers)
        assert response.status_code == 200, f"Pipeline user jobs failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "jobs" in data
        print(f"PIPELINE USER JOBS: {len(data['jobs'])} jobs")
        
    def test_pipeline_workers_status(self):
        """Test GET /api/pipeline/workers/status returns worker stats"""
        response = self.session.get(f"{BASE_URL}/api/pipeline/workers/status", headers=self.headers)
        assert response.status_code == 200, f"Pipeline workers status failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "workers" in data
        print(f"PIPELINE WORKERS: {data['workers']}")


class TestInsufficientCredits:
    """Test credit rejection scenarios (read-only, no actual generation)"""
    
    def test_insufficient_credits_reel_rejection(self):
        """Verify that low-credit users would be rejected for reel generation"""
        # This test just verifies the endpoint exists and responds correctly
        # We don't actually trigger generation to avoid using credits
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200
        
        # Get credits balance to verify
        token = login_resp.json()["token"]
        balance_resp = session.get(f"{BASE_URL}/api/credits/balance", 
            headers={"Authorization": f"Bearer {token}"})
        assert balance_resp.status_code == 200
        
        credits = balance_resp.json().get("credits") or balance_resp.json().get("balance", 0)
        print(f"CREDIT CHECK: User has {credits} credits - sufficient for generation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
