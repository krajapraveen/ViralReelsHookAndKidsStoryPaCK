import { test, expect } from '@playwright/test';

/**
 * Dashboard E2E Tests
 */
test.describe('Dashboard', () => {
  test.use({ storageState: './e2e/.auth/admin.json' });

  test('should display dashboard after login', async ({ page }) => {
    await page.goto('/app');
    
    // Check dashboard elements
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible({ timeout: 10000 });
  });

  test('should display user credits in header', async ({ page }) => {
    await page.goto('/app');
    
    // Credits should be visible
    await expect(page.locator('text=/credits|credit/i')).toBeVisible({ timeout: 10000 });
  });

  test('should have navigation to all features', async ({ page }) => {
    await page.goto('/app');
    
    // Check for feature cards or navigation
    const features = [
      'Story Episode',
      'Content Challenge',
      'Caption',
      'Photo to Comic',
      'Comic',
      'GIF',
      'Coloring'
    ];
    
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
