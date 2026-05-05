/**
 * SubscribeRequiredModal — global blocked-by-policy modal.
 *
 * Triggered by the api.js interceptor on 402 INSUFFICIENT_CREDITS / 403
 * UPGRADE_REQUIRED responses (or any backend response carrying
 * code === "INSUFFICIENT_CREDITS"). Listens for window event
 * `subscribe-required-modal` so any code path can pop the dialog.
 *
 * Funnel events fired:
 *   free_user_blocked_post_policy_first   (per session, first hit)
 *   free_user_blocked_post_policy_repeat  (subsequent hits same session)
 *   pricing_page_opened_from_block        (when CTA is clicked)
 */
import React, { useEffect, useState } from 'react';
import { Lock, ArrowRight, X } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const FIRST_FLAG = 'sr_modal_first_blocked';

export default function SubscribeRequiredModal() {
  const [open, setOpen] = useState(false);
  const [feature, setFeature] = useState(null);

  useEffect(() => {
    const handler = (e) => {
      const detail = e?.detail || {};
      setFeature(detail.feature || null);
      setOpen(true);

      // Funnel: first vs repeat per session
      try {
        const seen = sessionStorage.getItem(FIRST_FLAG);
        if (!seen) {
          sessionStorage.setItem(FIRST_FLAG, '1');
          trackFunnel('free_user_blocked_post_policy_first', {
            meta: { feature: detail.feature || 'unknown', source: detail.source || 'api_interceptor' },
          });
        } else {
          trackFunnel('free_user_blocked_post_policy_repeat', {
            meta: { feature: detail.feature || 'unknown', source: detail.source || 'api_interceptor' },
          });
        }
      } catch (_) { /* never break UX */ }
    };
    window.addEventListener('subscribe-required-modal', handler);
    return () => window.removeEventListener('subscribe-required-modal', handler);
  }, []);

  if (!open) return null;

  const goToPricing = () => {
    try {
      trackFunnel('pricing_page_opened_from_block', {
        meta: { feature: feature || 'unknown' },
      });
    } catch (_) { /* noop */ }
    setOpen(false);
    // Use full navigation so the modal unmounts cleanly across route changes.
    window.location.href = '/app/pricing';
  };

  const goToCheckout = () => {
    try {
      trackFunnel('pricing_page_opened_from_block', {
        meta: { feature: feature || 'unknown', destination: 'billing' },
      });
    } catch (_) { /* noop */ }
    setOpen(false);
    window.location.href = '/app/billing';
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      data-testid="subscribe-required-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sr-modal-title"
    >
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 p-6 shadow-[0_30px_80px_-20px_rgba(99,102,241,0.45)]">
        <button
          onClick={() => setOpen(false)}
          className="absolute right-4 top-4 text-slate-400 hover:text-white transition-colors"
          aria-label="Close"
          data-testid="sr-modal-close"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500/20 to-rose-500/20 border border-violet-400/30 mb-4">
          <Lock className="w-7 h-7 text-violet-300" />
        </div>

        <h2 id="sr-modal-title" className="text-xl font-bold text-white mb-2" data-testid="sr-modal-title">
          Free credits have been removed
        </h2>
        <p className="text-sm text-slate-300 mb-1" data-testid="sr-modal-body">
          Subscribe to continue creating.
        </p>
        <p className="text-xs text-slate-500 mb-5">
          Every plan unlocks the full toolset immediately. Cancel anytime.
        </p>

        <button
          onClick={goToPricing}
          className="w-full h-12 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-semibold text-sm flex items-center justify-center gap-2 hover:opacity-95 transition-opacity"
          data-testid="sr-modal-subscribe-cta"
        >
          Subscribe to Start Creating <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={goToCheckout}
          className="mt-2 w-full h-10 rounded-xl border border-white/10 bg-white/[0.04] text-slate-200 font-medium text-xs hover:bg-white/[0.08] transition-colors"
          data-testid="sr-modal-checkout-cta"
        >
          Already a subscriber? Go to billing
        </button>

        <p className="mt-4 text-[11px] text-slate-500 text-center">
          No free credits. Subscription required for all generation features.
        </p>
      </div>
    </div>
  );
}
