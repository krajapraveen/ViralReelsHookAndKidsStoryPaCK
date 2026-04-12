import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Swords, Crown, TrendingUp, ChevronUp, ChevronDown, Zap,
  ArrowRight, Flame, Eye, Loader2
} from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * HottestBattle — Entry Conversion Engine.
 *
 * Converts spectators → players via:
 * 1. Quick Shot (1-tap, zero-input entry)
 * 2. Personalized CTA ("You can beat #1 — only X continues ahead")
 * 3. Spectator Pressure Timer (urgency prompt after 6s)
 * 4. Entry Streak Hook (post-first-action confirmation)
 * Polls every 12s for live feel.
 */
export default function HottestBattle() {
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [prevContenders, setPrevContenders] = useState({});
  const [movements, setMovements] = useState({});
  const [viewTime, setViewTime] = useState(0);
  const [quickShotLoading, setQuickShotLoading] = useState(false);
  const [showPressure, setShowPressure] = useState(false);
  const [pressureDismissed, setPressureDismissed] = useState(false);
  const [streakJustStarted, setStreakJustStarted] = useState(false);
  const componentRef = useRef(null);
  const isVisible = useRef(false);
  const entryTracked = useRef(false);

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

  // Track view time ONLY when component is visible in viewport
  useEffect(() => {
    const el = componentRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      isVisible.current = entry.isIntersecting;
      // Track first impression
      if (entry.isIntersecting && !entryTracked.current) {
        entryTracked.current = true;
        try {
          api.post('/api/funnel/track', {
            event: 'spectator_impression',
            data: { root_id: battle?.root_story_id },
          });
        } catch {}
      }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [battle?.root_story_id]);

  useEffect(() => {
    const iv = setInterval(() => {
      if (isVisible.current) {
        setViewTime(t => t + 1);
      }
    }, 1000);
    return () => clearInterval(iv);
  }, []);

  // Pressure trigger: show after 6s of viewing
  useEffect(() => {
    if (viewTime >= 6 && !pressureDismissed && !showPressure) {
      setShowPressure(true);
      // Track pressure shown
      try {
        api.post('/api/funnel/track', {
          event: 'spectator_pressure_shown',
          data: {
            root_id: battle?.root_story_id,
            view_time: viewTime,
          },
        });
      } catch {}
    }
  }, [viewTime, pressureDismissed, showPressure, battle?.root_story_id]);

  // Quick Shot handler — 1-tap, zero input
  const handleQuickShot = async () => {
    if (quickShotLoading || !battle?.root_story_id) return;
    setQuickShotLoading(true);

    try {
      // Track conversion
      api.post('/api/funnel/track', {
        event: 'spectator_quick_shot',
        data: {
          root_id: battle.root_story_id,
          time_to_action: viewTime,
        },
      }).catch(() => {});

      const res = await api.post('/api/stories/quick-shot', {
        root_story_id: battle.root_story_id,
      });

      if (res.data?.success) {
        // Check for streak hook
        if (res.data.streak_started) {
          setStreakJustStarted(true);
          toast.success('Streak Started! Come back tomorrow to keep it alive.', {
            duration: 5000,
          });
        } else if (res.data.current_streak > 1) {
          toast.success(`${res.data.current_streak}-day streak! Version generating...`, {
            duration: 3000,
          });
        } else if (res.data.queued) {
          toast.success('You\'re in! Queued for rendering — we\'ll start as soon as a slot opens.', {
            duration: 4000,
          });
        } else {
          toast.success('Quick Shot fired! Your version is generating...', {
            duration: 3000,
          });
        }

        // Navigate to pipeline
        if (res.data.job_id) {
          navigate(`/app/story-video-pipeline?projectId=${res.data.job_id}`);
        }
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Quick Shot failed. Try again.';
      toast.error(detail);
    } finally {
      setQuickShotLoading(false);
    }
  };

  // Jump into battle (existing flow)
  const handleJumpIn = () => {
    // Track conversion
    try {
      api.post('/api/funnel/track', {
        event: 'spectator_to_player_conversion',
        data: {
          root_id: battle.root_story_id,
          time_to_action: viewTime,
          entry_type: 'jump_in',
        },
      });
    } catch {}
    navigate(`/app/story-battle/${battle.root_story_id}`);
  };

  if (!battle) return null;

  const {
    root_story_id, root_title, contenders, branch_count,
    near_win, gap_to_first, gap_continues_to_first,
    user_is_new, user_entry_count, user_already_in_battle,
  } = battle;

  // Build personalized CTA text
  let ctaText = 'Jump Into Battle';
  let ctaSubtext = null;

  if (user_already_in_battle) {
    ctaText = 'View Your Battle';
    ctaSubtext = null;
  } else if (gap_continues_to_first !== undefined && gap_continues_to_first <= 3 && contenders?.length >= 2) {
    ctaText = 'You can beat #1';
    ctaSubtext = gap_continues_to_first > 0
      ? `Only ${gap_continues_to_first} continue${gap_continues_to_first > 1 ? 's' : ''} ahead`
      : 'It\'s a dead heat';
  } else if (user_is_new) {
    ctaText = 'Try your first battle';
    ctaSubtext = 'New creators get a head start';
  } else if (near_win) {
    ctaText = 'Race is wide open';
    ctaSubtext = `Gap to #1: only ${gap_to_first} pts`;
  }

  return (
    <div ref={componentRef} className="px-4 sm:px-6 lg:px-10 py-2" data-testid="hottest-battle">
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

        {/* ═══ SPECTATOR PRESSURE TIMER ═══ */}
        {showPressure && !pressureDismissed && (
          <div
            className="mx-5 mb-3 bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 animate-in fade-in slide-in-from-bottom-2 duration-300"
            data-testid="spectator-pressure"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 min-w-0">
                <Flame className="w-4 h-4 text-rose-400 flex-shrink-0 animate-pulse" />
                <div>
                  <p className="text-xs font-bold text-rose-300">Battle is heating up</p>
                  <p className="text-[10px] text-white/40">Don't miss your chance</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setPressureDismissed(true);
                  handleQuickShot();
                }}
                className="flex-shrink-0 px-3 py-1.5 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold hover:bg-rose-500/30 transition-colors"
                data-testid="pressure-jump-in-btn"
              >
                Jump In Now
              </button>
            </div>
          </div>
        )}

        {/* ═══ CONVERSION CTAs ═══ */}
        <div className="px-5 pb-5 space-y-2" data-testid="spectator-cta">

          {/* Quick Shot — 1-tap, zero friction, converts lazy spectators */}
          <button
            onClick={handleQuickShot}
            disabled={quickShotLoading}
            className="w-full group relative overflow-hidden rounded-xl p-3 transition-all hover:scale-[1.01] active:scale-[0.99]"
            data-testid="quick-shot-btn"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-amber-600 to-rose-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center justify-center gap-2">
              {quickShotLoading ? (
                <>
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                  <span className="text-sm font-black text-white">Generating...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-white" />
                  <span className="text-sm font-black text-white">Quick Shot — 1 Tap Entry</span>
                </>
              )}
            </div>
            <p className="relative z-10 text-[10px] text-white/60 text-center mt-0.5">
              No prompt needed. Instant competitive version.
            </p>
          </button>

          {/* Personalized Jump Into Battle */}
          <button
            onClick={handleJumpIn}
            className="w-full group relative overflow-hidden rounded-xl p-3 transition-all hover:scale-[1.01] active:scale-[0.99]"
            data-testid="jump-into-battle-btn"
          >
            <div className="absolute inset-0 bg-white/[0.06] group-hover:bg-white/[0.1] transition-colors border border-white/10 rounded-xl" />
            <div className="relative z-10 flex items-center justify-center gap-2">
              <Swords className="w-4 h-4 text-white/70" />
              <span className="text-sm font-bold text-white/90">{ctaText}</span>
              <ArrowRight className="w-4 h-4 text-white/40 group-hover:text-white/70 transition-colors" />
            </div>
            {ctaSubtext && (
              <p className="relative z-10 text-[10px] text-white/40 text-center mt-0.5" data-testid="cta-subtext">
                {ctaSubtext}
              </p>
            )}
          </button>
        </div>

        {/* ═══ STREAK STARTED HOOK ═══ */}
        {streakJustStarted && (
          <div
            className="mx-5 mb-5 bg-orange-500/10 border border-orange-500/20 rounded-lg p-3 animate-in fade-in slide-in-from-bottom-2 duration-500"
            data-testid="streak-started-hook"
          >
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-orange-400" />
              <div>
                <p className="text-xs font-bold text-orange-400">Streak Started!</p>
                <p className="text-[10px] text-white/40">Come back tomorrow to keep it alive</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
