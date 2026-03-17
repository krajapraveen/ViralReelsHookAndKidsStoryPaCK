"""
Comprehensive QA Test Suite - Iteration 52
Tests ALL GenStudio endpoints including NEW Image-to-Video and Video Remix
"""
import pytest
import requests
import os
import json
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://narrative-suite.preview.emergentagent.com')
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


# ==============================================================================
# HEALTH & AUTH TESTS
# ==============================================================================
class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Health endpoint returns empty on success
        assert response.status_code == 200 or response.status_code == 204
        print("✓ Health endpoint working")
    
    def test_admin_login(self):
        """Test admin login credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token returned"
        assert "user" in data, "No user data returned"
        print(f"✓ Admin login successful, credits: {data['user'].get('credits', 0)}")


# ==============================================================================
# GENSTUDIO ENDPOINTS TESTS
# ==============================================================================
class TestGenStudioEndpoints:
    """Tests for all GenStudio endpoints"""
    
    def test_genstudio_dashboard(self, auth_headers):
        """Test GenStudio dashboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        assert "credits" in data, "Missing credits"
        assert "templates" in data, "Missing templates"
        assert "costs" in data, "Missing costs"
        print(f"✓ GenStudio Dashboard - Credits: {data['credits']}, Templates: {len(data['templates'])}")
    
    def test_genstudio_templates(self, auth_headers):
        """Test GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=auth_headers)
        assert response.status_code == 200, f"Templates failed: {response.text}"
        data = response.json()
        assert "templates" in data, "Missing templates"
        assert len(data["templates"]) >= 8, f"Expected 8+ templates, got {len(data['templates'])}"
        print(f"✓ GenStudio Templates - {len(data['templates'])} templates available")
    
    def test_genstudio_history(self, auth_headers):
        """Test GenStudio history endpoint with pagination"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history?page=1&limit=10", headers=auth_headers)
        assert response.status_code == 200, f"History failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs"
        assert "total" in data, "Missing total count"
        assert "fileExpiryMinutes" in data, "Missing fileExpiryMinutes"
        print(f"✓ GenStudio History - {data['total']} total jobs, page {data.get('page', 1)}")
    
    def test_genstudio_history_with_filters(self, auth_headers):
        """Test GenStudio history with type filter"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history?type_filter=text_to_image", headers=auth_headers)
        assert response.status_code == 200, f"History filter failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs"
        print(f"✓ GenStudio History Filter - {len(data['jobs'])} text_to_image jobs")
    
    def test_genstudio_style_profiles_list(self, auth_headers):
        """Test listing style profiles"""
        response = requests.get(f"{BASE_URL}/api/genstudio/style-profiles", headers=auth_headers)
        assert response.status_code == 200, f"Style profiles failed: {response.text}"
        data = response.json()
        assert "profiles" in data, "Missing profiles"
        print(f"✓ Style Profiles - {len(data['profiles'])} profiles")


# ==============================================================================
# TEXT-TO-IMAGE TESTS
# ==============================================================================
class TestTextToImage:
    """Text-to-Image endpoint tests"""
    
    def test_text_to_image_requires_consent(self, auth_headers):
        """Test text-to-image requires consent confirmation"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-image", 
            headers=auth_headers,
            json={
                "prompt": "A beautiful sunset over mountains",
                "consent_confirmed": False
            }
        )
        assert response.status_code == 400, f"Should require consent, got: {response.status_code}"
        assert "consent" in response.text.lower(), f"Error should mention consent: {response.text}"
        print("✓ Text-to-Image consent validation working")
    
    def test_text_to_image_validation(self, auth_headers):
        """Test text-to-image prompt validation"""
        # Test with very short prompt
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-image",
            headers=auth_headers,
            json={
                "prompt": "ab",  # Too short
                "consent_confirmed": True
            }
        )
        # Should fail validation for short prompt
        assert response.status_code in [400, 422], f"Should validate prompt length: {response.status_code}"
        print("✓ Text-to-Image prompt validation working")


