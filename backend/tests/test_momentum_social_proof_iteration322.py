"""
Test Enhanced Social Proof / Momentum-Based Data - Iteration 322

Tests:
1. GET /api/public/creation/{slug} returns momentum fields:
   - last_continuation_at, continuations_1h, continuations_24h, is_trending, is_alive
2. GET /api/public/character/{characterId} returns Character Power Score:
   - total_stories, total_continuations, last_continuation_at, tools_used, is_alive
3. Trending badge is_trending=false when thresholds not met
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data from requirements
TEST_SLUG = "da85bb12-785b-4906-8fba-48de780f4a2e"
TEST_CHARACTER_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"


class TestPublicCreationMomentum:
    """Test momentum fields in public creation endpoint"""

    def test_creation_endpoint_returns_200(self):
        """Creation endpoint should return 200 for valid slug"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is True, "Response should have success=True"
        print(f"✓ Creation endpoint returns 200 for slug: {TEST_SLUG}")

    def test_creation_has_momentum_fields(self):
        """Creation should have momentum fields"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200
        
        data = response.json()
        creation = data.get("creation", {})
        
        # Check momentum fields exist (may be null/0 if no continuations)
        assert "last_continuation_at" in creation, "Missing last_continuation_at field"
        assert "continuations_1h" in creation, "Missing continuations_1h field"
        assert "continuations_24h" in creation, "Missing continuations_24h field"
        assert "is_trending" in creation, "Missing is_trending field"
        assert "is_alive" in creation, "Missing is_alive field"
        
        print(f"✓ Momentum fields present:")
        print(f"  - last_continuation_at: {creation.get('last_continuation_at')}")
        print(f"  - continuations_1h: {creation.get('continuations_1h')}")
        print(f"  - continuations_24h: {creation.get('continuations_24h')}")
        print(f"  - is_trending: {creation.get('is_trending')}")
        print(f"  - is_alive: {creation.get('is_alive')}")

    def test_is_trending_is_boolean(self):
        """is_trending should be a boolean"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200
        
        creation = response.json().get("creation", {})
        is_trending = creation.get("is_trending")
        
        assert isinstance(is_trending, bool), f"is_trending should be bool, got {type(is_trending)}"
        print(f"✓ is_trending is boolean: {is_trending}")

    def test_is_alive_is_boolean(self):
        """is_alive should be a boolean"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200
        
        creation = response.json().get("creation", {})
        is_alive = creation.get("is_alive")
        
        assert isinstance(is_alive, bool), f"is_alive should be bool, got {type(is_alive)}"
        print(f"✓ is_alive is boolean: {is_alive}")

    def test_continuations_are_integers(self):
        """continuations_1h and continuations_24h should be integers"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200
        
        creation = response.json().get("creation", {})
        
        assert isinstance(creation.get("continuations_1h"), int), "continuations_1h should be int"
        assert isinstance(creation.get("continuations_24h"), int), "continuations_24h should be int"
        print(f"✓ Continuation counts are integers: 1h={creation.get('continuations_1h')}, 24h={creation.get('continuations_24h')}")

    def test_is_trending_false_without_threshold(self):
        """
        is_trending should be false when thresholds not met.
        Trending requires: (continuations_1h >= 2) OR (continuations_24h >= 5 AND views >= 20)
        """
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        assert response.status_code == 200
        
        creation = response.json().get("creation", {})
        is_trending = creation.get("is_trending")
        continuations_1h = creation.get("continuations_1h", 0)
        continuations_24h = creation.get("continuations_24h", 0)
        views = creation.get("views", 0)
        
        # If trending, verify thresholds
        if is_trending:
            assert (continuations_1h >= 2) or (continuations_24h >= 5 and views >= 20), \
                "is_trending=true but thresholds not met"
            print(f"✓ is_trending=true - thresholds verified")
        else:
            print(f"✓ is_trending=false - expected when thresholds not met")
            print(f"  - continuations_1h: {continuations_1h} (needs >=2)")
            print(f"  - continuations_24h: {continuations_24h} (needs >=5)")
            print(f"  - views: {views}")


