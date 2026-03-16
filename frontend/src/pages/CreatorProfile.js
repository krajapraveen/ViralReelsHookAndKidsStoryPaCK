import React, { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Film, Eye, RefreshCcw, User, Command, ArrowLeft, Play, Calendar } from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CreatorProfile() {
  const { username } = useParams();
  const [creator, setCreator] = useState(null);
  const [creations, setCreations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { fetchProfile(); }, [username]);

  const fetchProfile = async () => {
    try {
      const r = await axios.get(`${API}/api/public/creator/${username}`);
      setCreator(r.data.creator);
      setCreations(r.data.creations || []);
    } catch (e) {
      setError(e.response?.status === 404 ? 'Creator not found' : 'Failed to load profile');
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-center">
          <User className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <p className="text-[var(--vs-text-muted)]">Loading creator profile...</p>
        </div>
      </div>
    );
  }

  if (error || !creator) {
    return (
      <div className="vs-page min-h-screen flex items-center justify-center">
        <div className="text-center" data-testid="creator-not-found">
          <User className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-4" />
          <h2 className="vs-h2 mb-2">{error || 'Creator not found'}</h2>
          <Link to="/explore"><button className="vs-btn-primary mt-4">Explore Creations</button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="vs-page min-h-screen" data-testid="creator-profile-page">
      <Helmet>
        <title>{creator.name} — Creator on Visionary Suite</title>
        <meta name="description" content={`${creator.name} has created ${creator.total_creations} AI videos on Visionary Suite. ${creator.bio || ''}`} />
      </Helmet>

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
          <Link to="/app/story-video-studio"><button className="vs-btn-primary h-8 px-4 text-xs">Start Creating</button></Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {/* Creator Header */}
        <div className="vs-panel p-6 mb-8 vs-fade-up-1" data-testid="creator-header">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[var(--vs-primary-from)] to-[var(--vs-secondary-to)] flex items-center justify-center flex-shrink-0">
              {creator.avatar_url ? (
                <img src={creator.avatar_url} alt={creator.name} className="w-full h-full rounded-full object-cover" />
              ) : (
                <span className="text-2xl font-bold text-white">{creator.name?.[0]?.toUpperCase() || '?'}</span>
              )}
            </div>
            <div className="flex-1">
              <h1 className="vs-h2 mb-1" data-testid="creator-name">{creator.name}</h1>
              {creator.bio && <p className="text-sm text-[var(--vs-text-secondary)] mb-3">{creator.bio}</p>}
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <p className="text-lg font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creator.total_creations}</p>
                  <p className="text-xs text-[var(--vs-text-muted)]">Creations</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creator.total_views}</p>
                  <p className="text-xs text-[var(--vs-text-muted)]">Views</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-white" style={{ fontFamily: 'var(--vs-font-mono)' }}>{creator.total_remixes}</p>
                  <p className="text-xs text-[var(--vs-text-muted)]">Remixes</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Creations Grid */}
        <h2 className="vs-h3 mb-4 vs-fade-up-2">Creations</h2>
        {creations.length === 0 ? (
          <div className="text-center py-16" data-testid="no-creations">
            <Film className="w-12 h-12 text-[var(--vs-text-muted)] mx-auto mb-3" />
            <p className="text-[var(--vs-text-muted)]">No creations yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 vs-fade-up-3" data-testid="creator-grid">
            {creations.map(item => (
              <Link key={item.job_id} to={`/v/${item.slug || item.job_id}`}>
                <div className="vs-card group p-0 overflow-hidden cursor-pointer" data-testid={`creator-card-${item.job_id}`}>
                  <div className="relative w-full aspect-video bg-[var(--vs-bg-elevated)] overflow-hidden">
                    {item.thumbnail_url ? (
                      <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center"><Film className="w-10 h-10 text-[var(--vs-text-muted)]" /></div>
                    )}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                      <Play className="w-10 h-10 text-white opacity-0 group-hover:opacity-80 transition-opacity drop-shadow-lg" />
                    </div>
                  </div>
                  <div className="p-3">
                    <h3 className="text-sm font-medium text-white truncate group-hover:text-[var(--vs-text-accent)] transition-colors">{item.title}</h3>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="flex items-center gap-1 text-xs text-[var(--vs-text-muted)]"><Eye className="w-3 h-3" /> {item.views || 0}</span>
                      <span className="flex items-center gap-1 text-xs text-[var(--vs-text-muted)]"><RefreshCcw className="w-3 h-3" /> {item.remix_count || 0}</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
