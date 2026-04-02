import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  Users, Eye, Activity, FileText, DollarSign, Star, RefreshCw,
  AlertTriangle, TrendingUp, Zap, Shield, Heart, BookOpen,
  Film, Clock, Server, Database, BarChart3,
  CheckCircle, XCircle, MinusCircle, Radio, Gift, Target, Share2, Camera
} from 'lucide-react';

// ─── Widget State System ─────────────────────────────────────────────────────
// Every widget has: LOADING | READY | EMPTY | ERROR | STALE
const STALE_MS = { summary: 30000, funnel: 30000, reliability: 15000, revenue: 60000, series: 30000 };

function WidgetState({ state, lastUpdated, children }) {
  if (state === 'loading') {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }
  if (state === 'error') {
    return (
      <div className="flex items-center justify-center py-8 gap-2">
        <AlertTriangle className="w-4 h-4 text-red-400" />
        <span className="text-sm text-red-400">Failed to load data</span>
      </div>
    );
  }
  return (
    <div className="relative">
      {children}
      {lastUpdated && (
        <div className="absolute top-2 right-2 text-[9px] text-slate-600">
          {Math.round((Date.now() - new Date(lastUpdated).getTime()) / 1000)}s ago
        </div>
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, color = 'slate', state = 'ready', testId }) {
  const colors = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20',
    slate: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  };
  const c = colors[color] || colors.slate;

  const displayValue = state === 'loading' ? '...' : (value === null || value === undefined) ? 'No data' : value;
  const isNoData = displayValue === 'No data';

  return (
    <div className={`rounded-xl border p-4 ${c}`} data-testid={testId}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-[11px] font-medium uppercase tracking-wider opacity-80">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${isNoData ? 'text-slate-600 text-base' : 'text-white'}`}>{displayValue}</p>
      {sub && <p className="text-[11px] mt-1 opacity-70">{sub}</p>}
    </div>
  );
}

function HealthBadge({ status }) {
  const config = {
    healthy: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    degraded: { icon: MinusCircle, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    critical: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  };
  const c = config[status] || config.healthy;
  const Icon = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${c.color} ${c.bg}`}>
      <Icon className="w-3 h-3" /> {status}
    </span>
  );
}

function FunnelBar({ label, value, rate, maxValue }) {
  const width = maxValue ? Math.max((value / maxValue) * 100, 2) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-32 text-right flex-shrink-0">{label}</span>
      <div className="flex-1 h-5 bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full transition-all" style={{ width: `${width}%` }} />
      </div>
      <span className="text-xs text-white font-mono w-16 text-right">{value ?? 0}</span>
      {rate !== null && rate !== undefined && (
        <span className="text-[10px] text-slate-500 w-12 text-right">{rate}%</span>
      )}
    </div>
  );
}

// Credit Reset Widget
function CreditResetWidget() {
  const [resetCredits, setResetCredits] = useState(50);
  const [resetLoading, setResetLoading] = useState(false);
  const [dryRunResult, setDryRunResult] = useState(null);

  const handleDryRun = async () => {
    try {
      const res = await api.post('/api/admin/metrics/credit-reset', { credits: resetCredits, dry_run: true });
      if (res.data.success) setDryRunResult(res.data);
    } catch { toast.error('Dry run failed'); }
  };

  const handleReset = async () => {
    if (!dryRunResult) { toast.error('Run dry run first'); return; }
    if (!window.confirm(`Reset ${dryRunResult.affected_users} users to ${resetCredits} credits? This cannot be undone.`)) return;
    setResetLoading(true);
    try {
      const res = await api.post('/api/admin/metrics/credit-reset', { credits: resetCredits, dry_run: false });
      if (res.data.success) {
        toast.success(`Reset ${res.data.affected_users} users to ${resetCredits} credits`);
        setDryRunResult(null);
      }
    } catch { toast.error('Credit reset failed'); }
    setResetLoading(false);
  };

  return (
    <div className="bg-slate-900/60 border border-amber-800/30 rounded-xl p-6" data-testid="credit-reset-widget">
      <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" /> Credit Reset (Admin Action)
      </h3>
      <p className="text-xs text-slate-400 mb-4">Reset all normal users to a set number of credits. Excludes admin/test/uat/dev roles.</p>
      <div className="flex items-center gap-3 mb-3">
        <input type="number" value={resetCredits} onChange={(e) => setResetCredits(Number(e.target.value))}
          className="w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-sm text-white" min={0} max={1000} data-testid="credit-reset-input" />
        <span className="text-xs text-slate-500">credits per user</span>
        <Button size="sm" variant="outline" onClick={handleDryRun} className="text-xs" data-testid="credit-reset-dry-run">Dry Run</Button>
        {dryRunResult && (
          <Button size="sm" onClick={handleReset} disabled={resetLoading}
            className="text-xs bg-amber-600 hover:bg-amber-500 text-white" data-testid="credit-reset-execute">
            {resetLoading ? 'Resetting...' : `Reset ${dryRunResult.affected_users} users`}
          </Button>
        )}
      </div>
      {dryRunResult && (
        <p className="text-xs text-amber-400/70">Dry run: {dryRunResult.affected_users} users will be set to {dryRunResult.new_credits} credits</p>
      )}
    </div>
  );
}


// Email Nudge Status Widget
function EmailNudgeStatus() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/retention/admin/email-nudges');
        if (res.data.success) setData(res.data);
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (loading) return null;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="email-nudge-status">
      <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4 text-emerald-400" /> Email Nudge System
      </h3>
      <div className="flex items-center gap-3 mb-4">
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${
          data?.email_service_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${data?.email_service_active ? 'bg-emerald-400' : 'bg-red-400'}`} />
          {data?.email_service_active ? 'Resend Active' : 'Resend Inactive'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-[10px] text-slate-500 mb-1">Emails Sent</p>
          <p className="text-lg font-bold text-emerald-400">{data?.sent_count ?? 0}</p>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-[10px] text-slate-500 mb-1">Pending</p>
          <p className="text-lg font-bold text-amber-400">{data?.pending_count ?? 0}</p>
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [section, setSection] = useState('executive');
  const [days, setDays] = useState(30);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef(null);

  // Data stores with states
  const [summary, setSummary] = useState({ data: null, state: 'loading', ts: null });
  const [funnel, setFunnel] = useState({ data: null, state: 'loading', ts: null });
  const [reliability, setReliability] = useState({ data: null, state: 'loading', ts: null });
  const [revenue, setRevenue] = useState({ data: null, state: 'loading', ts: null });
  const [series, setSeries] = useState({ data: null, state: 'loading', ts: null });
  const [credits, setCredits] = useState({ data: null, state: 'loading', ts: null });
  const [conversion, setConversion] = useState({ data: null, state: 'loading', ts: null });
  const [abResults, setAbResults] = useState({ data: null, state: 'loading', ts: null });
  const [leaderboard, setLeaderboard] = useState({ data: null, state: 'loading', ts: null });
  const [kFactor, setKFactor] = useState({ data: null, state: 'loading', ts: null });
  const [shareRewards, setShareRewards] = useState({ data: null, state: 'loading', ts: null });
  const [hookAnalytics, setHookAnalytics] = useState({ data: null, state: 'loading', ts: null });
  const [comicHealth, setComicHealth] = useState({ data: null, state: 'loading', ts: null });

  const fetchSection = useCallback(async (name, setter, url) => {
    try {
      const res = await api.get(url);
      if (res.data.success) {
        setter({ data: res.data, state: 'ready', ts: new Date().toISOString() });
      } else {
        setter(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
      }
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/app');
        return;
      }
      setter(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
    }
  }, [navigate]);

  const fetchAll = useCallback(() => {
    fetchSection('summary', setSummary, `/api/admin/metrics/summary?days=${days}`);
    fetchSection('funnel', setFunnel, `/api/admin/metrics/funnel?days=${days}`);
    fetchSection('reliability', setReliability, '/api/admin/metrics/reliability');
    fetchSection('revenue', setRevenue, `/api/admin/metrics/revenue?days=${days}`);
    fetchSection('series', setSeries, '/api/admin/metrics/series');
    fetchSection('credits', setCredits, '/api/admin/metrics/credits');
    fetchSection('conversion', setConversion, '/api/admin/metrics/conversion');
    fetchSection('ab', setAbResults, '/api/ab/results');
    fetchSection('leaderboard', setLeaderboard, '/api/admin/metrics/leaderboard');
    // K-factor endpoint doesn't return {success: true}, handle separately
    (async () => {
      try {
        const res = await api.get('/api/growth/viral-coefficient?days=' + days);
        if (res.data?.viral_coefficient_K !== undefined) {
          setKFactor({ data: res.data, state: 'ready', ts: new Date().toISOString() });
        } else {
          setKFactor(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
        }
      } catch {
        setKFactor(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
      }
    })();
    // Share rewards metrics
    (async () => {
      try {
        const res = await api.get('/api/admin/metrics/share-rewards');
        setShareRewards({ data: res.data, state: 'ready', ts: new Date().toISOString() });
      } catch {
        setShareRewards(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
      }
    })();
    // Hook A/B analytics
    fetchSection('hookAnalytics', setHookAnalytics, '/api/ab/hook-analytics');
    // Comic Health (P1.5-D)
    (async () => {
      try {
        const res = await api.get(`/api/admin/metrics/comic-health?days=${days}`);
        setComicHealth({ data: res.data, state: 'ready', ts: new Date().toISOString() });
      } catch {
        setComicHealth(prev => ({ ...prev, state: prev.data ? 'stale' : 'error' }));
      }
    })();
  }, [days, fetchSection]);

  // WebSocket for live updates
  const wsRef = useRef(null);
  const [wsLive, setWsLive] = useState(false);
  const [liveSnapshot, setLiveSnapshot] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/admin/live?token=${token}`;
    try {
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsLive(true);
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'live_snapshot') setLiveSnapshot(data);
        } catch {}
      };
      ws.onclose = () => setWsLive(false);
      ws.onerror = () => setWsLive(false);
      wsRef.current = ws;
    } catch {}
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, []);

  // Initial load
  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Auto-refresh polling
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        fetchAll();
      }, 15000); // 15s
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, fetchAll]);

  const s = summary.data;
  const f = funnel.data;
  const r = reliability.data;
  const rev = revenue.data;
  const ser = series.data;
  const cred = credits.data;
  const conv = conversion.data;
  const ab = abResults.data;
  const lb = leaderboard.data;
  const kf = kFactor.data;
  const ha = hookAnalytics.data;
  const ch = comicHealth.data;

  const sections = [
    { id: 'executive', label: 'Executive', icon: BarChart3 },
    { id: 'kfactor', label: 'K-Factor', icon: Activity },
    { id: 'funnel', label: 'Growth Funnel', icon: TrendingUp },
    { id: 'hook_ab', label: 'Hook A/B', icon: Target },
    { id: 'ab_testing', label: 'A/B Tests', icon: Zap },
    { id: 'leaderboard', label: 'Leaderboard', icon: Star },
    { id: 'reliability', label: 'Reliability', icon: Server },
    { id: 'series', label: 'Story Intelligence', icon: BookOpen },
    { id: 'revenue', label: 'Revenue', icon: DollarSign },
    { id: 'retention', label: 'Retention', icon: Activity },
    { id: 'credits', label: 'Credits', icon: Zap },
    { id: 'conversion', label: 'Conversion', icon: TrendingUp },
    { id: 'comic_health', label: 'Comic Health', icon: Camera },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="admin-dashboard">
      {/* Slim toolbar — nav is handled by AdminLayout sidebar */}
      <div className="bg-slate-900/80 border-b border-slate-800 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-bold text-white">Executive Dashboard</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <Radio className={`w-3 h-3 ${wsLive ? 'text-emerald-400 animate-pulse' : autoRefresh ? 'text-cyan-400 animate-pulse' : 'text-slate-600'}`} />
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`${wsLive ? 'text-emerald-400' : autoRefresh ? 'text-cyan-400' : 'text-slate-500'} hover:text-white`}
                data-testid="toggle-auto-refresh"
              >
                {wsLive ? 'WS Live' : autoRefresh ? 'Polling' : 'Paused'}
              </button>
            </div>
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
              data-testid="date-range-select"
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
            <Button onClick={fetchAll} variant="ghost" size="sm" className="text-slate-400 hover:text-white" data-testid="refresh-btn">
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Section Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-900/60 rounded-xl p-1 border border-slate-800">
          {sections.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setSection(id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                section === id
                  ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
              data-testid={`section-${id}`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        {/* ═══ EXECUTIVE SNAPSHOT ═══ */}
        {section === 'executive' && (
          <WidgetState state={summary.state} lastUpdated={summary.ts}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="executive-metrics">
                <MetricCard icon={Users} label="Total Users" value={s?.total_users} sub={`+${s?.new_users_today ?? 0} today`} color="blue" state={summary.state} testId="metric-total-users" />
                <MetricCard icon={Activity} label="Active (24h)" value={s?.active_users_24h} sub={`${s?.active_sessions ?? 0} sessions`} color="purple" state={summary.state} testId="metric-active-users" />
                <MetricCard icon={FileText} label="Generations" value={s?.total_generations} sub={s?.success_rate != null ? `${s.success_rate}% success` : 'No jobs yet'} color="indigo" state={summary.state} testId="metric-generations" />
                <MetricCard icon={DollarSign} label="Revenue" value={s?.total_revenue != null ? `₹${s.total_revenue}` : null} sub={s?.revenue_today != null ? `₹${s.revenue_today} today` : null} color="emerald" state={summary.state} testId="metric-revenue" />
                <MetricCard icon={Star} label="Satisfaction" value={s?.satisfaction_pct != null ? `${s.satisfaction_pct}%` : null} sub={s?.satisfaction_note || (s?.rating_count ? `${s.avg_rating}/5 from ${s.rating_count} ratings` : 'Not enough ratings yet')} color="amber" state={summary.state} testId="metric-rating" />
                <MetricCard icon={Shield} label="Health" value={r?.overall_health?.toUpperCase()} color={r?.overall_health === 'healthy' ? 'green' : r?.overall_health === 'degraded' ? 'amber' : 'red'} state={reliability.state} testId="metric-health" />
              </div>

              {/* Quick Reliability */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Queue Depth</p>
                  <p className="text-lg font-bold text-white">{liveSnapshot?.queue_depth ?? r?.queue_depth ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Stuck Jobs</p>
                  <p className={`text-lg font-bold ${r?.stuck_jobs > 0 ? 'text-red-400' : 'text-white'}`}>{r?.stuck_jobs ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Active Sessions</p>
                  <p className="text-lg font-bold text-white">{liveSnapshot?.active_sessions ?? s?.active_sessions ?? 'N/A'}</p>
                  {wsLive && <p className="text-[9px] text-emerald-400 mt-0.5">Real-time via WS</p>}
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Completions (1h)</p>
                  <p className="text-lg font-bold text-white">{liveSnapshot?.recent_completions_1h ?? 'N/A'}</p>
                  {wsLive && <p className="text-[9px] text-emerald-400 mt-0.5">Real-time via WS</p>}
                </div>
              </div>

              {/* Quick Series Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Active Series</p>
                  <p className="text-lg font-bold text-white">{ser?.active_series ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Total Episodes</p>
                  <p className="text-lg font-bold text-white">{ser?.total_episodes ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Characters</p>
                  <p className="text-lg font-bold text-white">{ser?.total_characters ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Continuation Rate</p>
                  <p className="text-lg font-bold text-white">{ser?.continuation_rate != null ? `${ser.continuation_rate}%` : 'No data'}</p>
                </div>
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ K-FACTOR VIRAL DASHBOARD ═══ */}
        {section === 'kfactor' && (
          <WidgetState state={kFactor.state} lastUpdated={kFactor.ts}>
            <div className="space-y-6" data-testid="kfactor-section">
              {/* K-Factor Hero */}
              <div className="bg-gradient-to-r from-cyan-500/[0.06] to-indigo-500/[0.06] border border-cyan-500/20 rounded-xl p-6 text-center" data-testid="kfactor-hero">
                <p className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider mb-1">Viral Coefficient</p>
                <p className="text-5xl font-black text-white mb-1">
                  {kf?.viral_coefficient_K != null ? kf.viral_coefficient_K.toFixed(4) : 'N/A'}
                </p>
                <p className={`text-sm font-semibold ${
                  kf?.viral_coefficient_K > 1 ? 'text-emerald-400' :
                  kf?.viral_coefficient_K > 0.5 ? 'text-cyan-400' :
                  kf?.viral_coefficient_K > 0 ? 'text-amber-400' : 'text-slate-500'
                }`}>
                  {kf?.interpretation || 'No data'}
                </p>
                <div className="mt-3 flex items-center justify-center gap-2">
                  <div className="w-48 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        kf?.viral_coefficient_K > 0.5 ? 'bg-emerald-500' : kf?.viral_coefficient_K > 0 ? 'bg-amber-500' : 'bg-slate-700'
                      }`}
                      style={{ width: `${Math.min((kf?.viral_coefficient_K || 0) / 1 * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-500">Target: 0.5</span>
                </div>
              </div>

              {/* Funnel: Share → Click → Signup → Continue */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-400" /> Viral Funnel ({days}d)
                </h3>
                <div className="space-y-3">
                  <FunnelBar label="Total Shares" value={kf?.components?.total_shares} rate={null} maxValue={Math.max(kf?.components?.total_shares || 1, 1)} />
                  <FunnelBar label="Page Views" value={kf?.components?.page_views} rate={null} maxValue={Math.max(kf?.components?.total_shares || 1, 1)} />
                  <FunnelBar label="Signups from Shares" value={kf?.components?.signups_from_shares} rate={kf?.components?.conversion_rate_per_share} maxValue={Math.max(kf?.components?.total_shares || 1, 1)} />
                </div>
              </div>

              {/* Component Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard icon={Users} label="Unique Sharers" value={kf?.components?.unique_sharers} color="cyan" testId="kf-unique-sharers" />
                <MetricCard icon={Activity} label="Total Shares" value={kf?.components?.total_shares} color="blue" testId="kf-total-shares" />
                <MetricCard icon={TrendingUp} label="Avg Shares/User" value={kf?.components?.avg_shares_per_user} color="purple" testId="kf-avg-shares" />
                <MetricCard icon={Zap} label="Conv Rate" value={kf?.components?.conversion_rate_per_share != null ? `${kf.components.conversion_rate_per_share}%` : 'N/A'} color="emerald" testId="kf-conv-rate" />
              </div>

              {/* Top Performing Slugs */}
              {kf?.top_performing_slugs?.length > 0 && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Star className="w-4 h-4 text-amber-400" /> Top Performing Content
                  </h3>
                  <div className="space-y-2">
                    {kf.top_performing_slugs.map((slug, i) => (
                      <div key={slug.slug} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2.5">
                        <div className="flex items-center gap-3">
                          <span className={`text-sm font-black w-5 text-center ${i === 0 ? 'text-amber-400' : 'text-slate-500'}`}>{i + 1}</span>
                          <span className="text-xs text-white font-mono truncate max-w-[200px]">{slug.slug}</span>
                        </div>
                        <div className="flex items-center gap-4 text-[10px]">
                          <span className="text-slate-400"><strong className="text-white">{slug.views}</strong> views</span>
                          <span className="text-slate-400"><strong className="text-white">{slug.remix_clicks}</strong> remixes</span>
                          <span className={`font-bold ${slug.remix_rate > 10 ? 'text-emerald-400' : 'text-amber-400'}`}>{slug.remix_rate}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Email Nudge Status */}
              <EmailNudgeStatus />

              {/* Share Rewards Metrics */}
              {shareRewards.data && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="share-rewards-section">
                  <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                    <Gift className="w-4 h-4 text-emerald-400" /> Share Reward Metrics
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-black text-emerald-400">{shareRewards.data.total_share_rewards || 0}</p>
                      <p className="text-[10px] text-emerald-400/70">Shares (+5 each)</p>
                    </div>
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-black text-amber-400">{shareRewards.data.total_continuation_rewards || 0}</p>
                      <p className="text-[10px] text-amber-400/70">Continuations (+15)</p>
                    </div>
                    <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-black text-violet-400">{shareRewards.data.total_signup_rewards || 0}</p>
                      <p className="text-[10px] text-violet-400/70">Signups (+25)</p>
                    </div>
                    <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-black text-cyan-400">{shareRewards.data.total_credits_given || 0}</p>
                      <p className="text-[10px] text-cyan-400/70">Credits given</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{shareRewards.data.unique_sharers || 0} unique sharers</span>
                    <span>Last 7d: {shareRewards.data.last_7_days?.shares || 0} shares, {shareRewards.data.last_7_days?.continuations || 0} cont, {shareRewards.data.last_7_days?.signups || 0} signups</span>
                  </div>
                </div>
              )}
            </div>
          </WidgetState>
        )}

        {/* ═══ GROWTH FUNNEL ═══ */}
        {section === 'funnel' && (
          <WidgetState state={funnel.state} lastUpdated={funnel.ts}>
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="funnel-visualization">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-400" /> Conversion Funnel
                </h3>
                {f && (f.page_views > 0 || f.generate_clicks > 0 || f.creation_completed > 0) ? (
                  <div className="space-y-3">
                    <FunnelBar label="Page Views" value={f.page_views} rate={null} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Remix Clicks" value={f.remix_clicks} rate={f.remix_rate} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Tool Opens" value={f.tool_opens_prefilled} rate={f.tool_open_rate} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Generate Clicks" value={f.generate_clicks} rate={f.generate_rate} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Signups" value={f.signup_completed} rate={f.signup_rate} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Completed" value={f.creation_completed} rate={f.completion_rate} maxValue={Math.max(f.page_views, 1)} />
                    <FunnelBar label="Shares" value={f.share_clicks} rate={f.share_rate} maxValue={Math.max(f.page_views, 1)} />
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-slate-500">No funnel data available yet</p>
                    <p className="text-xs text-slate-600 mt-1">Growth events will appear as users interact with public pages and creation tools</p>
                  </div>
                )}
              </div>

              {/* Viral metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard icon={Zap} label="Viral K" value={f?.viral_coefficient_k} sub="K > 1 = viral" color="cyan" testId="metric-viral-k" />
                <MetricCard icon={Users} label="Unique Creators" value={f?.unique_creators} color="blue" testId="metric-unique-creators" />
                <MetricCard icon={TrendingUp} label="Avg Shares/Creator" value={f?.avg_shares_per_creator} color="purple" testId="metric-avg-shares" />
                <MetricCard icon={Activity} label="Share Rate" value={f?.share_rate != null ? `${f.share_rate}%` : null} color="emerald" testId="metric-share-rate" />
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ RELIABILITY ═══ */}
        {section === 'reliability' && (
          <WidgetState state={reliability.state} lastUpdated={reliability.ts}>
            <div className="space-y-6">
              {/* Health Status */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="health-panel">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Heart className="w-4 h-4 text-emerald-400" /> System Health
                </h3>
                <div className="flex items-center gap-3 mb-4">
                  <HealthBadge status={r?.overall_health || 'unknown'} />
                  <span className="text-xs text-slate-500">Overall system status</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {r?.health_checks && Object.entries(r.health_checks).map(([key, status]) => (
                    <div key={key} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2">
                      <span className="text-xs text-slate-400 capitalize">{key.replace('_', ' ')}</span>
                      <HealthBadge status={status} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Queue & Jobs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard icon={Database} label="Queue Depth" value={r?.queue_depth} color={r?.queue_depth > 50 ? 'red' : 'blue'} testId="metric-queue" />
                <MetricCard icon={Activity} label="Active Jobs" value={r?.active_jobs} color="purple" testId="metric-active-jobs" />
                <MetricCard icon={AlertTriangle} label="Stuck Jobs" value={r?.stuck_jobs} color={r?.stuck_jobs > 0 ? 'red' : 'green'} testId="metric-stuck-jobs" />
                <MetricCard icon={Clock} label="Avg Render" value={r?.avg_render_seconds != null ? `${r.avg_render_seconds}s` : null} color="cyan" testId="metric-avg-render" />
              </div>

              {/* Tool render stats */}
              {r?.tool_render_stats && Object.keys(r.tool_render_stats).length > 0 && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-sm font-semibold text-white mb-3">Render Time by Tool</h3>
                  <div className="space-y-2">
                    {Object.entries(r.tool_render_stats).map(([tool, stats]) => (
                      <div key={tool} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2">
                        <span className="text-xs text-white capitalize">{tool.replace('_', ' ')}</span>
                        <div className="flex gap-4 text-xs">
                          <span className="text-slate-400">Avg: <span className="text-white">{stats.avg_seconds}s</span></span>
                          <span className="text-slate-400">Max: <span className="text-white">{stats.max_seconds}s</span></span>
                          <span className="text-slate-400">Jobs: <span className="text-white">{stats.count}</span></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(!r?.tool_render_stats || Object.keys(r.tool_render_stats).length === 0) && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center">
                  <p className="text-sm text-slate-500">No render data available in last 24h</p>
                  <p className="text-xs text-slate-600 mt-1">Tool-specific render times will appear when jobs complete</p>
                </div>
              )}
            </div>
          </WidgetState>
        )}

        {/* ═══ STORY & CHARACTER INTELLIGENCE ═══ */}
        {section === 'series' && (
          <WidgetState state={series.state} lastUpdated={series.ts}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="series-metrics">
                <MetricCard icon={Film} label="Active Series" value={ser?.active_series} sub={`${ser?.total_series ?? 0} total`} color="indigo" testId="metric-active-series" />
                <MetricCard icon={BookOpen} label="Total Episodes" value={ser?.total_episodes} sub={ser?.avg_episodes_per_series != null ? `${ser.avg_episodes_per_series} avg/series` : null} color="cyan" testId="metric-episodes" />
                <MetricCard icon={TrendingUp} label="Continuation" value={ser?.continuation_rate != null ? `${ser.continuation_rate}%` : null} sub="Series with 2+ episodes" color="emerald" testId="metric-continuation" />
                <MetricCard icon={Users} label="Characters" value={ser?.total_characters} sub={`${ser?.auto_extracted_characters ?? 0} auto-extracted`} color="purple" testId="metric-characters" />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Character Reuse Rate</p>
                  <p className="text-lg font-bold text-white">{ser?.character_reuse_rate != null ? `${ser.character_reuse_rate}%` : 'No data'}</p>
                  <p className="text-[10px] text-slate-600">{ser?.reused_characters ?? 0} characters reused</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Continuity Pass Rate</p>
                  <p className="text-lg font-bold text-white">{ser?.continuity_pass_rate != null ? `${ser.continuity_pass_rate}%` : 'No data'}</p>
                  <p className="text-[10px] text-slate-600">Visual/narrative consistency</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Rewards Claimed</p>
                  <p className="text-lg font-bold text-white">{ser?.rewards_claimed ?? 0}</p>
                  <p className="text-[10px] text-slate-600">Milestone completions</p>
                </div>
              </div>

              {/* Most reused character */}
              {ser?.most_reused_character && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/15 flex items-center justify-center">
                    <Star className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Most Reused Character</p>
                    <p className="text-sm font-semibold text-white">{ser.most_reused_character.name}</p>
                    <p className="text-[10px] text-slate-500">{ser.most_reused_character.usage} episode appearances</p>
                  </div>
                </div>
              )}
            </div>
          </WidgetState>
        )}

        {/* ═══ REVENUE ═══ */}
        {section === 'revenue' && (
          <WidgetState state={revenue.state} lastUpdated={revenue.ts}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="revenue-metrics">
                <MetricCard icon={DollarSign} label="Total Revenue (INR)" value={rev?.total_revenue_inr != null ? `₹${rev.total_revenue_inr.toLocaleString()}` : null} sub={rev?.total_revenue_usd ? `$${rev.total_revenue_usd} USD` : null} color="emerald" testId="metric-total-revenue" />
                <MetricCard icon={DollarSign} label="Revenue Today" value={rev?.revenue_today_inr != null ? `₹${rev.revenue_today_inr.toLocaleString()}` : null} sub={`${rev?.today_payments ?? 0} payments today`} color="green" testId="metric-rev-today" />
                <MetricCard icon={CheckCircle} label="Successful" value={rev?.successful_payments} sub={`${rev?.payment_success_rate ?? 0}% success rate`} color="blue" testId="metric-success-payments" />
                <MetricCard icon={XCircle} label="Failed" value={rev?.failed_payments} sub={`${rev?.pending_payments ?? 0} pending`} color="red" testId="metric-failed-payments" />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <MetricCard icon={Users} label="Paying Users" value={rev?.paying_users} sub={`${rev?.conversion_rate ?? 0}% of ${rev?.total_users ?? 0}`} color="violet" testId="metric-paying-users" />
                <MetricCard icon={Star} label="ARPU" value={rev?.arpu != null ? `₹${rev.arpu}` : 'N/A'} color="amber" testId="metric-arpu" />
                <MetricCard icon={Zap} label="Credits Sold" value={rev?.total_credits_sold?.toLocaleString()} color="cyan" testId="metric-credits-sold" />
              </div>

              {/* Recent Cashfree Payments */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="recent-payments">
                <h3 className="text-sm font-semibold text-white mb-3">Recent Payments (Cashfree)</h3>
                {rev?.recent_payments?.length > 0 ? (
                  <div className="space-y-2">
                    {rev.recent_payments.map((txn, i) => (
                      <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-3">
                          <DollarSign className="w-3 h-3 text-emerald-400" />
                          <span className="text-xs text-white font-mono">
                            {txn.currency === 'USD' ? '$' : '₹'}{txn.amount}
                          </span>
                          <span className="text-[10px] text-violet-400 bg-violet-400/10 px-2 py-0.5 rounded">
                            +{txn.credits} credits
                          </span>
                          <span className="text-[10px] text-slate-500">{txn.productId}</span>
                        </div>
                        <span className="text-[10px] text-slate-600">{txn.paidAt ? new Date(txn.paidAt).toLocaleDateString() : ''}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-4">No Cashfree payments recorded</p>
                )}
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ Retention Section — Links to full retention dashboard ═══ */}
        {section === 'retention' && (
          <div className="space-y-4" data-testid="retention-section">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center">
              <Activity className="w-10 h-10 text-purple-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-white mb-2">Retention Analytics</h3>
              <p className="text-sm text-slate-400 mb-4">The 5 metrics that determine whether users stay or leave.</p>
              <button
                onClick={() => navigate('/app/admin/retention')}
                className="px-6 py-2 rounded-xl bg-purple-500/20 text-purple-300 font-semibold text-sm hover:bg-purple-500/30 border border-purple-500/20 transition-colors"
                data-testid="retention-dashboard-link"
              >
                Open Retention Dashboard
              </button>
            </div>
          </div>
        )}

        {/* ═══ Credits Section ═══ */}
        {section === 'credits' && (
          <WidgetState state={credits.state} lastUpdated={credits.ts}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="credit-metrics">
                <MetricCard icon={Zap} label="Credits Issued" value={cred?.total_credits_issued?.toLocaleString()} color="violet" testId="metric-credits-issued" />
                <MetricCard icon={Activity} label="Credits Consumed" value={cred?.total_credits_consumed?.toLocaleString()} color="rose" testId="metric-credits-consumed" />
                <MetricCard icon={Database} label="Current Balance" value={cred?.total_current_balance?.toLocaleString()} sub={`across ${cred?.total_users ?? 0} users`} color="cyan" testId="metric-credits-balance" />
                <MetricCard icon={Users} label="Avg per User" value={cred?.avg_credits_per_user} color="amber" testId="metric-credits-avg" />
              </div>

              {/* Top Users by Usage */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6" data-testid="top-users-usage">
                <h3 className="text-sm font-semibold text-white mb-3">Top Users by Credit Usage</h3>
                {cred?.top_users_by_usage?.length > 0 ? (
                  <div className="space-y-2">
                    {cred.top_users_by_usage.map((u, i) => (
                      <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] font-mono text-slate-600 w-5">{i + 1}.</span>
                          <div>
                            <span className="text-xs text-white">{u.name || u.email}</span>
                            <span className="text-[10px] text-slate-500 ml-2">{u.credits} credits left</span>
                          </div>
                        </div>
                        <span className="text-xs font-mono text-rose-400">-{u.total_spent} spent</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-4">No credit usage data</p>
                )}
              </div>

              {/* Credit Reset */}
              <CreditResetWidget />
            </div>
          </WidgetState>
        )}

        {/* ═══ Conversion Section ═══ */}
        {section === 'conversion' && (
          <WidgetState state={conversion.state} lastUpdated={conversion.ts}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="conversion-metrics">
                <MetricCard icon={TrendingUp} label="Free → Paid" value={conv?.free_to_paid_rate != null ? `${conv.free_to_paid_rate}%` : null} sub={`${conv?.paying_users ?? 0} of ${conv?.total_users ?? 0}`} color="emerald" testId="metric-free-to-paid" />
                <MetricCard icon={DollarSign} label="Top-up Rate" value={conv?.topup_purchase_rate != null ? `${conv.topup_purchase_rate}%` : null} color="blue" testId="metric-topup-rate" />
                <MetricCard icon={Star} label="Subscription Rate" value={conv?.subscription_rate != null ? `${conv.subscription_rate}%` : null} color="violet" testId="metric-sub-rate" />
                <MetricCard icon={Heart} label="Repeat Buyers" value={conv?.repeat_buyers} color="rose" testId="metric-repeat-buyers" />
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ HOOK A/B TESTING ═══ */}
        {section === 'hook_ab' && (
          <WidgetState state={hookAnalytics.state} lastUpdated={hookAnalytics.ts}>
            <div className="space-y-6" data-testid="hook-ab-section">
              {/* Header */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Target className="w-4 h-4 text-amber-400" /> Story Hook A/B Test
                  </h3>
                  {ha?.top_performer ? (
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full">
                      Leader: {ha.variants?.find(v => v.variant_id === ha.top_performer)?.label || ha.top_performer}
                    </span>
                  ) : (
                    <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full">
                      Collecting data...
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mb-4">
                  Testing 4 hook styles on public share pages and dashboard trending cards.
                  Min {ha?.min_sample_size || 50} impressions per variant for reliable rates.
                </p>

                {ha?.variants?.length > 0 ? (
                  <div className="space-y-3">
                    {ha.variants.map((v) => {
                      const isTop = ha.top_performer === v.variant_id;
                      const isBottom = ha.bottom_performer === v.variant_id;
                      const styleColors = {
                        mystery: 'border-amber-500/30 bg-amber-500/5',
                        emotional: 'border-rose-500/30 bg-rose-500/5',
                        shock: 'border-red-500/30 bg-red-500/5',
                        curiosity: 'border-cyan-500/30 bg-cyan-500/5',
                      };
                      const borderClass = isTop
                        ? 'border-emerald-500/40 bg-emerald-500/5'
                        : isBottom
                          ? 'border-red-500/20 bg-red-500/5'
                          : styleColors[v.style] || 'bg-slate-800/50';

                      return (
                        <div key={v.variant_id} className={`rounded-xl p-4 border ${borderClass}`} data-testid={`hook-variant-${v.variant_id}`}>
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white">{v.label}</span>
                              <span className="text-[10px] text-slate-500 capitalize">({v.style})</span>
                              {isTop && <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">BEST</span>}
                              {isBottom && <span className="text-[9px] font-bold text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">WORST</span>}
                            </div>
                            {v.data_warning && (
                              <span className="text-[9px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <AlertTriangle className="w-2.5 h-2.5" /> {v.data_warning}
                              </span>
                            )}
                          </div>

                          {/* Metrics grid */}
                          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className="text-lg font-black text-white">{v.impressions}</p>
                              <p className="text-[9px] text-slate-500">Impressions</p>
                            </div>
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className="text-lg font-black text-white">{v.clicks}</p>
                              <p className="text-[9px] text-slate-500">Clicks</p>
                            </div>
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className={`text-lg font-black ${v.sufficient_data ? (v.ctr > 5 ? 'text-emerald-400' : 'text-white') : 'text-slate-500'}`}>{v.ctr}%</p>
                              <p className="text-[9px] text-slate-500">CTR</p>
                            </div>
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className="text-lg font-black text-white">{v.continues}</p>
                              <p className="text-[9px] text-slate-500">Continues</p>
                            </div>
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className={`text-lg font-black ${v.sufficient_data ? (v.continue_rate > 3 ? 'text-emerald-400' : 'text-white') : 'text-slate-500'}`}>{v.continue_rate}%</p>
                              <p className="text-[9px] text-slate-500">Continue %</p>
                            </div>
                            <div className="text-center p-2 bg-slate-900/50 rounded-lg">
                              <p className={`text-lg font-black ${v.sufficient_data ? (v.share_rate > 2 ? 'text-emerald-400' : 'text-white') : 'text-slate-500'}`}>{v.share_rate}%</p>
                              <p className="text-[9px] text-slate-500">Share %</p>
                            </div>
                          </div>

                          {/* Progress bar */}
                          <div className="mt-2">
                            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${isTop ? 'bg-emerald-500' : isBottom ? 'bg-red-500/60' : 'bg-cyan-500/60'}`}
                                style={{ width: `${Math.min((v.impressions / (ha.min_sample_size || 50)) * 100, 100)}%` }}
                              />
                            </div>
                            <p className="text-[9px] text-slate-600 mt-0.5">
                              {v.sufficient_data ? 'Sufficient data' : `${v.impressions}/${ha.min_sample_size || 50} impressions`}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-slate-500">No hook experiment data yet</p>
                    <p className="text-xs text-slate-600 mt-1">Data will appear once traffic flows through public share pages and dashboard</p>
                  </div>
                )}
              </div>

              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard
                  icon={Eye}
                  label="Total Impressions"
                  value={ha?.variants?.reduce((s, v) => s + v.impressions, 0) || 0}
                  color="blue"
                  testId="metric-hook-impressions"
                />
                <MetricCard
                  icon={Target}
                  label="Best CTR"
                  value={ha?.variants?.length > 0 ? `${Math.max(...ha.variants.map(v => v.ctr))}%` : '\u2014'}
                  sub={ha?.top_performer ? ha.variants.find(v => v.variant_id === ha.top_performer)?.label : 'TBD'}
                  color="green"
                  testId="metric-hook-best-ctr"
                />
                <MetricCard
                  icon={TrendingUp}
                  label="Best Continue %"
                  value={ha?.variants?.length > 0 ? `${Math.max(...ha.variants.map(v => v.continue_rate))}%` : '\u2014'}
                  color="purple"
                  testId="metric-hook-best-continue"
                />
                <MetricCard
                  icon={Eye}
                  label="Best Share %"
                  value={ha?.variants?.length > 0 ? `${Math.max(...ha.variants.map(v => v.share_rate))}%` : '\u2014'}
                  color="indigo"
                  testId="metric-hook-best-share"
                />
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ A/B TEST RESULTS ═══ */}
        {section === 'ab_testing' && (
          <WidgetState state={abResults.state} lastUpdated={abResults.ts}>
            <div className="space-y-6" data-testid="ab-testing-section">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-cyan-400" /> Active A/B Experiments
                </h3>
                {ab?.experiments?.length > 0 ? (
                  <div className="space-y-6">
                    {ab.experiments.map(exp => (
                      <div key={exp.experiment_id} className="bg-slate-800/50 rounded-xl p-4 space-y-3" data-testid={`ab-exp-${exp.experiment_id}`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-sm font-medium text-white">{exp.name}</h4>
                            <p className="text-[10px] text-slate-500">Primary event: {exp.primary_event} | Min 200 sessions/variant</p>
                          </div>
                          {exp.tentative_winner && (
                            <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                              Winner: {exp.tentative_winner}
                            </span>
                          )}
                          {!exp.tentative_winner && (
                            <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
                              Collecting data...
                            </span>
                          )}
                        </div>
                        <div className="space-y-2">
                          {exp.variants.map(v => {
                            const maxSessions = Math.max(...exp.variants.map(x => x.sessions), 1);
                            const barWidth = Math.max((v.sessions / maxSessions) * 100, 2);
                            const isWinner = exp.tentative_winner === v.variant_id;
                            return (
                              <div key={v.variant_id} className={`rounded-lg p-2.5 ${isWinner ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-slate-700/30'}`}>
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="text-xs text-white font-medium">{v.label}</span>
                                  <div className="flex items-center gap-3 text-[10px]">
                                    <span className="text-slate-400">{v.sessions} sessions</span>
                                    <span className={`font-bold ${isWinner ? 'text-emerald-400' : 'text-white'}`}>{v.primary_conv_rate}%</span>
                                  </div>
                                </div>
                                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all ${isWinner ? 'bg-emerald-500' : 'bg-cyan-500/60'}`}
                                    style={{ width: `${barWidth}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-slate-500">No A/B experiments active</p>
                    <p className="text-xs text-slate-600 mt-1">Experiments will appear once seeded and traffic flows through public pages</p>
                  </div>
                )}
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ STORY CHAIN LEADERBOARD ═══ */}
        {section === 'leaderboard' && (
          <WidgetState state={leaderboard.state} lastUpdated={leaderboard.ts}>
            <div className="space-y-6" data-testid="leaderboard-section">
              {/* Top Continued Stories */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Film className="w-4 h-4 text-amber-400" /> Most Continued Stories
                </h3>
                {lb?.top_stories?.length > 0 ? (
                  <div className="space-y-2">
                    {lb.top_stories.map((story, i) => (
                      <div key={story.job_id || i} className="flex items-center gap-3 bg-slate-800/50 rounded-lg px-3 py-2.5" data-testid={`leaderboard-story-${i}`}>
                        <span className={`text-sm font-black w-6 text-center ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-orange-400' : 'text-slate-500'}`}>
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white font-medium truncate">{story.title || 'Untitled'}</p>
                          <p className="text-[10px] text-slate-500">{story.creator_name || 'Anonymous'}</p>
                        </div>
                        <div className="flex items-center gap-3 text-[10px]">
                          <span className="text-slate-400"><strong className="text-white">{story.continuations}</strong> continuations</span>
                          <span className="text-slate-400"><strong className="text-white">{story.views}</strong> views</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-4">No stories with continuations yet</p>
                )}
              </div>

              {/* Top Continuers (Users) */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                  <Users className="w-4 h-4 text-violet-400" /> Top Continuers
                </h3>
                {lb?.top_continuers?.length > 0 ? (
                  <div className="space-y-2">
                    {lb.top_continuers.map((user, i) => (
                      <div key={user.user_id || i} className="flex items-center gap-3 bg-slate-800/50 rounded-lg px-3 py-2.5" data-testid={`leaderboard-user-${i}`}>
                        <span className={`text-sm font-black w-6 text-center ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-orange-400' : 'text-slate-500'}`}>
                          {i + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-white font-medium">{user.name || 'Anonymous'}</p>
                        </div>
                        <span className="text-xs font-bold text-violet-400">{user.continuation_count} remixes</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500 text-center py-4">No continuation data yet</p>
                )}
              </div>

              {/* Overall Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard icon={Activity} label="Total Continuations" value={lb?.total_continuations} color="cyan" testId="metric-total-cont" />
                <MetricCard icon={Users} label="Unique Continuers" value={lb?.unique_continuers} color="violet" testId="metric-unique-cont" />
                <MetricCard icon={Film} label="Stories Continued" value={lb?.stories_with_continuations} color="amber" testId="metric-stories-cont" />
                <MetricCard icon={TrendingUp} label="Avg Chain Length" value={lb?.avg_chain_length} color="emerald" testId="metric-avg-chain" />
              </div>
            </div>
          </WidgetState>
        )}

        {/* ═══ COMIC HEALTH (P1.5-D) ═══ */}
        {section === 'comic_health' && (
          <WidgetState state={comicHealth.state} lastUpdated={comicHealth.ts}>
            <div className="space-y-6" data-testid="comic-health-section">
              {/* Alerts */}
              {ch?.alerts?.length > 0 && (
                <div className="space-y-2">
                  {ch.alerts.map((a, i) => (
                    <div key={i} className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border ${a.level === 'critical' ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-amber-500/10 border-amber-500/30 text-amber-400'}`} data-testid={`alert-${i}`}>
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-medium">{a.message}</span>
                    </div>
                  ))}
                </div>
              )}

              {ch?.empty_state ? (
                <p className="text-sm text-slate-500 text-center py-8">{ch.empty_message}</p>
              ) : (
                <>
                  {/* Job Success */}
                  <div>
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" /> Job Success ({days}d)
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      <MetricCard icon={Activity} label="Total Jobs" value={ch?.jobs?.total} color="blue" testId="comic-total-jobs" />
                      <MetricCard icon={CheckCircle} label="Completed" value={ch?.jobs?.completed} color="emerald" testId="comic-completed" />
                      <MetricCard icon={Shield} label="Partial" value={ch?.jobs?.partial} color="amber" testId="comic-partial" />
                      <MetricCard icon={XCircle} label="Failed" value={ch?.jobs?.failed} color="red" testId="comic-failed" />
                      <MetricCard icon={TrendingUp} label="Success Rate" value={ch?.jobs?.success_rate != null ? `${ch.jobs.success_rate}%` : '—'} color={ch?.jobs?.success_rate >= 80 ? 'emerald' : 'red'} testId="comic-success-rate" />
                    </div>
                  </div>

                  {/* Performance */}
                  <div>
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <Clock className="w-4 h-4 text-cyan-400" /> Performance
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <MetricCard icon={Clock} label="Avg Gen Time" value={ch?.performance?.avg_generation_time_seconds != null ? `${ch.performance.avg_generation_time_seconds}s` : '—'} color="cyan" testId="comic-avg-time" />
                      <MetricCard icon={RefreshCw} label="Retry Rate" value={ch?.performance?.retry_rate != null ? `${ch.performance.retry_rate}%` : '—'} color={ch?.performance?.retry_rate > 30 ? 'red' : 'blue'} testId="comic-retry-rate" />
                      <MetricCard icon={Activity} label="Retried Jobs" value={ch?.performance?.retried_jobs} color="amber" testId="comic-retried-jobs" />
                    </div>
                  </div>

                  {/* Character Consistency */}
                  <div>
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <Eye className="w-4 h-4 text-violet-400" /> Character Consistency
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <MetricCard icon={Eye} label="Avg Similarity" value={ch?.consistency?.avg_similarity != null ? ch.consistency.avg_similarity.toFixed(3) : '—'} color="violet" testId="comic-avg-similarity" />
                      <MetricCard icon={RefreshCw} label="Consistency Retry Rate" value={ch?.consistency?.consistency_retry_rate != null ? `${ch.consistency.consistency_retry_rate}%` : '—'} color="blue" testId="comic-consistency-retry" />
                      <MetricCard icon={Users} label="No-Face Panel Rate" value={ch?.consistency?.no_face_panel_rate != null ? `${ch.consistency.no_face_panel_rate}%` : '—'} color="amber" testId="comic-noface-rate" />
                    </div>
                    {ch?.consistency?.drift_by_style && Object.keys(ch.consistency.drift_by_style).length > 0 && (
                      <div className="mt-3 bg-slate-900/60 border border-slate-800 rounded-xl p-3">
                        <p className="text-[10px] text-slate-500 font-bold uppercase mb-2">Drift by Style</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {Object.entries(ch.consistency.drift_by_style).map(([style, data]) => (
                            <div key={style} className="bg-slate-800/50 rounded-lg px-3 py-2" data-testid={`drift-${style}`}>
                              <p className="text-[11px] text-white font-medium capitalize">{style.replace(/_/g, ' ')}</p>
                              <p className="text-[10px] text-slate-400">Similarity: {data.avg_similarity?.toFixed(3) ?? '—'}</p>
                              <p className="text-[10px] text-slate-500">{data.count} jobs, {data.retries} retries</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Quality Checks + Downloads */}
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-emerald-400" /> Quality Checks
                      </h3>
                      <div className="grid grid-cols-2 gap-3">
                        <MetricCard icon={Shield} label="Total Checks" value={ch?.quality_check?.total_checks} color="emerald" testId="comic-quality-total" />
                        <MetricCard icon={CheckCircle} label="Good" value={ch?.quality_check?.breakdown?.good} color="emerald" testId="comic-quality-good" />
                        <MetricCard icon={MinusCircle} label="Acceptable" value={ch?.quality_check?.breakdown?.acceptable} color="amber" testId="comic-quality-acceptable" />
                        <MetricCard icon={XCircle} label="Poor" value={ch?.quality_check?.breakdown?.poor} color="red" testId="comic-quality-poor" />
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-400" /> Downloads ({days}d)
                      </h3>
                      <div className="grid grid-cols-2 gap-3">
                        <MetricCard icon={FileText} label="PDF Attempts" value={ch?.downloads?.pdf_attempts} color="blue" testId="comic-pdf-attempts" />
                        <MetricCard icon={CheckCircle} label="PDF Success Rate" value={ch?.downloads?.pdf_success_rate != null ? `${ch.downloads.pdf_success_rate}%` : '—'} color="emerald" testId="comic-pdf-success" />
                        <MetricCard icon={Camera} label="PNG Downloads" value={ch?.downloads?.png_downloads} color="violet" testId="comic-png-downloads" />
                        <MetricCard icon={FileText} label="Script Downloads" value={ch?.downloads?.script_downloads} color="cyan" testId="comic-script-downloads" />
                      </div>
                    </div>
                  </div>

                  {/* Conversion Funnel */}
                  <div>
                    <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-pink-400" /> Conversion ({days}d)
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <MetricCard icon={Eye} label="Style Clicks" value={ch?.conversion?.style_clicks} color="pink" testId="comic-style-clicks" />
                      <MetricCard icon={Zap} label="Generate After Preview" value={ch?.conversion?.generate_after_preview} color="violet" testId="comic-gen-after-preview" />
                      <MetricCard icon={Activity} label="Result Views" value={ch?.conversion?.result_views} color="cyan" testId="comic-result-views" />
                    </div>
                  </div>
                </>
              )}
            </div>
          </WidgetState>
        )}
      </div>
    </div>
  );
}
