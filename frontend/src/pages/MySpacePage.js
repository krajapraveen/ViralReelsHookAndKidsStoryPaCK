import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Film, Image, BookOpen, Clock, CheckCircle, AlertCircle, Loader2, Download, Share2, RotateCcw, Play, Search, Filter, Grid3X3, List, Sparkles, RefreshCw } from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const api = {
  get: async (url) => {
    const token = localStorage.getItem('token');
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return { data: await res.json() };
  },
};

const STATUS_STYLES = {
  COMPLETED: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', icon: CheckCircle, label: 'Ready' },
  READY: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', icon: CheckCircle, label: 'Ready' },
  PARTIAL_READY: { bg: 'bg-amber-500/15', text: 'text-amber-400', icon: AlertCircle, label: 'Partial' },
  PROCESSING: { bg: 'bg-blue-500/15', text: 'text-blue-400', icon: Loader2, label: 'Processing' },
  FAILED: { bg: 'bg-red-500/15', text: 'text-red-400', icon: AlertCircle, label: 'Failed' },
};

const TYPE_ICONS = {
  story_video: Film,
  reel: Film,
  comic: Image,
  story: BookOpen,
};

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function CreationCard({ item, onView }) {
  const status = STATUS_STYLES[item.status] || STATUS_STYLES.PROCESSING;
  const StatusIcon = status.icon;
  const TypeIcon = TYPE_ICONS[item.type] || Film;
  const isReady = item.status === 'COMPLETED' || item.status === 'READY';
  const isProcessing = item.status === 'PROCESSING';

  return (
    <div
      className="group relative bg-slate-800/40 border border-slate-700/40 rounded-xl overflow-hidden hover:border-purple-500/30 transition-all cursor-pointer"
      onClick={() => onView(item)}
      data-testid={`creation-card-${item.id}`}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-slate-900/50">
        {item.thumbnail ? (
          <img src={item.thumbnail} alt={item.title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <TypeIcon className="w-10 h-10 text-slate-600" />
          </div>
        )}
        {isProcessing && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto mb-1" />
              <span className="text-blue-300 text-xs">{item.progress || 0}%</span>
            </div>
          </div>
        )}
        {/* Status badge */}
        <div className={`absolute top-2 right-2 ${status.bg} rounded-full px-2 py-0.5 flex items-center gap-1`}>
          <StatusIcon className={`w-3 h-3 ${status.text} ${isProcessing ? 'animate-spin' : ''}`} />
          <span className={`text-[10px] font-medium ${status.text}`}>{status.label}</span>
        </div>
      </div>

      {/* Info */}
      <div className="p-3">
        <h4 className="text-sm font-medium text-white truncate">{item.title || 'Untitled'}</h4>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[11px] text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3" /> {timeAgo(item.created_at)}
          </span>
          <span className="text-[11px] text-slate-600 capitalize">{(item.type || '').replace('_', ' ')}</span>
        </div>

        {/* Actions for ready items */}
        {isReady && (
          <div className="flex gap-1.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button size="sm" className="flex-1 h-7 text-[11px] bg-purple-600 hover:bg-purple-700" onClick={(e) => { e.stopPropagation(); onView(item); }}>
              <Play className="w-3 h-3 mr-1" /> Watch
            </Button>
            {item.download_url && (
              <Button size="sm" variant="outline" className="h-7 px-2 border-slate-600 text-slate-400" onClick={(e) => { e.stopPropagation(); window.open(item.download_url, '_blank'); }}>
                <Download className="w-3 h-3" />
              </Button>
            )}
          </div>
        )}
        {item.status === 'FAILED' && (
          <div className="mt-2">
            <Button size="sm" variant="outline" className="w-full h-7 text-[11px] border-red-500/30 text-red-400 hover:bg-red-500/10" onClick={(e) => { e.stopPropagation(); onView(item); }}>
              <RotateCcw className="w-3 h-3 mr-1" /> Retry
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function MySpacePage() {
  const navigate = useNavigate();
  const { assetId } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState('grid');

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch from multiple sources
      const [storyRes, reelRes] = await Promise.allSettled([
        api.get('/api/story-engine/user-jobs?limit=100'),
        api.get('/api/reels/my-reels?limit=50'),
      ]);

      const allItems = [];

      // Story engine jobs
      if (storyRes.status === 'fulfilled' && storyRes.value.data.success) {
        for (const j of storyRes.value.data.jobs || []) {
          allItems.push({
            id: j.job_id,
            title: j.title,
            type: 'story_video',
            status: j.status,
            thumbnail: j.thumbnail_url || j.thumbnail_small_url,
            download_url: j.output_url,
            created_at: j.created_at,
            progress: j.progress,
            route: `/app/story-video-studio?projectId=${j.job_id}`,
          });
        }
      }

      // Reels
      if (reelRes.status === 'fulfilled' && reelRes.value.data.success) {
        for (const r of reelRes.value.data.reels || []) {
          allItems.push({
            id: r.id || r._id,
            title: r.title || r.caption,
            type: 'reel',
            status: r.status || 'COMPLETED',
            thumbnail: r.thumbnail_url,
            download_url: r.video_url,
            created_at: r.created_at,
            route: `/app/reels`,
          });
        }
      }

      // Sort by date
      allItems.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      setItems(allItems);
    } catch (err) {
      toast.error('Failed to load your creations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  // Highlight asset if coming from generation
  useEffect(() => {
    if (assetId) {
      setTimeout(() => {
        const el = document.querySelector(`[data-testid="creation-card-${assetId}"]`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.classList.add('ring-2', 'ring-purple-500');
          setTimeout(() => el.classList.remove('ring-2', 'ring-purple-500'), 3000);
        }
      }, 500);
    }
  }, [assetId, items]);

  const handleView = (item) => {
    if (item.route) navigate(item.route);
  };

  const filtered = items.filter(item => {
    if (filter === 'all') return true;
    if (filter === 'videos') return item.type === 'story_video' || item.type === 'reel';
    if (filter === 'stories') return item.type === 'story';
    if (filter === 'failed') return item.status === 'FAILED';
    if (filter === 'processing') return item.status === 'PROCESSING';
    return true;
  }).filter(item => {
    if (!search) return true;
    return (item.title || '').toLowerCase().includes(search.toLowerCase());
  });

  const stats = {
    total: items.length,
    ready: items.filter(i => i.status === 'COMPLETED' || i.status === 'READY').length,
    processing: items.filter(i => i.status === 'PROCESSING').length,
    failed: items.filter(i => i.status === 'FAILED').length,
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="my-space-page">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">My Space</h1>
            <p className="text-slate-400 text-sm mt-1">Your creations, all in one place</p>
          </div>
          <Button onClick={() => navigate('/app/create')} className="bg-purple-600 hover:bg-purple-700" data-testid="create-new-from-space">
            <Sparkles className="w-4 h-4 mr-2" /> Create New
          </Button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Total', value: stats.total, color: 'text-white' },
            { label: 'Ready', value: stats.ready, color: 'text-emerald-400' },
            { label: 'Processing', value: stats.processing, color: 'text-blue-400' },
            { label: 'Failed', value: stats.failed, color: 'text-red-400' },
          ].map(s => (
            <div key={s.label} className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-3 text-center" data-testid={`stat-${s.label.toLowerCase()}`}>
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-[11px] text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Filters + Search */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex bg-slate-800/40 rounded-lg p-0.5 border border-slate-700/30">
            {[
              { id: 'all', label: 'All' },
              { id: 'videos', label: 'Videos' },
              { id: 'stories', label: 'Stories' },
              { id: 'processing', label: 'Processing' },
              { id: 'failed', label: 'Failed' },
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                  filter === f.id ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
                data-testid={`filter-${f.id}`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search creations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-800/30 border border-slate-700/30 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500/50"
              data-testid="search-input"
            />
          </div>

          <div className="flex bg-slate-800/40 rounded-lg border border-slate-700/30">
            <button onClick={() => setViewMode('grid')} className={`p-2 ${viewMode === 'grid' ? 'text-purple-400' : 'text-slate-500'}`}>
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button onClick={() => setViewMode('list')} className={`p-2 ${viewMode === 'list' ? 'text-purple-400' : 'text-slate-500'}`}>
              <List className="w-4 h-4" />
            </button>
          </div>

          <button onClick={fetchItems} className="p-2 text-slate-500 hover:text-white">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Content Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20" data-testid="empty-state">
            <Film className="w-16 h-16 text-slate-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400 mb-2">
              {search ? 'No results found' : 'No creations yet'}
            </h3>
            <p className="text-slate-500 text-sm mb-6">
              {search ? 'Try a different search term' : 'Start creating to see your work here'}
            </p>
            {!search && (
              <Button onClick={() => navigate('/app/create')} className="bg-purple-600 hover:bg-purple-700">
                <Sparkles className="w-4 h-4 mr-2" /> Create Your First Video
              </Button>
            )}
          </div>
        ) : (
          <div className={viewMode === 'grid' ? 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4' : 'space-y-3'} data-testid="content-grid">
            {filtered.map(item => (
              <CreationCard key={item.id} item={item} onView={handleView} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
