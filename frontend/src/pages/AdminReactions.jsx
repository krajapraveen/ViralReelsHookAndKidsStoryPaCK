import React, { useEffect, useState, useCallback } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import { RefreshCw, TrendingUp, Play, Share2, Repeat, Eye, Flame, Trophy } from 'lucide-react';

/**
 * Founder Reaction Dashboard — "which stories people love"
 * Route: /admin/reactions
 *
 * Answers four founder questions per the April 23 brief:
 *   1. Which videos get finished watching?
 *   2. Which videos get shared?
 *   3. Which videos hold attention past 50%?
 *   4. Which trigger a remix/regenerate?
 */
export default function AdminReactions() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [category, setCategory] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ days: String(days) });
      if (category) qs.set('category', category);
      const res = await api.get(`/api/funnel/reaction-dashboard?${qs.toString()}`);
      setData(res.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load reaction data');
    } finally {
      setLoading(false);
    }
  }, [days, category]);

  useEffect(() => { load(); }, [load]);

  const categories = data?.category_rollups?.map(c => c.category) || [];

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6" data-testid="admin-reactions">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Flame className="w-6 h-6 text-rose-400" />
              Reaction Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Which videos people actually love — completion, shares, holds, remixes
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              data-testid="reactions-days-select"
            >
              <option value={1}>Last 1 day</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              data-testid="reactions-category-select"
            >
              <option value="">All categories</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <button
              onClick={load}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm"
              data-testid="reactions-refresh-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {loading && !data && (
          <div className="text-center py-20 text-slate-500" data-testid="reactions-loading">Loading reaction data...</div>
        )}

        {data && data.video_count === 0 && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-10 text-center" data-testid="reactions-empty">
            <Eye className="w-10 h-10 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-300 font-medium">No reaction data yet.</p>
            <p className="text-sm text-slate-500 mt-2">
              Share your videos — once viewers hit play, their progress + share + remix events will land here.
            </p>
          </div>
        )}

        {data && data.video_count > 0 && (
          <>
            {/* ═══ NORTH STAR HERO ═══ */}
            <section
              className="mb-6 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/60 via-slate-950 to-slate-950 p-6"
              data-testid="reactions-north-star"
            >
              <div className="flex items-center justify-between gap-6 flex-wrap">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-emerald-400/90 font-bold mb-1">
                    North-Star Metric · View → Share Rate
                  </p>
                  <p className="text-xs text-slate-400 max-w-md">
                    The single best signal for public distribution health. Target: ≥10% = goldmine; &lt;2% = reconsider distribution channel or creative.
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-5xl font-black text-emerald-300 tabular-nums leading-none" data-testid="reactions-north-star-rate">
                    {data.north_star?.view_to_share_rate ?? 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {data.north_star?.total_share_clicks ?? 0} shares ÷ {data.north_star?.total_unique_viewers ?? 0} viewers
                  </p>
                </div>
              </div>
            </section>

            {/* Category rollups */}
            <section className="mb-8" data-testid="reactions-categories">
              <h2 className="text-lg font-semibold mb-3 text-slate-200">Categories by View→Share rate</h2>
              <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50">
                <table className="w-full text-sm">
                  <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="px-4 py-3 text-left">Category</th>
                      <th className="px-4 py-3 text-right">Videos</th>
                      <th className="px-4 py-3 text-right">Viewers</th>
                      <th className="px-4 py-3 text-right">Plays</th>
                      <th className="px-4 py-3 text-right text-emerald-300">View→Share %</th>
                      <th className="px-4 py-3 text-right">Completion %</th>
                      <th className="px-4 py-3 text-right">Hold 50% %</th>
                      <th className="px-4 py-3 text-right">Regen / play %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {data.category_rollups.map((c) => (
                      <tr key={c.category} data-testid={`reactions-category-row-${c.category}`}>
                        <td className="px-4 py-3 font-medium text-violet-300">{c.category}</td>
                        <td className="px-4 py-3 text-right">{c.videos}</td>
                        <td className="px-4 py-3 text-right">{c.unique_viewers}</td>
                        <td className="px-4 py-3 text-right">{c.plays}</td>
                        <td className="px-4 py-3 text-right font-bold">
                          <span className={c.view_to_share_rate >= 10 ? 'text-emerald-300' : c.view_to_share_rate >= 2 ? 'text-amber-300' : 'text-slate-500'}>
                            {c.view_to_share_rate}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">{c.completion_pct}%</td>
                        <td className="px-4 py-3 text-right">{c.hold_rate_50}%</td>
                        <td className="px-4 py-3 text-right text-amber-300">{c.regen_per_play}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Leaderboards */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              <Leaderboard
                title="⭐ Best view→share rate (NORTH STAR)"
                icon={<Flame className="w-4 h-4 text-emerald-400" />}
                rows={data.leaderboards.top_view_to_share}
                metric="view_to_share_rate"
                metricFormat={(v) => `${v}%`}
                testId="leaderboard-view-to-share"
              />
              <Leaderboard
                title="Top finished (completion %)"
                icon={<Trophy className="w-4 h-4 text-amber-400" />}
                rows={data.leaderboards.top_finished}
                metric="completion_pct"
                metricFormat={(v) => `${v}%`}
                testId="leaderboard-finished"
              />
              <Leaderboard
                title="Top shared (absolute)"
                icon={<Share2 className="w-4 h-4 text-emerald-400" />}
                rows={data.leaderboards.top_shared}
                metric="share_clicks"
                metricFormat={(v) => `${v}`}
                testId="leaderboard-shared"
              />
              <Leaderboard
                title="Best hold rate past 50%"
                icon={<TrendingUp className="w-4 h-4 text-violet-400" />}
                rows={data.leaderboards.top_hold_rate}
                metric="hold_rate_50"
                metricFormat={(v) => `${v}%`}
                testId="leaderboard-hold"
              />
              <Leaderboard
                title="Most regenerated"
                icon={<Repeat className="w-4 h-4 text-rose-400" />}
                rows={data.leaderboards.top_regen}
                metric="regen_clicks"
                metricFormat={(v) => `${v}`}
                testId="leaderboard-regen"
              />
            </section>

            {/* Full video table */}
            <section data-testid="reactions-all-videos">
              <h2 className="text-lg font-semibold mb-3 text-slate-200">All videos ({data.video_count})</h2>
              <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/50">
                <table className="w-full text-sm">
                  <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="px-4 py-3 text-left">Title</th>
                      <th className="px-4 py-3 text-left">Category</th>
                      <th className="px-4 py-3 text-right">Viewers</th>
                      <th className="px-4 py-3 text-right">Plays</th>
                      <th className="px-4 py-3 text-right text-emerald-300">V→S %</th>
                      <th className="px-4 py-3 text-right">25%</th>
                      <th className="px-4 py-3 text-right">50%</th>
                      <th className="px-4 py-3 text-right">75%</th>
                      <th className="px-4 py-3 text-right">100%</th>
                      <th className="px-4 py-3 text-right">Comp %</th>
                      <th className="px-4 py-3 text-right">Shares</th>
                      <th className="px-4 py-3 text-right">Regens</th>
                      <th className="px-4 py-3 text-left">Link</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {data.videos.map((v) => (
                      <tr key={v.story_id} data-testid={`reactions-row-${v.story_id.slice(0, 8)}`}>
                        <td className="px-4 py-3 font-medium text-white/90 max-w-[280px] truncate">{v.title}</td>
                        <td className="px-4 py-3 text-violet-300 text-xs">{v.category}</td>
                        <td className="px-4 py-3 text-right">{v.unique_viewers}</td>
                        <td className="px-4 py-3 text-right">{v.plays}</td>
                        <td className="px-4 py-3 text-right font-bold">
                          <span className={v.view_to_share_rate >= 10 ? 'text-emerald-300' : v.view_to_share_rate >= 2 ? 'text-amber-300' : 'text-slate-500'}>
                            {v.view_to_share_rate}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">{v.progress_25}</td>
                        <td className="px-4 py-3 text-right">{v.progress_50}</td>
                        <td className="px-4 py-3 text-right">{v.progress_75}</td>
                        <td className="px-4 py-3 text-right">{v.completions_100}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={v.completion_pct >= 60 ? 'text-emerald-300' : v.completion_pct >= 30 ? 'text-amber-300' : 'text-slate-400'}>
                            {v.completion_pct}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-emerald-300">{v.share_clicks}</td>
                        <td className="px-4 py-3 text-right text-amber-300">{v.regen_clicks}</td>
                        <td className="px-4 py-3">
                          {v.output_url ? (
                            <a
                              href={v.output_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-violet-400 hover:text-violet-300 text-xs"
                              data-testid={`reactions-video-link-${v.story_id.slice(0, 8)}`}
                            >
                              Open ↗
                            </a>
                          ) : (
                            <span className="text-slate-600 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <p className="text-xs text-slate-600 mt-6" data-testid="reactions-meta">
              Window: {data.period_days} days · {data.video_count} videos · filter: {data.filter_category || 'all'}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function Leaderboard({ title, icon, rows, metric, metricFormat, testId }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden" data-testid={testId}>
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2 text-slate-300 font-medium text-sm">
        {icon}
        {title}
      </div>
      <div className="divide-y divide-slate-800">
        {rows.length === 0 && (
          <div className="px-4 py-6 text-sm text-slate-500 text-center">No data yet</div>
        )}
        {rows.map((v, i) => (
          <div key={v.story_id} className="px-4 py-3 flex items-center gap-3">
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
              ${i === 0 ? 'bg-amber-500/20 text-amber-300' : i === 1 ? 'bg-slate-500/20 text-slate-300' : 'bg-slate-800 text-slate-400'}`}>
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white/90 truncate">{v.title}</p>
              <p className="text-xs text-slate-500">{v.category} · {v.plays} plays</p>
            </div>
            <span className="text-sm font-bold text-white tabular-nums" data-testid={`${testId}-metric-${i}`}>
              {metricFormat(v[metric])}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
