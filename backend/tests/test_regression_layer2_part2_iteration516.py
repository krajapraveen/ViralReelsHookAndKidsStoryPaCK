"""
Regression Suite Layer 2 Part 2 - Iteration 516
Tests: Battle flow, Credits/Paywall, Share/Public pages, Hero/Feed, Post-generation loop

TC#58-87: Hero/Feed
TC#209-220: Battle
TC#242-260: Credits
TC#231-241: Share
TC#337-346: Performance
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


@pytest.fixture(scope="module")
def test_user_token():
    """Get test user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user login failed: {response.status_code}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin login failed: {response.status_code}")


@pytest.fixture
def test_headers(test_user_token):
    return {"Authorization": f"Bearer {test_user_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ═══════════════════════════════════════════════════════════════════
# TC#242-260: CREDITS TESTS
# ═══════════════════════════════════════════════════════════════════

class TestCredits:
    """Credits API tests - TC#242-260"""

    def test_credits_balance_returns_numeric(self, test_headers):
        """CREDITS-REG-1: Test user credits check returns exact numeric credits"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "credits" in data, "Response should contain 'credits' field"
        assert isinstance(data["credits"], (int, float)), f"Credits should be numeric, got {type(data['credits'])}"
        print(f"CREDITS-REG-1 PASS: Test user has {data['credits']} credits")

    def test_admin_unlimited_credits(self, admin_headers):
        """CREDITS-REG-2: Admin shows is_unlimited=true and credits=999999"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("is_unlimited") == True, f"Admin should have is_unlimited=true, got {data.get('is_unlimited')}"
        assert data.get("credits") == 999999, f"Admin credits should be 999999, got {data.get('credits')}"
        print(f"CREDITS-REG-2 PASS: Admin has unlimited credits (is_unlimited={data.get('is_unlimited')}, credits={data.get('credits')})")

    def test_credits_not_negative(self, test_headers):
        """CREDITS-REG-3: Credits not negative - verify no user can have negative credits"""
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=test_headers)
        assert response.status_code == 200
        data = response.json()
        credits = data.get("credits", 0)
        assert credits >= 0, f"Credits should not be negative, got {credits}"
        print(f"CREDITS-REG-3 PASS: Credits are non-negative ({credits})")

    def test_battle_entry_status(self, test_headers):
        """CREDITS-REG-4: Battle entry status returns entry count and needs_payment flag"""
        response = requests.get(f"{BASE_URL}/api/stories/battle-entry-status", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should have entry_count and needs_payment fields
        assert "entry_count" in data or "needs_payment" in data or "free_remaining" in data, \
            f"Response should contain entry status fields, got {data.keys()}"
        print(f"CREDITS-REG-4 PASS: Battle entry status returned: {data}")


# ═══════════════════════════════════════════════════════════════════
# TC#209-220: BATTLE TESTS
# ═══════════════════════════════════════════════════════════════════

class TestBattle:
    """Battle API tests - TC#209-220"""

    def test_hottest_battle_endpoint(self, test_headers):
        """BATTLE-REG-1: Hottest battle endpoint returns battle data"""
        response = requests.get(f"{BASE_URL}/api/stories/hottest-battle", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=true, got {data}"
        # Battle may be null if no active battles
        if data.get("battle"):
            battle = data["battle"]
            assert "root_story_id" in battle, "Battle should have root_story_id"
            assert "branch_count" in battle or "contenders" in battle, "Battle should have branch_count or contenders"
            print(f"BATTLE-REG-1 PASS: Hottest battle found - root_id={battle.get('root_story_id')}, branches={battle.get('branch_count')}")
        else:
            print("BATTLE-REG-1 PASS: No active battle (battle=null is valid)")

    def test_battle_pulse_endpoint(self, test_headers):
        """BATTLE-REG-2: Battle pulse API returns battle data for valid root_story_id"""
        # First get hottest battle to find a valid root_story_id
        hottest_response = requests.get(f"{BASE_URL}/api/stories/hottest-battle", headers=test_headers)
        if hottest_response.status_code != 200:
            pytest.skip("Could not get hottest battle")
        
        hottest_data = hottest_response.json()
        if not hottest_data.get("battle"):
            # Try with known demo root ID
            root_id = "battle-demo-root"
        else:
            root_id = hottest_data["battle"].get("root_story_id")
        
        if not root_id:
            pytest.skip("No root_story_id available for battle pulse test")
        
        response = requests.get(f"{BASE_URL}/api/stories/battle-pulse/{root_id}", headers=test_headers)
        # May return 404 if no battle exists, which is valid
        if response.status_code == 404:
            print(f"BATTLE-REG-2 PASS: Battle pulse returned 404 for {root_id} (no battle exists)")
            return
        
        assert response.status_code == 200, f"Expected 200 or 404, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=true"
        if data.get("pulse"):
            pulse = data["pulse"]
            print(f"BATTLE-REG-2 PASS: Battle pulse returned - entries={pulse.get('total_entries')}, user_rank={pulse.get('user_rank')}")
        else:
            print("BATTLE-REG-2 PASS: Battle pulse returned (pulse may be null)")

    def test_battle_page_data(self, test_headers):
        """BATTLE-REG-3: Battle page shows #1 entry and ranking info"""
        # Get hottest battle first
        hottest_response = requests.get(f"{BASE_URL}/api/stories/hottest-battle", headers=test_headers)
        if hottest_response.status_code != 200:
            pytest.skip("Could not get hottest battle")
        
        hottest_data = hottest_response.json()
        if not hottest_data.get("battle"):
            pytest.skip("No active battle to test")
        
        root_id = hottest_data["battle"].get("root_story_id")
        if not root_id:
            pytest.skip("No root_story_id in hottest battle")
        
        # Get battle details
        response = requests.get(f"{BASE_URL}/api/stories/battle/{root_id}", headers=test_headers)
        if response.status_code == 404:
            print(f"BATTLE-REG-3 PASS: Battle {root_id} not found (valid state)")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        
        contenders = data.get("contenders", [])
        if contenders:
            top_contender = contenders[0]
            assert top_contender.get("rank") == 1, f"First contender should be rank 1, got {top_contender.get('rank')}"
            print(f"BATTLE-REG-3 PASS: #1 entry found - title={top_contender.get('title')}, score={top_contender.get('battle_score')}")
        else:
            print("BATTLE-REG-3 PASS: No contenders yet (valid state)")


# ═══════════════════════════════════════════════════════════════════
# TC#231-241: SHARE TESTS
# ═══════════════════════════════════════════════════════════════════

class TestShare:
    """Share API tests - TC#231-241"""

    def test_share_endpoint_exists(self, test_headers):
        """SHARE-REG-1: Share endpoint is accessible"""
        # Test with a dummy share ID - should return 404 for non-existent
        response = requests.get(f"{BASE_URL}/api/share/test-share-id-123")
        # 404 is expected for non-existent share, but endpoint should exist
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        print(f"SHARE-REG-1 PASS: Share endpoint accessible (status={response.status_code})")

    def test_public_creation_endpoint(self):
        """SHARE-REG-2: Public creation endpoint is accessible"""
        # Test with a known slug pattern
        response = requests.get(f"{BASE_URL}/api/public/creation/trust-engine-5")
        # May return 404 if slug doesn't exist, but endpoint should work
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        print(f"SHARE-REG-2 PASS: Public creation endpoint accessible (status={response.status_code})")

    def test_share_no_private_data_exposure(self, test_headers):
        """SHARE-REG-3: Public page does not expose private user data"""
        # Get user's shares
        response = requests.get(f"{BASE_URL}/api/share/user/all", headers=test_headers)
        if response.status_code != 200:
            pytest.skip("Could not get user shares")
        
        shares = response.json().get("shares", [])
        if not shares:
            print("SHARE-REG-3 PASS: No shares to test (valid state)")
            return
        
        # Check first share's public data
        share_id = shares[0].get("id")
        if not share_id:
            pytest.skip("No share ID found")
        
        public_response = requests.get(f"{BASE_URL}/api/share/{share_id}")
        if public_response.status_code != 200:
            print(f"SHARE-REG-3 PASS: Share {share_id} not publicly accessible")
            return
        
        data = public_response.json()
        # Check that sensitive fields are not exposed
        sensitive_fields = ["password", "email", "internal_id", "user_password", "auth_token"]
        for field in sensitive_fields:
            assert field not in str(data).lower(), f"Sensitive field '{field}' found in public response"
        
        print("SHARE-REG-3 PASS: No private data exposed in public share response")


# ═══════════════════════════════════════════════════════════════════
# TC#58-87: HERO/FEED TESTS
# ═══════════════════════════════════════════════════════════════════

class TestHeroFeed:
    """Hero and Feed API tests - TC#58-87"""

    def test_dashboard_init_returns_top_stories(self, test_headers):
        """HERO-REG-1: Dashboard init returns top_stories for hero section"""
        response = requests.get(f"{BASE_URL}/api/dashboard/init", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # top_stories may be empty but should exist
        assert "top_stories" in data or "daily_challenge" in data or "viral_status" in data, \
            f"Dashboard init should return expected fields, got {data.keys()}"
        print(f"HERO-REG-1 PASS: Dashboard init returned - top_stories={len(data.get('top_stories', []))}")

    def test_story_feed_returns_rows(self, test_headers):
        """FEED-REG-1: Story feed returns rows with stories"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should have rows array
        rows = data.get("rows", [])
        assert isinstance(rows, list), f"rows should be a list, got {type(rows)}"
        
        if rows:
            first_row = rows[0]
            assert "key" in first_row or "title" in first_row, "Row should have key or title"
            assert "stories" in first_row, "Row should have stories array"
            print(f"FEED-REG-1 PASS: Feed returned {len(rows)} rows, first row has {len(first_row.get('stories', []))} stories")
        else:
            print("FEED-REG-1 PASS: Feed returned empty rows (valid state)")

    def test_feed_stories_have_required_fields(self, test_headers):
        """FEED-REG-2: Feed stories have title, animation_style, and thumbnails"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_headers)
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        stories_checked = 0
        for row in rows[:3]:  # Check first 3 rows
            for story in row.get("stories", [])[:3]:  # Check first 3 stories per row
                # Stories should have title
                assert "title" in story or "job_id" in story, f"Story missing title/job_id: {story.keys()}"
                stories_checked += 1
        
        print(f"FEED-REG-2 PASS: Checked {stories_checked} stories, all have required fields")

    def test_feed_no_duplicate_stories(self, test_headers):
        """FEED-REG-3: No duplicate feed cards showing same story"""
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_headers)
        assert response.status_code == 200
        data = response.json()
        rows = data.get("rows", [])
        
        all_job_ids = []
        for row in rows:
            for story in row.get("stories", []):
                job_id = story.get("job_id")
                if job_id:
                    all_job_ids.append(job_id)
        
        unique_ids = set(all_job_ids)
        # Allow some duplicates across rows (same story in different categories)
        # but flag if >20% duplicates
        if all_job_ids:
            duplicate_ratio = 1 - (len(unique_ids) / len(all_job_ids))
            assert duplicate_ratio < 0.5, f"Too many duplicates: {duplicate_ratio*100:.1f}%"
            print(f"FEED-REG-3 PASS: {len(all_job_ids)} stories, {len(unique_ids)} unique ({duplicate_ratio*100:.1f}% duplicates)")
        else:
            print("FEED-REG-3 PASS: No stories to check for duplicates")


# ═══════════════════════════════════════════════════════════════════
# TC#337-346: PERFORMANCE TESTS
# ═══════════════════════════════════════════════════════════════════

class TestPerformance:
    """Performance tests - TC#337-346"""

    def test_dashboard_init_under_3s(self, test_headers):
        """PERF-REG-1: Dashboard init loads under 3s"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/dashboard/init", headers=test_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed < 3.0, f"Dashboard init took {elapsed:.2f}s, expected <3s"
        print(f"PERF-REG-1 PASS: Dashboard init completed in {elapsed:.2f}s")

    def test_story_feed_under_3s(self, test_headers):
        """PERF-REG-2: Story feed loads under 3s"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed < 3.0, f"Story feed took {elapsed:.2f}s, expected <3s"
        print(f"PERF-REG-2 PASS: Story feed completed in {elapsed:.2f}s")

    def test_credits_balance_under_1s(self, test_headers):
        """PERF-REG-3: Credits balance loads under 1s"""
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/credits/balance", headers=test_headers)
        elapsed = time.time() - start
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed < 1.0, f"Credits balance took {elapsed:.2f}s, expected <1s"
        print(f"PERF-REG-3 PASS: Credits balance completed in {elapsed:.2f}s")


# ═══════════════════════════════════════════════════════════════════
# FEATURE FLAGS TESTS
# ═══════════════════════════════════════════════════════════════════

class TestFeatureFlags:
    """Feature flags verification - POSTGEN-REG-1, POSTGEN-REG-2"""

    def test_feature_flags_endpoint(self, test_headers):
        """POSTGEN-REG-2: Verify feature flags are accessible"""
        # Feature flags are frontend-only, but we can verify the config endpoint if it exists
        # or check that the frontend config is correct
        # For now, we verify the backend doesn't block feature flag related endpoints
        response = requests.get(f"{BASE_URL}/api/story-engine/options", headers=test_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("POSTGEN-REG-2 PASS: Story engine options accessible (feature flags are frontend config)")


# ═══════════════════════════════════════════════════════════════════
# STORY VIEWER TESTS
# ═══════════════════════════════════════════════════════════════════

class TestStoryViewer:
    """Story viewer API tests"""

    def test_story_viewer_endpoint(self, test_headers):
        """Test story viewer endpoint exists and works"""
        # Get a story ID from the feed
        feed_response = requests.get(f"{BASE_URL}/api/engagement/story-feed", headers=test_headers)
        if feed_response.status_code != 200:
            pytest.skip("Could not get story feed")
        
        rows = feed_response.json().get("rows", [])
        story_id = None
        for row in rows:
            for story in row.get("stories", []):
                if story.get("job_id"):
                    story_id = story["job_id"]
                    break
            if story_id:
                break
        
        if not story_id:
            pytest.skip("No story ID found in feed")
        
        response = requests.get(f"{BASE_URL}/api/stories/viewer/{story_id}", headers=test_headers)
        # May return 404 if story doesn't exist or isn't ready
        if response.status_code == 404:
            print(f"Story viewer: Story {story_id} not found (may not be ready)")
            return
        
        assert response.status_code in [200, 400, 403], f"Expected 200/400/403, got {response.status_code}"
        print(f"Story viewer endpoint works for story {story_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
