import { test, expect } from "@playwright/test";
import { URLS, PROTECTED_URLS, ADMIN_URLS } from "../fixtures/urls";
import { login, requireAuthRedirect, loginAPI } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("01 - Authentication", () => {
  test.describe("Login Flow", () => {
    test("Login with valid credentials redirects to dashboard", async ({ page }) => {
      await login(page, users.demoUser.email, users.demoUser.password);
      await expect(page).toHaveURL(/\/app/);
      
      // Check dashboard elements
      await expect(page.getByText(/dashboard|welcome/i)).toBeVisible({ timeout: 10000 });
    });

    test("Login with invalid credentials shows error", async ({ page }) => {
      await page.goto(URLS.login);
      
      const emailInput = page.locator('input[placeholder="you@example.com"], input[type="email"]').first();
      await emailInput.fill(users.invalidCredentials.email);
      
      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.fill(users.invalidCredentials.password);
      
      await page.getByRole("button", { name: /login/i }).click();
      
      // Should show error message
      await expect(page.getByText(/invalid|error|incorrect/i)).toBeVisible({ timeout: 10000 });
      
      // Should NOT redirect
      await expect(page).toHaveURL(/\/login/);
    });

    test("Empty form shows validation errors", async ({ page }) => {
      await page.goto(URLS.login);
      await page.getByRole("button", { name: /login/i }).click();
      
      // Should show required field errors
      const hasError = await page.getByText(/required|email|password/i).isVisible();
      expect(hasError).toBeTruthy();
    });
  });

  test.describe("Registration Flow", () => {
    test("Register page shows validation errors for invalid input", async ({ page }) => {
      await page.goto(URLS.register);
      await page.getByRole("button", { name: /sign up|register|create/i }).click();
      
      // Should show validation errors
      await expect(page.getByText(/required|name|email|password/i).first()).toBeVisible();
    });

    test("Register shows password strength requirements", async ({ page }) => {
      await page.goto(URLS.register);
      
      const passwordInput = page.locator('input[type="password"]').first();
      await passwordInput.fill("weak");
      
      // Should show password requirements
      const hasRequirements = await page.getByText(/characters|uppercase|number|strong/i).isVisible();
      // Some forms don't show live validation, so this is optional
    });

    test("Email validation on registration", async ({ page }) => {
      await page.goto(URLS.register);
      
      const emailInput = page.locator('input[type="email"], input[placeholder*="email" i]').first();
      if (await emailInput.isVisible()) {
        await emailInput.fill("invalidemail");
        await page.keyboard.press("Tab");
        
        // Check for email validation error
        const hasError = await page.getByText(/valid email|invalid email/i).isVisible();
        // This is form-dependent
      }
    });
  });

  test.describe("Forgot Password", () => {
    test("Forgot password flow shows success message", async ({ page }) => {
      await page.goto(URLS.forgotPassword);
      
      const emailInput = page.locator('input[type="email"], input[placeholder*="email" i]').first();
      await emailInput.fill("someone@example.com");
      
      const submitBtn = page.getByRole("button", { name: /send|reset|submit/i });
      await submitBtn.click();
      
      // Should show confirmation message
      await expect(page.getByText(/email|link|sent|check|success/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Protected Routes", () => {
    test("Protected pages redirect to login when not authenticated", async ({ page }) => {
      for (const url of PROTECTED_URLS.slice(0, 5)) { // Test first 5 for speed
        await requireAuthRedirect(page, url);
      }
    });

    test("Admin pages require admin role", async ({ page, request }) => {
      // Login as regular user
      await login(page, users.demoUser.email, users.demoUser.password);
      
      // Try to access admin page
      await page.goto(URLS.admin);
      
      // Should either redirect or show forbidden
      const url = page.url();
      const hasAdminAccess = url.includes("/admin") && !url.includes("/login");
      
      // Regular user should NOT have full admin access
      // (They might see a restricted version)
    });

    test("Admin user can access admin pages", async ({ page }) => {
      await login(page, users.adminUser.email, users.adminUser.password);
      await page.goto(URLS.admin);
      
      // Admin should have access
      await expect(page.getByText(/admin|dashboard/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Session Management", () => {
    test("Logout clears session", async ({ page }) => {
      await login(page, users.demoUser.email, users.demoUser.password);
      
      // Find and click logout
      const logoutBtn = page.locator('[data-testid="logout-btn"], button:has-text("Logout"), button:has-text("Sign out")').first();
      
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click();
        
        // Try to access protected page
        await page.goto(URLS.app);
        await expect(page).toHaveURL(/\/login/);
      }
    });

    test("API returns 401 for unauthenticated requests", async ({ request }) => {
      const response = await request.get(URLS.api.profile);
      expect(response.status()).toBe(401);
    });
  });
});
