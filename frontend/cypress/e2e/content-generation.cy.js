/**
 * Content Generation E2E Tests
 * Tests Reel Generator, Story Generator, and Creator Tools
 */

describe('Content Generation', () => {
  beforeEach(() => {
    cy.loginAsDemo();
  });

  describe('Reel Generator', () => {
    beforeEach(() => {
      cy.visit('/app/reels');
    });

    it('should display reel generator form', () => {
      cy.contains('Generate Reel Script').should('be.visible');
      cy.getByTestId('reel-topic-input').should('be.visible');
      cy.getByTestId('reel-niche-select').should('be.visible');
    });

    it('should generate reel content successfully', () => {
      cy.fixture('testData').then((data) => {
        cy.getByTestId('reel-topic-input').type(data.reelTopics[0]);
        cy.getByTestId('reel-generate-btn').click();
        
        // Wait for generation
        cy.get('[data-testid="reel-result"]', { timeout: 30000 }).should('be.visible');
      });
    });

    it('should display generated hooks', () => {
      cy.fixture('testData').then((data) => {
        cy.getByTestId('reel-topic-input').type(data.reelTopics[1]);
        cy.getByTestId('reel-generate-btn').click();
        
        // Should show hooks section
        cy.contains('Hooks', { timeout: 30000 }).should('be.visible');
      });
    });
  });

  describe('Creator Tools - Carousel', () => {
    beforeEach(() => {
      cy.visit('/app/creator-tools');
      cy.getByTestId('tab-carousel').click();
    });

    it('should display carousel generator', () => {
      cy.contains('Carousel Generator').should('be.visible');
      cy.getByTestId('carousel-topic-input').should('be.visible');
    });

    it('should generate carousel content', () => {
      cy.getByTestId('carousel-topic-input').type('5 Morning Habits for Success');
      cy.getByTestId('generate-carousel-btn').click();
      
      // Wait for generation
      cy.getByTestId('carousel-result', { timeout: 15000 }).should('be.visible');
      cy.contains('Slide 1').should('be.visible');
    });
  });

  describe('Creator Tools - Hashtags', () => {
    beforeEach(() => {
      cy.visit('/app/creator-tools');
      cy.getByTestId('tab-hashtags').click();
    });

    it('should display hashtag bank', () => {
      cy.contains('Hashtag Bank').should('be.visible');
    });

    it('should fetch hashtags for niche', () => {
      cy.getByTestId('get-hashtags-btn').click();
      
      // Wait for hashtags
      cy.getByTestId('hashtag-result', { timeout: 10000 }).should('be.visible');
      cy.contains('#').should('be.visible');
    });

    it('should allow copying hashtags', () => {
      cy.getByTestId('get-hashtags-btn').click();
      cy.getByTestId('hashtag-result', { timeout: 10000 }).should('be.visible');
      
      // Click copy button
      cy.contains('Copy All').click();
    });
  });

  describe('Creator Tools - Calendar', () => {
    beforeEach(() => {
      cy.visit('/app/creator-tools');
      cy.getByTestId('tab-calendar').click();
    });

    it('should display content calendar generator', () => {
      cy.contains('30-Day Content Calendar').should('be.visible');
    });
  });

  describe('Creator Tools - Trending', () => {
    beforeEach(() => {
      cy.visit('/app/creator-tools');
      cy.getByTestId('tab-trending').click();
    });

    it('should display trending topics', () => {
      cy.contains('Trending').should('be.visible');
    });

    it('should be free to use', () => {
      cy.contains('FREE').should('be.visible');
    });
  });
});
