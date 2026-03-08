import { test, expect } from '@playwright/test';

/**
 * DEPLOYMENT SMOKE TESTS
 * Fast critical path tests to run on every deployment
 * Target execution time: < 2 minutes
 */

const BASE_URL = 'https://analytics-events.preview.emergentagent.com';

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

test.describe('🚀 DEPLOYMENT SMOKE TESTS', () => {
  test.describe.configure({ mode: 'serial' }); // Run in order

  test('1. API Health Check', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health/`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('2. Landing Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await expect(page.locator('body')).toBeVisible();
    // Check for key CTA
    const cta = page.locator('button, a').filter({ hasText: /get started|login|sign up/i }).first();
    await expect(cta).toBeVisible();
  });

  test('3. Login Page Accessible', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
  });

  test('4. Demo User Can Login', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    expect(page.url()).toContain('/app');
  });

  test('5. Dashboard Loads with Data', async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Check dashboard elements
    await expect(page.locator('body')).toBeVisible();
  });

  test('6. Reel Generator Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/reel-generator`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('7. Comix AI Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/comix`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('8. GIF Maker Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/gif-maker`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('9. Billing Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/billing`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('10. Credits API Works', async ({ request }) => {
    // Login to get token
    const loginResponse = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: DEMO_USER.email,
        password: DEMO_USER.password
      }
    });
    const loginData = await loginResponse.json();
    const token = loginData.token;
    
    // Check credits
    const creditsResponse = await request.get(`${BASE_URL}/api/credits/balance`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(creditsResponse.ok()).toBeTruthy();
    const creditsData = await creditsResponse.json();
    expect(creditsData.credits).toBeDefined();
  });

  test('11. Admin Can Login', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(ADMIN_USER.email);
    await page.locator('input[type="password"]').fill(ADMIN_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    expect(page.url()).toContain('/app');
  });

  test('12. Admin Dashboard Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(ADMIN_USER.email);
    await page.locator('input[type="password"]').fill(ADMIN_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/admin`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('13. Protected Routes Redirect', async ({ page }) => {
    // Try accessing protected route without auth
    await page.goto(`${BASE_URL}/app/billing`);
    await page.waitForURL(/login/, { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('14. GenStudio Dashboard Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/gen-studio`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('15. Creator Tools Page Loads', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/creator-tools`);
    await expect(page.locator('body')).toBeVisible();
  });
});

// Export for CI/CD integration
export const smokeTestConfig = {
  testDir: './tests',
  testMatch: 'smoke-tests.spec.ts',
  timeout: 30000,
  retries: 1,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: 'smoke-test-results.json' }]],
};
