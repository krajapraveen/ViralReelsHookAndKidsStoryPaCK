import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Crown, TrendingDown, TrendingUp, Zap, Share2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * BattlePulse — Real-time WIN/LOSS moments + competitive signals.
 * Polls /api/stories/battle-pulse/{rootId} every 12s.
 * 
 * Upgrades:
 * 1. WIN → share button INSIDE the moment (not below)
 * 2. LOSS → aggressive, drives immediate action
 * 3. Activity → competitive signals ("trying to beat #1"), not passive logs
 * 4. Compulsion hook on unmount
 */
export default function BattlePulse({ rootStoryId, onEnterBattle }) {
  const [pulse, setPulse] = useState(null);
  const [moment, setMoment] = useState(null);
  const momentTimer = useRef(null);
  const hasUnmounted = useRef(false);

  const fetchPulse = useCallback(async () => {
    if (!rootStoryId) return;
    try {
      const res = await api.get(`/api/stories/battle-pulse/${rootStoryId}`);
      if (res.data?.pulse) {
        setPulse(res.data.pulse);
        if (res.data.pulse.moment) {
          setMoment(res.data.pulse.moment);
          clearTimeout(momentTimer.current);
          momentTimer.current = setTimeout(() => setMoment(null), 6000);
        }
      }
    } catch {}
  }, [rootStoryId]);

  useEffect(() => { fetchPulse(); }, [fetchPulse]);
  useEffect(() => {
    const iv = setInterval(fetchPulse, 12000);
    return () => { clearInterval(iv); clearTimeout(momentTimer.current); };
  }, [fetchPulse]);

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
    // Find if anyone entered top 3 recently
    const top3Ids = new Set((pulse.top_3 || []).map(t => t.creator_name));
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
      {/* ═══ WIN MOMENT — ego spike + immediate share ═══ */}
      {moment && moment.type === 'win_first' && (
        <div
          className="rounded-xl p-5 text-center bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30 animate-in fade-in zoom-in-95 duration-500"
          data-testid="moment-win_first"
        >
          <Crown className="w-10 h-10 text-amber-400 mx-auto mb-2 animate-bounce" />
          <p className="text-base font-black text-amber-300">YOU'RE #1 RIGHT NOW</p>
          <p className="text-xs text-white/60 mt-1">You just beat {pulse.total_entries - 1} others in this battle</p>
          <p className="text-[10px] text-amber-400/70 mt-1">Your entry is being pushed to more users</p>
          <button
            onClick={handleShare}
            className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-bold hover:bg-amber-500/30 transition-colors"
            data-testid="win-share-btn"
          >
            <Share2 className="w-3.5 h-3.5" /> Share to lock your position
          </button>
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

      {/* ═══ COMPETITIVE SIGNALS — threat + competition, not activity logs ═══ */}
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
