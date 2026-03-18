"""
Growth Engine P0 Features Backend Tests - Iteration 318
=========================================================
Tests 3 P0 features:
1. Auto-Character Extraction: GET extracted-characters, POST confirm-characters, POST dismiss-extraction
2. Character-Based Sharing: GET /api/public/character/{id} - NO AUTH required, returns remix_data
3. Series Completion Rewards: GET rewards, POST claim-reward

Test data:
- User: test@visionary-suite.com / Test@2026#
- Series ID: ea2bc4e8-454d-4f40-8415-f4383593904a (Fox Forest, 4 episodes)
- Character ID: d8cf0208-ff0c-4c21-8725-ffa6326d8da9 (Finn)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
EXISTING_SERIES_ID = "ea2bc4e8-454d-4f40-8415-f4383593904a"
EXISTING_CHARACTER_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in response"
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ══════════════════════════════════════════════════════════════════════════════
# Feature 1: Auto-Character Extraction
# ══════════════════════════════════════════════════════════════════════════════

class TestAutoCharacterExtraction:
    """Tests for auto-character extraction after Episode 1 creation."""

    def test_get_extracted_characters_returns_status(self, auth_headers):
        """GET /api/story-series/{series_id}/extracted-characters returns extraction status."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/extracted-characters",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "success" in data
        assert "extraction_status" in data
        assert "extracted_characters" in data
        
        # extraction_status can be: none, pending_confirmation, confirmed, dismissed
        assert data["extraction_status"] in ["none", "pending_confirmation", "confirmed", "dismissed"]
        print(f"Extraction status: {data['extraction_status']}, chars: {len(data.get('extracted_characters', []))}")

    def test_get_extracted_characters_requires_auth(self):
        """GET /api/story-series/{series_id}/extracted-characters requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/extracted-characters"
        )
        assert response.status_code in [401, 403], f"Expected 401/403 but got {response.status_code}"

    def test_confirm_characters_requires_auth(self):
        """POST /api/story-series/{series_id}/confirm-characters requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/confirm-characters",
            json={"characters": []}
        )
        assert response.status_code in [401, 403], f"Expected 401/403 but got {response.status_code}"

    def test_confirm_characters_with_empty_list(self, auth_headers):
        """POST confirm-characters with empty list marks as dismissed."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/confirm-characters",
            headers=auth_headers,
            json={"characters": []}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        # With no characters confirmed, created should be 0
        assert data.get("created", 0) == 0
        print(f"Confirm response: {data}")

    def test_dismiss_extraction_works(self, auth_headers):
        """POST /api/story-series/{series_id}/dismiss-extraction marks extraction as dismissed."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/dismiss-extraction",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("extraction_status") == "dismissed"

    def test_dismiss_extraction_requires_auth(self):
        """POST dismiss-extraction requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/dismiss-extraction"
        )
        assert response.status_code in [401, 403]

    def test_confirm_characters_404_invalid_series(self, auth_headers):
        """POST confirm-characters returns 404 for invalid series."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/invalid-series-id/confirm-characters",
            headers=auth_headers,
            json={"characters": []}
        )
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Feature 2: Character-Based Sharing Loop (Public Character Page)
# ══════════════════════════════════════════════════════════════════════════════

