import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup for Playwright tests
 * Creates authenticated state for reuse across tests
 */
async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Navigate to login
  await page.goto(`${baseURL}/login`);
  
  // Login with admin credentials
  await page.fill('input[type="email"]', 'admin@creatorstudio.ai');
  await page.fill('input[type="password"]', 'Cr3@t0rStud!o#2026');
  await page.click('button:has-text("Login")');
  
  // Wait for redirect to dashboard
  await page.waitForURL('**/app**', { timeout: 10000 });
  
  // Save authenticated state
  await page.context().storageState({ path: './e2e/.auth/admin.json' });
  
  await browser.close();
}

export default globalSetup;
