import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  Users, Eye, Activity, FileText, DollarSign, Star, RefreshCw, ArrowLeft,
  LogOut, AlertTriangle, TrendingUp, Zap, Shield, Heart, BookOpen,
  Film, ChevronRight, ChevronDown, Clock, Server, Database, BarChart3,
  CheckCircle, XCircle, MinusCircle, Radio
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
  }, [days, fetchSection]);

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

  const sections = [
    { id: 'executive', label: 'Executive', icon: BarChart3 },
    { id: 'funnel', label: 'Growth Funnel', icon: TrendingUp },
    { id: 'reliability', label: 'Reliability', icon: Server },
    { id: 'series', label: 'Story Intelligence', icon: BookOpen },
    { id: 'revenue', label: 'Revenue', icon: DollarSign },
    { id: 'credits', label: 'Credits', icon: Zap },
    { id: 'conversion', label: 'Conversion', icon: TrendingUp },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white" data-testid="admin-dashboard">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-800 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white"><ArrowLeft className="w-4 h-4" /></Button>
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-sm font-bold text-white">Admin Control Center</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Live indicator */}
            <div className="flex items-center gap-1.5 text-xs">
              <Radio className={`w-3 h-3 ${autoRefresh ? 'text-emerald-400 animate-pulse' : 'text-slate-600'}`} />
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`${autoRefresh ? 'text-emerald-400' : 'text-slate-500'} hover:text-white`}
                data-testid="toggle-auto-refresh"
              >
                {autoRefresh ? 'Live' : 'Paused'}
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
            <Button onClick={() => { localStorage.removeItem('token'); navigate('/login'); }} variant="ghost" size="sm" className="text-slate-400 hover:text-white" data-testid="admin-logout-btn">
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="max-w-7xl mx-auto px-4 pb-2 flex gap-2 overflow-x-auto">
          {[
            ['/app/admin/users', Users, 'Users'],
            ['/app/admin/login-activity', Eye, 'Logins'],
            ['/app/admin/monitoring', Activity, 'Monitor'],
            ['/app/admin/audit-logs', FileText, 'Audit'],
            ['/app/admin/system-health', Heart, 'Health'],
            ['/app/admin/anti-abuse', Shield, 'Safety'],
          ].map(([href, Icon, label]) => (
            <Link key={href} to={href}>
              <Button variant="ghost" size="sm" className="text-slate-500 hover:text-white text-[11px] gap-1 h-7 px-2">
                <Icon className="w-3 h-3" /> {label}
              </Button>
            </Link>
          ))}
        </div>
      </header>

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
                  <p className="text-lg font-bold text-white">{r?.queue_depth ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Stuck Jobs</p>
                  <p className={`text-lg font-bold ${r?.stuck_jobs > 0 ? 'text-red-400' : 'text-white'}`}>{r?.stuck_jobs ?? 'N/A'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Avg Render</p>
                  <p className="text-lg font-bold text-white">{r?.avg_render_seconds != null ? `${r.avg_render_seconds}s` : 'No data'}</p>
                </div>
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                  <p className="text-[10px] text-slate-500 mb-1">Max Render</p>
                  <p className="text-lg font-bold text-white">{r?.max_render_seconds != null ? `${r.max_render_seconds}s` : 'No data'}</p>
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
      </div>
    </div>
  );
}
