import React from 'react';
import { BarChart3, PieChart, Users, CreditCard } from 'lucide-react';

export default function OverviewTab({ visitors, generations, recentActivity }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Daily Visitors Chart */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" />
          Daily Visitors
        </h3>
        <div className="space-y-2">
          {visitors?.dailyTrend?.slice(-7).map((day, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-20">{day.date}</span>
              <div className="flex-1 bg-slate-600 rounded-full h-4">
                <div 
                  className="bg-purple-500 h-4 rounded-full"
                  style={{ width: `${Math.min((day.visitors / (visitors?.uniqueVisitors || 1)) * 500, 100)}%` }}
                />
              </div>
              <span className="text-sm text-slate-300 w-12 text-right">{day.visitors}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Generation Stats */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5 text-indigo-400" />
          Generation Stats
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-indigo-400">{generations?.reelGenerations || 0}</div>
            <div className="text-sm text-slate-400">Reel Scripts</div>
          </div>
          <div className="text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-3xl font-bold text-purple-400">{generations?.storyGenerations || 0}</div>
            <div className="text-sm text-slate-400">Story Videos</div>
          </div>
          <div className="col-span-2 text-center p-4 bg-slate-600/50 rounded-lg">
            <div className="text-2xl font-bold text-green-400">{generations?.creditsUsed || 0}</div>
            <div className="text-sm text-slate-400">Credits Used</div>
          </div>
        </div>
      </div>

      {/* Recent Users */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-blue-400" />
          Recent Users
        </h3>
        <div className="space-y-2">
          {recentActivity?.recentUsers?.slice(0, 5).map((user, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <div>
                <div className="text-sm font-medium">{user.name}</div>
                <div className="text-xs text-slate-400">{user.email}</div>
              </div>
              <div className="text-xs text-slate-500">{new Date(user.createdAt).toLocaleDateString()}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Payments */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <CreditCard className="w-5 h-5 text-emerald-400" />
          Recent Payments
        </h3>
        <div className="space-y-2">
          {recentActivity?.recentPayments?.slice(0, 5).map((payment, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-slate-600/50 rounded-lg">
              <div>
                <div className="text-sm font-medium">₹{payment.amount}</div>
                <div className="text-xs text-slate-400">{payment.product || payment.productName}</div>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                payment.status === 'PAID' ? 'bg-green-500/20 text-green-400' :
                payment.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>
                {payment.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
