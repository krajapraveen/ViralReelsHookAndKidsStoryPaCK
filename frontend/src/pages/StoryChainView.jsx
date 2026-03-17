import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, BookOpen, RefreshCw, Sparkles, Loader2,
  ChevronRight, Coins, Palette, GitBranch, Play,
  Lightbulb, ArrowUpRight, Zap, TrendingUp, Layers
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

export default function StoryChainView() {
  const { chainId } = useParams();
  const navigate = useNavigate();
  const [chain, setChain] = useState(null);
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState(null);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  useEffect(() => {
    if (!chainId) return;
    (async () => {
      try {
        const res = await api.get(`/api/photo-to-comic/chain/${chainId}`);
        setChain(res.data);
      } catch {
        toast.error('Chain not found');
        navigate('/app/my-stories');
      } finally {
        setLoading(false);
      }
    })();
  }, [chainId, navigate]);

  const fetchSuggestions = useCallback(async () => {
    if (!chainId || loadingSuggestions) return;
    setLoadingSuggestions(true);
    try {
      const res = await api.post('/api/photo-to-comic/chain/suggestions', { chain_id: chainId });
      setSuggestions(res.data);
      api.post('/api/metrics/track', { event: 'suggestion_view', chain_id: chainId }).catch(() => {});
    } catch {
      toast.error('Could not generate suggestions');
    } finally {
      setLoadingSuggestions(false);
    }
  }, [chainId, loadingSuggestions]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
      </div>
    );
  }

  if (!chain) return null;

  const {
    flat = [], total_episodes = 0, completed = 0, continuations = 0,
    remixes = 0, styles_used = [], progress_pct = 0, total_panels = 0,
    latest_continuable_job_id, latest_continuable_style
  } = chain;

  const SUGGESTION_ICONS = { escalation: TrendingUp, twist: Zap, deepening: Layers };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/app/my-stories">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white px-2">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-base font-bold text-white flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-indigo-400" /> Story Chain
              </h1>
              <p className="text-[10px] text-slate-500">
                {total_episodes} episode{total_episodes !== 1 ? 's' : ''} &middot; {continuations} continuation{continuations !== 1 ? 's' : ''} &middot; {remixes} remix{remixes !== 1 ? 'es' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {styles_used?.map(s => (
              <span key={s} className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">{s}</span>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6" data-testid="story-chain-view">
        {/* ── Progression Header ── */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5" data-testid="chain-progress-header">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono, monospace)' }}>
                  {total_episodes}
                </span>
                <span className="text-sm text-slate-400">episodes</span>
                <span className="text-slate-700">&middot;</span>
                <span className="text-2xl font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono, monospace)' }}>
                  {total_panels}
                </span>
                <span className="text-sm text-slate-400">panels</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400 transition-all duration-700"
                    style={{ width: `${progress_pct}%` }}
                    data-testid="chain-progress-bar"
                  />
                </div>
                <span className="text-sm font-semibold text-white shrink-0" style={{ fontFamily: 'var(--vs-font-mono, monospace)' }}>
                  {progress_pct}%
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1.5">{completed} of {total_episodes} completed</p>
              {/* Momentum messaging */}
              {(() => {
                const milestone = total_episodes < 5 ? 5 : total_episodes < 10 ? 10 : 25;
                const left = milestone - total_episodes;
                if (left > 0) return <p className="text-xs text-amber-400/80 mt-1 flex items-center gap-1" data-testid="momentum-msg"><TrendingUp className="w-3 h-3" /> {left} more episode{left !== 1 ? 's' : ''} to reach {milestone}-episode milestone</p>;
                return <p className="text-xs text-emerald-400/80 mt-1" data-testid="momentum-msg">Milestone reached! Keep building your series.</p>;
              })()}
            </div>

            {/* Next Episode CTA */}
            {latest_continuable_job_id && (
              <Button
                onClick={() => navigate(`/app/photo-to-comic?continue=${latest_continuable_job_id}`)}
                className="bg-indigo-600 hover:bg-indigo-700 h-11 px-6 text-sm font-semibold shrink-0"
                data-testid="next-episode-cta"
              >
                <Play className="w-4 h-4 mr-2" /> Next Episode
              </Button>
            )}
          </div>
        </div>

        {/* ── AI Suggestions Panel ── */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5" data-testid="ai-suggestions-panel">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-semibold text-white">Next Episode Ideas</h2>
            </div>
            {!suggestions && (
              <Button
                variant="outline" size="sm"
                onClick={fetchSuggestions}
                disabled={loadingSuggestions}
                className="border-slate-700 text-slate-300 hover:text-white h-7 px-3 text-xs"
                data-testid="generate-suggestions-btn"
              >
                {loadingSuggestions ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Sparkles className="w-3 h-3 mr-1" />}
                {loadingSuggestions ? 'Thinking...' : 'Get AI Ideas'}
              </Button>
            )}
            {suggestions && (
              <Button
                variant="ghost" size="sm"
                onClick={() => { setSuggestions(null); fetchSuggestions(); }}
                className="text-slate-500 hover:text-white h-7 px-2 text-xs"
                data-testid="refresh-suggestions-btn"
              >
                <RefreshCw className="w-3 h-3" />
              </Button>
            )}
          </div>

          {!suggestions && !loadingSuggestions && (
            <p className="text-xs text-slate-500">AI will analyze your story context, panels, and style to suggest compelling next directions.</p>
          )}

          {loadingSuggestions && !suggestions && (
            <div className="flex items-center gap-2 py-4 justify-center">
              <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
              <span className="text-sm text-slate-400">Analyzing your story...</span>
            </div>
          )}

          {suggestions?.suggestions && (
            <div className="grid sm:grid-cols-3 gap-3" data-testid="suggestions-grid">
              {suggestions.suggestions.map((s, i) => {
                const TypeIcon = SUGGESTION_ICONS[s.type] || Sparkles;
                const colors = {
                  escalation: 'border-red-500/30 hover:border-red-500/50',
                  twist: 'border-amber-500/30 hover:border-amber-500/50',
                  deepening: 'border-blue-500/30 hover:border-blue-500/50',
                };
                const iconColors = {
                  escalation: 'text-red-400 bg-red-500/10',
                  twist: 'text-amber-400 bg-amber-500/10',
                  deepening: 'text-blue-400 bg-blue-500/10',
                };
                return (
                  <button
                    key={i}
                    onClick={() => {
                      api.post('/api/metrics/track', { event: 'suggestion_click', chain_id: chainId, meta: { suggestion_type: s.type, index: i } }).catch(() => {});
                      if (latest_continuable_job_id) {
                        navigate(`/app/photo-to-comic?continue=${latest_continuable_job_id}`, {
                          state: { suggestedPrompt: s.prompt }
                        });
                      }
                    }}
                    className={`text-left rounded-xl border bg-slate-900/80 p-4 transition-all hover:bg-slate-800/80 group ${colors[s.type] || 'border-slate-700'}`}
                    data-testid={`suggestion-${i}`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-6 h-6 rounded-md flex items-center justify-center ${iconColors[s.type] || 'text-slate-400 bg-slate-800'}`}>
                        <TypeIcon className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-xs font-semibold text-white">{s.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed mb-2">{s.prompt}</p>
                    <p className="text-[10px] text-slate-500 italic">{s.hook}</p>
                    <div className="flex items-center gap-1 mt-2 text-[10px] text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      Use this direction <ArrowUpRight className="w-3 h-3" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Chain Timeline ── */}
        <div className="relative" data-testid="chain-timeline">
          {flat.map((job, idx) => {
            const isRoot = job.branch_type === 'original';
            const isContinuation = job.branch_type === 'continuation';
            const isRemix = job.branch_type === 'remix';
            const imageUrl = job.resultUrl || job.resultUrls?.[0] || job.panels?.[0]?.imageUrl;
            const isCompleted = job.status === 'COMPLETED' || job.status === 'PARTIAL_COMPLETE';

            return (
              <div key={job.id} className="relative flex gap-4 pb-6" data-testid={`chain-node-${idx}`}>
                {/* Timeline connector */}
                <div className="flex flex-col items-center shrink-0 w-8">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    isRoot ? 'bg-indigo-500/20 ring-2 ring-indigo-500'
                    : isContinuation ? 'bg-blue-500/20 ring-2 ring-blue-500'
                    : 'bg-pink-500/20 ring-2 ring-pink-500'
                  }`}>
                    {isRoot && <BookOpen className="w-3.5 h-3.5 text-indigo-400" />}
                    {isContinuation && <ChevronRight className="w-3.5 h-3.5 text-blue-400" />}
                    {isRemix && <RefreshCw className="w-3.5 h-3.5 text-pink-400" />}
                  </div>
                  {idx < flat.length - 1 && (
                    <div className="w-px flex-1 bg-slate-700 mt-1" />
                  )}
                </div>

                {/* Content card */}
                <div className={`flex-1 rounded-xl border overflow-hidden transition-all hover:border-slate-600 ${
                  isCompleted ? 'border-slate-700 bg-slate-900/80' : 'border-slate-800 bg-slate-900/40 opacity-70'
                }`}>
                  <div className="flex gap-4 p-4">
                    {/* Preview */}
                    {imageUrl ? (
                      <div className="w-24 h-24 rounded-lg overflow-hidden border border-slate-700 shrink-0 bg-slate-800">
                        <img src={imageUrl} alt={`Episode ${idx + 1}`} className="w-full h-full object-cover" crossOrigin="anonymous" />
                      </div>
                    ) : (
                      <div className="w-24 h-24 rounded-lg bg-slate-800 border border-slate-700 shrink-0 flex items-center justify-center">
                        <Loader2 className={`w-5 h-5 text-slate-600 ${!isCompleted ? 'animate-spin' : ''}`} />
                      </div>
                    )}

                    {/* Info */}
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          isRoot ? 'bg-indigo-500/20 text-indigo-400'
                          : isContinuation ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-pink-500/20 text-pink-400'
                        }`}>
                          {isRoot ? 'Origin' : isContinuation ? `Ep. ${job.sequence_number}` : 'Remix'}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          isCompleted ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'
                        }`}>
                          {job.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span className="flex items-center gap-1"><Palette className="w-3 h-3" /> {job.style}</span>
                        {job.panelCount && <span>{job.panelCount} panels</span>}
                        {job.cost && <span className="flex items-center gap-0.5"><Coins className="w-3 h-3" /> {job.cost}</span>}
                      </div>

                      {job.storyPrompt && (
                        <p className="text-xs text-slate-400 line-clamp-2">{job.storyPrompt}</p>
                      )}

                      {/* Panels inline */}
                      {job.panels?.length > 1 && (
                        <div className="flex gap-1 pt-1">
                          {job.panels.slice(0, 4).map((p, pi) => (
                            <div key={pi} className="w-12 h-12 rounded overflow-hidden border border-slate-700 shrink-0">
                              <img src={p.imageUrl} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
                            </div>
                          ))}
                          {job.panels.length > 4 && (
                            <div className="w-12 h-12 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] text-slate-500">
                              +{job.panels.length - 4}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Actions */}
                      {isCompleted && (
                        <div className="flex gap-2 pt-1.5">
                          {job.mode === 'strip' && (
                            <Button
                              size="sm" variant="outline"
                              onClick={() => navigate(`/app/photo-to-comic?continue=${job.id}`)}
                              className="h-6 text-[10px] border-blue-500/30 text-blue-400 hover:bg-blue-500/10 px-2"
                              data-testid={`continue-from-${idx}`}
                            >
                              <Sparkles className="w-3 h-3 mr-1" /> Continue
                            </Button>
                          )}
                          <Button
                            size="sm" variant="outline"
                            onClick={() => navigate(`/app/photo-to-comic?remix=${job.id}`)}
                            className="h-6 text-[10px] border-pink-500/30 text-pink-400 hover:bg-pink-500/10 px-2"
                            data-testid={`remix-from-${idx}`}
                          >
                            <RefreshCw className="w-3 h-3 mr-1" /> Remix
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Add Episode CTA at end of timeline */}
          {latest_continuable_job_id && (
            <div className="relative flex gap-4 pb-2" data-testid="add-episode-cta">
              <div className="flex flex-col items-center shrink-0 w-8">
                <div className="w-8 h-8 rounded-full flex items-center justify-center bg-indigo-500/10 ring-2 ring-dashed ring-indigo-500/40">
                  <Play className="w-3.5 h-3.5 text-indigo-400" />
                </div>
              </div>
              <button
                onClick={() => navigate(`/app/photo-to-comic?continue=${latest_continuable_job_id}`)}
                className="flex-1 rounded-xl border-2 border-dashed border-indigo-500/30 bg-indigo-500/5 p-4 flex items-center justify-center gap-2 hover:border-indigo-500/50 hover:bg-indigo-500/10 transition-all group"
              >
                <Sparkles className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-medium text-indigo-400">Add Next Episode</span>
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
