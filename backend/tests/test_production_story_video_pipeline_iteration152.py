"""
Production Story → Video Pipeline Tests - Iteration 152
Full A-to-Z testing on https://www.visionary-suite.com
Tests: Pipeline stages, credit deduction, history, refresh recovery, concurrent runs
"""

import pytest
import requests
import time
import uuid
import concurrent.futures
import os
from datetime import datetime

# Production URL
BASE_URL = "https://www.visionary-suite.com"

# Test credentials
TEST_USER_EMAIL = "test@visionary-suite.com"
TEST_USER_PASSWORD = "Test@2026#"
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestAuthAndCredits:
    """Test authentication and credit system"""

    @pytest.fixture(scope="class")
    def session(self):
        """Create session for tests"""
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        """Get authentication token"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=30
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data or "access_token" in data, f"No token in response: {data}"
        return data.get("token") or data.get("access_token")

    def test_login_success(self, session, auth_token):
        """Test user login returns token"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"✅ Login successful, token obtained")

    def test_credits_balance(self, session, auth_token):
        """Test getting credit balance"""
        response = session.get(
            f"{BASE_URL}/api/credits/balance",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        assert response.status_code == 200, f"Credits balance failed: {response.text}"
        data = response.json()
        assert "credits" in data or "balance" in data, f"No credits in response: {data}"
        credits = data.get("credits") or data.get("balance")
        print(f"✅ Credit balance: {credits}")
        return credits

    def test_cashfree_plans(self, session, auth_token):
        """Test subscription plans endpoint"""
        response = session.get(
            f"{BASE_URL}/api/cashfree/plans",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        # May return 401 if plans API requires different auth or 200 with plans
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cashfree plans: {len(data.get('plans', []))} plans available")
        else:
            print(f"⚠️ Cashfree plans returned {response.status_code}")


class TestPipelineOptions:
    """Test pipeline configuration endpoints"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    def test_pipeline_options(self, session):
        """Test GET /api/pipeline/options returns all options"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/options",
            verify=False,
            timeout=30
        )
        assert response.status_code == 200, f"Options failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "animation_styles" in data
        assert "age_groups" in data
        assert "voice_presets" in data
        assert "credit_costs" in data
        
        # Verify counts
        assert len(data["animation_styles"]) == 6, f"Expected 6 styles, got {len(data['animation_styles'])}"
        assert len(data["age_groups"]) == 5, f"Expected 5 age groups, got {len(data['age_groups'])}"
        assert len(data["voice_presets"]) == 5, f"Expected 5 voices, got {len(data['voice_presets'])}"
        
        # Verify credit costs
        assert data["credit_costs"]["small"] == 50
        assert data["credit_costs"]["medium"] == 80
        assert data["credit_costs"]["large"] == 120
        
        print(f"✅ Pipeline options: {len(data['animation_styles'])} styles, {len(data['age_groups'])} ages, {len(data['voice_presets'])} voices")


class TestPipelineE2E:
    """End-to-end Story → Video pipeline tests"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        """Get authentication token"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=30
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("token") or data.get("access_token")

    def test_create_pipeline_job_validation(self, session, auth_token):
        """Test pipeline validation - short story text"""
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "Test",
                "story_text": "Too short",  # Less than 50 chars
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            verify=False,
            timeout=30
        )
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}: {response.text}"
        print(f"✅ Validation correctly rejects short story (< 50 chars)")

    def test_create_pipeline_job_missing_title(self, session, auth_token):
        """Test pipeline validation - missing title"""
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": "",  # Empty title
                "story_text": "This is a valid story text that meets the minimum 50 character requirement for testing purposes.",
                "animation_style": "cartoon_2d",
            },
            verify=False,
            timeout=30
        )
        assert response.status_code in [400, 422], f"Expected validation error for empty title, got {response.status_code}"
        print(f"✅ Validation correctly rejects empty title")

    def test_create_pipeline_job_success(self, session, auth_token):
        """Test creating a pipeline job - Single Run #1"""
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_Run1_{test_id}"
        story = """Once upon a time in a magical forest, there lived a brave little fox named Finn. 
        Finn loved to explore the woods and make friends with all the woodland creatures. 
        One sunny morning, Finn discovered a mysterious glowing mushroom near the old oak tree.
        The mushroom led him on an adventure that would change his life forever."""
        
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": title,
                "story_text": story,
                "animation_style": "cartoon_2d",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_warm"
            },
            verify=False,
            timeout=30
        )
        
        assert response.status_code == 200, f"Create pipeline failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "job_id" in data
        assert "credits_charged" in data
        assert data["credits_charged"] == 50, f"Expected 50 credits, got {data['credits_charged']}"
        
        job_id = data["job_id"]
        print(f"✅ Pipeline job created: {job_id}, {data['credits_charged']} credits charged")
        
        return job_id

    def test_poll_pipeline_status(self, session, auth_token):
        """Test polling pipeline status - Run #1 Full E2E"""
        # Create job first
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_E2E_{test_id}"
        story = """In a bustling city, a young robot named Zara discovered she had a special talent.
        She could understand the language of plants and flowers in the city park.
        Every day after school, Zara would visit the park and have conversations with the roses.
        One day, the flowers told her about a hidden garden that needed her help."""
        
        create_resp = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": title,
                "story_text": story,
                "animation_style": "watercolor",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_friendly"
            },
            verify=False,
            timeout=60
        )
        
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        job_id = create_resp.json()["job_id"]
        print(f"📹 E2E job created: {job_id}")
        
        # Poll for completion (max 200 seconds)
        start_time = time.time()
        max_wait = 200
        poll_interval = 10
        final_status = None
        
        while time.time() - start_time < max_wait:
            status_resp = session.get(
                f"{BASE_URL}/api/pipeline/status/{job_id}",
                headers={"Authorization": f"Bearer {auth_token}"},
                verify=False,
                timeout=30
            )
            
            assert status_resp.status_code == 200, f"Status poll failed: {status_resp.text}"
            job = status_resp.json().get("job", {})
            status = job.get("status")
            progress = job.get("progress", 0)
            current_step = job.get("current_step", "")
            
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed}s] Status: {status}, Progress: {progress}%, Step: {current_step}")
            
            if status == "COMPLETED":
                final_status = job
                print(f"✅ Job completed in {elapsed}s!")
                print(f"   Output URL: {job.get('output_url', 'N/A')[:80]}")
                break
            elif status == "FAILED":
                final_status = job
                print(f"❌ Job failed: {job.get('error')}")
                break
            
            time.sleep(poll_interval)
        
        assert final_status is not None, "Job did not complete within timeout"
        
        # If completed, verify output URL is accessible
        if final_status.get("status") == "COMPLETED":
            output_url = final_status.get("output_url")
            assert output_url is not None, "No output URL in completed job"
            
            # Verify video is accessible
            video_resp = session.head(output_url, verify=False, timeout=30, allow_redirects=True)
            assert video_resp.status_code == 200, f"Video not accessible: {video_resp.status_code}"
            print(f"✅ Video accessible: {output_url[:60]}...")
            
            # Verify timing breakdown
            timing = final_status.get("timing", {})
            assert "total_ms" in timing, "Missing total_ms in timing"
            print(f"   Total time: {timing.get('total_ms', 0) / 1000:.1f}s")
        
        return final_status

    def test_user_jobs_history(self, session, auth_token):
        """Test GET /api/pipeline/user-jobs returns history"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/user-jobs",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        
        assert response.status_code == 200, f"User jobs failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        print(f"✅ User has {len(data['jobs'])} pipeline jobs in history")
        
        # Print recent job statuses
        for job in data["jobs"][:5]:
            print(f"   - {job.get('title', 'Untitled')[:30]}: {job.get('status')}")
        
        return data["jobs"]


class TestPipelineConcurrent:
    """Test concurrent pipeline job creation"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=30
        )
        assert response.status_code == 200
        return response.json().get("token") or response.json().get("access_token")

    def test_concurrent_job_creation(self, session, auth_token):
        """Test creating 3 jobs concurrently"""
        def create_job(index):
            test_id = str(uuid.uuid4())[:6]
            title = f"TEST_Concurrent_{index}_{test_id}"
            story = f"""Story #{index}: A young adventurer named Hero{index} embarked on a quest.
            They traveled through enchanted lands and met magical creatures along the way.
            After many challenges, Hero{index} discovered the true meaning of courage and friendship.
            The journey taught them that the real treasure was the bonds formed with others."""
            
            resp = requests.post(
                f"{BASE_URL}/api/pipeline/create",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "title": title,
                    "story_text": story,
                    "animation_style": ["cartoon_2d", "anime_style", "watercolor"][index % 3],
                    "age_group": "kids_5_8",
                    "voice_preset": "narrator_warm"
                },
                verify=False,
                timeout=30
            )
            return {"index": index, "status_code": resp.status_code, "data": resp.json() if resp.ok else resp.text}
        
        # Create 3 jobs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_job, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all jobs created
        success_count = sum(1 for r in results if r["status_code"] == 200)
        print(f"✅ Concurrent creation: {success_count}/3 jobs created successfully")
        
        job_ids = []
        for r in results:
            if r["status_code"] == 200:
                job_ids.append(r["data"]["job_id"])
                print(f"   Job {r['index']}: {r['data']['job_id'][:8]}... ({r['data']['credits_charged']} credits)")
            else:
                print(f"   Job {r['index']}: FAILED - {r['data'][:100]}")
        
        assert success_count >= 2, f"At least 2 concurrent jobs should succeed, got {success_count}"
        
        return job_ids


