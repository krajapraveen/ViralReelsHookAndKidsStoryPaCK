import { test, expect } from '@playwright/test';

/**
 * Dashboard E2E Tests
 */
test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@creatorstudio.ai');
    await page.fill('input[type="password"]', 'Cr3@t0rStud!o#2026');
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/app**', { timeout: 10000 });
  });

  test('should display dashboard after login', async ({ page }) => {
    // Check dashboard elements - look for main content area
    await expect(page.locator('main, [data-testid="dashboard"], .dashboard')).toBeVisible({ timeout: 10000 });
  });

  test('should display user credits in header', async ({ page }) => {
    // Credits should be visible somewhere on the page
    await expect(page.locator('text=/credits|credit/i')).toBeVisible({ timeout: 10000 });
  });

  test('should have navigation to all features', async ({ page }) => {
    // Check for feature cards or navigation - just check that some feature names exist
    const features = ['Story', 'Content', 'Caption', 'Comic', 'GIF', 'Coloring'];
    
    for (const feature of features) {
      const element = page.locator(`text=/${feature}/i`).first();
      await expect(element).toBeVisible({ timeout: 5000 });
    }
  });

  test('should navigate to billing page', async ({ page }) => {
    await page.goto('/app/billing');
    
    // Should display pricing
    await expect(page.locator('text=/credits|subscription|pack/i')).toBeVisible({ timeout: 10000 });
  });
});
