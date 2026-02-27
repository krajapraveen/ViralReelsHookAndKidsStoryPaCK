"""
Test Suite for 3 REBUILT Features - Iteration 91
Tests Story Episode Creator, Content Challenge Planner, and Caption Rewriter Pro

Features:
1. Story Episode Creator (3-step wizard): Idea → Length → Generate
2. Content Challenge Planner (4-step wizard): Platform → Duration → Goal → Generate
3. Caption Rewriter Pro (3-step wizard): Text → Tone → Generate
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication for testing"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for demo user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}


# =============================================================================
# STORY EPISODE CREATOR TESTS (3-step wizard)
# =============================================================================
class TestStoryEpisodeCreatorConfig:
    """Test Story Episode Creator configuration endpoints"""
    
    def test_config_endpoint_accessible(self):
        """Test /api/story-episode-creator/config returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/story-episode-creator/config")
        assert response.status_code == 200, f"Config endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify pricing structure
        assert "pricing" in data, "Missing pricing in config"
        pricing = data["pricing"]
        assert "3_episodes" in pricing
        assert "5_episodes" in pricing
        assert "7_episodes" in pricing
        
        # Verify pricing values: 3 episodes=15cr, 5 episodes=25cr, 7 episodes=35cr
        assert pricing["3_episodes"]["credits"] == 15, "3 episodes should cost 15 credits"
        assert pricing["5_episodes"]["credits"] == 25, "5 episodes should cost 25 credits"
        assert pricing["7_episodes"]["credits"] == 35, "7 episodes should cost 35 credits"
        
        # Verify add-ons
        assert "add_ons" in data
        assert "export_pdf" in data["add_ons"]
        assert "commercial_license" in data["add_ons"]
        
        # Verify 3 steps
        assert "steps" in data
        assert len(data["steps"]) == 3, "Should have exactly 3 steps"
        
        print("Story Episode Creator config: PASS")

    def test_config_has_correct_steps(self):
        """Test that config has correct 3-step wizard labels"""
        response = requests.get(f"{BASE_URL}/api/story-episode-creator/config")
        data = response.json()
        
        steps = data.get("steps", [])
        step_titles = [s["title"] for s in steps]
        
        assert "Enter Your Idea" in step_titles or "Idea" in str(step_titles), "Missing Step 1: Enter Your Idea"
        assert "Choose Length" in step_titles or "Length" in str(step_titles), "Missing Step 2: Choose Length"
        assert "Generate" in step_titles, "Missing Step 3: Generate"
        
        print("Story Episode Creator steps: PASS")


