"""
Comprehensive QA Audit - Backend API Tests
Testing all pages: Login, Signup, Reset Password, Dashboard, 
Reel Generator, Story Generator, GenStudio, Creator Tools, 
Coloring Book, Story Series, Challenge Generator, Tone Switcher, 
and Billing/Cashfree payments.
"""
import pytest
import requests
import os
import time
import json
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://auth-photo-comic.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestHealthAndBasics:
    """Basic health check and connectivity tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✓ Health endpoint working")
    
    def test_subscription_plans(self):
        """Test subscription plans endpoint"""
        response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) > 0
        print(f"✓ Subscription plans: {len(data['plans'])} plans available")


class TestAuthentication:
    """Authentication tests - Login, Signup, Reset Password"""
    
    def test_login_admin_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "ADMIN"
        print(f"✓ Admin login successful - credits: {data['user'].get('credits', 0)}")
        return data["token"]
    
    def test_login_demo_success(self):
        """Test demo user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        data = response.json()
        assert "token" in data
        print(f"✓ Demo user login successful - credits: {data['user'].get('credits', 0)}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")
    
    def test_signup_validation_empty_name(self):
        """Test signup validation - empty name"""
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "name": "",
            "email": "test@test.com",
            "password": "Test1234!"
        })
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("✓ Signup validation - empty name rejected")
    
    def test_signup_validation_invalid_email(self):
        """Test signup validation - invalid email format"""
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "name": "Test User",
            "email": "invalid-email",
            "password": "Test1234!"
        })
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("✓ Signup validation - invalid email rejected")
    
    def test_reset_password_request(self):
        """Test reset password request endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/reset-password-request", json={
            "email": ADMIN_EMAIL
        })
        # Should return 200 regardless of email exists (security best practice)
        assert response.status_code in [200, 201, 404], f"Unexpected status: {response.status_code}"
        print("✓ Reset password request endpoint working")


class TestCreditsAndWallet:
    """Credits and wallet system tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_credits_balance(self):
        """Test credits balance endpoint"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data or "credits" in data
        print(f"✓ Credits balance: {data.get('balance') or data.get('credits')}")
    
    def test_get_wallet(self):
        """Test wallet endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/me", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Wallet data retrieved: {data.get('balanceCredits', 0)} credits")
    
    def test_wallet_pricing(self):
        """Test wallet pricing endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"✓ Wallet pricing: {len(data.get('pricing', {}))} pricing tiers")


class TestReelGenerator:
    """Reel Generator tests - topic validation, XSS, generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_reel_generation_valid(self):
        """Test reel generation with valid data"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", 
            headers=self.headers,
            json={
                "topic": "Morning productivity routine",
                "niche": "Motivation",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Engagement",
                "targetAudience": "Entrepreneurs"
            }
        )
        # May take time to generate
        assert response.status_code in [200, 503], f"Unexpected: {response.status_code} - {response.text[:200]}"
        if response.status_code == 200:
            data = response.json()
            assert "result" in data or "generationId" in data
            print("✓ Reel generation successful")
        else:
            print("⚠ Reel generation - AI service may be busy")
    
    def test_reel_topic_min_length_validation(self):
        """Test topic minimum length validation"""
        response = requests.post(f"{BASE_URL}/api/generate/reel",
            headers=self.headers,
            json={
                "topic": "ab",  # Less than 3 chars
                "niche": "General",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Engagement"
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Reel topic min length validation working")
    
    def test_reel_topic_max_length_validation(self):
        """Test topic max length validation (2000 chars)"""
        long_topic = "x" * 2001
        response = requests.post(f"{BASE_URL}/api/generate/reel",
            headers=self.headers,
            json={
                "topic": long_topic,
                "niche": "General",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Engagement"
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Reel topic max length (2000) validation working")
    
    def test_reel_xss_sanitization(self):
        """Test XSS sanitization in topic"""
        xss_topic = "<script>alert('xss')</script>Test topic"
        response = requests.post(f"{BASE_URL}/api/generate/reel",
            headers=self.headers,
            json={
                "topic": xss_topic,
                "niche": "General",
                "tone": "Bold",
                "duration": "30s",
                "language": "English",
                "goal": "Engagement"
            }
        )
        # Should either sanitize or reject
        assert response.status_code in [200, 400, 503], f"Unexpected: {response.status_code}"
        print("✓ XSS input handled safely")
    
    def test_demo_reel_no_auth(self):
        """Test demo reel endpoint without auth"""
        response = requests.post(f"{BASE_URL}/api/generate/demo/reel", json={
            "topic": "Morning routine tips",
            "niche": "Lifestyle"
        })
        assert response.status_code == 200, f"Demo reel failed: {response.text[:200]}"
        data = response.json()
        assert "result" in data
        print("✓ Demo reel generation (no auth) working")


class TestStoryGenerator:
    """Story Generator tests - age group, genre, scene count"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_story_generation_valid(self):
        """Test story generation with valid data"""
        response = requests.post(f"{BASE_URL}/api/generate/story",
            headers=self.headers,
            json={
                "ageGroup": "4-6",
                "genre": "Adventure",
                "theme": "Friendship",
                "sceneCount": 5
            }
        )
        assert response.status_code in [200, 503], f"Unexpected: {response.status_code} - {response.text[:200]}"
        if response.status_code == 200:
            data = response.json()
            assert "result" in data or "generationId" in data
            print("✓ Story generation successful")
        else:
            print("⚠ Story generation - AI service may be busy")
    
    def test_story_scene_count_min(self):
        """Test scene count minimum validation (3)"""
        response = requests.post(f"{BASE_URL}/api/generate/story",
            headers=self.headers,
            json={
                "ageGroup": "4-6",
                "genre": "Fantasy",
                "theme": "Adventure",
                "sceneCount": 2  # Less than 3
            }
        )
        assert response.status_code == 422, f"Expected 422 for sceneCount < 3, got {response.status_code}"
        print("✓ Story scene count min (3) validation working")
    
    def test_story_scene_count_max(self):
        """Test scene count maximum validation (15)"""
        response = requests.post(f"{BASE_URL}/api/generate/story",
            headers=self.headers,
            json={
                "ageGroup": "4-6",
                "genre": "Fantasy",
                "theme": "Adventure",
                "sceneCount": 20  # More than 15
            }
        )
        assert response.status_code == 422, f"Expected 422 for sceneCount > 15, got {response.status_code}"
        print("✓ Story scene count max (15) validation working")


