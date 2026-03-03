import React, { useState } from 'react';
import { Mail, Clock, AlertTriangle, Send, CheckCircle, X } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * Email Verification Required Banner
 * Shows when user hasn't verified their email and credits are locked
 */
const EmailVerificationBanner = ({ user, onVerified }) => {
  const [sending, setSending] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Don't show if email is verified or user dismissed
  if (!user || user.emailVerified || dismissed) {
    return null;
  }

  // Check if credits are locked
  const creditsLocked = user.credits_locked || user.credits === 0;
  const pendingCredits = user.pending_credits || 20;

  const handleResendVerification = async () => {
    setSending(true);
    try {
      const response = await api.post('/api/auth/resend-verification');
      if (response.data.success) {
        toast.success('Verification email sent! Check your inbox.', { duration: 5000 });
      } else {
        toast.info(response.data.message);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send verification email');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-amber-900/40 to-orange-900/40 border-2 border-amber-500/50 rounded-xl p-4 mb-6 relative animate-pulse-slow">
      <button 
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-amber-300/50 hover:text-amber-200 p-1"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
      
      <div className="flex items-start gap-4">
        <div className="p-3 bg-amber-500/20 rounded-xl border border-amber-500/30">
          <AlertTriangle className="w-8 h-8 text-amber-400" />
        </div>
        
        <div className="flex-1">
          <h3 className="text-amber-200 font-bold text-lg flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Email Verification Required
          </h3>
          
          <p className="text-amber-100/80 text-sm mt-2">
            Your <span className="font-bold text-amber-300">{pendingCredits} free credits</span> are locked until you verify your email address.
          </p>
          
          <div className="flex items-center gap-2 mt-2 text-amber-200/60 text-xs">
            <Clock className="w-4 h-4" />
            <span>Verify within 24 hours or lose access to your credits</span>
          </div>
          
          <div className="mt-4 flex items-center gap-3">
            <Button
              onClick={handleResendVerification}
              disabled={sending}
              className="bg-amber-600 hover:bg-amber-500 text-white border-0"
              size="sm"
            >
              {sending ? (
                <>
                  <Send className="w-4 h-4 mr-2 animate-pulse" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Resend Verification Email
                </>
              )}
            </Button>
            
            <span className="text-amber-200/50 text-xs">
              Check your inbox and spam folder
            </span>
          </div>
        </div>
        
        {/* Locked Credits Visual */}
        <div className="hidden sm:flex flex-col items-center justify-center p-4 bg-amber-500/10 rounded-xl border border-amber-500/20">
          <div className="text-3xl font-bold text-amber-400">🔒</div>
          <div className="text-amber-300 font-bold text-lg">{pendingCredits}</div>
          <div className="text-amber-200/60 text-xs">Credits Locked</div>
        </div>
      </div>
      
      {/* Progress Steps */}
      <div className="mt-4 pt-4 border-t border-amber-500/20">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-white" />
            </div>
            <span className="text-green-400">Account Created</span>
          </div>
          
          <div className="flex-1 h-0.5 mx-3 bg-amber-500/30">
            <div className="h-full w-1/2 bg-amber-500 animate-pulse"></div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-amber-500/30 border-2 border-amber-500 flex items-center justify-center animate-pulse">
              <Mail className="w-3 h-3 text-amber-400" />
            </div>
            <span className="text-amber-400 font-medium">Verify Email</span>
          </div>
          
          <div className="flex-1 h-0.5 mx-3 bg-gray-600"></div>
          
          <div className="flex items-center gap-2 opacity-50">
            <div className="w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center">
              <span className="text-xs text-gray-400">🎁</span>
            </div>
            <span className="text-gray-400">Get Credits</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailVerificationBanner;
