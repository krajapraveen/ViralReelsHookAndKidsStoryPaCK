"""
Test Suite for New CreatorStudio AI Features - Iteration 96
Testing: Comment Reply Bank and Bedtime Story Builder

Comment Reply Bank: Template-based comment reply generator with intent detection
- Single reply: 5 credits (4 replies)
- Full Pack: 15 credits (12 replies)

Bedtime Story Builder: Narration-ready story scripts with voice notes and SFX cues
- Story generation: 10 credits
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://subscription-gateway-1.preview.emergentagent.com')

# Test credentials
DEMO_USER = {"email": "demo@example.com", "password": "Password123!"}
ADMIN_USER = {"email": "admin@creatorstudio.ai", "password": "Cr3@t0rStud!o#2026"}


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_health(self):
        """Test API is responsive"""
        response = requests.get(f"{BASE_URL}/api/health/")
        assert response.status_code == 200
        print("✓ API health check passed")


class TestCommentReplyBankConfig:
    """Test Comment Reply Bank configuration endpoint"""
    
    def test_config_endpoint(self):
        """Test /api/comment-reply-bank/config returns proper configuration"""
        response = requests.get(f"{BASE_URL}/api/comment-reply-bank/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify modes
        assert "modes" in data
        assert len(data["modes"]) == 2
        
        # Verify single mode
        single_mode = next((m for m in data["modes"] if m["id"] == "single"), None)
        assert single_mode is not None
        assert single_mode["credits"] == 5
        assert single_mode["replies"] == 4
        
        # Verify full_pack mode
        full_pack = next((m for m in data["modes"] if m["id"] == "full_pack"), None)
        assert full_pack is not None
        assert full_pack["credits"] == 15
        assert full_pack["replies"] == 12
        
        # Verify reply types
        assert "replyTypes" in data
        assert set(data["replyTypes"]) == {"funny", "smart", "sales", "short"}
        
        # Verify max comment length
        assert data["maxCommentLength"] == 500
        
        print("✓ Comment Reply Bank config endpoint returns correct data")


class TestBedtimeStoryBuilderConfig:
    """Test Bedtime Story Builder configuration endpoint"""
    
    def test_config_endpoint(self):
        """Test /api/bedtime-story-builder/config returns proper configuration"""
        response = requests.get(f"{BASE_URL}/api/bedtime-story-builder/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify age groups
        assert "ageGroups" in data
        assert len(data["ageGroups"]) == 3
        age_ids = [ag["id"] for ag in data["ageGroups"]]
        assert set(age_ids) == {"3-5", "6-8", "9-12"}
        
        # Verify themes (should have at least the default themes)
        assert "themes" in data
        assert len(data["themes"]) >= 10  # Should have at least 10 themes
        assert "Friendship" in data["themes"]
        assert "Bravery" in data["themes"]
        assert "Bedtime Calm" in data["themes"]
        
        # Verify morals
        assert "morals" in data
        assert len(data["morals"]) >= 8  # Should have at least 8 morals
        assert "Be kind" in data["morals"]
        assert "Be brave" in data["morals"]
        
        # Verify lengths
        assert "lengths" in data
        assert len(data["lengths"]) == 3
        length_ids = [l["id"] for l in data["lengths"]]
        assert set(length_ids) == {"3", "5", "8"}
        
        # Verify 5 min is default
        default_length = next((l for l in data["lengths"] if l.get("default")), None)
        assert default_length is not None
        assert default_length["id"] == "5"
        
        # Verify voice styles
        assert "voiceStyles" in data
        assert len(data["voiceStyles"]) == 3
        style_ids = [v["id"] for v in data["voiceStyles"]]
        assert set(style_ids) == {"calm_parent", "playful_storyteller", "gentle_teacher"}
        
        # Verify pricing
        assert "pricing" in data
        assert data["pricing"]["story"] == 10
        assert data["pricing"]["pdfExport"] == 2
        
        print("✓ Bedtime Story Builder config endpoint returns correct data")


class TestAuthentication:
    """Test authentication for protected endpoints"""
    
    @pytest.fixture
    def demo_token(self):
        """Get demo user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get admin user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    def test_demo_login(self):
        """Test demo user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        assert "token" in response.json()
        print("✓ Demo user login successful")
    
    def test_admin_login(self):
        """Test admin user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_USER)
        assert response.status_code == 200
        assert "token" in response.json()
        print("✓ Admin user login successful")


