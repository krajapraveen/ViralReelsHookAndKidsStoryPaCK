const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || 'https://photo-to-comic-1.preview.emergentagent.com',
    supportFile: 'cypress/support/e2e.js',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    viewportWidth: 1920,
    viewportHeight: 1080,
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 15000,
    responseTimeout: 30000,
    retries: {
      runMode: 2,
      openMode: 0,
    },
    env: {
      // Test credentials
      testUserEmail: 'demo@example.com',
      testUserPassword: 'Password123!',
      adminEmail: 'admin@creatorstudio.ai',
      adminPassword: 'Cr3@t0rStud!o#2026',
    },
  },
  component: {
    devServer: {
      framework: 'create-react-app',
      bundler: 'webpack',
    },
  },
});
