"""
Content Seeding Engine API Tests - Iteration 333
Tests for AI-powered story generation with HOOK → BUILD → CLIFFHANGER format,
social media scripts, quality filtering, publishing, and admin controls.
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


class TestContentEngineAuth:
    """Test authentication and authorization for content engine endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in admin login response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Get test user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        assert response.status_code == 200, f"Test user login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in test user login response"
        return data["token"]
    
    def test_admin_login_success(self, admin_token):
        """Verify admin can login successfully"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")
    
    def test_test_user_login_success(self, test_user_token):
        """Verify test user can login successfully"""
        assert test_user_token is not None
        assert len(test_user_token) > 0
        print(f"✓ Test user login successful, token length: {len(test_user_token)}")


class TestContentEngineList:
    """Test GET /api/content-engine/list endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_list_stories_admin_success(self, admin_token):
        """Admin can list stories with stats"""
        response = requests.get(
            f"{BASE_URL}/api/content-engine/list",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"List failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "stories" in data
        assert "stats" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats
        assert "draft" in stats
        assert "published" in stats
        assert "featured" in stats
        assert "by_category" in stats
        
        print(f"✓ List stories successful - Total: {stats['total']}, Draft: {stats['draft']}, Published: {stats['published']}")
    
    def test_list_stories_with_category_filter(self, admin_token):
        """Admin can filter stories by category"""
        for category in ["emotional", "mystery", "kids", "horror", "viral"]:
            response = requests.get(
                f"{BASE_URL}/api/content-engine/list?category={category}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Filter by {category} failed: {response.text}"
            data = response.json()
            assert data.get("success") is True
            # All returned stories should match the category
            for story in data.get("stories", []):
                assert story.get("category") == category, f"Story category mismatch: {story.get('category')} != {category}"
        print("✓ Category filter working for all categories")
    
    def test_list_stories_with_status_filter(self, admin_token):
        """Admin can filter stories by status"""
        for status in ["draft", "published", "rejected"]:
            response = requests.get(
                f"{BASE_URL}/api/content-engine/list?status={status}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Filter by status {status} failed: {response.text}"
            data = response.json()
            assert data.get("success") is True
        print("✓ Status filter working for all statuses")
    
    def test_list_stories_with_tag_filter(self, admin_token):
        """Admin can filter stories by quality tag"""
        for tag in ["HIGH_VIRAL", "EMOTIONAL_HOOK", "FAST_CONVERSION"]:
            response = requests.get(
                f"{BASE_URL}/api/content-engine/list?tag={tag}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Filter by tag {tag} failed: {response.text}"
            data = response.json()
            assert data.get("success") is True
        print("✓ Tag filter working for all quality tags")
    
    def test_list_stories_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/content-engine/list",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on list endpoint")


class TestContentEngineGenerate:
    """Test POST /api/content-engine/generate endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_generate_stories_admin_success(self, admin_token):
        """Admin can generate stories via AI with quality filtering"""
        # Use small count (2) for faster testing
        response = requests.post(
            f"{BASE_URL}/api/content-engine/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "count": 2,
                "categories": ["viral"],
                "auto_publish": False
            },
            timeout=60  # AI generation can take time
        )
        assert response.status_code == 200, f"Generate failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "generated" in data
        assert "rejected" in data
        assert "stories" in data
        
        # Verify generated stories have required fields
        for story in data.get("stories", []):
            assert "story_id" in story
            assert "title" in story
            assert "story_text" in story
            assert "category" in story
            assert "quality_score" in story
            assert "quality_tags" in story
            assert "status" in story
            assert story["status"] == "draft"
        
        print(f"✓ Generate stories successful - Generated: {data['generated']}, Rejected: {data['rejected']}")
    
    def test_generate_stories_invalid_category(self, admin_token):
        """Generate with invalid category returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/generate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "count": 1,
                "categories": ["invalid_category"]
            },
            timeout=30
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Invalid category correctly returns 400")
    
    def test_generate_stories_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on generate endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/generate",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={"count": 1}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on generate endpoint")


class TestContentEngineFeature:
    """Test POST /api/content-engine/feature endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_feature_story_admin_success(self, admin_token):
        """Admin can toggle featured status on stories"""
        # First get a story ID
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No stories available to test feature toggle")
        
        story_id = list_response.json()["stories"][0]["story_id"]
        
        # Toggle featured on
        response = requests.post(
            f"{BASE_URL}/api/content-engine/feature",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "story_ids": [story_id],
                "featured": True
            }
        )
        assert response.status_code == 200, f"Feature toggle failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "modified" in data
        
        # Toggle featured off
        response = requests.post(
            f"{BASE_URL}/api/content-engine/feature",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "story_ids": [story_id],
                "featured": False
            }
        )
        assert response.status_code == 200
        print(f"✓ Feature toggle successful for story {story_id[:8]}")
    
    def test_feature_story_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on feature endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/feature",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "story_ids": ["fake-id"],
                "featured": True
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on feature endpoint")


class TestContentEngineTag:
    """Test POST /api/content-engine/tag endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_tag_story_admin_success(self, admin_token):
        """Admin can add quality tags to stories"""
        # First get a story ID
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No stories available to test tagging")
        
        story_id = list_response.json()["stories"][0]["story_id"]
        
        # Add HIGH_VIRAL tag
        response = requests.post(
            f"{BASE_URL}/api/content-engine/tag",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "story_id": story_id,
                "tag": "HIGH_VIRAL"
            }
        )
        assert response.status_code == 200, f"Tag failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        print(f"✓ Tag story successful for story {story_id[:8]}")
    
    def test_tag_story_invalid_tag(self, admin_token):
        """Invalid tag returns 400"""
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No stories available to test invalid tag")
        
        story_id = list_response.json()["stories"][0]["story_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/content-engine/tag",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "story_id": story_id,
                "tag": "INVALID_TAG"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Invalid tag correctly returns 400")
    
    def test_tag_story_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on tag endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/tag",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "story_id": "fake-id",
                "tag": "HIGH_VIRAL"
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on tag endpoint")


class TestContentEnginePublish:
    """Test POST /api/content-engine/publish/{story_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_publish_story_admin_success(self, admin_token):
        """Admin can publish a story to the pipeline"""
        # First get a draft story ID
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?status=draft&limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No draft stories available to test publish")
        
        story_id = list_response.json()["stories"][0]["story_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/content-engine/publish/{story_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Publish failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        # Either job_id for new publish or message for already published
        assert "job_id" in data or "message" in data
        print(f"✓ Publish story successful for story {story_id[:8]}")
    
    def test_publish_story_not_found(self, admin_token):
        """Publish non-existent story returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/publish/non-existent-story-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Non-existent story correctly returns 404")
    
    def test_publish_story_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on publish endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/publish/fake-id",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on publish endpoint")


