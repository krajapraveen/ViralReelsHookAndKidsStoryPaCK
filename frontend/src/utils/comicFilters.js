/**
 * Comic Image Processing Utilities
 * Client-side image filters using Canvas API and OpenCV.js
 */

// Check if OpenCV.js is loaded
let opencvReady = false;

// Load OpenCV.js dynamically
export const loadOpenCV = () => {
  return new Promise((resolve, reject) => {
    if (opencvReady) {
      resolve(window.cv);
      return;
    }

    if (window.cv && window.cv.Mat) {
      opencvReady = true;
      resolve(window.cv);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://docs.opencv.org/4.x/opencv.js';
    script.async = true;
    script.onload = () => {
      // Wait for OpenCV to initialize
      const checkReady = setInterval(() => {
        if (window.cv && window.cv.Mat) {
          clearInterval(checkReady);
          opencvReady = true;
          resolve(window.cv);
        }
      }, 100);

      // Timeout after 30 seconds
      setTimeout(() => {
        clearInterval(checkReady);
        reject(new Error('OpenCV.js load timeout'));
      }, 30000);
    };
    script.onerror = () => reject(new Error('Failed to load OpenCV.js'));
    document.head.appendChild(script);
  });
};

/**
 * Apply comic color style using Canvas API (fast, no OpenCV needed)
 */
export const applyComicColorCanvas = (imageData, options = {}) => {
  const { contrast = 1.2, saturation = 1.1, brightness = 1.0, posterize = 8 } = options;
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i];
    let g = data[i + 1];
    let b = data[i + 2];

    // Brightness
    r = r * brightness;
    g = g * brightness;
    b = b * brightness;

    // Contrast
    r = ((r / 255 - 0.5) * contrast + 0.5) * 255;
    g = ((g / 255 - 0.5) * contrast + 0.5) * 255;
    b = ((b / 255 - 0.5) * contrast + 0.5) * 255;

    // Saturation
    const gray = 0.2989 * r + 0.587 * g + 0.114 * b;
    r = gray + saturation * (r - gray);
    g = gray + saturation * (g - gray);
    b = gray + saturation * (b - gray);

    // Posterize (color quantization)
    const levels = posterize;
    r = Math.floor(r / (256 / levels)) * (256 / levels);
    g = Math.floor(g / (256 / levels)) * (256 / levels);
    b = Math.floor(b / (256 / levels)) * (256 / levels);

    // Clamp values
    data[i] = Math.max(0, Math.min(255, r));
    data[i + 1] = Math.max(0, Math.min(255, g));
    data[i + 2] = Math.max(0, Math.min(255, b));
  }

  return imageData;
};

/**
 * Apply edge detection for comic outline effect
 */
export const applyEdgeDetection = (ctx, width, height, threshold = 30) => {
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;
  const output = new Uint8ClampedArray(data.length);

  // Sobel operator
  const sobelX = [-1, 0, 1, -2, 0, 2, -1, 0, 1];
  const sobelY = [-1, -2, -1, 0, 0, 0, 1, 2, 1];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      let gx = 0, gy = 0;

      for (let ky = -1; ky <= 1; ky++) {
        for (let kx = -1; kx <= 1; kx++) {
          const idx = ((y + ky) * width + (x + kx)) * 4;
          const gray = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
          const ki = (ky + 1) * 3 + (kx + 1);
          gx += gray * sobelX[ki];
          gy += gray * sobelY[ki];
        }
      }

      const magnitude = Math.sqrt(gx * gx + gy * gy);
      const idx = (y * width + x) * 4;
      const edge = magnitude > threshold ? 0 : 255;

      output[idx] = edge;
      output[idx + 1] = edge;
      output[idx + 2] = edge;
      output[idx + 3] = 255;
    }
  }

  return new ImageData(output, width, height);
};

/**
 * Apply comic B&W style
 */
export const applyComicBW = (imageData, options = {}) => {
  const { threshold = 128, lineThickness = 1 } = options;
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    // Convert to grayscale
    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    
    // Apply threshold
    const bw = gray > threshold ? 255 : 0;

    data[i] = bw;
    data[i + 1] = bw;
    data[i + 2] = bw;
  }

  return imageData;
};

/**
 * Apply manga style with halftone dots
 */
