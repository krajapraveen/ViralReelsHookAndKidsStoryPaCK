/* eslint-disable */
// PhotoTrailerKpiDashboard — founder KPI readout for YouStar / Photo Trailer.
// One screen, 27 KPIs across Acquisition / Engagement / Conversion / Revenue
// / Ops / Virality. Truth-first, no chart-library bloat. 24h / 7d / 30d toggle.
//
// Mounted at /app/admin/photo-trailers (admin auth gated by AdminLayout).
import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, RefreshCw, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const RANGES = [
  { key: '24h', label: '24h' },
  { key: '7d',  label: '7d'  },
  { key: '30d', label: '30d' },
];

function fmtNum(v) {
  if (v == null) return '—';
  if (typeof v === 'number' && !Number.isFinite(v)) return '—';
  if (typeof v === 'number' && v >= 1000) return v.toLocaleString();
  return String(v);
}
function fmtPct(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return `${Number(v).toFixed(1)}%`;
}
function fmtSec(v) {
  if (v == null) return '—';
  if (v < 60) return `${Number(v).toFixed(1)}s`;
  return `${Math.floor(v / 60)}m ${Math.round(v % 60)}s`;
}

const Section = ({ title, children, testId }) => (
  <section className="mb-10" data-testid={testId}>
    <h2 className="text-xs uppercase tracking-[0.2em] text-violet-300 font-bold mb-3">
      {title}
    </h2>
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {children}
    </div>
  </section>
);

const Stat = ({ label, value, sub, accent, testId }) => (
  <div
    data-testid={testId}
    className="rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.05] transition-colors p-4"
  >
    <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">{label}</div>
    <div className={`text-2xl font-bold ${accent || 'text-white'}`}>{value}</div>
    {sub != null && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
  </div>
);

// Horizontal bar block — no charting library, just CSS widths.
const BarRow = ({ label, value, max, suffix, testId }) => {
  const pct = max ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-sm" data-testid={testId}>
      <div className="w-32 text-slate-400 truncate">{label}</div>
      <div className="flex-1 h-2 rounded-full bg-white/[0.05] overflow-hidden">
        <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500"
             style={{ width: `${pct}%` }} />
      </div>
      <div className="w-20 text-right text-white font-semibold tabular-nums">
        {value}{suffix || ''}
      </div>
    </div>
  );
};

