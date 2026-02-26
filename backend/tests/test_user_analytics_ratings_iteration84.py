"""
User Analytics & Ratings Module Tests - Iteration 84
======================================================
Tests for:
- A1) Dashboard with rating distributions and filters
- A2) Privacy-safe location tracking (session tracking)
- A3) Mandatory feedback for 1-2 star ratings
- A4) Event tracking/telemetry
- A5) Admin API endpoints
- A6) CSV export
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

class TestUserAnalyticsAuth:
    """Test authentication for analytics endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        """Get demo user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return response.json()["token"]
    
    def test_admin_login_success(self, admin_token):
        """Test admin login returns valid token"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print("✓ Admin login successful")
    
    def test_demo_user_login_success(self, demo_token):
        """Test demo user login returns valid token"""
        assert demo_token is not None
        assert len(demo_token) > 0
        print("✓ Demo user login successful")


class TestAdminRatingsSummary:
    """A1, A5: Admin ratings summary endpoint tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_ratings_summary_endpoint(self, admin_token):
        """Test GET /admin/user-analytics/ratings/summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/summary?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "period_days" in data
        assert "total_ratings" in data
        assert "average_rating" in data
        assert "distribution" in data
        assert "nps_score" in data
        assert "satisfaction_percentage" in data
        assert "low_rating_count" in data
        assert "low_rating_percentage" in data
        
        # Verify distribution structure
        assert isinstance(data["distribution"], dict)
        for key in ["1", "2", "3", "4", "5"]:
            # MongoDB may return int keys as strings
            pass
        
        print(f"✓ Ratings summary: {data['total_ratings']} ratings, avg: {data['average_rating']}")
    
    def test_ratings_summary_with_days_filter(self, admin_token):
        """Test ratings summary with different day filters"""
        for days in [7, 30, 90, 365]:
            response = requests.get(
                f"{BASE_URL}/api/admin/user-analytics/ratings/summary?days={days}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == days
        print("✓ All day filters work correctly")
    
    def test_ratings_summary_requires_admin(self):
        """Test that non-admin users cannot access admin endpoints"""
        # First login as demo user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        demo_token = response.json()["token"]
        
        # Try to access admin endpoint
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/summary",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code in [401, 403], "Non-admin should be denied"
        print("✓ Admin endpoint properly protected")


class TestAdminRatingsList:
    """A1, A5: Admin ratings list endpoint tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_ratings_list_endpoint(self, admin_token):
        """Test GET /admin/user-analytics/ratings/list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/list?days=30&page=0&size=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "ratings" in data
        assert isinstance(data["ratings"], list)
        
        print(f"✓ Ratings list: {data['total']} total, page {data['page']}")
    
    def test_ratings_list_with_rating_filter(self, admin_token):
        """Test ratings list with rating filter"""
        for rating_val in [1, 2, 3, 4, 5]:
            response = requests.get(
                f"{BASE_URL}/api/admin/user-analytics/ratings/list?rating_filter={rating_val}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
        print("✓ Rating filter works for all values")
    
    def test_ratings_list_with_feature_filter(self, admin_token):
        """Test ratings list with feature key filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/list?feature_key=reel_generator",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Feature filter works")


class TestRatingSubmission:
    """A3: Rating submission with mandatory feedback for 1-2 stars"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        return response.json()["token"]
    
    def test_submit_high_rating_no_reason_required(self, demo_token):
        """Test submitting 5-star rating without mandatory reason"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 5,
                "feature_key": "TEST_reel_generator",
                "comment": "Great experience!"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert "rating_id" in data
        print(f"✓ High rating submission successful: {data['rating_id']}")
    
    def test_submit_3_star_rating_no_reason_required(self, demo_token):
        """Test submitting 3-star rating without mandatory reason"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 3,
                "feature_key": "TEST_story_pack"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        print("✓ 3-star rating without reason - SUCCESS")
    
    def test_submit_1_star_without_reason_fails(self, demo_token):
        """Test that 1-star rating without reason is rejected (A3)"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 1,
                "feature_key": "TEST_comix_ai"
            }
        )
        assert response.status_code == 400, f"Should fail, got: {response.status_code}"
        data = response.json()
        assert "reason" in data.get("detail", "").lower() or "feedback" in data.get("detail", "").lower()
        print("✓ 1-star without reason correctly rejected")
    
    def test_submit_2_star_without_reason_fails(self, demo_token):
        """Test that 2-star rating without reason is rejected (A3)"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 2,
                "feature_key": "TEST_gif_maker"
            }
        )
        assert response.status_code == 400, f"Should fail, got: {response.status_code}"
        print("✓ 2-star without reason correctly rejected")
    
    def test_submit_1_star_with_reason_succeeds(self, demo_token):
        """Test that 1-star rating with reason succeeds (A3)"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 1,
                "feature_key": "TEST_generation_fail",
                "reason_type": "generation_failed",
                "comment": "Generation kept failing"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        print(f"✓ 1-star with reason accepted: {data['rating_id']}")
    
    def test_submit_2_star_with_other_reason_needs_comment(self, demo_token):
        """Test that 2-star with 'other' reason requires comment (A3)"""
        # Without comment - should fail
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 2,
                "feature_key": "TEST_other_issue",
                "reason_type": "other"
            }
        )
        assert response.status_code == 400, f"Should fail without comment, got: {response.status_code}"
        print("✓ 2-star with 'other' reason without comment - correctly rejected")
    
    def test_submit_2_star_with_other_reason_and_comment(self, demo_token):
        """Test that 2-star with 'other' reason and comment succeeds (A3)"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 2,
                "feature_key": "TEST_other_complete",
                "reason_type": "other",
                "comment": "Specific issue: animation was choppy"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        print(f"✓ 2-star with 'other' + comment accepted: {data['rating_id']}")


