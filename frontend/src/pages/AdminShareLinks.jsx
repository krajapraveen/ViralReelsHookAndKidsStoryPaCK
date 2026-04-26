import React, { useMemo, useState } from 'react';
import { Copy, MessageCircle, Instagram, Send, Users, Sparkles, Check } from 'lucide-react';
import { toast } from 'sonner';

/**
 * P2 (lite) — WhatsApp / Distribution share-link generator.
 * Founder tool: pick channel + campaign + audience → get a clean URL with
 * UTMs that funnelTracker.js auto-captures into traffic_source +
 * utm_campaign + utm_medium on every event.
 *
 * Default landing path is /experience (skips landing page friction since
 * the founder is sending DMs to people he's already pitched in chat).
 */

const PATHS = [
  { id: 'experience', label: 'Instant Demo (recommended)', path: '/experience' },
  { id: 'landing',    label: 'Landing Page',                path: '/' },
];

const CHANNELS = [
  { id: 'whatsapp',  label: 'WhatsApp DM',         icon: MessageCircle, medium: 'dm' },
  { id: 'whatsapp_group', label: 'WhatsApp Group', icon: Users,         medium: 'group' },
  { id: 'instagram', label: 'Instagram (Reel/DM/Story)', icon: Instagram, medium: 'social' },
  { id: 'telegram',  label: 'Telegram',            icon: Send,          medium: 'dm' },
  { id: 'sms',       label: 'SMS / iMessage',      icon: MessageCircle, medium: 'dm' },
  { id: 'personal',  label: 'Personal (email/in-person)', icon: Users,  medium: 'personal' },
];

const AUDIENCES = [
  'parents', 'family', 'school', 'creators', 'colleagues', 'other',
];

const ANGLES = [
  { id: 'curious',     label: 'Curiosity',     blurb: "Built something fun for kids — wanna try?" },
  { id: 'bedtime',     label: 'Bedtime story', blurb: "Tonight's bedtime story, personalized in 30 seconds." },
  { id: 'reaction',    label: 'Reaction',      blurb: "I want to see your kid's face when they hear their own name in a magical story." },
  { id: 'gift',        label: 'Gift',          blurb: "Made a tiny gift — a personalized story video for your child." },
  { id: 'demo',        label: 'Pure demo',     blurb: "Free demo. 30 seconds. Personalized story for your kid's name." },
];

const SAMPLE_TEMPLATE = (name, link) =>
  `Hey ${name}! I built something fun for kids — it creates a personalized magical story + video using your child's name in seconds. Want to try it free? 😊\n\n${link}`;

