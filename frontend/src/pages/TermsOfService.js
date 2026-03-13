import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Sparkles, ArrowLeft, FileText, Scale, Shield, AlertCircle, CreditCard, Users, Ban } from 'lucide-react';

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950">
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
              <span className="text-xl font-bold text-white">Terms of Service</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-slate-800 p-8">
          <div className="prose prose-invert max-w-none">
            <div className="flex items-center gap-3 mb-6">
              <Scale className="w-8 h-8 text-indigo-500" />
              <h1 className="text-3xl font-bold text-white m-0">Terms of Service</h1>
            </div>
            
            <p className="text-slate-400 text-sm mb-8">
              Last Updated: February 28, 2026
            </p>

            <div className="space-y-8">
              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  1. Acceptance of Terms
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  By accessing or using Visionary Suite ("the Service"), operated by Visionary Suite ("we," "our," or "us"), 
                  you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our Service.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Users className="w-5 h-5 text-indigo-400" />
                  2. Description of Service
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  Visionary Suite provides AI-powered content creation tools including but not limited to:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>Reel Script Generator</li>
                  <li>Story Generator</li>
                  <li>Photo to Comic Converter</li>
                  <li>Comic Storybook Builder</li>
                  <li>Coloring Book Generator</li>
                  <li>Various creator tools and utilities</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Shield className="w-5 h-5 text-indigo-400" />
                  3. User Accounts
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  To use certain features of the Service, you must register for an account. You agree to:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>Provide accurate and complete registration information</li>
                  <li>Maintain the security of your account credentials</li>
                  <li>Notify us immediately of any unauthorized access</li>
                  <li>Be responsible for all activities under your account</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <CreditCard className="w-5 h-5 text-indigo-400" />
                  4. Credits and Payments
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  Our Service operates on a credit-based system:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>New users receive 10 free credits upon registration</li>
                  <li>Additional credits can be purchased through our billing page</li>
                  <li>Credits are non-refundable once used for generation</li>
                  <li>Subscription plans provide monthly credit allocations</li>
                  <li>Unused credits from subscriptions do not roll over unless specified</li>
                </ul>
                <p className="text-slate-300 leading-relaxed mt-4">
                  All payments are processed securely through Cashfree. By making a purchase, you agree to 
                  Cashfree's terms of service and our refund policy.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <AlertCircle className="w-5 h-5 text-indigo-400" />
                  5. User Content and Intellectual Property
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  <strong className="text-white">Your Content:</strong> You retain ownership of content you upload to our Service. 
                  By uploading content, you grant us a license to process it for the purpose of providing our services.
                </p>
                <p className="text-slate-300 leading-relaxed mb-4">
                  <strong className="text-white">Generated Content:</strong> Content generated using our AI tools belongs to you, 
                  subject to the following conditions:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>You may use generated content for personal or commercial purposes</li>
                  <li>You are responsible for ensuring generated content doesn't infringe third-party rights</li>
                  <li>You may not claim the AI-generated content was created entirely by you without AI assistance</li>
                </ul>
                <p className="text-slate-300 leading-relaxed mt-4">
                  <strong className="text-white">Our Content:</strong> The Service, including its design, features, and branding, 
                  is owned by Visionary Suite and protected by intellectual property laws.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Ban className="w-5 h-5 text-indigo-400" />
                  6. Prohibited Uses
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  You agree NOT to use the Service to:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>Create content that infringes copyrights, trademarks, or other intellectual property rights</li>
                  <li>Generate content featuring copyrighted characters (Disney, Marvel, etc.) without authorization</li>
                  <li>Create illegal, harmful, threatening, abusive, or harassing content</li>
                  <li>Generate explicit adult content or content harmful to minors</li>
                  <li>Attempt to reverse engineer or compromise the Service</li>
                  <li>Use automated systems to abuse the Service</li>
                  <li>Violate any applicable laws or regulations</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Shield className="w-5 h-5 text-indigo-400" />
                  7. Disclaimer of Warranties
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. WE DO NOT GUARANTEE THAT:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4 mt-4">
                  <li>The Service will be uninterrupted or error-free</li>
                  <li>Generated content will meet your specific requirements</li>
                  <li>Any defects will be corrected</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Scale className="w-5 h-5 text-indigo-400" />
                  8. Limitation of Liability
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, VISIONARY SUITE SHALL NOT BE LIABLE FOR ANY INDIRECT, 
                  INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF THE SERVICE.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  9. Refund Policy
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  Refunds may be requested within 7 days of purchase under the following conditions:
                </p>
                <ul className="list-disc list-inside text-slate-300 space-y-2 ml-4">
                  <li>Technical issues preventing service use (with evidence)</li>
                  <li>Duplicate charges</li>
                  <li>Unauthorized transactions</li>
                </ul>
                <p className="text-slate-300 leading-relaxed mt-4">
                  Credits that have been used for content generation are non-refundable. 
                  Contact support@visionary-suite.com for refund requests.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <AlertCircle className="w-5 h-5 text-indigo-400" />
                  10. Termination
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  We reserve the right to suspend or terminate your account at any time for violations of these terms. 
                  Upon termination, your right to use the Service ceases immediately. 
                  Any unused credits will be forfeited upon termination for cause.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  11. Changes to Terms
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  We may update these Terms from time to time. We will notify you of significant changes by posting 
                  the new Terms on this page and updating the "Last Updated" date. Your continued use of the Service 
                  after changes constitutes acceptance of the new Terms.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Scale className="w-5 h-5 text-indigo-400" />
                  12. Governing Law
                </h2>
                <p className="text-slate-300 leading-relaxed">
                  These Terms shall be governed by and construed in accordance with the laws of India, 
                  without regard to its conflict of law provisions. Any disputes arising from these Terms 
                  shall be subject to the exclusive jurisdiction of the courts in Hyderabad, Telangana, India.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Users className="w-5 h-5 text-indigo-400" />
                  13. Contact Us
                </h2>
                <p className="text-slate-300 leading-relaxed mb-4">
                  If you have questions about these Terms, please contact us:
                </p>
                <div className="bg-slate-800/50 rounded-lg p-4 space-y-2">
                  <p className="text-slate-300"><strong className="text-white">Email:</strong> support@visionary-suite.com</p>
                  <p className="text-slate-300"><strong className="text-white">Website:</strong> www.visionary-suite.com</p>
                  <p className="text-slate-300"><strong className="text-white">Company:</strong> Visionary Suite</p>
                </div>
              </section>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center">
          <Link to="/privacy-policy">
            <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800">
              View Privacy Policy
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
