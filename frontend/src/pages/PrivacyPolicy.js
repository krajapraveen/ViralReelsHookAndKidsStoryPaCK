import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { ArrowLeft, Shield, Lock, Eye, FileText, Globe, Mail } from 'lucide-react';

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Home
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            <span className="text-xl font-bold">Privacy Policy</span>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl border border-slate-200 p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Privacy Policy</h1>
            <p className="text-slate-500">Last updated: December 2025</p>
          </div>

          <div className="prose prose-slate max-w-none space-y-8">
            {/* Introduction */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">1. Introduction</h2>
              </div>
              <p className="text-slate-600">
                Welcome to CreatorStudio AI ("we," "our," or "us"). We are committed to protecting your personal 
                information and your right to privacy. This Privacy Policy explains how we collect, use, disclose, 
                and safeguard your information when you use our services.
              </p>
              <p className="text-slate-600">
                By using CreatorStudio AI, you agree to the collection and use of information in accordance with 
                this policy. If you do not agree with our policies and practices, please do not use our services.
              </p>
            </section>

            {/* Information We Collect */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Eye className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">2. Information We Collect</h2>
              </div>
              
              <h3 className="font-semibold text-lg mt-4">2.1 Personal Information</h3>
              <p className="text-slate-600">We collect information you provide directly:</p>
              <ul className="list-disc list-inside text-slate-600 space-y-1">
                <li>Name and email address during registration</li>
                <li>Payment information (processed securely via Razorpay)</li>
                <li>Content you create using our AI tools</li>
                <li>Communications with our support team</li>
              </ul>

              <h3 className="font-semibold text-lg mt-4">2.2 Automatically Collected Information</h3>
              <ul className="list-disc list-inside text-slate-600 space-y-1">
                <li>Device information (browser type, operating system)</li>
                <li>Usage data (features used, time spent)</li>
                <li>IP address and approximate location</li>
                <li>Cookies and similar tracking technologies</li>
              </ul>
            </section>

            {/* How We Use Information */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <FileText className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">3. How We Use Your Information</h2>
              </div>
              <p className="text-slate-600">We use your information to:</p>
              <ul className="list-disc list-inside text-slate-600 space-y-1">
                <li>Provide and maintain our AI content generation services</li>
                <li>Process payments and manage your account</li>
                <li>Send service updates and promotional communications (with your consent)</li>
                <li>Improve our services and develop new features</li>
                <li>Detect and prevent fraud or abuse</li>
                <li>Comply with legal obligations</li>
              </ul>
            </section>

            {/* Data Retention */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Lock className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">4. Data Retention</h2>
              </div>
              <p className="text-slate-600">
                We retain your personal data only for as long as necessary to fulfill the purposes described 
                in this policy, unless a longer retention period is required by law. Generated content is 
                retained for 90 days after creation unless you delete it earlier.
              </p>
            </section>

            {/* Your Rights (GDPR/CCPA) */}
            <section className="bg-indigo-50 rounded-lg p-6 border border-indigo-100">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5 text-indigo-600" />
                <h2 className="text-xl font-semibold m-0 text-indigo-900">5. Your Rights (GDPR & CCPA)</h2>
              </div>
              <p className="text-slate-700 mb-4">
                Depending on your location, you may have the following rights:
              </p>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Access</h4>
                  <p className="text-sm text-slate-600">Request a copy of your personal data</p>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Rectification</h4>
                  <p className="text-sm text-slate-600">Correct inaccurate personal data</p>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Erasure</h4>
                  <p className="text-sm text-slate-600">Request deletion of your data</p>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Portability</h4>
                  <p className="text-sm text-slate-600">Export your data in a machine-readable format</p>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Object</h4>
                  <p className="text-sm text-slate-600">Opt out of certain data processing</p>
                </div>
                <div className="bg-white rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-800">Right to Withdraw Consent</h4>
                  <p className="text-sm text-slate-600">Withdraw consent at any time</p>
                </div>
              </div>
              <p className="text-sm text-indigo-700 mt-4">
                To exercise these rights, visit your <Link to="/app/privacy" className="underline font-medium">Privacy Settings</Link> or contact us.
              </p>
            </section>

            {/* Data Security */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Lock className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">6. Data Security</h2>
              </div>
              <p className="text-slate-600">
                We implement industry-standard security measures to protect your data:
              </p>
              <ul className="list-disc list-inside text-slate-600 space-y-1">
                <li>Encryption in transit (TLS/SSL) and at rest</li>
                <li>Secure payment processing via Razorpay (PCI-DSS compliant)</li>
                <li>Regular security audits and penetration testing</li>
                <li>Access controls and employee training</li>
              </ul>
            </section>

            {/* Third-Party Services */}
            <section>
              <h2 className="text-xl font-semibold mb-4">7. Third-Party Services</h2>
              <p className="text-slate-600">We use the following third-party services:</p>
              <ul className="list-disc list-inside text-slate-600 space-y-1">
                <li><strong>Razorpay</strong> - Payment processing</li>
                <li><strong>OpenAI</strong> - AI content generation</li>
                <li><strong>Google</strong> - Authentication services</li>
              </ul>
              <p className="text-slate-600 mt-2">
                These services have their own privacy policies governing how they handle your data.
              </p>
            </section>

            {/* Children's Privacy */}
            <section>
              <h2 className="text-xl font-semibold mb-4">8. Children's Privacy</h2>
              <p className="text-slate-600">
                Our services are not intended for children under 13. We do not knowingly collect personal 
                information from children under 13. If you believe we have collected such information, 
                please contact us immediately.
              </p>
            </section>

            {/* Changes to Policy */}
            <section>
              <h2 className="text-xl font-semibold mb-4">9. Changes to This Policy</h2>
              <p className="text-slate-600">
                We may update this Privacy Policy from time to time. We will notify you of significant changes 
                by email or through a prominent notice on our website. Your continued use of our services 
                after such changes constitutes acceptance of the updated policy.
              </p>
            </section>

            {/* Contact */}
            <section className="bg-slate-100 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Mail className="w-5 h-5 text-indigo-500" />
                <h2 className="text-xl font-semibold m-0">10. Contact Us</h2>
              </div>
              <p className="text-slate-600 mb-4">
                If you have questions about this Privacy Policy or your personal data, contact us:
              </p>
              <div className="bg-white rounded-lg p-4">
                <p className="font-medium">CreatorStudio AI Privacy Team</p>
                <p className="text-slate-600">Email: privacy@creatorstudio.ai</p>
                <p className="text-slate-600">Response time: Within 48 hours</p>
              </div>
            </section>
          </div>
        </div>

        {/* Quick Links */}
        <div className="mt-8 flex flex-wrap gap-4 justify-center">
          <Link to="/terms">
            <Button variant="outline">Terms of Service</Button>
          </Link>
          <Link to="/contact">
            <Button variant="outline">Contact Us</Button>
          </Link>
          <Link to="/app/privacy">
            <Button className="bg-indigo-500 hover:bg-indigo-600">Manage My Privacy</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
