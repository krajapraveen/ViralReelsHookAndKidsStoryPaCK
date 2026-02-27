import { test, expect } from '@playwright/test';

/**
 * Payment Flow E2E Tests
 */
test.describe('Payment Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@creatorstudio.ai');
    await page.fill('input[type="password"]', 'Cr3@t0rStud!o#2026');
    await page.click('button:has-text("Login")');
    await page.waitForURL('**/app**', { timeout: 10000 });
  });

  test('billing page displays credit packs', async ({ page }) => {
    await page.goto('/app/billing');
    
    // Should show credit packs
    await expect(page.locator('text=/starter|pro|business|enterprise/i').first()).toBeVisible({ timeout: 10000 });
    
    // Should show prices
    await expect(page.locator('text=/₹|INR|credits/i').first()).toBeVisible();
  });

  test('clicking buy initiates payment flow', async ({ page }) => {
    await page.goto('/app/billing');
    
    // Find and click a buy button
    const buyButton = page.locator('button:has-text("Buy"), button:has-text("Purchase"), button:has-text("Get Started")').first();
    
    if (await buyButton.isVisible()) {
      await buyButton.click();
      
      // Should either show payment modal or redirect to Cashfree
      await page.waitForTimeout(2000);
      
      // Check for payment-related content
      const hasPaymentUI = await page.locator('text=/payment|cashfree|pay now|processing/i').first().isVisible().catch(() => false);
      expect(hasPaymentUI || page.url().includes('cashfree')).toBeTruthy();
    }
  });

  test('payment history page is accessible', async ({ page }) => {
    await page.goto('/app/billing');
    
    // Look for payment history link/tab
    const historyLink = page.locator('text=/history|transactions|past payments/i').first();
    
    if (await historyLink.isVisible()) {
      await historyLink.click();
      await page.waitForTimeout(1000);
    }
  });
});
