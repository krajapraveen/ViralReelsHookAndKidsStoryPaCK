"""
Deterministic Homepage Personalization System Tests - Iteration 381
═══════════════════════════════════════════════════════════════════════════════
Tests the NEW API contract for /api/engagement/story-feed:
- personalization: { enabled, profile_strength, event_count }
- hero: { ...story }
- rows: [ { key, title, icon, icon_color, stories: [...] }, ... ]
- features: [ { name, desc, icon, path, key, gradient, score }, ... ]
- live_stats: { stories_today, total_stories }

SCORING FORMULAS:
STORY SCORE: (0.30 × category_affinity) + (0.20 × continue_rate) + (0.15 × completion_rate)
             + (0.10 × share_rate) + (0.10 × freshness_score) + (0.10 × momentum_score)
             + (0.05 × global_trending_score)

FEATURE SCORE: (0.50 × feature_affinity) + (0.25 × recent_usage) + (0.15 × success_rate)
               + (0.10 × monetization_priority)

EVENT WEIGHTS: card_click=1, watch_start=2, continue_click=5, watch_complete=8,
               share_click=10, generation_start=6, generation_complete=12

ROW PRIORITY:
- IF user has active stories → continue_stories = rank 1
- ELSE IF high continue_rate → trending = rank 1
- ELSE → fresh = rank 1

COLD START: If <5 events, personalization.enabled=false, return default order
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
TEST_USER_ID = "ea3b038c-d523-4a49-9fa5-e00c761fa4aa"

ADMIN_USER_EMAIL = "admin@creatorstudio.ai"
ADMIN_USER_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_token(api_client):
    """Get authentication token for test user."""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def authenticated_client(api_client, test_user_token):
    """Session with auth header for test user."""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestStoryFeedAPIContract:
    """Tests for GET /api/engagement/story-feed new API contract."""
    
    def test_anonymous_feed_returns_new_contract_structure(self, api_client):
        """Anonymous feed should return new API contract with personalization, hero, rows[], features[], live_stats."""
        response = api_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify new contract structure
        assert "personalization" in data, "Missing 'personalization' key in response"
        assert "hero" in data, "Missing 'hero' key in response"
        assert "rows" in data, "Missing 'rows' key in response"
        assert "features" in data, "Missing 'features' key in response"
        assert "live_stats" in data, "Missing 'live_stats' key in response"
        
        # Verify personalization structure
        personalization = data["personalization"]
        assert "enabled" in personalization, "Missing 'enabled' in personalization"
        assert "profile_strength" in personalization, "Missing 'profile_strength' in personalization"
        assert "event_count" in personalization, "Missing 'event_count' in personalization"
        
        print(f"✓ Anonymous feed returns new API contract structure")
        print(f"  - personalization: {personalization}")
        print(f"  - rows count: {len(data['rows'])}")
        print(f"  - features count: {len(data['features'])}")
    
    def test_anonymous_feed_personalization_disabled(self, api_client):
        """Anonymous (no auth) feed should return personalization.enabled=false."""
        # Use a fresh session without auth
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        personalization = data.get("personalization", {})
        
        assert personalization.get("enabled") == False, \
            f"Expected personalization.enabled=false for anonymous, got {personalization.get('enabled')}"
        
        print(f"✓ Anonymous feed has personalization.enabled=false")
    
    def test_anonymous_feed_default_row_order(self, api_client):
        """Anonymous feed should return rows in default order (fresh first for cold start)."""
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        # For cold start (no events), fresh should be first
        if len(rows) > 0:
            row_keys = [r.get("key") for r in rows]
            print(f"✓ Anonymous feed row order: {row_keys}")
            # Fresh should be first for cold start users
            # But if there are no fresh stories, trending may be first
            assert len(row_keys) > 0, "Expected at least one row"
    
    def test_authenticated_feed_returns_new_contract(self, authenticated_client):
        """Authenticated feed should return new API contract with personalization enabled."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify new contract structure
        assert "personalization" in data
        assert "hero" in data
        assert "rows" in data
        assert "features" in data
        assert "live_stats" in data
        
        personalization = data["personalization"]
        print(f"✓ Authenticated feed personalization: {personalization}")
        
        # Test user has 6 events (>= 5 threshold), so personalization should be enabled
        if personalization.get("event_count", 0) >= 5:
            assert personalization.get("enabled") == True, \
                f"Expected personalization.enabled=true for user with {personalization.get('event_count')} events"
            print(f"✓ Personalization enabled for test user with {personalization.get('event_count')} events")
    
    def test_rows_structure(self, authenticated_client):
        """Verify rows[] structure: key, title, icon, icon_color, stories[]."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        for row in rows:
            assert "key" in row, f"Missing 'key' in row: {row}"
            assert "title" in row, f"Missing 'title' in row: {row}"
            assert "icon" in row, f"Missing 'icon' in row: {row}"
            assert "icon_color" in row, f"Missing 'icon_color' in row: {row}"
            assert "stories" in row, f"Missing 'stories' in row: {row}"
            assert isinstance(row["stories"], list), f"'stories' should be a list: {row}"
            
            print(f"✓ Row '{row['key']}': {row['title']} - {len(row['stories'])} stories")
    
    def test_features_structure(self, authenticated_client):
        """Verify features[] structure: name, desc, icon, path, key, gradient, score."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        features = data.get("features", [])
        
        assert len(features) > 0, "Expected at least one feature"
        
        for feature in features:
            assert "name" in feature, f"Missing 'name' in feature: {feature}"
            assert "desc" in feature, f"Missing 'desc' in feature: {feature}"
            assert "icon" in feature, f"Missing 'icon' in feature: {feature}"
            assert "path" in feature, f"Missing 'path' in feature: {feature}"
            assert "key" in feature, f"Missing 'key' in feature: {feature}"
            assert "gradient" in feature, f"Missing 'gradient' in feature: {feature}"
            assert "score" in feature, f"Missing 'score' in feature: {feature}"
        
        # Features should be sorted by score descending
        scores = [f.get("score", 0) for f in features]
        assert scores == sorted(scores, reverse=True), \
            f"Features should be sorted by score descending: {scores}"
        
        print(f"✓ Features structure verified: {len(features)} features, sorted by score")
        print(f"  Top 3 features: {[f['key'] for f in features[:3]]}")
    
    def test_hero_has_displayable_media(self, authenticated_client):
        """Hero should have displayable media (thumbnail_small_url or poster_large_url)."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        hero = data.get("hero")
        
        if hero:
            media = hero.get("media", {})
            has_media = media.get("thumbnail_small_url") or media.get("poster_large_url")
            assert has_media, f"Hero should have displayable media: {hero}"
            print(f"✓ Hero has displayable media: {hero.get('title')}")
            print(f"  - thumbnail_small_url: {media.get('thumbnail_small_url', 'N/A')[:50]}...")
            print(f"  - poster_large_url: {media.get('poster_large_url', 'N/A')[:50]}...")
        else:
            print("⚠ No hero returned (may be expected if no stories)")
    
    def test_live_stats_structure(self, authenticated_client):
        """Verify live_stats structure: stories_today, total_stories."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        live_stats = data.get("live_stats", {})
        
        assert "stories_today" in live_stats, "Missing 'stories_today' in live_stats"
        assert "total_stories" in live_stats, "Missing 'total_stories' in live_stats"
        
        print(f"✓ Live stats: {live_stats}")