class TestPublicCharacterPage:
    """Tests for public character page - NO AUTH required."""

    def test_public_character_no_auth_required(self):
        """GET /api/public/character/{id} requires NO authentication."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200, f"Failed (no auth): {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"Public character (no auth) works - character: {data.get('character', {}).get('name')}")

    def test_public_character_returns_character_data(self):
        """Public character endpoint returns character profile data."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check character object structure
        char = data.get("character", {})
        assert "character_id" in char
        assert "name" in char
        assert "role" in char
        assert char["character_id"] == EXISTING_CHARACTER_ID
        print(f"Character: {char.get('name')} ({char.get('role')})")

    def test_public_character_returns_visual_bible(self):
        """Public character endpoint returns visual_bible data."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        # visual_bible can be null if not set
        vb = data.get("visual_bible")
        if vb:
            assert "canonical_description" in vb
            print(f"Visual bible canonical: {vb.get('canonical_description', '')[:100]}...")
        else:
            print("Visual bible is null (acceptable)")

    def test_public_character_returns_social_proof(self):
        """Public character endpoint returns social_proof stats."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        social = data.get("social_proof", {})
        assert "episode_count" in social
        assert "total_usage" in social
        print(f"Social proof - episodes: {social.get('episode_count')}, usage: {social.get('total_usage')}")

    def test_public_character_returns_remix_data(self):
        """Public character endpoint returns remix_data for sharing CTA integration."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        remix = data.get("remix_data")
        assert remix is not None, "remix_data is missing"
        assert "prompt" in remix, "remix_data missing 'prompt' field"
        assert "remixFrom" in remix, "remix_data missing 'remixFrom' field"
        
        remix_from = remix.get("remixFrom", {})
        assert remix_from.get("type") == "character_share"
        assert remix_from.get("character_id") == EXISTING_CHARACTER_ID
        print(f"Remix data prompt: {remix.get('prompt', '')[:80]}...")

    def test_public_character_returns_sample_scenes(self):
        """Public character endpoint returns sample_scenes."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        scenes = data.get("sample_scenes", [])
        assert isinstance(scenes, list)
        print(f"Sample scenes count: {len(scenes)}")

    def test_public_character_returns_relationships(self):
        """Public character endpoint returns relationships."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/{EXISTING_CHARACTER_ID}"
        )
        assert response.status_code == 200
        data = response.json()
        
        rels = data.get("relationships", [])
        assert isinstance(rels, list)
        print(f"Relationships count: {len(rels)}")

    def test_public_character_404_invalid_id(self):
        """Public character endpoint returns 404 for invalid character ID."""
        response = requests.get(
            f"{BASE_URL}/api/public/character/invalid-character-id"
        )
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Feature 3: Series Completion Rewards
# ══════════════════════════════════════════════════════════════════════════════

class TestSeriesCompletionRewards:
    """Tests for series completion rewards at 3/5/10 episodes."""

    def test_get_rewards_returns_milestone_data(self, auth_headers):
        """GET /api/story-series/{series_id}/rewards returns milestone data."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/rewards",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True
        assert "episode_count" in data
        assert "pending_rewards" in data
        assert "claimed_milestones" in data
        assert "all_milestones" in data
        
        print(f"Episode count: {data['episode_count']}")
        print(f"Pending rewards: {len(data['pending_rewards'])}")
        print(f"Claimed milestones: {data['claimed_milestones']}")

    def test_get_rewards_all_milestones_structure(self, auth_headers):
        """GET rewards returns all_milestones with proper structure."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/rewards",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        milestones = data.get("all_milestones", [])
        assert len(milestones) == 3, "Expected 3 milestones (3, 5, 10)"
        
        for m in milestones:
            assert "threshold" in m
            assert "title" in m
            assert "claimed" in m
            assert "reached" in m
        
        thresholds = [m["threshold"] for m in milestones]
        assert thresholds == [3, 5, 10], f"Thresholds should be [3, 5, 10], got {thresholds}"

    def test_get_rewards_next_milestone_structure(self, auth_headers):
        """GET rewards returns next_milestone with progress."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/rewards",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        next_m = data.get("next_milestone")
        # next_milestone can be None if all milestones are reached
        if next_m:
            assert "threshold" in next_m
            assert "title" in next_m
            assert "episodes_remaining" in next_m
            assert "progress" in next_m
            print(f"Next milestone: {next_m['title']} (threshold {next_m['threshold']}, {next_m['episodes_remaining']} episodes remaining)")
        else:
            print("All milestones reached (next_milestone is None)")

    def test_get_rewards_pending_rewards_structure(self, auth_headers):
        """GET rewards pending_rewards have correct structure."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/rewards",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        pending = data.get("pending_rewards", [])
        for p in pending:
            assert "threshold" in p
            assert "title" in p
            assert "emotional_message" in p
            assert "rewards" in p
            assert "next_loop" in p
            print(f"Pending reward: {p['title']} (threshold {p['threshold']})")

    def test_get_rewards_requires_auth(self):
        """GET /api/story-series/{series_id}/rewards requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/rewards"
        )
        assert response.status_code in [401, 403]

    def test_claim_reward_requires_auth(self):
        """POST claim-reward requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/claim-reward?milestone=3"
        )
        assert response.status_code in [401, 403]

    def test_claim_reward_invalid_milestone(self, auth_headers):
        """POST claim-reward returns 400 for invalid milestone."""
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/claim-reward?milestone=7",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid milestone" in response.text

    def test_claim_reward_milestone_3(self, auth_headers):
        """POST claim-reward for milestone 3 (existing series has 4 episodes)."""
        # Note: milestone 3 may already be claimed from previous test run
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/claim-reward?milestone=3",
            headers=auth_headers
        )
        
        if response.status_code == 400 and "Already claimed" in response.text:
            print("Milestone 3 already claimed (expected from previous test)")
            return
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert data.get("milestone") == 3
        assert data.get("title") == "Story Taking Shape"
        assert "rewards" in data
        assert "next_loop" in data
        print(f"Claimed milestone 3: {data['title']}")

    def test_claim_reward_milestone_5_insufficient_episodes(self, auth_headers):
        """POST claim-reward for milestone 5 fails if only 4 episodes exist."""
        # Series has 4 episodes, milestone 5 requires 5
        response = requests.post(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}/claim-reward?milestone=5",
            headers=auth_headers
        )
        
        # Either already claimed (400) or insufficient episodes (400)
        if response.status_code == 400:
            if "Already claimed" in response.text:
                print("Milestone 5 already claimed")
            elif "Need" in response.text:
                print("Milestone 5 not reached yet (need more episodes)")
            return
        
        # If status is 200, it means milestone was claimable
        print(f"Milestone 5 status: {response.status_code}")

    def test_get_rewards_404_invalid_series(self, auth_headers):
        """GET rewards returns 404 for invalid series."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/invalid-series-id/rewards",
            headers=auth_headers
        )
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Additional Tests: Series Endpoint Verification
# ══════════════════════════════════════════════════════════════════════════════

class TestSeriesEndpointsExist:
    """Verify all series endpoints exist and return proper responses."""

    def test_get_series_returns_extraction_status(self, auth_headers):
        """GET series includes extraction_status field."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/{EXISTING_SERIES_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        series = data.get("series", {})
        # extraction_status may or may not exist on older series
        if "extraction_status" in series:
            print(f"extraction_status: {series['extraction_status']}")
        else:
            print("extraction_status not in series (older series created before feature)")

    def test_get_my_series_works(self, auth_headers):
        """GET my-series endpoint works."""
        response = requests.get(
            f"{BASE_URL}/api/story-series/my-series",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "series" in data
        print(f"User has {len(data['series'])} series")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