# ==============================================================================
# TEXT-TO-VIDEO TESTS
# ==============================================================================
class TestTextToVideo:
    """Text-to-Video endpoint tests"""
    
    def test_text_to_video_requires_consent(self, auth_headers):
        """Test text-to-video requires consent"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-video",
            headers=auth_headers,
            json={
                "prompt": "A bird flying over a lake",
                "duration": 4,
                "consent_confirmed": False
            }
        )
        assert response.status_code == 400, f"Should require consent: {response.status_code}"
        print("✓ Text-to-Video consent validation working")


# ==============================================================================
# IMAGE-TO-VIDEO TESTS (NEW ENDPOINT)
# ==============================================================================
class TestImageToVideo:
    """Image-to-Video endpoint tests - NEW IMPLEMENTATION"""
    
    def test_image_to_video_endpoint_exists(self, auth_headers):
        """Test that image-to-video endpoint exists (not 404)"""
        # Send minimal request to check endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/genstudio/image-to-video",
            headers=auth_headers
        )
        # Should NOT be 404 (endpoint exists now)
        assert response.status_code != 404, "Image-to-video endpoint should exist (was 404 before)"
        # Expected: 422 (missing required fields) or 400 (validation error)
        assert response.status_code in [400, 422], f"Got status: {response.status_code}"
        print("✓ Image-to-Video endpoint EXISTS (not 404)")
    
    def test_image_to_video_requires_consent(self, auth_headers):
        """Test image-to-video requires consent confirmation"""
        # Create a minimal fake image file
        fake_image = BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR' + b'\x00' * 100)
        fake_image.name = 'test.png'
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/image-to-video",
            headers=auth_headers,
            files={"image": ("test.png", fake_image, "image/png")},
            data={
                "motion_prompt": "Make it fly through the clouds",
                "duration": 4,
                "consent_confirmed": "false"
            }
        )
        assert response.status_code == 400, f"Should require consent: {response.status_code} - {response.text}"
        assert "consent" in response.text.lower(), f"Error should mention consent: {response.text}"
        print("✓ Image-to-Video consent validation working")
    
    def test_image_to_video_validates_file_type(self, auth_headers):
        """Test image-to-video validates file type"""
        # Create a fake text file (wrong type)
        fake_file = BytesIO(b"This is not an image")
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/image-to-video",
            headers=auth_headers,
            files={"image": ("test.txt", fake_file, "text/plain")},
            data={
                "motion_prompt": "Make it move",
                "duration": 4,
                "consent_confirmed": "true"
            }
        )
        assert response.status_code == 400, f"Should reject invalid file type: {response.status_code}"
        print("✓ Image-to-Video file type validation working")
    
    def test_image_to_video_validates_motion_prompt(self, auth_headers):
        """Test motion prompt validation (3-1000 chars)"""
        fake_image = BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR' + b'\x00' * 100)
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/image-to-video",
            headers=auth_headers,
            files={"image": ("test.png", fake_image, "image/png")},
            data={
                "motion_prompt": "ab",  # Too short
                "duration": 4,
                "consent_confirmed": "true"
            }
        )
        assert response.status_code == 400, f"Should validate prompt length: {response.status_code}"
        print("✓ Image-to-Video motion prompt validation working")


# ==============================================================================
# VIDEO REMIX TESTS (NEW ENDPOINT)
# ==============================================================================
class TestVideoRemix:
    """Video Remix endpoint tests - NEW IMPLEMENTATION"""
    
    def test_video_remix_endpoint_exists(self, auth_headers):
        """Test that video-remix endpoint exists (not 404)"""
        response = requests.post(
            f"{BASE_URL}/api/genstudio/video-remix",
            headers=auth_headers
        )
        # Should NOT be 404
        assert response.status_code != 404, "Video-remix endpoint should exist"
        assert response.status_code in [400, 422], f"Got status: {response.status_code}"
        print("✓ Video Remix endpoint EXISTS (not 404)")
    
    def test_video_remix_requires_consent(self, auth_headers):
        """Test video-remix requires consent"""
        # Create a minimal fake video file
        fake_video = BytesIO(b'\x00\x00\x00\x20ftypisom' + b'\x00' * 100)
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/video-remix",
            headers=auth_headers,
            files={"video": ("test.mp4", fake_video, "video/mp4")},
            data={
                "remix_prompt": "Add cinematic color grading",
                "template_style": "dynamic",
                "consent_confirmed": "false"
            }
        )
        assert response.status_code == 400, f"Should require consent: {response.status_code} - {response.text}"
        print("✓ Video Remix consent validation working")
    
    def test_video_remix_validates_file_type(self, auth_headers):
        """Test video-remix validates file type (MP4/WebM/MOV only)"""
        fake_file = BytesIO(b"Not a video file")
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/video-remix",
            headers=auth_headers,
            files={"video": ("test.txt", fake_file, "text/plain")},
            data={
                "remix_prompt": "Add cool effects",
                "template_style": "dynamic",
                "consent_confirmed": "true"
            }
        )
        assert response.status_code == 400, f"Should reject invalid file type: {response.status_code}"
        print("✓ Video Remix file type validation working")
    
    def test_video_remix_validates_prompt(self, auth_headers):
        """Test remix prompt validation (3-1000 chars)"""
        fake_video = BytesIO(b'\x00\x00\x00\x20ftypisom' + b'\x00' * 100)
        
        response = requests.post(
            f"{BASE_URL}/api/genstudio/video-remix",
            headers=auth_headers,
            files={"video": ("test.mp4", fake_video, "video/mp4")},
            data={
                "remix_prompt": "ab",  # Too short
                "template_style": "dynamic",
                "consent_confirmed": "true"
            }
        )
        assert response.status_code == 400, f"Should validate prompt: {response.status_code}"
        print("✓ Video Remix prompt validation working")


# ==============================================================================
# CASHFREE PAYMENT TESTS
# ==============================================================================
class TestCashfreePayments:
    """Cashfree payment gateway tests"""
    
    def test_cashfree_health(self):
        """Test Cashfree health endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/health")
        assert response.status_code == 200, f"Cashfree health failed: {response.text}"
        data = response.json()
        assert data["status"] == "healthy", "Cashfree not healthy"
        assert data["configured"] == True, "Cashfree not configured"
        assert data["environment"] == "production", f"Wrong environment: {data['environment']}"
        print(f"✓ Cashfree Health - {data['environment'].upper()} mode, configured: {data['configured']}")
    
    def test_cashfree_products(self):
        """Test Cashfree products endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/products")
        assert response.status_code == 200, f"Products failed: {response.text}"
        data = response.json()
        assert "products" in data, "Missing products"
        products = data["products"]
        
        # Verify 3 credit packs
        assert "starter" in products, "Missing starter pack"
        assert "creator" in products, "Missing creator pack"
        assert "pro" in products, "Missing pro pack"
        
        # Verify 4 subscriptions
        assert "weekly" in products, "Missing weekly subscription"
        assert "monthly" in products, "Missing monthly subscription"
        assert "quarterly" in products, "Missing quarterly subscription"
        assert "yearly" in products, "Missing yearly subscription"
        
        print(f"✓ Cashfree Products - {len(products)} products (4 subscriptions + 3 packs)")
    
    def test_cashfree_plans_alias(self):
        """Test Cashfree plans endpoint (alias for products)"""
        response = requests.get(f"{BASE_URL}/api/cashfree/plans")
        assert response.status_code == 200, f"Plans failed: {response.text}"
        data = response.json()
        assert "products" in data, "Missing products"
        print("✓ Cashfree Plans alias working")
    
    def test_cashfree_create_order(self, auth_headers):
        """Test Cashfree order creation - returns cf_order_* format"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/create-order",
            headers=auth_headers,
            json={"productId": "starter", "currency": "INR"}
        )
        assert response.status_code == 200, f"Order creation failed: {response.text}"
        data = response.json()
        assert data["success"] == True, "Order not successful"
        assert "orderId" in data, "Missing orderId"
        assert "cfOrderId" in data, "Missing cfOrderId"
        assert "paymentSessionId" in data, "Missing paymentSessionId"
        assert data["orderId"].startswith("cf_order_"), f"Invalid order ID format: {data['orderId']}"
        assert data["environment"] == "production", f"Wrong environment: {data['environment']}"
        print(f"✓ Cashfree Order Created - {data['orderId']} (PRODUCTION mode)")
    
    def test_cashfree_webhook_rejects_invalid_signature(self):
        """Test webhook rejects requests with invalid signature"""
        response = requests.post(
            f"{BASE_URL}/api/cashfree/webhook",
            json={"type": "PAYMENT_SUCCESS_WEBHOOK", "data": {"order": {"order_id": "fake"}}},
            headers={
                "x-webhook-signature": "invalid_signature",
                "x-webhook-timestamp": "1234567890"
            }
        )
        assert response.status_code == 403, f"Webhook should reject invalid signature: {response.status_code}"
        print("✓ Cashfree Webhook signature verification working (rejects invalid)")


