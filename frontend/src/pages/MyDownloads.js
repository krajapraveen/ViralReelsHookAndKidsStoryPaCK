import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Download, Trash2, Clock, CheckCircle, AlertCircle, 
  Image, FileText, Video, Music, Loader2, RefreshCw, FolderOpen,
  Calendar, Filter, Search, ExternalLink
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';

// Feature names mapping
const FEATURE_NAMES = {
  comic_avatar: 'Comic Avatar',
  comic_strip: 'Comic Strip',
  comic_storybook: 'Comic Storybook',
  gif_maker: 'GIF Maker',
  reaction_gif: 'Reaction GIF',
  reel_generator: 'Reel Script',
  story_generator: 'Story',
  coloring_book: 'Coloring Book',
  bedtime_story: 'Bedtime Story',
  thumbnail_generator: 'Thumbnail',
  brand_story: 'Brand Story'
};

// File type icons
const getFileIcon = (fileType) => {
  if (fileType?.includes('image') || fileType?.includes('gif') || fileType?.includes('png') || fileType?.includes('jpg')) {
    return <Image className="w-5 h-5 text-purple-400" />;
  }
  if (fileType?.includes('video') || fileType?.includes('mp4')) {
    return <Video className="w-5 h-5 text-pink-400" />;
  }
  if (fileType?.includes('pdf')) {
    return <FileText className="w-5 h-5 text-red-400" />;
  }
  if (fileType?.includes('audio') || fileType?.includes('mp3')) {
    return <Music className="w-5 h-5 text-green-400" />;
  }
  return <FolderOpen className="w-5 h-5 text-slate-400" />;
};

// Calculate time remaining
const getTimeRemaining = (expiresAt) => {
  if (!expiresAt) return null;
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diff = expiry - now;
  
  if (diff <= 0) return 'Expired';
  
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};

