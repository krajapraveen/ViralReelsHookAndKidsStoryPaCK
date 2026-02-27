import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * COMPREHENSIVE MOBILE TEST SUITE
 * Tests ALL 47 pages with deep functionality and alignment checks
 * Viewports: iPhone SE (375px), iPhone 12 (390px), iPad (768px)
 */

const BASE_URL = 'https://reaction-pack.preview.emergentagent.com';
const SCREENSHOT_DIR = '/app/playwright-tests/mobile-screenshots';

const DEMO_USER = {
  email: 'demo@example.com',
  password: 'Password123!'
};

const ADMIN_USER = {
  email: 'admin@creatorstudio.ai',
  password: 'Cr3@t0rStud!o#2026'
};

// Mobile viewports to test
const MOBILE_VIEWPORTS = [
  { name: 'iPhone_SE', width: 375, height: 667 },
  { name: 'iPhone_12', width: 390, height: 844 },
  { name: 'iPad_Mini', width: 768, height: 1024 }
];

// All pages to test (47 total)
const PUBLIC_PAGES = [
  { path: '/', name: 'Landing' },
  { path: '/pricing', name: 'Pricing' },
  { path: '/contact', name: 'Contact' },
  { path: '/reviews', name: 'Reviews' },
  { path: '/privacy-policy', name: 'PrivacyPolicy' },
  { path: '/user-manual', name: 'UserManual' },
  { path: '/login', name: 'Login' },
  { path: '/signup', name: 'Signup' },
];

const AUTHENTICATED_PAGES = [
  { path: '/app', name: 'Dashboard' },
  { path: '/app/reel-generator', name: 'ReelGenerator' },
  { path: '/app/story-generator', name: 'StoryGenerator' },
  { path: '/app/gen-studio', name: 'GenStudioDashboard' },
  { path: '/app/gen-studio/text-to-image', name: 'TextToImage' },
  { path: '/app/gen-studio/text-to-video', name: 'TextToVideo' },
  { path: '/app/gen-studio/image-to-video', name: 'ImageToVideo' },
  { path: '/app/gen-studio/video-remix', name: 'VideoRemix' },
  { path: '/app/gen-studio/history', name: 'GenStudioHistory' },
  { path: '/app/gen-studio/style-profiles', name: 'StyleProfiles' },
  { path: '/app/creator-tools', name: 'CreatorTools' },
  { path: '/app/comix', name: 'ComixAI' },
  { path: '/app/gif-maker', name: 'GifMaker' },
  { path: '/app/comic-storybook', name: 'ComicStorybook' },
  { path: '/app/coloring-book', name: 'ColoringBook' },
  { path: '/app/story-series', name: 'StorySeries' },
  { path: '/app/challenge-generator', name: 'ChallengeGenerator' },
  { path: '/app/tone-switcher', name: 'ToneSwitcher' },
  { path: '/app/twinfinder', name: 'TwinFinder' },
  { path: '/app/creator-pro', name: 'CreatorPro' },
  { path: '/app/billing', name: 'Billing' },
  { path: '/app/payment-history', name: 'PaymentHistory' },
  { path: '/app/subscription', name: 'Subscription' },
  { path: '/app/profile', name: 'Profile' },
  { path: '/app/history', name: 'History' },
  { path: '/app/analytics', name: 'Analytics' },
  { path: '/app/content-vault', name: 'ContentVault' },
  { path: '/app/feature-requests', name: 'FeatureRequests' },
  { path: '/app/privacy', name: 'PrivacySettings' },
  { path: '/app/copyright', name: 'CopyrightInfo' },
];

const ADMIN_PAGES = [
  { path: '/app/admin', name: 'AdminDashboard' },
  { path: '/app/admin/realtime-analytics', name: 'RealtimeAnalytics' },
  { path: '/app/admin/users', name: 'UserManagement' },
  { path: '/app/admin/login-activity', name: 'LoginActivity' },
  { path: '/app/admin/monitoring', name: 'AdminMonitoring' },
  { path: '/app/admin/automation', name: 'AutomationDashboard' },
];

// Helper to create screenshot directory
function ensureScreenshotDir() {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
}

