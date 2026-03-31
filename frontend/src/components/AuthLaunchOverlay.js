import React, { useState, useEffect } from 'react';

const LOADING_MESSAGES = [
  'Signing you in…',
  'Preparing your creative workspace…',
  'Loading your AI studio…',
  'Almost there…',
];

/**
 * AuthLaunchOverlay — Premium full-screen branded overlay shown during auth transitions.
 * Renders instantly on Google sign-in click to mask the external auth redirect.
 */
export default function AuthLaunchOverlay({ phase = 'launching' }) {
  const [messageIdx, setMessageIdx] = useState(0);
  const [showSlowNotice, setShowSlowNotice] = useState(false);

  // Rotate loading messages every 2.5s
  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIdx(prev => (prev + 1) % LOADING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  // Show "taking longer" notice after 8 seconds
  useEffect(() => {
    const timer = setTimeout(() => setShowSlowNotice(true), 8000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className="fixed inset-0 z-[99999] flex items-center justify-center"
      style={{
        background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)',
      }}
      data-testid="auth-launch-overlay"
      role="status"
      aria-live="polite"
    >
      {/* Subtle animated background particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-violet-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-2/3 left-1/2 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      <div className="relative text-center max-w-md px-6">
        {/* Logo */}
        <div className="mb-8 flex items-center justify-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
            </svg>
          </div>
          <span className="text-2xl font-bold text-white tracking-tight">Visionary Suite</span>
        </div>

        {/* Spinner */}
        <div className="relative w-14 h-14 mx-auto mb-6">
          <div className="absolute inset-0 rounded-full border-2 border-slate-700/50" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-transparent border-b-violet-400 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        </div>

        {/* Rotating message */}
        <p
          className="text-slate-300 text-base font-medium transition-opacity duration-500"
          key={messageIdx}
          style={{ animation: 'fadeInUp 0.5s ease-out' }}
        >
          {LOADING_MESSAGES[messageIdx]}
        </p>

        {/* Slow network notice */}
        {showSlowNotice && (
          <p className="text-slate-500 text-sm mt-4 animate-fadeIn">
            Still working — this is taking a little longer than usual
          </p>
        )}
      </div>

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeInUp 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}
