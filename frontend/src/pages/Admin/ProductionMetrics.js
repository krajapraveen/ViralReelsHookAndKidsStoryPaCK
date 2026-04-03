import React, { useState, useEffect, useCallback } from 'react';
import api from '../../utils/api';
import { toast } from 'sonner';
import {
  BarChart3, RefreshCw, Activity, Camera, Palette, Download,
  Clock, Users, Zap, TrendingUp, CheckCircle, XCircle,
  FileText, Archive, ChevronLeft, ChevronRight, Filter
} from 'lucide-react';
import { Button } from '../../components/ui/button';

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'brand_kit', label: 'Brand Kit', icon: Palette },
  { id: 'photo_to_comic', label: 'Photo to Comic', icon: Camera },
  { id: 'jobs', label: 'Job Log', icon: FileText },
];

const PERIODS = [
  { value: 7, label: '7d' },
  { value: 14, label: '14d' },
  { value: 30, label: '30d' },
  { value: 90, label: '90d' },
];

function fmt(ms) {
  if (!ms && ms !== 0) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function pct(v) {
  if (v === null || v === undefined) return '—';
  return `${v}%`;
}

function StatCard({ icon: Icon, label, value, sub, color = 'slate', testId }) {
  const colors = {
    blue: 'border-blue-500/20 bg-blue-500/5',
    green: 'border-emerald-500/20 bg-emerald-500/5',
    red: 'border-red-500/20 bg-red-500/5',
    amber: 'border-amber-500/20 bg-amber-500/5',
    cyan: 'border-cyan-500/20 bg-cyan-500/5',
    purple: 'border-purple-500/20 bg-purple-500/5',
    slate: 'border-slate-700 bg-slate-800/50',
  };
  const iconColors = {
    blue: 'text-blue-400', green: 'text-emerald-400', red: 'text-red-400',
    amber: 'text-amber-400', cyan: 'text-cyan-400', purple: 'text-purple-400',
    slate: 'text-slate-400',
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`} data-testid={testId}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${iconColors[color]}`} />
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${value === '—' || value === 'No data' ? 'text-slate-600 text-base' : 'text-white'}`}>
        {value}
      </p>
      {sub && <p className="text-[11px] mt-1 text-slate-500">{sub}</p>}
    </div>
  );
}

function ProgressBar({ current, goal, label }) {
  const pctVal = Math.min((current / Math.max(goal, 1)) * 100, 100);
  const color = pctVal >= 100 ? 'from-emerald-500 to-emerald-400' :
    pctVal >= 50 ? 'from-cyan-500 to-blue-500' : 'from-amber-500 to-orange-500';
  return (
    <div data-testid="validation-progress-bar">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-xs font-mono text-white">{current} / {goal}</span>
      </div>
      <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-700`}
          style={{ width: `${pctVal}%` }}
        />
      </div>
      <p className="text-[10px] text-slate-600 mt-1">{pctVal.toFixed(0)}% of validation target</p>
    </div>
  );
}

