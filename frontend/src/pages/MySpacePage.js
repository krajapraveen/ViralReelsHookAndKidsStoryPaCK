import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Play, Download, Share2, RefreshCw, AlertTriangle, Film, Loader2, ChevronDown, ChevronUp, Bell, BellOff, Check, Plus, X, Settings2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';

const STAGE_LABELS = {
  INIT: 'Queued',
  PLANNING: 'Writing script',
  BUILDING_CHARACTER_CONTEXT: 'Building characters',
  PLANNING_SCENE_MOTION: 'Planning scenes',
  GENERATING_KEYFRAMES: 'Creating artwork',
  GENERATING_SCENE_CLIPS: 'Composing scenes',
  GENERATING_AUDIO: 'Generating narration',
  ASSEMBLING_VIDEO: 'Rendering video',
  VALIDATING: 'Finalizing',
  READY: 'Completed',
  scenes: 'Planning scenes',
  images: 'Creating artwork',
  voices: 'Generating narration',
  render: 'Rendering video',
  upload: 'Finalizing',
};

const STAGE_COLORS = {
  PLANNING: '#818cf8',
  BUILDING_CHARACTER_CONTEXT: '#818cf8',
  PLANNING_SCENE_MOTION: '#818cf8',
  GENERATING_KEYFRAMES: '#f472b6',
  GENERATING_SCENE_CLIPS: '#f472b6',
  GENERATING_AUDIO: '#34d399',
  ASSEMBLING_VIDEO: '#fb923c',
  VALIDATING: '#fbbf24',
  scenes: '#818cf8',
  images: '#f472b6',
  voices: '#34d399',
  render: '#fb923c',
  upload: '#fbbf24',
};

function getStageLabel(job) {
  const state = job.engine_state || job.current_stage;
  return STAGE_LABELS[state] || job.current_step || 'Processing';
}

function getSubStage(job) {
  if (job.current_step && !job.current_step.startsWith('Your story')) {
    return job.current_step;
  }
  return null;
}

