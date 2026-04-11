import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Swords, Clock, Trophy, Crown, GitBranch, TrendingUp, AlertTriangle,
  ArrowRight, Loader2, ChevronUp, ChevronDown, Eye, Share2, Plus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import ContinuationModal from '../components/ContinuationModal';

/**
 * DailyWarPage — The Daily Story War experience.
 * Route: /app/war
 * Polls every 15s for live-updating leaderboard.
 */
export default function DailyWarPage() {
  const navigate = useNavigate();
  const [war, setWar] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [yesterdayRank, setYesterdayRank] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showContinuation, setShowContinuation] = useState(false);
  const [prevRanks, setPrevRanks] = useState({});

  const fetchWar = useCallback(async () => {
    try {
      const res = await api.get('/api/war/current');
      if (res.data?.success) {
        const newLb = res.data.leaderboard;

        // Detect rank changes for overtake alerts
        if (leaderboard && newLb) {
          const oldMap = {};
          for (const e of leaderboard.entries || []) {
            oldMap[e.job_id] = e.war_rank;
          }
          setPrevRanks(oldMap);
        }

        setWar(res.data.war);
        setLeaderboard(newLb);
        setYesterdayRank(res.data.yesterday_rank);
      }
    } catch {
      // Silent fail for polling
    } finally {
      setLoading(false);
    }
  }, [leaderboard]);

  // Initial load
  useEffect(() => { fetchWar(); }, []);

  // Poll every 15s
  useEffect(() => {
    const iv = setInterval(fetchWar, 15000);
    return () => clearInterval(iv);
  }, [fetchWar]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" data-testid="war-loading">
        <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
      </div>
    );
  }

  // No war
  if (!war) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4" data-testid="war-empty">
        <div className="text-center max-w-md">
          <Swords className="w-12 h-12 text-rose-400/30 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No Story War Active</h2>
          <p className="text-sm text-white/40 mb-6">The next war will start soon. Check back later.</p>
          <Button onClick={() => navigate('/app/dashboard')} variant="outline" className="border-white/10 text-white/50">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const isActive = war.state === 'active';
  const isEnded = war.state === 'winner_declared' || war.state === 'ended';
  const entries = leaderboard?.entries || [];
  const userRank = leaderboard?.user_rank;
  const userEntry = leaderboard?.user_entry;
  const hasEntered = !!userEntry;
  const topEntry = entries[0];

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">

        {/* ═══ WAR HEADER ═══ */}
        <div className="relative overflow-hidden rounded-2xl border border-rose-500/30 bg-gradient-to-br from-rose-600/10 to-orange-600/5 p-6"
          data-testid="war-header">
          <div className="flex items-center gap-2 mb-3">
            <Swords className="w-5 h-5 text-rose-400" />
            <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">Daily Story War</span>
          </div>

          <h1 className="text-2xl font-black text-white mb-1" data-testid="war-title">
            {war.root_title || 'Story War'}
          </h1>

          {isActive && (
            <div className="flex items-center gap-4 mt-3">
              <CountdownTimer seconds={war.time_left_seconds} />
              <div className="text-xs text-white/40">
                {war.total_entries} warrior{war.total_entries !== 1 ? 's' : ''} competing
              </div>
            </div>
          )}

          {isEnded && war.winner_title && (
            <div className="mt-3 flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-400" />
              <span className="text-sm text-amber-400 font-bold">
                Winner: {war.winner_title} by {war.winner_creator_name}
              </span>
            </div>
          )}

          {/* Prize banner */}
          <div className="mt-4 bg-black/20 rounded-lg p-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Trophy className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <p className="text-xs font-bold text-amber-400">Prize: Featured on Homepage</p>
              <p className="text-[10px] text-white/30">Winner gets massive reach boost + homepage hero slot</p>
            </div>
          </div>
        </div>

        {/* ═══ YESTERDAY RE-ENTRY ═══ */}
        {yesterdayRank && isActive && !hasEntered && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-4 flex items-center gap-3"
            data-testid="yesterday-reentry">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <span className="text-lg font-black text-amber-400">#{yesterdayRank}</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-amber-300">Yesterday you were #{yesterdayRank}</p>
              <p className="text-xs text-white/40">Take the crown today.</p>
            </div>
            <Button
              size="sm"
              onClick={() => setShowContinuation(true)}
              className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs"
              data-testid="yesterday-enter-btn"
            >
              Enter Today
            </Button>
          </div>
        )}

        {/* ═══ YOUR RANK (if entered) ═══ */}
        {hasEntered && (
          <UserRankCard
            rank={userRank}
            entry={userEntry}
            topEntry={topEntry}
            isActive={isActive}
          />
        )}

        {/* ═══ OVERTAKE ALERT (inline) ═══ */}
        {hasEntered && userRank > 1 && prevRanks[userEntry?.job_id] && prevRanks[userEntry?.job_id] < userRank && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 flex items-center gap-3 animate-pulse"
            data-testid="overtake-alert">
            <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-bold text-rose-300">You were overtaken!</p>
              <p className="text-xs text-white/40">Someone just passed you. Share your entry to get more views.</p>
            </div>
          </div>
        )}

        {/* ═══ ENTER THE WAR CTA ═══ */}
        {isActive && !hasEntered && (
          <button
            onClick={() => setShowContinuation(true)}
            className="w-full group relative overflow-hidden rounded-2xl p-6 text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
            data-testid="enter-war-btn"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-rose-600 to-orange-600 opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                <Swords className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1">
                <span className="text-xl font-black text-white block mb-1">Enter the War</span>
                <span className="text-sm text-white/60">1 story. 24 hours. 1 winner. Create your version now.</span>
              </div>
              <ArrowRight className="w-6 h-6 text-white/40 group-hover:text-white group-hover:translate-x-1 transition-all" />
            </div>
          </button>
        )}

        {/* ═══ LEADERBOARD ═══ */}
        {entries.length > 0 && (
          <div data-testid="war-leaderboard">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white/60 flex items-center gap-2">
                <Swords className="w-4 h-4" /> War Leaderboard
              </h3>
              <span className="text-[10px] text-white/30">Live-updating</span>
            </div>
            <div className="space-y-2">
              {entries.map((entry) => (
                <LeaderboardEntry
                  key={entry.job_id}
                  entry={entry}
                  isCurrentUser={entry.user_id === leaderboard?.user_entry?.user_id}
                  prevRank={prevRanks[entry.job_id]}
                />
              ))}
            </div>
          </div>
        )}

        {/* ═══ END OF WAR — Winner Declaration ═══ */}
        {isEnded && war.winner_title && (
          <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-amber-600/5 p-6 text-center"
            data-testid="war-winner-declaration">
            <Crown className="w-10 h-10 text-amber-400 mx-auto mb-3" />
            <h2 className="text-xl font-black text-white mb-1">
              Winner: {war.winner_creator_name}
            </h2>
            <p className="text-sm text-amber-400 font-semibold mb-1">"{war.winner_title}"</p>
            <p className="text-xs text-white/40 mb-4">Score: {war.winner_score?.toFixed(1)} pts</p>

            {hasEntered && userRank > 1 && (
              <p className="text-sm text-rose-300 mb-4">
                You placed <span className="font-black">#{userRank}</span>. Try again tomorrow.
              </p>
            )}
            {hasEntered && userRank === 1 && (
              <p className="text-sm text-emerald-400 mb-4 font-bold">
                That's YOU! You'll be featured on the homepage.
              </p>
            )}
          </div>
        )}

        {/* ═══ STORY CONTEXT ═══ */}
        {war.root_story_text && (
          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4" data-testid="war-story-context">
            <p className="text-[10px] font-bold text-white/30 uppercase tracking-wider mb-2">Today's Story Prompt</p>
            <p className="text-sm text-white/60 italic leading-relaxed">
              "{war.root_story_text}"
            </p>
          </div>
        )}
      </div>

      {/* ═══ ContinuationModal for war entry ═══ */}
      <ContinuationModal
        isOpen={showContinuation}
        onClose={() => setShowContinuation(false)}
        mode="branch"
        parentJob={{
          job_id: war.root_story_id,
          title: war.root_title || 'Story War',
          story_text: war.root_story_text || '',
          animation_style: 'cartoon_2d',
        }}
        onJobCreated={(data) => {
          if (data?.job_id) {
            toast.success('War entry created! Your version is being generated.');
            fetchWar();
          }
        }}
      />
    </div>
  );
}


