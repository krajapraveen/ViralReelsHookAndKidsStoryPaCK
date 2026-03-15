import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Progress } from '../../components/ui/progress';
import {
  ArrowLeft, BarChart3, Clock, Zap, Users, TrendingUp,
  CheckCircle, XCircle, Activity, Eye, Download, Share2,
  Film, Package, Loader2, RefreshCw, Target
} from 'lucide-react';
import api from '../../utils/api';

function MetricCard({ label, value, unit, icon: Icon, color = 'purple', target, status }) {
  const isPass = status === 'pass';
  const bg = isPass ? 'bg-emerald-500/10 border-emerald-500/30' : status === 'fail' ? 'bg-red-500/10 border-red-500/30' : `bg-${color}-500/10 border-${color}-500/30`;
  const textColor = isPass ? 'text-emerald-400' : status === 'fail' ? 'text-red-400' : `text-${color}-400`;

  return (
    <div className={`p-4 rounded-xl border ${bg}`} data-testid={`metric-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${textColor}`} />
        <span className="text-xs text-slate-400 font-medium">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${textColor}`}>
          {value !== null && value !== undefined ? value : '—'}
        </span>
        <span className="text-xs text-slate-500">{unit}</span>
      </div>
      {target && (
        <div className="mt-2 flex items-center gap-1 text-xs">
          {isPass ? <CheckCircle className="w-3 h-3 text-emerald-400" /> : <XCircle className="w-3 h-3 text-red-400" />}
          <span className={isPass ? 'text-emerald-400' : 'text-red-400'}>
            Target: {target}{unit}
          </span>
        </div>
      )}
    </div>
  );
}

function TrendChart({ data, metricKey, label, color = '#a855f7' }) {
  if (!data || data.length === 0) return null;
  const values = data.map(d => d[metricKey]).filter(v => v != null);
  if (values.length === 0) return null;

  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const h = 80;
  const w = data.length * 40;

  return (
    <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
      <p className="text-xs text-slate-400 font-medium mb-2">{label}</p>
      <div className="overflow-x-auto">
        <svg width={Math.max(w, 200)} height={h + 30} className="min-w-full">
          {/* Grid lines */}
          {[0, 0.5, 1].map(pct => (
            <line
              key={pct}
              x1="0" y1={h - pct * h}
              x2={w} y2={h - pct * h}
              stroke="#334155" strokeWidth="0.5"
            />
          ))}
          {/* Data line */}
          <polyline
            fill="none"
            stroke={color}
            strokeWidth="2"
            points={data.map((d, i) => {
              const v = d[metricKey] ?? min;
              const y = h - ((v - min) / range) * h;
              return `${i * 40 + 20},${y}`;
            }).join(' ')}
          />
          {/* Data dots */}
          {data.map((d, i) => {
            const v = d[metricKey];
            if (v == null) return null;
            const y = h - ((v - min) / range) * h;
            return (
              <g key={i}>
                <circle cx={i * 40 + 20} cy={y} r="3" fill={color} />
                <text x={i * 40 + 20} y={h + 15} textAnchor="middle" className="text-[9px]" fill="#94a3b8">
                  {d.date?.slice(5)}
                </text>
                <text x={i * 40 + 20} y={y - 8} textAnchor="middle" className="text-[9px]" fill="#cbd5e1">
                  {v?.toFixed(1)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default function TTFDDashboard() {
  const [ttfd, setTtfd] = useState(null);
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ttfdRes, queueRes] = await Promise.all([
        api.get(`/api/analytics/ttfd?days=${days}`),
        api.get('/api/analytics/queue'),
      ]);
      setTtfd(ttfdRes.data?.data);
      setQueue(queueRes.data?.data);
    } catch (err) {
      console.error('Analytics fetch failed:', err);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  const ttfdData = ttfd?.ttfd || {};
  const targets = ttfd?.targets || [];
  const engagement = ttfd?.engagement || {};
  const health = ttfd?.pipeline_health || {};
  const trends = ttfd?.daily_trends || [];
  const queueData = queue || {};

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-[#0a0f1f] to-slate-950">
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="icon" className="text-white"><ArrowLeft className="w-5 h-5" /></Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white" data-testid="ttfd-dashboard-title">
                Performance Analytics
              </h1>
              <p className="text-xs text-slate-400">{ttfd?.jobs_analyzed || 0} jobs analyzed ({days} days)</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {[7, 14, 30].map(d => (
              <Button
                key={d}
                variant={days === d ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDays(d)}
                className={days === d ? 'bg-purple-600' : 'border-slate-700 text-slate-400'}
                data-testid={`period-${d}d`}
              >
                {d}d
              </Button>
            ))}
            <Button variant="outline" size="icon" onClick={fetchData} className="border-slate-700 text-slate-400" data-testid="refresh-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Performance vs Targets */}
        <section data-testid="targets-section">
          <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-purple-400" /> Performance vs Targets
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {targets.map(t => (
              <MetricCard
                key={t.metric}
                label={t.metric}
                value={t.current}
                unit={t.unit}
                icon={t.metric.includes('Scene') ? Clock : t.metric.includes('Image') ? Zap : t.metric.includes('Preview') ? Eye : Activity}
                target={t.target}
                status={t.status}
              />
            ))}
          </div>
        </section>

        {/* TTFD Detailed Metrics */}
        <section data-testid="ttfd-section">
          <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-purple-400" /> TTFD Metrics (Time to First Delight)
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            {Object.entries(ttfdData).map(([key, stats]) => (
              <div key={key} className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 font-medium mb-2">{key.replace(/_/g, ' ').replace('time to ', '')}</p>
                <p className="text-lg font-bold text-white">{stats.avg ? `${stats.avg}s` : '—'}</p>
                <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
                  <span>Med: {stats.median ?? '—'}s</span>
                  <span>P95: {stats.p95 ?? '—'}s</span>
                  <span>N={stats.count}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Daily Trends */}
        {trends.length > 0 && (
          <section data-testid="trends-section">
            <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-purple-400" /> Daily Trends
            </h2>
            <div className="grid lg:grid-cols-2 gap-4">
              <TrendChart data={trends} metricKey="avg_ttfs" label="Avg Time to First Scene (s)" color="#a855f7" />
              <TrendChart data={trends} metricKey="avg_ttfi" label="Avg Time to First Image (s)" color="#3b82f6" />
              <TrendChart data={trends} metricKey="avg_ttfp" label="Avg Time to Playable Preview (s)" color="#10b981" />
              <TrendChart data={trends} metricKey="avg_total" label="Avg Total Generation Time (s)" color="#f59e0b" />
            </div>
          </section>
        )}

        {/* Queue Performance */}
        <section data-testid="queue-section">
          <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-purple-400" /> Queue Performance (24h)
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard label="Queue Depth" value={queueData.queue_depth} unit="jobs" icon={Activity} color="blue" />
            <MetricCard label="Processing" value={queueData.processing} unit="jobs" icon={Loader2} color="amber" />
            {Object.entries(queueData.tier_wait_times_24h || {}).map(([tier, stats]) => (
              <div key={tier} className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
                <p className="text-xs text-slate-400 font-medium mb-1">{tier.toUpperCase()} Tier Wait</p>
                <p className="text-lg font-bold text-white">{stats.avg_ms}ms</p>
                <p className="text-[10px] text-slate-500">P95: {stats.p95_ms}ms | {stats.count} jobs</p>
              </div>
            ))}
          </div>
        </section>

        {/* Engagement Metrics */}
        <section data-testid="engagement-section">
          <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
            <Eye className="w-5 h-5 text-purple-400" /> User Engagement
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <MetricCard label="Preview Play Rate" value={engagement.preview_play_rate} unit="%" icon={Eye} color="emerald" />
            <MetricCard label="Export Start Rate" value={engagement.export_start_rate} unit="%" icon={Film} color="blue" />
            <MetricCard label="Export Completion" value={engagement.export_completion_rate} unit="%" icon={CheckCircle} color="emerald" />
            <MetricCard label="Pack Downloads" value={engagement.story_pack_download_rate} unit="%" icon={Package} color="amber" />
            <MetricCard label="Share Rate" value={engagement.share_rate} unit="%" icon={Share2} color="purple" />
          </div>
        </section>

        {/* Pipeline Health */}
        <section data-testid="health-section">
          <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-purple-400" /> Pipeline Health
          </h2>
          <div className="grid grid-cols-4 gap-3">
            <MetricCard label="Completed" value={health.completed} unit="jobs" icon={CheckCircle} color="emerald" />
            <MetricCard label="Partial (Fallback)" value={health.partial} unit="jobs" icon={Package} color="amber" />
            <MetricCard label="Failed" value={health.failed} unit="jobs" icon={XCircle} color="red" />
            <MetricCard label="Success Rate" value={health.export_success_rate} unit="%" icon={TrendingUp} color="emerald" />
          </div>
        </section>
      </main>
    </div>
  );
}
