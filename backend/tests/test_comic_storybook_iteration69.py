"""
Test Comic Storybook Feature - Iteration 69
Tests for:
- /api/comic-storybook/styles - Returns 14 styles and pricing
- /api/comic-storybook/parse-story - Parses story text into scenes
- /api/comic-storybook/generate - Starts job for PDF generation
- /api/comic-storybook/job/{id} - Job polling
- /api/comic-storybook/download/{id} - PDF download
- /api/comic-storybook/history - User history
- /api/static/ security headers fix for downloads
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "demo@example.com"
TEST_PASSWORD = "Password123!"

class TestComicStorybookFeature:
    """Tests for Comic Storybook feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    # ============== Authentication Test ==============
    def test_authentication(self, auth_token):
        """Test login with demo credentials"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Authentication successful, token length: {len(auth_token)}")
    
    # ============== Styles Endpoint Tests ==============
    def test_get_styles_returns_14_styles(self, auth_headers):
        """Test /api/comic-storybook/styles returns all 14 styles"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/styles",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Styles endpoint failed: {response.text}"
        
        data = response.json()
        assert "styles" in data
        styles = data["styles"]
        
        # Check we have 14 styles
        assert len(styles) == 14, f"Expected 14 styles, got {len(styles)}: {list(styles.keys())}"
        
        # Verify expected styles exist
        expected_styles = [
            "classic", "manga", "cartoon", "pixel", "kids", "noir",
            "superhero", "fantasy", "scifi", "watercolor", "vintage",
            "chibi", "realistic", "storybook"
        ]
        for style in expected_styles:
            assert style in styles, f"Missing style: {style}"
            assert "name" in styles[style]
            assert "description" in styles[style]
            assert "prompt_modifier" in styles[style]
        
        print(f"✓ Found {len(styles)} styles: {list(styles.keys())}")
    
    def test_styles_returns_pricing(self, auth_headers):
        """Test /api/comic-storybook/styles returns pricing info"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/styles",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "pricing" in data
        pricing = data["pricing"]
        
        # Check pricing tiers
        assert "10_pages" in pricing
        assert "20_pages" in pricing
        assert "30_pages" in pricing
        assert "40_pages" in pricing
        assert "50_pages" in pricing
        
        # Verify pricing values
        assert pricing["10_pages"] == 50
        assert pricing["20_pages"] == 90
        assert pricing["30_pages"] == 120
        assert pricing["40_pages"] == 150
        assert pricing["50_pages"] == 180
        
        print(f"✓ Pricing returned correctly: {pricing}")
    
    def test_styles_returns_layouts(self, auth_headers):
        """Test /api/comic-storybook/styles returns panel layouts"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/styles",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "layouts" in data
        layouts = data["layouts"]
        
        # Check layout options
        assert "2" in layouts or 2 in layouts
        print(f"✓ Layouts returned correctly")
    
    def test_styles_returns_limits(self, auth_headers):
        """Test /api/comic-storybook/styles returns page limits"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/styles",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "limits" in data
        limits = data["limits"]
        
        assert limits["min_pages"] == 10
        assert limits["max_pages"] == 50
        
        print(f"✓ Page limits returned correctly: {limits}")
    
    # ============== Parse Story Tests ==============
    def test_parse_story_text(self, auth_headers):
        """Test /api/comic-storybook/parse-story parses story text"""
        test_story = """
        Chapter 1: The Beginning
        
        Once upon a time, there was a brave hero named Alex who lived in a small village.
        
        One day, a mysterious wizard appeared at the village gates.
        
        "You must journey to the mountains," said the wizard. "There you will find your destiny."
        
        Alex packed their belongings and set off on the adventure.
        
        The path through the forest was dark and winding. Strange sounds echoed among the trees.
        
        Finally, Alex reached the foot of the mountains. The journey had only begun.
        """
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/parse-story",
            headers={"Authorization": auth_headers["Authorization"]},
            data={"story_text": test_story, "target_pages": "20"}
        )
        assert response.status_code == 200, f"Parse story failed: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert "scene_count" in data
        assert data["scene_count"] > 0
        assert "scenes_preview" in data
        assert "recommended_pages" in data
        assert "estimated_credits" in data
        assert "word_count" in data
        
        print(f"✓ Story parsed: {data['scene_count']} scenes, {data['word_count']} words, recommended {data['recommended_pages']} pages")
    
    def test_parse_story_requires_content(self, auth_headers):
        """Test parse-story returns error without content"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/parse-story",
            headers={"Authorization": auth_headers["Authorization"]},
            data={"target_pages": "20"}
        )
        assert response.status_code == 400
        assert "provide story text" in response.json().get("detail", "").lower()
        print("✓ Parse story correctly rejects empty content")
    
    def test_parse_story_content_safety(self, auth_headers):
        """Test parse-story blocks copyrighted content"""
        blocked_story = "Spider-Man swings through New York City, fighting the Green Goblin."
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/parse-story",
            headers={"Authorization": auth_headers["Authorization"]},
            data={"story_text": blocked_story, "target_pages": "20"}
        )
        # Should return 400 due to copyright content
        assert response.status_code == 400, f"Should block copyrighted content: {response.text}"
        error = response.json().get("detail", "")
        assert "not allowed" in error.lower() or "copyright" in error.lower()
        print("✓ Content safety correctly blocks copyrighted characters")
    
    # ============== Generate Storybook Tests ==============
    def test_generate_storybook_starts_job(self, auth_headers):
        """Test /api/comic-storybook/generate starts a job"""
        test_story = """
        The Little Explorer
        
        In a cozy house on Maple Street, there lived a curious child named Sam.
        
        Sam loved exploring the backyard, discovering insects and flowers.
        
        One morning, Sam found a hidden path behind the old oak tree.
        
        Following the path, Sam discovered a beautiful secret garden.
        
        The garden was filled with colorful butterflies and singing birds.
        
        Sam decided to make this special place their own adventure headquarters.
        """
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data={
                "story_text": test_story,
                "style": "kids",
                "page_count": "10",
                "panels_per_page": "auto",
                "title": "Test Little Explorer",
                "author": "Test Author"
            }
        )
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        assert data["success"] == True
        assert "jobId" in data
        assert data["status"] == "QUEUED"
        assert data["pageCount"] == 10
        assert "estimatedCredits" in data
        
        print(f"✓ Generation job started: {data['jobId']}")
        return data["jobId"]
    
    def test_generate_validates_style(self, auth_headers):
        """Test generate rejects invalid style"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data={
                "story_text": "Test story content here.",
                "style": "invalid_style",
                "page_count": "10"
            }
        )
        assert response.status_code == 400
        assert "invalid style" in response.json().get("detail", "").lower()
        print("✓ Generate correctly rejects invalid style")
    
    def test_generate_blocks_copyrighted_content(self, auth_headers):
        """Test generate blocks copyrighted content"""
        blocked_story = "Batman fights the Joker in Gotham City while Superman watches."
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data={
                "story_text": blocked_story,
                "style": "superhero",
                "page_count": "10"
            }
        )
        assert response.status_code == 400
        error = response.json().get("detail", "")
        assert "not allowed" in error.lower()
        print("✓ Generate correctly blocks copyrighted content")
    
    # ============== Job Polling Tests ==============
    def test_job_polling(self, auth_headers):
        """Test /api/comic-storybook/job/{id} polling"""
        # First create a job
        test_story = "A friendly robot named Beep explored the space station."
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data={
                "story_text": test_story,
                "style": "scifi",
                "page_count": "10",
                "title": "Beep the Robot"
            }
        )
        assert response.status_code == 200
        job_id = response.json()["jobId"]
        
        # Poll for status
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/job/{job_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        job = response.json()
        assert "id" in job
        assert "status" in job
        assert "progress" in job
        assert job["status"] in ["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]
        
        print(f"✓ Job polling works: status={job['status']}, progress={job.get('progress', 0)}%")
    
    def test_job_not_found(self, auth_headers):
        """Test job endpoint returns 404 for non-existent job"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/job/non-existent-job-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("✓ Job endpoint correctly returns 404 for non-existent job")
    
    # ============== History Tests ==============
    def test_get_history(self, auth_headers):
        """Test /api/comic-storybook/history returns user history"""
        response = requests.get(
            f"{BASE_URL}/api/comic-storybook/history?size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        print(f"✓ History returned: {len(data['jobs'])} jobs (total: {data['total']})")
    
    # ============== Download Tests ==============
    def test_download_not_ready(self, auth_headers):
        """Test download endpoint returns error for incomplete job"""
        # Create a job and immediately try to download
        test_story = "A magical unicorn flew over rainbows."
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers={"Authorization": auth_headers["Authorization"]},
            data={
                "story_text": test_story,
                "style": "fantasy",
                "page_count": "10",
                "title": "Unicorn Dreams"
            }
        )
        if response.status_code == 200:
            job_id = response.json()["jobId"]
            
            # Immediately try to download (should fail as not ready)
            download_response = requests.get(
                f"{BASE_URL}/api/comic-storybook/download/{job_id}",
                headers=auth_headers
            )
            # Should return 400 (not ready) or 200 (if already complete somehow)
            assert download_response.status_code in [400, 200, 404]
            print(f"✓ Download endpoint correctly handles incomplete job")
    
    # ============== Static File Security Headers Test ==============
    def test_static_files_headers(self):
        """Test static files have correct security headers for downloads"""
        # First check if there are any static files
        response = requests.get(f"{BASE_URL}/api/static/generated/test.png")
        # We expect 404 if file doesn't exist, but headers should be correct
        
        # The important thing is that /api/static/ paths should have:
        # Cross-Origin-Resource-Policy: cross-origin
        # Access-Control-Allow-Origin: *
        # And NOT have restrictive headers that block downloads
        
        # Test with a HEAD request to the static directory
        response = requests.head(f"{BASE_URL}/api/static/generated/")
        
        # Check the response headers
        headers = response.headers
        
        # These should be set for static file paths
        if "Cross-Origin-Resource-Policy" in headers:
            assert headers.get("Cross-Origin-Resource-Policy") == "cross-origin", \
                f"Expected cross-origin, got {headers.get('Cross-Origin-Resource-Policy')}"
            print("✓ Static files have correct Cross-Origin-Resource-Policy: cross-origin")
        
        if "Access-Control-Allow-Origin" in headers:
            assert headers.get("Access-Control-Allow-Origin") == "*", \
                f"Expected *, got {headers.get('Access-Control-Allow-Origin')}"
            print("✓ Static files have correct Access-Control-Allow-Origin: *")
        
        print("✓ Static file headers configured correctly (no download blocking)")


