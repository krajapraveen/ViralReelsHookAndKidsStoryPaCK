import { useState, useEffect, useCallback } from 'react';
import { Lock, Sparkles, ArrowRight, X } from 'lucide-react';

/**
 * Exit Interception Modal — shows when user tries to leave after generating.
 * Offers: Unlock Unlimited OR "Just one more free try"
 *
 * Props:
 *  - visible: boolean
 *  - onStay: () => void (sends back into loop)
 *  - onUpgrade: () => void (triggers paywall)
 *  - onLeave: () => void (actually navigate away)
 */
export default function ExitInterceptionModal({ visible, onStay, onUpgrade, onLeave }) {
  const [animateIn, setAnimateIn] = useState(false);

  useEffect(() => {
    if (visible) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimateIn(true));
      });
    } else {
      setAnimateIn(false);
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      className={`fixed inset-0 z-[10600] flex items-center justify-center transition-all duration-200 ${animateIn ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      data-testid="exit-interception-modal"
    >
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onLeave} />

      <div className={`relative z-10 max-w-sm w-full mx-6 transition-all duration-300 ${animateIn ? 'translate-y-0 scale-100' : 'translate-y-8 scale-95'}`}>
        <div className="bg-slate-900/95 border border-slate-700/60 rounded-3xl p-6 shadow-2xl text-center">
          <button onClick={onLeave} className="absolute top-3 right-3 text-slate-500 hover:text-white transition-colors" data-testid="exit-modal-close">
            <X className="w-4 h-4" />
          </button>

          <div className="w-12 h-12 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
            <Lock className="w-6 h-6 text-white" />
          </div>

          <h2 className="text-lg font-bold text-white mb-1">
            Wait... don't lose this!
          </h2>
          <p className="text-sm text-slate-400 mb-5">
            You've created amazing stories. They'll be limited after your free credits end.
          </p>

          <div className="space-y-2">
            <button
              onClick={onUpgrade}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white text-sm font-bold rounded-xl transition-all hover:scale-[1.01] shadow-lg shadow-indigo-500/20"
              data-testid="exit-modal-upgrade"
            >
              <Sparkles className="w-4 h-4" />
              Unlock Unlimited
            </button>
            <button
              onClick={onStay}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-all border border-slate-700"
              data-testid="exit-modal-one-more"
            >
              Just one more free try
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
