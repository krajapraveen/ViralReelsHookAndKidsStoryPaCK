import React, { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { authAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Eye, EyeOff, Loader2, ArrowLeft, Mail, Lock, User, Check, X, Shield, Gift } from 'lucide-react';
import api from '../utils/api';
import { collectFingerprint } from '../utils/fingerprint';
import analytics from '../utils/analytics';
import { useRecaptcha } from '../hooks/useRecaptcha';
import { trackSignupCompleted, linkSessionToUser } from '../utils/growthAnalytics';
import { trackConversion } from '../lib/abTesting';
import { useGoogleLogin } from '@react-oauth/google';

export default function Signup({ setAuth }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({ name: '', email: '', password: '' });
  const [touched, setTouched] = useState({ name: false, email: false, password: false });
  const [googleLoading, setGoogleLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { executeRecaptcha } = useRecaptcha();

  // Preload app shell so /app renders faster after auth
  useEffect(() => {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = '/app';
    document.head.appendChild(link);
    return () => document.head.removeChild(link);
  }, []);

  // Capture prompt from landing page for onboarding flow
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const prompt = params.get('prompt');
    if (prompt) {
      localStorage.setItem('onboarding_prompt', prompt);
    }
    analytics.trackFunnelStep('signup_start');
  }, []);

  // Password requirements check
  const passwordRequirements = useMemo(() => ({
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
  }), [password]);

  const isPasswordValid = Object.values(passwordRequirements).every(Boolean);

  // Email validation regex
  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Name validation - comprehensive
  const validateName = (value) => {
    const trimmed = value.trim();
    
    if (!trimmed) {
      return 'Full name is required';
    }
    
    // Check if only spaces
    if (value.length > 0 && trimmed.length === 0) {
      return 'Name cannot be only spaces';
    }
    
    // Check minimum length
    if (trimmed.length < 2) {
      return 'Name must be at least 2 characters';
    }
    
    // Check if only numbers
    if (/^[0-9]+$/.test(trimmed)) {
      return 'Name cannot be only numbers';
    }
    
    // Check if only special characters
    if (/^[^a-zA-Z0-9]+$/.test(trimmed)) {
      return 'Name must contain letters';
    }
    
    // Check max length
    if (trimmed.length > 100) {
      return 'Name is too long (max 100 characters)';
    }
    
    // Check for valid characters (letters, spaces, hyphens, apostrophes)
    if (!/^[a-zA-Z\s\-']+$/.test(trimmed)) {
      return 'Name can only contain letters, spaces, hyphens, and apostrophes';
    }
    
    return '';
  };

  // Email validation
  const validateEmail = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return 'Email is required';
    }
    if (trimmed.length > 254) {
      return 'Email is too long';
    }
    if (!isValidEmail(trimmed)) {
      return 'Please enter a valid email address';
    }
    return '';
  };

  // Password validation
  const validatePassword = (value) => {
    if (!value) {
      return 'Password is required';
    }
    if (value.length < 8) {
      return 'Password must be at least 8 characters';
    }
    if (!/[A-Z]/.test(value)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(value)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(value)) {
      return 'Password must contain at least one number';
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value)) {
      return 'Password must contain at least one special character';
    }
    return '';
  };

  const handleNameChange = (e) => {
    const value = e.target.value;
    // Max length protection
    if (value.length <= 100) {
      setName(value);
    }
    if (errors.name && touched.name) {
      setErrors(prev => ({ ...prev, name: validateName(value) }));
    }
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    // Max length protection
    if (value.length <= 254) {
      setEmail(value);
    }
    if (errors.email && touched.email) {
      setErrors(prev => ({ ...prev, email: validateEmail(value) }));
    }
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    if (errors.password && touched.password) {
      setErrors(prev => ({ ...prev, password: validatePassword(value) }));
    }
  };

  const handleBlur = (field) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    
    if (field === 'name') {
      setErrors(prev => ({ ...prev, name: validateName(name) }));
    } else if (field === 'email') {
      setErrors(prev => ({ ...prev, email: validateEmail(email) }));
    } else if (field === 'password') {
      setErrors(prev => ({ ...prev, password: validatePassword(password) }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Prevent double submission
    if (loading) return;
    
    // Validate all fields
    const nameError = validateName(name);
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    
    setTouched({ name: true, email: true, password: true });
    
    if (nameError || emailError || passwordError) {
      setErrors({ name: nameError, email: emailError, password: passwordError });
      return;
    }
    
    setLoading(true);

    try {
      // Get reCAPTCHA v3 token (invisible)
      const captchaToken = await executeRecaptcha('signup');

      // Collect device fingerprint for anti-abuse protection
      let fingerprint = null;
      try {
        fingerprint = await collectFingerprint();
      } catch (e) {
        console.warn('Fingerprint collection failed:', e);
      }
      
      const response = await authAPI.register({ 
        name: name.trim(), 
        email: email.trim().toLowerCase(), 
        password,
        captcha_token: captchaToken,
        fingerprint: fingerprint
      });
      localStorage.setItem('token', response.data.token);
      setAuth(true);
      
      // Track signup in Google Analytics
      analytics.trackSignup('email');
      analytics.setUserId(response.data.user?.id);
      
      // Track funnel step - Signup complete
      analytics.trackFunnelStep('signup_complete', { method: 'email' });
      const userId = response.data.user?.id;
      localStorage.setItem('user_id', userId || '');
      trackSignupCompleted({ source_page: '/signup', meta: { method: 'email' } });
      // Link anonymous session events to this new user
      if (userId) linkSessionToUser(userId);

      // Track A/B experiment conversions
      trackConversion('cta_copy', 'signup_completed');
      trackConversion('hook_text', 'signup_completed');
      trackConversion('login_timing', 'signup_completed');

      // ═══ REFERRAL ATTRIBUTION: Award +25 credits to referrer ═══
      try {
        const refRaw = localStorage.getItem('referral_source');
        if (refRaw && userId) {
          const refData = JSON.parse(refRaw);
          // Only attribute if referral was captured in the last 24 hours
          if (refData.job_id && Date.now() - refData.timestamp < 86400000) {
            await api.post('/api/growth/signup-referral-reward', {
              referrer_job_id: refData.job_id,
              new_user_id: userId,
            });
            localStorage.removeItem('referral_source');
          }
        }
      } catch (refErr) {
        console.warn('Referral attribution failed:', refErr);
      }
      
      // Show appropriate message based on credit system
      const delayedInfo = response.data.delayed_credits_info;
      if (delayedInfo) {
        toast.success(`Account created! You have ${delayedInfo.initial_credits} credits now. ${delayedInfo.pending_credits} more credits will be released over ${delayedInfo.release_period_days} days!`, {
          duration: 6000
        });
      } else {
        toast.success('Account created! Check your dashboard for credits.');
      }
      
      // Onboarding: redirect to Story→Video studio if user came from a prompt
      const onboardingPrompt = localStorage.getItem('onboarding_prompt');
      const returnUrl = localStorage.getItem('remix_return_url');
      if (returnUrl) {
        localStorage.removeItem('remix_return_url');
        navigate(returnUrl, { replace: true });
      } else if (onboardingPrompt) {
        navigate('/app/story-video-studio', { replace: true });
      } else {
        navigate('/app/story-video-studio', { replace: true });
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Signup failed. Please try again.';
      // Handle CAPTCHA error
      if (errorMessage.toLowerCase().includes('captcha')) {
        toast.error('CAPTCHA verification failed. Please try again.');
      // Handle disposable email error
      } else if (errorMessage.toLowerCase().includes('disposable') || errorMessage.toLowerCase().includes('not allowed')) {
        toast.error('Please use a valid email address. Temporary/disposable emails are not allowed.', { duration: 5000 });
      // Handle IP limit error
      } else if (errorMessage.toLowerCase().includes('ip') || errorMessage.toLowerCase().includes('maximum')) {
        toast.error('Too many accounts created from your network. Please try again later or contact support.', { duration: 5000 });
      // Handle device limit error
      } else if (errorMessage.toLowerCase().includes('device')) {
        toast.error('This device already has an account. Please login instead.', { duration: 5000 });
      // Handle duplicate email error
      } else if (errorMessage.toLowerCase().includes('email') && errorMessage.toLowerCase().includes('exist')) {
        toast.error('An account with this email already exists. Please login or use a different email.');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (tokenResponse) => {
    setGoogleLoading(true);
    try {
      const response = await api.post('/api/auth/google-signin', {
        access_token: tokenResponse.access_token,
      });
      const { token, user } = response.data;
      if (!token) {
        throw new Error('No token in response');
      }
      localStorage.setItem('token', token);
      if (user) {
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('user_id', user.id || '');
        analytics.trackSignup('google_direct');
        analytics.setUserId(user.id);
        linkSessionToUser(user.id);
        trackSignupCompleted(user.id, 'google');
        trackConversion('signup_google');
      }
      setAuth(true);
      const firstName = user?.name?.split(' ')[0] || 'there';
      toast.success(`Welcome, ${firstName}!`);
      const returnUrl = localStorage.getItem('auth_return_path')
        || localStorage.getItem('remix_return_url');
      if (returnUrl) {
        localStorage.removeItem('auth_return_path');
        localStorage.removeItem('remix_return_url');
        window.location.href = returnUrl;
      } else {
        window.location.href = '/app';
      }
    } catch (error) {
      const msg = error?.response?.data?.detail || 'Google sign-up failed. Please try again.';
      toast.error(msg);
      setGoogleLoading(false);
    }
  };

  const googleLogin = useGoogleLogin({
    onSuccess: handleGoogleSuccess,
    onError: () => { toast.error('Google sign-up was cancelled or failed.'); },
  });

  // Custom input styles for dark theme
  const inputBaseStyles = `
    w-full h-12 rounded-lg border border-slate-600/50 
    bg-slate-800/80 text-slate-100 
    placeholder:text-slate-400
    focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none
    transition-all duration-200
    text-base
  `.replace(/\s+/g, ' ').trim();

  // Password requirement indicator component
  const RequirementCheck = ({ met, text }) => (
    <div className={`flex items-center gap-2 text-xs ${met ? 'text-green-400' : 'text-slate-500'}`}>
      {met ? (
        <Check className="w-3 h-3" />
      ) : (
        <X className="w-3 h-3" />
      )}
      <span>{text}</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center p-4">
      {/* Loading overlay for Google sign-in */}
      {googleLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 backdrop-blur-sm">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mx-auto mb-3" />
            <p className="text-white text-sm">Creating your account...</p>
          </div>
        </div>
      )}

      <div className="w-full max-w-md">
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-4">
              <Sparkles className="w-8 h-8 text-indigo-500" />
              <span className="text-2xl font-bold text-white">Visionary Suite</span>
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">Get Started Free</h2>
            <div className="flex items-center justify-center gap-2 text-emerald-400">
              <Gift className="w-5 h-5" />
              <p className="font-medium">50 free credits on signup!</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="signup-form">
            {/* Full Name Field */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-slate-300 text-sm font-medium block">
                Full Name
              </Label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
                  <User className="w-5 h-5 text-slate-400" aria-hidden="true" />
                </span>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={handleNameChange}
                  onBlur={() => handleBlur('name')}
                  aria-label="Full name"
                  aria-describedby={errors.name ? "name-error" : undefined}
                  aria-invalid={!!errors.name}
                  style={{ paddingLeft: '48px', paddingRight: '16px' }}
                  className={`${inputBaseStyles} ${errors.name && touched.name ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                  placeholder="John Doe"
                  data-testid="signup-name-input"
                  autoComplete="name"
                  maxLength={100}
                />
              </div>
              {errors.name && touched.name && (
                <p id="name-error" className="text-red-400 text-sm mt-1" role="alert">
                  {errors.name}
                </p>
              )}
            </div>

            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300 text-sm font-medium block">
                Email
              </Label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
                  <Mail className="w-5 h-5 text-slate-400" aria-hidden="true" />
                </span>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={handleEmailChange}
                  onBlur={() => handleBlur('email')}
                  aria-label="Email address"
                  aria-describedby={errors.email ? "email-error" : undefined}
                  aria-invalid={!!errors.email}
                  style={{ paddingLeft: '48px', paddingRight: '16px' }}
                  className={`${inputBaseStyles} ${errors.email && touched.email ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                  placeholder="you@example.com"
                  data-testid="signup-email-input"
                  autoComplete="email"
                  maxLength={254}
                />
              </div>
              {errors.email && touched.email && (
                <p id="email-error" className="text-red-400 text-sm mt-1" role="alert">
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-300 text-sm font-medium block">
                Password
              </Label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
                  <Lock className="w-5 h-5 text-slate-400" aria-hidden="true" />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={handlePasswordChange}
                  onBlur={() => handleBlur('password')}
                  aria-label="Password"
                  aria-describedby="password-requirements"
                  aria-invalid={!!errors.password && touched.password}
                  style={{ paddingLeft: '48px', paddingRight: '48px' }}
                  className={`${inputBaseStyles} ${errors.password && touched.password ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                  placeholder="Create a strong password"
                  data-testid="signup-password-input"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center justify-center text-slate-400 hover:text-slate-200 transition-colors focus:outline-none"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  data-testid="toggle-password-visibility"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              
              {/* Password Requirements Checklist */}
              <div id="password-requirements" className="mt-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                <p className="text-slate-400 text-xs mb-2 font-medium">Password must have:</p>
                <div className="grid grid-cols-2 gap-1">
                  <RequirementCheck met={passwordRequirements.minLength} text="8+ characters" />
                  <RequirementCheck met={passwordRequirements.hasUppercase} text="Uppercase letter" />
                  <RequirementCheck met={passwordRequirements.hasLowercase} text="Lowercase letter" />
                  <RequirementCheck met={passwordRequirements.hasNumber} text="Number" />
                  <RequirementCheck met={passwordRequirements.hasSpecial} text="Special character" />
                </div>
              </div>
              
              {errors.password && touched.password && (
                <p id="password-error" className="text-red-400 text-sm mt-1" role="alert">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Protected by reCAPTCHA v3 (invisible) */}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl py-6 text-lg shadow-lg shadow-indigo-500/20 disabled:opacity-70 disabled:cursor-not-allowed transition-all duration-200"
              data-testid="signup-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </Button>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-slate-900/50 text-slate-400">Or continue with</span>
              </div>
            </div>

            <div className="w-full mt-4 flex justify-center" data-testid="google-signup-btn">
              <button
                type="button"
                onClick={() => googleLogin()}
                className="w-full max-w-[380px] h-11 rounded-full border border-slate-600 bg-slate-800 hover:bg-slate-700 transition-colors flex items-center justify-center gap-3 text-sm font-medium text-white"
                data-testid="google-signup-popup-btn"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
                  <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 2.58 9 2.58z" fill="#EA4335"/>
                </svg>
                Sign up with Google
              </button>
            </div>
          </div>

          <div className="mt-6 text-center">
            <p className="text-slate-400">
              Already have an account?{' '}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors" data-testid="login-link">
                Login
              </Link>
            </p>
          </div>
        </div>
        
        {/* Back to Home */}
        <div className="text-center mt-6">
          <Link to="/" className="text-slate-500 hover:text-slate-300 transition-colors inline-flex items-center gap-2" data-testid="back-to-home-link">
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
