import { test, expect } from '@playwright/test';

/**
 * Authentication E2E Tests
 */
test.describe('Authentication', () => {
  test('should display login page correctly', async ({ page }) => {
    await page.goto('/login');
    
    // Check page elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button:has-text("Login")');
    
    // Should stay on login page or show error (page shouldn't redirect to /app)
    await page.waitForTimeout(3000);
    expect(page.url()).toContain('login');
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'admin@creatorstudio.ai');
    await page.fill('input[type="password"]', 'Cr3@t0rStud!o#2026');
    await page.click('button:has-text("Login")');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*\/app/, { timeout: 10000 });
  });

  test('should display signup page correctly', async ({ page }) => {
    await page.goto('/signup');
    
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});
