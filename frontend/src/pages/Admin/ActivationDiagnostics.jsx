import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ArrowLeft, AlertTriangle, RefreshCw, Activity, Smartphone, Monitor,
  Users, User, Flame, Timer, ChevronDown, Lock, TrendingUp, TrendingDown, Minus,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import api from '../../utils/api';

/**
 * /app/admin/activation-diagnostics — V13.1 2026-05
 *
 * Founder directive: show where users die between landing and first published
 * story, and once P0-4 (anonymous pre-wow) ships, show the BEFORE/AFTER answer.
 *
 * Layout priority (above-the-fold, no scroll for critical signals):
 *   1. Biggest-drop badge   (dominant, left)
 *   2. Auth-wall card        (right)
 *   3. Rage / Repeat CTA     (right)
 *   4. Median time to abandon (left strip)
 *   5. Mobile vs Desktop heatmap (visible without scroll on 1440px+)
 *   6. P0-4 Before/After comparison (the verdict)
 *   7. Full funnel + abandonment tables below
 */
export default function ActivationDiagnostics() {
  const [days, setDays] = useState(7);
  const [deviceFilter, setDeviceFilter] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);

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

  const loadComparison = useCallback(async () => {
    setComparisonLoading(true);
    try {
      const r = await api.get('/api/funnel/p04-comparison?days_before=7&days_after=7');
      setComparison(r.data);
    } catch (e) {
      // 404/no-data is fine — comparison panel just renders the empty CTA
      setComparison(null);
    } finally {
      setComparisonLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadComparison(); }, [loadComparison]);

  const markP04Launch = async () => {
    try {
      await api.post('/api/funnel/p04-launch');
      toast.success('P0-4 launch timestamp marked. Comparison will populate as new data arrives.');
      loadComparison();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to mark P0-4 launch');
    }
  };

  const stages = data?.stages || [];
  const redAlerts = data?.red_alerts || [];
  const abandonment = data?.abandonment_breakdown || [];
  const unmapped = data?.unmapped_reasons || [];
  const biggestDrop = data?.biggest_drop;
  const heatmap = data?.abandonment_heatmap || [];
  const authWall = data?.auth_wall || { total_sessions: 0, pct_of_landing: 0, breakdown: [] };
  const maxSessions = Math.max(1, ...stages.map((s) => s.sessions || 0));

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
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
        <div className="flex flex-wrap items-center gap-3 mb-5">
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

        {/* Red alerts strip — surfaced ABOVE the fold */}
        {redAlerts.length > 0 && (
          <div className="mb-4 space-y-2" data-testid="red-alerts-strip">
            {redAlerts.map((a, i) => (
              <div key={i} className="flex items-center gap-3 bg-red-950/40 border border-red-500/40 rounded-lg px-4 py-2.5" data-testid={`red-alert-${i}`}>
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-red-200">{a.rule}</p>
                  <p className="text-[11px] text-red-300/80">
                    {a.observed_pct != null && `Observed ${a.observed_pct}% (threshold ${a.threshold_pct}%)`}
                    {a.observed_ms != null && `Observed ${a.observed_ms}ms (threshold ${a.threshold_ms}ms)`}
                    {' · '}{a.from_step} → {a.to_step}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ─── DOMINANT HERO STRIP (above the fold) ───────────────────────
            biggest-drop badge (left, span-2)  +  auth-wall + rage (right column) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-4">
          {biggestDrop ? (
            <div
              className="lg:col-span-2 rounded-2xl border-2 border-amber-500/60 bg-gradient-to-br from-amber-950/70 via-rose-950/40 to-slate-900 p-6 shadow-[0_0_40px_rgba(245,158,11,0.15)]"
              data-testid="biggest-drop-badge"
            >
              <div className="flex items-center gap-2 mb-3 text-amber-300">
                <ChevronDown className="w-6 h-6" />
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em]">Biggest Drop · The Bleed</span>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-white leading-tight">
                {biggestDrop.from_label} <span className="text-amber-400">→</span> {biggestDrop.to_label}
              </p>
              <p className="text-base text-amber-100/90 mt-2 leading-snug">
                <span className="font-mono text-2xl text-amber-300">{biggestDrop.drop_pct}%</span> of users die here.
                Only <span className="font-mono text-white">{biggestDrop.to_sessions}</span> of <span className="font-mono text-white">{biggestDrop.from_sessions}</span> made it through
                (<span className="font-mono">{biggestDrop.conversion_pct}%</span> conversion).
              </p>
              <p className="text-xs text-slate-400 mt-3">
                Median time at this stage: <span className="font-mono text-slate-200">{biggestDrop.median_to_next_ms != null ? `${biggestDrop.median_to_next_ms}ms` : 'n/a'}</span>
                {' · '}P95: <span className="font-mono text-slate-200">{biggestDrop.p95_to_next_ms != null ? `${biggestDrop.p95_to_next_ms}ms` : 'n/a'}</span>
              </p>
            </div>
          ) : (
            <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex items-center justify-center text-slate-500" data-testid="biggest-drop-empty">
              No funnel drop detected yet in this window.
            </div>
          )}

          {/* Right column: stacked critical cards */}
          <div className="flex flex-col gap-3">
            {/* Auth-wall — explicit, separate */}
            <div
              className={`rounded-xl border-2 p-4 ${authWall.total_sessions > 0 ? 'border-rose-500/50 bg-rose-950/40' : 'border-slate-800 bg-slate-900/60'}`}
              data-testid="auth-wall-card"
            >
              <div className="flex items-center gap-2 mb-1 text-rose-300">
                <Lock className="w-4 h-4" />
                <span className="text-[10px] font-semibold uppercase tracking-wider">Auth Wall Hits</span>
              </div>
              <p className="text-3xl font-bold font-mono text-white leading-none" data-testid="auth-wall-count">
                {authWall.total_sessions}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {authWall.pct_of_landing}% of landings · signup/paywall fired before wow
              </p>
              {authWall.breakdown?.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {authWall.breakdown.slice(0, 3).map((b, i) => (
                    <li key={i} className="text-[10px] text-rose-200/80 font-mono">
                      {b.reason} <span className="text-rose-400">×{b.session_count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Rage / repeat CTA */}
            <div className="rounded-xl border-2 border-orange-500/30 bg-orange-950/30 p-4" data-testid="rage-click-card">
              <div className="flex items-center gap-2 mb-1 text-orange-300">
                <Flame className="w-4 h-4" />
                <span className="text-[10px] font-semibold uppercase tracking-wider">Rage / Repeat CTA</span>
              </div>
              <p className="text-3xl font-bold font-mono text-white leading-none" data-testid="rage-click-count">
                {data?.rage_click_sessions ?? 0}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">≥3 CTA clicks within 5s</p>
              <p className="text-[10px] text-slate-500 mt-0.5">
                Repeat-CTA: <span className="font-mono">{data?.repeated_cta_sessions ?? 0}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Median-time-to-abandon strip */}
        <div className="mb-4 rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4 flex items-center gap-3" data-testid="time-to-abandon-card">
          <Timer className="w-5 h-5 text-indigo-300" />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Median time before abandonment</p>
            <p className="text-xl font-bold text-white font-mono">
              {data?.median_time_to_abandon_ms != null ? `${data.median_time_to_abandon_ms} ms` : 'n/a'}
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">Across sessions that clicked CTA but never reached generation_completed.</p>
          </div>
        </div>

        {/* ─── Mobile vs Desktop heatmap — surfaced above-the-fold ──────── */}
        {heatmap.length > 0 && (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-950/10 overflow-hidden mb-4" data-testid="heatmap-section">
            <div className="px-4 py-2.5 border-b border-cyan-500/20 flex items-center gap-2 bg-slate-900/60">
              <Smartphone className="w-4 h-4 text-cyan-300" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-cyan-200">Mobile vs Desktop Abandonment Heatmap</h2>
            </div>
            <table className="w-full text-sm" data-testid="heatmap-table">
              <thead className="text-[10px] uppercase text-slate-500 bg-slate-950/40">
                <tr>
                  <th className="text-left px-4 py-2">From Step</th>
                  <th className="text-right px-4 py-2">Mobile Died %</th>
                  <th className="text-right px-4 py-2">Desktop Died %</th>
                  <th className="text-right px-4 py-2">Δ (m − d)</th>
                </tr>
              </thead>
              <tbody>
                {heatmap.map((h, i) => {
                  const delta = (h.mobile_death_pct || 0) - (h.desktop_death_pct || 0);
                  const cellBg = (pct) => pct > 70 ? 'text-red-400' : pct > 40 ? 'text-amber-300' : 'text-slate-300';
                  return (
                    <tr key={i} className="border-t border-slate-800/60" data-testid={`heatmap-row-${h.from_step}`}>
                      <td className="px-4 py-2 text-slate-200">{h.from_label}</td>
                      <td className={`text-right px-4 py-2 font-mono ${cellBg(h.mobile_death_pct)}`}>
                        {h.mobile_death_pct}%
                        <span className="text-slate-600 ml-1 text-[10px]">({h.mobile_died}/{h.mobile_total})</span>
                      </td>
                      <td className={`text-right px-4 py-2 font-mono ${cellBg(h.desktop_death_pct)}`}>
                        {h.desktop_death_pct}%
                        <span className="text-slate-600 ml-1 text-[10px]">({h.desktop_died}/{h.desktop_total})</span>
                      </td>
                      <td className={`text-right px-4 py-2 font-mono ${Math.abs(delta) > 20 ? 'text-amber-400' : 'text-slate-500'}`}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)} pp
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ─── P0-4 Before/After Comparison ────────────────────────────── */}
        <ComparisonPanel comparison={comparison} loading={comparisonLoading} onMarkLaunch={markP04Launch} />

        {/* Conversion bars */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 mb-6" data-testid="conversion-bars">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4">Funnel — Conversion Bars</h2>
          <div className="space-y-3">
            {stages.map((s, i) => {
              const widthPct = (s.sessions / maxSessions) * 100;
              const danger = i > 0 && s.conversion_from_prev_pct < 60;
              return (
                <div key={s.step} data-testid={`conv-bar-${s.step}`}>
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>
                      <span className="text-white font-medium">{s.label}</span>
                      <span className="text-slate-600 ml-2 font-mono">{s.step}</span>
                    </span>
                    <span className="font-mono">
                      {s.sessions} sessions
                      {i > 0 && <span className={`ml-2 ${danger ? 'text-red-400' : 'text-emerald-300'}`}>· {s.conversion_from_prev_pct}%</span>}
                    </span>
                  </div>
                  <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${danger ? 'bg-gradient-to-r from-red-500 to-amber-500' : 'bg-gradient-to-r from-indigo-500 to-emerald-500'}`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Funnel table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-300" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Funnel — Per-Step</h2>
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

        {/* Abandonment breakdown — sorted by frequency (backend returns sorted) */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-300" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Top Abandonment Reasons (sorted by frequency)</h2>
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
                <tr key={i} className="border-t border-slate-800/60" data-testid={`abandonment-row-${i}`}>
                  <td className="px-4 py-2 text-slate-300">{a.abandonment_step || '—'}</td>
                  <td className="px-4 py-2 text-slate-200">
                    {a.abandonment_reason}
                    {!a.is_canonical && <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-300 text-[9px] font-mono">unmapped</span>}
                  </td>
                  <td className="text-right px-4 py-2 font-mono text-amber-300">{a.count}</td>
                </tr>
              ))}
              {abandonment.length === 0 && (
                <tr><td colSpan={3} className="text-center py-8 text-slate-500">No abandonment events captured yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Unmapped reasons */}
        {unmapped.length > 0 && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 mb-6" data-testid="unmapped-reasons">
            <div className="flex items-center gap-2 text-amber-300 mb-2">
              <AlertTriangle className="w-4 h-4" />
              <h2 className="text-sm font-semibold uppercase tracking-wider">Unmapped Abandonment Reasons</h2>
            </div>
            <p className="text-xs text-amber-200/80 mb-2">
              These reasons fired but are NOT in the canonical taxonomy. Add them to <code className="bg-slate-900/60 px-1 rounded">ABANDONMENT_REASONS</code> in <code className="bg-slate-900/60 px-1 rounded">routes/funnel_tracking.py</code>.
            </p>
            <ul className="text-xs font-mono space-y-1">
              {unmapped.map((u, i) => (
                <li key={i} className="text-amber-100">{u.reason} <span className="text-amber-500 ml-2">×{u.count}</span></li>
              ))}
            </ul>
          </div>
        )}

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

// ─── P0-4 Before/After Comparison Panel ────────────────────────────────
function ComparisonPanel({ comparison, loading, onMarkLaunch }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 mb-4" data-testid="p04-comparison-loading">
        <p className="text-sm text-slate-400">Loading P0-4 comparison…</p>
      </div>
    );
  }
  if (!comparison || !comparison.success) {
    return (
      <div className="rounded-xl border-2 border-indigo-500/30 bg-indigo-950/30 p-5 mb-4" data-testid="p04-comparison-empty">
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-indigo-300 mt-0.5" />
          <div className="flex-1">
            <h2 className="text-base font-bold text-white">P0-4 Comparison · Not Yet Launched</h2>
            <p className="text-xs text-slate-400 mt-1">
              Mark the moment the anonymous pre-wow flow goes live so we can split metrics before/after.
              The hard answer ("did P0-4 improve activation?") will populate within 24-48h of marking.
            </p>
            <Button onClick={onMarkLaunch} size="sm" className="mt-3 bg-indigo-600 hover:bg-indigo-500" data-testid="mark-p04-launch-btn">
              Mark P0-4 Launch Now
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const { pre, post, deltas, verdict, verdict_signals = [], p04_launch_ts } = comparison;

  const verdictColor = {
    IMPROVED: 'border-emerald-500/60 bg-emerald-950/40 text-emerald-200',
    REGRESSED: 'border-rose-500/60 bg-rose-950/40 text-rose-200',
    FLAT: 'border-slate-700 bg-slate-900/40 text-slate-300',
    INSUFFICIENT_DATA: 'border-amber-500/40 bg-amber-950/30 text-amber-200',
  }[verdict] || 'border-slate-700 bg-slate-900 text-slate-300';

  const VerdictIcon = verdict === 'IMPROVED' ? TrendingUp : verdict === 'REGRESSED' ? TrendingDown : Minus;

  const Row = ({ label, preVal, postVal, delta, unit = '', better = 'higher' }) => {
    const dir = better === 'higher' ? (delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat')
                                    : (delta < 0 ? 'up' : delta > 0 ? 'down' : 'flat');
    const cls = dir === 'up' ? 'text-emerald-300' : dir === 'down' ? 'text-rose-300' : 'text-slate-400';
    const fmt = (v) => (v == null ? '—' : `${v}${unit}`);
    return (
      <tr className="border-t border-slate-800/60" data-testid={`p04-row-${label.replace(/\s+/g, '-').toLowerCase()}`}>
        <td className="px-4 py-2 text-slate-200">{label}</td>
        <td className="text-right px-4 py-2 font-mono text-slate-400">{fmt(preVal)}</td>
        <td className="text-right px-4 py-2 font-mono text-white">{fmt(postVal)}</td>
        <td className={`text-right px-4 py-2 font-mono ${cls}`}>
          {delta == null ? '—' : `${delta > 0 ? '+' : ''}${delta}${unit}`}
        </td>
      </tr>
    );
  };

  return (
    <div
      className={`rounded-2xl border-2 ${verdictColor} p-5 mb-5`}
      data-testid="p04-comparison-panel"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <VerdictIcon className="w-5 h-5" />
          <h2 className="text-base font-bold">P0-4 Anonymous Pre-Wow · Before vs After</h2>
        </div>
        <span className="text-[11px] font-mono opacity-70" data-testid="p04-verdict">VERDICT: {verdict}</span>
      </div>
      <p className="text-xs opacity-80 mb-3">
        Launched at <span className="font-mono">{p04_launch_ts}</span>.
        {verdict_signals.length > 0 && ' Signals: ' + verdict_signals.join(' · ')}
      </p>
      <div className="rounded-lg overflow-hidden border border-slate-800/60 bg-slate-950/40">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wider text-slate-500 bg-slate-900/60">
            <tr>
              <th className="text-left px-4 py-2">Metric</th>
              <th className="text-right px-4 py-2">Pre</th>
              <th className="text-right px-4 py-2">Post</th>
              <th className="text-right px-4 py-2">Δ</th>
            </tr>
          </thead>
          <tbody>
            <Row label="Story generated (sessions)" preVal={pre.story_generated} postVal={post.story_generated} delta={deltas.story_generated_delta} />
            <Row label="CTA → Generation %" preVal={pre.cta_to_generation_pct} postVal={post.cta_to_generation_pct} delta={deltas.cta_to_generation_pct_delta} unit="%" />
            <Row label="Landing → Generation %" preVal={pre.landing_to_generation_pct} postVal={post.landing_to_generation_pct} delta={deltas.landing_to_generation_pct_delta} unit="%" />
            <Row label="Anon share of generation %" preVal={pre.anon_share_of_generation_pct} postVal={post.anon_share_of_generation_pct} delta={deltas.anon_share_of_generation_pct_delta} unit="%" />
            <Row label="Teaser latency median (ms)" preVal={pre.teaser_median_ms} postVal={post.teaser_median_ms} delta={deltas.teaser_median_ms_delta} unit=" ms" better="lower" />
            <Row label="Abandonment after CTA %" preVal={pre.abandonment_pct} postVal={post.abandonment_pct} delta={deltas.abandonment_pct_delta} unit="%" better="lower" />
            <Row label="Auth-wall sessions" preVal={pre.auth_wall_sessions} postVal={post.auth_wall_sessions} delta={deltas.auth_wall_delta} better="lower" />
          </tbody>
        </table>
      </div>
    </div>
  );
}