function getStageColor(job) {
  const state = job.engine_state || job.current_stage;
  return STAGE_COLORS[state] || '#60a5fa';
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function ProgressBar({ progress, color, animated }) {
  return (
    <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full"
        style={{
          width: `${Math.min(progress, 100)}%`,
          backgroundColor: color,
          transition: 'width 2s ease-in-out',
          animation: animated ? 'pulse 2s ease-in-out infinite' : 'none',
        }}
      />
    </div>
  );
}

function InProgressCard({ job, highlighted }) {
  const color = getStageColor(job);
  const stageLabel = getStageLabel(job);
  const subStage = getSubStage(job);
  const progress = job.progress || 0;

  return (
    <div
      data-testid={`project-card-${job.job_id}`}
      className={`relative bg-zinc-900/80 border rounded-xl p-4 transition-all duration-500 ${
        highlighted ? 'border-indigo-500 ring-1 ring-indigo-500/30' : 'border-white/10'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="w-16 h-16 rounded-lg bg-zinc-800 flex items-center justify-center overflow-hidden flex-shrink-0">
          {job.thumbnail_url ? (
            <img src={job.thumbnail_url} alt="" className="w-full h-full object-cover" />
          ) : (
            <Film className="w-6 h-6 text-zinc-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-white truncate">{job.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: color }} />
              <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: color }} />
            </span>
            <span className="text-xs font-medium" style={{ color }}>{stageLabel}</span>
          </div>
          {subStage && (
            <p className="text-[11px] text-zinc-500 mt-0.5 truncate">{subStage}</p>
          )}
        </div>
        <span className="text-xs font-mono text-zinc-500">{progress}%</span>
      </div>
      <div className="mt-3">
        <ProgressBar progress={progress} color={color} animated={true} />
      </div>
      <div className="flex justify-between items-center mt-2">
        <span className="text-[10px] text-zinc-600">{timeAgo(job.created_at)}</span>
      </div>
    </div>
  );
}

function CompletedCard({ job, highlighted, justCompleted, onShareWhatsApp }) {
  const handleDownload = async (e) => {
    e.stopPropagation();
    triggerDownload(job);
  };

  const handleWatch = () => {
    if (job.output_url) {
      window.open(job.output_url, '_blank');
    }
  };

  return (
    <div
      data-testid={`project-card-${job.job_id}`}
      className={`group relative bg-zinc-900/80 border rounded-xl overflow-hidden transition-all duration-500 hover:border-white/20 ${
        justCompleted
          ? 'border-emerald-400 ring-2 ring-emerald-400/40'
          : highlighted
            ? 'border-emerald-500 ring-1 ring-emerald-500/30'
            : 'border-white/10'
      }`}
    >
      {justCompleted && (
        <div className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/90 text-[10px] font-bold text-white" data-testid="just-completed-badge">
          <Check className="w-3 h-3" /> Ready
        </div>
      )}
      <div className="relative aspect-video bg-zinc-800 cursor-pointer" onClick={handleWatch}>
        {job.thumbnail_url ? (
          <img src={job.thumbnail_url} alt={job.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Film className="w-8 h-8 text-zinc-700" />
          </div>
        )}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Play className="w-10 h-10 text-white fill-white" />
        </div>
      </div>
      <div className="p-3">
        <h3 className="text-sm font-medium text-white truncate">{job.title}</h3>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] text-emerald-400 font-medium">Completed</span>
          <span className="text-[10px] text-zinc-600">{timeAgo(job.completed_at || job.created_at)}</span>
        </div>
        <div className="flex gap-2 mt-3">
          <button
            data-testid={`watch-btn-${job.job_id}`}
            onClick={handleWatch}
            className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs text-white transition-colors"
          >
            <Play className="w-3 h-3" /> Watch
          </button>
          <button
            data-testid={`download-btn-${job.job_id}`}
            onClick={handleDownload}
            className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs text-white transition-colors"
          >
            <Download className="w-3 h-3" /> Download
          </button>
          <button
            data-testid={`share-btn-${job.job_id}`}
            onClick={(e) => { e.stopPropagation(); onShareWhatsApp(job); }}
            className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-xs text-emerald-300 transition-colors"
          >
            <Share2 className="w-3 h-3" /> Share
          </button>
        </div>
      </div>
    </div>
  );
}

function FailedCard({ job, onRetry }) {
  const errorMsg = job.error || job.current_step || 'An error occurred during generation';

  return (
    <div
      data-testid={`project-card-${job.job_id}`}
      className="relative bg-zinc-900/80 border border-red-900/30 rounded-xl p-4"
    >
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-lg bg-red-950/50 flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="w-5 h-5 text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-white truncate">{job.title}</h3>
          <p className="text-[11px] text-red-400/80 mt-1 line-clamp-2">{errorMsg}</p>
        </div>
      </div>
      <div className="flex justify-between items-center mt-3">
        <span className="text-[10px] text-zinc-600">{timeAgo(job.created_at)}</span>
        {job.has_recoverable_assets && (
          <button
            onClick={() => onRetry(job)}
            className="flex items-center gap-1 px-3 py-1 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-xs text-red-300 transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ title, count, icon: Icon, color, collapsed, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between py-2 group"
      data-testid={`section-${title.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="text-sm font-semibold text-zinc-300">{title}</span>
        {count > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: color + '20', color }}>
            {count}
          </span>
        )}
      </div>
      {collapsed ? <ChevronDown className="w-4 h-4 text-zinc-600" /> : <ChevronUp className="w-4 h-4 text-zinc-600" />}
    </button>
  );
}

// ─── DOWNLOAD HELPER ──────────────────────────────────────────────────────────
function triggerDownload(job) {
  if (!job.output_url) {
    toast.error('Video not available for download');
    return;
  }
  try {
    const a = document.createElement('a');
    a.href = job.output_url;
    a.download = `${(job.title || 'video').replace(/[^a-z0-9]/gi, '-').toLowerCase()}-visionary-suite.mp4`;
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {
    window.open(job.output_url, '_blank');
  }
}

// ─── NOTIFICATION HELPERS ─────────────────────────────────────────────────────
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function fireBrowserNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      const n = new Notification(title, {
        body,
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        tag: 'video-complete',
        renotify: true,
      });
      n.onclick = () => {
        window.focus();
        n.close();
      };
    } catch {
      // Silent fail
    }
  }
}

