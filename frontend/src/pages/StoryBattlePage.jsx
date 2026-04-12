import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Trophy, GitBranch, Play, Eye, Share2,
  ChevronDown, ChevronUp, Crown, Swords, TrendingUp, ArrowRight,
  Plus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import ContinuationModal from '../components/ContinuationModal';
import StreakBadge from '../components/StreakBadge';

/**
 * StoryBattlePage — The destination for competitive notifications.
 * Shows side-by-side comparison of competing story branches ranked by battle_score.
 * Deep-linkable at /story-battle/:storyId
 */
export default function StoryBattlePage() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const [battle, setBattle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [continuationMode, setContinuationMode] = useState(null);

  useEffect(() => {
    if (!storyId) return;
    (async () => {
      try {
        const res = await api.get(`/api/stories/battle/${storyId}`);
        setBattle(res.data);
      } catch (err) {
        toast.error('Battle not found');
        navigate('/app/dashboard');
      } finally {
        setLoading(false);
      }
    })();
  }, [storyId, navigate]);

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

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-white/40 hover:text-white" data-testid="battle-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-bold text-white flex items-center gap-2">
              <Swords className="w-4 h-4 text-rose-400" /> Story Battle
            </h1>
            <p className="text-xs text-white/40">{total_contenders} competing versions</p>
          </div>
          <Button
            size="sm"
            onClick={() => setContinuationMode('branch')}
            className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
            data-testid="create-better-version-header-btn"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Create Better Version
          </Button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Streak Badge */}
        <StreakBadge compact />

        {/* Current #1 Highlight */}
        {topContender && (
          <div className="relative overflow-hidden rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-500/[0.06] to-orange-500/[0.04] p-6"
            data-testid="top-contender-card">
            <div className="absolute top-3 right-3">
              <div className="flex items-center gap-1 bg-amber-500/20 rounded-full px-2.5 py-1">
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs font-bold text-amber-400">#1</span>
              </div>
            </div>
            <h2 className="text-lg font-bold text-white mb-1" data-testid="top-contender-title">
              {topContender.title || 'Untitled'}
            </h2>
            <p className="text-xs text-white/40 mb-3">by {topContender.creator_name}</p>
            <div className="flex items-center gap-4 text-xs text-white/50">
              <span className="flex items-center gap-1">
                <Eye className="w-3.5 h-3.5" /> {topContender.total_views || 0} views
              </span>
              <span className="flex items-center gap-1">
                <Share2 className="w-3.5 h-3.5" /> {topContender.total_shares || 0} shares
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="w-3.5 h-3.5" /> {topContender.total_children || 0} continues
              </span>
              <span className="flex items-center gap-1 text-amber-400 font-semibold">
                <TrendingUp className="w-3.5 h-3.5" /> {(topContender.battle_score || 0).toFixed(1)} pts
              </span>
            </div>
            {topContender.is_original && (
              <span className="inline-block mt-2 text-[10px] bg-white/5 border border-white/10 rounded-full px-2 py-0.5 text-white/40">
                Original Story
              </span>
            )}
          </div>
        )}

        {/* User's Position */}
        {user_rank && (
          <div className={`rounded-xl p-4 border ${
            user_rank === 1
              ? 'bg-emerald-500/5 border-emerald-500/20'
              : 'bg-rose-500/5 border-rose-500/20'
          }`} data-testid="user-rank-card">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                user_rank === 1 ? 'bg-emerald-500/20' : 'bg-rose-500/20'
              }`}>
                {user_rank === 1
                  ? <Trophy className="w-5 h-5 text-emerald-400" />
                  : <span className="text-lg font-black text-rose-400">#{user_rank}</span>
                }
              </div>
              <div className="flex-1">
                <p className={`text-sm font-bold ${user_rank === 1 ? 'text-emerald-400' : 'text-rose-300'}`}>
                  {user_rank === 1 ? "You're #1!" : `You're ranked #${user_rank}`}
                </p>
                <p className="text-xs text-white/40">
                  {user_rank === 1
                    ? 'Your version is leading the competition'
                    : `${user_rank - 1} version${user_rank > 2 ? 's' : ''} ahead of you — can you take the top spot?`
                  }
                </p>
              </div>
              {user_rank > 1 && (
                <Button
                  size="sm"
                  onClick={() => setContinuationMode('branch')}
                  className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
                  data-testid="take-back-spot-btn"
                >
                  Take it back
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Full Leaderboard */}
        <div data-testid="battle-leaderboard">
          <h3 className="text-sm font-semibold text-white/60 mb-3 flex items-center gap-2">
            <Swords className="w-4 h-4" /> Battle Leaderboard
          </h3>
          <div className="space-y-2">
            {contenders.map((c, i) => (
              <ContenderCard
                key={c.job_id}
                contender={c}
                rank={c.rank}
                isCurrentUser={c.user_id === battle.user_id}
                onClick={() => {
                  // Navigate to the story's pipeline view
                  navigate(`/app/story-video-pipeline?projectId=${c.job_id}`);
                }}
              />
            ))}
          </div>
        </div>

        {/* CTA: Create Better Version */}
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/[0.04] p-6 text-center"
          data-testid="create-better-version-cta">
          <Swords className="w-8 h-8 text-rose-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-white mb-1">Think you can do better?</h3>
          <p className="text-xs text-white/40 mb-4">
            Create your own version and compete for the #1 spot.
            Views, shares, and continuations determine the winner.
          </p>
          <Button
            onClick={() => setContinuationMode('branch')}
            className="bg-rose-600 hover:bg-rose-700 text-white font-bold px-8"
            data-testid="create-better-version-btn"
          >
            <GitBranch className="w-4 h-4 mr-2" /> Create Better Version
          </Button>
        </div>
      </div>

      {/* ContinuationModal for branching */}
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
            toast.success('Your competing version is being created!');
            navigate(`/app/story-video-pipeline?projectId=${data.job_id}`);
          }
        }}
      />
    </div>
  );
}


