import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, ArrowRight, Flame, Film } from 'lucide-react';
import axios from 'axios';
import { SafeImage } from './SafeImage';

const API = process.env.REACT_APP_BACKEND_URL;

export function ReturnBanner() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    (async () => {
      try {
        const res = await axios.get(`${API}/api/retention/return-banner`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.data.success && res.data.has_story) setData(res.data);
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (loading || !data) return null;

  const { story, cliffhanger, character_name, series_info } = data;

  const handleContinue = () => {
    localStorage.setItem('remix_data', JSON.stringify({
      prompt: story.title || '',
      timestamp: Date.now(),
      source_tool: 'return-banner',
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

  const headline = character_name
    ? `${character_name}'s story isn't over`
    : 'Your story isn\'t over';

  const subtitle = series_info
    ? `Episode ${series_info.episode_number} is waiting...`
    : cliffhanger || 'What happens next?';

  return (
    <div
      className="vs-fade-up-1 mb-6 relative overflow-hidden rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-600/[0.06] to-rose-600/[0.06] cursor-pointer group"
      onClick={handleContinue}
      data-testid="return-banner"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-violet-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative flex items-center gap-4 p-4 sm:p-5">
        {/* Thumbnail */}
        {story.thumbnail_url && (
          <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl overflow-hidden flex-shrink-0 border border-white/[0.08]">
            <SafeImage src={story.thumbnail_url} alt={story.title} className="w-full h-full object-cover" />
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <Flame className="w-4 h-4 text-amber-400" />
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Continue your story</span>
          </div>
          <h3 className="text-base sm:text-lg font-bold text-white truncate" data-testid="return-banner-headline">
            {headline}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1" data-testid="return-banner-subtitle">
            {subtitle}
          </p>
          {series_info && (
            <span className="inline-flex items-center gap-1 text-[10px] text-violet-400 font-semibold mt-1">
              <Film className="w-3 h-3" /> {series_info.title}
            </span>
          )}
        </div>

        {/* CTA */}
        <button
          onClick={(e) => { e.stopPropagation(); handleContinue(); }}
          className="flex-shrink-0 h-10 px-5 rounded-xl bg-gradient-to-r from-violet-600 to-rose-600 text-white text-sm font-bold flex items-center gap-2 hover:opacity-90 shadow-lg shadow-violet-500/20 transition-all"
          style={{ animation: 'cta-glow 2s ease-in-out infinite' }}
          data-testid="return-banner-continue-btn"
        >
          <Play className="w-4 h-4" /> Continue <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <style>{`
        @keyframes cta-glow {
          0%, 100% { box-shadow: 0 0 30px -8px rgba(139,92,246,0.4); }
          50% { box-shadow: 0 0 50px -5px rgba(139,92,246,0.6); }
        }
      `}</style>
    </div>
  );
}
