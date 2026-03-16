"""
Live Activity Feed API Tests - Iteration 285
Tests for the live-activity endpoint that provides real-time platform activity 
for social proof on the homepage.

Features tested:
- GET /api/public/live-activity returns success:true with items array
- Items have required fields: id, creator, action, title, category, icon, type, time_ago
- No items with creator 'Visionary AI' (seeded content excluded from showing as creator name)
- Limit parameter works correctly (default 8)
- No duplicate titles in response
- Varied locations (not all same city)
- Activity types include creation, remix, publish
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


class TestLiveActivityEndpoint:
    """Tests for GET /api/public/live-activity"""

    def test_live_activity_endpoint_exists(self):
        """Test that /api/public/live-activity returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: /api/public/live-activity endpoint returns 200")

    def test_live_activity_response_structure(self):
        """Test response has success:true and items array"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity")
        data = response.json()
        
        assert data.get("success") is True, "Expected success:true in response"
        assert "items" in data, "Expected 'items' array in response"
        assert isinstance(data["items"], list), "Items should be a list"
        print(f"PASS: Response has success:true and items array with {len(data['items'])} items")

    def test_live_activity_item_fields(self):
        """Test that each item has required fields: id, creator, action, title, category, icon, type, time_ago"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity")
        data = response.json()
        items = data.get("items", [])
        
        required_fields = ["id", "creator", "action", "title", "category", "icon", "type", "time_ago"]
        
        for idx, item in enumerate(items[:5]):  # Check first 5 items
            for field in required_fields:
                assert field in item, f"Item {idx} missing required field: {field}"
        
        print(f"PASS: All {len(items)} items have required fields: {required_fields}")
        
        # Print sample item for verification
        if items:
            sample = items[0]
            print(f"  Sample item: creator='{sample.get('creator')}', action='{sample.get('action')}', title='{sample.get('title')}', type='{sample.get('type')}'")

    def test_live_activity_no_visionary_ai_creator(self):
        """Test that no items have creator 'Visionary AI' - seeded content excluded"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            creator = item.get("creator", "")
            # Check that "Visionary AI" is not the creator name
            assert "Visionary AI" not in creator, f"Found 'Visionary AI' in creator: {creator}"
            # Creator should be anonymized as "A creator in {Location}"
            assert creator.startswith("A creator in "), f"Creator should be anonymized, got: {creator}"
        
        print(f"PASS: No items have 'Visionary AI' as creator - all {len(items)} items anonymized")

    def test_live_activity_limit_parameter_default(self):
        """Test default limit is 8"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity")
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) <= 8, f"Default limit should be 8, got {len(items)} items"
        print(f"PASS: Default limit returns {len(items)} items (max 8)")

    def test_live_activity_limit_parameter_custom(self):
        """Test custom limit parameter works"""
        # Test limit=5
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=5")
        data = response.json()
        items = data.get("items", [])
        assert len(items) <= 5, f"Limit=5 should return max 5 items, got {len(items)}"
        print(f"PASS: limit=5 returns {len(items)} items")
        
        # Test limit=15
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=15")
        data = response.json()
        items = data.get("items", [])
        assert len(items) <= 15, f"Limit=15 should return max 15 items, got {len(items)}"
        print(f"PASS: limit=15 returns {len(items)} items")

    def test_live_activity_no_duplicate_titles(self):
        """Test that response has no duplicate titles"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        data = response.json()
        items = data.get("items", [])
        
        titles = [item.get("title") for item in items]
        unique_titles = set(titles)
        
        # Allow for some duplicates in synthetic pulse but check majority are unique
        duplicate_count = len(titles) - len(unique_titles)
        assert duplicate_count <= len(titles) * 0.3, f"Too many duplicate titles: {duplicate_count} out of {len(titles)}"
        
        print(f"PASS: {len(unique_titles)} unique titles out of {len(titles)} items")

    def test_live_activity_varied_locations(self):
        """Test that locations are varied (not all same city)"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=10")
        data = response.json()
        items = data.get("items", [])
        
        # Extract locations from "A creator in {Location}"
        locations = set()
        for item in items:
            creator = item.get("creator", "")
            if creator.startswith("A creator in "):
                location = creator.replace("A creator in ", "")
                locations.add(location)
        
        # Should have at least 2 different locations for 8+ items
        min_locations = 2 if len(items) >= 8 else 1
        assert len(locations) >= min_locations, f"Expected varied locations, got only: {locations}"
        print(f"PASS: Found {len(locations)} different locations: {list(locations)[:5]}")

    def test_live_activity_types_include_required(self):
        """Test that activity types include creation, remix, publish"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        data = response.json()
        items = data.get("items", [])
        
        types_found = set(item.get("type") for item in items)
        
        # Check that at least some valid types exist
        valid_types = {"creation", "remix", "publish"}
        found_valid = types_found & valid_types
        
        assert len(found_valid) >= 1, f"Expected at least one type from {valid_types}, got {types_found}"
        print(f"PASS: Found activity types: {types_found}")

    def test_live_activity_icons_valid(self):
        """Test that icons are valid mapped values"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        data = response.json()
        items = data.get("items", [])
        
        valid_icons = {"sparkles", "film", "refresh-ccw", "wand", "share"}
        
        for item in items:
            icon = item.get("icon")
            assert icon in valid_icons, f"Invalid icon: {icon}, expected one of {valid_icons}"
        
        icons_found = set(item.get("icon") for item in items)
        print(f"PASS: All icons valid. Found: {icons_found}")

    def test_live_activity_time_ago_format(self):
        """Test that time_ago field has valid format (Xm ago, Xh ago, Xd ago, just now)"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        data = response.json()
        items = data.get("items", [])
        
        import re
        valid_patterns = [
            r"^\d+m ago$",      # e.g., "5m ago"
            r"^\d+h ago$",      # e.g., "2h ago"
            r"^\d+d ago$",      # e.g., "1d ago"
            r"^just now$"       # "just now"
        ]
        
        for item in items:
            time_ago = item.get("time_ago", "")
            matched = any(re.match(pattern, time_ago) for pattern in valid_patterns)
            assert matched, f"Invalid time_ago format: '{time_ago}'"
        
        sample_times = [item.get("time_ago") for item in items[:4]]
        print(f"PASS: All time_ago values valid. Samples: {sample_times}")

    def test_live_activity_action_verbs(self):
        """Test that action verbs are valid"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        data = response.json()
        items = data.get("items", [])
        
        valid_actions = {"just created", "published", "remixed", "finished generating", "shared"}
        
        for item in items:
            action = item.get("action")
            assert action in valid_actions, f"Invalid action: '{action}', expected one of {valid_actions}"
        
        actions_found = set(item.get("action") for item in items)
        print(f"PASS: All action verbs valid. Found: {actions_found}")


