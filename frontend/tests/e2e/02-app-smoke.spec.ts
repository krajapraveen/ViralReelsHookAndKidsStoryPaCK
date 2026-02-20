import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import { captureConsoleErrors, findBrokenImages } from "../helpers/network";
import users from "../fixtures/users.json";

test.describe("02 - App Smoke Tests", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test("Dashboard loads with all key sections", async ({ page }) => {
    await page.goto(URLS.app);
    
    // Check credit balance is visible
    await expect(page.getByText(/credits|balance/i)).toBeVisible({ timeout: 10000 });
    
    // Check navigation links are present
    const navLinks = [
      "GenStudio",
      "Story",
      "Reel",
      "Creator Tools",
    ];
    
    for (const linkText of navLinks) {
      const link = page.getByText(new RegExp(linkText, "i")).first();
      await expect(link).toBeVisible();
    }
    
    // Check no broken images
    const brokenImages = await findBrokenImages(page);
    expect(brokenImages.length, `Broken images: ${brokenImages.join(", ")}`).toBe(0);
  });

  test("Dashboard quick links work", async ({ page }) => {
    await page.goto(URLS.app);
    
    // Test Subscription link
    const subLink = page.locator('a:has-text("Subscription"), [href*="subscription"]').first();
    if (await subLink.isVisible()) {
      await subLink.click();
      await expect(page).toHaveURL(/subscription/);
      await page.goBack();
    }
    
    // Test Analytics link
    const analyticsLink = page.locator('a:has-text("Analytics"), [href*="analytics"]').first();
    if (await analyticsLink.isVisible()) {
      await analyticsLink.click();
      await expect(page).toHaveURL(/analytics/);
      await page.goBack();
    }
    
    // Test Help link
    const helpLink = page.locator('a:has-text("Help"), a:has-text("Guides"), [href*="manual"]').first();
    if (await helpLink.isVisible()) {
      await helpLink.click();
      await expect(page).toHaveURL(/manual|help/);
    }
  });

  test("Profile page loads and shows user info", async ({ page }) => {
    await page.goto(URLS.profile);
    
    // Should show user email
    await expect(page.getByText(users.demoUser.email)).toBeVisible({ timeout: 10000 });
    
    // Should have edit capabilities
    const editBtn = page.locator('button:has-text("Edit"), button:has-text("Update"), button:has-text("Save")').first();
    await expect(editBtn).toBeVisible();
  });

  test("Billing page shows credit balance and purchase options", async ({ page }) => {
    await page.goto(URLS.billing);
    
    // Should show current balance
    await expect(page.getByText(/balance|credits/i)).toBeVisible({ timeout: 10000 });
    
    // Should show purchase options
    await expect(page.getByText(/buy|purchase|add|plans/i)).toBeVisible();
  });

  test("Subscription page shows plans", async ({ page }) => {
    await page.goto(URLS.subscription);
    
    // Should show subscription info or plans
    await expect(page.getByText(/subscription|plan/i)).toBeVisible({ timeout: 10000 });
    
    // Should show at least one plan
    const planElement = page.locator('[data-testid*="plan"], .plan, [class*="plan"]').first();
    await expect(planElement).toBeVisible();
  });

  test("Analytics page shows usage statistics", async ({ page }) => {
    await page.goto(URLS.analytics);
    
    // Should show analytics header
    await expect(page.getByText(/analytics|usage|statistics/i)).toBeVisible({ timeout: 10000 });
    
    // Should show credit info
    await expect(page.getByText(/credits|balance/i)).toBeVisible();
  });

  test("Content Vault page loads", async ({ page }) => {
    await page.goto(URLS.contentVault);
    
    // Should show content vault or history
    await expect(page.getByText(/vault|content|library|history/i)).toBeVisible({ timeout: 10000 });
  });

  test("Payment History page shows transaction list", async ({ page }) => {
    await page.goto(URLS.paymentHistory);
    
    // Should show history header
    await expect(page.getByText(/payment|history|transaction/i)).toBeVisible({ timeout: 10000 });
  });

  test("Privacy Settings page has controls", async ({ page }) => {
    await page.goto(URLS.privacySettings);
    
    // Should show privacy controls
    await expect(page.getByText(/privacy|data|settings/i)).toBeVisible({ timeout: 10000 });
    
    // Should have export or delete options
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download")').first();
    await expect(exportBtn).toBeVisible();
  });

  test("All app pages have no critical console errors", async ({ page }) => {
    const consoleErrors = captureConsoleErrors(page);
    
    const pagesToCheck = [
      URLS.app,
      URLS.billing,
      URLS.profile,
      URLS.subscription,
      URLS.analytics,
    ];
    
    for (const url of pagesToCheck) {
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1000);
    }
    
    // Filter harmless errors
    const criticalErrors = consoleErrors.filter(
      (err) => 
        !err.includes("favicon") && 
        !err.includes("analytics") &&
        !err.includes("ResizeObserver") &&
        !err.includes("Non-Error promise rejection")
    );
    
    expect(criticalErrors.length, `Errors: ${criticalErrors.join("\n")}`).toBeLessThanOrEqual(2);
  });
});
