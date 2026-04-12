import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Flame, Eye, GitBranch, Share2, ArrowRight, Play, TrendingUp } from 'lucide-react';
import api from '../utils/api';

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

  return (
    <button
      onClick={() => navigate(`/app/story-viewer/${story.job_id}`)}
      className="group rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden text-left hover:border-white/10 transition-all"
      data-testid={`trending-card-${index}`}
    >
      {/* Thumbnail / Gradient */}
      <div className="aspect-video bg-gradient-to-br from-slate-800 to-slate-900 relative overflow-hidden">
        {story.thumbnail_url ? (
          <img src={story.thumbnail_url} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-violet-600/20 to-rose-600/20" />
        )}
        {/* Hot badge */}
        {isHot && (
          <div className="absolute top-2 left-2 flex items-center gap-1 bg-rose-500/80 backdrop-blur rounded-full px-2 py-0.5">
            <Flame className="w-2.5 h-2.5 text-white" />
            <span className="text-[9px] font-bold text-white">HOT</span>
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
