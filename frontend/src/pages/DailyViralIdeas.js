import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Sparkles, Copy, Check, TrendingUp, Flame, Zap, Download, FileText, Image, Package, ChevronRight, RefreshCw, Clock, ArrowRight, Volume2, Video, MessageSquare, ThumbsUp, ThumbsDown, RotateCw, ShieldAlert, Heart, Lock } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PHASE_ICONS = {
  planning: Clock,
  generating_hooks: Zap,
  generating_script: FileText,
  generating_captions: Copy,
  generating_thumbnail: Image,
  generating_audio: Volume2,
  generating_video: Video,
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
const FALLBACK_IDEAS = [
  { idea: "Things that look fake but are real", type: "viral", niche: "Entertainment", trending_score: 97, badge: "trending" },
  { idea: "You won't believe what happened next", type: "story", niche: "Lifestyle", trending_score: 95, badge: "trending" },
  { idea: "Before vs After transformation that shocked everyone", type: "transformation", niche: "Fitness", trending_score: 94, badge: "fast_growing" },
  { idea: "This changed everything for me", type: "story", niche: "Business", trending_score: 93, badge: "trending" },
  { idea: "Wait till the end — you won't expect this", type: "loop", niche: "Entertainment", trending_score: 92, badge: "fast_growing" },
  { idea: "I tried this for 7 days — here's what changed", type: "experiment", niche: "Health", trending_score: 91, badge: "trending" },
  { idea: "Nobody talks about this productivity secret", type: "controversy", niche: "Tech", trending_score: 90, badge: "fast_growing" },
  { idea: "This is why you're stuck and how to fix it", type: "advice", niche: "Finance", trending_score: 89 },
  { idea: "What happens next will shock you", type: "shock", niche: "Lifestyle", trending_score: 88, badge: "trending" },
  { idea: "I tested every viral trend so you don't have to", type: "test", niche: "Entertainment", trending_score: 87 },
  { idea: "This one trick blew up my reach overnight", type: "growth", niche: "Business", trending_score: 86, badge: "fast_growing" },
  { idea: "Stop scrolling — this will save you hours", type: "hook", niche: "Tech", trending_score: 95, badge: "trending" },
];

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
        const fetched = data.ideas || [];
        // NEVER show empty — inject fallback if needed
        if (fetched.length < 3) {
          const fallback = selectedNiche
            ? FALLBACK_IDEAS.filter(i => i.niche === selectedNiche)
            : FALLBACK_IDEAS;
          setIdeas(fallback.length >= 3 ? fallback : FALLBACK_IDEAS);
        } else {
          setIdeas(fetched);
        }
        setNiches(data.niches || []);
      } else {
        setIdeas(FALLBACK_IDEAS);
      }
    } catch (e) {
      console.error(e);
      setIdeas(FALLBACK_IDEAS);
    }
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
                  {idea.badge === 'fast_growing' && idea.trending_score < 90 && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-400 flex items-center gap-0.5">
                      <Zap className="w-3 h-3" /> Fast growing
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
    </div>
  );
};

