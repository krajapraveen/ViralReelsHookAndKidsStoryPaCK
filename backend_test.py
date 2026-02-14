import requests
import sys
import time
from datetime import datetime

class CreatorStudioAPITester:
    def __init__(self, base_url="https://storymaker-33.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.user_token = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.json()}")
                except:
                    print(f"   Response: {response.text}")

            return success, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("\n=== TESTING BASIC ENDPOINTS ===")
        
        # Test root endpoint
        self.run_test("Root API", "GET", "api/", 200)
        
        # Test status endpoint
        success, response = self.run_test("Get Status Checks", "GET", "api/status", 200)
        
        # Test create status check
        test_data = {"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        self.run_test("Create Status Check", "POST", "api/status", 200, data=test_data)

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n=== TESTING AUTHENTICATION ENDPOINTS ===")
        
        # Test admin login
        admin_data = {"email": "admin@creatorstudio.ai", "password": "admin123"}
        success, response = self.run_test("Admin Login", "POST", "api/auth/login", 200, data=admin_data)
        
        if success and 'token' in response:
            self.admin_token = response['token']
            self.token = self.admin_token
            print(f"✅ Admin token obtained")
            
            # Test get current user
            self.run_test("Get Current User (Admin)", "GET", "api/auth/me", 200)
        
        # Test regular user login
        user_data = {"email": "demo@example.com", "password": "password123"}
        success, response = self.run_test("User Login", "POST", "api/auth/login", 200, data=user_data)
        
        if success and 'token' in response:
            self.user_token = response['token']
            print(f"✅ User token obtained")

    def test_credit_endpoints(self):
        """Test credit-related endpoints"""
        print("\n=== TESTING CREDIT ENDPOINTS ===")
        
        if self.admin_token:
            self.token = self.admin_token
            self.run_test("Get Credit Balance (Admin)", "GET", "api/credits/balance", 200)
            self.run_test("Get Credit Ledger (Admin)", "GET", "api/credits/ledger", 200)
        
        if self.user_token:
            self.token = self.user_token
            self.run_test("Get Credit Balance (User)", "GET", "api/credits/balance", 200)
            self.run_test("Get Credit Ledger (User)", "GET", "api/credits/ledger", 200)

    def test_generation_endpoints(self):
        """Test story/reel generation endpoints"""
        print("\n=== TESTING GENERATION ENDPOINTS ===")
        
        if self.admin_token:
            self.token = self.admin_token
            
            # Test story generation
            story_data = {
                "ageGroup": "13-15",
                "theme": "Adventure", 
                "genre": "Science Fiction",
                "moral": "Friendship",
                "characters": ["Teen", "Robot"],
                "setting": "space station",
                "scenes": 8,
                "language": "English",
                "style": "Pixar-like 3D",
                "length": "60s"
            }
            
            success, response = self.run_test("Generate Story", "POST", "api/generate/story", 200, data=story_data)
            
            if success and 'generationId' in response:
                generation_id = response['generationId']
                print(f"✅ Story generation started with ID: {generation_id}")
                
                # Test get generation status
                self.run_test("Get Generation Status", "GET", f"api/generate/generations/{generation_id}", 200)
                
                # Test get all generations
                self.run_test("Get All Generations", "GET", "api/generate/generations", 200)
            
            # Test reel generation
            reel_data = {
                "topic": "Space exploration for kids",
                "style": "Educational",
                "duration": "30s"
            }
            
            self.run_test("Generate Reel", "POST", "api/generate/reel", 200, data=reel_data)

    def test_payment_endpoints(self):
        """Test payment-related endpoints"""
        print("\n=== TESTING PAYMENT ENDPOINTS ===")
        
        if self.admin_token:
            self.token = self.admin_token
            self.run_test("Get Products", "GET", "api/payments/products", 200)
            self.run_test("Get Payment History", "GET", "api/payments/history", 200)

    def test_input_validation(self):
        """Test input validation"""
        print("\n=== TESTING INPUT VALIDATION ===")
        
        if self.admin_token:
            self.token = self.admin_token
            
            # Test extremely long topic for reel
            long_topic = "A" * 1001  # Over 1000 characters
            reel_data = {"topic": long_topic, "style": "Educational", "duration": "30s"}
            self.run_test("Reel with Long Topic", "POST", "api/generate/reel", 400, data=reel_data)
            
            # Test story generation without required fields
            incomplete_story = {"ageGroup": "6-8"}  # Missing required fields
            self.run_test("Incomplete Story Data", "POST", "api/generate/story", 400, data=incomplete_story)
            
            # Test invalid JSON (this will be caught by requests library)
            print("\n🔍 Testing Invalid JSON...")
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate/story",
                    data="invalid json",
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.admin_token}'},
                    timeout=10
                )
                if response.status_code == 400:
                    print("✅ Passed - Invalid JSON rejected")
                    self.tests_passed += 1
                else:
                    print(f"❌ Failed - Expected 400, got {response.status_code}")
                self.tests_run += 1
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                self.tests_run += 1

    def test_security(self):
        """Test security aspects"""
        print("\n=== TESTING SECURITY ===")
        
        # Test accessing protected endpoints without token
        self.token = None
        self.run_test("Access Credits Without Auth", "GET", "api/credits/balance", 401)
        self.run_test("Access Generation Without Auth", "POST", "api/generate/story", 401, data={})
        
        # Test with invalid token
        self.token = "invalid_token"
        self.run_test("Access with Invalid Token", "GET", "api/credits/balance", 401)

def main():
    print("🚀 Starting CreatorStudio AI Backend API Tests")
    print("=" * 60)
    
    tester = CreatorStudioAPITester()
    
    # Run all test suites
    tester.test_basic_endpoints()
    tester.test_auth_endpoints()
    tester.test_credit_endpoints()
    tester.test_generation_endpoints()
    tester.test_payment_endpoints()
    tester.test_input_validation()
    tester.test_security()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        failed = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())