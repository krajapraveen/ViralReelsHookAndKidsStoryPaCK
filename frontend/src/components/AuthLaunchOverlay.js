import React, { useState, useEffect } from 'react';

/**
 * AuthLaunchOverlay — Minimal full-screen branded overlay shown during auth transitions.
 * Renders instantly on Google sign-in click to mask the external auth redirect.
 * Kept ultra-lean for fastest possible paint.
 */
export default function AuthLaunchOverlay() {
  const [showSlowNotice, setShowSlowNotice] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowSlowNotice(true), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center"
      style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)' }}
      data-testid="auth-launch-overlay"
    >
      <div className="text-center max-w-md px-6">
        <div className="mb-6 flex items-center justify-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <span className="text-xl font-bold text-white tracking-tight">Visionary Suite</span>
        </div>

        <div className="relative w-10 h-10 mx-auto mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
        </div>

        <p className="text-slate-400 text-sm">Signing you in…</p>

        {showSlowNotice && (
          <p className="text-slate-500 text-xs mt-3">Still working — this is taking a little longer than usual</p>
        )}
      </div>
    </div>
  );
}
