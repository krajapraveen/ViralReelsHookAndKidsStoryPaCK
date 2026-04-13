import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Trophy, Crown, TrendingUp, Swords, GitBranch, ChevronUp, ChevronDown,
  Zap, Loader2, AlertTriangle
} from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * CompetitionPulse — Live rank + gap-to-#1 + INSTANT re-run CTAs.
 * Polls every 20s. Shows after EVERY action.
 * The "Try Again Instantly" button fires a zero-friction re-run (no modal).
 */
export default function CompetitionPulse({ jobId, rootStoryId, onTryAgain, onBeatTop, onNewJobCreated }) {
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [prevRank, setPrevRank] = useState(null);
  const [rankChanged, setRankChanged] = useState(null);
  const [rerunning, setRerunning] = useState(null); // 'try_again' | 'beat_top' | null
  const [qualityWarning, setQualityWarning] = useState(null);
  const [sessionDepth, setSessionDepth] = useState(0);

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
  useEffect(() => {
    const iv = setInterval(fetchBattle, 20000);
    return () => clearInterval(iv);
  }, [fetchBattle]);

  // Instant re-run — zero friction
  const handleInstantRerun = async (mode) => {
    if (rerunning) return;
    setRerunning(mode);

    try {
      const res = await api.post('/api/stories/instant-rerun', {
        source_job_id: jobId,
        mode: mode,
      });

      if (res.data?.success) {
        setSessionDepth(d => d + 1);

        if (res.data.quality_warning) {
          setQualityWarning(res.data.quality_warning);
        }

        toast.success(
          mode === 'beat_top'
            ? 'Competitive version generating...'
            : 'New variation generating...'
        );

        // Navigate to the new job's pipeline
        if (onNewJobCreated) {
          onNewJobCreated(res.data);
        } else if (res.data.job_id) {
          navigate(`/app/story-video-studio?projectId=${res.data.job_id}`);
        }
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Re-run failed. Try again.';
      toast.error(detail);
    } finally {
      setRerunning(null);
    }
  };

  if (!battle || !battle.user_rank) return null;

  const { user_rank, total_contenders, contenders } = battle;
  const topContender = contenders?.[0];
  const isWinning = user_rank === 1;
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

      {/* Rank Change Alerts */}
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

      {/* Quality Warning (after 3+ reruns) */}
      {qualityWarning && (
        <div className="flex items-center gap-2 mb-3 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5"
          data-testid="quality-warning">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span className="text-xs text-amber-300">{qualityWarning}</span>
          {onTryAgain && (
            <button
              onClick={onTryAgain}
              className="text-xs text-amber-400 font-bold underline flex-shrink-0 ml-auto"
              data-testid="try-twist-instead"
            >
              Add Twist Instead
            </button>
          )}
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
          <div className="flex gap-2">
            <Button size="sm" variant="outline"
              onClick={() => navigate(`/app/story-battle/${rootStoryId || jobId}`)}
              className="flex-1 border-amber-500/20 text-amber-400 hover:bg-amber-500/10 text-xs"
              data-testid="pulse-view-battle">
              <Swords className="w-3.5 h-3.5 mr-1" /> View Battle
            </Button>
            <Button size="sm" variant="outline"
              onClick={() => navigate(`/app/story-chain-timeline/${rootStoryId || jobId}`)}
              className="flex-1 border-white/10 text-white/50 hover:text-white text-xs"
              data-testid="pulse-view-chain">
              <TrendingUp className="w-3.5 h-3.5 mr-1" /> View Chain
            </Button>
          </div>
        </div>
      ) : (
        /* Competitor State — THE INTENSITY LOOP */
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

          {/* INSTANT RE-RUN BUTTONS — zero friction */}
          <div className="flex gap-2" data-testid="instant-rerun-buttons">
            <Button
              size="sm"
              onClick={() => handleInstantRerun('try_again')}
              disabled={!!rerunning}
              className="flex-1 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
              data-testid="instant-try-again"
            >
              {rerunning === 'try_again' ? (
                <><Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> Generating...</>
              ) : (
                <><Zap className="w-3.5 h-3.5 mr-1" /> Try Again Instantly</>
              )}
            </Button>
            <Button
              size="sm"
              onClick={() => handleInstantRerun('beat_top')}
              disabled={!!rerunning}
              className="flex-1 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold"
              data-testid="instant-beat-top"
            >
              {rerunning === 'beat_top' ? (
                <><Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> Generating...</>
              ) : (
                <><Swords className="w-3.5 h-3.5 mr-1" /> Beat #1</>
              )}
            </Button>
          </div>

          {/* Session depth counter */}
          {sessionDepth > 0 && (
            <p className="text-[10px] text-white/20 text-center mt-2" data-testid="session-depth">
              {sessionDepth} rerun{sessionDepth > 1 ? 's' : ''} this session
            </p>
          )}
        </div>
      )}
    </div>
  );
}
