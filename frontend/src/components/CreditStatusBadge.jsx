import React, { useState, useEffect } from 'react';
import { Coins, AlertTriangle, Gift, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import api from '../utils/api';

export default function CreditStatusBadge({ credits, onCreditsUpdate }) {
  const [status, setStatus] = useState('normal');
  const [dailyRewardAvailable, setDailyRewardAvailable] = useState(false);
  const [showRewardModal, setShowRewardModal] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    checkStatus();
    checkDailyReward();
  }, [credits]);

  const checkStatus = async () => {
    try {
      const res = await api.get('/api/monetization/credit-status');
      if (res.data.success) {
        setStatus(res.data.status);
      }
    } catch (error) {
      console.error('Failed to check credit status:', error);
    }
  };

  const checkDailyReward = async () => {
    try {
      const res = await api.get('/api/monetization/daily-reward/status');
      if (res.data.success) {
        setDailyRewardAvailable(!res.data.claimed_today);
      }
    } catch (error) {
      console.error('Failed to check daily reward:', error);
    }
  };

  const claimDailyReward = async () => {
    setClaiming(true);
    try {
      const res = await api.post('/api/monetization/daily-reward/claim');
      if (res.data.success) {
        toast.success(res.data.message);
        setDailyRewardAvailable(false);
        if (onCreditsUpdate) {
          onCreditsUpdate(res.data.new_balance);
        }
      } else {
        toast.info(res.data.message);
      }
    } catch (error) {
      toast.error('Failed to claim reward');
    } finally {
      setClaiming(false);
      setShowRewardModal(false);
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'critical':
        return 'text-red-400 bg-red-500/20 border-red-500/50';
      case 'low':
        return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50';
      default:
        return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/50';
    }
  };

  return (
    <>
      <div className="flex items-center gap-2">
        {/* Daily Reward Button */}
        {dailyRewardAvailable && (
          <button
            onClick={() => setShowRewardModal(true)}
            className="relative p-2 rounded-lg bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 hover:border-yellow-500/50 transition-all animate-pulse"
            title="Claim daily reward!"
          >
            <Gift className="w-5 h-5 text-yellow-400" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-500 rounded-full animate-ping" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-500 rounded-full" />
          </button>
        )}

        {/* Credit Balance */}
        <button
          onClick={() => navigate('/app/billing')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all hover:scale-105 ${getStatusColor()}`}
        >
          <Coins className="w-4 h-4" />
          <span className="font-semibold">{credits?.toLocaleString() || 0}</span>
          {status === 'critical' && (
            <AlertTriangle className="w-4 h-4 text-red-400 animate-bounce" />
          )}
        </button>

        {/* Low Credit Warning */}
        {(status === 'low' || status === 'critical') && (
          <Button
            size="sm"
            onClick={() => navigate('/app/billing')}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-xs"
          >
            Top Up
          </Button>
        )}
      </div>

      {/* Daily Reward Modal */}
      {showRewardModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-sm overflow-hidden">
            <div className="bg-gradient-to-r from-yellow-500 to-orange-500 p-6 text-center">
              <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Gift className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">Daily Reward!</h2>
              <p className="text-white/80">Claim your free credits</p>
            </div>
            
            <div className="p-6 text-center">
              <div className="text-4xl font-bold text-white mb-2">+3</div>
              <p className="text-slate-400 mb-6">Free credits</p>
              
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1 border-slate-600"
                  onClick={() => setShowRewardModal(false)}
                >
                  Later
                </Button>
                <Button
                  className="flex-1 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                  onClick={claimDailyReward}
                  disabled={claiming}
                >
                  {claiming ? 'Claiming...' : 'Claim Now'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
