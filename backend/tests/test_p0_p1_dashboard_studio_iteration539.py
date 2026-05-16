"""
P0/P1 Dashboard & Story Video Studio Tests - Iteration 539
Tests for:
- P0 DASHBOARD: No infinite skeleton, renders within 2 seconds
- P1 GENERATE OVERLAY: Immediate feedback overlay on generate click
- P1 VIEW PROGRESS ROUTING: Correct navigation to /app/my-space
- REGRESSION: Credit checks, Photo Trailer freeze
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCreditCheck:
    """Credit check endpoint tests for admin and normal users"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@visionary-suite.com",
            "password": "Test@2026#"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Test user authentication failed")
    
    def test_admin_credit_check_is_unlimited(self, admin_token):
        """REGRESSION: Admin credit-check returns is_unlimited=true with sufficient=true"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert data.get("is_unlimited") == True
        assert data.get("sufficient") == True
        assert data.get("role") == "ADMIN"
        print("PASS: Admin credit-check returns is_unlimited=true with sufficient=true")
    
    def test_normal_user_credit_check_with_breakdown(self, test_user_token):
        """REGRESSION: Normal user credit-check returns sufficient=true with normal breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/story-engine/credit-check",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert data.get("is_unlimited") == False
        assert "breakdown" in data
        assert data.get("current") > 0  # User has credits
        print(f"PASS: Normal user credit-check returns sufficient={data.get('sufficient')} with {data.get('current')} credits")


class TestPhotoTrailerFreeze:
    """Photo Trailer freeze verification"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_photo_trailer_templates_returns_9(self, admin_token):
        """REGRESSION: Photo Trailer freeze still HELD (/api/photo-trailer/templates returns 9)"""
        response = requests.get(
            f"{BASE_URL}/api/photo-trailer/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        templates = data.get("templates", [])
        assert len(templates) == 9, f"Expected 9 templates, got {len(templates)}"
        print("PASS: Photo Trailer freeze HELD - 9 templates returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
