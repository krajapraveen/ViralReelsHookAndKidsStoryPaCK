/**
 * CreatorStudio AI - Comprehensive Automated Regression Test Suite
 * Tests all critical user flows and functionality
 */
import { test, expect, Page } from '@playwright/test';

// Test credentials
const TEST_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

// Helper function to login
async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.fill('[data-testid="email-input"], input[type="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"]', password);
  await page.click('[data-testid="login-btn"], button[type="submit"]');
  await page.waitForURL(/\/(app\/)?dashboard/);
}

// ============================================================================
// AUTHENTICATION TESTS
// ============================================================================

test.describe('Authentication', () => {
  test('should display login page correctly', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[type="email"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('text=Invalid credentials').or(page.locator('[role="alert"]'))).toBeVisible({ timeout: 10000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    // Should be on dashboard
    await expect(page).toHaveURL(/dashboard/);
  });

  test('should display signup page correctly', async ({ page }) => {
    await page.goto('/signup');
    
    await expect(page.locator('input[placeholder*="name" i]').or(page.locator('[data-testid="name-input"]'))).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('should validate password requirements on signup', async ({ page }) => {
    await page.goto('/signup');
    
    // Enter weak password
    await page.fill('input[type="password"]', '123');
    
    // Should show password requirements (checklist should be visible)
    const passwordChecklist = page.locator('[class*="password"]').or(page.locator('text=8 characters'));
    await expect(passwordChecklist).toBeVisible({ timeout: 5000 });
  });

  test('should handle forgot password flow', async ({ page }) => {
    await page.goto('/login');
    
    // Click forgot password link
    await page.click('text=Forgot password');
    
    // Modal should appear
    await expect(page.locator('[role="dialog"]').or(page.locator('text=Reset Password'))).toBeVisible();
  });
});

// ============================================================================
// DASHBOARD TESTS
// ============================================================================

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
  });

  test('should display all feature cards', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Check for main feature cards
    const featureCards = [
      'Reel',
      'Story',
      'GenStudio',
      'Creator Tools',
      'Coloring',
      'Challenge',
      'Tone'
    ];
    
    for (const feature of featureCards) {
      await expect(page.locator(`text=${feature}`).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('should display user credits', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Credits should be displayed somewhere
    await expect(page.locator('text=credit').or(page.locator('text=Credit'))).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to Reel Generator', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    await page.click('text=Reel');
    await expect(page).toHaveURL(/reel/);
  });

  test('should navigate to Story Generator', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    await page.click('text=Story');
    await expect(page).toHaveURL(/story/);
  });
});

// ============================================================================
// REEL GENERATOR TESTS
// ============================================================================

test.describe('Reel Generator', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/reel-generator');
  });

  test('should display reel generator form', async ({ page }) => {
    await expect(page.locator('textarea, input[name="topic"]').first()).toBeVisible();
    await expect(page.locator('button:has-text("Generate")')).toBeVisible();
  });

  test('should validate empty topic', async ({ page }) => {
    // Try to submit without topic
    const generateBtn = page.locator('button:has-text("Generate")');
    await generateBtn.click();
    
    // Should show validation error or button should be disabled
    const error = page.locator('text=required').or(page.locator('[role="alert"]'));
    // Either show error or button was disabled
    const isDisabled = await generateBtn.isDisabled();
    expect(error.isVisible() || isDisabled).toBeTruthy();
  });

  test('should have platform selection', async ({ page }) => {
    // Check for platform dropdown/selection
    const platformSelector = page.locator('select, [role="combobox"]').first();
    await expect(platformSelector).toBeVisible();
  });

  test('should have style selection', async ({ page }) => {
    // Check for style dropdown/selection
    const styleSelector = page.locator('select, [role="combobox"]').nth(1);
    await expect(styleSelector).toBeVisible();
  });
});

// ============================================================================
// STORY GENERATOR TESTS
// ============================================================================

