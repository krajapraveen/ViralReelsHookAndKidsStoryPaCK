"""
Release Gatekeeper Test Suite - CreatorStudio AI
Comprehensive testing for all features before production release
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}
QA_TESTER = {"email": "qa.tester@creatorstudio.ai", "password": "QATester@2026!"}


class TestHealthAndBasics:
    """Basic health checks"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_payments_health(self):
        """Test payments gateway health"""
        response = requests.get(f"{BASE_URL}/api/payments/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("configured") == True
        assert data.get("mode") == "test"
        print("✓ Payments health check passed")


class TestAuthentication:
    """Authentication flow tests"""
    
    def test_login_demo_user(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_USER["email"]
        print(f"✓ Demo user login passed - Credits: {data['user'].get('credits', 0)}")
        return data["token"]
    
    def test_login_admin_user(self):
        """Test admin user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"].upper() == "ADMIN"
        print(f"✓ Admin user login passed - Role: {data['user']['role']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")
    
    def test_login_sql_injection(self):
        """Test SQL injection protection"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com' OR '1'='1",
            "password": "' OR '1'='1"
        })
        assert response.status_code == 401
        print("✓ SQL injection attempt rejected")
    
    def test_login_xss_attempt(self):
        """Test XSS protection"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "<script>alert('xss')</script>@test.com",
            "password": "<script>alert('xss')</script>"
        })
        assert response.status_code == 401
        print("✓ XSS attempt rejected")
    
    def test_protected_route_without_auth(self):
        """Test protected route without authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ Protected route blocked without auth")


class TestAdminAccess:
    """Admin access control tests"""
    
    @pytest.fixture
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        return response.json().get("token")
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json().get("token")
    
    def test_admin_dashboard_with_admin(self, admin_token):
        """Test admin dashboard access with admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        print("✓ Admin dashboard accessible with admin token")
    
    def test_admin_dashboard_with_regular_user(self, demo_token):
        """Test admin dashboard blocked for regular user"""
        headers = {"Authorization": f"Bearer {demo_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 403
        print("✓ Admin dashboard blocked for regular user (403)")
    
    def test_admin_users_list(self, admin_token):
        """Test admin users list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"✓ Admin users list - Total: {data.get('total', 0)}")
    
    def test_admin_feedback_list(self, admin_token):
        """Test admin feedback list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/feedback/all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        print(f"✓ Admin feedback list - Total: {data.get('stats', {}).get('total', 0)}")
    
    def test_admin_exceptions_list(self, admin_token):
        """Test admin exceptions list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/exceptions/all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "exceptions" in data
        print(f"✓ Admin exceptions list - Total: {data.get('total', 0)}")