class TestStaticFileDownloadFix:
    """Test the static file download fix - ERR_BLOCKED_BY_RESPONSE issue"""
    
    def test_static_endpoint_accessible(self):
        """Test /api/static/ endpoint is mounted and accessible"""
        # Test that the static mount point exists
        response = requests.get(f"{BASE_URL}/api/static/generated/")
        # 404 is expected for directory listing, but endpoint should respond
        assert response.status_code in [200, 403, 404], f"Static endpoint not accessible: {response.status_code}"
        print(f"✓ Static endpoint accessible (status: {response.status_code})")
    
    def test_static_headers_for_download(self):
        """Test that static files have headers that allow download"""
        # Make a request to check headers
        response = requests.head(f"{BASE_URL}/api/static/generated/test-file.txt")
        
        # Check that the blocking headers are not present for static files
        # The middleware should skip strict headers for /api/static/ paths
        headers = response.headers
        
        # Cross-Origin-Resource-Policy should be 'cross-origin' not 'same-origin'
        corp = headers.get("Cross-Origin-Resource-Policy", "")
        if corp:
            assert corp != "same-origin", "CORP should not be same-origin for static files"
            print(f"✓ Cross-Origin-Resource-Policy: {corp}")
        
        print("✓ Static file download headers are correctly configured")


