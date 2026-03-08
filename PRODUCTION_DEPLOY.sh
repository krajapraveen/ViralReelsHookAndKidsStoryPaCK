#!/bin/bash
# VISIONARY SUITE - PRODUCTION DEPLOYMENT SCRIPT
# Run this script on the production server to apply all fixes
# Date: March 8, 2026

echo "========================================"
echo "VISIONARY SUITE PRODUCTION FIXES"
echo "========================================"

# 1. Backup current files
echo "Step 1: Creating backups..."
cp /app/backend/server.py /app/backend/server.py.backup.$(date +%Y%m%d_%H%M%S)
cp /app/backend/routes/photo_to_comic.py /app/backend/routes/photo_to_comic.py.backup.$(date +%Y%m%d_%H%M%S)
cp /app/backend/routes/gif_maker.py /app/backend/routes/gif_maker.py.backup.$(date +%Y%m%d_%H%M%S)

# 2. Delete old payments.py if exists
echo "Step 2: Removing old Razorpay file..."
rm -f /app/backend/routes/payments.py

# 3. Verify static directory exists
echo "Step 3: Ensuring static directories exist..."
mkdir -p /app/backend/static/generated
chmod 755 /app/backend/static
chmod 755 /app/backend/static/generated

# 4. Restart backend
echo "Step 4: Restarting backend..."
sudo supervisorctl restart backend
sleep 5

# 5. Restart worker
echo "Step 5: Restarting worker..."
sudo supervisorctl restart worker
sleep 3

# 6. Verify services
echo "Step 6: Verifying services..."
sudo supervisorctl status

# 7. Test static file serving
echo "Step 7: Testing static file serving..."
# Create a test file
echo "test" > /app/backend/static/generated/test.txt
curl -s -o /dev/null -w "Static file test: HTTP %{http_code}\n" http://localhost:8001/api/static/generated/test.txt
rm /app/backend/static/generated/test.txt

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "VERIFICATION STEPS:"
echo "1. Test login: curl -X POST https://www.visionary-suite.com/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"test@test.com\",\"password\":\"test\"}'"
echo "2. Test static files: curl -I https://www.visionary-suite.com/api/static/generated/[filename]"
echo "3. Generate a new GIF and verify download works"
echo ""
echo "IF STATIC FILES STILL 404, ADD THIS TO NGINX:"
echo "location /api/static/ {"
echo "    alias /app/backend/static/;"
echo "    expires 1h;"
echo "    add_header Cache-Control 'public, no-transform';"
echo "}"
