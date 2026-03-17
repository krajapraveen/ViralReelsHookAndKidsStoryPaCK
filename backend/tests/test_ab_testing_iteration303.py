"""
A/B Testing System - Iteration 303
Tests for lean A/B testing system for viral content platform.
Endpoints: /api/ab/seed, /api/ab/assign, /api/ab/assign-all, /api/ab/convert, /api/ab/results
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAbSeed:
    """POST /api/ab/seed - Seeds 3 initial experiments (idempotent)"""
    
    def test_seed_experiments(self):
        """Seeding returns total_experiments count"""
        response = requests.post(f"{BASE_URL}/api/ab/seed")
        assert response.status_code == 200
        data = response.json()
        assert "seeded" in data
        assert "total_experiments" in data
        assert data["total_experiments"] == 3  # cta_copy, hook_text, login_timing
    
    def test_seed_idempotent(self):
        """Seeding is idempotent - calling twice doesn't create duplicates"""
        response1 = requests.post(f"{BASE_URL}/api/ab/seed")
        response2 = requests.post(f"{BASE_URL}/api/ab/seed")
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Second call should return empty seeded list
        data2 = response2.json()
        assert data2["seeded"] == []
        assert data2["total_experiments"] == 3


class TestAbAssign:
    """POST /api/ab/assign - Assigns deterministic variant for a session + experiment"""
    
    def test_assign_cta_copy(self):
        """Assigns variant for cta_copy experiment"""
        session_id = f"test-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "cta_copy"
        assert data["variant_id"] in ["cta_a", "cta_b", "cta_c"]
        assert data["variant_idx"] in [0, 1, 2]
        assert "variant_data" in data
        assert "cta_text" in data["variant_data"]
    
    def test_assign_hook_text(self):
        """Assigns variant for hook_text experiment"""
        session_id = f"test-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "hook_text"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "hook_text"
        assert data["variant_id"] in ["hook_a", "hook_b", "hook_c"]
        assert "hook_text" in data["variant_data"]
    
    def test_assign_login_timing(self):
        """Assigns variant for login_timing experiment"""
        session_id = f"test-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "login_timing"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == "login_timing"
        assert data["variant_id"] in ["gate_before", "gate_after", "gate_preview"]
        assert "gate_timing" in data["variant_data"]
        assert data["variant_data"]["gate_timing"] in ["before_generate", "after_generate", "after_preview"]
    
    def test_assign_deterministic(self):
        """Same session_id + experiment_id always returns same variant"""
        session_id = f"determinism-test-{uuid.uuid4()}"
        response1 = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        response2 = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["variant_id"] == response2.json()["variant_id"]
    
    def test_assign_nonexistent_experiment(self):
        """Returns 404 for nonexistent experiment"""
        response = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": "test-session",
            "experiment_id": "nonexistent_experiment"
        })
        assert response.status_code == 404


