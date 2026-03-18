import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Loader2, Play, Sparkles, Flame, Zap,
  RotateCcw, ChevronDown, Film, Clock, CheckCircle,
  AlertCircle, Users, Globe, BookOpen, Eye, Download
} from 'lucide-react';
import api from '../utils/api';

const STATUS_CONFIG = {
  planned: { color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20', label: 'Planned', icon: Clock },
  generating: { color: 'text-amber-400 bg-amber-500/10 border-amber-500/20', label: 'Generating', icon: Loader2 },
  ready: { color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', label: 'Ready', icon: CheckCircle },
  failed: { color: 'text-red-400 bg-red-500/10 border-red-500/20', label: 'Failed', icon: AlertCircle },
};

const DIRECTION_ACTIONS = [
  { type: 'continue', label: 'Continue', icon: Play, desc: 'Pick up where we left off' },
  { type: 'twist', label: 'Plot Twist', icon: RotateCcw, desc: 'An unexpected turn' },
  { type: 'stakes', label: 'Raise Stakes', icon: Flame, desc: 'Make it more intense' },
];

export default function SeriesTimeline() {
  const { seriesId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [generating, setGenerating] = useState(null);
  const [polling, setPolling] = useState(null);
  const [expandedEp, setExpandedEp] = useState(null);

  const fetchSeries = useCallback(async () => {
    try {
      const res = await api.get(`/api/story-series/${seriesId}`);
      setData(res.data);
    } catch (err) {
      toast.error('Failed to load series');
      navigate('/app/story-series');
    } finally {
      setLoading(false);
    }
  }, [seriesId, navigate]);

  useEffect(() => { fetchSeries(); }, [fetchSeries]);

  // Poll for generating episodes
  useEffect(() => {
    if (!data?.episodes) return;
    const genEps = data.episodes.filter(e => e.status === 'generating');
    if (genEps.length === 0) {
      if (polling) { clearInterval(polling); setPolling(null); }
      return;
    }
    if (polling) return;
    const id = setInterval(async () => {
      for (const ep of genEps) {
        try {
          const res = await api.get(`/api/story-series/${seriesId}/episode/${ep.episode_id}/status`);
          if (res.data.status !== 'generating') {
            fetchSeries();
            clearInterval(id);
            setPolling(null);
            if (res.data.status === 'ready') toast.success(`Episode ready!`);
            if (res.data.status === 'failed') toast.error(`Episode generation failed`);
            break;
          }
        } catch {}
      }
    }, 5000);
    setPolling(id);
    return () => clearInterval(id);
  }, [data?.episodes, seriesId, polling, fetchSeries]);

  const fetchSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const res = await api.post(`/api/story-series/${seriesId}/suggestions`);
      setSuggestions(res.data.suggestions || []);
    } catch { toast.error('Failed to get suggestions'); }
    finally { setLoadingSuggestions(false); }
  };

  const handlePlanEpisode = async (directionType, customPrompt) => {
    setPlanning(true);
    try {
      const res = await api.post(`/api/story-series/${seriesId}/plan-episode`, {
        direction_type: directionType,
        custom_prompt: customPrompt || null,
      });
      if (res.data.success) {
        toast.success(`Episode ${res.data.episode_number} planned!`);
        await fetchSeries();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Planning failed');
    } finally {
      setPlanning(false);
    }
  };

  const handleGenerate = async (episodeId) => {
    setGenerating(episodeId);
    try {
      const res = await api.post(`/api/story-series/${seriesId}/generate-episode`, {
        episode_id: episodeId,
      });
      if (res.data.success) {
        toast.success('Generation started!');
        await fetchSeries();
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Generation failed';
      toast.error(msg);
    } finally {
      setGenerating(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!data?.series) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Series not found. <Link to="/app/story-series" className="text-indigo-400 ml-2 underline">Go back</Link>
      </div>
    );
  }

  const { series, episodes = [], character_bible, world_bible, story_memory } = data;
  const readyEps = episodes.filter(e => e.status === 'ready').length;
  const totalEps = episodes.length;
  const latestEp = episodes[episodes.length - 1];
  const hasGenerating = episodes.some(e => e.status === 'generating');

  return (
    <div className="min-h-screen bg-slate-950" data-testid="series-timeline-page">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/story-series" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-lg font-bold text-white" data-testid="series-title">{series.title}</h1>
                <p className="text-xs text-slate-500">{series.genre} &middot; {series.audience_type}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Film className="w-3.5 h-3.5" />
              <span data-testid="episode-progress">{readyEps}/{totalEps} episodes</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Left: Timeline (3 cols) */}
          <div className="lg:col-span-3 space-y-4">
            {/* Progress Bar */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4" data-testid="progress-zone">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-400">Series Progress</span>
                <span className="text-xs text-slate-500">{readyEps} of {totalEps} ready</span>
              </div>
              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                  style={{ width: totalEps > 0 ? `${(readyEps / totalEps) * 100}%` : '0%' }}
                />
              </div>
            </div>

            {/* Episode Timeline */}
            <div className="space-y-3" data-testid="episode-timeline">
              {episodes.map((ep, idx) => {
                const cfg = STATUS_CONFIG[ep.status] || STATUS_CONFIG.planned;
                const StatusIcon = cfg.icon;
                const isExpanded = expandedEp === ep.episode_id;

                return (
                  <div
                    key={ep.episode_id}
                    className={`bg-slate-900/60 border rounded-xl overflow-hidden transition-all ${
                      isExpanded ? 'border-indigo-500/40' : 'border-slate-800'
                    }`}
                    data-testid={`episode-card-${ep.episode_id}`}
                  >
                    <button
                      onClick={() => setExpandedEp(isExpanded ? null : ep.episode_id)}
                      className="w-full text-left p-4 flex items-center gap-4"
                    >
                      {/* Episode number */}
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 border ${cfg.color}`}>
                        {ep.episode_number}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <h3 className="text-sm font-semibold text-white truncate">{ep.title}</h3>
                          <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${cfg.color}`}>
                            <StatusIcon className={`w-3 h-3 ${ep.status === 'generating' ? 'animate-spin' : ''}`} />
                            {cfg.label}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 truncate">{ep.summary}</p>
                      </div>

                      {ep.thumbnail_url && (
                        <img
                          src={ep.thumbnail_url}
                          alt=""
                          className="w-16 h-10 rounded object-cover flex-shrink-0"
                        />
                      )}

                      <ChevronDown className={`w-4 h-4 text-slate-600 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-4 border-t border-slate-800/50 pt-3 space-y-3">
                        {ep.summary && (
                          <p className="text-sm text-slate-400">{ep.summary}</p>
                        )}
                        {ep.cliffhanger && (
                          <p className="text-xs text-amber-400/80 italic">Cliffhanger: "{ep.cliffhanger}"</p>
                        )}
                        <div className="flex items-center gap-2 text-xs text-slate-600">
                          <span>{ep.scene_count || 0} scenes</span>
                          <span>&middot;</span>
                          <span>{ep.branch_type}</span>
                        </div>

                        {/* Action buttons based on status */}
                        <div className="flex items-center gap-2 pt-1">
                          {ep.status === 'planned' && (
                            <Button
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); handleGenerate(ep.episode_id); }}
                              disabled={generating === ep.episode_id || hasGenerating}
                              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
                              data-testid={`generate-ep-${ep.episode_id}`}
                            >
                              {generating === ep.episode_id ? (
                                <Loader2 className="w-3 h-3 animate-spin mr-1" />
                              ) : (
                                <Zap className="w-3 h-3 mr-1" />
                              )}
                              Generate
                            </Button>
                          )}
                          {ep.status === 'ready' && ep.output_asset_url && (
                            <>
                              <a
                                href={ep.output_asset_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md"
                                data-testid={`view-ep-${ep.episode_id}`}
                              >
                                <Eye className="w-3 h-3" /> View
                              </a>
                              <a
                                href={ep.output_asset_url}
                                download
                                className="inline-flex items-center gap-1 text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-md"
                                data-testid={`download-ep-${ep.episode_id}`}
                              >
                                <Download className="w-3 h-3" /> Download
                              </a>
                            </>
                          )}
                          {ep.status === 'failed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => { e.stopPropagation(); handleGenerate(ep.episode_id); }}
                              className="border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs"
                              data-testid={`retry-ep-${ep.episode_id}`}
                            >
                              <RotateCcw className="w-3 h-3 mr-1" /> Retry
                            </Button>
                          )}
                          {ep.status === 'generating' && (
                            <span className="flex items-center gap-2 text-xs text-amber-400">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Generating... this may take a few minutes
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Sidebar (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Zone 2: Action Zone — "What happens next?" */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid="action-zone">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                What happens next?
              </h3>
              <div className="space-y-2">
                {DIRECTION_ACTIONS.map(action => {
                  const Icon = action.icon;
                  return (
                    <button
                      key={action.type}
                      onClick={() => handlePlanEpisode(action.type)}
                      disabled={planning || hasGenerating}
                      className="w-full flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 hover:border-indigo-500/30 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
                      data-testid={`action-${action.type}`}
                    >
                      <Icon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-white block">{action.label}</span>
                        <span className="text-xs text-slate-500">{action.desc}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
              {planning && (
                <div className="mt-3 flex items-center gap-2 text-xs text-indigo-400">
                  <Loader2 className="w-3 h-3 animate-spin" /> Planning next episode...
                </div>
              )}
            </div>

            {/* Zone 3: AI Suggestions */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5" data-testid="suggestions-zone">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  AI Suggestions
                </h3>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={fetchSuggestions}
                  disabled={loadingSuggestions}
                  className="text-xs text-slate-400 hover:text-white h-7"
                  data-testid="refresh-suggestions-btn"
                >
                  {loadingSuggestions ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Refresh'}
                </Button>
              </div>
              {suggestions.length > 0 ? (
                <div className="space-y-2">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handlePlanEpisode(s.direction_type, s.description)}
                      disabled={planning}
                      className="w-full text-left p-3 rounded-lg bg-slate-800/30 hover:bg-slate-800/60 border border-slate-700/30 hover:border-indigo-500/20 transition-all disabled:opacity-50"
                      data-testid={`suggestion-${i}`}
                    >
                      <span className="text-sm text-white font-medium block">{s.title}</span>
                      <span className="text-xs text-slate-500">{s.description}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-600 text-center py-4">
                  Click Refresh to get AI-powered story ideas
                </p>
              )}
            </div>

            {/* Zone 4: Series Info */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4" data-testid="series-info-zone">
              {character_bible?.characters?.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-slate-400 mb-2 flex items-center gap-1.5">
                    <Users className="w-3 h-3" /> Characters
                  </h4>
                  <div className="space-y-1.5">
                    {character_bible.characters.slice(0, 5).map((c, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-400 font-bold flex-shrink-0">
                          {(c.name || '?')[0]}
                        </div>
                        <div className="min-w-0">
                          <span className="text-xs text-white font-medium">{c.name}</span>
                          <span className="text-[10px] text-slate-500 ml-1.5">{c.role}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {world_bible?.world_name && (
                <div>
                  <h4 className="text-xs font-medium text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <Globe className="w-3 h-3" /> World
                  </h4>
                  <p className="text-xs text-slate-300">{world_bible.world_name}</p>
                  {world_bible.setting_description && (
                    <p className="text-[11px] text-slate-500 mt-1 line-clamp-3">{world_bible.setting_description}</p>
                  )}
                </div>
              )}

              {story_memory?.pending_hooks?.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <BookOpen className="w-3 h-3" /> Story Hooks
                  </h4>
                  <div className="space-y-1">
                    {story_memory.pending_hooks.slice(0, 3).map((h, i) => (
                      <p key={i} className="text-xs text-amber-400/70 italic">"{h}"</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
