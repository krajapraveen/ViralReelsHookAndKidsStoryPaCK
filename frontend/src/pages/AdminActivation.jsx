import React, { useEffect, useState, useCallback } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  RefreshCw, AlertOctagon, Activity, Smartphone, Monitor, Globe2,
  ChevronRight, AlertTriangle, Gauge,
} from 'lucide-react';

/**
 * P0 Activation Funnel Dashboard
 * Route: /admin/activation
 *
 * Founder spec (Apr 23): show exact drop-off step in
 *   landing_view → cta_clicked → signup_modal_opened → signup_success →
 *   dashboard_loaded → prompt_submitted → story_generation_started →
 *   story_generation_completed
 * Plus: median time-per-step, mobile vs desktop split, browser split,
 *       country split, top exit step, frontend error counts.
 */
export default function AdminActivation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [deviceFilter, setDeviceFilter] = useState('');
  const [browserFilter, setBrowserFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ days: String(days) });
      if (deviceFilter) qs.set('device_type', deviceFilter);
      if (browserFilter) qs.set('browser', browserFilter);
      const res = await api.get(`/api/funnel/activation-funnel?${qs.toString()}`);
      setData(res.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load activation funnel');
    } finally {
      setLoading(false);
    }
  }, [days, deviceFilter, browserFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6" data-testid="admin-activation">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Activity className="w-6 h-6 text-amber-400" />
              Activation Funnel
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Where new visitors die between landing and a created story.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              data-testid="activation-days-select"
            >
              <option value={1}>Last 1 day</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <select
              value={deviceFilter}
              onChange={(e) => setDeviceFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              data-testid="activation-device-select"
            >
              <option value="">All devices</option>
              <option value="mobile">Mobile</option>
              <option value="desktop">Desktop</option>
              <option value="tablet">Tablet</option>
            </select>
            <select
              value={browserFilter}
              onChange={(e) => setBrowserFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              data-testid="activation-browser-select"
            >
              <option value="">All browsers</option>
              <option value="chrome">Chrome</option>
              <option value="safari">Safari</option>
              <option value="firefox">Firefox</option>
              <option value="edge">Edge</option>
              <option value="other">Other</option>
            </select>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm"
              data-testid="activation-refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {loading && !data && (
          <div className="text-center py-20 text-slate-500" data-testid="activation-loading">Loading funnel...</div>
        )}

        {data && (
          <>
            {/* Top Exit Hero */}
            {data.top_exit_step && (
              <div
                className="mb-6 rounded-2xl border border-rose-500/40 bg-gradient-to-br from-rose-950/60 via-slate-950 to-slate-950 p-6"
                data-testid="activation-top-exit"
              >
                <div className="flex items-center gap-3 mb-2">
                  <AlertOctagon className="w-5 h-5 text-rose-400" />
                  <p className="text-xs uppercase tracking-[0.2em] text-rose-400 font-bold">
                    Top Drop-Off
                  </p>
                </div>
                <p className="text-2xl font-bold text-white">
                  {data.top_exit_step.drop_count} sessions left after “{data.top_exit_step.after_step}”
                </p>
                <p className="text-sm text-rose-300 mt-1">
                  That's {data.top_exit_step.drop_pct}% of viewers who reached this step.
                </p>
              </div>
            )}

            {/* The funnel */}
            <section className="mb-8" data-testid="activation-funnel-stages">
              <h2 className="text-lg font-semibold mb-3 text-slate-200">Funnel ({data.total_sessions_seen} sessions)</h2>
              <div className="space-y-2">
                {data.stages.map((s, i) => {
                  const widthPct = data.stages[0].sessions > 0
                    ? (s.sessions / data.stages[0].sessions) * 100
                    : 0;
                  const dropFromPrev = i > 0
                    ? (data.stages[i - 1].sessions - s.sessions)
                    : 0;
                  return (
                    <div
                      key={s.step}
                      className="rounded-xl border border-slate-800 bg-slate-900/60 p-4"
                      data-testid={`activation-stage-${s.step}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 font-mono w-6">{i + 1}.</span>
                          <span className="text-sm font-medium text-white">{s.label}</span>
                          {i > 0 && dropFromPrev > 0 && (
                            <span className="text-xs text-rose-400">
                              -{dropFromPrev} ({(100 - s.conversion_from_prev_pct).toFixed(1)}% drop)
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          {s.median_to_next_ms != null && (
                            <span className="text-slate-500 text-xs">
                              median to next: {(s.median_to_next_ms / 1000).toFixed(1)}s
                            </span>
                          )}
                          <span className="font-bold text-white tabular-nums">{s.sessions}</span>
                          <span className="text-emerald-300 text-sm font-bold tabular-nums">
                            {s.conversion_from_prev_pct}%
                          </span>
                        </div>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500"
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Smartphone className="w-3 h-3" /> {s.mobile} mobile
                        </span>
                        <span className="flex items-center gap-1">
                          <Monitor className="w-3 h-3" /> {s.desktop} desktop
                        </span>
                        {s.tablet > 0 && (
                          <span className="flex items-center gap-1">
                            <ChevronRight className="w-3 h-3" /> {s.tablet} tablet
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Speed SLA panel (P0 Apr 2026 directive) */}
            {data.speed_sla && data.speed_sla.length > 0 && (
              <section className="mb-8" data-testid="activation-speed-sla">
                <h2 className="text-lg font-semibold mb-3 text-slate-200 flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-cyan-400" />
                  Speed SLA
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {data.speed_sla.map((s) => {
                    const healthy = s.samples > 0 && s.breach_pct <= 10;
                    const warn = s.samples > 0 && s.breach_pct > 10 && s.breach_pct <= 30;
                    const ringClass = s.samples === 0
                      ? 'border-slate-800 bg-slate-900/40'
                      : healthy
                        ? 'border-emerald-500/30 bg-emerald-950/20'
                        : warn
                          ? 'border-amber-500/30 bg-amber-950/20'
                          : 'border-rose-500/40 bg-rose-950/30';
                    return (
                      <div
                        key={s.event}
                        className={`rounded-2xl border ${ringClass} p-4`}
                        data-testid={`sla-${s.event}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs uppercase tracking-wider text-slate-400 font-mono">{s.event}</span>
                          <span className="text-xs text-slate-500">≤ {s.threshold_ms}ms</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-bold text-white tabular-nums">
                            {s.median_ms != null ? `${s.median_ms}` : '—'}
                          </span>
                          <span className="text-xs text-slate-500">ms p50</span>
                          {s.p95_ms != null && (
                            <span className="ml-auto text-xs text-slate-400 tabular-nums">p95 {s.p95_ms}ms</span>
                          )}
                        </div>
                        <div className="mt-2 text-xs text-slate-400">
                          {s.samples} samples ·
                          <span className={s.breach_pct > 10 ? ' text-rose-400 font-semibold' : ' text-emerald-300'}>
                            {' '}{s.breach_pct}% breach
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* Browser + country splits + errors side-by-side */}
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
              {/* Browser */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4" data-testid="activation-browser-split">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
                  <Globe2 className="w-4 h-4 text-violet-400" />
                  Browser at landing
                </h3>
                {data.browser_split.length === 0 && (
                  <p className="text-xs text-slate-500">No data yet</p>
                )}
                {data.browser_split.map((b) => (
                  <div key={b.browser} className="flex items-center justify-between text-sm py-1">
                    <span className="text-slate-300 capitalize">{b.browser}</span>
                    <span className="font-mono text-white">{b.sessions}</span>
                  </div>
                ))}
              </div>

              {/* Country */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4" data-testid="activation-country-split">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
                  <Globe2 className="w-4 h-4 text-emerald-400" />
                  Country at landing
                </h3>
                {data.country_split.length === 0 && (
                  <p className="text-xs text-slate-500">No country data — check your ingress is forwarding CF-IPCountry.</p>
                )}
                {data.country_split.map((c) => (
                  <div key={c.country} className="flex items-center justify-between text-sm py-1">
                    <span className="text-slate-300">{c.country}</span>
                    <span className="font-mono text-white">{c.sessions}</span>
                  </div>
                ))}
              </div>

              {/* Errors */}
              <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4" data-testid="activation-errors">
                <h3 className="text-sm font-semibold text-amber-200 flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  Frontend Failures
                </h3>
                {data.error_breakdown.length === 0 && (
                  <p className="text-xs text-slate-500">No errors logged in window. Either healthy, or sentinel needs a deploy cycle.</p>
                )}
                {data.error_breakdown.map((e) => (
                  <div key={e.step} className="flex items-center justify-between text-sm py-1">
                    <span className="text-amber-200 text-xs">{e.step}</span>
                    <span className="font-mono text-white">{e.count} <span className="text-amber-400/60 text-xs">({e.unique_sessions} sess)</span></span>
                  </div>
                ))}
              </div>
            </section>

            <p className="text-xs text-slate-600 mt-4" data-testid="activation-meta">
              Window: {data.period_days} days · {data.total_sessions_seen} sessions ·
              filter: {data.filter.device_type || 'all devices'}, {data.filter.browser || 'all browsers'}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
