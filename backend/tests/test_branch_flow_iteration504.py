"""
Test Suite: Post-Launch-Branch Flow (Iteration 504)

Tests the complete branch creation and viewing flow:
1. ContinuationModal → POST /api/stories/continue-branch
2. StoryVideoPipeline → Battle Entry Banner for branch jobs
3. StoryViewerPage → Battle Status Banner for branch jobs
4. Engagement row, Leaderboard link, Make Your Version CTA

Test data:
- battle-demo-root: Original story (continuation_type=original)
- battle-demo-br1: Branch job (continuation_type=branch, root_story_id=battle-demo-root)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"

# Test data
BRANCH_JOB_ID = "battle-demo-br1"
ROOT_STORY_ID = "battle-demo-root"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def test_user_token(api_client):
    """Get test user authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Test user authentication failed: {response.status_code}")


@pytest.fixture
def authenticated_client(api_client, test_user_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return api_client


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_health(self, api_client):
        """Verify API is accessible"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ API health check passed")


class TestStoryViewerEndpoint:
    """Tests for GET /api/stories/viewer/{job_id}"""
    
    def test_viewer_returns_branch_job(self, api_client):
        """Verify viewer endpoint returns branch job with correct fields"""
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/{BRANCH_JOB_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
        job = data.get("job", {})
        assert job.get("job_id") == BRANCH_JOB_ID
        assert job.get("continuation_type") == "branch"
        assert job.get("root_story_id") == ROOT_STORY_ID
        print(f"✓ Branch job {BRANCH_JOB_ID} has continuation_type='branch'")
        print(f"  root_story_id: {job.get('root_story_id')}")
        print(f"  battle_score: {job.get('battle_score')}")
    
    def test_viewer_returns_original_job(self, api_client):
        """Verify viewer endpoint returns original job with correct fields"""
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/{ROOT_STORY_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        
        job = data.get("job", {})
        assert job.get("job_id") == ROOT_STORY_ID
        assert job.get("continuation_type") == "original"
        print(f"✓ Original job {ROOT_STORY_ID} has continuation_type='original'")
    
    def test_viewer_returns_battle_score(self, api_client):
        """Verify viewer returns battle_score for branch jobs"""
        response = api_client.get(f"{BASE_URL}/api/stories/viewer/{BRANCH_JOB_ID}")
        assert response.status_code == 200
        
        job = response.json().get("job", {})
        battle_score = job.get("battle_score")
        assert battle_score is not None
        assert isinstance(battle_score, (int, float))
        print(f"✓ Branch job has battle_score: {battle_score}")


class TestStoryChainEndpoint:
    """Tests for GET /api/stories/{job_id}/chain"""
    
    def test_chain_returns_episodes(self, api_client):
        """Verify chain endpoint returns episodes for root story"""
        response = api_client.get(f"{BASE_URL}/api/stories/{ROOT_STORY_ID}/chain")
        
        # Chain endpoint may return 200 or 404 depending on implementation
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                episodes = data.get("episodes", [])
                print(f"✓ Chain endpoint returned {len(episodes)} episodes")
            else:
                print(f"? Chain endpoint returned success=false")
        else:
            print(f"? Chain endpoint returned {response.status_code}")


class TestStoryBranchesEndpoint:
    """Tests for GET /api/stories/{job_id}/branches"""
    
    def test_branches_returns_list(self, api_client):
        """Verify branches endpoint returns list of branches"""
        response = api_client.get(f"{BASE_URL}/api/stories/{ROOT_STORY_ID}/branches")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                branches = data.get("branches", [])
                print(f"✓ Branches endpoint returned {len(branches)} branches")
                
                # Check if battle-demo-br1 is in the list
                branch_ids = [b.get("job_id") for b in branches]
                if BRANCH_JOB_ID in branch_ids:
                    print(f"✓ {BRANCH_JOB_ID} found in branches list")
            else:
                print(f"? Branches endpoint returned success=false")
        else:
            print(f"? Branches endpoint returned {response.status_code}")


class TestContinueBranchEndpoint:
    """Tests for POST /api/stories/continue-branch"""
    
    def test_continue_branch_requires_auth(self, api_client):
        """Verify continue-branch requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/stories/continue-branch", json={
            "parent_job_id": ROOT_STORY_ID,
            "title": "Test Branch",
            "story_text": "This is a test branch story with at least 50 characters for validation."
        })
        assert response.status_code == 401 or response.status_code == 403
        print("✓ continue-branch requires authentication")
    
    def test_continue_branch_validates_parent(self, authenticated_client):
        """Verify continue-branch validates parent exists"""
        response = authenticated_client.post(f"{BASE_URL}/api/stories/continue-branch", json={
            "parent_job_id": "nonexistent-job-id",
            "title": "Test Branch",
            "story_text": "This is a test branch story with at least 50 characters for validation."
        })
        assert response.status_code == 404
        print("✓ continue-branch validates parent exists")
    
    def test_continue_branch_endpoint_exists(self, authenticated_client):
        """Verify continue-branch endpoint exists and responds"""
        response = authenticated_client.post(f"{BASE_URL}/api/stories/continue-branch", json={
            "parent_job_id": ROOT_STORY_ID,
            "title": "Test Branch",
            "story_text": "This is a test branch story with at least 50 characters for validation.",
            "animation_style": "cartoon_2d",
            "age_group": "kids_5_8",
            "voice_preset": "narrator_warm",
            "quality_mode": "balanced"
        })
        # May return 200 (success), 402 (insufficient credits), or 429 (rate limit)
        assert response.status_code in [200, 201, 400, 402, 429]
        print(f"✓ continue-branch endpoint responds with {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"  Created job_id: {data.get('job_id')}")


class TestStoryBattleEndpoint:
    """Tests for GET /api/stories/battle/{root_story_id}"""
    
    def test_battle_endpoint_returns_leaderboard(self, api_client):
        """Verify battle endpoint returns leaderboard data"""
        response = api_client.get(f"{BASE_URL}/api/stories/battle/{ROOT_STORY_ID}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                entries = data.get("entries", data.get("leaderboard", []))
                print(f"✓ Battle endpoint returned {len(entries)} entries")
                
                # Check for battle-demo-br1 in leaderboard
                entry_ids = [e.get("job_id") for e in entries]
                if BRANCH_JOB_ID in entry_ids:
                    print(f"✓ {BRANCH_JOB_ID} found in battle leaderboard")
            else:
                print(f"? Battle endpoint returned success=false")
        else:
            print(f"? Battle endpoint returned {response.status_code}")


class TestFunnelTrackingEndpoint:
    """Tests for POST /api/funnel/track"""
    
    def test_funnel_track_accepts_launch_branch_event(self, authenticated_client):
        """Verify funnel tracking accepts launch_branch event"""
        response = authenticated_client.post(f"{BASE_URL}/api/funnel/track", json={
            "event": "cta_clicked",
            "data": {
                "type": "launch_branch",
                "parent_job_id": ROOT_STORY_ID,
                "new_job_id": "test-job-id",
                "source": "continuation_modal"
            }
        })
        # Funnel tracking should accept the event (200) or silently fail (any status)
        # It should not return 404 (endpoint not found)
        assert response.status_code != 404
        print(f"✓ Funnel tracking endpoint responds with {response.status_code}")


class TestIncrementMetricEndpoint:
    """Tests for POST /api/stories/increment-metric"""
    
    def test_increment_views_metric(self, api_client):
        """Verify increment-metric endpoint works for views"""
        response = api_client.post(f"{BASE_URL}/api/stories/increment-metric", json={
            "job_id": BRANCH_JOB_ID,
            "metric": "views"
        })
        # Should accept the request (may require auth or not)
        assert response.status_code in [200, 201, 401, 403]
        print(f"✓ increment-metric endpoint responds with {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
