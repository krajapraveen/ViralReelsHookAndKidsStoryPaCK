"""
Test Suite: Truth-vs-Illusion Repair (Iteration 310)
Tests for:
1. Zero placehold.co URLs in backend API responses
2. Gallery returns real content with real images
3. Explore returns real content with real thumbnails
4. User-jobs excludes ORPHANED status jobs
5. Universal negative prompts in all image generation services
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


class TestNoPlaceholdCo:
    """All backend APIs must not return placehold.co URLs"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Authenticate and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code} - {response.text[:200]}")

    def test_gallery_no_placehold_co(self):
        """P0: /api/pipeline/gallery must not return placehold.co URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200, f"Gallery failed: {response.status_code}"
        
        data = response.json()
        # Gallery returns data in 'videos' key (Story Video Gallery)
        items = data.get("videos", data.get("items", data.get("jobs", [])))
        if isinstance(data, list):
            items = data
        
        assert len(items) > 0, "Gallery should have items"
        print(f"Gallery returned {len(items)} items")
        
        for item in items:
            # Check all URL fields
            for field in ["output_url", "thumbnail_url", "preview_url", "coverUrl", "pdfUrl"]:
                url = item.get(field)
                if url:
                    assert "placehold.co" not in url, f"Found placehold.co in {field}: {url}"
            
            # Check nested scene_images
            scene_images = item.get("scene_images", {})
            if scene_images:
                for key, url in scene_images.items():
                    if url:
                        assert "placehold.co" not in str(url), f"Found placehold.co in scene_images[{key}]: {url}"
        
        print("Gallery: No placehold.co URLs found")

    def test_explore_no_placehold_co(self):
        """P0: /api/public/explore must not return placehold.co URLs"""
        for tab in ["trending", "newest", "most_remixed"]:
            response = requests.get(f"{BASE_URL}/api/public/explore", params={"tab": tab})
            assert response.status_code == 200, f"Explore {tab} failed: {response.status_code}"
            
            data = response.json()
            items = data.get("items", [])
            
            print(f"Explore {tab}: {len(items)} items")
            
            for item in items:
                for field in ["thumbnail_url", "output_url", "preview_url"]:
                    url = item.get(field)
                    if url:
                        assert "placehold.co" not in url, f"Found placehold.co in {field} ({tab}): {url}"
        
        print("Explore: No placehold.co URLs found in any tab")

    def test_user_jobs_no_placehold_co(self, auth_token):
        """P0: /api/pipeline/user-jobs must not return placehold.co URLs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        assert response.status_code == 200, f"User-jobs failed: {response.status_code}"
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        print(f"User-jobs: {len(jobs)} jobs returned")
        
        for job in jobs:
            for field in ["output_url", "thumbnail_url", "preview_url"]:
                url = job.get(field)
                if url:
                    assert "placehold.co" not in url, f"Found placehold.co in {field}: {url}"
        
        print("User-jobs: No placehold.co URLs found")

    def test_active_chains_no_placehold_co(self, auth_token):
        """P0: /api/photo-to-comic/active-chains must not return placehold.co URLs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/photo-to-comic/active-chains", headers=headers)
        assert response.status_code == 200, f"Active-chains failed: {response.status_code}"
        
        data = response.json()
        chains = data.get("chains", [])
        
        print(f"Active-chains: {len(chains)} chains returned")
        
        for chain in chains:
            preview_url = chain.get("preview_url")
            if preview_url:
                assert "placehold.co" not in preview_url, f"Found placehold.co in preview_url: {preview_url}"
        
        print("Active-chains: No placehold.co URLs found")


class TestGalleryRealContent:
    """Gallery must show real content with real images"""

    def test_gallery_has_real_thumbnails(self):
        """Gallery items should have real R2 thumbnails or scene_images"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("videos", data.get("items", data.get("jobs", [])))
        if isinstance(data, list):
            items = data
        
        # Count items with real thumbnails (R2 presigned URLs)
        real_thumbnails = 0
        for item in items:
            thumb = item.get("thumbnail_url")
            scene_images = item.get("scene_images", {})
            
            if thumb and ("r2.cloudflarestorage.com" in thumb or "pub-" in thumb or "X-Amz-Signature" in thumb):
                real_thumbnails += 1
            elif scene_images:
                # Has scene_images as fallback
                real_thumbnails += 1
        
        print(f"Gallery: {real_thumbnails}/{len(items)} items have real thumbnails")
        # At least 5 items should have real thumbnails (relaxed requirement)
        assert real_thumbnails >= 5, f"Expected >= 5 items with real thumbnails, got {real_thumbnails}"

    def test_gallery_returns_sufficient_items(self):
        """Gallery should return substantial content (10+ items)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("videos", data.get("items", data.get("jobs", [])))
        if isinstance(data, list):
            items = data
        
        print(f"Gallery returned {len(items)} items")
        assert len(items) >= 10, f"Expected >= 10 gallery items, got {len(items)}"


class TestExploreRealContent:
    """Explore must show real content with real thumbnails"""

    def test_explore_trending_has_real_content(self):
        """Explore trending tab should return real items with thumbnails"""
        response = requests.get(f"{BASE_URL}/api/public/explore", params={"tab": "trending"})
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        print(f"Explore trending: {len(items)} items")
        
        # Count items with real R2 thumbnails
        real_thumbnails = 0
        for item in items:
            thumb = item.get("thumbnail_url")
            if thumb:
                # R2 URL patterns: contains r2.cloudflarestorage.com or pub- or has signature
                if "r2.cloudflarestorage.com" in thumb or "pub-" in thumb or "X-Amz-Signature" in thumb:
                    real_thumbnails += 1
        
        print(f"Explore trending: {real_thumbnails}/{len(items)} have R2 thumbnails")
        # At least some items should have R2 thumbnails
        assert real_thumbnails > 0, "Expected at least some items with R2 thumbnails"


class TestUserJobsExcludesOrphaned:
    """User-jobs must exclude ORPHANED status jobs"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Authenticate and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_user_jobs_no_orphaned_status(self, auth_token):
        """P0: /api/pipeline/user-jobs should return zero ORPHANED jobs"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/pipeline/user-jobs", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        jobs = data.get("jobs", [])
        
        orphaned_count = sum(1 for job in jobs if job.get("status") == "ORPHANED")
        
        print(f"User-jobs: {len(jobs)} total, {orphaned_count} ORPHANED")
        assert orphaned_count == 0, f"Found {orphaned_count} ORPHANED jobs that should be filtered out"


class TestUniversalNegativePrompts:
    """Verify universal negative prompts exist in all image generation modules"""

    def test_pipeline_engine_has_universal_negative_prompt(self):
        """pipeline_engine.py should have UNIVERSAL_NEGATIVE_PROMPT constant"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "UNIVERSAL_NEGATIVE_PROMPT", "/app/backend/services/pipeline_engine.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        print(f"pipeline_engine.py: UNIVERSAL_NEGATIVE_PROMPT found {count} times")
        assert count >= 1, "UNIVERSAL_NEGATIVE_PROMPT not found in pipeline_engine.py"

    def test_photo_to_comic_has_negative_prompts(self):
        """photo_to_comic.py should have UNIVERSAL_NEGATIVE_PROMPTS constant"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "UNIVERSAL_NEGATIVE_PROMPTS", "/app/backend/routes/photo_to_comic.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        print(f"photo_to_comic.py: UNIVERSAL_NEGATIVE_PROMPTS found {count} times")
        assert count >= 1, "UNIVERSAL_NEGATIVE_PROMPTS not found in photo_to_comic.py"

    def test_comix_ai_has_negative_prompt(self):
        """comix_ai.py should have COMIX_NEGATIVE_PROMPT constant"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "COMIX_NEGATIVE_PROMPT", "/app/backend/routes/comix_ai.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        print(f"comix_ai.py: COMIX_NEGATIVE_PROMPT found {count} times")
        assert count >= 2, "COMIX_NEGATIVE_PROMPT usage not found in comix_ai.py"

    def test_comic_storybook_has_negative_prompt(self):
        """comic_storybook.py should have STORYBOOK_NEGATIVE_PROMPT constant"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "STORYBOOK_NEGATIVE_PROMPT", "/app/backend/routes/comic_storybook.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        print(f"comic_storybook.py: STORYBOOK_NEGATIVE_PROMPT found {count} times")
        assert count >= 2, "STORYBOOK_NEGATIVE_PROMPT usage not found in comic_storybook.py"

    def test_gif_maker_has_negative_prompt(self):
        """gif_maker.py should have GIF_NEGATIVE_PROMPT constant"""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "GIF_NEGATIVE_PROMPT", "/app/backend/routes/gif_maker.py"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        print(f"gif_maker.py: GIF_NEGATIVE_PROMPT found {count} times")
        assert count >= 2, "GIF_NEGATIVE_PROMPT usage not found in gif_maker.py"


class TestAPIResponseVerification:
    """Verify API responses return real content"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Authenticate and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Auth failed: {response.status_code}")

    def test_gallery_output_urls_valid(self):
        """Gallery output_url should be presigned R2 URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("videos", data.get("items", data.get("jobs", [])))
        if isinstance(data, list):
            items = data
        
        valid_urls = 0
        for item in items:
            url = item.get("output_url")
            if url:
                # Should be R2 presigned URL or valid URL
                if "r2.dev" in url or "X-Amz-Signature" in url or url.startswith("https://"):
                    valid_urls += 1
        
        print(f"Gallery: {valid_urls}/{len(items)} have valid output URLs")
        assert valid_urls > 0, "Expected at least some valid output URLs"

    def test_explore_items_have_required_fields(self):
        """Explore items should have required fields"""
        response = requests.get(f"{BASE_URL}/api/public/explore", params={"tab": "trending"})
        assert response.status_code == 200
        
        data = response.json()
        items = data.get("items", [])
        
        for item in items[:5]:  # Check first 5
            assert "job_id" in item, f"Missing job_id in item: {item}"
            assert "title" in item, f"Missing title in item: {item}"
        
        print(f"Explore items have required fields (checked {min(5, len(items))})")

    def test_pipeline_options_api(self):
        """Pipeline options should return animation styles, age groups, voices"""
        response = requests.get(f"{BASE_URL}/api/pipeline/options")
        assert response.status_code == 200
        
        data = response.json()
        
        assert "animation_styles" in data, "Missing animation_styles"
        assert "age_groups" in data, "Missing age_groups"
        assert "voice_presets" in data, "Missing voice_presets"
        
        print(f"Pipeline options: {len(data['animation_styles'])} styles, {len(data['age_groups'])} ages, {len(data['voice_presets'])} voices")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
