import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Play, GitBranch, Crown, ChevronDown, ChevronUp,
  Eye, Share2, TrendingUp, Swords, Plus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * StoryChainTimeline — Hybrid Timeline + Branch visualizer.
 * Main episodes = horizontal timeline (scrollable).
 * Branches = expand vertically on tap.
 * Route: /app/story-chain-timeline/:storyId
 */
export default function StoryChainTimeline() {
  const { storyId } = useParams();
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedNode, setExpandedNode] = useState(null);
  const timelineRef = useRef(null);

  useEffect(() => {
    if (!storyId) return;
    (async () => {
      try {
        const res = await api.get(`/api/stories/${storyId}/chain`);
        setChain(res.data);
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

  const toggleExpand = (jobId) => {
    setExpandedNode(prev => prev === jobId ? null : jobId);
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-white/40 hover:text-white" data-testid="chain-back-btn">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-sm font-bold text-white">Story Chain</h1>
            <p className="text-xs text-white/40">
              {chain_stats.total_episodes} episodes, {chain_stats.total_branches} branches, depth {chain_stats.max_depth}
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Chain Stats Summary */}
        <div className="flex items-center gap-4 text-xs" data-testid="chain-stats">
          <div className="flex items-center gap-1.5 bg-violet-500/10 border border-violet-500/20 rounded-lg px-3 py-2">
            <Play className="w-3.5 h-3.5 text-violet-400" />
            <span className="text-violet-300 font-semibold">{chain_stats.total_episodes} Episodes</span>
          </div>
          <div className="flex items-center gap-1.5 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
            <GitBranch className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-rose-300 font-semibold">{chain_stats.total_branches} Branches</span>
          </div>
          <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
            <TrendingUp className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-amber-300 font-semibold">Depth {chain_stats.max_depth}</span>
          </div>
        </div>

        {/* Timeline: Horizontal scroll of episodes */}
        <div>
          <h3 className="text-xs font-bold text-white/40 uppercase tracking-wider mb-3">Main Timeline</h3>
          <div
            ref={timelineRef}
            className="flex gap-3 overflow-x-auto pb-3 scrollbar-thin scrollbar-thumb-white/10"
            data-testid="episode-timeline"
          >
            {episodes.map((ep, i) => {
              const branches = branch_map[ep.job_id] || [];
              const hasBranches = branches.length > 0;
              const isExpanded = expandedNode === ep.job_id;

              return (
                <div key={ep.job_id} className="flex-shrink-0 relative" style={{ minWidth: 200 }}>
                  {/* Connector line */}
                  {i > 0 && (
                    <div className="absolute -left-3 top-1/2 w-3 h-px bg-violet-500/30" />
                  )}

                  {/* Episode Node */}
                  <button
                    onClick={() => hasBranches ? toggleExpand(ep.job_id) : navigate(`/app/story-video-pipeline?projectId=${ep.job_id}`)}
                    className={`w-full rounded-xl border p-4 text-left transition-all hover:bg-white/[0.03] ${
                      isExpanded
                        ? 'border-violet-500/40 bg-violet-500/[0.06]'
                        : 'border-white/10 bg-white/[0.02]'
                    }`}
                    data-testid={`episode-node-${i}`}
                  >
                    {/* Episode badge */}
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-violet-400 bg-violet-500/10 rounded-full px-2 py-0.5">
                        {ep.continuation_type === 'original' ? 'Origin' : `Ep ${ep.chain_depth || i}`}
                      </span>
                      {hasBranches && (
                        <span className="flex items-center gap-1 text-[10px] text-rose-400">
                          <GitBranch className="w-3 h-3" /> {branches.length}
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <p className="text-sm font-semibold text-white truncate mb-1">
                      {ep.title || 'Untitled'}
                    </p>

                    {/* Metrics */}
                    <div className="flex items-center gap-2 text-[10px] text-white/30">
                      <span>{ep.total_views || 0} views</span>
                      <span>{ep.total_children || 0} continues</span>
                      {(ep.battle_score || 0) > 0 && (
                        <span className="text-amber-400 font-semibold">{(ep.battle_score || 0).toFixed(1)} pts</span>
                      )}
                    </div>
                  </button>

                  {/* Expanded Branches (vertical) */}
                  {isExpanded && hasBranches && (
                    <div className="mt-2 ml-4 pl-4 border-l-2 border-rose-500/20 space-y-2 animate-in slide-in-from-top-2"
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
                          <div className="flex items-center gap-2 text-[10px] text-white/30 mt-1">
                            <span>{br.total_views || 0} views</span>
                            <span>{br.total_shares || 0} shares</span>
                          </div>
                        </button>
                      ))}

                      {/* Open Battle */}
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

        {/* Quick Battle Link */}
        {chain_stats.total_branches > 0 && (
          <Button
            onClick={() => navigate(`/app/story-battle/${root_story_id}`)}
            variant="outline"
            className="w-full border-rose-500/20 text-rose-400 hover:bg-rose-500/10"
            data-testid="view-all-battles-btn"
          >
            <Swords className="w-4 h-4 mr-2" /> View All Battles ({chain_stats.total_branches} competing versions)
          </Button>
        )}
      </div>
    </div>
  );
}
