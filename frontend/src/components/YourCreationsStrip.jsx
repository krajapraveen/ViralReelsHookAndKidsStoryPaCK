import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Crown, TrendingUp, Eye, GitBranch, ArrowRight, ChevronRight } from 'lucide-react';
import api from '../utils/api';

/**
 * YourCreationsStrip — Shows user's own stories with rank + engagement.
 * Not just a list — shows competitive position for each story.
 */
export default function YourCreationsStrip() {
  const navigate = useNavigate();
  const [stories, setStories] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/story-engine/user-jobs');
        if (res.data?.jobs) {
          setStories(res.data.jobs.filter(s =>
            ['READY', 'PARTIAL_READY', 'COMPLETED'].includes(s.state || s.status)
          ).slice(0, 4));
        }
      } catch {}
    })();
  }, []);

  if (stories.length === 0) return null;

  return (
    <div className="px-4 sm:px-6 lg:px-10 py-3" data-testid="your-creations-strip">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Crown className="w-4 h-4 text-violet-400" /> Your Creations
        </h3>
        <button
          onClick={() => navigate('/app/my-stories')}
          className="text-xs text-white/40 hover:text-white flex items-center gap-1"
          data-testid="see-all-creations"
        >
          See all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-2">
        {stories.map((story, i) => {
          const score = story.battle_score || 0;
          const views = story.total_views || 0;
          const children = story.total_children || 0;

          return (
            <button
              key={story.job_id || i}
              onClick={() => navigate(`/app/story-viewer/${story.job_id}`)}
              className="w-full rounded-xl border border-white/5 bg-white/[0.02] p-3 flex items-center gap-3 text-left hover:bg-white/[0.04] transition-all"
              data-testid={`your-creation-${i}`}
            >
              {/* Thumbnail */}
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500/20 to-rose-500/20 flex-shrink-0 overflow-hidden">
                {story.thumbnail_url ? (
                  <img src={story.thumbnail_url} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-[10px] font-bold text-white/30">{(story.title || '?')[0]}</span>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{story.title || 'Untitled'}</p>
                <div className="flex items-center gap-2 text-[10px] text-white/30 mt-0.5">
                  {views > 0 && <span className="flex items-center gap-0.5"><Eye className="w-2.5 h-2.5" /> {views}</span>}
                  {children > 0 && <span className="flex items-center gap-0.5"><GitBranch className="w-2.5 h-2.5" /> {children} continues</span>}
                </div>
              </div>

              {/* Score */}
              {score > 0 && (
                <div className="flex items-center gap-1 flex-shrink-0">
                  <TrendingUp className="w-3 h-3 text-amber-400" />
                  <span className="text-xs font-bold text-amber-400">{score.toFixed(0)}</span>
                </div>
              )}

              <ChevronRight className="w-4 h-4 text-white/15 flex-shrink-0" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
