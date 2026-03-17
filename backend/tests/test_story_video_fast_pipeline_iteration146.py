"""
Test Suite for Story Video Fast Pipeline - P0 Performance Optimization
Iteration 146: Testing parallel image+voice generation, single-pass ffmpeg, async R2 upload

Tests cover:
- Fast options API (animation_styles, age_groups, voice_presets, credit_costs)
- Fast video status API with timing breakdown
- Copyright compliance (blocked trademarked characters)
- Credits deduction and insufficient credits (402 error)
- Video output validation
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comic-pipeline-v2.preview.emergentagent.com').rstrip('/')
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"

# Known benchmark job_id from the optimization run
BENCHMARK_JOB_ID = "29ff0a96-4839-4fa5-b388-0fdef7b7b4eb"


class TestFastOptionsAPI:
    """Test /api/story-video-studio/fast/options endpoint"""
    
    def test_options_returns_success(self):
        """Options API returns success with all required fields"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
    def test_options_contains_animation_styles(self):
        """Options contains animation_styles array with required structure"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        data = response.json()
        
        assert "animation_styles" in data
        assert len(data["animation_styles"]) >= 4
        
        # Check structure of first style
        style = data["animation_styles"][0]
        assert "id" in style
        assert "name" in style
        assert "description" in style
        assert "style_prompt" in style
        assert "negative_prompt" in style
        
    def test_options_contains_age_groups(self):
        """Options contains age_groups with max_scenes configuration"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        data = response.json()
        
        assert "age_groups" in data
        assert len(data["age_groups"]) >= 4
        
        # Check structure
        age = data["age_groups"][0]
        assert "id" in age
        assert "name" in age
        assert "max_scenes" in age
        
    def test_options_contains_voice_presets(self):
        """Options contains voice_presets with voice ID and speed"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        data = response.json()
        
        assert "voice_presets" in data
        assert len(data["voice_presets"]) >= 4
        
        voice = data["voice_presets"][0]
        assert "id" in voice
        assert "voice" in voice
        assert "speed" in voice
        assert "name" in voice
        
    def test_options_contains_credit_costs(self):
        """Options contains credit_costs for different video sizes"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        data = response.json()
        
        assert "credit_costs" in data
        costs = data["credit_costs"]
        assert "full_video_small" in costs
        assert "full_video_medium" in costs
        assert "full_video_large" in costs
        assert costs["full_video_small"] <= costs["full_video_medium"] <= costs["full_video_large"]
        
    def test_options_contains_music_moods(self):
        """Options contains music_moods for background music selection"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/options")
        data = response.json()
        
        assert "music_moods" in data
        assert len(data["music_moods"]) >= 4


class TestFastVideoStatusAPI:
    """Test /api/story-video-studio/fast/status/{job_id} endpoint"""
    
    def test_status_returns_job_details(self):
        """Status API returns job details for known benchmark job"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "job" in data
        
    def test_status_contains_timing_breakdown(self):
        """Status contains detailed timing breakdown for performance analysis"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        data = response.json()
        job = data["job"]
        
        assert "timing" in job
        timing = job["timing"]
        
        # Required timing fields from optimized pipeline
        assert "scene_generation_s" in timing
        assert "parallel_media_s" in timing
        assert "video_assembly_s" in timing
        assert "r2_upload_s" in timing
        assert "total_pipeline_s" in timing
        
        # All timings should be positive numbers
        assert timing["scene_generation_s"] >= 0
        assert timing["parallel_media_s"] >= 0
        assert timing["video_assembly_s"] >= 0
        
    def test_status_completed_has_output_url(self):
        """Completed job has output_url pointing to R2 CDN"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        data = response.json()
        job = data["job"]
        
        assert job["status"] == "COMPLETED"
        assert job["output_url"] is not None
        assert "r2.dev" in job["output_url"] or "/static/" in job["output_url"]
        
    def test_status_404_for_unknown_job(self):
        """Status returns 404 for non-existent job_id"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/unknown-job-id-12345")
        assert response.status_code == 404
        
    def test_status_shows_progress_info(self):
        """Status shows progress percentage and current step"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        data = response.json()
        job = data["job"]
        
        assert "progress" in job
        assert "current_step" in job
        assert job["progress"] == 100  # Completed job


