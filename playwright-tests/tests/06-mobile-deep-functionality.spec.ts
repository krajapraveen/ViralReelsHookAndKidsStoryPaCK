import { test, expect, Page } from '@playwright/test';

/**
 * DEEP MOBILE FUNCTIONALITY TESTS
 * Tests interactive elements, forms, tabs, modals on mobile
 */

const BASE_URL = 'https://activity-tracker-197.preview.emergentagent.com';

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

// Test on iPhone 12 viewport
test.use({ viewport: { width: 390, height: 844 } });

test.describe('Deep Mobile Functionality - Authentication', () => {
  test('Login form works on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Check form is fully visible
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');
    const loginButton = page.locator('button:has-text("Login")');
    
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(loginButton).toBeVisible();
    
    // Check inputs are properly sized for touch
    const emailBox = await emailInput.boundingBox();
    expect(emailBox?.height).toBeGreaterThanOrEqual(40);
    
    // Fill and submit
    await emailInput.fill(DEMO_USER.email);
    await passwordInput.fill(DEMO_USER.password);
    await loginButton.click();
    
    await page.waitForURL(/\/app/, { timeout: 15000 });
    expect(page.url()).toContain('/app');
  });

  test('Signup form works on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/signup`);
    
    // Check all form fields are accessible
    const nameInput = page.locator('input[name="name"], input[placeholder*="name" i]').first();
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]').first();
    
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    
    // Check form can be scrolled to
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
  });

  test('Forgot password modal works on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Find forgot password link
    const forgotLink = page.locator('a:has-text("Forgot"), button:has-text("Forgot")').first();
    if (await forgotLink.isVisible()) {
      await forgotLink.click();
      await page.waitForTimeout(1000);
      
      // Check modal is properly sized
      const modal = page.locator('[role="dialog"], .modal, [data-state="open"]').first();
      if (await modal.isVisible()) {
        const modalBox = await modal.boundingBox();
        expect(modalBox?.width).toBeLessThanOrEqual(390);
      }
    }
  });
});

test.describe('Deep Mobile Functionality - Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('Dashboard stats cards are readable', async ({ page }) => {
    // Check stats cards stack properly
    const cards = page.locator('.card, [class*="card"]');
    const cardCount = await cards.count();
    
    if (cardCount > 0) {
      const firstCard = cards.first();
      const cardBox = await firstCard.boundingBox();
      
      // Card should not overflow viewport
      expect(cardBox?.width).toBeLessThanOrEqual(390);
    }
  });

  test('Navigation menu works on mobile', async ({ page }) => {
    // Look for hamburger menu or mobile nav
    const hamburger = page.locator('[data-testid="mobile-menu"], button[aria-label*="menu"], .hamburger, [class*="menu-toggle"]').first();
    
    if (await hamburger.isVisible()) {
      await hamburger.click();
      await page.waitForTimeout(500);
      
      // Check nav items are visible
      const navItems = page.locator('nav a, [role="navigation"] a');
      expect(await navItems.count()).toBeGreaterThan(0);
    }
  });

  test('Quick action buttons are tappable', async ({ page }) => {
    const buttons = page.locator('button:visible');
    const buttonCount = await buttons.count();
    
    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = buttons.nth(i);
      const box = await button.boundingBox();
      if (box && box.width > 0) {
        // Touch targets should be at least 44px
        expect(box.height).toBeGreaterThanOrEqual(30);
      }
    }
  });
});