// ==================== PROGRESS VIEW ====================
const ProgressView = ({ jobId, onComplete, ideaText, ideaNiche }) => {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [pollCount, setPollCount] = useState(0);
  const [partialAssets, setPartialAssets] = useState([]);
  const pollRef = useRef(null);
  const startTime = useRef(Date.now());

  const pollStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        console.error(`[POLL] Status ${res.status} for job ${jobId}`);
        setPollCount(p => p + 1);
        return;
      }
      const data = await res.json();
      if (!data || !data.job_id) {
        console.error('[POLL] Malformed response', data);
        setPollCount(p => p + 1);
        return;
      }
      setJob(data);
      setPollCount(p => p + 1);

      // Fetch partial assets as they become available
      const completedTasks = (data.tasks || []).filter(t => t.status === 'completed' && t.task_type !== 'packaging');
      if (completedTasks.length > 0) {
        try {
          const assetsRes = await fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}/assets`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (assetsRes.ok) {
            const assetsData = await assetsRes.json();
            setPartialAssets(assetsData.assets || []);
          }
        } catch (e) { /* silent */ }
      }

      if (data.status === 'completed' || data.status === 'completed_with_fallbacks') {
        clearInterval(pollRef.current);
        onComplete(jobId);
      }
    } catch (e) {
      console.error('[POLL] Error:', e);
      setPollCount(p => p + 1);
    }
  }, [jobId, onComplete]);

  useEffect(() => {
    startTime.current = Date.now();
    pollStatus();
    pollRef.current = setInterval(pollStatus, 2000);
    return () => clearInterval(pollRef.current);
  }, [pollStatus]);

  const elapsedSec = Math.floor((Date.now() - startTime.current) / 1000);
  const isStale = pollCount > 5 && !job;
  const isTimeout = elapsedSec > 90;
  const progress = job?.progress || {};
  const tasks = job?.tasks || [];
  const taskOrder = ['hooks', 'script', 'captions', 'thumbnail', 'audio', 'video', 'packaging'];

  // Error: couldn't reach backend after several attempts
  if (isStale || error) {
    return (
      <div className="max-w-lg mx-auto space-y-4 py-8" data-testid="progress-error">
        <div className="bg-slate-900/80 border border-red-500/20 rounded-2xl p-6 text-center">
          <RefreshCw className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-white font-semibold mb-1">Having trouble loading status</p>
          <p className="text-sm text-slate-400 mb-4">{error || 'Connection issue — your pack is still generating'}</p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => { setError(null); setPollCount(0); pollStatus(); }} className="px-4 py-2 bg-orange-500 hover:bg-orange-400 text-white text-sm font-medium rounded-xl transition-colors" data-testid="retry-poll-btn">
              Retry Status
            </button>
            <Link to="/app/daily-viral-ideas" className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition-colors" data-testid="return-feed-btn">
              Return to Feed
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto space-y-6" data-testid="progress-view">
      {/* Idea Context — ALWAYS visible */}
      <div className="bg-slate-900/60 border border-slate-800/60 rounded-xl p-4" data-testid="progress-idea-context">
        <p className="text-white font-medium text-base">{ideaText || job?.idea || 'Generating your content pack...'}</p>
        <div className="flex items-center gap-2 mt-2">
          {(ideaNiche || job?.niche) && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-orange-500/20 text-orange-300">{ideaNiche || job?.niche}</span>
          )}
          <span className="text-xs text-slate-500">Started {elapsedSec}s ago</span>
        </div>
      </div>

      {/* Progress Circle */}
      <div className="text-center">
        <div className="relative inline-flex items-center justify-center w-28 h-28">
          <svg className="w-28 h-28 -rotate-90">
            <circle cx="56" cy="56" r="48" fill="none" stroke="#1e293b" strokeWidth="7" />
            <circle
              cx="56" cy="56" r="48" fill="none" stroke="url(#progressGrad)" strokeWidth="7"
              strokeLinecap="round" strokeDasharray={`${(progress.percentage || 5) * 3.02} 302`}
              className="transition-all duration-700"
            />
            <defs>
              <linearGradient id="progressGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f97316" />
                <stop offset="100%" stopColor="#ef4444" />
              </linearGradient>
            </defs>
          </svg>
          <span className="absolute text-xl font-bold text-white">{progress.percentage || 0}%</span>
        </div>
        <p className="mt-3 text-base font-semibold text-white">
          {isTimeout ? 'Still working on your pack...' : (progress.message || 'Setting up your content pack...')}
        </p>
        <p className="text-xs text-slate-500 mt-1">Usually takes 20-30 seconds</p>
      </div>

      {/* Task List — ALWAYS visible, shows skeleton before first poll */}
      <div className="space-y-2" data-testid="progress-tasks">
        {taskOrder.map((type) => {
          const task = tasks.find(t => t.task_type === type);
          const status = task?.status || 'pending';
          const Icon = PHASE_ICONS[`generating_${type}`] || PHASE_ICONS[type] || Clock;
          const label = type === 'hooks' ? 'Viral Hooks' : type === 'script' ? 'Video Script' : type === 'captions' ? 'Social Captions' : type === 'thumbnail' ? 'Thumbnail' : type === 'audio' ? 'Voiceover' : type === 'video' ? 'Social Video' : 'Final Package';
          return (
            <div
              key={type}
              className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-500 ${status === 'completed' ? 'bg-emerald-500/10 border border-emerald-500/20' : status === 'processing' ? 'bg-orange-500/10 border border-orange-500/20 animate-pulse' : 'bg-slate-800/40 border border-slate-800/60'}`}
              data-testid={`task-${type}`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${status === 'completed' ? 'bg-emerald-500/20' : status === 'processing' ? 'bg-orange-500/20' : 'bg-slate-700/40'}`}>
                {status === 'completed' ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : status === 'processing' ? (
                  <RefreshCw className="w-4 h-4 text-orange-400 animate-spin" />
                ) : (
                  <Icon className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <span className={`text-sm font-medium ${status === 'completed' ? 'text-emerald-300' : status === 'processing' ? 'text-orange-300' : 'text-slate-600'}`}>
                {label}
              </span>
              {task?.fallback_used && status === 'completed' && (
                <span className="ml-auto text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">alt</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Partial Assets Preview — show text assets as they arrive */}
      {partialAssets.length > 0 && (
        <div className="space-y-3" data-testid="partial-assets">
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Ready so far</p>
          {partialAssets.filter(a => a.asset_type === 'hooks' && a.content).map(a => (
            <div key={a.asset_id} className="bg-slate-900/60 border border-emerald-500/10 rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-[11px] font-semibold text-slate-400">Hooks Ready</span>
              </div>
              <p className="text-sm text-slate-300">{a.content.split('\n')[0]}</p>
            </div>
          ))}
          {partialAssets.filter(a => a.asset_type === 'thumbnail' && a.file_url).map(a => (
            <div key={a.asset_id} className="bg-slate-900/60 border border-emerald-500/10 rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Image className="w-3 h-3 text-violet-400" />
                <span className="text-[11px] font-semibold text-slate-400">Thumbnail Ready</span>
              </div>
              <img src={`${API_URL}${a.file_url.startsWith('/api') ? a.file_url : `/api${a.file_url}`}`} alt="" className="w-24 h-24 rounded-lg object-cover" />
            </div>
          ))}
        </div>
      )}

      {/* Timeout Recovery */}
      {isTimeout && (
        <div className="bg-slate-900/80 border border-amber-500/20 rounded-xl p-4 text-center space-y-3" data-testid="timeout-recovery">
          <p className="text-sm text-amber-300">Taking longer than usual</p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => { startTime.current = Date.now(); pollStatus(); }} className="px-3 py-1.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-medium rounded-lg transition-colors">
              Refresh Status
            </button>
            <Link to={`/app/daily-viral-ideas?job=${jobId}`} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors">
              Check Result
            </Link>
            <Link to="/app/daily-viral-ideas" className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors">
              Back to Ideas
            </Link>
          </div>
        </div>
      )}

      {/* Back action — ALWAYS available */}
      <div className="text-center">
        <Link to="/app/daily-viral-ideas" className="text-xs text-slate-600 hover:text-slate-400 transition-colors" data-testid="progress-back-link">
          <ArrowLeft className="w-3 h-3 inline mr-1" />Back to ideas
        </Link>
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
  const voiceover = assets.find(a => a.asset_type === 'voiceover');
  const video = assets.find(a => a.asset_type === 'video');
  const zipBundle = assets.find(a => a.asset_type === 'zip_bundle');
  const isLocked = job?.locked;

  const shareUrl = `${window.location.origin}/viral/${jobId}`;

  const handleShare = async (platform) => {
    const hookText = hooks?.content?.split('\n')[0] || job?.progress?.message || '';
    // Track share event
    try {
      await fetch(`${API_URL}/api/viral-ideas/share/${jobId}/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform, user_id: localStorage.getItem('userId') || 'anon' }),
      });
    } catch (e) { /* silent */ }

    if (platform === 'whatsapp') {
      window.open(`https://wa.me/?text=${encodeURIComponent(`${hookText}\n\n${shareUrl}?ref=wa`)}`, '_blank');
    } else if (platform === 'twitter') {
      window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(hookText)}&url=${encodeURIComponent(shareUrl + '?ref=tw')}`, '_blank');
    } else if (platform === 'copy') {
      navigator.clipboard.writeText(shareUrl);
      toast.success('Share link copied!');
    }
  };

  const handleUnlock = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}/unlock`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        toast.success('Pack unlocked!');
        fetchAssets(); // Reload with full content
      } else {
        toast.error(data.detail || 'Failed to unlock');
      }
    } catch (e) { toast.error('Failed to unlock'); }
  };

  return (
    <div className="space-y-6" data-testid="result-view">
      {/* Success Banner */}
      <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-5 text-center">
        <Check className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
        <h2 className="text-xl font-bold text-white">{isLocked ? 'Your Pack Preview is Ready' : 'Your Content Pack is Ready!'}</h2>
        {job && <p className="text-sm text-slate-400 mt-1">{job.progress?.message}</p>}
      </div>

      {/* Locked Banner */}
      {isLocked && (
        <div className="bg-gradient-to-r from-orange-500/10 to-amber-500/10 border border-orange-500/20 rounded-2xl p-5" data-testid="locked-banner">
          <div className="flex items-center gap-3 mb-3">
            <Lock className="w-5 h-5 text-orange-400" />
            <span className="text-white font-semibold">This pack is locked</span>
          </div>
          <p className="text-sm text-slate-400 mb-4">Unlock to download full content, remove watermarks, and access all assets.</p>
          <button
            onClick={handleUnlock}
            className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/20 transition-all"
            data-testid="unlock-pack-btn"
          >
            <Lock className="w-4 h-4" />
            Unlock This Pack (5 credits)
          </button>
        </div>
      )}

      {/* Share Buttons */}
      <div className="flex gap-2" data-testid="share-buttons">
        <button
          onClick={() => handleShare('whatsapp')}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#25D366]/15 hover:bg-[#25D366]/25 text-[#25D366] text-sm font-medium rounded-xl border border-[#25D366]/20 transition-all"
          data-testid="share-whatsapp-btn"
        >
          <MessageSquare className="w-4 h-4" /> WhatsApp
        </button>
        <button
          onClick={() => handleShare('twitter')}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-sky-500/15 hover:bg-sky-500/25 text-sky-400 text-sm font-medium rounded-xl border border-sky-500/20 transition-all"
          data-testid="share-twitter-btn"
        >
          <ArrowRight className="w-4 h-4" /> Twitter
        </button>
        <button
          onClick={() => handleShare('copy')}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800/60 hover:bg-slate-700 text-slate-400 text-sm font-medium rounded-xl border border-slate-700/50 transition-all"
          data-testid="share-copy-btn"
        >
          <Copy className="w-4 h-4" />
        </button>
      </div>

      {/* Download All — only if unlocked */}
      {!isLocked && zipBundle?.file_url && (
        <button
          onClick={() => downloadFile(zipBundle.file_url)}
          className="w-full flex items-center justify-center gap-2 py-3.5 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/20 transition-all"
          data-testid="download-all-btn"
        >
          <Download className="w-5 h-5" />
          Download Full Pack (ZIP)
        </button>
      )}

      {/* Video */}
      {video?.file_url && (
        <VideoAsset
          url={getAssetUrl(video.file_url)}
          isLocked={isLocked}
          onDownload={() => downloadFile(video.file_url)}
        />
      )}

      {/* Thumbnail */}
      {thumbnail?.file_url && (
        <ThumbnailAsset
          url={getAssetUrl(thumbnail.file_url)}
          isLocked={isLocked}
          onDownload={() => downloadFile(thumbnail.file_url)}
        />
      )}

      {/* Voiceover */}
      {voiceover?.file_url && !isLocked && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden" data-testid="asset-voiceover">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2"><Volume2 className="w-4 h-4 text-cyan-400" /><span className="text-sm font-semibold text-white">Voiceover</span></div>
            <button onClick={() => downloadFile(voiceover.file_url)} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1"><Download className="w-3 h-3" /> Download</button>
          </div>
          <div className="p-4"><audio controls className="w-full" src={getAssetUrl(voiceover.file_url)} /></div>
        </div>
      )}

      {/* Text Assets — truncated if locked */}
      {hooks?.content && (
        <AssetCard
          icon={<Zap className="w-4 h-4 text-amber-400" />}
          title="Viral Hooks"
          content={hooks.content}
          onCopy={!isLocked ? () => copyContent(hooks.content, 'hooks') : undefined}
          copied={copied === 'hooks'}
          locked={isLocked}
        />
      )}
      {script?.content && (
        <AssetCard
          icon={<FileText className="w-4 h-4 text-sky-400" />}
          title="Video Script"
          content={script.content}
          onCopy={!isLocked ? () => copyContent(script.content, 'script') : undefined}
          copied={copied === 'script'}
          locked={isLocked}
        />
      )}
      {captions?.content && (
        <AssetCard
          icon={<Copy className="w-4 h-4 text-emerald-400" />}
          title="Social Captions"
          content={captions.content}
          onCopy={!isLocked ? () => copyContent(captions.content, 'captions') : undefined}
          copied={copied === 'captions'}
          locked={isLocked}
        />
      )}

      {/* Feedback Panel */}
      <FeedbackPanel jobId={jobId} />

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

