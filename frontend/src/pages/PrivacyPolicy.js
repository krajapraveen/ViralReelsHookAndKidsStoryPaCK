/**
 * Privacy Policy — Visionary Suite
 *
 * P0 2026-06 LEGAL — Production-ready, platform-specific privacy
 * policy tailored to Visionary Suite's AI content-generation
 * features. Replaces the previous generic template.
 *
 * Covers (mandatory per the legal-scope brief):
 *   • Platform features: Story Video Studio, Photo to Comic,
 *     Comic Storybook, Character Studio, Story Series, Reel
 *     Generator, Brand Kit, Bedtime Stories, Reaction GIF, Daily
 *     Viral Ideas, MyTrailer (Photo Trailer).
 *   • Facial-image processing disclosure (dedicated section).
 *   • Voice / audio processing disclosure.
 *   • AI service-provider transmission disclosure.
 *   • User-ownership clause.
 *   • Generated-content responsibility clause.
 *   • Copyright responsibility.
 *   • GDPR rights enumeration.
 *   • India DPDP Act 2023 rights enumeration.
 *   • Web + iOS + Android coverage statement.
 *   • Retention rules + 30-day soft-delete + permanent purge.
 *
 * Effective date is computed at render time (so the policy carries
 * the live-deployment date as agreed). Do not extract — the date
 * must always reflect the latest build.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import {
  Sparkles, ArrowLeft, Shield, Lock, Eye, Mail, Globe,
  Image as ImageIcon, Mic, Cpu, FileText, Trash2, Cookie,
  Smartphone, AlertTriangle, ScrollText,
} from 'lucide-react';

const PRIVACY_EMAIL = 'privacy@visionary-suite.com';
const SUPPORT_EMAIL = 'support@visionary-suite.com';
const EFFECTIVE_DATE = new Date().toLocaleDateString('en-US', {
  year: 'numeric', month: 'long', day: 'numeric',
});

const FEATURE_LIST = [
  'Story Video Studio',
  'Photo to Comic',
  'Comic Storybook',
  'Character Studio',
  'Story Series',
  'Reel Generator',
  'Brand Kit',
  'Bedtime Stories',
  'Reaction GIF',
  'Daily Viral Ideas',
  'MyTrailer (Photo Trailer)',
];

function Section({ icon: Icon, num, title, children }) {
  return (
    <section data-testid={`privacy-section-${num}`}>
      <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
        {Icon ? <Icon className="w-5 h-5 text-indigo-400" /> : null}
        {num}. {title}
      </h2>
      <div className="text-slate-300 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800" data-testid="privacy-back-home">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Home
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold text-white">Privacy Policy</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">
          <div className="prose prose-invert max-w-none">
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-8 h-8 text-indigo-500" />
              <h1 className="text-3xl font-bold text-white m-0">Privacy Policy</h1>
            </div>
            <p className="text-slate-400 text-sm mb-8" data-testid="privacy-effective-date">
              Effective Date: {EFFECTIVE_DATE} · Last Updated: {EFFECTIVE_DATE}
            </p>

            <div className="space-y-8">

              <Section icon={Globe} num="1" title="Introduction">
                <p>
                  Visionary Suite (&quot;Visionary Suite&quot;, &quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) is an
                  AI-powered content creation platform that helps creators turn
                  ideas, photos, voices, and prompts into videos, comics,
                  storybooks, avatars, characters, reels, GIFs, trailers, and other
                  creative assets. This Privacy Policy explains what information we
                  collect, how we use it, how we share it, and the rights you have
                  over it.
                </p>
                <p>
                  This Policy applies to the Visionary Suite website
                  (https://visionary-suite.com), our iOS application, our Android
                  application, and any future Visionary Suite products or services.
                  By creating an account or using our services, you agree to the
                  practices described here. If you do not agree, please do not use
                  Visionary Suite.
                </p>
                <p className="text-slate-400 text-sm">
                  Visionary Suite features covered by this Policy include:
                </p>
                <ul className="list-disc list-inside ml-4 text-slate-400 text-sm" data-testid="privacy-feature-list">
                  {FEATURE_LIST.map((f) => <li key={f}>{f}</li>)}
                </ul>
              </Section>

              <Section icon={Eye} num="2" title="Information We Collect">
                <div>
                  <h3 className="font-semibold text-white mb-1">2.1 Account Information</h3>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Name, email address, username</li>
                    <li>Authentication credentials (password hashes — we never store plain-text passwords)</li>
                    <li>Google Sign-In profile data (name, email, profile picture) when you choose Google login</li>
                    <li>Subscription tier, plan history, and credit balance</li>
                    <li>Account preferences, notification settings, and language</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">2.2 Content You Upload</h3>
                  <p>You may upload the following to Visionary Suite for AI processing:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Personal photos, family photos, children&apos;s photos, and portraits</li>
                    <li>Character images and reference artwork</li>
                    <li>Brand assets and logos</li>
                    <li>Voice recordings and audio files</li>
                    <li>Story content, scripts, prompts, and instructions</li>
                    <li>Documents (text, PDF) that you submit for processing</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">2.3 AI Generation Information</h3>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>Generation prompts you write</li>
                    <li>Style selections, character settings, and story settings</li>
                    <li>Video, audio, and output preferences (length, aspect ratio, format)</li>
                    <li>AI-generated outputs and the project metadata around them</li>
                  </ul>
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1">2.4 Technical Information</h3>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>IP address, browser type, device type, operating system</li>
                    <li>Session data and login timestamps</li>
                    <li>Anonymous usage analytics and feature-adoption events</li>
                    <li>Crash logs and error diagnostics</li>
                  </ul>
                </div>
              </Section>

              <Section icon={ImageIcon} num="3" title="Facial Image Processing Disclosure">
                <p className="font-semibold text-amber-300" data-testid="privacy-facial-disclosure">
                  Several Visionary Suite features process uploaded photographs
                  that may contain human faces — including Character Studio,
                  MyTrailer (Photo Trailer), Reaction GIF, Photo to Comic, and
                  related avatar / illustration tools.
                </p>
                <p>The following commitments apply to ALL facial image processing:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Uploaded images are used <strong>solely</strong> to generate the outputs you request and to operate the platform.</li>
                  <li>We do <strong>not sell</strong> facial images, biometric data, or any data derived from them.</li>
                  <li>We do <strong>not</strong> use uploaded photographs for law-enforcement identification, facial-recognition surveillance, biometric identification, or any purpose outside the requested AI generation.</li>
                  <li>We do <strong>not</strong> use uploaded photographs to identify, profile, or track individuals beyond the requested creative output.</li>
                  <li>You must only upload photographs that you own or for which you have all necessary permissions from the people depicted. By uploading, you confirm you hold those rights.</li>
                </ul>
              </Section>

              <Section icon={Mic} num="4" title="Voice and Audio Processing">
                <p data-testid="privacy-voice-disclosure">
                  Voice recordings and audio files you upload may be processed
                  through AI systems to generate narration, video soundtracks,
                  trailer voiceovers, story audio, and other requested outputs.
                  You must have the rights and permissions necessary for any audio
                  content you upload. Audio is not used to identify speakers
                  outside the requested generation process, and we do not sell
                  voice recordings or voice prints.
                </p>
              </Section>

              <Section icon={FileText} num="5" title="How We Use Your Information">
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Create and authenticate your account</li>
                  <li>Deliver the AI generation services you request</li>
                  <li>Save your projects, drafts, and generated assets</li>
                  <li>Process subscription billing and credit purchases</li>
                  <li>Provide customer support and respond to your requests</li>
                  <li>Improve the platform, debug errors, and prevent abuse</li>
                  <li>Monitor for fraud, security incidents, and policy violations</li>
                  <li>Comply with legal obligations</li>
                </ul>
              </Section>

              <Section icon={Cpu} num="6" title="AI Service Providers and Third-Party Processing">
                <p data-testid="privacy-ai-provider-disclosure">
                  To provide AI-powered services, Visionary Suite may transmit
                  your content to carefully selected third-party service
                  providers, including:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>AI model providers (large language models, image / video / audio generation models)</li>
                  <li>Cloud infrastructure and storage providers</li>
                  <li>Authentication providers (e.g., Google Sign-In)</li>
                  <li>Payment processors</li>
                  <li>Analytics and error-monitoring providers</li>
                </ul>
                <p>
                  Such processing occurs solely to deliver the services you
                  request, return results to you, and operate the platform. We
                  do not authorize providers to use your content to train
                  general-purpose models on your behalf without your consent
                  where such consent is required by applicable law. Inputs are
                  transmitted to providers; outputs return to Visionary Suite
                  and are delivered to you.
                </p>
              </Section>

              <Section icon={Lock} num="7" title="Payment Information">
                <p>
                  Subscription and credit-pack purchases are processed by
                  third-party payment providers. Visionary Suite does not
                  receive or store full payment card numbers. We retain
                  transaction records (amount, date, plan, last four card
                  digits or wallet identifier) for billing, refunds, and tax /
                  accounting compliance.
                </p>
              </Section>

              <Section icon={ScrollText} num="8" title="Data Retention">
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Account information:</strong> retained while your account is active.</li>
                  <li><strong>Generated projects:</strong> remain available until you delete them or your account is closed. Visionary Suite may remove inactive content after account closure per operational retention requirements.</li>
                  <li><strong>Support requests:</strong> retained for operational and quality-improvement purposes.</li>
                  <li><strong>Billing records:</strong> retained as required by tax and accounting law.</li>
                  <li><strong>Account deletion:</strong> we apply a <strong>30-day soft-deletion period</strong> followed by <strong>permanent deletion</strong> of personal data where legally permissible. Certain records (billing, fraud, legal compliance) may be retained longer where required by law.</li>
                </ul>
              </Section>

              <Section icon={Shield} num="9" title="Your Rights">
                <p>You have the following rights over your personal data:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Access:</strong> request a copy of the personal data we hold about you</li>
                  <li><strong>Correction:</strong> ask us to correct inaccurate or incomplete data</li>
                  <li><strong>Deletion:</strong> request deletion of your data (see Section 8)</li>
                  <li><strong>Withdraw consent:</strong> revoke previously given consent at any time</li>
                  <li><strong>Data portability:</strong> request a portable copy of your data where applicable</li>
                  <li><strong>Restriction:</strong> ask us to limit the processing of your data</li>
                  <li><strong>Object:</strong> object to certain types of processing</li>
                </ul>
                <p>
                  Send any rights request to <a href={`mailto:${PRIVACY_EMAIL}`} className="text-indigo-400 hover:text-indigo-300">{PRIVACY_EMAIL}</a> from the email address on your account.
                </p>
              </Section>

              <Section icon={Globe} num="10" title="GDPR — European Economic Area, United Kingdom, and Switzerland">
                <p data-testid="privacy-gdpr-section">
                  If you are located in the European Economic Area, the United
                  Kingdom, or Switzerland, you have the following rights under
                  the General Data Protection Regulation (GDPR) and
                  UK / Swiss equivalents:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Right of access (Article 15)</li>
                  <li>Right of rectification (Article 16)</li>
                  <li>Right of erasure (Article 17)</li>
                  <li>Right to restrict processing (Article 18)</li>
                  <li>Right to data portability (Article 20)</li>
                  <li>Right to object to processing (Article 21)</li>
                  <li>Right to withdraw consent at any time (Article 7(3))</li>
                  <li>Right to lodge a complaint with your local supervisory authority</li>
                </ul>
                <p>
                  Legal bases on which we process your data include: <strong>contract</strong> (delivering the services you signed up for), <strong>legitimate interests</strong> (platform security, fraud prevention, service improvement), <strong>consent</strong> (analytics cookies, optional marketing), and <strong>legal obligation</strong> (tax, accounting, regulator requests).
                </p>
              </Section>

              <Section icon={Globe} num="11" title="India — Digital Personal Data Protection Act 2023 (DPDP Act)">
                <p data-testid="privacy-dpdp-section">
                  If you are located in India, the Digital Personal Data
                  Protection Act 2023 (&quot;DPDP Act&quot;) grants you the following
                  rights with respect to your personal data:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Right to obtain a summary of personal data we process about you</li>
                  <li>Right to correction, completion, and erasure of personal data</li>
                  <li>Right to grievance redressal</li>
                  <li>Right to nominate another person to exercise your rights in case of incapacity or death</li>
                  <li>Right to withdraw consent for processing</li>
                </ul>
                <p>
                  For DPDP Act requests, please contact our Data Protection
                  team at <a href={`mailto:${PRIVACY_EMAIL}`} className="text-indigo-400 hover:text-indigo-300">{PRIVACY_EMAIL}</a>.
                  We will respond within the timeframes prescribed under the
                  DPDP Act.
                </p>
              </Section>

              <Section icon={AlertTriangle} num="12" title="Children's Privacy">
                <p>
                  Visionary Suite is not intended for children under 13. We do
                  not knowingly collect personal data from children under 13.
                  For users between 13 and the age of majority in their
                  jurisdiction, parent or guardian consent may be required
                  under applicable law. If you believe a child has provided us
                  with personal data, contact us at <a href={`mailto:${PRIVACY_EMAIL}`} className="text-indigo-400 hover:text-indigo-300">{PRIVACY_EMAIL}</a> and we will take prompt action.
                </p>
              </Section>

              <Section icon={Lock} num="13" title="Security">
                <p>
                  We apply reasonable technical and organizational measures
                  designed to protect your data, including:
                </p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>HTTPS / TLS encryption in transit</li>
                  <li>Bcrypt-hashed passwords (we never store plain text)</li>
                  <li>Authentication-gated access to your account data</li>
                  <li>Role-based access controls for our staff</li>
                  <li>Monitoring and alerting for unusual activity</li>
                </ul>
                <p>
                  No method of internet transmission or electronic storage is
                  100% secure. We cannot guarantee absolute security.
                </p>
              </Section>

              <Section icon={FileText} num="14" title="Content Ownership and Copyright">
                <p className="font-semibold" data-testid="privacy-user-ownership">
                  Visionary Suite does not claim ownership of user-uploaded
                  content. Users retain ownership of content they upload,
                  subject to the limited license necessary for Visionary Suite
                  to store, process, display, transform, generate, and deliver
                  the requested outputs.
                </p>
                <p>By uploading content, you confirm that:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>You own the content, or you have all permissions necessary to upload and use it</li>
                  <li>Uploading and processing the content does not violate copyright, trademark, publicity, privacy, or any other applicable right</li>
                  <li>The content does not violate any applicable law</li>
                </ul>
              </Section>

              <Section icon={AlertTriangle} num="15" title="AI-Generated Content Disclaimer">
                <p>
                  AI-generated outputs may contain inaccuracies, omissions, or
                  unexpected results. You are responsible for reviewing all
                  AI-generated outputs before publishing, distributing, or
                  using them commercially. Visionary Suite is not liable for
                  the accuracy, fitness for purpose, or downstream use of
                  generated outputs.
                </p>
              </Section>

              <Section icon={Trash2} num="16" title="Account Deletion">
                <p>To delete your account:</p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Sign in, open <strong>Profile → Settings</strong>, and use the &quot;Delete Account&quot; option, or email <a href={`mailto:${PRIVACY_EMAIL}`} className="text-indigo-400 hover:text-indigo-300">{PRIVACY_EMAIL}</a> from your registered email address.</li>
                  <li>Your account enters a <strong>30-day soft-deletion period</strong> during which you may restore it by contacting support.</li>
                  <li>After 30 days, your personal data is permanently deleted where legally permissible.</li>
                  <li>Certain records (billing, tax, legal compliance) may be retained for the period required by law.</li>
                </ul>
              </Section>

              <Section icon={Smartphone} num="17" title="Mobile Applications and Cross-Platform Coverage">
                <p data-testid="privacy-mobile-section">
                  This Privacy Policy applies to the Visionary Suite website
                  (https://visionary-suite.com), the Visionary Suite iOS
                  application, the Visionary Suite Android application, and any
                  future Visionary Suite products or services. Mobile platforms
                  may also be subject to additional terms imposed by Apple, Google,
                  or your device manufacturer.
                </p>
              </Section>

              <Section icon={Cookie} num="18" title="Cookies and Tracking Technologies">
                <p>
                  We use cookies and similar tracking technologies to operate
                  the platform, remember your preferences, and (with your
                  consent) measure usage. For details on which cookies we set,
                  the categories they fall into, and how you can manage them,
                  see our <Link to="/cookie-policy" className="text-indigo-400 hover:text-indigo-300" data-testid="privacy-link-cookie-policy">Cookie Policy</Link>.
                </p>
                <p>
                  You can update or withdraw your cookie preferences at any
                  time on the <Link to="/privacy-settings" className="text-indigo-400 hover:text-indigo-300" data-testid="privacy-link-privacy-settings">Privacy Settings</Link> page.
                </p>
              </Section>

              <Section icon={Globe} num="19" title="International Data Transfers">
                <p>
                  Visionary Suite operates globally. Your data may be processed
                  in countries other than the one in which you reside, including
                  countries that may have different data-protection standards.
                  Where we transfer data internationally, we rely on appropriate
                  safeguards under applicable law (such as Standard Contractual
                  Clauses for transfers from the European Economic Area).
                </p>
              </Section>

              <Section icon={FileText} num="20" title="Changes to this Privacy Policy">
                <p>
                  We may update this Privacy Policy from time to time. Material
                  changes will be communicated via the platform or by email.
                  Continued use of Visionary Suite after the changes take
                  effect constitutes acceptance of the updated Policy.
                </p>
              </Section>

              <Section icon={Mail} num="21" title="Contact Us">
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li><strong>Privacy enquiries:</strong> <a href={`mailto:${PRIVACY_EMAIL}`} className="text-indigo-400 hover:text-indigo-300" data-testid="privacy-contact-email">{PRIVACY_EMAIL}</a></li>
                  <li><strong>General support:</strong> <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-400 hover:text-indigo-300">{SUPPORT_EMAIL}</a></li>
                  <li><strong>Business location:</strong> India</li>
                </ul>
              </Section>

            </div>

            <div className="mt-12 pt-6 border-t border-slate-800 text-center">
              <p className="text-slate-400 text-sm">
                See also:&nbsp;
                <Link to="/cookie-policy" className="text-indigo-400 hover:text-indigo-300 underline">Cookie Policy</Link>
                &nbsp;·&nbsp;
                <Link to="/terms-of-service" className="text-indigo-400 hover:text-indigo-300 underline">Terms of Service</Link>
                &nbsp;·&nbsp;
                <Link to="/privacy-settings" className="text-indigo-400 hover:text-indigo-300 underline">Privacy Settings</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
