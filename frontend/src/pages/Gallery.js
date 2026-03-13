import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Film, Clock, ArrowRight, Clapperboard, Play, RefreshCcw } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Gallery() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API_URL}/api/pipeline/gallery`)
      .then(r => r.json())
      .then(d => { setVideos(d.videos || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleRemix = (video) => {
    // Store remix data and navigate to studio
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

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Nav */}
      <nav className="border-b border-white/[0.06] bg-[#0a0a0f]/80 backdrop-blur-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Clapperboard className="w-6 h-6 text-indigo-400" />
            <span className="text-lg font-bold tracking-tight">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-sm text-slate-400 hover:text-white transition-colors">Home</Link>
            <Link to="/signup">
              <Button className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full px-5 py-2 text-sm font-semibold" data-testid="gallery-cta">
                Create Your Own
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-400 mb-4">AI Video Gallery</p>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-white">Made with Visionary Suite</h1>
          <p className="text-lg text-slate-300 max-w-xl mx-auto">Real AI-generated story videos created by our community. Every video was made from a simple text story.</p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : videos.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((video, i) => (
              <div key={i} className="group rounded-2xl overflow-hidden border border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] transition-all" data-testid={`gallery-card-${i}`}>
                <div className="aspect-video bg-black relative">
                  <video src={video.output_url} className="w-full h-full object-cover" preload="metadata" controls muted />
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-white truncate">{video.title || 'AI Story Video'}</h3>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><Film className="w-3 h-3" /> {video.animation_style || 'cartoon_2d'}</span>
                    {video.timing?.total_ms && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {Math.round(video.timing.total_ms / 1000)}s</span>}
                    {video.remix_count > 0 && <span className="flex items-center gap-1 text-pink-400"><RefreshCcw className="w-3 h-3" /> {video.remix_count}</span>}
                  </div>
                  {/* Remix Button */}
                  <button
                    onClick={() => handleRemix(video)}
                    className="mt-3 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-pink-500/10 border border-pink-500/20 text-pink-300 text-sm font-medium hover:bg-pink-500/20 hover:border-pink-500/40 transition-all"
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
            <p>No videos yet. Be the first to create one!</p>
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
