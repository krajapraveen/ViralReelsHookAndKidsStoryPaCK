/**
 * Admin Dashboard E2E Tests
 * Tests admin-specific functionality
 */

describe('Admin Dashboard', () => {
  beforeEach(() => {
    cy.loginAsAdmin();
  });

  describe('Admin Access', () => {
    it('should access admin dashboard', () => {
      cy.visit('/app/admin');
      cy.contains('Admin').should('be.visible');
    });

    it('should display admin statistics', () => {
      cy.visit('/app/admin');
      cy.contains('Users').should('be.visible');
    });
  });

  describe('Admin Monitoring', () => {
    it('should access monitoring page', () => {
      cy.visit('/app/admin/monitoring');
      cy.contains('Monitoring').should('be.visible');
    });

    it('should display system metrics', () => {
      cy.visit('/app/admin/monitoring');
      cy.contains('Security').should('be.visible');
    });
  });

  describe('Admin Help Guide', () => {
    it('should show admin-specific help', () => {
      cy.visit('/app/admin');
      cy.getByTestId('help-guide-btn').click();
      cy.getByTestId('help-guide-panel').should('be.visible');
      cy.contains('Admin').should('be.visible');
    });
  });
});