export default function AdminShareLinks() {
  const [pathId, setPathId] = useState('experience');
  const [channelId, setChannelId] = useState('whatsapp');
  const [audience, setAudience] = useState('parents');
  const [angle, setAngle] = useState('curious');
  const [campaign, setCampaign] = useState('founder_dm_apr26');
  const [recipientName, setRecipientName] = useState('there');
  const [copied, setCopied] = useState(null);

  const channel = CHANNELS.find(c => c.id === channelId);
  const path = PATHS.find(p => p.id === pathId);
  const angleObj = ANGLES.find(a => a.id === angle);

  const link = useMemo(() => {
    const origin = window.location.origin;
    const qs = new URLSearchParams({
      utm_source: channelId,
      utm_medium: channel?.medium || 'dm',
      utm_campaign: campaign || 'founder_dm',
      utm_content: `${audience}_${angle}`,
      source: channelId, // also fills funnelTracker traffic_source via existing handler
    });
    return `${origin}${path?.path || '/'}?${qs.toString()}`;
  }, [pathId, channelId, audience, angle, campaign, channel, path]);

  const message = useMemo(() => {
    const blurb = angleObj?.blurb || '';
    return `Hey ${recipientName || 'there'}! ${blurb}\n\n${link}`;
  }, [recipientName, angleObj, link]);

  const waLink = useMemo(() => {
    const text = encodeURIComponent(message);
    return `https://wa.me/?text=${text}`;
  }, [message]);

  const copyText = async (key, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      toast.success('Copied');
      setTimeout(() => setCopied(null), 1500);
    } catch (_) {
      toast.error('Copy failed — long-press to copy manually');
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a10] text-white" data-testid="admin-share-links">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageCircle className="w-6 h-6 text-emerald-400" />
            Distribution Share Links
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Pick a channel + angle. Send the link. Every click is auto-tagged in <span className="font-mono text-emerald-300">/admin/activation</span>.
          </p>
        </header>

        {/* Settings grid */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-5 mb-6">
          {/* Path */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Landing path</label>
            <div className="grid grid-cols-2 gap-2">
              {PATHS.map(p => (
                <button
                  key={p.id}
                  onClick={() => setPathId(p.id)}
                  className={`px-3 py-2 rounded-lg text-sm border transition-all ${
                    pathId === p.id ? 'border-emerald-500 bg-emerald-500/10 text-white'
                                    : 'border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/5'
                  }`}
                  data-testid={`share-path-${p.id}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Channel */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Channel</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {CHANNELS.map(c => {
                const Icon = c.icon;
                const active = channelId === c.id;
                return (
                  <button
                    key={c.id}
                    onClick={() => setChannelId(c.id)}
                    className={`px-3 py-2 rounded-lg text-sm border transition-all flex items-center gap-2 ${
                      active ? 'border-emerald-500 bg-emerald-500/10 text-white'
                             : 'border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/5'
                    }`}
                    data-testid={`share-channel-${c.id}`}
                  >
                    <Icon className="w-4 h-4" /> {c.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Audience + Angle */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Audience</label>
              <select
                value={audience}
                onChange={(e) => setAudience(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm"
                data-testid="share-audience"
              >
                {AUDIENCES.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Message angle</label>
              <select
                value={angle}
                onChange={(e) => setAngle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm"
                data-testid="share-angle"
              >
                {ANGLES.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
              </select>
            </div>
          </div>

          {/* Campaign */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Campaign tag</label>
              <input
                value={campaign}
                onChange={(e) => setCampaign(e.target.value.replace(/\s+/g, '_').slice(0, 60))}
                className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm font-mono"
                placeholder="founder_dm_apr26"
                data-testid="share-campaign"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">Recipient first name (optional)</label>
              <input
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value.slice(0, 40))}
                className="w-full px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 text-white text-sm"
                placeholder="there"
                data-testid="share-recipient"
              />
            </div>
          </div>
        </section>

        {/* Output */}
        <section className="rounded-2xl border border-emerald-500/30 bg-emerald-950/15 p-5 mb-6" data-testid="share-output">
          <h2 className="text-sm font-semibold text-emerald-200 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5" /> Tagged link
          </h2>
          <div className="rounded-lg bg-black/40 border border-emerald-500/20 px-3 py-2 font-mono text-xs text-emerald-200 break-all" data-testid="share-link-text">
            {link}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => copyText('link', link)}
              className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold flex items-center gap-2"
              data-testid="share-copy-link"
            >
              {copied === 'link' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied === 'link' ? 'Copied' : 'Copy link'}
            </button>
            <button
              onClick={() => copyText('msg', message)}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-semibold flex items-center gap-2"
              data-testid="share-copy-msg"
            >
              {copied === 'msg' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied === 'msg' ? 'Copied' : 'Copy full message'}
            </button>
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-2 rounded-lg bg-[#25D366] hover:opacity-90 text-white text-sm font-semibold flex items-center gap-2"
              data-testid="share-open-wa"
            >
              <MessageCircle className="w-4 h-4" /> Open in WhatsApp
            </a>
          </div>
        </section>

        {/* Message preview */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5" data-testid="share-message-preview">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-3">Message preview</h2>
          <pre className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed font-sans">{message}</pre>
        </section>

        <p className="mt-4 text-xs text-slate-500">
          Tip: every click on this link auto-fills <span className="font-mono">utm_source</span>,{' '}
          <span className="font-mono">utm_campaign</span>, <span className="font-mono">utm_content</span> on every funnel event.{' '}
          Filter <span className="font-mono">/admin/activation</span> by these tomorrow morning to see which channel paid out.
        </p>

        {/* tiny dev-only debug */}
        <details className="mt-4 text-xs text-slate-600">
          <summary className="cursor-pointer">Sample message</summary>
          <pre className="whitespace-pre-wrap mt-2 font-mono text-slate-500">{SAMPLE_TEMPLATE(recipientName || 'there', link)}</pre>
        </details>
      </div>
    </div>
  );
}
