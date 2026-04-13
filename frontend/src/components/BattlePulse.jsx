import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Crown, TrendingDown, TrendingUp, Zap, Users, Swords } from 'lucide-react';
import api from '../utils/api';

/**
 * BattlePulse — Real-time WIN/LOSS moments + live activity feed.
 * Polls /api/stories/battle-pulse/{rootId} every 12s.
 * Shows rank changes with emotional peaks.
 */
export default function BattlePulse({ rootStoryId }) {
  const [pulse, setPulse] = useState(null);
  const [moment, setMoment] = useState(null);
  const momentTimer = useRef(null);

  const fetchPulse = useCallback(async () => {
    if (!rootStoryId) return;
    try {
      const res = await api.get(`/api/stories/battle-pulse/${rootStoryId}`);
      if (res.data?.pulse) {
        setPulse(res.data.pulse);

        // Show WIN/LOSS moment if detected
        if (res.data.pulse.moment) {
          setMoment(res.data.pulse.moment);
          clearTimeout(momentTimer.current);
          momentTimer.current = setTimeout(() => setMoment(null), 5000);
        }
      }
    } catch {}
  }, [rootStoryId]);

  useEffect(() => { fetchPulse(); }, [fetchPulse]);
  useEffect(() => {
    const iv = setInterval(fetchPulse, 12000);
    return () => { clearInterval(iv); clearTimeout(momentTimer.current); };
  }, [fetchPulse]);

  if (!pulse) return null;

  return (
    <div className="space-y-2" data-testid="battle-pulse">
      {/* ═══ WIN/LOSS MOMENT — emotional peak ═══ */}
      {moment && (
        <div
          className={`rounded-xl p-4 text-center animate-in fade-in zoom-in-95 duration-500 ${
            moment.type === 'win_first'
              ? 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20 border border-amber-500/30'
              : moment.type === 'rank_up'
              ? 'bg-emerald-500/10 border border-emerald-500/20'
              : 'bg-rose-500/10 border border-rose-500/20'
          }`}
          data-testid={`moment-${moment.type}`}
        >
          {moment.type === 'win_first' && (
            <Crown className="w-8 h-8 text-amber-400 mx-auto mb-2 animate-bounce" />
          )}
          {moment.type === 'rank_up' && (
            <TrendingUp className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
          )}
          {moment.type === 'rank_drop' && (
            <TrendingDown className="w-6 h-6 text-rose-400 mx-auto mb-2" />
          )}
          <p className={`text-sm font-black ${
            moment.type === 'win_first' ? 'text-amber-300' :
            moment.type === 'rank_up' ? 'text-emerald-300' : 'text-rose-300'
          }`}>
            {moment.message}
          </p>
          <p className="text-xs text-white/50 mt-0.5">{moment.detail}</p>
          {moment.subtext && (
            <p className="text-[10px] text-white/30 mt-1">{moment.subtext}</p>
          )}
        </div>
      )}

      {/* ═══ REAL-TIME ACTIVITY — makes battle feel alive ═══ */}
      {pulse.recent_activity?.length > 0 && (
        <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3" data-testid="recent-activity">
          <div className="flex items-center gap-1.5 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">Live Activity</span>
          </div>
          <div className="space-y-1">
            {pulse.recent_activity.slice(0, 3).map((a, i) => (
              <p key={i} className="text-[11px] text-white/40 flex items-center gap-1.5">
                <Zap className="w-2.5 h-2.5 text-amber-400/60" />
                {a.text}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Active rendering indicator */}
      {pulse.active_rendering > 0 && (
        <p className="text-[10px] text-violet-400/60 flex items-center gap-1 px-1">
          <div className="w-1 h-1 rounded-full bg-violet-400 animate-pulse" />
          {pulse.active_rendering} entr{pulse.active_rendering > 1 ? 'ies' : 'y'} generating right now
        </p>
      )}
    </div>
  );
}
