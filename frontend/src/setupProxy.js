const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // P0 2026-06-PROD-FOLLOWUP — COEP/COOP REMOVED.
  // These headers were added speculatively for SharedArrayBuffer
  // (ffmpeg.wasm) but they broke cross-origin video playback from R2
  // in production (the photo-trailer result page). BrowserVideoExport
  // already falls back to single-threaded ffmpeg.wasm via its
  // `hasSAB` guard, so removing the headers is the correct trade.
  // Keep this dev proxy aligned with the production server.py state
  // so preview-environment testing reproduces prod behaviour exactly.

  // Proxy /sitemap.xml to backend API for dynamic generation
  app.use(
    '/sitemap.xml',
    createProxyMiddleware({
      target: 'http://localhost:8001',
      changeOrigin: true,
      pathRewrite: { '^/sitemap.xml': '/api/public/sitemap.xml' },
    })
  );
};
