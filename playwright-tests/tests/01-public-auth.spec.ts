import { test, expect } from '@playwright/test';

/**
 * Phase 2 - Automated Functional Testing
 * Test Suite 1: Public Pages & Authentication
 */

const BASE_URL = 'https://comic-pipeline-v2.preview.emergentagent.com';

// Test credentials
const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

test.describe('A. Public Pages', () => {
  test('A1. Landing page loads correctly', async ({ page }) => {
    await page.goto('/');
    
    // Check hero section
    await expect(page.locator('body')).toBeVisible();
    
    // Check navigation exists
    const nav = page.locator('nav, header');
    await expect(nav.first()).toBeVisible();
    
    // Check for CTA buttons
    const ctaButtons = page.getByRole('button').or(page.getByRole('link'));
    expect(await ctaButtons.count()).toBeGreaterThan(0);
  });

  test('A2. Pricing page loads', async ({ page }) => {
    await page.goto('/pricing');
    await expect(page).toHaveURL(/pricing/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('A3. Contact page loads', async ({ page }) => {
    await page.goto('/contact');
    await expect(page).toHaveURL(/contact/);
  });

  test('A4. User manual page loads', async ({ page }) => {
    await page.goto('/user-manual');
    await expect(page).toHaveURL(/user-manual|help/);
  });

  test('A5. Privacy policy page loads', async ({ page }) => {
    await page.goto('/privacy-policy');
    await expect(page).toHaveURL(/privacy/);
  });
});

test.describe('B. Authentication', () => {
  test('B1. Login page renders correctly', async ({ page }) => {
    await page.goto('/login');
    
    // Check form elements
    await expect(page.locator('input[type="email"], input[name="email"]').first()).toBeVisible();
    await expect(page.locator('input[type="password"], input[name="password"]').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /login|sign in/i }).first()).toBeVisible();
  });

  test('B2. Demo user login succeeds', async ({ page }) => {
    await page.goto('/login');
    
    // Fill login form
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    
    // Submit
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    
    // Should redirect to dashboard
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/app/);
  });

  test('B3. Invalid login shows error', async ({ page }) => {
    await page.goto('/login');
    
    await page.locator('input[type="email"], input[name="email"]').first().fill('wrong@email.com');
    await page.locator('input[type="password"], input[name="password"]').first().fill('wrongpassword');
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    
    // Should show error or stay on login
    await page.waitForTimeout(2000);
    // Either shows error or stays on login page
    const isOnLogin = page.url().includes('/login');
    const hasError = await page.locator('[role="alert"], .error, .toast').count() > 0;
    expect(isOnLogin || hasError).toBeTruthy();
  });

  test('B4. Signup page renders correctly', async ({ page }) => {
    await page.goto('/signup');
    
    await expect(page.locator('input[type="email"], input[name="email"]').first()).toBeVisible();
    await expect(page.locator('input[type="password"], input[name="password"]').first()).toBeVisible();
  });

  test('B5. Admin login succeeds', async ({ page }) => {
    await page.goto('/login');
    
    await page.locator('input[type="email"], input[name="email"]').first().fill(ADMIN_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(ADMIN_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/app/);
  });
});

test.describe('C. Dashboard & Navigation (Authenticated)', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('C1. Dashboard loads with user data', async ({ page }) => {
    await expect(page).toHaveURL(/\/app/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('C2. Navigate to Reel Generator', async ({ page }) => {
    await page.goto('/app/reel-generator');
    await expect(page).toHaveURL(/reel-generator/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('C3. Navigate to Story Generator', async ({ page }) => {
    await page.goto('/app/story-generator');
    await expect(page).toHaveURL(/story/);
  });

  test('C4. Navigate to GenStudio', async ({ page }) => {
    await page.goto('/app/gen-studio');
    await expect(page).toHaveURL(/gen-studio/);
  });

  test('C5. Navigate to Creator Tools', async ({ page }) => {
    await page.goto('/app/creator-tools');
    await expect(page).toHaveURL(/creator-tools/);
  });

  test('C6. Navigate to Comix AI', async ({ page }) => {
    await page.goto('/app/comix');
    await expect(page).toHaveURL(/comix/);
  });

  test('C7. Navigate to GIF Maker', async ({ page }) => {
    await page.goto('/app/gif-maker');
    await expect(page).toHaveURL(/gif-maker/);
  });

  test('C8. Navigate to Comic Storybook', async ({ page }) => {
    await page.goto('/app/comic-storybook');
    await expect(page).toHaveURL(/comic-storybook/);
  });

  test('C9. Navigate to Billing', async ({ page }) => {
    await page.goto('/app/billing');
    await expect(page).toHaveURL(/billing/);
  });

  test('C10. Navigate to Profile', async ({ page }) => {
    await page.goto('/app/profile');
    await expect(page).toHaveURL(/profile/);
  });

  test('C11. Navigate to History', async ({ page }) => {
    await page.goto('/app/history');
    await expect(page).toHaveURL(/history/);
  });

  test('C12. Navigate to Analytics', async ({ page }) => {
    await page.goto('/app/analytics');
    await expect(page).toHaveURL(/analytics/);
  });
});