export default function MyDownloads() {
  const [downloads, setDownloads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // Fetch user downloads
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

  useEffect(() => {
    fetchDownloads();
    
    // Refresh every 30 seconds to update expiry times
    const interval = setInterval(fetchDownloads, 30000);
    return () => clearInterval(interval);
  }, [fetchDownloads]);

  // Handle refresh
  const handleRefresh = () => {
    setRefreshing(true);
    fetchDownloads();
  };

  // Handle download
  const handleDownload = async (download) => {
    try {
      // Check if expired
      if (download.expires_at && new Date(download.expires_at) < new Date()) {
        toast.error('This download has expired');
        return;
      }

      // Get fresh download URL
      const res = await api.get(`/api/downloads/${download.id}/url`);
      
      if (res.data.url) {
        // Open download in new tab
        window.open(res.data.url, '_blank');
        toast.success('Download started!');
        
        // Mark as downloaded
        await api.post(`/api/downloads/${download.id}/mark-downloaded`);
        fetchDownloads();
      } else {
        toast.error('Download URL not available');
      }
    } catch (error) {
      console.error('Download error:', error);
      toast.error(error.response?.data?.detail || 'Failed to download');
    }
  };

  // Handle delete
  const handleDelete = async (downloadId) => {
    try {
      await api.delete(`/api/downloads/${downloadId}`);
      toast.success('Download removed');
      setDownloads(prev => prev.filter(d => d.id !== downloadId));
    } catch (error) {
      toast.error('Failed to remove download');
    }
  };

  // Filter downloads
  const filteredDownloads = downloads.filter(d => {
    // Filter by status
    if (filter === 'active') {
      if (d.expires_at && new Date(d.expires_at) < new Date()) return false;
    } else if (filter === 'expired') {
      if (!d.expires_at || new Date(d.expires_at) >= new Date()) return false;
    } else if (filter === 'downloaded') {
      if (!d.downloaded) return false;
    }
    
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const featureName = FEATURE_NAMES[d.feature] || d.feature || '';
      const filename = d.filename || '';
      return featureName.toLowerCase().includes(query) || filename.toLowerCase().includes(query);
    }
    
    return true;
  });

  // Group by date
  const groupedDownloads = filteredDownloads.reduce((acc, download) => {
    const date = new Date(download.created_at).toLocaleDateString();
    if (!acc[date]) acc[date] = [];
    acc[date].push(download);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <FolderOpen className="w-6 h-6 text-purple-400" />
                My Downloads
              </h1>
              <p className="text-sm text-slate-400">Your saved generated content</p>
            </div>
          </div>
          
          <Button 
            variant="outline" 
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-slate-300 border-slate-600"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Important Warning Banner */}
        <div className="mb-6 bg-amber-500/20 border border-amber-500/50 rounded-xl p-4" data-testid="expiry-warning-banner">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-amber-400 font-semibold text-lg">Important: 30-Minute Download Window</h3>
              <p className="text-amber-200/80 text-sm mt-1">
                All generated files (images, videos, audio, PDFs) are automatically deleted after <strong>30 minutes</strong> to save server space. 
                Please download your files after generation. Expired files cannot be recovered.
              </p>
            </div>
          </div>
        </div>
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search downloads..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-slate-800 border-slate-700 text-white"
            />
          </div>
          
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700 text-white">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              <SelectItem value="all" className="text-white">All Downloads</SelectItem>
              <SelectItem value="active" className="text-white">Active</SelectItem>
              <SelectItem value="expired" className="text-white">Expired</SelectItem>
              <SelectItem value="downloaded" className="text-white">Downloaded</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
            <span className="ml-3 text-slate-400">Loading downloads...</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredDownloads.length === 0 && (
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 mx-auto text-slate-600 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Downloads Found</h2>
            <p className="text-slate-400 mb-6">
              {searchQuery || filter !== 'all' 
                ? 'Try adjusting your filters'
                : 'Generate content to see your downloads here'}
            </p>
            <Link to="/app">
              <Button className="bg-purple-600 hover:bg-purple-700">
                Explore Features
              </Button>
            </Link>
          </div>
        )}

        {/* Downloads List */}
        {!loading && Object.entries(groupedDownloads).map(([date, items]) => (
          <div key={date} className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-medium text-slate-400">{date}</h3>
              <span className="text-xs text-slate-600">({items.length} items)</span>
            </div>
            
            <div className="space-y-3">
              {items.map((download) => {
                const isExpired = download.expires_at && new Date(download.expires_at) < new Date();
                const timeRemaining = getTimeRemaining(download.expires_at);
                
                return (
                  <div 
                    key={download.id}
                    className={`bg-slate-800/50 rounded-xl border p-4 transition-all ${
                      isExpired 
                        ? 'border-red-500/30 opacity-60' 
                        : 'border-slate-700 hover:border-purple-500/50'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      {/* Icon */}
                      <div className={`p-3 rounded-lg ${isExpired ? 'bg-slate-700' : 'bg-slate-700/50'}`}>
                        {getFileIcon(download.file_type)}
                      </div>
                      
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-white truncate">
                            {download.filename || 'Untitled'}
                          </h4>
                          {download.downloaded && (
                            <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-sm text-slate-400">
                          {FEATURE_NAMES[download.feature] || download.feature}
                        </p>
                        
                        {/* Expiry */}
                        {download.expires_at && (
                          <div className="flex items-center gap-2 mt-1">
                            <Clock className={`w-3 h-3 ${isExpired ? 'text-red-400' : 'text-amber-400'}`} />
                            <span className={`text-xs ${isExpired ? 'text-red-400' : 'text-amber-400'}`}>
                              {isExpired ? 'Expired' : `Expires in ${timeRemaining}`}
                            </span>
                          </div>
                        )}
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {!isExpired && (
                          <Button
                            size="sm"
                            onClick={() => handleDownload(download)}
                            className="bg-purple-600 hover:bg-purple-700"
                          >
                            <Download className="w-4 h-4 mr-1" />
                            Download
                          </Button>
                        )}
                        
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDelete(download.id)}
                          className="text-slate-400 hover:text-red-400"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    
                    {/* Preview for images */}
                    {download.preview_url && !isExpired && (
                      <div className="mt-3 pt-3 border-t border-slate-700">
                        <img 
                          src={download.preview_url}
                          alt="Preview"
                          className="h-20 rounded-lg object-cover"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {/* Info Banner */}
        <div className="mt-8 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-amber-300">Download Expiry Notice</h4>
              <p className="text-sm text-amber-400/80 mt-1">
                Downloads are available for 5 minutes after generation. Make sure to save your files before they expire.
                We'll notify you when your content is ready for download.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
