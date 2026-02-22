/**
 * Dashboard E2E Tests
 * Tests main dashboard functionality and navigation
 */

describe('Dashboard', () => {
  beforeEach(() => {
    cy.loginAsDemo();
    cy.visit('/app');
  });

  describe('Dashboard Display', () => {
    it('should display welcome message', () => {
      cy.contains('Welcome back').should('be.visible');
    });

    it('should display credit balance', () => {
      cy.getByTestId('credit-balance').should('be.visible');
    });

    it('should display all main feature cards', () => {
      cy.getByTestId('quick-action-reel').should('be.visible');
      cy.getByTestId('quick-action-story').should('be.visible');
      cy.getByTestId('quick-action-gen-studio').should('be.visible');
      cy.getByTestId('quick-action-creator-tools').should('be.visible');
    });
  });

  describe('Navigation from Dashboard', () => {
    it('should navigate to Reel Generator', () => {
      cy.getByTestId('quick-action-reel').click();
      cy.url().should('include', '/app/reels');
    });

    it('should navigate to Story Generator', () => {
      cy.getByTestId('quick-action-story').click();
      cy.url().should('include', '/app/stories');
    });

    it('should navigate to GenStudio', () => {
      cy.getByTestId('quick-action-gen-studio').click();
      cy.url().should('include', '/app/gen-studio');
    });

    it('should navigate to Creator Tools', () => {
      cy.getByTestId('quick-action-creator-tools').click();
      cy.url().should('include', '/app/creator-tools');
    });
  });

  describe('Help Guide', () => {
    it('should display help guide button', () => {
      cy.getByTestId('help-guide-btn').should('be.visible');
    });

    it('should open help guide panel on click', () => {
      cy.getByTestId('help-guide-btn').click();
      cy.getByTestId('help-guide-panel').should('be.visible');
    });

    it('should close help guide on second click', () => {
      cy.getByTestId('help-guide-btn').click();
      cy.getByTestId('help-guide-panel').should('be.visible');
      cy.getByTestId('help-guide-btn').click();
      cy.getByTestId('help-guide-panel').should('not.exist');
    });
  });
});
