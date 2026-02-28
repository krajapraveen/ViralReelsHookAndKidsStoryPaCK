import { test, expect } from '@playwright/test';

/**
 * API Integration E2E Tests
 */
test.describe('API Endpoints', () => {
  const baseURL = process.env.REACT_APP_BACKEND_URL || 'https://worker-scaling.preview.emergentagent.com';

  test('health endpoint returns 200', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/health/`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('products endpoint returns products', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/cashfree/products`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.products).toBeDefined();
    expect(Object.keys(data.products).length).toBeGreaterThan(0);
  });

  test('coloring book styles endpoint works', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/coloring-book/styles`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.styles).toBeDefined();
  });

  test('gif maker templates endpoint works', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/gif-maker/templates`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.templates).toBeDefined();
  });

  test('login returns token for valid credentials', async ({ request }) => {
    const response = await request.post(`${baseURL}/api/auth/login`, {
      data: {
        email: 'admin@creatorstudio.ai',
        password: 'Cr3@t0rStud!o#2026'
      }
    });
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.token).toBeDefined();
  });

  test('protected endpoint requires auth', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/wallet/me`);
    expect(response.status()).toBe(401);
  });
});