class TestStoryEpisodeCreatorGeneration(TestAuth):
    """Test Story Episode Creator generation"""
    
    def test_generate_3_episodes(self, auth_headers):
        """Test generating 3 episode series"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "A young inventor named Mia discovers a magical toolbox that brings her drawings to life.",
                "episode_count": 3,
                "add_ons": []
            }
        )
        
        # May fail due to insufficient credits, but endpoint should work
        if response.status_code == 402:
            print("Generate 3 episodes: SKIP (insufficient credits)")
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["episode_count"] == 3
        assert len(data["episodes"]) == 3, "Should have exactly 3 episodes"
        
        # Verify episodes have cliffhangers (except last)
        for i, ep in enumerate(data["episodes"][:-1]):
            assert "cliffhanger" in ep, f"Episode {i+1} should have cliffhanger"
        
        print(f"Generate 3 episodes: PASS - Credits used: {data.get('credits_used')}")

    def test_generate_5_episodes(self, auth_headers):
        """Test generating 5 episode series"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "A space explorer named Leo discovers a hidden planet with friendly aliens who need help.",
                "episode_count": 5,
                "add_ons": []
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["episode_count"] == 5
        assert len(data["episodes"]) == 5
        
        print(f"Generate 5 episodes: PASS - Credits used: {data.get('credits_used')}")

    def test_copyright_blocking_disney(self, auth_headers):
        """Test that Disney characters are blocked"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "Mickey Mouse goes on an adventure to find his lost pet.",
                "episode_count": 3,
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should block Disney content"
        assert "copyright" in response.text.lower() or "branded" in response.text.lower()
        print("Copyright blocking (Disney): PASS")

    def test_copyright_blocking_marvel(self, auth_headers):
        """Test that Marvel characters are blocked"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "Spiderman teams up with Hulk to save the city.",
                "episode_count": 3,
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should block Marvel content"
        print("Copyright blocking (Marvel): PASS")

    def test_copyright_blocking_pokemon(self, auth_headers):
        """Test that Pokemon characters are blocked"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "Pikachu and Ash go on a new pokemon adventure.",
                "episode_count": 3,
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should block Pokemon content"
        print("Copyright blocking (Pokemon): PASS")

    def test_invalid_episode_count(self, auth_headers):
        """Test that invalid episode count is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/story-episode-creator/generate",
            headers=auth_headers,
            json={
                "story_idea": "A valid story idea for testing purposes.",
                "episode_count": 4,  # Invalid - must be 3, 5, or 7
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should reject invalid episode count"
        print("Invalid episode count rejection: PASS")


# =============================================================================
# CONTENT CHALLENGE PLANNER TESTS (4-step wizard)
# =============================================================================
class TestContentChallengePlannerConfig:
    """Test Content Challenge Planner configuration"""
    
    def test_config_endpoint_accessible(self):
        """Test /api/content-challenge-planner/config returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/content-challenge-planner/config")
        assert response.status_code == 200, f"Config endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify 5 platforms
        assert "platforms" in data
        platforms = data["platforms"]
        assert "instagram" in platforms, "Missing Instagram platform"
        assert "youtube" in platforms, "Missing YouTube platform"
        assert "linkedin" in platforms, "Missing LinkedIn platform"
        assert "kids_channel" in platforms, "Missing Kids Channel platform"
        assert "business" in platforms, "Missing Business platform"
        assert len(platforms) == 5, f"Should have exactly 5 platforms, got {len(platforms)}"
        
        print("Content Challenge Planner platforms: PASS - 5 platforms verified")

    def test_config_has_correct_durations(self):
        """Test that durations have correct pricing"""
        response = requests.get(f"{BASE_URL}/api/content-challenge-planner/config")
        data = response.json()
        
        # Verify 3 durations with correct pricing
        assert "durations" in data
        durations = data["durations"]
        assert len(durations) == 3, "Should have exactly 3 durations"
        
        # Check pricing: 7 days=10cr, 14 days=18cr, 30 days=30cr
        duration_map = {d["days"]: d["credits"] for d in durations}
        assert duration_map.get(7) == 10, "7 days should cost 10 credits"
        assert duration_map.get(14) == 18, "14 days should cost 18 credits"
        assert duration_map.get(30) == 30, "30 days should cost 30 credits"
        
        print("Content Challenge Planner durations: PASS - 7d=10cr, 14d=18cr, 30d=30cr")

    def test_config_has_4_goals(self):
        """Test that config has exactly 4 goals"""
        response = requests.get(f"{BASE_URL}/api/content-challenge-planner/config")
        data = response.json()
        
        # Verify 4 goals
        assert "goals" in data
        goals = data["goals"]
        assert "followers" in goals, "Missing Followers goal"
        assert "sales" in goals, "Missing Sales goal"
        assert "engagement" in goals, "Missing Engagement goal"
        assert "brand_growth" in goals, "Missing Brand Growth goal"
        assert len(goals) == 4, f"Should have exactly 4 goals, got {len(goals)}"
        
        print("Content Challenge Planner goals: PASS - 4 goals verified")

    def test_config_has_4_steps(self):
        """Test that config has exactly 4 wizard steps"""
        response = requests.get(f"{BASE_URL}/api/content-challenge-planner/config")
        data = response.json()
        
        assert "steps" in data
        steps = data["steps"]
        assert len(steps) == 4, f"Should have exactly 4 steps, got {len(steps)}"
        
        print("Content Challenge Planner steps: PASS - 4 steps verified")


class TestContentChallengePlannerGeneration(TestAuth):
    """Test Content Challenge Planner generation"""
    
    def test_generate_7_day_plan(self, auth_headers):
        """Test generating 7-day content plan"""
        response = requests.post(
            f"{BASE_URL}/api/content-challenge-planner/generate",
            headers=auth_headers,
            json={
                "platform": "instagram",
                "duration": 7,
                "goal": "followers"
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["duration"] == 7
        assert len(data["daily_plans"]) == 7, "Should have 7 daily plans"
        
        # Verify daily plan structure
        day1 = data["daily_plans"][0]
        assert "hook" in day1, "Missing hook in daily plan"
        assert "content_idea" in day1, "Missing content_idea in daily plan"
        assert "caption" in day1, "Missing caption in daily plan"
        assert "cta" in day1, "Missing CTA in daily plan"
        assert "hashtags" in day1, "Missing hashtags in daily plan"
        
        print(f"Generate 7-day plan: PASS - Credits used: {data.get('credits_used')}")

    def test_generate_14_day_plan(self, auth_headers):
        """Test generating 14-day content plan"""
        response = requests.post(
            f"{BASE_URL}/api/content-challenge-planner/generate",
            headers=auth_headers,
            json={
                "platform": "youtube",
                "duration": 14,
                "goal": "engagement"
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert len(data["daily_plans"]) == 14, "Should have 14 daily plans"
        
        print(f"Generate 14-day plan: PASS - Credits used: {data.get('credits_used')}")

    def test_all_platforms_valid(self, auth_headers):
        """Test that all 5 platforms are accepted"""
        platforms = ["instagram", "youtube", "linkedin", "kids_channel", "business"]
        
        for platform in platforms:
            response = requests.post(
                f"{BASE_URL}/api/content-challenge-planner/generate",
                headers=auth_headers,
                json={
                    "platform": platform,
                    "duration": 7,
                    "goal": "followers"
                }
            )
            
            if response.status_code == 402:
                print(f"Platform {platform}: SKIP (insufficient credits)")
                continue
            
            assert response.status_code == 200, f"Platform {platform} failed: {response.text}"
            print(f"Platform {platform}: PASS")

    def test_invalid_platform_rejected(self, auth_headers):
        """Test that invalid platform is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/content-challenge-planner/generate",
            headers=auth_headers,
            json={
                "platform": "tiktok",  # Invalid
                "duration": 7,
                "goal": "followers"
            }
        )
        
        assert response.status_code == 400, "Should reject invalid platform"
        print("Invalid platform rejection: PASS")


