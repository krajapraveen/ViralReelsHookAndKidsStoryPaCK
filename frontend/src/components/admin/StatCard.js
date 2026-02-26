import React from 'react';
import { AlertTriangle } from 'lucide-react';

const colorClasses = {
  blue: 'bg-blue-500/20 text-blue-400',
  green: 'bg-green-500/20 text-green-400',
  purple: 'bg-purple-500/20 text-purple-400',
  indigo: 'bg-indigo-500/20 text-indigo-400',
  emerald: 'bg-emerald-500/20 text-emerald-400',
  yellow: 'bg-yellow-500/20 text-yellow-400',
  red: 'bg-red-500/20 text-red-400',
};

export default function StatCard({ icon, label, value, subValue, color, hasError = false }) {
  return (
    <div className={`bg-slate-800 border rounded-xl p-4 relative ${hasError ? 'border-amber-500/30' : 'border-slate-700'}`}>
      {hasError && (
        <div className="absolute top-2 right-2">
          <AlertTriangle className="w-4 h-4 text-amber-400/60" />
        </div>
      )}
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${colorClasses[color]}`}>
        {icon}
      </div>
      <div className={`text-2xl font-bold ${hasError ? 'text-slate-500' : 'text-white'}`}>{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
      {subValue && <div className={`text-xs mt-1 ${hasError ? 'text-amber-400/60' : 'text-slate-500'}`}>{subValue}</div>}
    </div>
  );
}
