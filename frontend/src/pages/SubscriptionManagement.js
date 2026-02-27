import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  ArrowLeft, CreditCard, Calendar, CheckCircle, XCircle,
  RefreshCw, Crown, Zap, Clock, AlertCircle, ChevronRight,
  History, Award, Shield
} from 'lucide-react';
import api from '../utils/api';
import { toast } from 'sonner';

export default function SubscriptionManagement() {
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [subscriptionHistory, setSubscriptionHistory] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      const [currentRes, historyRes, plansRes] = await Promise.all([
        api.get('/api/subscriptions/current'),
        api.get('/api/subscriptions/history'),
        api.get('/api/subscriptions/plans')
      ]);
      
      setCurrentSubscription(currentRes.data.subscription);
      setSubscriptionHistory(historyRes.data.subscriptions || []);
      setPlans(plansRes.data.plans || []);
    } catch (error) {
      console.error('Failed to fetch subscription data:', error);
      toast.error('Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    setActionLoading(true);
    try {
      await api.post('/api/subscriptions/cancel', { reason: cancelReason });
      toast.success('Auto-renewal cancelled successfully');
      setShowCancelModal(false);
      fetchSubscriptionData();
    } catch (error) {
      toast.error('Failed to cancel subscription');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivate = async () => {
    setActionLoading(true);
    try {
      await api.post('/api/subscriptions/reactivate');
      toast.success('Auto-renewal reactivated!');
      fetchSubscriptionData();
    } catch (error) {
      toast.error('Failed to reactivate subscription');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'EXPIRED': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'CANCELLED': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const daysRemaining = (endDate) => {
    const end = new Date(endDate);
    const now = new Date();
    const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
    return Math.max(0, diff);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/app" className="text-slate-400 hover:text-white">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Crown className="w-8 h-8 text-yellow-400" />
              <div>
                <h1 className="text-xl font-bold text-white">Subscription</h1>
                <p className="text-xs text-slate-400">Manage your subscription plan</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Current Subscription */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-400" />
            Current Subscription
          </h2>
          
          {currentSubscription ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold text-white">
                      {currentSubscription.planDetails?.name || currentSubscription.planId}
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(currentSubscription.status)}`}>
                      {currentSubscription.status}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm">
                    {currentSubscription.planDetails?.credits || currentSubscription.creditsGranted} credits per cycle
                  </p>
                </div>
                {currentSubscription.autoRenew && currentSubscription.status === 'ACTIVE' ? (
                  <div className="flex items-center gap-2 text-green-400">
                    <RefreshCw className="w-4 h-4" />
                    <span className="text-sm">Auto-renewal on</span>
                  </div>
                ) : currentSubscription.status === 'ACTIVE' ? (
                  <div className="flex items-center gap-2 text-yellow-400">
                    <AlertCircle className="w-4 h-4" />
                    <span className="text-sm">Auto-renewal off</span>
                  </div>
                ) : null}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-400 mb-1">Start Date</p>
                  <p className="text-white font-medium">{formatDate(currentSubscription.startDate)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-400 mb-1">End Date</p>
                  <p className="text-white font-medium">{formatDate(currentSubscription.endDate)}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-400 mb-1">Days Remaining</p>
                  <p className="text-purple-400 font-bold text-xl">
                    {daysRemaining(currentSubscription.endDate)}
                  </p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-400 mb-1">Credits Granted</p>
                  <p className="text-green-400 font-bold text-xl">
                    {currentSubscription.creditsGranted}
                  </p>
                </div>
              </div>

              {/* Progress Bar */}
              {currentSubscription.status === 'ACTIVE' && (
                <div className="mb-6">
                  <div className="flex justify-between text-xs text-slate-400 mb-2">
                    <span>Progress</span>
                    <span>{daysRemaining(currentSubscription.endDate)} days left</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                      style={{ 
                        width: `${Math.min(100, ((currentSubscription.planDetails?.duration_days || 30) - daysRemaining(currentSubscription.endDate)) / (currentSubscription.planDetails?.duration_days || 30) * 100)}%` 
                      }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Actions */}
              {currentSubscription.status === 'ACTIVE' && (
                <div className="flex gap-3">
                  {currentSubscription.autoRenew ? (
                    <Button
                      onClick={() => setShowCancelModal(true)}
                      variant="outline"
                      className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                      data-testid="cancel-renewal-btn"
                    >
                      <XCircle className="w-4 h-4 mr-2" />
                      Cancel Auto-Renewal
                    </Button>
                  ) : (
                    <Button
                      onClick={handleReactivate}
                      disabled={actionLoading}
                      className="bg-green-600 hover:bg-green-700"
                      data-testid="reactivate-btn"
                    >
                      <RefreshCw className={`w-4 h-4 mr-2 ${actionLoading ? 'animate-spin' : ''}`} />
                      Reactivate Auto-Renewal
                    </Button>
                  )}
                  <Link to="/pricing">
                    <Button variant="outline" className="border-purple-500/30 text-purple-400 hover:bg-purple-500/10">
                      <Zap className="w-4 h-4 mr-2" />
                      Upgrade Plan
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center">
              <Crown className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">No Active Subscription</h3>
              <p className="text-slate-400 mb-4">Subscribe to a plan to unlock all features and get more credits.</p>
              <Link to="/pricing">
                <Button className="bg-purple-600 hover:bg-purple-700" data-testid="subscribe-btn">
                  <Zap className="w-4 h-4 mr-2" />
                  View Plans
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Available Plans */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-yellow-400" />
            Available Plans
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className={`bg-slate-900/50 border rounded-xl p-6 relative ${
                  plan.badge ? 'border-purple-500/50' : 'border-slate-800'
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <span className="bg-purple-500 text-white text-xs font-medium px-3 py-1 rounded-full">
                      {plan.badge}
                    </span>
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white mb-2">{plan.name}</h3>
                <div className="mb-4">
                  <span className="text-3xl font-bold text-white">
                    {plan.currency === 'INR' ? '₹' : '$'}{plan.price}
                  </span>
                  <span className="text-slate-400 text-sm">/{plan.durationDays} days</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features?.map((feature, idx) => (
                    <li key={idx} className="text-sm text-slate-300 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link to="/pricing">
                  <Button className="w-full bg-slate-800 hover:bg-slate-700" data-testid={`plan-${plan.id}-btn`}>
                    Select Plan
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* Subscription History */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <History className="w-5 h-5 text-blue-400" />
            Subscription History
          </h2>
          {subscriptionHistory.length > 0 ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left py-4 px-6 text-sm text-slate-400">Plan</th>
                    <th className="text-left py-4 px-6 text-sm text-slate-400">Period</th>
                    <th className="text-left py-4 px-6 text-sm text-slate-400">Credits</th>
                    <th className="text-left py-4 px-6 text-sm text-slate-400">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptionHistory.map((sub, idx) => (
                    <tr key={idx} className="border-b border-slate-800 last:border-0">
                      <td className="py-4 px-6">
                        <p className="text-white font-medium">
                          {sub.planDetails?.name || sub.planId}
                        </p>
                      </td>
                      <td className="py-4 px-6">
                        <p className="text-sm text-slate-300">
                          {formatDate(sub.startDate)} - {formatDate(sub.endDate)}
                        </p>
                      </td>
                      <td className="py-4 px-6">
                        <p className="text-green-400 font-medium">{sub.creditsGranted}</p>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(sub.status)}`}>
                          {sub.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center">
              <History className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No subscription history yet.</p>
            </div>
          )}
        </div>
      </main>

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold text-white mb-4">Cancel Auto-Renewal?</h3>
            <p className="text-slate-400 mb-4">
              Your subscription will remain active until the end date. You won't be charged again after it expires.
            </p>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Optional: Tell us why you're cancelling..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-white mb-4 h-24 resize-none"
              data-testid="cancel-reason-input"
            />
            <div className="flex gap-3">
              <Button
                onClick={() => setShowCancelModal(false)}
                variant="outline"
                className="flex-1"
              >
                Keep Subscription
              </Button>
              <Button
                onClick={handleCancelSubscription}
                disabled={actionLoading}
                className="flex-1 bg-red-600 hover:bg-red-700"
                data-testid="confirm-cancel-btn"
              >
                {actionLoading ? 'Cancelling...' : 'Confirm Cancel'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
