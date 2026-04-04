import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import {
  ArrowLeft, Check, Zap, Crown, Star,
  Sparkles, Film, BookOpen, Loader2
} from 'lucide-react';
import api from '../utils/api';

const PLANS = [
  {
    id: 'free', name: 'Free', price: 0, period: '',
    icon: Zap, accent: 'border-slate-700',
    features: [
      '50 free credits on signup',
      'All tools unlocked',
      'Watermarked outputs',
      'Standard queue',
    ],
  },
  {
    id: 'weekly', name: 'Weekly', price: 149, period: '/wk',
    icon: Zap, accent: 'border-blue-500',
    features: [
      '40 credits per week',
      'All core tools unlocked',
      'Standard support',
    ],
  },
  {
    id: 'monthly', name: 'Monthly', price: 499, period: '/mo',
    icon: Star, accent: 'border-indigo-500', badge: 'POPULAR',
    features: [
      '200 credits per month',
      'All core tools unlocked',
      'Priority generation',
      'HD downloads',
    ],
  },
  {
    id: 'quarterly', name: 'Quarterly', price: 1199, period: '/qtr',
    icon: Crown, accent: 'border-amber-500', badge: 'BEST VALUE',
    features: [
      '750 credits per quarter',
      'Faster generation queue',
      'Bonus styles / packs',
      'All core tools unlocked',
    ],
  },
  {
    id: 'yearly', name: 'Yearly', price: 3999, period: '/yr',
    icon: Sparkles, accent: 'border-rose-500', badge: 'BEST DEAL',
    features: [
      '3,000 credits per year',
      'Highest priority',
      'Early feature access',
      'Best value',
      'All core tools unlocked',
    ],
  },
];

const TOPUPS = [
  { id: 'topup_40', credits: 40, price: 99 },
  { id: 'topup_120', credits: 120, price: 249, badge: 'POPULAR' },
  { id: 'topup_300', credits: 300, price: 499, badge: 'BEST VALUE' },
  { id: 'topup_700', credits: 700, price: 999 },
];

const TOOL_COSTS = [
  { name: 'Caption / Text', credits: 1, icon: '1' },
  { name: 'GIF Maker', credits: 2, icon: '2' },
  { name: 'Photo to Comic', credits: 3, icon: '3' },
  { name: 'Comic Storybook', credits: 5, icon: '5' },
  { name: 'Story Video', credits: '8-12', icon: '10' },
];

export default function PricingPage() {
  const navigate = useNavigate();
  const [currentPlan, setCurrentPlan] = useState('free');

  useEffect(() => {
    api.get('/api/monetization/my-limits').then(r => {
      setCurrentPlan(r.data.plan || 'free');
    }).catch(() => {});
  }, []);

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
          {PLANS.map((plan) => {
            const Icon = plan.icon;
            const isCurrent = plan.id === currentPlan;
            return (
              <div
                key={plan.id}
                className={`relative bg-slate-900/60 border-2 rounded-2xl p-5 flex flex-col ${plan.accent} ${
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
                  {plan.price > 0 ? (
                    <>
                      <span className="text-2xl font-bold text-white">INR {plan.price}</span>
                      <span className="text-xs text-slate-500">{plan.period}</span>
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
                      : plan.id === 'yearly'
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                  }`}
                  data-testid={`select-plan-${plan.id}`}
                  onClick={() => {
                    if (!isCurrent) navigate('/app/billing');
                  }}
                >
                  {isCurrent ? 'Current Plan' : plan.price > 0 ? 'Upgrade' : 'Downgrade'}
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
            {TOPUPS.map((t) => (
              <div key={t.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col items-center text-center relative" data-testid={`topup-${t.id}`}>
                {t.badge && (
                  <span className="absolute -top-2.5 text-[10px] font-bold bg-amber-600 text-white px-2.5 py-0.5 rounded-full">
                    {t.badge}
                  </span>
                )}
                <span className="text-3xl font-bold text-white mb-1">{t.credits}</span>
                <span className="text-xs text-slate-500 mb-3">credits</span>
                <span className="text-lg font-semibold text-white mb-4">INR {t.price}</span>
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
                <span className="text-sm font-semibold text-indigo-400">{t.credits} credit{typeof t.credits === 'number' && t.credits !== 1 ? 's' : 's'}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