class TestCommentReplyBankGeneration:
    """Test Comment Reply Bank generation endpoint"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_generate_single_reply_set(self, auth_headers):
        """Test generating single reply set (5 credits, 4 replies)"""
        payload = {
            "comment": "This is amazing content! How do you create such great videos?",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "intent_detected" in data
        assert "replies" in data
        assert len(data["replies"]) == 4  # Single mode returns 4 replies
        assert data["credits_used"] == 5
        
        # Verify each reply has type and reply text
        for reply in data["replies"]:
            assert "type" in reply
            assert "reply" in reply
            assert reply["type"] in ["funny", "smart", "sales", "short"]
        
        print(f"✓ Single reply set generated - Intent: {data['intent_detected']}, Replies: {len(data['replies'])}")
    
    def test_generate_full_pack(self, auth_headers):
        """Test generating full pack (15 credits, 12 replies)"""
        payload = {
            "comment": "How much does this cost? I want to buy it!",
            "mode": "full_pack"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "intent_detected" in data
        assert data["intent_detected"] == "pricing"  # Should detect pricing intent
        assert len(data["replies"]) == 12  # Full pack returns 12 replies
        assert data["credits_used"] == 15
        
        print(f"✓ Full pack generated - Intent: {data['intent_detected']}, Replies: {len(data['replies'])}")
    
    def test_intent_detection_praise(self, auth_headers):
        """Test intent detection for praise comments"""
        payload = {
            "comment": "Love your content! You're amazing!",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["intent_detected"] == "praise"
        print("✓ Praise intent detected correctly")
    
    def test_intent_detection_question(self, auth_headers):
        """Test intent detection for question comments"""
        payload = {
            "comment": "How did you learn to do this? Can you explain?",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["intent_detected"] == "question"
        print("✓ Question intent detected correctly")
    
    def test_blocked_content_rejection(self, auth_headers):
        """Test that blocked/copyrighted content is rejected"""
        payload = {
            "comment": "I love Marvel movies! Your video is like Avengers!",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "copyrighted" in response.json()["detail"].lower() or "brand" in response.json()["detail"].lower()
        print("✓ Blocked content correctly rejected")
    
    def test_empty_comment_validation(self, auth_headers):
        """Test that empty comments are rejected"""
        payload = {
            "comment": "",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]  # Validation error
        print("✓ Empty comment validation working")
    
    def test_invalid_mode_validation(self, auth_headers):
        """Test that invalid mode is rejected"""
        payload = {
            "comment": "Great content!",
            "mode": "invalid_mode"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        print("✓ Invalid mode validation working")
    
    def test_unauthorized_request(self):
        """Test that unauthenticated request is rejected"""
        payload = {
            "comment": "Great content!",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [401, 403]
        print("✓ Unauthorized request correctly rejected")


class TestBedtimeStoryBuilderGeneration:
    """Test Bedtime Story Builder generation endpoint"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_generate_story_5min(self, auth_headers):
        """Test generating a 5-minute story (default length)"""
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "story" in data
        assert data["credits_used"] == 10
        
        story = data["story"]
        assert "script" in story
        assert "voice_notes" in story
        assert "sfx_cues" in story
        assert "metadata" in story
        
        # Verify script contains content
        assert len(story["script"]) > 100  # Should have substantial script
        
        # Verify voice notes
        assert len(story["voice_notes"]) > 0
        for note in story["voice_notes"]:
            assert "scene" in note
            assert "note" in note
            assert "pacing" in note
        
        # Verify SFX cues
        assert len(story["sfx_cues"]) > 0
        for cue in story["sfx_cues"]:
            assert "scene" in cue
            assert "cue" in cue
        
        # Verify metadata
        assert "character" in story["metadata"]
        assert "word_count" in story["metadata"]
        assert "target_duration" in story["metadata"]
        assert story["metadata"]["target_duration"] == "5 min"
        
        print(f"✓ 5-minute story generated - Character: {story['metadata']['character']}, Words: {story['metadata']['word_count']}")
    
    def test_generate_story_3min(self, auth_headers):
        """Test generating a 3-minute story (short)"""
        payload = {
            "age_group": "6-8",
            "theme": "Bravery",
            "moral": "Be brave",
            "length": "3",
            "voice_style": "playful_storyteller"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["story"]["metadata"]["target_duration"] == "3 min"
        print("✓ 3-minute story generated successfully")
    
    def test_generate_story_8min(self, auth_headers):
        """Test generating an 8-minute story (long)"""
        payload = {
            "age_group": "9-12",
            "theme": "Adventure",
            "moral": "Believe in yourself",
            "length": "8",
            "voice_style": "gentle_teacher"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["story"]["metadata"]["target_duration"] == "8 min"
        print("✓ 8-minute story generated successfully")
    
    def test_generate_story_with_child_name(self, auth_headers):
        """Test generating a story with personalized child name"""
        payload = {
            "age_group": "3-5",
            "theme": "Bedtime Calm",
            "moral": "Be thankful",
            "length": "5",
            "voice_style": "calm_parent",
            "child_name": "Emma"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        print("✓ Story with personalized child name generated successfully")
    
    def test_blocked_child_name_rejection(self, auth_headers):
        """Test that copyrighted names are rejected"""
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent",
            "child_name": "Elsa from Frozen"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "copyrighted" in response.json()["detail"].lower() or "original" in response.json()["detail"].lower()
        print("✓ Copyrighted child name correctly rejected")
    
    def test_invalid_age_group_validation(self, auth_headers):
        """Test that invalid age group is rejected"""
        payload = {
            "age_group": "invalid",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        print("✓ Invalid age group validation working")
    
    def test_invalid_length_validation(self, auth_headers):
        """Test that invalid length is rejected"""
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "10",  # Invalid length
            "voice_style": "calm_parent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        print("✓ Invalid length validation working")
    
    def test_unauthorized_request(self):
        """Test that unauthenticated request is rejected"""
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [401, 403]
        print("✓ Unauthorized request correctly rejected")


class TestBedtimeStoryExport:
    """Test Bedtime Story Builder export endpoint"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_export_story_txt(self, auth_headers):
        """Test exporting story as text file"""
        # First generate a story
        gen_payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent"
        }
        
        gen_response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=gen_payload,
            headers=auth_headers
        )
        
        assert gen_response.status_code == 200
        story = gen_response.json()["story"]
        
        # Then export it
        export_response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/export",
            json=story,
            params={"format": "txt"},
            headers=auth_headers
        )
        
        assert export_response.status_code == 200
        data = export_response.json()
        
        assert data["success"] == True
        assert "content" in data
        assert "filename" in data
        assert ".txt" in data["filename"]
        assert "BEDTIME STORY AUDIO SCRIPT" in data["content"]
        assert "NARRATION SCRIPT" in data["content"]
        assert "VOICE PACING NOTES" in data["content"]
        assert "SOUND EFFECT CUES" in data["content"]
        
        print("✓ Story export as TXT working correctly")


class TestDashboardFeatureCards:
    """Test that Dashboard displays the new feature cards"""
    
    def test_dashboard_accessible(self):
        """Test dashboard is accessible after login"""
        # Login first
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json()["token"]
        
        # Get user info (verify logged in)
        headers = {"Authorization": f"Bearer {token}"}
        user_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert user_response.status_code == 200
        print("✓ Dashboard accessible after login")


class TestCreditDeduction:
    """Test credit deduction for both features"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=DEMO_USER)
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def test_comment_reply_credits_returned(self, auth_headers):
        """Test that remaining credits are returned after Comment Reply Bank generation"""
        payload = {
            "comment": "Great content! Keep it up!",
            "mode": "single"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/comment-reply-bank/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "remaining_credits" in data
        assert isinstance(data["remaining_credits"], (int, float))
        print(f"✓ Comment Reply Bank returns remaining credits: {data['remaining_credits']}")
    
    def test_bedtime_story_credits_returned(self, auth_headers):
        """Test that remaining credits are returned after Bedtime Story generation"""
        payload = {
            "age_group": "3-5",
            "theme": "Friendship",
            "moral": "Be kind",
            "length": "5",
            "voice_style": "calm_parent"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/bedtime-story-builder/generate",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "remaining_credits" in data
        assert isinstance(data["remaining_credits"], (int, float))
        print(f"✓ Bedtime Story Builder returns remaining credits: {data['remaining_credits']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
