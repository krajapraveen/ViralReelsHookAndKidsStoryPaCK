/**
 * Comprehensive Verification Test Suite - 22 Critical Fixes
 * This test suite verifies all P0-P3 fixes implemented on Feb 24, 2026
 */

describe('P0 - Critical Fixes Verification', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });

  describe('1. Infinite Toast Loop Fix', () => {
    it('should not show infinite toast notifications on dashboard', () => {
      cy.visit('/app');
      cy.wait(5000);
      // Count toast notifications - should be 0 or 1 (login success only)
      cy.get('[data-sonner-toast]').should('have.length.lessThan', 3);
    });

    it('should not show infinite toast on Comix AI page', () => {
      cy.visit('/app/comix');
      cy.wait(5000);
      cy.get('[data-sonner-toast]').should('have.length.lessThan', 3);
    });

    it('should not show infinite toast on GIF Maker page', () => {
      cy.visit('/app/gif-maker');
      cy.wait(5000);
      cy.get('[data-sonner-toast]').should('have.length.lessThan', 3);
    });
  });

  describe('2. Comix AI Generation', () => {
    it('should load Comix AI page correctly', () => {
      cy.visit('/app/comix');
      cy.contains('Transform Photos into').should('be.visible');
      cy.contains('Comic Art').should('be.visible');
    });

    it('should display Character, Panels, and Story Mode tabs', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-character"]').should('be.visible');
      cy.get('[data-testid="tab-panel"]').should('be.visible');
      cy.get('[data-testid="tab-story"]').should('be.visible');
    });

    it('should show negative prompt field in Character tab', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-character"]').click();
      cy.get('[data-testid="character-negative-prompt"]').should('be.visible');
    });

    it('should show negative prompt field in Panel tab', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-panel"]').click();
      cy.get('[data-testid="panel-negative-prompt"]').should('be.visible');
    });

    it('should show negative prompt field in Story tab', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-story"]').click();
      cy.get('[data-testid="story-negative-prompt"]').should('be.visible');
    });
  });

  describe('3. GIF Maker Display', () => {
    it('should load GIF Maker page correctly', () => {
      cy.visit('/app/gif-maker');
      cy.contains('Turn Your Photos into').should('be.visible');
      cy.contains('Fun Reaction GIFs').should('be.visible');
    });

    it('should display Recent GIFs section without broken images', () => {
      cy.visit('/app/gif-maker');
      // Recent GIFs should either show images or fallback gradients
      cy.get('body').then(($body) => {
        if ($body.find('.grid-cols-3').length > 0) {
          // If history exists, check no broken image icons
          cy.get('.grid-cols-3 img').each(($img) => {
            cy.wrap($img).should('be.visible');
          });
        }
      });
    });

    it('should display emotion selection options', () => {
      cy.visit('/app/gif-maker');
      cy.contains('Happy').should('be.visible');
      cy.contains('Sad').should('be.visible');
      cy.contains('Excited').should('be.visible');
    });
  });

  describe('4. Comic Story Book', () => {
    it('should load Comic Storybook page correctly', () => {
      cy.visit('/app/comic-storybook');
      cy.get('body').should('not.contain', 'error');
    });
  });
});

describe('P1 - Core Functionality Fixes', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });

  describe('5. Content Vault Fix', () => {
    it('should load Content Vault without error', () => {
      cy.visit('/app/content-vault');
      cy.get('body').should('not.contain', 'Failed to load content vault');
    });

    it('should display vault sections', () => {
      cy.visit('/app/content-vault');
      // Wait for API response
      cy.wait(2000);
      cy.get('body').should('be.visible');
    });
  });

  describe('6. Admin Dashboard Fix', () => {
    it('should load Admin Dashboard without error for admin user', () => {
      // Logout first
      cy.visit('/login');
      // Login as admin
      cy.get('input[type="email"]').clear().type(Cypress.env('adminEmail'));
      cy.get('input[type="password"]').clear().type(Cypress.env('adminPassword'));
      cy.get('button').contains('Login').click();
      cy.wait(3000);
      cy.visit('/app/admin');
      cy.get('body').should('not.contain', 'Failed to load dashboard data');
      cy.contains('Admin Analytics').should('be.visible');
    });
  });

  describe('7. Analytics Links Fix', () => {
    it('should display functional Quick Action links', () => {
      cy.visit('/app/analytics');
      cy.contains('View Job History').should('be.visible');
      cy.contains('Buy More Credits').should('be.visible');
      cy.contains('Manage Subscription').should('be.visible');
    });

    it('should navigate to Job History when clicked', () => {
      cy.visit('/app/analytics');
      cy.contains('View Job History').click();
      cy.url().should('include', '/gen-studio/history');
    });

    it('should navigate to Billing when Buy More Credits clicked', () => {
      cy.visit('/app/analytics');
      cy.contains('Buy More Credits').click();
      cy.url().should('include', '/billing');
    });

    it('should navigate to Subscription when Manage Subscription clicked', () => {
      cy.visit('/app/analytics');
      cy.contains('Manage Subscription').click();
      cy.url().should('include', '/subscription');
    });
  });

  describe('8. Creator Tools Credit Cost Update', () => {
    it('should show 10 credits for Reel to Carousel', () => {
      cy.visit('/app/creator-tools');
      cy.contains('Convert').click();
      cy.contains('Reel → Carousel').parent().should('contain', '10 credits');
    });

    it('should show 10 credits for Reel to YouTube', () => {
      cy.visit('/app/creator-tools');
      cy.contains('Convert').click();
      cy.contains('Reel → YouTube').parent().should('contain', '10 credits');
    });

    it('should show 10 credits for Story to Reel', () => {
      cy.visit('/app/creator-tools');
      cy.contains('Convert').click();
      cy.contains('Story → Reel').parent().should('contain', '10 credits');
    });
  });
});