# ==============================================================================
# STYLE PROFILE TESTS
# ==============================================================================
class TestStyleProfiles:
    """Style Profile creation and management tests"""
    
    def test_create_style_profile(self, auth_headers):
        """Test creating a style profile (costs 20 credits)"""
        response = requests.post(
            f"{BASE_URL}/api/genstudio/style-profile",
            headers=auth_headers,
            json={
                "name": f"TEST_Profile_QA52",
                "description": "Test profile for QA iteration 52",
                "tags": ["test", "qa"]
            }
        )
        assert response.status_code == 200, f"Profile creation failed: {response.text}"
        data = response.json()
        assert data["success"] == True, "Profile not created"
        assert "profileId" in data, "Missing profileId"
        assert data["creditsUsed"] == 20, f"Wrong credits: {data['creditsUsed']}"
        print(f"✓ Style Profile Created - {data['profileId']} (20 credits)")
        return data["profileId"]


# ==============================================================================
# CREDITS AND WALLET TESTS
# ==============================================================================
class TestCreditsAndWallet:
    """Credits and wallet functionality tests"""
    
    def test_credits_balance(self, auth_headers):
        """Test credits balance endpoint"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=auth_headers)
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        assert "balance" in data, "Missing balance"
        print(f"✓ Credits Balance - {data['balance']} credits")
    
    def test_wallet_me(self, auth_headers):
        """Test wallet endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=auth_headers)
        assert response.status_code == 200, f"Wallet failed: {response.text}"
        data = response.json()
        assert "balanceCredits" in data or "balance" in data, "Missing balance info"
        print(f"✓ Wallet - {data.get('balanceCredits', data.get('balance', 0))} credits")
    
    def test_wallet_jobs(self, auth_headers):
        """Test wallet jobs listing"""
        response = requests.get(f"{BASE_URL}/api/wallet/jobs?limit=10&skip=0", headers=auth_headers)
        assert response.status_code == 200, f"Wallet jobs failed: {response.text}"
        data = response.json()
        assert "jobs" in data, "Missing jobs"
        print(f"✓ Wallet Jobs - {len(data['jobs'])} jobs returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
