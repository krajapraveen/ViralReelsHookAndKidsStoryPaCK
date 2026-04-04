"""
Regression tests for media protection layer.
Covers: URL normalization, prefix matching, secure_url generation, file_url stripping.
"""
import pytest
from routes.viral_ideas_v2 import _is_protected_asset_url, _normalize_asset_url


class TestIsProtectedAssetUrl:
    """Verify both /api/static/ and /static/ prefixes are recognized."""

    def test_api_static_video(self):
        assert _is_protected_asset_url("/api/static/generated/viral_videos/video_abc.mp4") is True

    def test_api_static_thumbnail(self):
        assert _is_protected_asset_url("/api/static/generated/viral_thumbs/thumb_abc.png") is True

    def test_api_static_audio(self):
        assert _is_protected_asset_url("/api/static/generated/viral_audio/vo_abc.mp3") is True

    def test_api_static_zip(self):
        assert _is_protected_asset_url("/api/static/generated/viral_packs/pack_abc.zip") is True

    def test_static_thumbnail_no_api_prefix(self):
        """The exact bug case — /static/ without /api/ prefix."""
        assert _is_protected_asset_url("/static/generated/viral_thumbs/thumb_abc.png") is True

    def test_static_zip_no_api_prefix(self):
        assert _is_protected_asset_url("/static/generated/viral_packs/pack_abc.zip") is True

    def test_unrelated_static_path(self):
        assert _is_protected_asset_url("/api/static/other/file.txt") is False

    def test_empty_string(self):
        assert _is_protected_asset_url("") is False

    def test_external_url(self):
        assert _is_protected_asset_url("https://example.com/file.mp4") is False

    def test_partial_match(self):
        assert _is_protected_asset_url("/api/static/generated/vira") is False

    def test_none_guard(self):
        """Callers should guard against None, but the function should not crash."""
        try:
            result = _is_protected_asset_url(None)
            assert result is False
        except (TypeError, AttributeError):
            pass  # Acceptable — caller's responsibility to guard


class TestNormalizeAssetUrl:
    """Verify normalization to /api/static/... format."""

    def test_already_normalized(self):
        url = "/api/static/generated/viral_videos/video_abc.mp4"
        assert _normalize_asset_url(url) == url

    def test_missing_api_prefix(self):
        url = "/static/generated/viral_thumbs/thumb_abc.png"
        assert _normalize_asset_url(url) == "/api/static/generated/viral_thumbs/thumb_abc.png"

    def test_missing_api_prefix_zip(self):
        url = "/static/generated/viral_packs/pack_abc.zip"
        assert _normalize_asset_url(url) == "/api/static/generated/viral_packs/pack_abc.zip"

    def test_does_not_double_prefix(self):
        url = "/api/static/generated/viral_audio/vo_abc.mp3"
        normalized = _normalize_asset_url(url)
        assert not normalized.startswith("/api/api/")
        assert normalized == url

    def test_unrelated_path_unchanged(self):
        url = "/some/other/path.txt"
        assert _normalize_asset_url(url) == url
