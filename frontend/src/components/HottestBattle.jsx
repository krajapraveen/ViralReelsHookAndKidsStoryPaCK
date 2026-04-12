import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Swords, Crown, TrendingUp, ChevronUp, ChevronDown, Zap,
  ArrowRight, Flame, Eye, GitBranch
} from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

/**
 * HottestBattle — Spectator mode on homepage.
 * Shows the most active battle with live-updating leaderboard.
 * Converts spectators into participants: "You can beat this → Jump Into Battle"
 * Polls every 12s for live feel.
 */
export default function HottestBattle() {
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [prevContenders, setPrevContenders] = useState({});
  const [movements, setMovements] = useState({});
  const [viewTime, setViewTime] = useState(0);

  const fetchBattle = useCallback(async () => {
    try {
      const res = await api.get('/api/stories/hottest-battle');
      if (res.data?.battle) {
        const newBattle = res.data.battle;

        // Detect rank movements
        if (battle?.contenders) {
          const oldRanks = {};
          for (const c of battle.contenders) oldRanks[c.job_id] = c.rank;
          const newMovements = {};
          for (const c of newBattle.contenders) {
            const old = oldRanks[c.job_id];
            if (old && old !== c.rank) {
              newMovements[c.job_id] = old > c.rank ? 'up' : 'down';
            }
          }
          if (Object.keys(newMovements).length > 0) {
            setMovements(newMovements);
            setTimeout(() => setMovements({}), 4000);
          }
        }

        setBattle(newBattle);
      }
    } catch {}
  }, [battle]);

  useEffect(() => { fetchBattle(); }, []);
  useEffect(() => {
    const iv = setInterval(fetchBattle, 12000);
    return () => clearInterval(iv);
  }, [fetchBattle]);

  // Track view time for conversion prompt
  useEffect(() => {
    const iv = setInterval(() => setViewTime(t => t + 1), 1000);
    return () => clearInterval(iv);
  }, []);

  if (!battle) return null;

  const { root_story_id, root_title, contenders, branch_count, near_win, gap_to_first } = battle;
  const showConversionPrompt = viewTime >= 5; // After 5 seconds of viewing

  return (
    <div className="px-4 sm:px-6 lg:px-10 py-2" data-testid="hottest-battle">
      <div className="rounded-2xl border border-rose-500/20 bg-gradient-to-br from-rose-500/[0.06] to-amber-500/[0.03] overflow-hidden">

        {/* Header */}
        <div className="px-5 pt-5 pb-3">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">Live Battle</span>
              {near_win && (
                <span className="text-[10px] bg-amber-500/20 text-amber-400 rounded-full px-2 py-0.5 font-bold animate-pulse">
                  CLOSE RACE
                </span>
              )}
            </div>
            <span className="text-[10px] text-white/30">{branch_count} competing</span>
          </div>
          <h3 className="text-base font-bold text-white truncate" data-testid="hottest-battle-title">
            {root_title || 'Story Battle'}
          </h3>
        </div>

        {/* Live Leaderboard — Top 3 */}
        <div className="px-5 pb-3 space-y-1.5" data-testid="spectator-leaderboard">
          {contenders.map((c, i) => {
            const moved = movements[c.job_id];
            return (
              <div
                key={c.job_id}
                className={`flex items-center gap-2.5 rounded-lg p-2 transition-all ${
                  moved === 'up' ? 'bg-emerald-500/10 border border-emerald-500/20' :
                  moved === 'down' ? 'bg-rose-500/10 border border-rose-500/20' :
                  i === 0 ? 'bg-amber-500/[0.06] border border-amber-500/10' :
                  'bg-white/[0.02] border border-transparent'
                }`}
                data-testid={`spectator-rank-${i + 1}`}
              >
                {/* Rank */}
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  i === 0 ? 'bg-amber-500/20' : 'bg-white/5'
                }`}>
                  {i === 0
                    ? <Crown className="w-3.5 h-3.5 text-amber-400" />
                    : <span className="text-[11px] font-black text-white/40">#{i + 1}</span>
                  }
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-white truncate">{c.title || 'Untitled'}</p>
                  <p className="text-[10px] text-white/30">{c.creator_name}</p>
                </div>

                {/* Movement indicator */}
                {moved && (
                  <div className={`flex items-center gap-0.5 text-xs font-bold ${
                    moved === 'up' ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {moved === 'up' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </div>
                )}

                {/* Score */}
                <span className={`text-xs font-bold flex-shrink-0 ${i === 0 ? 'text-amber-400' : 'text-white/40'}`}>
                  {(c.battle_score || 0).toFixed(0)} pts
                </span>
              </div>
            );
          })}
        </div>

        {/* Near-win highlight */}
        {near_win && contenders.length >= 2 && (
          <div className="mx-5 mb-3 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 text-center"
            data-testid="near-win-highlight">
            <p className="text-xs text-amber-300 font-semibold">
              <Zap className="w-3 h-3 inline mr-1" />
              #{2} is only <span className="font-black">{gap_to_first} pts</span> from #1
            </p>
          </div>
        )}

        {/* Conversion CTA — "You can beat this" */}
        <div className={`px-5 pb-5 transition-all ${showConversionPrompt ? 'opacity-100' : 'opacity-70'}`}
          data-testid="spectator-cta">
          <button
            onClick={() => {
              // Track conversion
              try { api.post('/api/funnel/track', { event: 'spectator_to_player_conversion', data: { root_id: root_story_id } }); } catch {}
              navigate(`/app/story-battle/${root_story_id}`);
            }}
            className="w-full group relative overflow-hidden rounded-xl p-3.5 transition-all hover:scale-[1.01] active:scale-[0.99]"
            data-testid="jump-into-battle-btn"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-rose-600 to-amber-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center justify-center gap-2">
              <Swords className="w-4 h-4 text-white" />
              <span className="text-sm font-black text-white">
                {showConversionPrompt ? 'You can beat this — Jump In' : 'Jump Into Battle'}
              </span>
              <ArrowRight className="w-4 h-4 text-white/50 group-hover:text-white transition-colors" />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
