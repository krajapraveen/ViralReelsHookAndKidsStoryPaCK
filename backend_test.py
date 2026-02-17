import requests
import sys
import json
from datetime import datetime

class CreatorStudioAPITester:
    def __init__(self, base_url="https://creatorai-dev.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Try to parse JSON response
                try:
                    json_response = response.json()
                    if isinstance(json_response, dict) and len(json_response) < 10:
                        print(f"   Response: {json_response}")
                    else:
                        print(f"   Response: Large JSON object with {len(json_response)} keys" if isinstance(json_response, dict) else "JSON array/other")
                except:
                    print(f"   Response: Non-JSON content (length: {len(response.text)})")
                    
                return success, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, email, password):
        """Test login and get token"""
        success, response = self.run_test(
            "Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and isinstance(response, dict) and 'token' in response:
            self.token = response['token']
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_credits_balance(self):
        """Test getting credits balance"""
        success, response = self.run_test(
            "Get Credits Balance",
            "GET",
            "api/credits/balance",
            200
        )
        return success, response

    def test_generate_story(self):
        """Test story generation"""
        story_data = {
            "ageGroup": "13-15",
            "theme": "Adventure",
            "genre": "Science Fiction",
            "moral": "Friendship",
            "characters": ["Kid", "Robot"],
            "setting": "space station",
            "scenes": 8,
            "language": "English",
            "style": "Pixar-like 3D",
            "length": "60s"
        }
        
        success, response = self.run_test(
            "Generate Story",
            "POST",
            "api/generate/story",
            200,
            data=story_data
        )
        return success, response

    def test_generate_reel(self):
        """Test reel generation"""
        reel_data = {
            "language": "English",
            "niche": "Tech",
            "tone": "Bold",
            "duration": "30s",
            "goal": "Followers",
            "topic": "AI in 2025"
        }
        
        success, response = self.run_test(
            "Generate Reel",
            "POST",
            "api/generate/reel",
            200,
            data=reel_data
        )
        return success, response

    def test_get_generations(self):
        """Test getting generations list"""
        success, response = self.run_test(
            "Get Generations",
            "GET",
            "api/generate/generations",
            200
        )
        return success, response

    def test_basic_endpoints(self):
        """Test basic endpoints"""
        # Test root endpoint
        self.run_test("Root Endpoint", "GET", "api/", 200)
        
        # Test status endpoint
        self.run_test("Status Endpoint", "GET", "api/status", 200)

def main():
    print("🚀 CreatorStudio AI Backend API Testing")
    print("=" * 50)
    
    # Setup
    tester = CreatorStudioAPITester()
    
    # Test basic endpoints first
    print("\n📋 Testing Basic Endpoints...")
    tester.test_basic_endpoints()
    
    # Test authentication
    print("\n🔐 Testing Authentication...")
    if not tester.test_login("admin@creatorstudio.ai", "admin123"):
        print("❌ Login failed, stopping authenticated tests")
        print(f"\n📊 Basic Tests Results: {tester.tests_passed}/{tester.tests_run}")
        return 1

    # Test authenticated endpoints
    print("\n💰 Testing Credits System...")
    credits_success, credits_response = tester.test_credits_balance()
    
    print("\n📚 Testing Story Generation...")
    story_success, story_response = tester.test_generate_story()
    
    print("\n🎬 Testing Reel Generation...")
    reel_success, reel_response = tester.test_generate_reel()
    
    print("\n📋 Testing Generations List...")
    generations_success, generations_response = tester.test_get_generations()

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())