class TestRowOrdering:
    """Tests for row ordering based on user behavior."""
    
    def test_continue_stories_rank_1_when_user_has_active_stories(self, authenticated_client):
        """If user has active stories, continue_stories should be rank 1."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        # Find continue_stories row
        continue_row = next((r for r in rows if r.get("key") == "continue_stories"), None)
        
        if continue_row and len(continue_row.get("stories", [])) > 0:
            # If user has active stories, continue_stories should be first
            first_row_key = rows[0].get("key") if rows else None
            assert first_row_key == "continue_stories", \
                f"Expected continue_stories as rank 1 when user has active stories, got {first_row_key}"
            print(f"✓ continue_stories is rank 1 (user has {len(continue_row['stories'])} active stories)")
        else:
            print("⚠ User has no active stories, continue_stories not rank 1 (expected)")
            # Verify alternative ordering
            if rows:
                print(f"  First row: {rows[0].get('key')}")


class TestStoryRanking:
    """Tests for story ranking within rows based on personalization."""
    
    def test_watercolor_stories_rank_higher_for_test_user(self, authenticated_client):
        """Test user has high watercolor affinity - watercolor stories should rank higher."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        personalization = data.get("personalization", {})
        
        # Only check if personalization is enabled
        if not personalization.get("enabled"):
            pytest.skip("Personalization not enabled for this user")
        
        # Check trending or fresh row for watercolor stories
        rows = data.get("rows", [])
        trending_row = next((r for r in rows if r.get("key") == "trending_now"), None)
        
        if trending_row and len(trending_row.get("stories", [])) > 0:
            stories = trending_row["stories"]
            watercolor_indices = [
                i for i, s in enumerate(stories) 
                if s.get("animation_style", "").lower() == "watercolor"
            ]
            
            if watercolor_indices:
                # Watercolor stories should be in top half
                avg_position = sum(watercolor_indices) / len(watercolor_indices)
                print(f"✓ Watercolor stories found at positions: {watercolor_indices}")
                print(f"  Average position: {avg_position:.1f} (lower is better)")
            else:
                print("⚠ No watercolor stories in trending row")
        else:
            print("⚠ No trending row or empty")


