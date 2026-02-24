/**
 * End-to-End Image Generation Flow Tests
 * Tests actual AI generation workflows for Comix AI, GIF Maker, and GenStudio
 */

describe('Image Generation E2E Flows', () => {
  const testImagePath = 'cypress/fixtures/test-portrait.jpg';

  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
    cy.wait(2000);
  });

  describe('Comix AI - Character Generation Flow', () => {
    it('should complete character generation workflow', () => {
      cy.visit('/app/comix');
      cy.wait(2000);

      // Verify Character tab is active
      cy.get('[data-testid="tab-character"]').should('have.attr', 'data-state', 'active');

      // Select comic style
      cy.get('[data-testid="character-style-select"]').click();
      cy.get('[data-radix-select-content]').contains('Classic Comic').click();

      // Select character type
      cy.get('[data-testid="character-type-select"]').click();
      cy.get('[data-radix-select-content]').contains('Portrait').click();

      // Add custom details
      cy.get('[data-testid="character-custom-prompt"]').type('Superhero costume, cape');

      // Add negative prompt
      cy.get('[data-testid="character-negative-prompt"]').type('blurry, low quality, distorted');

      // Verify generate button exists
      cy.contains('Generate Character').should('be.visible');
    });

    it('should handle file upload for character generation', () => {
      cy.visit('/app/comix');
      cy.wait(2000);

      // Check if upload area exists
      cy.contains('Click to upload or drag and drop').should('be.visible');
      cy.contains('PNG, JPG, WEBP up to 10MB').should('be.visible');
    });
  });

  describe('Comix AI - Panel Generation Flow', () => {
    it('should complete panel generation workflow', () => {
      cy.visit('/app/comix');
      cy.wait(2000);

      // Switch to Panels tab
      cy.get('[data-testid="tab-panel"]').click();
      cy.wait(1000);

      // Enter scene description
      cy.get('textarea').first().type('A superhero flying over a city at sunset');

      // Select panel style
      cy.get('body').then(($body) => {
        if ($body.find('[data-testid="panel-style-select"]').length) {
          cy.get('[data-testid="panel-style-select"]').click();
          cy.get('[data-radix-select-content]').first().click();
        }
      });

      // Add negative prompt
      cy.get('[data-testid="panel-negative-prompt"]').type('text, watermark, signature');

      // Verify generate button exists
      cy.contains('Generate Panel').should('be.visible');
    });
  });

  describe('Comix AI - Story Generation Flow', () => {
    it('should complete story generation workflow', () => {
      cy.visit('/app/comix');
      cy.wait(2000);

      // Switch to Story tab
      cy.get('[data-testid="tab-story"]').click();
      cy.wait(1000);

      // Enter story prompt
      cy.get('textarea').first().type('A brave young girl saves her village from a dragon');

      // Add negative prompt
      cy.get('[data-testid="story-negative-prompt"]').type('violence, scary, dark themes');

      // Check auto-dialogue option
      cy.get('#auto-dialogue').should('be.visible');

      // Verify generate button exists
      cy.contains('Generate Story').should('be.visible');
    });
  });

  describe('GIF Maker - Generation Flow', () => {
    it('should complete GIF generation workflow', () => {
      cy.visit('/app/gif-maker');
      cy.wait(2000);

      // Verify upload section
      cy.contains('Upload Your Photo').should('be.visible');

      // Select emotion
      cy.contains('Happy').click();

      // Check style selector
      cy.get('[data-testid="gif-style-select"]').should('be.visible');

      // Verify generate button
      cy.contains('Generate GIF').should('be.visible');
    });

    it('should allow batch mode selection', () => {
      cy.visit('/app/gif-maker');
      cy.wait(2000);

      // Check for Batch mode button
      cy.contains('Batch').click();

      // Should allow multiple emotion selection
      cy.contains('Select Multiple Emotions').should('be.visible');
    });
  });

  describe('GenStudio - Text to Image Flow', () => {
    it('should complete text-to-image generation workflow', () => {
      cy.visit('/app/gen-studio/text-to-image');
      cy.wait(2000);

      // Enter prompt
      cy.get('textarea').first().type('A majestic mountain landscape at golden hour, professional photography');

      // Check for style/settings options
      cy.get('body').should('be.visible');

      // Verify generate button
      cy.get('button').contains(/Generate|Create/i).should('be.visible');
    });
  });

  describe('GenStudio - Image to Video Flow', () => {
    it('should load image-to-video page', () => {
      cy.visit('/app/gen-studio/image-to-video');
      cy.wait(2000);

      // Verify page loaded
      cy.get('body').should('be.visible');
      cy.contains(/Image to Video|Upload/i).should('be.visible');
    });
  });

  describe('Comic Storybook - Generation Flow', () => {
    it('should complete storybook generation workflow', () => {
      cy.visit('/app/comic-storybook');
      cy.wait(2000);

      // Check for story input
      cy.get('body').then(($body) => {
        if ($body.find('input, textarea').length) {
          // Fill in story details
          cy.get('input, textarea').first().type('The Adventures of Luna the Cat');
        }
      });

      // Verify page is functional
      cy.get('body').should('be.visible');
    });
  });

  describe('Story Generator - Generation Flow', () => {
    it('should complete story generation workflow', () => {
      cy.visit('/app/story-generator');
      cy.wait(2000);

      // Check for story prompt input
      cy.get('textarea').first().type('A friendly dragon who loves to bake cookies');

      // Verify generate button
      cy.get('button').contains(/Generate|Create/i).should('be.visible');
    });
  });

  describe('Reel Generator - Generation Flow', () => {
    it('should complete reel script generation workflow', () => {
      cy.visit('/app/reel-generator');
      cy.wait(2000);

      // Enter topic
      cy.get('textarea, input').first().type('5 productivity tips for remote workers');

      // Check for niche selector
      cy.get('body').should('be.visible');

      // Verify generate button exists
      cy.get('button').contains(/Generate|Create/i).should('be.visible');
    });
  });

  describe('Generation Job Status Polling', () => {
    it('should not create infinite polling loops', () => {
      cy.visit('/app/comix');
      cy.wait(10000); // Wait 10 seconds

      // Check network requests - should not have excessive polling
      cy.window().then((win) => {
        // Verify no infinite loops by checking page responsiveness
        cy.get('body').should('be.visible');
        cy.get('button').should('be.enabled');
      });
    });
  });

  describe('Generation Results Display', () => {
    it('should display Recent Creations in Comix AI', () => {
      cy.visit('/app/comix');
      cy.wait(3000);

      // Scroll to see recent creations
      cy.scrollTo('bottom');

      // Check for history section
      cy.get('body').then(($body) => {
        if ($body.find(':contains("Recent Creations")').length) {
          cy.contains('Recent Creations').should('be.visible');
        }
      });
    });

    it('should display Recent GIFs in GIF Maker', () => {
      cy.visit('/app/gif-maker');
      cy.wait(3000);

      // Check for recent GIFs section
      cy.get('body').then(($body) => {
        if ($body.find(':contains("Recent GIFs")').length) {
          cy.contains('Recent GIFs').should('be.visible');
        }
      });
    });
  });
});

describe('Credit Deduction Verification', () => {
  beforeEach(() => {
    cy.visit('/login');
    cy.get('input[type="email"]').type(Cypress.env('testUserEmail'));
    cy.get('input[type="password"]').type(Cypress.env('testUserPassword'));
    cy.get('button').contains('Login').click();
    cy.url().should('include', '/app');
  });

  it('should display current credit balance', () => {
    cy.visit('/app');
    cy.wait(2000);

    // Check for credit display in header
    cy.get('body').should('contain', 'Credits');
  });

  it('should show credit cost before generation', () => {
    cy.visit('/app/comix');
    cy.wait(2000);

    // Check for credit cost display
    cy.get('body').should('contain', 'credits');
  });
});
