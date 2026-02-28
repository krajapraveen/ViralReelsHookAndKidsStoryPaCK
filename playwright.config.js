// Playwright configuration for stable CI
import { defineConfig, devices } from '@playwright/test';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'https://downloads-recovery.preview.emergentagent.com';

export default defineConfig({
  testDir: './tests/e2e',
  
  // Run tests in parallel
  fullyParallel: true,
  
  // Retry on CI
  retries: process.env.CI ? 2 : 0,
  
  // Limit workers on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }]
  ],
  
  // Shared settings
  use: {
    baseURL: API_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    
    // Increase timeouts for stability
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  // Global setup for auth state
  globalSetup: './tests/e2e/auth-setup.js',

  // Projects
  projects: [
    // Setup project to create auth state
    {
      name: 'setup',
      testMatch: /global-setup\.ts/,
    },
    
    // Chrome tests with auth
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: '.auth/demo-user.json',
      },
      dependencies: ['setup'],
    },

    // Admin tests
    {
      name: 'admin',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/admin-user.json',
      },
      dependencies: ['setup'],
    },
  ],

  // Web server (optional - for local testing)
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
