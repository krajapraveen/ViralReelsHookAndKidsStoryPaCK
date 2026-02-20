import { expect, Page, APIRequestContext } from "@playwright/test";
import { URLS } from "../fixtures/urls";

/**
 * Login via UI
 */
export async function login(page: Page, email: string, password: string) {
  await page.goto(URLS.login, { waitUntil: "domcontentloaded" });
  
  // Fill email - try multiple selectors
  const emailInput = page.locator('input[placeholder="you@example.com"], input[type="email"], input[name="email"]').first();
  await emailInput.fill(email);
  
  // Fill password
  const passwordInput = page.locator('input[type="password"]').first();
  await passwordInput.fill(password);
  
  // Click login button
  await page.getByRole("button", { name: /login/i }).click();
  
  // Wait for redirect to app
  await expect(page).toHaveURL(/\/app/, { timeout: 15000 });
}

/**
 * Login via API and return token
 */
export async function loginAPI(request: APIRequestContext, email: string, password: string): Promise<string> {
  const response = await request.post(URLS.api.login, {
    data: { email, password },
  });
  expect(response.status()).toBe(200);
  const body = await response.json();
  return body.token;
}

/**
 * Check that a protected URL redirects to login
 */
export async function requireAuthRedirect(page: Page, url: string) {
  await page.goto(url);
  await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
}

/**
 * Logout
 */
export async function logout(page: Page) {
  // Click user menu or logout button
  const logoutBtn = page.locator('[data-testid="logout-btn"], button:has-text("Logout"), button:has-text("Sign out")').first();
  if (await logoutBtn.isVisible()) {
    await logoutBtn.click();
    await expect(page).toHaveURL(/\/(login|$)/);
  }
}

/**
 * Create authenticated request context
 */
export async function getAuthHeaders(request: APIRequestContext, email: string, password: string) {
  const token = await loginAPI(request, email, password);
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}
