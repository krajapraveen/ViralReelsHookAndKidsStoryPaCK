import React from 'react';
import { Monitor, Smartphone, Globe } from 'lucide-react';

export default function VisitorsTab({ visitors }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Visitor Summary */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Visitor Summary</h3>
        <div className="space-y-4">
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Unique Visitors</span>
            <span className="text-xl font-bold">{visitors?.uniqueVisitors || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Total Page Views</span>
            <span className="text-xl font-bold">{visitors?.totalPageViews || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Anonymous Visitors</span>
            <span className="text-xl font-bold">{visitors?.anonymousVisitors || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-slate-600/50 rounded-lg">
            <span className="text-slate-300">Logged-in Users</span>
            <span className="text-xl font-bold">{visitors?.loggedInVisitors || 0}</span>
          </div>
        </div>
      </div>

      {/* Page Views */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4">Top Pages</h3>
        <div className="space-y-2">
          {visitors?.pageViews?.slice(0, 8).map((page, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm text-slate-300 flex-1 truncate">{page.page || 'Home'}</span>
              <span className="text-sm font-medium text-purple-400">{page.views}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Device Distribution */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Monitor className="w-5 h-5 text-blue-400" />
          Device Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(visitors?.deviceDistribution || {}).map(([device, count], i) => (
            <div key={i} className="flex items-center gap-3">
              {device === 'Desktop' ? <Monitor className="w-4 h-4 text-slate-400" /> :
               device === 'Mobile' ? <Smartphone className="w-4 h-4 text-slate-400" /> :
               <Globe className="w-4 h-4 text-slate-400" />}
              <span className="text-sm text-slate-300 flex-1">{device}</span>
              <span className="text-sm font-medium">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Browser Distribution */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-green-400" />
          Browser Distribution
        </h3>
        <div className="space-y-3">
          {Object.entries(visitors?.browserDistribution || {}).map(([browser, count], i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm text-slate-300 flex-1">{browser}</span>
              <span className="text-sm font-medium">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
