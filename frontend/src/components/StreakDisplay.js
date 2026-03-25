import React, { useState, useEffect } from 'react';
import { Flame, Gift, TrendingUp } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export function StreakDisplay({ variant = 'dashboard' }) {
  const [streak, setStreak] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    (async () => {
      try {
        const res = await axios.get(`${API}/api/retention/streak`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.data.success) setStreak(res.data);
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (loading || !streak) return null;

  const { current_streak, longest_streak, next_milestone, next_reward } = streak;

  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-2" data-testid="streak-compact">
        <div className="flex items-center gap-1 bg-amber-500/10 px-2.5 py-1 rounded-full">
          <Flame className={`w-4 h-4 ${current_streak > 0 ? 'text-amber-400' : 'text-slate-600'}`} />
          <span className={`text-sm font-bold ${current_streak > 0 ? 'text-amber-400' : 'text-slate-500'}`}>
            {current_streak}
          </span>
        </div>
      </div>
    );
  }

  // Dashboard variant — emotional messaging
  const progress = next_milestone ? Math.min((current_streak / next_milestone) * 100, 100) : 100;

  const getEmotionalMessage = () => {
    if (current_streak === 0) return 'Create a story today to start your streak';
    if (current_streak === 1) return 'Great start! Come back tomorrow to build momentum';
    if (current_streak < 3) return "Don't break it — your story streak is growing";
    if (current_streak < 7) return "You're on fire! Keep the momentum going";
    return "Legendary streak! You're a storytelling machine";
  };

  const getStreakLabel = () => {
    if (current_streak === 0) return 'Start a Story Streak';
    return `${current_streak}-Day Story Streak`;
  };

  return (
    <div className="vs-card p-4" data-testid="streak-display">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            current_streak > 0 ? 'bg-amber-500/10' : 'bg-slate-800'
          }`}>
            <Flame className={`w-5 h-5 ${current_streak > 0 ? 'text-amber-400 animate-pulse' : 'text-slate-600'}`} />
          </div>
          <div>
            <p className={`text-xs font-bold ${current_streak > 0 ? 'text-amber-400' : 'text-slate-500'}`}>{getStreakLabel()}</p>
            <p className="text-lg font-black text-white leading-tight">{current_streak} day{current_streak !== 1 ? 's' : ''}</p>
          </div>
        </div>
        {longest_streak > 0 && (
          <div className="text-right">
            <p className="text-[10px] text-slate-600">Best</p>
            <p className="text-xs font-bold text-slate-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> {longest_streak}d
            </p>
          </div>
        )}
      </div>

      {/* Emotional message */}
      <p className="text-xs text-slate-400 mb-3 italic" data-testid="streak-message">{getEmotionalMessage()}</p>

      {/* Next milestone progress */}
      {next_milestone && (
        <div data-testid="streak-milestone">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-500">Day {next_milestone} reward</span>
            <span className="text-amber-400 font-bold flex items-center gap-1">
              <Gift className="w-3 h-3" /> +{next_reward} credits
            </span>
          </div>
          <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-700"
              style={{ width: `${Math.max(progress, 4)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-600 mt-1">
            {current_streak < next_milestone
              ? `Continue today to keep your streak alive — ${next_milestone - current_streak} more day${next_milestone - current_streak > 1 ? 's' : ''} to go`
              : 'Milestone reached!'}
          </p>
        </div>
      )}

      {!next_milestone && current_streak > 0 && (
        <p className="text-xs text-emerald-400 font-medium">All milestones claimed!</p>
      )}
    </div>
  );
}
