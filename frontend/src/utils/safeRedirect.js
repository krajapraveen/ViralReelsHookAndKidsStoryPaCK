/**
 * P0 Security Hardening — Safe redirect sanitizer (2026-06)
 * =========================================================
 *
 * Bug class: Open redirect via post-login `?next=` / `?return=` param.
 *
 * Attack surface:
 *   /login?next=https://evil.com         → external phishing
 *   /login?next=//evil.com               → scheme-relative bypass
 *   /login?next=javascript:alert(1)      → XSS via navigation
 *   /login?next=data:text/html,<script>  → data-URL exfil
 *   /login?next=%2F%2Fevil.com           → encoded bypass
 *
 * Contract for a "safe" redirect target:
 *   1. Must be a non-empty string.
 *   2. After exhaustive URL-decoding, must start with `/`.
 *   3. After decoding, must NOT start with `//` (scheme-relative).
 *   4. After decoding, must NOT start with `/\` or `/%5C` (backslash
 *      scheme-relative — Chromium, Edge, Safari all coerce `\` to `/`).
 *   5. Must NOT contain the substring `://` anywhere
 *      (defense-in-depth — catches `/https://evil.com` obfuscation).
 *   6. Must NOT begin with a dangerous scheme (`javascript:`, `data:`,
 *      `vbscript:`, `file:`) — applied to the fully-decoded value.
 *   7. Must NOT loop to `/login` or `/signup`.
 *
 * Anything failing these checks returns the safe fallback:
 *   `/app/dashboard` (founder-mandated post-login landing).
 *
 * Pinned by:
 *   backend/tests/test_safe_redirect_open_redirect_guard_2026_06.py
 */

const SAFE_FALLBACK = '/app/dashboard';

/** Exhaustively url-decode (cap at 5 iterations to prevent pathological loops). */
function exhaustiveDecode(s) {
  let cur = s;
  for (let i = 0; i < 5; i++) {
    let next;
    try {
      next = decodeURIComponent(cur);
    } catch {
      // Malformed encoding — treat the raw value as untrusted.
      return cur;
    }
    if (next === cur) return cur;
    cur = next;
  }
  return cur;
}

/**
 * Return a safe same-origin path or the canonical fallback.
 *
 * @param {string|null|undefined} input - candidate path (decoded or not)
 * @param {string} [fallback='/app/dashboard']
 * @returns {string}
 */
export function safeRedirectPath(input, fallback = SAFE_FALLBACK) {
  if (!input || typeof input !== 'string') return fallback;

  // Trim leading/trailing whitespace AND control characters (some browsers
  // ignore leading whitespace when navigating: `\t//evil.com` could escape).
  // eslint-disable-next-line no-control-regex
  const val = input.replace(/^[\s\u0000-\u001f]+|[\s\u0000-\u001f]+$/g, '');
  if (!val) return fallback;

  // Decode to the canonical form an attacker would actually navigate to.
  const decoded = exhaustiveDecode(val).toLowerCase();
  // Keep an original-case decoded copy for the return value so legitimate
  // paths preserve their casing (e.g., `/app/My-Space`).
  const decodedRaw = exhaustiveDecode(val);

  // Must be a relative same-site path.
  if (!decoded.startsWith('/')) return fallback;
  // Reject scheme-relative `//evil.com`.
  if (decoded.startsWith('//')) return fallback;
  // Reject backslash variants — browsers coerce these to scheme-relative.
  if (decoded.startsWith('/\\') || decoded.startsWith('\\\\')) return fallback;

  // Reject any embedded protocol (defense in depth — catches things like
  // `/https://evil.com` or weird `/foo/bar://evil`).
  if (decoded.includes('://')) return fallback;

  // Reject dangerous schemes right after the leading slash.
  if (/^\/(javascript|data|vbscript|file|about|blob):/i.test(decoded)) {
    return fallback;
  }

  // Prevent self-loops back to auth pages.
  if (
    decoded === '/login' ||
    decoded.startsWith('/login?') ||
    decoded.startsWith('/login#') ||
    decoded.startsWith('/login/') ||
    decoded === '/signup' ||
    decoded.startsWith('/signup?') ||
    decoded.startsWith('/signup#') ||
    decoded.startsWith('/signup/')
  ) {
    return fallback;
  }

  return decodedRaw;
}

/** Exported for tests only. */
export const __SAFE_FALLBACK = SAFE_FALLBACK;
