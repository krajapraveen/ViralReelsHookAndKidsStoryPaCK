"""
Iteration 255: Gallery Showcase Testing
Tests for gallery page with 30 showcase items, presigned URLs, rate limits, and category filtering.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://comic-pipeline-v2.preview.emergentagent.com')


class TestGalleryShowcase:
    """Test suite for gallery showcase functionality"""

    def test_gallery_returns_exactly_30_videos(self):
        """Verify gallery returns exactly 30 videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        data = response.json()
        videos = data.get('videos', [])
        assert len(videos) == 30, f"Expected 30 videos, got {len(videos)}"

    def test_all_videos_have_professional_titles(self):
        """Verify no test/debug titles like TEST_, Concurrent Test, etc."""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        
        test_titles = []
        for video in videos:
            title = video.get('title', '').upper()
            if 'TEST_' in title or 'CONCURRENT TEST' in title or 'DEBUG' in title:
                test_titles.append(video.get('title'))
        
        assert len(test_titles) == 0, f"Found test/debug titles: {test_titles}"

    def test_all_videos_have_presigned_output_urls(self):
        """Verify all video output URLs contain X-Amz-Algorithm (presigned)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        
        for video in videos:
            output_url = video.get('output_url', '')
            assert 'X-Amz-Algorithm' in output_url, f"Video {video.get('title')} missing presigned output URL"

    def test_all_videos_have_presigned_thumbnail_urls(self):
        """Verify all video thumbnail URLs contain X-Amz-Algorithm (presigned)"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        
        for video in videos:
            thumbnail_url = video.get('thumbnail_url', '')
            assert thumbnail_url, f"Video {video.get('title')} missing thumbnail URL"
            assert 'X-Amz-Algorithm' in thumbnail_url, f"Video {video.get('title')} missing presigned thumbnail URL"


class TestCategoryFiltering:
    """Test category filtering and counts"""

    def test_categories_endpoint_returns_correct_structure(self):
        """Verify categories endpoint returns all expected categories"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        data = response.json()
        categories = data.get('categories', [])
        
        # Should have All + 5 specific categories = 6 total
        assert len(categories) == 6, f"Expected 6 categories, got {len(categories)}"
        
        # Check category names exist
        category_ids = [c.get('id') for c in categories]
        assert 'all' in category_ids
        assert 'cartoon_2d' in category_ids
        assert 'watercolor' in category_ids
        assert 'anime_style' in category_ids
        assert 'comic_book' in category_ids
        assert 'claymation' in category_ids

    def test_category_counts_are_correct(self):
        """Verify category counts match expected values"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/categories")
        assert response.status_code == 200
        categories = response.json().get('categories', [])
        
        counts = {c.get('id'): c.get('count') for c in categories}
        
        assert counts.get('all') == 30, f"Expected 30 for 'all', got {counts.get('all')}"
        assert counts.get('cartoon_2d') == 14, f"Expected 14 for '2D Cartoon', got {counts.get('cartoon_2d')}"
        assert counts.get('watercolor') == 9, f"Expected 9 for 'Watercolor', got {counts.get('watercolor')}"
        assert counts.get('anime_style') == 4, f"Expected 4 for 'Anime', got {counts.get('anime_style')}"
        assert counts.get('comic_book') == 2, f"Expected 2 for 'Comic Book', got {counts.get('comic_book')}"
        assert counts.get('claymation') == 1, f"Expected 1 for 'Claymation', got {counts.get('claymation')}"

    def test_filter_cartoon_2d_returns_14_videos(self):
        """Filter by cartoon_2d should return 14 videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=cartoon_2d")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 14, f"Expected 14 videos for cartoon_2d, got {len(videos)}"

    def test_filter_watercolor_returns_9_videos(self):
        """Filter by watercolor should return 9 videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=watercolor")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 9, f"Expected 9 videos for watercolor, got {len(videos)}"

    def test_filter_anime_style_returns_4_videos(self):
        """Filter by anime_style should return 4 videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=anime_style")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 4, f"Expected 4 videos for anime_style, got {len(videos)}"

    def test_filter_comic_book_returns_2_videos(self):
        """Filter by comic_book should return 2 videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=comic_book")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 2, f"Expected 2 videos for comic_book, got {len(videos)}"

    def test_filter_claymation_returns_1_video(self):
        """Filter by claymation should return 1 video"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?category=claymation")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 1, f"Expected 1 video for claymation, got {len(videos)}"


class TestSortOptions:
    """Test sort options functionality"""

    def test_sort_newest_works(self):
        """Sort by newest should return videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort=newest")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 30

    def test_sort_most_remixed_works(self):
        """Sort by most_remixed should return videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort=most_remixed")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 30

    def test_sort_trending_works(self):
        """Sort by trending should return videos"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery?sort=trending")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        assert len(videos) == 30


class TestGalleryDetailAPI:
    """Test gallery detail endpoint for remix functionality"""

    def test_gallery_detail_returns_presigned_url(self):
        """Get single video detail returns presigned URL"""
        # Get first video's job_id
        gallery_response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        videos = gallery_response.json().get('videos', [])
        job_id = videos[0].get('job_id')
        
        # Get detail
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery/{job_id}")
        assert response.status_code == 200
        video = response.json().get('video', {})
        
        assert video.get('title')
        assert 'X-Amz-Algorithm' in video.get('output_url', '')


class TestRateLimitStatus:
    """Test rate limit configuration"""

    def test_rate_limit_max_is_5_per_hour(self):
        """Rate limit should be max 5 videos per hour"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@visionary-suite.com", "password": "Test@2026#"}
        )
        assert login_response.status_code == 200
        token = login_response.json().get('token')
        
        # Check rate limit status
        response = requests.get(
            f"{BASE_URL}/api/pipeline/rate-limit-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('max_per_hour') == 5, f"Expected max_per_hour=5, got {data.get('max_per_hour')}"


class TestVideoDataIntegrity:
    """Test video data integrity and structure"""

    def test_all_videos_have_required_fields(self):
        """All videos should have required fields"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        
        required_fields = ['job_id', 'title', 'output_url', 'animation_style']
        
        for video in videos:
            for field in required_fields:
                assert video.get(field), f"Video missing {field}: {video.get('title', 'Unknown')}"

    def test_no_broken_thumbnails(self):
        """All thumbnail URLs should be valid presigned URLs"""
        response = requests.get(f"{BASE_URL}/api/pipeline/gallery")
        assert response.status_code == 200
        videos = response.json().get('videos', [])
        
        broken_thumbs = []
        for video in videos:
            thumb = video.get('thumbnail_url', '')
            if not thumb or 'X-Amz-Algorithm' not in thumb:
                broken_thumbs.append(video.get('title'))
        
        assert len(broken_thumbs) == 0, f"Videos with broken thumbnails: {broken_thumbs}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
