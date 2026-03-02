import React, { useState, useEffect } from 'react';
import { Gift, Flame, Star, Trophy, X, CheckCircle, Lock } from 'lucide-react';
import { Button } from './ui/button';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DailyRewardsModal({ isOpen, onClose }) {
  const [loading, setLoading] = useState(true);
  const [claiming, setClaiming] = useState(false);
  const [rewardData, setRewardData] = useState(null);
  const [claimed, setClaimed] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchRewardStatus();
    }
  }, [isOpen]);

  const fetchRewardStatus = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    
    try {
      const response = await fetch(`${API_URL}/api/daily-rewards/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setRewardData(data);
        setClaimed(!data.can_claim);
      }
    } catch (error) {
      console.error('Failed to fetch reward status:', error);
    } finally {
      setLoading(false);
    }
  };

  const claimReward = async () => {
    setClaiming(true);
    const token = localStorage.getItem('token');
    
    try {
      const response = await fetch(`${API_URL}/api/daily-rewards/claim`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setClaimed(true);
        toast.success(`🎉 Claimed ${data.reward.total_credits} credits!`);
        
        // Update local storage or trigger refresh
        if (data.reward.streak_bonus > 0) {
          toast.success(`🔥 Streak Bonus: +${data.reward.streak_bonus} credits!`);
        }
        
        // Refresh status
        fetchRewardStatus();
      } else {
        toast.error('Already claimed today!');
      }
    } catch (error) {
      toast.error('Failed to claim reward');
    } finally {
      setClaiming(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="daily-rewards-modal">
      <div className="relative w-full max-w-md bg-gradient-to-b from-slate-900 to-slate-950 rounded-3xl border border-white/10 overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* Close button */}
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-white/60 hover:text-white z-10"
          data-testid="close-rewards-modal"
        >
          <X className="w-6 h-6" />
        </button>

        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 via-pink-500 to-purple-500 p-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Gift className="w-8 h-8 text-white" />
            <h2 className="text-2xl font-bold text-white">Daily Rewards</h2>
          </div>
          <p className="text-white/90 text-sm">Login daily to earn free credits!</p>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : rewardData ? (
            <>
              {/* Streak Info */}
              <div className="flex items-center justify-center gap-6 mb-6">
                <div className="text-center">
                  <div className="flex items-center gap-1 text-orange-400">
                    <Flame className="w-5 h-5" />
                    <span className="text-2xl font-bold">{rewardData.current_streak}</span>
                  </div>
                  <p className="text-xs text-slate-400">Current Streak</p>
                </div>
                <div className="h-8 w-px bg-white/10"></div>
                <div className="text-center">
                  <div className="flex items-center gap-1 text-yellow-400">
                    <Trophy className="w-5 h-5" />
                    <span className="text-2xl font-bold">{rewardData.longest_streak}</span>
                  </div>
                  <p className="text-xs text-slate-400">Best Streak</p>
                </div>
                <div className="h-8 w-px bg-white/10"></div>
                <div className="text-center">
                  <div className="flex items-center gap-1 text-green-400">
                    <Star className="w-5 h-5" />
                    <span className="text-2xl font-bold">{rewardData.total_rewards_claimed}</span>
                  </div>
                  <p className="text-xs text-slate-400">Total Earned</p>
                </div>
              </div>

              {/* Weekly Progress */}
              <div className="grid grid-cols-7 gap-2 mb-6">
                {rewardData.weekly_progress?.map((day, index) => (
                  <div 
                    key={index}
                    className={`relative p-2 rounded-xl text-center transition-all ${
                      day.claimed 
                        ? 'bg-green-500/20 border border-green-500/50' 
                        : day.is_today 
                          ? 'bg-gradient-to-b from-orange-500/30 to-pink-500/30 border-2 border-orange-500 animate-pulse' 
                          : 'bg-white/5 border border-white/10'
                    }`}
                  >
                    <p className="text-[10px] text-slate-400 mb-1">Day {day.day}</p>
                    <p className={`font-bold ${day.claimed ? 'text-green-400' : day.is_today ? 'text-orange-400' : 'text-white'}`}>
                      +{day.credits}
                    </p>
                    {day.claimed && (
                      <CheckCircle className="absolute -top-1 -right-1 w-4 h-4 text-green-500" />
                    )}
                    {!day.claimed && !day.is_today && index > rewardData.current_streak % 7 && (
                      <Lock className="absolute -top-1 -right-1 w-3 h-3 text-slate-500" />
                    )}
                  </div>
                ))}
              </div>

              {/* Today's Reward */}
              <div className={`p-4 rounded-2xl text-center mb-6 ${
                claimed 
                  ? 'bg-green-500/20 border border-green-500/50' 
                  : 'bg-gradient-to-r from-orange-500/20 to-pink-500/20 border border-orange-500/50'
              }`}>
                {claimed ? (
                  <>
                    <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-2" />
                    <p className="text-green-400 font-bold text-lg">Today's Reward Claimed!</p>
                    <p className="text-slate-400 text-sm">Come back tomorrow for more</p>
                  </>
                ) : (
                  <>
                    <p className="text-slate-400 text-sm mb-1">{rewardData.today_reward?.label}</p>
                    <p className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-pink-400">
                      +{rewardData.today_reward?.total}
                    </p>
                    <p className="text-white text-sm">credits waiting for you!</p>
                    {rewardData.today_reward?.streak_bonus > 0 && (
                      <p className="text-orange-400 text-xs mt-1">
                        Includes +{rewardData.today_reward.streak_bonus} streak bonus! 🔥
                      </p>
                    )}
                  </>
                )}
              </div>

              {/* Claim Button */}
              {!claimed && (
                <Button
                  onClick={claimReward}
                  disabled={claiming}
                  className="w-full bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white py-6 text-lg font-bold rounded-xl"
                  data-testid="claim-reward-btn"
                >
                  {claiming ? (
                    <span className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Claiming...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Gift className="w-5 h-5" />
                      Claim {rewardData.today_reward?.total} Credits
                    </span>
                  )}
                </Button>
              )}

              {/* Streak Milestones */}
              <div className="mt-6 pt-4 border-t border-white/10">
                <p className="text-xs text-slate-400 text-center mb-3">Streak Milestones</p>
                <div className="flex justify-between text-xs">
                  {rewardData.streak_bonuses?.map((milestone, i) => (
                    <div key={i} className={`text-center ${milestone.achieved ? 'text-green-400' : 'text-slate-500'}`}>
                      <p className="font-bold">{milestone.label}</p>
                      <p>+{milestone.bonus}</p>
                      {milestone.achieved && <CheckCircle className="w-3 h-3 mx-auto mt-1" />}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-center text-slate-400">Failed to load rewards</p>
          )}
        </div>
      </div>
    </div>
  );
}