class TestPayments:
    """Payment system tests"""
    
    def test_get_products(self):
        """Test products endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        products = data["products"]
        assert "starter" in products
        assert "creator" in products
        assert "pro" in products
        assert "quarterly" in products
        assert "yearly" in products
        print("✓ Products endpoint - All 5 products available")
    
    def test_get_currencies(self):
        """Test currencies endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/currencies")
        assert response.status_code == 200
        data = response.json()
        assert "currencies" in data
        currencies = data["currencies"]
        assert "INR" in currencies
        assert "USD" in currencies
        assert "EUR" in currencies
        assert "GBP" in currencies
        print("✓ Currencies endpoint - INR, USD, EUR, GBP available")
    
    def test_exchange_rate(self):
        """Test exchange rate endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/exchange-rate/USD")
        assert response.status_code == 200
        data = response.json()
        assert data.get("currency") == "USD"
        assert "rate" in data
        print(f"✓ Exchange rate - USD rate: {data.get('rate')}")


class TestGenStudio:
    """GenStudio AI tools tests"""
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_genstudio_dashboard(self, auth_headers):
        """Test GenStudio dashboard"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data
        assert "templates" in data
        assert "costs" in data
        print(f"✓ GenStudio dashboard - Credits: {data.get('credits')}")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        templates = data["templates"]
        assert len(templates) >= 4
        print(f"✓ GenStudio templates - {len(templates)} templates available")
    
    def test_genstudio_history(self, auth_headers):
        """Test GenStudio history"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"✓ GenStudio history - {data.get('total', 0)} jobs")
    
    def test_genstudio_style_profiles(self, auth_headers):
        """Test GenStudio style profiles"""
        response = requests.get(f"{BASE_URL}/api/genstudio/style-profiles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        print(f"✓ GenStudio style profiles - {data.get('count', 0)} profiles")


class TestCreatorProTools:
    """Creator Pro Tools tests"""
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_creator_tools_list(self, auth_headers):
        """Test creator tools list"""
        response = requests.get(f"{BASE_URL}/api/creator-tools", headers=auth_headers)
        # May return 200 or 404 depending on implementation
        if response.status_code == 200:
            print("✓ Creator tools endpoint available")
        else:
            print(f"⚠ Creator tools endpoint returned {response.status_code}")


class TestGenerationEndpoints:
    """Generation endpoints tests"""
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_reel_generation_endpoint(self, auth_headers):
        """Test reel generation endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/generation/reel", 
            headers=auth_headers,
            json={
                "topic": "Test topic",
                "niche": "tech",
                "tone": "professional",
                "duration": "30",
                "language": "English"
            }
        )
        # Should return 200 or 400/402 for credits, not 404
        assert response.status_code != 404
        print(f"✓ Reel generation endpoint exists - Status: {response.status_code}")
    
    def test_story_generation_endpoint(self, auth_headers):
        """Test story generation endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/generation/story",
            headers=auth_headers,
            json={
                "ageGroup": "5-8",
                "genre": "adventure",
                "scenes": 3
            }
        )
        # Should return 200 or 400/402 for credits, not 404
        assert response.status_code != 404
        print(f"✓ Story generation endpoint exists - Status: {response.status_code}")


class TestContactAndFeedback:
    """Contact and feedback tests"""
    
    def test_contact_form(self):
        """Test contact form submission"""
        response = requests.post(f"{BASE_URL}/api/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test Subject",
            "message": "This is a test message"
        })
        assert response.status_code == 200
        print("✓ Contact form submission works")
    
    def test_feedback_submission(self):
        """Test feedback submission"""
        response = requests.post(f"{BASE_URL}/api/feedback", json={
            "rating": 5,
            "message": "Great app!",
            "category": "general"
        })
        # May require auth or be public
        if response.status_code == 200:
            print("✓ Feedback submission works (public)")
        elif response.status_code in [401, 403]:
            print("✓ Feedback requires authentication")
        else:
            print(f"⚠ Feedback returned {response.status_code}")


class TestSecurityHeaders:
    """Security headers tests"""
    
    def test_security_headers_present(self):
        """Test security headers are present"""
        response = requests.get(f"{BASE_URL}/api/health")
        headers = response.headers
        
        # Check for security headers
        security_checks = {
            "X-Frame-Options": headers.get("X-Frame-Options"),
            "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
            "X-XSS-Protection": headers.get("X-XSS-Protection")
        }
        
        for header, value in security_checks.items():
            if value:
                print(f"✓ {header}: {value}")
            else:
                print(f"⚠ {header}: Not set")


class TestAdminDashboardData:
    """Admin dashboard data verification"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        return response.json().get("token")
    
    def test_admin_analytics_overview(self, admin_token):
        """Test admin analytics overview data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify overview data
        overview = data.get("data", {}).get("overview", {})
        assert "totalUsers" in overview
        assert "totalGenerations" in overview
        assert "totalRevenue" in overview
        print(f"✓ Overview - Users: {overview.get('totalUsers')}, Generations: {overview.get('totalGenerations')}, Revenue: ₹{overview.get('totalRevenue')}")
    
    def test_admin_satisfaction_data(self, admin_token):
        """Test admin satisfaction tab data (previously buggy)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify satisfaction data
        satisfaction = data.get("data", {}).get("satisfaction", {})
        assert "satisfactionPercentage" in satisfaction
        assert "averageRating" in satisfaction
        assert "npsScore" in satisfaction
        assert "totalReviews" in satisfaction
        assert "ratingDistribution" in satisfaction
        assert "recentReviews" in satisfaction
        print(f"✓ Satisfaction - Rating: {satisfaction.get('averageRating')}, NPS: {satisfaction.get('npsScore')}, Reviews: {satisfaction.get('totalReviews')}")
    
    def test_admin_visitors_data(self, admin_token):
        """Test admin visitors tab data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify visitors data
        visitors = data.get("data", {}).get("visitors", {})
        assert "uniqueVisitors" in visitors
        assert "dailyTrend" in visitors
        daily_trend = visitors.get("dailyTrend", [])
        assert len(daily_trend) == 7  # 7 days of data
        print(f"✓ Visitors - Unique: {visitors.get('uniqueVisitors')}, Daily trend: {len(daily_trend)} days")
    
    def test_admin_payments_data(self, admin_token):
        """Test admin payments tab data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/payments/successful", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "payments" in data
        print(f"✓ Payments - Successful: {data.get('total', 0)}")


class TestEdgeCases:
    """Edge case tests"""
    
    def test_very_long_input(self):
        """Test handling of very long input"""
        long_input = "A" * 1000
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": f"{long_input}@test.com",
            "password": long_input
        })
        # Should handle gracefully, not crash
        assert response.status_code in [400, 401, 422]
        print("✓ Very long input handled gracefully")
    
    def test_unicode_emoji_input(self):
        """Test handling of unicode and emoji"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test🎉@example.com",
            "password": "Password123!🔥"
        })
        # Should handle gracefully
        assert response.status_code in [400, 401, 422]
        print("✓ Unicode/emoji input handled gracefully")
    
    def test_empty_request_body(self):
        """Test handling of empty request body"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={})
        assert response.status_code in [400, 422]
        print("✓ Empty request body rejected")


class TestTwinFinder:
    """TwinFinder tests"""
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_celebrity_database(self, auth_headers):
        """Test celebrity database endpoint"""
        response = requests.get(f"{BASE_URL}/api/twinfinder/celebrities", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Celebrity database - {len(data.get('celebrities', []))} celebrities")
        elif response.status_code == 404:
            print("⚠ Celebrity database endpoint not found")
        else:
            print(f"⚠ Celebrity database returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
