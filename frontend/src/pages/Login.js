import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { authAPI } from '../utils/api';
import { toast } from 'sonner';
import { Sparkles, Eye, EyeOff, Loader2, ArrowLeft, Mail, Lock, CheckCircle2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';

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
  const forgotEmailInputRef = useRef(null);
  const forgotPasswordLinkRef = useRef(null);
  const navigate = useNavigate();

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
    // Clear error when user starts typing
    if (errors.email) {
      setErrors(prev => ({ ...prev, email: '' }));
    }
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    // Clear error when user starts typing
    if (errors.password) {
      setErrors(prev => ({ ...prev, password: '' }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate all fields
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    
    if (emailError || passwordError) {
      setErrors({ email: emailError, password: passwordError });
      return;
    }
    
    setLoading(true);

    try {
      const response = await authAPI.login({ email: email.trim().toLowerCase(), password });
      localStorage.setItem('token', response.data.token);
      // Store user data from login response for immediate access
      if (response.data.user) {
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      setAuth(true);
      toast.success('Login successful!');
      navigate('/app', { replace: true });
    } catch (error) {
      const status = error.response?.status;
      const message = error.response?.data?.detail || '';
      
      // Handle account lockout (HTTP 423)
      if (status === 423) {
        toast.error(message || 'Account temporarily locked. Please try again later.');
      }
      // Handle remaining attempts warning
      else if (message.includes('attempts remaining')) {
        toast.error(message);
      }
      // Generic error message to not reveal if email exists
      else {
        toast.error('Invalid email or password. Please try again.');
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
      const response = await authAPI.forgotPassword({ email: forgotEmail.trim().toLowerCase() });
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

  const handleGoogleSignIn = () => {
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
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
              <span className="text-2xl font-bold text-white">CreatorStudio AI</span>
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

            <Button
              type="button"
              onClick={handleGoogleSignIn}
              className="w-full mt-4 bg-white hover:bg-gray-100 text-gray-900 rounded-xl py-6 text-lg flex items-center justify-center gap-3"
              data-testid="google-signin-btn"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign in with Google
            </Button>
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
