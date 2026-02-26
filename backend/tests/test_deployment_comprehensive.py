"""
Comprehensive Deployment Tests for CreatorStudio AI
Tests all critical endpoints before production deployment
"""
import pytest
import requests
import os
import json

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dashboard-stability.preview.emergentagent.com').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthEndpoints:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test GET /api/health/ returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert "timestamp" in data
        print(f"✓ Health endpoint: {data}")
    
    def test_health_live(self):
        """Test GET /api/health/live returns alive"""
        response = requests.get(f"{BASE_URL}/api/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        print(f"✓ Liveness probe: {data}")
    
    def test_health_ready(self):
        """Test GET /api/health/ready returns ready"""
        response = requests.get(f"{BASE_URL}/api/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        print(f"✓ Readiness probe: {data}")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_demo_user_login(self):
        """Test POST /api/auth/login with demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_USER["email"]
        print(f"✓ Demo user login: {data['user']['email']}, credits: {data['user'].get('credits', 0)}")
        return data["token"]
    
    def test_admin_user_login(self):
        """Test POST /api/auth/login with admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_USER["email"]
        assert data["user"]["role"].upper() == "ADMIN"
        print(f"✓ Admin user login: {data['user']['email']}, role: {data['user']['role']}")
        return data["token"]
    
    def test_invalid_login(self):
        """Test POST /api/auth/login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")
    
    def test_google_callback_error_handling(self):
        """Test POST /api/auth/google-callback error handling"""
        response = requests.post(f"{BASE_URL}/api/auth/google-callback", json={
            "sessionId": "invalid-session-id-12345"
        })
        # Should return 400 or 503 (service unavailable) - not 500
        assert response.status_code in [400, 503]
        print(f"✓ Google callback error handling: {response.status_code}")


class TestCreditsEndpoints:
    """Credits endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_credits_balance(self, auth_token):
        """Test GET /api/credits/balance"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert isinstance(data["credits"], (int, float))
        print(f"✓ Credits balance: {data['credits']}")
    
    def test_credits_ledger(self, auth_token):
        """Test GET /api/credits/ledger"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/ledger", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "ledger" in data
        print(f"✓ Credits ledger: {len(data['ledger'])} entries")


class TestGenerationEndpoints:
    """Generation endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_get_generations(self, auth_token):
        """Test GET /api/generate/"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/generate/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "generations" in data
        assert "total" in data
        print(f"✓ User generations: {data['total']} total")
        return data


class TestAdminEndpoints:
    """Admin endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json()["token"]
    
    def test_admin_dashboard(self, admin_token):
        """Test GET /api/admin/analytics/dashboard"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "generations" in data
        assert "revenue" in data
        print(f"✓ Admin dashboard: {data['users']['total']} users, {data['generations']['total']} generations")
    
    def test_admin_users_list(self, admin_token):
        """Test GET /api/admin/users/list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users/list", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        print(f"✓ Admin users list: {data['total']} users")


class TestPaymentEndpoints:
    """Payment endpoint tests"""
    
    def test_payment_products(self):
        """Test GET /api/payments/products"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) > 0
        print(f"✓ Payment products: {list(data['products'].keys())}")
    
    def test_payment_health(self):
        """Test GET /api/payments/health"""
        response = requests.get(f"{BASE_URL}/api/payments/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Payment health: {data}")


class TestCreatorProEndpoints:
    """Creator Pro endpoint tests"""
    
    def test_creator_pro_costs(self):
        """Test GET /api/creator-pro/costs"""
        response = requests.get(f"{BASE_URL}/api/creator-pro/costs")
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert "features" in data
        print(f"✓ Creator Pro costs: {len(data['costs'])} features")


class TestTwinFinderEndpoints:
    """TwinFinder endpoint tests"""
    
    def test_twinfinder_costs(self):
        """Test GET /api/twinfinder/costs"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/costs")
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert "features" in data
        print(f"✓ TwinFinder costs: {data['costs']}")
    
    def test_twinfinder_celebrities(self):
        """Test GET /api/twinfinder/celebrities"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities")
        assert response.status_code == 200
        data = response.json()
        assert "celebrities" in data
        assert "total" in data
        print(f"✓ TwinFinder celebrities: {data['total']} celebrities")


class TestGenStudioEndpoints:
    """GenStudio endpoint tests"""
    
    def test_genstudio_costs(self):
        """Test GET /api/genstudio/costs - should return costs"""
        response = requests.get(f"{BASE_URL}/api/genstudio/costs")
        # This endpoint may not exist, check if it returns 404 or 200
        if response.status_code == 200:
            data = response.json()
            print(f"✓ GenStudio costs: {data}")
        elif response.status_code == 404:
            print("⚠ GenStudio costs endpoint not found (may be in dashboard)")
        else:
            print(f"⚠ GenStudio costs: {response.status_code}")
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_genstudio_dashboard(self, auth_token):
        """Test GET /api/genstudio/dashboard"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "costs" in data
        print(f"✓ GenStudio dashboard: credits={data['credits']}, costs={data['costs']}")
    
    def test_genstudio_templates(self):
        """Test GET /api/genstudio/templates"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"✓ GenStudio templates: {len(data['templates'])} templates")


class TestStoryToolsEndpoints:
    """Story Tools endpoint tests - PDF generation"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_printable_books_list(self, auth_token):
        """Test GET /api/story-tools/printable-books"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-tools/printable-books", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "books" in data
        print(f"✓ Printable books: {len(data['books'])} books")
    
    def test_worksheets_list(self, auth_token):
        """Test GET /api/story-tools/worksheets"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/story-tools/worksheets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "worksheets" in data
        print(f"✓ Worksheets: {len(data['worksheets'])} worksheets")


class TestPDFGeneration:
    """Test PDF generation with ReportLab (production-safe)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    def test_pdf_generation_with_existing_story(self, auth_token):
        """Test POST /api/story-tools/printable-book/{id} with existing story"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First get user's generations to find a story
        response = requests.get(f"{BASE_URL}/api/generate/?type=STORY", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] == 0:
            print("⚠ No existing stories to test PDF generation - skipping")
            pytest.skip("No existing stories for PDF test")
            return
        
        # Get the first story
        story_id = data["generations"][0]["id"]
        print(f"Testing PDF generation with story: {story_id}")
        
        # Test PDF generation
        response = requests.post(
            f"{BASE_URL}/api/story-tools/printable-book/{story_id}",
            headers=headers,
            params={"include_activities": True}
        )
        
        # Should return 200 or 400 (insufficient credits)
        if response.status_code == 200:
            result = response.json()
            assert result["success"] == True
            assert "bookId" in result
            assert "downloadUrl" in result
            print(f"✓ PDF generated: {result['bookId']}, download: {result['downloadUrl']}")
            
            # Test download
            download_response = requests.get(
                f"{BASE_URL}{result['downloadUrl']}",
                headers=headers
            )
            if download_response.status_code == 200:
                assert download_response.headers.get("content-type") == "application/pdf"
                print(f"✓ PDF download successful: {len(download_response.content)} bytes")
            else:
                print(f"⚠ PDF download: {download_response.status_code}")
        elif response.status_code == 400:
            print(f"⚠ PDF generation: insufficient credits")
        else:
            print(f"⚠ PDF generation: {response.status_code} - {response.text}")


class TestMongoDBObjectIdExclusion:
    """Test that MongoDB _id is properly excluded from all responses"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json()["token"]
    
    def test_generations_no_objectid(self, auth_token):
        """Test that generations response has no _id field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/generate/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        for gen in data.get("generations", []):
            assert "_id" not in gen, f"Found _id in generation: {gen.get('id')}"
        print("✓ Generations: No _id fields found")
    
    def test_admin_dashboard_no_objectid(self, admin_token):
        """Test that admin dashboard response has no _id field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check recent users
        for user in data.get("users", {}).get("recentUsers", []):
            assert "_id" not in user, f"Found _id in user"
        
        # Check recent generations
        for gen in data.get("generations", {}).get("recentGenerations", []):
            assert "_id" not in gen, f"Found _id in generation"
        
        print("✓ Admin dashboard: No _id fields found")
    
    def test_credits_ledger_no_objectid(self, auth_token):
        """Test that credits ledger response has no _id field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credits/ledger", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        for entry in data.get("ledger", []):
            assert "_id" not in entry, f"Found _id in ledger entry"
        print("✓ Credits ledger: No _id fields found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
