import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, AlertTriangle, RefreshCw, Activity, Smartphone, Monitor, Users, User } from 'lucide-react';
import { Button } from '../../components/ui/button';
import api from '../../utils/api';

/**
 * /app/admin/activation-diagnostics — V13 2026-05 P0-3
 *
 * Founder directive: a single page that shows where users die between
 * landing and first published story. No cosmetic work, no polishing.
 * Consumes /api/funnel/activation-funnel which has been extended with
 * `red_alerts` and `abandonment_breakdown`.
 */
export default function ActivationDiagnostics() {
  const [days, setDays] = useState(7);
  const [deviceFilter, setDeviceFilter] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ days: String(days) });
      if (deviceFilter) params.set('device_type', deviceFilter);
      const r = await api.get(`/api/funnel/activation-funnel?${params.toString()}`);
      setData(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load diagnostics');
    } finally {
      setLoading(false);
    }
  }, [days, deviceFilter]);

  useEffect(() => { load(); }, [load]);

  const stages = data?.stages || [];
  const redAlerts = data?.red_alerts || [];
  const abandonment = data?.abandonment_breakdown || [];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link to="/app/admin" className="text-slate-400 hover:text-white">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold">Activation Diagnostics</h1>
              <p className="text-sm text-slate-400">Where users die between landing and first published story.</p>
            </div>
          </div>
          <Button onClick={load} disabled={loading} variant="outline" className="border-slate-700" data-testid="reload-btn">
            <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Reload
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <label className="text-sm text-slate-400">Window</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm"
            data-testid="window-select"
          >
            <option value={1}>Last 24h</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
          </select>
          <label className="text-sm text-slate-400 ml-4">Device</label>
          <select
            value={deviceFilter}
            onChange={(e) => setDeviceFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-sm"
            data-testid="device-select"
          >
            <option value="">All</option>
            <option value="mobile">Mobile</option>
            <option value="desktop">Desktop</option>
            <option value="tablet">Tablet</option>
          </select>
          <div className="ml-auto text-xs text-slate-500" data-testid="session-count">
            {data?.total_sessions_seen ?? '—'} sessions in window
          </div>
        </div>

        {/* Red alerts strip */}
        {redAlerts.length > 0 && (
          <div className="mb-6 space-y-2" data-testid="red-alerts-strip">
            {redAlerts.map((a, i) => (
              <div key={i} className="flex items-center gap-3 bg-red-950/40 border border-red-500/40 rounded-lg px-4 py-3" data-testid={`red-alert-${i}`}>
                <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-red-200">{a.rule}</p>
                  <p className="text-xs text-red-300/80">
                    {a.observed_pct != null && `Observed ${a.observed_pct}% (threshold ${a.threshold_pct}%)`}
                    {a.observed_ms != null && `Observed ${a.observed_ms}ms (threshold ${a.threshold_ms}ms)`}
                    {' · '}{a.from_step} → {a.to_step}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Funnel table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-300" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Funnel</h2>
          </div>
          <table className="w-full text-sm" data-testid="funnel-table">
            <thead className="text-xs uppercase text-slate-500 bg-slate-950/60">
              <tr>
                <th className="text-left px-4 py-2">Step</th>
                <th className="text-right px-4 py-2">Sessions</th>
                <th className="text-right px-4 py-2">Conv. from prev</th>
                <th className="text-right px-4 py-2">Median → next</th>
                <th className="text-right px-4 py-2">P95 → next</th>
                <th className="text-right px-4 py-2">Mobile / Desktop</th>
                <th className="text-right px-4 py-2">Anon / Auth</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((s, i) => {
                const dangerConv = i > 0 && s.conversion_from_prev_pct < 60;
                return (
                  <tr key={s.step} className="border-t border-slate-800/60" data-testid={`row-${s.step}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{s.label}</div>
                      <div className="text-[10px] text-slate-500">{s.step}</div>
                    </td>
                    <td className="text-right px-4 py-3 font-mono">{s.sessions}</td>
                    <td className={`text-right px-4 py-3 font-mono ${dangerConv ? 'text-red-400' : 'text-emerald-300'}`}>
                      {i === 0 ? '—' : `${s.conversion_from_prev_pct}%`}
                    </td>
                    <td className="text-right px-4 py-3 font-mono text-slate-300">
                      {s.median_to_next_ms != null ? `${s.median_to_next_ms} ms` : '—'}
                    </td>
                    <td className="text-right px-4 py-3 font-mono text-slate-400">
                      {s.p95_to_next_ms != null ? `${s.p95_to_next_ms} ms` : '—'}
                    </td>
                    <td className="text-right px-4 py-3 font-mono text-slate-400">
                      <span className="inline-flex items-center gap-1"><Smartphone className="w-3 h-3" />{s.mobile}</span>
                      <span className="text-slate-700 mx-1">/</span>
                      <span className="inline-flex items-center gap-1"><Monitor className="w-3 h-3" />{s.desktop}</span>
                    </td>
                    <td className="text-right px-4 py-3 font-mono text-slate-400">
                      <span className="inline-flex items-center gap-1"><Users className="w-3 h-3" />{s.anon_sessions}</span>
                      <span className="text-slate-700 mx-1">/</span>
                      <span className="inline-flex items-center gap-1"><User className="w-3 h-3" />{s.auth_sessions}</span>
                    </td>
                  </tr>
                );
              })}
              {stages.length === 0 && !loading && (
                <tr><td colSpan={7} className="text-center py-8 text-slate-500">No funnel data in window.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Abandonment breakdown */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-300" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Top Abandonment Reasons</h2>
          </div>
          <table className="w-full text-sm" data-testid="abandonment-table">
            <thead className="text-xs uppercase text-slate-500 bg-slate-950/60">
              <tr>
                <th className="text-left px-4 py-2">Step</th>
                <th className="text-left px-4 py-2">Reason</th>
                <th className="text-right px-4 py-2">Count</th>
              </tr>
            </thead>
            <tbody>
              {abandonment.map((a, i) => (
                <tr key={i} className="border-t border-slate-800/60">
                  <td className="px-4 py-2 text-slate-300">{a.abandonment_step || '—'}</td>
                  <td className="px-4 py-2 text-slate-200">{a.abandonment_reason}</td>
                  <td className="text-right px-4 py-2 font-mono text-amber-300">{a.count}</td>
                </tr>
              ))}
              {abandonment.length === 0 && (
                <tr><td colSpan={3} className="text-center py-8 text-slate-500">No abandonment events captured yet. Frontend needs to emit `story_generation_abandoned` with an `abandonment_reason`.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Speed SLA */}
        {data?.speed_sla && (
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 mb-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-3">Speed SLAs</h2>
            <pre className="text-xs text-slate-400 whitespace-pre-wrap" data-testid="speed-sla-json">
              {JSON.stringify(data.speed_sla, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
