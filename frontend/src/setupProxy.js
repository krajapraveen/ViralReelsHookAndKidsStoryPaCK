const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Cross-Origin Isolation headers — required for SharedArrayBuffer (ffmpeg.wasm)
  app.use((req, res, next) => {
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'credentialless');
    next();
  });
};
