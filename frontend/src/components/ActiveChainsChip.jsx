import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, ChevronRight, Play, BookOpen, X, Sparkles, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

/**
 * ActiveChainsChip — nav bar chip + slide-out resume drawer (top 3 chains).
 */
export function ActiveChainsChip() {
  const navigate = useNavigate();
  const [chains, setChains] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/photo-to-comic/active-chains');
        setChains(res.data.chains || []);
      } catch { /* noop */ }
    })();
  }, []);

  // Close drawer on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (!chains.length) return null;

  const incomplete = chains.filter(c => c.progress_pct < 100).length;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition-colors"
        data-testid="active-chains-chip"
      >
        <GitBranch className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Stories</span>
        {incomplete > 0 && (
          <span className="min-w-[16px] h-[16px] bg-amber-500 rounded-full flex items-center justify-center text-[10px] font-bold text-black" data-testid="chains-badge">
            {incomplete}
          </span>
        )}
      </button>

      {/* Resume drawer */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/40 z-50 overflow-hidden" data-testid="resume-drawer">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
            <h3 className="text-sm font-semibold text-white">Active Stories</h3>
            <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="divide-y divide-slate-800/50">
            {chains.map((c) => (
              <div key={c.chain_id} className="p-3 hover:bg-slate-800/50 transition-colors" data-testid={`drawer-chain-${c.chain_id}`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-slate-800 overflow-hidden shrink-0 border border-slate-700">
                    {c.preview_url ? (
                      <img src={c.preview_url} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center"><BookOpen className="w-4 h-4 text-slate-600" /></div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-xs text-white font-medium">{c.total_episodes} ep</span>
                      <span className="text-slate-700">&middot;</span>
                      <span className="text-[10px] text-slate-500">{c.root_style}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400" style={{ width: `${c.progress_pct}%` }} />
                      </div>
                      <span className="text-[10px] text-slate-500">{c.progress_pct}%</span>
                    </div>
                    {c.momentum_msg && (
                      <p className="text-[10px] text-amber-400/70 mt-0.5 flex items-center gap-0.5">
                        <TrendingUp className="w-2.5 h-2.5" /> {c.momentum_msg}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col gap-1 shrink-0">
                    {c.continue_job_id ? (
                      <Button
                        size="sm"
                        onClick={() => { setOpen(false); navigate(`/app/photo-to-comic?continue=${c.continue_job_id}`); }}
                        className="bg-indigo-600 hover:bg-indigo-700 h-7 px-2.5 text-[10px]"
                        data-testid={`drawer-continue-${c.chain_id}`}
                      >
                        <Play className="w-3 h-3 mr-1" /> Continue
                      </Button>
                    ) : (
                      <Button
                        size="sm" variant="outline"
                        onClick={() => { setOpen(false); navigate(`/app/story-chain/${c.chain_id}`); }}
                        className="border-slate-700 text-slate-300 h-7 px-2.5 text-[10px]"
                        data-testid={`drawer-view-${c.chain_id}`}
                      >
                        <ChevronRight className="w-3 h-3 mr-1" /> View
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="px-4 py-2.5 border-t border-slate-800 bg-slate-900/50">
            <button
              onClick={() => { setOpen(false); navigate('/app/my-stories'); }}
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
              data-testid="drawer-all-stories"
            >
              All Stories <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
