import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Sparkles, ArrowLeft, Shield, Lock, Eye, FileText, Mail, Globe } from 'lucide-react';

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950">
      <header className="bg-slate-900/50 backdrop-blur-xl border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
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
            <div className="flex items-center gap-3 mb-6">
              <Shield className="w-8 h-8 text-indigo-500" />
              <h1 className="text-3xl font-bold text-white m-0">Privacy Policy</h1>
            </div>
            
            <p className="text-slate-400 text-sm mb-8">
              Last Updated: February 19, 2026
            </p>

            <div className="space-y-8">
              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Globe className="w-5 h-5 text-indigo-400" />
                  1. Introduction
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  Welcome to CreatorStudio AI, a service provided by Visionary Suite ("we," "our," or "us"). 
                  This Privacy Policy explains how we collect, use, disclose, and safeguard your information 
                  when you use our AI-powered content creation platform. By using CreatorStudio AI, you agree 
                  to the collection and use of information in accordance with this policy.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Eye className="w-5 h-5 text-indigo-400" />
                  2. Information We Collect
                </h2>
                <div className="space-y-4 text-slate-300">
                  <div>
                    <h3 className="font-semibold text-white mb-2">2.1 Information You Provide</h3>
                    <ul className="list-disc list-inside space-y-1 ml-4">
                      <li>Account registration data (name, email address)</li>
                      <li>Profile information you choose to provide</li>
                      <li>Content inputs (topics, descriptions, preferences)</li>
                      <li>Payment information (processed securely via Cashfree)</li>
                      <li>Communications with our support team</li>
                      <li>Feedback and feature requests</li>
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-semibold text-white mb-2">2.2 Automatically Collected Information</h3>
                    <ul className="list-disc list-inside space-y-1 ml-4">
                      <li>Device information (browser type, operating system)</li>
                      <li>Usage data (features used, generation history)</li>
                      <li>Log data (IP address, access times, pages viewed)</li>
                      <li>Cookies and similar tracking technologies</li>
                    </ul>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  3. How We Use Your Information
                </h2>
                <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
                  <li>To provide, maintain, and improve our AI content generation services</li>
                  <li>To process transactions and manage your account</li>
                  <li>To personalize your experience and content recommendations</li>
                  <li>To communicate with you about updates, features, and support</li>
                  <li>To detect, prevent, and address technical issues and abuse</li>
                  <li>To comply with legal obligations</li>
                  <li>To analyze usage patterns and improve our services (with your consent)</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Lock className="w-5 h-5 text-indigo-400" />
                  4. Data Security
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  We implement industry-standard security measures to protect your personal information, including:
                </p>
                <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4 mt-4">
                  <li>Encryption of data in transit (TLS/SSL) and at rest</li>
                  <li>Secure password hashing using bcrypt</li>
                  <li>Regular security audits and penetration testing</li>
                  <li>Access controls and authentication requirements</li>
                  <li>PCI-DSS compliant payment processing via Cashfree</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">5. Data Retention</h2>
                <div className="text-slate-300 space-y-2">
                  <p>We retain your data for the following periods:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li><strong>Account data:</strong> Until account deletion</li>
                    <li><strong>Generated content:</strong> 90 days after creation (unless saved)</li>
                    <li><strong>Payment records:</strong> 7 years (legal requirement)</li>
                    <li><strong>Usage logs:</strong> 12 months</li>
                  </ul>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">6. Your Rights (GDPR/CCPA)</h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  Depending on your location, you may have the following rights:
                </p>
                <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
                  <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
                  <li><strong>Right to Rectification:</strong> Correct inaccurate data</li>
                  <li><strong>Right to Erasure:</strong> Request deletion of your data</li>
                  <li><strong>Right to Portability:</strong> Export your data in a machine-readable format</li>
                  <li><strong>Right to Object:</strong> Opt out of certain data processing</li>
                  <li><strong>Right to Withdraw Consent:</strong> Revoke previously given consent</li>
                </ul>
                <p className="text-slate-300 mt-4">
                  To exercise these rights, visit your <Link to="/app/privacy" className="text-indigo-400 hover:text-indigo-300">Privacy Settings</Link> or contact us at the email below.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">7. Cookies</h2>
                <p className="text-slate-300 leading-relaxed">
                  We use essential cookies for authentication and session management. Optional analytics 
                  cookies help us understand usage patterns. You can manage cookie preferences in your 
                  browser settings. Disabling essential cookies may affect service functionality.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">8. Third-Party Services</h2>
                <div className="text-slate-300 space-y-2">
                  <p>We use the following third-party services:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li><strong>Cashfree:</strong> Payment processing (PCI-DSS compliant)</li>
                    <li><strong>Google OAuth:</strong> Optional social login (via Emergent Auth)</li>
                    <li><strong>SendGrid:</strong> Transactional emails</li>
                    <li><strong>AI Services:</strong> Content generation (Gemini, OpenAI)</li>
                  </ul>
                  <p className="mt-2">
                    These services have their own privacy policies. We do not sell your personal data.
                  </p>
                </div>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">9. Children's Privacy</h2>
                <p className="text-slate-300 leading-relaxed">
                  CreatorStudio AI is not intended for users under 13 years of age. We do not knowingly 
                  collect personal information from children. If you believe we have collected data from 
                  a child, please contact us immediately.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white mb-4">10. Changes to This Policy</h2>
                <p className="text-slate-300 leading-relaxed">
                  We may update this Privacy Policy periodically. We will notify you of significant changes 
                  via email or in-app notification. Continued use of the service after changes constitutes 
                  acceptance of the updated policy.
                </p>
              </section>

              <section className="bg-slate-800/30 rounded-xl p-6 mt-8">
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Mail className="w-5 h-5 text-indigo-400" />
                  Contact Us
                </h2>
                <p className="text-slate-300 mb-4">
                  For any privacy-related questions, concerns, or to exercise your data rights:
                </p>
                <div className="space-y-2 text-slate-300">
                  <p><strong>Email:</strong> <a href="mailto:krajapraveen@visionary-suite.com" className="text-indigo-400 hover:text-indigo-300">krajapraveen@visionary-suite.com</a></p>
                  <p><strong>Company:</strong> Visionary Suite</p>
                  <p><strong>Service:</strong> CreatorStudio AI</p>
                </div>
                <p className="text-slate-500 text-sm mt-4">
                  We aim to respond to all privacy inquiries within 30 days.
                </p>
              </section>
            </div>
          </div>
        </div>

        <div className="text-center mt-8">
          <Link to="/">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