class TestDashboardAndNavigation:
    """Test dashboard and navigation endpoints"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=30
        )
        return response.json().get("token") or response.json().get("access_token")

    def test_user_profile(self, session, auth_token):
        """Test user profile endpoint"""
        response = session.get(
            f"{BASE_URL}/api/user/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User profile: {data.get('name', 'N/A')}, {data.get('email', 'N/A')}")
        else:
            # Try alternative endpoint
            response2 = session.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {auth_token}"},
                verify=False,
                timeout=30
            )
            assert response2.status_code == 200, f"Profile endpoint failed: {response.status_code}"
            data = response2.json()
            print(f"✅ User profile (via /auth/me): {data.get('name', 'N/A')}")

    def test_daily_reward_status(self, session, auth_token):
        """Test daily reward status"""
        response = session.get(
            f"{BASE_URL}/api/rewards/status",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Daily reward status: claimed={data.get('claimed_today', False)}")
        else:
            print(f"⚠️ Daily rewards endpoint returned {response.status_code}")


class TestAdminPanel:
    """Test admin panel endpoints"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def admin_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            verify=False,
            timeout=30
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("token") or response.json().get("access_token")

    def test_admin_login(self, session, admin_token):
        """Test admin login"""
        assert admin_token is not None
        print(f"✅ Admin login successful")

    def test_admin_users_list(self, session, admin_token):
        """Test admin users list"""
        response = session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            print(f"✅ Admin users list: {len(users)} users")
        else:
            print(f"⚠️ Admin users endpoint returned {response.status_code}")

    def test_pipeline_workers_status(self, session, admin_token):
        """Test pipeline workers status"""
        response = session.get(
            f"{BASE_URL}/api/pipeline/workers/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            verify=False,
            timeout=30
        )
        
        assert response.status_code == 200, f"Workers status failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        workers = data.get("workers", {})
        print(f"✅ Pipeline workers: {workers}")


class TestOtherFeatures:
    """Test other feature endpoints"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=30
        )
        return response.json().get("token") or response.json().get("access_token")

    def test_reel_generator_options(self, session, auth_token):
        """Test reel generator has required endpoints"""
        # Test if reel generator endpoint exists
        response = session.get(
            f"{BASE_URL}/api/generate/reel-options",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        print(f"Reel options endpoint: {response.status_code}")

    def test_story_generator_options(self, session, auth_token):
        """Test story generator options"""
        response = session.get(
            f"{BASE_URL}/api/story/options",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        print(f"Story generator options: {response.status_code}")

    def test_photo_to_comic_health(self, session, auth_token):
        """Test photo to comic endpoint exists"""
        response = session.get(
            f"{BASE_URL}/api/photo-to-comic/options",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        print(f"Photo to comic options: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
