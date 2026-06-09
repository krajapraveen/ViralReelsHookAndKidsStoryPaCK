/**
 * Cookie Policy — Visionary Suite
 *
 * P0 2026-06 LEGAL — Production-ready Cookie Policy aligned with the
 * Privacy Policy. Identifies each cookie category, names the consent
 * banner buttons, and links to the Privacy Settings page where the
 * user can withdraw consent at any time.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Sparkles, ArrowLeft, Cookie, Shield, Settings, BarChart3,
  Activity, ExternalLink, Mail, FileText,
} from 'lucide-react';

const PRIVACY_EMAIL = 'privacy@visionary-suite.com';
const EFFECTIVE_DATE = new Date().toLocaleDateString('en-US', {
  year: 'numeric', month: 'long', day: 'numeric',
});

function Section({ icon: Icon, num, title, children, testid }) {
  return (
    <section data-testid={testid || `cookie-section-${num}`}>
      <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
        {Icon ? <Icon className="w-5 h-5 text-purple-400" /> : null}
        {num}. {title}
      </h2>
      <div className="text-slate-300 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

export default function CookiePolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-purple-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800" data-testid="cookie-back-home">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Home
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-500" />
              <span className="text-xl font-bold text-white">Cookie Policy</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">
          <div className="prose prose-invert max-w-none">
            <div className="flex items-center gap-3 mb-2">
              <Cookie className="w-8 h-8 text-purple-500" />
              <h1 className="text-3xl font-bold text-white m-0">Cookie Policy</h1>
            </div>
            <p className="text-slate-400 text-sm mb-8" data-testid="cookie-effective-date">
              Effective Date: {EFFECTIVE_DATE} · Last Updated: {EFFECTIVE_DATE}
            </p>

            <div className="space-y-8">

              <Section icon={FileText} num="1" title="What Are Cookies?">
                <p>
                  Cookies are small text files that a website stores in your
                  browser when you visit. They allow the website to remember
                  who you are between page loads and visits — keeping you
                  signed in, remembering your preferences, and (with your
                  consent) helping us understand how the platform is used so
                  we can improve it.
                </p>
                <p>
                  Visionary Suite uses cookies and similar technologies
                  (including localStorage entries and pixel tags) across the
                  Visionary Suite website, iOS application, and Android
                  application. Where mobile platforms use device identifiers
                  rather than cookies, equivalent privacy controls apply.
                </p>
              </Section>

              <Section icon={Shield} num="2" title="Essential Cookies (Strictly Necessary)" testid="cookie-essential">
                <p>
                  Essential cookies are required to operate the platform. You
                  cannot disable them through the consent banner because
                  without them the service simply does not work. Examples:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Login session tokens (kept in HTTP-only cookies or localStorage)</li>
                  <li>Authentication state and CSRF protection</li>
                  <li>Subscription verification and access control</li>
                  <li>Account-management session data</li>
                  <li>Cookie-consent preferences themselves</li>
                </ul>
              </Section>

              <Section icon={Settings} num="3" title="Functional Cookies" testid="cookie-functional">
                <p>Functional cookies remember choices you make to give you a more personalized experience:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Language preferences</li>
                  <li>Theme and display preferences</li>
                  <li>Saved settings (e.g., default video aspect ratio, last-used template)</li>
                  <li>Onboarding / tour completion flags</li>
                </ul>
              </Section>

              <Section icon={BarChart3} num="4" title="Analytics Cookies" testid="cookie-analytics">
                <p>
                  Analytics cookies help us understand how creators use
                  Visionary Suite so we can improve features and fix problems.
                  They <strong>do not load until you grant consent</strong> via the
                  cookie banner. Analytics partners we use include:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Google Analytics 4 — usage measurement, feature adoption, page-load timing</li>
                  <li>PostHog — product analytics, funnel measurement, session-quality diagnostics</li>
                </ul>
                <p>
                  Both providers are configured in <strong>denied-by-default
                  consent mode</strong>. If you do not opt in, analytics events
                  are not transmitted.
                </p>
              </Section>

              <Section icon={Activity} num="5" title="Performance Cookies" testid="cookie-performance">
                <p>Performance cookies help us monitor and improve service reliability:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Page load and Core Web Vitals measurement</li>
                  <li>Error monitoring and crash diagnostics</li>
                  <li>Feature-level performance metrics</li>
                </ul>
              </Section>

              <Section icon={ExternalLink} num="6" title="Third-Party Cookies" testid="cookie-third-party">
                <p>Some pages embed third-party services that may set their own cookies:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Authentication providers</strong> — Google Sign-In</li>
                  <li><strong>Analytics providers</strong> — Google Analytics 4, PostHog</li>
                  <li><strong>Payment providers</strong> — for processing subscription and credit purchases</li>
                  <li><strong>Embedded services</strong> — such as the Emergent platform widget</li>
                </ul>
                <p>
                  These providers are independent data controllers and have
                  their own privacy policies. Where applicable, third-party
                  cookies are only set after you consent through the cookie
                  banner.
                </p>
              </Section>

              <Section icon={Cookie} num="7" title="Cookie Consent Banner">
                <p>
                  The first time you visit Visionary Suite, a cookie consent
                  banner appears giving you three choices:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1" data-testid="cookie-banner-buttons">
                  <li><strong>Accept All</strong> — enable every cookie category, including analytics and marketing.</li>
                  <li><strong>Reject Non-Essential</strong> — keep only essential cookies; analytics, marketing, and personalization remain off.</li>
                  <li><strong>Manage Preferences</strong> — toggle each category individually.</li>
                </ul>
                <p>
                  Your choice is persisted in your browser and respected on
                  every subsequent visit. Analytics scripts default to a
                  denied / opted-out state and only begin sending events
                  after you opt in.
                </p>
              </Section>

              <Section icon={Settings} num="8" title="Withdrawing or Changing Your Consent">
                <p>You may withdraw consent or change your cookie preferences at any time:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Visit the <Link to="/privacy-settings" className="text-purple-400 hover:text-purple-300 underline" data-testid="cookie-link-privacy-settings">Privacy Settings</Link> page and reopen the cookie preferences.</li>
                  <li>Use your browser&apos;s built-in settings to clear or block cookies for visionary-suite.com.</li>
                  <li>On mobile, use the device privacy controls (e.g., iOS App Tracking Transparency, Android privacy dashboard).</li>
                </ul>
                <p>
                  Disabling essential cookies will impair core functionality
                  such as login and subscription access.
                </p>
              </Section>

              <Section icon={Activity} num="9" title="Cookie Retention">
                <p>How long different cookies remain on your device:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Session cookies</strong> — deleted when you close the browser</li>
                  <li><strong>Authentication cookies</strong> — typically valid for the lifetime of your session, refreshed on activity</li>
                  <li><strong>Functional preference cookies</strong> — up to 12 months</li>
                  <li><strong>Analytics cookies</strong> — up to 13 months (Google Analytics 4 default)</li>
                  <li><strong>Consent record</strong> — kept until you withdraw it or clear browser storage</li>
                </ul>
              </Section>

              <Section icon={Mail} num="10" title="Contact and Further Information">
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Privacy enquiries:</strong> <a href={`mailto:${PRIVACY_EMAIL}`} className="text-purple-400 hover:text-purple-300" data-testid="cookie-contact-email">{PRIVACY_EMAIL}</a></li>
                  <li>For details on how Visionary Suite handles personal data more broadly, see the <Link to="/privacy-policy" className="text-purple-400 hover:text-purple-300 underline" data-testid="cookie-link-privacy-policy">Privacy Policy</Link>.</li>
                </ul>
              </Section>

            </div>

            <div className="mt-12 pt-6 border-t border-slate-800 text-center">
              <p className="text-slate-400 text-sm">
                See also:&nbsp;
                <Link to="/privacy-policy" className="text-purple-400 hover:text-purple-300 underline">Privacy Policy</Link>
                &nbsp;·&nbsp;
                <Link to="/terms-of-service" className="text-purple-400 hover:text-purple-300 underline">Terms of Service</Link>
                &nbsp;·&nbsp;
                <Link to="/privacy-settings" className="text-purple-400 hover:text-purple-300 underline">Privacy Settings</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
