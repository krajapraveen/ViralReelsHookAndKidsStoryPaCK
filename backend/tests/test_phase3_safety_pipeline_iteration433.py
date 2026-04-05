"""
Phase 3 Safety Pipeline Tests — Semantic Detection (3B), Rewrite Quality (3C), 
Safety Telemetry (3D), and Frontend Soft Warning UX (3E).

Tests:
  - 3B: Semantic detection catches indirect IP references
  - 3B: Fuzzy alias detection catches obfuscated names
  - 3B: No false positives on clean prompts
  - 3C: Rewrite quality - rewrites are narrative-rich (5+ words) and don't contain original IP names
  - 3D: GET /api/admin/metrics/safety-insights endpoint returns telemetry data
  - 3D: GET /api/admin/metrics/safety-overview endpoint still works
  - 3E: POST to generation endpoint with copyrighted content returns _safety_meta.was_rewritten=true
  - 3E: POST to generation endpoint with clean content does NOT return _safety_meta
  - Fail-closed: Dangerous content is properly BLOCKED with 400 status
  - Regression: Existing safety-events list endpoint still works

Run: cd /app/backend && python -m pytest tests/test_phase3_safety_pipeline_iteration433.py -v
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get auth token for test user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get auth token for admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


# ═══════════════════════════════════════════════════════════════
# Phase 3B: Semantic Detection Tests
# Note: story-hook-generator is template-based and doesn't accept free-form text.
# We test semantic detection on bedtime-story-builder which accepts theme/moral fields.
# ═══════════════════════════════════════════════════════════════

class TestPhase3BSemanticDetection:
    """Test semantic detection catches indirect IP references."""

    @pytest.mark.parametrize("prompt,expected_ip", [
        ("wizard boy with lightning scar", "Harry Potter"),
        ("web-slinging hero from Queens", "Spider-Man"),
        ("ice princess with magical powers", "Frozen"),
    ])
    def test_semantic_detection_indirect_references(self, test_user_token, prompt, expected_ip):
        """3B: Semantic detection catches indirect IP references."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        # Use bedtime-story-builder which accepts free-form text in theme field
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": prompt,
                "moral": "courage",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        # Should either succeed with rewrite (200) or fail due to credits (402)
        # Should NOT be blocked (400) for copyright content - it should be rewritten
        assert response.status_code in [200, 402], f"Unexpected status {response.status_code} for '{prompt}'"
        
        if response.status_code == 200:
            data = response.json()
            # Check if _safety_meta indicates rewrite
            safety_meta = data.get("_safety_meta", {})
            assert safety_meta.get("was_rewritten") == True, f"Expected rewrite for '{expected_ip}' indirect reference"

    @pytest.mark.parametrize("obfuscated_name", [
        "sp1der man",
        "H4rry P0tter",
        "h a r r y p o t t e r",
    ])
    def test_fuzzy_alias_detection(self, test_user_token, obfuscated_name):
        """3B: Fuzzy alias detection catches obfuscated names."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": f"A story about {obfuscated_name}",
                "moral": "friendship",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        # Should either succeed with rewrite (200) or fail due to credits (402)
        assert response.status_code in [200, 402], f"Unexpected status {response.status_code} for '{obfuscated_name}'"
        
        if response.status_code == 200:
            data = response.json()
            safety_meta = data.get("_safety_meta", {})
            assert safety_meta.get("was_rewritten") == True, f"Expected rewrite for obfuscated '{obfuscated_name}'"

    @pytest.mark.parametrize("clean_prompt", [
        "A brave knight saves a village",
        "An astronaut explores a distant planet",
    ])
    def test_no_false_positives_clean_prompts(self, test_user_token, clean_prompt):
        """3B: No false positives on clean prompts."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": clean_prompt,
                "moral": "courage",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        # Should either succeed without rewrite (200) or fail due to credits (402)
        assert response.status_code in [200, 402], f"Unexpected status {response.status_code} for clean prompt"
        
        if response.status_code == 200:
            data = response.json()
            # Clean prompts should NOT have _safety_meta or was_rewritten should be False
            safety_meta = data.get("_safety_meta", {})
            was_rewritten = safety_meta.get("was_rewritten", False)
            assert was_rewritten == False, f"FALSE POSITIVE: Clean prompt '{clean_prompt}' was rewritten"


