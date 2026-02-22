/**
 * GenStudio E2E Tests
 * Tests AI image and video generation features
 */

describe('GenStudio', () => {
  beforeEach(() => {
    cy.loginAsDemo();
  });

  describe('GenStudio Dashboard', () => {
    beforeEach(() => {
      cy.visit('/app/gen-studio');
    });

    it('should display GenStudio dashboard', () => {
      cy.contains('GenStudio').should('be.visible');
    });

    it('should display wallet balance', () => {
      cy.contains('Credits').should('be.visible');
    });

    it('should display all generation options', () => {
      cy.contains('Text to Image').should('be.visible');
      cy.contains('Text to Video').should('be.visible');
      cy.contains('Image to Video').should('be.visible');
    });

    it('should navigate to Text to Image', () => {
      cy.contains('Text to Image').click();
      cy.url().should('include', '/text-to-image');
    });
  });

  describe('Text to Image', () => {
    beforeEach(() => {
      cy.visit('/app/gen-studio/text-to-image');
    });

    it('should display text to image form', () => {
      cy.contains('Text to Image').should('be.visible');
      cy.get('textarea').should('be.visible');
    });

    it('should show credit cost', () => {
      cy.contains('credits').should('be.visible');
    });
  });

  describe('Help Guide on GenStudio', () => {
    beforeEach(() => {
      cy.visit('/app/gen-studio');
    });

    it('should display help guide', () => {
      cy.getByTestId('help-guide-btn').should('be.visible');
    });

    it('should show GenStudio specific help', () => {
      cy.getByTestId('help-guide-btn').click();
      cy.getByTestId('help-guide-panel').should('be.visible');
      cy.contains('GenStudio').should('be.visible');
    });
  });
});
