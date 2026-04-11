import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Play, GitBranch, Crown, ChevronDown, ChevronUp,
  Eye, Share2, TrendingUp, Swords, ArrowRight, Trophy
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';
import ContinuationModal from '../components/ContinuationModal';

/**
 * StoryChainTimeline — Competition-first story chain visualizer.
 *
 * ABOVE THE FOLD: Winner spotlight + user rank (Player mode) or social proof (Viewer mode)
 * BELOW THE FOLD: Episode timeline + expandable branches
 *
 * Route: /app/story-chain-timeline/:storyId
 */
export default function StoryChainTimeline() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [battle, setBattle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedNode, setExpandedNode] = useState(null);
  const [continuationMode, setContinuationMode] = useState(null);
  const timelineRef = useRef(null);

  useEffect(() => {
    if (!storyId) return;
    (async () => {
      try {
        const [chainRes, battleRes] = await Promise.all([
          api.get(`/api/stories/${storyId}/chain`),
          api.get(`/api/stories/battle/${storyId}`).catch(() => null),
        ]);
        setChain(chainRes.data);
        if (battleRes?.data) setBattle(battleRes.data);
      } catch {
        toast.error('Chain not found');
        navigate('/app/dashboard');
      } finally {
        setLoading(false);
      }
    })();
  }, [storyId, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center" data-testid="chain-loading">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (!chain) return null;

  const { episodes, branch_map, chain_stats, root_story_id } = chain;
  const contenders = battle?.contenders || [];
  const topContender = contenders[0];
  const userRank = battle?.user_rank;
  const isPlayer = !!userRank;
  const hasBranches = chain_stats.total_branches > 0;

  const toggleExpand = (jobId) => {
    setExpandedNode(prev => prev === jobId ? null : jobId);
  };

  // Find the parent job for pre-filled continuation
  const parentForContinuation = topContender || (episodes.length > 0 ? episodes[0] : null);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-white/40 hover:text-white" data-testid="chain-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-bold text-white">Story Chain</h1>
            <p className="text-xs text-white/40">
              {chain_stats.total_episodes} ep, {chain_stats.total_branches} branches
            </p>
          </div>
          {hasBranches && (
            <Button
              size="sm"
              onClick={() => setContinuationMode('branch')}
              className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold"
              data-testid="chain-beat-this-btn"
            >
              Beat This Version
            </Button>
          )}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">

        {/* ═══════════════════════════════════════════════════════
            ABOVE THE FOLD — Competition & Status FIRST
            ═══════════════════════════════════════════════════════ */}

        {/* PLAYER MODE: User has participated — show their rank + loss/win */}
        {isPlayer && (
          <div className={`rounded-2xl border p-5 ${
            userRank === 1
              ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-600/5'
              : 'border-rose-500/30 bg-gradient-to-br from-rose-500/10 to-rose-600/5'
          }`} data-testid="player-rank-card">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${
                userRank === 1 ? 'bg-emerald-500/20' : 'bg-rose-500/20'
              }`}>
                {userRank === 1
                  ? <Crown className="w-7 h-7 text-emerald-400" />
                  : <span className="text-2xl font-black text-rose-400">#{userRank}</span>
                }
              </div>
              <div className="flex-1">
                <p className={`text-lg font-black ${userRank === 1 ? 'text-emerald-400' : 'text-rose-300'}`}>
                  {userRank === 1 ? "You're #1!" : `You're ranked #${userRank}`}
                </p>
                <p className="text-xs text-white/40">
                  {userRank === 1
                    ? 'Your version is leading — keep the momentum'
                    : `${userRank - 1} version${userRank > 2 ? 's' : ''} ahead of you`
                  }
                </p>
              </div>
              {userRank > 1 && (
                <Button
                  onClick={() => setContinuationMode('branch')}
                  className="bg-rose-600 hover:bg-rose-700 text-white font-bold"
                  data-testid="take-back-rank-btn"
                >
                  Take Back Your Rank
                </Button>
              )}
            </div>
          </div>
        )}

        {/* TOP VERSION SPOTLIGHT — The thing everyone wants to beat */}
        {topContender && (
          <div className="relative overflow-hidden rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-500/[0.06] to-orange-500/[0.03] p-6"
            data-testid="winner-spotlight">
            <div className="absolute top-4 right-4">
              <div className="flex items-center gap-1 bg-amber-500/20 rounded-full px-2.5 py-1">
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-xs font-bold text-amber-400">#1 Version</span>
              </div>
            </div>

            <p className="text-[10px] font-bold text-amber-400/60 uppercase tracking-wider mb-1">
              {isPlayer ? 'Top Competing Version' : 'Trending — Top Version'}
            </p>
            <h2 className="text-xl font-black text-white mb-1" data-testid="winner-title">
              {topContender.title || 'Untitled'}
            </h2>
            <p className="text-xs text-white/40 mb-3">by {topContender.creator_name}</p>

            {/* Metrics */}
            <div className="flex items-center gap-4 text-xs text-white/50 mb-4">
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

            {/* CTA */}
            <div className="flex gap-3">
              <Button
                onClick={() => navigate(`/app/story-battle/${root_story_id}`)}
                variant="outline"
                className="border-amber-500/20 text-amber-400 hover:bg-amber-500/10"
                data-testid="view-battle-btn"
              >
                <Swords className="w-4 h-4 mr-2" /> View Battle
              </Button>
              <Button
                onClick={() => setContinuationMode('branch')}
                className="bg-rose-600 hover:bg-rose-700 text-white font-bold"
                data-testid="beat-this-version-btn"
              >
                <GitBranch className="w-4 h-4 mr-2" /> Beat This Version
              </Button>
            </div>
          </div>
        )}

        {/* VIEWER MODE: No participation yet — social proof + entry CTA */}
        {!isPlayer && hasBranches && (
          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 flex items-center gap-3"
            data-testid="viewer-cta">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center flex-shrink-0">
              <Swords className="w-5 h-5 text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">{contenders.length} versions competing</p>
              <p className="text-xs text-white/40">Think you can do better? Create your version.</p>
            </div>
            <Button
              size="sm"
              onClick={() => setContinuationMode('branch')}
              className="bg-violet-600 hover:bg-violet-700 text-white text-xs font-bold"
              data-testid="viewer-enter-btn"
            >
              Compete <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════
            BELOW THE FOLD — Structure (Timeline + Branches)
            ═══════════════════════════════════════════════════════ */}

        {/* Chain Stats */}
        <div className="flex items-center gap-3 text-xs pt-2" data-testid="chain-stats">
          <div className="flex items-center gap-1.5 bg-violet-500/10 border border-violet-500/20 rounded-lg px-2.5 py-1.5">
            <Play className="w-3 h-3 text-violet-400" />
            <span className="text-violet-300 font-semibold">{chain_stats.total_episodes} Episodes</span>
          </div>
          <div className="flex items-center gap-1.5 bg-rose-500/10 border border-rose-500/20 rounded-lg px-2.5 py-1.5">
            <GitBranch className="w-3 h-3 text-rose-400" />
            <span className="text-rose-300 font-semibold">{chain_stats.total_branches} Branches</span>
          </div>
          <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-1.5">
            <TrendingUp className="w-3 h-3 text-amber-400" />
            <span className="text-amber-300 font-semibold">Depth {chain_stats.max_depth}</span>
          </div>
        </div>

        {/* Timeline */}
        <div>
          <h3 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-3">Episode Timeline</h3>
          <div
            ref={timelineRef}
            className="flex gap-3 overflow-x-auto pb-3 scrollbar-thin scrollbar-thumb-white/10"
            data-testid="episode-timeline"
          >
            {episodes.map((ep, i) => {
              const branches = branch_map[ep.job_id] || [];
              const hasBr = branches.length > 0;
              const isExpanded = expandedNode === ep.job_id;

              return (
                <div key={ep.job_id} className="flex-shrink-0 relative" style={{ minWidth: 200 }}>
                  {i > 0 && <div className="absolute -left-3 top-1/2 w-3 h-px bg-violet-500/30" />}

                  <button
                    onClick={() => hasBr ? toggleExpand(ep.job_id) : navigate(`/app/story-video-pipeline?projectId=${ep.job_id}`)}
                    className={`w-full rounded-xl border p-4 text-left transition-all hover:bg-white/[0.03] ${
                      isExpanded ? 'border-violet-500/40 bg-violet-500/[0.06]' : 'border-white/10 bg-white/[0.02]'
                    }`}
                    data-testid={`episode-node-${i}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-violet-400 bg-violet-500/10 rounded-full px-2 py-0.5">
                        {ep.continuation_type === 'original' ? 'Origin' : `Ep ${ep.chain_depth || i}`}
                      </span>
                      {hasBr && (
                        <span className="flex items-center gap-1 text-[10px] text-rose-400">
                          <GitBranch className="w-3 h-3" /> {branches.length}
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-semibold text-white truncate mb-1">{ep.title || 'Untitled'}</p>
                    <div className="flex items-center gap-2 text-[10px] text-white/30">
                      <span>{ep.total_views || 0} views</span>
                      <span>{ep.total_children || 0} cont.</span>
                      {(ep.battle_score || 0) > 0 && (
                        <span className="text-amber-400 font-semibold">{(ep.battle_score || 0).toFixed(1)} pts</span>
                      )}
                    </div>
                  </button>

                  {isExpanded && hasBr && (
                    <div className="mt-2 ml-4 pl-4 border-l-2 border-rose-500/20 space-y-2"
                      data-testid={`branches-for-${ep.job_id}`}>
                      {branches.map((br, bi) => (
                        <button
                          key={br.job_id}
                          onClick={() => navigate(`/app/story-battle/${ep.job_id}`)}
                          className="w-full rounded-lg border border-rose-500/10 bg-rose-500/[0.02] p-3 text-left hover:bg-rose-500/[0.05] transition-all"
                          data-testid={`branch-node-${bi}`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="flex items-center gap-1">
                              {bi === 0 && <Crown className="w-3 h-3 text-amber-400" />}
                              <span className="text-[10px] font-bold text-rose-400">
                                Version {bi + 1} {bi === 0 ? '(Top)' : ''}
                              </span>
                            </span>
                            <span className="text-[10px] text-amber-400 font-semibold">
                              {(br.battle_score || 0).toFixed(1)} pts
                            </span>
                          </div>
                          <p className="text-xs font-medium text-white/80 truncate">{br.title || 'Untitled'}</p>
                        </button>
                      ))}
                      <button
                        onClick={() => navigate(`/app/story-battle/${ep.job_id}`)}
                        className="w-full rounded-lg border border-dashed border-rose-500/20 p-2.5 text-center hover:bg-rose-500/[0.03] transition-all"
                        data-testid="open-battle-btn"
                      >
                        <span className="text-xs font-semibold text-rose-400 flex items-center justify-center gap-1.5">
                          <Swords className="w-3.5 h-3.5" /> Open Battle
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Battle link */}
        {hasBranches && (
          <Button
            onClick={() => navigate(`/app/story-battle/${root_story_id}`)}
            variant="outline"
            className="w-full border-rose-500/20 text-rose-400 hover:bg-rose-500/10"
            data-testid="view-all-battles-btn"
          >
            <Swords className="w-4 h-4 mr-2" /> View All Battles ({chain_stats.total_branches} versions)
          </Button>
        )}
      </div>

      {/* Pre-filled Continuation Modal */}
      <ContinuationModal
        isOpen={!!continuationMode}
        onClose={() => setContinuationMode(null)}
        mode="branch"
        parentJob={{
          job_id: parentForContinuation?.job_id || root_story_id,
          title: parentForContinuation?.title || 'Story',
          story_text: parentForContinuation?.story_text || '',
          animation_style: parentForContinuation?.animation_style || 'cartoon_2d',
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
