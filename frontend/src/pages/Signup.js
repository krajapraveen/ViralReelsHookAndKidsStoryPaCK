import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { authAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Eye, EyeOff, Loader2, ArrowLeft, Mail, Lock, User, Check, X, Shield, Gift } from 'lucide-react';
import api from '../utils/api';
import { collectFingerprint } from '../utils/fingerprint';
import analytics from '../utils/analytics';

export default function Signup({ setAuth }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({ name: '', email: '', password: '' });
  const [touched, setTouched] = useState({ name: false, email: false, password: false });
  const navigate = useNavigate();
  
  // CAPTCHA state
  const [captchaConfig, setCaptchaConfig] = useState({ enabled: false, siteKey: '' });
  const [captchaToken, setCaptchaToken] = useState('');
  const [captchaLoaded, setCaptchaLoaded] = useState(false);
  const captchaRef = useRef(null);

  // Load CAPTCHA config on mount
  useEffect(() => {
    // Track funnel step - Signup page view
    analytics.trackFunnelStep('signup_start');
    
    const loadCaptchaConfig = async () => {
      try {
        const response = await api.get('/api/auth/captcha-config');
        setCaptchaConfig(response.data);
        
        if (response.data.enabled && response.data.siteKey) {
          // Load hCaptcha script
          if (!window.hcaptcha) {
            const script = document.createElement('script');
            script.src = 'https://js.hcaptcha.com/1/api.js';
            script.async = true;
            script.defer = true;
            script.onload = () => setCaptchaLoaded(true);
            document.head.appendChild(script);
          } else {
            setCaptchaLoaded(true);
          }
        }
      } catch (error) {
        console.error('Failed to load CAPTCHA config:', error);
      }
    };
    loadCaptchaConfig();
  }, []);

  // Render hCaptcha when loaded
  useEffect(() => {
    if (captchaLoaded && captchaConfig.enabled && captchaRef.current && window.hcaptcha) {
      try {
        window.hcaptcha.render(captchaRef.current, {
          sitekey: captchaConfig.siteKey,
          callback: (token) => setCaptchaToken(token),
          'expired-callback': () => setCaptchaToken(''),
          theme: 'dark'
        });
      } catch (e) {
        // Already rendered
      }
    }
  }, [captchaLoaded, captchaConfig]);

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
    
    // Validate CAPTCHA
    if (captchaConfig.enabled && !captchaToken) {
      toast.error('Please complete the CAPTCHA verification');
      return;
    }
    
    setLoading(true);

    try {
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
      
      // Show appropriate message based on credit system
      const delayedInfo = response.data.delayed_credits_info;
      if (delayedInfo) {
        toast.success(`Account created! You have ${delayedInfo.initial_credits} credits now. ${delayedInfo.pending_credits} more credits will be released over ${delayedInfo.release_period_days} days!`, {
          duration: 6000
        });
      } else {
        toast.success('Account created! Check your dashboard for credits.');
      }
      
      navigate('/app', { replace: true });
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Signup failed. Please try again.';
      // Handle CAPTCHA error
      if (errorMessage.toLowerCase().includes('captcha')) {
        toast.error('CAPTCHA verification failed. Please try again.');
        // Reset CAPTCHA
        if (window.hcaptcha && captchaRef.current) {
          window.hcaptcha.reset();
          setCaptchaToken('');
        }
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

  const handleGoogleSignIn = () => {
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

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
              <p className="font-medium">100 free credits on signup!</p>
            </div>
            <p className="text-slate-500 text-xs mt-1">Verify your email to unlock 20 credits + 80 bonus over 7 days</p>
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

            {/* CAPTCHA */}
            {captchaConfig.enabled && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-slate-300 text-sm">
                  <Shield className="w-4 h-4 text-green-400" />
                  <span>Security Verification</span>
                </div>
                <div 
                  ref={captchaRef}
                  className="flex justify-center"
                  data-testid="captcha-container"
                />
                {!captchaToken && (
                  <p className="text-xs text-slate-500 text-center">Please complete the verification above</p>
                )}
              </div>
            )}

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

            <Button
              type="button"
              onClick={handleGoogleSignIn}
              className="w-full mt-4 bg-white hover:bg-gray-100 text-gray-900 rounded-xl py-6 text-lg flex items-center justify-center gap-3"
              data-testid="google-signup-btn"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign up with Google
            </Button>
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
