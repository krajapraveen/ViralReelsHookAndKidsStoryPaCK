import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, Send, X } from 'lucide-react';
import { trackFunnel } from '../utils/funnelTracker';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * P1.6 Post-Payment Micro-Survey
 *   "What made you buy today?"
 *   ○ Preview  ○ Price  ○ Story  ○ Needed it now  ○ Other
 *
 * Fires once per payment. Triggered by the global mount when
 * localStorage.pending_purchase_survey === '1'. Submits to
 * POST /api/funnel/purchase-survey then clears the flag.
 *
 * Discipline: ONE question, ONE submit. No upsell. No second screen.
 */
const OPTIONS = [
  { id: 'preview',     label: 'The preview hooked me' },
  { id: 'price',       label: 'The price was right' },
  { id: 'story',       label: 'The story itself was good' },
  { id: 'needed_now',  label: 'I needed it tonight' },
  { id: 'other',       label: 'Other' },
];

function getSessionId() {
  let sid = sessionStorage.getItem('funnel_session_id');
  if (!sid) {
    sid = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem('funnel_session_id', sid);
  }
  return sid;
}

export default function PurchaseSurvey({ open, onClose, orderId, plan }) {
  const [answer, setAnswer] = useState(null);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const shownRef = useRef(false);

  useEffect(() => {
    if (open && !shownRef.current) {
      shownRef.current = true;
      try {
        trackFunnel('purchase_survey_shown', {
          meta: { order_id: orderId, plan },
        });
      } catch {}
    }
  }, [open, orderId, plan]);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!answer || submitting) return;
    setSubmitting(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      const token = localStorage.getItem('token');
      if (token) headers['Authorization'] = `Bearer ${token}`;
      await fetch(`${API}/api/funnel/purchase-survey`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          answer,
          note: answer === 'other' ? note.slice(0, 500) : '',
          session_id: getSessionId(),
          order_id: orderId,
          plan,
        }),
      });
    } catch (_) {
      // Silent — survey is best-effort, never block UX.
    }
    onClose?.({ submitted: true, answer });
  };

  const handleDismiss = () => {
    try {
      trackFunnel('purchase_survey_dismissed', { meta: { order_id: orderId, plan } });
    } catch {}
    onClose?.({ submitted: false });
  };

  return (
    <div className="fixed inset-0 z-[10000] flex items-end sm:items-center justify-center" data-testid="purchase-survey-overlay">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-md" onClick={handleDismiss} />

      <div
        className="relative w-full max-w-md mx-auto sm:mx-4 bg-[#0d0d18] border border-emerald-500/20 sm:rounded-2xl rounded-t-2xl overflow-hidden ps-slide-up"
        data-testid="purchase-survey-modal"
      >
        <button
          onClick={handleDismiss}
          className="absolute top-3 right-3 z-10 p-1.5 rounded-full bg-white/5 hover:bg-white/10 transition-colors"
          data-testid="ps-close-btn"
          aria-label="Close survey"
        >
          <X className="w-4 h-4 text-slate-400" />
        </button>

        <div className="px-6 pt-6 pb-4">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 text-[10px] font-bold uppercase tracking-widest mb-3">
            <Sparkles className="w-3 h-3" /> Thank you
          </div>
          <h2 className="text-xl font-bold text-white mb-1" data-testid="ps-headline">What made you buy today?</h2>
          <p className="text-slate-500 text-xs">One tap. Helps us ship more of what you love.</p>
        </div>

        <div className="px-6 pb-3 space-y-2">
          {OPTIONS.map((o) => (
            <button
              key={o.id}
              onClick={() => setAnswer(o.id)}
              className={`w-full text-left px-4 py-3 rounded-xl border transition-all flex items-center justify-between text-sm ${
                answer === o.id
                  ? 'border-emerald-500 bg-emerald-500/10 text-white'
                  : 'border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/5'
              }`}
              data-testid={`ps-option-${o.id}`}
            >
              <span>{o.label}</span>
              <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${answer === o.id ? 'border-emerald-500 bg-emerald-500' : 'border-slate-600'}`}>
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
              className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-emerald-500/50"
              data-testid="ps-other-note"
            />
          </div>
        )}

        <div className="px-6 pt-2 pb-5" style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}>
          <button
            onClick={handleSubmit}
            disabled={!answer || submitting}
            className="w-full py-3.5 px-5 rounded-xl font-semibold text-white text-base flex items-center justify-center gap-2 ps-cta disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] transition-transform"
            data-testid="ps-submit-btn"
          >
            <Send className="w-4 h-4" />
            {submitting ? 'Sending...' : 'Submit'}
          </button>
        </div>
      </div>

      <style>{`
        .ps-slide-up { animation: psSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes psSlideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .ps-cta {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          box-shadow: 0 6px 20px -6px rgba(16, 185, 129, 0.55);
        }
      `}</style>
    </div>
  );
}

/**
 * Trigger helper — call this immediately after a successful payment.
 * The global PurchaseSurveyMount picks up the flag on next render.
 */
export function triggerPurchaseSurvey({ orderId, plan }) {
  try {
    const payload = JSON.stringify({ order_id: orderId || null, plan: plan || null, ts: Date.now() });
    localStorage.setItem('pending_purchase_survey', payload);
    // Dispatch a custom event so the global mount opens immediately even
    // without a re-render trigger from the host page.
    window.dispatchEvent(new CustomEvent('purchase-survey-ready', { detail: { orderId, plan } }));
  } catch (_) { /* noop */ }
}

/**
 * Global mount — drop this once near the App root. Listens for the trigger
 * helper or the localStorage flag and shows the modal exactly once.
 */
export function PurchaseSurveyMount() {
  const [openState, setOpenState] = useState(null);

  useEffect(() => {
    const check = () => {
      try {
        const raw = localStorage.getItem('pending_purchase_survey');
        if (!raw) return;
        const parsed = JSON.parse(raw);
        setOpenState(parsed);
      } catch (_) {
        localStorage.removeItem('pending_purchase_survey');
      }
    };
    check();
    const handler = () => check();
    window.addEventListener('purchase-survey-ready', handler);
    window.addEventListener('storage', handler);
    return () => {
      window.removeEventListener('purchase-survey-ready', handler);
      window.removeEventListener('storage', handler);
    };
  }, []);

  if (!openState) return null;

  return (
    <PurchaseSurvey
      open={true}
      orderId={openState.order_id}
      plan={openState.plan}
      onClose={() => {
        localStorage.removeItem('pending_purchase_survey');
        setOpenState(null);
      }}
    />
  );
}
