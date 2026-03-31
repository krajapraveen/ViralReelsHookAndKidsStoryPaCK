import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Eye, RotateCcw, Film, Loader2, TrendingUp, Star, Clock, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const api = {
  get: async (url) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return { data: await res.json() };
  },
};

function BrowseCard({ item, onPreview, onRemix }) {
  return (
    <div className="group relative bg-slate-800/40 border border-slate-700/40 rounded-xl overflow-hidden hover:border-purple-500/30 transition-all" data-testid={`browse-card-${item.id}`}>
      <div className="relative aspect-video bg-slate-900/50">
        {item.thumbnail ? (
          <img src={item.thumbnail} alt={item.title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Film className="w-10 h-10 text-slate-600" />
          </div>
        )}
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
          <Button size="sm" className="bg-purple-600 hover:bg-purple-700 h-8 text-xs" onClick={() => onPreview(item)}>
            <Eye className="w-3 h-3 mr-1" /> Preview
          </Button>
          <Button size="sm" variant="outline" className="border-slate-500 text-white h-8 text-xs" onClick={() => onRemix(item)}>
            <RotateCcw className="w-3 h-3 mr-1" /> Remix
          </Button>
        </div>
      </div>
      <div className="p-3">
        <h4 className="text-sm font-medium text-white truncate">{item.title || 'Untitled'}</h4>
        <p className="text-[11px] text-slate-500 mt-1">{item.creator || 'AI Generated'}</p>
      </div>
    </div>
  );
}

export default function BrowsePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('trending');
  const [search, setSearch] = useState('');
  const [previewItem, setPreviewItem] = useState(null);

  const fetchContent = useCallback(async () => {
    setLoading(true);
    try {
      // Try public endpoint first, fall back to story-engine
      const res = await api.get(`/api/story-engine/user-jobs?limit=30&sort=${tab}`);
      if (res.data.success) {
        setItems((res.data.jobs || []).map(j => ({
          id: j.job_id,
          title: j.title,
          thumbnail: j.thumbnail_url || j.thumbnail_small_url,
          creator: 'AI Generated',
          video_url: j.output_url,
          style: j.animation_style,
          slug: j.slug,
        })).filter(i => i.thumbnail));
      }
    } catch {
      toast.error('Failed to load content');
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => { fetchContent(); }, [fetchContent]);

  const handlePreview = (item) => {
    if (item.slug) {
      window.open(`/v/${item.slug}`, '_blank');
    } else if (item.video_url) {
      setPreviewItem(item);
    }
  };

  const handleRemix = (item) => {
    navigate(`/app/story-video-studio?projectId=${item.id}`);
  };

  const filtered = items.filter(i =>
    !search || (i.title || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="browse-page">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Explore Creations</h1>
            <p className="text-slate-400 text-sm mt-1">Discover AI-generated content and get inspired</p>
          </div>
          <Button onClick={() => navigate('/app/create')} className="bg-purple-600 hover:bg-purple-700" data-testid="create-from-browse">
            <Sparkles className="w-4 h-4 mr-2" /> Create Your Own
          </Button>
        </div>

        {/* Tabs + Search */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex bg-slate-800/40 rounded-lg p-0.5 border border-slate-700/30">
            {[
              { id: 'trending', label: 'Trending', icon: TrendingUp },
              { id: 'newest', label: 'New', icon: Clock },
              { id: 'most_remixed', label: 'Featured', icon: Star },
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors flex items-center gap-1.5 ${
                  tab === t.id ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
                data-testid={`tab-${t.id}`}
              >
                <t.icon className="w-3 h-3" /> {t.label}
              </button>
            ))}
          </div>

          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search content..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-800/30 border border-slate-700/30 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
              data-testid="browse-search"
            />
          </div>
        </div>

        {/* Content Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20" data-testid="browse-empty">
            <Film className="w-16 h-16 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400 mb-2">No content found</h3>
            <p className="text-slate-500 text-sm">Be the first to create something amazing!</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" data-testid="browse-grid">
            {filtered.map(item => (
              <BrowseCard key={item.id} item={item} onPreview={handlePreview} onRemix={handleRemix} />
            ))}
          </div>
        )}

        {/* Preview Modal */}
        {previewItem && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setPreviewItem(null)}>
            <div className="bg-slate-900 rounded-2xl border border-slate-700 max-w-3xl w-full p-6" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-lg font-bold text-white mb-4">{previewItem.title}</h3>
              {previewItem.video_url && (
                <video src={previewItem.video_url} controls autoPlay className="w-full rounded-xl mb-4" />
              )}
              <div className="flex gap-3">
                <Button onClick={() => handleRemix(previewItem)} className="bg-purple-600 hover:bg-purple-700">
                  <RotateCcw className="w-4 h-4 mr-2" /> Remix This
                </Button>
                <Button variant="outline" className="border-slate-600 text-slate-300" onClick={() => setPreviewItem(null)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
