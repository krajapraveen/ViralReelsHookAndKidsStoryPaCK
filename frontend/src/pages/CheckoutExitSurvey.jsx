import React, { useEffect, useRef, useState } from 'react';
import { X, Send } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * P1.7 Checkout Exit-Intent Survey
 * Shown when a user returns to /billing WITHOUT a successful payment
 * (no orderId, or verify came back unsuccessful). Founder spec — gold for
 * reducing payment-stage churn.
 *
 * Single question. One submit. No upsell.
 */
const OPTIONS = [
  { id: 'price',             label: 'Price was too high' },
  { id: 'payment_failed',    label: 'Payment failed / did not work' },
  { id: 'needed_more_trust', label: 'Needed more trust before paying' },
  { id: 'just_browsing',     label: 'Just browsing today' },
  { id: 'other',             label: 'Other' },
];

function getSessionId() {
  let sid = sessionStorage.getItem('funnel_session_id');
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('funnel_session_id', sid);
  }
  return sid;
}

export default function CheckoutExitSurvey({ open, onClose }) {
  const [answer, setAnswer] = useState(null);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const shownRef = useRef(false);

  useEffect(() => {
    if (open && !shownRef.current) {
      shownRef.current = true;
      try {
        trackFunnel('checkout_exit_survey_shown', { source_page: 'billing' });
      } catch {}
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!answer || submitting) return;
    setSubmitting(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      const token = localStorage.getItem('token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
      await fetch(`${API}/api/funnel/checkout-exit-survey`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          answer,
          note: answer === 'other' ? note.slice(0, 500) : '',
          session_id: getSessionId(),
        }),
      });
    } catch (_) { /* silent */ }
    onClose?.({ submitted: true, answer });
  };

  const handleDismiss = () => {
    try { trackFunnel('checkout_exit_survey_dismissed', { source_page: 'billing' }); } catch {}
    onClose?.({ submitted: false });
  };

  return (
    <div className="fixed inset-0 z-[10000] flex items-end sm:items-center justify-center" data-testid="checkout-exit-survey-overlay">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={handleDismiss} />
      <div
        className="relative w-full max-w-md mx-auto sm:mx-4 bg-[#0d0d18] border border-amber-500/20 sm:rounded-2xl rounded-t-2xl overflow-hidden ces-slide-up"
        data-testid="checkout-exit-survey-modal"
      >
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-white/5 hover:bg-white/10 transition-colors"
          data-testid="ces-close-btn"
          aria-label="Close survey"
        >
          <X className="w-4 h-4 text-slate-400" />
        </button>

        <div className="px-6 pt-6 pb-4">
          <h2 className="text-xl font-bold text-white mb-1" data-testid="ces-headline">
            Anything stop you today?
          </h2>
          <p className="text-slate-500 text-xs">One tap. We'll fix what's broken.</p>
        </div>

        <div className="px-6 pb-3 space-y-2">
          {OPTIONS.map((o) => (
            <button
              key={o.id}
              onClick={() => setAnswer(o.id)}
              className={`w-full text-left px-4 py-3 rounded-xl border transition-all flex items-center justify-between text-sm ${
                answer === o.id
                  ? 'border-amber-500 bg-amber-500/10 text-white'
                  : 'border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/5'
              }`}
              data-testid={`ces-option-${o.id}`}
            >
              <span>{o.label}</span>
              <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${answer === o.id ? 'border-amber-500 bg-amber-500' : 'border-slate-600'}`}>
                {answer === o.id && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
              </span>
            </button>
          ))}
        </div>

        {answer === 'other' && (
          <div className="px-6 pt-1 pb-2">
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Optional — tell us in one line"
              maxLength={300}
              rows={2}
              className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50"
              data-testid="ces-other-note"
            />
          </div>
        )}

        <div className="px-6 pt-2 pb-5" style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}>
          <button
            onClick={handleSubmit}
            disabled={!answer || submitting}
            className="w-full py-3.5 px-5 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2 ces-cta disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] transition-transform"
            data-testid="ces-submit-btn"
          >
            <Send className="w-4 h-4" />
            {submitting ? 'Sending...' : 'Submit'}
          </button>
        </div>
      </div>

      <style>{`
        .ces-slide-up { animation: cesSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes cesSlideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .ces-cta {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          box-shadow: 0 6px 20px -6px rgba(245, 158, 11, 0.55);
        }
      `}</style>
    </div>
  );
}
