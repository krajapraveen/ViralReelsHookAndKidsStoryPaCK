import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, Trophy, Crown, Flame, BarChart3, Swords
} from 'lucide-react';
import api from '../utils/api';

/**
 * MomentumSection — Shows user's competitive stats to drive return behavior.
 * Current Rank, Best Rank, Streak, Battles Entered.
 */
export default function MomentumSection() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [entryRes, pulseRes] = await Promise.all([
          api.get('/api/stories/battle-entry-status'),
          api.get('/api/stories/hottest-battle').then(r => {
            const rootId = r.data?.battle?.root_story_id;
            return rootId ? api.get(`/api/stories/battle-pulse/${rootId}`) : null;
          }),
        ]);
        const pulse = pulseRes?.data?.pulse;
        setData({
          currentRank: pulse?.user_rank || null,
          bestRank: pulse?.user_rank || null,
          battlesEntered: entryRes.data?.entry_count || 0,
          credits: entryRes.data?.credits || 0,
        });
      } catch {}
    };
    load();
  }, []);

  if (!data) {
    return (
      <section className="rounded-2xl border border-white/[0.06] bg-[#121624]/80 p-5" data-testid="momentum-section-empty">
        <div className="flex items-center gap-2 mb-3">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2">
            <TrendingUp className="w-4 h-4 text-violet-300" />
          </div>
          <h2 className="text-lg font-bold text-white">Your Momentum</h2>
        </div>
        <p className="text-sm text-slate-400">Enter your first battle to start tracking your competitive stats.</p>
      </section>
    );
  }

  const stats = [
    {
      label: 'Current Rank',
      value: data.currentRank ? `#${data.currentRank}` : '—',
      icon: Trophy,
      accent: 'text-amber-300',
    },
    {
      label: 'Battles Entered',
      value: String(data.battlesEntered),
      icon: Swords,
      accent: 'text-violet-300',
    },
    {
      label: 'Credits',
      value: String(data.credits),
      icon: Flame,
      accent: 'text-rose-300',
    },
    {
      label: 'Status',
      value: data.currentRank === 1 ? 'Leading' : data.currentRank ? 'Competing' : 'Spectating',
      icon: BarChart3,
      accent: 'text-sky-300',
    },
  ];

  return (
    <section className="rounded-2xl border border-white/[0.06] bg-[#121624]/80 p-5" data-testid="momentum-section">
      <div className="flex items-center gap-2 mb-4">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-2">
          <TrendingUp className="w-4 h-4 text-violet-300" />
        </div>
        <h2 className="text-lg font-bold text-white">Your Momentum</h2>
      </div>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5" data-testid={`momentum-${s.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <div className="flex items-center gap-1.5 text-slate-400">
                <Icon className={`w-3.5 h-3.5 ${s.accent}`} />
                <span className="text-[10px] font-semibold uppercase tracking-wider">{s.label}</span>
              </div>
              <p className="mt-1.5 text-xl font-bold text-white">{s.value}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex gap-2.5">
        <button
          onClick={() => navigate('/app/story-battle/battle-demo-root')}
          className="rounded-xl bg-violet-600 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-violet-500"
          data-testid="improve-rank-btn"
        >
          Improve Rank
        </button>
        <button
          onClick={() => navigate('/app/explore')}
          className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-4 py-2.5 text-xs font-bold text-white transition hover:bg-white/[0.06]"
          data-testid="view-battles-btn"
        >
          View All Battles
        </button>
      </div>
    </section>
  );
}