class TestAbAssignAll:
    """POST /api/ab/assign-all - Assigns all active experiments at once for a session"""
    
    def test_assign_all_experiments(self):
        """Returns assignments for all 3 active experiments"""
        session_id = f"test-all-{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/ab/assign-all", json={
            "session_id": session_id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "assignments" in data
        
        # Check all 3 experiments are assigned
        assignments = data["assignments"]
        assert "cta_copy" in assignments
        assert "hook_text" in assignments
        assert "login_timing" in assignments
        
        # Check structure of each assignment
        for exp_id in ["cta_copy", "hook_text", "login_timing"]:
            assert "variant_id" in assignments[exp_id]
            assert "variant_idx" in assignments[exp_id]
            assert "variant_data" in assignments[exp_id]
    
    def test_assign_all_requires_session_id(self):
        """Returns 400 if session_id is missing"""
        response = requests.post(f"{BASE_URL}/api/ab/assign-all", json={})
        assert response.status_code == 400
        assert "session_id" in response.json()["detail"].lower()
    
    def test_assign_all_deterministic(self):
        """Same session always gets same assignments"""
        session_id = f"determinism-all-{uuid.uuid4()}"
        response1 = requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        response2 = requests.post(f"{BASE_URL}/api/ab/assign-all", json={"session_id": session_id})
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Compare all variant assignments
        for exp_id in ["cta_copy", "hook_text", "login_timing"]:
            assert response1.json()["assignments"][exp_id]["variant_id"] == \
                   response2.json()["assignments"][exp_id]["variant_id"]


class TestAbConvert:
    """POST /api/ab/convert - Tracks conversion events with deduplication"""
    
    def test_convert_remix_click(self):
        """Tracks remix_click conversion"""
        session_id = f"convert-{uuid.uuid4()}"
        # First assign
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        # Then convert
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_convert_generate_click(self):
        """Tracks generate_click conversion"""
        session_id = f"convert-gen-{uuid.uuid4()}"
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "hook_text"
        })
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "hook_text",
            "event": "generate_click"
        })
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    def test_convert_signup_completed(self):
        """Tracks signup_completed conversion"""
        session_id = f"convert-signup-{uuid.uuid4()}"
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "login_timing"
        })
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "login_timing",
            "event": "signup_completed"
        })
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    def test_convert_deduplication(self):
        """Duplicate conversion returns dedupe=true"""
        session_id = f"dedupe-{uuid.uuid4()}"
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        
        # First conversion
        response1 = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert response1.status_code == 200
        assert response1.json()["success"] == True
        assert "dedupe" not in response1.json()
        
        # Duplicate conversion
        response2 = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert response2.status_code == 200
        assert response2.json()["success"] == True
        assert response2.json()["dedupe"] == True
    
    def test_convert_invalid_event(self):
        """Returns 400 for invalid event type"""
        session_id = f"invalid-{uuid.uuid4()}"
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "invalid_event"
        })
        assert response.status_code == 400
        assert "Invalid event" in response.json()["detail"]
    
    def test_convert_no_assignment(self):
        """Returns success=false if no assignment exists"""
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": f"no-assignment-{uuid.uuid4()}",
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["reason"] == "no_assignment"
    
    def test_convert_share_click(self):
        """Tracks share_click conversion"""
        session_id = f"convert-share-{uuid.uuid4()}"
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "share_click"
        })
        assert response.status_code == 200
        assert response.json()["success"] == True


