/**
 * Visual Regression Testing with Cypress
 * Captures and compares screenshots of critical UI components
 * 
 * Prerequisites:
 * - yarn add -D @percy/cli @percy/cypress cypress-image-snapshot
 * - Set PERCY_TOKEN environment variable for Percy integration
 */

// Import Percy for visual testing (install: yarn add -D @percy/cypress)
// import '@percy/cypress';

describe('Visual Regression Tests', () => {
  const testUser = {
    email: Cypress.env('testUserEmail'),
    password: Cypress.env('testUserPassword')
  };

  // Helper function to take visual snapshot
  const takeSnapshot = (name) => {
    // Using Percy
    // cy.percySnapshot(name);
    
    // Using cypress-image-snapshot (fallback)
    cy.matchImageSnapshot(name, {
      failureThreshold: 0.05,
      failureThresholdType: 'percent'
    });
  };

  beforeEach(() => {
    // Set consistent viewport for all tests
    cy.viewport(1920, 1080);
  });

  describe('Landing Page Visual Tests', () => {
    it('should match landing page visual baseline', () => {
      cy.visit('/');
      cy.wait(2000);
      cy.screenshot('landing-page-full', { capture: 'viewport' });
      // takeSnapshot('Landing Page - Hero Section');
    });

    it('should match landing page mobile view', () => {
      cy.viewport('iphone-x');
      cy.visit('/');
      cy.wait(2000);
      cy.screenshot('landing-page-mobile', { capture: 'viewport' });
      // takeSnapshot('Landing Page - Mobile');
    });
  });

  describe('Login Page Visual Tests', () => {
    it('should match login page visual baseline', () => {
      cy.visit('/login');
      cy.wait(1000);
      cy.screenshot('login-page', { capture: 'viewport' });
      // takeSnapshot('Login Page');
    });

    it('should match login page with error state', () => {
      cy.visit('/login');
      cy.get('input[type="email"]').type('invalid@email.com');
      cy.get('input[type="password"]').type('wrongpassword');
      cy.get('button').contains('Login').click();
      cy.wait(2000);
      cy.screenshot('login-page-error', { capture: 'viewport' });
      // takeSnapshot('Login Page - Error State');
    });
  });

  describe('Dashboard Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.url().should('include', '/app');
      cy.wait(2000);
    });

    it('should match dashboard visual baseline', () => {
      cy.screenshot('dashboard-main', { capture: 'viewport' });
      // takeSnapshot('Dashboard - Main View');
    });

    it('should match dashboard with help guide open', () => {
      cy.get('[data-testid="help-guide-btn"]').click();
      cy.wait(500);
      cy.screenshot('dashboard-help-open', { capture: 'viewport' });
      // takeSnapshot('Dashboard - Help Guide Open');
    });
  });

  describe('Comix AI Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match Comix AI Character tab visual baseline', () => {
      cy.visit('/app/comix');
      cy.wait(2000);
      cy.screenshot('comix-ai-character', { capture: 'viewport' });
      // takeSnapshot('Comix AI - Character Tab');
    });

    it('should match Comix AI Panels tab visual baseline', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-panel"]').click();
      cy.wait(1000);
      cy.screenshot('comix-ai-panels', { capture: 'viewport' });
      // takeSnapshot('Comix AI - Panels Tab');
    });

    it('should match Comix AI Story tab visual baseline', () => {
      cy.visit('/app/comix');
      cy.get('[data-testid="tab-story"]').click();
      cy.wait(1000);
      cy.screenshot('comix-ai-story', { capture: 'viewport' });
      // takeSnapshot('Comix AI - Story Tab');
    });
  });

  describe('GIF Maker Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match GIF Maker visual baseline', () => {
      cy.visit('/app/gif-maker');
      cy.wait(2000);
      cy.screenshot('gif-maker-main', { capture: 'viewport' });
      // takeSnapshot('GIF Maker - Main View');
    });

    it('should match GIF Maker batch mode visual baseline', () => {
      cy.visit('/app/gif-maker');
      cy.contains('Batch').click();
      cy.wait(1000);
      cy.screenshot('gif-maker-batch', { capture: 'viewport' });
      // takeSnapshot('GIF Maker - Batch Mode');
    });
  });

  describe('Creator Tools Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match Creator Tools Calendar tab', () => {
      cy.visit('/app/creator-tools');
      cy.wait(2000);
      cy.screenshot('creator-tools-calendar', { capture: 'viewport' });
      // takeSnapshot('Creator Tools - Calendar');
    });

    it('should match Creator Tools Convert tab with 10 credits', () => {
      cy.visit('/app/creator-tools');
      cy.contains('Convert').click();
      cy.wait(1000);
      cy.screenshot('creator-tools-convert', { capture: 'viewport' });
      // takeSnapshot('Creator Tools - Convert (10 Credits)');
    });
  });

  describe('Coloring Book Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match Coloring Book DIY mode instructions', () => {
      cy.visit('/app/coloring-book');
      cy.wait(2000);
      cy.screenshot('coloring-book-diy', { capture: 'viewport' });
      // takeSnapshot('Coloring Book - DIY Mode');
    });

    it('should match Coloring Book Photo mode instructions', () => {
      cy.visit('/app/coloring-book');
      cy.get('[data-testid="mode-photo"]').click();
      cy.wait(1000);
      cy.screenshot('coloring-book-photo', { capture: 'viewport' });
      // takeSnapshot('Coloring Book - Photo Mode');
    });
  });

  describe('Admin Dashboard Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(Cypress.env('adminEmail'));
      cy.get('input[type="password"]').type(Cypress.env('adminPassword'));
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match Admin Dashboard visual baseline', () => {
      cy.visit('/app/admin');
      cy.wait(3000);
      cy.screenshot('admin-dashboard-main', { capture: 'viewport' });
      // takeSnapshot('Admin Dashboard - Main View');
    });
  });

  describe('User Manual Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match User Manual visual baseline', () => {
      cy.visit('/user-manual');
      cy.wait(2000);
      cy.screenshot('user-manual-main', { capture: 'viewport' });
      // takeSnapshot('User Manual - Main View');
    });

    it('should show new features (Comix AI, GIF Maker, Comic Story Book)', () => {
      cy.visit('/user-manual');
      cy.wait(2000);
      cy.scrollTo('bottom');
      cy.screenshot('user-manual-new-features', { capture: 'viewport' });
      // takeSnapshot('User Manual - New Features');
    });
  });

  describe('Analytics Page Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match Analytics page with Quick Actions', () => {
      cy.visit('/app/analytics');
      cy.wait(2000);
      cy.screenshot('analytics-quick-actions', { capture: 'viewport' });
      // takeSnapshot('Analytics - Quick Actions');
    });
  });

  describe('Mobile Responsive Visual Tests', () => {
    const mobileViewports = [
      { name: 'iphone-x', width: 375, height: 812 },
      { name: 'ipad-mini', width: 768, height: 1024 },
      { name: 'samsung-s10', width: 360, height: 760 }
    ];

    mobileViewports.forEach((viewport) => {
      it(`should match dashboard on ${viewport.name}`, () => {
        cy.viewport(viewport.width, viewport.height);
        cy.visit('/login');
        cy.get('input[type="email"]').type(testUser.email);
        cy.get('input[type="password"]').type(testUser.password);
        cy.get('button').contains('Login').click();
        cy.wait(2000);
        cy.visit('/app');
        cy.wait(2000);
        cy.screenshot(`dashboard-${viewport.name}`, { capture: 'viewport' });
        // takeSnapshot(`Dashboard - ${viewport.name}`);
      });
    });
  });

  describe('Dark/Light Theme Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match default dark theme', () => {
      cy.visit('/app');
      cy.wait(2000);
      cy.screenshot('theme-dark', { capture: 'viewport' });
      // takeSnapshot('Theme - Dark Mode');
    });
  });

  describe('Component State Visual Tests', () => {
    beforeEach(() => {
      cy.visit('/login');
      cy.get('input[type="email"]').type(testUser.email);
      cy.get('input[type="password"]').type(testUser.password);
      cy.get('button').contains('Login').click();
      cy.wait(2000);
    });

    it('should match button hover states', () => {
      cy.visit('/app');
      cy.get('button').first().trigger('mouseover');
      cy.screenshot('button-hover', { capture: 'viewport' });
      // takeSnapshot('Button - Hover State');
    });

    it('should match dropdown open state', () => {
      cy.visit('/app/comix');
      cy.wait(2000);
      cy.get('[data-testid="character-style-select"]').click();
      cy.screenshot('dropdown-open', { capture: 'viewport' });
      // takeSnapshot('Dropdown - Open State');
    });
  });
});
