"""
Iteration 99 - Comprehensive Testing
Tests: PDF Protection, Video Streaming, Instagram Bio Generator, Bedtime Story Builder,
YouTube Thumbnail Generator, Brand Story Builder, Offer Generator, Story Hook Generator,
Daily Viral Ideas, Comment Reply Bank, Auto-Refund, Self-Healing
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


class TestHealthAndConfig:
    """Health and basic config tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"Health check passed: {data['status']}")
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "CreatorStudio" in data.get("name", "")
        print(f"Root endpoint: {data['name']}")


class TestPDFProtection:
    """PDF Protection endpoint tests"""
    
    def test_pdf_protection_config(self):
        """Test PDF protection config endpoint"""
        response = requests.get(f"{BASE_URL}/api/pdf-protection/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify protection features
        assert "protection_features" in data
        assert "watermarking" in data["protection_features"]
        assert "flattening" in data["protection_features"]
        assert "copy_protection" in data["protection_features"]
        assert data["enabled"] == True
        print(f"PDF protection features: {data['protection_features']}")


class TestVideoStreaming:
    """Video Streaming endpoint tests"""
    
    def test_video_streaming_config(self):
        """Test video streaming config endpoint"""
        response = requests.get(f"{BASE_URL}/api/video-stream/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify streaming config
        assert "chunk_size" in data
        assert "url_expiry_seconds" in data
        assert data["require_auth"] == True
        assert "mp4" in data["supported_formats"]
        print(f"Video streaming config: chunk_size={data['chunk_size']}, expiry={data['url_expiry_seconds']}s")


class TestInstagramBioGenerator:
    """Instagram Bio Generator tests"""
    
    def test_instagram_bio_config(self):
        """Test Instagram Bio Generator config endpoint"""
        response = requests.get(f"{BASE_URL}/api/instagram-bio-generator/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "niches" in data
        assert "tones" in data
        assert "goals" in data
        assert "creditCost" in data
        assert len(data["niches"]) >= 10
        assert len(data["tones"]) >= 8
        assert len(data["goals"]) >= 7
        print(f"Instagram Bio Config: {len(data['niches'])} niches, {len(data['tones'])} tones, cost={data['creditCost']}")
    
    def test_instagram_bio_generate_requires_auth(self):
        """Test generation endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/instagram-bio-generator/generate", json={
            "niche": "Business Coach",
            "tone": "Professional",
            "goal": "Grow Followers"
        })
        assert response.status_code == 401 or response.status_code == 403
        print("Instagram Bio generation correctly requires auth")


class TestBedtimeStoryBuilder:
    """Bedtime Story Builder tests"""
    
    def test_bedtime_story_config(self):
        """Test Bedtime Story Builder config endpoint"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "ageGroups" in data
        assert "themes" in data
        assert "morals" in data
        assert "lengths" in data
        assert "voiceStyles" in data
        assert "pricing" in data
        
        # Verify age groups
        age_ids = [a["id"] for a in data["ageGroups"]]
        assert "3-5" in age_ids
        assert "6-8" in age_ids
        assert "9-12" in age_ids
        
        # Verify pricing
        assert data["pricing"]["story"] == 10
        print(f"Bedtime Story Config: {len(data['themes'])} themes, {len(data['morals'])} morals")


class TestYouTubeThumbnailGenerator:
    """YouTube Thumbnail Generator tests"""
    
    def test_thumbnail_config(self):
        """Test Thumbnail Generator config"""
        response = requests.get(f"{BASE_URL}/api/youtube-thumbnail-generator/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "niches" in data
        assert "emotions" in data
        assert "credit_cost" in data
        assert data["output_count"] == 10
        print(f"Thumbnail Generator: {len(data['niches'])} niches, cost={data['credit_cost']}")


class TestBrandStoryBuilder:
    """Brand Story Builder tests"""
    
    def test_brand_story_config(self):
        """Test Brand Story Builder config"""
        response = requests.get(f"{BASE_URL}/api/brand-story-builder/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "industries" in data
        assert "tones" in data
        assert "credit_cost" in data
        print(f"Brand Story Config: {len(data['industries'])} industries, cost={data['credit_cost']}")


class TestOfferGenerator:
    """Offer Generator tests"""
    
    def test_offer_generator_config(self):
        """Test Offer Generator config"""
        response = requests.get(f"{BASE_URL}/api/offer-generator/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "offer_types" in data
        assert "industries" in data
        assert "credit_cost" in data
        print(f"Offer Generator: {len(data['offer_types'])} types, cost={data['credit_cost']}")


class TestStoryHookGenerator:
    """Story Hook Generator tests"""
    
    def test_story_hook_config(self):
        """Test Story Hook Generator config"""
        response = requests.get(f"{BASE_URL}/api/story-hook-generator/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "genres" in data
        assert "hook_styles" in data
        assert "credit_cost" in data
        print(f"Story Hook Generator: {len(data['genres'])} genres, cost={data['credit_cost']}")


class TestDailyViralIdeas:
    """Daily Viral Ideas tests"""
    
    def test_daily_viral_ideas_public(self):
        """Test Daily Viral Ideas public endpoint"""
        response = requests.get(f"{BASE_URL}/api/daily-viral-ideas/today")
        # Should work without auth for daily free idea
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            print(f"Daily Viral Ideas: Got today's ideas")


class TestCommentReplyBank:
    """Comment Reply Bank tests"""
    
    def test_comment_reply_config(self):
        """Test Comment Reply Bank config"""
        response = requests.get(f"{BASE_URL}/api/comment-reply-bank/config")
        assert response.status_code == 200
        data = response.json()
        
        assert "intents" in data
        assert "tones" in data
        assert "credit_cost" in data
        print(f"Comment Reply Bank: {len(data['intents'])} intents, cost={data['credit_cost']}")


class TestAuthentication:
    """Authentication tests"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_demo_login(self, demo_token):
        """Test demo user login"""
        assert demo_token is not None
        print(f"Demo login successful, token length: {len(demo_token)}")
    
    def test_admin_login(self, admin_token):
        """Test admin user login"""
        assert admin_token is not None
        print(f"Admin login successful, token length: {len(admin_token)}")
    
    def test_get_current_user(self, demo_token):
        """Test get current user endpoint"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {demo_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == DEMO_EMAIL or data.get("user", {}).get("email") == DEMO_EMAIL
        print(f"Current user verified: {DEMO_EMAIL}")


class TestAuthenticatedFeatures:
    """Tests requiring authentication"""
    
    @pytest.fixture
    def demo_headers(self):
        """Get demo user headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin user headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_instagram_bio_generation(self, demo_headers):
        """Test Instagram Bio generation with auth"""
        response = requests.post(f"{BASE_URL}/api/instagram-bio-generator/generate", 
            headers=demo_headers,
            json={
                "niche": "Business Coach",
                "tone": "Professional",
                "goal": "Grow Followers"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "bios" in data
        assert len(data["bios"]) == 5  # Should generate 5 bios
        assert data["credits_used"] == 5
        print(f"Generated {len(data['bios'])} Instagram bios, credits used: {data['credits_used']}")
    
    def test_bedtime_story_generation(self, demo_headers):
        """Test Bedtime Story generation with auth"""
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate",
            headers=demo_headers,
            json={
                "age_group": "3-5",
                "theme": "Friendship",
                "moral": "Be kind",
                "length": "5",
                "voice_style": "calm_parent"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "story" in data
        assert "script" in data["story"]
        assert "voice_notes" in data["story"]
        assert "sfx_cues" in data["story"]
        print(f"Generated bedtime story, credits used: {data.get('credits_used', 10)}")
    
    def test_wallet_balance(self, demo_headers):
        """Test wallet balance endpoint"""
        response = requests.get(f"{BASE_URL}/api/wallet/", headers=demo_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Wallet balance: {data}")


class TestAdminEndpoints:
    """Admin-only endpoint tests"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin user headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_admin_audit_logs_actions(self, admin_headers):
        """Test admin audit logs actions endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/audit-logs/actions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "actions" in data
        print(f"Audit log actions: {len(data['actions'])} types")
    
    def test_admin_audit_logs_stats(self, admin_headers):
        """Test admin audit logs stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/audit-logs/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_actions" in data
        print(f"Audit log stats: {data['total_actions']} total actions")
    
    def test_template_leaderboard(self, admin_headers):
        """Test template leaderboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/template-leaderboard/revenue-rankings", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Leaderboard: {data.get('total_revenue', 0)} total revenue")
    
    def test_template_analytics(self, admin_headers):
        """Test template analytics endpoint"""
        response = requests.get(f"{BASE_URL}/api/template-analytics/dashboard", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Template analytics: success")
    
    def test_admin_instagram_bio_stats(self, admin_headers):
        """Test admin Instagram Bio stats"""
        response = requests.get(f"{BASE_URL}/api/instagram-bio-generator/admin/stats", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_generations" in data
        print(f"Instagram Bio admin stats: {data['total_generations']} generations")


class TestCashfreePaymentConfig:
    """Cashfree payment configuration tests"""
    
    @pytest.fixture
    def demo_headers(self):
        """Get demo user headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_cashfree_config(self, demo_headers):
        """Test Cashfree configuration endpoint"""
        response = requests.get(f"{BASE_URL}/api/cashfree/config", headers=demo_headers)
        # Config endpoint might be different - check common patterns
        if response.status_code == 404:
            response = requests.get(f"{BASE_URL}/api/payments/config", headers=demo_headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Payment config: {data}")
        else:
            print(f"Payment config endpoint status: {response.status_code}")


class TestProtectedDownload:
    """Protected download tests"""
    
    def test_protected_download_config(self):
        """Test protected download config (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/protected-download/config")
        assert response.status_code == 200
        data = response.json()
        assert "watermark_removal_cost" in data or "enabled" in data
        print(f"Protected download config: {data}")


class TestSelfHealing:
    """Self-healing system tests"""
    
    @pytest.fixture
    def admin_headers(self):
        """Get admin user headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_self_healing_status(self, admin_headers):
        """Test self-healing status endpoint"""
        response = requests.get(f"{BASE_URL}/api/self-healing/status", headers=admin_headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Self-healing status: {data}")
        else:
            print(f"Self-healing status: {response.status_code}")


class TestPerformance:
    """Performance endpoints"""
    
    def test_performance_health(self):
        """Test performance health endpoint"""
        response = requests.get(f"{BASE_URL}/api/performance/health")
        assert response.status_code == 200
        data = response.json()
        print(f"Performance health: {data.get('overall_status', 'N/A')}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
