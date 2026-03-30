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
 * - Proxy paths (/api/media/r2/KEY) → CDN URL (https://...r2.dev/KEY)
 * - Already absolute URLs → pass through
 * - null/undefined → null
 */
export function resolveMediaUrl(url) {
  if (!url) return null;

  // Already an absolute URL (https://...)
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  // Proxy path: /api/media/r2/KEY → CDN
  if (url.startsWith('/api/media/r2/') && CDN_BASE) {
    const key = url.slice('/api/media/r2/'.length);
    return CDN_BASE + '/' + key;
  }

  // Fallback: relative path → use app origin
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return origin + url;
}
