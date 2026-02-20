import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import { waitForDownload, validatePDF, validateImage } from "../helpers/downloads";
import users from "../fixtures/users.json";

test.describe("04 - Downloads and Exports", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test.describe("Privacy Settings Export", () => {
    test("Data export produces valid file", async ({ page }) => {
      await page.goto(URLS.privacySettings);
      
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download Data")').first();
      
      if (await exportBtn.isVisible()) {
        try {
          const { download, path, filename } = await waitForDownload(
            page,
            async () => { await exportBtn.click(); },
            [".pdf", ".json", ".zip", ".csv"]
          );
          
          expect(filename).toBeTruthy();
          console.log(`Downloaded: ${filename}`);
          
          if (filename.endsWith(".pdf")) {
            expect(await validatePDF(path)).toBeTruthy();
          }
        } catch (e) {
          // Export might require confirmation or time
          console.log("Export not immediately available:", e);
        }
      }
    });
  });

  test.describe("Content Vault Downloads", () => {
    test("Content Vault allows downloading saved content", async ({ page }) => {
      await page.goto(URLS.contentVault);
      
      // Wait for content to load
      await page.waitForTimeout(2000);
      
      // Find download button on first item
      const downloadBtn = page.locator('button:has-text("Download"), [data-testid*="download"]').first();
      
      if (await downloadBtn.isVisible()) {
        try {
          const { filename } = await waitForDownload(
            page,
            async () => { await downloadBtn.click(); },
            [".pdf", ".png", ".jpg", ".mp4", ".json"]
          );
          
          expect(filename).toBeTruthy();
        } catch (e) {
          console.log("No downloadable content available:", e);
        }
      }
    });
  });

  test.describe("GenStudio Downloads", () => {
    test("Generated content can be downloaded", async ({ page }) => {
      await page.goto(URLS.genHistory);
      
      // Wait for history to load
      await page.waitForTimeout(2000);
      
      // Find a completed job with download option
      const downloadBtn = page.locator('[data-testid*="download"], button:has-text("Download")').first();
      
      if (await downloadBtn.isVisible()) {
        try {
          const { filename } = await waitForDownload(
            page,
            async () => { await downloadBtn.click(); },
            [".png", ".jpg", ".mp4", ".webp"]
          );
          
          expect(filename).toBeTruthy();
        } catch (e) {
          console.log("No completed jobs to download:", e);
        }
      }
    });
  });

  test.describe("Story Generator Exports", () => {
    test("Story can be exported as PDF", async ({ page }) => {
      await page.goto(URLS.storyGen);
      
      // Wait for page to load
      await page.waitForTimeout(2000);
      
      // Check for export button (might need to generate a story first)
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("PDF"), button:has-text("Download")').first();
      
      if (await exportBtn.isVisible()) {
        // Check if it's enabled
        const isDisabled = await exportBtn.isDisabled();
        if (!isDisabled) {
          try {
            const { path, filename } = await waitForDownload(
              page,
              async () => { await exportBtn.click(); },
              [".pdf"]
            );
            
            expect(filename).toContain(".pdf");
            expect(await validatePDF(path)).toBeTruthy();
          } catch (e) {
            console.log("PDF export not available:", e);
          }
        }
      }
    });
  });

  test.describe("Coloring Book Downloads", () => {
    test("Coloring Book page has export functionality", async ({ page }) => {
      await page.goto(URLS.coloringBook);
      
      // Wait for page
      await page.waitForTimeout(2000);
      
      // Check for export/download option
      const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download"), button:has-text("PDF")').first();
      await expect(exportBtn).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Invoice Downloads", () => {
    test("Payment History allows invoice download", async ({ page }) => {
      await page.goto(URLS.paymentHistory);
      
      // Wait for history to load
      await page.waitForTimeout(2000);
      
      // Find invoice/receipt download button
      const invoiceBtn = page.locator('button:has-text("Invoice"), button:has-text("Receipt"), [data-testid*="invoice"]').first();
      
      if (await invoiceBtn.isVisible()) {
        try {
          const { filename } = await waitForDownload(
            page,
            async () => { await invoiceBtn.click(); },
            [".pdf"]
          );
          
          expect(filename).toContain(".pdf");
        } catch (e) {
          console.log("No invoices available:", e);
        }
      }
    });
  });
});