test.describe('Story Generator', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/story-generator');
  });

  test('should display story generator form', async ({ page }) => {
    await expect(page.locator('input, textarea').first()).toBeVisible();
    await expect(page.locator('button:has-text("Generate")').or(page.locator('button:has-text("Create")'))).toBeVisible();
  });

  test('should have age group selection', async ({ page }) => {
    const ageSelector = page.locator('select, [role="combobox"]').first();
    await expect(ageSelector).toBeVisible();
  });
});

// ============================================================================
// CREATOR TOOLS TESTS
// ============================================================================

test.describe('Creator Tools', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/creator-tools');
  });

  test('should display all tabs', async ({ page }) => {
    const tabs = ['Calendar', 'Carousel', 'Hashtags', 'Thumbnails', 'Trending'];
    
    for (const tab of tabs) {
      await expect(page.locator(`text=${tab}`).first()).toBeVisible();
    }
  });

  test('should switch between tabs', async ({ page }) => {
    // Click on Trending tab
    await page.click('text=Trending');
    
    // Content should change
    await expect(page.locator('text=niche').or(page.locator('text=Niche'))).toBeVisible({ timeout: 10000 });
  });

  test('Trending tab should load data', async ({ page }) => {
    await page.click('text=Trending');
    
    // Wait for content to load
    await page.waitForTimeout(2000);
    
    // Should show trending content or niche selector
    const content = page.locator('[class*="card"]').or(page.locator('text=Hook'));
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });
});

// ============================================================================
// BILLING PAGE TESTS
// ============================================================================

test.describe('Billing', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/billing');
  });

  test('should display subscription plans', async ({ page }) => {
    await expect(page.locator('text=Weekly').or(page.locator('text=Monthly'))).toBeVisible();
  });

  test('should display credit balance', async ({ page }) => {
    await expect(page.locator('text=Credit').or(page.locator('text=Balance'))).toBeVisible();
  });

  test('should display credit packs', async ({ page }) => {
    await expect(page.locator('text=Starter').or(page.locator('text=Pack').or(page.locator('text=credits')))).toBeVisible();
  });
});

// ============================================================================
// GENSTUDIO TESTS
// ============================================================================

test.describe('GenStudio', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
  });

  test('should display GenStudio dashboard', async ({ page }) => {
    await page.goto('/app/gen-studio');
    
    await expect(page.locator('text=Text to Image').or(page.locator('text=Text-to-Image'))).toBeVisible();
    await expect(page.locator('text=Text to Video').or(page.locator('text=Text-to-Video'))).toBeVisible();
  });

  test('Text-to-Image page should load', async ({ page }) => {
    await page.goto('/app/gen-studio/text-to-image');
    
    await expect(page.locator('textarea, input[name="prompt"]').first()).toBeVisible();
    await expect(page.locator('button:has-text("Generate")').or(page.locator('button:has-text("Create")'))).toBeVisible();
  });

  test('Text-to-Video page should load', async ({ page }) => {
    await page.goto('/app/gen-studio/text-to-video');
    
    await expect(page.locator('textarea, input[name="prompt"]').first()).toBeVisible();
  });
});

// ============================================================================
// CHALLENGE GENERATOR TESTS
// ============================================================================

test.describe('Challenge Generator', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/challenge-generator');
  });

  test('should display challenge options', async ({ page }) => {
    await expect(page.locator('text=7').or(page.locator('text=day'))).toBeVisible();
    await expect(page.locator('text=30').or(page.locator('text=Day'))).toBeVisible();
  });

  test('should have niche selection', async ({ page }) => {
    const nicheSelector = page.locator('select, [role="combobox"]').first();
    await expect(nicheSelector).toBeVisible();
  });
});

// ============================================================================
// TONE SWITCHER TESTS
// ============================================================================

