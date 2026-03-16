import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Film, Eye, RefreshCcw, Share2, Download, Play, ArrowLeft, Command, User, ChevronRight, ExternalLink } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PublicCreation() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [creation, setCreation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeScene, setActiveScene] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    fetchCreation();
  }, [slug]);

  const fetchCreation = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creation/${slug}`);
      setCreation(r.data.creation);
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creation not found' : 'Failed to load');
    }
    setLoading(false);
  };

  const handleRemix = () => {
    if (!creation) return;
    navigate('/app/story-video-studio', {
      state: {
        prompt: creation.story_text,
        remixFrom: creation.job_id,
        title: `Remix of ${creation.title}`,
      }
    });
  };

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: creation?.title, text: `Check out "${creation?.title}" — AI-generated video`, url });
      } catch {}
    } else {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard!');
    }
  };

  const playSceneAudio = (idx) => {
    setActiveScene(idx);
    const scene = creation?.scenes?.[idx];
    if (scene?.audio_url) {
      const audio = new Audio(scene.audio_url);
      audio.play().catch(() => {});
      setIsPlaying(true);
      audio.onended = () => setIsPlaying(false);
    }
  };

  if (loading) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-center">
          <Film className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <p className="text-[var(--vs-text-muted)]">Loading creation...</p>
        </div>
      </div>
    );
  }

  if (error || !creation) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="text-center" data-testid="creation-not-found">
          <Film className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <h2 className="vs-h2 mb-2">{error || 'Creation not found'}</h2>
          <Link to="/explore">
            <button className="vs-btn-primary mt-4">Explore Creations</button>
          </Link>
        </div>
      </div>
    );
  }

  const currentScene = creation.scenes?.[activeScene];

  return (
    <div className="vs-page min-h-screen" data-testid="public-creation-page">
      {/* Header */}
      <header className="vs-glass sticky top-0 z-40 border-b border-[var(--vs-border-subtle)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/explore" className="text-[var(--vs-text-muted)] hover:text-white"><ArrowLeft className="w-5 h-5" /></Link>
            <Link to="/" className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg vs-gradient-bg flex items-center justify-center">
                <Command className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-sm font-semibold text-white hidden sm:inline" style={{ fontFamily: 'var(--vs-font-heading)' }}>Visionary Suite</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleShare} className="vs-btn-secondary h-8 px-3 text-xs" data-testid="share-btn">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
            <button onClick={handleRemix} className="vs-btn-primary h-8 px-4 text-xs" data-testid="remix-btn">
              <RefreshCcw className="w-3.5 h-3.5" /> Remix This
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6 vs-fade-up-1">
            {/* Scene Viewer */}
            <div className="vs-panel overflow-hidden" data-testid="scene-viewer">
              <div className="relative w-full aspect-video bg-[var(--vs-bg-elevated)]">
                {currentScene?.image_url ? (
                  <img src={currentScene.image_url} alt={`Scene ${activeScene + 1}`} className="w-full h-full object-contain" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Film className="w-16 h-16 text-[var(--vs-text-muted)]" />
                  </div>
                )}
                {currentScene?.audio_url && (
                  <button
                    onClick={() => playSceneAudio(activeScene)}
                    className="absolute bottom-4 right-4 w-12 h-12 rounded-full bg-[var(--vs-cta)] hover:bg-[var(--vs-cta-hover)] flex items-center justify-center shadow-lg transition-all"
                    data-testid="play-scene-audio"
                  >
                    <Play className="w-5 h-5 text-white ml-0.5" />
                  </button>
                )}
              </div>

              {/* Scene navigation */}
              {creation.scenes?.length > 1 && (
                <div className="flex gap-2 p-3 overflow-x-auto" data-testid="scene-thumbnails">
                  {creation.scenes.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => setActiveScene(i)}
                      className={`flex-shrink-0 w-20 h-14 rounded-lg overflow-hidden border-2 transition-all ${
                        i === activeScene ? 'border-[var(--vs-primary-from)] ring-1 ring-[var(--vs-primary-from)]/30' : 'border-transparent opacity-60 hover:opacity-100'
                      }`}
                    >
                      {s.image_url ? (
                        <img src={s.image_url} alt={`Scene ${i + 1}`} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full bg-[var(--vs-bg-card)] flex items-center justify-center">
                          <span className="text-xs text-[var(--vs-text-muted)]">{i + 1}</span>
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Narration Text */}
            {currentScene?.narration && (
              <div className="vs-panel p-5">
                <p className="text-sm text-[var(--vs-text-secondary)] leading-relaxed italic" style={{ fontFamily: 'var(--vs-font-body)' }}>
                  "{currentScene.narration}"
                </p>
              </div>
            )}

            {/* Remix CTA */}
            <div className="vs-card bg-gradient-to-r from-[var(--vs-primary-from)]/10 to-[var(--vs-secondary-to)]/10 border-[var(--vs-border-glow)] text-center py-8" data-testid="remix-cta">
              <h3 className="vs-h3 mb-2">Make It Yours</h3>
              <p className="text-sm text-[var(--vs-text-secondary)] mb-4">Create your own version of this video with different styles, voices, or stories.</p>
              <button onClick={handleRemix} className="vs-btn-primary px-8 h-12 text-base">
                <RefreshCcw className="w-4 h-4" /> Remix This Creation
              </button>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-4 vs-fade-up-2">
            {/* Title & Meta */}
            <div className="vs-panel p-5" data-testid="creation-meta">
              <h1 className="vs-h2 mb-3" data-testid="creation-title">{creation.title}</h1>
              <div className="flex items-center gap-4 mb-4">
                <span className="flex items-center gap-1.5 text-sm text-[var(--vs-text-muted)]">
                  <Eye className="w-4 h-4" /> <span style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.views}</span> views
                </span>
                <span className="flex items-center gap-1.5 text-sm text-[var(--vs-text-muted)]">
                  <RefreshCcw className="w-4 h-4" /> <span style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.remix_count}</span> remixes
                </span>
              </div>
              <div className="flex items-center gap-3 py-3 border-t border-[var(--vs-border)]">
                <div className="w-8 h-8 rounded-full bg-[var(--vs-bg-card)] flex items-center justify-center">
                  <User className="w-4 h-4 text-[var(--vs-text-muted)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{creation.creator?.name || 'Anonymous'}</p>
                  <p className="text-xs text-[var(--vs-text-muted)]">Creator</p>
                </div>
              </div>
            </div>

            {/* Details */}
            <div className="vs-panel p-5 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--vs-text-muted)]">Style</span>
                <span className="text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.animation_style?.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--vs-text-muted)]">Scenes</span>
                <span className="text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creation.scenes?.length || 0}</span>
              </div>
              {creation.age_group && (
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--vs-text-muted)]">Age Group</span>
                  <span className="text-white">{creation.age_group}</span>
                </div>
              )}
              {creation.created_at && (
                <div className="flex justify-between text-sm">
                  <span className="text-[var(--vs-text-muted)]">Created</span>
                  <span className="text-white">{new Date(creation.created_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <button onClick={handleRemix} className="w-full vs-btn-primary h-11 text-sm" data-testid="sidebar-remix-btn">
                <RefreshCcw className="w-4 h-4" /> Remix This Video
              </button>
              <button onClick={handleShare} className="w-full vs-btn-secondary h-11 text-sm" data-testid="sidebar-share-btn">
                <Share2 className="w-4 h-4" /> Share
              </button>
              <Link to="/app/story-video-studio" className="block">
                <button className="w-full vs-btn-secondary h-11 text-sm">
                  Create Your Own <ChevronRight className="w-4 h-4" />
                </button>
              </Link>
            </div>

            {/* Branding */}
            <div className="text-center pt-4">
              <p className="text-xs text-[var(--vs-text-muted)]">Created with</p>
              <Link to="/" className="text-sm font-semibold vs-gradient-text" style={{ fontFamily: 'var(--vs-font-heading)' }}>
                Visionary Suite AI
              </Link>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
