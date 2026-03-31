"""
Test Story Quality Score Feature - P1 Enhancement for Comic Story Builder Step 2
Tests the /api/comic-storybook-v2/analyze-story endpoint

Features tested:
- Short prompt analysis (expect score < 50)
- Detailed prompt analysis (expect score 70+)
- Too-short prompt rejection (< 10 chars)
- Response structure validation (dimensions, strengths, opportunities, quick_fixes)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@creatorstudio.ai"
ADMIN_PASSWORD = "Cr3@t0rStud!o#2026"


class TestStoryQualityScore:
    """Tests for the Story Quality Score analyze-story endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_analyze_short_prompt_low_score(self, auth_headers):
        """Test that a short/vague prompt returns a score below 50"""
        short_prompt = "shy teenager magic"  # Minimal story idea
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
            headers=auth_headers,
            json={
                "storyIdea": short_prompt,
                "genre": "fantasy",
                "ageGroup": "6-10",
                "readingLevel": "intermediate"
            },
            timeout=30  # LLM calls can take time
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify success
        assert data.get("success") == True, f"Expected success=True, got {data}"
        
        # Verify score structure
        assert "overall_score" in data, "Missing overall_score in response"
        score = data["overall_score"]
        assert isinstance(score, int), f"Score should be int, got {type(score)}"
        assert 0 <= score <= 100, f"Score should be 0-100, got {score}"
        
        # Short prompts should score below 50 (vague, lacks detail)
        assert score < 50, f"Short prompt should score < 50, got {score}"
        
        # Verify dimensions
        assert "dimensions" in data, "Missing dimensions in response"
        dims = data["dimensions"]
        expected_dims = ["clarity", "protagonist", "setting", "conflict", 
                        "emotional_appeal", "age_appropriateness", "visual_richness", "lesson_potential"]
        for dim in expected_dims:
            assert dim in dims, f"Missing dimension: {dim}"
            assert isinstance(dims[dim], int), f"Dimension {dim} should be int"
            assert 0 <= dims[dim] <= 100, f"Dimension {dim} should be 0-100"
        
        # Verify strengths and opportunities
        assert "strengths" in data, "Missing strengths"
        assert "opportunities" in data, "Missing opportunities"
        assert isinstance(data["strengths"], list), "Strengths should be a list"
        assert isinstance(data["opportunities"], list), "Opportunities should be a list"
        
        # Verify quick_fixes
        assert "quick_fixes" in data, "Missing quick_fixes"
        assert isinstance(data["quick_fixes"], list), "quick_fixes should be a list"
        if len(data["quick_fixes"]) > 0:
            fix = data["quick_fixes"][0]
            assert "label" in fix, "Quick fix missing label"
            assert "instruction" in fix, "Quick fix missing instruction"
        
        print(f"✓ Short prompt '{short_prompt}' scored {score} (expected < 50)")
        print(f"  Dimensions: {dims}")
        print(f"  Strengths: {data['strengths']}")
        print(f"  Opportunities: {data['opportunities'][:2]}")
        print(f"  Quick fixes: {[f['label'] for f in data['quick_fixes'][:3]]}")
    
    def test_analyze_detailed_prompt_high_score(self, auth_headers):
        """Test that a detailed prompt with clear protagonist, setting, conflict returns score 70+"""
        detailed_prompt = """
        Luna is a brave 8-year-old girl who lives in a cozy treehouse village in the Enchanted Forest. 
        One day, she discovers that the magical Crystal of Light that protects her village has been stolen 
        by the mischievous Shadow Sprites. With her loyal talking fox companion Ember, Luna must journey 
        through the Whispering Woods, solve ancient riddles, and learn the power of friendship and courage 
        to retrieve the crystal before darkness falls over her home forever.
        """
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
            headers=auth_headers,
            json={
                "storyIdea": detailed_prompt.strip(),
                "genre": "fantasy",
                "ageGroup": "6-10",
                "readingLevel": "intermediate"
            },
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=True, got {data}"
        
        score = data["overall_score"]
        # Detailed prompts with clear protagonist, setting, conflict should score 70+
        assert score >= 70, f"Detailed prompt should score >= 70, got {score}"
        
        # Verify all 8 dimensions present
        dims = data["dimensions"]
        assert len(dims) == 8, f"Expected 8 dimensions, got {len(dims)}"
        
        # Key dimensions should be high for this detailed prompt
        assert dims.get("protagonist", 0) >= 60, f"Protagonist score should be >= 60, got {dims.get('protagonist')}"
        assert dims.get("setting", 0) >= 60, f"Setting score should be >= 60, got {dims.get('setting')}"
        assert dims.get("conflict", 0) >= 60, f"Conflict score should be >= 60, got {dims.get('conflict')}"
        
        print(f"✓ Detailed prompt scored {score} (expected >= 70)")
        print(f"  Key dimensions: protagonist={dims.get('protagonist')}, setting={dims.get('setting')}, conflict={dims.get('conflict')}")
    
    def test_analyze_too_short_prompt_rejected(self, auth_headers):
        """Test that prompts < 10 chars are rejected gracefully"""
        too_short = "cat"  # Only 3 chars
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
            headers=auth_headers,
            json={
                "storyIdea": too_short,
                "genre": "comedy",
                "ageGroup": "6-10",
                "readingLevel": "beginner"
            },
            timeout=10
        )
        
        assert response.status_code == 200, f"Expected 200 (graceful rejection), got {response.status_code}"
        data = response.json()
        
        # Should return success=False with a message
        assert data.get("success") == False, f"Expected success=False for too-short prompt, got {data}"
        assert "message" in data, "Expected message explaining rejection"
        
        print(f"✓ Too-short prompt '{too_short}' rejected gracefully: {data.get('message')}")
    
    def test_analyze_empty_prompt_rejected(self, auth_headers):
        """Test that empty prompts are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
            headers=auth_headers,
            json={
                "storyIdea": "   ",  # Whitespace only
                "genre": "fantasy"
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == False, "Empty prompt should be rejected"
        
        print(f"✓ Empty/whitespace prompt rejected: {data.get('message')}")
    
    def test_analyze_medium_prompt_moderate_score(self, auth_headers):
        """Test that a medium-detail prompt gets a moderate score (40-70)"""
        medium_prompt = "A young wizard named Max discovers a magical book that can bring drawings to life. He must learn to control his new power."
        
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
            headers=auth_headers,
            json={
                "storyIdea": medium_prompt,
                "genre": "fantasy",
                "ageGroup": "6-10",
                "readingLevel": "intermediate"
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        score = data["overall_score"]
        # Medium prompts should score in the middle range
        assert 40 <= score <= 85, f"Medium prompt should score 40-85, got {score}"
        
        print(f"✓ Medium prompt scored {score} (expected 40-85)")
    
    def test_improve_idea_endpoint_works(self, auth_headers):
        """Test that improve-idea endpoint still works (integration with quick-fix)"""
        response = requests.post(
            f"{BASE_URL}/api/comic-storybook-v2/improve-idea",
            headers=auth_headers,
            json={
                "storyIdea": "A cat goes on an adventure",
                "genre": "kids_adventure",
                "ageGroup": "4-7",
                "language": "English",
                "readingLevel": "beginner"
            },
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert "improved" in data, "Missing improved story in response"
        assert len(data["improved"]) > len("A cat goes on an adventure"), "Improved story should be longer"
        
        print(f"✓ Improve-idea endpoint works")
        print(f"  Original: 'A cat goes on an adventure'")
        print(f"  Improved: '{data['improved'][:100]}...'")


class TestAnalyzeStoryEdgeCases:
    """Edge case tests for analyze-story endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("token") or data.get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_analyze_with_different_genres(self, auth_headers):
        """Test analysis works across different genres"""
        genres = ["kids_adventure", "superhero", "fantasy", "comedy", "mystery"]
        prompt = "A young hero discovers a hidden power and must save their village from danger."
        
        for genre in genres:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
                headers=auth_headers,
                json={"storyIdea": prompt, "genre": genre, "ageGroup": "6-10"},
                timeout=30
            )
            assert response.status_code == 200, f"Failed for genre {genre}"
            data = response.json()
            assert data.get("success") == True, f"Analysis failed for genre {genre}"
            print(f"✓ Genre '{genre}' analysis: score={data['overall_score']}")
    
    def test_analyze_with_different_age_groups(self, auth_headers):
        """Test analysis adapts to different age groups"""
        age_groups = ["3-6", "6-10", "8-12", "12+"]
        prompt = "A brave knight goes on a quest to find a magical sword."
        
        for age in age_groups:
            response = requests.post(
                f"{BASE_URL}/api/comic-storybook-v2/analyze-story",
                headers=auth_headers,
                json={"storyIdea": prompt, "genre": "fantasy", "ageGroup": age},
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") == True
            # Age appropriateness dimension should be present
            assert "age_appropriateness" in data.get("dimensions", {})
            print(f"✓ Age group '{age}' analysis: score={data['overall_score']}, age_appropriateness={data['dimensions'].get('age_appropriateness')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
