import React, { useState, useEffect } from 'react';
import { Flame, TrendingUp } from 'lucide-react';
import api from '../utils/api';

/**
 * StreakBadge — Shows on homepage + battle screens.
 * Displays current streak, milestone, boost, and next target.
 */
export default function StreakBadge({ compact = false }) {
  const [streak, setStreak] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/streaks/me');
        if (res.data?.streak) setStreak(res.data.streak);
      } catch {}
    })();
  }, []);

  if (!streak || streak.current === 0) return null;

  const { current, boost_percent, milestone, next_milestone, participated_today } = streak;

  if (compact) {
    return (
      <div className="inline-flex items-center gap-1.5 bg-orange-500/10 border border-orange-500/20 rounded-full px-2.5 py-1"
        data-testid="streak-badge-compact">
        <Flame className="w-3 h-3 text-orange-400" />
        <span className="text-xs font-bold text-orange-400">{current}-day</span>
        {boost_percent && boost_percent !== '+0%' && (
          <span className="text-[10px] text-orange-300/60">{boost_percent}</span>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-orange-500/20 bg-orange-500/[0.04] p-4" data-testid="streak-badge">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-orange-500/20 flex items-center justify-center">
          <Flame className="w-5 h-5 text-orange-400" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-black text-orange-400">{current}-Day Battle Streak</span>
            {milestone && (
              <span className="text-[10px] bg-orange-500/20 text-orange-300 rounded-full px-2 py-0.5 font-bold">
                {milestone.label}
              </span>
            )}
          </div>
          <p className="text-xs text-white/40">
            {participated_today
              ? "You've competed today"
              : "Compete today to keep your streak alive"
            }
            {next_milestone && (
              <span className="text-orange-300/60">
                {' '} — {next_milestone.days_remaining} more day{next_milestone.days_remaining > 1 ? 's' : ''} to {next_milestone.label}
              </span>
            )}
          </p>
        </div>
        {boost_percent && boost_percent !== '+0%' && (
          <div className="flex items-center gap-1 bg-orange-500/10 rounded-lg px-2 py-1">
            <TrendingUp className="w-3 h-3 text-orange-400" />
            <span className="text-xs font-bold text-orange-400">{boost_percent} boost</span>
          </div>
        )}
      </div>
    </div>
  );
}
