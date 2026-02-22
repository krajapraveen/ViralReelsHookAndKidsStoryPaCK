/**
 * Authentication E2E Tests
 * Tests login, signup, logout, and session management
 */

describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.clearAuth();
  });

  describe('Login', () => {
    it('should successfully login with valid credentials', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
      cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
      cy.get('button[type="submit"]').click();
      
      // Should redirect to dashboard
      cy.url().should('include', '/app');
      cy.contains('Welcome back').should('be.visible');
    });

    it('should show error for invalid credentials', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type('invalid@email.com');
      cy.get('input[type="password"]').type('wrongpassword');
      cy.get('button[type="submit"]').click();
      
      // Should show error message
      cy.get('[data-sonner-toast]').should('be.visible');
    });

    it('should validate email format', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type('notanemail');
      cy.get('input[type="password"]').type('Password123!');
      cy.get('button[type="submit"]').click();
      
      // Should not navigate away
      cy.url().should('include', '/login');
    });
  });

  describe('Signup', () => {
    it('should display signup form correctly', () => {
      cy.visit('/signup');
      cy.get('input[name="name"]').should('be.visible');
      cy.get('input[type="email"]').should('be.visible');
      cy.get('input[type="password"]').should('be.visible');
      cy.get('button[type="submit"]').should('be.visible');
    });

    it('should validate password requirements', () => {
      cy.visit('/signup');
      cy.get('input[name="name"]').type('Test User');
      cy.get('input[type="email"]').type('test@example.com');
      cy.get('input[type="password"]').type('weak');
      cy.get('button[type="submit"]').click();
      
      // Should show validation error
      cy.url().should('include', '/signup');
    });
  });

  describe('Logout', () => {
    it('should successfully logout', () => {
      cy.loginAsDemo();
      cy.visit('/app');
      
      // Click logout
      cy.contains('Logout').click();
      
      // Should redirect to landing or login
      cy.url().should('not.include', '/app');
    });
  });

  describe('Protected Routes', () => {
    it('should redirect to login when accessing protected route without auth', () => {
      cy.visit('/app');
      cy.url().should('include', '/login');
    });

    it('should redirect to login when accessing protected API routes', () => {
      cy.visit('/app/reels');
      cy.url().should('include', '/login');
    });
  });
});
