"""
A/B Testing for Story Hooks - Iteration 347
Tests the story_hook experiment with 4 variants (mystery, emotional, shock, curiosity)
Verifies: hook-analytics, assign-all, convert endpoints, deduplication, and metrics
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestABHookAnalytics:
    """Tests for /api/ab/hook-analytics endpoint"""
    
    def test_hook_analytics_returns_4_variants(self):
        """Verify hook-analytics returns all 4 story_hook variants"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("experiment_id") == "story_hook"
        assert data.get("name") == "Story Hook Style"
        assert data.get("min_sample_size") == 50
        
        variants = data.get("variants", [])
        assert len(variants) == 4, f"Expected 4 variants, got {len(variants)}"
        
        variant_ids = [v["variant_id"] for v in variants]
        assert "hook_mystery" in variant_ids
        assert "hook_emotional" in variant_ids
        assert "hook_shock" in variant_ids
        assert "hook_curiosity" in variant_ids
        print(f"PASS: hook-analytics returns 4 variants: {variant_ids}")
    
    def test_hook_analytics_variant_metrics(self):
        """Verify each variant has required metrics fields"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200
        
        data = response.json()
        variants = data.get("variants", [])
        
        required_fields = ["variant_id", "label", "style", "sessions", "impressions", 
                          "clicks", "ctr", "continues", "continue_rate", 
                          "shares", "share_rate", "sufficient_data", "data_warning"]
        
        for variant in variants:
            for field in required_fields:
                assert field in variant, f"Missing field '{field}' in variant {variant.get('variant_id')}"
        
        print(f"PASS: All variants have required metrics fields")
    
    def test_hook_analytics_variant_styles(self):
        """Verify variant styles match expected values"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200
        
        data = response.json()
        variants = data.get("variants", [])
        
        style_map = {
            "hook_mystery": "mystery",
            "hook_emotional": "emotional",
            "hook_shock": "shock",
            "hook_curiosity": "curiosity"
        }
        
        for variant in variants:
            vid = variant["variant_id"]
            expected_style = style_map.get(vid)
            assert variant["style"] == expected_style, f"Variant {vid} has wrong style: {variant['style']}"
        
        print(f"PASS: All variant styles match expected values")
    
    def test_hook_analytics_data_warning_when_insufficient(self):
        """Verify data_warning appears when impressions < 50"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200
        
        data = response.json()
        variants = data.get("variants", [])
        
        for variant in variants:
            if variant["impressions"] < 50:
                assert variant["sufficient_data"] is False
                assert variant["data_warning"] is not None
                assert "impressions" in variant["data_warning"].lower()
                print(f"  - {variant['variant_id']}: {variant['data_warning']}")
        
        print(f"PASS: Data warnings shown for variants with insufficient data")


class TestABAssignAll:
    """Tests for /api/ab/assign-all endpoint"""
    
    def test_assign_all_returns_story_hook_variant(self):
        """Verify assign-all returns story_hook variant assignment"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={"session_id": session_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("session_id") == session_id
        assert "assignments" in data
        assert "story_hook" in data["assignments"]
        
        story_hook = data["assignments"]["story_hook"]
        assert "variant_id" in story_hook
        assert "variant_data" in story_hook
        assert story_hook["variant_id"].startswith("hook_")
        
        print(f"PASS: assign-all returns story_hook variant: {story_hook['variant_id']}")
    
    def test_assign_all_variant_data_structure(self):
        """Verify variant_data contains required fields for story_hook"""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={"session_id": session_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        variant_data = data["assignments"]["story_hook"]["variant_data"]
        
        required_fields = ["style", "section_label", "hook_suffix", "cta_text", "urgency", "accent"]
        for field in required_fields:
            assert field in variant_data, f"Missing field '{field}' in variant_data"
        
        print(f"PASS: variant_data contains all required fields: {list(variant_data.keys())}")
    
    def test_assign_all_deterministic(self):
        """Verify same session_id gets same variant (deterministic)"""
        session_id = f"test_deterministic_{uuid.uuid4().hex[:8]}"
        
        # First call
        response1 = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={"session_id": session_id}
        )
        variant1 = response1.json()["assignments"]["story_hook"]["variant_id"]
        
        # Second call with same session_id
        response2 = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={"session_id": session_id}
        )
        variant2 = response2.json()["assignments"]["story_hook"]["variant_id"]
        
        assert variant1 == variant2, f"Variants differ: {variant1} vs {variant2}"
        print(f"PASS: Deterministic assignment - same session gets same variant: {variant1}")
    
    def test_assign_all_requires_session_id(self):
        """Verify assign-all returns 400 without session_id"""
        response = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={}
        )
        assert response.status_code == 400
        print(f"PASS: assign-all returns 400 without session_id")


