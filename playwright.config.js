// Playwright configuration for stable CI
// CreatorStudio AI E2E Tests
import { defineConfig, devices } from '@playwright/test';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'https://daily-challenges-10.preview.emergentagent.com';

export default defineConfig({
  testDir: './tests/e2e',
  
  // Test timeout
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  
  // Run tests in parallel
  fullyParallel: true,
  
  // Retry on CI
  retries: process.env.CI ? 2 : 1,
  
  // Limit workers on CI
  workers: process.env.CI ? 1 : 2,
  
  // Reporter
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/playwright-results.json' }]
  ],
  
  // Output directory for test artifacts
  outputDir: 'test-results/',
  
  // Shared settings
  use: {
    baseURL: API_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    
    // Increase timeouts for stability
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Browser settings
    headless: true,
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  },

  // Projects - simplified without global setup
  projects: [
    // Chrome tests (main)
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
      },
    },

    // Firefox tests (cross-browser)
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
      },
    },

    // Mobile viewport tests
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
      },
    },
  ],
});
