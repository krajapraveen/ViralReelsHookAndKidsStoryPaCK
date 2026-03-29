/**
 * Cross-browser safe media URL conversion.
 *
 * Routes direct R2 CDN URLs through the backend proxy to ensure
 * proper CORS headers, Content-Type, and byte-range support
 * required by Safari and mobile browsers.
 *
 * Direct R2 CDN URLs (https://pub-*.r2.dev/...) are blocked by
 * Safari's ORB (Opaque Response Blocking) because R2 public URLs
 * don't include Access-Control-Allow-Origin headers.
 */
const API = process.env.REACT_APP_BACKEND_URL;

export function safeMediaUrl(url) {
  if (!url) return null;
  // Already a proxy path — prepend API base
  if (url.startsWith('/api/media/') || url.startsWith('/api/generated/')) {
    return `${API}${url}`;
  }
  // Direct R2 CDN URL — route through backend proxy for CORS safety
  const r2Match = url.match(/^https?:\/\/pub-[a-f0-9]+\.r2\.dev\/(.+)$/);
  if (r2Match) {
    return `${API}/api/media/r2/${r2Match[1]}`;
  }
  return url;
}