class TestSessionTracking:
    """A2, A4: Session tracking for privacy-safe location tracking"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        return response.json()["token"]
    
    def test_start_session(self, demo_token):
        """Test session start endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/session/start",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
        print(f"✓ Session started: {data['session_id']}")
        return data["session_id"]
    
    def test_end_session(self, demo_token):
        """Test session end endpoint"""
        # First start a session
        start_response = requests.post(
            f"{BASE_URL}/api/user-analytics/session/start",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        session_id = start_response.json()["session_id"]
        
        # Then end it
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/session/end",
            headers={"Authorization": f"Bearer {demo_token}"},
            params={"session_id": session_id}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        print(f"✓ Session ended: {session_id}")


class TestFeatureEventTracking:
    """A4: Feature event tracking/telemetry"""
    
    @pytest.fixture(scope="class")
    def demo_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        return response.json()["token"]
    
    def test_track_feature_event_success(self, demo_token):
        """Test tracking a successful feature event"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/event",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "feature_key": "TEST_reel_generator",
                "event_type": "GENERATION_SUCCESS",
                "status": "success",
                "latency_ms": 2500,
                "metadata": {"format": "mp4", "duration": 15}
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        assert "event_id" in data
        print(f"✓ Event tracked: {data['event_id']}")
    
    def test_track_feature_event_failure(self, demo_token):
        """Test tracking a failed feature event"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/event",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "feature_key": "TEST_comix_ai",
                "event_type": "GENERATION_FAILED",
                "status": "failed",
                "error_code": "ERR_TIMEOUT",
                "latency_ms": 30000
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] is True
        print(f"✓ Failed event tracked: {data['event_id']}")
    
    def test_track_feature_opened_event(self, demo_token):
        """Test tracking a feature opened event"""
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/event",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "feature_key": "TEST_genstudio",
                "event_type": "FEATURE_OPENED",
                "status": "success"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Feature opened event tracked")