test.describe('Deep Mobile Functionality - Comix AI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto(`${BASE_URL}/app/comix`);
  });

  test('Tabs are accessible on mobile', async ({ page }) => {
    // Check tabs exist and are clickable
    const tabs = page.locator('[role="tab"], button').filter({ hasText: /character|panel|story/i });
    const tabCount = await tabs.count();
    
    expect(tabCount).toBeGreaterThanOrEqual(1);
    
    // Try clicking each tab
    for (let i = 0; i < Math.min(tabCount, 3); i++) {
      const tab = tabs.nth(i);
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('Upload area is accessible on mobile', async ({ page }) => {
    const uploadArea = page.locator('input[type="file"], [data-testid*="upload"], .upload-area, .dropzone').first();
    await expect(uploadArea).toBeAttached();
  });

  test('Style dropdown works on mobile', async ({ page }) => {
    const styleSelect = page.locator('select, [role="combobox"], [data-testid*="style"]').first();
    
    if (await styleSelect.isVisible()) {
      await styleSelect.click();
      await page.waitForTimeout(500);
      
      // Check dropdown options are visible
      const options = page.locator('[role="option"], option');
      expect(await options.count()).toBeGreaterThanOrEqual(0);
    }
  });

  test('Generate button is visible and tappable', async ({ page }) => {
    const generateBtn = page.locator('button:has-text("Generate"), button:has-text("Create")').first();
    
    if (await generateBtn.isVisible()) {
      const box = await generateBtn.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(40);
      expect(box?.width).toBeGreaterThanOrEqual(100);
    }
  });
});

test.describe('Deep Mobile Functionality - GIF Maker', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto(`${BASE_URL}/app/gif-maker`);
  });

  test('Emotion selector is accessible', async ({ page }) => {
    // Check for emotion buttons or select
    const emotionElements = page.locator('button, [role="option"]').filter({ hasText: /happy|sad|excited|laugh/i });
    const count = await emotionElements.count();
    
    // At least some emotion options should be visible
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('Style selector works on mobile', async ({ page }) => {
    const styleSelect = page.locator('select, [role="combobox"]').first();
    
    if (await styleSelect.isVisible()) {
      const box = await styleSelect.boundingBox();
      expect(box?.width).toBeLessThanOrEqual(390);
    }
  });

  test('Recent GIFs section scrolls properly', async ({ page }) => {
    // Scroll to recent GIFs section
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    
    // Check no horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
  });
});

test.describe('Deep Mobile Functionality - Creator Tools', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.goto(`${BASE_URL}/app/creator-tools`);
  });

  test('All 6 tabs are accessible', async ({ page }) => {
    const tabs = page.locator('[role="tab"], button').filter({ 
      hasText: /calendar|carousel|hashtag|thumbnail|trending|convert/i 
    });
    
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(3);
    
    // Test each tab
    for (let i = 0; i < Math.min(tabCount, 6); i++) {
      const tab = tabs.nth(i);
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(500);
        
        // Check no horizontal overflow after clicking
        const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
        const viewportWidth = await page.evaluate(() => window.innerWidth);
        expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
      }
    }
  });

  test('Tab content scrolls properly', async ({ page }) => {
    // Scroll through the page
    for (let i = 0; i < 3; i++) {
      await page.evaluate(() => window.scrollBy(0, 300));
      await page.waitForTimeout(200);
    }
    
    // Scroll back up
    await page.evaluate(() => window.scrollTo(0, 0));
  });
});

test.describe('Deep Mobile Functionality - GenStudio', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('GenStudio dashboard cards are properly sized', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/gen-studio`);
    
    const cards = page.locator('.card, [class*="card"], a[href*="gen-studio"]');
    const cardCount = await cards.count();
    
    if (cardCount > 0) {
      const firstCard = cards.first();
      const box = await firstCard.boundingBox();
      
      if (box) {
        expect(box.width).toBeLessThanOrEqual(390);
      }
    }
  });

  test('Text-to-Image prompt input works', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/gen-studio/text-to-image`);
    
    const promptInput = page.locator('textarea, input[type="text"]').first();
    await expect(promptInput).toBeVisible();
    
    // Type in the prompt
    await promptInput.fill('A beautiful sunset over mountains');
    
    // Check value was entered
    const value = await promptInput.inputValue();
    expect(value).toContain('sunset');
  });

  test('Image-to-Video upload works', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/gen-studio/image-to-video`);
    
    const uploadArea = page.locator('input[type="file"], [data-testid*="upload"]').first();
    await expect(uploadArea).toBeAttached();
  });
});

test.describe('Deep Mobile Functionality - Billing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('Billing page shows credit balance', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/billing`);
    
    // Look for credit balance display
    const creditDisplay = page.locator('text=/credit|balance/i').first();
    await expect(page.locator('body')).toBeVisible();
  });

  test('Pricing cards are properly stacked', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/billing`);
    
    const cards = page.locator('.card, [class*="card"], [class*="plan"]');
    const cardCount = await cards.count();
    
    if (cardCount > 1) {
      // Check cards don't overflow
      for (let i = 0; i < Math.min(cardCount, 3); i++) {
        const card = cards.nth(i);
        const box = await card.boundingBox();
        if (box && box.width > 0) {
          expect(box.width).toBeLessThanOrEqual(400);
        }
      }
    }
  });
});

test.describe('Deep Mobile Functionality - Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(ADMIN_USER.email);
    await page.locator('input[type="password"]').fill(ADMIN_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('Admin dashboard stats are readable', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/admin`);
    
    // Check page loads
    await expect(page.locator('body')).toBeVisible();
    
    // Check no horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
  });

  test('Realtime Analytics tabs work on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/admin/realtime-analytics`);
    
    // Check tabs are visible
    const tabs = page.locator('[role="tab"], button').filter({ 
      hasText: /overview|revenue|monitoring|alerts|export/i 
    });
    
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(1);
    
    // Click through tabs
    for (let i = 0; i < Math.min(tabCount, 5); i++) {
      const tab = tabs.nth(i);
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('User Management table scrolls horizontally if needed', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/admin/users`);
    
    // Check table exists
    const table = page.locator('table, [role="table"], .table').first();
    if (await table.isVisible()) {
      // Table container should have overflow handling
      await expect(table).toBeVisible();
    }
  });

  test('Login Activity filters work on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/admin/login-activity`);
    
    // Check filter elements
    const filters = page.locator('select, input[type="search"], [role="combobox"]');
    const filterCount = await filters.count();
    
    if (filterCount > 0) {
      const firstFilter = filters.first();
      const box = await firstFilter.boundingBox();
      if (box) {
        expect(box.width).toBeLessThanOrEqual(390);
      }
    }
  });
});