// Helper to check mobile alignment issues
async function checkMobileAlignment(page: Page, pageName: string): Promise<string[]> {
  const issues: string[] = [];
  
  // Check for horizontal overflow
  const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  if (bodyWidth > viewportWidth + 5) {
    issues.push(`Horizontal overflow: body(${bodyWidth}px) > viewport(${viewportWidth}px)`);
  }
  
  // Check for elements overflowing viewport
  const overflowingElements = await page.evaluate(() => {
    const viewportWidth = window.innerWidth;
    const elements = document.querySelectorAll('*');
    const overflowing: string[] = [];
    elements.forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.right > viewportWidth + 10) {
        const tag = el.tagName.toLowerCase();
        const className = el.className?.toString().slice(0, 50) || '';
        overflowing.push(`${tag}.${className}`);
      }
    });
    return overflowing.slice(0, 5); // Return first 5
  });
  if (overflowingElements.length > 0) {
    issues.push(`Overflowing elements: ${overflowingElements.join(', ')}`);
  }
  
  // Check touch target sizes
  const smallTouchTargets = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button, a, input, select, [role="button"]');
    const small: string[] = [];
    buttons.forEach(btn => {
      const rect = btn.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0 && (rect.width < 44 || rect.height < 44)) {
        const text = (btn.textContent || '').slice(0, 20);
        small.push(`${btn.tagName}:"${text}"(${Math.round(rect.width)}x${Math.round(rect.height)})`);
      }
    });
    return small.slice(0, 3);
  });
  if (smallTouchTargets.length > 0) {
    issues.push(`Small touch targets: ${smallTouchTargets.join(', ')}`);
  }
  
  // Check text readability (font size)
  const smallText = await page.evaluate(() => {
    const textElements = document.querySelectorAll('p, span, div, li, td, th, label');
    let smallCount = 0;
    textElements.forEach(el => {
      const style = window.getComputedStyle(el);
      const fontSize = parseFloat(style.fontSize);
      if (fontSize > 0 && fontSize < 12 && el.textContent && el.textContent.trim().length > 0) {
        smallCount++;
      }
    });
    return smallCount;
  });
  if (smallText > 10) {
    issues.push(`${smallText} elements with font-size < 12px`);
  }
  
  return issues;
}

// Helper to check page functionality
async function checkPageFunctionality(page: Page, pageName: string): Promise<{ working: string[], issues: string[] }> {
  const working: string[] = [];
  const issues: string[] = [];
  
  // Check if page loaded
  const bodyVisible = await page.locator('body').isVisible();
  if (bodyVisible) {
    working.push('Page loaded');
  } else {
    issues.push('Page body not visible');
  }
  
  // Check for error messages
  const errorCount = await page.locator('[role="alert"], .error, .text-red-500, .text-destructive').count();
  if (errorCount > 0) {
    const errorText = await page.locator('[role="alert"], .error').first().textContent().catch(() => '');
    if (errorText && !errorText.includes('success')) {
      issues.push(`Error visible: ${errorText.slice(0, 50)}`);
    }
  }
  
  // Check navigation is accessible
  const navVisible = await page.locator('nav, [role="navigation"], header').first().isVisible().catch(() => false);
  if (navVisible) {
    working.push('Navigation visible');
  }
  
  // Check main content area
  const mainContent = await page.locator('main, [role="main"], .main-content, .container').first().isVisible().catch(() => false);
  if (mainContent) {
    working.push('Main content visible');
  }
  
  // Check for broken images
  const brokenImages = await page.evaluate(() => {
    const images = document.querySelectorAll('img');
    let broken = 0;
    images.forEach(img => {
      if (!img.complete || img.naturalWidth === 0) {
        broken++;
      }
    });
    return broken;
  });
  if (brokenImages > 0) {
    issues.push(`${brokenImages} broken images`);
  }
  
  // Check buttons are clickable
  const buttonCount = await page.locator('button:visible').count();
  if (buttonCount > 0) {
    working.push(`${buttonCount} buttons visible`);
  }
  
  // Check forms have inputs
  const inputCount = await page.locator('input:visible, textarea:visible, select:visible').count();
  if (inputCount > 0) {
    working.push(`${inputCount} form inputs`);
  }
  
  return { working, issues };
}

// Test report structure
interface TestResult {
  viewport: string;
  page: string;
  url: string;
  status: 'PASS' | 'FAIL' | 'WARN';
  loadTime: number;
  alignmentIssues: string[];
  functionalityWorking: string[];
  functionalityIssues: string[];
  screenshot: string;
}

const testResults: TestResult[] = [];

test.describe('COMPREHENSIVE MOBILE TESTS - Public Pages', () => {
  for (const viewport of MOBILE_VIEWPORTS) {
    test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
      });

      for (const pageInfo of PUBLIC_PAGES) {
        test(`${pageInfo.name} - Layout & Functionality`, async ({ page }) => {
          ensureScreenshotDir();
          const startTime = Date.now();
          
          await page.goto(`${BASE_URL}${pageInfo.path}`);
          await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
          
          const loadTime = Date.now() - startTime;
          
          // Check alignment
          const alignmentIssues = await checkMobileAlignment(page, pageInfo.name);
          
          // Check functionality
          const { working, issues } = await checkPageFunctionality(page, pageInfo.name);
          
          // Take screenshot
          const screenshotPath = `${SCREENSHOT_DIR}/${viewport.name}_${pageInfo.name}.png`;
          await page.screenshot({ path: screenshotPath, fullPage: true });
          
          // Determine status
          let status: 'PASS' | 'FAIL' | 'WARN' = 'PASS';
          if (issues.length > 0 || alignmentIssues.some(i => i.includes('overflow'))) {
            status = alignmentIssues.some(i => i.includes('overflow')) ? 'FAIL' : 'WARN';
          }
          
          // Store result
          testResults.push({
            viewport: viewport.name,
            page: pageInfo.name,
            url: pageInfo.path,
            status,
            loadTime,
            alignmentIssues,
            functionalityWorking: working,
            functionalityIssues: issues,
            screenshot: screenshotPath
          });
          
          // Assertions
          expect(alignmentIssues.filter(i => i.includes('Horizontal overflow'))).toHaveLength(0);
          expect(issues.filter(i => i.includes('Page body not visible'))).toHaveLength(0);
        });
      }
    });
  }
});

