import React, { useState, useEffect, useCallback } from 'react';
import api from '../../utils/api';
import { Loader2, Activity, Cpu, Clock, AlertTriangle, RefreshCcw, Server, Gauge } from 'lucide-react';
import { Button } from '../ui/button';

export default function PerformanceMonitorTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.get('/api/pipeline/performance');
      if (res.data.success) setData(res.data);
    } catch (e) {
      console.error('Performance fetch error', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  if (loading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
    </div>
  );

  if (!data) return <p className="text-slate-400 text-center py-16">Unable to load performance data.</p>;

  const queue = data.queue || {};
  const render = data.render_stats || {};
  const workers = data.workers || {};

  // Thresholds for alerts
  const queueAlert = queue.queued > 5;
  const failureAlert = data.failure_rate > 10;
  const renderAlert = render.max_total_ms > 180000; // 3 min

  return (
    <div className="space-y-8" data-testid="performance-monitor-tab">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <Activity className="w-5 h-5 text-purple-400" /> Performance Monitor
        </h3>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-purple-500"
            />
            Auto-refresh (10s)
          </label>
          <Button onClick={fetchData} variant="outline" size="sm" className="border-slate-600 text-slate-400 hover:text-white">
            <RefreshCcw className="w-4 h-4 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {(queueAlert || failureAlert || renderAlert) && (
        <div className="space-y-2" data-testid="performance-alerts">
          {queueAlert && (
            <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-amber-300 text-sm">
              <AlertTriangle className="w-4 h-4" /> Queue backlog high: {queue.queued} jobs queued
            </div>
          )}
          {failureAlert && (
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-300 text-sm">
              <AlertTriangle className="w-4 h-4" /> High failure rate: {data.failure_rate}% in last hour
            </div>
          )}
          {renderAlert && (
            <div className="flex items-center gap-2 bg-orange-500/10 border border-orange-500/30 rounded-lg px-4 py-3 text-orange-300 text-sm">
              <AlertTriangle className="w-4 h-4" /> Render time spike: {Math.round(render.max_total_ms / 1000)}s max
            </div>
          )}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={Server}
          label="Queue Depth"
          value={queue.queued || 0}
          sub={`${queue.processing || 0} processing`}
          color="indigo"
          alert={queueAlert}
        />
        <MetricCard
          icon={Gauge}
          label="Failure Rate"
          value={`${data.failure_rate || 0}%`}
          sub={`${data.failed_last_hour || 0} / ${data.total_last_hour || 0} last hr`}
          color="red"
          alert={failureAlert}
        />
        <MetricCard
          icon={Clock}
          label="Avg Render"
          value={render.avg_total_ms ? `${Math.round(render.avg_total_ms / 1000)}s` : '—'}
          sub={render.count ? `${render.count} videos last hr` : 'No data'}
          color="emerald"
        />
        <MetricCard
          icon={Cpu}
          label="Max Render"
          value={render.max_total_ms ? `${Math.round(render.max_total_ms / 1000)}s` : '—'}
          sub="Peak this hour"
          color="amber"
          alert={renderAlert}
        />
      </div>

      {/* Worker Details */}
      <div>
        <h4 className="text-sm font-medium text-slate-300 mb-3 uppercase tracking-wide">Worker Pool</h4>
        <div className="bg-slate-700/30 rounded-xl border border-slate-600/50 p-4">
          {workers.total_workers != null ? (
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-white">{workers.total_workers || 0}</div>
                <div className="text-xs text-slate-400 mt-1">Total Workers</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-emerald-400">{workers.active_workers || 0}</div>
                <div className="text-xs text-slate-400 mt-1">Active</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-400">{workers.pending_jobs || queue.queued || 0}</div>
                <div className="text-xs text-slate-400 mt-1">Pending Jobs</div>
              </div>
            </div>
          ) : (
            <p className="text-slate-500 text-sm text-center py-4">Worker stats unavailable</p>
          )}
        </div>
      </div>

      {/* Timestamp */}
      <p className="text-xs text-slate-600 text-center">
        Last updated: {data.timestamp ? new Date(data.timestamp).toLocaleString() : '—'}
      </p>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, sub, color, alert }) {
  return (
    <div className={`bg-slate-700/30 rounded-xl border ${alert ? `border-${color}-500/50` : 'border-slate-600/50'} p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 text-${color}-400`} />
        <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${alert ? `text-${color}-400` : 'text-white'}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{sub}</p>
    </div>
  );
}
