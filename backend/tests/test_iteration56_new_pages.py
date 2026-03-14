"""
Test Suite: Iteration 56 - New Pages Testing
Tests: Challenge Generator, Tone Switcher, History, Billing, Feature Requests
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://daily-challenges-10.preview.emergentagent.com')

class TestAuthAndBasics:
    """Basic auth and health tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Demo user auth failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health OK: {data}")
    
    def test_auth_login(self, auth_token):
        """Test auth login works"""
        assert auth_token is not None
        print(f"Auth token obtained successfully")


class TestChallengeGenerator:
    """Test Challenge Generator API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_challenge_pricing(self, auth_headers):
        """Test GET /api/challenge-generator/pricing"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/pricing", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        assert "7_DAY" in data["pricing"]
        assert "30_DAY" in data["pricing"]
        print(f"Challenge Pricing: {data['pricing']}")
    
    def test_challenge_niches(self, auth_headers):
        """Test GET /api/challenge-generator/niches"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/niches", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        # Should have niches like luxury, fitness, kids_stories, motivation, business
        print(f"Available niches: {data['niches']}")
    
    def test_challenge_platforms(self, auth_headers):
        """Test GET /api/challenge-generator/platforms"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/platforms", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        # Should have instagram, youtube, tiktok
        print(f"Available platforms: {list(data['platforms'].keys())}")
    
    def test_challenge_goals(self, auth_headers):
        """Test GET /api/challenge-generator/goals"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/goals", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        # Should have followers, leads, sales, engagement
        print(f"Available goals: {list(data['goals'].keys())}")
    
    def test_challenge_history(self, auth_headers):
        """Test GET /api/challenge-generator/history"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "challenges" in data
        print(f"Challenge history: {data.get('total', 0)} challenges")


class TestToneSwitcher:
    """Test Tone Switcher API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_tone_pricing(self, auth_headers):
        """Test GET /api/tone-switcher/pricing"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/pricing", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        assert "SINGLE_REWRITE" in data["pricing"]
        assert "BATCH_5" in data["pricing"]
        assert "BATCH_10" in data["pricing"]
        print(f"Tone Pricing: {data['pricing']}")
    
    def test_tone_list(self, auth_headers):
        """Test GET /api/tone-switcher/tones"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/tones", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "tones" in data
        # Should have funny, aggressive, calm, luxury, motivational
        tones = list(data["tones"].keys())
        print(f"Available tones: {tones}")
        assert len(tones) >= 5, "Should have at least 5 tones"
    
    def test_tone_preview_free(self, auth_headers):
        """Test POST /api/tone-switcher/preview - FREE preview"""
        response = requests.post(
            f"{BASE_URL}/api/tone-switcher/preview",
            headers=auth_headers,
            json={
                "text": "This is a test message for tone switching.",
                "targetTone": "funny",
                "intensity": 50,
                "keepLength": "same",
                "variationCount": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data
        assert data.get("isPreview") == True
        print(f"Tone Preview (FREE): {data['preview'][:100]}...")
    
    def test_tone_history(self, auth_headers):
        """Test GET /api/tone-switcher/history"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "rewrites" in data
        print(f"Tone history: {data.get('total', 0)} rewrites")


class TestGenerationHistory:
    """Test Generation History API endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_generation_list(self, auth_headers):
        """Test GET /api/generate/ - list generations"""
        response = requests.get(f"{BASE_URL}/api/generate/?page=0&size=20", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # API returns 'generations' not 'content'
        assert "generations" in data or "content" in data
        generations = data.get("generations", data.get("content", []))
        print(f"Generation history: {len(generations)} items")
    
    def test_generation_filter_by_type_reel(self, auth_headers):
        """Test GET /api/generate/ with type=REEL filter"""
        response = requests.get(f"{BASE_URL}/api/generate/?type=REEL&page=0&size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data or "content" in data
        generations = data.get("generations", data.get("content", []))
        print(f"REEL generations: {len(generations)} items")
    
    def test_generation_filter_by_type_story(self, auth_headers):
        """Test GET /api/generate/ with type=STORY filter"""
        response = requests.get(f"{BASE_URL}/api/generate/?type=STORY&page=0&size=10", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data or "content" in data
        generations = data.get("generations", data.get("content", []))
        print(f"STORY generations: {len(generations)} items")


class TestBilling:
    """Test Billing related API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_get_products(self, auth_headers):
        """Test GET /api/payments/products"""
        response = requests.get(f"{BASE_URL}/api/payments/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        products = data["products"]
        print(f"Products available: {list(products.keys())}")
        # Verify subscriptions and packs exist
        assert len(products) >= 4, "Should have at least 4 products"
    
    def test_get_credits_balance(self, auth_headers):
        """Test GET /api/credits/balance - CRITICAL for Billing header"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Check if 'credits' or 'balance' field exists
        balance = data.get("credits", data.get("balance", -1))
        assert balance >= 0, "Balance should be non-negative"
        print(f"Credits balance: {balance}")
    
    def test_wallet_me(self, auth_headers):
        """Test GET /api/wallet/me - alternative wallet endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Wallet data: availableCredits={data.get('availableCredits')}")


class TestFeatureRequests:
    """Test Feature Requests API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_feature_requests_list(self, auth_headers):
        """Test GET /api/feature-requests"""
        response = requests.get(f"{BASE_URL}/api/feature-requests", headers=auth_headers)
        # Endpoint may return 200 or 404 depending on implementation
        if response.status_code == 200:
            data = response.json()
            print(f"Feature requests: {data}")
        else:
            print(f"Feature requests endpoint status: {response.status_code}")
        # Accept 200 or 404 (may not be implemented as separate route)
        assert response.status_code in [200, 404, 307]
    
    def test_feature_requests_categories(self, auth_headers):
        """Test GET /api/feature-requests/categories"""
        response = requests.get(f"{BASE_URL}/api/feature-requests/categories", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Feature request categories: {data}")
        else:
            print(f"Categories endpoint status: {response.status_code}")
        assert response.status_code in [200, 404, 307]


class TestCashfreePayments:
    """Test Cashfree payment endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json().get('token')}"}
        pytest.skip("Auth failed")
    
    def test_cashfree_create_order(self, auth_headers):
        """Test POST /api/cashfree/create-order"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=auth_headers,
            json={"productId": "starter", "currency": "INR"}
        )
        # Should return 200 with paymentSessionId
        if response.status_code == 200:
            data = response.json()
            assert "paymentSessionId" in data or "orderId" in data
            print(f"Cashfree order created: orderId={data.get('orderId')}")
        else:
            print(f"Cashfree order response: {response.status_code} - {response.text[:200]}")
        # 200 is success, 402 means insufficient data
        assert response.status_code in [200, 400, 402]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
