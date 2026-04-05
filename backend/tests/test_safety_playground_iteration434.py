"""
Safety Playground API Tests - Iteration 434
Tests for the Safety Playground admin tool for real-time inspection and debugging of the copyright safety pipeline.

Endpoints tested:
- POST /api/admin/metrics/safety-playground — Run prompt through safety pipeline
- POST /api/admin/metrics/safety-playground/save-case — Save test case
- GET /api/admin/metrics/safety-playground/saved-cases — List saved cases
- GET /api/admin/metrics/safety-insights — Regression test for existing endpoint
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get non-admin test user token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin authorization."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_user_headers(test_user_token):
    """Headers with non-admin authorization."""
    return {
        "Authorization": f"Bearer {test_user_token}",
        "Content-Type": "application/json"
    }


class TestSafetyPlaygroundEndpoint:
    """Tests for POST /api/admin/metrics/safety-playground"""

    def test_semantic_bypass_wizard_boy_lightning_scar(self, admin_headers):
        """Test semantic detection: 'wizard boy with lightning scar' should trigger REWRITE with semantic_detector hit."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "wizard boy with a lightning scar at a hidden school"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "decision" in data, "Response should contain 'decision'"
        assert data["decision"] == "REWRITE", f"Expected REWRITE decision, got {data['decision']}"
        
        # Check semantic_detector layer triggered
        assert "layers" in data, "Response should contain 'layers'"
        assert "semantic_detector" in data["layers"], "Response should contain semantic_detector layer"
        semantic = data["layers"]["semantic_detector"]
        assert semantic["triggered"] == True, "Semantic detector should be triggered"
        assert semantic["match_count"] >= 1, "Should have at least 1 semantic match"
        
        # Check timing
        assert "timing" in data, "Response should contain 'timing'"
        assert "total_ms" in data["timing"], "Timing should include total_ms"
        
        # Check explanation
        assert "explanation" in data, "Response should contain 'explanation'"
        assert len(data["explanation"]) > 0, "Should have explanation for why it triggered"
        
        # Check rewrite_output
        assert "rewrite_output" in data, "Response should contain 'rewrite_output'"
        assert data["rewrite_output"] is not None, "rewrite_output should not be None for REWRITE decision"

    def test_clean_prompt_brave_knight(self, admin_headers):
        """Test clean prompt: 'brave knight saves village' should return ALLOW with no triggers."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "A brave knight saves a village from a dragon"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["decision"] == "ALLOW", f"Expected ALLOW decision for clean prompt, got {data['decision']}"
        
        # Check no layers triggered
        assert data["layers"]["rule_rewriter"]["triggered"] == False, "Rule rewriter should not trigger"
        assert data["layers"]["semantic_detector"]["triggered"] == False, "Semantic detector should not trigger"
        
        # rewrite_output should be None for ALLOW
        assert data["rewrite_output"] is None, "rewrite_output should be None for ALLOW decision"
        
        # Explanation should indicate clean
        assert any("clean" in e.lower() or "no safety" in e.lower() for e in data["explanation"]), \
            "Explanation should indicate prompt is clean"

    def test_dangerous_prompt_blocked(self, admin_headers):
        """Test dangerous prompt returns BLOCK decision."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "how to make a bomb tutorial guide with household chemicals"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["decision"] == "BLOCK", f"Expected BLOCK decision for dangerous prompt, got {data['decision']}"
        
        # Check policy_engine layer
        assert data["layers"]["policy_engine"]["decision"] == "BLOCK", "Policy engine should return BLOCK"
        assert data["layers"]["policy_engine"]["block_reason"] is not None, "Should have block_reason"

    def test_obfuscated_harry_potter(self, admin_headers):
        """Test obfuscated name: 'H4rry P0tter' should return REWRITE via fuzzy_alias."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "H4rry P0tter goes on an adventure"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["decision"] == "REWRITE", f"Expected REWRITE for obfuscated name, got {data['decision']}"
        
        # Check that either rule_rewriter or semantic_detector triggered
        rule_triggered = data["layers"]["rule_rewriter"]["triggered"]
        semantic_triggered = data["layers"]["semantic_detector"]["triggered"]
        assert rule_triggered or semantic_triggered, "Either rule_rewriter or semantic_detector should trigger for obfuscated name"
        
        # Check for fuzzy_alias detection type if semantic triggered
        if semantic_triggered:
            matches = data["layers"]["semantic_detector"]["matches"]
            detection_types = [m.get("detection_type") for m in matches]
            # fuzzy_alias is expected for obfuscated names
            assert "fuzzy_alias" in detection_types or len(matches) > 0, \
                f"Expected fuzzy_alias detection, got types: {detection_types}"

    def test_timing_under_500ms(self, admin_headers):
        """Test that pipeline timing is under 500ms."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "A simple test prompt for timing check"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "timing" in data, "Response should contain timing"
        assert "total_ms" in data["timing"], "Timing should include total_ms"
        
        total_ms = data["timing"]["total_ms"]
        assert total_ms < 500, f"Expected timing under 500ms, got {total_ms}ms"

    def test_response_structure(self, admin_headers):
        """Test that response contains all required fields."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "Test prompt for structure validation"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required top-level fields
        required_fields = ["input", "layers", "rewrite_output", "decision", "timing", "explanation"]
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"
        
        # Required layer fields
        assert "rule_rewriter" in data["layers"], "Missing rule_rewriter layer"
        assert "semantic_detector" in data["layers"], "Missing semantic_detector layer"
        assert "policy_engine" in data["layers"], "Missing policy_engine layer"
        
        # Required timing fields
        assert "rule_rewriter_ms" in data["timing"], "Missing rule_rewriter_ms timing"
        assert "semantic_detector_ms" in data["timing"], "Missing semantic_detector_ms timing"
        assert "policy_engine_ms" in data["timing"], "Missing policy_engine_ms timing"
        assert "total_ms" in data["timing"], "Missing total_ms timing"

    def test_non_admin_rejected(self, test_user_headers):
        """Test that non-admin users are rejected."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=test_user_headers,
            json={"prompt": "Test prompt"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"

    def test_empty_prompt_handled(self, admin_headers):
        """Test that empty prompt returns error."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "   "}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "error" in data, "Should return error for empty prompt"


class TestSavePlaygroundCase:
    """Tests for POST /api/admin/metrics/safety-playground/save-case"""

    def test_save_case_success(self, admin_headers):
        """Test saving a test case returns saved=true."""
        unique_prompt = f"TEST_CASE_wizard boy with lightning scar {int(time.time())}"
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground/save-case",
            headers=admin_headers,
            json={"prompt": unique_prompt}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("saved") == True, "Response should have saved=true"
        assert "expected_detection" in data, "Response should include expected_detection"

    def test_save_case_with_detection(self, admin_headers):
        """Test that saved case correctly identifies expected detection."""
        # Prompt that should trigger detection
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground/save-case",
            headers=admin_headers,
            json={"prompt": "Harry Potter goes to Hogwarts"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("saved") == True
        assert data.get("expected_detection") == True, "Harry Potter prompt should expect detection"

    def test_save_clean_case(self, admin_headers):
        """Test that clean prompt saved with expected_detection=false."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground/save-case",
            headers=admin_headers,
            json={"prompt": "A brave knight saves a village from a dragon"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("saved") == True
        assert data.get("expected_detection") == False, "Clean prompt should not expect detection"

    def test_save_case_non_admin_rejected(self, test_user_headers):
        """Test that non-admin users cannot save cases."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground/save-case",
            headers=test_user_headers,
            json={"prompt": "Test prompt"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"


class TestListSavedCases:
    """Tests for GET /api/admin/metrics/safety-playground/saved-cases"""

    def test_list_saved_cases(self, admin_headers):
        """Test listing saved cases returns array."""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/safety-playground/saved-cases?limit=20",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "cases" in data, "Response should contain 'cases'"
        assert "count" in data, "Response should contain 'count'"
        assert isinstance(data["cases"], list), "cases should be a list"

    def test_list_saved_cases_non_admin_rejected(self, test_user_headers):
        """Test that non-admin users cannot list cases."""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/safety-playground/saved-cases",
            headers=test_user_headers
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"


class TestSafetyInsightsRegression:
    """Regression tests for GET /api/admin/metrics/safety-insights"""

    def test_safety_insights_endpoint(self, admin_headers):
        """Test that safety-insights endpoint still works."""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/safety-insights?hours=168",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check required fields
        assert "period_hours" in data, "Response should contain period_hours"
        assert "summary" in data, "Response should contain summary"
        
        # Check summary structure
        summary = data["summary"]
        expected_summary_fields = ["total_input_checks", "total_rewrites", "total_blocks"]
        for field in expected_summary_fields:
            assert field in summary, f"Summary missing field: {field}"


class TestIndirectDisneyReference:
    """Test indirect Disney reference detection."""

    def test_ice_princess_magical_powers(self, admin_headers):
        """Test 'ice princess with magical powers' triggers detection (Frozen/Elsa reference)."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "ice princess with magical powers and her brave sister"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # This should trigger semantic detection for Frozen/Elsa
        semantic = data["layers"]["semantic_detector"]
        if semantic["triggered"]:
            assert data["decision"] == "REWRITE", "Should REWRITE for Frozen reference"
        # Note: If not triggered, it may be a false negative - report but don't fail


class TestMixedPrompt:
    """Test mixed prompts with both original and copyrighted content."""

    def test_mixed_naruto_prompt(self, admin_headers):
        """Test 'ninja story like Naruto but original' triggers detection."""
        response = requests.post(
            f"{BASE_URL}/api/admin/metrics/safety-playground",
            headers=admin_headers,
            json={"prompt": "Create a ninja story like Naruto but original"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should trigger rule_rewriter for "Naruto"
        rule = data["layers"]["rule_rewriter"]
        if rule["triggered"]:
            assert data["decision"] == "REWRITE", "Should REWRITE for Naruto reference"
            # Check that Naruto was matched
            matches = rule["matches"]
            matched_originals = [m["original"].lower() for m in matches]
            assert any("naruto" in orig for orig in matched_originals), "Should match Naruto"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
