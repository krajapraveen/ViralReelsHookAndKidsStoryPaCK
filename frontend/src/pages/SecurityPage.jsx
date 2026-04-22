import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck, Lock, Zap, Users, ChevronDown, Mail, ArrowRight,
  Radio, Clock, Award, Check, X,
} from 'lucide-react';

/**
 * /security — Vulnerability Disclosure Program landing
 * Enterprise-grade dark trust page. Stripe / Linear / OpenAI aesthetic.
 */
export default function SecurityPage() {
  const [openFaq, setOpenFaq] = React.useState(0);

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white overflow-x-hidden" data-testid="security-page">
      {/* Subtle animated grid bg */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(139,92,246,0.12), transparent 60%)',
        }}
      />

      {/* Top nav */}
      <header className="relative z-10 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="security-brand">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-violet-500 to-rose-500 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold tracking-tight">Visionary Suite</span>
          </Link>
          <div className="flex items-center gap-5 text-sm">
            <Link to="/" className="text-slate-400 hover:text-white transition-colors">Home</Link>
            <Link to="/pricing" className="text-slate-400 hover:text-white transition-colors">Pricing</Link>
            <Link
              to="/security/report"
              className="px-4 py-1.5 rounded-lg bg-white text-black hover:bg-slate-100 transition-colors font-medium"
              data-testid="nav-report-cta"
            >
              Report Vulnerability
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-16 grid lg:grid-cols-[1.1fr,0.9fr] gap-12 items-center">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/30 text-[11px] tracking-[0.12em] text-violet-300 font-medium mb-6">
            <Lock className="w-3 h-3" /> SECURITY · RESPONSIBLE DISCLOSURE
          </div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-[1.05] mb-6">
            Security built into<br />
            <span className="bg-gradient-to-r from-violet-300 via-indigo-300 to-rose-300 bg-clip-text text-transparent">
              Visionary Suite
            </span>
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed max-w-xl mb-8">
            We protect creators, businesses, and AI workflows through secure architecture, responsible disclosure, and continuous improvement.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              to="/security/report"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 transition-colors group"
              data-testid="hero-report-cta"
            >
              Report a Vulnerability
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <a
              href="mailto:krajapraveen@visionary-suite.com"
              className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              <Mail className="w-4 h-4" /> Email Security Team
            </a>
          </div>
          <div className="flex flex-wrap items-center gap-5 mt-8 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-emerald-400" /> Responsible Disclosure</span>
            <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-emerald-400" /> Fast Triage</span>
            <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-emerald-400" /> Secure Infrastructure</span>
          </div>
        </div>

        {/* Right — dashboard card */}
        <div className="relative">
          <div className="relative rounded-2xl border border-white/[0.08] bg-gradient-to-br from-white/[0.05] to-white/[0.02] backdrop-blur-xl p-7 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <span className="text-[11px] tracking-[0.12em] text-slate-400 font-medium">SECURITY HEALTH</span>
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE
              </div>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Monitoring Active', ok: true },
                { label: 'Responsible Disclosure', ok: true },
                { label: 'Access Controls Enabled', ok: true },
                { label: 'Encrypted Sessions (TLS 1.3)', ok: true },
                { label: 'Attachment Isolation', ok: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-sm">
                  <span className="text-slate-300">{item.label}</span>
                  <div className="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                    <Check className="w-3 h-3 text-emerald-400" />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 pt-5 border-t border-white/[0.06] flex items-center justify-between">
              <span className="text-[11px] text-slate-500">Last reviewed</span>
              <span className="text-[11px] text-slate-300 font-mono">Apr 2026</span>
            </div>
          </div>
          <div className="absolute -inset-px bg-gradient-to-br from-violet-500/10 to-transparent rounded-2xl pointer-events-none -z-10 blur-2xl" />
        </div>
      </section>

      {/* Metrics strip */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { value: '72h', label: 'Typical Initial Response', icon: Clock },
            { value: '7 Days', label: 'Triage Target', icon: Zap },
            { value: '24/7', label: 'Monitoring Signals', icon: Radio },
            { value: '300+', label: 'Credits for Valid Reports*', icon: Award },
          ].map((m) => (
            <div
              key={m.label}
              className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors"
              data-testid={`metric-${m.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
            >
              <m.icon className="w-4 h-4 text-violet-400 mb-3" />
              <p className="text-2xl font-bold tracking-tight">{m.value}</p>
              <p className="text-xs text-slate-500 mt-1">{m.label}</p>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-3">*Discretionary for eligible, accepted reports.</p>
      </section>

      {/* Principles */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">How we think about security</h2>
        <p className="text-slate-400 mb-12 max-w-2xl">Security isn't a checkbox. It's how the product is architected, maintained, and improved.</p>
        <div className="grid md:grid-cols-3 gap-5">
          {[
            { icon: ShieldCheck, title: 'Secure by Design', body: 'Authentication, permissions, media access, and billing controls are built into product architecture — not bolted on after release.' },
            { icon: Zap, title: 'Continuous Improvement', body: 'We regularly harden systems, review risks, and respond to evolving threats across every layer of the stack.' },
            { icon: Users, title: 'Community Collaboration', body: 'Responsible researchers help us make Visionary Suite stronger. We review every valid report and coordinate remediation openly.' },
          ].map((card) => (
            <div
              key={card.title}
              className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-7 hover:border-violet-500/30 transition-colors"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/30 flex items-center justify-center mb-5">
                <card.icon className="w-5 h-5 text-violet-300" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{card.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{card.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Scope */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-5">
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] p-7" data-testid="in-scope">
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-[10px] text-emerald-400 font-medium tracking-wider mb-4">IN SCOPE</div>
            <h3 className="text-xl font-semibold mb-5">Systems we welcome reports on</h3>
            <ul className="space-y-2.5">
              {[
                'visionary-suite.com public website experience',
                'Authentication & user account systems',
                'Billing & subscription flows',
                'APIs operated by Visionary Suite',
                'Creator dashboards & internal user controls',
                'Public share pages & media access flows',
                'Session management & authorization logic',
              ].map((i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  {i}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.03] p-7" data-testid="out-scope">
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-400 font-medium tracking-wider mb-4">OUT OF SCOPE</div>
            <h3 className="text-xl font-semibold mb-5">Please do not submit</h3>
            <ul className="space-y-2.5">
              {[
                'Social engineering or phishing attempts',
                'Denial-of-service or traffic flooding',
                'Spam or content moderation issues',
                'Third-party services outside our control',
                'Missing best-practice headers without exploitability',
                'Self-XSS requiring your own browser input',
                'Automated scanner noise without proof of impact',
              ].map((i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                  <X className="w-4 h-4 text-amber-400/70 shrink-0 mt-0.5" />
                  {i}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">Safe harbor & process</h2>
        <p className="text-slate-400 mb-12 max-w-2xl">If you act in good faith and follow this policy, we consider your research authorized.</p>
        <div className="relative rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-6">
            {[
              'Discover issue',
              'Report privately',
              'We acknowledge',
              'We investigate',
              'We remediate',
              'Coordinated disclosure',
            ].map((step, i) => (
              <div key={step} className="relative">
                <div className="w-8 h-8 rounded-full border border-violet-500/40 bg-violet-500/10 flex items-center justify-center text-xs font-bold text-violet-300 mb-3">
                  {i + 1}
                </div>
                <p className="text-sm font-medium text-white">{step}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="text-sm text-slate-500 mt-6 leading-relaxed max-w-3xl">
          Please access only what is necessary to validate the issue. Do not modify or destroy data, degrade service availability, or disclose publicly before coordinated remediation.
        </p>
      </section>

      {/* Rewards */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="relative rounded-3xl border border-white/[0.06] bg-gradient-to-br from-violet-500/[0.06] to-transparent p-10 overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse 60% 50% at 100% 0%, rgba(168,85,247,0.14), transparent 60%)' }}
          />
          <div className="relative">
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-violet-500/10 border border-violet-500/30 text-[10px] text-violet-300 font-medium tracking-wider mb-4">
              <Award className="w-3 h-3" /> RECOGNITION
            </div>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">Great reports deserve recognition</h2>
            <p className="text-slate-400 mb-8 max-w-2xl">
              Our responsible disclosure program rewards high-quality, validated reports with complimentary credits and recognition.
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              {[
                { title: 'Hall of Fame', body: 'Optional public recognition for researchers who help us strengthen the platform.' },
                { title: '300+ Free Credits', body: 'Validated reports may receive complimentary Visionary Suite credits. Severity-tiered.' },
                { title: 'Direct Collaboration', body: 'Exceptional researchers may be invited for coordinated private testing.' },
              ].map((r) => (
                <div key={r.title} className="rounded-xl border border-white/[0.06] bg-black/30 p-5 backdrop-blur-sm">
                  <p className="text-sm font-semibold mb-2">{r.title}</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{r.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-12">Frequently asked</h2>
        <div className="space-y-3">
          {[
            { q: 'Do you offer cash bug bounties?', a: 'Currently we primarily offer recognition and complimentary Visionary Suite credits for eligible validated reports. We do not operate a public cash bounty program at this time.' },
            { q: 'Can I test production systems?', a: 'Only within this policy, without harming users, and without degrading service availability. Do not access, modify, or destroy user data beyond what is necessary to validate the issue.' },
            { q: 'Will I receive a response?', a: 'Legitimate, in-scope reports are typically acknowledged within 72 hours. Duplicate, out-of-scope, or low-effort submissions may not receive a response.' },
            { q: 'Can I disclose the issue publicly?', a: 'Please wait until coordinated remediation is complete. Publishing details before a fix is deployed can put users at risk and may void safe harbor.' },
            { q: 'How do rewards work?', a: 'Severity-tiered credit rewards are granted at our discretion for valid, accepted reports. Duplicates, informative-only, or out-of-scope reports are not eligible.' },
          ].map((faq, i) => (
            <button
              key={faq.q}
              onClick={() => setOpenFaq(openFaq === i ? -1 : i)}
              className="w-full text-left rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors"
              data-testid={`faq-${i}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{faq.q}</span>
                <ChevronDown
                  className={`w-4 h-4 text-slate-500 transition-transform ${openFaq === i ? 'rotate-180' : ''}`}
                />
              </div>
              {openFaq === i && (
                <p className="text-sm text-slate-400 leading-relaxed mt-3">{faq.a}</p>
              )}
            </button>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 py-24 text-center">
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-5">Help us keep Visionary Suite secure</h2>
        <p className="text-lg text-slate-400 mb-10 max-w-2xl mx-auto">
          Responsible disclosure strengthens the platform for creators and teams worldwide.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/security/report"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 transition-colors"
            data-testid="final-report-cta"
          >
            Submit Security Report <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="mailto:krajapraveen@visionary-suite.com"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-white/20 text-white hover:bg-white/5 transition-colors"
          >
            <Mail className="w-4 h-4" /> krajapraveen@visionary-suite.com
          </a>
        </div>
      </section>

      <footer className="relative z-10 border-t border-white/[0.06] py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
          <span>&copy; 2026 Visionary Suite</span>
          <div className="flex items-center gap-5">
            <Link to="/" className="hover:text-white">Home</Link>
            <Link to="/privacy" className="hover:text-white">Privacy</Link>
            <Link to="/terms" className="hover:text-white">Terms</Link>
            <Link to="/security" className="text-white">Security</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
