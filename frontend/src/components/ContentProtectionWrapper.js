import React from 'react';
import { useLocation } from 'react-router-dom';
import { useContentProtection } from '../hooks/useContentProtection';

/**
 * Routes where anti-copy friction is NOT applied.
 * These are public info pages, auth flows, admin pages, and legal pages.
 */
const UNPROTECTED_PREFIXES = [
  '/login',
  '/signup',
  '/auth/',
  '/verify-email',
  '/reset-password',
  '/forgot-password',
  '/privacy-policy',
  '/cookie-policy',
  '/terms',
  '/user-manual',
  '/help',
  '/app/admin',
];

const UNPROTECTED_EXACT = [
  '/',
  '/pricing',
  '/contact',
  '/reviews',
  '/blog',
];

function isProtectedRoute(pathname) {
  // Exact unprotected matches
  if (UNPROTECTED_EXACT.includes(pathname)) return false;
  // Blog sub-paths (e.g. /blog/some-slug)
  if (pathname.startsWith('/blog/')) return false;
  // Prefix unprotected matches
  for (const prefix of UNPROTECTED_PREFIXES) {
    if (pathname.startsWith(prefix)) return false;
  }
  // Everything else is protected
  return true;
}

/**
 * ContentProtectionWrapper — applies site-wide anti-copy friction
 * on all protected routes. Wraps children with CSS protection styles.
 *
 * Place this inside the Router but wrapping all Route content.
 */
export function ContentProtectionWrapper({ children }) {
  const location = useLocation();
  const shouldProtect = isProtectedRoute(location.pathname);

  useContentProtection(shouldProtect);

  if (!shouldProtect) {
    return <>{children}</>;
  }

  return (
    <div
      data-testid="content-protection-layer"
      style={{
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none',
        WebkitTouchCallout: 'none',
      }}
    >
      {children}
    </div>
  );
}
