import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';

export default function AuthCallback({ setAuth }) {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        const hash = location.hash;
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          toast.error('No session ID found');
          navigate('/login');
          return;
        }

        const sessionId = sessionIdMatch[1];
        
        // Exchange session_id for user data
        const response = await api.post('/api/auth/google-callback', { sessionId });
        const { user, token } = response.data;
        
        // Store token
        localStorage.setItem('token', token);
        
        // Set authentication state
        if (setAuth) {
          setAuth(true);
        }
        
        toast.success(`Welcome, ${user.name}!`);
        
        // Navigate to dashboard immediately
        navigate('/app', { replace: true });
        
      } catch (error) {
        console.error('Auth error:', error);
        toast.error('Authentication failed: ' + (error.response?.data?.message || error.message));
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
