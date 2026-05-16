import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

/**
 * BackButton — universal navigation primitive (P1 · 2026-05-16)
 *
 * Behavior:
 *  • Click → navigate(-1) if browser history exists; else `fallbackPath`.
 *  • For `/app/admin/*` pages the implicit fallback is `/app/admin`.
 *  • For all other `/app/*` pages the implicit fallback is `/app`.
 *  • For everything else the implicit fallback is `/`.
 *
 * Variants:
 *  • <BackButton />                       → controlled, in-flow (use inside page headers)
 *  • <BackButton floating />              → fixed top-left, used by GlobalBackButton
 *
 * Optional props: fallbackPath, label, className, floating, dataTestId.
 *
 * Pages that already render their own back affordance MUST add the attribute
 * `data-page-has-back="true"` on any ancestor element. GlobalBackButton will
 * detect it via DOM and suppress its own render to avoid duplication.
 */
export default function BackButton({
  fallbackPath,
  label = 'Back',
  className = '',
  floating = false,
  dataTestId = 'back-button',
}) {
  const navigate = useNavigate();
  const location = useLocation();

  const resolvedFallback = (() => {
    if (fallbackPath) return fallbackPath;
    if (location.pathname.startsWith('/app/admin')) return '/app/admin';
    if (location.pathname.startsWith('/app')) return '/app';
    return '/';
  })();

  const onClick = useCallback(() => {
    // Browser history "length" > 1 means at least one prior entry exists,
    // but it can lie (cross-origin redirects). Use a stamped sentinel on
    // window for the most reliable signal: did THIS tab navigate at all?
    const hasInternalHistory = window.history.length > 1 && document.referrer;
    if (hasInternalHistory) {
      try {
        navigate(-1);
        return;
      } catch (_) { /* fall through */ }
    }
    navigate(resolvedFallback, { replace: true });
  }, [navigate, resolvedFallback]);

  const base =
    'inline-flex items-center gap-1.5 rounded-full border text-sm font-medium ' +
    'transition-all active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400';
  const inFlow =
    'px-3 py-1.5 border-white/10 bg-white/[0.04] text-zinc-300 hover:bg-white/10 hover:text-white';
  // Mobile-safe: respects iOS safe-area inset; z-30 stays below toasts (50) but above page content
  const floatStyles = floating
    ? 'fixed left-3 top-3 sm:left-4 sm:top-4 z-30 px-3 py-1.5 ' +
      'border-white/12 bg-zinc-900/85 backdrop-blur-md text-zinc-200 ' +
      'shadow-[0_4px_18px_rgba(0,0,0,0.45)] hover:bg-zinc-800/90 hover:text-white ' +
      'safe-area-top'
    : '';
  const cls = floating
    ? `${base} ${floatStyles} ${className}`
    : `${base} ${inFlow} ${className}`;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cls}
      data-testid={dataTestId}
      aria-label={label}
    >
      <ArrowLeft className="w-4 h-4" aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}

/* ─── GlobalBackButton — mount once at the app root ──────────────────
 * Renders a floating BackButton on every page except the exempt list,
 * and suppresses itself when a page already provides its own.
 */
export const GLOBAL_BACK_EXEMPT_PREFIXES = [
  '/login',
  '/signup',
  '/auth/callback',
  '/verify-email',
  '/reset-password',
  '/forgot-password',
  '/experience',          // anonymous pre-wow flow — no chrome
];

export const GLOBAL_BACK_EXEMPT_EXACT = new Set([
  '/',
  '/app',                 // top-level dashboard
  '/app/admin',           // top-level admin
]);

export function isBackButtonExempt(pathname) {
  if (GLOBAL_BACK_EXEMPT_EXACT.has(pathname)) return true;
  return GLOBAL_BACK_EXEMPT_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

export function GlobalBackButton() {
  const location = useLocation();
  const [suppressed, setSuppressed] = useState(false);

  useEffect(() => {
    // Allow page to fully mount, then check for an existing back affordance.
    const t = setTimeout(() => {
      try {
        const hasLocal =
          document.querySelector('[data-page-has-back="true"]') ||
          document.querySelector('[data-testid="page-back-btn"]') ||
          // Common existing patterns: any clickable that says "Back" near top
          Array.from(document.querySelectorAll('button[aria-label="Back"], a[aria-label="Back"]'))
            .filter((el) => el.getAttribute('data-testid') !== 'global-back-btn')
            .some((el) => {
              const r = el.getBoundingClientRect();
              return r.top < 96 && r.left < 200;  // top-left region
            });
        setSuppressed(Boolean(hasLocal));
      } catch (_) {
        setSuppressed(false);
      }
    }, 120);
    return () => clearTimeout(t);
  }, [location.pathname]);

  if (isBackButtonExempt(location.pathname)) return null;
  if (suppressed) return null;
  return <BackButton floating dataTestId="global-back-btn" />;
}
