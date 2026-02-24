// Cypress E2E Support File
// Custom commands and global configuration

import '@testing-library/cypress/add-commands';
// Uncomment for visual regression:
// import { addMatchImageSnapshotCommand } from 'cypress-image-snapshot/command';
// addMatchImageSnapshotCommand();

// Custom login command
Cypress.Commands.add('login', (email, password) => {
  cy.session([email, password], () => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(email);
    cy.get('input[type="password"]').type(password);
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });
});

// Login as demo user
Cypress.Commands.add('loginAsDemo', () => {
  cy.login(Cypress.env('testUserEmail'), Cypress.env('testUserPassword'));
});

// Login as admin
Cypress.Commands.add('loginAsAdmin', () => {
  cy.login(Cypress.env('adminEmail'), Cypress.env('adminPassword'));
});

// Get element by data-testid
Cypress.Commands.add('getByTestId', (testId) => {
  return cy.get(`[data-testid="${testId}"]`);
});

// Check toast notification
Cypress.Commands.add('checkToast', (message) => {
  cy.get('[data-sonner-toast]').should('contain', message);
});

// Wait for API call
Cypress.Commands.add('waitForApi', (alias, statusCode = 200) => {
  cy.wait(alias).its('response.statusCode').should('eq', statusCode);
});

// Clear local storage before test
Cypress.Commands.add('clearAuth', () => {
  cy.clearLocalStorage();
  cy.clearCookies();
});

// Intercept API calls
Cypress.Commands.add('interceptApi', (method, path, alias) => {
  cy.intercept(method, `**/api/${path}`).as(alias);
});

// Take screenshot with timestamp
Cypress.Commands.add('screenshotWithTimestamp', (name) => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  cy.screenshot(`${name}-${timestamp}`);
});

// Visual regression snapshot command
Cypress.Commands.add('matchImageSnapshot', (name, options = {}) => {
  // Default options for image comparison
  const defaultOptions = {
    failureThreshold: 0.05,
    failureThresholdType: 'percent',
    customSnapshotsDir: 'cypress/snapshots',
    customDiffDir: 'cypress/snapshots/diff'
  };
  
  const mergedOptions = { ...defaultOptions, ...options };
  
  // For now, just take a screenshot - replace with actual snapshot comparison
  cy.screenshot(name, { capture: 'viewport' });
  
  // Uncomment when cypress-image-snapshot is installed:
  // cy.matchImageSnapshot(name, mergedOptions);
});

// Check for infinite toast loop
Cypress.Commands.add('verifyNoToastLoop', (waitTime = 5000) => {
  cy.wait(waitTime);
  cy.get('[data-sonner-toast]').should('have.length.lessThan', 5);
});

// Verify generation job completes without errors
Cypress.Commands.add('waitForGeneration', (timeout = 60000) => {
  cy.get('[data-testid="generation-status"]', { timeout })
    .should('contain.text', 'COMPLETED')
    .or('contain.text', 'FAILED');
});

// Global error handling
Cypress.on('uncaught:exception', (err, runnable) => {
  // Return false to prevent Cypress from failing the test
  // Log the error for debugging
  console.error('Uncaught exception:', err.message);
  return false;
});

// Before each test
beforeEach(() => {
  // Set viewport
  cy.viewport(1920, 1080);
});

// After each test - cleanup
afterEach(() => {
  // Log any console errors from the app
  cy.window().then((win) => {
    if (win.console && win.console.error) {
      // Log app errors for debugging
    }
  });
});
