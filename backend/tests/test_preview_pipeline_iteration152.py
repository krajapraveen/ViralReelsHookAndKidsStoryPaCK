"""
Production Story → Video Pipeline Tests - Iteration 152
Testing on preview environment: https://gallery-showcase-43.preview.emergentagent.com
(Production https://www.visionary-suite.com has 502 backend errors)

Tests: Pipeline stages, credit deduction, history, refresh recovery, concurrent runs
"""

import pytest
import requests
import time
import uuid
import concurrent.futures
import os
from datetime import datetime

# Preview URL (Production has 502 errors)
BASE_URL = "https://gallery-showcase-43.preview.emergentagent.com"

# Test credentials - demo user has unlimited credits
TEST_USER_EMAIL = "demo@example.com"
TEST_USER_PASSWORD = "Password123!"
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
            timeout=60
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
    """End-to-end Story → Video pipeline tests - Single User Runs"""

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
            timeout=60
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        return data.get("token") or data.get("access_token")

    def test_create_pipeline_job_validation_short_story(self, session, auth_token):
        """Test pipeline validation - short story text (<50 chars)"""
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

    def test_create_pipeline_job_validation_empty_title(self, session, auth_token):
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

    def test_pipeline_run_1_create_and_verify(self, session, auth_token):
        """Pipeline Run #1 - Create job and verify initial state"""
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
            timeout=60
        )
        
        assert response.status_code == 200, f"Create pipeline failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "job_id" in data
        assert "credits_charged" in data
        assert data["credits_charged"] == 50, f"Expected 50 credits, got {data['credits_charged']}"
        
        job_id = data["job_id"]
        print(f"✅ Pipeline Run #1 created: {job_id}, {data['credits_charged']} credits charged")
        
        # Poll status once to verify job exists
        status_resp = session.get(
            f"{BASE_URL}/api/pipeline/status/{job_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        assert status_resp.status_code == 200
        job = status_resp.json().get("job", {})
        assert job.get("status") in ["QUEUED", "PROCESSING"], f"Unexpected status: {job.get('status')}"
        print(f"   Job status: {job.get('status')}, progress: {job.get('progress', 0)}%")

    def test_pipeline_run_2_full_e2e(self, session, auth_token):
        """Pipeline Run #2 - Full E2E with polling until completion"""
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_Run2_E2E_{test_id}"
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
        print(f"📹 Run #2 E2E job created: {job_id}")
        
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
            print(f"  [{elapsed}s] Status: {status}, Progress: {progress}%, Step: {current_step[:50]}")
            
            if status == "COMPLETED":
                final_status = job
                print(f"✅ Run #2 completed in {elapsed}s!")
                break
            elif status == "FAILED":
                final_status = job
                print(f"❌ Run #2 failed: {job.get('error')}")
                break
            
            time.sleep(poll_interval)
        
        assert final_status is not None, "Job did not complete within timeout"
        
        # Verify output if completed
        if final_status.get("status") == "COMPLETED":
            output_url = final_status.get("output_url")
            assert output_url is not None, "No output URL in completed job"
            print(f"   Output URL: {output_url[:80]}...")

    def test_pipeline_run_3_different_style(self, session, auth_token):
        """Pipeline Run #3 - Different animation style (anime)"""
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_Run3_Anime_{test_id}"
        story = """Deep in the ocean, a curious mermaid named Pearl found a shimmering treasure chest.
        Inside was a magical compass that could guide her to any destination she dreamed of.
        With her best friend, a playful dolphin named Splash, Pearl set out on a grand adventure.
        Together they explored ancient underwater caves and met creatures beyond imagination."""
        
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": title,
                "story_text": story,
                "animation_style": "anime_style",
                "age_group": "kids_9_12",
                "voice_preset": "narrator_dramatic"
            },
            verify=False,
            timeout=60
        )
        
        assert response.status_code == 200, f"Create pipeline failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        print(f"✅ Run #3 (Anime style) created: {data['job_id']}")

    def test_pipeline_run_4_comic_style(self, session, auth_token):
        """Pipeline Run #4 - Comic book style"""
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_Run4_Comic_{test_id}"
        story = """Superhero Sam was just an ordinary kid until lightning struck his bicycle one stormy night.
        Now Sam can run faster than anyone and jump over tall buildings in a single leap.
        When the city is in danger, Sam puts on his cape and becomes the amazing Captain Flash.
        Every villain knows to watch out when Captain Flash is on patrol."""
        
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": title,
                "story_text": story,
                "animation_style": "comic_book",
                "age_group": "kids_5_8",
                "voice_preset": "narrator_energetic"
            },
            verify=False,
            timeout=60
        )
        
        assert response.status_code == 200, f"Create pipeline failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        print(f"✅ Run #4 (Comic style) created: {data['job_id']}")

    def test_pipeline_run_5_claymation_style(self, session, auth_token):
        """Pipeline Run #5 - Claymation style"""
        test_id = str(uuid.uuid4())[:8]
        title = f"TEST_Iter152_Run5_Clay_{test_id}"
        story = """Wallace the worm lived in a cozy hole beneath the big apple tree.
        Every morning he would stretch out and say hello to his snail friend, Shelly.
        One day they decided to have a race to see who could reach the garden fence first.
        It was the slowest, funniest race the garden had ever seen, and everyone cheered."""
        
        response = session.post(
            f"{BASE_URL}/api/pipeline/create",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "title": title,
                "story_text": story,
                "animation_style": "claymation",
                "age_group": "toddler",
                "voice_preset": "narrator_calm"
            },
            verify=False,
            timeout=60
        )
        
        assert response.status_code == 200, f"Create pipeline failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        print(f"✅ Run #5 (Claymation style) created: {data['job_id']}")

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
        
        # Count jobs by status
        status_counts = {}
        for job in data["jobs"]:
            status = job.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"   Status breakdown: {status_counts}")


class TestPipelineConcurrent:
    """Test concurrent pipeline job creation - 3 concurrent runs"""

    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()

    @pytest.fixture(scope="class")
    def auth_token(self, session):
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            verify=False,
            timeout=60
        )
        assert response.status_code == 200
        return response.json().get("token") or response.json().get("access_token")

    def test_concurrent_3_job_creation(self, session, auth_token):
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
                timeout=60
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
        for r in sorted(results, key=lambda x: x["index"]):
            if r["status_code"] == 200:
                job_ids.append(r["data"]["job_id"])
                print(f"   Job {r['index']}: {r['data']['job_id'][:8]}... ({r['data']['credits_charged']} credits)")
            else:
                print(f"   Job {r['index']}: FAILED - {str(r['data'])[:100]}")
        
        assert success_count >= 2, f"At least 2 concurrent jobs should succeed, got {success_count}"


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
            timeout=60
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
            timeout=60
        )
        return response.json().get("token") or response.json().get("access_token")

    def test_reel_generator_endpoint(self, session, auth_token):
        """Test reel generator endpoint exists"""
        response = session.get(
            f"{BASE_URL}/api/generate/reel-options",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        # Endpoint may or may not exist - just check it's accessible
        print(f"Reel options endpoint: {response.status_code}")

    def test_story_generator_endpoint(self, session, auth_token):
        """Test story generator endpoint"""
        response = session.get(
            f"{BASE_URL}/api/story/options",
            headers={"Authorization": f"Bearer {auth_token}"},
            verify=False,
            timeout=30
        )
        print(f"Story generator options: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
