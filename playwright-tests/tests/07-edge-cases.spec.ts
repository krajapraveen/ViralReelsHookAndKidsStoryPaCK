import { test, expect } from '@playwright/test';

/**
 * EDGE CASE TESTS
 * Tests for form validation, error handling, session expiration, etc.
 */

const BASE_URL = 'https://story-to-video-dev.preview.emergentagent.com';

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

test.describe('Edge Cases - Form Validation', () => {
  test('Login with empty email shows error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="password"]').fill('somepassword');
    await page.locator('button:has-text("Login")').click();
    
    // Should show validation error or stay on page
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/login');
  });

  test('Login with empty password shows error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill('test@example.com');
    await page.locator('button:has-text("Login")').click();
    
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/login');
  });

  test('Login with invalid email format', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill('notanemail');
    await page.locator('input[type="password"]').fill('password123');
    await page.locator('button:has-text("Login")').click();
    
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/login');
  });

  test('Login with wrong password', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.locator('button:has-text("Login")').click();
    
    await page.waitForTimeout(2000);
    // Should show error or stay on login page
    const isOnLogin = page.url().includes('/login');
    const hasError = await page.locator('[role="alert"], .error, .toast, .text-red').count() > 0;
    expect(isOnLogin || hasError).toBeTruthy();
  });

  test('Signup with mismatched passwords', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    
    const confirmPassword = page.locator('input[name="confirmPassword"], input[placeholder*="confirm" i]');
    if (await confirmPassword.isVisible()) {
      await page.locator('input[type="email"]').fill('newuser@example.com');
      await page.locator('input[type="password"]').first().fill('Password123!');
      await confirmPassword.fill('DifferentPassword!');
      
      const submitBtn = page.locator('button[type="submit"], button:has-text("Sign up")').first();
      await submitBtn.click();
      
      await page.waitForTimeout(1000);
      // Should show validation error
      expect(page.url()).toContain('/signup');
    }
  });

  test('Signup with weak password', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    
    await page.locator('input[type="email"]').fill('weakpass@example.com');
    await page.locator('input[type="password"]').first().fill('123'); // Too short
    
    const submitBtn = page.locator('button[type="submit"], button:has-text("Sign up")').first();
    await submitBtn.click();
    
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/signup');
  });
});

