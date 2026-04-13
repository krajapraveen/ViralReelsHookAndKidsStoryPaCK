import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Flame, Swords, Eye, Trophy, Zap, Crown, TrendingUp,
  PlayCircle, ArrowRight, Loader2
} from 'lucide-react';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';
import BattlePaywallModal from './BattlePaywallModal';

/**
 * LiveBattleHero — THE top-of-dashboard battle zone.
 * Shows the hottest live battle, user rank, stats, and two primary CTAs.
 * Wired to real APIs: /api/stories/hottest-battle + /api/stories/battle-pulse
 */
export default function LiveBattleHero() {
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [pulse, setPulse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quickShotLoading, setQuickShotLoading] = useState(false);
  const [enterLoading, setEnterLoading] = useState(false);
  const [showPaywall, setShowPaywall] = useState(false);
  const [nextUpdate, setNextUpdate] = useState(15); // countdown to next rank refresh

  useEffect(() => {
    const load = async () => {
      try {
        const [battleRes, entryRes] = await Promise.all([
          api.get('/api/stories/hottest-battle'),
          api.get('/api/stories/battle-entry-status').catch(() => null),
        ]);
        const b = battleRes.data?.battle;
        if (b) {
          setBattle(b);
          // Also fetch pulse for this battle
          try {
            const pulseRes = await api.get(`/api/stories/battle-pulse/${b.root_story_id}`);
            setPulse(pulseRes.data?.pulse);
          } catch {}
        }
      } catch {}
      setLoading(false);
    };
    load();
  }, []);

  // Poll pulse every 12-18s (randomized to feel alive) + countdown timer
  useEffect(() => {
    if (!battle?.root_story_id) return;
    const pollInterval = 12000 + Math.random() * 6000; // 12-18s
    const iv = setInterval(async () => {
      try {
        const res = await api.get(`/api/stories/battle-pulse/${battle.root_story_id}`);
        if (res.data?.pulse) setPulse(res.data.pulse);
        setNextUpdate(Math.floor(12 + Math.random() * 6)); // 12-18s countdown
      } catch {}
    }, pollInterval);
    return () => clearInterval(iv);
  }, [battle?.root_story_id]);

  // Countdown ticker
  useEffect(() => {
    if (!battle) return;
    const tick = setInterval(() => {
      setNextUpdate(prev => prev > 0 ? prev - 1 : 15);
    }, 1000);
    return () => clearInterval(tick);
  }, [battle]);

  const handleEnterBattle = async () => {
    if (enterLoading) return;
    setEnterLoading(true);
    try {
      const res = await api.get('/api/stories/battle-entry-status');
      if (res.data?.needs_payment) {
        setShowPaywall(true);
        setEnterLoading(false);
        return;
      }
    } catch {}
    trackFunnel('cta_clicked', { meta: { type: 'enter_battle', source: 'hero' } });
    navigate(`/app/story-battle/${battle.root_story_id}`);
  };

  const handleQuickShot = async () => {
    if (quickShotLoading || !battle?.root_story_id) return;
    setQuickShotLoading(true);
    try {
      const res = await api.post('/api/stories/quick-shot', { root_story_id: battle.root_story_id });
      if (res.data?.success && res.data.job_id) {
        trackFunnel('spectator_quick_shot', { data: { root_id: battle.root_story_id } });
        navigate(`/app/story-video-studio?projectId=${res.data.job_id}`);
      }
    } catch (err) {
      if (err.response?.status === 402) {
        setShowPaywall(true);
      }
    } finally {
      setQuickShotLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-3xl border border-white/[0.06] bg-[#12111e] p-8 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (!battle) {
    return (
      <section className="rounded-3xl border border-white/[0.06] bg-gradient-to-br from-[#161427] via-[#1b1633] to-[#101420] p-6 md:p-8 text-center" data-testid="live-battle-hero-empty">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(139,92,246,0.1),transparent_40%)]" />
        <Flame className="w-8 h-8 text-rose-400 mx-auto mb-3" />
        <h2 className="text-xl font-black text-white">No active battle yet</h2>
        <p className="text-sm text-slate-400 mt-2 max-w-md mx-auto">Be the first to start a story and launch a battle. Create something others want to compete with.</p>
        <button
          onClick={() => navigate('/app/story-video-studio', { state: { freshSession: true } })}
          className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-violet-600 px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet-500"
          data-testid="create-first-battle-btn"
        >
          <Zap className="w-4 h-4" /> Create First Story
        </button>
      </section>
    );
  }

  const userRank = pulse?.user_rank;
  const totalEntries = pulse?.total_entries || battle.branch_count || 0;
  const topEntry = pulse?.top_3?.[0];
  const totalViews = pulse?.top_3?.reduce((s, e) => s + (e.views || 0), 0) || 0;
  const activeRendering = pulse?.active_rendering || 0;

  return (
    <>
      <section
        className="relative overflow-hidden rounded-3xl border border-white/[0.06] bg-gradient-to-br from-[#161427] via-[#1b1633] to-[#101420] p-5 shadow-2xl shadow-violet-950/20 md:p-8"
        data-testid="live-battle-hero"
      >
        {/* Radial glow accents */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(139,92,246,0.15),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(236,72,153,0.08),transparent_35%)]" />

        <div className="relative grid gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          {/* Left — Copy + Stats + CTAs */}
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-rose-400/20 bg-rose-400/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-rose-200">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
              Live Battle Now
            </div>

            <h1 className="mt-4 max-w-xl text-2xl font-black leading-tight text-white sm:text-3xl lg:text-4xl" data-testid="hero-battle-title">
              {battle.root_title || 'Join the Battle'}
            </h1>

            <p className="mt-3 max-w-lg text-sm leading-relaxed text-slate-300">
              {totalEntries > 3
                ? `${totalEntries} creators fighting for #1 right now. Your rank is not safe.`
                : 'The battle is live. Jump in before someone takes the top spot.'}
            </p>

            {/* Stat cards — pressure framing, not passive info */}
            <div className="mt-5 grid gap-3 grid-cols-3">
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-3.5" data-testid="stat-views">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Eye className="w-3.5 h-3.5 text-violet-300" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">Watching</span>
                </div>
                <p className="mt-1.5 text-xl font-bold text-white">
                  {totalViews > 1000 ? `${(totalViews / 1000).toFixed(1)}K` : totalViews}
                </p>
              </div>
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-3.5" data-testid="stat-competing">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Swords className="w-3.5 h-3.5 text-fuchsia-300" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">Fighting</span>
                </div>
                <p className="mt-1.5 text-xl font-bold text-white">{totalEntries}</p>
              </div>
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-3.5" data-testid="stat-rank">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Trophy className="w-3.5 h-3.5 text-amber-300" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">Your Rank</span>
                </div>
                <p className={`mt-1.5 text-xl font-bold ${userRank === 1 ? 'text-amber-300' : userRank && userRank <= 3 ? 'text-rose-300' : 'text-white'}`}>
                  {userRank ? `#${userRank}` : '—'}
                </p>
              </div>
            </div>

            {/* Time pressure + rank context */}
            <div className="mt-4 space-y-2.5">
              {/* Countdown timer — measurable urgency */}
              <div className="flex items-center gap-2 text-[11px]" data-testid="rank-countdown">
                <span className="inline-flex items-center gap-1 text-amber-400/80 font-mono font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                  Next rank update in 0:{nextUpdate.toString().padStart(2, '0')}
                </span>
                <span className="text-slate-500">— rankings can shift anytime</span>
              </div>

              {/* Rank context — psychological pressure */}
              {userRank && (
                <div className={`rounded-2xl border p-3.5 ${
                  userRank === 1
                    ? 'border-amber-400/20 bg-amber-400/[0.06]'
                    : 'border-rose-400/15 bg-rose-400/[0.04]'
                }`} data-testid="rank-context">
                  <div className="flex items-start gap-2.5">
                    <Crown className={`mt-0.5 w-4 h-4 flex-shrink-0 ${userRank === 1 ? 'text-amber-300' : 'text-rose-300'}`} />
                    <div>
                      <p className="text-sm font-bold text-white">
                        {userRank === 1
                          ? "You're #1 — but they're coming for you"
                          : userRank <= 3
                          ? `You're losing your spot — ${activeRendering > 0 ? `${activeRendering} new entries just dropped` : 'rankings shifting now'}`
                          : `#${userRank} — you need to move fast`}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {userRank === 1
                          ? `${activeRendering > 0 ? `${activeRendering} challengers rendering` : 'Stay sharp — someone could overtake you anytime'}`
                          : `You're 1 move away from climbing`}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Win reward visibility — concrete, not abstract */}
              <div className="rounded-2xl border border-amber-500/10 bg-amber-500/[0.03] p-3 flex items-center gap-2.5" data-testid="win-reward">
                <Crown className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <p className="text-xs text-amber-200/70">
                  <span className="font-bold text-amber-200">#1 gets featured to all users</span> — last winner gained +{Math.max(200, totalViews)} views in 24hrs
                </p>
              </div>
            </div>

            {/* CTAs — identity + speed + loss micro-copy */}
            <div className="mt-5 space-y-1.5">
              <div className="flex flex-col gap-2.5 sm:flex-row">
                <button
                  onClick={handleEnterBattle}
                  disabled={enterLoading}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-violet-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-violet-900/30 transition-all hover:bg-violet-500 hover:shadow-violet-900/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
                  data-testid="hero-enter-battle-btn"
                >
                  {enterLoading
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Swords className="w-4 h-4" />
                  }
                  {userRank ? 'Claim Your Rank' : 'Enter Battle'}
                </button>
                <button
                  onClick={handleQuickShot}
                  disabled={quickShotLoading}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-6 py-3 text-sm font-bold text-white transition-all hover:bg-white/[0.08] hover:scale-[1.02] active:scale-[0.98]"
                  data-testid="hero-quick-shot-btn"
                >
                  {quickShotLoading
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Zap className="w-4 h-4" />
                  }
                  Post in 10 Seconds
                </button>
              </div>
              {/* Loss framing micro-copy */}
              <div className="flex gap-4 text-[10px] text-slate-500 pl-1">
                <span>Lose position if you wait</span>
                <span>Fastest way to climb right now</span>
              </div>
            </div>
          </div>

          {/* Right — #1 Preview */}
          <div className="relative">
            <div className="overflow-hidden rounded-2xl border border-white/[0.06] bg-black/20 shadow-xl">
              <div className="relative aspect-[16/10]">
                {topEntry?.thumbnail_url || battle.root_thumbnail ? (
                  <img
                    src={topEntry?.thumbnail_url || battle.root_thumbnail}
                    alt={topEntry?.title || battle.root_title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-violet-600/20 to-rose-600/20" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

                <button
                  onClick={() => navigate(`/app/story-battle/${battle.root_story_id}`)}
                  className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-black/40 px-2.5 py-1 text-[10px] font-medium text-white backdrop-blur-sm hover:bg-black/60 transition-colors"
                  data-testid="hero-watch-preview"
                >
                  <PlayCircle className="w-3.5 h-3.5" /> Watch Battle
                </button>

                <div className="absolute bottom-0 left-0 right-0 p-4">
                  <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-0.5 text-[10px] font-bold text-amber-200">
                    <Crown className="w-3 h-3" /> #1 Entry
                  </div>
                  <h3 className="mt-2 text-base font-bold text-white line-clamp-2">
                    {topEntry?.title || battle.root_title}
                  </h3>
                  <p className="mt-1 text-xs text-slate-300">
                    by {topEntry?.creator_name || 'Creator'} · {topEntry?.score?.toFixed(0) || 0} pts
                  </p>
                </div>
              </div>
            </div>

            {/* Live activity badge */}
            {activeRendering > 0 && (
              <div className="absolute -top-2 -right-2 flex items-center gap-1 rounded-full bg-rose-500 px-2.5 py-1 text-[10px] font-bold text-white shadow-lg shadow-rose-500/30 z-10">
                <Flame className="w-3 h-3" /> {activeRendering} rendering now
              </div>
            )}
          </div>
        </div>
      </section>

      <BattlePaywallModal
        open={showPaywall}
        onClose={() => setShowPaywall(false)}
        onSuccess={() => {
          setShowPaywall(false);
          handleEnterBattle();
        }}
        trigger="enter_battle"
        battleContext={{
          rootTitle: battle.root_title,
          currentRank: userRank,
          competitorCount: totalEntries,
        }}
      />
    </>
  );
}
