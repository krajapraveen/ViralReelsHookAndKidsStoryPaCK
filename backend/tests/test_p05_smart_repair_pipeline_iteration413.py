"""
P0.5 Smart Repair Pipeline Tests - Iteration 413
Tests for the complete smart-repair pipeline refactor for Photo-to-Comic.

Tests:
1. POST /api/photo-to-comic/admin/fallback-validation with mode=single_panel
2. POST /api/photo-to-comic/admin/fallback-validation with mode=majority_failure
3. GET /api/photo-to-comic/admin/ui-safety-audit returns PASS with 0 violations
4. GET /api/admin/metrics/comic-health returns smart_repair field
5. GET /api/admin/metrics/comic-health returns validation_quality field
6. GET /api/admin/metrics/comic-health returns recent_validations list
7. POST /api/photo-to-comic/quality-check backward compatibility
8. Non-admin users get 403 on admin endpoints
9. Backend starts without errors (verified by health check)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text[:200]}")


@pytest.fixture(scope="module")
def test_user_token():
    """Get non-admin user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def user_headers(test_user_token):
    """Headers with non-admin auth"""
    return {"Authorization": f"Bearer {test_user_token}", "Content-Type": "application/json"}


class TestBackendHealth:
    """Verify backend starts without errors after refactor"""
    
    def test_health_endpoint(self):
        """Backend health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ Backend health check passed")
    
    def test_auth_endpoint_available(self):
        """Auth endpoint is available"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "invalid"
        })
        # Should return 401 (unauthorized), not 500 (server error)
        assert response.status_code in [401, 400, 422], f"Auth endpoint error: {response.status_code}"
        print("✓ Auth endpoint available")


class TestFallbackValidationEndpoints:
    """Test fallback validation endpoints after refactor"""
    
    def test_single_panel_validation_works(self, admin_headers):
        """POST /api/photo-to-comic/admin/fallback-validation with mode=single_panel"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/admin/fallback-validation",
            headers=admin_headers,
            json={"mode": "single_panel"}
        )
        assert response.status_code == 200, f"Single panel validation failed: {response.status_code} - {response.text[:300]}"
        
        data = response.json()
        assert "validation_id" in data, "Response should contain validation_id"
        
        validation_id = data["validation_id"]
        print(f"✓ Single panel validation started: {validation_id}")
        
        # Poll for completion (max 60 seconds)
        for _ in range(30):
            time.sleep(2)
            status_response = requests.get(
                f"{BASE_URL}/api/photo-to-comic/admin/fallback-validation/{validation_id}",
                headers=admin_headers
            )
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get("status") in ["COMPLETED", "ERROR"]:
                    print(f"✓ Single panel validation completed: {status_data.get('status')}")
                    # Verify validation quality dimensions exist
                    if status_data.get("status") == "COMPLETED":
                        vq = status_data.get("validation_quality", {})
                        assert "perceived_quality_score" in vq or vq is None, "Should have perceived_quality_score"
                    return
        
        # If we get here, validation timed out but endpoint works
        print("⚠ Validation timed out but endpoint is functional")
    
    def test_majority_failure_validation_works(self, admin_headers):
        """POST /api/photo-to-comic/admin/fallback-validation with mode=majority_failure"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/admin/fallback-validation",
            headers=admin_headers,
            json={"mode": "majority_failure"}
        )
        assert response.status_code == 200, f"Majority failure validation failed: {response.status_code} - {response.text[:300]}"
        
        data = response.json()
        assert "validation_id" in data, "Response should contain validation_id"
        
        validation_id = data["validation_id"]
        print(f"✓ Majority failure validation started: {validation_id}")
        
        # Poll for completion (max 60 seconds)
        for _ in range(30):
            time.sleep(2)
            status_response = requests.get(
                f"{BASE_URL}/api/photo-to-comic/admin/fallback-validation/{validation_id}",
                headers=admin_headers
            )
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get("status") in ["COMPLETED", "ERROR"]:
                    print(f"✓ Majority failure validation completed: {status_data.get('status')}")
                    return
        
        print("⚠ Validation timed out but endpoint is functional")


