import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  CreditCard, Crown, Check, X, Loader2, ChevronRight, 
  Sparkles, Zap, Star, Calendar, Receipt, AlertCircle,
  ArrowRight, Shield, Clock, Gift, Wallet
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import api from '../utils/api';

export default function SubscriptionManagement() {
  const [loading, setLoading] = useState(true);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [plans, setPlans] = useState([]);
  const [payments, setPayments] = useState([]);
  const [credits, setCredits] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [currentRes, plansRes, paymentsRes] = await Promise.all([
        api.get('/api/subscriptions/recurring/current'),
        api.get('/api/subscriptions/recurring/plans'),
        api.get('/api/subscriptions/payments').catch(() => ({ data: { payments: [] } }))
      ]);

      if (currentRes.data.success) {
        setCurrentPlan(currentRes.data.current_plan);
        setSubscription(currentRes.data.subscription);
        setCredits(currentRes.data.credits || 0);
      }

      if (plansRes.data.success) {
        setPlans(plansRes.data.plans);
      }

      setPayments(paymentsRes.data.payments || []);
    } catch (error) {
      console.error('Failed to load subscription data:', error);
      toast.error('Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (planKey) => {
    setActionLoading(true);
    try {
      const res = await api.post('/api/subscriptions/recurring/create', {
        plan_key: planKey
      });

      if (res.data.success && res.data.payment_link) {
        toast.success('Redirecting to payment...');
        window.location.href = res.data.payment_link;
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Failed to create subscription');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will lose premium benefits at the end of your billing period.')) {
      return;
    }

    setActionLoading(true);
    try {
      const res = await api.post('/api/subscriptions/recurring/cancel');
      if (res.data.success) {
        toast.success('Subscription cancelled successfully');
        fetchData();
      }
    } catch (error) {
      toast.error('Failed to cancel subscription');
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangePlan = async (newPlanKey) => {
    if (!confirm(`Are you sure you want to change to the ${newPlanKey} plan?`)) {
      return;
    }

    setActionLoading(true);
    try {
      const res = await api.post(`/api/subscriptions/recurring/change-plan?new_plan_key=${newPlanKey}`);
      if (res.data.success && res.data.payment_link) {
        toast.success('Redirecting to payment for new plan...');
        window.location.href = res.data.payment_link;
      }
    } catch (error) {
      toast.error('Failed to change plan');
    } finally {
      setActionLoading(false);
    }
  };

  const getPlanIcon = (key) => {
    const icons = { creator: Sparkles, pro: Crown, studio: Star };
    return icons[key] || Sparkles;
  };

  const getPlanColor = (key) => {
    const colors = {
      creator: 'from-blue-500 to-cyan-500',
      pro: 'from-purple-500 to-pink-500',
      studio: 'from-yellow-500 to-orange-500'
    };
    return colors[key] || 'from-slate-500 to-slate-600';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-purple-500" />
      </div>
    );
  }

  const isPaid = currentPlan && currentPlan !== 'free' && currentPlan !== 'demo';
  const currentPlanDetails = plans.find(p => p.key === currentPlan);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950/30 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/app" className="flex items-center gap-3">
            <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
              ← Back to Dashboard
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-800/50 rounded-full px-4 py-2 border border-slate-700">
              <Wallet className="w-4 h-4 text-purple-400" />
              <span className="font-bold text-white">{credits}</span>
              <span className="text-xs text-slate-400">credits</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Page Title */}
        <div className="text-center mb-10">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">Subscription Management</h1>
          <p className="text-slate-400">Manage your plan, view payment history, and upgrade anytime</p>
        </div>

        {/* Current Plan Card */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Crown className="w-5 h-5 text-purple-400" />
            Current Plan
          </h2>
          
          {isPaid && currentPlanDetails ? (
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${getPlanColor(currentPlan)} flex items-center justify-center shadow-lg`}>
                  {React.createElement(getPlanIcon(currentPlan), { className: "w-8 h-8 text-white" })}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{currentPlanDetails.name}</h3>
                  <p className="text-slate-400">{currentPlanDetails.description}</p>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span className="text-purple-400 font-semibold">₹{currentPlanDetails.price_inr}/month</span>
                    <span className="text-emerald-400">{currentPlanDetails.discount_percent}% discount</span>
                    <span className="text-cyan-400">{currentPlanDetails.credits_per_cycle} credits/month</span>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="border-red-500/50 text-red-400 hover:bg-red-500/20"
                  onClick={handleCancel}
                  disabled={actionLoading}
                >
                  Cancel Subscription
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-slate-700 flex items-center justify-center">
                  <Zap className="w-8 h-8 text-slate-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">Free Plan</h3>
                  <p className="text-slate-400">Basic access with watermarked outputs</p>
                </div>
              </div>
              <Button
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                onClick={() => document.getElementById('plans-section').scrollIntoView({ behavior: 'smooth' })}
              >
                Upgrade Now
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}

          {/* Subscription Status */}
          {subscription && (
            <div className="mt-4 pt-4 border-t border-slate-700/50">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div className="bg-slate-900/50 rounded-xl p-3">
                  <span className="text-slate-400 block">Status</span>
                  <span className={`font-semibold ${subscription.status === 'ACTIVE' ? 'text-emerald-400' : 'text-yellow-400'}`}>
                    {subscription.status}
                  </span>
                </div>
                {subscription.next_billing_at && (
                  <div className="bg-slate-900/50 rounded-xl p-3">
                    <span className="text-slate-400 block">Next Billing</span>
                    <span className="text-white font-semibold">
                      {new Date(subscription.next_billing_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
                <div className="bg-slate-900/50 rounded-xl p-3">
                  <span className="text-slate-400 block">Credits This Cycle</span>
                  <span className="text-purple-400 font-semibold">{currentPlanDetails?.credits_per_cycle || 0}</span>
                </div>
                <div className="bg-slate-900/50 rounded-xl p-3">
                  <span className="text-slate-400 block">Total Payments</span>
                  <span className="text-white font-semibold">{subscription.total_payments || 0}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Available Plans */}
        <div id="plans-section" className="mb-8">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Gift className="w-5 h-5 text-purple-400" />
            {isPaid ? 'Change Plan' : 'Choose a Plan'}
          </h2>
          
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => {
              const Icon = getPlanIcon(plan.key);
              const isCurrentPlan = currentPlan === plan.key;
              
              return (
                <div
                  key={plan.key}
                  className={`relative bg-slate-800/30 border rounded-2xl overflow-hidden transition-all duration-300 ${
                    isCurrentPlan 
                      ? 'border-purple-500 ring-2 ring-purple-500/30' 
                      : plan.popular 
                      ? 'border-purple-500/50' 
                      : 'border-slate-700/50 hover:border-slate-600'
                  }`}
                >
                  {plan.popular && !isCurrentPlan && (
                    <div className="absolute top-0 left-0 right-0 bg-purple-500 text-white text-xs font-bold text-center py-1">
                      MOST POPULAR
                    </div>
                  )}
                  {isCurrentPlan && (
                    <div className="absolute top-0 left-0 right-0 bg-emerald-500 text-white text-xs font-bold text-center py-1">
                      CURRENT PLAN
                    </div>
                  )}
                  
                  <div className={`p-6 ${(plan.popular || isCurrentPlan) ? 'pt-10' : ''}`}>
                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${getPlanColor(plan.key)} flex items-center justify-center mb-4 shadow-lg`}>
                      <Icon className="w-7 h-7 text-white" />
                    </div>
                    
                    <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
                    <p className="text-slate-400 text-sm mb-4">{plan.description}</p>
                    
                    <div className="mb-4">
                      <span className="text-3xl font-bold text-white">₹{plan.price_inr}</span>
                      <span className="text-slate-400">/month</span>
                    </div>
                    
                    <div className="space-y-2 mb-6">
                      {plan.features.map((feature, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          <span className="text-slate-300">{feature}</span>
                        </div>
                      ))}
                    </div>
                    
                    {isCurrentPlan ? (
                      <Button disabled className="w-full bg-slate-700 text-slate-400">
                        Current Plan
                      </Button>
                    ) : isPaid ? (
                      <Button
                        className={`w-full bg-gradient-to-r ${getPlanColor(plan.key)}`}
                        onClick={() => handleChangePlan(plan.key)}
                        disabled={actionLoading}
                      >
                        {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Switch to {plan.name}
                      </Button>
                    ) : (
                      <Button
                        className={`w-full bg-gradient-to-r ${getPlanColor(plan.key)}`}
                        onClick={() => handleSubscribe(plan.key)}
                        disabled={actionLoading}
                      >
                        {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                        Subscribe Now
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Payment History */}
        <div className="bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Receipt className="w-5 h-5 text-purple-400" />
            Payment History
          </h2>
          
          {payments.length > 0 ? (
            <div className="space-y-3">
              {payments.slice(0, 10).map((payment, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl border border-slate-700/50"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <Check className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">Subscription Payment</p>
                      <p className="text-sm text-slate-400">
                        {new Date(payment.created_at).toLocaleDateString()} • 
                        +{payment.credits_added || 0} credits
                      </p>
                    </div>
                  </div>
                  <span className="font-bold text-white">₹{payment.amount || 0}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Receipt className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400">No payment history yet</p>
              <p className="text-sm text-slate-500">Your subscription payments will appear here</p>
            </div>
          )}
        </div>

        {/* FAQ Section */}
        <div className="mt-8 bg-slate-800/30 border border-slate-700/50 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Frequently Asked Questions</h2>
          <div className="space-y-4">
            <div className="border-b border-slate-700/50 pb-4">
              <h3 className="font-semibold text-white mb-2">When do I get my credits?</h3>
              <p className="text-slate-400 text-sm">Credits are added immediately after each successful payment and refresh every month on your billing date.</p>
            </div>
            <div className="border-b border-slate-700/50 pb-4">
              <h3 className="font-semibold text-white mb-2">Can I change my plan anytime?</h3>
              <p className="text-slate-400 text-sm">Yes! You can upgrade or downgrade your plan anytime. Changes take effect at your next billing cycle.</p>
            </div>
            <div>
              <h3 className="font-semibold text-white mb-2">What happens if I cancel?</h3>
              <p className="text-slate-400 text-sm">You'll keep your premium benefits until the end of your billing period. After that, you'll be moved to the free plan.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
