# Production 502 Error - Root Cause Analysis

## Issue Summary
API endpoints on production (visionary-suite.com) return 502 Bad Gateway errors.

## Root Cause
The nginx/Cloudflare configuration is redirecting API requests incorrectly:

```
Request: https://visionary-suite.com/api/health
Redirects to: http://visionary-suite.com:8080/api/health/
```

### Problems Identified:
1. **Port Exposure**: Redirecting to port 8080 (backend port) instead of proxying
2. **Protocol Downgrade**: HTTPS → HTTP redirect (security issue)
3. **Trailing Slash**: Adding unnecessary trailing slash

## Expected Behavior
API requests should be proxied to the backend, not redirected:
- `https://visionary-suite.com/api/*` → proxy to `localhost:8001/api/*`

## Fix Required (Server-Side)

### Nginx Configuration Fix
```nginx
server {
    listen 443 ssl;
    server_name visionary-suite.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API - Proxy to backend (NOT redirect)
    location /api/ {
        proxy_pass http://localhost:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
    }
}
```

### Cloudflare Configuration
1. Ensure SSL/TLS is set to "Full (strict)"
2. Disable any Page Rules that redirect /api/* paths
3. Check Transform Rules for unwanted redirects

## Verification Steps
After fix is applied:
```bash
curl -s "https://visionary-suite.com/api/health"
# Should return: {"status":"healthy",...}
```

## Current Workaround
The frontend works because browser requests go through the same origin and don't trigger the redirect. Only direct API calls (curl, Postman) are affected.

## Status
- **Preview Environment**: Working correctly
- **Production**: Requires server configuration fix
- **Impact**: Direct API testing, webhooks, external integrations may fail

---
Created: 2026-02-28
