import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { trackFunnel } from '../utils/funnelTracker';
import { toast } from 'sonner';
import api from '../utils/api';
import {
  Sparkles, X, Crown, Check, Zap, Lock, ArrowRight, Loader2
} from 'lucide-react';

/**
 * Smart Paywall — Primary inline paywall shown over content.
 * No navigation, no page change. Fetches plans from backend.
 * Shows "Most Popular" plan highlighted, has "Continue free" soft exit.
 *
 * Props:
 *  - open: boolean
 *  - onClose: () => void
 *  - reason: 'credit_limit' | 'generation_limit' | 'post_value' | 'episode_limit'
 *  - context: { credits, limit, blurredPreview, generationCount }
 *  - triggerSource: string (where the paywall was triggered from)
 */
export function UpgradeModal({ open, isOpen, onClose, reason, context, triggerSource }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(null);

  const isVisible = open || isOpen;

  useEffect(() => {
    if (!isVisible) return;
    setLoading(true);
    api.get('/api/pricing-catalog/plans')
      .then(res => {
        if (res.data?.plans) {
          setPlans(res.data.plans);
        }
      })
      .catch(() => toast.error('Failed to load plans'))
      .finally(() => setLoading(false));

    // Track paywall view
    trackFunnel('paywall_viewed', {
      source_page: triggerSource || 'unknown',
      meta: { reason, generation_count: context?.generationCount },
    });
  }, [isVisible]);

  const handleSelectPlan = useCallback(async (plan) => {
    trackFunnel('plan_selected', {
      plan_selected: plan.id,
      source_page: triggerSource,
      meta: { price: plan.price_inr },
    });

    trackFunnel('payment_started', {
      plan_selected: plan.id,
      source_page: triggerSource,
    });

    setPurchasing(plan.id);

    try {
      const response = await api.post('/api/cashfree/create-order', {
        productId: plan.id,
        currency: 'INR',
      });

      if (!response.data.paymentSessionId) {
        toast.error('Payment configuration error.');
        setPurchasing(null);
        return;
      }

      const cashfreeEnv = response.data.environment === 'production' ? 'production' : 'sandbox';
      const cashfree = await loadCashfreeCheckout(cashfreeEnv);

      if (cashfree) {
        cashfree.checkout({
          paymentSessionId: response.data.paymentSessionId,
          redirectTarget: '_modal',
        }).then(async (result) => {
          if (result.error) {
            const msg = result.error.message || '';
            if (msg.includes('cancel') || msg.includes('closed') || msg.includes('dismiss')) {
              trackFunnel('payment_abandoned', { plan_selected: plan.id });
              toast.info('Payment cancelled. No charges made.');
            } else {
              trackFunnel('payment_abandoned', { plan_selected: plan.id, meta: { error: msg } });
              toast.error(`Payment failed: ${msg}`);
            }
          } else if (result.paymentDetails) {
            try {
              const verifyRes = await api.post('/api/cashfree/verify', { order_id: response.data.orderId });
              if (verifyRes.data.success) {
                trackFunnel('payment_success', {
                  plan_selected: plan.id,
                  meta: { order_id: response.data.orderId, credits: verifyRes.data.creditsAdded },
                });
                toast.success(`${verifyRes.data.creditsAdded} credits added!`);
                onClose();
                // Refresh the page to update credit balance
                window.dispatchEvent(new CustomEvent('credits-updated'));
              } else {
                toast.info(verifyRes.data.message || 'Processing... credits will appear shortly.');
              }
            } catch {
              toast.warning('Payment succeeded. Credits syncing — refresh in a moment.');
            }
          } else {
            trackFunnel('payment_abandoned', { plan_selected: plan.id });
            toast.info('Payment window closed. No charges made.');
          }
        }).catch(() => {
          trackFunnel('payment_abandoned', { plan_selected: plan.id });
          toast.info('Payment window closed.');
        }).finally(() => setPurchasing(null));
        return;
      } else {
        toast.error('Unable to load payment gateway.');
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Could not start payment. Try again.');
    }
    setPurchasing(null);
  }, [triggerSource, onClose]);

  const handleContinueFree = () => {
    trackFunnel('paywall_viewed', {
      source_page: triggerSource,
      meta: { action: 'continue_free' },
    });
    onClose();
  };

  if (!isVisible) return null;

  // Emotional copy based on reason
  const copy = getCopy(reason, context);

  // Sort plans: find the "most popular" one and put it in the middle
  const sortedPlans = [...plans].sort((a, b) => a.price_inr - b.price_inr);
  // Pick best 3 plans to show (skip free/cheapest, show starter/popular/pro)
  const displayPlans = sortedPlans.length > 3
    ? [sortedPlans[0], sortedPlans[1], sortedPlans[2]]
    : sortedPlans;

  // Mark middle plan as "Most Popular"
  const popularIdx = displayPlans.findIndex(p => p.badge === 'POPULAR') !== -1
    ? displayPlans.findIndex(p => p.badge === 'POPULAR')
    : Math.min(1, displayPlans.length - 1);

  return (
    <div
      className="fixed inset-0 z-[10500] flex items-center justify-center transition-all duration-300"
      data-testid="smart-paywall"
    >
      {/* Blurred backdrop */}
      <div className="absolute inset-0 bg-black/85 backdrop-blur-md" onClick={handleContinueFree} />

      <div className="relative z-10 max-w-lg w-full mx-4">
        {/* Glow */}
        <div className="absolute -inset-2 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 rounded-3xl opacity-15 blur-2xl" />

        <div className="relative bg-slate-950 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
          {/* Close */}
          <button
            onClick={handleContinueFree}
            className="absolute top-4 right-4 z-20 text-slate-500 hover:text-white transition-colors"
            data-testid="paywall-close"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Header */}
          <div className="relative px-6 pt-8 pb-4 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Crown className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-lg font-bold text-white mb-1" data-testid="paywall-title">
              {copy.title}
            </h2>
            <p className="text-sm text-slate-400">
              {copy.subtitle}
            </p>
          </div>

          {/* Plans */}
          <div className="px-4 pb-4">
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="paywall-plans">
                {displayPlans.map((plan, idx) => {
                  const isPopular = idx === popularIdx;
                  const perDay = Math.round(plan.price_inr / plan.duration_days);
                  const uiLabel = getUILabel(plan, idx, displayPlans.length);

                  return (
                    <div
                      key={plan.id}
                      className={`relative rounded-2xl p-4 transition-all cursor-pointer group ${
                        isPopular
                          ? 'bg-indigo-500/10 border-2 border-indigo-500 scale-[1.02] shadow-lg shadow-indigo-500/10'
                          : 'bg-slate-900/80 border border-slate-800 hover:border-slate-600'
                      }`}
                      onClick={() => !purchasing && handleSelectPlan(plan)}
                      data-testid={`paywall-plan-${plan.id}`}
                    >
                      {isPopular && (
                        <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-bold bg-indigo-500 text-white px-3 py-0.5 rounded-full whitespace-nowrap">
                          MOST POPULAR
                        </span>
                      )}

                      <p className="text-xs text-slate-400 font-medium mb-1">{uiLabel}</p>
                      <div className="flex items-baseline gap-1 mb-2">
                        <span className="text-2xl font-bold text-white">{plan.price_inr}</span>
                        <span className="text-[10px] text-slate-500">INR</span>
                      </div>
                      <p className="text-[10px] text-slate-500 mb-3">{perDay}/day &middot; {plan.credits} credits</p>

                      <ul className="space-y-1.5 mb-4">
                        {plan.features.slice(0, 3).map((f, fi) => (
                          <li key={fi} className="flex items-start gap-1.5 text-[11px] text-slate-400">
                            <Check className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>

                      <Button
                        className={`w-full text-xs font-semibold h-9 ${
                          isPopular
                            ? 'bg-indigo-500 hover:bg-indigo-600 text-white'
                            : 'bg-slate-800 hover:bg-slate-700 text-white border border-slate-700'
                        }`}
                        disabled={!!purchasing}
                        data-testid={`paywall-select-${plan.id}`}
                      >
                        {purchasing === plan.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <Zap className="w-3 h-3 mr-1" />
                            {isPopular ? 'Get Started' : 'Select'}
                          </>
                        )}
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Continue Free CTA */}
          <div className="px-6 pb-6 text-center">
            <button
              onClick={handleContinueFree}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors py-2"
              data-testid="paywall-continue-free"
            >
              Continue with limited access <ArrowRight className="w-3 h-3 inline ml-1" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function getCopy(reason, context) {
  switch (reason) {
    case 'post_value':
      return {
        title: 'You\'re creating something amazing',
        subtitle: 'Unlock unlimited generations to keep the flow going',
      };
    case 'credit_limit':
      return {
        title: 'Your creative energy is running low',
        subtitle: `${context?.credits ?? 0} credits left \u2014 refuel to keep creating`,
      };
    case 'generation_limit':
      return {
        title: 'You\'ve hit the free limit',
        subtitle: 'Upgrade to create without limits',
      };
    case 'episode_limit':
      return {
        title: 'Your story is just getting good...',
        subtitle: `Episode ${context?.limit || 3} reached \u2014 unlock the next chapter`,
      };
    default:
      return {
        title: 'Unlock your full creative power',
        subtitle: 'Choose a plan and create without limits',
      };
  }
}

function getUILabel(plan, idx, total) {
  // Friendly labels instead of raw plan names
  if (plan.period === 'weekly') return 'Starter';
  if (plan.period === 'monthly') return 'Creator';
  if (plan.period === 'quarterly') return 'Pro';
  if (plan.period === 'yearly') return 'Ultimate';
  return plan.name;
}

function loadCashfreeCheckout(env = 'production') {
  return new Promise((resolve) => {
    if (window.Cashfree) {
      resolve(window.Cashfree({ mode: env }));
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://sdk.cashfree.com/js/v3/cashfree.js';
    script.onload = () => {
      if (window.Cashfree) resolve(window.Cashfree({ mode: env }));
      else resolve(null);
    };
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
}

export default UpgradeModal;