export const applyMangaStyle = (ctx, width, height, options = {}) => {
  const { dotSize = 4, threshold = 128 } = options;
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;

  // First convert to grayscale
  for (let i = 0; i < data.length; i += 4) {
    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    data[i] = data[i + 1] = data[i + 2] = gray;
  }

  ctx.putImageData(imageData, 0, 0);

  // Create halftone overlay
  const halftoneCanvas = document.createElement('canvas');
  halftoneCanvas.width = width;
  halftoneCanvas.height = height;
  const hCtx = halftoneCanvas.getContext('2d');

  // Draw halftone pattern
  hCtx.fillStyle = '#fff';
  hCtx.fillRect(0, 0, width, height);

  for (let y = 0; y < height; y += dotSize * 2) {
    for (let x = 0; x < width; x += dotSize * 2) {
      const idx = (y * width + x) * 4;
      const brightness = data[idx] / 255;
      const radius = (1 - brightness) * dotSize;

      if (radius > 0.5) {
        hCtx.beginPath();
        hCtx.arc(x + dotSize, y + dotSize, radius, 0, Math.PI * 2);
        hCtx.fillStyle = '#000';
        hCtx.fill();
      }
    }
  }

  return halftoneCanvas;
};

/**
 * Process image with selected style
 */
export const processImage = async (image, style, genreOptions = {}) => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  canvas.width = image.width || image.naturalWidth;
  canvas.height = image.height || image.naturalHeight;

  ctx.drawImage(image, 0, 0);

  let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

  switch (style) {
    case 'comic_color':
      imageData = applyComicColorCanvas(imageData, genreOptions);
      ctx.putImageData(imageData, 0, 0);
      
      // Add edge overlay
      const edgeData = applyEdgeDetection(ctx, canvas.width, canvas.height, 40);
      const edgeCanvas = document.createElement('canvas');
      edgeCanvas.width = canvas.width;
      edgeCanvas.height = canvas.height;
      const edgeCtx = edgeCanvas.getContext('2d');
      edgeCtx.putImageData(edgeData, 0, 0);
      
      // Blend edges with color
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(edgeCanvas, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      break;

    case 'comic_bw':
      imageData = applyComicBW(imageData, { threshold: 140 });
      ctx.putImageData(imageData, 0, 0);
      break;

    case 'manga_bw':
      const halftoneCanvas = applyMangaStyle(ctx, canvas.width, canvas.height);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(halftoneCanvas, 0, 0);
      break;

    default:
      // No processing
      break;
  }

  return canvas;
};

/**
 * Apply cartoon shader effect using Canvas
 */
export const applyCartoonEffect = (imageData, options = {}) => {
  const { levels = 6, edgeThreshold = 50 } = options;
  const data = imageData.data;
  
  // Color quantization for cartoon look
  for (let i = 0; i < data.length; i += 4) {
    data[i] = Math.floor(data[i] / (256 / levels)) * (256 / levels);
    data[i + 1] = Math.floor(data[i + 1] / (256 / levels)) * (256 / levels);
    data[i + 2] = Math.floor(data[i + 2] / (256 / levels)) * (256 / levels);
  }
  
  return imageData;
};

/**
 * Apply pencil sketch effect
 */
export const applySketchEffect = (ctx, width, height) => {
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;
  const output = new Uint8ClampedArray(data.length);
  
  // Convert to grayscale first
  for (let i = 0; i < data.length; i += 4) {
    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    data[i] = data[i + 1] = data[i + 2] = gray;
  }
  
  // Apply Laplacian-like edge detection for sketch effect
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = (y * width + x) * 4;
      
      // Simple edge detection
      const center = data[idx];
      const left = data[idx - 4];
      const right = data[idx + 4];
      const top = data[idx - width * 4];
      const bottom = data[idx + width * 4];
      
      const edge = Math.abs(4 * center - left - right - top - bottom);
      const sketch = 255 - Math.min(255, edge * 2);
      
      output[idx] = sketch;
      output[idx + 1] = sketch;
      output[idx + 2] = sketch;
      output[idx + 3] = 255;
    }
  }
  
  return new ImageData(output, width, height);
};

/**
 * Apply pop art effect
 */
export const applyPopArtEffect = (imageData, options = {}) => {
  const data = imageData.data;
  const colors = [
    [255, 0, 255],   // Magenta
    [0, 255, 255],   // Cyan
    [255, 255, 0],   // Yellow
    [255, 0, 0],     // Red
    [0, 255, 0],     // Green
    [0, 0, 255]      // Blue
  ];
  
  for (let i = 0; i < data.length; i += 4) {
    const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
    const colorIndex = Math.floor((brightness / 256) * colors.length);
    const color = colors[Math.min(colorIndex, colors.length - 1)];
    
    data[i] = color[0];
    data[i + 1] = color[1];
    data[i + 2] = color[2];
  }
  
  return imageData;
};

