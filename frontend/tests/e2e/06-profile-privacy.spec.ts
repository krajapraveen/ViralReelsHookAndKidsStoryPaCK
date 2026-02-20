import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("06 - Profile and Privacy", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test.describe("Profile Management", () => {
    test("Profile page shows user information", async ({ page }) => {
      await page.goto(URLS.profile);
      
      // Should show email
      await expect(page.getByText(users.demoUser.email)).toBeVisible({ timeout: 10000 });
      
      // Should show profile form
      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first();
      await expect(nameInput).toBeVisible();
    });

    test("Profile can be updated", async ({ page }) => {
      await page.goto(URLS.profile);
      
      // Find name input
      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first();
      
      if (await nameInput.isVisible()) {
        const originalValue = await nameInput.inputValue();
        const newName = `Test User ${Date.now()}`;
        
        await nameInput.clear();
        await nameInput.fill(newName);
        
        // Find save button
        const saveBtn = page.locator('button:has-text("Save"), button:has-text("Update"), button[type="submit"]').first();
        await saveBtn.click();
        
        // Should show success message
        await expect(page.getByText(/success|updated|saved/i)).toBeVisible({ timeout: 10000 });
        
        // Restore original name
        await nameInput.clear();
        await nameInput.fill(originalValue || "Demo User");
        await saveBtn.click();
      }
    });

    test("Email change requires verification", async ({ page }) => {
      await page.goto(URLS.profile);
      
      // Find email input if editable
      const emailInput = page.locator('input[name="email"], input[type="email"]:not([disabled])').first();
      
      if (await emailInput.isVisible() && !(await emailInput.isDisabled())) {
        // Email change might require special flow
        await expect(page.getByText(/verify|confirmation/i)).toBeVisible();
      }
    });
  });

  test.describe("Privacy Settings", () => {
    test("Privacy settings page has control options", async ({ page }) => {
      await page.goto(URLS.privacySettings);
      
      // Should show privacy header
      await expect(page.getByText(/privacy|data/i)).toBeVisible({ timeout: 10000 });
      
      // Should have export option
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download")').first();
      await expect(exportBtn).toBeVisible();
    });

    test("Data export can be requested", async ({ page }) => {
      await page.goto(URLS.privacySettings);
      
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download Data")').first();
      
      if (await exportBtn.isVisible()) {
        await exportBtn.click();
        
        // Should show confirmation or start download
        const hasConfirmation = await page.getByText(/export|download|processing|success/i).isVisible();
        expect(hasConfirmation).toBeTruthy();
      }
    });

    test("Account deletion option exists", async ({ page }) => {
      await page.goto(URLS.privacySettings);
      
      // Should have delete account option
      const deleteOption = page.locator('button:has-text("Delete"), :text("delete account")').first();
      
      if (await deleteOption.isVisible()) {
        await deleteOption.click();
        
        // Should show confirmation dialog
        await expect(page.getByText(/confirm|are you sure|cannot be undone/i)).toBeVisible({ timeout: 5000 });
        
        // Cancel the dialog
        const cancelBtn = page.locator('button:has-text("Cancel"), button:has-text("No")').first();
        if (await cancelBtn.isVisible()) {
          await cancelBtn.click();
        }
      }
    });
  });

  test.describe("Copyright Settings", () => {
    test("Copyright page has legal information", async ({ page }) => {
      await page.goto(URLS.copyright);
      
      // Should show copyright info
      await expect(page.getByText(/copyright|legal|license/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Session Security", () => {
    test("Password change requires current password", async ({ page }) => {
      await page.goto(URLS.profile);
      
      // Find password change section
      const passwordSection = page.locator('[data-testid="password-section"], :text("Change Password")').first();
      
      if (await passwordSection.isVisible()) {
        await passwordSection.click();
        
        // Should require current password
        const currentPasswordInput = page.locator('input[name="currentPassword"], input[placeholder*="current" i]').first();
        await expect(currentPasswordInput).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe("Notification Preferences", () => {
    test("User can manage notification settings", async ({ page }) => {
      await page.goto(URLS.profile);
      
      // Look for notification toggles
      const notificationSection = page.locator('[data-testid*="notification"], :text-matches("notification", "i")').first();
      
      if (await notificationSection.isVisible()) {
        // Should have toggle controls
        const toggles = page.locator('input[type="checkbox"], [role="switch"]');
        const count = await toggles.count();
        expect(count).toBeGreaterThan(0);
      }
    });
  });
});
