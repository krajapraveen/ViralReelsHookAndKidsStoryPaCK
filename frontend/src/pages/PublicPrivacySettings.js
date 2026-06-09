/**
 * Privacy Settings (Public) — cookie-consent management surface.
 *
 * P0 2026-06 LEGAL — Required by Article 7(3) GDPR and the DPDP Act
 * 2023: withdrawing consent must be as easy as granting it. Since
 * the consent banner appears to non-authenticated visitors, the
 * withdrawal surface must ALSO be reachable without auth.
 *
 * For authenticated users, the deeper account-level privacy console
 * (data export / deletion / per-feature consent) lives at /app/privacy.
 * Both are linked from each other.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import {
  Sparkles, ArrowLeft, Cookie, Shield, BarChart3, Target,
  RefreshCw, Mail, FileText,
} from 'lucide-react';

const CONSENT_KEY = 'visionary_cookie_consent';
const CONSENT_VERSION = '1.0';
const PRIVACY_EMAIL = 'privacy@visionary-suite.com';

function readConsent() {
  try {
    const raw = localStorage.getItem(CONSENT_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function writeConsent(next) {
  const final = {
    ...next,
    version: CONSENT_VERSION,
    timestamp: new Date().toISOString(),
  };
  localStorage.setItem(CONSENT_KEY, JSON.stringify(final));
  // Mirror the CookieConsent component's gtag / posthog enforcement
  // so the choice takes effect IMMEDIATELY without a page reload.
  try {
    if (window.gtag) {
      window.gtag('consent', 'update', {
        ad_storage: next.marketing ? 'granted' : 'denied',
        ad_user_data: next.marketing ? 'granted' : 'denied',
        ad_personalization: next.marketing ? 'granted' : 'denied',
        analytics_storage: next.analytics ? 'granted' : 'denied',
      });
    }
    if (window.posthog) {
      if (next.analytics) {
        try { window.posthog.opt_in_capturing(); } catch (e) { /* opt-in failed; non-fatal */ }
      } else {
        try { window.posthog.opt_out_capturing(); } catch (e) { /* opt-out failed; non-fatal */ }
      }
    }
  } catch (e) { /* gtag/posthog enforcement is best-effort */ }
  return final;
}

