import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { TrendingUp, Clock, RefreshCcw, Film, Eye, Play, Command, ChevronRight, Search } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { key: 'trending', label: 'Trending', icon: TrendingUp },
  { key: 'newest', label: 'Newest', icon: Clock },
  { key: 'most_remixed', label: 'Most Remixed', icon: RefreshCcw },
];

export default function ExplorePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get('tab') || 'trending');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    fetchItems(tab, 0);
  }, [tab]);

  const fetchItems = async (currentTab, skip) => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/api/public/explore?tab=${currentTab}&limit=12&skip=${skip}`);
      if (skip === 0) {
        setItems(r.data.items || []);
      } else {
        setItems(prev => [...prev, ...(r.data.items || [])]);
      }
      setTotal(r.data.total || 0);
      setHasMore(r.data.has_more || false);
    } catch (e) {
      console.error('Explore fetch error:', e);
    }
    setLoading(false);
  };

  const handleTabChange = (newTab) => {
    setTab(newTab);
    setSearchParams({ tab: newTab });
  };

  return (
    <div className="vs-page min-h-screen" data-testid="explore-page">
      {/* Header */}
      <header className="vs-glass sticky top-0 z-40 border-b border-[var(--vs-border-subtle)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg vs-gradient-bg flex items-center justify-center">
              <Command className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-semibold text-white tracking-tight" style={{ fontFamily: 'var(--vs-font-heading)' }}>
              Visionary Suite
            </span>
          </Link>
          <nav className="flex items-center gap-1">
            <Link to="/app" className="px-3 py-1.5 text-sm text-[var(--vs-text-muted)] hover:text-white rounded-lg hover:bg-white/[0.04] transition-colors">Create</Link>
            <Link to="/explore" className="px-3 py-1.5 text-sm text-white rounded-lg bg-white/[0.04]">Explore</Link>
            <Link to="/pricing" className="px-3 py-1.5 text-sm text-[var(--vs-text-muted)] hover:text-white rounded-lg hover:bg-white/[0.04] transition-colors">Pricing</Link>
            <Link to="/signup" className="vs-btn-primary h-8 px-4 text-xs ml-2">Start Creating</Link>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Page Title */}
        <div className="text-center mb-8 vs-fade-up-1">
          <h1 className="vs-h1 mb-2">Explore Creations</h1>
          <p className="text-[var(--vs-text-secondary)] text-sm" style={{ fontFamily: 'var(--vs-font-body)' }}>
            Discover AI-generated videos, comics, and stories from creators worldwide
          </p>
        </div>

        {/* Tabs */}
        <div className="flex items-center justify-center gap-1 mb-8 vs-fade-up-2" data-testid="explore-tabs">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => handleTabChange(t.key)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-[var(--vs-btn-radius)] text-sm font-medium transition-all ${
                tab === t.key
                  ? 'bg-[var(--vs-cta)] text-white shadow-lg shadow-purple-500/20'
                  : 'text-[var(--vs-text-muted)] hover:text-white hover:bg-white/[0.04]'
              }`}
              data-testid={`explore-tab-${t.key}`}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
          <span className="ml-4 text-xs text-[var(--vs-text-muted)]" style={{ fontFamily: 'var(--vs-font-mono)' }}>
            {total} creations
          </span>
        </div>

        {/* Grid */}
        {loading && items.length === 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="vs-card p-0 overflow-hidden animate-pulse">
                <div className="w-full aspect-video bg-[var(--vs-bg-elevated)]" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-[var(--vs-bg-elevated)] rounded w-3/4" />
                  <div className="h-3 bg-[var(--vs-bg-elevated)] rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20" data-testid="explore-empty">
            <Film className="w-16 h-16 text-[var(--vs-text-muted)] mx-auto mb-4" />
            <h2 className="vs-h3 mb-2">No creations yet</h2>
            <p className="text-[var(--vs-text-muted)] mb-6">Be the first to create something amazing!</p>
            <Link to="/app/story-video-studio">
              <button className="vs-btn-primary">Create AI Video</button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 vs-fade-up-3" data-testid="explore-grid">
            {items.map(item => (
              <Link key={item.job_id} to={`/v/${item.slug || item.job_id}`}>
                <div className="vs-card group p-0 overflow-hidden cursor-pointer" data-testid={`explore-card-${item.job_id}`}>
                  <div className="relative w-full aspect-video bg-[var(--vs-bg-elevated)] overflow-hidden">
                    {item.thumbnail_url ? (
                      <img src={item.thumbnail_url} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Film className="w-10 h-10 text-[var(--vs-text-muted)]" />
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                      <Play className="w-10 h-10 text-white opacity-0 group-hover:opacity-80 transition-opacity drop-shadow-lg" />
                    </div>
                    <span className="absolute bottom-2 right-2 bg-black/60 text-white text-xs px-2 py-0.5 rounded" style={{ fontFamily: 'var(--vs-font-mono)' }}>
                      {item.animation_style?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="p-3">
                    <h3 className="text-sm font-medium text-white truncate group-hover:text-[var(--vs-text-accent)] transition-colors">{item.title}</h3>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="flex items-center gap-1 text-xs text-[var(--vs-text-muted)]">
                        <Eye className="w-3 h-3" /> {item.views || 0}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-[var(--vs-text-muted)]">
                        <RefreshCcw className="w-3 h-3" /> {item.remix_count || 0}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Load More */}
        {hasMore && !loading && (
          <div className="text-center mt-8">
            <button onClick={() => fetchItems(tab, items.length)} className="vs-btn-secondary" data-testid="load-more-btn">
              Load More <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
