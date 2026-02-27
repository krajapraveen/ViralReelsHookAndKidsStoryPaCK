import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, Users, Gift, Copy, Share2, TrendingUp, 
  Crown, Medal, Award, Star, Check, Loader2,
  CreditCard, Mail, ChevronRight, Sparkles
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import api from '../utils/api';

const TIER_CONFIG = {
  bronze: { icon: Medal, color: 'text-orange-400', bg: 'bg-orange-500/20', border: 'border-orange-500/30' },
  silver: { icon: Award, color: 'text-slate-300', bg: 'bg-slate-500/20', border: 'border-slate-400/30' },
  gold: { icon: Crown, color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
  platinum: { icon: Star, color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/30' }
};

export default function ReferralProgram() {
  const [loading, setLoading] = useState(true);
  const [referralData, setReferralData] = useState(null);
  const [stats, setStats] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [giftCardOptions, setGiftCardOptions] = useState([]);
  const [myGiftCards, setMyGiftCards] = useState({ purchased: [], redeemed: [] });
  const [redeemCode, setRedeemCode] = useState('');
  const [redeemLoading, setRedeemLoading] = useState(false);
  const [purchaseLoading, setPurchaseLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [codeRes, statsRes, leaderRes, giftRes, myCardsRes] = await Promise.all([
        api.get('/api/referral/code'),
        api.get('/api/referral/stats'),
        api.get('/api/referral/leaderboard'),
        api.get('/api/referral/gift-cards/options'),
        api.get('/api/referral/gift-cards/my-cards')
      ]);
      
      setReferralData(codeRes.data);
      setStats(statsRes.data.stats || {});
      setLeaderboard(leaderRes.data.leaderboard || []);
      setGiftCardOptions(giftRes.data.denominations || []);
      setMyGiftCards(myCardsRes.data);
    } catch (e) {
      console.error('Failed to fetch referral data:', e);
    }
    setLoading(false);
  };

  const copyReferralLink = () => {
    if (referralData?.link) {
      navigator.clipboard.writeText(referralData.link);
      toast.success('Referral link copied!');
    }
  };

  const shareReferralLink = () => {
    if (navigator.share && referralData?.link) {
      navigator.share({
        title: 'Join CreatorStudio AI',
        text: `Sign up with my referral link and get ${referralData?.tier?.referee_bonus || 25} free credits!`,
        url: referralData.link
      });
    } else {
      copyReferralLink();
    }
  };

  const redeemGiftCard = async () => {
    if (!redeemCode.trim()) {
      toast.error('Please enter a gift card code');
      return;
    }
    
    setRedeemLoading(true);
    try {
      const res = await api.post('/api/referral/gift-cards/redeem', null, {
        params: { code: redeemCode }
      });
      if (res.data.success) {
        toast.success(`Redeemed ${res.data.creditsAdded} credits!`);
        setRedeemCode('');
        fetchData();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to redeem gift card');
    }
    setRedeemLoading(false);
  };

  const purchaseGiftCard = async (denomination) => {
    setPurchaseLoading(true);
    try {
      const res = await api.post('/api/referral/gift-cards/purchase', null, {
        params: { denomination: denomination.value, quantity: 1 }
      });
      if (res.data.success) {
        toast.success('Gift card purchased! Code: ' + res.data.giftCards[0].code);
        fetchData();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to purchase gift card');
    }
    setPurchaseLoading(false);
  };

  const TierIcon = TIER_CONFIG[referralData?.tier?.name || 'bronze']?.icon || Medal;
  const tierConfig = TIER_CONFIG[referralData?.tier?.name || 'bronze'];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link to="/app" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span>Dashboard</span>
              </Link>
              <div className="flex items-center gap-2">
                <Users className="w-6 h-6 text-purple-400" />
                <h1 className="text-2xl font-bold text-white">Referral & Gift Cards</h1>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Tabs defaultValue="referral" className="space-y-8">
          <TabsList className="bg-slate-800/50 border border-slate-700">
            <TabsTrigger value="referral" className="data-[state=active]:bg-purple-600">
              <Users className="w-4 h-4 mr-2" />
              Referral Program
            </TabsTrigger>
            <TabsTrigger value="giftcards" className="data-[state=active]:bg-purple-600">
              <Gift className="w-4 h-4 mr-2" />
              Gift Cards
            </TabsTrigger>
            <TabsTrigger value="leaderboard" className="data-[state=active]:bg-purple-600">
              <TrendingUp className="w-4 h-4 mr-2" />
              Leaderboard
            </TabsTrigger>
          </TabsList>

          {/* Referral Program Tab */}
          <TabsContent value="referral" className="space-y-6">
            {/* Referral Code Card */}
            <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-2xl p-6 md:p-8">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-2">Your Referral Code</h2>
                  <p className="text-slate-400 mb-4">Share your code and earn credits when friends sign up!</p>
                  <div className="flex items-center gap-3">
                    <div className="bg-slate-800 border border-slate-600 rounded-lg px-6 py-3">
                      <span className="text-2xl font-mono font-bold text-purple-400">{referralData?.code}</span>
                    </div>
                    <Button onClick={copyReferralLink} variant="outline" className="border-slate-600">
                      <Copy className="w-4 h-4 mr-2" /> Copy Link
                    </Button>
                    <Button onClick={shareReferralLink} className="bg-purple-600 hover:bg-purple-700">
                      <Share2 className="w-4 h-4 mr-2" /> Share
                    </Button>
                  </div>
                </div>
                
                {/* Tier Badge */}
                <div className={`${tierConfig.bg} ${tierConfig.border} border rounded-2xl p-6 text-center`}>
                  <TierIcon className={`w-12 h-12 mx-auto ${tierConfig.color} mb-2`} />
                  <h3 className={`text-xl font-bold capitalize ${tierConfig.color}`}>{referralData?.tier?.name || 'Bronze'}</h3>
                  <p className="text-slate-400 text-sm">{referralData?.tier?.bonus_multiplier || 1}x Bonus</p>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-slate-400 text-sm mb-1">Total Referrals</p>
                <p className="text-3xl font-bold text-white">{stats?.totalReferrals || 0}</p>
              </div>
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-slate-400 text-sm mb-1">Credits Earned</p>
                <p className="text-3xl font-bold text-green-400">{stats?.totalEarned || 0}</p>
              </div>
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-slate-400 text-sm mb-1">This Month</p>
                <p className="text-3xl font-bold text-purple-400">{stats?.monthlyReferrals || 0}</p>
              </div>
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
                <p className="text-slate-400 text-sm mb-1">Pending</p>
                <p className="text-3xl font-bold text-yellow-400">{stats?.pendingReferrals || 0}</p>
              </div>
            </div>

            {/* How It Works */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-white mb-6">How It Works</h3>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-purple-400 font-bold">1</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-white mb-1">Share Your Link</h4>
                    <p className="text-slate-400 text-sm">Send your referral code to friends via social media or email</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-purple-400 font-bold">2</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-white mb-1">Friend Signs Up</h4>
                    <p className="text-slate-400 text-sm">They create an account and make their first purchase</p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-purple-400 font-bold">3</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-white mb-1">Both Get Rewarded</h4>
                    <p className="text-slate-400 text-sm">You get 50 credits, they get 25 credits!</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Tier Progress */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-white mb-4">Tier Progress</h3>
              <div className="space-y-4">
                {Object.entries(TIER_CONFIG).map(([tierName, config]) => {
                  const Icon = config.icon;
                  const tierRequirement = { bronze: 1, silver: 5, gold: 15, platinum: 30 }[tierName];
                  const isCurrentTier = referralData?.tier?.name === tierName;
                  const isCompleted = (stats?.totalReferrals || 0) >= tierRequirement;
                  
                  return (
                    <div key={tierName} className={`flex items-center gap-4 p-3 rounded-lg ${isCurrentTier ? config.bg : ''}`}>
                      <Icon className={`w-6 h-6 ${config.color}`} />
                      <div className="flex-1">
                        <div className="flex justify-between items-center mb-1">
                          <span className={`font-medium capitalize ${isCurrentTier ? 'text-white' : 'text-slate-400'}`}>
                            {tierName}
                          </span>
                          <span className="text-sm text-slate-500">{tierRequirement}+ referrals</span>
                        </div>
                        <Progress 
                          value={Math.min(100, ((stats?.totalReferrals || 0) / tierRequirement) * 100)} 
                          className="h-2"
                        />
                      </div>
                      {isCompleted && <Check className="w-5 h-5 text-green-400" />}
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>

          {/* Gift Cards Tab */}
          <TabsContent value="giftcards" className="space-y-6">
            {/* Redeem Gift Card */}
            <div className="bg-gradient-to-r from-pink-600/20 to-purple-600/20 border border-pink-500/30 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-white mb-4">Redeem Gift Card</h3>
              <div className="flex gap-3">
                <Input
                  placeholder="Enter gift card code (e.g., GC-XXXX-XXXX)"
                  value={redeemCode}
                  onChange={(e) => setRedeemCode(e.target.value.toUpperCase())}
                  className="bg-slate-800 border-slate-600 text-white font-mono"
                />
                <Button 
                  onClick={redeemGiftCard}
                  disabled={redeemLoading}
                  className="bg-pink-600 hover:bg-pink-700 px-6"
                >
                  {redeemLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Redeem'}
                </Button>
              </div>
            </div>

            {/* Purchase Gift Cards */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-white mb-2">Purchase Gift Cards</h3>
              <p className="text-slate-400 mb-6">Send credits to friends or save for later</p>
              
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {giftCardOptions.map((option, idx) => (
                  <div 
                    key={idx}
                    className={`relative bg-slate-700/50 border rounded-xl p-5 hover:border-purple-500 transition-colors ${
                      option.badge ? 'border-yellow-500/50' : 'border-slate-600'
                    }`}
                  >
                    {option.badge && (
                      <span className="absolute -top-2 -right-2 bg-yellow-500 text-black text-xs font-bold px-2 py-1 rounded-full">
                        {option.badge}
                      </span>
                    )}
                    <div className="flex items-center justify-between mb-3">
                      <Gift className="w-8 h-8 text-purple-400" />
                      {option.discount && (
                        <span className="text-green-400 text-sm font-medium">{option.discount}</span>
                      )}
                    </div>
                    <h4 className="text-2xl font-bold text-white mb-1">{option.value} Credits</h4>
                    <p className="text-slate-400 mb-4">
                      <span className="line-through text-slate-500 mr-2">₹{option.value}</span>
                      <span className="text-white font-semibold">₹{option.price}</span>
                    </p>
                    <Button 
                      onClick={() => purchaseGiftCard(option)}
                      disabled={purchaseLoading}
                      className="w-full bg-purple-600 hover:bg-purple-700"
                    >
                      <CreditCard className="w-4 h-4 mr-2" /> Buy Now
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* My Gift Cards */}
            {(myGiftCards.purchased.length > 0 || myGiftCards.redeemed.length > 0) && (
              <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-4">My Gift Cards</h3>
                
                {myGiftCards.purchased.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-slate-400 mb-3">Purchased</h4>
                    <div className="space-y-2">
                      {myGiftCards.purchased.slice(0, 5).map((card, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Gift className="w-5 h-5 text-purple-400" />
                            <span className="font-mono text-white">{card.code}</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-slate-400">{card.value} credits</span>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              card.status === 'active' ? 'bg-green-500/20 text-green-400' :
                              card.status === 'redeemed' ? 'bg-blue-500/20 text-blue-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>
                              {card.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {myGiftCards.redeemed.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-400 mb-3">Redeemed</h4>
                    <div className="space-y-2">
                      {myGiftCards.redeemed.slice(0, 5).map((card, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <Check className="w-5 h-5 text-green-400" />
                            <span className="font-mono text-slate-400">{card.code}</span>
                          </div>
                          <span className="text-green-400">+{card.value} credits</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          {/* Leaderboard Tab */}
          <TabsContent value="leaderboard" className="space-y-6">
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
              <h3 className="text-xl font-bold text-white mb-6">Top Referrers</h3>
              
              {/* Top 3 Podium */}
              <div className="flex justify-center gap-4 mb-8">
                {leaderboard.slice(0, 3).map((leader, idx) => {
                  const positions = [1, 0, 2]; // 2nd, 1st, 3rd for visual display
                  const position = positions[idx];
                  const heights = ['h-24', 'h-32', 'h-20'];
                  const colors = ['bg-slate-400', 'bg-yellow-400', 'bg-orange-400'];
                  const tierConfig = TIER_CONFIG[leader.tier] || TIER_CONFIG.bronze;
                  const TierIcon = tierConfig.icon;
                  
                  return (
                    <div key={idx} className="text-center" style={{ order: position }}>
                      <div className={`w-8 h-8 ${tierConfig.bg} rounded-full flex items-center justify-center mx-auto mb-2`}>
                        <TierIcon className={`w-4 h-4 ${tierConfig.color}`} />
                      </div>
                      <p className="font-medium text-white mb-2 truncate max-w-[100px]">{leader.name}</p>
                      <div className={`${heights[idx]} w-20 ${colors[idx]}/20 rounded-t-lg flex items-end justify-center pb-2`}>
                        <span className={`text-2xl font-bold ${colors[idx].replace('bg-', 'text-')}`}>#{position + 1}</span>
                      </div>
                      <p className="text-sm text-slate-400 mt-1">{leader.totalReferrals} referrals</p>
                    </div>
                  );
                })}
              </div>
              
              {/* Full List */}
              <div className="space-y-2">
                {leaderboard.slice(3).map((leader, idx) => {
                  const tierConfig = TIER_CONFIG[leader.tier] || TIER_CONFIG.bronze;
                  const TierIcon = tierConfig.icon;
                  
                  return (
                    <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div className="flex items-center gap-4">
                        <span className="w-8 text-center text-slate-500 font-medium">#{idx + 4}</span>
                        <TierIcon className={`w-5 h-5 ${tierConfig.color}`} />
                        <span className="text-white">{leader.name}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-slate-400">{leader.totalReferrals} referrals</span>
                        <span className="text-green-400 font-medium">{leader.totalEarned} cr</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