# =============================================================================
# CAPTION REWRITER PRO TESTS (3-step wizard)
# =============================================================================
class TestCaptionRewriterProConfig:
    """Test Caption Rewriter Pro configuration"""
    
    def test_config_endpoint_accessible(self):
        """Test /api/caption-rewriter-pro/config returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/config")
        assert response.status_code == 200, f"Config endpoint failed: {response.text}"
        
        data = response.json()
        
        # Verify 6 tones only
        assert "tones" in data
        tones = data["tones"]
        assert "funny" in tones, "Missing Funny tone"
        assert "luxury" in tones, "Missing Luxury tone"
        assert "bold" in tones, "Missing Bold tone"
        assert "emotional" in tones, "Missing Emotional tone"
        assert "motivational" in tones, "Missing Motivational tone"
        assert "storytelling" in tones, "Missing Storytelling tone"
        assert len(tones) == 6, f"Should have exactly 6 tones, got {len(tones)}"
        
        print("Caption Rewriter Pro tones: PASS - 6 tones verified")

    def test_config_has_correct_pricing(self):
        """Test that pricing packs are correct"""
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/config")
        data = response.json()
        
        # Verify 3 pricing packs: Single=5cr, 3 Tones=12cr, All Tones=20cr
        assert "pricing" in data
        pricing = data["pricing"]
        
        assert "single_tone" in pricing
        assert pricing["single_tone"]["credits"] == 5, "Single tone should cost 5 credits"
        
        assert "three_tones" in pricing
        assert pricing["three_tones"]["credits"] == 12, "3 tones should cost 12 credits"
        
        assert "all_tones" in pricing
        assert pricing["all_tones"]["credits"] == 20, "All tones should cost 20 credits"
        
        print("Caption Rewriter Pro pricing: PASS - Single=5cr, 3Tones=12cr, AllTones=20cr")

    def test_config_has_3_steps(self):
        """Test that config has exactly 3 wizard steps"""
        response = requests.get(f"{BASE_URL}/api/caption-rewriter-pro/config")
        data = response.json()
        
        assert "steps" in data
        steps = data["steps"]
        assert len(steps) == 3, f"Should have exactly 3 steps, got {len(steps)}"
        
        print("Caption Rewriter Pro steps: PASS - 3 steps verified")


class TestCaptionRewriterProGeneration(TestAuth):
    """Test Caption Rewriter Pro generation"""
    
    def test_rewrite_single_tone(self, auth_headers):
        """Test generating 3 variations in single tone"""
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            headers=auth_headers,
            json={
                "text": "Check out our new product! It's really good and you should buy it.",
                "tone": "funny",
                "pack_type": "single_tone",
                "add_ons": []
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Rewrite failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["total_variations"] == 3, "Single tone should have 3 variations"
        
        # Verify 3 variations in selected tone
        assert "funny" in data["results"]
        assert len(data["results"]["funny"]["variations"]) == 3
        
        print(f"Rewrite single tone: PASS - {data.get('total_variations')} variations generated")

    def test_rewrite_three_tones(self, auth_headers):
        """Test generating 9 variations in 3 tones"""
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            headers=auth_headers,
            json={
                "text": "Just launched my new business! Really excited about this opportunity.",
                "tone": "motivational",
                "pack_type": "three_tones",
                "add_ons": []
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Rewrite failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["total_variations"] == 9, "3 tones pack should have 9 variations"
        
        # Verify 3 tones with 3 variations each
        assert len(data["results"]) == 3, "Should have 3 different tones"
        
        print(f"Rewrite 3 tones: PASS - {data.get('total_variations')} variations, {data.get('credits_used')} credits")

    def test_rewrite_all_tones(self, auth_headers):
        """Test generating 18 variations in all 6 tones"""
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            headers=auth_headers,
            json={
                "text": "Today we're announcing something special that will change the way you think about creativity.",
                "tone": "bold",
                "pack_type": "all_tones",
                "add_ons": []
            }
        )
        
        if response.status_code == 402:
            pytest.skip("Insufficient credits for test")
        
        assert response.status_code == 200, f"Rewrite failed: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert data["total_variations"] == 18, "All tones pack should have 18 variations"
        
        # Verify all 6 tones with 3 variations each
        assert len(data["results"]) == 6, "Should have all 6 tones"
        
        print(f"Rewrite all tones: PASS - {data.get('total_variations')} variations, {data.get('credits_used')} credits")

    def test_copyright_blocking(self, auth_headers):
        """Test that copyrighted content is blocked"""
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            headers=auth_headers,
            json={
                "text": "Just bought my new Nike shoes and they're amazing!",
                "tone": "funny",
                "pack_type": "single_tone",
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should block brand names"
        assert "copyright" in response.text.lower() or "branded" in response.text.lower()
        print("Copyright blocking: PASS")

    def test_invalid_tone_rejected(self, auth_headers):
        """Test that invalid tone is rejected"""
        response = requests.post(
            f"{BASE_URL}/api/caption-rewriter-pro/rewrite",
            headers=auth_headers,
            json={
                "text": "A valid caption for testing purposes.",
                "tone": "sarcastic",  # Invalid - not in 6 tones
                "pack_type": "single_tone",
                "add_ons": []
            }
        )
        
        assert response.status_code == 400, "Should reject invalid tone"
        print("Invalid tone rejection: PASS")


# =============================================================================
# DASHBOARD INTEGRATION TESTS
# =============================================================================
class TestDashboardIntegration(TestAuth):
    """Test that Dashboard shows all 3 rebuilt features"""
    
    def test_health_check(self):
        """Test API health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health check: PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
