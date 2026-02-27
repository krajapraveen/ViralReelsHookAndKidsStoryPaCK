import React from 'react';
import { Lock, Crown, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

/**
 * PremiumLock Component
 * Overlay for premium-only styles/features
 * Shows lock icon and redirects to upgrade page
 */
export default function PremiumLock({ 
  locked = false, 
  children, 
  feature = 'style',
  unlockPlan = 'Pro'
}) {
  const navigate = useNavigate();

  const handleClick = (e) => {
    if (locked) {
      e.preventDefault();
      e.stopPropagation();
      toast.info(`Upgrade to ${unlockPlan} to unlock premium ${feature}s`);
      navigate('/app/subscription');
    }
  };

  if (!locked) {
    return children;
  }

  return (
    <div className="relative group" onClick={handleClick}>
      {children}
      
      {/* Lock Overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] rounded-lg flex flex-col items-center justify-center cursor-pointer transition-all duration-300 group-hover:bg-black/70 z-10">
        <div className="w-10 h-10 bg-yellow-500/20 rounded-full flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
          <Lock className="w-5 h-5 text-yellow-400" />
        </div>
        <span className="text-xs font-bold text-yellow-400 flex items-center gap-1">
          <Crown className="w-3 h-3" />
          {unlockPlan.toUpperCase()}
        </span>
      </div>
      
      {/* Pro Badge */}
      <div className="absolute top-1 right-1 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full z-20 flex items-center gap-0.5">
        <Crown className="w-2.5 h-2.5" />
        PRO
      </div>
    </div>
  );
}

/**
 * StyleCard with Premium Lock support
 * Use this in generator style selectors
 */
export function StyleCard({ 
  style, 
  selected, 
  onSelect, 
  isPremium = false, 
  hasAccess = true 
}) {
  const locked = isPremium && !hasAccess;

  const handleClick = () => {
    if (!locked && onSelect) {
      onSelect(style.id);
    }
  };

  return (
    <PremiumLock locked={locked} feature="style">
      <button
        onClick={handleClick}
        disabled={locked}
        className={`relative p-3 rounded-xl border-2 text-left transition-all duration-300 w-full ${
          selected
            ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
            : locked
            ? 'border-slate-700 bg-slate-800/30 opacity-80'
            : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
        }`}
      >
        {style.image && (
          <img 
            src={style.image} 
            alt={style.name}
            className={`w-full aspect-square object-cover rounded-lg mb-2 ${locked ? 'grayscale' : ''}`}
          />
        )}
        <p className={`font-medium text-sm truncate ${selected ? 'text-white' : 'text-slate-300'}`}>
          {style.name}
        </p>
        {style.description && (
          <p className="text-xs text-slate-500 truncate">{style.description}</p>
        )}
      </button>
    </PremiumLock>
  );
}

/**
 * Premium Feature Banner
 * Shows when user tries to access locked content
 */
export function PremiumBanner({ onUpgrade }) {
  return (
    <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 className="font-semibold text-white">Unlock Premium Styles</h3>
          <p className="text-sm text-slate-400">Upgrade to Pro for exclusive templates and features</p>
        </div>
      </div>
      <button
        onClick={onUpgrade}
        className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 transition-all"
      >
        Upgrade Now
      </button>
    </div>
  );
}
