import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Sparkles, Gift, ArrowRight, Check, Loader2, ShieldCheck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Public landing page for invited users.
 * URL: /refer?code=XYZ
 * - Validates code
 * - Persists code to localStorage for signup attribution
 * - CTA → /signup?ref=XYZ
 */
export default function ReferLanding() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const code = params.get('code') || '';
  const [state, setState] = useState({ loading: true, valid: false });

  useEffect(() => {
    if (!code) {
      setState({ loading: false, valid: false });
      return;
    }
    (async () => {
      try {
        const { data } = await axios.get(`${API}/api/referrals/lookup/${encodeURIComponent(code)}`);
        if (data.valid) {
          localStorage.setItem('ref_code', data.code);
          localStorage.setItem('ref_code_set_at', String(Date.now()));
          // Fire click event
          try {
            const fp = navigator.userAgent + '|' + (navigator.language || '');
            await axios.post(`${API}/api/referrals/click`, {
              code: data.code, path: '/refer', fingerprint: fp,
            });
          } catch (_) { /* best-effort */ }
        }
        setState({ loading: false, valid: !!data.valid });
      } catch (e) {
        setState({ loading: false, valid: false });
      }
    })();
  }, [code]);

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white flex items-center justify-center p-6" data-testid="refer-landing">
      <div
        className="fixed inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 50% at 50% 10%, rgba(139,92,246,0.15), transparent 60%)' }}
      />
      <div className="relative z-10 max-w-xl w-full text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/30 text-[11px] tracking-[0.12em] text-violet-300 font-medium mb-6">
          <Gift className="w-3 h-3" /> YOU'VE BEEN INVITED
        </div>

        {state.loading ? (
          <Loader2 className="w-8 h-8 text-violet-400 animate-spin mx-auto" />
        ) : state.valid ? (
          <>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-5">
              Welcome to{' '}
              <span className="bg-gradient-to-r from-violet-300 via-indigo-300 to-rose-300 bg-clip-text text-transparent">
                Visionary Suite
              </span>
            </h1>
            <p className="text-lg text-slate-400 leading-relaxed mb-8">
              A friend invited you to try the AI story-to-video engine used by creators worldwide. Sign up and get started in seconds.
            </p>

            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.06] p-5 mb-8 text-left flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <Sparkles className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-300">Invite applied</p>
                <p className="text-xs text-slate-400">You're joining via invite code <code className="font-mono text-slate-300">{code}</code></p>
              </div>
            </div>

            <button
              onClick={() => navigate(`/signup?ref=${encodeURIComponent(code)}`)}
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 transition-colors group"
              data-testid="refer-signup-btn"
            >
              Create Free Account
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </button>

            <div className="mt-10 grid grid-cols-3 gap-4 text-xs text-slate-500">
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <Check className="w-3 h-3 text-emerald-400 mx-auto mb-1" />
                50 free credits
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <Check className="w-3 h-3 text-emerald-400 mx-auto mb-1" />
                No credit card
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <ShieldCheck className="w-3 h-3 text-emerald-400 mx-auto mb-1" />
                Cancel anytime
              </div>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-3xl md:text-4xl font-bold mb-4">Invite link invalid</h1>
            <p className="text-slate-400 mb-8">
              This invite link isn't valid or has expired. You can still sign up and start creating for free.
            </p>
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-slate-100 transition-colors"
              data-testid="refer-fallback-signup"
            >
              Continue to Sign Up <ArrowRight className="w-4 h-4" />
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
