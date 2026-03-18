import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, ChevronRight, Sparkles, GitBranch, Play, Loader2, Film, Flame, Zap, AlertTriangle } from 'lucide-react';
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
      await Promise.all([
        api.get('/api/photo-to-comic/active-chains').then(r => setChains(r.data.chains || [])).catch(() => {}),
        api.get('/api/story-series/my-series').then(r => setSeries(r.data.series || [])).catch(() => {}),
      ]);
      setLoading(false);
    })();
  }, []);

  if (loading) return null;

  const validChains = chains.filter(c =>
    c.preview_url && c.preview_url !== '' &&
    !c.preview_url.includes('placehold.co') &&
    (c.preview_url.startsWith('http://') || c.preview_url.startsWith('https://'))
  );

  const hasContent = validChains.length > 0 || series.length > 0;
  if (!hasContent) return null;

  return (
    <div className="vs-fade-up-1 mb-8" data-testid="resume-your-story">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-[var(--vs-primary-from)]" />
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider" style={{ fontFamily: 'var(--vs-font-heading)' }}>
            Continue Creating
          </h2>
        </div>
        {series.length > 0 && (
          <Link to="/app/story-series" className="text-xs text-[var(--vs-text-accent)] hover:text-white transition-colors flex items-center gap-0.5">
            All Series <ChevronRight className="w-3 h-3" />
          </Link>
        )}
      </div>

      {/* Story Series — Compulsion-Driven Cards */}
      {series.length > 0 && (
        <div className="space-y-3 mb-3">
          {series.slice(0, 3).map((s) => (
            <SeriesCompulsionCard key={s.series_id} series={s} navigate={navigate} />
          ))}
        </div>
      )}

      {/* Photo-to-Comic Chains */}
      {validChains.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {validChains.slice(0, 4).map((c) => (
            <Link key={c.chain_id} to={`/app/story-chain/${c.chain_id}`}
              className="vs-card group p-3 flex items-center gap-3 hover:border-[var(--vs-border-glow)] transition-all"
              data-testid={`resume-chain-${c.chain_id}`}
            >
              <SafeImage src={c.preview_url} alt="" aspectRatio="1/1" titleOverlay={c.root_style} className="w-12 h-12 rounded-lg shrink-0" />
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

function SeriesCompulsionCard({ series: s, navigate }) {
  const nextEp = s.next_episode;
  const latestEp = s.latest_episode;
  const nextEpNum = nextEp ? nextEp.episode_number : (latestEp?.episode_number || 0) + 1;
  const hasUnresolved = s.open_loops_count > 0;
  const epsLeft = s.episodes_left || 0;

  // Build urgency line
  let urgencyLine = '';
  if (epsLeft > 0) {
    urgencyLine = `${epsLeft} episode${epsLeft !== 1 ? 's' : ''} unfinished`;
  }
  if (hasUnresolved) {
    urgencyLine += urgencyLine ? ' · ' : '';
    urgencyLine += `${s.open_loops_count} unresolved twist${s.open_loops_count !== 1 ? 's' : ''}`;
  }

  // Navigate to timeline with auto-focus on next episode
  const handleContinue = (e) => {
    e.stopPropagation();
    const focusEp = nextEp?.episode_id || '';
    navigate(`/app/story-series/${s.series_id}${focusEp ? `?focus=${focusEp}` : ''}`);
  };

  return (
    <div
      className="vs-card group cursor-pointer p-0 overflow-hidden hover:border-[var(--vs-border-glow)] transition-all"
      onClick={() => navigate(`/app/story-series/${s.series_id}`)}
      data-testid={`resume-series-${s.series_id}`}
    >
      <div className="p-4">
        {/* Top row: title + episode badge */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/15 flex items-center justify-center flex-shrink-0">
              {s.cover_asset_url ? (
                <img src={s.cover_asset_url} alt="" className="w-9 h-9 rounded-lg object-cover" />
              ) : (
                <BookOpen className="w-4 h-4 text-indigo-400" />
              )}
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-white truncate">{s.title}</h3>
              <p className="text-[10px] text-slate-500">{s.genre} &middot; {s.total_episodes || s.episode_count || 0} episodes</p>
            </div>
          </div>
          {nextEp && (
            <span className="text-[10px] font-bold bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded-full flex-shrink-0">
              Ep {nextEpNum} waiting
            </span>
          )}
        </div>

        {/* Compulsion hook */}
        {s.next_hook && (
          <p className="text-xs text-amber-400/90 italic mb-2 line-clamp-1 flex items-center gap-1.5">
            <Flame className="w-3 h-3 flex-shrink-0 text-amber-500" />
            {s.next_hook}
          </p>
        )}

        {/* Urgency line */}
        {urgencyLine && (
          <p className="text-[11px] text-rose-400/70 mb-3 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
            {urgencyLine}
          </p>
        )}

        {/* CTA hierarchy: primary = Continue Episode X, secondary = View Timeline */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleContinue}
            className="vs-btn-primary h-8 px-4 text-xs font-semibold"
            data-testid={`continue-ep-${s.series_id}`}
          >
            <Zap className="w-3.5 h-3.5 mr-1" />
            Continue Episode {nextEpNum}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => { e.stopPropagation(); navigate(`/app/story-series/${s.series_id}`); }}
            className="text-xs text-slate-400 hover:text-white h-8"
            data-testid={`view-timeline-${s.series_id}`}
          >
            View Timeline
          </Button>
        </div>
      </div>
    </div>
  );
}