// ==================== FEEDBACK PANEL ====================
const FEEDBACK_SIGNALS = [
  { signal: 'useful', label: 'Useful', icon: ThumbsUp, color: 'text-emerald-400 hover:bg-emerald-500/20' },
  { signal: 'not_useful', label: 'Not useful', icon: ThumbsDown, color: 'text-red-400 hover:bg-red-500/20' },
  { signal: 'more_aggressive_hook', label: 'Punchier hooks', icon: Zap, color: 'text-amber-400 hover:bg-amber-500/20' },
  { signal: 'safer_hook', label: 'Safer hooks', icon: ShieldAlert, color: 'text-sky-400 hover:bg-sky-500/20' },
  { signal: 'better_captions', label: 'Better captions', icon: MessageSquare, color: 'text-violet-400 hover:bg-violet-500/20' },
  { signal: 'regenerate_angle', label: 'Different angle', icon: RotateCw, color: 'text-pink-400 hover:bg-pink-500/20' },
];

const FeedbackPanel = ({ jobId }) => {
  const [sent, setSent] = useState({});

  const sendFeedback = async (signal) => {
    if (sent[signal]) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/viral-ideas/jobs/${jobId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ signal }),
      });
      if (res.ok) {
        setSent(prev => ({ ...prev, [signal]: true }));
        toast.success('Feedback recorded');
      }
    } catch (e) { console.error(e); }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4" data-testid="feedback-panel">
      <div className="flex items-center gap-2 mb-3">
        <Heart className="w-4 h-4 text-pink-400" />
        <span className="text-sm font-semibold text-white">How was this pack?</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {FEEDBACK_SIGNALS.map(({ signal, label, icon: Icon, color }) => (
          <button
            key={signal}
            onClick={() => sendFeedback(signal)}
            disabled={sent[signal]}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700/60 transition-all ${sent[signal] ? 'bg-slate-700/50 text-slate-500 border-slate-700' : `${color} bg-slate-800/60`}`}
            data-testid={`feedback-${signal}`}
          >
            <Icon className="w-3.5 h-3.5" />
            {sent[signal] ? <Check className="w-3 h-3" /> : label}
          </button>
        ))}
      </div>
    </div>
  );
};

// ==================== ASSET CARD ====================
const AssetCard = ({ icon, title, content, onCopy, copied, locked }) => (
  <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden ${locked ? 'opacity-70' : ''}`} data-testid={`asset-${title.toLowerCase().replace(/\s/g, '-')}`}>
    <div className="p-4 border-b border-slate-800 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold text-white">{title}</span>
        {locked && <Lock className="w-3 h-3 text-orange-400" />}
      </div>
      {onCopy && !locked && (
        <button onClick={onCopy} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1">
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      )}
    </div>
    <div className="p-4 relative">
      <pre className={`text-sm text-slate-300 whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto ${locked ? 'select-none' : ''}`}>{content}</pre>
      {locked && <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-slate-900 to-transparent" />}
    </div>
  </div>
);

// ==================== VIDEO ASSET (with error handling) ====================
const VideoAsset = ({ url, isLocked, onDownload }) => {
  const [videoError, setVideoError] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const videoRef = useRef(null);

  const handleRetry = () => {
    setRetrying(true);
    setVideoError(false);
    if (videoRef.current) {
      videoRef.current.src = url + '?t=' + Date.now();
      videoRef.current.load();
    }
    setTimeout(() => setRetrying(false), 2000);
  };

  return (
    <div className={`bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden ${isLocked ? 'opacity-60' : ''}`} data-testid="asset-video">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Video className="w-4 h-4 text-rose-400" />
          <span className="text-sm font-semibold text-white">Social Video</span>
          {isLocked && <Lock className="w-3 h-3 text-orange-400" />}
        </div>
        {!isLocked && (
          <button onClick={onDownload} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1" data-testid="download-video-btn">
            <Download className="w-3 h-3" /> Download
          </button>
        )}
      </div>
      <div className="p-4 relative">
        {videoError ? (
          <div className="flex flex-col items-center justify-center py-8 text-center" data-testid="video-error-fallback">
            <Video className="w-10 h-10 text-slate-600 mb-3" />
            <p className="text-sm text-slate-400 mb-1">Video preview unavailable</p>
            <p className="text-xs text-slate-600 mb-3">Your video is ready — download to view</p>
            <div className="flex gap-2">
              <button onClick={handleRetry} disabled={retrying} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1" data-testid="retry-video-btn">
                <RefreshCw className={`w-3 h-3 ${retrying ? 'animate-spin' : ''}`} /> Retry
              </button>
              {!isLocked && (
                <button onClick={onDownload} className="px-3 py-1.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1" data-testid="download-video-fallback-btn">
                  <Download className="w-3 h-3" /> Download MP4
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              controls={!isLocked}
              className="w-full max-w-md mx-auto rounded-xl"
              src={url}
              style={isLocked ? { filter: 'blur(4px)' } : {}}
              onError={() => setVideoError(true)}
              preload="metadata"
              playsInline
              data-testid="video-player"
            />
            {isLocked && (
              <div className="absolute inset-0 flex items-center justify-center">
                <Lock className="w-8 h-8 text-orange-400/60" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// ==================== THUMBNAIL ASSET (with error handling) ====================
const ThumbnailAsset = ({ url, isLocked, onDownload }) => {
  const [imgError, setImgError] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const handleRetry = () => {
    setRetrying(true);
    setImgError(false);
    setTimeout(() => setRetrying(false), 2000);
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden" data-testid="asset-thumbnail">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Image className="w-4 h-4 text-violet-400" />
          <span className="text-sm font-semibold text-white">Thumbnail</span>
        </div>
        {!isLocked && (
          <button onClick={onDownload} className="text-xs text-orange-400 hover:text-orange-300 flex items-center gap-1" data-testid="download-thumbnail-btn">
            <Download className="w-3 h-3" /> Download
          </button>
        )}
      </div>
      <div className="p-4 relative">
        {imgError ? (
          <div className="flex flex-col items-center justify-center py-8 text-center" data-testid="thumbnail-error-fallback">
            <Image className="w-10 h-10 text-slate-600 mb-3" />
            <p className="text-sm text-slate-400 mb-1">Thumbnail preview unavailable</p>
            <p className="text-xs text-slate-600 mb-3">Download to view the full image</p>
            <div className="flex gap-2">
              <button onClick={handleRetry} disabled={retrying} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1" data-testid="retry-thumbnail-btn">
                <RefreshCw className={`w-3 h-3 ${retrying ? 'animate-spin' : ''}`} /> Retry
              </button>
              {!isLocked && (
                <button onClick={onDownload} className="px-3 py-1.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1" data-testid="download-thumbnail-fallback-btn">
                  <Download className="w-3 h-3" /> Download Image
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            <img
              src={imgError ? '' : (retrying ? url + '?t=' + Date.now() : url)}
              alt="Thumbnail"
              className="w-full max-w-xs mx-auto rounded-xl"
              style={isLocked ? { filter: 'blur(3px) brightness(0.7)' } : {}}
              onError={() => setImgError(true)}
              data-testid="thumbnail-image"
            />
            {isLocked && (
              <div className="absolute inset-4 flex items-center justify-center text-orange-400/40 text-4xl font-black tracking-widest select-none">PREVIEW</div>
            )}
          </>
        )}
      </div>
    </div>
  );
};


// ==================== MAIN PAGE ====================
const DailyViralIdeas = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState('feed');
  const [activeJobId, setActiveJobId] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [activeIdea, setActiveIdea] = useState('');
  const [activeNiche, setActiveNiche] = useState('');

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
        setActiveIdea(idea);
        setActiveNiche(niche);
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
        {view === 'progress' && activeJobId && <ProgressView jobId={activeJobId} onComplete={handleJobComplete} ideaText={activeIdea} ideaNiche={activeNiche} />}
        {view === 'result' && activeJobId && <ResultView jobId={activeJobId} />}
      </div>
    </div>
  );
};

export default DailyViralIdeas;