/**
 * Process image with selected style (ENHANCED with new styles)
 */
export const processImageEnhanced = async (image, style, genreOptions = {}) => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  canvas.width = image.width || image.naturalWidth;
  canvas.height = image.height || image.naturalHeight;

  ctx.drawImage(image, 0, 0);

  let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

  switch (style) {
    case 'comic_color':
      imageData = applyComicColorCanvas(imageData, genreOptions);
      ctx.putImageData(imageData, 0, 0);
      
      // Add edge overlay
      const edgeData = applyEdgeDetection(ctx, canvas.width, canvas.height, 40);
      const edgeCanvas = document.createElement('canvas');
      edgeCanvas.width = canvas.width;
      edgeCanvas.height = canvas.height;
      const edgeCtx = edgeCanvas.getContext('2d');
      edgeCtx.putImageData(edgeData, 0, 0);
      
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(edgeCanvas, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      break;

    case 'comic_bw':
      imageData = applyComicBW(imageData, { threshold: 140 });
      ctx.putImageData(imageData, 0, 0);
      break;

    case 'manga_bw':
      const halftoneCanvas = applyMangaStyle(ctx, canvas.width, canvas.height);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(halftoneCanvas, 0, 0);
      break;

    case 'cartoon':
      imageData = applyCartoonEffect(imageData, { levels: 8 });
      ctx.putImageData(imageData, 0, 0);
      // Add soft edges
      const cartoonEdges = applyEdgeDetection(ctx, canvas.width, canvas.height, 60);
      const cartoonEdgeCanvas = document.createElement('canvas');
      cartoonEdgeCanvas.width = canvas.width;
      cartoonEdgeCanvas.height = canvas.height;
      cartoonEdgeCanvas.getContext('2d').putImageData(cartoonEdges, 0, 0);
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(cartoonEdgeCanvas, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      break;

    case 'sketch':
      const sketchData = applySketchEffect(ctx, canvas.width, canvas.height);
      ctx.putImageData(sketchData, 0, 0);
      break;

    case 'pop_art':
      imageData = applyPopArtEffect(imageData);
      ctx.putImageData(imageData, 0, 0);
      break;

    default:
      // No processing
      break;
  }

  return canvas;
};

/**
 * Advanced processing using OpenCV.js (optional, higher quality)
 */
export const processImageOpenCV = async (image, style, options = {}) => {
  try {
    const cv = await loadOpenCV();
    
    const canvas = document.createElement('canvas');
    canvas.width = image.width || image.naturalWidth;
    canvas.height = image.height || image.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(image, 0, 0);

    const src = cv.imread(canvas);
    const dst = new cv.Mat();

    switch (style) {
      case 'comic_color':
        // Bilateral filter for smoothing while preserving edges
        cv.bilateralFilter(src, dst, 9, 75, 75, cv.BORDER_DEFAULT);
        
        // Edge detection
        const gray = new cv.Mat();
        const edges = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        cv.Canny(gray, edges, 100, 200);
        cv.bitwise_not(edges, edges);
        
        // Combine
        const colorEdges = new cv.Mat();
        cv.cvtColor(edges, colorEdges, cv.COLOR_GRAY2RGBA);
        cv.multiply(dst, colorEdges, dst, 1/255);
        
        gray.delete();
        edges.delete();
        colorEdges.delete();
        break;

      case 'comic_bw':
        cv.cvtColor(src, dst, cv.COLOR_RGBA2GRAY);
        cv.threshold(dst, dst, 127, 255, cv.THRESH_BINARY);
        cv.cvtColor(dst, dst, cv.COLOR_GRAY2RGBA);
        break;

      case 'manga_bw':
        cv.cvtColor(src, dst, cv.COLOR_RGBA2GRAY);
        cv.adaptiveThreshold(dst, dst, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 11, 2);
        cv.cvtColor(dst, dst, cv.COLOR_GRAY2RGBA);
        break;
        
      case 'cartoon':
        // Bilateral filter for cartoon effect
        const temp1 = new cv.Mat();
        cv.bilateralFilter(src, temp1, 9, 150, 150, cv.BORDER_DEFAULT);
        cv.bilateralFilter(temp1, dst, 9, 150, 150, cv.BORDER_DEFAULT);
        temp1.delete();
        break;
        
      case 'sketch':
        // Pencil sketch using edge detection
        const graySketch = new cv.Mat();
        const blurred = new cv.Mat();
        cv.cvtColor(src, graySketch, cv.COLOR_RGBA2GRAY);
        cv.GaussianBlur(graySketch, blurred, new cv.Size(21, 21), 0);
        cv.divide(graySketch, blurred, dst, 256);
        cv.cvtColor(dst, dst, cv.COLOR_GRAY2RGBA);
        graySketch.delete();
        blurred.delete();
        break;

      default:
        src.copyTo(dst);
    }

    cv.imshow(canvas, dst);
    
    src.delete();
    dst.delete();

    return canvas;
  } catch (error) {
    console.warn('OpenCV processing failed, falling back to Canvas:', error);
    return processImageEnhanced(image, style, options);
  }
};

/**
 * Create panel layout canvas
 */
export const createPanelLayout = (panels, layout, options = {}) => {
  const { 
    width = 800, 
    height = 1200, 
    gutterSize = 10,
    borderWidth = 3,
    borderColor = '#000',
    backgroundColor = '#fff'
  } = options;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  // Background
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(0, 0, width, height);

  // Layout configurations
  const layouts = {
    '1': { rows: 1, cols: 1 },
    '2h': { rows: 1, cols: 2 },
    '2v': { rows: 2, cols: 1 },
    '4': { rows: 2, cols: 2 },
    '6': { rows: 3, cols: 2 }
  };

  const config = layouts[layout] || layouts['4'];
  const panelWidth = (width - gutterSize * (config.cols + 1)) / config.cols;
  const panelHeight = (height - gutterSize * (config.rows + 1)) / config.rows;

  const panelPositions = [];

  for (let row = 0; row < config.rows; row++) {
    for (let col = 0; col < config.cols; col++) {
      const panelIndex = row * config.cols + col;
      if (panelIndex >= panels.length) break;

      const x = gutterSize + col * (panelWidth + gutterSize);
      const y = gutterSize + row * (panelHeight + gutterSize);

      panelPositions.push({ x, y, width: panelWidth, height: panelHeight, index: panelIndex });

      // Draw panel border
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = borderWidth;
      ctx.strokeRect(x, y, panelWidth, panelHeight);

      // Draw panel image if available
      const panel = panels[panelIndex];
      if (panel && panel.processedImage) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(x + borderWidth/2, y + borderWidth/2, panelWidth - borderWidth, panelHeight - borderWidth);
        ctx.clip();
        
        // Cover fit
        const img = panel.processedImage;
        const imgAspect = img.width / img.height;
        const panelAspect = panelWidth / panelHeight;
        
        let drawWidth, drawHeight, drawX, drawY;
        
        if (imgAspect > panelAspect) {
          drawHeight = panelHeight - borderWidth;
          drawWidth = drawHeight * imgAspect;
          drawX = x + (panelWidth - drawWidth) / 2;
          drawY = y + borderWidth/2;
        } else {
          drawWidth = panelWidth - borderWidth;
          drawHeight = drawWidth / imgAspect;
          drawX = x + borderWidth/2;
          drawY = y + (panelHeight - drawHeight) / 2;
        }
        
        ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
        ctx.restore();
      }
    }
  }

  return { canvas, panelPositions };
};

