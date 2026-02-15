import React from 'react';
import { MousePointerClick, PieChart, Users } from 'lucide-react';

function formatFeatureName(name) {
  if (!name) return 'Unknown';
  return name
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function FeaturesTab({ featureUsage }) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Top Features */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <MousePointerClick className="w-5 h-5 text-purple-400" />
          Most Used Features
        </h3>
        <div className="space-y-3">
          {featureUsage?.topFeatures?.map((feature, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="w-6 h-6 flex items-center justify-center bg-purple-500/20 text-purple-400 rounded-full text-xs font-bold">
                {i + 1}
              </span>
              <span className="text-sm text-slate-300 flex-1">{formatFeatureName(feature.feature)}</span>
              <span className="text-sm font-medium text-purple-400">{feature.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Usage Percentage */}
      <div className="bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <PieChart className="w-5 h-5 text-indigo-400" />
          Usage Distribution
        </h3>
        <div className="space-y-3">
          {featureUsage?.featurePercentages?.slice(0, 8).map((feature, i) => (
            <div key={i}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{formatFeatureName(feature.feature)}</span>
                <span className="text-slate-400">{feature.percentage}%</span>
              </div>
              <div className="h-2 bg-slate-600 rounded-full">
                <div 
                  className="h-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
                  style={{ width: `${feature.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Unique Users per Feature */}
      <div className="md:col-span-2 bg-slate-700/50 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Users className="w-5 h-5 text-blue-400" />
          Unique Users per Feature
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {featureUsage?.uniqueUsersPerFeature?.slice(0, 8).map((feature, i) => (
            <div key={i} className="text-center p-3 bg-slate-600/50 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">{feature.uniqueUsers}</div>
              <div className="text-xs text-slate-400 mt-1">{formatFeatureName(feature.feature)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
