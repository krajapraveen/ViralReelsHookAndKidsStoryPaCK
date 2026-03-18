import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Sparkles, X, Flame } from 'lucide-react';

export function UpgradeModal({ open, onClose, reason, context }) {
  const navigate = useNavigate();
  if (!open) return null;

  const messages = {
    series_limit: {
      title: 'Your stories are growing',
      subtitle: 'Upgrade to create more series',
      detail: context?.message || "You've reached your series limit.",
      cta: 'Unlock More Series',
    },
    episode_limit: {
      title: 'Your story is getting interesting...',
      subtitle: `You've reached Episode ${context?.limit || 3}`,
      detail: 'Upgrade to continue your story and see what happens next.',
      cta: 'Continue the Story',
    },
    credit_limit: {
      title: 'Your creative energy is running low',
      subtitle: `${context?.credits || 0} credits remaining`,
      detail: 'Top up or upgrade to keep creating.',
      cta: 'Get More Credits',
    },
    daily_limit: {
      title: "You've hit today's limit",
      subtitle: '3 free generations per day',
      detail: 'Upgrade for unlimited daily creations.',
      cta: 'Upgrade Now',
    },
  };

  const msg = messages[reason] || messages.credit_limit;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="upgrade-modal">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-sm w-full mx-4 relative">
        <button onClick={onClose} className="absolute top-3 right-3 text-slate-500 hover:text-white" data-testid="close-upgrade-modal">
          <X className="w-5 h-5" />
        </button>

        <div className="text-center">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-indigo-500/20 flex items-center justify-center">
            <Flame className="w-7 h-7 text-amber-400" />
          </div>
          <h2 className="text-lg font-bold text-white mb-1">{msg.title}</h2>
          <p className="text-sm text-indigo-400 font-medium mb-2">{msg.subtitle}</p>
          <p className="text-xs text-slate-500 mb-6">{msg.detail}</p>

          <Button
            onClick={() => { onClose(); navigate('/app/pricing'); }}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold h-11 gap-2"
            data-testid="upgrade-cta-btn"
          >
            <Sparkles className="w-4 h-4" /> {msg.cta}
          </Button>
          <p className="text-[10px] text-slate-600 mt-3">Starting at INR 499/month</p>
        </div>
      </div>
    </div>
  );
}

export default UpgradeModal;
