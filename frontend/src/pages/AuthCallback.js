import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import analytics from '../utils/analytics';

export default function AuthCallback({ setAuth }) {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Extract session_id from hash or query params (support both formats)
        const hash = location.hash || '';
        const search = location.search || '';
        const fullFragment = hash + '&' + search;
        
        const sessionIdMatch = fullFragment.match(/session_id=([^&]+)/) 
          || fullFragment.match(/sessionId=([^&]+)/);
        
        if (!sessionIdMatch) {
          console.error('Auth callback: No session_id found in URL', { hash, search });
          toast.error('Authentication failed. Please try again.');
          navigate('/login');
          return;
        }

        const sessionId = sessionIdMatch[1];
        
        // Exchange session_id for user data
        const response = await api.post('/api/auth/google-callback', { sessionId });
        const { user, token } = response.data;
        
        if (!token || !user) {
          toast.error('Authentication failed. Invalid response from server.');
          navigate('/login');
          return;
        }
        
        // Store token
        localStorage.setItem('token', token);
        
        // Track Google sign-in/sign-up in Google Analytics
        analytics.trackSignup('google');
        if (user?.id) {
          analytics.setUserId(user.id);
        }
        
        // Set authentication state
        if (setAuth) {
          setAuth(true);
        }
        
        toast.success(`Welcome, ${user.name}!`);
        
        // Navigate to dashboard immediately
        navigate('/app', { replace: true });
        
      } catch (error) {
        console.error('Auth callback error:', error?.response?.data || error);
        const detail = error?.response?.data?.detail || error?.response?.data?.message || 'Please try again.';
        toast.error('Google sign-in failed: ' + detail);
        navigate('/login');
      }
    };

    // Process immediately
    processAuth();
  }, [location, navigate, setAuth]);

  // Minimal loading screen without any branding
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-slate-400 text-sm">Signing you in...</p>
      </div>
    </div>
  );
}