/**
 * Add watermark to canvas
 */
export const addWatermark = (canvas, text = 'CreatorStudio AI') => {
  const ctx = canvas.getContext('2d');
  
  ctx.save();
  ctx.globalAlpha = 0.3;
  ctx.font = 'bold 24px Arial';
  ctx.fillStyle = '#666';
  ctx.textAlign = 'center';
  
  // Diagonal watermark pattern
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate(-Math.PI / 6);
  
  for (let y = -canvas.height; y < canvas.height; y += 100) {
    for (let x = -canvas.width; x < canvas.width; x += 300) {
      ctx.fillText(text, x, y);
    }
  }
  
  ctx.restore();
  return canvas;
};

/**
 * Draw stickers on canvas
 */
export const drawStickers = (canvas, stickers) => {
  const ctx = canvas.getContext('2d');
  
  stickers.forEach(sticker => {
    ctx.save();
    
    const x = sticker.x * canvas.width / 100;
    const y = sticker.y * canvas.height / 100;
    const size = sticker.size || 50;
    
    if (sticker.type === 'sfx') {
      // Draw SFX text with comic style
      ctx.translate(x, y);
      ctx.rotate((sticker.rotation || 0) * Math.PI / 180);
      
      // Outer stroke
      ctx.font = `bold ${size}px Impact, sans-serif`;
      ctx.strokeStyle = sticker.strokeColor || '#000';
      ctx.lineWidth = 4;
      ctx.strokeText(sticker.text, 0, 0);
      
      // Fill
      ctx.fillStyle = sticker.color || '#ff0000';
      ctx.fillText(sticker.text, 0, 0);
    } else if (sticker.type === 'bubble') {
      // Draw speech bubble
      ctx.translate(x, y);
      
      const bubbleWidth = Math.max(100, sticker.text.length * 8);
      const bubbleHeight = 50;
      
      // Bubble shape
      ctx.fillStyle = '#fff';
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.beginPath();
      
      if (sticker.bubbleType === 'thought') {
        ctx.ellipse(0, 0, bubbleWidth / 2, bubbleHeight / 2, 0, 0, Math.PI * 2);
      } else if (sticker.bubbleType === 'shout') {
        // Spiky bubble
        const spikes = 12;
        for (let i = 0; i < spikes; i++) {
          const angle = (i / spikes) * Math.PI * 2;
          const r = i % 2 === 0 ? bubbleWidth / 2 : bubbleWidth / 2.5;
          ctx.lineTo(Math.cos(angle) * r, Math.sin(angle) * r * 0.6);
        }
        ctx.closePath();
      } else {
        // Regular speech bubble
        ctx.ellipse(0, 0, bubbleWidth / 2, bubbleHeight / 2, 0, 0, Math.PI * 2);
      }
      
      ctx.fill();
      ctx.stroke();
      
      // Tail
      ctx.beginPath();
      ctx.moveTo(-10, bubbleHeight / 2 - 5);
      ctx.lineTo(-20, bubbleHeight / 2 + 20);
      ctx.lineTo(10, bubbleHeight / 2 - 5);
      ctx.fillStyle = '#fff';
      ctx.fill();
      ctx.stroke();
      
      // Text
      ctx.fillStyle = '#000';
      ctx.font = '14px Comic Sans MS, cursive';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(sticker.text, 0, 0);
    }
    
    ctx.restore();
  });
  
  return canvas;
};

