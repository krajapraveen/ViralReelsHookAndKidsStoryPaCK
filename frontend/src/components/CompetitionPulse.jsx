import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy, Crown, TrendingUp, Swords, GitBranch, ChevronUp, ChevronDown, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

/**
 * CompetitionPulse — Live rank + gap-to-#1 + re-engagement CTA.
 * Shows after EVERY action/generation. Polls every 20s for live feel.
 * This is the same-session compulsion loop.
 */
export default function CompetitionPulse({ jobId, rootStoryId, onTryAgain, onBeatTop }) {
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [prevRank, setPrevRank] = useState(null);
  const [rankChanged, setRankChanged] = useState(null); // 'up' | 'down' | null

  const fetchBattle = useCallback(async () => {
    if (!rootStoryId && !jobId) return;
    try {
      const target = rootStoryId || jobId;
      const res = await api.get(`/api/stories/battle/${target}`);
      if (res.data?.success) {
        const newRank = res.data.user_rank;
        if (prevRank && newRank && newRank !== prevRank) {
          setRankChanged(newRank < prevRank ? 'up' : 'down');
          setTimeout(() => setRankChanged(null), 5000);
        }
        if (newRank) setPrevRank(newRank);
        setBattle(res.data);
      }
    } catch {}
  }, [rootStoryId, jobId, prevRank]);

  useEffect(() => { fetchBattle(); }, []);

  // Poll every 20s
  useEffect(() => {
    const iv = setInterval(fetchBattle, 20000);
    return () => clearInterval(iv);
  }, [fetchBattle]);

  if (!battle || !battle.user_rank) return null;

  const { user_rank, total_contenders, contenders } = battle;
  const topContender = contenders?.[0];
  const isWinning = user_rank === 1;

  // Compute gap to #1
  const userEntry = contenders?.find(c => c.user_id === battle.user_id);
  const topScore = topContender?.battle_score || 0;
  const userScore = userEntry?.battle_score || 0;
  const gapScore = Math.round(topScore - userScore);
  const topContinues = topContender?.total_children || 0;
  const userContinues = userEntry?.total_children || 0;
  const gapContinues = topContinues - userContinues;

  return (
    <div className={`rounded-xl border p-4 transition-all ${
      rankChanged === 'up' ? 'border-emerald-500/40 bg-emerald-500/10 animate-pulse' :
      rankChanged === 'down' ? 'border-rose-500/40 bg-rose-500/10 animate-pulse' :
      isWinning ? 'border-amber-500/20 bg-amber-500/[0.04]' :
      'border-rose-500/20 bg-rose-500/[0.04]'
    }`} data-testid="competition-pulse">

      {/* Rank Change Alert */}
      {rankChanged === 'up' && (
        <div className="flex items-center gap-2 mb-3 text-emerald-400" data-testid="rank-up-alert">
          <ChevronUp className="w-5 h-5" />
          <span className="text-sm font-bold">You moved up to #{user_rank}!</span>
        </div>
      )}
      {rankChanged === 'down' && (
        <div className="flex items-center gap-2 mb-3 text-rose-400" data-testid="rank-down-alert">
          <ChevronDown className="w-5 h-5" />
          <span className="text-sm font-bold">You dropped to #{user_rank} — someone just beat you</span>
        </div>
      )}

      {/* Winner State */}
      {isWinning ? (
        <div data-testid="winner-state">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <Crown className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <p className="text-lg font-black text-amber-400">YOU ARE #1</p>
              <p className="text-xs text-white/40">
                You beat {total_contenders - 1} creator{total_contenders > 2 ? 's' : ''}
              </p>
            </div>
          </div>
          <p className="text-xs text-amber-300/70 mb-3">
            This is now the top version. Share it to widen your lead.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate(`/app/story-battle/${rootStoryId || jobId}`)}
              className="flex-1 border-amber-500/20 text-amber-400 hover:bg-amber-500/10 text-xs"
              data-testid="pulse-view-battle"
            >
              <Swords className="w-3.5 h-3.5 mr-1" /> View Battle
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate(`/app/story-chain-timeline/${rootStoryId || jobId}`)}
              className="flex-1 border-white/10 text-white/50 hover:text-white text-xs"
              data-testid="pulse-view-chain"
            >
              <TrendingUp className="w-3.5 h-3.5 mr-1" /> View Chain
            </Button>
          </div>
        </div>
      ) : (
        /* Loser / Competitor State */
        <div data-testid="competitor-state">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-rose-500/20 flex items-center justify-center">
              <span className="text-xl font-black text-rose-400">#{user_rank}</span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-rose-300">
                Not enough. You're #{user_rank} of {total_contenders}.
              </p>
              <p className="text-xs text-white/40">
                Gap to #1: {gapScore > 0 ? `${gapScore} pts` : ''}{gapScore > 0 && gapContinues > 0 ? ', ' : ''}{gapContinues > 0 ? `${gapContinues} continues behind` : ''}
              </p>
            </div>
          </div>

          {/* #1 leader preview */}
          {topContender && (
            <div className="bg-black/20 rounded-lg p-2.5 mb-3 flex items-center gap-2">
              <Crown className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
              <span className="text-xs text-white/50 truncate">
                #1: "{topContender.title}" by {topContender.creator_name}
              </span>
              <span className="text-xs text-amber-400 font-bold flex-shrink-0 ml-auto">
                {topScore.toFixed(0)} pts
              </span>
            </div>
          )}

          <div className="flex gap-2">
            {onTryAgain && (
              <Button
                size="sm"
                onClick={onTryAgain}
                className="flex-1 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
                data-testid="pulse-try-again"
              >
                <GitBranch className="w-3.5 h-3.5 mr-1" /> Try Again
              </Button>
            )}
            {onBeatTop && (
              <Button
                size="sm"
                onClick={onBeatTop}
                className="flex-1 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold"
                data-testid="pulse-beat-top"
              >
                <Swords className="w-3.5 h-3.5 mr-1" /> Beat #1
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