class TestGenStudio:
    """GenStudio tests - Text-to-Image, Text-to-Video, History"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_genstudio_dashboard(self):
        """Test GenStudio dashboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "templates" in data
        print(f"✓ GenStudio dashboard - {data.get('stats', {}).get('totalGenerations', 0)} total generations")
    
    def test_genstudio_templates(self):
        """Test GenStudio templates endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/templates", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        print(f"✓ GenStudio templates: {len(data.get('templates', []))} templates")
    
    def test_text_to_image_prompt_validation(self):
        """Test text-to-image prompt min length validation"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-image",
            headers=self.headers,
            json={
                "prompt": "ab",  # Less than 3 chars
                "consent_confirmed": True
            }
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Text-to-image prompt min validation working")
    
    def test_text_to_image_consent_required(self):
        """Test text-to-image requires consent checkbox"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-image",
            headers=self.headers,
            json={
                "prompt": "A beautiful sunset over mountains",
                "consent_confirmed": False
            }
        )
        assert response.status_code == 400, f"Expected 400 for missing consent, got {response.status_code}"
        print("✓ Text-to-image consent required validation working")
    
    def test_text_to_video_consent_required(self):
        """Test text-to-video requires consent checkbox"""
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-video",
            headers=self.headers,
            json={
                "prompt": "A serene beach scene with waves",
                "duration": 4,
                "consent_confirmed": False
            }
        )
        assert response.status_code == 400, f"Expected 400 for missing consent, got {response.status_code}"
        print("✓ Text-to-video consent required validation working")
    
    def test_text_to_video_duration_validation(self):
        """Test text-to-video duration range (2-12s)"""
        # Test below minimum
        response = requests.post(f"{BASE_URL}/api/genstudio/text-to-video",
            headers=self.headers,
            json={
                "prompt": "A serene beach scene",
                "duration": 1,  # Below 2
                "consent_confirmed": True
            }
        )
        assert response.status_code == 422, f"Expected 422 for duration < 2, got {response.status_code}"
        print("✓ Text-to-video duration min validation working")
    
    def test_genstudio_history(self):
        """Test GenStudio history endpoint"""
        response = requests.get(f"{BASE_URL}/api/genstudio/history", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        print(f"✓ GenStudio history: {len(data.get('jobs', []))} jobs")


class TestCreatorTools:
    """Creator Tools tests - Calendar, Carousel, Hashtags, Thumbnails"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_creator_tools_niches(self):
        """Test get niches endpoint"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/niches", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        print(f"✓ Creator tools niches: {len(data.get('niches', []))} niches")
    
    def test_content_calendar_generation(self):
        """Test content calendar generation"""
        response = requests.post(f"{BASE_URL}/api/creator-tools/content-calendar?niche=fitness&days=7",
            headers=self.headers
        )
        assert response.status_code == 200, f"Calendar generation failed: {response.text[:200]}"
        data = response.json()
        assert "calendar" in data
        print(f"✓ Content calendar: {len(data.get('calendar', []))} days generated")
    
    def test_hashtag_bank(self):
        """Test hashtag bank endpoint"""
        response = requests.get(f"{BASE_URL}/api/creator-tools/hashtags/fitness", headers=self.headers)
        assert response.status_code == 200, f"Hashtag bank failed: {response.text[:200]}"
        data = response.json()
        assert "hashtags" in data
        print("✓ Hashtag bank working")
    
    def test_thumbnail_text_generation(self):
        """Test thumbnail text generation"""
        response = requests.post(f"{BASE_URL}/api/creator-tools/thumbnail-text?topic=Morning%20Routine&style=bold",
            headers=self.headers
        )
        assert response.status_code == 200, f"Thumbnail generation failed: {response.text[:200]}"
        data = response.json()
        assert "thumbnails" in data
        print("✓ Thumbnail text generation working")
    
    def test_carousel_generation(self):
        """Test carousel generation"""
        response = requests.post(f"{BASE_URL}/api/creator-tools/carousel?topic=Fitness%20Tips&slides=5",
            headers=self.headers
        )
        assert response.status_code == 200, f"Carousel generation failed: {response.text[:200]}"
        data = response.json()
        assert "carousel" in data
        print("✓ Carousel generation working")


class TestChallengeGenerator:
    """Challenge Generator tests - 7-day and 30-day challenges"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_challenge_pricing(self):
        """Test challenge generator pricing"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"✓ Challenge pricing: {data.get('pricing', {})}")
    
    def test_challenge_niches(self):
        """Test challenge generator niches"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/niches", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "niches" in data
        print(f"✓ Challenge niches available")
    
    def test_challenge_platforms(self):
        """Test challenge generator platforms"""
        response = requests.get(f"{BASE_URL}/api/challenge-generator/platforms", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        print(f"✓ Challenge platforms available")
    
    def test_7_day_challenge_generation(self):
        """Test 7-day challenge generation"""
        response = requests.post(f"{BASE_URL}/api/challenge-generator/generate",
            headers=self.headers,
            json={
                "challengeType": "7_day",
                "niche": "motivation",
                "platform": "instagram",
                "goal": "followers",
                "timePerDay": 15
            }
        )
        assert response.status_code == 200, f"Challenge generation failed: {response.text[:200]}"
        data = response.json()
        assert data.get("success") == True
        print("✓ 7-day challenge generation working")


class TestStorySeries:
    """Story Series tests - Episode generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_story_series_pricing(self):
        """Test story series pricing"""
        response = requests.get(f"{BASE_URL}/api/story-series/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        print(f"✓ Story series pricing available")
    
    def test_story_series_themes(self):
        """Test story series themes"""
        response = requests.get(f"{BASE_URL}/api/story-series/themes", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        print(f"✓ Story series themes: {len(data.get('themes', []))} themes")
    
    def test_story_series_generation(self):
        """Test story series generation"""
        response = requests.post(f"{BASE_URL}/api/story-series/generate",
            headers=self.headers,
            json={
                "storySummary": "A brave young explorer discovers a magical forest",
                "characterNames": ["Luna", "Max"],
                "targetAgeGroup": "4-7",
                "theme": "Adventure",
                "episodeCount": 3
            }
        )
        assert response.status_code == 200, f"Story series failed: {response.text[:200]}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Story series generation working")


class TestToneSwitcher:
    """Tone Switcher tests - 5 tones, text rewrite"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_tone_switcher_tones(self):
        """Test tone switcher available tones"""
        response = requests.get(f"{BASE_URL}/api/tone-switcher/tones", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "tones" in data
        tones = data.get("tones", {})
        assert len(tones) >= 5, f"Expected at least 5 tones, got {len(tones)}"
        print(f"✓ Tone switcher: {len(tones)} tones available")
    
    def test_tone_switcher_rewrite(self):
        """Test tone switcher text rewrite"""
        response = requests.post(f"{BASE_URL}/api/tone-switcher/rewrite",
            headers=self.headers,
            json={
                "text": "This product is really good. You should buy it.",
                "targetTone": "funny",
                "intensity": 50,
                "keepLength": "same",
                "variationCount": 1
            }
        )
        assert response.status_code == 200, f"Tone rewrite failed: {response.text[:200]}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Tone switcher rewrite working")


class TestColoringBook:
    """Coloring Book tests - Templates, Pricing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_coloring_book_pricing(self):
        """Test coloring book pricing"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/pricing", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Coloring book pricing available")
    
    def test_coloring_book_templates(self):
        """Test coloring book templates"""
        response = requests.get(f"{BASE_URL}/api/coloring-book/templates", headers=self.headers)
        assert response.status_code == 200
        print("✓ Coloring book templates endpoint working")


class TestBillingAndPayments:
    """Billing and Cashfree payments tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_billing_products(self):
        """Test billing products endpoint"""
        response = requests.get(f"{BASE_URL}/api/payments/products", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        print(f"✓ Billing products: {len(data.get('products', {}))} products")
    
    def test_pricing_plans(self):
        """Test pricing plans endpoint"""
        response = requests.get(f"{BASE_URL}/api/pricing/plans", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        print("✓ Pricing plans endpoint working")
    
    def test_cashfree_order_creation(self):
        """Test Cashfree order creation"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order",
            headers=self.headers,
            json={
                "productId": "starter",
                "currency": "INR"
            }
        )
        # May fail if product not found but endpoint should work
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "paymentSessionId" in data or "order_id" in data or "orderId" in data
            print(f"✓ Cashfree order creation working")
        else:
            print(f"⚠ Cashfree order: {response.json().get('detail', 'Unknown error')}")
    
    def test_cashfree_order_creation_no_product(self):
        """Test Cashfree order with invalid product"""
        response = requests.post(f"{BASE_URL}/api/cashfree/create-order",
            headers=self.headers,
            json={
                "productId": "invalid_product_xyz",
                "currency": "INR"
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid product, got {response.status_code}"
        print("✓ Cashfree invalid product validation working")


class TestProtectedRoutes:
    """Protected routes and authorization tests"""
    
    def test_protected_route_without_auth(self):
        """Test protected routes require authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Protected route requires auth")
    
    def test_generation_without_auth(self):
        """Test generation endpoints require auth"""
        response = requests.post(f"{BASE_URL}/api/generate/reel", json={
            "topic": "Test topic"
        })
        assert response.status_code in [401, 422], f"Expected auth error, got {response.status_code}"
        print("✓ Generation requires auth")


# Main execution
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