export default function PhotoTrailerKpiDashboard() {
  const [range, setRange] = useState('7d');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = useCallback(async (r) => {
    setLoading(true); setErr(null);
    try {
      const tok = localStorage.getItem('token');
      const res = await fetch(`${API}/api/photo-trailer/admin/dashboard?range=${r}`, {
        headers: { Authorization: `Bearer ${tok}` },
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`${res.status} ${t.slice(0, 200)}`);
      }
      setData(await res.json());
    } catch (e) {
      setErr(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(range); }, [range, load]);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-[#0a0a10] text-white flex items-center justify-center"
           data-testid="kpi-dash-loading">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (err) {
    return (
      <div className="min-h-screen bg-[#0a0a10] text-white flex items-center justify-center px-6"
           data-testid="kpi-dash-error">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="w-10 h-10 mx-auto text-amber-400" />
          <div className="text-lg font-bold">Could not load dashboard</div>
          <div className="text-xs text-slate-400 break-all">{err}</div>
          <button onClick={() => load(range)}
                  className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-sm"
                  data-testid="kpi-dash-retry">Retry</button>
        </div>
      </div>
    );
  }

  const a = data?.acquisition || {};
  const e = data?.engagement  || {};
  const c = data?.conversion  || {};
  const r = data?.revenue     || {};
  const o = data?.ops         || {};
  const v = data?.virality    || {};

  const srcMax = Math.max(1, ...Object.values(a.source_split || {}));
  const fmtMax = Math.max(1, ...Object.values(e.format_play_split || {}));

  return (
    <div className="min-h-screen bg-[#0a0a10] text-white" data-testid="photo-trailer-kpi-dash">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <header className="mb-8 flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] text-violet-300 font-bold">YouStar</div>
            <h1 className="text-3xl sm:text-4xl font-black mt-1">Photo Trailer · KPI Dashboard</h1>
            <p className="text-sm text-slate-400 mt-1">
              Truth-first measurement readout. Generated {data?.generated_at?.replace('T', ' ').slice(0, 19)} UTC
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-xl border border-white/10 bg-white/[0.03] p-1"
                 data-testid="kpi-dash-range-toggle">
              {RANGES.map((rg) => (
                <button
                  key={rg.key}
                  onClick={() => setRange(rg.key)}
                  data-testid={`kpi-dash-range-${rg.key}`}
                  className={`px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${
                    range === rg.key ? 'bg-violet-600 text-white' : 'text-slate-300 hover:text-white'
                  }`}
                >{rg.label}</button>
              ))}
            </div>
            <button onClick={() => load(range)} disabled={loading}
                    className="p-2 rounded-lg border border-white/10 hover:bg-white/[0.05] disabled:opacity-50"
                    data-testid="kpi-dash-refresh">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </header>

        {/* ═══════════════ ACQUISITION ═══════════════ */}
        <Section title="1 · Acquisition" testId="kpi-section-acquisition">
          <Stat label="Share page views" value={fmtNum(a.share_page_views)}
                testId="kpi-share-page-views" />
          <Stat label="Unique visitors" value={fmtNum(a.unique_visitors)}
                testId="kpi-unique-visitors" />
        </Section>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 mb-10"
             data-testid="kpi-source-split">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Source split</div>
          <div className="space-y-2">
            <BarRow label="WhatsApp"     value={a.source_split?.whatsapp     || 0} max={srcMax} testId="kpi-src-whatsapp" />
            <BarRow label="Native share" value={a.source_split?.native_share || 0} max={srcMax} testId="kpi-src-native" />
            <BarRow label="Direct"       value={a.source_split?.direct       || 0} max={srcMax} testId="kpi-src-direct" />
            <BarRow label="Other"        value={a.source_split?.other        || 0} max={srcMax} testId="kpi-src-other" />
          </div>
        </div>

        {/* ═══════════════ ENGAGEMENT ═══════════════ */}
        <Section title="2 · Engagement" testId="kpi-section-engagement">
          <Stat label="View → Play" value={fmtPct(e.view_to_play_pct)}
                sub={`${fmtNum(e.plays_unique)} plays`} testId="kpi-view-to-play" />
          <Stat label="Reached 25%" value={fmtPct(e.watch_25_pct)} testId="kpi-watch-25" />
          <Stat label="Reached 50%" value={fmtPct(e.watch_50_pct)} testId="kpi-watch-50" />
          <Stat label="Reached 75%" value={fmtPct(e.watch_75_pct)} testId="kpi-watch-75" />
          <Stat label="Completed (100%)" value={fmtPct(e.watch_100_pct)} accent="text-emerald-400"
                testId="kpi-watch-100" />
        </Section>
        <div className="grid md:grid-cols-2 gap-6 mb-10">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
               data-testid="kpi-format-split">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Wide vs Vertical play rate</div>
            <div className="space-y-2">
              <BarRow label="16:9 Wide"     value={e.format_play_split?.wide     || 0} max={fmtMax} testId="kpi-fmt-wide" />
              <BarRow label="9:16 Vertical" value={e.format_play_split?.vertical || 0} max={fmtMax} testId="kpi-fmt-vertical" />
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
               data-testid="kpi-top-templates-completion">
            <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Top templates · completion rate</div>
            {(e.top_templates_by_completion || []).length === 0 ? (
              <div className="text-xs text-slate-500">No data yet in this range.</div>
            ) : (
              <div className="space-y-1.5">
                {e.top_templates_by_completion.slice(0, 6).map((t) => (
                  <div key={t.template_id} className="flex justify-between text-sm">
                    <span className="text-slate-300 truncate pr-2">{t.title}</span>
                    <span className="text-white font-semibold tabular-nums">
                      {fmtPct(t.completion_pct)}{' '}
                      <span className="text-slate-500 text-xs">({t.completes}/{t.views})</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ═══════════════ CONVERSION ═══════════════ */}
        <Section title="3 · Conversion" testId="kpi-section-conversion">
          <Stat label="Make Your Own CTR"   value={fmtPct(c.make_your_own_ctr_pct)}
                sub={`${fmtNum(c.make_your_own_clicks)} clicks`} testId="kpi-make-your-own-ctr" />
          <Stat label="Signup started"      value={fmtNum(c.signup_started)} testId="kpi-signup-started" />
          <Stat label="Signup completed"    value={fmtNum(c.signup_completed)} testId="kpi-signup-completed" />
          <Stat label="First trailer created" value={fmtNum(c.first_trailer_created)}
                accent="text-emerald-400" testId="kpi-first-trailer" />
          <Stat label="View → Signup"       value={fmtPct(c.view_to_signup_pct)} testId="kpi-view-to-signup" />
          <Stat label="Signup → First trailer" value={fmtPct(c.signup_to_first_trailer_pct)}
                testId="kpi-signup-to-first" />
        </Section>

        {/* ═══════════════ REVENUE ═══════════════ */}
        <Section title="4 · Revenue" testId="kpi-section-revenue">
          <Stat label="Free jobs"      value={fmtNum(r.free_jobs)}    testId="kpi-jobs-free" />
          <Stat label="Paid jobs"      value={fmtNum(r.paid_jobs)}    testId="kpi-jobs-paid" />
          <Stat label="Premium jobs"   value={fmtNum(r.premium_jobs)} accent="text-fuchsia-400"
                testId="kpi-jobs-premium" />
          <Stat label="60s purchases"  value={fmtNum(r.purchases_60s)} testId="kpi-purchases-60s" />
          <Stat label="90s premium usage" value={fmtNum(r.purchases_90s)} testId="kpi-purchases-90s" />
          <Stat label="Upgrade modal shown"  value={fmtNum(r.upgrade_modal_shown)} testId="kpi-upgrade-shown" />
          <Stat label="Upgrade clicked"      value={fmtNum(r.upgrade_clicked)} testId="kpi-upgrade-clicked" />
          <Stat label="Upgrade CTR"          value={fmtPct(r.upgrade_ctr_pct)}
                accent="text-amber-300" testId="kpi-upgrade-ctr" />
          <Stat label="Credits charged (revenue proxy)" value={fmtNum(r.credits_charged_total)}
                sub="Funnel-attributable economic units" testId="kpi-credits-total" />
        </Section>

        {/* ═══════════════ OPS ═══════════════ */}
        <Section title="5 · Ops" testId="kpi-section-ops">
          <Stat label="Queue depth (active+queued)" value={fmtNum(o.queue_depth_active)}
                testId="kpi-queue-depth" />
          <Stat label="Avg wait · Premium"  value={fmtSec(o.avg_wait_premium_seconds)}
                sub={`${o.wait_samples?.priority || 0} samples`}
                accent="text-fuchsia-400" testId="kpi-wait-premium" />
          <Stat label="Avg wait · Standard" value={fmtSec(o.avg_wait_standard_seconds)}
                sub={`${o.wait_samples?.standard || 0} samples`} testId="kpi-wait-standard" />
          <Stat label="Fail rate"           value={fmtPct(o.fail_rate_pct)}
                sub={`${o.total_jobs || 0} jobs`}
                accent={(o.fail_rate_pct || 0) > 10 ? 'text-rose-400' : 'text-white'}
                testId="kpi-fail-rate" />
          <Stat label="Avg render · 20s" value={fmtSec(o.avg_render_seconds_by_duration?.['20'])}
                sub={`${o.render_samples_by_duration?.['20'] || 0} samples`} testId="kpi-render-20" />
          <Stat label="Avg render · 60s" value={fmtSec(o.avg_render_seconds_by_duration?.['60'])}
                sub={`${o.render_samples_by_duration?.['60'] || 0} samples`} testId="kpi-render-60" />
          <Stat label="Avg render · 90s" value={fmtSec(o.avg_render_seconds_by_duration?.['90'])}
                sub={`${o.render_samples_by_duration?.['90'] || 0} samples`} testId="kpi-render-90" />
        </Section>

        {/* ═══════════════ VIRALITY ═══════════════ */}
        <Section title="6 · Virality" testId="kpi-section-virality">
          <Stat label="View → Share" value={fmtPct(v.view_to_share_pct)}
                sub={`${fmtNum(v.shares_total)} shares`}
                accent="text-emerald-400" testId="kpi-view-to-share" />
          <Stat label="Shares per completed trailer" value={fmtNum(v.shares_per_completed_trailer)}
                testId="kpi-shares-per-trailer" />
          <Stat label="WhatsApp shares" value={fmtNum(v.whatsapp_shares)} testId="kpi-shares-whatsapp" />
          <Stat label="Native shares"   value={fmtNum(v.native_shares)} testId="kpi-shares-native" />
        </Section>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 mb-10"
             data-testid="kpi-top-templates-share">
          <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-3">Top templates · share rate</div>
          {(v.top_templates_by_share_rate || []).length === 0 ? (
            <div className="text-xs text-slate-500">No data yet in this range.</div>
          ) : (
            <div className="space-y-1.5">
              {v.top_templates_by_share_rate.slice(0, 6).map((t) => (
                <div key={t.template_id} className="flex justify-between text-sm">
                  <span className="text-slate-300 truncate pr-2">{t.title}</span>
                  <span className="text-white font-semibold tabular-nums">
                    {fmtPct(t.share_rate_pct)}{' '}
                    <span className="text-slate-500 text-xs">({t.shares}/{t.views})</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="text-xs text-slate-600 mt-12 pb-12">
          KPI source · funnel_events + photo_trailer_jobs · range = {data?.range}
        </footer>
      </div>
    </div>
  );
}
