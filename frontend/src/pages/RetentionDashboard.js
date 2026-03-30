import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Activity, Clock, MousePointerClick, BarChart3, TrendingDown, Eye, Play, Zap } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

function MetricCard({ title, value, subtitle, target, icon: Icon, color = 'text-white', status }) {
  const statusColor = status === 'good' ? 'text-emerald-400' : status === 'warn' ? 'text-amber-400' : status === 'bad' ? 'text-red-400' : 'text-white/40';
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#121218] p-5" data-testid={`metric-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-center gap-3 mb-3">
        {Icon && <Icon size={18} className={color} />}
        <span className="text-white/50 text-xs font-semibold uppercase tracking-wider">{title}</span>
      </div>
      <div className="text-3xl font-bold text-white tracking-tight">
        {value ?? <span className="text-white/20">No data</span>}
      </div>
      {subtitle && <p className="text-white/40 text-xs mt-1">{subtitle}</p>}
      {target && <p className={`text-xs mt-2 ${statusColor}`}>Target: {target}</p>}
    </div>
  );
}

function RetentionCurve({ data }) {
  if (!data || data.length === 0) return null;
  const maxCount = Math.max(...data.map(d => d.count), 1);
  const total = data.reduce((acc, d) => acc + d.count, 0) || 1;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#121218] p-5" data-testid="retention-curve">
      <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-4">Session Retention Curve</h3>
      <div className="space-y-2">
        {data.map((bucket) => {
          const pct = Math.round((bucket.count / total) * 100);
          const barWidth = Math.max(2, (bucket.count / maxCount) * 100);
          const isGood = bucket.bucket.includes('min');
          return (
            <div key={bucket.bucket} className="flex items-center gap-3">
              <span className="text-white/40 text-xs w-14 text-right shrink-0">{bucket.bucket}</span>
              <div className="flex-1 h-5 bg-white/[0.03] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${isGood ? 'bg-emerald-500/70' : 'bg-white/15'}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <span className="text-white/60 text-xs w-12 text-right">{pct}%</span>
              <span className="text-white/30 text-xs w-8 text-right">{bucket.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TrendChart({ trends, metricKey, label, color = '#818cf8' }) {
  if (!trends || trends.length === 0) return null;
  const values = trends.map(t => t[metricKey] || 0);
  const max = Math.max(...values, 1);
  const min = Math.min(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * 100;
    const y = 100 - ((v - min) / range) * 80 - 10;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#121218] p-5" data-testid={`trend-${metricKey}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-white/50 text-xs font-semibold uppercase tracking-wider">{label}</span>
        <span className="text-white/30 text-xs">{trends.length} days</span>
      </div>
      <svg viewBox="0 0 100 100" className="w-full h-20" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="flex justify-between mt-2">
        <span className="text-white/30 text-[10px]">{trends[0]?.date?.slice(5)}</span>
        <span className="text-white text-xs font-semibold">{values[values.length - 1]?.toFixed?.(1) ?? values[values.length - 1]}</span>
        <span className="text-white/30 text-[10px]">{trends[trends.length - 1]?.date?.slice(5)}</span>
      </div>
    </div>
  );
}

function PreviewAnalytics({ data }) {
  if (!data) return null;
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#121218] p-5" data-testid="preview-analytics">
      <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-4">Autoplay Preview Funnel</h3>
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <Eye size={16} className="text-white/30 mx-auto mb-1" />
          <div className="text-lg font-bold text-white">{data.impressions || 0}</div>
          <div className="text-white/30 text-[10px]">Impressions</div>
        </div>
        <div className="text-center">
          <Play size={16} className="text-purple-400 mx-auto mb-1" />
          <div className="text-lg font-bold text-white">{data.plays || 0}</div>
          <div className="text-white/30 text-[10px]">Plays ({data.play_rate ?? 0}%)</div>
        </div>
        <div className="text-center">
          <MousePointerClick size={16} className="text-emerald-400 mx-auto mb-1" />
          <div className="text-lg font-bold text-white">{data.clicks || 0}</div>
          <div className="text-white/30 text-[10px]">Clicks ({data.click_conversion ?? 0}%)</div>
        </div>
      </div>
    </div>
  );
}

export default function RetentionDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API}/api/admin/retention/dashboard?days=${days}`, auth());
        setData(res.data);
      } catch (e) {
        console.error('Retention dashboard load failed:', e);
      }
      setLoading(false);
    };
    load();
  }, [days]);

  const m = data?.metrics || {};
  const avgSec = m.avg_session_time?.seconds || 0;
  const sessionStatus = avgSec >= 300 ? 'good' : avgSec >= 180 ? 'warn' : avgSec > 0 ? 'bad' : null;
  const hookCtr = m.hook_ctr?.rate;
  const hookStatus = hookCtr >= 15 ? 'good' : hookCtr >= 8 ? 'warn' : hookCtr > 0 ? 'bad' : null;
  const contRate = m.continue_rate?.rate;
  const contStatus = contRate >= 10 ? 'good' : contRate >= 5 ? 'warn' : contRate > 0 ? 'bad' : null;
  const dropoff = m.dropoff_10s?.rate;
  const dropStatus = dropoff !== null ? (dropoff <= 10 ? 'good' : dropoff <= 25 ? 'warn' : 'bad') : null;

  function formatTime(sec) {
    if (!sec || sec <= 0) return 'No data';
    if (sec < 60) return `${Math.round(sec)}s`;
    const mins = Math.floor(sec / 60);
    const secs = Math.round(sec % 60);
    return `${mins}m ${secs}s`;
  }

  return (
    <div className="min-h-screen bg-[#0B0B0F] text-white" data-testid="retention-dashboard">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-[#0B0B0F]/95 backdrop-blur-xl border-b border-white/[0.04] px-4 py-3 sm:px-6">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/app/admin')} className="p-2 rounded-xl hover:bg-white/5 transition-colors" data-testid="back-btn">
              <ArrowLeft size={18} className="text-white/60" />
            </button>
            <div>
              <h1 className="text-base font-bold text-white">Retention Analytics</h1>
              <p className="text-white/30 text-xs">The 5 metrics that matter</p>
            </div>
          </div>
          <div className="flex gap-2">
            {[7, 14, 30].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${days === d ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/60'}`}
                data-testid={`period-${d}d`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-6 h-6 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 space-y-6">
          {/* Top 5 Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3" data-testid="metrics-grid">
            <MetricCard
              title="Avg Session"
              value={formatTime(avgSec)}
              subtitle={`${m.avg_session_time?.total_sessions || 0} sessions`}
              target="3 min+ = good"
              icon={Clock}
              color="text-purple-400"
              status={sessionStatus}
            />
            <MetricCard
              title="Hook CTR"
              value={hookCtr !== null ? `${hookCtr}%` : null}
              subtitle={`${m.hook_ctr?.clicks || 0} / ${m.hook_ctr?.impressions || 0}`}
              target="15%+ CTR"
              icon={MousePointerClick}
              color="text-amber-400"
              status={hookStatus}
            />
            <MetricCard
              title="Continue Rate"
              value={contRate !== null ? `${contRate}%` : null}
              subtitle={`${m.continue_rate?.continues || 0} / ${m.continue_rate?.views || 0}`}
              target="10%+ rate"
              icon={Zap}
              color="text-emerald-400"
              status={contStatus}
            />
            <MetricCard
              title="10s Drop-Off"
              value={dropoff !== null ? `${dropoff}%` : null}
              subtitle={`${m.dropoff_10s?.dropped || 0} / ${m.dropoff_10s?.total_sessions || 0}`}
              target="<10% drop"
              icon={TrendingDown}
              color="text-red-400"
              status={dropStatus}
            />
            <MetricCard
              title="Scroll Depth"
              value={Object.keys(m.scroll_depth?.distribution || {}).length > 0
                ? `${Object.values(m.scroll_depth?.distribution || {}).reduce((a, b) => a + b, 0)} tracked`
                : null}
              subtitle="Sessions with scroll data"
              target="50%+ reach depth 5+"
              icon={BarChart3}
              color="text-blue-400"
            />
          </div>

          {/* Device Breakdown */}
          {m.avg_session_time?.device_breakdown && Object.keys(m.avg_session_time.device_breakdown).length > 0 && (
            <div className="rounded-2xl border border-white/[0.06] bg-[#121218] p-5" data-testid="device-breakdown">
              <h3 className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-3">By Device</h3>
              <div className="flex gap-4">
                {Object.entries(m.avg_session_time.device_breakdown).map(([device, stats]) => (
                  <div key={device} className="flex items-center gap-3 px-4 py-2 rounded-xl bg-white/[0.03]">
                    <span className="text-white/60 text-sm capitalize">{device}</span>
                    <span className="text-white font-bold text-sm">{formatTime(stats.avg_seconds)}</span>
                    <span className="text-white/30 text-xs">({stats.count})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Retention Curve + Preview Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RetentionCurve data={data?.retention_curve} />
            <PreviewAnalytics data={data?.preview_analytics} />
          </div>

          {/* Trend Charts */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <TrendChart trends={data?.trends} metricKey="avg_session_seconds" label="Session Time (s)" color="#a78bfa" />
            <TrendChart trends={data?.trends} metricKey="hook_ctr" label="Hook CTR (%)" color="#fbbf24" />
            <TrendChart trends={data?.trends} metricKey="sessions" label="Daily Sessions" color="#34d399" />
            <TrendChart trends={data?.trends} metricKey="dropoff_10s" label="10s Drop-Off (%)" color="#f87171" />
          </div>
        </div>
      )}
    </div>
  );
}
