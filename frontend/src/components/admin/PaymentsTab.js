import React from 'react';
import { CreditCard, TrendingUp, AlertCircle, BarChart3 } from 'lucide-react';

export default function PaymentsTab({ payments }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Transaction Summary */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-emerald-400" />
          Transaction Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-white">{payments?.totalTransactions || 0}</div>
            <div className="text-sm text-slate-400">Total</div>
          </div>
          <div className="text-center p-4 bg-green-500/10 rounded-lg">
            <div className="text-3xl font-bold text-green-400">{payments?.successfulTransactions || 0}</div>
            <div className="text-sm text-slate-400">Successful</div>
          </div>
          <div className="text-center p-4 bg-red-500/10 rounded-lg">
            <div className="text-3xl font-bold text-red-400">{payments?.failedTransactions || 0}</div>
            <div className="text-sm text-slate-400">Failed</div>
          </div>
          <div className="text-center p-4 bg-yellow-500/10 rounded-lg">
            <div className="text-3xl font-bold text-yellow-400">{payments?.pendingTransactions || 0}</div>
            <div className="text-sm text-slate-400">Pending</div>
          </div>
        </div>
        <div className="mt-4 p-4 bg-slate-600/50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-slate-300">Success Rate</span>
            <span className="text-2xl font-bold text-green-400">{payments?.successRate || 0}%</span>
          </div>
        </div>
      </div>

      {/* Subscription Plans */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          Subscriptions by Plan
        </h3>
        <div className="space-y-3">
          {payments?.planBreakdown?.map((plan, i) => (
            <div key={i} className="p-3 bg-slate-600/50 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium">{plan.productName}</span>
                <span className="text-purple-400 font-bold">{plan.count} sales</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                Revenue: ₹{plan.revenue}
              </div>
            </div>
          ))}
          {(!payments?.planBreakdown || payments.planBreakdown.length === 0) && (
            <div className="text-center text-slate-400 py-4">No subscription data yet</div>
          )}
        </div>
      </div>

      {/* Failure Reasons */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          Failed Transaction Reasons
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {payments?.failureReasons?.map((reason, i) => (
            <div key={i} className="text-center p-4 bg-red-500/10 rounded-lg">
              <div className="text-2xl font-bold text-red-400">{reason.count || 0}</div>
              <div className="text-xs text-slate-400 mt-1">{reason.reason}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Daily Revenue Trend */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          Daily Revenue Trend
        </h3>
        <div className="space-y-2">
          {payments?.dailyRevenueTrend?.slice(-10).map((day, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-24">{day.date}</span>
              <div className="flex-1 bg-slate-600 rounded-full h-4">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-green-400 h-4 rounded-full"
                  style={{ width: `${Math.min((Number(day.revenue) / 10000) * 100, 100)}%` }}
                />
              </div>
              <span className="text-sm text-emerald-400 w-20 text-right">₹{day.revenue}</span>
              <span className="text-xs text-slate-500 w-16 text-right">{day.count} txn</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
