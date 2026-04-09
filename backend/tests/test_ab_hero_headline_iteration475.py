"""
A/B Hero Headline Testing - Iteration 475
Tests for the A/B Hook Text Optimization framework for homepage hero headline.
Week 1: 2 variants (A control vs B challenger)
"""

import pytest
import requests
import os
import uuid
import hashlib

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Hero headline experiment config
EXPERIMENT_ID = "hero_headline"
VARIANT_A = "headline_a"  # Control - "Create stories kids will remember forever"
VARIANT_B = "headline_b"  # Challenger - "Create award-worthy AI stories in minutes"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed - skipping admin tests")


@pytest.fixture(scope="module")
def authenticated_admin_client(api_client, admin_token):
    """Session with admin auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestABResultsEndpoint:
    """Test GET /api/ab/results?experiment_id=hero_headline"""
    
    def test_results_returns_correct_structure(self, api_client):
        """Backend: GET /api/ab/results?experiment_id=hero_headline returns correct structure with 2 variants"""
        response = api_client.get(f"{BASE_URL}/api/ab/results?experiment_id={EXPERIMENT_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True, "Response should have success=True"
        assert "experiments" in data, "Response should have experiments array"
        
        experiments = data["experiments"]
        assert len(experiments) >= 1, "Should have at least 1 experiment"
        
        # Find hero_headline experiment
        hero_exp = next((e for e in experiments if e["experiment_id"] == EXPERIMENT_ID), None)
        assert hero_exp is not None, f"Should find {EXPERIMENT_ID} experiment"
        
        # Verify experiment structure
        assert hero_exp["name"] == "Hero Headline — Week 1 (A vs B)", f"Experiment name mismatch: {hero_exp.get('name')}"
        assert hero_exp["primary_event"] == "experience_click", f"Primary event should be experience_click"
        assert hero_exp["secondary_event"] == "paywall_shown", f"Secondary event should be paywall_shown"
        assert hero_exp["active"] is True, "Experiment should be active"
        assert hero_exp["min_sessions_per_variant"] == 500, "Min sessions should be 500"
        
        # Verify 2 variants
        variants = hero_exp["variants"]
        assert len(variants) == 2, f"Should have exactly 2 variants, got {len(variants)}"
        
        # Verify variant structure
        variant_ids = [v["variant_id"] for v in variants]
        assert VARIANT_A in variant_ids, f"Should have {VARIANT_A} variant"
        assert VARIANT_B in variant_ids, f"Should have {VARIANT_B} variant"
        
        # Verify control variant
        control_variant = next((v for v in variants if v["variant_id"] == VARIANT_A), None)
        assert control_variant is not None, "Should find control variant"
        assert control_variant["is_control"] is True, "headline_a should be marked as control"
        assert control_variant["label"] == "Emotional (Control)", f"Control label mismatch: {control_variant.get('label')}"
        
        # Verify challenger variant
        challenger_variant = next((v for v in variants if v["variant_id"] == VARIANT_B), None)
        assert challenger_variant is not None, "Should find challenger variant"
        assert challenger_variant["is_control"] is False, "headline_b should NOT be marked as control"
        assert challenger_variant["label"] == "Prestige (Challenger)", f"Challenger label mismatch: {challenger_variant.get('label')}"
        
        # Verify each variant has required metrics
        for v in variants:
            assert "sessions" in v, f"Variant {v['variant_id']} should have sessions"
            assert "impressions" in v, f"Variant {v['variant_id']} should have impressions"
            assert "clicks" in v, f"Variant {v['variant_id']} should have clicks"
            assert "ctr" in v, f"Variant {v['variant_id']} should have ctr"
            assert "paywall_rate" in v, f"Variant {v['variant_id']} should have paywall_rate"
        
        # Verify confidence is present
        assert "confidence" in hero_exp, "Experiment should have confidence field"
        
        print(f"✓ Results endpoint returns correct structure with 2 variants")
        print(f"  - Control: {control_variant['label']} (sessions: {control_variant['sessions']})")
        print(f"  - Challenger: {challenger_variant['label']} (sessions: {challenger_variant['sessions']})")
        print(f"  - Confidence: {hero_exp['confidence']}%")


class TestABAssignEndpoint:
    """Test POST /api/ab/assign for sticky variant assignment"""
    
    def test_assign_returns_variant(self, api_client):
        """Backend: POST /api/ab/assign with session_id + experiment_id returns sticky variant assignment"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "experiment_id" in data, "Response should have experiment_id"
        assert data["experiment_id"] == EXPERIMENT_ID, f"Experiment ID mismatch"
        assert "variant_id" in data, "Response should have variant_id"
        assert data["variant_id"] in [VARIANT_A, VARIANT_B], f"Variant should be headline_a or headline_b, got {data['variant_id']}"
        assert "variant_idx" in data, "Response should have variant_idx"
        assert "variant_data" in data, "Response should have variant_data"
        
        # Verify variant_data has headline content
        variant_data = data["variant_data"]
        assert "heading" in variant_data, "variant_data should have heading"
        assert "badge" in variant_data, "variant_data should have badge"
        assert "subtitle" in variant_data, "variant_data should have subtitle"
        
        print(f"✓ Assign endpoint returns variant: {data['variant_id']}")
        print(f"  - Heading: {variant_data['heading']}")
        print(f"  - Badge: {variant_data['badge']}")
    
    def test_same_session_gets_same_variant_idempotent(self, api_client):
        """Backend: Same session_id always gets same variant (idempotent)"""
        session_id = f"idempotent_test_{uuid.uuid4().hex[:8]}"
        
        # First assignment
        response1 = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert response1.status_code == 200
        variant1 = response1.json()["variant_id"]
        
        # Second assignment with same session_id
        response2 = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert response2.status_code == 200
        variant2 = response2.json()["variant_id"]
        
        # Third assignment
        response3 = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert response3.status_code == 200
        variant3 = response3.json()["variant_id"]
        
        # All should be the same
        assert variant1 == variant2 == variant3, f"Same session should always get same variant. Got: {variant1}, {variant2}, {variant3}"
        
        print(f"✓ Same session_id always gets same variant: {variant1} (idempotent)")
    
    def test_different_sessions_get_roughly_50_50_split(self, api_client):
        """Backend: Different session_ids get roughly 50/50 split between headline_a and headline_b"""
        variant_counts = {VARIANT_A: 0, VARIANT_B: 0}
        num_sessions = 100
        
        for i in range(num_sessions):
            session_id = f"split_test_{uuid.uuid4().hex}"
            response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
                "session_id": session_id,
                "experiment_id": EXPERIMENT_ID
            })
            assert response.status_code == 200
            variant = response.json()["variant_id"]
            variant_counts[variant] += 1
        
        # Check roughly 50/50 (allow 30-70 range for statistical variance)
        a_pct = variant_counts[VARIANT_A] / num_sessions * 100
        b_pct = variant_counts[VARIANT_B] / num_sessions * 100
        
        assert 30 <= a_pct <= 70, f"headline_a should be ~50%, got {a_pct}%"
        assert 30 <= b_pct <= 70, f"headline_b should be ~50%, got {b_pct}%"
        
        print(f"✓ Different sessions get roughly 50/50 split")
        print(f"  - headline_a: {variant_counts[VARIANT_A]} ({a_pct:.1f}%)")
        print(f"  - headline_b: {variant_counts[VARIANT_B]} ({b_pct:.1f}%)")
    
    def test_assign_invalid_experiment_returns_404(self, api_client):
        """Backend: POST /api/ab/assign with invalid experiment_id returns 404"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "nonexistent_experiment"
        })
        
        assert response.status_code == 404, f"Expected 404 for invalid experiment, got {response.status_code}"
        print(f"✓ Invalid experiment_id returns 404")


class TestABConvertEndpoint:
    """Test POST /api/ab/convert for tracking conversion events"""
    
    def test_convert_experience_click(self, api_client):
        """Backend: POST /api/ab/convert tracks experience_click event"""
        session_id = f"convert_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track experience_click conversion
        response = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "experience_click"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Conversion should succeed"
        
        print(f"✓ experience_click conversion tracked successfully")
    
    def test_convert_paywall_shown(self, api_client):
        """Backend: POST /api/ab/convert tracks paywall_shown event"""
        session_id = f"paywall_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track paywall_shown conversion
        response = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "paywall_shown"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Conversion should succeed"
        
        print(f"✓ paywall_shown conversion tracked successfully")
    
    def test_convert_impression(self, api_client):
        """Backend: POST /api/ab/convert tracks impression event"""
        session_id = f"impression_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track impression conversion
        response = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "impression"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Conversion should succeed"
        
        print(f"✓ impression conversion tracked successfully")
    
    def test_convert_click(self, api_client):
        """Backend: POST /api/ab/convert tracks click event"""
        session_id = f"click_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track click conversion
        response = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "click"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") is True, "Conversion should succeed"
        
        print(f"✓ click conversion tracked successfully")
    
    def test_convert_dedupe_same_event(self, api_client):
        """Backend: POST /api/ab/convert deduplicates same event for same session"""
        session_id = f"dedupe_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track first conversion
        response1 = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "experience_click"
        })
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Track same conversion again
        response2 = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "experience_click"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Second should be deduplicated
        assert data2.get("success") is True
        assert data2.get("dedupe") is True, "Second conversion should be marked as dedupe"
        
        print(f"✓ Duplicate conversions are deduplicated")
    
    def test_convert_invalid_event_returns_400(self, api_client):
        """Backend: POST /api/ab/convert with invalid event returns 400"""
        session_id = f"invalid_event_test_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        assign_response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        assert assign_response.status_code == 200
        
        # Track invalid event
        response = api_client.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID,
            "event": "invalid_event_type"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid event, got {response.status_code}"
        print(f"✓ Invalid event type returns 400")


class TestPublicABImpressionEndpoint:
    """Test POST /api/public/ab-impression for tracking impressions with traffic source"""
    
    def test_ab_impression_with_traffic_source(self, api_client):
        """Backend: POST /api/public/ab-impression includes traffic_source and session_id fields"""
        session_id = f"impression_public_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/public/ab-impression", json={
            "variant": VARIANT_A,
            "action": "impression",
            "session_id": session_id,
            "traffic_source": "instagram",
            "experiment_id": EXPERIMENT_ID
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("ok") is True, "Response should have ok=True"
        
        print(f"✓ ab-impression endpoint accepts traffic_source and session_id")
    
    def test_ab_impression_different_traffic_sources(self, api_client):
        """Backend: POST /api/public/ab-impression works with different traffic sources"""
        traffic_sources = ["direct", "instagram", "organic", "referral", "internal"]
        
        for source in traffic_sources:
            session_id = f"traffic_{source}_{uuid.uuid4().hex[:8]}"
            response = api_client.post(f"{BASE_URL}/api/public/ab-impression", json={
                "variant": VARIANT_B,
                "action": "ab_variant_assigned",
                "session_id": session_id,
                "traffic_source": source,
                "experiment_id": EXPERIMENT_ID
            })
            assert response.status_code == 200, f"Failed for traffic_source={source}"
        
        print(f"✓ ab-impression works with all traffic sources: {traffic_sources}")
    
    def test_ab_impression_cta_click_action(self, api_client):
        """Backend: POST /api/public/ab-impression tracks cta_click action"""
        session_id = f"cta_click_{uuid.uuid4().hex[:8]}"
        
        response = api_client.post(f"{BASE_URL}/api/public/ab-impression", json={
            "variant": VARIANT_A,
            "action": "cta_click",
            "session_id": session_id,
            "traffic_source": "direct",
            "experiment_id": EXPERIMENT_ID
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ cta_click action tracked via ab-impression")


class TestABResultsConfidenceCalculation:
    """Test that confidence is calculated correctly via z-test"""
    
    def test_results_include_confidence_percentage(self, api_client):
        """Backend: GET /api/ab/results includes confidence percentage from z-test"""
        response = api_client.get(f"{BASE_URL}/api/ab/results?experiment_id={EXPERIMENT_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        hero_exp = next((e for e in data["experiments"] if e["experiment_id"] == EXPERIMENT_ID), None)
        assert hero_exp is not None
        
        # Confidence should be a number between 0 and 100
        confidence = hero_exp.get("confidence")
        assert confidence is not None, "Confidence should be present"
        assert isinstance(confidence, (int, float)), f"Confidence should be numeric, got {type(confidence)}"
        assert 0 <= confidence <= 100, f"Confidence should be 0-100, got {confidence}"
        
        print(f"✓ Results include confidence: {confidence}%")
    
    def test_winner_requires_min_sessions_and_95_confidence(self, api_client):
        """Backend: Winner is only declared when min_sessions reached AND confidence >= 95%"""
        response = api_client.get(f"{BASE_URL}/api/ab/results?experiment_id={EXPERIMENT_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        hero_exp = next((e for e in data["experiments"] if e["experiment_id"] == EXPERIMENT_ID), None)
        assert hero_exp is not None
        
        min_sessions = hero_exp.get("min_sessions_per_variant", 500)
        confidence = hero_exp.get("confidence", 0)
        tentative_winner = hero_exp.get("tentative_winner")
        
        # Check if all variants have min sessions
        all_have_min = all(v["sessions"] >= min_sessions for v in hero_exp["variants"])
        
        if tentative_winner:
            # If there's a winner, both conditions must be met
            assert all_have_min, "Winner declared but not all variants have min sessions"
            assert confidence >= 95, f"Winner declared but confidence is only {confidence}%"
            print(f"✓ Winner declared: {tentative_winner} (confidence: {confidence}%, all variants >= {min_sessions} sessions)")
        else:
            # No winner - either not enough sessions or confidence < 95%
            if not all_have_min:
                print(f"✓ No winner yet - waiting for min sessions ({min_sessions})")
            elif confidence < 95:
                print(f"✓ No winner yet - confidence {confidence}% < 95%")
            else:
                print(f"✓ No winner yet - collecting more data")


class TestDeterministicAssignment:
    """Test that assignment is deterministic based on MD5 hash"""
    
    def test_assignment_is_deterministic(self, api_client):
        """Backend: Assignment is deterministic via MD5 hash of session_id + experiment_id"""
        # Use a known session_id and verify we get consistent results
        session_id = "deterministic_test_session_12345"
        
        # Calculate expected variant using same algorithm as backend
        key = f"{session_id}:{EXPERIMENT_ID}"
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        expected_idx = h % 2  # 2 variants
        expected_variant = VARIANT_A if expected_idx == 0 else VARIANT_B
        
        # Get actual assignment
        response = api_client.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": EXPERIMENT_ID
        })
        
        assert response.status_code == 200
        actual_variant = response.json()["variant_id"]
        actual_idx = response.json()["variant_idx"]
        
        assert actual_idx == expected_idx, f"Expected idx {expected_idx}, got {actual_idx}"
        assert actual_variant == expected_variant, f"Expected {expected_variant}, got {actual_variant}"
        
        print(f"✓ Assignment is deterministic: session '{session_id}' -> {actual_variant} (idx={actual_idx})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