// ─── COMPLETION PROMPT MODAL ──────────────────────────────────────────────────
function CompletionPromptModal({ job, onClose, onDownload, onShareWhatsApp, onCreateAnother }) {
  if (!job) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="completion-prompt-modal">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-zinc-900 border border-zinc-700/50 rounded-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <style>{`@keyframes pulseShare { 0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); } 50% { box-shadow: 0 0 0 12px rgba(16,185,129,0); } }`}</style>
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 p-1 rounded-full bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
          data-testid="completion-prompt-close"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Thumbnail */}
        <div className="relative aspect-video bg-zinc-800">
          {job.thumbnail_url ? (
            <img src={job.thumbnail_url} alt={job.title} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Film className="w-12 h-12 text-zinc-600" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-900 via-transparent to-transparent" />
          <div className="absolute bottom-3 left-3 right-3">
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">Ready</span>
            </div>
            <h3 className="text-white font-semibold text-base truncate" data-testid="completion-prompt-title">{job.title}</h3>
          </div>
        </div>

        {/* Actions — Share is PRIMARY */}
        <div className="p-4 space-y-2">
          <p className="text-xs text-center text-amber-300/80 font-medium mb-1" data-testid="viral-nudge">
            This video can go viral — share it now
          </p>
          <button
            onClick={() => { onShareWhatsApp(job); }}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition-colors"
            style={{ animation: 'pulseShare 2.5s infinite' }}
            data-testid="completion-prompt-whatsapp"
          >
            <Share2 className="w-5 h-5" />
            Share with Friends
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => { onDownload(job); onClose(); }}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/10 text-white text-sm hover:bg-white/15 transition-colors"
              data-testid="completion-prompt-download"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
            <button
              onClick={() => { onCreateAnother(); onClose(); }}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/10 text-zinc-300 text-sm hover:bg-white/15 hover:text-white transition-colors"
              data-testid="completion-prompt-create-another"
            >
              <Plus className="w-4 h-4" />
              Create Another
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
export default function MySpacePage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [collapsedSections, setCollapsedSections] = useState({});
  const [justCompletedIds, setJustCompletedIds] = useState(new Set());
  const [completionPromptJob, setCompletionPromptJob] = useState(null);
  const [autoDownload, setAutoDownload] = useState(() => {
    try { return localStorage.getItem('vs_auto_download') === 'true'; } catch { return false; }
  });
  const [notificationsEnabled, setNotificationsEnabled] = useState(
    'Notification' in window && Notification.permission === 'granted'
  );
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('projectId');
  const highlightRef = useRef(null);
  const pollRef = useRef(null);
  const prevStatusMap = useRef({});
  const promptedJobIds = useRef(new Set());

  const fetchJobs = useCallback(async () => {
    try {
      const [storyRes, reelRes] = await Promise.allSettled([
        api.get('/api/story-engine/user-jobs?limit=100'),
        api.get('/api/convert/user-reels').catch(() => ({ data: { reels: [] } })),
      ]);

      const allItems = [];

      if (storyRes.status === 'fulfilled' && storyRes.value?.data?.jobs) {
        for (const j of storyRes.value.data.jobs) {
          allItems.push({ ...j, type: 'story_video' });
        }
      }

      if (reelRes.status === 'fulfilled' && reelRes.value?.data?.reels) {
        for (const r of reelRes.value.data.reels) {
          allItems.push({
            job_id: r.reel_id || r.id,
            title: r.title || 'Reel',
            type: 'reel',
            status: r.status === 'completed' ? 'COMPLETED' : r.status === 'failed' ? 'FAILED' : 'PROCESSING',
            thumbnail_url: r.thumbnail_url,
            output_url: r.output_url || r.video_url,
            progress: r.status === 'completed' ? 100 : 50,
            created_at: r.created_at,
            completed_at: r.completed_at,
          });
        }
      }

      allItems.sort((a, b) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0;
        const db_ = b.created_at ? new Date(b.created_at).getTime() : 0;
        return db_ - da;
      });

      // ── Detect newly completed jobs ──────────────────────────────────
      const newlyCompleted = [];
      for (const item of allItems) {
        const prevStatus = prevStatusMap.current[item.job_id];
        const curStatus = item.status;
        if (prevStatus && prevStatus !== 'COMPLETED' && curStatus === 'COMPLETED') {
          newlyCompleted.push(item);
        }
      }

      // Update previous status map
      const newMap = {};
      for (const item of allItems) {
        newMap[item.job_id] = item.status;
      }
      prevStatusMap.current = newMap;

      // Handle newly completed jobs
      for (const item of newlyCompleted) {
        // Toast notification
        toast.success(
          `Your video "${item.title}" is ready!`,
          { duration: 8000, id: `complete-${item.job_id}` }
        );

        // Browser notification
        fireBrowserNotification(
          'Your video is ready!',
          `"${item.title}" has finished rendering. Watch it now.`
        );

        // Mark as just completed (green glow)
        setJustCompletedIds(prev => new Set([...prev, item.job_id]));
        setTimeout(() => {
          setJustCompletedIds(prev => {
            const next = new Set(prev);
            next.delete(item.job_id);
            return next;
          });
        }, 30000);

        // Auto-download if preference is on
        if (autoDownload && item.output_url) {
          triggerDownload(item);
          toast.info(`Auto-downloading "${item.title}"`, { duration: 3000 });
        }

        // Show completion prompt (only once per job)
        if (!promptedJobIds.current.has(item.job_id)) {
          promptedJobIds.current.add(item.job_id);
          setCompletionPromptJob(item);
        }
      }

      setJobs(allItems);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setLoading(false);
    }
  }, [autoDownload]);

  useEffect(() => {
    fetchJobs();
    requestNotificationPermission();
  }, [fetchJobs]);

  // Auto-poll for in-progress items
  useEffect(() => {
    const hasInProgress = jobs.some(j =>
      !['COMPLETED', 'FAILED', 'ARCHIVED', 'ORPHANED', 'PARTIAL'].includes(j.status)
    );

    if (hasInProgress) {
      pollRef.current = setInterval(fetchJobs, 4000);
    } else if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs, fetchJobs]);

  // Auto-scroll to highlighted project
  useEffect(() => {
    if (highlightId && highlightRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 300);
    }
  }, [highlightId, jobs]);

  const handleRetry = (job) => {
    window.location.href = `/app/story-video-studio?projectId=${job.job_id}`;
  };

  const handleShareWhatsApp = async (job) => {
    try {
      const res = await api.post(`/api/story-engine/share-link/${job.job_id}`);
      if (res.data?.whatsapp_url) {
        window.open(res.data.whatsapp_url, '_blank');
      }
    } catch {
      const shareUrl = `${window.location.origin}/share/${job.job_id}`;
      const text = encodeURIComponent(
        `Check out my AI video: ${job.title}\n\n${shareUrl}\n\nMade with Visionary Suite`
      );
      window.open(`https://wa.me/?text=${text}`, '_blank');
    }
  };

  const handleCreateAnother = () => {
    navigate('/app/story-video-studio');
  };

  const toggleSection = (section) => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const toggleAutoDownload = () => {
    setAutoDownload(prev => {
      const next = !prev;
      try { localStorage.setItem('vs_auto_download', String(next)); } catch {}
      toast.success(next ? 'Auto-download enabled' : 'Auto-download disabled', { duration: 2000 });
      return next;
    });
  };

  const toggleNotifications = () => {
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        setNotificationsEnabled(prev => !prev);
      } else if (Notification.permission === 'default') {
        Notification.requestPermission().then(perm => {
          setNotificationsEnabled(perm === 'granted');
        });
      } else {
        toast.error('Notifications are blocked. Enable them in browser settings.');
      }
    }
  };

  // Categorize jobs
  const inProgress = jobs.filter(j => ['QUEUED', 'PROCESSING'].includes(j.status));
  const completed = jobs.filter(j => ['COMPLETED', 'PARTIAL'].includes(j.status));
  const failed = jobs.filter(j => ['FAILED'].includes(j.status));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="myspace-loading">
        <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4" data-testid="myspace-empty">
        <Film className="w-12 h-12 text-zinc-700" />
        <p className="text-zinc-500 text-sm">No projects yet</p>
        <a
          href="/app/story-video-studio"
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors"
          data-testid="create-first-video-btn"
        >
          Create your first video
        </a>
      </div>
    );
  }

  return (
    <>
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="myspace-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">My Space</h1>
          <div className="flex items-center gap-1">
            {/* Auto-download toggle */}
            <button
              onClick={toggleAutoDownload}
              className={`p-2 rounded-lg transition-colors ${
                autoDownload
                  ? 'bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30'
                  : 'hover:bg-white/5 text-zinc-500 hover:text-white'
              }`}
              data-testid="toggle-auto-download-btn"
              title={autoDownload ? 'Auto-download on' : 'Auto-download off'}
            >
              <Download className="w-4 h-4" />
            </button>
            {/* Notification toggle */}
            <button
              onClick={toggleNotifications}
              className={`p-2 rounded-lg transition-colors ${
                notificationsEnabled
                  ? 'bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30'
                  : 'hover:bg-white/5 text-zinc-500 hover:text-white'
              }`}
              data-testid="toggle-notifications-btn"
              title={notificationsEnabled ? 'Notifications on' : 'Notifications off'}
            >
              {notificationsEnabled ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            </button>
            {/* Refresh */}
            <button
              onClick={fetchJobs}
              className="p-2 rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-colors"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* In Progress Section */}
        {inProgress.length > 0 && (
          <section>
            <SectionHeader
              title="In Progress"
              count={inProgress.length}
              icon={Loader2}
              color="#60a5fa"
              collapsed={collapsedSections.inProgress}
              onToggle={() => toggleSection('inProgress')}
            />
            {!collapsedSections.inProgress && (
              <div className="space-y-3 mt-2">
                {inProgress.map(job => (
                  <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                    <InProgressCard job={job} highlighted={job.job_id === highlightId} />
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Completed Section */}
        <section>
          <SectionHeader
            title="Completed"
            count={completed.length}
            icon={Play}
            color="#34d399"
            collapsed={collapsedSections.completed}
            onToggle={() => toggleSection('completed')}
          />
          {!collapsedSections.completed && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-2">
              {completed.map(job => (
                <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                  <CompletedCard
                    job={job}
                    highlighted={job.job_id === highlightId}
                    justCompleted={justCompletedIds.has(job.job_id)}
                    onShareWhatsApp={handleShareWhatsApp}
                  />
                </div>
              ))}
            </div>
          )}
          {completed.length === 0 && !collapsedSections.completed && (
            <p className="text-zinc-600 text-xs py-4 text-center">No completed projects yet</p>
          )}
        </section>

        {/* Create Another — Retention Loop */}
        <section className="border border-white/[0.06] rounded-xl p-4 bg-white/[0.02]" data-testid="create-another-section">
          <h3 className="text-sm font-semibold text-zinc-300 mb-3">Create another video</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { label: 'New story', desc: 'Start fresh', path: '/app/story-video-studio' },
              { label: 'Different style', desc: 'Try anime or 3D', path: '/app/story-video-studio?style=explore' },
              { label: 'Make it funny', desc: 'Comedy twist', path: '/app/story-video-studio?tone=comedy' },
              { label: 'Kids story', desc: 'Family friendly', path: '/app/story-video-studio?age=kids' },
            ].map(item => (
              <button
                key={item.label}
                onClick={() => navigate(item.path)}
                className="text-left p-3 rounded-lg bg-zinc-900/60 border border-white/[0.06] hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all group"
                data-testid={`create-${item.label.toLowerCase().replace(/\s/g, '-')}-btn`}
              >
                <p className="text-xs font-medium text-white group-hover:text-indigo-300 transition-colors">{item.label}</p>
                <p className="text-[10px] text-zinc-500 mt-0.5">{item.desc}</p>
              </button>
            ))}
          </div>
        </section>

        {/* Failed Section */}
        {failed.length > 0 && (
          <section>
            <SectionHeader
              title="Failed"
              count={failed.length}
              icon={AlertTriangle}
              color="#f87171"
              collapsed={collapsedSections.failed}
              onToggle={() => toggleSection('failed')}
            />
            {!collapsedSections.failed && (
              <div className="space-y-3 mt-2">
                {failed.map(job => (
                  <div key={job.job_id} ref={job.job_id === highlightId ? highlightRef : null}>
                    <FailedCard job={job} onRetry={handleRetry} />
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>

      {/* Completion Prompt Modal */}
      {completionPromptJob && (
        <CompletionPromptModal
          job={completionPromptJob}
          onClose={() => setCompletionPromptJob(null)}
          onDownload={triggerDownload}
          onShareWhatsApp={handleShareWhatsApp}
          onCreateAnother={handleCreateAnother}
        />
      )}
    </>
  );
}
