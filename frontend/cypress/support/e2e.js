// Cypress E2E Support File
// Custom commands and global configuration

import '@testing-library/cypress/add-commands';

// Custom login command
Cypress.Commands.add('login', (email, password) => {
  cy.session([email, password], () => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(email);
    cy.get('input[type="password"]').type(password);
    cy.get('button[type="submit"]').click();
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