class TestContentEnginePublishBatch:
    """Test POST /api/content-engine/publish-batch endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_publish_batch_admin_success(self, admin_token):
        """Admin can publish all draft stories"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/publish-batch",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Publish batch failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "published" in data
        assert "total_drafts" in data
        print(f"✓ Publish batch successful - Published: {data['published']}, Total drafts: {data['total_drafts']}")
    
    def test_publish_batch_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on publish-batch endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/content-engine/publish-batch",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on publish-batch endpoint")


class TestContentEngineDelete:
    """Test DELETE /api/content-engine/{story_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_delete_story_not_found(self, admin_token):
        """Delete non-existent story returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/content-engine/non-existent-story-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Delete non-existent story correctly returns 404")
    
    def test_delete_story_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on delete endpoint"""
        response = requests.delete(
            f"{BASE_URL}/api/content-engine/fake-id",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on delete endpoint")


class TestContentEngineSocialScripts:
    """Test GET /api/content-engine/social-scripts/{story_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_social_scripts_admin_success(self, admin_token):
        """Admin can get social media scripts for a story"""
        # First get a story ID
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?limit=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No stories available to test social scripts")
        
        story_id = list_response.json()["stories"][0]["story_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/content-engine/social-scripts/{story_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=60  # May need to generate scripts
        )
        assert response.status_code == 200, f"Get social scripts failed: {response.text}"
        data = response.json()
        assert data.get("success") is True
        assert "story_id" in data
        assert "title" in data
        assert "story_text" in data
        # social_scripts may be null if not yet generated
        print(f"✓ Get social scripts successful for story {story_id[:8]}")
    
    def test_get_social_scripts_not_found(self, admin_token):
        """Get social scripts for non-existent story returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/content-engine/social-scripts/non-existent-story-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Non-existent story correctly returns 404")
    
    def test_get_social_scripts_non_admin_forbidden(self, test_user_token):
        """Non-admin users get 403 on social-scripts endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/content-engine/social-scripts/fake-id",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly gets 403 on social-scripts endpoint")


class TestContentEngineStoryStructure:
    """Test story data structure and quality scoring"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_story_has_required_fields(self, admin_token):
        """Verify stories have all required fields"""
        list_response = requests.get(
            f"{BASE_URL}/api/content-engine/list?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if list_response.status_code != 200 or not list_response.json().get("stories"):
            pytest.skip("No stories available to verify structure")
        
        required_fields = [
            "story_id", "title", "story_text", "category", "category_label",
            "quality_score", "quality_tags", "status", "is_featured", "is_published",
            "created_at"
        ]
        
        for story in list_response.json()["stories"]:
            for field in required_fields:
                assert field in story, f"Missing required field: {field}"
            
            # Verify quality_score is between 0 and 100
            assert 0 <= story["quality_score"] <= 100, f"Invalid quality score: {story['quality_score']}"
            
            # Verify quality_tags is a list
            assert isinstance(story["quality_tags"], list), "quality_tags should be a list"
            
            # Verify status is valid
            assert story["status"] in ["draft", "published", "rejected"], f"Invalid status: {story['status']}"
            
            # Verify category is valid
            assert story["category"] in ["emotional", "mystery", "kids", "horror", "viral"], f"Invalid category: {story['category']}"
        
        print(f"✓ All {len(list_response.json()['stories'])} stories have valid structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
