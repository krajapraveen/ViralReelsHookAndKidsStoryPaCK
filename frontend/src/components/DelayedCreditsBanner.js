import React, { useState, useEffect } from 'react';
import { Gift, Clock, Sparkles, X } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

/**
 * Delayed Credits Banner
 * Shows pending bonus credits and allows claiming
 */
const DelayedCreditsBanner = ({ onCreditsAdded }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await api.get('/api/anti-abuse/delayed-credits/status');
      if (response.data.success) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch delayed credits status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClaim = async () => {
    setClaiming(true);
    try {
      const response = await api.post('/api/anti-abuse/delayed-credits/claim');
      if (response.data.success && response.data.credits_released > 0) {
        toast.success(response.data.message, { duration: 5000 });
        if (onCreditsAdded) {
          onCreditsAdded(response.data.new_balance);
        }
        fetchStatus(); // Refresh status
      } else {
        toast.info(response.data.message);
      }
    } catch (error) {
      toast.error('Failed to claim credits. Please try again.');
    } finally {
      setClaiming(false);
    }
  };

  // Don't show if loading, dismissed, or no delayed credits
  if (loading || dismissed || !status?.has_delayed_credits || status?.pending === 0) {
    return null;
  }

  const nextRelease = status.next_release;
  const nextReleaseDate = nextRelease ? new Date(nextRelease.date) : null;
  const isClaimable = nextReleaseDate && nextReleaseDate <= new Date();

  return (
    <div className="bg-gradient-to-r from-emerald-900/30 to-teal-900/30 border border-emerald-500/30 rounded-xl p-4 mb-6 relative">
      <button 
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-slate-400 hover:text-white p-1"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
      
      <div className="flex items-start gap-4">
        <div className="p-3 bg-emerald-500/20 rounded-xl">
          <Gift className="w-6 h-6 text-emerald-400" />
        </div>
        
        <div className="flex-1">
          <h3 className="text-emerald-300 font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Bonus Credits Pending!
          </h3>
          
          <p className="text-slate-400 text-sm mt-1">
            You have <span className="text-emerald-400 font-bold">{status.pending} credits</span> waiting to be released.
            {status.released > 0 && (
              <span className="text-slate-500"> ({status.released} already released)</span>
            )}
          </p>
          
          {nextRelease && (
            <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              {isClaimable ? (
                <span className="text-emerald-400">
                  {nextRelease.credits} credits available to claim now!
                </span>
              ) : (
                <span>
                  Next release: {nextRelease.credits} credits on {nextReleaseDate.toLocaleDateString()}
                </span>
              )}
            </div>
          )}
        </div>
        
        {isClaimable && (
          <Button
            onClick={handleClaim}
            disabled={claiming}
            className="bg-emerald-600 hover:bg-emerald-500 text-white"
            size="sm"
          >
            {claiming ? (
              <>
                <Sparkles className="w-4 h-4 mr-2 animate-spin" />
                Claiming...
              </>
            ) : (
              <>
                <Gift className="w-4 h-4 mr-2" />
                Claim Now
              </>
            )}
          </Button>
        )}
      </div>
      
      {/* Progress bar */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Progress</span>
          <span>{status.released}/{status.total_delayed} credits released</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-500"
            style={{ width: `${(status.released / status.total_delayed) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default DelayedCreditsBanner;
