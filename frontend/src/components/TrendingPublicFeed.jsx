import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Flame, Eye, GitBranch, Share2, ArrowRight, Play, TrendingUp } from 'lucide-react';
import api from '../utils/api';
import { trackFunnel } from '../utils/funnelTracker';

/**
 * TrendingPublicFeed — Shows public stories from ALL users with competition metrics.
 * NOT static cards. Shows continues, shares, "exploding" indicators.
 */
export default function TrendingPublicFeed() {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/stories/feed/discover?limit=8&sort_by=trending');
        if (res.data?.stories) setStories(res.data.stories);
      } catch {}
    })();
  }, []);

  if (stories.length === 0) return null;

  return (
    <div className="px-4 sm:px-6 lg:px-10 py-3" data-testid="trending-public-feed">
      <style>{`
        @keyframes kenburns{0%{transform:scale(1) translate(0,0)}50%{transform:scale(1.06) translate(-1%,-0.5%)}100%{transform:scale(1) translate(0,0)}}
        .kenburns-auto{animation:kenburns 10s ease-in-out infinite}
      `}</style>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Flame className="w-4 h-4 text-amber-400" /> Trending Now
        </h3>
        <button
          onClick={() => navigate('/app/discover')}
          className="text-xs text-white/40 hover:text-white flex items-center gap-1"
          data-testid="see-all-trending"
        >
          See all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stories.slice(0, 4).map((story, i) => (
          <TrendingCard key={story.job_id || i} story={story} index={i} navigate={navigate} />
        ))}
      </div>
    </div>
  );
}

