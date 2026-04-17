import React, { useState, useEffect } from 'react';
import { Sparkles, Zap, Star, ArrowRight, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useCredits } from '../contexts/CreditContext';

/**
 * Smart upgrade prompt — shows at moments of peak excitement.
 * Triggers: after first generation, after sharing, after 2nd use, low credits.
 * 
 * Usage: <SmartUpgradePrompt trigger="generation_complete" />
 */
export default function SmartUpgradePrompt({ trigger, onDismiss }) {
  const [visible, setVisible] = useState(false);
  const navigate = useNavigate();
  const { credits } = useCredits();

  useEffect(() => {
    // Don't show for paid users or if recently dismissed
    const lastDismissed = localStorage.getItem('upgrade_prompt_dismissed');
    if (lastDismissed && Date.now() - parseInt(lastDismissed) < 86400000) return; // 24h cooldown

    // Don't show if user has plenty of credits
    if (credits > 20) return;

    // Show after 1.5s delay (let the wow moment sink in)
    const timer = setTimeout(() => setVisible(true), 1500);
    return () => clearTimeout(timer);
  }, [trigger, credits]);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem('upgrade_prompt_dismissed', String(Date.now()));
    if (onDismiss) onDismiss();
  };

  const goUpgrade = () => {
    dismiss();
    navigate('/app/billing');
  };

  if (!visible) return null;

  // Context-sensitive messaging based on trigger
  const messages = {
    generation_complete: {
      title: 'Your video is ready!',
      subtitle: 'Want to create more? Upgrade for faster generation and premium styles.',
      cta: 'Unlock More Creations',
      icon: Star,
    },
    share_success: {
      title: 'Your story is spreading!',
      subtitle: 'Upgrade to remove watermarks and unlock commercial use.',
      cta: 'Go Premium',
      icon: Sparkles,
    },
    low_credits: {
      title: `Only ${credits} credit${credits !== 1 ? 's' : ''} left`,
      subtitle: 'Top up now and keep creating without interruption.',
      cta: 'Get More Credits',
      icon: Zap,
    },
    second_use: {
      title: 'You\'re on a roll!',
      subtitle: 'Upgrade for unlimited creativity — faster generations, more styles, no limits.',
      cta: 'Upgrade Now',
      icon: Sparkles,
    },
  };

  const msg = messages[trigger] || messages.low_credits;
  const IconComp = msg.icon;

  return (
    <div className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 sm:w-96 z-[80] animate-in slide-in-from-bottom-4 duration-300" data-testid="smart-upgrade-prompt">
      <div className="bg-slate-900/95 backdrop-blur-xl border border-violet-500/30 rounded-2xl shadow-2xl shadow-violet-500/10 p-5 relative">
        <button onClick={dismiss} className="absolute top-3 right-3 text-slate-500 hover:text-white transition-colors" data-testid="upgrade-prompt-close">
          <X className="w-4 h-4" />
        </button>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center flex-shrink-0">
            <IconComp className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-white mb-1">{msg.title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-3">{msg.subtitle}</p>
            <div className="flex items-center gap-2">
              <button
                onClick={goUpgrade}
                className="h-9 px-4 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-xs font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                data-testid="upgrade-prompt-cta"
              >
                {msg.cta} <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button onClick={dismiss} className="text-xs text-slate-500 hover:text-slate-300 transition-colors" data-testid="upgrade-prompt-later">
                Maybe later
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
