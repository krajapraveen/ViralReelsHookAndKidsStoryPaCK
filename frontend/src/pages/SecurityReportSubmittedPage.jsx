import React from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, ShieldCheck, ArrowRight } from 'lucide-react';

export default function SecurityReportSubmittedPage() {
  const [params] = useSearchParams();
  const reportId = params.get('id') || 'VSR-UNKNOWN';

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white flex items-center justify-center p-6" data-testid="security-submitted-page">
      <div
        className="fixed inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 10%, rgba(139,92,246,0.12), transparent 60%)' }}
      />
      <div className="relative z-10 max-w-md w-full text-center">
        <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-6">
          <Check className="w-8 h-8 text-emerald-400" />
        </div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/30 text-[11px] tracking-[0.12em] text-violet-300 font-medium mb-5">
          <ShieldCheck className="w-3 h-3" /> REPORT RECEIVED
        </div>
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-3">Thank you</h1>
        <p className="text-slate-400 leading-relaxed mb-8">
          Your report has been received and is queued for review by our security team.
        </p>

        <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-5 mb-6 text-left">
          <p className="text-[10px] text-slate-500 uppercase tracking-[0.12em] mb-1">Your tracking ID</p>
          <p className="text-xl font-bold text-white font-mono tracking-tight" data-testid="submitted-report-id">
            {reportId}
          </p>
        </div>

        <p className="text-sm text-slate-500 leading-relaxed mb-8">
          Legitimate reports are typically acknowledged within <span className="text-white">72 hours</span>. Please retain this ID for future communication, and avoid public disclosure until coordinated remediation.
        </p>

        <Link
          to="/"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 transition-colors"
          data-testid="return-home-btn"
        >
          Return Home <ArrowRight className="w-4 h-4" />
        </Link>

        <p className="text-xs text-slate-600 mt-10">
          Questions? Email{' '}
          <a href="mailto:krajapraveen@visionary-suite.com" className="text-violet-300 hover:text-violet-200 underline">
            krajapraveen@visionary-suite.com
          </a>
        </p>
      </div>
    </div>
  );
}