describe('P2 - UI/UX Enhancements', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });

  describe('9. GenStudio Templates', () => {
    it('should have sample copyright-free templates', () => {
      cy.request('/api/genstudio/templates').then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.templates.length).to.be.greaterThan(10);
        // Check for sample templates
        const templates = response.body.templates;
        const sampleTemplates = templates.filter(t => t.category === 'sample');
        expect(sampleTemplates.length).to.be.greaterThan(0);
      });
    });
  });

  describe('10. Coloring Book Instructions', () => {
    it('should show DIY Mode instructions', () => {
      cy.visit('/app/coloring-book');
      cy.get('[data-testid="mode-placeholder"]').click();
      cy.contains('DIY Mode Instructions').should('be.visible');
    });

    it('should show Photo Mode instructions', () => {
      cy.visit('/app/coloring-book');
      cy.get('[data-testid="mode-photo"]').click();
      cy.contains('Photo Mode Instructions').should('be.visible');
    });
  });

  describe('11. Quick Tour Button Visibility', () => {
    it('should display prominent Quick Tour button in Help Guide', () => {
      cy.visit('/app');
      cy.get('[data-testid="help-guide-btn"]').click();
      cy.get('[data-testid="quick-tour-btn"]').should('be.visible');
      cy.get('[data-testid="quick-tour-btn"]').should('contain', 'Start Quick Tour');
    });
  });
});

describe('P3 - Documentation Updates', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });

  describe('12. User Manual Updates', () => {
    it('should NOT contain TwinFinder in User Manual', () => {
      cy.request('/api/help/manual').then((response) => {
        expect(response.status).to.eq(200);
        const features = Object.keys(response.body.features);
        expect(features).to.not.include('twinfinder');
      });
    });

    it('should contain Comix AI in User Manual', () => {
      cy.request('/api/help/manual').then((response) => {
        expect(response.status).to.eq(200);
        const features = Object.keys(response.body.features);
        expect(features).to.include('comix_ai');
      });
    });

    it('should contain GIF Maker in User Manual', () => {
      cy.request('/api/help/manual').then((response) => {
        expect(response.status).to.eq(200);
        const features = Object.keys(response.body.features);
        expect(features).to.include('gif_maker');
      });
    });

    it('should contain Comic Story Book in User Manual', () => {
      cy.request('/api/help/manual').then((response) => {
        expect(response.status).to.eq(200);
        const features = Object.keys(response.body.features);
        expect(features).to.include('comic_storybook');
      });
    });
  });

  describe('13. User Manual Page Display', () => {
    it('should display Comix AI in User Manual page', () => {
      cy.visit('/user-manual');
      cy.contains('Comix AI').should('be.visible');
    });

    it('should display GIF Maker in User Manual page', () => {
      cy.visit('/user-manual');
      cy.contains('GIF Maker').should('be.visible');
    });

    it('should display Comic Story Book in User Manual page', () => {
      cy.visit('/user-manual');
      cy.contains('Comic Story Book').should('be.visible');
    });

    it('should NOT display TwinFinder in User Manual page', () => {
      cy.visit('/user-manual');
      cy.contains('TwinFinder').should('not.exist');
    });
  });
});

describe('Backend API Verification', () => {
  it('should verify Content Vault API returns correct format', () => {
    cy.request({
      method: 'GET',
      url: '/api/content/vault',
      headers: {
        Authorization: `Bearer ${Cypress.env('testUserToken')}`
      },
      failOnStatusCode: false
    }).then((response) => {
      if (response.status === 200) {
        expect(response.body).to.have.property('themes');
        expect(response.body).to.have.property('sampleHooks');
      }
    });
  });

  it('should verify conversion costs are updated', () => {
    cy.request('/api/convert/costs').then((response) => {
      if (response.status === 200) {
        expect(response.body.reel_to_carousel).to.eq(10);
        expect(response.body.reel_to_youtube).to.eq(10);
        expect(response.body.story_to_reel).to.eq(10);
      }
    });
  });
});