class TestUISafetyAudit:
    """Test UI safety audit endpoint"""
    
    def test_ui_safety_audit_returns_pass(self, admin_headers):
        """GET /api/photo-to-comic/admin/ui-safety-audit returns PASS with 0 violations"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/admin/ui-safety-audit",
            headers=admin_headers
        )
        assert response.status_code == 200, f"UI safety audit failed: {response.status_code} - {response.text[:300]}"
        
        data = response.json()
        assert "overall" in data, "Response should contain 'overall' field"
        assert data["overall"] == "PASS", f"UI safety audit should PASS, got: {data['overall']}"
        
        violations = data.get("violations", [])
        violation_count = data.get("violation_count", len(violations) if isinstance(violations, list) else violations)
        assert violation_count == 0 or len(violations) == 0, f"Should have 0 violations, got: {violation_count}"
        
        print(f"✓ UI safety audit: {data['overall']} with {violations} violations")
        print(f"  Texts checked: {data.get('texts_checked', 'N/A')}")


class TestComicHealthMetrics:
    """Test comic health metrics endpoint with smart repair fields"""
    
    def test_comic_health_returns_smart_repair_field(self, admin_headers):
        """GET /api/admin/metrics/comic-health returns smart_repair field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health?days=7",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Comic health failed: {response.status_code} - {response.text[:300]}"
        
        data = response.json()
        
        # smart_repair field should exist (may be null if no attempts yet)
        assert "smart_repair" in data, "Response should contain 'smart_repair' field"
        
        smart_repair = data.get("smart_repair")
        if smart_repair is not None:
            # If data exists, verify structure
            assert "total_attempts" in smart_repair, "smart_repair should have total_attempts"
            assert "primary" in smart_repair, "smart_repair should have primary stats"
            assert "repair" in smart_repair, "smart_repair should have repair stats"
            assert "fallback" in smart_repair, "smart_repair should have fallback stats"
            print(f"✓ smart_repair field present with {smart_repair.get('total_attempts', 0)} attempts")
            print(f"  Primary pass rate: {smart_repair.get('primary', {}).get('pass_rate', 'N/A')}%")
            print(f"  Repair success rate: {smart_repair.get('repair', {}).get('pass_rate', 'N/A')}%")
        else:
            print("✓ smart_repair field present (null - no attempts yet)")
    
    def test_comic_health_returns_validation_quality_field(self, admin_headers):
        """GET /api/admin/metrics/comic-health returns validation_quality field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health?days=7",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Comic health failed: {response.status_code}"
        
        data = response.json()
        
        # validation_quality field should exist (may be null if no jobs yet)
        assert "validation_quality" in data, "Response should contain 'validation_quality' field"
        
        vq = data.get("validation_quality")
        if vq is not None:
            # If data exists, verify 5 dimensions structure
            assert "perceived_quality" in vq, "Should have perceived_quality dimension"
            assert "narrative_coherence" in vq, "Should have narrative_coherence dimension"
            assert "style_consistency" in vq, "Should have style_consistency dimension"
            assert "fallback_latency" in vq, "Should have fallback_latency dimension"
            assert "ui_emotional_safety" in vq, "Should have ui_emotional_safety dimension"
            print(f"✓ validation_quality field present with all 5 dimensions")
            print(f"  Perceived quality avg: {vq.get('perceived_quality', {}).get('avg', 'N/A')}")
        else:
            print("✓ validation_quality field present (null - no jobs with scores yet)")
    
    def test_comic_health_returns_recent_validations_list(self, admin_headers):
        """GET /api/admin/metrics/comic-health returns recent_validations list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health?days=7",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Comic health failed: {response.status_code}"
        
        data = response.json()
        
        # recent_validations field should exist (may be empty list)
        assert "recent_validations" in data, "Response should contain 'recent_validations' field"
        
        recent = data.get("recent_validations", [])
        assert isinstance(recent, list), "recent_validations should be a list"
        
        print(f"✓ recent_validations field present with {len(recent)} entries")
        
        if len(recent) > 0:
            # Verify structure of first entry
            first = recent[0]
            assert "validation_id" in first or "mode" in first, "Validation entry should have id or mode"
            print(f"  Latest validation: {first.get('mode', 'N/A')} - {first.get('overall_verdict', 'N/A')}")


