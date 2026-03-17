import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, X, ChevronRight, Play, TrendingUp, BookOpen } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

/**
 * Action Banner — persistent, action-first re-entry CTA.
 * Deep-links into continuation. Resurfaces if dismissed (after 4h).
 */
export function ActionBanner() {
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissedAt = localStorage.getItem('action_banner_dismissed_at');
    if (dismissedAt) {
      const elapsed = Date.now() - parseInt(dismissedAt, 10);
      if (elapsed < 4 * 60 * 60 * 1000) return; // 4 hours
    }

    (async () => {
      try {
        const res = await api.get('/api/photo-to-comic/active-chains');
        const chains = res.data.chains || [];
        const best = chains.find(c => c.continue_job_id) || chains[0];
        if (best) {
          setChain(best);
          setVisible(true);
          api.post('/api/metrics/track', { event: 'banner_shown', chain_id: best.chain_id }).catch(() => {});
        }
      } catch { /* noop */ }
    })();
  }, []);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem('action_banner_dismissed_at', Date.now().toString());
  };

  const handleContinue = useCallback(() => {
    if (!chain) return;
    api.post('/api/metrics/track', { event: 'continue_from_banner', chain_id: chain.chain_id }).catch(() => {});
    if (chain.continue_job_id) {
      navigate(`/app/photo-to-comic?continue=${chain.continue_job_id}`);
    } else {
      navigate(`/app/story-chain/${chain.chain_id}`);
    }
  }, [chain, navigate]);

  if (!visible || !chain) return null;

  return (
    <div className="mb-4 rounded-xl border border-indigo-500/25 bg-gradient-to-r from-indigo-500/8 via-slate-900/80 to-cyan-500/8 overflow-hidden" data-testid="action-banner">
      <div className="flex items-center gap-4 px-4 py-3">
        {/* Preview thumbnail */}
        <div className="w-12 h-12 rounded-lg overflow-hidden border border-indigo-500/20 shrink-0 bg-slate-800">
          {chain.preview_url ? (
            <img src={chain.preview_url} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
          ) : (
            <div className="w-full h-full flex items-center justify-center"><BookOpen className="w-5 h-5 text-slate-600" /></div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Your story is waiting</span>
            {chain.momentum_msg && (
              <>
                <span className="text-slate-700">&middot;</span>
                <span className="text-xs text-amber-400/80 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> {chain.momentum_msg}
                </span>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 max-w-[200px] h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{ width: `${chain.progress_pct}%` }} />
            </div>
            <span className="text-xs text-slate-400">{chain.total_episodes} ep &middot; {chain.progress_pct}%</span>
          </div>
        </div>

        {/* CTA */}
        <Button
          size="sm" onClick={handleContinue}
          className="bg-indigo-600 hover:bg-indigo-700 h-9 px-4 text-xs font-semibold shrink-0"
          data-testid="action-banner-continue"
        >
          {chain.continue_job_id ? <><Play className="w-3.5 h-3.5 mr-1.5" /> Continue</> : <><ChevronRight className="w-3.5 h-3.5 mr-1.5" /> View</>}
        </Button>

        {/* Dismiss */}
        <button onClick={dismiss} className="p-1 rounded-md text-slate-500 hover:text-white hover:bg-slate-800 transition-colors shrink-0" data-testid="action-banner-dismiss">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
