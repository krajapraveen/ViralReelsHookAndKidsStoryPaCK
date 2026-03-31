import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../utils/api';

const MediaEntitlementContext = createContext({
  canDownload: false,
  upgradeRequired: true,
  planType: 'free',
  loading: true,
  refresh: () => {},
});

export function MediaEntitlementProvider({ children }) {
  const [entitlement, setEntitlement] = useState({
    canDownload: false,
    upgradeRequired: true,
    planType: 'free',
    watermarkRequired: true,
    loading: true,
  });

  const fetchEntitlement = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setEntitlement(prev => ({ ...prev, loading: false }));
      return;
    }
    try {
      const res = await api.get('/api/media/entitlement');
      if (res.data.success) {
        setEntitlement({
          canDownload: res.data.can_download,
          upgradeRequired: res.data.upgrade_required,
          planType: res.data.plan_type,
          watermarkRequired: res.data.watermark_required,
          loading: false,
        });
      }
    } catch {
      setEntitlement(prev => ({ ...prev, loading: false }));
    }
  }, []);

  useEffect(() => {
    fetchEntitlement();
  }, [fetchEntitlement]);

  // Re-fetch when token changes (login/logout)
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'token') fetchEntitlement();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [fetchEntitlement]);

  return (
    <MediaEntitlementContext.Provider value={{ ...entitlement, refresh: fetchEntitlement }}>
      {children}
    </MediaEntitlementContext.Provider>
  );
}

export function useMediaEntitlement() {
  return useContext(MediaEntitlementContext);
}
