import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3, TrendingUp, Users, Eye, RefreshCcw, Zap, AlertTriangle,
  ArrowDown, ArrowRight, CheckCircle, Target, Activity, Flame, FlaskConical
} from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── ALERT THRESHOLDS ──────────────────────────────────────────────
const THRESHOLDS = {
  remix_click_rate: { warn: 5, good: 15, label: 'Remix Click Rate' },
  prefill_rate: { warn: 50, good: 80, label: 'Prefill Rate' },
  generation_rate: { warn: 30, good: 60, label: 'Generation Rate' },
  signup_completion_rate: { warn: 10, good: 30, label: 'Signup Rate' },
  creation_rate: { warn: 40, good: 70, label: 'Creation Rate' },
};

function getStatus(value, threshold) {
  if (value >= threshold.good) return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Healthy' };
  if (value >= threshold.warn) return { color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Needs Work' };
  return { color: 'text-red-400', bg: 'bg-red-500/10', label: 'Critical' };
}

// ─── FUNNEL STAGE VISUALIZATION ─────────────────────────────────────
function FunnelStage({ stage, count, prevCount, isFirst, isWorst }) {
  const convRate = isFirst ? 100 : prevCount > 0 ? ((count / prevCount) * 100) : 0;
  const labels = {
    page_view: 'Page Views', remix_click: 'Remix Clicks', tool_open_prefilled: 'Tool Opens',
    generate_click: 'Generate Clicks', signup_completed: 'Signups', creation_completed: 'Creations',
  };
  const widthPct = count > 0 && prevCount > 0 ? Math.max(20, (count / prevCount) * 100) : (isFirst ? 100 : 20);

  return (
    <div className={`relative ${isWorst ? 'ring-1 ring-red-500/40 rounded-lg' : ''}`} data-testid={`funnel-${stage}`}>
      {!isFirst && (
        <div className="flex items-center gap-2 py-1 px-2">
          <ArrowDown className={`w-3 h-3 ${convRate < 30 ? 'text-red-400' : convRate < 60 ? 'text-amber-400' : 'text-emerald-400'}`} />
          <span className={`text-xs font-mono font-bold ${convRate < 30 ? 'text-red-400' : convRate < 60 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {convRate.toFixed(1)}%
          </span>
          {isWorst && <span className="text-[9px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded-full font-medium">BIGGEST DROP</span>}
        </div>
      )}
      <div className="bg-slate-900/50 border border-white/[0.06] rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400">{labels[stage] || stage}</span>
          <span className="text-sm font-bold font-mono text-white">{count.toLocaleString()}</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isFirst ? 'bg-indigo-500' : convRate < 30 ? 'bg-red-500' : convRate < 60 ? 'bg-amber-500' : 'bg-emerald-500'}`}
            style={{ width: `${isFirst ? 100 : Math.min(100, widthPct)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── VIRAL K DISPLAY ────────────────────────────────────────────────
function ViralKBadge({ k, interpretation }) {
  const config = k >= 1
    ? { bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', icon: Flame, label: 'VIRAL' }
    : k >= 0.5
    ? { bg: 'bg-amber-500/15 border-amber-500/30', text: 'text-amber-400', icon: TrendingUp, label: 'CLOSE' }
    : k > 0
    ? { bg: 'bg-red-500/15 border-red-500/30', text: 'text-red-400', icon: AlertTriangle, label: 'WEAK' }
    : { bg: 'bg-slate-800 border-slate-700', text: 'text-slate-400', icon: Activity, label: 'NO DATA' };

  return (
    <div className={`rounded-xl border ${config.bg} p-5`} data-testid="viral-k-badge">
      <div className="flex items-center gap-3 mb-3">
        <config.icon className={`w-6 h-6 ${config.text}`} />
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-wider">Viral Coefficient</p>
          <p className={`text-3xl font-bold font-mono ${config.text}`}>{k.toFixed(3)}</p>
        </div>
        <span className={`ml-auto text-[10px] font-bold px-2 py-0.5 rounded-full ${config.bg} ${config.text} border`}>
          {config.label}
        </span>
      </div>
      <p className="text-xs text-slate-400">
        {k >= 1 ? 'Each user brings in >1 new users. Exponential growth!' :
         k >= 0.5 ? 'Getting close. Optimize drop-off stages to push K > 1.' :
         k > 0 ? 'Users are not converting enough. Focus on the biggest funnel drop.' :
         'Not enough data yet. Share creations to start tracking.'}
      </p>
    </div>
  );
}

// ─── GROWTH ALERTS ──────────────────────────────────────────────────
function GrowthAlerts({ rates }) {
  const alerts = [];
  for (const [key, threshold] of Object.entries(THRESHOLDS)) {
    const val = rates?.[key] || 0;
    if (val < threshold.warn) {
      alerts.push({
        metric: threshold.label,
        value: val,
        threshold: threshold.warn,
        diagnosis: getDiagnosis(key),
      });
    }
  }

  if (alerts.length === 0) {
    return (
      <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3" data-testid="growth-alerts-ok">
        <CheckCircle className="w-5 h-5 text-emerald-400" />
        <p className="text-sm text-emerald-300">All funnel metrics are healthy. Keep monitoring.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="growth-alerts">
      {alerts.map((a, i) => (
        <div key={i} className="bg-red-500/5 border border-red-500/20 rounded-xl p-4" data-testid={`alert-${i}`}>
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-sm font-medium text-red-300">{a.metric}: {a.value.toFixed(1)}%</span>
            <span className="text-[9px] text-red-400/60 ml-auto">Threshold: {a.threshold}%</span>
          </div>
          <p className="text-xs text-slate-400 ml-6">{a.diagnosis}</p>
        </div>
      ))}
    </div>
  );
}

function getDiagnosis(key) {
  const map = {
    remix_click_rate: 'Users see the page but don\'t click Remix. Check: CTA visibility, copy strength, output quality on public page.',
    prefill_rate: 'Users click Remix but tool doesn\'t open prefilled. Check: localStorage flow, remix_data TTL, navigation routing.',
    generation_rate: 'Users reach the tool but don\'t generate. Check: form complexity, credit barriers, confusing UI.',
    signup_completion_rate: 'Users try to sign up but abandon. Check: signup friction, required fields, social login option.',
    creation_rate: 'Users sign up but don\'t complete their first creation. Check: onboarding flow, credit availability, tool clarity.',
  };
  return map[key] || 'Investigate user behavior at this stage.';
}

// ─── MAIN DASHBOARD ──────────────────────────────────────────────────
export default function GrowthDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [viral, setViral] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [trends, setTrends] = useState(null);
  const [experiments, setExperiments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [mRes, vRes, fRes, tRes, eRes] = await Promise.all([
        axios.get(`${API}/api/growth/metrics?days=${days}`, { headers: h }),
        axios.get(`${API}/api/growth/viral-coefficient?days=${days}`, { headers: h }),
        axios.get(`${API}/api/growth/funnel?days=${days}`, { headers: h }),
        axios.get(`${API}/api/growth/trends?days=${days}`, { headers: h }),
        axios.get(`${API}/api/ab/results`, { headers: h }),
      ]);
      setMetrics(mRes.data);
      setViral(vRes.data);
      setFunnel(fRes.data);
      setTrends(tRes.data);
      setExperiments(eRes.data?.experiments || []);
    } catch (e) {
      console.error('Growth data fetch error:', e);
    }
    setLoading(false);
  }, [days]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Find worst drop-off
  const findWorstDropoff = () => {
    if (!funnel?.funnel) return null;
    let worst = null;
    let worstRate = Infinity;
    for (let i = 1; i < funnel.funnel.length; i++) {
      const prev = funnel.funnel[i - 1].count;
      const curr = funnel.funnel[i].count;
      if (prev > 0) {
        const rate = curr / prev;
        if (rate < worstRate && prev > 0) {
          worstRate = rate;
          worst = funnel.funnel[i].stage;
        }
      }
    }
    return worst;
  };
  const worstStage = findWorstDropoff();

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-xl font-bold text-white flex items-center gap-2"><BarChart3 className="w-5 h-5 text-indigo-400" /> Growth Intelligence</h1>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <div key={i} className="bg-slate-900/50 border border-white/[0.06] rounded-xl p-5 animate-pulse h-28" />)}</div>
      </div>
    );
  }

  const rc = metrics?.raw_counts || {};
  const rates = metrics?.conversion_rates || {};

  return (
    <div className="p-6 space-y-6" data-testid="growth-intelligence-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Growth Intelligence
          </h1>
          <p className="text-xs text-slate-500 mt-1">Where are users dropping? What to fix next.</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={`px-3 py-1 text-xs rounded-lg transition-colors ${days === d ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-slate-500 hover:text-white border border-white/[0.06]'}`}
              data-testid={`period-${d}d`}
            >{d}d</button>
          ))}
          <button onClick={fetchAll} className="px-3 py-1 text-xs text-slate-400 hover:text-white border border-white/[0.06] rounded-lg" data-testid="refresh-btn">
            <RefreshCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Top Row: K + Core Numbers */}
      <div className="grid lg:grid-cols-3 gap-4">
        <ViralKBadge k={viral?.viral_coefficient_K || 0} interpretation={viral?.interpretation || 'no data'} />

        <div className="grid grid-cols-2 gap-3 lg:col-span-2">
          <div className="bg-slate-900/50 border border-white/[0.06] rounded-xl p-4" data-testid="stat-views">
            <Eye className="w-4 h-4 text-blue-400 mb-2" />
            <p className="text-xl font-bold font-mono text-white">{(rc.page_views || 0).toLocaleString()}</p>
            <p className="text-[10px] text-slate-500">Page Views</p>
          </div>
          <div className="bg-slate-900/50 border border-white/[0.06] rounded-xl p-4" data-testid="stat-remixes">
            <RefreshCcw className="w-4 h-4 text-pink-400 mb-2" />
            <p className="text-xl font-bold font-mono text-white">{(rc.remix_clicks || 0).toLocaleString()}</p>
            <p className="text-[10px] text-slate-500">Remix Clicks</p>
          </div>
          <div className="bg-slate-900/50 border border-white/[0.06] rounded-xl p-4" data-testid="stat-signups">
            <Users className="w-4 h-4 text-emerald-400 mb-2" />
            <p className="text-xl font-bold font-mono text-white">{(rc.signups_completed || 0).toLocaleString()}</p>
            <p className="text-[10px] text-slate-500">Signups</p>
          </div>
          <div className="bg-slate-900/50 border border-white/[0.06] rounded-xl p-4" data-testid="stat-creations">
            <Zap className="w-4 h-4 text-amber-400 mb-2" />
            <p className="text-xl font-bold font-mono text-white">{(rc.creations_completed || 0).toLocaleString()}</p>
            <p className="text-[10px] text-slate-500">Creations</p>
          </div>
        </div>
      </div>

      {/* Growth Alerts */}
      <div>
        <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" /> Growth Alerts
        </h2>
        <GrowthAlerts rates={rates} />
      </div>

      {/* Funnel Visualization */}
      <div className="bg-slate-900/30 border border-white/[0.06] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-indigo-400" /> Conversion Funnel
        </h2>
        <div className="space-y-1">
          {(funnel?.funnel || []).map((s, i, arr) => (
            <FunnelStage
              key={s.stage}
              stage={s.stage}
              count={s.count}
              prevCount={i > 0 ? arr[i - 1].count : s.count}
              isFirst={i === 0}
              isWorst={s.stage === worstStage}
            />
          ))}
        </div>
      </div>

      {/* Top Performing Slugs */}
      {viral?.top_performing_slugs?.length > 0 && (
        <div className="bg-slate-900/30 border border-white/[0.06] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <Flame className="w-4 h-4 text-orange-400" /> Top Performing Content
          </h2>
          <div className="space-y-2">
            {viral.top_performing_slugs.map((s, i) => (
              <Link key={i} to={`/v/${s.slug}`} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white/[0.04] transition-colors">
                <span className="text-xs text-slate-300 font-mono truncate max-w-[200px]">{s.slug}</span>
                <div className="flex items-center gap-4 text-[10px]">
                  <span className="text-slate-500"><Eye className="w-3 h-3 inline mr-0.5" />{s.views}</span>
                  <span className="text-pink-400"><RefreshCcw className="w-3 h-3 inline mr-0.5" />{s.remix_clicks}</span>
                  <span className={`font-bold ${s.remix_rate >= 15 ? 'text-emerald-400' : s.remix_rate >= 5 ? 'text-amber-400' : 'text-red-400'}`}>
                    {s.remix_rate}%
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Daily Trends */}
      {trends?.daily && Object.keys(trends.daily).length > 0 && (
        <div className="bg-slate-900/30 border border-white/[0.06] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" /> Daily Trends
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left py-2 text-slate-500 font-normal">Date</th>
                  <th className="text-right py-2 text-slate-500 font-normal">Views</th>
                  <th className="text-right py-2 text-slate-500 font-normal">Remixes</th>
                  <th className="text-right py-2 text-slate-500 font-normal">Generates</th>
                  <th className="text-right py-2 text-slate-500 font-normal">Signups</th>
                  <th className="text-right py-2 text-slate-500 font-normal">Shares</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(trends.daily).sort(([a], [b]) => b.localeCompare(a)).slice(0, 14).map(([date, events]) => (
                  <tr key={date} className="border-b border-white/[0.03]">
                    <td className="py-2 text-slate-400 font-mono">{date}</td>
                    <td className="py-2 text-right text-white font-mono">{events.page_view || 0}</td>
                    <td className="py-2 text-right text-pink-400 font-mono">{events.remix_click || 0}</td>
                    <td className="py-2 text-right text-blue-400 font-mono">{events.generate_click || 0}</td>
                    <td className="py-2 text-right text-emerald-400 font-mono">{events.signup_completed || 0}</td>
                    <td className="py-2 text-right text-amber-400 font-mono">{events.share_click || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Overall Conversion */}
      <div className="bg-slate-900/30 border border-white/[0.06] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Conversion Rates</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {Object.entries(rates).filter(([k]) => k !== 'overall_conversion').map(([key, val]) => {
            const t = THRESHOLDS[key];
            const s = t ? getStatus(val, t) : { color: 'text-slate-300', bg: 'bg-slate-800', label: '-' };
            return (
              <div key={key} className={`rounded-lg p-3 ${s.bg} border border-white/[0.04]`} data-testid={`rate-${key}`}>
                <p className={`text-lg font-bold font-mono ${s.color}`}>{val.toFixed(1)}%</p>
                <p className="text-[9px] text-slate-500 mt-0.5">{key.replace(/_/g, ' ')}</p>
              </div>
            );
          })}
        </div>
        <div className="mt-3 pt-3 border-t border-white/[0.04] text-center">
          <p className="text-[10px] text-slate-500">Overall Conversion (View → Creation)</p>
          <p className="text-2xl font-bold font-mono text-indigo-400">{(rates.overall_conversion || 0).toFixed(2)}%</p>
        </div>
      </div>

      {/* A/B Experiment Results */}
      {experiments && experiments.length > 0 && (
        <div className="bg-slate-900/30 border border-white/[0.06] rounded-xl p-5" data-testid="ab-experiments-section">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <FlaskConical className="w-4 h-4 text-purple-400" /> A/B Experiments
          </h2>
          <div className="space-y-4">
            {experiments.map(exp => (
              <div key={exp.experiment_id} className="bg-slate-800/50 border border-white/[0.04] rounded-lg p-4" data-testid={`exp-${exp.experiment_id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-xs font-semibold text-white">{exp.name}</p>
                    <p className="text-[10px] text-slate-500">Primary: {exp.primary_event.replace(/_/g, ' ')}</p>
                  </div>
                  {exp.tentative_winner && (
                    <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" data-testid={`winner-${exp.experiment_id}`}>
                      WINNER: {exp.variants.find(v => v.variant_id === exp.tentative_winner)?.label}
                    </span>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        <th className="text-left py-1.5 text-slate-500 font-normal">Variant</th>
                        <th className="text-right py-1.5 text-slate-500 font-normal">Sessions</th>
                        <th className="text-right py-1.5 text-slate-500 font-normal">Remixes</th>
                        <th className="text-right py-1.5 text-slate-500 font-normal">Generates</th>
                        <th className="text-right py-1.5 text-slate-500 font-normal">Signups</th>
                        <th className="text-right py-1.5 text-slate-500 font-normal">Conv %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exp.variants.map(v => {
                        const isBest = exp.variants.length > 1 &&
                          v.primary_conv_rate === Math.max(...exp.variants.map(x => x.primary_conv_rate)) &&
                          v.primary_conv_rate > 0;
                        return (
                          <tr key={v.variant_id} className={`border-b border-white/[0.03] ${isBest ? 'bg-emerald-500/[0.04]' : ''}`} data-testid={`variant-row-${v.variant_id}`}>
                            <td className="py-1.5 text-slate-300">{v.label}</td>
                            <td className="py-1.5 text-right text-white font-mono">{v.sessions}</td>
                            <td className="py-1.5 text-right text-pink-400 font-mono">{v.conversions?.remix_click || 0}</td>
                            <td className="py-1.5 text-right text-blue-400 font-mono">{v.conversions?.generate_click || 0}</td>
                            <td className="py-1.5 text-right text-emerald-400 font-mono">{v.conversions?.signup_completed || 0}</td>
                            <td className={`py-1.5 text-right font-bold font-mono ${isBest ? 'text-emerald-400' : 'text-slate-300'}`}>{v.primary_conv_rate}%</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden flex">
                    {exp.variants.map((v, i) => {
                      const total = exp.variants.reduce((s, x) => s + x.sessions, 0);
                      const pct = total > 0 ? (v.sessions / total) * 100 : 100 / exp.variants.length;
                      const colors = ['bg-indigo-500', 'bg-amber-500', 'bg-emerald-500'];
                      return <div key={i} className={`h-full ${colors[i % 3]}`} style={{ width: `${pct}%` }} />;
                    })}
                  </div>
                  <span className="text-[9px] text-slate-600">
                    {exp.variants.reduce((s, v) => s + v.sessions, 0)} total sessions
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
