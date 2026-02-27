import React, { useState, useEffect } from 'react';
import { Layers, Sparkles, Check, TrendingUp } from 'lucide-react';
import api from '../utils/api';

export default function VariationSelector({ 
  baseCredits, 
  selectedVariation, 
  onVariationSelect,
  // Support alternative prop names from different generators
  baseCost,
  value,
  onChange
}) {
  // Use alternative prop names if main ones not provided
  const credits = baseCredits ?? baseCost ?? 10;
  const selected = selectedVariation ?? value ?? 'single';
  const onSelect = onVariationSelect ?? onChange;
  const [variations, setVariations] = useState(null);

  useEffect(() => {
    fetchVariations();
  }, []);

  const fetchVariations = async () => {
    try {
      const res = await api.get('/api/monetization/variations');
      if (res.data.success) {
        setVariations(res.data.variations);
      }
    } catch (error) {
      console.error('Failed to fetch variations:', error);
    }
  };

  if (!variations) return null;

  const calculateTotalCost = (variationType) => {
    const variation = variations[variationType];
    return credits + variation.extra_credits;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Layers className="w-4 h-4" />
        <span>Output Variations</span>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {Object.entries(variations).map(([key, variation]) => {
          const isSelected = selectedVariation === key;
          const totalCost = calculateTotalCost(key);
          
          return (
            <button
              key={key}
              onClick={() => onVariationSelect(key)}
              className={`relative p-3 rounded-xl border text-left transition-all ${
                isSelected
                  ? 'border-purple-500 bg-purple-500/20'
                  : 'border-slate-700 hover:border-slate-600'
              }`}
            >
              {/* Badge */}
              {variation.badge && (
                <span className={`absolute -top-2 -right-2 text-xs px-2 py-0.5 rounded-full ${
                  variation.badge === 'BEST VALUE' 
                    ? 'bg-green-500 text-white' 
                    : variation.badge === 'POPULAR'
                    ? 'bg-purple-500 text-white'
                    : 'bg-yellow-500 text-black'
                }`}>
                  {variation.badge}
                </span>
              )}
              
              <div className="flex items-center gap-2 mb-1">
                {isSelected ? (
                  <Check className="w-4 h-4 text-purple-400" />
                ) : (
                  <Sparkles className="w-4 h-4 text-slate-500" />
                )}
                <span className={`font-semibold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                  {variation.label}
                </span>
              </div>
              
              <div className="text-sm">
                <span className={`font-bold ${isSelected ? 'text-purple-400' : 'text-slate-400'}`}>
                  {totalCost}
                </span>
                <span className="text-slate-500 ml-1">credits</span>
              </div>
              
              {variation.count > 1 && (
                <div className="text-xs text-green-400 mt-1 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  Save {Math.round((1 - totalCost / (baseCredits * variation.count)) * 100)}%
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
