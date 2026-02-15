import React from 'react';

const colorClasses = {
  blue: 'bg-blue-500/20 text-blue-400',
  green: 'bg-green-500/20 text-green-400',
  purple: 'bg-purple-500/20 text-purple-400',
  indigo: 'bg-indigo-500/20 text-indigo-400',
  emerald: 'bg-emerald-500/20 text-emerald-400',
  yellow: 'bg-yellow-500/20 text-yellow-400',
  red: 'bg-red-500/20 text-red-400',
};

export default function StatCard({ icon, label, value, subValue, color }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${colorClasses[color]}`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
      {subValue && <div className="text-xs text-slate-500 mt-1">{subValue}</div>}
    </div>
  );
}
