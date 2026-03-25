import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Play, Lock, Check, ArrowRight, Film, BookOpen,
  Loader2, Command, Sparkles, Flame
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

export default function SeriesTimeline() {
  const { seriesId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (seriesId) fetchSeries();
  }, [seriesId]);

  const fetchSeries = async () => {
    try {
      const res = await api.get(`/api/universe/series/${seriesId}/episodes`);
      if (res.data.success) setData(res.data);
      else setError('Series not found');
    } catch {
      setError('Series not found');
    } finally {
      setLoading(false);
    }
  };

  const handleContinueEpisode = async () => {
    try {
      const res = await api.post(`/api/universe/series/${seriesId}/continue`);
      if (res.data.success) {
        localStorage.setItem('remix_data', JSON.stringify({
          prompt: res.data.prompt,
          timestamp: Date.now(),
          source_tool: 'series-continue',
          remixFrom: {
            tool: 'story-video-studio',
            prompt: res.data.prompt,
            title: `Episode ${res.data.next_episode_number}: ${res.data.series_title}`,
            settings: {},
            parentId: null,
          },
        }));
        navigate('/app/story-video-studio');
        toast.success(`Creating Episode ${res.data.next_episode_number}!`);
      }
    } catch {
      toast.error('Failed to load episode context');
    }
  };

  const watchEpisode = (ep) => {
    if (ep.locked) {
      toast.error('Complete the previous episode to unlock this one!');
      return;
    }
    if (ep.slug) {
      navigate(`/v/${ep.slug}`);
    } else if (ep.job_id) {
      navigate(`/app/story-video-studio?job=${ep.job_id}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex flex-col items-center justify-center gap-4">
        <p className="text-slate-400">{error || 'Series not found'}</p>
        <Link to="/app/story-series"><button className="px-5 py-2 bg-violet-600 text-white rounded-lg text-sm">Back to Series</button></Link>
      </div>
    );
  }

  const { series, episodes, next_episode_number } = data;
  const completedCount = episodes.filter(ep => ep.is_completed).length;
  const totalCount = episodes.length;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // Find the current episode for the cliffhanger
  const currentEpisode = episodes.find(ep => ep.is_current);
  const lastCompletedEpisode = [...episodes].reverse().find(ep => ep.is_completed);
  const cliffhangerText = lastCompletedEpisode?.cliffhanger_text || currentEpisode?.cliffhanger_text || '';

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="series-timeline">
      {/* HEADER */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-4 h-13 flex items-center justify-between py-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <Command className="w-3 h-3 text-white" />
            </div>
          </Link>
          <button onClick={handleContinueEpisode} className="px-4 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-rose-600 hover:opacity-90 rounded-lg flex items-center gap-1.5" data-testid="header-continue-btn">
            <Play className="w-3 h-3" /> Continue Episode {next_episode_number}
          </button>
        </div>
      </header>

      {/* SERIES HERO — Action first */}
      <section className="relative py-8 px-4">
        <div className="absolute top-0 left-1/4 w-[500px] h-[300px] bg-violet-600/[0.06] rounded-full blur-[150px] pointer-events-none" />
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="flex items-center justify-center gap-2 mb-3">
            <BookOpen className="w-4 h-4 text-violet-400" />
            <span className="text-[10px] font-bold text-violet-400 uppercase tracking-[0.2em]">Story Series</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-white mb-3" data-testid="series-title">{series.title}</h1>
          {series.description && <p className="text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed mb-4">{series.description}</p>}

          {/* Cliffhanger Preview — urgency */}
          {cliffhangerText && (
            <div className="max-w-lg mx-auto mb-5 px-5 py-3 rounded-xl bg-amber-500/[0.06] border border-amber-500/20" data-testid="cliffhanger-preview">
              <p className="text-sm text-amber-200 italic leading-relaxed">
                "{cliffhangerText.slice(0, 200)}{cliffhangerText.length > 200 ? '...' : ''}"
              </p>
            </div>
          )}

          {/* Progress Bar */}
          <div className="max-w-sm mx-auto mb-5" data-testid="progress-bar">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-400">Story Progress</span>
              <span className="text-white font-bold">{completedCount}/{totalCount} episodes</span>
            </div>
            <div className="h-2.5 rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-rose-500 transition-all duration-700"
                style={{ width: `${Math.max(progressPct, 4)}%` }}
              />
            </div>
          </div>

          {/* BIG Continue CTA */}
          <button
            onClick={handleContinueEpisode}
            className="group inline-flex items-center gap-3 h-13 px-8 rounded-2xl bg-gradient-to-r from-violet-600 to-rose-600 text-white font-bold text-base shadow-[0_0_50px_-10px_rgba(139,92,246,0.5)] hover:shadow-[0_0_70px_-10px_rgba(139,92,246,0.7)] hover:scale-[1.03] active:scale-[0.98] transition-all"
            data-testid="big-continue-btn"
          >
            <Flame className="w-5 h-5" />
            Continue Episode {next_episode_number}
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </section>

      {/* ═══ EPISODE TIMELINE ═══ */}
      <section className="pb-16 px-4" data-testid="episode-timeline">
        <div className="max-w-4xl mx-auto">
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-emerald-500/40 via-violet-500/30 to-slate-800" />

            <div className="space-y-3">
              {episodes.map((ep, idx) => {
                const isCompleted = ep.is_completed;
                const isCurrent = ep.is_current;
                const isLocked = ep.locked;

                return (
                  <div key={ep.episode_id || idx} className={`relative flex gap-4 ${isLocked ? 'opacity-40' : ''}`} data-testid={`episode-${idx}`}>
                    {/* Node */}
                    <div className="flex-shrink-0 w-12 flex flex-col items-center">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center z-10 transition-all ${
                        isCompleted ? 'bg-emerald-500/20 border-2 border-emerald-500/50' :
                        isCurrent ? 'bg-violet-500/20 border-2 border-violet-500/50 ring-4 ring-violet-500/10 shadow-[0_0_20px_-4px_rgba(139,92,246,0.4)]' :
                        'bg-slate-800/80 border-2 border-slate-700'
                      }`}>
                        {isCompleted ? <Check className="w-5 h-5 text-emerald-400" /> :
                         isCurrent ? <Flame className="w-5 h-5 text-violet-400 animate-pulse" /> :
                         isLocked ? <Lock className="w-5 h-5 text-slate-600" /> :
                         <span className="text-sm font-bold text-slate-500">{ep.episode_number}</span>}
                      </div>
                    </div>

                    {/* Card */}
                    <div className={`flex-1 rounded-2xl border p-4 transition-all ${
                      isCurrent ? 'bg-violet-500/[0.06] border-violet-500/30 hover:border-violet-500/50 shadow-[0_0_30px_-10px_rgba(139,92,246,0.2)]' :
                      isCompleted ? 'bg-white/[0.02] border-white/[0.06] hover:border-emerald-500/20' :
                      'bg-white/[0.01] border-white/[0.04]'
                    } ${!isLocked ? 'cursor-pointer' : ''}`} onClick={() => !isLocked && watchEpisode(ep)}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className={`text-[10px] font-bold uppercase tracking-wider ${
                              isCompleted ? 'text-emerald-400' : isCurrent ? 'text-violet-400' : 'text-slate-600'
                            }`}>
                              Episode {ep.episode_number}
                            </span>
                            {isCompleted && <span className="text-[10px] text-emerald-400/70">Completed</span>}
                            {isCurrent && (
                              <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full flex items-center gap-1 animate-pulse" data-testid={`current-badge-${idx}`}>
                                <Flame className="w-2.5 h-2.5" /> CONTINUE NOW
                              </span>
                            )}
                            {isLocked && <span className="text-[10px] text-slate-600 flex items-center gap-1"><Lock className="w-2.5 h-2.5" /> Locked</span>}
                          </div>
                          <h3 className="text-base font-bold text-white mb-1">{ep.title || `Episode ${ep.episode_number}`}</h3>
                          {/* Cliffhanger text on completed episodes */}
                          {ep.cliffhanger_text && isCompleted && (
                            <p className="text-xs text-slate-400 italic leading-relaxed">"...{ep.cliffhanger_text.slice(0, 120)}"</p>
                          )}
                          {isLocked && <p className="text-xs text-slate-600 italic">Complete Episode {ep.episode_number - 1} to unlock</p>}
                        </div>
                        {/* Action button */}
                        {!isLocked && (
                          <div className="flex-shrink-0">
                            {isCurrent ? (
                              <button onClick={(e) => { e.stopPropagation(); handleContinueEpisode(); }} className="h-9 px-5 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-xs font-bold flex items-center gap-1.5 hover:opacity-90 shadow-lg shadow-violet-500/20" data-testid={`continue-ep-${idx}`}>
                                <Play className="w-3.5 h-3.5" /> Continue <ArrowRight className="w-3 h-3" />
                              </button>
                            ) : isCompleted ? (
                              <button className="h-9 px-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-xs text-slate-400 flex items-center gap-1.5 hover:text-white transition-colors" data-testid={`watch-ep-${idx}`}>
                                <Play className="w-3 h-3" /> Watch
                              </button>
                            ) : null}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Next Episode CTA */}
              <div className="relative flex gap-4" data-testid="next-episode-cta">
                <div className="flex-shrink-0 w-12 flex flex-col items-center">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500/20 to-rose-500/20 border-2 border-dashed border-violet-500/30 flex items-center justify-center z-10">
                    <Sparkles className="w-5 h-5 text-violet-400" />
                  </div>
                </div>
                <div className="flex-1 rounded-2xl border border-dashed border-violet-500/20 bg-violet-500/[0.03] p-5">
                  <p className="text-xs text-slate-500 mb-1">What happens next is up to you</p>
                  <h3 className="text-base font-bold text-white mb-3">Episode {next_episode_number}</h3>
                  <button onClick={handleContinueEpisode} className="h-11 px-6 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-sm font-bold flex items-center gap-2 hover:opacity-90 shadow-lg shadow-violet-500/20" data-testid="create-next-episode">
                    <Play className="w-4 h-4" /> Create Episode {next_episode_number}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