function HBar({ label, value, max, color = 'cyan' }) {
  const w = max ? Math.max((value / max) * 100, 2) : 0;
  const gradients = {
    cyan: 'from-cyan-500 to-blue-500',
    amber: 'from-amber-500 to-orange-500',
    green: 'from-emerald-500 to-emerald-400',
    purple: 'from-purple-500 to-indigo-500',
  };
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-28 text-right flex-shrink-0 truncate">{label}</span>
      <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${gradients[color]} rounded-full transition-all`} style={{ width: `${w}%` }} />
      </div>
      <span className="text-xs text-white font-mono w-10 text-right">{value}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OVERVIEW TAB
// ═══════════════════════════════════════════════════
function OverviewTab({ data }) {
  if (!data) return <Loading />;
  const { totals, brand_kit, photo_to_comic, target } = data;

  return (
    <div className="space-y-6" data-testid="overview-tab">
      {/* Validation Target */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-cyan-400" /> Validation Target
        </h3>
        <ProgressBar current={target.current} goal={target.goal} label="Total real jobs toward 200-job validation" />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Activity} label="Total Jobs" value={totals.jobs} color="blue" testId="total-jobs" />
        <StatCard icon={CheckCircle} label="Success Rate" value={pct(totals.success_rate)} sub={`${totals.success} succeeded`} color="green" testId="success-rate" />
        <StatCard icon={Zap} label="Credits Consumed" value={totals.credits_consumed} color="amber" testId="credits-consumed" />
        <StatCard icon={Download} label="Downloads" value={totals.downloads} color="cyan" testId="total-downloads" />
      </div>

      {/* Feature Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FeatureCard
          title="Brand Kit Generator"
          icon={Palette}
          color="purple"
          stats={brand_kit}
          testId="bk-overview"
        />
        <FeatureCard
          title="Photo to Comic"
          icon={Camera}
          color="cyan"
          stats={photo_to_comic}
          testId="ptc-overview"
        />
      </div>
    </div>
  );
}

function FeatureCard({ title, icon: Icon, color, stats, testId }) {
  const borderColor = color === 'purple' ? 'border-purple-500/20' : 'border-cyan-500/20';
  const iconColor = color === 'purple' ? 'text-purple-400' : 'text-cyan-400';
  return (
    <div className={`bg-slate-900/60 border ${borderColor} rounded-xl p-5`} data-testid={testId}>
      <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <Icon className={`w-4 h-4 ${iconColor}`} /> {title}
      </h4>
      <div className="grid grid-cols-3 gap-3">
        <MiniStat label="Jobs" value={stats.jobs} />
        <MiniStat label="Success" value={pct(stats.success_rate)} good={stats.success_rate >= 80} />
        <MiniStat label="Failed" value={stats.failed} bad={stats.failed > 0} />
        <MiniStat label="Credits" value={stats.credits} />
        <MiniStat label="Downloads" value={stats.downloads} />
        <MiniStat label="Failure %" value={stats.failed > 0 ? pct((stats.failed / Math.max(stats.jobs, 1) * 100).toFixed(1)) : '0%'} bad={stats.failed > 0} />
      </div>
    </div>
  );
}

function MiniStat({ label, value, good, bad }) {
  const color = good ? 'text-emerald-400' : bad ? 'text-red-400' : 'text-white';
  return (
    <div className="bg-slate-800/50 rounded-lg p-2.5 text-center">
      <p className="text-[9px] text-slate-500 uppercase mb-1">{label}</p>
      <p className={`text-base font-bold ${color}`}>{value ?? '—'}</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// BRAND KIT TAB
// ═══════════════════════════════════════════════════
function BrandKitTab({ data }) {
  if (!data) return <Loading />;
  const noData = data.total_jobs === 0;

  if (noData) return <EmptyState feature="Brand Kit Generator" />;

  return (
    <div className="space-y-6" data-testid="brand-kit-tab">
      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard icon={Activity} label="Total Jobs" value={data.total_jobs} color="blue" testId="bk-total" />
        <StatCard icon={CheckCircle} label="Success Rate" value={pct(data.success_rate)} color="green" testId="bk-success" />
        <StatCard icon={XCircle} label="Failure Rate" value={pct(data.failure_rate)} color="red" testId="bk-failure" />
        <StatCard icon={Download} label="Downloads" value={data.downloads?.total ?? 0} sub={`PDF: ${data.downloads?.pdf ?? 0} | ZIP: ${data.downloads?.zip ?? 0}`} color="cyan" testId="bk-downloads" />
        <StatCard icon={Users} label="Unique Users" value={data.regenerate?.unique_users ?? 0} sub={`Regen rate: ${pct(data.regenerate?.regenerate_rate)}`} color="purple" testId="bk-users" />
      </div>

      {/* Mode Split & Timing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mode Split */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" /> Mode Split
          </h4>
          <div className="space-y-3">
            <HBar label="Fast (10 cr)" value={data.mode_split?.fast ?? 0} max={data.total_jobs} color="amber" />
            <HBar label="Pro (25 cr)" value={data.mode_split?.pro ?? 0} max={data.total_jobs} color="purple" />
          </div>
          <div className="mt-4 flex gap-4 text-xs text-slate-500">
            <span>Fast: {pct(data.mode_split?.fast_pct)}</span>
            <span>Pro: {pct(data.mode_split?.pro_pct)}</span>
          </div>
        </div>

        {/* Timing */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" /> Generation Timing
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="Avg Total" value={fmt(data.timing?.avg_total_ms)} />
            <MiniStat label="Time to 1st Artifact" value={fmt(data.timing?.avg_time_to_first_artifact_ms)} />
            <MiniStat label="p50 Total" value={fmt(data.timing?.p50_total_ms)} />
            <MiniStat label="p95 Total" value={fmt(data.timing?.p95_total_ms)} />
          </div>
        </div>
      </div>

      {/* Status Breakdown */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
        <h4 className="text-sm font-semibold text-white mb-3">Status Breakdown</h4>
        <div className="grid grid-cols-4 gap-3">
          <MiniStat label="Ready" value={data.status_breakdown?.ready ?? 0} good />
          <MiniStat label="Partial Ready" value={data.status_breakdown?.partial_ready ?? 0} />
          <MiniStat label="Failed" value={data.status_breakdown?.failed ?? 0} bad={data.status_breakdown?.failed > 0} />
          <MiniStat label="Generating" value={data.status_breakdown?.generating ?? 0} />
        </div>
      </div>

      {/* Per-Artifact Metrics */}
      {data.artifact_metrics && Object.keys(data.artifact_metrics).length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" /> Per-Artifact Performance
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="artifact-table">
              <thead>
                <tr className="text-slate-500 border-b border-slate-800">
                  <th className="text-left py-2 pr-4">Artifact</th>
                  <th className="text-right py-2 px-2">Avg Latency</th>
                  <th className="text-right py-2 px-2">p50</th>
                  <th className="text-right py-2 px-2">p95</th>
                  <th className="text-right py-2 px-2">Success</th>
                  <th className="text-right py-2 px-2">Fallback</th>
                  <th className="text-right py-2 px-2">Failed</th>
                  <th className="text-right py-2 pl-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.artifact_metrics).map(([name, m]) => (
                  <tr key={name} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-2 pr-4 text-slate-300 font-mono">{name.replace(/_/g, ' ')}</td>
                    <td className="text-right py-2 px-2 text-white">{fmt(m.avg_latency_ms)}</td>
                    <td className="text-right py-2 px-2 text-slate-400">{fmt(m.p50_latency_ms)}</td>
                    <td className="text-right py-2 px-2 text-slate-400">{fmt(m.p95_latency_ms)}</td>
                    <td className="text-right py-2 px-2 text-emerald-400">{pct(m.success_rate)}</td>
                    <td className="text-right py-2 px-2 text-amber-400">{pct(m.fallback_rate)}</td>
                    <td className="text-right py-2 px-2 text-red-400">{pct(m.failure_rate)}</td>
                    <td className="text-right py-2 pl-2 text-slate-400">{m.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Download Conversion & Industry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Download Conversion */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Download className="w-4 h-4 text-cyan-400" /> Completion-to-Download
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="Completed Jobs" value={(data.status_breakdown?.ready ?? 0) + (data.status_breakdown?.partial_ready ?? 0)} />
            <MiniStat label="Downloads" value={data.downloads?.total ?? 0} />
            <MiniStat label="PDF" value={data.downloads?.pdf ?? 0} />
            <MiniStat label="ZIP" value={data.downloads?.zip ?? 0} />
          </div>
          <p className="text-xs text-slate-500 mt-3">Download rate: <span className="text-white font-mono">{pct(data.downloads?.download_rate)}</span></p>
        </div>

        {/* Industry Distribution */}
        {data.industry_distribution?.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
            <h4 className="text-sm font-semibold text-white mb-3">Top Industries</h4>
            <div className="space-y-2">
              {data.industry_distribution.map((ind) => (
                <HBar key={ind.industry} label={ind.industry} value={ind.count} max={data.industry_distribution[0]?.count} color="green" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// PHOTO TO COMIC TAB
// ═══════════════════════════════════════════════════
function PhotoToComicTab({ data }) {
  if (!data) return <Loading />;
  const noData = data.total_jobs === 0;

  if (noData) return <EmptyState feature="Photo to Comic" />;

  return (
    <div className="space-y-6" data-testid="photo-to-comic-tab">
      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard icon={Activity} label="Total Jobs" value={data.total_jobs} color="blue" testId="ptc-total" />
        <StatCard icon={CheckCircle} label="Success Rate" value={pct(data.success_rate)} color="green" testId="ptc-success" />
        <StatCard icon={XCircle} label="Failure Rate" value={pct(data.failure_rate)} color="red" testId="ptc-failure" />
        <StatCard icon={Download} label="Downloaded" value={data.downloads?.downloaded ?? 0} sub={`Rate: ${pct(data.downloads?.download_rate)}`} color="cyan" testId="ptc-downloads" />
        <StatCard icon={Users} label="Unique Users" value={data.users?.unique ?? 0} sub={`Regen: ${pct(data.users?.regenerate_rate)}`} color="purple" testId="ptc-users" />
      </div>

      {/* Type Split & Timing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Camera className="w-4 h-4 text-cyan-400" /> Type Split
          </h4>
          <div className="space-y-3">
            <HBar label="Avatar" value={data.type_split?.avatar ?? 0} max={data.total_jobs} color="cyan" />
            <HBar label="Comic Strip" value={data.type_split?.strip ?? 0} max={data.total_jobs} color="purple" />
          </div>
          <div className="mt-4 flex gap-4 text-xs text-slate-500">
            <span>Avatar: {pct(data.type_split?.avatar_pct)}</span>
            <span>Strip: {pct(data.type_split?.strip_pct)}</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" /> Generation Timing
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <MiniStat label="Avg Latency" value={fmt(data.timing?.avg_latency_ms)} />
            <MiniStat label="p50" value={fmt(data.timing?.p50_latency_ms)} />
            <MiniStat label="p95" value={fmt(data.timing?.p95_latency_ms)} />
            <MiniStat label="Credits Used" value={data.credits_consumed ?? 0} />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <MiniStat label="Avatar Avg" value={fmt(data.timing?.avatar_avg_ms)} />
            <MiniStat label="Strip Avg" value={fmt(data.timing?.strip_avg_ms)} />
          </div>
        </div>
      </div>

      {/* Status & Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-white mb-3">Status Breakdown</h4>
          <div className="grid grid-cols-3 gap-3">
            <MiniStat label="Completed" value={data.status_breakdown?.completed ?? 0} good />
            <MiniStat label="Failed" value={data.status_breakdown?.failed ?? 0} bad={data.status_breakdown?.failed > 0} />
            <MiniStat label="Processing" value={data.status_breakdown?.processing ?? 0} />
          </div>
        </div>

        {data.style_distribution?.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
            <h4 className="text-sm font-semibold text-white mb-3">Style Popularity</h4>
            <div className="space-y-2">
              {data.style_distribution.map((s) => (
                <HBar key={s.style} label={s.style.replace(/_/g, ' ')} value={s.count} max={data.style_distribution[0]?.count} color="purple" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// JOB LOG TAB
// ═══════════════════════════════════════════════════
function JobLogTab({ period }) {
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [featureFilter, setFeatureFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/production-metrics/jobs', {
        params: { feature: featureFilter, page, limit }
      });
      setJobs(res.data.jobs || []);
      setTotal(res.data.total || 0);
    } catch {
      toast.error('Failed to load job log');
    }
    setLoading(false);
  }, [featureFilter, page]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const totalPages = Math.ceil(total / limit);
  const statusColor = (s) => {
    if (['READY', 'COMPLETED'].includes(s)) return 'text-emerald-400';
    if (['PARTIAL_READY'].includes(s)) return 'text-amber-400';
    if (['FAILED'].includes(s)) return 'text-red-400';
    return 'text-slate-400';
  };

  return (
    <div className="space-y-4" data-testid="job-log-tab">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-slate-500" />
        {['all', 'brand_kit', 'photo_to_comic'].map((f) => (
          <button
            key={f}
            onClick={() => { setFeatureFilter(f); setPage(1); }}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              featureFilter === f ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'text-slate-500 hover:text-white bg-slate-800/50'
            }`}
            data-testid={`filter-${f}`}
          >
            {f === 'all' ? 'All' : f === 'brand_kit' ? 'Brand Kit' : 'Photo to Comic'}
          </button>
        ))}
        <span className="text-xs text-slate-600 ml-auto">{total} jobs</span>
      </div>

      {/* Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-12">No jobs found</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs" data-testid="job-log-table">
              <thead>
                <tr className="text-slate-500 border-b border-slate-800 bg-slate-900/80">
                  <th className="text-left py-2.5 px-3">Job ID</th>
                  <th className="text-left py-2.5 px-2">Feature</th>
                  <th className="text-left py-2.5 px-2">Status</th>
                  <th className="text-left py-2.5 px-2">Mode</th>
                  <th className="text-right py-2.5 px-2">Credits</th>
                  <th className="text-left py-2.5 px-2">Detail</th>
                  <th className="text-left py-2.5 px-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-2 px-3 font-mono text-slate-400">{j.job_id?.slice(0, 8)}...</td>
                    <td className="py-2 px-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        j.feature === 'brand_kit' ? 'bg-purple-500/10 text-purple-400' : 'bg-cyan-500/10 text-cyan-400'
                      }`}>
                        {j.feature === 'brand_kit' ? 'Brand Kit' : 'Photo'}
                      </span>
                    </td>
                    <td className={`py-2 px-2 font-medium ${statusColor(j.status)}`}>{j.status}</td>
                    <td className="py-2 px-2 text-slate-400">{j.mode}</td>
                    <td className="py-2 px-2 text-right text-amber-400">{j.credits ?? '—'}</td>
                    <td className="py-2 px-2 text-slate-500 truncate max-w-[140px]">
                      {j.business_name || j.style || '—'}
                    </td>
                    <td className="py-2 px-3 text-slate-500">
                      {j.created_at ? new Date(j.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="text-xs"
            data-testid="prev-page"
          >
            <ChevronLeft className="w-3 h-3" />
          </Button>
          <span className="text-xs text-slate-500">{page} / {totalPages}</span>
          <Button
            size="sm"
            variant="outline"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="text-xs"
            data-testid="next-page"
          >
            <ChevronRight className="w-3 h-3" />
          </Button>
        </div>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div className="flex items-center justify-center py-16">
      <RefreshCw className="w-6 h-6 text-slate-500 animate-spin" />
    </div>
  );
}

function EmptyState({ feature }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center" data-testid="empty-state">
      <Activity className="w-10 h-10 text-slate-700 mb-3" />
      <p className="text-sm text-slate-500">No {feature} jobs in this period</p>
      <p className="text-xs text-slate-600 mt-1">Real job data will appear here as users create content</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════
export default function ProductionMetrics() {
  const [tab, setTab] = useState('overview');
  const [period, setPeriod] = useState(30);
  const [loading, setLoading] = useState(false);
  const [overviewData, setOverviewData] = useState(null);
  const [brandKitData, setBrandKitData] = useState(null);
  const [ptcData, setPtcData] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, bkRes, ptcRes] = await Promise.all([
        api.get('/api/production-metrics/overview', { params: { days: period } }),
        api.get('/api/production-metrics/brand-kit', { params: { days: period } }),
        api.get('/api/production-metrics/photo-to-comic', { params: { days: period } }),
      ]);
      setOverviewData(ovRes.data);
      setBrandKitData(bkRes.data);
      setPtcData(ptcRes.data);
      setLastRefresh(new Date());
    } catch (err) {
      toast.error('Failed to load production metrics');
    }
    setLoading(false);
  }, [period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="min-h-screen bg-slate-950 text-white" data-testid="production-metrics-page">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-lg font-bold text-white flex items-center gap-2" data-testid="page-title">
                <BarChart3 className="w-5 h-5 text-cyan-400" />
                Production Metrics
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Validation phase — tracking real production jobs
                {lastRefresh && (
                  <span className="ml-2 text-slate-600">
                    Updated {Math.round((Date.now() - lastRefresh.getTime()) / 1000)}s ago
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Period selector */}
              <div className="flex bg-slate-900 rounded-lg border border-slate-800 p-0.5">
                {PERIODS.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setPeriod(p.value)}
                    className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                      period === p.value ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-500 hover:text-white'
                    }`}
                    data-testid={`period-${p.value}`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchData}
                disabled={loading}
                className="text-xs"
                data-testid="refresh-btn"
              >
                <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1">
            {TABS.map((t) => {
              const Icon = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`flex items-center gap-1.5 text-xs px-4 py-2 rounded-t-lg transition-colors ${
                    tab === t.id
                      ? 'bg-slate-900 text-white border-t border-x border-slate-700'
                      : 'text-slate-500 hover:text-white hover:bg-slate-900/50'
                  }`}
                  data-testid={`tab-${t.id}`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {tab === 'overview' && <OverviewTab data={overviewData} />}
        {tab === 'brand_kit' && <BrandKitTab data={brandKitData} />}
        {tab === 'photo_to_comic' && <PhotoToComicTab data={ptcData} />}
        {tab === 'jobs' && <JobLogTab period={period} />}
      </div>
    </div>
  );
}
