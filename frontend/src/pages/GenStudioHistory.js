import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { 
  ArrowLeft, Image, Video, Clock, Download,
  Filter, RefreshCw, Eye, ChevronLeft, ChevronRight,
  Wallet, CheckCircle, XCircle, Loader2, AlertCircle
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api, { walletAPI } from '../utils/api';

export default function GenStudioHistory() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [wallet, setWallet] = useState({ balanceCredits: 0, reservedCredits: 0, availableCredits: 0 });
  const limit = 12;

  useEffect(() => {
    fetchHistory();
  }, [page, typeFilter, statusFilter]);

  // Poll for active jobs
  useEffect(() => {
    const hasActiveJobs = jobs.some(j => ['QUEUED', 'RUNNING'].includes(j.status));
    let interval;
    if (hasActiveJobs) {
      interval = setInterval(fetchHistory, 5000);
    }
    return () => clearInterval(interval);
  }, [jobs]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      
      const params = { limit, skip: page * limit };
      if (typeFilter !== 'all') params.job_type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;
      
      const [jobsRes, walletRes] = await Promise.all([
        walletAPI.listJobs(params),
        walletAPI.getWallet()
      ]);
      
      setJobs(jobsRes.data.jobs);
      setTotal(jobsRes.data.total);
      setWallet(walletRes.data);
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
          toast.error('File expired (3 min security limit)');
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

  const handleCancelJob = async (jobId) => {
    try {
      await walletAPI.cancelJob(jobId);
      toast.success('Job cancelled. Credits released.');
      fetchHistory();
    } catch (error) {
      toast.error('Failed to cancel job');
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'TEXT_TO_IMAGE': return <Image className="w-4 h-4 text-purple-400" />;
      case 'TEXT_TO_VIDEO': return <Video className="w-4 h-4 text-blue-400" />;
      case 'IMAGE_TO_VIDEO': return <Video className="w-4 h-4 text-green-400" />;
      case 'VIDEO_REMIX': return <RefreshCw className="w-4 h-4 text-red-400" />;
      case 'STORY_GENERATION': return <Image className="w-4 h-4 text-amber-400" />;
      case 'REEL_GENERATION': return <Video className="w-4 h-4 text-pink-400" />;
      default: return <Image className="w-4 h-4 text-slate-400" />;
    }
  };

  const getTypeLabel = (type) => {
    const labels = {
      'TEXT_TO_IMAGE': 'Text → Image',
      'TEXT_TO_VIDEO': 'Text → Video',
      'IMAGE_TO_VIDEO': 'Image → Video',
      'VIDEO_REMIX': 'Video Remix',
      'STORY_GENERATION': 'Story',
      'REEL_GENERATION': 'Reel',
      'STYLE_PROFILE_CREATE': 'Style Profile'
    };
    return labels[type] || type;
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'SUCCEEDED':
        return (
          <span className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full">
            <CheckCircle className="w-3 h-3" /> Completed
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1 text-xs text-red-400 bg-red-400/10 px-2 py-1 rounded-full">
            <XCircle className="w-3 h-3" /> Failed
          </span>
        );
      case 'RUNNING':
        return (
          <span className="flex items-center gap-1 text-xs text-blue-400 bg-blue-400/10 px-2 py-1 rounded-full">
            <Loader2 className="w-3 h-3 animate-spin" /> Processing
          </span>
        );
      case 'QUEUED':
        return (
          <span className="flex items-center gap-1 text-xs text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" /> Queued
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="flex items-center gap-1 text-xs text-slate-400 bg-slate-400/10 px-2 py-1 rounded-full">
            <AlertCircle className="w-3 h-3" /> Cancelled
          </span>
        );
      default:
        return (
          <span className="text-xs text-slate-400 bg-slate-400/10 px-2 py-1 rounded-full">{status}</span>
        );
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const totalPages = Math.ceil(total / limit);

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
              <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-4 py-2" data-testid="wallet-balance">
                <Wallet className="w-4 h-4 text-purple-400" />
                <div className="flex flex-col">
                  <span className="font-bold text-white text-sm">{wallet.availableCredits}</span>
                  <span className="text-xs text-slate-500">available</span>
                </div>
                {wallet.reservedCredits > 0 && (
                  <div className="border-l border-slate-600 pl-2 ml-2">
                    <span className="text-xs text-yellow-400">{wallet.reservedCredits} held</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(0); }}>
                <SelectTrigger className="w-[160px] bg-slate-800 border-slate-700 text-white">
                  <SelectValue placeholder="Filter by type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="TEXT_TO_IMAGE">Text → Image</SelectItem>
                  <SelectItem value="TEXT_TO_VIDEO">Text → Video</SelectItem>
                  <SelectItem value="IMAGE_TO_VIDEO">Image → Video</SelectItem>
                  <SelectItem value="VIDEO_REMIX">Video Remix</SelectItem>
                  <SelectItem value="STORY_GENERATION">Story</SelectItem>
                  <SelectItem value="REEL_GENERATION">Reel</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
              <SelectTrigger className="w-[140px] bg-slate-800 border-slate-700 text-white">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="SUCCEEDED">Completed</SelectItem>
                <SelectItem value="RUNNING">Processing</SelectItem>
                <SelectItem value="QUEUED">Queued</SelectItem>
                <SelectItem value="FAILED">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{total} jobs</span>
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
        </div>

        {/* Security Notice */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-2 text-yellow-400 text-sm">
            <Clock className="w-4 h-4" />
            <span>SECURITY: Files auto-deleted 3 minutes after generation. Download immediately!</span>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {jobs.map((job) => (
              <div key={job.id} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden group hover:border-slate-700 transition-colors">
                {/* Preview */}
                <div className="aspect-video bg-slate-800 relative flex items-center justify-center">
                  {job.status === 'SUCCEEDED' && job.outputUrls?.[0] ? (
                    job.jobType?.includes('VIDEO') || job.outputUrls[0]?.includes('.mp4') ? (
                      <video 
                        src={`${process.env.REACT_APP_BACKEND_URL}${job.outputUrls[0]}`}
                        className="w-full h-full object-cover"
                        muted
                        onMouseOver={(e) => e.target.play()}
                        onMouseOut={(e) => { e.target.pause(); e.target.currentTime = 0; }}
                      />
                    ) : (
                      <img 
                        src={`${process.env.REACT_APP_BACKEND_URL}${job.outputUrls[0]}`}
                        alt="Generated"
                        className="w-full h-full object-cover"
                      />
                    )
                  ) : job.status === 'RUNNING' || job.status === 'QUEUED' ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                      <span className="text-xs text-slate-400">{job.progress || 0}%</span>
                    </div>
                  ) : job.status === 'FAILED' ? (
                    <div className="flex flex-col items-center gap-2">
                      <XCircle className="w-8 h-8 text-red-400" />
                      <span className="text-xs text-red-400">Failed</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      {getTypeIcon(job.jobType)}
                      <span className="text-xs text-slate-500">No preview</span>
                    </div>
                  )}
                </div>
                
                {/* Info */}
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getTypeIcon(job.jobType)}
                      <span className="text-sm font-medium text-white">{getTypeLabel(job.jobType)}</span>
                    </div>
                    {getStatusBadge(job.status)}
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>{formatDate(job.createdAt)}</span>
                    <span>{job.costCredits} credits</span>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex gap-2">
                    {job.status === 'SUCCEEDED' && job.outputUrls?.[0] && (
                      <Button 
                        size="sm" 
                        className="flex-1 bg-green-600 hover:bg-green-700"
                        onClick={() => handleDownload(job.outputUrls[0], `genstudio-${job.id}.${job.outputUrls[0].includes('.mp4') ? 'mp4' : 'png'}`)}
                      >
                        <Download className="w-3 h-3 mr-1" />
                        Download
                      </Button>
                    )}
                    {job.status === 'QUEUED' && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        className="flex-1 border-red-500/50 text-red-400 hover:bg-red-500/10"
                        onClick={() => handleCancelJob(job.id)}
                      >
                        <XCircle className="w-3 h-3 mr-1" />
                        Cancel
                      </Button>
                    )}
                    {job.status === 'FAILED' && (
                      <div className="flex-1 text-xs text-red-400 truncate" title={job.errorMessage}>
                        {job.errorMessage || 'Generation failed'}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="border-slate-700 text-slate-300"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>
            <span className="text-sm text-slate-400">
              Page {page + 1} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page >= totalPages - 1}
              className="border-slate-700 text-slate-300"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
