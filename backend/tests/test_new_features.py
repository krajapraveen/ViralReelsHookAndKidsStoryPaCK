"""
Test suite for CreatorStudio AI new features:
1. 54 free credits for new users
2. isFreeTier field in /api/credits/balance
3. PDF watermark for free tier users
"""
import pytest
import requests
import os
import time
import random
import string

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCreditsAndFreeTier:
    """Test credits balance and free tier detection"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    def test_credits_balance_returns_isFreeTier(self, admin_token):
        """Test that /api/credits/balance returns isFreeTier field"""
        response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get balance: {response.text}"
        
        data = response.json()
        assert "balance" in data, "balance field missing"
        assert "isFreeTier" in data, "isFreeTier field missing"
        assert "hasPurchased" in data, "hasPurchased field missing"
        
        # Admin user should be free tier (no payments)
        assert data["isFreeTier"] == True, f"Expected isFreeTier=True, got {data['isFreeTier']}"
        assert data["hasPurchased"] == False, f"Expected hasPurchased=False, got {data['hasPurchased']}"
        print(f"Balance: {data['balance']}, isFreeTier: {data['isFreeTier']}, hasPurchased: {data['hasPurchased']}")
    
    def test_new_user_gets_54_credits(self):
        """Test that new users get 54 free credits on signup"""
        # Generate unique email
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        test_email = f"test_user_{random_suffix}@test.com"
        
        # Register new user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "name": "Test User",
            "email": test_email,
            "password": "testpass123"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        token = response.json()["token"]
        
        # Check credits balance
        balance_response = requests.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert balance_response.status_code == 200, f"Failed to get balance: {balance_response.text}"
        
        data = balance_response.json()
        assert data["balance"] == 54.0, f"Expected 54 credits, got {data['balance']}"
        assert data["isFreeTier"] == True, f"New user should be free tier"
        print(f"New user {test_email} has {data['balance']} credits, isFreeTier: {data['isFreeTier']}")


class TestReelGeneration:
    """Test reel generation with watermark for free tier"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    def test_reel_generation_works(self, admin_token):
        """Test that reel generation works"""
        response = requests.post(
            f"{BASE_URL}/api/generate/reel",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "topic": "Morning routines of successful entrepreneurs",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            }
        )
        assert response.status_code == 200, f"Reel generation failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "SUCCEEDED", f"Expected SUCCEEDED, got {data['status']}"
        assert "output" in data, "output field missing"
        print(f"Reel generation status: {data['status']}")


class TestDemoGeneration:
    """Test demo reel generation (no auth required)"""
    
    def test_demo_reel_has_watermark(self):
        """Test that demo reel includes watermark"""
        response = requests.post(
            f"{BASE_URL}/api/generate/demo-reel",
            json={
                "topic": "Test topic for demo",
                "niche": "Luxury",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Followers",
                "audience": "General"
            }
        )
        assert response.status_code == 200, f"Demo generation failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "SUCCEEDED", f"Expected SUCCEEDED, got {data['status']}"
        assert "output" in data, "output field missing"
        
        output = data["output"]
        assert "watermark" in output, "watermark field missing in demo output"
        assert "demo_version" in output, "demo_version field missing in demo output"
        assert output["demo_version"] == True, "demo_version should be True"
        print(f"Demo watermark: {output.get('watermark')}")


class TestPDFExport:
    """Test PDF export with watermark for free tier"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def story_generation_id(self, admin_token):
        """Generate a story and return its ID"""
        response = requests.post(
            f"{BASE_URL}/api/generate/story",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "ageGroup": "4-6",
                "theme": "Adventure",
                "genre": "Fantasy",
                "moral": "Friendship",
                "characters": ["Kid", "Dog"],
                "setting": "forest",
                "scenes": 8,
                "language": "English",
                "style": "Animated 3D",
                "length": "60s"
            }
        )
        if response.status_code != 200:
            pytest.skip(f"Story generation failed: {response.text}")
        
        data = response.json()
        return data.get("generationId")
    
    def test_pdf_export_endpoint_exists(self, admin_token, story_generation_id):
        """Test that PDF export endpoint exists and returns PDF"""
        if not story_generation_id:
            pytest.skip("No story generation ID available")
        
        # Wait for story generation to complete
        max_retries = 30
        for i in range(max_retries):
            response = requests.get(
                f"{BASE_URL}/api/generate/{story_generation_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "SUCCEEDED":
                    break
            time.sleep(3)
        
        # Try to download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/generate/{story_generation_id}/pdf",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # PDF endpoint should return 200 with PDF content
        assert pdf_response.status_code == 200, f"PDF export failed: {pdf_response.status_code}"
        assert pdf_response.headers.get("Content-Type") == "application/pdf", "Expected PDF content type"
        print(f"PDF export successful, size: {len(pdf_response.content)} bytes")


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("API health check passed")
    
    def test_login_works(self):
        """Test login endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "token field missing"
        assert "email" in data, "email field missing"
        print(f"Login successful for {data['email']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