class TestABConvert:
    """Tests for /api/ab/convert endpoint"""
    
    def test_convert_impression_event(self):
        """Verify convert tracks impression event"""
        session_id = f"test_convert_{uuid.uuid4().hex[:8]}"
        
        # First assign a variant
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        # Track impression
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "impression"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        print(f"PASS: convert tracks impression event")
    
    def test_convert_click_event(self):
        """Verify convert tracks click event"""
        session_id = f"test_convert_{uuid.uuid4().hex[:8]}"
        
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "click"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
        print(f"PASS: convert tracks click event")
    
    def test_convert_continue_click_event(self):
        """Verify convert tracks continue_click event"""
        session_id = f"test_convert_{uuid.uuid4().hex[:8]}"
        
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "continue_click"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
        print(f"PASS: convert tracks continue_click event")
    
    def test_convert_share_click_event(self):
        """Verify convert tracks share_click event"""
        session_id = f"test_convert_{uuid.uuid4().hex[:8]}"
        
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "share_click"
            }
        )
        assert response.status_code == 200
        assert response.json().get("success") is True
        print(f"PASS: convert tracks share_click event")
    
    def test_convert_deduplication(self):
        """Verify convert deduplicates same session+experiment+event"""
        session_id = f"test_dedupe_{uuid.uuid4().hex[:8]}"
        
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        # First conversion
        response1 = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "impression"
            }
        )
        assert response1.json().get("success") is True
        assert response1.json().get("dedupe") is not True  # First time, no dedupe
        
        # Second conversion (same event)
        response2 = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "impression"
            }
        )
        assert response2.json().get("success") is True
        assert response2.json().get("dedupe") is True  # Should be deduplicated
        
        print(f"PASS: convert deduplicates same session+experiment+event")
    
    def test_convert_invalid_event(self):
        """Verify convert returns 400 for invalid event"""
        session_id = f"test_invalid_{uuid.uuid4().hex[:8]}"
        
        requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "invalid_event"
            }
        )
        assert response.status_code == 400
        print(f"PASS: convert returns 400 for invalid event")
    
    def test_convert_no_assignment(self):
        """Verify convert returns no_assignment for unassigned session"""
        session_id = f"test_no_assign_{uuid.uuid4().hex[:8]}"
        
        # Don't assign first, just try to convert
        response = requests.post(
            f"{BASE_URL}/api/ab/convert",
            json={
                "session_id": session_id,
                "experiment_id": "story_hook",
                "event": "impression"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is False
        assert data.get("reason") == "no_assignment"
        print(f"PASS: convert returns no_assignment for unassigned session")


class TestAdminHookABSection:
    """Tests for Admin Dashboard Hook A/B section"""
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_admin_can_access_hook_analytics(self):
        """Verify admin can access hook-analytics endpoint"""
        token = self.get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/ab/hook-analytics",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert len(data.get("variants", [])) == 4
        print(f"PASS: Admin can access hook-analytics")
    
    def test_hook_analytics_summary_metrics(self):
        """Verify hook-analytics returns summary metrics for admin dashboard"""
        response = requests.get(f"{BASE_URL}/api/ab/hook-analytics")
        assert response.status_code == 200
        
        data = response.json()
        variants = data.get("variants", [])
        
        # Calculate summary metrics
        total_impressions = sum(v["impressions"] for v in variants)
        best_ctr = max(v["ctr"] for v in variants) if variants else 0
        best_continue = max(v["continue_rate"] for v in variants) if variants else 0
        best_share = max(v["share_rate"] for v in variants) if variants else 0
        
        print(f"  Total Impressions: {total_impressions}")
        print(f"  Best CTR: {best_ctr}%")
        print(f"  Best Continue %: {best_continue}%")
        print(f"  Best Share %: {best_share}%")
        print(f"PASS: Summary metrics calculable from hook-analytics response")


class TestPublicPageABIntegration:
    """Tests for A/B testing integration on public share pages"""
    
    def test_public_creation_endpoint(self):
        """Verify public creation endpoint returns data for A/B testing"""
        slug = "13ddd5d5-307c-4c45-8ac6-e349344d8abf"
        
        response = requests.get(f"{BASE_URL}/api/public/creation/{slug}")
        assert response.status_code == 200
        
        data = response.json()
        assert "creation" in data
        creation = data["creation"]
        assert "title" in creation
        assert "slug" in creation
        print(f"PASS: Public creation endpoint returns data for slug: {slug}")
    
    def test_ab_variant_assignment_for_public_page(self):
        """Verify A/B variant can be assigned for public page visitor"""
        session_id = f"public_visitor_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/ab/assign-all",
            json={"session_id": session_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        story_hook = data["assignments"]["story_hook"]
        
        # Verify variant_data has fields needed for public page
        variant_data = story_hook["variant_data"]
        assert "section_label" in variant_data  # For cliffhanger section label
        assert "hook_suffix" in variant_data    # For hook suffix text
        assert "cta_text" in variant_data       # For Continue button text
        assert "accent" in variant_data         # For styling
        
        print(f"PASS: A/B variant assigned for public page: {story_hook['variant_id']}")
        print(f"  section_label: {variant_data['section_label']}")
        print(f"  cta_text: {variant_data['cta_text']}")


class TestABResultsEndpoint:
    """Tests for /api/ab/results endpoint"""
    
    def test_ab_results_returns_story_hook(self):
        """Verify /api/ab/results includes story_hook experiment"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=story_hook")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        experiments = data.get("experiments", [])
        assert len(experiments) >= 1
        
        story_hook_exp = next((e for e in experiments if e["experiment_id"] == "story_hook"), None)
        assert story_hook_exp is not None
        assert story_hook_exp["name"] == "Story Hook Style"
        assert story_hook_exp["primary_event"] == "continue_click"
        assert len(story_hook_exp["variants"]) == 4
        
        print(f"PASS: /api/ab/results returns story_hook experiment")
    
    def test_ab_results_variant_conversions(self):
        """Verify /api/ab/results returns conversion counts per variant"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=story_hook")
        assert response.status_code == 200
        
        data = response.json()
        story_hook_exp = data["experiments"][0]
        
        for variant in story_hook_exp["variants"]:
            assert "sessions" in variant
            assert "conversions" in variant
            assert "primary_conv_rate" in variant
            
            # Conversions should have all event types
            conversions = variant["conversions"]
            assert "impression" in conversions
            assert "click" in conversions
            assert "continue_click" in conversions
            assert "share_click" in conversions
        
        print(f"PASS: /api/ab/results returns conversion counts per variant")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
