import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import analytics from '../utils/analytics';

const BOOTSTRAP_MESSAGES = [
  'Welcome back',
  'Syncing your studio…',
];

export default function AuthCallback({ setAuth }) {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);
  const [showSlowNotice, setShowSlowNotice] = useState(false);
  const [errorState, setErrorState] = useState(null);

  // Show slow-network notice only after 4s (reduced from 6s)
  useEffect(() => {
    const timer = setTimeout(() => setShowSlowNotice(true), 4000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        const hash = location.hash || '';
        const search = location.search || '';
        const fullFragment = hash + '&' + search;

        const sessionIdMatch = fullFragment.match(/session_id=([^&]+)/)
          || fullFragment.match(/sessionId=([^&]+)/);

        if (!sessionIdMatch) {
          setErrorState('No authentication session found. Please try signing in again.');
          return;
        }

        const sessionId = sessionIdMatch[1];

        const response = await api.post('/api/auth/google-callback', { sessionId });
        const { user, token } = response.data;

        if (!token || !user) {
          setErrorState('Authentication failed. Please try again.');
          return;
        }

        localStorage.setItem('token', token);

        analytics.trackSignup('google');
        if (user?.id) {
          analytics.setUserId(user.id);
        }

        if (setAuth) {
          setAuth(true);
        }

        // Show personalized welcome
        const firstName = user.name?.split(' ')[0] || 'there';
        toast.success(`Welcome back, ${firstName}!`);

        // Referral attribution
        try {
          const refRaw = localStorage.getItem('referral_source');
          if (refRaw && user?.id) {
            const refData = JSON.parse(refRaw);
            if (refData.job_id && Date.now() - refData.timestamp < 86400000) {
              await api.post('/api/growth/signup-referral-reward', {
                referrer_job_id: refData.job_id,
                new_user_id: user.id,
              });
              localStorage.removeItem('referral_source');
            }
          }
        } catch {
          // Silent fail for referral attribution
        }

        // Return-path: check for preserved destination
        const returnUrl = localStorage.getItem('auth_return_path')
          || localStorage.getItem('remix_return_url');

        if (returnUrl) {
          localStorage.removeItem('auth_return_path');
          localStorage.removeItem('remix_return_url');
          navigate(returnUrl, { replace: true });
        } else {
          navigate('/app', { replace: true });
        }
      } catch (error) {
        const detail = error?.response?.data?.detail
          || error?.response?.data?.message
          || 'Something went wrong. Please try again.';
        setErrorState(detail);
      }
    };

    processAuth();
  }, [location, navigate, setAuth]);

  // Error state — branded, with retry and return CTAs
  if (errorState) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-6"
        style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)' }}
        data-testid="auth-error-screen"
      >
        <div className="text-center max-w-sm">
          {/* Logo */}
          <div className="mb-6 flex items-center justify-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <span className="text-xl font-bold text-white">Visionary Suite</span>
          </div>

          <div className="w-14 h-14 mx-auto mb-5 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <svg className="w-7 h-7 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>

          <h2 className="text-white text-lg font-semibold mb-2">Sign-in didn't complete</h2>
          <p className="text-slate-400 text-sm mb-6">{errorState}</p>

          <div className="flex flex-col gap-3">
            <button
              onClick={() => {
                const redirectUrl = window.location.origin + '/auth/callback';
                window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
              }}
              className="w-full h-11 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-600 text-white font-semibold text-sm hover:opacity-90 transition-opacity"
              data-testid="auth-retry-btn"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="w-full h-11 rounded-xl border border-slate-700 text-slate-300 font-medium text-sm hover:bg-slate-800/50 transition-colors"
              data-testid="auth-back-to-login"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Loading state — near-instant branded bridge screen
  return (
    <div
      className="min-h-screen flex items-center justify-center px-6"
      style={{ background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0f172a 100%)' }}
      data-testid="auth-callback-loading"
      role="status"
      aria-live="polite"
    >
      <div className="relative text-center max-w-md">
        {/* Logo */}
        <div className="mb-6 flex items-center justify-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <span className="text-xl font-bold text-white tracking-tight">Visionary Suite</span>
        </div>

        {/* Minimal spinner */}
        <div className="relative w-10 h-10 mx-auto mb-4">
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-indigo-500 animate-spin" />
        </div>

        <p className="text-slate-400 text-sm">Signing you in…</p>

        {/* Slow network notice */}
        {showSlowNotice && (
          <p className="text-slate-500 text-xs mt-3">
            Still working — this is taking a little longer than usual
          </p>
        )}
      </div>
    </div>
  );
}
