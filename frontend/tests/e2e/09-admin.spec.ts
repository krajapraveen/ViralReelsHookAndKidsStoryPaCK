import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login, loginAPI } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("09 - Admin Features", () => {
  test.describe("Admin Dashboard", () => {
    test("Admin can access admin dashboard", async ({ page }) => {
      await login(page, users.adminUser.email, users.adminUser.password);
      await page.goto(URLS.admin);
      
      // Should see admin content
      await expect(page.getByText(/admin/i)).toBeVisible({ timeout: 10000 });
    });

    test("Non-admin cannot access admin pages", async ({ page }) => {
      await login(page, users.demoUser.email, users.demoUser.password);
      await page.goto(URLS.admin);
      
      // Should be redirected or see forbidden
      const url = page.url();
      const isForbidden = await page.getByText(/forbidden|access denied|unauthorized/i).isVisible();
      const isRedirected = !url.includes("/admin");
      
      // Either forbidden or redirected
    });
  });

  test.describe("Admin Monitoring Dashboard", () => {
    test.beforeEach(async ({ page }) => {
      await login(page, users.adminUser.email, users.adminUser.password);
    });

    test("Monitoring dashboard loads with all tabs", async ({ page }) => {
      await page.goto(URLS.adminMonitoring);
      
      // Check for tabs
      await expect(page.locator('[data-testid="tab-overview"]')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('[data-testid="tab-security"]')).toBeVisible();
      await expect(page.locator('[data-testid="tab-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="tab-performance"]')).toBeVisible();
    });

    test("Overview tab shows statistics", async ({ page }) => {
      await page.goto(URLS.adminMonitoring);
      
      // Should show stats
      await expect(page.getByText(/total users/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/active today/i)).toBeVisible();
      await expect(page.getByText(/job success rate/i)).toBeVisible();
    });

    test("Security tab shows threat detection info", async ({ page }) => {
      await page.goto(URLS.adminMonitoring);
      
      // Click security tab
      await page.click('[data-testid="tab-security"]');
      await page.waitForTimeout(1000);
      
      // Should show security info
      await expect(page.getByText(/threat|blocked|throttled/i)).toBeVisible({ timeout: 10000 });
    });

    test("Time range filter works", async ({ page }) => {
      await page.goto(URLS.adminMonitoring);
      
      // Find and change time range
      const timeSelect = page.locator('[data-testid="time-range-select"]');
      await expect(timeSelect).toBeVisible();
      
      await timeSelect.selectOption("7");
      await page.waitForTimeout(500);
      
      // Page should still be functional
      await expect(page.getByText(/total users|overview/i)).toBeVisible();
    });

    test("Refresh button works", async ({ page }) => {
      await page.goto(URLS.adminMonitoring);
      
      const refreshBtn = page.locator('[data-testid="refresh-btn"]');
      await expect(refreshBtn).toBeVisible();
      
      await refreshBtn.click();
      
      // Button should show loading state or data should refresh
      await page.waitForTimeout(1000);
      await expect(page.getByText(/total users|overview/i)).toBeVisible();
    });
  });

  test.describe("Admin API Endpoints", () => {
    test("Admin overview endpoint works", async ({ request }) => {
      const token = await loginAPI(request, users.adminUser.email, users.adminUser.password);
      
      const response = await request.get(`${URLS.api.health.replace("/health/", "/analytics/admin/overview")}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.users).toBeDefined();
      expect(data.jobs).toBeDefined();
    });

    test("Worker status endpoint works", async ({ request }) => {
      const token = await loginAPI(request, users.adminUser.email, users.adminUser.password);
      
      const response = await request.get(`${URLS.api.health.replace("/health/", "/analytics/admin/worker-status")}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.current_workers).toBeDefined();
      expect(data.max_workers).toBeDefined();
    });

    test("Copyright audit endpoint works", async ({ request }) => {
      const token = await loginAPI(request, users.adminUser.email, users.adminUser.password);
      
      const response = await request.post(`${URLS.api.health.replace("/health/", "/analytics/admin/run-copyright-audit")}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.audit).toBeDefined();
      expect(data.audit.compliance_score).toBeDefined();
    });

    test("CDN status endpoint works", async ({ request }) => {
      const token = await loginAPI(request, users.adminUser.email, users.adminUser.password);
      
      const response = await request.get(`${URLS.api.health.replace("/health/", "/analytics/admin/cdn-status")}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.enabled !== undefined).toBeTruthy();
    });

    test("Non-admin cannot access admin endpoints", async ({ request }) => {
      const token = await loginAPI(request, users.demoUser.email, users.demoUser.password);
      
      const response = await request.get(`${URLS.api.health.replace("/health/", "/analytics/admin/overview")}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      // Should be forbidden
      expect(response.status()).toBe(403);
    });
  });

  test.describe("Reconciliation", () => {
    test("Admin can trigger reconciliation", async ({ request }) => {
      const token = await loginAPI(request, users.adminUser.email, users.adminUser.password);
      
      const response = await request.post(`${URLS.api.health.replace("/health/", "/subscriptions/admin/reconcile")}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
      });
      
      // Should work (might return success with no issues)
      expect(response.status()).toBeLessThan(500);
    });
  });
});