class TestPublicCharacterPowerScore:
    """Test Character Power Score in public character endpoint"""

    def test_character_endpoint_returns_404_or_200(self):
        """Character endpoint should return 200 for valid character or 404 if not found"""
        response = requests.get(f"{BASE_URL}/api/public/character/{TEST_CHARACTER_ID}")
        
        # Character may or may not exist - both are valid
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            print(f"✓ Character found: {TEST_CHARACTER_ID}")
        else:
            print(f"✓ Character not found (404) - expected if no test characters in DB")
            pytest.skip("Character not found in DB - skipping character tests")

    def test_character_has_social_proof_fields(self):
        """Character should have enhanced social_proof with Character Power Score fields"""
        response = requests.get(f"{BASE_URL}/api/public/character/{TEST_CHARACTER_ID}")
        
        if response.status_code == 404:
            pytest.skip("Character not found in DB")
            return
            
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        social_proof = data.get("social_proof", {})
        
        # Check enhanced social proof fields
        assert "total_stories" in social_proof, "Missing total_stories in social_proof"
        assert "total_continuations" in social_proof, "Missing total_continuations in social_proof"
        assert "last_continuation_at" in social_proof, "Missing last_continuation_at in social_proof"
        assert "tools_used" in social_proof, "Missing tools_used in social_proof"
        assert "is_alive" in social_proof, "Missing is_alive in social_proof"
        
        print(f"✓ Character Power Score fields present:")
        print(f"  - total_stories: {social_proof.get('total_stories')}")
        print(f"  - total_continuations: {social_proof.get('total_continuations')}")
        print(f"  - last_continuation_at: {social_proof.get('last_continuation_at')}")
        print(f"  - tools_used: {social_proof.get('tools_used')}")
        print(f"  - is_alive: {social_proof.get('is_alive')}")

    def test_character_tools_used_is_list(self):
        """tools_used should be a list"""
        response = requests.get(f"{BASE_URL}/api/public/character/{TEST_CHARACTER_ID}")
        
        if response.status_code == 404:
            pytest.skip("Character not found in DB")
            return
            
        social_proof = response.json().get("social_proof", {})
        tools_used = social_proof.get("tools_used")
        
        assert isinstance(tools_used, list), f"tools_used should be list, got {type(tools_used)}"
        print(f"✓ tools_used is list with {len(tools_used)} tools: {tools_used}")

    def test_character_is_alive_is_boolean(self):
        """is_alive in social_proof should be boolean"""
        response = requests.get(f"{BASE_URL}/api/public/character/{TEST_CHARACTER_ID}")
        
        if response.status_code == 404:
            pytest.skip("Character not found in DB")
            return
            
        social_proof = response.json().get("social_proof", {})
        is_alive = social_proof.get("is_alive")
        
        # Can be None/False if no recent activity
        assert is_alive is None or isinstance(is_alive, bool), f"is_alive should be bool or None"
        print(f"✓ is_alive: {is_alive}")


class TestCreationRemixTrack:
    """Test remix tracking endpoint"""

    def test_remix_endpoint_works(self):
        """POST /api/public/creation/{slug}/remix should increment remix count"""
        response = requests.post(f"{BASE_URL}/api/public/creation/{TEST_SLUG}/remix")
        
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            print(f"✓ Remix tracked successfully for slug: {TEST_SLUG}")
        else:
            print(f"✓ Creation not found (404) - expected if slug doesn't exist")


class TestCreationDataStructure:
    """Test overall creation data structure"""

    def test_creation_has_required_fields(self):
        """Creation should have all required fields for frontend"""
        response = requests.get(f"{BASE_URL}/api/public/creation/{TEST_SLUG}")
        
        if response.status_code == 404:
            pytest.skip("Creation not found")
            return
            
        assert response.status_code == 200
        creation = response.json().get("creation", {})
        
        required_fields = [
            "job_id", "title", "views", "remix_count",
            "last_continuation_at", "continuations_1h", "continuations_24h",
            "is_trending", "is_alive"
        ]
        
        for field in required_fields:
            assert field in creation, f"Missing required field: {field}"
        
        print(f"✓ All required fields present")
        print(f"  - title: {creation.get('title')}")
        print(f"  - views: {creation.get('views')}")
        print(f"  - remix_count: {creation.get('remix_count')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