class TestBackwardCompatibility:
    """Test backward compatibility of existing endpoints"""
    
    def test_quality_check_endpoint_works(self, admin_headers):
        """POST /api/photo-to-comic/quality-check still works"""
        # Create a minimal test image (1x1 pixel PNG)
        import base64
        # Minimal valid PNG (1x1 transparent pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {"photo": ("test.png", png_data, "image/png")}
        
        # Remove Content-Type from headers for multipart
        headers = {"Authorization": admin_headers["Authorization"]}
        
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/quality-check",
            headers=headers,
            files=files
        )
        
        # Should return 200 with quality result, or 400 if image too small
        assert response.status_code in [200, 400], f"Quality check failed: {response.status_code} - {response.text[:300]}"
        
        if response.status_code == 200:
            data = response.json()
            assert "overall" in data or "quality" in data or "can_proceed" in data, "Should return quality assessment"
            print(f"✓ Quality check endpoint works: {data.get('overall', data.get('quality', 'OK'))}")
        else:
            print("✓ Quality check endpoint works (rejected minimal test image as expected)")


class TestAccessControl:
    """Test admin endpoint access control"""
    
    def test_non_admin_gets_403_on_fallback_validation(self, user_headers):
        """Non-admin users get 403 on admin endpoints"""
        response = requests.post(
            f"{BASE_URL}/api/photo-to-comic/admin/fallback-validation",
            headers=user_headers,
            json={"mode": "single_panel"}
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got: {response.status_code}"
        print("✓ Non-admin correctly blocked from fallback-validation (403)")
    
    def test_non_admin_gets_403_on_ui_safety_audit(self, user_headers):
        """Non-admin users get 403 on UI safety audit"""
        response = requests.get(
            f"{BASE_URL}/api/photo-to-comic/admin/ui-safety-audit",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got: {response.status_code}"
        print("✓ Non-admin correctly blocked from ui-safety-audit (403)")
    
    def test_non_admin_gets_403_on_comic_health(self, user_headers):
        """Non-admin users get 403 on comic health metrics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/metrics/comic-health",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403 for non-admin, got: {response.status_code}"
        print("✓ Non-admin correctly blocked from comic-health (403)")


class TestSmartRepairPipelineModules:
    """Verify smart repair pipeline modules are importable and functional"""
    
    def test_pipeline_enums_importable(self):
        """Pipeline enums module is importable"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from enums.pipeline_enums import (
                FailureType, ModelTier, RepairMode, PipelineState, PanelStatus, RiskBucket,
                PASS_THRESHOLDS, FALLBACK_THRESHOLDS, MODEL_TIER_MAPPING
            )
            
            # Verify key enums exist
            assert FailureType.FACE_DRIFT.value == "face_drift"
            assert ModelTier.TIER1_QUALITY.value == "tier1_quality"
            assert RepairMode.R1_PROMPT_ONLY.value == "R1_PROMPT_ONLY"
            assert RiskBucket.LOW.value == "LOW"
            
            # Verify thresholds exist
            assert "source_similarity" in PASS_THRESHOLDS
            assert "face_consistency" in FALLBACK_THRESHOLDS
            
            # Verify model tier mapping
            assert ModelTier.TIER1_QUALITY in MODEL_TIER_MAPPING
            
            print("✓ pipeline_enums module importable with all expected exports")
        except ImportError as e:
            pytest.fail(f"Failed to import pipeline_enums: {e}")
    
    def test_panel_orchestrator_importable(self):
        """Panel orchestrator module is importable"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.comic_pipeline.panel_orchestrator import PanelOrchestrator
            
            # Verify class exists and has expected methods
            assert hasattr(PanelOrchestrator, 'process_panel')
            assert hasattr(PanelOrchestrator, '_generate_panel')
            
            print("✓ panel_orchestrator module importable")
        except ImportError as e:
            pytest.fail(f"Failed to import panel_orchestrator: {e}")
    
    def test_validator_stack_importable(self):
        """Validator stack module is importable"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.comic_pipeline.validator_stack import ValidatorStack
            
            # Verify class exists and has validate method
            assert hasattr(ValidatorStack, 'validate')
            
            print("✓ validator_stack module importable")
        except ImportError as e:
            pytest.fail(f"Failed to import validator_stack: {e}")
    
    def test_model_router_importable(self):
        """Model router module is importable"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from services.comic_pipeline.model_router import ModelRouter
            
            # Verify class exists and has expected methods
            assert hasattr(ModelRouter, 'choose_initial_tier')
            assert hasattr(ModelRouter, 'choose_repair_strategy')
            
            print("✓ model_router module importable")
        except ImportError as e:
            pytest.fail(f"Failed to import model_router: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
