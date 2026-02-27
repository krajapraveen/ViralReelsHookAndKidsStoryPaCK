import { test, expect, devices } from '@playwright/test';

/**
 * Mobile Responsiveness E2E Tests
 */
test.use({ ...devices['iPhone 13'] });

test.describe('Mobile Responsiveness', () => {
  test('landing page is mobile responsive', async ({ page }) => {
    await page.goto('/');
    
    // Check that mobile menu exists (hamburger)
    await expect(page.locator('[data-testid="mobile-menu"], button[aria-label*="menu"], .hamburger, svg')).toBeVisible();
    
    // Main content should be visible
    await expect(page.locator('text=/creator|studio|AI/i').first()).toBeVisible();
  });

  test('login page is mobile responsive', async ({ page }) => {
    await page.goto('/login');
    
    // Form should be accessible on mobile
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
  });

  test('dashboard is mobile responsive', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@creatorstudio.ai');
    await page.fill('input[type="password"]', 'Cr3@t0rStud!o#2026');
    await page.click('button:has-text("Login")');
    
    await page.waitForURL('**/app**', { timeout: 10000 });
    
    // Dashboard should render properly
    await expect(page.locator('[data-testid="dashboard"], .dashboard, main')).toBeVisible();
  });
});
