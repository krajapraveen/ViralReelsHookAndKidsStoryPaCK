# Cloudflare Worker Setup Guide
## API Reverse Proxy for visionary-suite.com

This guide will help you set up a Cloudflare Worker to proxy all `/api/*` requests to your Emergent backend.

---

## Step 1: Access Cloudflare Dashboard

1. Go to [https://dash.cloudflare.com](https://dash.cloudflare.com)
2. Log in with your account
3. Select your domain: **visionary-suite.com**

---

## Step 2: Create the Worker

1. In the left sidebar, click **"Workers & Pages"**
2. Click **"Create application"**
3. Click **"Create Worker"**
4. Name it: `api-proxy` (or any name you prefer)
5. Click **"Deploy"** (we'll edit the code next)

---

## Step 3: Edit the Worker Code

1. After creating, click **"Edit code"** or go to the worker and click **"Quick edit"**
2. **Delete all the default code**
3. **Copy and paste this code:**

```javascript
/**
 * Cloudflare Worker - API Reverse Proxy
 * CreatorStudio AI (visionary-suite.com)
 */

const BACKEND_URL = 'https://blog-seo-posts.preview.emergentagent.com';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Handle OPTIONS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
          'Access-Control-Max-Age': '86400'
        }
      });
    }
    
    // Check if this is an API request
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/api')) {
      return handleApiRequest(request, url);
    }
    
    // For non-API requests, pass through to origin
    return fetch(request);
  }
};

async function handleApiRequest(request, url) {
  const backendUrl = new URL(url.pathname + url.search, BACKEND_URL);
  
  const headers = new Headers(request.headers);
  headers.set('X-Forwarded-Host', url.hostname);
  headers.set('X-Forwarded-Proto', 'https');
  headers.set('X-Real-IP', request.headers.get('CF-Connecting-IP') || '');
  
  try {
    const response = await fetch(backendUrl.toString(), {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
    });
    
    const newResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    });
    
    newResponse.headers.set('Access-Control-Allow-Origin', '*');
    newResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH');
    newResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    
    return newResponse;
    
  } catch (error) {
    return new Response(JSON.stringify({
      error: 'Backend connection failed',
      message: error.message
    }), {
      status: 502,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
}
```

4. Click **"Save and deploy"**

---

## Step 4: Add Route to Your Domain

1. Go back to **Workers & Pages** in the sidebar
2. Click on your worker (`api-proxy`)
3. Go to **"Settings"** tab → **"Triggers"**
4. Under **"Routes"**, click **"Add route"**
5. Enter the route pattern:
   ```
   visionary-suite.com/api/*
   ```
6. Select Zone: **visionary-suite.com**
7. Click **"Add route"**

---

## Step 5: Verify It Works

After setup, test with:

```bash
# Test health endpoint
curl -s "https://visionary-suite.com/api/health"

# Expected response:
# {"status":"healthy","timestamp":"...","version":"preview-dev","commit":"unknown"}
```

You can also test in your browser:
- Open: `https://visionary-suite.com/api/health`
- Should see JSON response (not 502 error)

---

## Step 6: Test Payment Webhook

```bash
# Test that the webhook endpoint is reachable
curl -s -X POST "https://visionary-suite.com/api/cashfree/webhook" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## Troubleshooting

### Still getting 502?
- Make sure the route is active (check Workers → Routes)
- Verify the worker is deployed (green checkmark)
- Check worker logs in Cloudflare dashboard

### CORS errors?
- The worker already handles CORS
- Clear browser cache and try again

### Worker not triggering?
- Ensure route pattern is exactly: `visionary-suite.com/api/*`
- Check that the zone is selected correctly

---

## Summary

After completing these steps:
- ✅ All `/api/*` requests will be proxied to Emergent backend
- ✅ Payment webhooks will work correctly
- ✅ Users will receive credits after payment
- ✅ No changes needed to GoDaddy

---

## Quick Reference

| Setting | Value |
|---------|-------|
| Worker Name | `api-proxy` |
| Route | `visionary-suite.com/api/*` |
| Backend URL | `https://blog-seo-posts.preview.emergentagent.com` |
| Zone | `visionary-suite.com` |

---

Created: 2026-02-28
