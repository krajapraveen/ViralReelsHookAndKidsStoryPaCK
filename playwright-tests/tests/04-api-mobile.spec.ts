import { test, expect } from '@playwright/test';

/**
 * Phase 2 - Automated Functional Testing
 * Test Suite 4: API Tests & Mobile Responsiveness
 */

const BASE_URL = 'https://ui-consistency-pass-2.preview.emergentagent.com';

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

test.describe('N. API Health & Status', () => {
  test('N1. Health endpoint returns OK', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('N2. Root endpoint returns API info', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/`);
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('O. Authentication API', () => {
  test('O1. Login API returns token', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: DEMO_USER.email,
        password: DEMO_USER.password
      }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.token).toBeDefined();
    expect(data.user).toBeDefined();
  });

  test('O2. Login API rejects invalid credentials', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: 'wrong@email.com',
        password: 'wrongpassword'
      }
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('O3. Admin login API returns token', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: ADMIN_USER.email,
        password: ADMIN_USER.password
      }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.token).toBeDefined();
    expect(data.user.role).toBe('ADMIN');
  });

  test('O4. Protected endpoint rejects without token', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/credits/balance`);
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('O5. Protected endpoint works with token', async ({ request }) => {
    // First login
    const loginResponse = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: DEMO_USER.email,
        password: DEMO_USER.password
      }
    });
    const loginData = await loginResponse.json();
    const token = loginData.token;

    // Then access protected endpoint
    const response = await request.get(`${BASE_URL}/api/credits/balance`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.credits).toBeDefined();
  });
});

test.describe('P. Admin API Access Control', () => {
  let adminToken: string;
  let userToken: string;

  test.beforeAll(async ({ request }) => {
    // Get admin token
    const adminLogin = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: ADMIN_USER.email,
        password: ADMIN_USER.password
      }
    });
    const adminData = await adminLogin.json();
    adminToken = adminData.token;

    // Get user token
    const userLogin = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: DEMO_USER.email,
        password: DEMO_USER.password
      }
    });
    const userData = await userLogin.json();
    userToken = userData.token;
  });

  test('P1. Admin can access realtime-analytics', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/realtime-analytics/snapshot`, {
      headers: {
        'Authorization': `Bearer ${adminToken}`
      }
    });
    expect(response.ok()).toBeTruthy();
  });

  test('P2. Admin can access live-stats', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/realtime-analytics/live-stats`, {
      headers: {
        'Authorization': `Bearer ${adminToken}`
      }
    });
    expect(response.ok()).toBeTruthy();
  });

  test('P3. Non-admin blocked from admin endpoints', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/realtime-analytics/snapshot`, {
      headers: {
        'Authorization': `Bearer ${userToken}`
      }
    });
    // Should return 403 or similar
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });
});

test.describe('Q. Mobile Responsiveness - 375px (iPhone SE)', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('Q1. Landing page mobile layout', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    
    // No horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
  });

  test('Q2. Login page mobile layout', async ({ page }) => {
    await page.goto('/login');
    
    // Form should be visible
    await expect(page.locator('input[type="email"], input[name="email"]').first()).toBeVisible();
    
    // Button should be tappable size
    const button = page.getByRole('button', { name: /login|sign in/i }).first();
    const buttonBox = await button.boundingBox();
    if (buttonBox) {
      expect(buttonBox.height).toBeGreaterThanOrEqual(44); // Min touch target
    }
  });

  test('Q3. Dashboard mobile layout', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await expect(page.locator('body')).toBeVisible();
    
    // Check no horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
  });

  test('Q4. Comix AI mobile layout', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto('/app/comix');
    await expect(page.locator('body')).toBeVisible();
  });

  test('Q5. GIF Maker mobile layout', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto('/app/gif-maker');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('R. Mobile Responsiveness - 768px (Tablet)', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('R1. Dashboard tablet layout', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await expect(page.locator('body')).toBeVisible();
  });

  test('R2. Creator Tools tablet layout', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto('/app/creator-tools');
    await expect(page.locator('body')).toBeVisible();
  });

  test('R3. GenStudio tablet layout', async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto('/app/gen-studio');
    await expect(page.locator('body')).toBeVisible();
  });
});
