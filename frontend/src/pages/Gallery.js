import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Film, Clock, ArrowRight, Clapperboard, Play, RefreshCcw, Trophy,
  SlidersHorizontal, Sparkles, Download, Eye, Crown, Flame, ChevronRight,
  Star, Zap
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Gallery() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [previewVideo, setPreviewVideo] = useState(null);
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
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/signup?redirect=/app/story-video-studio&remix=true');
      return;
    }
    // Track remix via new API
    try {
      axios.post(`${API_URL}/api/remix/track`, {
        source_tool: 'gallery',
        target_tool: 'story-video-studio',
        original_prompt: video.story_text || video.title || '',
        variation_type: 'gallery_remix',
        variation_label: 'Gallery Remix',
        original_generation_id: video.job_id,
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch {}

    // Store in localStorage for reliable cross-page data passing
    const remixData = {
      prompt: video.story_text || video.title || '',
      remixFrom: {
        tool: 'gallery',
        prompt: video.story_text || video.title,
        title: video.title,
        settings: {
          animation_style: video.animation_style,
          age_group: video.age_group,
          voice_preset: video.voice_preset,
        },
        parentId: video.job_id,
      }
    };
    localStorage.setItem('remix_data', JSON.stringify(remixData));

    navigate('/app/story-video-studio', { state: remixData });
    toast.success(`Remixing "${video.title}"...`);
  };

  const handlePreview = (video) => {
    // If video has output_url, play it in modal
    // Otherwise, navigate to story preview page for rich experience
    if (video.output_url) {
      setPreviewVideo(video);
    } else if (video.job_id) {
      navigate(`/app/story-preview/${video.job_id}`);
    } else {
      setPreviewVideo(video);
    }
  };

  const SORT_OPTIONS = [
    { id: 'newest', label: 'Newest', icon: Clock },
    { id: 'trending', label: 'Trending', icon: Flame },
    { id: 'most_remixed', label: 'Most Remixed', icon: RefreshCcw },
  ];

  const RANK_STYLES = [
    'text-amber-400 bg-amber-400/10 border-amber-400/30',
    'text-slate-300 bg-slate-300/10 border-slate-300/30',
    'text-orange-400 bg-orange-400/10 border-orange-400/30',
  ];

  return (
    <div className="min-h-screen bg-[#060B1A] text-white">
      {/* Nav */}
      <nav className="border-b border-white/[0.04] bg-[#060B1A]/90 backdrop-blur-2xl sticky top-0 z-50">
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

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="text-center mb-10">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-3">AI Video Gallery</p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-3 text-white" data-testid="gallery-heading">Made with Visionary Suite</h1>
          <p className="text-base text-slate-400 max-w-xl mx-auto">AI-generated story videos from our community. Remix any video to make it your own.</p>
        </div>

        {/* Most Remixed Leaderboard */}
        {leaderboard.length > 0 && (
          <div className="mb-10" data-testid="remix-leaderboard">
            <div className="flex items-center gap-2.5 mb-5">
              <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <Flame className="w-4 h-4 text-amber-400" />
              </div>
              <h2 className="text-base font-bold text-white">Most Remixed Creations</h2>
              <span className="text-[11px] text-amber-400/60 font-medium bg-amber-500/5 border border-amber-500/10 px-2 py-0.5 rounded-full">TOP {Math.min(leaderboard.length, 5)}</span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide" data-testid="leaderboard-carousel">
              {leaderboard.slice(0, 5).map((video, i) => (
                <div
                  key={video.job_id || i}
                  className={`flex-shrink-0 w-[260px] rounded-2xl overflow-hidden border transition-all hover:scale-[1.02] ${
                    i === 0
                      ? 'border-amber-500/30 bg-amber-500/[0.03] ring-1 ring-amber-500/10'
                      : 'border-white/[0.06] bg-white/[0.015]'
                  }`}
                  data-testid={`leaderboard-item-${i}`}
                >
                  <div className="aspect-video bg-black/50 relative group cursor-pointer" onClick={() => handlePreview(video)}>
                    {video.thumbnail_url ? (
                      <img src={video.thumbnail_url} alt={video.title} className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-indigo-900/40 to-purple-900/30">
                        <Play className="w-8 h-8 text-white/20" />
                      </div>
                    )}
                    {/* Rank badge */}
                    <div className={`absolute top-2 left-2 px-2 py-0.5 rounded-md text-[10px] font-black border ${RANK_STYLES[i] || 'text-slate-500 bg-slate-500/10 border-slate-500/20'}`}>
                      #{i + 1}
                    </div>
                    {/* Remix count */}
                    <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/70 backdrop-blur-sm text-pink-300 px-2 py-1 rounded-full text-[11px] font-semibold">
                      <RefreshCcw className="w-3 h-3" /> {video.remix_count || 0}
                    </div>
                    {/* Hover overlay */}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button onClick={(e) => { e.stopPropagation(); handlePreview(video); }} className="p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); handleRemix(video); }} className="p-2 rounded-full bg-pink-500/20 hover:bg-pink-500/40 text-pink-200 transition-colors">
                        <RefreshCcw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-medium text-white truncate">{video.title || 'Untitled'}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-[11px] text-slate-500">{video.animation_style || ''}</span>
                      <button
                        onClick={() => handleRemix(video)}
                        className="text-[11px] font-medium text-pink-400 hover:text-pink-300 flex items-center gap-1 transition-colors"
                        data-testid={`leaderboard-remix-${i}`}
                      >
                        Remix <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
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
          <div className="flex items-center gap-1.5" data-testid="sort-controls">
            <SlidersHorizontal className="w-4 h-4 text-slate-500" />
            {SORT_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              return (
                <button
                  key={opt.id}
                  onClick={() => setSortBy(opt.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1 ${
                    sortBy === opt.id
                      ? 'bg-white/[0.08] text-white'
                      : 'text-slate-500 hover:text-white'
                  }`}
                  data-testid={`sort-${opt.id}`}
                >
                  <Icon className="w-3 h-3" /> {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Video Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : videos.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="video-grid">
            {videos.map((video, i) => (
              <div key={video.job_id || i} className="group rounded-2xl overflow-hidden border border-white/[0.05] bg-white/[0.015] hover:border-white/[0.12] transition-all" data-testid={`gallery-card-${i}`}>
                <div className="aspect-video bg-black relative">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-full h-full object-cover cursor-pointer"
                      onClick={() => handlePreview(video)}
                      loading="lazy"
                    />
                  ) : (
                    <video
                      src={video.output_url}
                      className="w-full h-full object-cover"
                      preload="metadata"
                      muted
                    />
                  )}
                  {video.remix_count > 0 && (
                    <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/60 backdrop-blur-sm text-pink-300 px-2 py-1 rounded-full text-[11px] font-semibold">
                      <RefreshCcw className="w-3 h-3" /> {video.remix_count} remixes
                    </div>
                  )}
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                    <button
                      onClick={() => handlePreview(video)}
                      className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
                      data-testid={`preview-btn-${i}`}
                    >
                      <Eye className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleRemix(video)}
                      className="p-2.5 rounded-full bg-pink-500/20 hover:bg-pink-500/40 text-pink-200 transition-colors"
                      data-testid={`remix-btn-${i}`}
                    >
                      <RefreshCcw className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-white truncate">{video.title || 'AI Story Video'}</h3>
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1"><Film className="w-3 h-3" /> {video.animation_style || 'cartoon_2d'}</span>
                    {video.timing?.total_ms && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {Math.round(video.timing.total_ms / 1000)}s</span>}
                  </div>
                  <button
                    onClick={() => handleRemix(video)}
                    className="mt-3 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-pink-500/[0.06] border border-pink-500/15 text-pink-300 text-sm font-medium hover:bg-pink-500/[0.12] hover:border-pink-500/30 transition-all"
                    data-testid={`remix-card-btn-${i}`}
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

        {/* Contextual Upgrade CTA */}
        <div className="mt-12 rounded-2xl border border-indigo-500/15 bg-gradient-to-r from-indigo-500/[0.04] to-purple-500/[0.04] p-8 text-center" data-testid="gallery-upgrade-cta">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-bold text-white">Create videos like these</h3>
          </div>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-5">Generate AI story videos, comics, GIFs, reels and more. Remix any creation to make it uniquely yours.</p>
          <div className="flex items-center justify-center gap-3">
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-6 py-2.5 text-sm font-semibold" data-testid="gallery-bottom-cta">
                Start Creating <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </Link>
            <Link to="/pricing">
              <Button variant="outline" className="rounded-full px-6 py-2.5 text-sm font-semibold border-white/10 text-slate-300 hover:bg-white/5" data-testid="gallery-pricing-cta">
                <Crown className="w-3.5 h-3.5 mr-1.5" /> View Plans
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Video Preview Modal */}
      {previewVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={() => setPreviewVideo(null)} data-testid="video-preview-modal">
          <div className="relative w-full max-w-3xl mx-4 rounded-2xl overflow-hidden border border-white/[0.08] bg-[#0B1220]" onClick={(e) => e.stopPropagation()}>
            <div className="aspect-video bg-black">
              {previewVideo.output_url ? (
                <video
                  src={previewVideo.output_url}
                  className="w-full h-full object-contain"
                  controls
                  autoPlay
                />
              ) : previewVideo.thumbnail_url ? (
                <div className="relative w-full h-full">
                  <img src={previewVideo.thumbnail_url} alt={previewVideo.title} className="w-full h-full object-contain" />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                    <span className="px-4 py-2 bg-indigo-600/80 backdrop-blur-sm rounded-full text-white text-sm font-medium">
                      Story Preview
                    </span>
                  </div>
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-500">
                  <Film className="w-12 h-12 opacity-30" />
                </div>
              )}
            </div>
            <div className="p-5">
              <h3 className="text-lg font-semibold text-white mb-2">{previewVideo.title || 'AI Story Video'}</h3>
              <div className="flex items-center gap-3 text-xs text-slate-500 mb-4">
                <span className="flex items-center gap-1"><Film className="w-3 h-3" /> {previewVideo.animation_style}</span>
                {previewVideo.remix_count > 0 && (
                  <span className="flex items-center gap-1 text-pink-400"><RefreshCcw className="w-3 h-3" /> {previewVideo.remix_count} remixes</span>
                )}
              </div>
              <div className="flex gap-2">
                <Button onClick={() => handleRemix(previewVideo)} className="flex-1 bg-pink-500/10 hover:bg-pink-500/20 border border-pink-500/20 text-pink-300 rounded-xl" data-testid="modal-remix-btn">
                  <RefreshCcw className="w-4 h-4 mr-2" /> Remix This Video
                </Button>
                <Button onClick={() => setPreviewVideo(null)} variant="outline" className="rounded-xl text-slate-400 border-white/10" data-testid="modal-close-btn">
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