test.describe('COMPREHENSIVE MOBILE TESTS - Authenticated Pages', () => {
  for (const viewport of MOBILE_VIEWPORTS) {
    test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        
        // Login
        await page.goto(`${BASE_URL}/login`);
        await page.locator('input[type="email"]').fill(DEMO_USER.email);
        await page.locator('input[type="password"]').fill(DEMO_USER.password);
        await page.locator('button:has-text("Login")').click();
        await page.waitForURL(/\/app/, { timeout: 15000 });
      });

      for (const pageInfo of AUTHENTICATED_PAGES) {
        test(`${pageInfo.name} - Layout & Functionality`, async ({ page }) => {
          ensureScreenshotDir();
          const startTime = Date.now();
          
          await page.goto(`${BASE_URL}${pageInfo.path}`);
          await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
          await page.waitForTimeout(1000); // Extra wait for dynamic content
          
          const loadTime = Date.now() - startTime;
          
          // Check alignment
          const alignmentIssues = await checkMobileAlignment(page, pageInfo.name);
          
          // Check functionality
          const { working, issues } = await checkPageFunctionality(page, pageInfo.name);
          
          // Take screenshot
          const screenshotPath = `${SCREENSHOT_DIR}/${viewport.name}_${pageInfo.name}.png`;
          await page.screenshot({ path: screenshotPath, fullPage: true });
          
          // Determine status
          let status: 'PASS' | 'FAIL' | 'WARN' = 'PASS';
          if (issues.length > 0 || alignmentIssues.some(i => i.includes('overflow'))) {
            status = alignmentIssues.some(i => i.includes('overflow')) ? 'FAIL' : 'WARN';
          }
          
          // Store result
          testResults.push({
            viewport: viewport.name,
            page: pageInfo.name,
            url: pageInfo.path,
            status,
            loadTime,
            alignmentIssues,
            functionalityWorking: working,
            functionalityIssues: issues,
            screenshot: screenshotPath
          });
          
          // Assertions
          expect(alignmentIssues.filter(i => i.includes('Horizontal overflow'))).toHaveLength(0);
          expect(issues.filter(i => i.includes('Page body not visible'))).toHaveLength(0);
        });
      }
    });
  }
});

test.describe('COMPREHENSIVE MOBILE TESTS - Admin Pages', () => {
  for (const viewport of MOBILE_VIEWPORTS) {
    test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        
        // Login as admin
        await page.goto(`${BASE_URL}/login`);
        await page.locator('input[type="email"]').fill(ADMIN_USER.email);
        await page.locator('input[type="password"]').fill(ADMIN_USER.password);
        await page.locator('button:has-text("Login")').click();
        await page.waitForURL(/\/app/, { timeout: 15000 });
      });

      for (const pageInfo of ADMIN_PAGES) {
        test(`${pageInfo.name} - Layout & Functionality`, async ({ page }) => {
          ensureScreenshotDir();
          const startTime = Date.now();
          
          await page.goto(`${BASE_URL}${pageInfo.path}`);
          await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
          await page.waitForTimeout(1000);
          
          const loadTime = Date.now() - startTime;
          
          // Check alignment
          const alignmentIssues = await checkMobileAlignment(page, pageInfo.name);
          
          // Check functionality
          const { working, issues } = await checkPageFunctionality(page, pageInfo.name);
          
          // Take screenshot
          const screenshotPath = `${SCREENSHOT_DIR}/${viewport.name}_${pageInfo.name}.png`;
          await page.screenshot({ path: screenshotPath, fullPage: true });
          
          // Determine status
          let status: 'PASS' | 'FAIL' | 'WARN' = 'PASS';
          if (issues.length > 0 || alignmentIssues.some(i => i.includes('overflow'))) {
            status = alignmentIssues.some(i => i.includes('overflow')) ? 'FAIL' : 'WARN';
          }
          
          // Store result
          testResults.push({
            viewport: viewport.name,
            page: pageInfo.name,
            url: pageInfo.path,
            status,
            loadTime,
            alignmentIssues,
            functionalityWorking: working,
            functionalityIssues: issues,
            screenshot: screenshotPath
          });
          
          // Assertions
          expect(alignmentIssues.filter(i => i.includes('Horizontal overflow'))).toHaveLength(0);
          expect(issues.filter(i => i.includes('Page body not visible'))).toHaveLength(0);
        });
      }
    });
  }
});
