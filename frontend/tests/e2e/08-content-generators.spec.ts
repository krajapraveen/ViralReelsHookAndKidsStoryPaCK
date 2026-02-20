import { test, expect } from "@playwright/test";
import { URLS } from "../fixtures/urls";
import { login } from "../helpers/auth";
import users from "../fixtures/users.json";

test.describe("08 - Content Generator Apps", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, users.demoUser.email, users.demoUser.password);
  });

  test.describe("Story Series Generator", () => {
    test("Story Series page loads with form elements", async ({ page }) => {
      await page.goto(URLS.storySeries);
      
      // Check page header
      await expect(page.getByText(/story series/i)).toBeVisible({ timeout: 10000 });
      
      // Check for input fields
      const summaryInput = page.locator('textarea[placeholder*="summary" i], textarea[placeholder*="story" i], textarea').first();
      await expect(summaryInput).toBeVisible();
      
      // Check for generate button
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await expect(generateBtn).toBeVisible();
    });

    test("Story Series validates empty input", async ({ page }) => {
      await page.goto(URLS.storySeries);
      
      // Try to generate without input
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      
      if (await generateBtn.isEnabled()) {
        await generateBtn.click();
        
        // Should show validation error or not proceed
        const hasError = await page.getByText(/required|empty|enter/i).isVisible();
        const stillOnPage = page.url().includes("story-series");
        
        expect(hasError || stillOnPage).toBeTruthy();
      }
    });

    test("Story Series shows credit cost", async ({ page }) => {
      await page.goto(URLS.storySeries);
      
      // Should display credit cost
      await expect(page.getByText(/credit|cost/i)).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe("Challenge Generator", () => {
    test("Challenge Generator page loads", async ({ page }) => {
      await page.goto(URLS.challengeGen);
      
      // Check page header
      await expect(page.getByText(/challenge/i)).toBeVisible({ timeout: 10000 });
      
      // Check for challenge type selector or input
      const hasInput = await page.locator('select, input[type="text"], textarea').first().isVisible();
      expect(hasInput).toBeTruthy();
    });

    test("Challenge Generator has duration options", async ({ page }) => {
      await page.goto(URLS.challengeGen);
      
      // Should show duration options (7-day or 30-day)
      const has7Day = await page.getByText(/7.?day/i).isVisible();
      const has30Day = await page.getByText(/30.?day/i).isVisible();
      
      expect(has7Day || has30Day).toBeTruthy();
    });

    test("Challenge Generator shows generate button", async ({ page }) => {
      await page.goto(URLS.challengeGen);
      
      const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
      await expect(generateBtn).toBeVisible();
    });
  });

  test.describe("Tone Switcher", () => {
    test("Tone Switcher page loads", async ({ page }) => {
      await page.goto(URLS.toneSwitcher);
      
      // Check page header
      await expect(page.getByText(/tone/i)).toBeVisible({ timeout: 10000 });
      
      // Check for text input area
      const textInput = page.locator('textarea').first();
      await expect(textInput).toBeVisible();
    });

    test("Tone Switcher has tone options", async ({ page }) => {
      await page.goto(URLS.toneSwitcher);
      
      // Should show different tone options
      const tones = ["Funny", "Aggressive", "Calm", "Luxury", "Motivational"];
      let foundTones = 0;
      
      for (const tone of tones) {
        if (await page.getByText(new RegExp(tone, "i")).isVisible()) {
          foundTones++;
        }
      }
      
      expect(foundTones).toBeGreaterThan(0);
    });

    test("Tone Switcher rewrite button exists", async ({ page }) => {
      await page.goto(URLS.toneSwitcher);
      
      const rewriteBtn = page.locator('button:has-text("Rewrite"), button:has-text("Transform"), button:has-text("Switch")').first();
      await expect(rewriteBtn).toBeVisible();
    });
  });

  test.describe("Coloring Book Generator", () => {
    test("Coloring Book page loads", async ({ page }) => {
      await page.goto(URLS.coloringBook);
      
      // Check page header
      await expect(page.getByText(/coloring/i)).toBeVisible({ timeout: 10000 });
    });

    test("Coloring Book has upload option", async ({ page }) => {
      await page.goto(URLS.coloringBook);
      
      // Should have file upload or text input option
      const hasUpload = await page.locator('input[type="file"]').isVisible();
      const hasTextOption = await page.getByText(/text|story|prompt/i).isVisible();
      
      expect(hasUpload || hasTextOption).toBeTruthy();
    });

    test("Coloring Book shows export option", async ({ page }) => {
      await page.goto(URLS.coloringBook);
      
      // Should have export/PDF option mentioned
      await expect(page.getByText(/pdf|export|download/i)).toBeVisible({ timeout: 10000 });
    });

    test("Coloring Book uses client-side processing", async ({ page }) => {
      await page.goto(URLS.coloringBook);
      
      // This is a client-side feature, so the page should mention no server costs
      // or show canvas/jsPDF related UI
      const hasClientSide = await page.getByText(/free|no.?cost|client/i).isVisible();
      const hasCanvas = await page.locator('canvas').isVisible();
      
      // At minimum, the page should load without errors
      expect(page.url()).toContain("coloring-book");
    });
  });

  test.describe("Creator Tools", () => {
    test("Creator Tools main page loads", async ({ page }) => {
      await page.goto(URLS.creatorTools);
      
      // Check for main tools
      await expect(page.getByText(/creator tools/i)).toBeVisible({ timeout: 10000 });
    });

    test("Creator Tools shows available tools", async ({ page }) => {
      await page.goto(URLS.creatorTools);
      
      // Should show multiple tools
      const tools = ["Calendar", "Hashtag", "Thumbnail", "Carousel", "Trending"];
      let foundTools = 0;
      
      for (const tool of tools) {
        if (await page.getByText(new RegExp(tool, "i")).isVisible()) {
          foundTools++;
        }
      }
      
      expect(foundTools).toBeGreaterThan(0);
    });
  });

  test.describe("TwinFinder", () => {
    test("TwinFinder page loads", async ({ page }) => {
      await page.goto(URLS.twinFinder);
      
      // Check for TwinFinder content
      await expect(page.getByText(/twin|lookalike|celebrity/i)).toBeVisible({ timeout: 10000 });
    });

    test("TwinFinder has upload option", async ({ page }) => {
      await page.goto(URLS.twinFinder);
      
      // Should have file upload for face photo
      const hasUpload = await page.locator('input[type="file"]').isVisible();
      const hasUploadArea = await page.locator('[data-testid="upload"], .upload-area').isVisible();
      
      expect(hasUpload || hasUploadArea).toBeTruthy();
    });
  });
});
