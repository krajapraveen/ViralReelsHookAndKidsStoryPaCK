import React, { useEffect, useState, useCallback } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  RefreshCw, Users, Gift, TrendingUp, Shield, Trophy,
  CheckCircle, XCircle, Undo2,
} from 'lucide-react';

export default function AdminReferrals() {
  const [overview, setOverview] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [actioning, setActioning] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, list] = await Promise.all([
        api.get('/api/referrals/admin/overview'),
        api.get(`/api/referrals/admin/attributions${filter ? `?status=${filter}` : ''}`),
      ]);
      setOverview(ov.data);
      setRows(list.data.rows || []);
    } catch (e) {
      toast.error('Failed to load referrals');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const act = async (id, action, reason = '') => {
    if (action === 'REVERSE' && !window.confirm('Reverse this reward? Credits will be deducted from the referrer.')) return;
    if (action === 'REJECT' && !window.confirm('Reject this referral?')) return;
    setActioning(id);
    try {
      await api.post('/api/referrals/admin/review', { attribution_id: id, action, reason });
      toast.success(`${action} applied`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Action failed');
    } finally {
      setActioning(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6" data-testid="admin-referrals">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Gift className="w-6 h-6 text-violet-400" />
              Referral Program
            </h1>
            <p className="text-sm text-slate-500 mt-1">Invite & Earn — attribution, fraud review, credit grants</p>
          </div>
          <button onClick={load} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Stat icon={Users} label="Profiles" value={overview?.total_profiles ?? 0} color="slate" testId="stat-profiles" />
          <Stat icon={TrendingUp} label="Clicks" value={overview?.total_clicks ?? 0} color="slate" testId="stat-clicks" />
          <Stat icon={CheckCircle} label="Qualified" value={overview?.qualified ?? 0} color="emerald" testId="stat-qualified" />
          <Stat icon={Gift} label="Credits Granted" value={overview?.credits_granted ?? 0} color="violet" testId="stat-credits" />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <Stat icon={Shield} label="Pending" value={overview?.pending ?? 0} color="amber" testId="stat-pending" />
          <Stat icon={XCircle} label="Rejected" value={overview?.rejected ?? 0} color="rose" testId="stat-rejected" />
          <Stat icon={Gift} label="Rewards" value={overview?.rewards_granted_count ?? 0} color="slate" testId="stat-rewards-count" />
          <Stat icon={TrendingUp} label="Conv Rate" value={`${overview?.conversion_rate ?? 0}%`} color="slate" testId="stat-conv-rate" />
        </div>

        {/* Monetization hardening stats */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 mb-6" data-testid="monetization-card">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4">Monetization Health</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <MonetStat label="Credits Issued This Month" value={overview?.credits_issued_this_month ?? 0} testId="stat-credits-mtd" />
            <MonetStat label="Purchase Bonuses" value={overview?.purchase_bonuses_granted ?? 0} testId="stat-purchase-bonuses" />
            <MonetStat label="Referred Paid Users" value={overview?.referred_paid_users ?? 0} testId="stat-referred-paid" />
            <MonetStat label="Expired Credits Total" value={overview?.expired_credits_sum ?? 0} testId="stat-expired-sum" />
          </div>
          {overview?.cap_hits_by_tier && Object.keys(overview.cap_hits_by_tier).length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Cap Hits This Month (by tier)</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(overview.cap_hits_by_tier).map(([tier, hits]) => (
                  <span key={tier} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-300">
                    {tier}: {hits} hits
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-3 flex-wrap">
            <button
              onClick={async () => {
                try {
                  const { data } = await api.post('/api/referrals/admin/run-expiry-sweep');
                  toast.success(`${data.expired_count} rewards expired`);
                  load();
                } catch (_) { toast.error('Sweep failed'); }
              }}
              className="inline-flex items-center gap-1 text-[11px] px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700"
              data-testid="run-sweep-btn"
            >
              <RefreshCw className="w-3 h-3" /> Run expiry sweep
            </button>
            {overview?.reward_tiers && (
              <div className="text-[10px] text-slate-500">
                FREE: {overview.reward_tiers.FREE.credits}c/ref · {overview.reward_tiers.FREE.cap} cap
                &nbsp;·&nbsp; PAID: {overview.reward_tiers.PAID.credits}c · {overview.reward_tiers.PAID.cap} cap
                &nbsp;·&nbsp; PREMIUM: {overview.reward_tiers.PREMIUM.credits}c · {overview.reward_tiers.PREMIUM.cap} cap
              </div>
            )}
          </div>
        </div>

        {/* Top referrers */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 mb-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
            <Trophy className="w-3.5 h-3.5 text-amber-400" /> Top Referrers
          </h3>
          {(overview?.top_referrers || []).length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-4">No referrers yet</p>
          ) : (
            <div className="space-y-2">
              {(overview?.top_referrers || []).map((r, i) => (
                <div key={r.user_id} className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3 py-2" data-testid={`top-referrer-${i}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 font-mono w-5">#{i + 1}</span>
                    <span className="text-sm text-white">{r.email}</span>
                    <code className="text-[10px] text-violet-300 bg-violet-500/10 px-1.5 py-0.5 rounded border border-violet-500/20">{r.referral_code}</code>
                  </div>
                  <div className="text-xs text-slate-400">
                    <span className="text-emerald-400 font-semibold">{r.valid_referrals}</span> valid · +{r.total_credits_earned} credits
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Attributions */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Recent Attributions</h3>
            <div className="flex gap-1 bg-slate-800 rounded-lg p-0.5">
              {['', 'SIGNED_UP', 'QUALIFIED', 'REWARDED', 'REJECTED'].map(s => (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={`px-3 py-1 rounded-md text-[10px] font-medium transition-colors ${filter === s ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'}`}
                  data-testid={`filter-${s || 'all'}`}
                >
                  {s || 'All'}
                </button>
              ))}
            </div>
          </div>
          {rows.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-8">No attributions</p>
          ) : (
            <div className="space-y-2" data-testid="admin-attribution-list">
              {rows.map(r => (
                <div key={r.id} className="flex items-start justify-between gap-3 bg-slate-800/40 rounded-lg px-3 py-2.5" data-testid={`admin-attribution-${r.id}`}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-slate-400">Referrer:</span>
                      <span className="text-sm text-white">{r.referrer_email}</span>
                      <code className="text-[10px] text-violet-300">{r.referrer_code}</code>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap mt-0.5">
                      <span className="text-xs text-slate-400">Referred:</span>
                      <span className="text-sm text-white">{r.referred_email_display || r.referred_email}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap mt-1 text-[10px] text-slate-500">
                      <span>{new Date(r.created_at).toLocaleString()}</span>
                      {r.reason && <span>· reason: {r.reason}</span>}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <StatusPill status={r.status} />
                    <div className="flex gap-1 mt-1">
                      {['SIGNED_UP', 'VERIFIED', 'ACTIVATED', 'QUALIFIED'].includes(r.status) && (
                        <button
                          onClick={() => act(r.id, 'APPROVE', 'Admin approved')}
                          disabled={actioning === r.id}
                          className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-40"
                          data-testid={`approve-${r.id}`}
                        >
                          <CheckCircle className="w-3 h-3" /> Approve
                        </button>
                      )}
                      {r.status !== 'REJECTED' && r.status !== 'REWARDED' && (
                        <button
                          onClick={() => act(r.id, 'REJECT', 'Admin rejected')}
                          disabled={actioning === r.id}
                          className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-slate-700/40 border border-slate-700 text-slate-400 hover:bg-slate-700"
                          data-testid={`reject-${r.id}`}
                        >
                          <XCircle className="w-3 h-3" /> Reject
                        </button>
                      )}
                      {r.status === 'REWARDED' && (
                        <button
                          onClick={() => act(r.id, 'REVERSE', 'Admin reversed')}
                          disabled={actioning === r.id}
                          className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-rose-500/20 border border-rose-500/40 text-rose-300 hover:bg-rose-500/30"
                          data-testid={`reverse-${r.id}`}
                        >
                          <Undo2 className="w-3 h-3" /> Reverse
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, color, testId }) {
  const colors = {
    slate: 'bg-slate-800/40 border-slate-800 text-slate-300',
    emerald: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
    violet: 'bg-violet-500/10 border-violet-500/30 text-violet-300',
    rose: 'bg-rose-500/10 border-rose-500/30 text-rose-300',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-300',
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color] || colors.slate}`} data-testid={testId}>
      <Icon className="w-4 h-4 mb-2" />
      <p className="text-[10px] uppercase tracking-wider opacity-80 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function StatusPill({ status }) {
  const map = {
    SIGNED_UP: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    QUALIFIED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    REWARDED: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40',
    REJECTED: 'bg-slate-700/40 text-slate-500 border-slate-700',
  };
  const cls = map[status] || 'bg-slate-800 text-slate-400 border-slate-700';
  return <span className={`inline-block text-[10px] px-2 py-0.5 rounded border ${cls}`}>{status}</span>;
}

function MonetStat({ label, value, testId }) {
  return (
    <div className="rounded-lg bg-slate-800/40 border border-slate-800 p-3" data-testid={testId}>
      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-xl font-bold text-white">{typeof value === 'number' ? value.toLocaleString() : value}</p>
    </div>
  );
}
