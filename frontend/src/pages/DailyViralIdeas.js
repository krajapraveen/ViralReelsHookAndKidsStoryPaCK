import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, TrendingUp, Flame, Zap, Download, FileText, Image, Package, ChevronRight, RefreshCw, Clock, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PHASE_ICONS = {
  planning: Clock,
  generating_hooks: Zap,
  generating_script: FileText,
  generating_captions: Copy,
  generating_thumbnail: Image,
  packaging: Package,
  ready: Check,
};

const NICHE_COLORS = {
  Tech: 'from-sky-500 to-cyan-400', Finance: 'from-emerald-500 to-green-400',
  Fitness: 'from-rose-500 to-red-400', Food: 'from-amber-500 to-yellow-400',
  Travel: 'from-violet-500 to-purple-400', Fashion: 'from-pink-500 to-rose-400',
  Gaming: 'from-indigo-500 to-blue-400', Education: 'from-teal-500 to-cyan-400',
  Business: 'from-slate-500 to-gray-400', Lifestyle: 'from-orange-500 to-amber-400',
  Health: 'from-lime-500 to-green-400', Entertainment: 'from-fuchsia-500 to-purple-400',
};

// ==================== FEED VIEW ====================
const FeedView = ({ onGenerate, generating }) => {
  const [ideas, setIdeas] = useState([]);
  const [niches, setNiches] = useState([]);
  const [selectedNiche, setSelectedNiche] = useState('');
  const [loading, setLoading] = useState(true);
  const [myJobs, setMyJobs] = useState([]);

  useEffect(() => {
    fetchFeed();
    fetchMyJobs();
  }, [selectedNiche]);

  const fetchFeed = async () => {
    try {
      const url = selectedNiche
        ? `${API_URL}/api/viral-ideas/daily-feed?niche=${selectedNiche}`
        : `${API_URL}/api/viral-ideas/daily-feed`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setIdeas(data.ideas || []);
        setNiches(data.niches || []);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const fetchMyJobs = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      const res = await fetch(`${API_URL}/api/viral-ideas/my-jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMyJobs(data.jobs || []);
      }
    } catch (e) { console.error(e); }
  };

  const getTypeTag = (type) => {
    const styles = {
      list: 'bg-sky-500/15 text-sky-300', tutorial: 'bg-emerald-500/15 text-emerald-300',
      review: 'bg-violet-500/15 text-violet-300', story: 'bg-amber-500/15 text-amber-300',
      analysis: 'bg-cyan-500/15 text-cyan-300', educational: 'bg-pink-500/15 text-pink-300',
    };
    return styles[type] || 'bg-slate-500/15 text-slate-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Recent Jobs */}
      {myJobs.length > 0 && (
        <div data-testid="recent-jobs-section">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Recent Packs</h2>
          <div className="grid gap-2">
            {myJobs.slice(0, 3).map(job => (
              <Link
                key={job.job_id}
                to={`/app/daily-viral-ideas?job=${job.job_id}`}
                className="flex items-center justify-between p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-colors"
                data-testid={`job-card-${job.job_id}`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-2 h-2 rounded-full ${job.status === 'completed' ? 'bg-emerald-400' : job.status === 'processing' ? 'bg-amber-400 animate-pulse' : 'bg-slate-500'}`} />
                  <span className="text-sm text-white truncate">{job.idea}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-slate-500">{job.niche}</span>
                  <ChevronRight className="w-4 h-4 text-slate-600" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Niche Filter */}
      <div className="flex flex-wrap gap-1.5" data-testid="niche-filters">
        <button
          onClick={() => setSelectedNiche('')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${!selectedNiche ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-300'}`}
        >All</button>
        {niches.map(n => (
          <button
            key={n}
            onClick={() => setSelectedNiche(n)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${selectedNiche === n ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-300'}`}
          >{n}</button>
        ))}
      </div>

      {/* Ideas Grid */}
      <div className="grid gap-3" data-testid="ideas-feed">
        {ideas.map((idea, idx) => (
          <div
            key={idx}
            className="group relative bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all"
            data-testid={`idea-card-${idx}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2.5">
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md bg-gradient-to-r ${NICHE_COLORS[idea.niche] || 'from-slate-500 to-gray-400'} text-white`}>
                    {idea.niche}
                  </span>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${getTypeTag(idea.type)}`}>
                    {idea.type}
                  </span>
                  {idea.trending_score >= 90 && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-red-500/15 text-red-400 flex items-center gap-0.5">
                      <TrendingUp className="w-3 h-3" /> Hot
                    </span>
                  )}
                </div>
                <p className="text-white font-medium text-base leading-snug">{idea.idea}</p>
              </div>
              <button
                onClick={() => onGenerate(idea.idea, idea.niche)}
                disabled={generating}
                className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-orange-500/20 hover:shadow-orange-500/30 transition-all disabled:opacity-50 flex-shrink-0"
                data-testid={`generate-btn-${idx}`}
              >
                {generating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                Generate
              </button>
            </div>
          </div>
        ))}
      </div>

      {ideas.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium text-slate-400">No ideas available</p>
          <p className="text-sm">Check back soon for fresh content ideas</p>
        </div>
      )}
    </div>
  );
};

// ==================== PROGRESS VIEW ====================
const ProgressView = ({ jobId, onComplete }) => {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const pollStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setError('Unable to load job status');
        return;
      }
      const data = await res.json();
      setJob(data);
      if (data.status === 'completed' || data.status === 'completed_with_fallbacks') {
        clearInterval(pollRef.current);
        onComplete(jobId);
      }
    } catch (e) {
      console.error(e);
    }
  }, [jobId, onComplete]);

  useEffect(() => {
    pollStatus();
    pollRef.current = setInterval(pollStatus, 2000);
    return () => clearInterval(pollRef.current);
  }, [pollStatus]);

  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-400">{error}</p>
        <Link to="/app/daily-viral-ideas" className="text-orange-400 underline mt-2 inline-block">Back to feed</Link>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const progress = job.progress || {};
  const tasks = job.tasks || [];
  const taskOrder = ['hooks', 'script', 'captions', 'thumbnail', 'packaging'];

  return (
    <div className="max-w-lg mx-auto space-y-8" data-testid="progress-view">
      {/* Progress Circle */}
      <div className="text-center">
        <div className="relative inline-flex items-center justify-center w-32 h-32">
          <svg className="w-32 h-32 -rotate-90">
            <circle cx="64" cy="64" r="56" fill="none" stroke="#1e293b" strokeWidth="8" />
            <circle
              cx="64" cy="64" r="56" fill="none" stroke="url(#progressGrad)" strokeWidth="8"
              strokeLinecap="round" strokeDasharray={`${(progress.percentage || 0) * 3.52} 352`}
              className="transition-all duration-700"
            />
            <defs>
              <linearGradient id="progressGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f97316" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>
          </svg>
          <span className="absolute text-2xl font-bold text-white">{progress.percentage || 0}%</span>
        </div>
        <p className="mt-4 text-lg font-semibold text-white">{progress.message || 'Processing...'}</p>
      </div>

      {/* Task List */}
      <div className="space-y-2">
        {taskOrder.map((type) => {
          const task = tasks.find(t => t.task_type === type);
          const status = task?.status || 'pending';
          const Icon = PHASE_ICONS[`generating_${type}`] || PHASE_ICONS[type] || Clock;
          return (
            <div
              key={type}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all ${status === 'completed' ? 'bg-emerald-500/10 border border-emerald-500/20' : status === 'processing' ? 'bg-orange-500/10 border border-orange-500/20' : 'bg-slate-800/40 border border-slate-800'}`}
              data-testid={`task-${type}`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${status === 'completed' ? 'bg-emerald-500/20' : status === 'processing' ? 'bg-orange-500/20' : 'bg-slate-700/50'}`}>
                {status === 'completed' ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : status === 'processing' ? (
                  <RefreshCw className="w-4 h-4 text-orange-400 animate-spin" />
                ) : (
                  <Icon className="w-4 h-4 text-slate-500" />
                )}
              </div>
              <span className={`text-sm font-medium capitalize ${status === 'completed' ? 'text-emerald-300' : status === 'processing' ? 'text-orange-300' : 'text-slate-500'}`}>
                {type === 'hooks' ? 'Viral Hooks' : type === 'script' ? 'Video Script' : type === 'captions' ? 'Social Captions' : type === 'thumbnail' ? 'Thumbnail' : 'Final Package'}
              </span>
              {task?.fallback_used && status === 'completed' && (
                <span className="ml-auto text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">alt</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ==================== RESULT VIEW ====================
const ResultView = ({ jobId }) => {
  const [assets, setAssets] = useState([]);
  const [job, setJob] = useState(null);
  const [copied, setCopied] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAssets();
  }, [jobId]);

  const fetchAssets = async () => {
    try {
      const token = localStorage.getItem('token');
      const [assetsRes, jobRes] = await Promise.all([
        fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}/assets`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (assetsRes.ok) {
        const data = await assetsRes.json();
        setAssets(data.assets || []);
      }
      if (jobRes.ok) setJob(await jobRes.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const copyContent = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success('Copied to clipboard');
  };

  const getAssetUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    const path = url.startsWith('/api') ? url : `/api${url}`;
    return `${API_URL}${path}`;
  };

  const downloadFile = (url) => {
    window.open(getAssetUrl(url), '_blank');
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-3 border-orange-500 border-t-transparent rounded-full" /></div>;
  }

  const hooks = assets.find(a => a.asset_type === 'hooks');
  const script = assets.find(a => a.asset_type === 'script');
  const captions = assets.find(a => a.asset_type === 'captions');
  const thumbnail = assets.find(a => a.asset_type === 'thumbnail');
  const zipBundle = assets.find(a => a.asset_type === 'zip_bundle');

  return (
    <div className="space-y-6" data-testid="result-view">
      {/* Success Banner */}
      <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-5 text-center">
        <Check className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
        <h2 className="text-xl font-bold text-white">Your Content Pack is Ready!</h2>
        {job && <p className="text-sm text-slate-400 mt-1">{job.progress?.message}</p>}
      </div>

      {/* Download All */}
      {zipBundle?.file_url && (
        <button
          onClick={() => downloadFile(zipBundle.file_url)}
          className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/20 transition-all"
          data-testid="download-all-btn"
        >
          <Download className="w-5 h-5" />
          Download Full Pack (ZIP)
        </button>
      )}

      {/* Thumbnail */}
      {thumbnail?.file_url && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden" data-testid="asset-thumbnail">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Image className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-semibold text-white">Thumbnail</span>
            </div>
            <button onClick={() => downloadFile(thumbnail.file_url)} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1">
              <Download className="w-3 h-3" /> Download
            </button>
          </div>
          <div className="p-4">
            <img src={getAssetUrl(thumbnail.file_url)} alt="Thumbnail" className="w-full max-w-xs mx-auto rounded-xl" />
          </div>
        </div>
      )}

      {/* Hooks */}
      {hooks?.content && (
        <AssetCard
          icon={<Zap className="w-4 h-4 text-amber-400" />}
          title="Viral Hooks"
          content={hooks.content}
          onCopy={() => copyContent(hooks.content, 'hooks')}
          copied={copied === 'hooks'}
        />
      )}

      {/* Script */}
      {script?.content && (
        <AssetCard
          icon={<FileText className="w-4 h-4 text-sky-400" />}
          title="Video Script"
          content={script.content}
          onCopy={() => copyContent(script.content, 'script')}
          copied={copied === 'script'}
        />
      )}

      {/* Captions */}
      {captions?.content && (
        <AssetCard
          icon={<Copy className="w-4 h-4 text-emerald-400" />}
          title="Social Captions"
          content={captions.content}
          onCopy={() => copyContent(captions.content, 'captions')}
          copied={copied === 'captions'}
        />
      )}

      {/* Generate Another */}
      <Link
        to="/app/daily-viral-ideas"
        className="flex items-center justify-center gap-2 py-3 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition-colors"
        data-testid="generate-another-btn"
      >
        <ArrowRight className="w-4 h-4" />
        Generate Another Pack
      </Link>
    </div>
  );
};

// ==================== ASSET CARD ====================
const AssetCard = ({ icon, title, content, onCopy, copied }) => (
  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden" data-testid={`asset-${title.toLowerCase().replace(/\s/g, '-')}`}>
    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold text-white">{title}</span>
      </div>
      <button onClick={onCopy} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1">
        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
    <div className="p-4">
      <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto">{content}</pre>
    </div>
  </div>
);

// ==================== MAIN PAGE ====================
const DailyViralIdeas = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState('feed');
  const [activeJobId, setActiveJobId] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const jobParam = searchParams.get('job');
    if (jobParam) {
      setActiveJobId(jobParam);
      setView('result');
    }
  }, [searchParams]);

  const handleGenerate = async (idea, niche) => {
    setGenerating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/viral-ideas/generate-bundle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ idea, niche }),
      });
      const data = await res.json();
      if (res.ok && data.job_id) {
        setActiveJobId(data.job_id);
        setView('progress');
        toast.success('Content pack generation started!');
      } else {
        toast.error(data.detail || 'Generation failed');
      }
    } catch (e) {
      toast.error('Failed to start generation');
    } finally {
      setGenerating(false);
    }
  };

  const handleJobComplete = useCallback((jobId) => {
    setSearchParams({ job: jobId });
    setView('result');
  }, [setSearchParams]);

  const goToFeed = () => {
    setSearchParams({});
    setView('feed');
    setActiveJobId(null);
  };

  return (
    <div className="min-h-screen bg-[#070b14] py-6 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            {view !== 'feed' ? (
              <button onClick={goToFeed} className="p-2 bg-slate-800/80 rounded-xl hover:bg-slate-700 transition-colors" data-testid="back-to-feed-btn">
                <ArrowLeft className="w-5 h-5 text-slate-400" />
              </button>
            ) : (
              <Link to="/app" className="p-2 bg-slate-800/80 rounded-xl hover:bg-slate-700 transition-colors">
                <ArrowLeft className="w-5 h-5 text-slate-400" />
              </Link>
            )}
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2" data-testid="page-title">
                <Flame className="w-5 h-5 text-orange-400" />
                Viral Idea Drop
              </h1>
              <p className="text-slate-500 text-xs">
                {view === 'feed' ? 'Pick an idea, generate a full content pack' : view === 'progress' ? 'Creating your pack...' : 'Your pack is ready'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Sparkles className="w-3.5 h-3.5" />
            5 credits / pack
          </div>
        </div>

        {/* View Router */}
        {view === 'feed' && <FeedView onGenerate={handleGenerate} generating={generating} />}
        {view === 'progress' && activeJobId && <ProgressView jobId={activeJobId} onComplete={handleJobComplete} />}
        {view === 'result' && activeJobId && <ResultView jobId={activeJobId} />}
      </div>
    </div>
  );
};

export default DailyViralIdeas;
