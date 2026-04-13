/**
 * Cookie Consent Banner
 * GDPR/CCPA compliant cookie consent with granular controls
 */
import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Cookie, Shield, BarChart3, Target, X, ChevronDown, ChevronUp } from 'lucide-react';

const CONSENT_KEY = 'visionary_cookie_consent';
const CONSENT_VERSION = '1.0';

// Default consent settings
const DEFAULT_CONSENT = {
  necessary: true, // Always required
  analytics: false,
  marketing: false,
  preferences: false,
  version: CONSENT_VERSION,
  timestamp: null
};

export default function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [consent, setConsent] = useState(DEFAULT_CONSENT);

  useEffect(() => {
    // Check if consent has been given
    const storedConsent = localStorage.getItem(CONSENT_KEY);
    
    if (storedConsent) {
      try {
        const parsed = JSON.parse(storedConsent);
        // Check if consent version matches
        if (parsed.version === CONSENT_VERSION) {
          setConsent(parsed);
          applyConsent(parsed);
          return;
        }
      } catch (e) {
        console.error('Failed to parse stored consent:', e);
      }
    }
    
    // Show banner if no valid consent
    setTimeout(() => setShowBanner(true), 1000);
  }, []);

  const applyConsent = (consentData) => {
    // Apply analytics consent
    if (consentData.analytics) {
      enableAnalytics();
    } else {
      disableAnalytics();
    }

    // Apply marketing consent
    if (consentData.marketing) {
      enableMarketing();
    } else {
      disableMarketing();
    }
  };

  const enableAnalytics = () => {
    // Enable Google Analytics
    if (window.gtag) {
      window.gtag('consent', 'update', {
        'analytics_storage': 'granted'
      });
    }
    // Enable PostHog
    if (window.posthog) {
      window.posthog.opt_in_capturing();
    }
  };

  const disableAnalytics = () => {
    // Disable Google Analytics
    if (window.gtag) {
      window.gtag('consent', 'update', {
        'analytics_storage': 'denied'
      });
    }
    // Disable PostHog
    if (window.posthog) {
      window.posthog.opt_out_capturing();
    }
  };

  const enableMarketing = () => {
    if (window.gtag) {
      window.gtag('consent', 'update', {
        'ad_storage': 'granted',
        'ad_user_data': 'granted',
        'ad_personalization': 'granted'
      });
    }
  };

  const disableMarketing = () => {
    if (window.gtag) {
      window.gtag('consent', 'update', {
        'ad_storage': 'denied',
        'ad_user_data': 'denied',
        'ad_personalization': 'denied'
      });
    }
  };

  const saveConsent = (consentData) => {
    const finalConsent = {
      ...consentData,
      version: CONSENT_VERSION,
      timestamp: new Date().toISOString()
    };
    
    localStorage.setItem(CONSENT_KEY, JSON.stringify(finalConsent));
    setConsent(finalConsent);
    applyConsent(finalConsent);
    setShowBanner(false);
  };

  const acceptAll = () => {
    saveConsent({
      necessary: true,
      analytics: true,
      marketing: true,
      preferences: true
    });
  };

  const rejectAll = () => {
    saveConsent({
      necessary: true,
      analytics: false,
      marketing: false,
      preferences: false
    });
  };

  const savePreferences = () => {
    saveConsent(consent);
  };

  const updateConsent = (key, value) => {
    setConsent(prev => ({ ...prev, [key]: value }));
  };

  if (!showBanner) return null;

  return (
    <div 
      className="fixed bottom-20 right-4 z-[9000] max-w-sm sm:bottom-4"
      data-testid="cookie-consent-banner"
    >
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-xl shadow-2xl overflow-hidden">
        <div className="p-3">
          <div className="flex items-center gap-3">
            <Cookie className="w-4 h-4 text-purple-400 flex-shrink-0" />
            <p className="text-xs text-slate-300 flex-1">
              We use cookies to improve your experience.{' '}
              <a href="/privacy-policy" className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">Learn more</a>
            </p>
          </div>
          <div className="flex gap-2 mt-2.5">
            <Button
              onClick={acceptAll}
              size="sm"
              className="h-7 px-3 text-xs bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg"
              data-testid="cookie-accept-btn"
            >
              Accept All
            </Button>
            <Button
              onClick={rejectAll}
              variant="outline"
              size="sm"
              className="h-7 px-3 text-xs border-slate-600 text-slate-300 hover:bg-slate-800 rounded-lg"
              data-testid="cookie-reject-btn"
            >
              Reject All
            </Button>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="h-7 px-2 text-xs text-slate-400 hover:text-white transition-colors flex items-center gap-1"
              data-testid="cookie-customize-btn"
            >
              {showDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Detailed Preferences */}
        {showDetails && (
          <div className="border-t border-slate-700/50 p-3 bg-slate-950/50">
            <h4 className="text-xs font-semibold text-white mb-3">Cookie Preferences</h4>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Shield className="w-3 h-3 text-green-400" />
                  <span className="text-xs text-white">Necessary</span>
                </div>
                <Switch checked={true} disabled className="opacity-50 scale-75" />
              </div>
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-3 h-3 text-blue-400" />
                  <span className="text-xs text-white">Analytics</span>
                </div>
                <Switch 
                  checked={consent.analytics} 
                  onCheckedChange={(checked) => updateConsent('analytics', checked)}
                  className="scale-75"
                  data-testid="analytics-toggle"
                />
              </div>
              <div className="flex items-center justify-between gap-2 p-2 bg-slate-800/50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Target className="w-3 h-3 text-amber-400" />
                  <span className="text-xs text-white">Marketing</span>
                </div>
                <Switch 
                  checked={consent.marketing} 
                  onCheckedChange={(checked) => updateConsent('marketing', checked)}
                  className="scale-75"
                  data-testid="marketing-toggle"
                />
              </div>
            </div>
            <div className="flex justify-end mt-2">
              <Button
                onClick={savePreferences}
                size="sm"
                className="h-7 px-3 text-xs bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                data-testid="save-cookie-preferences"
              >
                Save
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Export utility function to check consent
export const hasAnalyticsConsent = () => {
  try {
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored) {
      const consent = JSON.parse(stored);
      return consent.analytics === true;
    }
  } catch (e) {
    console.error('Failed to check analytics consent:', e);
  }
  return false;
};

export const hasMarketingConsent = () => {
  try {
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored) {
      const consent = JSON.parse(stored);
      return consent.marketing === true;
    }
  } catch (e) {
    console.error('Failed to check marketing consent:', e);
  }
  return false;
};

// Function to open consent manager
export const openConsentManager = () => {
  localStorage.removeItem(CONSENT_KEY);
  window.location.reload();
};