# ═══════════════════════════════════════════════════════════════
# Phase 3C: Rewrite Quality Tests
# ═══════════════════════════════════════════════════════════════

class TestPhase3CRewriteQuality:
    """Test rewrite quality - rewrites are narrative-rich and don't contain original IP names."""

    def test_rewrite_quality_via_unit_test(self):
        """3C: Verify rewrites are narrative-rich (5+ words) via unit test."""
        # Import the rewrite engine directly
        import sys
        sys.path.insert(0, '/app/backend')
        from services.rewrite_engine.rule_rewriter import rewrite_text
        from services.rewrite_engine.semantic_detector import detect_semantic_patterns
        
        # Test direct keyword rewrite
        rewritten, changes = rewrite_text("Create a story about Harry Potter")
        assert len(changes) > 0, "Failed to detect Harry Potter"
        replacement = changes[0]["replacement"]
        word_count = len(replacement.split())
        assert word_count >= 5, f"Rewrite too short ({word_count} words): '{replacement}'"
        assert "harry potter" not in replacement.lower(), f"Rewrite contains original IP: '{replacement}'"
        
        # Test semantic rewrite
        matches = detect_semantic_patterns("wizard boy with lightning scar")
        assert len(matches) > 0, "Failed to detect semantic pattern"
        safe_rewrite = matches[0].safe_rewrite
        assert len(safe_rewrite.split()) >= 5, f"Semantic rewrite too short: '{safe_rewrite}'"
        assert "harry potter" not in safe_rewrite.lower(), f"Semantic rewrite contains IP: '{safe_rewrite}'"


# ═══════════════════════════════════════════════════════════════
# Phase 3D: Safety Telemetry Tests
# ═══════════════════════════════════════════════════════════════

class TestPhase3DSafetyTelemetry:
    """Test safety telemetry endpoints."""

    def test_safety_insights_endpoint(self, admin_token):
        """3D: GET /api/admin/metrics/safety-insights returns telemetry data."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/metrics/safety-insights?hours=168", headers=headers)
        
        assert response.status_code == 200, f"safety-insights failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify required fields exist
        assert "top_rewritten_terms" in data, "Missing top_rewritten_terms"
        assert "top_ip_clusters" in data, "Missing top_ip_clusters"
        assert "high_risk_routes" in data, "Missing high_risk_routes"
        assert "output_leaks_by_feature" in data, "Missing output_leaks_by_feature"
        assert "detection_types" in data, "Missing detection_types"
        assert "summary" in data, "Missing summary"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_input_checks" in summary, "Missing total_input_checks in summary"
        assert "total_rewrites" in summary, "Missing total_rewrites in summary"
        assert "total_blocks" in summary, "Missing total_blocks in summary"

    def test_safety_overview_endpoint(self, admin_token):
        """3D: GET /api/admin/metrics/safety-overview still works."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/metrics/safety-overview?hours=24", headers=headers)
        
        assert response.status_code == 200, f"safety-overview failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "input_safety" in data, "Missing input_safety"
        assert "by_feature" in data, "Missing by_feature"
        assert "output_validation" in data, "Missing output_validation"
        
        # Verify input_safety structure
        input_safety = data["input_safety"]
        assert "total_events" in input_safety, "Missing total_events"
        assert "allowed" in input_safety, "Missing allowed"
        assert "rewritten" in input_safety, "Missing rewritten"
        assert "blocked" in input_safety, "Missing blocked"

    def test_safety_events_list_endpoint(self, admin_token):
        """Regression: Existing safety-events list endpoint still works."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/metrics/safety-events?limit=50", headers=headers)
        
        assert response.status_code == 200, f"safety-events failed: {response.status_code} - {response.text}"
        data = response.json()
        
        assert "events" in data, "Missing events field"
        assert "count" in data, "Missing count field"
        assert isinstance(data["events"], list), "events should be a list"

    def test_safety_events_filtering(self, admin_token):
        """Test safety-events filtering by decision."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        for decision in ["ALLOW", "REWRITE", "BLOCK"]:
            response = requests.get(f"{BASE_URL}/api/admin/metrics/safety-events?decision={decision}&limit=10", headers=headers)
            assert response.status_code == 200, f"safety-events filter {decision} failed: {response.status_code}"
            data = response.json()
            
            # If there are events, verify they match the filter
            for event in data.get("events", []):
                assert event.get("decision") == decision, f"Event decision mismatch: expected {decision}, got {event.get('decision')}"