function TrendingCard({ story, index, navigate }) {
  const isHot = (story.total_children || 0) >= 3 || (story.battle_score || 0) > 50;
  const competitors = story.total_children || 0;
  const views = story.total_views || 0;
  const preview = story.preview_media;
  const videoRef = useRef(null);
  const cardRef = useRef(null);
  const [previewPlaying, setPreviewPlaying] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);

  // Generate curiosity hook based on story context
  const hookText = isHot && competitors >= 3
    ? `${competitors} creators fighting for #1`
    : competitors >= 2
    ? 'Battle in progress'
    : views > 20
    ? `Blowing up — ${views > 100 ? `${views}` : views} watching`
    : null;

  // IntersectionObserver for autoplay + impression tracking
  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;

    let impressionTracked = false;

    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // Track impression once
          if (!impressionTracked) {
            impressionTracked = true;
            trackFunnel('feed_card_impression', {
              story_id: story.job_id,
              has_preview: preview?.autoplay_enabled || false,
            });
          }

          // Autoplay preview
          if (preview?.autoplay_enabled && preview?.preview_url && !previewFailed && entry.intersectionRatio > 0.6) {
            if (videoRef.current && !previewPlaying) {
              videoRef.current.src = preview.preview_url;
              videoRef.current.play()
                .then(() => {
                  setPreviewPlaying(true);
                  trackFunnel('preview_started', { story_id: story.job_id, has_preview: true });
                })
                .catch(() => {
                  setPreviewFailed(true);
                  trackFunnel('preview_failed', { story_id: story.job_id, has_preview: true });
                });
            }
          }
        } else {
          if (videoRef.current && previewPlaying) {
            videoRef.current.pause();
            setPreviewPlaying(false);
          }
        }
      },
      { threshold: [0.3, 0.6] }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [story.job_id, preview?.autoplay_enabled, preview?.preview_url, previewPlaying, previewFailed]);

  return (
    <button
      ref={cardRef}
      onClick={() => navigate(`/app/story-viewer/${story.job_id}`)}
      className="group rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden text-left hover:border-white/10 transition-all"
      data-testid={`trending-card-${index}`}
    >
      {/* Thumbnail / Video Preview */}
      <div className="aspect-video bg-gradient-to-br from-slate-800 to-slate-900 relative overflow-hidden">
        {/* Video preview layer (hidden until playing) */}
        {preview?.autoplay_enabled && !previewFailed && (
          <video
            ref={videoRef}
            muted
            playsInline
            loop
            preload="none"
            poster={preview.poster_url || story.thumbnail_url}
            className={`absolute inset-0 w-full h-full object-cover z-[1] transition-opacity duration-300 ${previewPlaying ? 'opacity-100' : 'opacity-0'}`}
            onError={() => {
              setPreviewFailed(true);
              trackFunnel('preview_failed', { story_id: story.job_id });
            }}
            onEnded={() => trackFunnel('preview_completed', { story_id: story.job_id })}
            onTimeUpdate={(e) => {
              // Track completion at first loop end (~2s)
              if (e.target.currentTime >= 1.9 && !e.target._completionTracked) {
                e.target._completionTracked = true;
                trackFunnel('preview_completed', { story_id: story.job_id, has_preview: true });
              }
            }}
            data-testid={`preview-video-${index}`}
          />
        )}

        {/* Poster/thumbnail layer (always visible as base) */}
        {(preview?.poster_url || story.thumbnail_url) ? (
          <img
            src={preview?.poster_url || story.thumbnail_url}
            alt=""
            loading="lazy"
            className="w-full h-full object-cover kenburns-auto group-hover:animation-none"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="absolute inset-0 bg-gradient-to-br from-violet-900/60 via-slate-800 to-rose-900/40" />
            <div className="relative z-[2] text-center px-3">
              <p className="text-white/80 font-bold text-sm line-clamp-2">{story.title || 'Untitled'}</p>
              {story.animation_style && (
                <p className="text-white/40 text-[10px] mt-1 uppercase tracking-wider">{story.animation_style.replace(/_/g, ' ')}</p>
              )}
            </div>
          </div>
        )}

        {/* Hook text overlay — first thing viewer sees */}
        {hookText && (
          <div className="absolute top-0 left-0 right-0 z-10 p-2" data-testid="card-hook-overlay">
            <span className="text-[10px] font-bold text-white bg-black/50 backdrop-blur-sm rounded px-2 py-1 inline-block">
              {hookText}
            </span>
          </div>
        )}

        {/* Hot badge */}
        {isHot && !hookText && (
          <div className="absolute top-2 left-2 flex items-center gap-1 bg-rose-500/80 backdrop-blur rounded-full px-2 py-0.5">
            <Flame className="w-2.5 h-2.5 text-white" />
            <span className="text-[9px] font-bold text-white">HOT</span>
          </div>
        )}

        {/* Live indicator for active battles */}
        {competitors > 0 && (
          <div className="absolute bottom-2 left-2 flex items-center gap-1 z-10">
            <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-[9px] font-semibold text-white/80 bg-black/40 backdrop-blur-sm rounded-full px-1.5 py-0.5">
              LIVE
            </span>
          </div>
        )}

        {/* Play overlay */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-8 h-8 rounded-full bg-white/15 backdrop-blur flex items-center justify-center">
            <Play className="w-3.5 h-3.5 text-white fill-white ml-0.5" />
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="p-2.5">
        <p className="text-xs font-semibold text-white line-clamp-1 mb-0.5">{story.title || 'Untitled'}</p>
        <p className="text-[10px] text-white/30 mb-1.5">by {story.creator_name || 'Anonymous'}</p>

        {/* Metrics row */}
        <div className="flex items-center gap-2 text-[10px] text-white/40">
          {(story.total_views || 0) > 0 && (
            <span className="flex items-center gap-0.5">
              <Eye className="w-2.5 h-2.5" /> {story.total_views}
            </span>
          )}
          {(story.total_children || 0) > 0 && (
            <span className="flex items-center gap-0.5">
              <GitBranch className="w-2.5 h-2.5" /> {story.total_children}
            </span>
          )}
          {(story.total_shares || 0) > 0 && (
            <span className="flex items-center gap-0.5">
              <Share2 className="w-2.5 h-2.5" /> {story.total_shares}
            </span>
          )}
          {(story.battle_score || 0) > 0 && (
            <span className="flex items-center gap-0.5 text-amber-400 font-semibold ml-auto">
              <TrendingUp className="w-2.5 h-2.5" /> {story.battle_score.toFixed(0)}
            </span>
          )}
        </div>

        {/* Attribution for derivatives */}
        {story.derivative_label && story.source_story_title && (
          <p className="text-[9px] text-violet-400/60 mt-1 truncate">
            {story.derivative_label === 'continued_from' ? 'Continued from' :
             story.derivative_label === 'remixed_from' ? 'Remixed from' : 'From'}{' '}
            {story.source_story_title}
          </p>
        )}
      </div>
    </button>
  );
}
