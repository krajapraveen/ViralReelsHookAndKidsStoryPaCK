/**
 * Playwright Auth State Management
 * Centralized authentication for stable CI
 */
import { test as base, expect } from '@playwright/test';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'https://narrative-suite.preview.emergentagent.com';

// Test credentials
const TEST_USERS = {
  demo: {
    email: 'demo@example.com',
    password: 'Password123!'
  },
  admin: {
    email: 'krajapraveen.katta@creatorstudio.ai',
    password: 'Onemanarmy@1979#'
  }
};

// Extend base test with authentication
export const test = base.extend({
  // Demo user authenticated page
  authenticatedPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/demo-user.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Admin user authenticated page
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: '.auth/admin-user.json'
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  }
});

/**
 * Setup authentication state before tests run
 * This creates storage state files for reuse
 */
export async function globalSetup() {
  const { chromium } = await import('@playwright/test');
  const browser = await chromium.launch();

  // Authenticate demo user
  try {
    const demoContext = await browser.newContext();
    const demoPage = await demoContext.newPage();
    
    await demoPage.goto(`${API_URL}/login`);
    await demoPage.waitForLoadState('networkidle');
    
    await demoPage.fill('input[type="email"]', TEST_USERS.demo.email);
    await demoPage.fill('input[type="password"]', TEST_USERS.demo.password);
    await demoPage.click('button[type="submit"]');
    
    await demoPage.waitForURL('**/app**', { timeout: 15000 });
    
    // Save storage state
    await demoContext.storageState({ path: '.auth/demo-user.json' });
    await demoContext.close();
    
    console.log('Demo user auth state saved');
  } catch (error) {
    console.error('Failed to authenticate demo user:', error);
  }

  // Authenticate admin user
  try {
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    
    await adminPage.goto(`${API_URL}/login`);
    await adminPage.waitForLoadState('networkidle');
    
    await adminPage.fill('input[type="email"]', TEST_USERS.admin.email);
    await adminPage.fill('input[type="password"]', TEST_USERS.admin.password);
    await adminPage.click('button[type="submit"]');
    
    await adminPage.waitForURL('**/app**', { timeout: 15000 });
    
    // Save storage state
    await adminContext.storageState({ path: '.auth/admin-user.json' });
    await adminContext.close();
    
    console.log('Admin user auth state saved');
  } catch (error) {
    console.error('Failed to authenticate admin user:', error);
  }

  await browser.close();
}

export { expect };
export default test;
