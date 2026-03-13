import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { paymentAPI } from '../utils/api';
import { toast } from 'sonner';
import { Check, Sparkles, ArrowLeft, Loader2, Zap, Film, Star } from 'lucide-react';

export default function Pricing() {
  const [products, setProducts] = useState({});
  const [loading, setLoading] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await paymentAPI.getProducts();
      const data = response.data.products;
      if (data && typeof data === 'object') {
        setProducts(data);
      }
    } catch {
      // Not authenticated or API issue, show static pricing
    }
  };

  const handlePurchase = (productId) => {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('Please login to purchase');
      navigate('/login');
      return;
    }
    navigate('/app/billing');
  };

  // Subscription plans (static fallback + dynamic)
  const subscriptionPlans = [
    {
      id: 'creator_monthly',
      name: 'Creator',
      price: '$9',
      priceNote: '/month',
      credits: products.creator_monthly?.credits || 100,
      popular: true,
      features: ['5 Story Videos/mo', 'All animation styles', 'Priority rendering', 'Email support'],
    },
    {
      id: 'pro_monthly',
      name: 'Pro',
      price: '$19',
      priceNote: '/month',
      credits: products.pro_monthly?.credits || 250,
      popular: false,
      badge: 'BEST VALUE',
      features: ['12+ Story Videos/mo', 'All animation styles', 'Priority rendering', 'No watermark', 'Gallery featured', 'Priority support'],
    },
  ];

  const topUpPacks = [
    { id: 'topup_small', name: '50 Credits', price: '$5', credits: 50 },
    { id: 'topup_medium', name: '150 Credits', price: '$12', credits: 150, popular: true },
    { id: 'topup_large', name: '500 Credits', price: '$30', credits: 500 },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <Link to="/">
          <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-white/[0.06] mb-8" data-testid="pricing-back-btn">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Button>
        </Link>

        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-6 py-2 mb-6">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="text-indigo-400 text-sm font-medium">Simple, Transparent Pricing</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">Choose Your Plan</h1>
          <p className="text-lg text-slate-300 max-w-2xl mx-auto">
            Start with 10 free credits. Subscribe for monthly credits or top up as you go.
          </p>
        </div>

        {/* Free Tier */}
        <div className="mb-16">
          <div className="max-w-md mx-auto bg-white/[0.03] border border-white/[0.08] rounded-2xl p-8 text-center">
            <h3 className="text-xl font-bold text-white mb-2">Free Tier</h3>
            <div className="text-5xl font-black text-white mb-1">10</div>
            <p className="text-slate-400 mb-6">free credits on signup</p>
            <ul className="space-y-2 mb-6 text-left max-w-xs mx-auto">
              <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400 flex-shrink-0" /> 1 Story Video</li>
              <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400 flex-shrink-0" /> 1 Reel Script</li>
              <li className="flex items-center gap-2 text-sm text-slate-300"><Check className="w-4 h-4 text-emerald-400 flex-shrink-0" /> All features unlocked</li>
            </ul>
            <Link to="/signup">
              <Button className="bg-white/[0.06] hover:bg-white/10 text-white border border-white/[0.1] rounded-full px-8 py-3 font-medium" data-testid="pricing-free-btn">
                Get Started Free
              </Button>
            </Link>
          </div>
        </div>

        {/* Monthly Subscriptions */}
        <div className="mb-16">
          <h2 className="text-2xl font-bold text-white text-center mb-2">Monthly Subscriptions</h2>
          <p className="text-slate-400 text-center mb-8">Best value — credits renew every month</p>

          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {subscriptionPlans.map((plan) => (
              <div
                key={plan.id}
                className={`relative flex flex-col rounded-2xl p-8 transition-all ${
                  plan.popular
                    ? 'border-2 border-indigo-500/50 bg-indigo-500/[0.05]'
                    : 'border border-white/[0.08] bg-white/[0.02]'
                }`}
                data-testid={`plan-${plan.id}`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-4 py-1 rounded-full">POPULAR</div>
                )}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-black text-xs font-bold px-4 py-1 rounded-full">{plan.badge}</div>
                )}
                <h3 className="text-2xl font-bold text-white mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-4xl font-black text-white">{plan.price}</span>
                  <span className="text-slate-400">{plan.priceNote}</span>
                </div>
                <p className="text-indigo-300 text-sm mb-6">{plan.credits} credits/month</p>
                <ul className="space-y-2.5 mb-8 flex-1">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-slate-300">
                      <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <Button
                  onClick={() => handlePurchase(plan.id)}
                  disabled={loading[plan.id]}
                  className={`w-full rounded-full py-3 font-semibold transition-all ${
                    plan.popular
                      ? 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-[0_0_24px_-4px_rgba(99,102,241,0.5)]'
                      : 'bg-white/[0.06] hover:bg-white/10 text-white border border-white/[0.1]'
                  }`}
                  data-testid={`subscribe-${plan.id}-btn`}
                >
                  {loading[plan.id] ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Processing...</> : 'Subscribe Now'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Top-Ups */}
        <div className="mb-16">
          <h2 className="text-2xl font-bold text-white text-center mb-2">Credit Top-Ups</h2>
          <p className="text-slate-400 text-center mb-8">One-time purchase — credits never expire</p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
            {topUpPacks.map((pack) => (
              <div
                key={pack.id}
                className={`flex flex-col items-center rounded-2xl p-6 transition-all ${
                  pack.popular
                    ? 'border-2 border-emerald-500/40 bg-emerald-500/[0.05]'
                    : 'border border-white/[0.08] bg-white/[0.02]'
                }`}
                data-testid={`topup-${pack.id}`}
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3">
                  <Zap className="w-6 h-6 text-emerald-400" />
                </div>
                <h3 className="text-lg font-bold text-white mb-1">{pack.credits} Credits</h3>
                <p className="text-2xl font-black text-white mb-4">{pack.price}</p>
                {pack.popular && <span className="text-xs text-emerald-400 font-medium mb-3">Most Popular</span>}
                <Button
                  onClick={() => handlePurchase(pack.id)}
                  disabled={loading[pack.id]}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-full py-2.5 font-medium text-sm"
                  data-testid={`buy-${pack.id}-btn`}
                >
                  {loading[pack.id] ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Buy Now'}
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Usage Guide */}
        <div className="bg-white/[0.03] border border-white/[0.08] rounded-2xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 text-center">How Credits Work</h3>
          <div className="grid sm:grid-cols-3 gap-6">
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
                <Film className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold text-sm mb-1">Story Video</h4>
                <p className="text-slate-400 text-xs">~10-20 credits per video depending on scene count</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold text-sm mb-1">Reel Scripts</h4>
                <p className="text-slate-400 text-xs">10 credits per reel with hooks, captions & hashtags</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-lg bg-pink-500/20 flex items-center justify-center flex-shrink-0">
                <Star className="w-5 h-5 text-pink-400" />
              </div>
              <div>
                <h4 className="text-white font-semibold text-sm mb-1">Other Tools</h4>
                <p className="text-slate-400 text-xs">Photo to Comic, GIFs, Storybooks — 10-20 credits each</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
