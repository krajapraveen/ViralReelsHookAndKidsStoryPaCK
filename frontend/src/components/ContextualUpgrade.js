import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Crown, Zap, Check, X } from 'lucide-react';
import { Button } from './ui/button';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const BENEFITS = [
  '250 monthly credits',
  'HD video export',
  'No watermark',
  'Faster generation',
  'Priority rendering',
];

export default function ContextualUpgrade({ trigger = 'low_credits', sourcePage = 'unknown', onDismiss }) {
  const [dismissed, setDismissed] = useState(false);
  const navigate = useNavigate();

  if (dismissed) return null;

  const handleUpgrade = () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        axios.post(`${API}/api/engagement-analytics/track-cta`, {
          cta_type: 'upgrade_prompt',
          source_page: sourcePage,
        }, { headers: { Authorization: `Bearer ${token}` } });
      } catch {}
    }
    navigate('/pricing');
  };

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  const TRIGGERS = {
    low_credits: {
      title: 'Running low on credits',
      subtitle: 'Upgrade to keep creating without interruption.',
    },
    after_generation: {
      title: "Loved what you created?",
      subtitle: 'Get faster rendering and HD exports with Pro.',
    },
    remix_limit: {
      title: "You're creating a lot today",
      subtitle: 'Unlock unlimited variations with Pro.',
    },
    watermark: {
      title: 'Remove watermark',
      subtitle: 'Export clean videos with Creator Pro.',
    },
  };

  const config = TRIGGERS[trigger] || TRIGGERS.low_credits;

  return (
    <div className="relative rounded-xl border border-indigo-500/15 bg-gradient-to-r from-indigo-500/[0.04] to-purple-500/[0.03] p-4 mt-4" data-testid="contextual-upgrade">
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 p-1 rounded-md text-white/20 hover:text-white/50 transition-colors"
        data-testid="upgrade-dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 shrink-0">
          <Crown className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-white">{config.title}</h4>
          <p className="text-xs text-slate-400 mt-0.5">{config.subtitle}</p>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
            {BENEFITS.slice(0, 3).map((b, i) => (
              <span key={i} className="text-[11px] text-indigo-300/70 flex items-center gap-1">
                <Check className="w-3 h-3" /> {b}
              </span>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-3">
            <Button onClick={handleUpgrade} size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg px-4 h-8 text-xs" data-testid="upgrade-cta-btn">
              <Zap className="w-3 h-3 mr-1" /> Upgrade to Pro
            </Button>
            <button onClick={handleDismiss} className="text-[11px] text-slate-500 hover:text-slate-400 transition-colors" data-testid="upgrade-continue-free">
              Continue free
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
