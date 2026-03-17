import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, ChevronRight, Sparkles, GitBranch, Play, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import api from '../utils/api';

export function ResumeYourStory() {
  const navigate = useNavigate();
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/photo-to-comic/active-chains');
        setChains(res.data.chains || []);
      } catch { /* noop */ }
      setLoading(false);
    })();
  }, []);

  if (loading) return null;
  if (!chains.length) return null;

  const primary = chains[0];
  const rest = chains.slice(1);

  return (
    <div className="vs-fade-up-1 mb-8" data-testid="resume-your-story">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-[var(--vs-primary-from)]" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            Resume Your Story
          </h2>
        </div>
        <Link to="/app/my-stories" className="text-xs text-[var(--vs-text-accent)] hover:text-white transition-colors flex items-center gap-0.5">
          All Stories <ChevronRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Primary chain — large card */}
      <div
        className="vs-card group cursor-pointer p-0 overflow-hidden mb-3 hover:border-[var(--vs-border-glow)] transition-all"
        onClick={() => navigate(`/app/story-chain/${primary.chain_id}`)}
        data-testid="resume-primary-chain"
      >
        <div className="flex flex-col sm:flex-row">
          {/* Preview image */}
          <div className="sm:w-48 h-32 sm:h-auto bg-[var(--vs-bg-elevated)] relative overflow-hidden shrink-0">
            {primary.preview_url ? (
              <img src={primary.preview_url} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <BookOpen className="w-8 h-8 text-[var(--vs-text-muted)]" />
              </div>
            )}
            <div className="absolute top-2 left-2">
              <span className="bg-black/60 backdrop-blur text-[10px] text-white font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
                <GitBranch className="w-3 h-3" /> {primary.total_episodes} episode{primary.total_episodes !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {/* Info + CTA */}
          <div className="flex-1 p-4 flex flex-col justify-between min-w-0">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                  {primary.root_style || 'comic'} &middot; {primary.root_genre || 'story'}
                </span>
                {primary.continuations > 0 && (
                  <span className="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded-full">
                    {primary.continuations} cont.
                  </span>
                )}
                {primary.remixes > 0 && (
                  <span className="text-[10px] bg-pink-500/10 text-pink-400 px-1.5 py-0.5 rounded-full">
                    {primary.remixes} remix
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-1.5 rounded-full bg-[var(--vs-bg-card)] overflow-hidden">
                  <div
                    className="h-full rounded-full vs-gradient-bg transition-all duration-700"
                    style={{ width: `${primary.progress_pct}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--vs-text-muted)] shrink-0" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                  {primary.progress_pct}%
                </span>
              </div>

              <p className="text-xs text-[var(--vs-text-secondary)] line-clamp-1">
                {primary.total_panels || 0} panels &middot; {primary.completed} of {primary.total_episodes} completed
              </p>
            </div>

            <div className="flex gap-2 mt-3">
              {primary.continue_job_id ? (
                <Button
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); navigate(`/app/photo-to-comic?continue=${primary.continue_job_id}`); }}
                  className="vs-btn-primary h-8 px-4 text-xs"
                  data-testid="resume-continue-btn"
                >
                  <Sparkles className="w-3.5 h-3.5 mr-1" /> Next Episode
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); navigate(`/app/story-chain/${primary.chain_id}`); }}
                  className="vs-btn-primary h-8 px-4 text-xs"
                  data-testid="resume-view-chain-btn"
                >
                  <BookOpen className="w-3.5 h-3.5 mr-1" /> View Chain
                </Button>
              )}
              <Button
                variant="ghost" size="sm"
                onClick={(e) => { e.stopPropagation(); navigate(`/app/story-chain/${primary.chain_id}`); }}
                className="text-[var(--vs-text-muted)] hover:text-white h-8 px-3 text-xs"
                data-testid="resume-timeline-btn"
              >
                Timeline <ChevronRight className="w-3 h-3 ml-0.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary chains — compact row */}
      {rest.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {rest.map((c) => (
            <Link
              key={c.chain_id}
              to={`/app/story-chain/${c.chain_id}`}
              className="vs-card group p-3 flex items-center gap-3 hover:border-[var(--vs-border-glow)] transition-all"
              data-testid={`resume-secondary-${c.chain_id}`}
            >
              <div className="w-10 h-10 rounded-lg bg-[var(--vs-bg-elevated)] overflow-hidden shrink-0">
                {c.preview_url ? (
                  <img src={c.preview_url} alt="" className="w-full h-full object-cover" crossOrigin="anonymous" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <BookOpen className="w-4 h-4 text-[var(--vs-text-muted)]" />
                  </div>
                )}
              </div>
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
