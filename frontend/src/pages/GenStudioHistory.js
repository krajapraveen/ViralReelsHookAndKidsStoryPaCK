import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  ArrowLeft, Coins, Image, Video, Clock, Download,
  Filter, RefreshCw, Trash2, Eye, ChevronLeft, ChevronRight
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api from '../utils/api';

export default function GenStudioHistory() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [typeFilter, setTypeFilter] = useState('all');
  const [credits, setCredits] = useState(0);

  useEffect(() => {
    fetchHistory();
  }, [page, typeFilter]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const [historyRes, creditsRes] = await Promise.all([
        api.get('/api/genstudio/history', {
          params: { 
            page, 
            limit: 12,
            type_filter: typeFilter !== 'all' ? typeFilter : undefined
          }
        }),
        api.get('/api/credits/balance')
      ]);
      
      setJobs(historyRes.data.jobs);
      setTotalPages(historyRes.data.totalPages);
      setCredits(creditsRes.data.balance);
    } catch (error) {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}${url}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        if (response.status === 410) {
          toast.error('File expired (15 min limit)');
          return;
        }
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      toast.success('Downloaded!');
    } catch (error) {
      toast.error('Download failed');
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'text_to_image': return <Image className="w-4 h-4" />;
      case 'text_to_video': return <Video className="w-4 h-4" />;
      case 'image_to_video': return <Video className="w-4 h-4" />;
      case 'video_remix': return <RefreshCw className="w-4 h-4" />;
      default: return <Image className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type) => {
    return type.replace(/_/g, ' → ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-400/10';
      case 'processing': return 'text-yellow-400 bg-yellow-400/10';
      case 'failed': return 'text-red-400 bg-red-400/10';
      default: return 'text-slate-400 bg-slate-400/10';
    }
  };

  const isExpired = (expiresAt) => {
    if (!expiresAt) return true;
    return new Date(expiresAt) < new Date();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app/gen-studio" className="text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-white">Generation History</h1>
                <p className="text-xs text-slate-400">View and download your creations</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2">
                <Coins className="w-4 h-4 text-yellow-500" />
                <span className="font-bold text-white">{credits}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
                <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="text_to_image">Text → Image</SelectItem>
                  <SelectItem value="text_to_video">Text → Video</SelectItem>
                  <SelectItem value="image_to_video">Image → Video</SelectItem>
                  <SelectItem value="video_remix">Video Remix</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchHistory}
            className="border-slate-700 text-slate-300"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Notice */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 text-yellow-400 text-sm">
            <Clock className="w-4 h-4" />
            <span>⚠️ SECURITY: Files auto-deleted 3 minutes after generation. Download immediately!</span>
          </div>
        </div>

        {/* Jobs Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
              <Image className="w-10 h-10 text-slate-600" />
            </div>
            <p className="text-slate-400">No generations yet</p>
            <Link to="/app/gen-studio/text-to-image">
              <Button className="mt-4 bg-purple-600 hover:bg-purple-700">
                Create Your First Image
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {jobs.map((job) => (
              <div key={job.id} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden group">
                {/* Preview */}
                <div className="aspect-square bg-slate-800 relative">
                  {job.outputUrls?.[0] && !isExpired(job.expiresAt) ? (
                    <img 
                      src={`${process.env.REACT_APP_BACKEND_URL}${job.outputUrls[0]}`}
                      alt="Generated"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.querySelector('.placeholder')?.classList.remove('hidden');
                      }}
                    />
                  ) : (
                    <div className="placeholder w-full h-full flex items-center justify-center">
                      {isExpired(job.expiresAt) ? (
                        <div className="text-center text-slate-500">
                          <Clock className="w-8 h-8 mx-auto mb-2" />
                          <p className="text-xs">Expired</p>
                        </div>
                      ) : (
                        getTypeIcon(job.type)
                      )}
                    </div>
                  )}
                  
                  {/* Overlay on hover */}
                  {!isExpired(job.expiresAt) && job.outputUrls?.[0] && (
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleDownload(job.outputUrls[0], `genstudio-${job.id}.png`)}
                        className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
                      >
                        <Download className="w-5 h-5 text-white" />
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Info */}
                <div className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-slate-400">
                      {getTypeIcon(job.type)}
                      <span className="text-xs">{getTypeLabel(job.type)}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  
                  <p className="text-xs text-slate-500 truncate" title={job.inputJson?.prompt}>
                    {job.inputJson?.prompt?.substring(0, 50)}...
                  </p>
                  
                  <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                    <span>{job.costCredits} credits</span>
                    <span>{new Date(job.createdAt).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-8">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="border-slate-700"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-slate-400 text-sm px-4">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="border-slate-700"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
