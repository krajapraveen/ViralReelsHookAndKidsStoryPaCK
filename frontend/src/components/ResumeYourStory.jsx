import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, ChevronRight, Sparkles, GitBranch, Play, Loader2, Film, Clock, Flame } from 'lucide-react';
import { Button } from './ui/button';
import { SafeImage } from './SafeImage';
import api from '../utils/api';

export function ResumeYourStory() {
  const navigate = useNavigate();
  const [chains, setChains] = useState([]);
  const [series, setSeries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const promises = [];
      promises.push(
        api.get('/api/photo-to-comic/active-chains').then(r => setChains(r.data.chains || [])).catch(() => {})
      );
      promises.push(
        api.get('/api/story-series/my-series').then(r => setSeries(r.data.series || [])).catch(() => {})
      );
      await Promise.all(promises);
      setLoading(false);
    })();
  }, []);

  if (loading) return null;

  const validChains = chains.filter(c =>
    c.preview_url &&
    c.preview_url !== '' &&
    !c.preview_url.includes('placehold.co') &&
    (c.preview_url.startsWith('http://') || c.preview_url.startsWith('https://'))
  );

  const hasContent = validChains.length > 0 || series.length > 0;
  if (!hasContent) return null;

  const primary = validChains[0];
  const restChains = validChains.slice(1, 3);

  return (
    <div className="vs-fade-up-1 mb-8" data-testid="resume-your-story">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-[var(--vs-primary-from)]" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            Resume Your Story
          </h2>
        </div>
        <Link to="/app/story-series" className="text-xs text-[var(--vs-text-accent)] hover:text-white transition-colors flex items-center gap-0.5">
          All Series <ChevronRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Story Series Cards */}
      {series.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
          {series.slice(0, 4).map((s) => (
            <button
              key={s.series_id}
              onClick={() => navigate(`/app/story-series/${s.series_id}`)}
              className="vs-card group text-left p-4 hover:border-[var(--vs-border-glow)] transition-all"
              data-testid={`resume-series-${s.series_id}`}
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-white truncate">{s.title}</h3>
                    <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-1.5 py-0.5 rounded-full flex-shrink-0">
                      Series
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--vs-text-muted)]">
                    <span className="flex items-center gap-1">
                      <Film className="w-3 h-3" />
                      {s.episode_count || 0} ep{(s.episode_count || 0) !== 1 ? 's' : ''}
                    </span>
                    <span>{s.genre}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(s.updated_at || s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {s.next_hook && (
                    <p className="mt-1.5 text-[11px] text-amber-400/80 italic line-clamp-1 flex items-center gap-1">
                      <Flame className="w-3 h-3 flex-shrink-0" /> {s.next_hook}
                    </p>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-[var(--vs-text-muted)] group-hover:text-white flex-shrink-0 mt-1" />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Photo-to-Comic Chains (existing) */}
      {primary && (
        <div
          className="vs-card group cursor-pointer p-0 overflow-hidden mb-3 hover:border-[var(--vs-border-glow)] transition-all"
          onClick={() => navigate(`/app/story-chain/${primary.chain_id}`)}
          data-testid="resume-primary-chain"
        >
          <div className="flex flex-col sm:flex-row">
            <div className="sm:w-48 relative shrink-0" style={{ aspectRatio: '4/3' }}>
              <SafeImage
                src={primary.preview_url}
                alt="Story chain preview"
                aspectRatio="4/3"
                titleOverlay={primary.root_style || 'Comic'}
                className="w-full h-full rounded-none"
              />
              <div className="absolute top-2 left-2">
                <span className="bg-black/60 backdrop-blur text-[10px] text-white font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
                  <GitBranch className="w-3 h-3" /> {primary.total_episodes} episode{primary.total_episodes !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
            <div className="flex-1 p-4 flex flex-col justify-between min-w-0">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                    {primary.root_style || 'comic'} &middot; {primary.root_genre || 'story'}
                  </span>
                </div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex-1 h-1.5 rounded-full bg-[var(--vs-bg-card)] overflow-hidden">
                    <div className="h-full rounded-full vs-gradient-bg transition-all duration-700" style={{ width: `${primary.progress_pct}%` }} />
                  </div>
                  <span className="text-xs text-[var(--vs-text-muted)] shrink-0" style={{ fontFamily: 'var(--vs-font-mono)' }}>{primary.progress_pct}%</span>
                </div>
                {primary.momentum_msg && (
                  <p className="text-xs text-amber-400/80 mb-1">{primary.momentum_msg}</p>
                )}
                <p className="text-xs text-[var(--vs-text-secondary)] line-clamp-1">
                  {primary.total_panels || 0} panels &middot; {primary.completed} of {primary.total_episodes} completed
                </p>
              </div>
              <div className="flex gap-2 mt-3">
                {primary.continue_job_id ? (
                  <Button size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/app/photo-to-comic?continue=${primary.continue_job_id}`); }} className="vs-btn-primary h-8 px-4 text-xs" data-testid="resume-continue-btn">
                    <Sparkles className="w-3.5 h-3.5 mr-1" /> Next Episode
                  </Button>
                ) : (
                  <Button size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/app/story-chain/${primary.chain_id}`); }} className="vs-btn-primary h-8 px-4 text-xs" data-testid="resume-view-chain-btn">
                    <BookOpen className="w-3.5 h-3.5 mr-1" /> View Chain
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {restChains.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {restChains.map((c) => (
            <Link key={c.chain_id} to={`/app/story-chain/${c.chain_id}`} className="vs-card group p-3 flex items-center gap-3 hover:border-[var(--vs-border-glow)] transition-all" data-testid={`resume-secondary-${c.chain_id}`}>
              <SafeImage src={c.preview_url} alt="" aspectRatio="1/1" titleOverlay={c.root_style} className="w-10 h-10 rounded-lg shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white font-medium truncate">{c.total_episodes} ep &middot; {c.root_style}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <div className="flex-1 h-1 rounded-full bg-[var(--vs-bg-card)] overflow-hidden">
                    <div className="h-full rounded-full vs-gradient-bg" style={{ width: `${c.progress_pct}%` }} />
                  </div>
                  <span className="text-[10px] text-[var(--vs-text-muted)]">{c.progress_pct}%</span>
                </div>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-[var(--vs-text-muted)] group-hover:text-white shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