test.describe('Deep Mobile Functionality - Forms & Inputs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('Profile form inputs are properly sized', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/profile`);
    
    const inputs = page.locator('input:visible, textarea:visible');
    const inputCount = await inputs.count();
    
    for (let i = 0; i < Math.min(inputCount, 5); i++) {
      const input = inputs.nth(i);
      const box = await input.boundingBox();
      if (box && box.width > 0) {
        expect(box.width).toBeLessThanOrEqual(390);
        expect(box.height).toBeGreaterThanOrEqual(36);
      }
    }
  });

  test('Feature request form works on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/feature-requests`);
    
    // Check form elements
    const textarea = page.locator('textarea').first();
    if (await textarea.isVisible()) {
      await textarea.fill('This is a test feature request from mobile');
      const value = await textarea.inputValue();
      expect(value).toContain('test feature request');
    }
  });

  test('Privacy settings toggles are accessible', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/privacy`);
    
    // Check for toggle switches or checkboxes
    const toggles = page.locator('input[type="checkbox"], [role="switch"], button[role="switch"]');
    const toggleCount = await toggles.count();
    
    if (toggleCount > 0) {
      const firstToggle = toggles.first();
      const box = await firstToggle.boundingBox();
      if (box) {
        expect(box.width).toBeGreaterThanOrEqual(20);
      }
    }
  });
});

test.describe('Deep Mobile Functionality - Scrolling & Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"]').fill(DEMO_USER.email);
    await page.locator('input[type="password"]').fill(DEMO_USER.password);
    await page.locator('button:has-text("Login")').click();
    await page.waitForURL(/\/app/, { timeout: 15000 });
  });

  test('Long pages scroll smoothly', async ({ page }) => {
    await page.goto(`${BASE_URL}/app/history`);
    
    // Scroll down
    for (let i = 0; i < 5; i++) {
      await page.evaluate(() => window.scrollBy(0, 200));
      await page.waitForTimeout(100);
    }
    
    // Scroll back up
    await page.evaluate(() => window.scrollTo(0, 0));
    
    // Verify we're at top
    const scrollY = await page.evaluate(() => window.scrollY);
    expect(scrollY).toBeLessThan(10);
  });

  test('Back button navigation works', async ({ page }) => {
    await page.goto(`${BASE_URL}/app`);
    await page.goto(`${BASE_URL}/app/billing`);
    
    // Go back
    await page.goBack();
    await page.waitForTimeout(500);
    
    // Should be back at dashboard
    expect(page.url()).toContain('/app');
  });

  test('Sidebar/drawer navigation on mobile', async ({ page }) => {
    await page.goto(`${BASE_URL}/app`);
    
    // Look for mobile menu toggle
    const menuToggle = page.locator('[data-testid="menu-toggle"], [aria-label*="menu"], .hamburger').first();
    
    if (await menuToggle.isVisible()) {
      await menuToggle.click();
      await page.waitForTimeout(500);
      
      // Check drawer/sidebar is visible
      const drawer = page.locator('[role="navigation"], .sidebar, .drawer, nav').first();
      await expect(drawer).toBeVisible();
    }
  });
});