export default function PublicPrivacySettings() {
  // Read consent BEFORE the first render so we don't trip
  // react-hooks/set-state-in-effect. The lazy initializer runs once;
  // subsequent re-reads happen only through user toggles.
  const initialConsent = (() => {
    if (typeof window === 'undefined') {
      return { necessary: true, analytics: false, marketing: false, preferences: false };
    }
    const existing = readConsent();
    return {
      necessary: true,
      analytics: !!(existing && existing.analytics),
      marketing: !!(existing && existing.marketing),
      preferences: !!(existing && existing.preferences),
    };
  })();
  const [consent, setConsentState] = useState(initialConsent);

  const update = (key, value) => setConsentState((p) => ({ ...p, [key]: value }));

  const handleSave = () => {
    writeConsent(consent);
    toast.success('Your cookie preferences have been saved.');
  };

  const handleAcceptAll = () => {
    const next = { necessary: true, analytics: true, marketing: true, preferences: true };
    writeConsent(next);
    setConsentState(next);
    toast.success('All non-essential cookies enabled.');
  };

  const handleRejectAll = () => {
    const next = { necessary: true, analytics: false, marketing: false, preferences: false };
    writeConsent(next);
    setConsentState(next);
    toast.success('All non-essential cookies disabled.');
  };

  const handleResetBanner = () => {
    localStorage.removeItem(CONSENT_KEY);
    toast.success('Consent reset. The banner will appear on your next visit.');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800" data-testid="settings-back-home">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Home
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-500" />
              <span className="text-xl font-bold text-white">Privacy Settings</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">
          <div className="flex items-center gap-3 mb-2">
            <Cookie className="w-7 h-7 text-purple-500" />
            <h1 className="text-2xl font-bold text-white m-0">Cookie Preferences</h1>
          </div>
          <p className="text-slate-400 text-sm mb-8">
            Review and update which cookie categories you allow on Visionary
            Suite. You can change these at any time. Withdrawing consent is as
            easy as granting it.
          </p>

          <div className="space-y-3" data-testid="privacy-settings-toggles">
            <CategoryRow
              icon={Shield}
              color="text-green-400"
              testid="settings-row-necessary"
              title="Necessary"
              description="Required for sign-in, security, and core platform functionality. Always on."
              checked={true}
              disabled
            />
            <CategoryRow
              icon={BarChart3}
              color="text-blue-400"
              testid="settings-row-analytics"
              title="Analytics"
              description="Helps us measure feature usage and reliability. Disabled until you opt in."
              checked={consent.analytics}
              onChange={(v) => update('analytics', v)}
            />
            <CategoryRow
              icon={Target}
              color="text-amber-400"
              testid="settings-row-marketing"
              title="Marketing"
              description="Used for ad measurement and personalization."
              checked={consent.marketing}
              onChange={(v) => update('marketing', v)}
            />
            <CategoryRow
              icon={Cookie}
              color="text-pink-400"
              testid="settings-row-preferences"
              title="Preferences"
              description="Remembers preferences like language, theme, and last-used template."
              checked={consent.preferences}
              onChange={(v) => update('preferences', v)}
            />
          </div>

          <div className="flex flex-wrap gap-2 mt-6">
            <Button
              onClick={handleSave}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="settings-save-btn"
            >
              Save Preferences
            </Button>
            <Button
              onClick={handleAcceptAll}
              variant="outline"
              className="border-slate-600 text-slate-200 hover:bg-slate-800"
              data-testid="settings-accept-all-btn"
            >
              Accept All
            </Button>
            <Button
              onClick={handleRejectAll}
              variant="outline"
              className="border-slate-600 text-slate-200 hover:bg-slate-800"
              data-testid="settings-reject-all-btn"
            >
              Reject Non-Essential
            </Button>
            <Button
              onClick={handleResetBanner}
              variant="ghost"
              className="text-slate-400 hover:text-white hover:bg-slate-800"
              data-testid="settings-reset-banner-btn"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Reset Banner
            </Button>
          </div>

          <div className="mt-10 pt-6 border-t border-slate-800 space-y-3 text-sm text-slate-300">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Mail className="w-4 h-4 text-purple-400" />
              Privacy contact
            </h2>
            <p>
              For privacy enquiries, data-access requests, or consent
              withdrawal under GDPR / DPDP Act 2023, email&nbsp;
              <a href={`mailto:${PRIVACY_EMAIL}`} className="text-purple-400 hover:text-purple-300" data-testid="settings-privacy-email">{PRIVACY_EMAIL}</a>.
            </p>
            <p className="text-slate-400">
              For full details, see the&nbsp;
              <Link to="/privacy-policy" className="text-purple-400 hover:text-purple-300 underline" data-testid="settings-link-privacy-policy">Privacy Policy</Link>
              &nbsp;and the&nbsp;
              <Link to="/cookie-policy" className="text-purple-400 hover:text-purple-300 underline" data-testid="settings-link-cookie-policy">Cookie Policy</Link>.
            </p>
            <p className="text-slate-500 text-xs">
              Authenticated users can manage account-level privacy
              (data export, account deletion) at&nbsp;
              <Link to="/app/privacy" className="text-purple-400 hover:text-purple-300 underline">/app/privacy</Link>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function CategoryRow({ icon: Icon, color, testid, title, description, checked, disabled, onChange }) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 bg-slate-800/40 rounded-lg" data-testid={testid}>
      <div className="flex gap-3">
        <Icon className={`w-5 h-5 mt-0.5 ${color}`} />
        <div>
          <div className="text-white font-medium">{title}</div>
          <div className="text-slate-400 text-sm">{description}</div>
        </div>
      </div>
      <Switch
        checked={checked}
        disabled={!!disabled}
        onCheckedChange={(v) => onChange && onChange(v)}
        className={disabled ? 'opacity-50' : ''}
      />
    </div>
  );
}
