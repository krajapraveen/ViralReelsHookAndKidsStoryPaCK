// Comic Studio E2E Tests
describe('Comic Studio', () => {
  const demoUser = {
    email: 'demo@example.com',
    password: 'Password123!'
  };

  beforeEach(() => {
    // Login before each test
    cy.visit('/login');
    cy.get('input[type="email"]').type(demoUser.email);
    cy.get('input[type="password"]').type(demoUser.password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/app');
    
    // Navigate to Comic Studio
    cy.visit('/app/comic-studio');
    cy.get('[data-testid="comic-studio-page"]').should('be.visible');
  });

  describe('Page Load', () => {
    it('should load Comic Studio page', () => {
      cy.contains('Comic Studio').should('be.visible');
      cy.get('[data-testid="genre-selection"]').should('be.visible');
      cy.get('[data-testid="layout-selection"]').should('be.visible');
      cy.get('[data-testid="upload-section"]').should('be.visible');
      cy.get('[data-testid="preview-section"]').should('be.visible');
    });

    it('should show credits display', () => {
      cy.get('[data-testid="credits-display"]').should('be.visible');
    });

    it('should show privacy notice', () => {
      cy.contains('Privacy First').should('be.visible');
      cy.contains('Images are processed on your device').should('be.visible');
    });
  });

  describe('Genre Selection', () => {
    it('should display all 8 genres', () => {
      const genres = ['superhero', 'romance', 'comedy', 'scifi', 'fantasy', 'mystery', 'horror', 'kids'];
      genres.forEach(genre => {
        cy.get(`[data-testid="genre-${genre}"]`).should('be.visible');
      });
    });

    it('should highlight selected genre', () => {
      cy.get('[data-testid="genre-romance"]').click();
      cy.get('[data-testid="genre-romance"]').should('have.class', 'bg-purple-600');
    });

    it('should change genre on click', () => {
      cy.get('[data-testid="genre-comedy"]').click();
      cy.get('[data-testid="genre-comedy"]').should('have.class', 'bg-purple-600');
    });
  });

  describe('Layout Selection', () => {
    it('should display all 5 layouts', () => {
      const layouts = ['1', '2h', '2v', '4', '6'];
      layouts.forEach(layout => {
        cy.get(`[data-testid="layout-${layout}"]`).should('be.visible');
      });
    });

    it('should highlight selected layout', () => {
      cy.get('[data-testid="layout-2h"]').click();
      cy.get('[data-testid="layout-2h"]').should('have.class', 'bg-blue-600');
    });

    it('should update max images text when layout changes', () => {
      cy.get('[data-testid="layout-1"]').click();
      cy.contains('Max 1 for selected layout').should('be.visible');
      
      cy.get('[data-testid="layout-6"]').click();
      cy.contains('Max 6 for selected layout').should('be.visible');
    });
  });

  describe('Style Selection', () => {
    it('should have style dropdown', () => {
      cy.contains('Style').should('be.visible');
      cy.contains('Comic Color').should('be.visible');
    });

    it('should show new advanced filters', () => {
      cy.get('[role="combobox"]').first().click();
      cy.contains('Cartoon Shader').should('be.visible');
      cy.contains('Pencil Sketch').should('be.visible');
      cy.contains('Pop Art').should('be.visible');
    });
  });

  describe('Story Mode', () => {
    it('should toggle story mode', () => {
      cy.get('[data-testid="story-mode-toggle"]').click();
      cy.get('[data-testid="story-mode-toggle"]').should('contain', 'ON');
    });

    it('should show character name input when story mode is ON', () => {
      cy.get('[data-testid="story-mode-toggle"]').click();
      cy.get('[data-testid="character-name-input"]').should('be.visible');
    });

    it('should update export cost when story mode is enabled', () => {
      cy.contains('8 credits').should('be.visible');
      cy.get('[data-testid="story-mode-toggle"]').click();
      cy.contains('Story Mode').should('be.visible');
      cy.contains('+1 credit').should('be.visible');
    });
  });

  describe('Image Upload', () => {
    it('should show upload area', () => {
      cy.get('[data-testid="upload-section"]').should('be.visible');
      cy.contains('Drag & drop or click to upload').should('be.visible');
    });

    it('should have convert button disabled when no images', () => {
      cy.get('[data-testid="convert-to-comic-btn"]').should('be.disabled');
    });

    it('should accept image file input', () => {
      cy.get('[data-testid="image-upload-input"]').should('exist');
    });
  });

  describe('Export Cost', () => {
    it('should display base cost', () => {
      cy.contains('Base (4 panels)').should('be.visible');
      cy.contains('8 credits').should('be.visible');
    });

    it('should show watermark removal cost', () => {
      cy.contains('Remove Watermark').should('be.visible');
      cy.contains('+2 credits').should('be.visible');
    });
  });

  describe('Navigation', () => {
    it('should have back to dashboard button', () => {
      cy.get('[data-testid="back-to-dashboard"]').should('be.visible');
    });

    it('should navigate back to dashboard', () => {
      cy.get('[data-testid="back-to-dashboard"]').click();
      cy.url().should('include', '/app');
    });
  });
});
