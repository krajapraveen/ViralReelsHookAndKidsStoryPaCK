/**
 * Media URL resolver — converts proxy paths to direct R2 CDN URLs.
 * 
 * WHY: K8s ingress overrides Cache-Control to "no-store" on proxy responses.
 * Safari strictly obeys no-store → media fails to render/cache properly.
 * Direct R2 CDN serves: Cache-Control: public, max-age=31536000, immutable.
 *
 * HOW: Backend returns proxy paths (/api/media/r2/...).
 *      Frontend resolves to CDN URLs at render time.
 *      If CDN unavailable, falls back to proxy path with origin prefix.
 */

// CDN base is set once from the feed API response
let CDN_BASE = '';

export function setCdnBase(base) {
  if (base && typeof base === 'string') {
    CDN_BASE = base.replace(/\/+$/, '');
  }
}

export function getCdnBase() {
  return CDN_BASE;
}

/**
 * Resolve a media URL for use as <img src> or <video src>.
 * - Image proxy paths (/api/media/r2/images/...) → CDN URL (fast, Safari-safe)
 * - Video proxy paths (/api/media/r2/videos/...) → origin proxy (CORS-safe streaming)
 * - Already absolute URLs → pass through
 * - null/undefined → null
 *
 * NOTE: Videos must use origin proxy because R2 public bucket has no CORS headers,
 * and cross-origin video loading triggers ORB (Opaque Response Blocking) in browsers.
 * Images use CDN because they need proper Cache-Control for Safari rendering.
 */
export function resolveMediaUrl(url) {
  if (!url) return null;

  // Already an absolute URL (https://...)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  // Proxy path: /api/media/r2/KEY
  if (url.startsWith('/api/media/r2/') && CDN_BASE) {
    const key = url.slice('/api/media/r2/'.length);
    // Only CDN-ify images (not videos — no CORS headers on R2)
    if (!key.startsWith('videos/')) {
      return CDN_BASE + '/' + key;
    }
  }

  // Fallback: relative path → use app origin (proxy)
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return origin + url;
}
