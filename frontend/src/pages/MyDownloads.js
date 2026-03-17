import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Download, Trash2, CheckCircle,
  Image, FileText, Video, Music, Loader2, RefreshCw, FolderOpen,
  Calendar, Search, Shield
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import api from '../utils/api';

const TYPE_LABELS = {
  COMIC_AVATAR: 'Comic Avatar',
  COMIC_STRIP: 'Comic Strip',
  COMIC_STORYBOOK_PDF: 'Comic Story Book',
  COMIC_STORYBOOK_COVER: 'Cover Image',
};

const getFileIcon = (mime) => {
  if (mime?.includes('image')) return <Image className="w-5 h-5 text-purple-400" />;
  if (mime?.includes('video')) return <Video className="w-5 h-5 text-pink-400" />;
  if (mime?.includes('pdf')) return <FileText className="w-5 h-5 text-red-400" />;
  if (mime?.includes('audio')) return <Music className="w-5 h-5 text-green-400" />;
  return <FolderOpen className="w-5 h-5 text-slate-400" />;
};

export default function MyDownloads() {
  const [downloads, setDownloads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchDownloads = useCallback(async () => {
    try {
      const res = await api.get('/api/downloads/my-downloads');
      setDownloads(res.data.downloads || []);
    } catch (error) {
      console.error('Failed to fetch downloads:', error);
      toast.error('Failed to load downloads');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchDownloads(); }, [fetchDownloads]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDownloads();
  };

  const handleDownload = async (item) => {
    try {
      const res = await api.get(`/api/downloads/${item.id}/url`);
      if (res.data.url) {
        window.open(res.data.url, '_blank');
        toast.success('Download started!');
        await api.post(`/api/downloads/${item.id}/mark-downloaded`).catch(() => {});
        fetchDownloads();
      } else {
        toast.error('Download URL not available');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Download failed');
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/downloads/${id}`);
      toast.success('Removed from downloads');
      setDownloads(prev => prev.filter(d => d.id !== id));
    } catch {
      toast.error('Failed to remove');
    }
  };

  const filtered = downloads.filter(d => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (d.filename || '').toLowerCase().includes(q) ||
           (TYPE_LABELS[d.feature] || d.feature || '').toLowerCase().includes(q);
  });

  const grouped = filtered.reduce((acc, d) => {
    const date = d.created_at ? new Date(d.created_at).toLocaleDateString() : 'Unknown';
    if (!acc[date]) acc[date] = [];
    acc[date].push(d);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-[var(--vs-bg-primary,#0a0a12)]">
      <header className="border-b border-[var(--vs-border-subtle,#1e1e2e)] bg-[var(--vs-bg-surface,#12121a)]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2" data-testid="downloads-title">
                <FolderOpen className="w-6 h-6 text-purple-400" />
                My Creations
              </h1>
              <p className="text-sm text-slate-400">Permanent assets — download anytime</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing} className="text-slate-300 border-slate-600" data-testid="refresh-downloads">
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Permanent assets banner */}
        <div className="mb-6 bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3" data-testid="permanent-assets-banner">
          <Shield className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-emerald-300 font-semibold">Your Assets Are Safe</h3>
            <p className="text-emerald-400/70 text-sm mt-0.5">
              All generated content is stored permanently on our CDN. Download anytime — your creations never expire.
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="mb-8 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search your creations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-slate-800 border-slate-700 text-white"
            data-testid="search-downloads"
          />
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
            <span className="ml-3 text-slate-400">Loading your creations...</span>
          </div>
        )}

        {/* Empty */}
        {!loading && filtered.length === 0 && (
          <div className="text-center py-20" data-testid="empty-downloads">
            <FolderOpen className="w-16 h-16 mx-auto text-slate-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Creations Yet</h2>
            <p className="text-slate-400 mb-6">
              {searchQuery ? 'No results match your search' : 'Generate content to see your permanent assets here'}
            </p>
            <Link to="/app">
              <Button className="bg-purple-600 hover:bg-purple-700">Start Creating</Button>
            </Link>
          </div>
        )}

        {/* Downloads list */}
        {!loading && Object.entries(grouped).map(([date, items]) => (
          <div key={date} className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-medium text-slate-400">{date}</h3>
              <span className="text-xs text-slate-600">({items.length})</span>
            </div>

            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.id} className="bg-[var(--vs-bg-surface,#12121a)] rounded-xl border border-[var(--vs-border-subtle,#1e1e2e)] hover:border-purple-500/30 transition-all p-4" data-testid={`download-item-${item.id}`}>
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-slate-800/50">
                      {getFileIcon(item.file_type)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-white truncate">{item.filename || 'Untitled'}</h4>
                        {item.downloaded && <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />}
                      </div>
                      <p className="text-sm text-slate-400">{TYPE_LABELS[item.feature] || item.feature}</p>
                      <p className="text-xs text-emerald-500/70 mt-0.5">Permanent — stored on CDN</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button size="sm" onClick={() => handleDownload(item)} className="bg-purple-600 hover:bg-purple-700" data-testid={`download-btn-${item.id}`}>
                        <Download className="w-4 h-4 mr-1" />
                        Download
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(item.id)} className="text-slate-400 hover:text-red-400" data-testid={`delete-btn-${item.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}
