import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Flame, Trophy, TrendingUp, ArrowRight, Play, Zap } from 'lucide-react';
import { SafeImage } from './SafeImage';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export function TrendingCompete() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get(`${API}/api/compete/trending`);
        if (res.data.success) setData(res.data);
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (loading || !data?.has_data) return null;

  const { top_story_today, most_continued, fastest_character, rising_stories } = data;
  const hasSpotlight = top_story_today || most_continued || fastest_character;

  if (!hasSpotlight && rising_stories.length === 0) return null;

  const continueStory = (story) => {
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: story.title || '',
      timestamp: Date.now(),
      source_tool: 'trending',
      remixFrom: {
        tool: 'story-video-studio',
        prompt: story.title,
        title: story.title,
        settings: { animation_style: story.animation_style },
        parentId: story.job_id,
      },
    }));
    navigate('/app/story-video-studio');
  };

  return (
    <div className="mb-8 vs-fade-up-2" data-testid="trending-compete-section">
      <div className="flex items-center gap-2 mb-4">
        <Flame className="w-5 h-5 text-orange-400" />
        <h2 className="text-base font-bold text-white tracking-tight" style={{ fontFamily: 'var(--vs-font-heading)' }}>
          Trending Now
        </h2>
      </div>

      {/* Spotlight Cards */}
      {hasSpotlight && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          {/* Top Story Today */}
          {top_story_today && (
            <div
              className="vs-card group p-0 overflow-hidden cursor-pointer relative"
              onClick={() => continueStory(top_story_today)}
              data-testid="top-story-card"
            >
              <span className="absolute top-2 left-2 z-10 text-[10px] font-black bg-gradient-to-r from-orange-500 to-red-500 text-white px-2.5 py-1 rounded-full shadow-lg shadow-orange-500/30" style={{ animation: 'badge-pulse 2s ease-in-out infinite' }}>
                #1 Trending
              </span>
              <SafeImage
                src={top_story_today.thumbnail_url}
                alt={top_story_today.title}
                aspectRatio="16/9"
                titleOverlay={top_story_today.title}
                fallbackType="gradient"
                className="rounded-b-none"
              />
              <div className="p-3">
                <h3 className="text-sm font-semibold text-white truncate">{top_story_today.title}</h3>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-orange-400 font-bold">{top_story_today.score} interactions today</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); continueStory(top_story_today); }}
                    className="h-6 px-3 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                    data-testid="top-story-continue"
                  >
                    <Play className="w-3 h-3" /> Continue
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Most Continued */}
          {most_continued && (
            <div
              className="vs-card group p-0 overflow-hidden cursor-pointer relative"
              onClick={() => continueStory(most_continued)}
              data-testid="most-continued-card"
            >
              <span className="absolute top-2 left-2 z-10 text-[10px] font-black bg-gradient-to-r from-violet-500 to-indigo-500 text-white px-2.5 py-1 rounded-full shadow-lg shadow-violet-500/30">
                Most Continued
              </span>
              <SafeImage
                src={most_continued.thumbnail_url}
                alt={most_continued.title}
                aspectRatio="16/9"
                titleOverlay={most_continued.title}
                fallbackType="gradient"
                className="rounded-b-none"
              />
              <div className="p-3">
                <h3 className="text-sm font-semibold text-white truncate">{most_continued.title}</h3>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-violet-400 font-bold">{most_continued.continuations} continuations</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); continueStory(most_continued); }}
                    className="h-6 px-3 rounded-lg bg-gradient-to-r from-violet-600 to-rose-600 text-white text-[10px] font-bold flex items-center gap-1 hover:opacity-90"
                    data-testid="most-continued-continue"
                  >
                    <Play className="w-3 h-3" /> Continue
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Fastest Growing Character */}
          {fastest_character && (
            <div className="vs-card p-4 flex flex-col justify-center" data-testid="fastest-character-card">
              <span className="text-[10px] font-black text-emerald-400 bg-emerald-500/10 self-start px-2.5 py-1 rounded-full mb-3">
                <Zap className="w-3 h-3 inline mr-0.5" /> Rising Fast
              </span>
              {fastest_character.thumbnail && (
                <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-emerald-500/30 mb-3">
                  <SafeImage src={fastest_character.thumbnail} alt={fastest_character.name} aspectRatio="1/1" />
                </div>
              )}
              <h3 className="text-sm font-bold text-white">{fastest_character.name}</h3>
              <p className="text-[11px] text-emerald-400/80 mt-1">{fastest_character.stories_24h} new stories in 24h</p>
            </div>
          )}
        </div>
      )}

      {/* Rising Stories */}
      {rising_stories.length > 0 && (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none">
          {rising_stories.map((story, i) => (
            <div
              key={story.job_id}
              className="vs-card group p-0 overflow-hidden cursor-pointer flex-shrink-0 w-[180px]"
              onClick={() => continueStory(story)}
              data-testid={`rising-story-${i}`}
            >
              <SafeImage
                src={story.thumbnail_url}
                alt={story.title}
                aspectRatio="16/9"
                titleOverlay={story.title}
                fallbackType="gradient"
                className="rounded-b-none"
              />
              <div className="p-2.5">
                <h4 className="text-xs font-medium text-white truncate">{story.title}</h4>
                <span className="text-[10px] text-slate-400">{story.score} interactions</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes badge-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
      `}</style>
    </div>
  );
}

/* Empty state for when no trending data exists */
export function TrendingEmptyState() {
  return (
    <div className="mb-6 text-center py-6 rounded-xl border border-dashed border-slate-700/50 bg-slate-900/30" data-testid="trending-empty">
      <Trophy className="w-8 h-8 text-slate-600 mx-auto mb-2" />
      <p className="text-sm text-slate-500 font-medium">Be the first to create a trending story</p>
      <Link to="/app/story-video-studio" className="text-xs text-violet-400 hover:text-violet-300 mt-1 inline-block">
        Start Creating <ArrowRight className="w-3 h-3 inline" />
      </Link>
    </div>
  );
}
