import { test, expect } from "@playwright/test";
import { URLS, PUBLIC_URLS } from "../fixtures/urls";
import { captureConsoleErrors, findBrokenImages } from "../helpers/network";

test.describe("00 - Public Pages", () => {
  test("All public pages load without console errors", async ({ page }) => {
    const consoleErrors = captureConsoleErrors(page);

    for (const url of PUBLIC_URLS) {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await expect(page).toHaveTitle(/.+/);
      
      // Check page is not blank
      const body = page.locator("body");
      await expect(body).toBeVisible();
    }

    // Filter known harmless errors
    const criticalErrors = consoleErrors.filter(
      (err) => !err.includes("favicon") && !err.includes("analytics")
    );
    expect(criticalErrors, `Console errors: ${criticalErrors.join("\n")}`).toHaveLength(0);
  });

  test("Landing page has all key elements", async ({ page }) => {
    await page.goto(URLS.landing);
    
    // Check navigation
    await expect(page.locator('[data-testid="nav-pricing-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-help-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-login-btn"]')).toBeVisible();
    
    // Check main CTA
    const ctaButton = page.locator('button:has-text("Get Started"), a:has-text("Get Started")').first();
    await expect(ctaButton).toBeVisible();
    
    // Check no broken images
    const brokenImages = await findBrokenImages(page);
    expect(brokenImages.length, `Broken images: ${brokenImages.join(", ")}`).toBe(0);
  });

  test("Pricing page displays plans", async ({ page }) => {
    await page.goto(URLS.pricing);
    
    // Should show pricing plans
    await expect(page.getByText(/pricing|plans/i)).toBeVisible();
    
    // Should have at least one plan card
    const planCards = page.locator('[data-testid*="plan"], .plan-card, [class*="pricing"]');
    await expect(planCards.first()).toBeVisible({ timeout: 10000 });
  });

  test("User Manual page loads with content", async ({ page }) => {
    await page.goto(URLS.userManual);
    
    // Check header
    await expect(page.getByText(/user manual|help/i)).toBeVisible();
    
    // Check search input
    const searchInput = page.locator('input[placeholder*="search" i], input[type="search"]');
    await expect(searchInput).toBeVisible();
    
    // Check feature guides section
    await expect(page.getByText(/feature guides|features/i)).toBeVisible();
  });

  test("Privacy Policy page exists and has content", async ({ page }) => {
    await page.goto(URLS.privacy);
    
    await expect(page.getByText(/privacy/i)).toBeVisible();
    // Should have substantial content
    const content = await page.locator("main, article, .content").textContent();
    expect(content?.length).toBeGreaterThan(100);
  });

  test("Contact page has form elements", async ({ page }) => {
    await page.goto(URLS.contact);
    
    // Should have contact form or contact info
    const hasForm = await page.locator('form, input[type="email"], textarea').isVisible();
    const hasContactInfo = await page.getByText(/email|phone|support/i).isVisible();
    
    expect(hasForm || hasContactInfo).toBeTruthy();
  });

  test("All public page links are valid", async ({ page }) => {
    for (const url of [URLS.landing, URLS.userManual, URLS.pricing]) {
      await page.goto(url, { waitUntil: "domcontentloaded" });
      
      const links = await page.locator("a[href]").all();
      for (const link of links.slice(0, 20)) { // Check first 20 links per page
        const href = await link.getAttribute("href");
        if (!href || href.startsWith("mailto:") || href.startsWith("tel:") || href.startsWith("#")) continue;
        if (href.startsWith("http") && !href.includes(URLS.landing.split("//")[1]?.split("/")[0])) continue;

        const target = href.startsWith("http") ? href : new URL(href, url).toString();
        const resp = await page.request.get(target);
        expect(resp.status(), `Broken link on ${url}: ${target}`).toBeLessThan(400);
      }
    }
  });
});
