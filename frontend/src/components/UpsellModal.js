import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Coins, Sparkles, X, ArrowRight, Zap } from 'lucide-react';

export default function UpsellModal({ credits, onClose }) {
  const navigate = useNavigate();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" data-testid="upsell-modal">
      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-white/10 bg-slate-900 p-8 shadow-2xl">
        <button onClick={onClose} className="absolute top-4 right-4 text-slate-500 hover:text-white" data-testid="upsell-close-btn">
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-6">
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-amber-500/20 flex items-center justify-center">
            <Coins className="w-7 h-7 text-amber-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Running Low on Credits</h2>
          <p className="text-slate-400 text-sm">
            You have <span className="text-amber-400 font-semibold">{credits ?? 0} credits</span> remaining.
            A Story Video costs ~10 credits.
          </p>
        </div>

        <div className="space-y-3 mb-6">
          <button
            onClick={() => { onClose(); navigate('/pricing'); }}
            className="w-full flex items-center gap-4 p-4 rounded-xl border-2 border-indigo-500/50 bg-indigo-500/10 hover:bg-indigo-500/20 transition-all text-left"
            data-testid="upsell-subscribe-btn"
          >
            <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-white">Subscribe — from $9/mo</p>
              <p className="text-xs text-slate-400">100 credits/mo + priority rendering</p>
            </div>
            <ArrowRight className="w-4 h-4 text-indigo-400" />
          </button>

          <button
            onClick={() => { onClose(); navigate('/pricing'); }}
            className="w-full flex items-center gap-4 p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-all text-left"
            data-testid="upsell-topup-btn"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <Zap className="w-5 h-5 text-emerald-400" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-white">Top Up Credits</p>
              <p className="text-xs text-slate-400">50 credits from $5 — use anytime</p>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <button onClick={onClose} className="w-full text-center text-sm text-slate-500 hover:text-slate-300 transition-colors" data-testid="upsell-dismiss-btn">
          Maybe later
        </button>
      </div>
    </div>
  );
}