/**
 * Generate social share thumbnail
 */
export const generateShareThumbnail = (canvas, options = {}) => {
  const { width = 600, height = 315, title = 'My Comic' } = options;
  
  const thumbCanvas = document.createElement('canvas');
  thumbCanvas.width = width;
  thumbCanvas.height = height;
  const ctx = thumbCanvas.getContext('2d');
  
  // Background gradient
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, '#667eea');
  gradient.addColorStop(1, '#764ba2');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  
  // Draw comic preview
  const previewSize = Math.min(width * 0.4, height * 0.8);
  const previewX = width - previewSize - 20;
  const previewY = (height - previewSize) / 2;
  
  // Add border/frame
  ctx.fillStyle = '#fff';
  ctx.fillRect(previewX - 5, previewY - 5, previewSize + 10, previewSize + 10);
  
  // Draw scaled comic
  ctx.drawImage(canvas, previewX, previewY, previewSize, previewSize);
  
  // Add title
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 32px Impact, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(title, 30, height / 2 - 20);
  
  // Add subtitle
  ctx.font = '18px Arial, sans-serif';
  ctx.fillText('Created with CreatorStudio AI', 30, height / 2 + 20);
  
  // Add logo/badge
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.beginPath();
  ctx.arc(60, height - 50, 25, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#764ba2';
  ctx.font = 'bold 20px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('🎨', 60, height - 43);
  
  return thumbCanvas;
};

/**
 * Create multi-page comic structure
 */
export const createComicBook = (pages, options = {}) => {
  const { title = 'My Comic Book', author = 'Anonymous' } = options;
  
  return {
    title,
    author,
    createdAt: new Date().toISOString(),
    pageCount: pages.length,
    pages: pages.map((page, index) => ({
      pageNumber: index + 1,
      canvas: page.canvas,
      panels: page.panels,
      stickers: page.stickers || []
    }))
  };
};

