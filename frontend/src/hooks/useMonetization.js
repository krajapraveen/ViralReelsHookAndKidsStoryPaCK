/**
 * Monetization Integration Hook
 * Provides monetization features (variations, upsells, watermarks, premium locks) to generators
 */
import { useState, useEffect, useCallback } from 'react';
import api from '../utils/api';
import { toast } from 'sonner';

export function useMonetization(feature) {
  const [variations, setVariations] = useState(null);
  const [upsells, setUpsells] = useState(null);
  const [styles, setStyles] = useState([]);
  const [userPlan, setUserPlan] = useState('free');
  const [hasPremiumAccess, setHasPremiumAccess] = useState(false);
  const [watermarkRequired, setWatermarkRequired] = useState(true);
  const [selectedVariation, setSelectedVariation] = useState('single');
  const [showUpsellModal, setShowUpsellModal] = useState(false);
  const [lastGenerationId, setLastGenerationId] = useState(null);

  useEffect(() => {
    fetchMonetizationData();
  }, [feature]);

  const fetchMonetizationData = async () => {
    try {
      // Fetch in parallel
      const [variationsRes, upsellsRes, watermarkRes, stylesRes] = await Promise.all([
        api.get('/api/monetization/variations').catch(() => null),
        api.get('/api/monetization/upsells').catch(() => null),
        api.get('/api/monetization/watermark-status').catch(() => null),
        feature ? api.get(`/api/monetization/styles/${feature}`).catch(() => null) : null
      ]);

      if (variationsRes?.data?.success) {
        setVariations(variationsRes.data.variations);
      }

      if (upsellsRes?.data?.success) {
        setUpsells(upsellsRes.data.upsells);
      }

      if (watermarkRes?.data?.success) {
        setWatermarkRequired(watermarkRes.data.add_watermark);
        setUserPlan(watermarkRes.data.plan || 'free');
      }

      if (stylesRes?.data?.success) {
        setStyles(stylesRes.data.styles || []);
        setHasPremiumAccess(stylesRes.data.has_premium_access || false);
        setUserPlan(stylesRes.data.user_plan || 'free');
      }
    } catch (error) {
      console.error('Failed to fetch monetization data:', error);
    }
  };

  const calculateTotalCost = useCallback((baseCost) => {
    if (!variations || !selectedVariation) return baseCost;
    const variation = variations[selectedVariation];
    return baseCost + (variation?.extra_credits || 0);
  }, [variations, selectedVariation]);

  const triggerUpsellModal = useCallback((generationId) => {
    setLastGenerationId(generationId);
    setShowUpsellModal(true);
  }, []);

  const closeUpsellModal = useCallback(() => {
    setShowUpsellModal(false);
  }, []);

  const checkStyleAccess = useCallback((styleId) => {
    const style = styles.find(s => s.id === styleId);
    if (!style) return true;
    if (!style.premium) return true;
    return hasPremiumAccess;
  }, [styles, hasPremiumAccess]);

  const getLockedStyles = useCallback(() => {
    return styles.filter(s => s.premium && !hasPremiumAccess);
  }, [styles, hasPremiumAccess]);

  const getFreeStyles = useCallback(() => {
    return styles.filter(s => !s.premium);
  }, [styles]);

  const getPremiumStyles = useCallback(() => {
    return styles.filter(s => s.premium);
  }, [styles]);

  return {
    // State
    variations,
    upsells,
    styles,
    userPlan,
    hasPremiumAccess,
    watermarkRequired,
    selectedVariation,
    showUpsellModal,
    lastGenerationId,
    
    // Setters
    setSelectedVariation,
    
    // Actions
    calculateTotalCost,
    triggerUpsellModal,
    closeUpsellModal,
    checkStyleAccess,
    getLockedStyles,
    getFreeStyles,
    getPremiumStyles,
    refreshData: fetchMonetizationData
  };
}

/**
 * Premium Style Lock Component
 * Locks 50% of styles for non-Pro users
 */
export function PremiumLock({ locked, onUpgrade }) {
  if (!locked) return null;
  
  return (
    <div 
      className="absolute inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center rounded-lg cursor-pointer z-10"
      onClick={onUpgrade}
    >
      <div className="text-center">
        <div className="w-8 h-8 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-1">
          <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <span className="text-xs text-yellow-400 font-medium">PRO</span>
      </div>
    </div>
  );
}

/**
 * Watermark Overlay Component
 * Shows diagonal watermark text for free users
 */
export function WatermarkOverlay({ visible, text = "CREATORSTUDIO AI" }) {
  if (!visible) return null;
  
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-20">
      <div 
        className="absolute inset-0 flex items-center justify-center"
        style={{ transform: 'rotate(-30deg)' }}
      >
        <div className="whitespace-nowrap text-white/15 text-2xl font-bold tracking-wider select-none">
          {Array(5).fill(text).join('    ')}
        </div>
      </div>
    </div>
  );
}

export default useMonetization;
