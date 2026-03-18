"""
AI Character Memory Sprint C Tests - Iteration 317
===================================================
Testing Sprint C specific features:
1. Editable Visual Bibles (PATCH /api/characters/{id}/visual-bible with versioning/validation)
2. Relationship Graph (POST/GET /api/characters/{id}/relationships)
3. Emotional Memory (GET /api/characters/{id}/emotional-arc)
4. Library Search/Filter (GET /api/characters/search/query)

Test User: test@visionary-suite.com / Test@2026#
Test Characters:
  - Finn: d8cf0208-ff0c-4c21-8725-ffa6326d8da9 (fox hero, VB v2, has relationship with Zara)
  - Zara: 9c0c60aa-7fab-4885-bb4d-111287275ba5 (cat sidekick, has reverse relationship with Finn)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://viral-loop-2.preview.emergentagent.com').rstrip('/')

# Test character IDs
FINN_ID = "d8cf0208-ff0c-4c21-8725-ffa6326d8da9"
ZARA_ID = "9c0c60aa-7fab-4885-bb4d-111287275ba5"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


class TestSession:
    """Shared auth session"""
    token = None
    user_id = None


@pytest.fixture(scope="module")
def auth_headers():
    """Get authentication token and headers"""
    if TestSession.token:
        return {"Authorization": f"Bearer {TestSession.token}"}
    
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    data = login_response.json()
    TestSession.token = data.get("token")
    TestSession.user_id = data.get("user", {}).get("id")
    
    return {"Authorization": f"Bearer {TestSession.token}"}


# =====================================================
# SPRINT C.1: EDITABLE VISUAL BIBLES
# =====================================================

class TestEditableVisualBibles:
    """Tests for PATCH /api/characters/{id}/visual-bible"""
    
    def test_edit_visual_bible_clothing_bumps_version(self, auth_headers):
        """Editing clothing description bumps version and archives old"""
        # Get current version
        detail_response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        current_version = detail_response.json().get("visual_bible", {}).get("version", 1)
        
        # Edit clothing
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"clothing_description": "Updated red bandana with gold trim, adventurer vest"}
        )
        assert edit_response.status_code == 200, f"Edit failed: {edit_response.text}"
        
        data = edit_response.json()
        assert data.get("success") is True
        assert data.get("new_version") == current_version + 1, f"Version not bumped correctly"
        assert "clothing_description" in data.get("updated_fields", [])
        
        # Check continuity_check is returned
        assert "continuity_check" in data
        assert "score" in data["continuity_check"]
        
        print(f"PASS: VB edited v{current_version}->v{data['new_version']}, continuity_score={data['continuity_check']['score']}")
    
    def test_edit_visual_bible_style_lock_blocked_without_reset(self, auth_headers):
        """Changing style_lock without style_reset=true returns 422"""
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"style_lock": "anime"}  # No style_reset=true
        )
        assert edit_response.status_code == 422, f"Expected 422, got {edit_response.status_code}"
        
        detail = edit_response.json().get("detail", {})
        assert detail.get("error") == "style_lock_protected", f"Wrong error: {detail}"
        assert "current_style" in detail
        
        print(f"PASS: style_lock change blocked without style_reset (current: {detail.get('current_style')})")
    
    def test_edit_visual_bible_style_lock_allowed_with_reset(self, auth_headers):
        """Changing style_lock with style_reset=true succeeds"""
        # Get current style
        detail_response = requests.get(f"{BASE_URL}/api/characters/{FINN_ID}", headers=auth_headers)
        current_style = detail_response.json().get("visual_bible", {}).get("style_lock")
        
        # Try changing with style_reset=true (then change back)
        new_style = "anime" if current_style != "anime" else "cartoon_2d"
        
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"style_lock": new_style, "style_reset": True}
        )
        assert edit_response.status_code == 200, f"Edit failed: {edit_response.text}"
        
        data = edit_response.json()
        assert "style_lock" in data.get("updated_fields", [])
        
        # Change back to original
        requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"style_lock": current_style, "style_reset": True}
        )
        
        print(f"PASS: style_lock changed with style_reset=true")
    
    def test_edit_visual_bible_canonical_description_safety_check(self, auth_headers):
        """Editing canonical_description triggers safety re-check"""
        # Try setting canonical description with copyrighted term
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"canonical_description": "A fox that looks like Spider-Man"}
        )
        assert edit_response.status_code == 422, f"Expected 422, got {edit_response.status_code}"
        
        detail = edit_response.json().get("detail", {})
        assert detail.get("error") == "safety_block"
        
        print("PASS: canonical_description change triggers safety check")
    
    def test_edit_visual_bible_returns_impact_warning(self, auth_headers):
        """Edit response includes impact_warning for version > 2"""
        # Make sure we have at least version 3
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={"accessories": "Updated adventurer goggles on forehead"}
        )
        
        data = edit_response.json()
        if data.get("new_version", 0) > 2:
            assert "impact_warning" in data or data.get("impact_warning") is not None
            print(f"PASS: impact_warning included (v{data['new_version']})")
        else:
            print(f"INFO: Version {data.get('new_version')} < 3, impact_warning may be None (expected)")
    
    def test_no_fields_to_update_returns_400(self, auth_headers):
        """Empty update request returns 400"""
        edit_response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            headers=auth_headers,
            json={}
        )
        assert edit_response.status_code == 400
        print("PASS: Empty update returns 400")


class TestVisualBibleHistory:
    """Tests for GET /api/characters/{id}/visual-bible-history"""
    
    def test_visual_bible_history_returns_versions(self, auth_headers):
        """History endpoint returns archived versions"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible-history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "history" in data
        assert "current_version" in data
        assert "total_versions" in data
        
        # History should have archived snapshots
        assert isinstance(data["history"], list)
        
        print(f"PASS: VB history - current_version={data['current_version']}, total={data['total_versions']}, archived={len(data['history'])}")
    
    def test_visual_bible_history_404_invalid_character(self, auth_headers):
        """History returns 404 for invalid character"""
        response = requests.get(
            f"{BASE_URL}/api/characters/invalid-char-id-12345/visual-bible-history",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("PASS: VB history returns 404 for invalid character")


# =====================================================
# SPRINT C.2: RELATIONSHIP GRAPH
# =====================================================

class TestRelationshipGraph:
    """Tests for POST/GET /api/characters/{id}/relationships"""
    
    def test_create_relationship_bidirectional(self, auth_headers):
        """Creating relationship creates both A->B and B->A"""
        # Create relationship from Finn to Zara
        response = requests.post(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships",
            headers=auth_headers,
            json={
                "related_character_id": ZARA_ID,
                "relationship_type": "friend",
                "relationship_state": "trusting"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("relationship_type") == "friend"
        assert data.get("relationship_state") == "trusting"
        assert "character_name" in data
        assert "related_name" in data
        
        print(f"PASS: Relationship created: {data.get('character_name')} <-> {data.get('related_name')}")
    
    def test_get_relationships_enriched(self, auth_headers):
        """GET relationships returns enriched data with names and portraits"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "relationships" in data
        assert "total" in data
        
        # Check enrichment
        if data["total"] > 0:
            rel = data["relationships"][0]
            assert "related_name" in rel, "Missing related_name enrichment"
            assert "related_character_id" in rel
            assert "relationship_type" in rel
            assert "relationship_state" in rel
            print(f"PASS: Relationships enriched - {data['total']} found, first: {rel.get('related_name')}/{rel.get('relationship_type')}")
        else:
            print("INFO: No relationships to verify enrichment")
    
    def test_relationship_bidirectional_check(self, auth_headers):
        """Relationship also exists in reverse direction"""
        # Check Zara's relationships to see Finn
        response = requests.get(
            f"{BASE_URL}/api/characters/{ZARA_ID}/relationships",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        relationships = data.get("relationships", [])
        
        # Should have relationship to Finn
        finn_rels = [r for r in relationships if r.get("related_character_id") == FINN_ID]
        assert len(finn_rels) > 0, "Bidirectional relationship not created"
        
        print(f"PASS: Bidirectional relationship verified (Zara -> Finn)")
    
    def test_self_relationship_blocked(self, auth_headers):
        """Cannot create relationship with self"""
        response = requests.post(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships",
            headers=auth_headers,
            json={
                "related_character_id": FINN_ID,
                "relationship_type": "friend",
                "relationship_state": "neutral"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Self-relationship blocked")
    
    def test_invalid_relationship_type_defaults(self, auth_headers):
        """Invalid relationship_type defaults to 'unknown'"""
        response = requests.post(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships",
            headers=auth_headers,
            json={
                "related_character_id": ZARA_ID,
                "relationship_type": "invalid_type",
                "relationship_state": "trusting"
            }
        )
        assert response.status_code == 200
        
        # Check type was set to unknown
        data = response.json()
        assert data.get("relationship_type") == "unknown", f"Expected 'unknown', got {data.get('relationship_type')}"
        print("PASS: Invalid relationship_type defaults to 'unknown'")


# =====================================================
# SPRINT C.3: EMOTIONAL MEMORY
# =====================================================

class TestEmotionalArc:
    """Tests for GET /api/characters/{id}/emotional-arc"""
    
    def test_emotional_arc_returns_structure(self, auth_headers):
        """Emotional arc endpoint returns arc, trend, current_emotion"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/emotional-arc",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "arc" in data
        assert "total_entries" in data
        assert "trend" in data
        assert "current_emotion" in data
        assert "current_intensity" in data
        
        # Arc should be a list
        assert isinstance(data["arc"], list)
        
        # Trend should be one of valid values
        assert data["trend"] in ["stable", "improving", "declining"]
        
        print(f"PASS: Emotional arc - entries={data['total_entries']}, trend={data['trend']}, current={data['current_emotion']}")
    
    def test_emotional_arc_entry_structure(self, auth_headers):
        """Each arc entry has emotion/intensity/event_summary/timestamp"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/emotional-arc",
            headers=auth_headers
        )
        
        data = response.json()
        arc = data.get("arc", [])
        
        if len(arc) > 0:
            entry = arc[0]
            assert "emotion" in entry, "Missing emotion in arc entry"
            assert "intensity" in entry, "Missing intensity in arc entry"
            assert "event_summary" in entry or entry.get("event_summary") is not None
            
            # Intensity should be 1-5
            intensity = entry.get("intensity", 0)
            assert 1 <= intensity <= 5, f"Intensity {intensity} not in range 1-5"
            
            print(f"PASS: Arc entry structure valid - emotion={entry['emotion']}, intensity={intensity}")
        else:
            print("INFO: No arc entries to verify structure (expected - no episodes generated)")
    
    def test_emotional_arc_404_invalid_character(self, auth_headers):
        """Emotional arc returns 404 for invalid character"""
        response = requests.get(
            f"{BASE_URL}/api/characters/invalid-char-id-12345/emotional-arc",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("PASS: Emotional arc returns 404 for invalid character")


# =====================================================
# SPRINT C.4: LIBRARY SEARCH/FILTER
# =====================================================

class TestLibrarySearch:
    """Tests for GET /api/characters/search/query"""
    
    def test_search_by_name(self, auth_headers):
        """Search by name returns matching characters"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?q=Finn",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "characters" in data
        assert "total" in data
        assert "query" in data
        
        # Should find Finn
        characters = data.get("characters", [])
        finn_matches = [c for c in characters if "Finn" in c.get("name", "")]
        assert len(finn_matches) > 0, "Finn not found in search results"
        
        print(f"PASS: Search q='Finn' returned {len(finn_matches)} matches")
    
    def test_search_case_insensitive(self, auth_headers):
        """Search is case-insensitive"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?q=finn",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        characters = data.get("characters", [])
        finn_matches = [c for c in characters if "finn" in c.get("name", "").lower()]
        
        assert len(finn_matches) > 0, "Case-insensitive search failed"
        print(f"PASS: Case-insensitive search works")
    
    def test_filter_by_role(self, auth_headers):
        """Filter by role returns only matching characters"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?role=sidekick",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        characters = data.get("characters", [])
        
        # All returned characters should have role=sidekick
        for c in characters:
            assert c.get("role") == "sidekick", f"Character {c.get('name')} has role {c.get('role')}, expected sidekick"
        
        print(f"PASS: Role filter 'sidekick' returned {len(characters)} characters")
    
    def test_sort_by_name(self, auth_headers):
        """Sort by name returns alphabetically sorted results"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?sort_by=name",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        characters = data.get("characters", [])
        
        if len(characters) >= 2:
            names = [c.get("name", "") for c in characters]
            assert names == sorted(names), f"Names not sorted: {names}"
            print(f"PASS: Sort by name returns alphabetical order")
        else:
            print("INFO: Less than 2 characters, cannot verify sort order")
    
    def test_search_returns_enriched_data(self, auth_headers):
        """Search results include visual_summary, style_lock, memory_entries"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?q=Finn",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        characters = data.get("characters", [])
        
        if len(characters) > 0:
            c = characters[0]
            assert "visual_summary" in c, "Missing visual_summary"
            assert "style_lock" in c, "Missing style_lock"
            assert "memory_entries" in c, "Missing memory_entries"
            assert "vb_version" in c, "Missing vb_version"
            print(f"PASS: Search results enriched with visual_summary/style_lock/memory_entries/vb_version")
        else:
            print("INFO: No characters in search results")
    
    def test_search_empty_query_returns_all(self, auth_headers):
        """Empty query returns all user's characters"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("total", 0) >= 0
        print(f"PASS: Empty query returns {data.get('total')} characters")
    
    def test_combined_search_and_filter(self, auth_headers):
        """Combining q and role filter works"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?q=Z&role=sidekick",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        characters = data.get("characters", [])
        
        for c in characters:
            assert "Z" in c.get("name", "").upper() or "z" in c.get("name", "").lower()
            assert c.get("role") == "sidekick"
        
        print(f"PASS: Combined search+filter works ({len(characters)} results)")


# =====================================================
# AUTH REQUIREMENT TESTS
# =====================================================

class TestAuthRequirements:
    """Verify all Sprint C endpoints require authentication"""
    
    def test_edit_visual_bible_requires_auth(self):
        """PATCH visual-bible requires auth"""
        response = requests.patch(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible",
            json={"accessories": "test"}
        )
        assert response.status_code in [401, 403]
        print("PASS: PATCH visual-bible requires auth")
    
    def test_visual_bible_history_requires_auth(self):
        """GET visual-bible-history requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/visual-bible-history"
        )
        assert response.status_code in [401, 403]
        print("PASS: GET visual-bible-history requires auth")
    
    def test_relationships_post_requires_auth(self):
        """POST relationships requires auth"""
        response = requests.post(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships",
            json={"related_character_id": ZARA_ID}
        )
        assert response.status_code in [401, 403]
        print("PASS: POST relationships requires auth")
    
    def test_relationships_get_requires_auth(self):
        """GET relationships requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/relationships"
        )
        assert response.status_code in [401, 403]
        print("PASS: GET relationships requires auth")
    
    def test_emotional_arc_requires_auth(self):
        """GET emotional-arc requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/characters/{FINN_ID}/emotional-arc"
        )
        assert response.status_code in [401, 403]
        print("PASS: GET emotional-arc requires auth")
    
    def test_search_requires_auth(self):
        """GET search/query requires auth"""
        response = requests.get(
            f"{BASE_URL}/api/characters/search/query?q=test"
        )
        assert response.status_code in [401, 403]
        print("PASS: GET search/query requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
