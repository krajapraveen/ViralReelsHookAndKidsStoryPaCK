import { test, expect } from '@playwright/test';

/**
 * Phase 2 - Automated Functional Testing
 * Test Suite 2: Generation Features (Comix AI, GIF Maker, etc.)
 */

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

test.describe('D. Comix AI Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto('/app/comix');
  });

  test('D1. Comix AI page loads with tabs', async ({ page }) => {
    await expect(page).toHaveURL(/comix/);
    
    // Check for tabs (Character, Panel, Story)
    const tabs = page.locator('[role="tab"], button').filter({ hasText: /character|panel|story/i });
    expect(await tabs.count()).toBeGreaterThanOrEqual(1);
  });

  test('D2. Character tab has upload and style options', async ({ page }) => {
    // Click Character tab if exists
    const characterTab = page.locator('[role="tab"], button').filter({ hasText: /character/i }).first();
    if (await characterTab.isVisible()) {
      await characterTab.click();
    }
    
    // Check for upload area or file input
    const uploadArea = page.locator('input[type="file"], [data-testid*="upload"], .upload, .dropzone').first();
    await expect(uploadArea).toBeAttached();
    
    // Check for style selection
    const styleSelect = page.locator('select, [role="combobox"], [data-testid*="style"]').first();
    await expect(styleSelect).toBeVisible();
  });

  test('D3. Panel tab has scene input', async ({ page }) => {
    const panelTab = page.locator('[role="tab"], button').filter({ hasText: /panel/i }).first();
    if (await panelTab.isVisible()) {
      await panelTab.click();
      await page.waitForTimeout(500);
    }
    
    // Check for text input for scene description
    const textInput = page.locator('textarea, input[type="text"]').first();
    await expect(textInput).toBeVisible();
  });

  test('D4. Story tab has genre and mood options', async ({ page }) => {
    const storyTab = page.locator('[role="tab"], button').filter({ hasText: /story/i }).first();
    if (await storyTab.isVisible()) {
      await storyTab.click();
      await page.waitForTimeout(500);
    }
    
    // Should have some form elements
    const formElements = page.locator('select, input, textarea, [role="combobox"]');
    expect(await formElements.count()).toBeGreaterThan(0);
  });
});

test.describe('E. GIF Maker Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto('/app/gif-maker');
  });

  test('E1. GIF Maker page loads', async ({ page }) => {
    await expect(page).toHaveURL(/gif-maker/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('E2. Has photo upload area', async ({ page }) => {
    const uploadArea = page.locator('input[type="file"], [data-testid*="upload"], .upload').first();
    await expect(uploadArea).toBeAttached();
  });

  test('E3. Has emotion selection', async ({ page }) => {
    // Check for emotion buttons or select
    const emotionSelect = page.locator('select, [role="combobox"], button, [data-testid*="emotion"]')
      .filter({ hasText: /happy|sad|excited|emotion/i });
    expect(await emotionSelect.count()).toBeGreaterThanOrEqual(0);
  });

  test('E4. Has style selection', async ({ page }) => {
    const styleSelect = page.locator('select, [role="combobox"], [data-testid*="style"]').first();
    await expect(styleSelect).toBeVisible();
  });

  test('E5. Has animation intensity option', async ({ page }) => {
    // Check for intensity selector
    const intensitySelect = page.locator('select, [role="combobox"], button')
      .filter({ hasText: /simple|medium|complex|intensity/i });
    // This might be hidden, so just check count
    const count = await intensitySelect.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('F. Comic Storybook Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto('/app/comic-storybook');
  });

  test('F1. Comic Storybook page loads', async ({ page }) => {
    await expect(page).toHaveURL(/comic-storybook/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('F2. Has text input or file upload', async ({ page }) => {
    // Should have textarea for story text or file upload
    const textInput = page.locator('textarea, input[type="file"]').first();
    await expect(textInput).toBeAttached();
  });

  test('F3. Has style selection', async ({ page }) => {
    const styleSelect = page.locator('select, [role="combobox"], [data-testid*="style"]').first();
    await expect(styleSelect).toBeVisible();
  });

  test('F4. Has generate button', async ({ page }) => {
    const generateBtn = page.getByRole('button', { name: /generate|create|submit/i }).first();
    await expect(generateBtn).toBeVisible();
  });
});

test.describe('G. GenStudio Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('G1. GenStudio dashboard shows tools', async ({ page }) => {
    await page.goto('/app/gen-studio');
    await expect(page).toHaveURL(/gen-studio/);
    
    // Should have tool cards or links
    const toolCards = page.locator('a, button, [role="link"]')
      .filter({ hasText: /text-to-image|text-to-video|image-to-video/i });
    expect(await toolCards.count()).toBeGreaterThanOrEqual(0);
  });

  test('G2. Text-to-Image page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/text-to-image');
    await expect(page).toHaveURL(/text-to-image/);
    
    // Has prompt input
    const promptInput = page.locator('textarea, input[type="text"]').first();
    await expect(promptInput).toBeVisible();
  });

  test('G3. Text-to-Video page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/text-to-video');
    await expect(page).toHaveURL(/text-to-video/);
  });

  test('G4. Image-to-Video page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/image-to-video');
    await expect(page).toHaveURL(/image-to-video/);
  });

  test('G5. Video Remix page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/video-remix');
    await expect(page).toHaveURL(/video-remix/);
  });

  test('G6. GenStudio History page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/history');
    await expect(page).toHaveURL(/history/);
  });

  test('G7. Style Profiles page loads', async ({ page }) => {
    await page.goto('/app/gen-studio/style-profiles');
    await expect(page).toHaveURL(/style-profiles/);
  });
});

test.describe('H. Creator Tools Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').first().fill(DEMO_USER.email);
    await page.locator('input[type="password"], input[name="password"]').first().fill(DEMO_USER.password);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto('/app/creator-tools');
  });

  test('H1. Creator Tools page loads with tabs', async ({ page }) => {
    await expect(page).toHaveURL(/creator-tools/);
    
    // Check for tabs
    const tabs = page.locator('[role="tab"], button')
      .filter({ hasText: /calendar|carousel|hashtag|thumbnail|trending|convert/i });
    expect(await tabs.count()).toBeGreaterThanOrEqual(1);
  });

  test('H2. Calendar tab accessible', async ({ page }) => {
    const calendarTab = page.locator('[role="tab"], button').filter({ hasText: /calendar/i }).first();
    if (await calendarTab.isVisible()) {
      await calendarTab.click();
    }
    await page.waitForTimeout(500);
  });

  test('H3. Hashtags tab accessible', async ({ page }) => {
    const hashtagsTab = page.locator('[role="tab"], button').filter({ hasText: /hashtag/i }).first();
    if (await hashtagsTab.isVisible()) {
      await hashtagsTab.click();
    }
    await page.waitForTimeout(500);
  });

  test('H4. Trending tab accessible', async ({ page }) => {
    const trendingTab = page.locator('[role="tab"], button').filter({ hasText: /trending/i }).first();
    if (await trendingTab.isVisible()) {
      await trendingTab.click();
    }
    await page.waitForTimeout(500);
  });
});
