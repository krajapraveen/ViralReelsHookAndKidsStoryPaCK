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
      className="fixed bottom-0 left-0 right-0 z-[9999] p-4 md:p-6"
      data-testid="cookie-consent-banner"
    >
      <div className="max-w-4xl mx-auto bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden">
        {/* Main Banner */}
        <div className="p-4 md:p-6">
          <div className="flex items-start gap-4">
            <div className="hidden sm:flex w-12 h-12 rounded-xl bg-purple-500/20 items-center justify-center flex-shrink-0">
              <Cookie className="w-6 h-6 text-purple-400" />
            </div>
            
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                <Cookie className="w-5 h-5 text-purple-400 sm:hidden" />
                We value your privacy
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                We use cookies to enhance your browsing experience, analyze site traffic, and personalize content. 
                By clicking "Accept All", you consent to our use of cookies. You can customize your preferences below.
              </p>
              
              {/* Quick Links */}
              <div className="flex flex-wrap gap-3 mt-3 text-xs">
                <a 
                  href="/privacy-policy" 
                  className="text-purple-400 hover:text-purple-300 underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Privacy Policy
                </a>
                <a 
                  href="/cookie-policy" 
                  className="text-purple-400 hover:text-purple-300 underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Cookie Policy
                </a>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 mt-4">
            <Button
              onClick={acceptAll}
              className="bg-purple-600 hover:bg-purple-700 text-white flex-1 sm:flex-none"
              data-testid="accept-all-cookies"
            >
              Accept All
            </Button>
            <Button
              onClick={rejectAll}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-800 flex-1 sm:flex-none"
              data-testid="reject-all-cookies"
            >
              Reject All
            </Button>
            <Button
              onClick={() => setShowDetails(!showDetails)}
              variant="ghost"
              className="text-slate-400 hover:text-white flex-1 sm:flex-none"
              data-testid="customize-cookies"
            >
              Customize
              {showDetails ? (
                <ChevronUp className="w-4 h-4 ml-1" />
              ) : (
                <ChevronDown className="w-4 h-4 ml-1" />
              )}
            </Button>
          </div>
        </div>

        {/* Detailed Preferences */}
        {showDetails && (
          <div className="border-t border-slate-700/50 p-4 md:p-6 bg-slate-950/50">
            <h4 className="text-sm font-semibold text-white mb-4">Cookie Preferences</h4>
            
            <div className="space-y-4">
              {/* Necessary Cookies */}
              <div className="flex items-start justify-between gap-4 p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Necessary Cookies</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Essential for the website to function. Cannot be disabled.
                    </p>
                  </div>
                </div>
                <Switch checked={true} disabled className="opacity-50" />
              </div>

              {/* Analytics Cookies */}
              <div className="flex items-start justify-between gap-4 p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                    <BarChart3 className="w-4 h-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Analytics Cookies</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Help us understand how visitors interact with our website (Google Analytics, PostHog).
                    </p>
                  </div>
                </div>
                <Switch 
                  checked={consent.analytics} 
                  onCheckedChange={(checked) => updateConsent('analytics', checked)}
                  data-testid="analytics-toggle"
                />
              </div>

              {/* Marketing Cookies */}
              <div className="flex items-start justify-between gap-4 p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                    <Target className="w-4 h-4 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Marketing Cookies</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Used to deliver personalized advertisements and measure campaign effectiveness.
                    </p>
                  </div>
                </div>
                <Switch 
                  checked={consent.marketing} 
                  onCheckedChange={(checked) => updateConsent('marketing', checked)}
                  data-testid="marketing-toggle"
                />
              </div>

              {/* Preference Cookies */}
              <div className="flex items-start justify-between gap-4 p-3 bg-slate-800/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <Cookie className="w-4 h-4 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Preference Cookies</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Remember your settings and preferences for a better experience.
                    </p>
                  </div>
                </div>
                <Switch 
                  checked={consent.preferences} 
                  onCheckedChange={(checked) => updateConsent('preferences', checked)}
                  data-testid="preferences-toggle"
                />
              </div>
            </div>

            {/* Save Preferences Button */}
            <div className="flex justify-end mt-4">
              <Button
                onClick={savePreferences}
                className="bg-purple-600 hover:bg-purple-700 text-white"
                data-testid="save-cookie-preferences"
              >
                Save Preferences
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
