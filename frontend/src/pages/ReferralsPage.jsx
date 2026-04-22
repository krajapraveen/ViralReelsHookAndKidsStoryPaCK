import React, { useEffect, useState, useCallback } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';
import {
  Gift, Copy, Check, Users, Loader2, TrendingUp,
  MessageCircle, Mail, Send, Twitter, Sparkles, ArrowRight,
} from 'lucide-react';

const SHARE_MESSAGE =
  "I've been using Visionary Suite to create AI stories and videos. Join with my invite link and try it here:";

export default function ReferralsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/referrals/me');
      setData(data);
      // Opportunistic qualification check — in case this user is a referred user
      // completing their first project, promotes/grants without waiting for cron.
      api.post('/api/referrals/qualify', {}).catch(() => {});
    } catch (e) {
      toast.error('Failed to load referrals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const share_url = data?.share_url || '';
  const p = data?.profile;

  const copy = async () => {
    if (!share_url) return;
    try {
      await navigator.clipboard.writeText(share_url);
      setCopied(true);
      toast.success('Invite link copied');
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {
      toast.error('Copy failed');
    }
  };

  const openShare = (url) => window.open(url, '_blank', 'noopener,noreferrer');
  const shareWhatsApp = () => openShare(`https://wa.me/?text=${encodeURIComponent(`${SHARE_MESSAGE} ${share_url}`)}`);
  const shareEmail = () => openShare(`mailto:?subject=${encodeURIComponent('Try Visionary Suite')}&body=${encodeURIComponent(`${SHARE_MESSAGE}\n\n${share_url}`)}`);
  const shareTelegram = () => openShare(`https://t.me/share/url?url=${encodeURIComponent(share_url)}&text=${encodeURIComponent(SHARE_MESSAGE)}`);
  const shareTwitter = () => openShare(`https://twitter.com/intent/tweet?text=${encodeURIComponent(`${SHARE_MESSAGE} ${share_url}`)}`);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white" data-testid="referrals-page">
      <div className="max-w-5xl mx-auto px-5 py-10">
        {/* Hero */}
        <div className="relative rounded-3xl border border-white/[0.06] bg-gradient-to-br from-violet-500/[0.08] to-rose-500/[0.06] p-7 md:p-10 overflow-hidden mb-6">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse 60% 50% at 100% 0%, rgba(168,85,247,0.14), transparent 60%)' }}
          />
          <div className="relative">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/20 border border-violet-500/30 text-[11px] tracking-[0.12em] text-violet-200 font-semibold mb-4">
              <Gift className="w-3 h-3" /> INVITE & EARN
            </div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">
              Invite Friends. Earn {data?.reward_credits || 300} Credits.
            </h1>
            <p className="text-slate-300/90 leading-relaxed max-w-2xl">
              When someone joins with your invite link and creates their first project, you automatically earn {data?.reward_credits || 300} free credits. No limit. No catch.
            </p>

            {/* Link + copy */}
            <div className="mt-6 flex items-center gap-2 bg-black/40 border border-white/[0.08] rounded-xl p-2 max-w-xl" data-testid="invite-link-row">
              <code className="flex-1 text-sm text-white/90 px-3 truncate font-mono" data-testid="invite-link-text">
                {share_url}
              </code>
              <button
                onClick={copy}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white text-black hover:bg-slate-100 text-sm font-semibold transition-colors"
                data-testid="copy-invite-btn"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>

            {/* Share row */}
            <div className="mt-4 flex flex-wrap gap-2">
              <ShareBtn icon={MessageCircle} label="WhatsApp" onClick={shareWhatsApp} testId="share-whatsapp" />
              <ShareBtn icon={Mail} label="Email" onClick={shareEmail} testId="share-email" />
              <ShareBtn icon={Send} label="Telegram" onClick={shareTelegram} testId="share-telegram" />
              <ShareBtn icon={Twitter} label="X" onClick={shareTwitter} testId="share-twitter" />
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard icon={Users} label="Total Invites" value={p?.total_invites ?? 0} color="slate" testId="stat-invites" />
          <StatCard icon={TrendingUp} label="Clicks" value={p?.total_clicks ?? 0} color="slate" testId="stat-clicks" />
          <StatCard icon={Sparkles} label="Successful" value={p?.valid_referrals ?? 0} color="emerald" testId="stat-valid" />
          <StatCard icon={Gift} label="Credits Earned" value={p?.total_credits_earned ?? 0} color="violet" testId="stat-earned" />
        </div>

        {/* How it works */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 mb-6">
          <h3 className="text-sm font-semibold uppercase tracking-[0.1em] text-slate-400 mb-5">How it works</h3>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { n: '1', t: 'Share your link', d: 'Send your personal invite link to friends, colleagues, or your community.' },
              { n: '2', t: 'They sign up', d: 'When they create a free Visionary Suite account using your link.' },
              { n: '3', t: 'You earn 300 credits', d: 'The moment they complete their first creation, credits land in your wallet.' },
            ].map(s => (
              <div key={s.n} className="rounded-xl border border-slate-800 bg-slate-800/30 p-4">
                <div className="w-7 h-7 rounded-full border border-violet-500/40 bg-violet-500/10 flex items-center justify-center text-xs font-bold text-violet-300 mb-3">{s.n}</div>
                <p className="text-sm font-medium text-white mb-1">{s.t}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-5 leading-relaxed">
            Every 3 successful referrals unlock a <span className="text-violet-300">bonus +500 credits</span>. Fair-use policy applies — duplicate or self-referrals are automatically blocked.
          </p>
        </div>

        {/* Attribution table */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold uppercase tracking-[0.1em] text-slate-400">Your referrals</h3>
            <span className="text-[11px] text-slate-500">Last 50</span>
          </div>
          {(data?.attributions || []).length === 0 ? (
            <div className="text-center py-10">
              <div className="w-12 h-12 rounded-full bg-violet-500/10 border border-violet-500/30 flex items-center justify-center mx-auto mb-3">
                <Users className="w-5 h-5 text-violet-400" />
              </div>
              <p className="text-sm text-slate-400 mb-1">No referrals yet</p>
              <p className="text-xs text-slate-500">Share your link above — your first friend is one message away.</p>
            </div>
          ) : (
            <div className="space-y-2" data-testid="attribution-list">
              {(data.attributions || []).map(a => (
                <div
                  key={a.id}
                  className="flex items-center justify-between bg-slate-800/40 border border-slate-800/50 rounded-lg px-3 py-2.5"
                  data-testid={`attribution-${a.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500/30 to-rose-500/30 flex items-center justify-center text-[11px] font-bold text-white">
                      {(a.friend_display || 'F')[0]}
                    </div>
                    <div>
                      <p className="text-sm text-white">{a.friend_display || 'Friend'}</p>
                      <p className="text-[10px] text-slate-500">{new Date(a.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <StatusPill status={a.status} reason={a.reason} />
                </div>
              ))}
            </div>
          )}
          {/* Education messages */}
          {(data?.attributions || []).some(a => a.status === 'SIGNED_UP') && (
            <div className="mt-5 p-4 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-amber-300" />
              </div>
              <div className="text-xs text-amber-100/80 leading-relaxed">
                <strong className="text-amber-200">Pending activation.</strong> Some of your friends have joined but haven't created their first project yet. Once they do, 300 credits will land in your wallet automatically.
              </div>
            </div>
          )}
          {(data?.attributions || []).some(a => a.status === 'REJECTED') && (
            <div className="mt-3 p-4 rounded-xl bg-slate-800/40 border border-slate-700 flex items-start gap-3">
              <div className="text-xs text-slate-400 leading-relaxed">
                A referral was not eligible under our fair-use policy (duplicate device, self-referral, or disposable email). Keep sharing with genuine friends to earn credits.
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-slate-600 mt-6 text-center leading-relaxed">
          Questions? See our <a className="text-violet-400 underline" href="/terms" target="_blank" rel="noreferrer">fair-use policy</a> or{' '}
          <a className="text-violet-400 underline" href="mailto:support@visionary-suite.com">contact support</a>.
        </p>
      </div>
    </div>
  );
}

function ShareBtn({ icon: Icon, label, onClick, testId }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 text-sm text-white transition-colors"
      data-testid={testId}
    >
      <Icon className="w-4 h-4" /> {label}
    </button>
  );
}

function StatCard({ icon: Icon, label, value, color, testId }) {
  const colors = {
    slate: 'text-slate-300 bg-slate-800/40 border-slate-800',
    violet: 'text-violet-300 bg-violet-500/10 border-violet-500/30',
    emerald: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color] || colors.slate}`} data-testid={testId}>
      <Icon className="w-4 h-4 mb-2" />
      <p className="text-[10px] uppercase tracking-wider opacity-80 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function StatusPill({ status, reason }) {
  const map = {
    CLICKED: { label: 'Clicked', cls: 'bg-slate-700/40 text-slate-400 border-slate-700' },
    SIGNED_UP: { label: 'Signed up', cls: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30' },
    VERIFIED: { label: 'Verified', cls: 'bg-blue-500/10 text-blue-300 border-blue-500/30' },
    ACTIVATED: { label: 'Activated', cls: 'bg-blue-500/10 text-blue-300 border-blue-500/30' },
    QUALIFIED: { label: 'Qualified', cls: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' },
    REWARDED: { label: '+300 awarded', cls: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40' },
    REJECTED: { label: reason === 'SELF_REFERRAL' ? 'Self-ref blocked' : 'Not eligible', cls: 'bg-slate-700/40 text-slate-500 border-slate-700' },
  };
  const p = map[status] || { label: status, cls: 'bg-slate-800 text-slate-400 border-slate-700' };
  return (
    <span className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded border ${p.cls}`}>
      {p.label}
    </span>
  );
}
