"""
Story Video Studio - Templates, Waiting Games, Sharing & Beta Tester Guide Tests
Iteration 128 - Testing endpoints in story_video_templates.py

Tests:
- GET /api/story-video-studio/templates/list - Video templates (8 templates)
- GET /api/story-video-studio/templates/waiting-games - Game counts 
- GET /api/story-video-studio/templates/waiting-games/trivia?count=3 - Trivia questions
- GET /api/story-video-studio/templates/waiting-games/word-puzzle - Word puzzle
- GET /api/story-video-studio/templates/waiting-games/riddle - Riddle
- POST /api/story-video-studio/templates/share - Social sharing links
- GET /api/story-video-studio/templates/my-videos - User's completed videos
- GET /api/story-video-studio/templates/beta-testers/test-guide - 8-step testing guide
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
VIDEO_ID = "06f297cc-15cb-4789-b556-c8a8dc0eb03f"  # Completed video from main agent

# Test credentials
TEST_EMAIL = "krajapraveen.katta@creatorstudio.ai"
TEST_PASSWORD = "Onemanarmy@1979#"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ============================================================================
# TEST: Video Templates List (8 templates expected)
# ============================================================================
class TestVideoTemplates:
    """Tests for video templates endpoint"""
    
    def test_get_templates_list_returns_8_templates(self, api_client):
        """GET /api/story-video-studio/templates/list - returns 8 video templates"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/list")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "templates" in data
        assert data["total"] == 8, f"Expected 8 templates, got {data['total']}"
        
        # Verify template structure
        templates = data["templates"]
        assert len(templates) == 8
        
        # Check each template has required fields
        required_fields = ["template_id", "name", "description", "age_group", "style", 
                         "duration_estimate", "scene_count", "structure", "fill_in_blanks"]
        
        template_ids = []
        for template in templates:
            for field in required_fields:
                assert field in template, f"Template missing field: {field}"
            template_ids.append(template["template_id"])
        
        # Verify expected templates exist
        expected_templates = [
            "bedtime_adventure", "superhero_origin", "fairy_tale", "space_explorer",
            "friendship_story", "educational_journey", "animal_adventure", "mystery_detective"
        ]
        for expected in expected_templates:
            assert expected in template_ids, f"Missing template: {expected}"
        
        print(f"PASS: Found {len(templates)} templates: {template_ids}")

    def test_templates_have_age_groups_and_styles(self, api_client):
        """Verify templates response includes age_groups and styles"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/list")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "age_groups" in data
        assert "styles" in data
        
        expected_age_groups = ["toddler", "kids_5_8", "kids_9_12", "teen", "all_ages"]
        assert data["age_groups"] == expected_age_groups
        
        expected_styles = ["watercolor", "cartoon_2d", "3d_animation", "comic_book", "storybook"]
        assert data["styles"] == expected_styles
        
        print(f"PASS: age_groups={data['age_groups']}, styles={data['styles']}")


# ============================================================================
# TEST: Waiting Games Endpoints
# ============================================================================
class TestWaitingGames:
    """Tests for waiting games during video generation"""
    
    def test_get_waiting_games_returns_counts(self, api_client):
        """GET /api/story-video-studio/templates/waiting-games - returns games, trivia, puzzles, riddles counts"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Check games list
        assert "games" in data
        assert len(data["games"]) > 0, "Expected at least 1 game"
        
        # Check counts
        assert "trivia_count" in data, "Missing trivia_count"
        assert "puzzles_count" in data, "Missing puzzles_count"
        assert "riddles_count" in data, "Missing riddles_count"
        
        assert data["trivia_count"] >= 10, f"Expected at least 10 trivia, got {data['trivia_count']}"
        assert data["puzzles_count"] >= 10, f"Expected at least 10 puzzles, got {data['puzzles_count']}"
        assert data["riddles_count"] >= 10, f"Expected at least 10 riddles, got {data['riddles_count']}"
        
        print(f"PASS: games={len(data['games'])}, trivia={data['trivia_count']}, puzzles={data['puzzles_count']}, riddles={data['riddles_count']}")

    def test_get_trivia_questions_with_count(self, api_client):
        """GET /api/story-video-studio/templates/waiting-games/trivia?count=3 - returns trivia questions"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/trivia?count=3")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert "questions" in data
        assert len(data["questions"]) == 3, f"Expected 3 questions, got {len(data['questions'])}"
        
        # Verify question structure (no answers should be included)
        for q in data["questions"]:
            assert "id" in q
            assert "question" in q
            assert "options" in q
            assert len(q["options"]) == 4, "Each question should have 4 options"
            assert "answer" not in q, "Answer should NOT be included in response"
        
        print(f"PASS: Got {len(data['questions'])} trivia questions with proper structure")

    def test_get_word_puzzle(self, api_client):
        """GET /api/story-video-studio/templates/waiting-games/word-puzzle - returns scrambled word and hint"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/word-puzzle")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Verify word puzzle structure
        assert "scrambled" in data, "Missing scrambled word"
        assert "hint" in data, "Missing hint"
        assert "length" in data, "Missing length"
        
        assert len(data["scrambled"]) > 0, "Scrambled word should not be empty"
        assert len(data["hint"]) > 0, "Hint should not be empty"
        assert data["length"] > 0, "Length should be positive"
        
        # Answer should NOT be in response
        assert "answer" not in data, "Answer should NOT be included in puzzle response"
        
        print(f"PASS: word-puzzle returned scrambled='{data['scrambled']}', hint='{data['hint']}', length={data['length']}")

    def test_get_riddle(self, api_client):
        """GET /api/story-video-studio/templates/waiting-games/riddle - returns a riddle"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/riddle")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Verify riddle structure
        assert "riddle" in data, "Missing riddle field"
        assert len(data["riddle"]) > 0, "Riddle should not be empty"
        
        # Answer should NOT be in response
        assert "answer" not in data, "Answer should NOT be included in riddle response"
        
        print(f"PASS: riddle returned: '{data['riddle'][:50]}...'")


# ============================================================================
# TEST: Social Sharing
# ============================================================================
class TestSocialSharing:
    """Tests for social sharing functionality"""
    
    def test_share_video_all_platforms(self, authenticated_client):
        """POST /api/story-video-studio/templates/share with video_id and platform='all' - returns share links"""
        payload = {
            "video_id": VIDEO_ID,
            "platform": "all"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/story-video-studio/templates/share",
            json=payload
        )
        
        # Could be 404 if video doesn't exist
        if response.status_code == 404:
            print(f"SKIP: Video {VIDEO_ID} not found - may need a real completed video")
            pytest.skip("Video not found - need completed video for share test")
        
        # Could be 400 if video not completed
        if response.status_code == 400:
            error_msg = response.json().get("detail", "")
            print(f"SKIP: Video not ready for sharing: {error_msg}")
            pytest.skip(f"Video not ready: {error_msg}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["video_id"] == VIDEO_ID
        
        # Verify share links for all platforms
        assert "share_links" in data
        share_links = data["share_links"]
        
        expected_platforms = ["facebook", "twitter", "whatsapp", "linkedin", "email"]
        for platform in expected_platforms:
            assert platform in share_links, f"Missing share link for {platform}"
            assert share_links[platform].startswith("http") or share_links[platform].startswith("mailto"), \
                f"Invalid share link for {platform}"
        
        # Verify share URL
        assert "share_url" in data
        
        print(f"PASS: Share links generated for all {len(expected_platforms)} platforms")

    def test_share_requires_auth(self, api_client):
        """POST /api/story-video-studio/templates/share requires authentication"""
        # Use unauthenticated client
        unauth_client = requests.Session()
        unauth_client.headers.update({"Content-Type": "application/json"})
        
        payload = {
            "video_id": VIDEO_ID,
            "platform": "all"
        }
        
        response = unauth_client.post(
            f"{BASE_URL}/api/story-video-studio/templates/share",
            json=payload
        )
        
        # Should require authentication (401 or 403)
        assert response.status_code in [401, 403, 422], \
            f"Expected 401/403/422 for unauthenticated request, got {response.status_code}"
        
        print(f"PASS: Share endpoint correctly requires authentication (returned {response.status_code})")


# ============================================================================
# TEST: User Videos
# ============================================================================
class TestUserVideos:
    """Tests for user's video library"""
    
    def test_get_my_videos(self, authenticated_client):
        """GET /api/story-video-studio/templates/my-videos - returns user's completed videos"""
        response = authenticated_client.get(f"{BASE_URL}/api/story-video-studio/templates/my-videos")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Verify response structure
        assert "videos" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        
        # Videos should be a list
        assert isinstance(data["videos"], list)
        
        # If there are videos, verify structure
        if len(data["videos"]) > 0:
            video = data["videos"][0]
            expected_fields = ["video_id", "title", "type"]
            for field in expected_fields:
                assert field in video, f"Video missing field: {field}"
        
        print(f"PASS: my-videos returned {len(data['videos'])} videos, total={data['total']}")

    def test_my_videos_requires_auth(self, api_client):
        """GET /api/story-video-studio/templates/my-videos requires authentication"""
        unauth_client = requests.Session()
        unauth_client.headers.update({"Content-Type": "application/json"})
        
        response = unauth_client.get(f"{BASE_URL}/api/story-video-studio/templates/my-videos")
        
        assert response.status_code in [401, 403, 422], \
            f"Expected 401/403/422 for unauthenticated request, got {response.status_code}"
        
        print(f"PASS: my-videos endpoint correctly requires authentication (returned {response.status_code})")


