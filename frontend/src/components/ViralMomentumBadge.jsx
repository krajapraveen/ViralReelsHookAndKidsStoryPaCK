import React, { useState, useEffect } from 'react';
import { Flame, Rocket, Star, TrendingUp, Zap, Award, GitBranch, Share2 } from 'lucide-react';
import { toast } from 'sonner';

const LEVEL_CONFIG = {
  viral_surge: { Icon: Star, color: 'text-amber-300 bg-amber-500/15 border-amber-500/30', glow: 'shadow-amber-500/20', pulse: true },
  spreading_widely: { Icon: Rocket, color: 'text-rose-300 bg-rose-500/15 border-rose-500/30', glow: 'shadow-rose-500/20', pulse: true },
  trending: { Icon: TrendingUp, color: 'text-violet-300 bg-violet-500/15 border-violet-500/30', glow: 'shadow-violet-500/20', pulse: true },
  rising_fast: { Icon: Flame, color: 'text-orange-300 bg-orange-500/15 border-orange-500/30', glow: '', pulse: false },
  warming_up: { Icon: Zap, color: 'text-cyan-300 bg-cyan-500/15 border-cyan-500/30', glow: '', pulse: false },
  new: { Icon: TrendingUp, color: 'text-slate-400 bg-slate-500/10 border-slate-500/20', glow: '', pulse: false },
};

const BADGE_TIER_COLOR = {
  bronze: 'text-amber-600 bg-amber-900/20 border-amber-700/30',
  silver: 'text-slate-300 bg-slate-500/15 border-slate-400/30',
  gold: 'text-yellow-300 bg-yellow-500/15 border-yellow-500/30',
};

export default function ViralMomentumBadge({ jobId, variant = 'inline', showBadges = false, className = '' }) {
  const [data, setData] = useState(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    const API = process.env.REACT_APP_BACKEND_URL;
    fetch(`${API}/api/viral/story-momentum/${jobId}`)
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          setData(d);
          // Badge reveal toast for new milestone
          if (d.badges?.length > 0 && !revealed) {
            setRevealed(true);
          }
        }
      })
      .catch(() => {});
  }, [jobId, revealed]);

  if (!data || data.momentum_level === 'new') return null;

  const config = LEVEL_CONFIG[data.momentum_level] || LEVEL_CONFIG.new;
  const { Icon } = config;

  if (variant === 'compact') {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${config.color} ${config.pulse ? 'animate-pulse' : ''} ${className}`}
        data-testid="momentum-badge-compact"
      >
        <Icon className="w-3 h-3" /> {data.momentum_label}
      </span>
    );
  }

  if (variant === 'card') {
    return (
      <div className={`rounded-xl border p-4 ${config.color} ${config.glow ? `shadow-lg ${config.glow}` : ''} ${className}`} data-testid="momentum-card">
        <div className="flex items-center gap-2 mb-2">
          <Icon className={`w-5 h-5 ${config.pulse ? 'animate-pulse' : ''}`} />
          <span className="text-sm font-bold">{data.momentum_label}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[11px]">
          <div className="flex items-center gap-1"><GitBranch className="w-3 h-3 opacity-60" /> {data.total_remixes} remix{data.total_remixes !== 1 ? 'es' : ''}</div>
          <div className="flex items-center gap-1"><Share2 className="w-3 h-3 opacity-60" /> {data.total_shares} share{data.total_shares !== 1 ? 's' : ''}</div>
          {data.chain_depth > 0 && <div className="flex items-center gap-1"><Zap className="w-3 h-3 opacity-60" /> depth {data.chain_depth}</div>}
        </div>
        {showBadges && data.badges?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3" data-testid="milestone-badges">
            {data.badges.map(b => (
              <span key={b.id} className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${BADGE_TIER_COLOR[b.tier] || ''}`}>
                <Award className="w-3 h-3" /> {b.label}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Default: inline
  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`} data-testid="momentum-badge-inline">
      <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full border ${config.color} ${config.pulse ? 'animate-pulse' : ''}`}>
        <Icon className="w-3.5 h-3.5" /> {data.momentum_label}
      </span>
      {data.chain_depth > 0 && (
        <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
          <GitBranch className="w-3 h-3" /> chain depth {data.chain_depth}
        </span>
      )}
    </div>
  );
}
