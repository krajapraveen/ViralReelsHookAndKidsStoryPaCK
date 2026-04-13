import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Trophy, GitBranch, Play, Eye, Share2,
  Crown, Swords, TrendingUp, ArrowRight, Plus, Flame
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';
import ContinuationModal from '../components/ContinuationModal';
import BattlePulse from '../components/BattlePulse';
import BattlePaywallModal from '../components/BattlePaywallModal';

/**
 * StoryBattlePage — THE WATCH PAGE. Core of the competition loop.
 *
 * 7 required components:
 * 1. Rank + Score
 * 2. Live activity (BattlePulse polling)
 * 3. WIN/LOSS system (BattlePulse moments)
 * 4. Video autoplay (#1 contender)
 * 5. Share CTA
 * 6. Enter Battle CTA (paywall-gated)
 * 7. Return trigger
 */
export default function StoryBattlePage() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [continuationMode, setContinuationMode] = useState(null);
  const [showPaywall, setShowPaywall] = useState(false);
  const [paywallTrigger, setPaywallTrigger] = useState('enter_battle');
  const returnTriggerRef = useRef(null);
  const returnTracked = useRef(false);

  const fetchBattle = useCallback(async () => {
    if (!storyId) return;
    try {
      const res = await api.get(`/api/stories/battle/${storyId}`);
      setBattle(res.data);
    } catch {
      toast.error('Battle not found');
      navigate('/app');
    } finally {
      setLoading(false);
    }
  }, [storyId, navigate]);

  useEffect(() => { fetchBattle(); }, [fetchBattle]);

  // Poll battle data every 12s for live updates
  useEffect(() => {
    const iv = setInterval(fetchBattle, 12000);
    return () => clearInterval(iv);
  }, [fetchBattle]);

  // Track return_trigger_sent when user scrolls to see it
  useEffect(() => {
    const el = returnTriggerRef.current;
    if (!el || returnTracked.current) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !returnTracked.current) {
        returnTracked.current = true;
        trackFunnel('return_trigger_sent', { story_id: storyId, battle_id: storyId });
      }
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [storyId]);

  // Share handler
  const handleShare = () => {
    const url = `${window.location.origin}/app/story-battle/${storyId}`;
    if (navigator.share) {
      navigator.share({ title: 'Story Battle', url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url);
      toast.success('Battle link copied!');
    }
    trackFunnel('cta_clicked', { meta: { type: 'share_battle', story_id: storyId } });
  };

  // Enter battle with paywall check
  const handleEnterBattle = async (trigger = 'enter_battle') => {
    try {
      const res = await api.get('/api/stories/battle-entry-status');
      if (res.data?.needs_payment) {
        setPaywallTrigger(trigger);
        setShowPaywall(true);
        return;
      }
    } catch {}
    trackFunnel('cta_clicked', { meta: { type: 'enter_battle', source: 'watch_page' }, story_id: storyId, battle_id: rootId });
    trackFunnel('entered_battle', { story_id: storyId, battle_id: rootId });
    setContinuationMode('branch');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" data-testid="battle-loading">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (!battle) return null;

  const { contenders, total_contenders, user_rank, battle_parent_id, current_story } = battle;
  const topContender = contenders?.[0];
  const rootId = battle_parent_id || storyId;

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate('/app')} className="text-white/40 hover:text-white" data-testid="battle-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-bold text-white flex items-center gap-2" data-testid="battle-header-title">
              <Swords className="w-4 h-4 text-rose-400" /> Story Battle
            </h1>
            <p className="text-xs text-white/40">{total_contenders} competing</p>
          </div>
          <button
            onClick={handleShare}
            className="p-2 rounded-lg bg-white/[0.04] text-white/50 hover:text-white transition-colors"
            data-testid="battle-share-header-btn"
          >
            <Share2 className="w-4 h-4" />
          </button>
          <Button
            size="sm"
            onClick={() => handleEnterBattle('enter_battle')}
            className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
            data-testid="enter-battle-header-btn"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Enter Battle
          </Button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-5 space-y-5">

        {/* ═══ 1. RANK + SCORE (User's position) ═══ */}
        {user_rank && (
          <div className={`rounded-xl p-4 border ${
            user_rank === 1
              ? 'bg-amber-500/[0.06] border-amber-500/25'
              : 'bg-rose-500/[0.06] border-rose-500/20'
          }`} data-testid="user-rank-card">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                user_rank === 1 ? 'bg-amber-500/20' : 'bg-rose-500/20'
              }`}>
                {user_rank === 1
                  ? <Crown className="w-6 h-6 text-amber-400" />
                  : <span className="text-xl font-black text-rose-400">#{user_rank}</span>
                }
              </div>
              <div className="flex-1">
                <p className={`text-base font-black ${user_rank === 1 ? 'text-amber-300' : 'text-rose-300'}`}>
                  {user_rank === 1 ? "You're #1!" : `You're ranked #${user_rank}`}
                </p>
                <p className="text-xs text-white/40">
                  {user_rank === 1
                    ? 'Share to lock your position'
                    : `${user_rank - 1} ahead — one entry could change it`
                  }
                </p>
              </div>
              {user_rank === 1 ? (
                <button
                  onClick={handleShare}
                  className="flex-shrink-0 px-4 py-2 rounded-lg bg-amber-500 text-black text-xs font-black hover:bg-amber-400 transition-colors"
                  data-testid="win-share-battle-btn"
                >
                  <Share2 className="w-3.5 h-3.5 inline mr-1" /> Share
                </button>
              ) : (
                <button
                  onClick={() => handleEnterBattle('loss_moment')}
                  className="flex-shrink-0 px-4 py-2 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold hover:bg-rose-500/30 transition-colors"
                  data-testid="take-back-spot-btn"
                >
                  Take it back
                </button>
              )}
            </div>
          </div>
        )}

        {/* ═══ 2+3. LIVE ACTIVITY + WIN/LOSS SYSTEM (BattlePulse) ═══ */}
        <BattlePulse
          rootStoryId={rootId}
          onEnterBattle={() => handleEnterBattle('loss_moment')}
          onNearWinPaywall={() => handleEnterBattle('near_win')}
        />

        {/* ═══ 4. VIDEO AUTOPLAY (#1 contender) ═══ */}
        {topContender?.output_url && (
          <div className="rounded-xl overflow-hidden border border-white/5" data-testid="top-video-player">
            <video
              src={topContender.output_url}
              poster={topContender.thumbnail_url}
              className="w-full aspect-video object-contain bg-black"
              autoPlay
              muted
              playsInline
              loop
              data-testid="battle-top-video"
            />
            <div className="p-3 bg-white/[0.02] flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs font-bold text-amber-300">#1</span>
              </div>
              <p className="text-xs font-semibold text-white truncate flex-1">{topContender.title}</p>
              <span className="text-xs text-white/40">by {topContender.creator_name}</span>
              <button
                onClick={() => navigate(`/app/story-viewer/${topContender.job_id}`)}
                className="text-xs text-violet-400 font-medium hover:text-violet-300 flex items-center gap-1"
                data-testid="watch-full-btn"
              >
                Watch <Play className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}

        {/* ═══ 5. SHARE CTA (prominent) ═══ */}
        <button
          onClick={handleShare}
          className="w-full bg-gradient-to-r from-amber-500/10 to-rose-500/10 border border-amber-500/15 rounded-xl p-3.5 text-left hover:from-amber-500/15 hover:to-rose-500/15 transition-all"
          data-testid="share-battle-cta"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Share2 className="w-4 h-4 text-amber-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-bold text-amber-300">Share this battle</p>
              <p className="text-[10px] text-white/35">More shares = more visibility for your entry</p>
            </div>
            <ArrowRight className="w-4 h-4 text-amber-400/40 flex-shrink-0" />
          </div>
        </button>

        {/* ═══ LEADERBOARD ═══ */}
        <div data-testid="battle-leaderboard">
          <h3 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3 flex items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5" /> Leaderboard
          </h3>
          <div className="space-y-2">
            {contenders.map((c) => (
              <button
                key={c.job_id}
                onClick={() => navigate(`/app/story-viewer/${c.job_id}`)}
                className={`w-full rounded-xl border p-3.5 flex items-center gap-3 transition-all hover:bg-white/[0.03] text-left ${
                  c.rank === 1 ? 'border-amber-500/20 bg-amber-500/[0.03]' :
                  c.user_id === battle.user_id ? 'border-violet-500/20 bg-violet-500/[0.03]' :
                  'border-white/5 bg-white/[0.01]'
                }`}
                data-testid={`contender-card-${c.rank}`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  c.rank === 1 ? 'bg-amber-500/20' : 'bg-white/5'
                }`}>
                  {c.rank === 1
                    ? <Crown className="w-4 h-4 text-amber-400" />
                    : <span className="text-xs font-black text-white/40">#{c.rank}</span>
                  }
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">
                    {c.title || 'Untitled'}
                    {c.user_id === battle.user_id && <span className="text-violet-400 text-[10px] ml-1.5">(You)</span>}
                  </p>
                  <p className="text-[10px] text-white/30">
                    {c.creator_name} · {c.total_views || 0} views
                  </p>
                </div>
                <span className={`text-xs font-bold flex-shrink-0 ${c.rank === 1 ? 'text-amber-400' : 'text-white/40'}`}>
                  {(c.battle_score || 0).toFixed(0)} pts
                </span>
                <Play className="w-3.5 h-3.5 text-white/20 flex-shrink-0" />
              </button>
            ))}
          </div>
        </div>

        {/* ═══ 6. ENTER BATTLE CTA (paywall-gated) ═══ */}
        <button
          onClick={() => handleEnterBattle(user_rank > 1 ? 'loss_moment' : 'enter_battle')}
          className="w-full group relative overflow-hidden rounded-xl p-4 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
          data-testid="enter-battle-cta"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-rose-600 to-violet-600 opacity-90 group-hover:opacity-100 transition-opacity rounded-xl" />
          <div className="relative z-10 flex items-center justify-center gap-2">
            <Swords className="w-5 h-5 text-white" />
            <span className="text-sm font-black text-white">
              {user_rank ? (user_rank === 1 ? 'Defend Your #1 Spot' : 'Claim Your Rank') : 'Enter Battle'}
            </span>
          </div>
          <p className="relative z-10 text-[10px] text-white/60 text-center mt-1">
            {user_rank > 1
              ? `You're #${user_rank} — 1 move changes everything`
              : 'Create your version and compete for the top spot'
            }
          </p>
        </button>

        {/* ═══ 7. RETURN TRIGGER — unfinished business ═══ */}
        <div
          ref={returnTriggerRef}
          className="bg-slate-800/30 border border-white/5 rounded-xl p-4 text-center"
          data-testid="return-trigger"
        >
          <div className="flex items-center justify-center gap-1.5 mb-1">
            <Flame className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <p className="text-xs font-bold text-white/50">This battle is moving fast</p>
          </div>
          <p className="text-[10px] text-white/30">Leave now and your rank might drop — someone new enters every few minutes</p>
        </div>
      </div>

      {/* ContinuationModal */}
      <ContinuationModal
        isOpen={!!continuationMode}
        onClose={() => setContinuationMode(null)}
        mode="branch"
        parentJob={{
          job_id: battle_parent_id,
          title: current_story?.title || 'Story',
          story_text: current_story?.story_text || '',
          animation_style: current_story?.animation_style || 'cartoon_2d',
        }}
        onJobCreated={(data) => {
          if (data?.job_id) {
            toast.success('Your competing version is generating!');
            navigate(`/app/story-video-studio?projectId=${data.job_id}`);
          }
        }}
      />

      {/* Battle Paywall — modal only */}
      <BattlePaywallModal
        open={showPaywall}
        onClose={() => setShowPaywall(false)}
        onSuccess={() => {
          setShowPaywall(false);
          setContinuationMode('branch');
        }}
        trigger={paywallTrigger}
        battleContext={{
          rootTitle: current_story?.title,
          currentRank: user_rank,
          competitorCount: total_contenders,
        }}
      />
    </div>
  );
}
