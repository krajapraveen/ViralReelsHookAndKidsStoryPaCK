/**
 * Cloudflare Worker - API Reverse Proxy
 * CreatorStudio AI (visionary-suite.com)
 * 
 * This worker proxies all /api/* requests to the Emergent backend
 * while serving frontend requests from the origin (GoDaddy)
 */

// Configuration
const BACKEND_URL = 'https://story-video-builder.preview.emergentagent.com';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Check if this is an API request
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/api')) {
      return handleApiRequest(request, url);
    }
    
    // For non-API requests, pass through to origin (GoDaddy)
    return fetch(request);
  }
};

async function handleApiRequest(request, url) {
  // Build the backend URL
  const backendUrl = new URL(url.pathname + url.search, BACKEND_URL);
  
  // Clone the request with the new URL
  const modifiedRequest = new Request(backendUrl.toString(), {
    method: request.method,
    headers: request.headers,
    body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
    redirect: 'follow'
  });
  
  // Add/modify headers for the backend
  const headers = new Headers(modifiedRequest.headers);
  headers.set('X-Forwarded-Host', url.hostname);
  headers.set('X-Forwarded-Proto', 'https');
  headers.set('X-Real-IP', request.headers.get('CF-Connecting-IP') || '');
  
  try {
    // Make the request to the backend
    const response = await fetch(backendUrl.toString(), {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
    });
    
    // Clone the response and add CORS headers
    const modifiedResponse = new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    });
    
    // Add CORS headers for browser requests
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');
    modifiedResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH');
    modifiedResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    modifiedResponse.headers.set('Access-Control-Max-Age', '86400');
    
    return modifiedResponse;
    
  } catch (error) {
    // Return error response
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

// Handle OPTIONS preflight requests
export async function handleOptions(request) {
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
