import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { ArrowLeft, Cookie, Shield, BarChart3, Target, Settings } from 'lucide-react';
import { openConsentManager } from '../components/CookieConsent';

export default function CookiePolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="icon" className="text-white">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Cookie className="w-6 h-6 text-purple-400" />
              Cookie Policy
            </h1>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="prose prose-invert max-w-none">
          <p className="text-slate-400 text-sm mb-8">
            Last updated: March 8, 2026
          </p>

          {/* Introduction */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">What Are Cookies?</h2>
            <p className="text-slate-300 leading-relaxed">
              Cookies are small text files that are stored on your device when you visit our website. 
              They help us provide you with a better experience by remembering your preferences, 
              analyzing how you use our site, and delivering relevant content.
            </p>
          </section>

          {/* Cookie Types */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Types of Cookies We Use</h2>
            
            <div className="space-y-6">
              {/* Necessary */}
              <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <Shield className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Necessary Cookies</h3>
                    <span className="text-xs text-green-400">Always Active</span>
                  </div>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">
                  These cookies are essential for the website to function properly. They enable core 
                  functionality such as security, network management, and accessibility. You cannot 
                  opt-out of these cookies as the website would not function properly without them.
                </p>
                <div className="mt-3 text-xs text-slate-400">
                  <strong>Examples:</strong> Session cookies, authentication tokens, CSRF protection
                </div>
              </div>

              {/* Analytics */}
              <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Analytics Cookies</h3>
                    <span className="text-xs text-blue-400">Optional</span>
                  </div>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">
                  These cookies help us understand how visitors interact with our website by collecting 
                  and reporting information anonymously. This helps us improve our website and services.
                </p>
                <div className="mt-3 text-xs text-slate-400">
                  <strong>Services:</strong> Google Analytics (GA4), PostHog
                </div>
              </div>

              {/* Marketing */}
              <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Target className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Marketing Cookies</h3>
                    <span className="text-xs text-amber-400">Optional</span>
                  </div>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">
                  These cookies are used to track visitors across websites. The intention is to display 
                  ads that are relevant and engaging for the individual user and thereby more valuable 
                  for publishers and third-party advertisers.
                </p>
                <div className="mt-3 text-xs text-slate-400">
                  <strong>Purpose:</strong> Personalized advertising, conversion tracking
                </div>
              </div>

              {/* Preferences */}
              <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Settings className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">Preference Cookies</h3>
                    <span className="text-xs text-purple-400">Optional</span>
                  </div>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">
                  These cookies allow our website to remember choices you make (such as your language 
                  preference or the region you are in) and provide enhanced, more personal features.
                </p>
                <div className="mt-3 text-xs text-slate-400">
                  <strong>Examples:</strong> Language settings, theme preferences, recently viewed items
                </div>
              </div>
            </div>
          </section>

          {/* Third Party Cookies */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Third-Party Services</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              We use the following third-party services that may set cookies:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2">
              <li><strong>Google Analytics:</strong> Website traffic analysis</li>
              <li><strong>PostHog:</strong> Product analytics and user behavior</li>
              <li><strong>Cashfree:</strong> Payment processing</li>
              <li><strong>Cloudflare:</strong> Security and performance</li>
            </ul>
          </section>

          {/* Managing Cookies */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Managing Your Cookie Preferences</h2>
            <p className="text-slate-300 leading-relaxed mb-4">
              You can manage your cookie preferences at any time by clicking the button below:
            </p>
            <Button 
              onClick={openConsentManager}
              className="bg-purple-600 hover:bg-purple-700"
              data-testid="manage-cookies-btn"
            >
              <Cookie className="w-4 h-4 mr-2" />
              Manage Cookie Preferences
            </Button>
            <p className="text-slate-400 text-sm mt-4">
              You can also control cookies through your browser settings. Most browsers allow you to:
            </p>
            <ul className="list-disc list-inside text-slate-400 text-sm space-y-1 mt-2">
              <li>View what cookies are stored and delete them individually</li>
              <li>Block third-party cookies</li>
              <li>Block cookies from specific sites</li>
              <li>Block all cookies</li>
              <li>Delete all cookies when you close your browser</li>
            </ul>
          </section>

          {/* Your Rights */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Your Rights</h2>
            <p className="text-slate-300 leading-relaxed">
              Under GDPR and CCPA, you have the right to:
            </p>
            <ul className="list-disc list-inside text-slate-300 space-y-2 mt-4">
              <li>Know what personal data we collect</li>
              <li>Request deletion of your personal data</li>
              <li>Opt-out of the sale of your personal data</li>
              <li>Access your personal data</li>
              <li>Correct inaccurate personal data</li>
              <li>Data portability</li>
            </ul>
            <p className="text-slate-400 text-sm mt-4">
              To exercise these rights, please visit our{' '}
              <Link to="/app/privacy-settings" className="text-purple-400 hover:text-purple-300 underline">
                Privacy Settings
              </Link>{' '}
              page or contact us at{' '}
              <a href="mailto:privacy@visionary-suite.com" className="text-purple-400 hover:text-purple-300 underline">
                privacy@visionary-suite.com
              </a>
            </p>
          </section>

          {/* Contact */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Contact Us</h2>
            <p className="text-slate-300 leading-relaxed">
              If you have any questions about our Cookie Policy, please contact us:
            </p>
            <div className="mt-4 text-slate-400">
              <p>Email: <a href="mailto:privacy@visionary-suite.com" className="text-purple-400">privacy@visionary-suite.com</a></p>
              <p>Website: <a href="https://www.visionary-suite.com" className="text-purple-400">www.visionary-suite.com</a></p>
            </div>
          </section>

          {/* Links */}
          <section className="border-t border-slate-700/50 pt-8">
            <h3 className="text-lg font-semibold text-white mb-4">Related Policies</h3>
            <div className="flex flex-wrap gap-4">
              <Link to="/privacy-policy">
                <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800">
                  Privacy Policy
                </Button>
              </Link>
              <Link to="/terms-of-service">
                <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-800">
                  Terms of Service
                </Button>
              </Link>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