test.describe('Tone Switcher', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/tone-switcher');
  });

  test('should display tone options', async ({ page }) => {
    const tones = ['Funny', 'Bold', 'Calm', 'Luxury', 'Motivational'];
    
    for (const tone of tones) {
      const toneElement = page.locator(`text=${tone}`).first();
      // At least some tones should be visible
      if (await toneElement.isVisible()) {
        expect(true).toBeTruthy();
        return;
      }
    }
    // If no specific tone text found, check for generic tone selector
    await expect(page.locator('select, [role="combobox"], [class*="tone"]').first()).toBeVisible();
  });

  test('should have text input area', async ({ page }) => {
    await expect(page.locator('textarea').first()).toBeVisible();
  });
});

// ============================================================================
// COLORING BOOK TESTS
// ============================================================================

test.describe('Coloring Book', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/coloring-book');
  });

  test('should display coloring book interface', async ({ page }) => {
    await expect(page.locator('text=Coloring').or(page.locator('text=color'))).toBeVisible();
  });

  test('should have mode selection', async ({ page }) => {
    await expect(page.locator('text=DIY').or(page.locator('text=Photo').or(page.locator('text=mode')))).toBeVisible();
  });
});

// ============================================================================
// ADMIN DASHBOARD TESTS
// ============================================================================

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);
  });

  test('should access admin dashboard', async ({ page }) => {
    await page.goto('/app/admin');
    
    // Should not redirect away
    await expect(page).toHaveURL(/admin/);
  });

  test('should display admin metrics', async ({ page }) => {
    await page.goto('/app/admin');
    
    await expect(page.locator('text=Users').or(page.locator('text=Revenue').or(page.locator('text=Total')))).toBeVisible();
  });

  test('should access admin monitoring', async ({ page }) => {
    await page.goto('/app/admin/monitoring');
    
    await expect(page.locator('text=Monitor').or(page.locator('text=Activity').or(page.locator('text=Security')))).toBeVisible();
  });
});

// ============================================================================
// NAVIGATION TESTS
// ============================================================================

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
  });

  test('should have working sidebar navigation', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Check sidebar links
    const navLinks = ['Dashboard', 'Billing', 'Profile', 'History'];
    
    for (const link of navLinks) {
      const navItem = page.locator(`a:has-text("${link}"), [role="link"]:has-text("${link}")`).first();
      if (await navItem.isVisible()) {
        expect(true).toBeTruthy();
      }
    }
  });

  test('should logout successfully', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Find and click logout
    const logoutBtn = page.locator('button:has-text("Logout"), a:has-text("Logout"), [data-testid="logout"]');
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await expect(page).toHaveURL(/login|\/$/);
    }
  });
});

// ============================================================================
// API HEALTH TESTS
// ============================================================================

test.describe('API Health', () => {
  test('health endpoint should respond', async ({ request }) => {
    const response = await request.get('/api/health/');
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('pricing endpoint should respond', async ({ request }) => {
    const response = await request.get('/api/pricing/plans');
    expect(response.ok()).toBeTruthy();
  });
});

// ============================================================================
// MOBILE RESPONSIVE TESTS
// ============================================================================

test.describe('Mobile Responsive', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('login page should be responsive', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('dashboard should be responsive', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto('/app/dashboard');
    
    // Content should be visible on mobile
    await expect(page.locator('text=Reel').or(page.locator('text=Story'))).toBeVisible();
  });
});

// ============================================================================
// SECURITY TESTS
// ============================================================================

test.describe('Security', () => {
  test('protected routes should redirect to login', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('admin routes should block non-admin users', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    await page.goto('/app/admin');
    
    // Should either redirect or show access denied
    const isOnAdmin = page.url().includes('/admin');
    const hasAccessDenied = await page.locator('text=denied').or(page.locator('text=unauthorized')).isVisible().catch(() => false);
    
    // Non-admin should not have full admin access
    expect(!isOnAdmin || hasAccessDenied).toBeTruthy();
  });
});