// ═══ Countdown Timer ═══
function CountdownTimer({ seconds }) {
  const [timeLeft, setTimeLeft] = useState(seconds);

  useEffect(() => {
    setTimeLeft(seconds);
  }, [seconds]);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const iv = setInterval(() => setTimeLeft(t => Math.max(0, t - 1)), 1000);
    return () => clearInterval(iv);
  }, [timeLeft]);

  const h = Math.floor(timeLeft / 3600);
  const m = Math.floor((timeLeft % 3600) / 60);
  const s = timeLeft % 60;
  const pad = (n) => String(n).padStart(2, '0');

  const isUrgent = timeLeft < 3600;

  return (
    <div className={`flex items-center gap-1.5 ${isUrgent ? 'text-rose-400' : 'text-white/60'}`}
      data-testid="war-countdown">
      <Clock className="w-3.5 h-3.5" />
      <span className={`text-sm font-mono font-bold ${isUrgent ? 'animate-pulse' : ''}`}>
        {pad(h)}:{pad(m)}:{pad(s)}
      </span>
      <span className="text-[10px] text-white/30 ml-1">left</span>
    </div>
  );
}


// ═══ User Rank Card ═══
function UserRankCard({ rank, entry, topEntry, isActive }) {
  const isLeader = rank === 1;

  return (
    <div className={`rounded-xl border p-4 ${
      isLeader
        ? 'border-emerald-500/30 bg-emerald-500/[0.06]'
        : 'border-rose-500/30 bg-rose-500/[0.06]'
    }`} data-testid="war-user-rank">
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
          isLeader ? 'bg-emerald-500/20' : 'bg-rose-500/20'
        }`}>
          {isLeader
            ? <Crown className="w-6 h-6 text-emerald-400" />
            : <span className="text-xl font-black text-rose-400">#{rank}</span>
          }
        </div>
        <div className="flex-1">
          <p className={`text-base font-bold ${isLeader ? 'text-emerald-400' : 'text-rose-300'}`}>
            {isLeader ? "You're #1!" : `You're ranked #${rank}`}
          </p>
          <p className="text-xs text-white/40">
            {isLeader
              ? 'Defend your spot — time is ticking'
              : `Gap to #1: ${entry?.gap_score || 0} pts, ${entry?.gap_continues || 0} continues behind`
            }
          </p>
        </div>
      </div>
    </div>
  );
}


