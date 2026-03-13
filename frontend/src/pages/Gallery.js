import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Film, Clock, ArrowRight, Clapperboard, Play, RefreshCcw, Trophy, SlidersHorizontal, Sparkles } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Gallery() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const navigate = useNavigate();

  const fetchVideos = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeCategory !== 'all') params.set('category', activeCategory);
      params.set('sort', sortBy);
      const res = await fetch(`${API_URL}/api/pipeline/gallery?${params}`);
      const d = await res.json();
      setVideos(d.videos || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [activeCategory, sortBy]);

  useEffect(() => { fetchVideos(); }, [fetchVideos]);

  useEffect(() => {
    fetch(`${API_URL}/api/pipeline/gallery/categories`)
      .then(r => r.json())
      .then(d => setCategories(d.categories || []))
      .catch(() => {});

    fetch(`${API_URL}/api/pipeline/gallery/leaderboard`)
      .then(r => r.json())
      .then(d => setLeaderboard(d.leaderboard || []))
      .catch(() => {});
  }, []);

  const handleRemix = (video) => {
    localStorage.setItem('remix_video', JSON.stringify({
      parent_video_id: video.job_id,
      title: video.title,
      story_text: video.story_text,
      animation_style: video.animation_style,
      age_group: video.age_group,
      voice_preset: video.voice_preset,
    }));
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/app/story-video-studio?remix=true');
    } else {
      navigate('/signup?redirect=/app/story-video-studio&remix=true');
    }
  };

  const SORT_OPTIONS = [
    { id: 'newest', label: 'Newest' },
    { id: 'most_remixed', label: 'Most Remixed' },
    { id: 'trending', label: 'Trending' },
  ];

  return (
    <div className="min-h-screen bg-[#06060b] text-white">
      {/* Nav */}
      <nav className="border-b border-white/[0.04] bg-[#06060b]/80 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Clapperboard className="w-6 h-6 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-sm text-slate-400 hover:text-white transition-colors">Home</Link>
            <Link to="/pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</Link>
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-5 py-2 text-sm font-semibold" data-testid="gallery-cta">
                Create Your Own
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">AI Video Gallery</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-white" data-testid="gallery-heading">Made with Visionary Suite</h1>
          <p className="text-lg text-slate-400 max-w-xl mx-auto">AI-generated story videos from our community. Remix any video to make it your own.</p>
        </div>

        {/* Leaderboard */}
        {leaderboard.length > 0 && (
          <div className="mb-12 bg-white/[0.02] border border-white/[0.06] rounded-2xl p-6" data-testid="remix-leaderboard">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="w-5 h-5 text-amber-400" />
              <h2 className="text-lg font-bold text-white">Most Remixed Videos</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {leaderboard.slice(0, 6).map((video, i) => (
                <div key={i} className="flex items-center gap-3 bg-white/[0.02] border border-white/[0.04] rounded-xl px-4 py-3 hover:border-amber-500/20 transition-all" data-testid={`leaderboard-item-${i}`}>
                  <span className={`text-lg font-black ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-orange-400' : 'text-slate-600'}`}>
                    #{i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{video.title || 'Untitled'}</p>
                    <p className="text-xs text-slate-500">{video.animation_style}</p>
                  </div>
                  <div className="flex items-center gap-1 text-pink-400">
                    <RefreshCcw className="w-3.5 h-3.5" />
                    <span className="text-sm font-semibold">{video.remix_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          {/* Categories */}
          <div className="flex-1 flex flex-wrap gap-2" data-testid="category-filters">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  activeCategory === cat.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white/[0.04] text-slate-400 hover:text-white hover:bg-white/[0.08] border border-white/[0.06]'
                }`}
                data-testid={`category-${cat.id}`}
              >
                {cat.name} <span className="text-xs opacity-60 ml-1">({cat.count})</span>
              </button>
            ))}
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2" data-testid="sort-controls">
            <SlidersHorizontal className="w-4 h-4 text-slate-500" />
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setSortBy(opt.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  sortBy === opt.id
                    ? 'bg-white/[0.08] text-white'
                    : 'text-slate-500 hover:text-white'
                }`}
                data-testid={`sort-${opt.id}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Video Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : videos.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="video-grid">
            {videos.map((video, i) => (
              <div key={i} className="group rounded-2xl overflow-hidden border border-white/[0.05] bg-white/[0.015] hover:border-white/[0.12] transition-all" data-testid={`gallery-card-${i}`}>
                <div className="aspect-video bg-black relative">
                  <video src={video.output_url} className="w-full h-full object-cover" preload="metadata" controls muted />
                  {video.remix_count > 0 && (
                    <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm text-pink-300 px-2 py-1 rounded-full text-xs font-medium">
                      <RefreshCcw className="w-3 h-3" /> {video.remix_count} remixes
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-white truncate">{video.title || 'AI Story Video'}</h3>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><Film className="w-3 h-3" /> {video.animation_style || 'cartoon_2d'}</span>
                    {video.timing?.total_ms && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {Math.round(video.timing.total_ms / 1000)}s</span>}
                  </div>
                  <button
                    onClick={() => handleRemix(video)}
                    className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-pink-500/[0.08] border border-pink-500/20 text-pink-300 text-sm font-medium hover:bg-pink-500/[0.15] hover:border-pink-500/40 transition-all"
                    data-testid={`remix-btn-${i}`}
                  >
                    <RefreshCcw className="w-3.5 h-3.5" />
                    Remix This Video
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 text-slate-500">
            <Play className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p>No videos found for this filter. Try another category.</p>
          </div>
        )}

        <div className="text-center mt-16">
          <Link to="/signup">
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-8 py-4 text-lg font-semibold" data-testid="gallery-bottom-cta">
              Create Your First Video <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
