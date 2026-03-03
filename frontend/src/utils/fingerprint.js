/**
 * Device Fingerprinting Utility
 * Collects browser fingerprint data for anti-abuse protection
 */

// Collect canvas fingerprint
const getCanvasFingerprint = () => {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 200;
    canvas.height = 50;
    
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('Visionary Suite', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('Fingerprint', 4, 30);
    
    return canvas.toDataURL();
  } catch (e) {
    return null;
  }
};

// Collect WebGL fingerprint
const getWebGLFingerprint = () => {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (!gl) return { vendor: null, renderer: null };
    
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    
    return {
      vendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : null,
      renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : null
    };
  } catch (e) {
    return { vendor: null, renderer: null };
  }
};

// Get installed fonts (limited set for fingerprinting)
const getInstalledFonts = () => {
  const baseFonts = ['monospace', 'sans-serif', 'serif'];
  const testFonts = [
    'Arial', 'Verdana', 'Times New Roman', 'Courier New', 'Georgia',
    'Palatino', 'Garamond', 'Comic Sans MS', 'Impact', 'Lucida Console'
  ];
  
  const testString = 'mmmmmmmmmmlli';
  const testSize = '72px';
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  
  const getWidth = (fontFamily) => {
    ctx.font = `${testSize} ${fontFamily}`;
    return ctx.measureText(testString).width;
  };
  
  const baseWidths = baseFonts.map(getWidth);
  const installedFonts = [];
  
  testFonts.forEach(font => {
    for (let i = 0; i < baseFonts.length; i++) {
      const testWidth = getWidth(`'${font}', ${baseFonts[i]}`);
      if (testWidth !== baseWidths[i]) {
        installedFonts.push(font);
        break;
      }
    }
  });
  
  return installedFonts;
};

// Get browser plugins
const getPlugins = () => {
  try {
    const plugins = [];
    for (let i = 0; i < navigator.plugins.length && i < 10; i++) {
      plugins.push(navigator.plugins[i].name);
    }
    return plugins;
  } catch (e) {
    return [];
  }
};

/**
 * Collect complete device fingerprint
 * @returns {Object} Fingerprint data object
 */
export const collectFingerprint = async () => {
  const webgl = getWebGLFingerprint();
  
  const fingerprint = {
    // Screen properties
    screen_resolution: `${window.screen.width}x${window.screen.height}`,
    screen_available: `${window.screen.availWidth}x${window.screen.availHeight}`,
    color_depth: window.screen.colorDepth,
    pixel_ratio: window.devicePixelRatio,
    
    // Browser properties
    user_agent: navigator.userAgent,
    language: navigator.language,
    languages: navigator.languages?.join(','),
    platform: navigator.platform,
    hardware_concurrency: navigator.hardwareConcurrency,
    device_memory: navigator.deviceMemory,
    
    // Timezone
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timezone_offset: new Date().getTimezoneOffset(),
    
    // Canvas fingerprint
    canvas: getCanvasFingerprint(),
    
    // WebGL fingerprint
    webgl_vendor: webgl.vendor,
    webgl_renderer: webgl.renderer,
    
    // Fonts
    fonts: getInstalledFonts(),
    
    // Plugins
    plugins: getPlugins(),
    
    // Touch support
    touch_support: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
    max_touch_points: navigator.maxTouchPoints,
    
    // Media devices
    has_webcam: false,
    has_microphone: false,
    
    // Local storage
    local_storage: !!window.localStorage,
    session_storage: !!window.sessionStorage,
    indexed_db: !!window.indexedDB,
    
    // Do Not Track
    do_not_track: navigator.doNotTrack,
    
    // Timestamp
    collected_at: new Date().toISOString()
  };
  
  // Check media devices
  try {
    const devices = await navigator.mediaDevices?.enumerateDevices();
    if (devices) {
      fingerprint.has_webcam = devices.some(d => d.kind === 'videoinput');
      fingerprint.has_microphone = devices.some(d => d.kind === 'audioinput');
    }
  } catch (e) {
    // Media devices not available
  }
  
  return fingerprint;
};

/**
 * Get a hash of the fingerprint for quick comparison
 * Note: Actual hashing happens on the server
 */
export const getFingerprintHash = (fingerprint) => {
  const key = [
    fingerprint.canvas,
    fingerprint.webgl_vendor,
    fingerprint.webgl_renderer,
    fingerprint.screen_resolution,
    fingerprint.timezone,
    fingerprint.language,
    fingerprint.platform
  ].join('|');
  
  // Simple hash for client-side reference (real verification on server)
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    const char = key.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(16);
};

export default collectFingerprint;