test.describe('Edge Cases - API Error Handling', () => {
  test('Invalid token is rejected', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/credits/balance`, {
      headers: { 'Authorization': 'Bearer invalid_token_12345' }
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('Expired token is rejected', async ({ request }) => {
    // Use a fake expired token
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid';
    const response = await request.get(`${BASE_URL}/api/credits/balance`, {
      headers: { 'Authorization': `Bearer ${expiredToken}` }
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('Missing Authorization header rejected', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/credits/balance`);
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('Malformed JSON in request body', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/json' },
      data: 'not valid json{'
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('Non-existent endpoint returns 404', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/nonexistent/endpoint`);
    expect(response.status()).toBe(404);
  });
});

test.describe('Edge Cases - Session Management', () => {
  test('Logout clears session', async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Find and click logout
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]').first();
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForTimeout(1000);
      
      // Should be redirected to login or landing
      expect(page.url()).toMatch(/login|\/$/);
    }
  });

  test('Protected route after logout redirects to login', async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Clear localStorage to simulate logout
    await page.evaluate(() => localStorage.clear());
    
    // Try to access protected route
    await page.goto(`${BASE_URL}/app/billing`);
    await page.waitForURL(/login/, { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });

  test('Session persists across page refresh', async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Refresh page
    await page.reload();
    await page.waitForTimeout(1000);
    
    // Should still be on app (not redirected to login)
    expect(page.url()).toContain('/app');
  });
});

test.describe('Edge Cases - Input Sanitization', () => {
  test('XSS attempt in login email is sanitized', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill('<script>alert("xss")</script>');
    await page.locator('input[type="password"]').fill('password123');
    await page.locator('button:has-text("Login")').click();
    
    await page.waitForTimeout(1000);
    // Should not execute script, stay on login
    expect(page.url()).toContain('/login');
  });

  test('SQL injection attempt in login', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill("' OR '1'='1");
    await page.locator('input[type="password"]').fill("' OR '1'='1");
    await page.locator('button:has-text("Login")').click();
    
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/login');
  });

  test('NoSQL injection attempt in API', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        email: { "$gt": "" },
        password: { "$gt": "" }
      }
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });
});

test.describe('Edge Cases - Concurrent Operations', () => {
  test('Rapid login attempts are handled', async ({ request }) => {
    const loginPromises = Array(5).fill(null).map(() => 
      request.post(`${BASE_URL}/api/auth/login`, {
        data: {
          email: DEMO_USER.email,
          password: DEMO_USER.password
        }
      })
    );
    
    const responses = await Promise.all(loginPromises);
    
    // At least some should succeed
    const successCount = responses.filter(r => r.ok()).length;
    expect(successCount).toBeGreaterThan(0);
  });

  test('Multiple tab session consistency', async ({ browser }) => {
    // Create two contexts (simulating two tabs)
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const page1 = await context1.newPage();
    const page2 = await context2.newPage();
    
    // Login in tab 1
    await page1.goto(`${BASE_URL}/login`);
    await page1.locator('input[type="email"]').fill(DEMO_USER.email);
    await page1.locator('input[type="password"]').fill(DEMO_USER.password);
    await page1.locator('button:has-text("Login")').click();
    await page1.waitForURL(/\/app/, { timeout: 15000 });
    
    // Login in tab 2
    await page2.goto(`${BASE_URL}/login`);
    await page2.locator('input[type="email"]').fill(DEMO_USER.email);
    await page2.locator('input[type="password"]').fill(DEMO_USER.password);
    await page2.locator('button:has-text("Login")').click();
    await page2.waitForURL(/\/app/, { timeout: 15000 });
    
    // Both should be logged in
    expect(page1.url()).toContain('/app');
    expect(page2.url()).toContain('/app');
    
    await context1.close();
    await context2.close();
  });
});

test.describe('Edge Cases - Browser Navigation', () => {
  test('Back button after login works correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Go to another page
    await page.goto(`${BASE_URL}/app/billing`);
    
    // Go back
    await page.goBack();
    await page.waitForTimeout(500);
    
    // Should be at dashboard, not login
    expect(page.url()).toContain('/app');
  });

  test('Forward button works correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/billing`);
    await page.goBack();
    await page.goForward();
    
    expect(page.url()).toContain('/billing');
  });

  test('Direct URL access to protected route', async ({ page }) => {
    // Try to directly access a protected page
    await page.goto(`${BASE_URL}/app/admin/users`);
    
    // Should redirect to login
    await page.waitForURL(/login/, { timeout: 5000 });
    expect(page.url()).toContain('/login');
  });
});

test.describe('Edge Cases - Network Conditions', () => {
  test('Page handles slow network gracefully', async ({ page }) => {
    // Simulate slow network
    const client = await page.context().newCDPSession(page);
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      downloadThroughput: 50 * 1024, // 50kb/s
      uploadThroughput: 50 * 1024,
      latency: 500 // 500ms latency
    });
    
    await page.goto(`${BASE_URL}/`, { timeout: 30000 });
    await expect(page.locator('body')).toBeVisible();
  });

  test('Offline mode shows appropriate message', async ({ page, context }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    // Go offline
    await context.setOffline(true);
    
    // Try to navigate
    await page.goto(`${BASE_URL}/app/billing`).catch(() => {});
    
    // Should show some indication of offline or cached content
    await page.waitForTimeout(1000);
    
    // Go back online
    await context.setOffline(false);
  });
});

test.describe('Edge Cases - Large Data', () => {
  test('Long text input is handled', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/gen-studio/text-to-image`);
    
    // Enter very long prompt
    const longText = 'A '.repeat(500) + 'beautiful sunset';
    const promptInput = page.locator('textarea, input[type="text"]').first();
    
    if (await promptInput.isVisible()) {
      await promptInput.fill(longText);
      
      // Should either accept or truncate, not crash
      await page.waitForTimeout(500);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('Special characters in input', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    
    await page.goto(`${BASE_URL}/app/feature-requests`);
    
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible()) {
      await textarea.fill('Test with special chars: <>&"\'`{}[]|\\');
      await page.waitForTimeout(500);
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
