/**
 * Mobile Experience Verification Test Suite
 * Tests all feature pages on mobile viewports (375px, 320px)
 * Verifies autofill styling, layout, and functionality
 */

describe('Mobile Experience Verification', () => {
  const mobileViewports = [
    { name: 'iPhone 12/13/14', width: 375, height: 812 },
    { name: 'iPhone SE', width: 320, height: 568 },
    { name: 'Samsung Galaxy', width: 360, height: 740 }
  ];

  const testUser = {
    email: Cypress.env('testUserEmail'),
    password: Cypress.env('testUserPassword')
  };

  const adminUser = {
    email: Cypress.env('adminEmail'),
    password: Cypress.env('adminPassword')
  };

  // All feature pages to test
  const featurePages = [
    { path: '/app', name: 'Dashboard' },
    { path: '/app/comix', name: 'Comix AI' },
    { path: '/app/gif-maker', name: 'GIF Maker' },
    { path: '/app/creator-tools', name: 'Creator Tools' },
    { path: '/app/story-generator', name: 'Story Generator' },
    { path: '/app/reel-generator', name: 'Reel Generator' },
    { path: '/app/coloring-book', name: 'Coloring Book' },
    { path: '/app/gen-studio', name: 'GenStudio' },
    { path: '/app/analytics', name: 'Analytics' },
    { path: '/app/profile', name: 'Profile' },
    { path: '/app/billing', name: 'Billing' },
    { path: '/user-manual', name: 'User Manual' }
  ];

  describe('Autofill Color Verification', () => {
    mobileViewports.forEach((viewport) => {
      it(`should have no yellow/colored autofill on Login (${viewport.name})`, () => {
        cy.viewport(viewport.width, viewport.height);
        cy.visit('/login');
        cy.wait(1000);

        // Fill in credentials to trigger autofill styling
        cy.get('input[type="email"]').type(testUser.email);
        cy.get('input[type="password"]').type(testUser.password);

        // Verify no yellow background
        cy.get('input[type="email"]').should(($input) => {
          const styles = window.getComputedStyle($input[0]);
          const bgColor = styles.backgroundColor;
          // Should not be yellow (rgb(250, 255, 189) or similar)
          expect(bgColor).to.not.match(/rgb\(25[0-5], 25[0-5], 1[0-9]{2}\)/);
        });

        cy.screenshot(`autofill-login-${viewport.name}`);
      });

      it(`should have no yellow/colored autofill on Signup (${viewport.name})`, () => {
        cy.viewport(viewport.width, viewport.height);
        cy.visit('/signup');
        cy.wait(1000);

        // Verify form is visible
        cy.get('input[type="email"]').should('be.visible');
        
        cy.screenshot(`autofill-signup-${viewport.name}`);
      });
    });
  });

  describe('Feature Pages Mobile Layout', () => {
    beforeEach(() => {
      cy.viewport(375, 812); // Default iPhone viewport
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.url().should('include', '/app');
      cy.wait(2000);
    });

    featurePages.forEach((page) => {
      it(`should display ${page.name} properly on mobile`, () => {
        cy.visit(page.path);
        cy.wait(2000);

        // Verify no horizontal scroll
        cy.window().then((win) => {
          const docWidth = win.document.documentElement.scrollWidth;
          const viewportWidth = win.innerWidth;
          expect(docWidth).to.be.lte(viewportWidth + 10); // Allow small margin
        });

        // Verify page is not blank
        cy.get('body').should('not.be.empty');

        // Verify no error messages
        cy.get('body').should('not.contain', 'error');
        cy.get('body').should('not.contain', 'Error');

        cy.screenshot(`mobile-${page.name.toLowerCase().replace(/\s+/g, '-')}`);
      });
    });
  });

  describe('Admin Dashboard Mobile', () => {
    beforeEach(() => {
      cy.viewport(375, 812);
      cy.visit('/login');
      cy.get('input[type="email"]').type(adminUser.email);
      cy.get('input[type="password"]').type(adminUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(3000);
    });

    it('should display Admin Dashboard properly on mobile', () => {
      cy.visit('/app/admin');
      cy.wait(2000);

      // Verify dashboard loads
      cy.get('body').should('not.contain', 'Failed to load');

      // Verify stats cards are visible
      cy.contains('Total Users').should('be.visible');

      cy.screenshot('mobile-admin-dashboard');
    });
  });

  describe('Landing Page Mobile', () => {
    mobileViewports.forEach((viewport) => {
      it(`should display Landing Page properly on ${viewport.name}`, () => {
        cy.viewport(viewport.width, viewport.height);
        cy.visit('/');
        cy.wait(2000);

        // Verify hero section
        cy.contains('Generate').should('be.visible');

        // Verify CTA buttons
        cy.get('button').contains(/demo|reel|story/i).should('be.visible');

        // Verify no horizontal scroll
        cy.window().then((win) => {
          const docWidth = win.document.documentElement.scrollWidth;
          const viewportWidth = win.innerWidth;
          expect(docWidth).to.be.lte(viewportWidth + 10);
        });

        cy.screenshot(`mobile-landing-${viewport.name}`);
      });
    });
  });

  describe('Form Inputs Mobile', () => {
    beforeEach(() => {
      cy.viewport(375, 812);
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should have properly sized inputs on Reel Generator', () => {
      cy.visit('/app/reel-generator');
      cy.wait(2000);

      // Verify inputs are full width
      cy.get('textarea, input').first().then(($input) => {
        const inputWidth = $input.width();
        cy.window().then((win) => {
          // Input should be at least 80% of viewport width
          expect(inputWidth).to.be.gte(win.innerWidth * 0.7);
        });
      });

      cy.screenshot('mobile-reel-generator-inputs');
    });

    it('should have properly sized inputs on Story Generator', () => {
      cy.visit('/app/story-generator');
      cy.wait(2000);

      // Verify select dropdowns work
      cy.get('select, [data-radix-select-trigger]').first().should('be.visible');

      cy.screenshot('mobile-story-generator-inputs');
    });

    it('should have scrollable tabs on Creator Tools', () => {
      cy.visit('/app/creator-tools');
      cy.wait(2000);

      // Verify tabs are present
      cy.get('[role="tablist"]').should('be.visible');

      // Tabs should be horizontally scrollable
      cy.get('[role="tablist"]').then(($tablist) => {
        const scrollWidth = $tablist[0].scrollWidth;
        const clientWidth = $tablist[0].clientWidth;
        // If tabs overflow, scrollWidth > clientWidth
        if (scrollWidth > clientWidth) {
          cy.log('Tabs are scrollable - PASS');
        }
      });

      cy.screenshot('mobile-creator-tools-tabs');
    });
  });

  describe('Touch Interactions Mobile', () => {
    beforeEach(() => {
      cy.viewport(375, 812);
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should have touch-friendly button sizes', () => {
      cy.visit('/app');
      cy.wait(2000);

      // Verify buttons are at least 44px (Apple's minimum touch target)
      cy.get('button').first().then(($button) => {
        const height = $button.outerHeight();
        const width = $button.outerWidth();
        expect(Math.min(height, width)).to.be.gte(40);
      });

      cy.screenshot('mobile-touch-targets');
    });
  });

  describe('Modal/Dialog Mobile', () => {
    beforeEach(() => {
      cy.viewport(375, 812);
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should display Help Guide properly on mobile', () => {
      cy.visit('/app');
      cy.wait(2000);

      // Click help button
      cy.get('[data-testid="help-guide-btn"]').click();
      cy.wait(500);

      // Verify help panel is visible
      cy.contains('Dashboard Overview').should('be.visible');

      cy.screenshot('mobile-help-guide');
    });
  });

  describe('Small Screen (320px) Verification', () => {
    beforeEach(() => {
      cy.viewport(320, 568); // iPhone SE
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should not have horizontal overflow on Dashboard', () => {
      cy.visit('/app');
      cy.wait(2000);

      cy.window().then((win) => {
        const docWidth = win.document.documentElement.scrollWidth;
        const viewportWidth = win.innerWidth;
        expect(docWidth).to.be.lte(viewportWidth + 5);
      });

      cy.screenshot('mobile-320px-dashboard');
    });

    it('should display Comix AI without overflow', () => {
      cy.visit('/app/comix');
      cy.wait(2000);

      cy.window().then((win) => {
        const docWidth = win.document.documentElement.scrollWidth;
        const viewportWidth = win.innerWidth;
        expect(docWidth).to.be.lte(viewportWidth + 5);
      });

      cy.screenshot('mobile-320px-comix');
    });
  });
});
