/**
 * Landing Page E2E Tests
 * Tests public pages and navigation
 */

describe('Landing Page', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  describe('Navigation Links', () => {
    it('should display navigation menu', () => {
      cy.contains('CreatorStudio').should('be.visible');
    });

    it('should navigate to Pricing', () => {
      cy.getByTestId('nav-pricing-btn').click();
      cy.url().should('include', '/pricing');
    });

    it('should navigate to Reviews', () => {
      cy.getByTestId('nav-reviews-btn').click();
      cy.url().should('include', '/reviews');
    });

    it('should navigate to Help', () => {
      cy.getByTestId('nav-help-btn').click();
      cy.url().should('include', '/user-manual');
    });

    it('should navigate to Contact', () => {
      cy.getByTestId('nav-contact-btn').click();
      cy.url().should('include', '/contact');
    });

    it('should navigate to Login', () => {
      cy.getByTestId('nav-login-btn').click();
      cy.url().should('include', '/login');
    });

    it('should navigate to Signup', () => {
      cy.getByTestId('nav-signup-btn').click();
      cy.url().should('include', '/signup');
    });
  });

  describe('Hero Section', () => {
    it('should display hero content', () => {
      cy.contains('Generate viral').should('be.visible');
    });

    it('should display CTA buttons', () => {
      cy.contains('Try Free Demo').should('be.visible');
    });
  });

  describe('Feature Sections', () => {
    it('should display feature highlights', () => {
      cy.contains('Reel').should('be.visible');
    });
  });
});

describe('Pricing Page', () => {
  beforeEach(() => {
    cy.visit('/pricing');
  });

  it('should display pricing plans', () => {
    cy.contains('Pricing').should('be.visible');
  });

  it('should display credit packages', () => {
    cy.contains('Credits').should('be.visible');
  });
});

describe('Contact Page', () => {
  beforeEach(() => {
    cy.visit('/contact');
  });

  it('should display contact form', () => {
    cy.contains('Contact').should('be.visible');
  });
});

describe('User Manual', () => {
  beforeEach(() => {
    cy.visit('/user-manual');
  });

  it('should display user manual', () => {
    cy.contains('User Manual').should('be.visible');
  });

  it('should have searchable content', () => {
    cy.get('input[type="search"]').should('be.visible');
  });
});
