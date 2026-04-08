"""
Test MySpace UX Overhaul and Backend Auth Fixes - Iteration 465

Tests:
1. Backend /api/story-video-studio/projects endpoint works with auth token
2. Backend /api/story-video-studio/generation/active-jobs endpoint works with auth token
3. Frontend MySpacePage.js has correct STATUS_COPY mapping
4. Frontend has ProgressTimeline component with 6 steps
5. Frontend has HowThisWorks component with 7 steps
6. Failed section header says 'Needs Attention' not 'Failed'
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trust-engine-5.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@visionary-suite.com"
TEST_PASSWORD = "Test@2026#"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


class TestBackendAuthEndpoints:
    """Test backend endpoints use proper auth (no test_user fallback)"""
    
    def test_projects_endpoint_requires_auth(self):
        """Test /api/story-video-studio/projects returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/projects")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ /api/story-video-studio/projects requires auth (returns 401 without token)")
    
    def test_projects_endpoint_with_auth(self, auth_token):
        """Test /api/story-video-studio/projects works with auth token"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/projects",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "projects" in data
        print(f"✅ /api/story-video-studio/projects works with auth - returned {len(data.get('projects', []))} projects")
    
    def test_active_jobs_endpoint_requires_auth(self):
        """Test /api/story-video-studio/generation/active-jobs returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/generation/active-jobs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ /api/story-video-studio/generation/active-jobs requires auth (returns 401 without token)")
    
    def test_active_jobs_endpoint_with_auth(self, auth_token):
        """Test /api/story-video-studio/generation/active-jobs works with auth token"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/generation/active-jobs",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "generation_jobs" in data
        assert "render_jobs" in data
        assert "total_active" in data
        print(f"✅ /api/story-video-studio/generation/active-jobs works with auth - {data.get('total_active', 0)} active jobs")
    
    def test_continue_video_endpoint_requires_auth(self):
        """Test /api/story-video-studio/continue-video returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/continue-video",
            json={"parent_project_id": "test", "story_text": "test story"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ /api/story-video-studio/continue-video requires auth (returns 401 without token)")
    
    def test_active_video_chains_endpoint_requires_auth(self):
        """Test /api/story-video-studio/active-video-chains returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/story-video-studio/active-video-chains")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ /api/story-video-studio/active-video-chains requires auth (returns 401 without token)")
    
    def test_active_video_chains_endpoint_with_auth(self, auth_token):
        """Test /api/story-video-studio/active-video-chains works with auth token"""
        response = requests.get(
            f"{BASE_URL}/api/story-video-studio/active-video-chains",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "chains" in data
        print(f"✅ /api/story-video-studio/active-video-chains works with auth - {len(data.get('chains', []))} chains")
    
    def test_upload_story_endpoint_requires_auth(self):
        """Test /api/story-video-studio/upload-story returns 401 without auth"""
        response = requests.post(
            f"{BASE_URL}/api/story-video-studio/upload-story",
            data={"language": "english", "age_group": "kids_5_8", "style_id": "storybook"}
        )
        # Should return 401 or 422 (missing file), but not 200
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"
        print(f"✅ /api/story-video-studio/upload-story requires auth (returns {response.status_code} without token)")


class TestFrontendCodeReview:
    """Verify frontend code has correct UX overhaul implementation"""
    
    def test_status_copy_mapping_exists(self):
        """Verify STATUS_COPY mapping has all required statuses"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for STATUS_COPY object
        assert "STATUS_COPY" in content, "STATUS_COPY mapping not found"
        
        # Check for all status keys
        statuses = ["QUEUED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"]
        for status in statuses:
            assert f'"{status}"' in content or f"'{status}'" in content or f"{status}:" in content, f"Status {status} not found in STATUS_COPY"
        
        print("✅ STATUS_COPY mapping has all required statuses")
    
    def test_plain_english_labels(self):
        """Verify plain-English status labels are used"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for plain-English labels
        labels = [
            "Waiting in line",
            "Creating your video",
            "Your video is ready",
            "Needs attention"
        ]
        
        for label in labels:
            assert label in content, f"Plain-English label '{label}' not found"
        
        print("✅ All plain-English status labels found")
    
    def test_info_sections_exist(self):
        """Verify 4 info sections exist: What this is, What's happening now, What you need to do, What happens next"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        info_sections = [
            "what_this_is",
            "whats_happening",
            "what_to_do",
            "what_next"
        ]
        
        for section in info_sections:
            assert section in content, f"Info section '{section}' not found"
        
        # Check for InfoSection component
        assert "InfoSection" in content, "InfoSection component not found"
        
        print("✅ All 4 info sections found in STATUS_COPY")
    
    def test_progress_timeline_component(self):
        """Verify ProgressTimeline component with 6 steps"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for ProgressTimeline component
        assert "ProgressTimeline" in content, "ProgressTimeline component not found"
        
        # Check for TIMELINE_STAGES
        assert "TIMELINE_STAGES" in content, "TIMELINE_STAGES not found"
        
        # Check for 6 stages
        stages = [
            "Story received",
            "Preparing your story",
            "Creating visuals",
            "Recording narration",
            "Building your video",
            "Ready"
        ]
        
        for stage in stages:
            assert stage in content, f"Timeline stage '{stage}' not found"
        
        print("✅ ProgressTimeline component with 6 stages found")
    
    def test_how_this_works_component(self):
        """Verify HowThisWorks component with 7 steps"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for HowThisWorks component
        assert "HowThisWorks" in content, "HowThisWorks component not found"
        
        # Check for 7 steps
        steps = [
            "You enter your story or idea",
            "We plan the scenes",
            "We generate visuals",
            "We create narration",
            "We build your video",
            "You preview and download",
            "You can regenerate improved versions"
        ]
        
        for step in steps:
            assert step in content, f"HowThisWorks step '{step}' not found"
        
        print("✅ HowThisWorks component with 7 steps found")
    
    def test_needs_attention_section_header(self):
        """Verify 'Needs Attention' is used instead of 'Failed' for section header"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for "Needs Attention" section header
        assert 'title="Needs Attention"' in content, "'Needs Attention' section header not found"
        
        # Verify "Failed" is not used as section header (but can be used as status key)
        # The section header should be "Needs Attention", not "Failed"
        assert 'title="Failed"' not in content, "'Failed' should not be used as section header"
        
        print("✅ 'Needs Attention' section header used instead of 'Failed'")
    
    def test_ctas_for_completed_cards(self):
        """Verify CTAs for completed cards: Preview, Download, Create Another Version, Share, Delete"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        ctas = [
            "preview-btn",
            "download-btn",
            "create-version-btn",
            "share-btn",
            "delete-btn"
        ]
        
        for cta in ctas:
            assert cta in content, f"CTA '{cta}' not found for completed cards"
        
        print("✅ All CTAs for completed cards found")
    
    def test_ctas_for_processing_cards(self):
        """Verify CTAs for processing cards: View Progress, Leave & come back later"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        ctas = [
            "view-progress-btn",
            "leave-btn"
        ]
        
        for cta in ctas:
            assert cta in content, f"CTA '{cta}' not found for processing cards"
        
        print("✅ All CTAs for processing cards found")
    
    def test_ctas_for_failed_cards(self):
        """Verify CTAs for failed cards: Retry, Edit & Retry, Delete"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        ctas = [
            "retry-btn",
            "edit-retry-btn"
        ]
        
        for cta in ctas:
            assert cta in content, f"CTA '{cta}' not found for failed cards"
        
        print("✅ All CTAs for failed cards found")
    
    def test_project_assets_section(self):
        """Verify Project Assets section with Script, Scenes, Voiceover, Final Video"""
        with open("/app/frontend/src/pages/MySpacePage.js", "r") as f:
            content = f.read()
        
        # Check for Project Assets section
        assert "Project Assets" in content, "Project Assets section not found"
        
        # Check for asset descriptions
        assets = [
            "Script",
            "Scenes",
            "Voiceover",
            "Final Video"
        ]
        
        for asset in assets:
            assert asset in content, f"Asset '{asset}' not found in Project Assets section"
        
        print("✅ Project Assets section with all 4 assets found")


class TestStoryVideoStudioRefreshResume:
    """Test refresh-safe resume logic in StoryVideoStudio.js"""
    
    def test_active_jobs_call_on_mount(self):
        """Verify StoryVideoStudio.js calls /active-jobs on mount"""
        with open("/app/frontend/src/pages/StoryVideoStudio.js", "r") as f:
            content = f.read()
        
        # Check for active-jobs API call
        assert "/api/story-video-studio/generation/active-jobs" in content, "active-jobs API call not found"
        
        # Check for resumeActiveJobs function
        assert "resumeActiveJobs" in content, "resumeActiveJobs function not found"
        
        print("✅ StoryVideoStudio.js calls /active-jobs on mount for refresh-safe resume")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
