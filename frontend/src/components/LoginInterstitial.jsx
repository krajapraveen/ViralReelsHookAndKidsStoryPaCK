import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Sparkles, X, ChevronRight, Play, GitBranch } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

/**
 * Login Interstitial — shown once per session on dashboard mount
 * if user has active chains with episodes to continue.
 */
export function LoginInterstitial() {
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = sessionStorage.getItem('interstitial_dismissed');
    if (dismissed) return;

    (async () => {
      try {
        const res = await api.get('/api/photo-to-comic/active-chains');
        const chains = res.data.chains || [];
        const best = chains.find(c => c.continue_job_id) || chains[0];
        if (best) {
          setChain(best);
          setVisible(true);
          api.post('/api/metrics/track', { event: 'login_interstitial_shown', chain_id: best.chain_id }).catch(() => {});
        }
      } catch { /* noop */ }
    })();
  }, []);

  const dismiss = () => { setVisible(false); sessionStorage.setItem('interstitial_dismissed', '1'); };

  const handleContinue = () => {
    api.post('/api/metrics/track', { event: 'login_interstitial_continue', chain_id: chain.chain_id }).catch(() => {});
    dismiss();
    if (chain.continue_job_id) {
      navigate(`/app/photo-to-comic?continue=${chain.continue_job_id}`);
    } else {
      navigate(`/app/story-chain/${chain.chain_id}`);
    }
  };

  if (!visible || !chain) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="login-interstitial">
      <div className="w-full max-w-md mx-4 rounded-2xl border border-indigo-500/30 bg-slate-900 overflow-hidden shadow-2xl shadow-indigo-500/10 animate-in fade-in zoom-in-95 duration-300">
        {/* Preview */}
        <div className="relative h-40 bg-gradient-to-br from-indigo-600/20 to-cyan-600/20 flex items-center justify-center">
          {chain.preview_url ? (
            <img src={chain.preview_url} alt="" className="w-full h-full object-cover opacity-60" crossOrigin="anonymous" />
          ) : (
            <BookOpen className="w-12 h-12 text-indigo-400/40" />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent" />
          <button onClick={dismiss} className="absolute top-3 right-3 p-1.5 rounded-lg bg-black/40 hover:bg-black/60 text-slate-400 hover:text-white transition-colors" data-testid="interstitial-dismiss">
            <X className="w-4 h-4" />
          </button>
          <div className="absolute bottom-4 left-4 right-4">
            <p className="text-xs text-indigo-300 uppercase tracking-wider font-semibold mb-1">Your story is waiting</p>
            <h2 className="text-lg font-bold text-white">Pick up where you left off</h2>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-sm text-slate-300 font-medium">{chain.total_episodes} episode{chain.total_episodes !== 1 ? 's' : ''}</span>
            </div>
            <span className="text-slate-700">&middot;</span>
            <span className="text-sm text-slate-400">{chain.root_style}</span>
          </div>

          {/* Progress */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-700" style={{ width: `${chain.progress_pct}%` }} />
              </div>
              <span className="text-sm font-semibold text-white">{chain.progress_pct}%</span>
            </div>
            {chain.momentum_msg && (
              <p className="text-xs text-amber-400/80">{chain.momentum_msg}</p>
            )}
          </div>

          {/* CTAs */}
          <div className="flex gap-2 pt-1">
            <Button onClick={handleContinue} className="flex-1 bg-indigo-600 hover:bg-indigo-700 h-11" data-testid="interstitial-continue-btn">
              {chain.continue_job_id ? (
                <><Play className="w-4 h-4 mr-2" /> Next Episode</>
              ) : (
                <><Sparkles className="w-4 h-4 mr-2" /> View Chain</>
              )}
            </Button>
            <Button variant="ghost" onClick={dismiss} className="text-slate-400 hover:text-white h-11 px-4" data-testid="interstitial-skip-btn">
              Later
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
