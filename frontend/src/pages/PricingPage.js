import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Check, Zap, Crown, Star,
  Sparkles, Film, Loader2
} from 'lucide-react';
import api from '../utils/api';

const TOOL_COSTS = [
  { name: 'Caption / Text', credits: 1 },
  { name: 'GIF Maker', credits: 2 },
  { name: 'Photo to Comic', credits: 3 },
  { name: 'Comic Storybook', credits: 5 },
  { name: 'Story Video', credits: '8-12' },
];

const PLAN_ICONS = { weekly: Zap, monthly: Star, quarterly: Crown, yearly: Sparkles };
const PLAN_ACCENTS = { weekly: 'border-blue-500', monthly: 'border-indigo-500', quarterly: 'border-amber-500', yearly: 'border-rose-500' };

export default function PricingPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [topups, setTopups] = useState([]);
  const [currentPlan, setCurrentPlan] = useState('free');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/api/pricing-catalog/plans'),
      api.get('/api/monetization/my-limits').catch(() => ({ data: {} })),
    ]).then(([pricingRes, limitsRes]) => {
      if (pricingRes.data?.plans) setPlans(pricingRes.data.plans);
      if (pricingRes.data?.topups) setTopups(pricingRes.data.topups);
      setCurrentPlan(limitsRes.data?.plan || 'free');
    }).catch(() => toast.error('Failed to load pricing'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    );
  }

  // Add "Free" tier at the beginning
  const allPlans = [
    {
      id: 'free', name: 'Free', period: 'free', price_inr: 0,
      credits: 50, duration_days: 0, badge: null,
      features: ['50 free credits on signup', 'All tools unlocked', 'Watermarked outputs', 'Standard queue'],
    },
    ...plans,
  ];

  return (
    <div className="min-h-screen bg-slate-950" data-testid="pricing-page">
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/app" className="text-slate-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white">Pricing</h1>
            <p className="text-xs text-slate-500">Choose your creative power level</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-10">
        {/* Plans */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-16" data-testid="plans-grid">
          {allPlans.map((plan) => {
            const Icon = PLAN_ICONS[plan.period] || Zap;
            const accent = PLAN_ACCENTS[plan.period] || 'border-slate-700';
            const isCurrent = plan.id === currentPlan;
            return (
              <div
                key={plan.id}
                className={`relative bg-slate-900/60 border-2 rounded-2xl p-5 flex flex-col ${accent} ${
                  isCurrent ? 'ring-2 ring-indigo-500/50' : ''
                }`}
                data-testid={`plan-${plan.id}`}
              >
                {plan.badge && (
                  <span className="absolute -top-2.5 right-4 text-[10px] font-bold bg-indigo-600 text-white px-2.5 py-0.5 rounded-full">
                    {plan.badge}
                  </span>
                )}
                <Icon className="w-6 h-6 text-indigo-400 mb-3" />
                <h3 className="text-base font-bold text-white mb-1">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-4">
                  {plan.price_inr > 0 ? (
                    <>
                      <span className="text-2xl font-bold text-white">INR {plan.price_inr}</span>
                      <span className="text-xs text-slate-500">/{plan.period === 'weekly' ? 'wk' : plan.period === 'monthly' ? 'mo' : plan.period === 'quarterly' ? 'qtr' : 'yr'}</span>
                    </>
                  ) : (
                    <span className="text-2xl font-bold text-white">Free</span>
                  )}
                </div>
                <ul className="space-y-2 flex-1 mb-5">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                      <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  disabled={isCurrent}
                  className={`w-full text-xs font-semibold ${
                    isCurrent
                      ? 'bg-slate-700 text-slate-400 cursor-default'
                      : plan.period === 'yearly'
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                  }`}
                  data-testid={`select-plan-${plan.id}`}
                  onClick={() => {
                    if (!isCurrent && plan.price_inr > 0) navigate('/app/billing');
                  }}
                >
                  {isCurrent ? 'Current Plan' : plan.price_inr > 0 ? 'Upgrade' : 'Downgrade'}
                </Button>
              </div>
            );
          })}
        </div>

        {/* Top-ups */}
        <div className="mb-16">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" /> Credit Top-ups
          </h2>
          <p className="text-xs text-slate-500 mb-6">Need more without a subscription? Buy credits instantly.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="topups-grid">
            {topups.map((t) => (
              <div key={t.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col items-center text-center relative" data-testid={`topup-${t.id}`}>
                {t.popular && (
                  <span className="absolute -top-2.5 text-[10px] font-bold bg-amber-600 text-white px-2.5 py-0.5 rounded-full">
                    POPULAR
                  </span>
                )}
                <span className="text-3xl font-bold text-white mb-1">{t.credits}</span>
                <span className="text-xs text-slate-500 mb-3">credits</span>
                <span className="text-lg font-semibold text-white mb-4">INR {t.price_inr}</span>
                <Button
                  className="w-full bg-slate-700 hover:bg-slate-600 text-white text-xs"
                  onClick={() => navigate('/app/billing')}
                  data-testid={`buy-topup-${t.id}`}
                >
                  Buy Now
                </Button>
              </div>
            ))}
          </div>
        </div>

        {/* Credit costs table */}
        <div>
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
            <Film className="w-4 h-4 text-indigo-400" /> Credit Costs Per Tool
          </h2>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden" data-testid="credit-costs-table">
            {TOOL_COSTS.map((t, i) => (
              <div key={i} className={`flex items-center justify-between px-5 py-3 ${i > 0 ? 'border-t border-slate-800/50' : ''}`}>
                <span className="text-sm text-white">{t.name}</span>
                <span className="text-sm font-semibold text-indigo-400">{t.credits} credits</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
