import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Crown, TrendingDown, TrendingUp, Zap, Share2, AlertTriangle, Bell, X } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { usePushNotifications } from '../hooks/usePushNotifications';

/**
 * BattlePulse — Real-time WIN/LOSS moments + competitive signals + push prompts.
 * Polls /api/stories/battle-pulse/{rootId} every 12s.
 *
 * P0: Push notification prompt on first rank detection
 * P0.5: WIN share trigger — persistent, aggressive, unmissable
 */
export default function BattlePulse({ rootStoryId, onEnterBattle }) {
  const [pulse, setPulse] = useState(null);
  const [moment, setMoment] = useState(null);
  const [winDismissed, setWinDismissed] = useState(false);
  const [showPushPrompt, setShowPushPrompt] = useState(false);
  const pushPromptShown = useRef(false);
  const hasUnmounted = useRef(false);
  const { permission, subscribed, requestPermission, isSupported } = usePushNotifications();

  const fetchPulse = useCallback(async () => {
    if (!rootStoryId) return;
    try {
      const res = await api.get(`/api/stories/battle-pulse/${rootStoryId}`);
      if (res.data?.pulse) {
        setPulse(res.data.pulse);
        if (res.data.pulse.moment) {
          setMoment(res.data.pulse.moment);
          // WIN moments persist until dismissed. Others auto-dismiss.
          if (res.data.pulse.moment.type !== 'win_first') {
            setTimeout(() => setMoment(null), 6000);
          }
        }
      }
    } catch {}
  }, [rootStoryId]);

  useEffect(() => { fetchPulse(); }, [fetchPulse]);
  useEffect(() => {
    const iv = setInterval(fetchPulse, 12000);
    return () => clearInterval(iv);
  }, [fetchPulse]);

  // Show push notification prompt when user has a rank (they're in the battle)
  useEffect(() => {
    if (
      pulse?.user_rank &&
      isSupported &&
      permission === 'default' &&
      !pushPromptShown.current
    ) {
      pushPromptShown.current = true;
      // Delay to not interrupt the experience
      const t = setTimeout(() => setShowPushPrompt(true), 3000);
      return () => clearTimeout(t);
    }
  }, [pulse?.user_rank, isSupported, permission]);

  // Compulsion hook: when user leaves the page
  useEffect(() => {
    hasUnmounted.current = false;
    return () => {
      hasUnmounted.current = true;
      if (pulse?.user_rank && pulse.user_rank <= 5) {
        toast('This battle is still active — your rank is not stable', {
          duration: 4000,
        });
      }
    };
  }, [pulse?.user_rank]);

  const handleShare = () => {
    const url = `${window.location.origin}/app/story-battle/${rootStoryId}`;
    if (navigator.share) {
      navigator.share({ title: 'Battle', url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url);
      toast.success('Link copied!');
    }
    // Track win-share conversion
    api.post('/api/funnel/track', {
      event: 'win_share_triggered',
      data: { root_id: rootStoryId, rank: pulse?.user_rank },
    }).catch(() => {});
    api.post('/api/stories/increment-metric', {
      job_id: rootStoryId, metric: 'shares'
    }).catch(() => {});
  };

  const handleEnablePush = async () => {
    const ok = await requestPermission();
    setShowPushPrompt(false);
    if (ok) {
      toast.success('Notifications enabled — we\'ll alert you if your rank drops');
    }
  };

  if (!pulse) return null;

  // Transform activity into competitive signals
  const competitiveSignals = [];
  if (pulse.active_rendering > 0) {
    competitiveSignals.push({
      text: `${pulse.active_rendering} ${pulse.active_rendering > 1 ? 'people are' : 'person is'} trying to beat the leaderboard`,
      urgent: true,
    });
  }
  if (pulse.recent_activity?.length > 0) {
    const recentCount = pulse.recent_activity.length;
    if (recentCount >= 2) {
      competitiveSignals.push({
        text: `${recentCount} new entries in the last hour`,
        urgent: false,
      });
    }
    for (const a of pulse.recent_activity.slice(0, 2)) {
      if (a.mins_ago < 15) {
        competitiveSignals.push({
          text: `${a.text.split(' entered')[0]} just entered — rankings shifting`,
          urgent: a.mins_ago < 5,
        });
        break;
      }
    }
  }
  if (pulse.user_rank && pulse.user_rank > 1 && pulse.top_3?.[0]) {
    const gap = (pulse.top_3[0].score - (pulse.user_entry?.score || 0)).toFixed(0);
    if (gap <= 5) {
      competitiveSignals.push({
        text: `Only ${gap} pts to #1 — one share could flip it`,
        urgent: true,
      });
    }
  }

  return (
    <div className="space-y-2" data-testid="battle-pulse">
      {/* ═══ PUSH NOTIFICATION PROMPT — "Know when your rank drops" ═══ */}
      {showPushPrompt && (
        <div
          className="rounded-xl p-4 bg-slate-800/60 border border-white/10 animate-in fade-in slide-in-from-top-2 duration-300"
          data-testid="push-notification-prompt"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-rose-500/20 flex items-center justify-center flex-shrink-0">
              <Bell className="w-4 h-4 text-rose-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white">Get notified if your rank drops</p>
              <p className="text-[10px] text-white/40">We'll send a push when someone beats you</p>
            </div>
            <button
              onClick={handleEnablePush}
              className="flex-shrink-0 px-3 py-2 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold hover:bg-rose-500/30 transition-colors"
              data-testid="enable-push-btn"
            >
              Enable
            </button>
            <button
              onClick={() => setShowPushPrompt(false)}
              className="flex-shrink-0 text-white/20 hover:text-white/50 transition-colors"
              data-testid="dismiss-push-prompt"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ═══ WIN MOMENT — #1 — ego spike + UNMISSABLE share trigger ═══ */}
      {moment && moment.type === 'win_first' && !winDismissed && (
        <div
          className="rounded-xl p-5 text-center bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border-2 border-amber-500/40 animate-in fade-in zoom-in-95 duration-500 relative"
          data-testid="moment-win_first"
        >
          <button
            onClick={() => setWinDismissed(true)}
            className="absolute top-2 right-2 text-white/20 hover:text-white/50"
            data-testid="dismiss-win-moment"
          >
            <X className="w-4 h-4" />
          </button>
          <Crown className="w-12 h-12 text-amber-400 mx-auto mb-2 animate-bounce" />
          <p className="text-lg font-black text-amber-300">YOU'RE #1</p>
          <p className="text-sm text-white/70 mt-1 font-semibold">
            You just beat {pulse.total_entries - 1} others in this battle
          </p>
          <p className="text-xs text-amber-400/80 mt-2 font-medium">
            This is getting pushed to more users
          </p>

          {/* PRIMARY SHARE CTA — BIG, unmissable */}
          <button
            onClick={handleShare}
            className="mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-sm font-black transition-all hover:scale-[1.02] active:scale-[0.98]"
            data-testid="win-share-btn"
          >
            <Share2 className="w-4 h-4" /> Share now to lock your position
          </button>
          <p className="text-[10px] text-amber-400/60 mt-2">
            Sharing boosts your visibility score
          </p>
        </div>
      )}

      {/* ═══ RANK UP — positive reinforcement ═══ */}
      {moment && moment.type === 'rank_up' && (
        <div
          className="rounded-xl p-4 text-center bg-emerald-500/10 border border-emerald-500/20 animate-in fade-in zoom-in-95 duration-500"
          data-testid="moment-rank_up"
        >
          <TrendingUp className="w-7 h-7 text-emerald-400 mx-auto mb-2" />
          <p className="text-sm font-black text-emerald-300">{moment.message}</p>
          <p className="text-xs text-white/50 mt-0.5">{moment.detail}</p>
          {moment.subtext && <p className="text-[10px] text-emerald-400/60 mt-1">{moment.subtext}</p>}
        </div>
      )}

      {/* ═══ LOSS — aggressive, drives action ═══ */}
      {moment && moment.type === 'rank_drop' && (
        <div
          className="rounded-xl p-4 bg-rose-500/10 border border-rose-500/25 animate-in fade-in zoom-in-95 duration-500"
          data-testid="moment-rank_drop"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm font-black text-rose-300">{moment.message}</p>
              <p className="text-xs text-white/50">Someone just beat your entry</p>
            </div>
            <button
              onClick={() => onEnterBattle?.()}
              className="flex-shrink-0 px-3 py-2 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold hover:bg-rose-500/30 transition-colors"
              data-testid="loss-act-btn"
            >
              Act now
            </button>
          </div>
        </div>
      )}

      {/* ═══ COMPETITIVE SIGNALS — threat + competition ═══ */}
      {competitiveSignals.length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3" data-testid="competitive-signals">
          <div className="flex items-center gap-1.5 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">Battle Pulse</span>
          </div>
          <div className="space-y-1.5">
            {competitiveSignals.slice(0, 3).map((s, i) => (
              <p key={i} className={`text-[11px] flex items-center gap-1.5 ${s.urgent ? 'text-amber-400/70 font-medium' : 'text-white/35'}`}>
                <Zap className={`w-2.5 h-2.5 ${s.urgent ? 'text-amber-400' : 'text-white/20'}`} />
                {s.text}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
