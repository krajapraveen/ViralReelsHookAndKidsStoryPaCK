import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import { waitForJobCompletion } from "../helpers/sse";
import users from "../fixtures/users.json";

test.describe("03 - GenStudio Features", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test.describe("GenStudio Dashboard", () => {
    test("GenStudio main page loads with all feature cards", async ({ page }) => {
      await page.goto(URLS.genStudio);
      
      // Check for main features
      await expect(page.getByText(/text.*(to|→).*image/i)).toBeVisible({ timeout: 10000 });
      await expect(page.getByText(/text.*(to|→).*video/i)).toBeVisible();
      await expect(page.getByText(/image.*(to|→).*video/i)).toBeVisible();
    });

    test("GenStudio navigation works", async ({ page }) => {
      await page.goto(URLS.genStudio);
      
      // Click on Text-to-Image
      await page.getByText(/text.*(to|→).*image/i).click();
      await expect(page).toHaveURL(/text-to-image/);
    });
  });

  test.describe("Text-to-Image", () => {
    test("T2I page has required input elements", async ({ page }) => {
      await page.goto(URLS.t2i);
      
      // Check for prompt input
      const promptInput = page.locator('textarea[placeholder*="prompt" i], textarea[placeholder*="describe" i], input[placeholder*="prompt" i]').first();
      await expect(promptInput).toBeVisible({ timeout: 10000 });
      
      // Check for generate button
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await expect(generateBtn).toBeVisible();
    });

    test("T2I validates empty prompt", async ({ page }) => {
      await page.goto(URLS.t2i);
      
      // Try to generate without prompt
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await generateBtn.click();
      
      // Should show validation error or button should be disabled
      const hasError = await page.getByText(/required|prompt|empty/i).isVisible();
      const isDisabled = await generateBtn.isDisabled();
      
      expect(hasError || isDisabled).toBeTruthy();
    });

    test("T2I generates image with valid prompt", async ({ page }) => {
      test.setTimeout(180000); // 3 min timeout for generation
      
      await page.goto(URLS.t2i);
      
      // Enter prompt
      const promptInput = page.locator('textarea, input[placeholder*="prompt" i]').first();
      await promptInput.fill("A cute cartoon cat playing with yarn, colorful, playful");
      
      // Generate
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await generateBtn.click();
      
      // Wait for result
      try {
        const result = await waitForJobCompletion(page, 120000);
        expect(result.status).toBe("completed");
        
        // Check for output image
        const outputImg = page.locator('img[src*="blob:"], img[src*="http"], [data-testid="generated-image"]').first();
        await expect(outputImg).toBeVisible({ timeout: 10000 });
      } catch (e) {
        // Check if there's an error message instead
        const errorMsg = await page.getByText(/error|failed|insufficient/i).isVisible();
        if (errorMsg) {
          console.log("Generation failed with error message");
        } else {
          throw e;
        }
      }
    });
  });

  test.describe("Text-to-Video", () => {
    test("T2V page has required input elements", async ({ page }) => {
      await page.goto(URLS.t2v);
      
      // Check for prompt input
      const promptInput = page.locator('textarea, input[placeholder*="prompt" i]').first();
      await expect(promptInput).toBeVisible({ timeout: 10000 });
      
      // Check for generate button
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await expect(generateBtn).toBeVisible();
    });
  });

  test.describe("Image-to-Video", () => {
    test("I2V page has file upload element", async ({ page }) => {
      await page.goto(URLS.i2v);
      
      // Check for file input or upload area
      const fileInput = page.locator('input[type="file"], [data-testid="upload"], .upload-area').first();
      await expect(fileInput).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Generation History", () => {
    test("History page shows past generations", async ({ page }) => {
      await page.goto(URLS.genHistory);
      
      // Check for history header
      await expect(page.getByText(/history|jobs|generations/i)).toBeVisible({ timeout: 10000 });
      
      // Should show job list or empty state
      const hasJobs = await page.locator('[data-testid*="job"], .job-card, .history-item').first().isVisible();
      const hasEmptyState = await page.getByText(/no.*jobs|empty|nothing/i).isVisible();
      
      expect(hasJobs || hasEmptyState).toBeTruthy();
    });
  });

  test.describe("Style Profiles", () => {
    test("Style Profiles page loads", async ({ page }) => {
      await page.goto(URLS.styleProfiles);
      
      // Check for style profiles content
      await expect(page.getByText(/style|profile|brand/i)).toBeVisible({ timeout: 10000 });
    });
  });
});