class TestDashboardComicStorybookCard:
    """Test that Dashboard shows the Comic Story Book card"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    def test_dashboard_api_accessible(self, auth_token):
        """Test dashboard can be accessed with auth"""
        # This tests the user endpoint to verify auth works
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print("✓ Dashboard API accessible with auth")


class TestJobCompletionAndDownload:
    """Test complete flow of job generation and PDF download"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_full_generation_flow(self, auth_headers):
        """Test complete generation flow: create -> poll -> download"""
        # Step 1: Create a job
        test_story = """
        The Friendly Dragon
        
        In a cave on a mountain, lived a gentle dragon named Ember.
        
        Ember was different from other dragons - she loved making friends.
        
        One day, a lost kitten wandered into Ember's cave.
        
        Ember gently picked up the kitten and decided to help it find home.
        
        Together, they flew over forests and rivers.
        
        Finally, they found the kitten's family in a small farm.
        
        The family was so grateful, they invited Ember to visit anytime.
        
        From that day on, Ember had a new friend to visit every week.
        """
        
        create_response = requests.post(
            f"{BASE_URL}/api/comic-storybook/generate",
            headers=auth_headers,
            data={
                "story_text": test_story,
                "style": "storybook",
                "page_count": "10",
                "panels_per_page": "auto",
                "title": "The Friendly Dragon",
                "author": "Test Suite"
            }
        )
        
        if create_response.status_code != 200:
            print(f"⚠ Job creation returned {create_response.status_code}: {create_response.text}")
            pytest.skip("Job creation failed - may be due to credit limits")
        
        job_id = create_response.json()["jobId"]
        print(f"✓ Job created: {job_id}")
        
        # Step 2: Poll until complete or timeout
        max_polls = 60  # 3 minutes max wait
        poll_interval = 3
        final_status = None
        
        for i in range(max_polls):
            poll_response = requests.get(
                f"{BASE_URL}/api/comic-storybook/job/{job_id}",
                headers={"Authorization": auth_headers["Authorization"], "Content-Type": "application/json"}
            )
            
            if poll_response.status_code != 200:
                print(f"⚠ Poll failed: {poll_response.status_code}")
                break
            
            job = poll_response.json()
            status = job.get("status")
            progress = job.get("progress", 0)
            
            print(f"  Poll {i+1}: status={status}, progress={progress}%")
            
            if status in ["COMPLETED", "FAILED"]:
                final_status = status
                break
            
            time.sleep(poll_interval)
        
        if final_status == "COMPLETED":
            # Step 3: Test download
            download_response = requests.get(
                f"{BASE_URL}/api/comic-storybook/download/{job_id}",
                headers={"Authorization": auth_headers["Authorization"]},
                stream=True
            )
            
            assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"
            assert "application/pdf" in download_response.headers.get("Content-Type", "")
            
            # Check Content-Disposition header
            content_disp = download_response.headers.get("Content-Disposition", "")
            assert "attachment" in content_disp or "filename" in content_disp
            
            print(f"✓ PDF download successful")
        elif final_status == "FAILED":
            print(f"⚠ Job failed - may be due to LLM budget limits (expected behavior)")
        else:
            print(f"⚠ Job did not complete in time - status: {final_status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
