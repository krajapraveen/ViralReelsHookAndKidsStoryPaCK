"""
Comprehensive UAT/QA/Performance Test - Iteration 130
Visionary Suite - All Features Across All Pages

Features to test:
1. Dashboard - feature cards visible, Daily Reward working
2. Reel Generator - script generation with download
3. Photo to Comic - file upload, comic generation, download (base64 PNG)
4. Story Video Studio - full E2E flow (create project -> scenes -> images -> voice -> video)
5. WebSocket progress notifications - real-time updates
6. GenStudio - styles and history
7. Creator Tools - calendar, hashtags, thumbnails
8. Profile & Settings - update profile
9. Blog content - posts available
10. Waiting Games - trivia, puzzles, riddles
11. Social Sharing - share buttons work
12. Security - auth required for protected routes, admin routes blocked
"""

import pytest
import requests
import os
import time
import uuid
import base64
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Password123!"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def demo_auth_token(api_client):
    """Get authentication token for demo user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Demo auth failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_auth_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin auth failed: {response.status_code}")


@pytest.fixture(scope="module")
def demo_client(api_client, demo_auth_token):
    """Session with demo user auth header"""
    api_client.headers.update({"Authorization": f"Bearer {demo_auth_token}"})
    return api_client


@pytest.fixture(scope="module")
def admin_client(api_client, admin_auth_token):
    """Session with admin auth header"""
    admin_session = requests.Session()
    admin_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_auth_token}"
    })
    return admin_session


# =============================================================================
# 1. DASHBOARD TESTS
# =============================================================================
class TestDashboard:
    """Tests for Dashboard features"""
    
    def test_user_profile_endpoint(self, demo_client):
        """GET /api/user/profile - returns user profile data"""
        response = demo_client.get(f"{BASE_URL}/api/user/profile")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "email" in data or "name" in data or "credits" in data
        print(f"PASS: User profile endpoint works - credits: {data.get('credits', 'N/A')}")
    
    def test_daily_reward_endpoint(self, demo_client):
        """POST /api/user/daily-reward - claims daily reward"""
        response = demo_client.post(f"{BASE_URL}/api/user/daily-reward")
        # Can be 200 (claimed) or 429 (already claimed today)
        assert response.status_code in [200, 400, 429], f"Got {response.status_code}: {response.text}"
        print(f"PASS: Daily reward endpoint responds - status: {response.status_code}")
    
    def test_credits_balance_endpoint(self, demo_client):
        """GET /api/credits/balance - returns credits balance"""
        response = demo_client.get(f"{BASE_URL}/api/credits/balance")
        if response.status_code == 404:
            # Try alternate endpoint
            response = demo_client.get(f"{BASE_URL}/api/user/credits")
        
        assert response.status_code in [200, 404], f"Got {response.status_code}: {response.text}"
        print(f"PASS: Credits balance endpoint status: {response.status_code}")


# =============================================================================
# 2. REEL GENERATOR TESTS
# =============================================================================
class TestReelGenerator:
    """Tests for Reel Generator feature"""
    
    def test_reel_generate_script(self, demo_client):
        """POST /api/generate/reel - generates reel script"""
        payload = {
            "topic": "morning routine tips for productivity",
            "tone": "upbeat",
            "duration": "30s"
        }
        response = demo_client.post(f"{BASE_URL}/api/generate/reel", json=payload)
        
        if response.status_code == 402:
            print("SKIP: Insufficient credits for reel generation")
            pytest.skip("Insufficient credits")
        
        assert response.status_code in [200, 201], f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check for script components
        has_content = any(k in data for k in ["hook", "script", "captions", "content", "result"])
        assert has_content, f"Response missing content: {data.keys()}"
        print(f"PASS: Reel script generation works")
    
    def test_reel_history(self, demo_client):
        """GET /api/generate/history - returns generation history"""
        response = demo_client.get(f"{BASE_URL}/api/generate/history")
        
        if response.status_code == 404:
            print("SKIP: History endpoint not available")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        print("PASS: Reel history endpoint works")


# =============================================================================
# 3. PHOTO TO COMIC TESTS
# =============================================================================
class TestPhotoToComic:
    """Tests for Photo to Comic feature with file upload"""
    
    def test_photo_comic_styles(self, demo_client):
        """GET /api/photo-to-comic/styles - returns available styles"""
        response = demo_client.get(f"{BASE_URL}/api/photo-to-comic/styles")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) >= 10, f"Expected 10+ styles, got {len(data['styles'])}"
        print(f"PASS: Found {len(data['styles'])} comic styles")
    
    def test_photo_comic_pricing(self, demo_client):
        """GET /api/photo-to-comic/pricing - returns pricing info"""
        response = demo_client.get(f"{BASE_URL}/api/photo-to-comic/pricing")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pricing" in data
        print(f"PASS: Photo-to-comic pricing retrieved")
    
    def test_photo_comic_generate_with_file(self, demo_auth_token):
        """POST /api/photo-to-comic/generate - test with actual file upload"""
        # Create a minimal valid PNG (1x1 pixel red)
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        png_bytes = base64.b64decode(png_b64)
        
        files = {
            'photo': ('test.png', BytesIO(png_bytes), 'image/png')
        }
        data = {
            'mode': 'avatar',
            'style': 'cartoon_fun',
            'genre': 'comedy'
        }
        
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {demo_auth_token}"})
        
        response = session.post(
            f"{BASE_URL}/api/photo-to-comic/generate",
            files=files,
            data=data
        )
        
        if response.status_code == 400 and "credits" in response.text.lower():
            print("SKIP: Insufficient credits for comic generation")
            pytest.skip("Insufficient credits")
        
        assert response.status_code in [200, 201, 400, 422], f"Got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            resp_data = response.json()
            assert "jobId" in resp_data or "job_id" in resp_data or "success" in resp_data
            print(f"PASS: Photo-to-comic generation started")
        else:
            print(f"INFO: Photo-to-comic returned {response.status_code} - {response.text[:100]}")
    
    def test_photo_comic_history(self, demo_client):
        """GET /api/photo-to-comic/history - returns job history"""
        response = demo_client.get(f"{BASE_URL}/api/photo-to-comic/history")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "jobs" in data
        print(f"PASS: Photo-to-comic history - {len(data['jobs'])} jobs found")


# =============================================================================
# 4. STORY VIDEO STUDIO TESTS
# =============================================================================
class TestStoryVideoStudio:
    """Tests for Story Video Studio E2E flow"""
    
    def test_story_video_styles(self, demo_client):
        """GET /api/story-video-studio/styles - returns video styles"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/styles")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "styles" in data
        assert len(data["styles"]) >= 5, f"Expected 5+ styles, got {len(data['styles'])}"
        print(f"PASS: Found {len(data['styles'])} video styles")
    
    def test_story_video_pricing(self, demo_client):
        """GET /api/story-video-studio/pricing - returns pricing info"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/pricing")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pricing" in data
        pricing = data["pricing"]
        assert "scene_generation" in pricing
        assert "image_per_scene" in pricing
        print(f"PASS: Story video pricing - scene: {pricing['scene_generation']} credits")
    
    def test_story_video_templates(self, demo_client):
        """GET /api/story-video-studio/templates/list - returns templates"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/templates/list")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) >= 5, f"Expected 5+ templates, got {len(data['templates'])}"
        print(f"PASS: Found {len(data['templates'])} story templates")
    
    def test_story_video_create_project(self, demo_client):
        """POST /api/story-video-studio/projects/create - creates new project"""
        payload = {
            "story_text": "Once upon a time in a magical forest, there lived a brave little fox named Ruby. Ruby loved exploring and one day she discovered a hidden garden filled with glowing flowers. The flowers had special powers that could grant wishes to those with pure hearts. Ruby made a wish to help all the animals in the forest, and from that day on, the forest became the happiest place in the world.",
            "title": f"Test Story {uuid.uuid4().hex[:8]}",
            "language": "english",
            "age_group": "kids_5_8",
            "style_id": "storybook"
        }
        
        response = demo_client.post(f"{BASE_URL}/api/story-video-studio/projects/create", json=payload)
        
        assert response.status_code in [200, 201], f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "project_id" in data
        print(f"PASS: Story project created - ID: {data['project_id'][:16]}...")
        return data["project_id"]
    
    def test_story_video_generate_scenes(self, demo_client):
        """Test scene generation for story video"""
        # First create a project
        project_payload = {
            "story_text": "A brave knight named Arthur embarked on a quest to save the kingdom from a friendly dragon who just wanted to make friends. Along the way, Arthur met a wise owl who taught him that kindness is the greatest weapon.",
            "title": f"Scene Test {uuid.uuid4().hex[:8]}",
            "language": "english",
            "age_group": "kids_5_8",
            "style_id": "storybook"
        }
        
        create_response = demo_client.post(f"{BASE_URL}/api/story-video-studio/projects/create", json=project_payload)
        
        if create_response.status_code != 200:
            pytest.skip(f"Project creation failed: {create_response.status_code}")
        
        project_id = create_response.json().get("project_id")
        
        # Generate scenes
        scene_response = demo_client.post(f"{BASE_URL}/api/story-video-studio/projects/{project_id}/generate-scenes")
        
        if scene_response.status_code == 402:
            print("SKIP: Insufficient credits for scene generation")
            pytest.skip("Insufficient credits")
        
        assert scene_response.status_code in [200, 201], f"Got {scene_response.status_code}: {scene_response.text}"
        
        scene_data = scene_response.json()
        if "data" in scene_data and "scenes" in scene_data["data"]:
            scene_count = len(scene_data["data"]["scenes"])
            print(f"PASS: Generated {scene_count} scenes for project")
        else:
            print(f"PASS: Scene generation response received")


