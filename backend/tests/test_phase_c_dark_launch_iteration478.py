"""
Phase C Dark Launch Infrastructure Tests - Iteration 478
Tests for: Leaderboards, Rewards, Streaks, Achievements (Dark Launch)
All engines compute silently, UI gated behind feature flag.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestPhaseCStatus:
    """Test Phase C feature flag status endpoint"""
    
    def test_phase_c_status_returns_correct_structure(self):
        """GET /api/phase-c/status returns enable_phase_c:false with correct threshold/volume data"""
        response = requests.get(f"{BASE_URL}/api/phase-c/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") is True
        assert "enable_phase_c" in data
        assert "thresholds_passing" in data
        assert "required_thresholds" in data
        assert "total_viral_events" in data
        assert "required_viral_events" in data
        assert "condition_a_met" in data
        assert "condition_b_met" in data
        
        # Verify required_thresholds is 4 and required_viral_events is 1000
        assert data["required_thresholds"] == 4
        assert data["required_viral_events"] == 1000
        
        print(f"Phase C Status: enable_phase_c={data['enable_phase_c']}, "
              f"thresholds={data['thresholds_passing']}/4, "
              f"viral_events={data['total_viral_events']}/1000")
    
    def test_phase_c_status_no_auth_required(self):
        """Phase C status endpoint should be publicly accessible"""
        response = requests.get(f"{BASE_URL}/api/phase-c/status")
        assert response.status_code == 200


class TestPhaseCEngines:
    """Test Phase C engine computation endpoints (admin only)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Admin auth headers"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get normal user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def user_headers(self, user_token):
        """Normal user auth headers"""
        return {"Authorization": f"Bearer {user_token}"}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENGINE TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_compute_streaks_admin_only(self, admin_headers):
        """POST /api/phase-c/engine/compute-streaks tracks streak data correctly"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/compute-streaks",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "streaks_updated" in data
        assert "active_streaks" in data
        assert "freezes_auto_used" in data
        assert "tier_distribution" in data
        
        print(f"Streaks computed: {data['streaks_updated']} updated, "
              f"{data['active_streaks']} active, "
              f"tiers: {data['tier_distribution']}")
    
    def test_compute_leaderboard_admin_only(self, admin_headers):
        """POST /api/phase-c/engine/compute-leaderboard stores rankings and daily snapshots"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/compute-leaderboard",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "total_ranked" in data
        assert "tier_distribution" in data
        
        # Verify tier distribution structure
        tier_dist = data["tier_distribution"]
        assert "diamond" in tier_dist
        assert "gold" in tier_dist
        assert "silver" in tier_dist
        assert "bronze" in tier_dist
        
        print(f"Leaderboard computed: {data['total_ranked']} ranked, "
              f"tiers: {tier_dist}")
    
    def test_compute_rewards_admin_only(self, admin_headers):
        """POST /api/phase-c/engine/compute-rewards silently creates pending rewards with earned_at"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/compute-rewards",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "new_rewards_created" in data
        assert "new_notifications_drafted" in data
        assert "total_pending_rewards" in data
        assert "total_draft_notifications" in data
        
        print(f"Rewards computed: {data['new_rewards_created']} new, "
              f"{data['total_pending_rewards']} total pending, "
              f"{data['total_draft_notifications']} notification drafts")
    
    def test_compute_achievements_admin_only(self, admin_headers):
        """POST /api/phase-c/engine/compute-achievements awards rank/streak/reward badges"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/compute-achievements",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "new_achievements_awarded" in data
        assert "total_achievements" in data
        assert "category_distribution" in data
        
        # Verify category distribution structure
        cat_dist = data["category_distribution"]
        assert "rank" in cat_dist
        assert "streak" in cat_dist
        assert "reward" in cat_dist
        
        print(f"Achievements computed: {data['new_achievements_awarded']} new, "
              f"{data['total_achievements']} total, "
              f"categories: {cat_dist}")
    
    def test_run_all_engines_admin_only(self, admin_headers):
        """POST /api/phase-c/engine/run-all computes all 4 engines (streaks, leaderboard, rewards, achievements)"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/run-all",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "engines" in data
        
        engines = data["engines"]
        assert "streaks" in engines
        assert "leaderboard" in engines
        assert "rewards" in engines
        assert "achievements" in engines
        
        # Verify each engine returned success
        assert engines["streaks"].get("success") is True
        assert engines["leaderboard"].get("success") is True
        assert engines["rewards"].get("success") is True
        assert engines["achievements"].get("success") is True
        
        print(f"All engines ran successfully: "
              f"streaks={engines['streaks']['streaks_updated']}, "
              f"leaderboard={engines['leaderboard']['total_ranked']}, "
              f"rewards={engines['rewards']['total_pending_rewards']}, "
              f"achievements={engines['achievements']['total_achievements']}")


class TestPhaseCAdminMonitor:
    """Test Phase C admin monitoring endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Admin auth headers"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_admin_monitor_returns_aggregate_stats(self, admin_headers):
        """GET /api/phase-c/admin/monitor returns aggregate stats"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/monitor",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        
        # Verify all required sections
        assert "activation" in data
        assert "leaderboard" in data
        assert "rewards" in data
        assert "streaks" in data
        assert "achievements" in data
        assert "notifications" in data
        assert "simulated_engagement" in data
        
        # Verify activation section
        activation = data["activation"]
        assert "enable_phase_c" in activation
        assert "thresholds_passing" in activation
        assert "required_thresholds" in activation
        assert "total_viral_events" in activation
        assert "required_viral_events" in activation
        assert "condition_a_met" in activation
        assert "condition_b_met" in activation
        
        # Verify simulated engagement section
        sim = data["simulated_engagement"]
        assert "users_eligible_for_leaderboard_display" in sim
        assert "users_eligible_for_reward_reveal" in sim
        assert "users_with_streak_badges" in sim
        assert "users_with_rank_badges" in sim
        
        print(f"Admin Monitor: activation={activation['enable_phase_c']}, "
              f"leaderboard={data['leaderboard']['total_ranked']}, "
              f"rewards={data['rewards']['total_pending']}, "
              f"streaks={data['streaks']['total_active']}, "
              f"achievements={data['achievements']['total']}")
    
    def test_drill_down_leaderboard(self, admin_headers):
        """GET /api/phase-c/admin/drill-down?category=leaderboard returns per-user drill-down data"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/drill-down?category=leaderboard",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("category") == "leaderboard"
        assert "results" in data
        
        # If there are results, verify structure
        if data["results"]:
            entry = data["results"][0]
            assert "user_id" in entry
            assert "name" in entry
            assert "viral_score" in entry
            assert "rank_tier" in entry
            assert "rank_position" in entry
            print(f"Leaderboard drill-down: {len(data['results'])} entries, "
                  f"top: {entry.get('name')} (score: {entry.get('viral_score')})")
        else:
            print("Leaderboard drill-down: No entries yet")
    
    def test_drill_down_streaks(self, admin_headers):
        """GET /api/phase-c/admin/drill-down?category=streaks returns streak drill-down"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/drill-down?category=streaks",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("category") == "streaks"
        assert "results" in data
        
        if data["results"]:
            entry = data["results"][0]
            assert "user_id" in entry
            assert "name" in entry
            assert "streak_days" in entry
            print(f"Streaks drill-down: {len(data['results'])} entries, "
                  f"top: {entry.get('name')} ({entry.get('streak_days')} days)")
        else:
            print("Streaks drill-down: No entries yet")
    
    def test_drill_down_rewards(self, admin_headers):
        """GET /api/phase-c/admin/drill-down?category=rewards returns reward drill-down"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/drill-down?category=rewards",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("category") == "rewards"
        assert "results" in data
        
        if data["results"]:
            entry = data["results"][0]
            assert "user_id" in entry
            assert "name" in entry
            assert "total_credits_pending" in entry
            assert "reward_count" in entry
            print(f"Rewards drill-down: {len(data['results'])} entries, "
                  f"top: {entry.get('name')} ({entry.get('total_credits_pending')} credits)")
        else:
            print("Rewards drill-down: No entries yet")
    
    def test_drill_down_achievements(self, admin_headers):
        """GET /api/phase-c/admin/drill-down?category=achievements returns achievement drill-down"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/drill-down?category=achievements",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("category") == "achievements"
        assert "results" in data
        
        if data["results"]:
            entry = data["results"][0]
            assert "user_id" in entry
            assert "name" in entry
            assert "badge_count" in entry
            assert "badges" in entry
            print(f"Achievements drill-down: {len(data['results'])} entries, "
                  f"top: {entry.get('name')} ({entry.get('badge_count')} badges)")
        else:
            print("Achievements drill-down: No entries yet")


class TestPhaseCSecurityAuth:
    """Test Phase C security - authentication and authorization"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get normal user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def user_headers(self, user_token):
        """Normal user auth headers"""
        return {"Authorization": f"Bearer {user_token}"}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UNAUTHENTICATED ACCESS TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_admin_monitor_unauthenticated_returns_401(self):
        """Unauthenticated access to admin/monitor returns 401"""
        response = requests.get(f"{BASE_URL}/api/phase-c/admin/monitor")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"Admin monitor unauthenticated: {response.status_code}")
    
    def test_admin_drill_down_unauthenticated_returns_401(self):
        """Unauthenticated access to admin/drill-down returns 401"""
        response = requests.get(f"{BASE_URL}/api/phase-c/admin/drill-down?category=leaderboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"Admin drill-down unauthenticated: {response.status_code}")
    
    def test_engine_compute_streaks_unauthenticated_returns_401(self):
        """Unauthenticated access to engine/compute-streaks returns 401"""
        response = requests.post(f"{BASE_URL}/api/phase-c/engine/compute-streaks")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"Engine compute-streaks unauthenticated: {response.status_code}")
    
    def test_engine_run_all_unauthenticated_returns_401(self):
        """Unauthenticated access to engine/run-all returns 401"""
        response = requests.post(f"{BASE_URL}/api/phase-c/engine/run-all")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"Engine run-all unauthenticated: {response.status_code}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NORMAL USER ACCESS TESTS (should be denied)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_admin_monitor_normal_user_returns_403(self, user_headers):
        """Normal user access to admin/monitor returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/monitor",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"Admin monitor normal user: {response.status_code}")
    
    def test_admin_drill_down_normal_user_returns_403(self, user_headers):
        """Normal user access to admin/drill-down returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/phase-c/admin/drill-down?category=leaderboard",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"Admin drill-down normal user: {response.status_code}")
    
    def test_engine_compute_streaks_normal_user_returns_403(self, user_headers):
        """Normal user access to engine/compute-streaks returns 403"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/compute-streaks",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"Engine compute-streaks normal user: {response.status_code}")
    
    def test_engine_run_all_normal_user_returns_403(self, user_headers):
        """Normal user access to engine/run-all returns 403"""
        response = requests.post(
            f"{BASE_URL}/api/phase-c/engine/run-all",
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"Engine run-all normal user: {response.status_code}")


class TestPhaseCNoDataLeaks:
    """Test that Phase C data doesn't leak to public endpoints"""
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get normal user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"User login failed: {response.status_code}")
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def user_headers(self, user_token):
        """Normal user auth headers"""
        return {"Authorization": f"Bearer {user_token}"}
    
    def test_public_streaks_endpoint_no_phase_c_data(self, user_headers):
        """Public /api/streaks/my should not expose Phase C hidden data"""
        response = requests.get(
            f"{BASE_URL}/api/streaks/my",
            headers=user_headers
        )
        # Endpoint may return 200 or 404 depending on user data
        if response.status_code == 200:
            data = response.json()
            # Should not contain Phase C specific fields
            assert "freeze_tokens_earned" not in data or data.get("freeze_tokens_earned") is None
            assert "current_tier" not in data or data.get("current_tier") is None
            print(f"Public streaks endpoint: No Phase C data leaked")
        else:
            print(f"Public streaks endpoint: {response.status_code} (no data)")
    
    def test_phase_c_status_no_hidden_data(self):
        """Phase C status should not expose internal engine data"""
        response = requests.get(f"{BASE_URL}/api/phase-c/status")
        assert response.status_code == 200
        
        data = response.json()
        # Should not contain detailed user data
        assert "users" not in data
        assert "leaderboard" not in data
        assert "rewards" not in data
        assert "achievements" not in data
        print("Phase C status: No hidden data exposed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