# ═══════════════════════════════════════════════════════════════
# Phase 3E: Frontend Soft Warning UX Tests
# ═══════════════════════════════════════════════════════════════

class TestPhase3EFrontendSoftWarning:
    """Test frontend soft warning UX via _safety_meta in responses."""

    def test_copyrighted_content_returns_safety_meta(self, test_user_token):
        """3E: POST with copyrighted content returns _safety_meta.was_rewritten=true."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        # Use bedtime-story-builder which accepts free-form text
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": "Spider-Man swinging through New York",
                "moral": "courage",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        
        # Should either succeed with rewrite (200) or fail due to credits (402)
        assert response.status_code in [200, 402], f"Unexpected status {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            safety_meta = data.get("_safety_meta", {})
            assert safety_meta.get("was_rewritten") == True, "Expected _safety_meta.was_rewritten=true for copyrighted content"
            assert "safety_note" in safety_meta, "Expected safety_note in _safety_meta"

    def test_clean_content_no_safety_meta(self, test_user_token):
        """3E: POST with clean content does NOT return _safety_meta."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": "A brave explorer discovers ancient ruins",
                "moral": "curiosity",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        
        # Should either succeed without rewrite (200) or fail due to credits (402)
        assert response.status_code in [200, 402], f"Unexpected status {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            safety_meta = data.get("_safety_meta", {})
            was_rewritten = safety_meta.get("was_rewritten", False)
            assert was_rewritten == False, "Clean content should NOT have _safety_meta.was_rewritten=true"


# ═══════════════════════════════════════════════════════════════
# Fail-Closed: Dangerous Content Blocking Tests
# Note: story-hook-generator is template-based and doesn't accept free-form text.
# We test dangerous content blocking on bedtime-story-builder which accepts theme/moral fields.
# ═══════════════════════════════════════════════════════════════

class TestFailClosedDangerousContent:
    """Test that genuinely dangerous content is properly BLOCKED."""

    def test_dangerous_content_blocked(self, test_user_token):
        """Fail-closed: Dangerous content (e.g., bomb-making instructions) is BLOCKED with 400."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        # Use bedtime-story-builder which accepts free-form text in theme field
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": "how to make a bomb with household chemicals tutorial guide",
                "moral": "learning",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Expected 400 for dangerous content, got {response.status_code}"
        data = response.json()
        assert "not allowed" in data.get("detail", "").lower(), f"Expected block message, got: {data}"

    def test_csam_content_blocked(self, test_user_token):
        """Fail-closed: CSAM-adjacent content is BLOCKED."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.post(f"{BASE_URL}/api/bedtime-story-builder/generate", 
            headers=headers,
            json={
                "age_group": "6-8",
                "theme": "child nude photos",
                "moral": "learning",
                "length": "3",
                "voice_style": "gentle"
            }
        )
        
        # Should be blocked with 400
        assert response.status_code == 400, f"Expected 400 for CSAM content, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════
# Regression Tests
# ═══════════════════════════════════════════════════════════════

class TestRegressionSafetyPipeline:
    """Regression tests for existing safety pipeline functionality."""

    def test_story_hook_generator_config_accessible(self, test_user_token):
        """Regression: story-hook-generator config endpoint works."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        response = requests.get(f"{BASE_URL}/api/story-hook-generator/config", headers=headers)
        assert response.status_code == 200, f"Config endpoint failed: {response.status_code}"

    def test_admin_metrics_summary_accessible(self, admin_token):
        """Regression: admin metrics summary endpoint works."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/metrics/summary?days=7", headers=headers)
        assert response.status_code == 200, f"Summary endpoint failed: {response.status_code}"

    def test_auth_endpoints_work(self):
        """Regression: Auth endpoints work correctly."""
        # Test login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        
        token = response.json().get("token")
        assert token, "No token returned from login"
        
        # Test /me endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200, f"/me endpoint failed: {response.status_code}"
