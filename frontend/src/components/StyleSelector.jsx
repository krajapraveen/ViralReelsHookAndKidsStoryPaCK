import React, { useState, useEffect } from 'react';
import { Lock, Crown, Check, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

export default function StyleSelector({ feature, selectedStyle, onStyleSelect }) {
  const [styles, setStyles] = useState([]);
  const [userPlan, setUserPlan] = useState('free');
  const [hasPremiumAccess, setHasPremiumAccess] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchStyles();
  }, [feature]);

  const fetchStyles = async () => {
    try {
      const res = await api.get(`/api/monetization/styles/${feature}`);
      if (res.data.success) {
        setStyles(res.data.styles);
        setUserPlan(res.data.user_plan);
        setHasPremiumAccess(res.data.has_premium_access);
      }
    } catch (error) {
      console.error('Failed to fetch styles:', error);
    }
  };

  const handleStyleClick = (style) => {
    if (style.locked && !style.can_access) {
      setShowUpgradeModal(true);
      return;
    }
    onStyleSelect(style.id);
  };

  // Separate free and premium styles
  const freeStyles = styles.filter(s => !s.premium);
  const premiumStyles = styles.filter(s => s.premium);

  return (
    <div className="space-y-4">
      {/* Free Styles */}
      <div>
        <h3 className="text-sm font-medium text-slate-400 mb-2">Basic Styles</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {freeStyles.map(style => (
            <button
              key={style.id}
              onClick={() => handleStyleClick(style)}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedStyle === style.id
                  ? 'border-purple-500 bg-purple-500/20 text-white'
                  : 'border-slate-700 hover:border-slate-600 text-slate-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {selectedStyle === style.id && (
                  <Check className="w-4 h-4 text-purple-400" />
                )}
                <span className="text-sm">{style.name}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Premium Styles */}
      {premiumStyles.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Crown className="w-4 h-4 text-yellow-500" />
            <h3 className="text-sm font-medium text-slate-400">Pro Styles</h3>
            {!hasPremiumAccess && (
              <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full">
                Pro Only
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {premiumStyles.map(style => {
              const isLocked = style.locked && !style.can_access;
              
              return (
                <button
                  key={style.id}
                  onClick={() => handleStyleClick(style)}
                  className={`p-3 rounded-lg border text-left transition-all relative ${
                    isLocked
                      ? 'border-slate-700 bg-slate-800/50 opacity-80'
                      : selectedStyle === style.id
                      ? 'border-yellow-500 bg-yellow-500/20 text-white'
                      : 'border-slate-700 hover:border-yellow-500/50 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {isLocked ? (
                      <Lock className="w-4 h-4 text-slate-500" />
                    ) : selectedStyle === style.id ? (
                      <Check className="w-4 h-4 text-yellow-400" />
                    ) : (
                      <Sparkles className="w-4 h-4 text-yellow-500" />
                    )}
                    <span className="text-sm">{style.name}</span>
                  </div>
                  
                  {isLocked && (
                    <div className="absolute top-1 right-1">
                      <Lock className="w-3 h-3 text-slate-600" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Upgrade Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <Crown className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Unlock Pro Styles</h2>
              <p className="text-slate-400 mb-6">
                Upgrade to Pro to access premium styles, watermark-free outputs, and more!
              </p>
              
              <div className="bg-slate-800 rounded-lg p-4 mb-6">
                <div className="text-2xl font-bold text-white mb-1">
                  ₹1,499<span className="text-sm text-slate-400">/month</span>
                </div>
                <ul className="text-sm text-slate-400 space-y-1">
                  <li>✓ 800 credits/month</li>
                  <li>✓ All premium styles</li>
                  <li>✓ Watermark-free outputs</li>
                  <li>✓ Commercial license</li>
                </ul>
              </div>
              
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1 border-slate-600"
                  onClick={() => setShowUpgradeModal(false)}
                >
                  Maybe Later
                </Button>
                <Button
                  className="flex-1 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                  onClick={() => {
                    setShowUpgradeModal(false);
                    navigate('/app/billing');
                  }}
                >
                  Upgrade Now
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