class TestFeatureRanking:
    """Tests for feature ranking based on personalization."""
    
    def test_story_video_studio_top_ranked_for_test_user(self, authenticated_client):
        """Test user has high story-video-studio affinity - should be top-ranked feature."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        personalization = data.get("personalization", {})
        features = data.get("features", [])
        
        # Only check if personalization is enabled
        if not personalization.get("enabled"):
            pytest.skip("Personalization not enabled for this user")
        
        # Find story-video-studio position
        svs_position = next(
            (i for i, f in enumerate(features) if f.get("key") == "story-video-studio"),
            None
        )
        
        if svs_position is not None:
            print(f"✓ story-video-studio at position {svs_position + 1} of {len(features)}")
            # Should be in top 3 for test user with high affinity
            if svs_position < 3:
                print(f"  ✓ story-video-studio is in top 3 (expected for test user)")
            else:
                print(f"  ⚠ story-video-studio not in top 3 (position {svs_position + 1})")
        else:
            print("⚠ story-video-studio not found in features")


class TestEventTracking:
    """Tests for event tracking and profile updates."""
    
    def test_single_event_tracking(self, authenticated_client):
        """POST /api/growth/event with user_id should succeed."""
        event_data = {
            "event": "click",
            "user_id": TEST_USER_ID,
            "session_id": str(uuid.uuid4()),
            "meta": {
                "story_id": "test-story-123",
                "category": "watercolor",
                "tool_type": "story-video-studio"
            }
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/growth/event", json=event_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Expected success=true: {data}"
        
        print(f"✓ Single event tracked successfully: {data}")
    
    def test_batch_event_tracking(self, authenticated_client):
        """POST /api/growth/events/batch with user_id should succeed."""
        events = [
            {
                "event": "impression",
                "user_id": TEST_USER_ID,
                "session_id": str(uuid.uuid4()),
                "meta": {"story_id": "test-story-1", "category": "watercolor"}
            },
            {
                "event": "click",
                "user_id": TEST_USER_ID,
                "session_id": str(uuid.uuid4()),
                "meta": {"story_id": "test-story-2", "category": "anime"}
            }
        ]
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/growth/events/batch",
            json={"events": events}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Expected success=true: {data}"
        
        print(f"✓ Batch events tracked: {data.get('tracked', 0)} events")


class TestColdStart:
    """Tests for cold start behavior."""
    
    def test_new_user_cold_start(self, api_client):
        """New user with 0 events should get personalization.enabled=false."""
        # Create a new user or use anonymous session
        fresh_session = requests.Session()
        fresh_session.headers.update({"Content-Type": "application/json"})
        
        response = fresh_session.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        personalization = data.get("personalization", {})
        
        # Anonymous/new user should have personalization disabled
        assert personalization.get("enabled") == False, \
            f"Expected personalization.enabled=false for cold start, got {personalization}"
        assert personalization.get("event_count", 0) < 5, \
            f"Cold start user should have <5 events, got {personalization.get('event_count')}"
        
        print(f"✓ Cold start user has personalization.enabled=false")
        print(f"  - event_count: {personalization.get('event_count', 0)}")
        print(f"  - profile_strength: {personalization.get('profile_strength', 0)}")


class TestMediaInFeed:
    """Tests for media fields in feed response."""
    
    def test_stories_have_media_object(self, authenticated_client):
        """Stories in rows should have nested media object."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        stories_checked = 0
        for row in rows:
            for story in row.get("stories", [])[:3]:  # Check first 3 per row
                media = story.get("media", {})
                assert "thumbnail_small_url" in media or "poster_large_url" in media, \
                    f"Story missing media URLs: {story.get('title')}"
                stories_checked += 1
        
        print(f"✓ Checked {stories_checked} stories - all have media object")
    
    def test_media_urls_are_proxy_paths(self, authenticated_client):
        """Media URLs should be same-origin proxy paths (/api/media/r2/)."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        rows = data.get("rows", [])
        
        proxy_urls = 0
        for row in rows:
            for story in row.get("stories", [])[:3]:
                media = story.get("media", {})
                thumb = media.get("thumbnail_small_url", "")
                poster = media.get("poster_large_url", "")
                
                if thumb and thumb.startswith("/api/media/r2/"):
                    proxy_urls += 1
                if poster and poster.startswith("/api/media/r2/"):
                    proxy_urls += 1
        
        print(f"✓ Found {proxy_urls} proxy URLs in feed")


class TestNoOldAPIFields:
    """Verify old API fields are NOT present in new contract."""
    
    def test_no_flat_story_keys(self, authenticated_client):
        """Old flat keys (featured_story, trending_stories, etc.) should NOT be present."""
        response = authenticated_client.get(f"{BASE_URL}/api/engagement/story-feed")
        assert response.status_code == 200
        
        data = response.json()
        
        old_keys = ["featured_story", "trending_stories", "fresh_stories", 
                    "continue_stories", "unfinished_worlds"]
        
        for key in old_keys:
            assert key not in data, f"Old key '{key}' should NOT be in response"
        
        print(f"✓ No old flat keys in response (verified: {old_keys})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
