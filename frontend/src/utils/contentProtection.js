/**
 * Content Protection Utilities
 * Implements practical SaaS content protection
 */

// ==================== RIGHT-CLICK PROTECTION ====================
export const disableContextMenu = (element) => {
  if (!element) return;
  
  element.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    return false;
  });
};

export const enableContextMenu = (element) => {
  if (!element) return;
  
  element.removeEventListener('contextmenu', (e) => e.preventDefault());
};

// ==================== TEXT SELECTION PROTECTION ====================
export const disableTextSelection = (element) => {
  if (!element) return;
  
  element.style.userSelect = 'none';
  element.style.webkitUserSelect = 'none';
  element.style.msUserSelect = 'none';
  element.style.MozUserSelect = 'none';
};

export const enableTextSelection = (element) => {
  if (!element) return;
  
  element.style.userSelect = 'auto';
  element.style.webkitUserSelect = 'auto';
  element.style.msUserSelect = 'auto';
  element.style.MozUserSelect = 'auto';
};

// ==================== DRAG PROTECTION ====================
export const disableDrag = (element) => {
  if (!element) return;
  
  element.setAttribute('draggable', 'false');
  element.addEventListener('dragstart', (e) => {
    e.preventDefault();
    return false;
  });
};

// ==================== DEVTOOLS DETERRENCE ====================
export const addDevToolsDeterrence = () => {
  // Block F12
  document.addEventListener('keydown', (e) => {
    if (e.key === 'F12') {
      e.preventDefault();
      return false;
    }
    
    // Block Ctrl+Shift+I
    if (e.ctrlKey && e.shiftKey && e.key === 'I') {
      e.preventDefault();
      return false;
    }
    
    // Block Ctrl+Shift+J (Console)
    if (e.ctrlKey && e.shiftKey && e.key === 'J') {
      e.preventDefault();
      return false;
    }
    
    // Block Ctrl+U (View Source)
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      return false;
    }
  });
};

// ==================== COMPREHENSIVE PROTECTION ====================
export const applyContentProtection = (containerRef) => {
  if (!containerRef?.current) return;
  
  const container = containerRef.current;
  
  // Disable right-click on container
  disableContextMenu(container);
  
  // Disable text selection on output areas
  const outputAreas = container.querySelectorAll('[data-protected="true"]');
  outputAreas.forEach(area => {
    disableTextSelection(area);
    disableContextMenu(area);
  });
  
  // Disable drag on images
  const images = container.querySelectorAll('img');
  images.forEach(img => {
    disableDrag(img);
    disableContextMenu(img);
  });
};

// ==================== PROTECTED IMAGE COMPONENT STYLES ====================
export const protectedImageStyles = {
  userSelect: 'none',
  WebkitUserSelect: 'none',
  MozUserSelect: 'none',
  msUserSelect: 'none',
  pointerEvents: 'none',
  WebkitTouchCallout: 'none',
};

// ==================== WATERMARK OVERLAY STYLES ====================
export const watermarkOverlayStyles = {
  position: 'absolute',
  bottom: '10px',
  right: '10px',
  backgroundColor: 'rgba(0, 0, 0, 0.5)',
  color: 'rgba(255, 255, 255, 0.7)',
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '10px',
  pointerEvents: 'none',
  userSelect: 'none',
  zIndex: 10,
};

// ==================== SUBTLE WATERMARK PATTERN ====================
export const generateWatermarkPattern = (text = 'visionary-suite.com') => {
  // Create a repeating SVG pattern for subtle watermark
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
      <text 
        x="50%" 
        y="50%" 
        font-family="Arial, sans-serif" 
        font-size="12" 
        fill="rgba(128, 128, 128, 0.1)" 
        text-anchor="middle" 
        dominant-baseline="middle"
        transform="rotate(-45, 100, 50)"
      >
        ${text}
      </text>
    </svg>
  `;
  
  const encoded = btoa(svg);
  return `url("data:image/svg+xml;base64,${encoded}")`;
};

// ==================== COPY PROTECTION NOTICE ====================
export const showCopyProtectionNotice = () => {
  // Optional: Show a toast notification when copy is attempted
  console.info('Content is protected. Please use the download button.');
};

// Initialize global deterrence on module load
if (typeof window !== 'undefined') {
  // Add DevTools deterrence (only in production)
  if (process.env.NODE_ENV === 'production') {
    addDevToolsDeterrence();
  }
}

export default {
  disableContextMenu,
  enableContextMenu,
  disableTextSelection,
  enableTextSelection,
  disableDrag,
  addDevToolsDeterrence,
  applyContentProtection,
  protectedImageStyles,
  watermarkOverlayStyles,
  generateWatermarkPattern,
  showCopyProtectionNotice,
};