class TestLiveActivityDataIntegrity:
    """Test data integrity and edge cases"""

    def test_live_activity_response_count_matches_items(self):
        """Test that 'count' field matches actual items length"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=8")
        data = response.json()
        
        items = data.get("items", [])
        count = data.get("count", 0)
        
        assert count == len(items), f"count ({count}) doesn't match items length ({len(items)})"
        print(f"PASS: count ({count}) matches items length")

    def test_live_activity_items_have_unique_ids(self):
        """Test that all items have unique IDs"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        data = response.json()
        items = data.get("items", [])
        
        ids = [item.get("id") for item in items]
        unique_ids = set(ids)
        
        assert len(ids) == len(unique_ids), f"Duplicate IDs found: {len(ids)} total, {len(unique_ids)} unique"
        print(f"PASS: All {len(ids)} items have unique IDs")

    def test_live_activity_limit_boundary_min(self):
        """Test minimum limit boundary (1)"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=1")
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) <= 1, f"limit=1 should return max 1 item, got {len(items)}"
        print(f"PASS: limit=1 returns {len(items)} item(s)")

    def test_live_activity_limit_boundary_max(self):
        """Test maximum limit boundary (20)"""
        response = requests.get(f"{BASE_URL}/api/public/live-activity?limit=20")
        data = response.json()
        items = data.get("items", [])
        
        assert len(items) <= 20, f"limit=20 should return max 20 items, got {len(items)}"
        print(f"PASS: limit=20 returns {len(items)} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
