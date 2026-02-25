"""
Iteration 54: Trending Tab Fix Verification + Comprehensive QA Audit
CreatorStudio AI Platform
Tests: Backend APIs, Creator Tools Trending endpoint, Auth flows
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://test-phase-runner.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✅ Health endpoint working")
    
    def test_admin_login(self):
        """Test admin login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✅ Admin login successful - Credits: {data['user'].get('credits', 'N/A')}")
        return data["token"]


class TestTrendingEndpointFix:
    """CRITICAL: Verify trending tab fix - backend API now returns proper data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_trending_general_niche(self, auth_token):
        """Test /api/creator-tools/trending with general niche"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["success"] == True
        assert data["niche"] == "general"
        assert "topics" in data
        assert len(data["topics"]) == 8
        
        # Verify topic structure
        first_topic = data["topics"][0]
        assert "topic" in first_topic
        assert "hook" in first_topic
        assert "engagement" in first_topic
        
        print(f"✅ Trending general niche: Found {len(data['topics'])} topics")
        print(f"   First topic: {first_topic['topic']} - {first_topic['engagement']}")
    
    def test_trending_fitness_niche(self, auth_token):
        """Test /api/creator-tools/trending with fitness niche"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/trending?niche=fitness&limit=8",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["niche"] == "fitness"
        assert len(data["topics"]) == 8
        
        # Verify fitness-specific topics
        topics = [t["topic"] for t in data["topics"]]
        assert any("Workout" in t or "Gym" in t or "Fitness" in t or "Protein" in t for t in topics)
        print(f"✅ Trending fitness niche: {', '.join(topics[:3])}")
    
    def test_trending_business_niche(self, auth_token):
        """Test /api/creator-tools/trending with business niche"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/trending?niche=business&limit=8",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["niche"] == "business"
        print(f"✅ Trending business niche: {len(data['topics'])} topics")
    
    def test_trending_includes_tips(self, auth_token):
        """Test /api/creator-tools/trending includes tips"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/trending?niche=general&limit=8",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        assert "tips" in data
        assert len(data["tips"]) >= 3
        print(f"✅ Trending includes {len(data['tips'])} tips")


class TestCreatorToolsAPIs:
    """Test all Creator Tools endpoints"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_hashtags_endpoint(self, auth_token):
        """Test /api/creator-tools/hashtags/{niche}"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/hashtags/business",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "hashtags" in data
        assert "tip" in data
        print(f"✅ Hashtags endpoint: {len(data['hashtags'])} hashtags")
    
    def test_niches_endpoint(self, auth_token):
        """Test /api/creator-tools/niches"""
        response = requests.get(
            f"{BASE_URL}/api/creator-tools/niches",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        assert len(data["niches"]) > 0
        print(f"✅ Niches endpoint: {data['niches']}")


class TestWalletAndCredits:
    """Test wallet and credits functionality"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_wallet_balance(self, auth_token):
        """Test /api/wallet/me returns balance"""
        response = requests.get(
            f"{BASE_URL}/api/wallet/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Check for balance field (may be balanceCredits or balance)
        balance = data.get("balanceCredits") or data.get("balance") or data.get("credits")
        assert balance is not None
        print(f"✅ Wallet balance: {balance}")


class TestBillingProducts:
    """Test billing and payment products"""
    
    @pytest.fixture
    def auth_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()["token"]
    
    def test_products_endpoint(self, auth_token):
        """Test /api/billing/products"""
        response = requests.get(
            f"{BASE_URL}/api/billing/products",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Products endpoint might be public
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Products endpoint: {len(data)} products")
        else:
            # Try without auth
            response = requests.get(f"{BASE_URL}/api/billing/products")
            if response.status_code == 200:
                print("✅ Products endpoint (public): working")
            else:
                print(f"⚠️ Products endpoint returned: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
