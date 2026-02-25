import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 2,
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results.json' }],
    ['html', { open: 'never' }]
  ],
  use: {
    baseURL: 'https://test-phase-runner.preview.emergentagent.com',
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
    },
  ],
  timeout: 60000,
  expect: {
    timeout: 15000,
  },
});