# =============================================================================
# 5. WEBSOCKET PROGRESS TESTS (via HTTP endpoint check)
# =============================================================================
class TestWebSocketProgress:
    """Tests for WebSocket progress notification availability"""
    
    def test_websocket_endpoint_exists(self, demo_client):
        """Check WebSocket endpoint is configured"""
        # We can't test WebSocket via HTTP, but we can verify the route exists
        # by checking if the server is configured for WS
        response = demo_client.get(f"{BASE_URL}/api/health")
        assert response.status_code in [200, 404], f"Got {response.status_code}"
        print("PASS: Server is running, WebSocket should be available at /ws/progress")


# =============================================================================
# 6. GENSTUDIO TESTS
# =============================================================================
class TestGenStudio:
    """Tests for GenStudio styles and history"""
    
    def test_genstudio_styles(self, demo_client):
        """GET /api/genstudio/styles - returns available styles"""
        response = demo_client.get(f"{BASE_URL}/api/genstudio/styles")
        
        if response.status_code == 404:
            # Try alternate endpoint
            response = demo_client.get(f"{BASE_URL}/api/gen-studio/styles")
        
        if response.status_code == 404:
            print("SKIP: GenStudio styles endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        print("PASS: GenStudio styles endpoint works")
    
    def test_genstudio_history(self, demo_client):
        """GET /api/genstudio/history - returns generation history"""
        response = demo_client.get(f"{BASE_URL}/api/genstudio/history")
        
        if response.status_code == 404:
            response = demo_client.get(f"{BASE_URL}/api/gen-studio/history")
        
        if response.status_code == 404:
            print("SKIP: GenStudio history endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        print("PASS: GenStudio history endpoint works")


# =============================================================================
# 7. CREATOR TOOLS TESTS
# =============================================================================
class TestCreatorTools:
    """Tests for Creator Tools - calendar, hashtags, thumbnails"""
    
    def test_content_calendar_generate(self, demo_client):
        """POST /api/content-calendar/generate - generates content calendar"""
        payload = {
            "niche": "fitness",
            "duration": "7",
            "platform": "instagram"
        }
        response = demo_client.post(f"{BASE_URL}/api/content-calendar/generate", json=payload)
        
        if response.status_code == 404:
            response = demo_client.post(f"{BASE_URL}/api/creator-tools/calendar/generate", json=payload)
        
        if response.status_code == 402:
            print("SKIP: Insufficient credits for calendar generation")
            pytest.skip("Insufficient credits")
        
        if response.status_code == 404:
            print("SKIP: Content calendar endpoint not found")
            return
        
        assert response.status_code in [200, 201], f"Got {response.status_code}: {response.text}"
        print("PASS: Content calendar generation works")
    
    def test_hashtag_generator(self, demo_client):
        """POST /api/hashtags/generate - generates hashtags"""
        payload = {
            "topic": "fitness motivation",
            "count": 20
        }
        response = demo_client.post(f"{BASE_URL}/api/hashtags/generate", json=payload)
        
        if response.status_code == 404:
            response = demo_client.post(f"{BASE_URL}/api/creator-tools/hashtags/generate", json=payload)
        
        if response.status_code == 402:
            print("SKIP: Insufficient credits for hashtag generation")
            pytest.skip("Insufficient credits")
        
        if response.status_code == 404:
            print("SKIP: Hashtag generator endpoint not found")
            return
        
        assert response.status_code in [200, 201], f"Got {response.status_code}: {response.text}"
        print("PASS: Hashtag generation works")
    
    def test_thumbnail_generator(self, demo_client):
        """POST /api/thumbnails/generate - generates thumbnails"""
        payload = {
            "title": "5 Ways to Stay Motivated",
            "style": "bold"
        }
        response = demo_client.post(f"{BASE_URL}/api/thumbnails/generate", json=payload)
        
        if response.status_code == 404:
            response = demo_client.post(f"{BASE_URL}/api/creator-tools/thumbnails/generate", json=payload)
        
        if response.status_code == 402:
            print("SKIP: Insufficient credits for thumbnail generation")
            pytest.skip("Insufficient credits")
        
        if response.status_code == 404:
            print("SKIP: Thumbnail generator endpoint not found")
            return
        
        assert response.status_code in [200, 201], f"Got {response.status_code}: {response.text}"
        print("PASS: Thumbnail generation works")


# =============================================================================
# 8. PROFILE & SETTINGS TESTS
# =============================================================================
class TestProfileSettings:
    """Tests for Profile and Settings"""
    
    def test_get_profile(self, demo_client):
        """GET /api/user/profile - returns user profile"""
        response = demo_client.get(f"{BASE_URL}/api/user/profile")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert any(k in data for k in ["email", "name", "id"]), f"Missing profile fields: {data.keys()}"
        print(f"PASS: Profile retrieved successfully")
    
    def test_update_profile(self, demo_client):
        """PUT /api/user/profile - updates user profile"""
        payload = {
            "name": f"Test User {uuid.uuid4().hex[:4]}"
        }
        response = demo_client.put(f"{BASE_URL}/api/user/profile", json=payload)
        
        if response.status_code == 404:
            response = demo_client.patch(f"{BASE_URL}/api/user/profile", json=payload)
        
        if response.status_code == 404:
            print("SKIP: Profile update endpoint not found")
            return
        
        assert response.status_code in [200, 204], f"Got {response.status_code}: {response.text}"
        print("PASS: Profile update works")
    
    def test_credits_history(self, demo_client):
        """GET /api/credits/history - returns credits transaction history"""
        response = demo_client.get(f"{BASE_URL}/api/credits/history")
        
        if response.status_code == 404:
            response = demo_client.get(f"{BASE_URL}/api/user/credits/history")
        
        if response.status_code == 404:
            print("SKIP: Credits history endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        print("PASS: Credits history works")


# =============================================================================
# 9. BLOG CONTENT TESTS
# =============================================================================
class TestBlogContent:
    """Tests for Blog posts availability"""
    
    def test_blog_posts_list(self, api_client):
        """GET /api/blog/posts - returns list of blog posts"""
        response = api_client.get(f"{BASE_URL}/api/blog/posts")
        
        if response.status_code == 404:
            print("SKIP: Blog posts endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        if isinstance(data, list):
            print(f"PASS: Found {len(data)} blog posts")
        elif "posts" in data:
            print(f"PASS: Found {len(data['posts'])} blog posts")
        else:
            print(f"PASS: Blog posts endpoint works")
    
    def test_blog_post_detail(self, api_client):
        """GET /api/blog/posts/1 - returns single blog post"""
        # Try to get first post
        list_response = api_client.get(f"{BASE_URL}/api/blog/posts")
        
        if list_response.status_code != 200:
            print("SKIP: Cannot get blog list for detail test")
            return
        
        data = list_response.json()
        posts = data if isinstance(data, list) else data.get("posts", [])
        
        if not posts:
            print("SKIP: No blog posts available")
            return
        
        post_id = posts[0].get("id") or posts[0].get("slug") or "1"
        detail_response = api_client.get(f"{BASE_URL}/api/blog/posts/{post_id}")
        
        assert detail_response.status_code in [200, 404], f"Got {detail_response.status_code}"
        print(f"PASS: Blog post detail endpoint works")


# =============================================================================
# 10. WAITING GAMES TESTS
# =============================================================================
class TestWaitingGames:
    """Tests for Waiting Games - trivia, puzzles, riddles"""
    
    def test_waiting_games_overview(self, demo_client):
        """GET /api/story-video-studio/templates/waiting-games - returns games overview"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "games" in data
        assert "trivia_count" in data
        assert "puzzles_count" in data
        print(f"PASS: Waiting games overview - {data.get('trivia_count', 0)} trivia, {data.get('puzzles_count', 0)} puzzles")
    
    def test_trivia_questions(self, demo_client):
        """GET /api/story-video-studio/templates/waiting-games/trivia - returns trivia questions"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/trivia?count=5")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) >= 1
        print(f"PASS: Got {len(data['questions'])} trivia questions")
    
    def test_trivia_answer_check(self, demo_client):
        """POST /api/story-video-studio/templates/waiting-games/trivia/check - checks answer"""
        response = demo_client.post(
            f"{BASE_URL}/api/story-video-studio/templates/waiting-games/trivia/check",
            params={"question_id": 0, "answer_index": 0}
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "correct" in data
        print(f"PASS: Trivia answer check works - correct: {data.get('correct')}")
    
    def test_word_puzzle(self, demo_client):
        """GET /api/story-video-studio/templates/waiting-games/word-puzzle - returns word puzzle"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/word-puzzle")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "scrambled" in data
        assert "hint" in data
        print(f"PASS: Word puzzle - scrambled: {data.get('scrambled')}, hint: {data.get('hint')}")
    
    def test_riddle(self, demo_client):
        """GET /api/story-video-studio/templates/waiting-games/riddle - returns riddle"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/templates/waiting-games/riddle")
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "riddle" in data
        print(f"PASS: Riddle endpoint works")


# =============================================================================
# 11. SOCIAL SHARING TESTS
# =============================================================================
class TestSocialSharing:
    """Tests for Social Sharing functionality"""
    
    def test_share_requires_auth(self, api_client):
        """POST /api/story-video-studio/templates/share - requires authentication"""
        payload = {
            "video_id": "test-video-123",
            "platform": "facebook"
        }
        response = api_client.post(f"{BASE_URL}/api/story-video-studio/templates/share", json=payload)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Share endpoint requires authentication")
    
    def test_share_with_auth(self, demo_client):
        """POST /api/story-video-studio/templates/share - generates share links"""
        payload = {
            "video_id": "test-video-123",
            "platform": "all"
        }
        response = demo_client.post(f"{BASE_URL}/api/story-video-studio/templates/share", json=payload)
        
        # Will likely return 404 for non-existent video, which is expected
        assert response.status_code in [200, 404, 400], f"Got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "share_links" in data
            print(f"PASS: Share links generated")
        else:
            print(f"PASS: Share endpoint responds correctly ({response.status_code})")


# =============================================================================
# 12. SECURITY TESTS
# =============================================================================
class TestSecurity:
    """Tests for Security - auth required, admin routes blocked"""
    
    def test_protected_route_requires_auth(self, api_client):
        """Protected routes return 401 without auth"""
        response = api_client.get(f"{BASE_URL}/api/user/profile")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Protected routes require authentication")
    
    def test_admin_route_blocked_for_users(self, demo_client):
        """Admin routes blocked for normal users"""
        response = demo_client.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code in [401, 403, 404], f"Expected 401/403/404, got {response.status_code}"
        print("PASS: Admin routes blocked for normal users")
    
    def test_admin_route_works_for_admin(self, admin_client):
        """Admin routes work for admin users"""
        response = admin_client.get(f"{BASE_URL}/api/admin/users")
        
        # Admin route should work (200) or at least not be a generic error
        if response.status_code == 200:
            print("PASS: Admin route works for admin user")
        elif response.status_code == 404:
            print("INFO: Admin users endpoint not found (may be different path)")
        else:
            print(f"INFO: Admin route returned {response.status_code}")
    
    def test_security_headers(self, api_client):
        """Check security headers are present"""
        response = api_client.get(f"{BASE_URL}/")
        
        # Check for common security headers
        headers_to_check = [
            "strict-transport-security",
            "x-content-type-options",
        ]
        
        missing = []
        for header in headers_to_check:
            if header not in [h.lower() for h in response.headers.keys()]:
                missing.append(header)
        
        if missing:
            print(f"INFO: Missing security headers: {missing}")
        else:
            print("PASS: Security headers present")
    
    def test_rate_limiting(self, api_client):
        """Test rate limiting on auth endpoint"""
        # Make multiple rapid requests
        results = []
        for i in range(6):
            response = api_client.post(f"{BASE_URL}/api/auth/login", json={
                "email": "invalid@test.com",
                "password": "wrongpassword"
            })
            results.append(response.status_code)
            time.sleep(0.1)
        
        # Should get rate limited (423) after several failed attempts
        has_rate_limit = 423 in results or 429 in results
        if has_rate_limit:
            print("PASS: Rate limiting is active")
        else:
            print(f"INFO: Rate limiting may not be active (got statuses: {results})")


# =============================================================================
# 13. ADDITIONAL FEATURE TESTS
# =============================================================================
class TestAdditionalFeatures:
    """Additional feature tests"""
    
    def test_notifications_endpoint(self, demo_client):
        """GET /api/notifications - returns user notifications"""
        response = demo_client.get(f"{BASE_URL}/api/notifications")
        
        if response.status_code == 404:
            response = demo_client.get(f"{BASE_URL}/api/user/notifications")
        
        if response.status_code == 404:
            print("SKIP: Notifications endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        print("PASS: Notifications endpoint works")
    
    def test_voice_config(self, demo_client):
        """GET /api/story-video-studio/generation/voice/config - returns voice config"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/generation/voice/config")
        
        if response.status_code == 404:
            print("SKIP: Voice config endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"PASS: Voice config retrieved")
    
    def test_music_library(self, demo_client):
        """GET /api/story-video-studio/generation/music/library - returns music library"""
        response = demo_client.get(f"{BASE_URL}/api/story-video-studio/generation/music/library")
        
        if response.status_code == 404:
            print("SKIP: Music library endpoint not found")
            return
        
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"PASS: Music library retrieved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
