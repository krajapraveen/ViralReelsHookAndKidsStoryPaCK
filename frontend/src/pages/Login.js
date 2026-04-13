import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import api, { authAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Eye, EyeOff, Loader2, ArrowLeft, Mail, Lock, CheckCircle2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import analytics from '../utils/analytics';
import { useRecaptcha } from '../hooks/useRecaptcha';
import { linkSessionToUser } from '../utils/growthAnalytics';

export default function Login({ setAuth }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotEmailError, setForgotEmailError] = useState('');
  const [sendingReset, setSendingReset] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  const [errors, setErrors] = useState({ email: '', password: '' });
  const [loginError, setLoginError] = useState('');
  const [failedAttempts, setFailedAttempts] = useState(0);
  const forgotEmailInputRef = useRef(null);
  const forgotPasswordLinkRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { executeRecaptcha } = useRecaptcha();

  // Preload app shell so /app renders faster after auth
  useEffect(() => {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = '/app';
    document.head.appendChild(link);
    return () => document.head.removeChild(link);
  }, []);

  // Focus email input when modal opens
  useEffect(() => {
    if (showForgotPassword && forgotEmailInputRef.current && !resetSent) {
      setTimeout(() => {
        forgotEmailInputRef.current?.focus();
      }, 100);
    }
  }, [showForgotPassword, resetSent]);

  // Email validation regex
  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Validate forgot email field
  const validateForgotEmail = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return 'Email is required';
    }
    if (trimmed.length > 254) {
      return 'Email is too long';
    }
    if (!isValidEmail(trimmed)) {
      return 'Enter a valid email address';
    }
    return '';
  };

  // Validate email field
  const validateEmail = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return 'Email is required';
    }
    if (!isValidEmail(trimmed)) {
      return 'Please enter a valid email address';
    }
    return '';
  };

  // Validate password field  
  const validatePassword = (value) => {
    if (!value) {
      return 'Password is required';
    }
    if (value.length < 8) {
      return 'Password must be at least 8 characters';
    }
    return '';
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    // Clear errors when user starts typing
    if (errors.email) {
      setErrors(prev => ({ ...prev, email: '' }));
    }
    if (loginError) {
      setLoginError('');
    }
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    // Clear errors when user starts typing
    if (errors.password) {
      setErrors(prev => ({ ...prev, password: '' }));
    }
    if (loginError) {
      setLoginError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Clear previous login error
    setLoginError('');
    
    // Validate all fields
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    
    if (emailError || passwordError) {
      setErrors({ email: emailError, password: passwordError });
      return;
    }
    
    setLoading(true);

    try {
      // Get reCAPTCHA token (always execute, backend enforces only after 3 failures)
      let captchaToken = '';
      if (failedAttempts >= 2) {
        captchaToken = await executeRecaptcha('login');
      }

      const response = await authAPI.login({ 
        email: email.trim().toLowerCase(), 
        password,
        captcha_token: captchaToken
      });
      localStorage.setItem('token', response.data.token);
      // Store user data from login response for immediate access
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
        localStorage.setItem('user_id', response.data.user.id || '');
        // Track login in Google Analytics
        analytics.trackLogin('email');
        analytics.setUserId(response.data.user.id);
        // Link anonymous session events to this user
        linkSessionToUser(response.data.user.id);
      }
      setAuth(true);
      toast.success('Login successful!');
      // Priority: 1) URL ?return= param (from 401 redirect), 2) localStorage remix_return_url, 3) /app
      const returnParam = searchParams.get('return');
      const returnUrl = returnParam || localStorage.getItem('remix_return_url');
      if (returnUrl) {
        localStorage.removeItem('remix_return_url');
        navigate(returnUrl, { replace: true });
      } else {
        navigate('/app', { replace: true });
      }
    } catch (error) {
      const status = error.response?.status;
      const message = error.response?.data?.detail || '';
      
      // Handle account lockout (HTTP 423)
      if (status === 423) {
        const errorMsg = message || 'Account temporarily locked. Please try again later.';
        setLoginError(errorMsg);
        toast.error(errorMsg);
      }
      // Handle CAPTCHA requirement
      else if (status === 400 && message.toLowerCase().includes('captcha')) {
        setLoginError('Security verification required. Please try again.');
        setFailedAttempts(prev => Math.max(prev, 3));
      }
      // Handle remaining attempts warning
      else if (message.includes('attempts remaining')) {
        setFailedAttempts(prev => prev + 1);
        setLoginError(message);
        toast.error(message);
      }
      // Generic error message to not reveal if email exists
      else {
        setFailedAttempts(prev => prev + 1);
        const errorMsg = 'Invalid email or password. Please try again.';
        setLoginError(errorMsg);
        toast.error(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    
    // Prevent double submission
    if (sendingReset) return;
    
    // Validate email
    const emailError = validateForgotEmail(forgotEmail);
    if (emailError) {
      setForgotEmailError(emailError);
      return;
    }
    
    setSendingReset(true);
    
    try {
      // Get reCAPTCHA token for forgot password
      const captchaToken = await executeRecaptcha('forgot_password');
      
      const response = await authAPI.forgotPassword({ email: forgotEmail.trim().toLowerCase() }, {
        headers: { 'X-Captcha-Token': captchaToken }
      });
      if (response.data.success) {
        setResetSent(true);
        // Don't show specific toast - show generic success in modal
      }
    } catch (error) {
      // Still show success to prevent email enumeration
      setResetSent(true);
    } finally {
      setSendingReset(false);
    }
  };

  const handleForgotEmailChange = (e) => {
    const value = e.target.value;
    setForgotEmail(value);
    // Clear error when user starts typing
    if (forgotEmailError) {
      setForgotEmailError('');
    }
  };

  const handleModalClose = (open) => {
    if (!open) {
      // Reset modal state when closing
      setForgotEmailError('');
      setResetSent(false);
      // Return focus to the forgot password link
      setTimeout(() => {
        forgotPasswordLinkRef.current?.focus();
      }, 100);
    }
    setShowForgotPassword(open);
  };

  // Check if email is valid for enabling submit button
  const isForgotEmailValid = forgotEmail.trim() && isValidEmail(forgotEmail.trim());

  // Custom input styles for dark theme with proper alignment
  const inputBaseStyles = `
    w-full h-12 rounded-lg border border-slate-600/50 
    bg-slate-800/80 text-slate-100 
    placeholder:text-slate-400
    focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 focus:outline-none
    transition-all duration-200
    text-base
  `.replace(/\s+/g, ' ').trim();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-4">
              <Sparkles className="w-8 h-8 text-indigo-500" />
              <span className="text-2xl font-bold text-white">Visionary Suite</span>
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
            <p className="text-slate-400">Login to continue creating</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
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
                  onBlur={() => setErrors(prev => ({ ...prev, email: validateEmail(email) }))}
                  aria-label="Email address"
                  aria-describedby={errors.email ? "email-error" : undefined}
                  aria-invalid={!!errors.email}
                  style={{ paddingLeft: '48px', paddingRight: '16px' }}
                  className={`${inputBaseStyles} ${errors.email ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                  placeholder="you@example.com"
                  data-testid="login-email-input"
                  autoComplete="email"
                />
              </div>
              {errors.email && (
                <p id="email-error" className="text-red-400 text-sm mt-1" role="alert">
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-slate-300 text-sm font-medium">
                  Password
                </Label>
                <button
                  ref={forgotPasswordLinkRef}
                  type="button"
                  onClick={() => {
                    setForgotEmail(email);
                    setForgotEmailError('');
                    setShowForgotPassword(true);
                    setResetSent(false);
                  }}
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors focus:outline-none focus:underline"
                  data-testid="forgot-password-link"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
                  <Lock className="w-5 h-5 text-slate-400" aria-hidden="true" />
                </span>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={handlePasswordChange}
                  onBlur={() => setErrors(prev => ({ ...prev, password: validatePassword(password) }))}
                  aria-label="Password"
                  aria-describedby={errors.password ? "password-error" : undefined}
                  aria-invalid={!!errors.password}
                  style={{ paddingLeft: '48px', paddingRight: '48px' }}
                  className={`${inputBaseStyles} ${errors.password ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                  placeholder="Enter your password"
                  data-testid="login-password-input"
                  autoComplete="current-password"
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
              {errors.password && (
                <p id="password-error" className="text-red-400 text-sm mt-1" role="alert">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Inline Login Error Message */}
            {loginError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-3" data-testid="login-error-message">
                <div className="w-5 h-5 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-red-400 text-xs font-bold">!</span>
                </div>
                <p className="text-red-400 text-sm">{loginError}</p>
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white rounded-xl py-6 text-lg shadow-lg shadow-indigo-500/20 disabled:opacity-70 disabled:cursor-not-allowed transition-all duration-200"
              data-testid="login-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Logging in...
                </>
              ) : (
                'Login'
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

            <div className="w-full mt-4 flex justify-center" data-testid="google-signin-btn">
              {/* REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH */}
              <button
                type="button"
                onClick={() => {
                  const redirectUrl = window.location.origin + '/auth/callback';
                  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
                }}
                className="w-full max-w-[380px] h-11 rounded-full border border-slate-600 bg-slate-800 hover:bg-slate-700 transition-colors flex items-center justify-center gap-3 text-sm font-medium text-white"
                data-testid="google-signin-redirect-btn"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
                  <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
                  <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                  <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 2.58 9 2.58z" fill="#EA4335"/>
                </svg>
                Sign in with Google
              </button>
            </div>
          </div>

          <div className="mt-6 text-center">
            <p className="text-slate-400">
              Don't have an account?{' '}
              <Link to="/signup" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                Sign up
              </Link>
            </p>
          </div>
        </div>
        
        {/* Back to Home */}
        <div className="text-center mt-6">
          <Link to="/" className="text-slate-500 hover:text-slate-300 transition-colors inline-flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>
      
      {/* Forgot Password Modal - Enhanced */}
      <Dialog open={showForgotPassword} onOpenChange={handleModalClose}>
        <DialogContent 
          className="bg-slate-900 border-slate-700 sm:max-w-md"
          aria-describedby="reset-password-description"
        >
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2 text-lg">
              <Lock className="w-5 h-5 text-indigo-400" aria-hidden="true" />
              Reset Password
            </DialogTitle>
            <DialogDescription id="reset-password-description" className="text-slate-400 text-sm">
              {resetSent 
                ? "If an account exists for that email, we sent a reset link."
                : "Enter your email address and we'll send you a link to reset your password."
              }
            </DialogDescription>
          </DialogHeader>
          
          {!resetSent ? (
            <form onSubmit={handleForgotPassword} className="space-y-4 py-2">
              <div className="space-y-2">
                <Label 
                  htmlFor="forgot-email" 
                  className="text-slate-300 text-sm font-medium block"
                >
                  Email Address
                </Label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
                    <Mail className="w-5 h-5 text-slate-400" aria-hidden="true" />
                  </span>
                  <input
                    ref={forgotEmailInputRef}
                    id="forgot-email"
                    type="email"
                    value={forgotEmail}
                    onChange={handleForgotEmailChange}
                    onBlur={() => {
                      if (forgotEmail.trim()) {
                        setForgotEmailError(validateForgotEmail(forgotEmail));
                      }
                    }}
                    placeholder="you@example.com"
                    style={{ paddingLeft: '48px', paddingRight: '16px' }}
                    className={`${inputBaseStyles} ${forgotEmailError ? 'border-red-500 focus:border-red-500 focus:ring-red-500/30' : ''}`}
                    aria-label="Email address for password reset"
                    aria-describedby={forgotEmailError ? "forgot-email-error" : undefined}
                    aria-invalid={!!forgotEmailError}
                    maxLength={254}
                    data-testid="forgot-email-input"
                    autoComplete="email"
                  />
                </div>
                {forgotEmailError && (
                  <p id="forgot-email-error" className="text-red-400 text-sm" role="alert">
                    {forgotEmailError}
                  </p>
                )}
              </div>
              <DialogFooter className="gap-2 pt-4 flex-col-reverse sm:flex-row">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => handleModalClose(false)} 
                  className="border-slate-700 text-slate-300 hover:bg-slate-800 w-full sm:w-auto"
                  data-testid="forgot-password-cancel"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={sendingReset || !isForgotEmailValid} 
                  className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
                  data-testid="forgot-password-submit"
                >
                  {sendingReset ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    'Send Reset Link'
                  )}
                </Button>
              </DialogFooter>
            </form>
          ) : (
            <div className="py-6 text-center">
              <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-white font-medium text-lg mb-2">Check Your Email</h3>
              <p className="text-slate-400 text-sm mb-6">
                If an account exists for <span className="text-slate-300">{forgotEmail}</span>, you'll receive a password reset link shortly.
              </p>
              <p className="text-slate-500 text-xs mb-4">
                Didn't receive the email? Check your spam folder or try again.
              </p>
              <Button 
                onClick={() => handleModalClose(false)} 
                className="bg-indigo-500 hover:bg-indigo-600"
                data-testid="back-to-login-btn"
              >
                Back to Login
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
