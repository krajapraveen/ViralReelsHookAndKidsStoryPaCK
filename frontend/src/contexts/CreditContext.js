import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

const CreditContext = createContext(null);

const PAID_PLANS = ['weekly', 'monthly', 'quarterly', 'yearly', 'starter', 'creator', 'pro', 'premium', 'enterprise', 'admin', 'demo'];

export function CreditProvider({ children }) {
  const [credits, setCredits] = useState(null);
  const [plan, setPlan] = useState('free');
  const [isFreeTier, setIsFreeTier] = useState(false);
  const [creditsLoaded, setCreditsLoaded] = useState(false);

  const fetchCredits = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setCreditsLoaded(true);
      return;
    }
    try {
      const res = await api.get('/api/credits/balance');
      const data = res.data;
      setCredits(data.balance ?? data.credits ?? 0);
      setPlan(data.plan || 'free');
      setIsFreeTier(data.isFreeTier ?? (data.plan === 'free' || !PAID_PLANS.includes(data.plan?.toLowerCase())));
    } catch {
      setCredits(0);
    } finally {
      setCreditsLoaded(true);
    }
  }, []);

  useEffect(() => {
    fetchCredits();
  }, [fetchCredits]);

  const refreshCredits = useCallback(() => {
    setCreditsLoaded(false);
    return fetchCredits();
  }, [fetchCredits]);

  return (
    <CreditContext.Provider value={{ credits, plan, isFreeTier, creditsLoaded, refreshCredits }}>
      {children}
    </CreditContext.Provider>
  );
}

export function useCredits() {
  const ctx = useContext(CreditContext);
  if (!ctx) throw new Error('useCredits must be used within CreditProvider');
  return ctx;
}
