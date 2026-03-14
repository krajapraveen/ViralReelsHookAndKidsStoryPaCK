import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Run tests in sequence for mobile to avoid rate limiting
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1, // Single worker for mobile tests
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results.json' }],
    ['html', { open: 'never' }]
  ],
  use: {
    baseURL: 'https://engagement-loop-core.preview.emergentagent.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    headless: true,
  },
  projects: [
    {
      name: 'desktop',
      use: { 
        viewport: { width: 1280, height: 720 },
      },
      testMatch: /0[1-4].*\.spec\.ts$/,
    },
    {
      name: 'mobile-comprehensive',
      use: { 
        viewport: { width: 390, height: 844 },
      },
      testMatch: /05-mobile-comprehensive\.spec\.ts$/,
    },
    {
      name: 'mobile-deep',
      use: { 
        viewport: { width: 390, height: 844 },
      },
      testMatch: /06-mobile-deep-functionality\.spec\.ts$/,
    },
    {
      name: 'smoke',
      use: { 
        viewport: { width: 1280, height: 720 },
      },
      testMatch: /smoke-tests\.spec\.ts$/,
    },
    {
      name: 'edge-cases',
      use: { 
        viewport: { width: 1280, height: 720 },
      },
      testMatch: /07-edge-cases\.spec\.ts$/,
    },
  ],
  timeout: 60000,
  expect: {
    timeout: 15000,
  },
});
