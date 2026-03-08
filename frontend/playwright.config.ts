import { defineConfig, devices } from '@playwright/test';

/**
 * CreatorStudio AI - Playwright E2E Test Configuration
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: '../test_reports/playwright-report' }],
    ['json', { outputFile: '../test_reports/playwright-results.json' }],
    ['list']
  ],
  
  use: {
    baseURL: process.env.REACT_APP_BACKEND_URL || 'https://narrative-visuals-6.preview.emergentagent.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* Global setup/teardown */
  globalSetup: './e2e/global-setup.ts',
});