# ============================================================================
# TEST: Beta Tester Guide
# ============================================================================
class TestBetaTesterGuide:
    """Tests for beta tester guide endpoint"""
    
    def test_get_beta_test_guide_returns_8_steps(self, api_client):
        """GET /api/story-video-studio/templates/beta-testers/test-guide - returns 8-step testing guide"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/beta-testers/test-guide")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        
        # Verify guide structure
        assert "guide" in data
        guide = data["guide"]
        
        assert "title" in guide
        assert "Story → Video Studio" in guide["title"]
        
        assert "version" in guide
        assert "estimated_time" in guide
        assert "credits_needed" in guide
        
        # Verify 8 steps
        assert "steps" in guide
        steps = guide["steps"]
        assert len(steps) == 8, f"Expected 8 steps, got {len(steps)}"
        
        # Verify step structure
        for step in steps:
            assert "step" in step
            assert "name" in step
            assert "action" in step
        
        # Verify step numbers are 1-8
        step_numbers = [s["step"] for s in steps]
        assert step_numbers == [1, 2, 3, 4, 5, 6, 7, 8], f"Step numbers incorrect: {step_numbers}"
        
        # Verify feedback questions
        assert "feedback_questions" in guide
        assert len(guide["feedback_questions"]) >= 5, "Expected at least 5 feedback questions"
        
        # Verify contact info
        assert "contact" in guide
        
        print(f"PASS: Beta test guide has {len(steps)} steps and {len(guide['feedback_questions'])} feedback questions")

    def test_guide_steps_have_proper_flow(self, api_client):
        """Verify the 8 steps cover the complete user flow"""
        response = api_client.get(f"{BASE_URL}/api/story-video-studio/templates/beta-testers/test-guide")
        
        assert response.status_code == 200
        
        guide = response.json()["guide"]
        steps = guide["steps"]
        
        # Expected flow: Access -> Template/Story -> Generate -> Preview -> Games -> Full Video -> Download/Share -> Feedback
        step_names = [s["name"] for s in steps]
        
        # Check key steps are present
        assert any("Access" in name for name in step_names), "Missing 'Access' step"
        assert any("Template" in name or "Story" in name for name in step_names), "Missing template/story step"
        assert any("Preview" in name for name in step_names), "Missing preview step"
        assert any("Games" in name or "Waiting" in name for name in step_names), "Missing games step"
        assert any("Download" in name or "Share" in name for name in step_names), "Missing download/share step"
        assert any("Feedback" in name for name in step_names), "Missing feedback step"
        
        print(f"PASS: Guide steps cover complete flow: {step_names}")


# ============================================================================
# MAIN: Run tests directly
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
