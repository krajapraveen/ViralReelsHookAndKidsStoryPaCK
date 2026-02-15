import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { 
  Sparkles, ArrowLeft, Scale, Shield, CheckCircle, 
  AlertTriangle, FileText, BookOpen, Copyright, Info
} from 'lucide-react';

export default function CopyrightInfo() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-500" />
              <span className="text-xl font-bold">Copyright & Legal</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Header Section */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 text-white">
          <div className="flex items-center gap-3 mb-4">
            <Copyright className="w-8 h-8" />
            <h1 className="text-3xl font-bold">Copyright & Content Guidelines</h1>
          </div>
          <p className="text-indigo-100 text-lg">
            Understanding intellectual property rights for AI-generated content
          </p>
        </div>

        {/* AI-Generated Content Ownership */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Scale className="w-5 h-5 text-indigo-500" />
            AI-Generated Content Ownership
          </h2>
          <div className="space-y-4 text-slate-600">
            <p>
              <strong>Who owns the content?</strong> Content generated through CreatorStudio AI is 
              created based on your inputs and prompts. Here's how ownership works:
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="font-semibold text-green-700">You Own</span>
                </div>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• Your original prompts and inputs</li>
                  <li>• The specific output generated for you</li>
                  <li>• Rights to use content commercially</li>
                  <li>• Ability to modify and adapt outputs</li>
                </ul>
              </div>
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  <span className="font-semibold text-amber-700">Considerations</span>
                </div>
                <ul className="text-sm text-amber-700 space-y-1">
                  <li>• AI may generate similar outputs for others</li>
                  <li>• Copyright registration may vary by jurisdiction</li>
                  <li>• Some platforms have specific AI content policies</li>
                  <li>• Always verify legal requirements in your region</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Content Usage Guidelines */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-500" />
            Content Usage Guidelines
          </h2>
          <div className="space-y-4">
            <div className="p-4 bg-slate-50 rounded-lg">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Permitted Uses
              </h3>
              <ul className="text-sm text-slate-600 space-y-1 ml-6">
                <li>• Social media content (Instagram, TikTok, YouTube, etc.)</li>
                <li>• Business marketing and advertising</li>
                <li>• Educational materials and presentations</li>
                <li>• Personal projects and portfolios</li>
                <li>• Commercial products (with proper attribution)</li>
                <li>• Modification and derivative works</li>
              </ul>
            </div>
            
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <h3 className="font-semibold mb-2 flex items-center gap-2 text-red-700">
                <AlertTriangle className="w-4 h-4" />
                Prohibited Uses
              </h3>
              <ul className="text-sm text-red-700 space-y-1 ml-6">
                <li>• Creating content that infringes on third-party copyrights</li>
                <li>• Generating content that violates trademark laws</li>
                <li>• Creating defamatory or illegal content</li>
                <li>• Impersonating real individuals without consent</li>
                <li>• Generating harmful, hateful, or discriminatory content</li>
                <li>• Creating content for fraudulent purposes</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Kids Story Content Guidelines */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-purple-500" />
            Kids Story Content Guidelines
          </h2>
          <div className="space-y-4 text-slate-600">
            <p>
              Our Kids Story Generator is designed to create original, age-appropriate content. 
              Here's what you should know:
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <h3 className="font-semibold text-purple-700 mb-2">Content Safety</h3>
                <ul className="text-sm text-purple-700 space-y-1">
                  <li>• All stories are filtered for appropriate content</li>
                  <li>• Violence, adult themes, and harmful content are blocked</li>
                  <li>• Characters are original (not based on copyrighted characters)</li>
                  <li>• Stories promote positive values and morals</li>
                </ul>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="font-semibold text-blue-700 mb-2">Best Practices</h3>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• Review all generated content before publishing</li>
                  <li>• Ensure content is appropriate for your target age group</li>
                  <li>• Avoid using real children's images or names</li>
                  <li>• Follow platform-specific guidelines for kids' content</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Third-Party Copyright Notice */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-500" />
            Third-Party Copyright Protection
          </h2>
          <div className="space-y-4 text-slate-600">
            <p>
              CreatorStudio AI is designed to generate original content. However, users are 
              responsible for ensuring their inputs don't infringe on existing copyrights.
            </p>
            <div className="p-4 bg-slate-50 rounded-lg">
              <h3 className="font-semibold mb-2">Avoid in Your Prompts:</h3>
              <ul className="text-sm space-y-1 ml-4">
                <li>• Copyrighted character names (Mickey Mouse, Spider-Man, etc.)</li>
                <li>• Trademarked brand names or logos</li>
                <li>• Song lyrics or copyrighted text</li>
                <li>• Specific scenes from movies/TV shows</li>
                <li>• Celebrity names or likenesses</li>
              </ul>
            </div>
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div className="flex items-start gap-2">
                <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-amber-700 mb-1">DMCA Notice</h3>
                  <p className="text-sm text-amber-700">
                    If you believe content generated through our platform infringes on your 
                    copyright, please contact us at <strong>legal@creatorstudio.ai</strong> 
                    with details of the alleged infringement.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Platform-Specific Guidelines */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-500" />
            Platform-Specific Guidelines
          </h2>
          <div className="space-y-3">
            <div className="p-4 bg-gradient-to-r from-pink-50 to-purple-50 rounded-lg border border-pink-200">
              <h3 className="font-semibold text-pink-700 mb-2">Instagram / TikTok</h3>
              <p className="text-sm text-pink-700">
                Both platforms allow AI-generated content but may require disclosure. 
                Check their current community guidelines for AI content policies.
              </p>
            </div>
            <div className="p-4 bg-gradient-to-r from-red-50 to-orange-50 rounded-lg border border-red-200">
              <h3 className="font-semibold text-red-700 mb-2">YouTube</h3>
              <p className="text-sm text-red-700">
                YouTube requires disclosure of AI-generated content in certain categories. 
                Made for Kids content has additional requirements.
              </p>
            </div>
            <div className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
              <h3 className="font-semibold text-blue-700 mb-2">General Social Media</h3>
              <p className="text-sm text-blue-700">
                Always review the terms of service for each platform where you publish 
                AI-generated content. Policies are evolving rapidly.
              </p>
            </div>
          </div>
        </div>

        {/* Legal Disclaimer */}
        <div className="bg-slate-100 rounded-xl p-6">
          <h3 className="font-bold mb-2 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-slate-600" />
            Legal Disclaimer
          </h3>
          <p className="text-sm text-slate-600">
            This information is provided for educational purposes only and does not constitute 
            legal advice. Copyright and intellectual property laws vary by jurisdiction and are 
            subject to change. For specific legal questions about your use case, please consult 
            with a qualified attorney in your jurisdiction.
          </p>
        </div>

        {/* Contact Section */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 text-center">
          <h3 className="font-bold mb-2">Have Questions?</h3>
          <p className="text-slate-600 mb-4">
            If you have specific questions about copyright or content usage, we're here to help.
          </p>
          <div className="flex gap-4 justify-center">
            <Link to="/contact">
              <Button variant="outline">Contact Support</Button>
            </Link>
            <a href="mailto:legal@creatorstudio.ai">
              <Button>Email Legal Team</Button>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
