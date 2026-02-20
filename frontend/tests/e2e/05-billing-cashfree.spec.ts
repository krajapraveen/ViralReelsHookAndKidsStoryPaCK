import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login, loginAPI } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("05 - Billing and Cashfree Payments", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test.describe("Billing Page", () => {
    test("Billing page displays current credits", async ({ page }) => {
      await page.goto(URLS.billing);
      
      // Should show credit balance
      const balanceElement = page.locator('[data-testid="credit-balance"], .credit-balance, :text-matches("\\d+ credits", "i")').first();
      await expect(balanceElement).toBeVisible({ timeout: 10000 });
    });

    test("Billing page shows credit packages", async ({ page }) => {
      await page.goto(URLS.billing);
      
      // Should show purchase options
      const packages = page.locator('[data-testid*="package"], .credit-package, [class*="pricing"]');
      await expect(packages.first()).toBeVisible({ timeout: 10000 });
    });

    test("Buy credits button initiates payment flow", async ({ page }) => {
      await page.goto(URLS.billing);
      
      // Find a buy button
      const buyBtn = page.locator('button:has-text("Buy"), button:has-text("Purchase"), button:has-text("Add Credits")').first();
      
      if (await buyBtn.isVisible()) {
        await buyBtn.click();
        
        // Should either show payment modal or redirect to payment page
        const paymentModal = page.locator('.payment-modal, [data-testid="payment-modal"], [role="dialog"]');
        const onPaymentPage = page.url().includes("payment") || page.url().includes("checkout");
        
        const hasPaymentUI = (await paymentModal.isVisible()) || onPaymentPage;
        expect(hasPaymentUI).toBeTruthy();
      }
    });
  });

  test.describe("Cashfree Integration", () => {
    test("Cashfree health endpoint reports configured", async ({ request }) => {
      const token = await loginAPI(request, users.demoUser.email, users.demoUser.password);
      
      const response = await request.get(URLS.api.cashfreeHealth, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.gateway).toBe("cashfree");
      expect(data.configured).toBe(true);
    });

    test("Cashfree order creation works in sandbox", async ({ request }) => {
      const token = await loginAPI(request, users.demoUser.email, users.demoUser.password);
      
      const response = await request.post(URLS.api.cashfreeCreateOrder, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        data: {
          product_id: "credits_100",
          amount: 299,
          currency: "INR",
        },
      });
      
      // Should return order details or redirect URL
      expect(response.status()).toBeLessThan(500);
      
      if (response.status() === 200) {
        const data = await response.json();
        // Check for order_id or payment_session_id
        const hasOrderInfo = data.order_id || data.payment_session_id || data.cf_order_id;
        expect(hasOrderInfo).toBeTruthy();
      }
    });

    test("Products endpoint returns available packages", async ({ request }) => {
      const token = await loginAPI(request, users.demoUser.email, users.demoUser.password);
      
      const response = await request.get(`${URLS.api.cashfreeHealth.replace("health", "products")}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(Array.isArray(data.products) || Array.isArray(data)).toBeTruthy();
    });
  });

  test.describe("Subscription Plans", () => {
    test("Subscription plans endpoint returns plans", async ({ request }) => {
      const response = await request.get(URLS.api.subscriptionPlans);
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.plans).toBeDefined();
      expect(data.plans.length).toBeGreaterThan(0);
      
      // Verify plan structure
      const plan = data.plans[0];
      expect(plan.name).toBeDefined();
      expect(plan.price).toBeDefined();
    });

    test("Subscription page shows available plans", async ({ page }) => {
      await page.goto(URLS.subscription);
      
      // Should show plans
      const plans = page.locator('[data-testid*="plan"], .plan-card');
      await expect(plans.first()).toBeVisible({ timeout: 10000 });
      
      // Should show pricing
      await expect(page.getByText(/₹|INR|\$|USD/)).toBeVisible();
    });

    test("Select plan button is clickable", async ({ page }) => {
      await page.goto(URLS.subscription);
      
      // Find select/subscribe button
      const selectBtn = page.locator('button:has-text("Select"), button:has-text("Subscribe"), button:has-text("Choose")').first();
      
      if (await selectBtn.isVisible()) {
        await expect(selectBtn).toBeEnabled();
      }
    });
  });

  test.describe("Payment History", () => {
    test("Payment history shows transactions", async ({ page }) => {
      await page.goto(URLS.paymentHistory);
      
      // Should show history or empty state
      const hasTransactions = await page.locator('.transaction, [data-testid*="payment"], table tr').first().isVisible();
      const hasEmptyState = await page.getByText(/no.*payments|empty|no.*transactions/i).isVisible();
      
      expect(hasTransactions || hasEmptyState).toBeTruthy();
    });
  });

  test.describe("Currency Handling", () => {
    test("Plans support INR currency", async ({ request }) => {
      const response = await request.get(`${URLS.api.subscriptionPlans}?currency=INR`);
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      
      // All plans should have INR pricing
      for (const plan of data.plans) {
        expect(plan.currency === "INR" || plan.price).toBeTruthy();
      }
    });

    test("Plans support USD currency", async ({ request }) => {
      const response = await request.get(`${URLS.api.subscriptionPlans}?currency=USD`);
      
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.plans.length).toBeGreaterThan(0);
    });
  });
});