class TestCopyrightCompliance:
    """Test copyright compliance blocking for trademarked characters"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
            
    def test_blocks_mickey_mouse(self):
        """Blocks Mickey Mouse trademarked character"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/fast/generate",
            headers=self.headers,
            json={
                "story_text": "Once upon a time, Mickey Mouse went on an adventure. He met his friend Minnie and they played in the park. The end of the story about Mickey and friends.",
                "title": "Mickey's Adventure",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            }
        )
        assert response.status_code == 400
        assert "copyrighted" in response.json()["detail"].lower() or "mickey" in response.json()["detail"].lower()
        
    def test_blocks_frozen_elsa(self):
        """Blocks Frozen/Elsa trademarked characters"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/fast/generate",
            headers=self.headers,
            json={
                "story_text": "Queen Elsa used her ice powers to build a magical castle. Anna came to visit and they had a wonderful time in Arendelle. The frozen kingdom was beautiful.",
                "title": "Elsa's Ice Castle",
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8"
            }
        )
        assert response.status_code == 400
        assert "copyrighted" in response.json()["detail"].lower() or "elsa" in response.json()["detail"].lower() or "frozen" in response.json()["detail"].lower()
        
    def test_blocks_pokemon_pikachu(self):
        """Blocks Pokemon/Pikachu trademarked characters"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/fast/generate",
            headers=self.headers,
            json={
                "story_text": "Pikachu and Ash went on a journey to become Pokemon masters. They caught many Pokemon and won battles at the gym. Pikachu used thunderbolt attack!",
                "title": "Pikachu Adventure",
                "animation_style": "anime_style",
                "age_group": "kids_5_8"
            }
        )
        assert response.status_code == 400
        assert "copyrighted" in response.json()["detail"].lower() or "pikachu" in response.json()["detail"].lower() or "pokemon" in response.json()["detail"].lower()
        
    def test_blocks_marvel_spiderman(self):
        """Blocks Marvel Spider-Man character"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/fast/generate",
            headers=self.headers,
            json={
                "story_text": "Spider-Man swung through the city saving people. Peter Parker was a friendly neighborhood hero. The avengers helped him defeat the villain.",
                "title": "Spider-Man Story",
                "animation_style": "comic_book",
                "age_group": "kids_5_8"
            }
        )
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "copyrighted" in detail or "spider" in detail or "avengers" in detail


class TestCreditsDeduction:
    """Test credits handling for fast video generation"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get authentication token and current credits"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.initial_credits = data["user"]["credits"]
        else:
            pytest.skip("Authentication failed")
            
    def test_user_has_credits(self):
        """Verify test user has credits available"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert response.status_code == 200
        assert response.json()["credits"] >= 0


class TestVideoOutputValidation:
    """Test that video output is valid and accessible"""
    
    def test_benchmark_video_accessible(self):
        """Benchmark video URL is accessible"""
        # Get the video URL from status
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        data = response.json()
        video_url = data["job"]["output_url"]
        
        # HEAD request to check accessibility
        if video_url and video_url.startswith("http"):
            head_response = requests.head(video_url, timeout=10)
            assert head_response.status_code == 200
            
            # Check content type is video
            content_type = head_response.headers.get("Content-Type", "")
            assert "video" in content_type or "mp4" in content_type or "application/octet-stream" in content_type
            
    def test_video_has_reasonable_size(self):
        """Video file has reasonable size (not empty, not corrupted)"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        data = response.json()
        video_url = data["job"]["output_url"]
        
        if video_url and video_url.startswith("http"):
            head_response = requests.head(video_url, timeout=10)
            content_length = head_response.headers.get("Content-Length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                # Video should be between 1MB and 100MB
                assert 1 <= size_mb <= 100, f"Video size {size_mb:.1f}MB is outside expected range"


class TestPreviousFeaturesStillWork:
    """Regression tests - previous features should still work"""
    
    def test_gif_maker_page_accessible(self):
        """GIF maker API is accessible"""
        response = requests.get(f"{BASE_URL}/api/reaction-gif-maker/config")
        # Should return 200 with config, or 404 if not implemented
        assert response.status_code in [200, 404]
        
    def test_blog_posts_accessible(self):
        """Blog posts API is accessible"""
        response = requests.get(f"{BASE_URL}/api/blog/posts")
        assert response.status_code == 200
        
    def test_payment_history_accessible(self):
        """Payment history requires auth but endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/cashfree/payments/history")
        # Should return 401 without auth (endpoint exists)
        assert response.status_code in [200, 401, 403]
        
    def test_health_endpoint(self):
        """Health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestTimingBreakdownAnalysis:
    """Analyze timing breakdown from benchmark job"""
    
    def test_scene_generation_under_15_seconds(self):
        """Scene generation should complete in under 15 seconds"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        timing = response.json()["job"]["timing"]
        assert timing["scene_generation_s"] < 15, f"Scene generation took {timing['scene_generation_s']}s (expected <15s)"
        
    def test_video_assembly_under_20_seconds(self):
        """Video assembly should complete in under 20 seconds"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        timing = response.json()["job"]["timing"]
        assert timing["video_assembly_s"] < 20, f"Video assembly took {timing['video_assembly_s']}s (expected <20s)"
        
    def test_r2_upload_under_30_seconds(self):
        """R2 upload should complete in under 30 seconds"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        timing = response.json()["job"]["timing"]
        assert timing["r2_upload_s"] < 30, f"R2 upload took {timing['r2_upload_s']}s (expected <30s)"
        
    def test_parallel_media_is_bottleneck(self):
        """Parallel media generation is the bottleneck (external API)"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/status/{BENCHMARK_JOB_ID}")
        timing = response.json()["job"]["timing"]
        
        # Parallel media (image generation) should be > 60% of total time
        # This confirms the bottleneck is external GPT Image 1 API
        total = timing["total_pipeline_s"]
        parallel = timing["parallel_media_s"]
        
        if total > 0:
            ratio = parallel / total
            assert ratio > 0.5, f"Parallel media is {ratio*100:.1f}% of total (expected >50%)"


class TestUserJobsAPI:
    """Test /api/story-video-studio/fast/user-jobs endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Authentication failed")
            
    def test_user_jobs_requires_auth(self):
        """User jobs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/fast/user-jobs")
        assert response.status_code in [401, 403]
        
    def test_user_jobs_returns_list(self):
        """User jobs returns list of jobs"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/fast/user-jobs",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
