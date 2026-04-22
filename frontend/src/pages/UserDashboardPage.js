import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Film, Coins, TrendingUp, CheckCircle, AlertCircle, Clock, Activity, Loader2, RefreshCw, Gift, ArrowRight } from 'lucide-react';
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

function StatCard({ icon: Icon, label, value, color, subtitle }) {
  return (
    <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-5" data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5 text-white" />
        </div>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function ActivityItem({ item }) {
  const statusColor = item.status === 'COMPLETED' || item.status === 'READY' ? 'text-emerald-400' :
    item.status === 'FAILED' ? 'text-red-400' : 'text-blue-400';
  const StatusIcon = item.status === 'COMPLETED' || item.status === 'READY' ? CheckCircle :
    item.status === 'FAILED' ? AlertCircle : Activity;

  return (
    <div className="flex items-center gap-3 py-3 border-b border-slate-800/50 last:border-0">
      <StatusIcon className={`w-4 h-4 ${statusColor} flex-shrink-0`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white truncate">{item.title || 'Untitled'}</p>
        <p className="text-[11px] text-slate-500">{item.type}</p>
      </div>
      <span className="text-[11px] text-slate-500 flex-shrink-0">{item.time_ago}</span>
    </div>
  );
}

export default function UserDashboardPage() {
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [jobsRes, creditRes] = await Promise.allSettled([
        api.get('/api/story-engine/user-jobs?limit=100'),
        api.get('/api/credits/balance'),
      ]);

      const jobs = jobsRes.status === 'fulfilled' && jobsRes.value.data.success ? jobsRes.value.data.jobs : [];
      const credits = creditRes.status === 'fulfilled' && creditRes.value.data.credits !== undefined ? creditRes.value.data.credits : null;

      const total = jobs.length;
      const completed = jobs.filter(j => j.status === 'COMPLETED' || j.status === 'READY').length;
      const failed = jobs.filter(j => j.status === 'FAILED').length;
      const processing = jobs.filter(j => !['COMPLETED', 'READY', 'FAILED', 'PARTIAL_READY'].includes(j.status)).length;

      setStats({
        total,
        completed,
        failed,
        processing,
        credits: credits ?? 'N/A',
        successRate: total > 0 ? Math.round(completed / total * 100) : 0,
      });

      // Build activity feed
      const now = Date.now();
      setActivity(jobs.slice(0, 10).map(j => {
        const diff = now - new Date(j.created_at || 0).getTime();
        const mins = Math.floor(diff / 60000);
        let time_ago = 'Just now';
        if (mins >= 60 * 24) time_ago = `${Math.floor(mins / 1440)}d ago`;
        else if (mins >= 60) time_ago = `${Math.floor(mins / 60)}h ago`;
        else if (mins >= 1) time_ago = `${mins}m ago`;
        return {
          id: j.job_id,
          title: j.title,
          status: j.status,
          type: (j.animation_style || 'story_video').replace('_', ' '),
          time_ago,
        };
      }));
    } catch {
      setError(true);
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center" data-testid="dashboard-error-state">
        <div className="text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Failed to load dashboard</h2>
          <p className="text-sm text-slate-400">Check your connection and try again</p>
          <button onClick={fetchData} className="px-5 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium inline-flex items-center gap-2" data-testid="dashboard-retry-btn">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white" data-testid="user-dashboard-page">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Your creation activity and stats at a glance</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard icon={Film} label="Total Creations" value={stats?.total ?? 0} color="bg-purple-500/20" />
          <StatCard icon={Coins} label="Credits" value={stats?.credits ?? 'N/A'} color="bg-amber-500/20" />
          <StatCard icon={CheckCircle} label="Success Rate" value={`${stats?.successRate ?? 0}%`} color="bg-emerald-500/20"
            subtitle={`${stats?.completed ?? 0} completed, ${stats?.failed ?? 0} failed`} />
          <StatCard icon={Activity} label="In Progress" value={stats?.processing ?? 0} color="bg-blue-500/20" />
        </div>

        {/* Invite & Earn card */}
        <Link
          to="/app/referrals"
          className="block mb-8 relative rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-500/[0.08] to-rose-500/[0.06] p-5 hover:border-violet-500/40 transition-colors overflow-hidden group"
          data-testid="dashboard-invite-card"
        >
          <div className="absolute inset-0 pointer-events-none opacity-60" style={{ background: 'radial-gradient(ellipse 60% 50% at 100% 0%, rgba(168,85,247,0.12), transparent 60%)' }} />
          <div className="relative flex items-center gap-4 flex-wrap">
            <div className="w-11 h-11 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center shrink-0">
              <Gift className="w-5 h-5 text-violet-300" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] tracking-[0.12em] text-violet-300/90 font-semibold uppercase mb-0.5">Invite & Earn</p>
              <h3 className="text-lg font-bold text-white">Invite Friends. Earn 300 Credits.</h3>
              <p className="text-xs text-slate-400 mt-0.5">Share your invite link. When friends create their first project, you earn 300 credits.</p>
            </div>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-violet-300 group-hover:text-violet-200">
              Get your link <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </div>
        </Link>

        {/* Two column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Success / Failure breakdown */}
          <div className="bg-slate-800/20 border border-slate-700/30 rounded-xl p-6" data-testid="breakdown-card">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Generation Breakdown</h3>
            <div className="space-y-3">
              {[
                { label: 'Completed', count: stats?.completed ?? 0, total: stats?.total ?? 1, color: 'bg-emerald-500' },
                { label: 'Failed', count: stats?.failed ?? 0, total: stats?.total ?? 1, color: 'bg-red-500' },
                { label: 'Processing', count: stats?.processing ?? 0, total: stats?.total ?? 1, color: 'bg-blue-500' },
              ].map(item => (
                <div key={item.label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">{item.label}</span>
                    <span className="text-slate-500">{item.count}</span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full transition-all`}
                      style={{ width: `${Math.round(item.count / Math.max(item.total, 1) * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-slate-800/20 border border-slate-700/30 rounded-xl p-6" data-testid="activity-feed">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Recent Activity</h3>
            {activity.length === 0 ? (
              <p className="text-slate-500 text-sm py-4">No activity yet</p>
            ) : (
              <div className="max-h-72 overflow-y-auto">
                {activity.map(item => (
                  <ActivityItem key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