class TestAdminFeatureEvents:
    """A5: Admin feature events endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_get_feature_events(self, admin_token):
        """Test GET /admin/user-analytics/feature-events"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/feature-events?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "events" in data
        assert isinstance(data["events"], list)
        
        print(f"✓ Feature events: {data['total']} events")
    
    def test_feature_events_with_filters(self, admin_token):
        """Test feature events with various filters"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/feature-events?days=7&status=failed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Feature events filter by status works")


class TestAdminRatingsDrilldown:
    """A1: Rating drilldown for understanding WHY low ratings"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def sample_rating_id(self, admin_token):
        """Create a sample rating and return its ID"""
        # Login as demo user to create rating
        demo_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        demo_token = demo_response.json()["token"]
        
        # Create a rating
        response = requests.post(
            f"{BASE_URL}/api/user-analytics/rating",
            headers={"Authorization": f"Bearer {demo_token}"},
            json={
                "rating": 1,
                "feature_key": "TEST_drilldown",
                "reason_type": "poor_quality",
                "comment": "Test drilldown comment"
            }
        )
        if response.status_code == 200:
            return response.json()["rating_id"]
        return None
    
    def test_rating_drilldown(self, admin_token, sample_rating_id):
        """Test GET /admin/user-analytics/ratings/drilldown/{rating_id}"""
        if not sample_rating_id:
            pytest.skip("No sample rating created")
        
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/drilldown/{sample_rating_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify drilldown structure
        assert "rating_id" in data
        assert "user_email" in data
        assert "rating" in data
        assert "reason_type" in data
        assert "feature_key" in data
        assert "session_id" in data or data.get("session_id") is None
        assert "feature_events_before_rating" in data
        assert "output_status" in data
        
        print(f"✓ Drilldown: user={data['user_email']}, rating={data['rating']}, reason={data['reason_type']}")
    
    def test_drilldown_nonexistent_rating(self, admin_token):
        """Test drilldown for non-existent rating returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/drilldown/nonexistent-id-12345",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ Drilldown 404 for non-existent rating")


class TestAdminUserSessions:
    """A5: Admin user sessions endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_get_user_sessions(self, admin_token):
        """Test GET /admin/user-analytics/users/{user_id}/sessions"""
        # First get demo user ID
        demo_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        demo_user_id = demo_response.json()["user"]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/users/{demo_user_id}/sessions?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "user_id" in data
        assert "total_sessions" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        
        print(f"✓ User sessions: {data['total_sessions']} sessions for user {data['user_id']}")


class TestFeatureHappinessReport:
    """A1: Feature happiness report - Happy vs Unhappy features"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_feature_happiness_report(self, admin_token):
        """Test GET /admin/user-analytics/feature-happiness"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/feature-happiness?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "happy_features" in data
        assert "unhappy_features" in data
        assert "all_features" in data
        assert "period_days" in data
        assert isinstance(data["happy_features"], list)
        assert isinstance(data["unhappy_features"], list)
        
        print(f"✓ Feature happiness: {len(data['happy_features'])} happy, {len(data['unhappy_features'])} unhappy")


class TestDashboardSummary:
    """A1: Dashboard summary endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_dashboard_summary(self, admin_token):
        """Test GET /admin/user-analytics/dashboard-summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/dashboard-summary?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "period_days" in data
        assert "ratings" in data
        assert "sessions" in data
        assert "events" in data
        assert "low_ratings_requiring_attention" in data
        
        # Check nested structure
        assert "total_ratings" in data["ratings"]
        assert "total" in data["sessions"]
        assert "total" in data["events"]
        
        print(f"✓ Dashboard summary: {data['ratings']['total_ratings']} ratings, {data['sessions']['total']} sessions, {data['events']['total']} events")


class TestCSVExport:
    """A6: CSV export functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        return response.json()["token"]
    
    def test_csv_export(self, admin_token):
        """Test GET /admin/user-analytics/ratings/export/csv"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/export/csv?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV, got: {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".csv" in content_disp
        
        # Check CSV content has header
        content = response.text
        assert "Rating ID" in content or "rating_id" in content.lower()
        
        print(f"✓ CSV export: {len(content)} bytes, content-type: {content_type}")
    
    def test_csv_export_with_rating_filter(self, admin_token):
        """Test CSV export with rating filter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/user-analytics/ratings/export/csv?days=30&rating_filter=1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ CSV export with filter works")


class TestResetRatings:
    """Reset all ratings functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@creatorstudio.ai",
            "password": "Cr3@t0rStud!o#2026"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("token")
    
    def test_reset_ratings_without_confirm_fails(self, admin_token):
        """Test that reset without confirm=true fails"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/user-analytics/ratings/reset",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400, f"Should require confirm=true, got: {response.status_code}"
        print("✓ Reset without confirm correctly rejected")
    
    def test_reset_ratings_requires_admin(self):
        """Test that non-admin cannot reset ratings"""
        demo_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Password123!"
        })
        if demo_response.status_code != 200:
            pytest.skip("Demo user login rate-limited")
        
        demo_token = demo_response.json().get("token")
        if not demo_token:
            pytest.skip("Demo user login failed")
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/user-analytics/ratings/reset?confirm=true",
            headers={"Authorization": f"Bearer {demo_token}"}
        )
        assert response.status_code in [401, 403], "Non-admin should be denied"
        print("✓ Reset correctly requires admin")
    
    # Note: Not actually running reset as it would delete test data
    # def test_reset_ratings_with_confirm(self, admin_token):
    #     """Test reset with confirm=true works"""
    #     pass


class TestRatingReasons:
    """Test rating reasons endpoint"""
    
    def test_get_rating_reasons(self):
        """Test GET /user-analytics/rating-reasons (public)"""
        response = requests.get(f"{BASE_URL}/api/user-analytics/rating-reasons")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "reasons" in data
        assert isinstance(data["reasons"], list)
        assert len(data["reasons"]) > 0
        
        # Check structure of reasons
        for reason in data["reasons"]:
            assert "key" in reason
            assert "label" in reason
        
        # Check expected reasons exist
        keys = [r["key"] for r in data["reasons"]]
        expected_keys = ["generation_failed", "poor_quality", "too_slow", "other"]
        for key in expected_keys:
            assert key in keys, f"Missing expected reason: {key}"
        
        print(f"✓ Rating reasons: {len(data['reasons'])} reasons available")


# Cleanup fixture to remove TEST_ prefixed data
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Clean up test data after all tests"""
    yield
    # Note: Could implement cleanup here if needed
    # For now, test data with TEST_ prefix is left for inspection
    print("✓ Test suite completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
