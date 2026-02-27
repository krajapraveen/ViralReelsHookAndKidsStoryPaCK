import { test, expect } from '@playwright/test';

/**
 * Feature Pages E2E Tests
 */
test.describe('Feature Pages', () => {
  test.use({ storageState: './e2e/.auth/admin.json' });

  test('Story Episode Creator loads correctly', async ({ page }) => {
    await page.goto('/app/story-episode-creator');
    
    // Check for wizard or form elements
    await expect(page.locator('text=/story|episode|series/i').first()).toBeVisible({ timeout: 10000 });
    
    // Should have content policy
    await expect(page.locator('text=/content policy|copyright/i')).toBeVisible();
  });

  test('Content Challenge Planner loads correctly', async ({ page }) => {
    await page.goto('/app/content-challenge-planner');
    
    await expect(page.locator('text=/challenge|content|planner/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('Caption Rewriter Pro loads correctly', async ({ page }) => {
    await page.goto('/app/caption-rewriter');
    
    await expect(page.locator('text=/caption|rewrite/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('Photo to Comic loads correctly', async ({ page }) => {
    await page.goto('/app/photo-to-comic');
    
    await expect(page.locator('text=/photo|comic|avatar/i').first()).toBeVisible({ timeout: 10000 });
    
    // Should have content policy
    await expect(page.locator('text=/content policy|copyright/i')).toBeVisible();
  });

  test('Comic Story Book Builder loads correctly', async ({ page }) => {
    await page.goto('/app/comic-storybook');
    
    await expect(page.locator('text=/comic|story|book/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('GIF Maker loads correctly', async ({ page }) => {
    await page.goto('/app/gif-maker');
    
    await expect(page.locator('text=/gif|reaction/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('Coloring Book Creator loads correctly', async ({ page }) => {
    await page.goto('/app/coloring-book');
    
    await expect(page.locator('text=/coloring|book/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('Blueprint Library loads correctly', async ({ page }) => {
    await page.goto('/app/blueprint-library');
    
    await expect(page.locator('text=/blueprint|library|content/i').first()).toBeVisible({ timeout: 10000 });
  });
});
