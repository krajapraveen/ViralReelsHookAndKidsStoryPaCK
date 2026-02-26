import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { 
  Sparkles, ArrowLeft, Scale, Shield, CheckCircle, 
  AlertTriangle, FileText, BookOpen, Copyright, Info,
  Users, Globe, Lock, Award, Heart, Zap
} from 'lucide-react';

export default function CopyrightInfo() {
  const sections = [
    {
      title: "Content Ownership",
      icon: Award,
      color: "purple",
      items: [
        { label: "Your Inputs", desc: "All prompts, ideas, and creative direction you provide remain your intellectual property." },
        { label: "Generated Content", desc: "AI-generated text, scripts, and stories created through our platform are yours to use commercially." },
        { label: "Kids Stories", desc: "Stories generated for children are 100% owned by you with full commercial rights." },
        { label: "Reel Scripts", desc: "All reel scripts and content calendars are yours to publish on any platform." }
      ]
    },
    {
      title: "Usage Rights",
      icon: CheckCircle,
      color: "green",
      items: [
        { label: "Commercial Use", desc: "You may use generated content for commercial purposes including monetized social media." },
        { label: "Modification", desc: "You can edit, adapt, and transform generated content without restrictions." },
        { label: "Publication", desc: "Publish on any platform - YouTube, Instagram, TikTok, books, etc." },
        { label: "Resale", desc: "You may sell products (like story books) containing generated content." }
      ]
    },
    {
      title: "Restrictions",
      icon: AlertTriangle,
      color: "amber",
      items: [
        { label: "Platform Branding", desc: "Do not claim to be CreatorStudio AI or use our branding without permission." },
        { label: "Harmful Content", desc: "Generated content must not be used for illegal or harmful purposes." },
        { label: "Misrepresentation", desc: "Do not claim AI-generated content was created by humans for deceptive purposes." },
        { label: "Copyright Infringement", desc: "Do not use our tools to intentionally copy or infringe on others' copyrights." }
      ]
    }
  ];

  const faqs = [
    {
      q: "Can I sell story books created with CreatorStudio AI?",
      a: "Yes! Stories generated through our platform are yours to publish and sell. Many users create children's books, coloring books, and educational materials using our story generator."
    },
    {
      q: "Do I need to credit CreatorStudio AI?",
      a: "No attribution is required. However, you're welcome to mention us if you'd like to support our platform."
    },
    {
      q: "Can I use content for my business/brand?",
      a: "Absolutely. All content is suitable for commercial use including brand content, marketing materials, and monetized social media posts."
    },
    {
      q: "What about the images in PDF story books?",
      a: "The placeholder images and avatars used in PDFs are from free, royalty-free sources (Unsplash, DiceBear). You have full rights to use the complete PDF."
    },
    {
      q: "Can multiple people use the same generated content?",
      a: "While you own your generated content, AI systems may produce similar outputs for similar inputs. Your specific outputs and customizations are uniquely yours."
    },
    {
      q: "What happens to my content if I cancel?",
      a: "All content you've generated and downloaded remains yours forever. We don't retain exclusive rights to your creations."
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-indigo-950 to-slate-950 text-white">
      <header className="bg-slate-900/80 backdrop-blur-sm border-b border-slate-700/50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/app">
              <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-white/10">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Copyright className="w-6 h-6 text-purple-400" />
              <span className="text-xl font-bold text-white">Copyright & Legal</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-8 text-white">
          <div className="flex items-center gap-3 mb-4">
            <Scale className="w-10 h-10" />
            <div>
              <h1 className="text-3xl font-bold">Content Rights & Guidelines</h1>
              <p className="text-purple-200">Understanding your rights with AI-generated content</p>
            </div>
          </div>
          <div className="mt-6 grid md:grid-cols-3 gap-4">
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <CheckCircle className="w-6 h-6 mb-2" />
              <p className="font-semibold">100% Commercial Use</p>
              <p className="text-sm text-purple-200">Full rights to monetize</p>
            </div>
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <Award className="w-6 h-6 mb-2" />
              <p className="font-semibold">You Own It</p>
              <p className="text-sm text-purple-200">Your content, your property</p>
            </div>
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur">
              <Globe className="w-6 h-6 mb-2" />
              <p className="font-semibold">Publish Anywhere</p>
              <p className="text-sm text-purple-200">Any platform, any format</p>
            </div>
          </div>
        </div>

        {/* Main Sections */}
        {sections.map((section, idx) => {
          const Icon = section.icon;
          const colorClasses = {
            purple: { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-200' },
            green: { bg: 'bg-green-100', text: 'text-green-600', border: 'border-green-200' },
            amber: { bg: 'bg-amber-100', text: 'text-amber-600', border: 'border-amber-200' }
          };
          const colors = colorClasses[section.color];
          
          return (
            <div key={idx} className={`bg-white rounded-xl border ${colors.border} p-6 shadow-sm`}>
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-slate-900">
                <div className={`p-2 ${colors.bg} rounded-lg`}>
                  <Icon className={`w-5 h-5 ${colors.text}`} />
                </div>
                {section.title}
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                {section.items.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50">
                    <CheckCircle className={`w-5 h-5 ${colors.text} mt-0.5 flex-shrink-0`} />
                    <div>
                      <p className="font-semibold text-slate-900">{item.label}</p>
                      <p className="text-sm text-slate-600">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

        {/* For Kids Stories */}
        <div className="bg-gradient-to-r from-pink-500 to-rose-500 rounded-xl p-6 text-white">
          <div className="flex items-center gap-3 mb-4">
            <Heart className="w-8 h-8" />
            <h2 className="text-xl font-bold">Special Note for Kids Story Creators</h2>
          </div>
          <p className="text-pink-100 mb-4">
            Parents and creators using our Kids Story Generator have complete ownership of all generated stories, characters, and narratives. You can:
          </p>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Publish stories as physical or digital books
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Create merchandise featuring story characters
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Use stories for educational purposes
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Personalize stories with your child's name (with Personalization Pack)
            </li>
          </ul>
        </div>

        {/* FAQs */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-slate-900">
            <Info className="w-5 h-5 text-purple-600" />
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div key={idx} className="border-b border-slate-100 pb-4 last:border-0 last:pb-0">
                <h3 className="font-semibold text-slate-900 mb-2">{faq.q}</h3>
                <p className="text-slate-600 text-sm">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Legal Disclaimer */}
        <div className="bg-slate-100 rounded-xl p-6">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2 text-slate-900">
            <FileText className="w-5 h-5 text-slate-600" />
            Legal Disclaimer
          </h2>
          <div className="text-sm text-slate-600 space-y-3">
            <p>
              <strong>No Legal Advice:</strong> This page provides general information about content rights and is not legal advice. For specific legal questions, consult a qualified attorney.
            </p>
            <p>
              <strong>AI Limitations:</strong> While we strive to generate original content, AI systems may occasionally produce outputs similar to existing works. Users are responsible for ensuring their use of generated content doesn't infringe on third-party rights.
            </p>
            <p>
              <strong>Platform Rights:</strong> CreatorStudio AI retains the right to use anonymized, aggregated data to improve our services. We do not claim ownership of individual user-generated content.
            </p>
            <p>
              <strong>Updates:</strong> This policy may be updated periodically. Continued use of our services constitutes acceptance of any changes.
            </p>
          </div>
        </div>

        {/* Contact */}
        <div className="text-center py-6">
          <p className="text-slate-600 mb-4">Have questions about content rights?</p>
          <Link to="/contact">
            <Button className="bg-purple-600 hover:bg-purple-700">
              Contact Support
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