// ═══ Leaderboard Entry ═══
function LeaderboardEntry({ entry, isCurrentUser, prevRank }) {
  const rank = entry.war_rank;
  const moved = prevRank ? prevRank - rank : 0; // positive = moved up

  const rankColors = {
    1: 'border-amber-500/30 bg-amber-500/[0.04]',
    2: 'border-slate-400/20 bg-slate-400/[0.02]',
    3: 'border-orange-700/20 bg-orange-700/[0.02]',
  };

  return (
    <div className={`rounded-xl border p-3.5 flex items-center gap-3 ${
      rankColors[rank] || 'border-white/5 bg-white/[0.01]'
    } ${isCurrentUser ? 'ring-1 ring-violet-500/30' : ''}`}
      data-testid={`war-entry-rank-${rank}`}>
      {/* Rank */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        rank === 1 ? 'bg-amber-500/20' : 'bg-white/5'
      }`}>
        {rank === 1
          ? <Crown className="w-4 h-4 text-amber-400" />
          : <span className={`text-sm font-black ${rank <= 3 ? 'text-white/60' : 'text-white/30'}`}>#{rank}</span>
        }
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">
          {entry.title || 'Untitled'}
          {isCurrentUser && <span className="text-violet-400 text-xs ml-2">(You)</span>}
        </p>
        <p className="text-xs text-white/30">
          by {entry.creator_name}
        </p>
      </div>

      {/* Rank movement */}
      {moved !== 0 && (
        <div className={`flex items-center gap-0.5 text-xs font-bold ${
          moved > 0 ? 'text-emerald-400' : 'text-rose-400'
        }`}>
          {moved > 0 ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {Math.abs(moved)}
        </div>
      )}

      {/* Score + stats */}
      <div className="text-right flex-shrink-0">
        <p className={`text-sm font-bold ${rank === 1 ? 'text-amber-400' : 'text-white/50'}`}>
          {(entry.war_score || 0).toFixed(1)}
        </p>
        <p className="text-[10px] text-white/30">{entry.war_views}v {entry.war_shares}s {entry.war_continues}c</p>
      </div>
    </div>
  );
}