function ContenderCard({ contender, rank, isCurrentUser, onClick }) {
  const rankColors = {
    1: 'border-amber-500/30 bg-amber-500/[0.04]',
    2: 'border-slate-400/20 bg-slate-400/[0.02]',
    3: 'border-orange-700/20 bg-orange-700/[0.02]',
  };

  const rankBadge = {
    1: { bg: 'bg-amber-500/20', text: 'text-amber-400', icon: Crown },
    2: { bg: 'bg-slate-400/20', text: 'text-slate-300', icon: null },
    3: { bg: 'bg-orange-700/20', text: 'text-orange-400', icon: null },
  };

  const badge = rankBadge[rank] || { bg: 'bg-white/5', text: 'text-white/40', icon: null };
  const RankIcon = badge.icon;

  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border p-4 flex items-center gap-4 transition-all hover:bg-white/[0.02] text-left ${
        rankColors[rank] || 'border-white/5 bg-white/[0.01]'
      } ${isCurrentUser ? 'ring-1 ring-violet-500/30' : ''}`}
      data-testid={`contender-card-${rank}`}
    >
      {/* Rank */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${badge.bg}`}>
        {RankIcon
          ? <RankIcon className={`w-4 h-4 ${badge.text}`} />
          : <span className={`text-sm font-black ${badge.text}`}>#{rank}</span>
        }
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">
          {contender.title || 'Untitled'}
          {isCurrentUser && <span className="text-violet-400 text-xs ml-2">(You)</span>}
        </p>
        <p className="text-xs text-white/30 truncate">
          by {contender.creator_name}
          {contender.is_original && ' · Original'}
        </p>
      </div>

      {/* Score */}
      <div className="text-right flex-shrink-0">
        <p className={`text-sm font-bold ${rank === 1 ? 'text-amber-400' : 'text-white/60'}`}>
          {(contender.battle_score || 0).toFixed(1)}
        </p>
        <p className="text-[10px] text-white/30">pts</p>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-3 text-[10px] text-white/30 flex-shrink-0">
        <span>{contender.total_views || 0} views</span>
        <span>{contender.total_children || 0} cont.</span>
      </div>

      <ArrowRight className="w-4 h-4 text-white/20 flex-shrink-0" />
    </button>
  );
}
