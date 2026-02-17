#!/bin/bash
# CreatorStudio AI - Load Test Script
# Run: chmod +x load_test.sh && ./load_test.sh

API_URL="${1:-https://creatorai-dev.preview.emergentagent.com}"
CONCURRENT_USERS="${2:-100}"
DURATION="${3:-30}"

echo "=========================================="
echo "⚡ CreatorStudio AI Load Test"
echo "=========================================="
echo "Target: $API_URL"
echo "Concurrent Users: $CONCURRENT_USERS"
echo "Duration: ${DURATION}s"
echo ""

# Install ab (Apache Bench) if not present
if ! command -v ab &> /dev/null; then
    echo "Installing Apache Bench..."
    apt-get update && apt-get install -y apache2-utils
fi

# Test Results
echo "📊 Running Load Tests..."
echo ""

# 1. Landing Page Load Test
echo "1️⃣ Landing Page Test"
echo "---------------------"
ab -n 500 -c $CONCURRENT_USERS -t $DURATION "$API_URL/" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Complete requests"
echo ""

# 2. API Health Check
echo "2️⃣ Products API Test"
echo "---------------------"
ab -n 500 -c $CONCURRENT_USERS -t $DURATION "$API_URL/api/payments/products" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Complete requests"
echo ""

# 3. Login Endpoint (POST)
echo "3️⃣ Login API Test"
echo "------------------"
echo '{"email":"test@test.com","password":"test123"}' > /tmp/login_payload.json
ab -n 200 -c 50 -t $DURATION -p /tmp/login_payload.json -T "application/json" "$API_URL/api/auth/login" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Complete requests"
echo ""

# 4. Demo Reel Generation
echo "4️⃣ Demo Reel API Test (light load)"
echo "------------------------------------"
echo '{"topic":"test","niche":"Tech","tone":"Bold","duration":"30s","language":"English","goal":"Followers","audience":"General"}' > /tmp/reel_payload.json
ab -n 20 -c 5 -p /tmp/reel_payload.json -T "application/json" "$API_URL/api/generate/demo-reel" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Complete requests"
echo ""

# 5. Contact Form
echo "5️⃣ Contact Form Test"
echo "---------------------"
echo '{"name":"Load Test","email":"load@test.com","subject":"Test","message":"Load test message"}' > /tmp/contact_payload.json
ab -n 100 -c 20 -p /tmp/contact_payload.json -T "application/json" "$API_URL/api/contact" 2>&1 | grep -E "Requests per second|Time per request|Failed requests|Complete requests"
echo ""

# Cleanup
rm -f /tmp/login_payload.json /tmp/reel_payload.json /tmp/contact_payload.json

echo "=========================================="
echo "📈 Load Test Complete"
echo "=========================================="
echo ""
echo "Performance Recommendations:"
echo "- If 'Failed requests' > 0: Check server logs"
echo "- If 'Time per request' > 1000ms: Consider caching"
echo "- If 'Requests/sec' < 50: Optimize database queries"