class TestAbResults:
    """GET /api/ab/results - Returns experiment results with winner heuristic"""
    
    def test_results_all_experiments(self):
        """Returns results for all experiments"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        assert response.status_code == 200
        data = response.json()
        assert "experiments" in data
        
        experiments = data["experiments"]
        exp_ids = [e["experiment_id"] for e in experiments]
        assert "cta_copy" in exp_ids
        assert "hook_text" in exp_ids
        assert "login_timing" in exp_ids
    
    def test_results_structure(self):
        """Each experiment has correct structure"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        assert response.status_code == 200
        
        for exp in response.json()["experiments"]:
            # Required fields
            assert "experiment_id" in exp
            assert "name" in exp
            assert "primary_event" in exp
            assert "active" in exp
            assert "variants" in exp
            assert "tentative_winner" in exp
            assert "min_sessions_per_variant" in exp
            assert exp["min_sessions_per_variant"] == 200
            
            # Check variant structure
            for variant in exp["variants"]:
                assert "variant_id" in variant
                assert "label" in variant
                assert "sessions" in variant
                assert "conversions" in variant
                assert "primary_conv_rate" in variant
    
    def test_results_single_experiment(self):
        """Can filter results by experiment_id"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=cta_copy")
        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) == 1
        assert data["experiments"][0]["experiment_id"] == "cta_copy"
    
    def test_results_cta_copy_variants(self):
        """CTA Copy experiment has 3 correct variants"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=cta_copy")
        assert response.status_code == 200
        
        exp = response.json()["experiments"][0]
        assert exp["name"] == "CTA Copy Test"
        assert exp["primary_event"] == "remix_click"
        
        variant_ids = [v["variant_id"] for v in exp["variants"]]
        assert "cta_a" in variant_ids
        assert "cta_b" in variant_ids
        assert "cta_c" in variant_ids
        
        labels = {v["variant_id"]: v["label"] for v in exp["variants"]}
        assert labels["cta_a"] == "Create This in 1 Click"
        assert labels["cta_b"] == "Make Your Own Now"
        assert labels["cta_c"] == "Generate This in Seconds"
    
    def test_results_hook_text_variants(self):
        """Hook Text experiment has 3 correct variants"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=hook_text")
        assert response.status_code == 200
        
        exp = response.json()["experiments"][0]
        assert exp["name"] == "Hook Text Test"
        assert exp["primary_event"] == "remix_click"
        
        variant_ids = [v["variant_id"] for v in exp["variants"]]
        assert "hook_a" in variant_ids
        assert "hook_b" in variant_ids
        assert "hook_c" in variant_ids
    
    def test_results_login_timing_variants(self):
        """Login Timing experiment has 3 correct variants"""
        response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=login_timing")
        assert response.status_code == 200
        
        exp = response.json()["experiments"][0]
        assert exp["name"] == "Login Gate Timing"
        assert exp["primary_event"] == "signup_completed"
        
        variant_ids = [v["variant_id"] for v in exp["variants"]]
        assert "gate_before" in variant_ids
        assert "gate_after" in variant_ids
        assert "gate_preview" in variant_ids


class TestAbConversionTracking:
    """Integration test for assignment + conversion flow"""
    
    def test_full_flow_cta_copy(self):
        """Full flow: assign -> convert -> verify in results"""
        session_id = f"full-flow-{uuid.uuid4()}"
        
        # Get assignment
        assign_response = requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        assert assign_response.status_code == 200
        variant_id = assign_response.json()["variant_id"]
        
        # Track conversion
        convert_response = requests.post(f"{BASE_URL}/api/ab/convert", json={
            "session_id": session_id,
            "experiment_id": "cta_copy",
            "event": "remix_click"
        })
        assert convert_response.status_code == 200
        assert convert_response.json()["success"] == True
        
        # Verify in results
        results_response = requests.get(f"{BASE_URL}/api/ab/results?experiment_id=cta_copy")
        assert results_response.status_code == 200
        
        exp = results_response.json()["experiments"][0]
        variant = next(v for v in exp["variants"] if v["variant_id"] == variant_id)
        assert variant["sessions"] >= 1
    
    def test_multiple_conversions_different_events(self):
        """Can track multiple different events for same session"""
        session_id = f"multi-event-{uuid.uuid4()}"
        
        # Assign
        requests.post(f"{BASE_URL}/api/ab/assign", json={
            "session_id": session_id,
            "experiment_id": "cta_copy"
        })
        
        # Track multiple events
        for event in ["remix_click", "generate_click", "signup_completed"]:
            response = requests.post(f"{BASE_URL}/api/ab/convert", json={
                "session_id": session_id,
                "experiment_id": "cta_copy",
                "event": event
            })
            assert response.status_code == 200
            assert response.json()["success"] == True


class TestAbWinnerHeuristic:
    """Tests for the winner heuristic (20%+ uplift after 200 sessions)"""
    
    def test_no_winner_without_200_sessions(self):
        """No winner declared when sessions < 200 per variant"""
        response = requests.get(f"{BASE_URL}/api/ab/results")
        assert response.status_code == 200
        
        # All experiments should have no winner since we don't have 200+ sessions
        for exp in response.json()["experiments"]:
            # Check if any variant has >= 200 sessions
            all_have_200 = all(v["sessions"] >= 200 for v in exp["variants"])
            if not all_have_200:
                assert exp["tentative_winner"] is None, \
                    f"Winner should be None for {exp['experiment_id']} without 200+ sessions per variant"
