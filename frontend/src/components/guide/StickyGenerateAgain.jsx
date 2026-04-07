import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, RefreshCw } from 'lucide-react';
import { trackFunnel } from '../../utils/funnelTracker';

/**
 * Sticky "Generate Again" CTA — fixed at bottom of result screen.
 * Only shows when user is on the result step.
 *
 * Props:
 *  - visible: boolean
 *  - onGenerateAgain: () => void
 */
export default function StickyGenerateAgain({ visible, onGenerateAgain }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (visible) {
      const t = setTimeout(() => setShow(true), 2000);
      return () => clearTimeout(t);
    }
    setShow(false);
  }, [visible]);

  if (!show) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-[10000] pointer-events-none"
      data-testid="sticky-generate-again"
    >
      <div className="max-w-3xl mx-auto px-4 pb-4 pointer-events-auto">
        <div className="bg-slate-900/95 backdrop-blur-lg border border-slate-700/60 rounded-2xl p-3 flex items-center justify-between shadow-2xl shadow-black/40">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <span className="text-sm text-white font-medium">That was good. Try one more?</span>
          </div>
          <button
            onClick={() => {
              trackFunnel('second_action', { source_page: 'studio', meta: { action: 'generate_again_sticky' } });
              onGenerateAgain?.();
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-bold rounded-xl transition-all hover:scale-[1.02] shadow-lg shadow-indigo-500/20"
            data-testid="generate-again-btn"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Generate Again
          </button>
        </div>
      </div>
    </div>
  );
}
